import time
import logging
import threading
from collections import defaultdict
import requests
import urllib3
from . import utils
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class WebSeedError(Exception):
    pass


class HttpPeer(object):
    """One web seed (BEP 19) with per-file failure tracking and backoff."""
    MAX_FILE_FAILURES = 3  # ban this seed for a file after this many failures
    MAX_BACKOFF = 60
    CHUNK_SIZE = 1 << 16

    def __init__(self, url, torrent=None):
        self.url = url
        self.torrent = torrent
        self.sess = requests.Session()
        self.sess.headers.update(utils.HEADERS)
        self.lock = threading.Lock()
        self.file_failures = defaultdict(int)
        self.consecutive_failures = 0
        self.backoff_until = 0

    def url_for(self, relpath):
        if self.torrent is None:
            return self.url + relpath
        return self.torrent.web_seed_url(self.url, relpath)

    def can_serve(self, relpath, now=None):
        now = time.time() if now is None else now
        with self.lock:
            return now >= self.backoff_until and self.file_failures[relpath] < self.MAX_FILE_FAILURES

    def is_banned(self, relpath):
        with self.lock:
            return self.file_failures[relpath] >= self.MAX_FILE_FAILURES

    def record_failure(self, relpath):
        with self.lock:
            self.file_failures[relpath] += 1
            self.consecutive_failures += 1
            delay = min(self.MAX_BACKOFF, 2 ** (self.consecutive_failures - 1))
            self.backoff_until = time.time() + delay

    def record_success(self):
        with self.lock:
            self.consecutive_failures = 0
            self.backoff_until = 0

    def fetch(self, relpath, start, length, sink):
        """Stream bytes [start, start+length) of a file into sink(chunk).

        Returns the number of bytes delivered. Raises WebSeedError if the
        server does not honour the range request.
        """
        end = start + length - 1  # HTTP Range end is inclusive
        resp = self.sess.get(self.url_for(relpath), headers={'Range': 'bytes=%d-%d' % (start, end)},
                             stream=True, verify=False, timeout=(10, 30))
        try:
            if resp.status_code != 206:
                # Never read the body: a server ignoring Range sends the whole file.
                raise WebSeedError("HTTP %d for %s" % (resp.status_code, relpath))
            content_range = resp.headers.get('Content-Range', '')
            if content_range and not content_range.replace(' ', '').startswith('bytes%d-' % start):
                raise WebSeedError("unexpected Content-Range %r" % content_range)
            got = 0
            for chunk in resp.iter_content(self.CHUNK_SIZE):
                if not chunk:
                    continue
                chunk = chunk[:length - got]
                sink(chunk)
                got += len(chunk)
                if got >= length:
                    break
            return got
        finally:
            resp.close()

    def close(self):
        self.sess.close()
