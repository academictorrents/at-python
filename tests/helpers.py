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


class FakeMetadataPeer(object):
    """TCP peer that serves a torrent's info dict over ut_metadata (BEP 9/10)."""

    def __init__(self, info_raw, info_hash, corrupt=False):
        import socket
        self.info_raw = bytearray(info_raw)
        if corrupt:
            self.info_raw[-2] ^= 0xFF
        self.info_hash = info_hash
        self.sock = socket.socket()
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(5)
        self.connections = 0
        threading.Thread(target=self._serve, daemon=True).start()

    @property
    def addr(self):
        return self.sock.getsockname()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            self.connections += 1
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        import struct
        from academictorrents import bencoding
        try:
            conn.settimeout(10)
            buf = b''
            while len(buf) < 68:
                buf += conn.recv(4096)
            reserved = bytearray(8)
            reserved[5] = 0x10
            conn.sendall(b'\x13BitTorrent protocol' + bytes(reserved) + self.info_hash + b'S' * 20)
            hs = bencoding.encode({'m': {'ut_metadata': 7}, 'metadata_size': len(self.info_raw)})
            conn.sendall(struct.pack('!IBB', 2 + len(hs), 20, 0) + hs)
            buf = buf[68:]
            while True:
                while len(buf) >= 4 and len(buf) >= 4 + struct.unpack('!I', buf[:4])[0]:
                    n = struct.unpack('!I', buf[:4])[0]
                    msg, buf = buf[4:4 + n], buf[4 + n:]
                    if n >= 2 and msg[0] == 20 and msg[1] == 7:
                        req = bencoding.decode(msg[2:])
                        i = req[b'piece']
                        chunk = bytes(self.info_raw[i * 16384:(i + 1) * 16384])
                        body = bencoding.encode({'msg_type': 1, 'piece': i, 'total_size': len(self.info_raw)}) + chunk
                        conn.sendall(struct.pack('!IBB', 2 + len(body), 20, 3) + body)
                data = conn.recv(65536)
                if not data:
                    return
                buf += data
        except Exception:
            pass
        finally:
            conn.close()

    def close(self):
        self.sock.close()


class FakeDHTNode(object):
    """UDP DHT node answering get_peers with fixed peers and/or nodes."""

    def __init__(self, peers=(), nodes=()):
        import socket
        self.peers = list(peers)
        self.nodes = list(nodes)  # [(node_id, (ip, port))]
        self.node_id = os.urandom(20)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('127.0.0.1', 0))
        self.queries = 0
        threading.Thread(target=self._serve, daemon=True).start()

    @property
    def addr(self):
        return self.sock.getsockname()

    def _serve(self):
        import socket
        import struct
        from academictorrents import bencoding
        while True:
            try:
                data, addr = self.sock.recvfrom(65536)
            except OSError:
                return
            msg = bencoding.decode(data)
            if msg.get(b'y') != b'q':
                continue
            self.queries += 1
            r = {b'id': self.node_id, b'token': b'tok'}
            if self.peers:
                r[b'values'] = [socket.inet_aton(ip) + struct.pack('!H', port) for ip, port in self.peers]
            if self.nodes:
                r[b'nodes'] = b''.join(nid + socket.inet_aton(ip) + struct.pack('!H', port)
                                       for nid, (ip, port) in self.nodes)
            self.sock.sendto(bencoding.encode({b't': msg[b't'], b'y': b'r', b'r': r}), addr)

    def close(self):
        self.sock.close()
