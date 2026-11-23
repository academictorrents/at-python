"""Minimal Mainline DHT client (BEP 5) for finding peers by info hash.

Only what a downloader needs: iterative ``get_peers`` lookups, plus answering
ping/find_node/get_peers queries so other nodes keep talking to us. We never
``announce_peer`` because this client does not accept incoming connections.
"""
import os
import time
import queue
import socket
import struct
import logging
import threading
from . import bencoding

logger = logging.getLogger(__name__)

BOOTSTRAP = [
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.utorrent.com", 6881),
    ("dht.libtorrent.org", 25401),
]
ALPHA = 8  # parallel queries per lookup
K = 8  # closest nodes that must answer before a lookup is done
MAX_NODES = 2000


def _distance(a, b):
    return int.from_bytes(a, "big") ^ int.from_bytes(b, "big")


def parse_compact_nodes(data):
    nodes = []
    for i in range(0, len(data) - len(data) % 26, 26):
        node_id = data[i:i + 20]
        ip = socket.inet_ntoa(data[i + 20:i + 24])
        port = struct.unpack("!H", data[i + 24:i + 26])[0]
        if port:
            nodes.append((node_id, (ip, port)))
    return nodes


def parse_compact_peer(data):
    if len(data) != 6:
        return None
    port = struct.unpack("!H", data[4:6])[0]
    return (socket.inet_ntoa(data[:4]), port) if port else None


def encode_nodes(nodes):
    out = b""
    for node_id, (ip, port) in nodes:
        try:
            out += node_id + socket.inet_aton(ip) + struct.pack("!H", port)
        except OSError:
            pass
    return out


class DHT(object):
    def __init__(self, port=0, bootstrap=None):
        self.node_id = os.urandom(20)
        self.bootstrap = list(BOOTSTRAP if bootstrap is None else bootstrap)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", port))
        self.sock.settimeout(0.5)
        self.lock = threading.Lock()
        self.pending = {}  # transaction id -> response queue
        self.nodes = {}  # node id -> (ip, port), nodes that answered us
        self._tid = 0
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self._recv_loop, name="dht", daemon=True)
        self.thread.start()

    @property
    def port(self):
        return self.sock.getsockname()[1]

    def close(self):
        self.closed.set()
        try:
            self.sock.close()
        except OSError:
            pass

    # ---- transport ----------------------------------------------------------

    def _next_tid(self):
        with self.lock:
            self._tid = (self._tid + 1) & 0xFFFF
            return struct.pack("!H", self._tid)

    def _send(self, msg, addr):
        try:
            self.sock.sendto(bencoding.encode(msg), addr)
        except OSError as e:
            logger.debug("dht send to %s failed: %s", addr, e)

    def query(self, addr, q, args, responses):
        """Send a query; the reply (addr, msg) is put on the responses queue."""
        tid = self._next_tid()
        with self.lock:
            self.pending[tid] = (responses, time.time())
        args = dict(args, id=self.node_id)
        self._send({"t": tid, "y": "q", "q": q, "a": args}, addr)
        return tid

    def _recv_loop(self):
        while not self.closed.is_set():
            try:
                data, addr = self.sock.recvfrom(65536)
            except socket.timeout:
                self._expire()
                continue
            except OSError:
                if self.closed.is_set():
                    return
                continue
            try:
                msg = bencoding.decode(data)
                if not isinstance(msg, dict):
                    continue
                kind = msg.get(b"y")
                if kind in (b"r", b"e"):
                    with self.lock:
                        entry = self.pending.pop(msg.get(b"t"), None)
                    if entry:
                        entry[0].put((addr, msg))
                    r = msg.get(b"r")
                    if kind == b"r" and isinstance(r, dict) and len(r.get(b"id", b"")) == 20:
                        self._add_node(r[b"id"], addr)
                elif kind == b"q":
                    self._answer(msg, addr)
            except Exception as e:
                logger.debug("dht bad message from %s: %s", addr, e)

    def _expire(self):
        cutoff = time.time() - 30
        with self.lock:
            for tid in [t for t, (_, ts) in self.pending.items() if ts < cutoff]:
                del self.pending[tid]

    def _add_node(self, node_id, addr):
        with self.lock:
            if node_id in self.nodes or len(self.nodes) < MAX_NODES:
                self.nodes[node_id] = addr

    def closest_nodes(self, target, n=K):
        with self.lock:
            items = list(self.nodes.items())
        items.sort(key=lambda kv: _distance(kv[0], target))
        return items[:n]

    def _answer(self, msg, addr):
        q = msg.get(b"q")
        a = msg.get(b"a") or {}
        reply = {b"id": self.node_id}
        if q == b"find_node" or q == b"get_peers":
            target = a.get(b"target") or a.get(b"info_hash") or b""
            if len(target) == 20:
                reply[b"nodes"] = encode_nodes(self.closest_nodes(target))
            if q == b"get_peers":
                reply[b"token"] = os.urandom(4)
        elif q not in (b"ping", b"announce_peer"):
            self._send({b"t": msg.get(b"t", b""), b"y": b"e", b"e": [204, b"Method Unknown"]}, addr)
            return
        self._send({b"t": msg.get(b"t", b""), b"y": b"r", b"r": reply}, addr)

    # ---- lookup -------------------------------------------------------------

    def _bootstrap_addrs(self):
        addrs = []
        for host, port in self.bootstrap:
            try:
                addrs.append((socket.gethostbyname(host), port))
            except OSError as e:
                logger.debug("dht bootstrap %s unresolvable: %s", host, e)
        return addrs

    def get_peers(self, info_hash, timeout=30, on_peer=None, max_peers=200, stop_event=None):
        """Iteratively look up peers for info_hash. Returns the set of peers found."""
        deadline = time.time() + timeout
        responses = queue.Queue()
        peers = set()
        # candidates: addr -> distance (unknown ids sort last)
        unknown = 1 << 160
        candidates = {addr: _distance(nid, info_hash) for nid, addr in self.closest_nodes(info_hash, 32)}
        for addr in self._bootstrap_addrs():
            candidates.setdefault(addr, unknown)
        queried = set()
        answered = {}  # addr -> distance
        in_flight = {}  # addr -> time sent

        while time.time() < deadline and not self.closed.is_set():
            if stop_event is not None and stop_event.is_set():
                break
            now = time.time()
            for addr in [a for a, t in in_flight.items() if now - t > 3]:
                del in_flight[addr]  # unanswered; give up on it
            todo = sorted((d, a) for a, d in candidates.items() if a not in queried)
            # done when the K closest nodes that answered are closer than anything left
            best = sorted(answered.values())[:K]
            if len(best) >= K and (not todo or todo[0][0] > best[-1]) and not in_flight:
                break
            if not todo and not in_flight:
                break
            for d, addr in todo[:max(0, ALPHA - len(in_flight))]:
                queried.add(addr)
                in_flight[addr] = now
                self.query(addr, "get_peers", {"info_hash": info_hash}, responses)
            try:
                addr, msg = responses.get(timeout=0.3)
            except queue.Empty:
                continue
            in_flight.pop(addr, None)
            r = msg.get(b"r")
            if not isinstance(r, dict):
                continue
            node_id = r.get(b"id", b"")
            answered[addr] = _distance(node_id, info_hash) if len(node_id) == 20 else unknown
            for value in r.get(b"values") or []:
                peer = parse_compact_peer(value) if isinstance(value, bytes) else None
                if peer and peer not in peers:
                    peers.add(peer)
                    if on_peer:
                        on_peer(peer)
            for nid, naddr in parse_compact_nodes(r.get(b"nodes") or b""):
                if naddr not in candidates:
                    candidates[naddr] = _distance(nid, info_hash)
            if len(peers) >= max_peers:
                break
        logger.info("dht lookup found %d peers (%d nodes answered)", len(peers), len(answered))
        return peers


class DHTPeerFinder(threading.Thread):
    """Repeats DHT lookups during a download and feeds peers to a queue."""
    INTERVAL = 300

    def __init__(self, dht, info_hash, peers_queue, stop_event):
        threading.Thread.__init__(self, daemon=True)
        self.dht = dht
        self.info_hash = info_hash
        self.peers_queue = peers_queue
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.dht.get_peers(self.info_hash, timeout=60, on_peer=self.peers_queue.put,
                                   stop_event=self.stop_event)
            except Exception:
                logger.exception("dht lookup failed")
            self.stop_event.wait(self.INTERVAL)

    def request_stop(self):
        self.stop_event.set()
