"""Thread-safe file access with a small cache of open file descriptors."""
import os
import threading
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

_BINARY = getattr(os, "O_BINARY", 0)
_HAS_PIO = hasattr(os, "pread") and hasattr(os, "pwrite")


class _Handle(object):
    __slots__ = ("fd", "refs", "lock")

    def __init__(self, fd):
        self.fd = fd
        self.refs = 0
        self.lock = threading.Lock()  # only used where pread/pwrite are missing


class Storage(object):
    def __init__(self, max_open=64):
        self.max_open = max_open
        self._lock = threading.Lock()
        self._handles = OrderedDict()

    def _acquire(self, path, create):
        with self._lock:
            h = self._handles.get(path)
            if h is None:
                flags = os.O_RDWR | _BINARY | (os.O_CREAT if create else 0)
                try:
                    fd = os.open(path, flags, 0o644)
                except PermissionError:
                    if create:
                        raise
                    fd = os.open(path, os.O_RDONLY | _BINARY)
                h = _Handle(fd)
                self._handles[path] = h
            h.refs += 1
            self._handles.move_to_end(path)
            self._evict()
            return h

    def _release(self, h):
        with self._lock:
            h.refs -= 1
            self._evict()

    def _evict(self):
        # Only close handles nobody is using, oldest first.
        if len(self._handles) <= self.max_open:
            return
        for path in list(self._handles):
            if len(self._handles) <= self.max_open:
                break
            h = self._handles[path]
            if h.refs == 0:
                del self._handles[path]
                os.close(h.fd)

    def read(self, path, offset, length):
        """Read up to length bytes; returns fewer if the file is short or missing."""
        try:
            h = self._acquire(path, create=False)
        except (FileNotFoundError, NotADirectoryError, IsADirectoryError):
            return b""
        try:
            chunks = []
            got = 0
            while got < length:
                if _HAS_PIO:
                    chunk = os.pread(h.fd, length - got, offset + got)
                else:
                    with h.lock:
                        os.lseek(h.fd, offset + got, os.SEEK_SET)
                        chunk = os.read(h.fd, length - got)
                if not chunk:
                    break
                chunks.append(chunk)
                got += len(chunk)
            return b"".join(chunks)
        finally:
            self._release(h)

    def write(self, path, offset, data):
        h = self._acquire(path, create=True)
        try:
            view = memoryview(data)
            while view:
                if _HAS_PIO:
                    n = os.pwrite(h.fd, view, offset)
                else:
                    with h.lock:
                        os.lseek(h.fd, offset, os.SEEK_SET)
                        n = os.write(h.fd, view)
                view = view[n:]
                offset += n
        finally:
            self._release(h)

    def preallocate(self, path, length):
        """Create the file at its final size (sparse where supported)."""
        try:
            if os.path.getsize(path) >= length:
                return
        except OSError:
            pass
        h = self._acquire(path, create=True)
        try:
            os.ftruncate(h.fd, length)
        finally:
            self._release(h)

    def close(self):
        with self._lock:
            for h in self._handles.values():
                try:
                    os.close(h.fd)
                except OSError:
                    pass
            self._handles.clear()
