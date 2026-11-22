"""Offline test helpers: a local HTTP server with Range support and a torrent builder."""
import os
import re
import hashlib
import tempfile
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote
import bencode


class RangeHandler(BaseHTTPRequestHandler):
    """Serves server.files (url path -> bytes) with single-range support.

    server.mode: "ok", "ignore_range" (always 200 + full body),
    "corrupt_once" (first response per path has a flipped byte), "corrupt" (always).
    """

    def log_message(self, *args):
        pass

    def _body(self):
        path = unquote(self.path.split('?')[0])
        data = self.server.files.get(path)
        if data is None:
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None, None
        return path, data

    def do_HEAD(self):
        path, data = self._body()
        if data is None:
            return
        self.send_response(200)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()

    def do_GET(self):
        path, data = self._body()
        if data is None:
            return
        with self.server.lock:
            self.server.requests.append((path, self.headers.get('Range')))
            n = self.server.counts.get(path, 0)
            self.server.counts[path] = n + 1
        mode = self.server.mode
        m = re.match(r'bytes=(\d+)-(\d+)', self.headers.get('Range') or '')
        if mode == "ignore_range" or not m:
            self.send_response(200)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        start, end = int(m.group(1)), int(m.group(2))
        body = bytearray(data[start:end + 1])
        if body and (mode == "corrupt" or (mode == "corrupt_once" and n == 0)):
            body[0] ^= 0xFF
        self.send_response(206)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, start + len(body) - 1, len(data)))
        self.end_headers()
        self.wfile.write(bytes(body))


class LocalServer(object):
    def __init__(self, mode="ok"):
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), RangeHandler)
        self.httpd.daemon_threads = True
        self.httpd.files = {}
        self.httpd.mode = mode
        self.httpd.lock = threading.Lock()
        self.httpd.requests = []
        self.httpd.counts = {}
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return 'http://127.0.0.1:%d/' % self.httpd.server_address[1]

    def set_mode(self, mode):
        self.httpd.mode = mode

    def add(self, path, data):
        self.httpd.files['/' + path.lstrip('/')] = data

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def make_torrent(name, files, piece_length, web_seeds=(), announce=''):
    """Build a torrent. files: {relpath: bytes} (multi-file) or bytes (single file).

    The .torrent is cached where Torrent() looks first; returns (info_hash_hex, path).
    """
    if isinstance(files, (bytes, bytearray)):
        stream = bytes(files)
        info = {'name': name, 'piece length': piece_length, 'length': len(stream)}
    else:
        stream = b''.join(files.values())
        info = {'name': name, 'piece length': piece_length,
                'files': [{'length': len(d), 'path': rel.split('/')} for rel, d in files.items()]}
    info['pieces'] = b''.join(hashlib.sha1(stream[i:i + piece_length]).digest()
                              for i in range(0, len(stream), piece_length))
    meta = {'announce': announce, 'info': info}
    if web_seeds:
        meta['url-list'] = list(web_seeds)
    info_hash = hashlib.sha1(bencode.encode(info)).hexdigest()
    path = os.path.join(tempfile.gettempdir(), info_hash + '.torrent')
    with open(path, 'wb') as f:
        f.write(bencode.encode(meta))
    return info_hash, path


def serve_torrent(server, name, files):
    """Publish a torrent's files on the server, BEP 19 layout."""
    if isinstance(files, (bytes, bytearray)):
        server.add(name, bytes(files))
    else:
        for rel, data in files.items():
            server.add(name + '/' + rel, data)


def random_bytes(n, seed):
    out = bytearray()
    h = hashlib.sha256(str(seed).encode()).digest()
    while len(out) < n:
        h = hashlib.sha256(h).digest()
        out += h
    return bytes(out[:n])
