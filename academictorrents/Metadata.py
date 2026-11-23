"""Fetch a torrent's info dict from peers (BEP 9 ut_metadata over BEP 10)."""
import math
import queue
import socket
import struct
import hashlib
import logging
import threading
from types import SimpleNamespace
from . import bencoding
from .Peer import Peer, ProtocolError, PSTR

logger = logging.getLogger(__name__)

EXTENDED = 20
METADATA_PIECE = 16384
MAX_METADATA = 64 * 1024 * 1024
UT_METADATA_ID = 3  # our id for ut_metadata in the extension handshake


def build_handshake(info_hash, peer_id):
    reserved = bytearray(8)
    reserved[5] |= 0x10  # BEP 10 extension protocol
    return bytes([len(PSTR)]) + PSTR + bytes(reserved) + info_hash + peer_id


def extended_message(ext_id, payload):
    return struct.pack("!IBB", 2 + len(payload), EXTENDED, ext_id) + payload


def fetch_from_peer(addr, info_hash, peer_id, timeout=15, stop_event=None):
    """Download and verify the info dict from one peer. Returns raw bytes or raises."""
    sock = socket.create_connection(addr, timeout=timeout)
    try:
        sock.settimeout(timeout)
        peer = Peer(SimpleNamespace(number_of_pieces=0, info_hash=info_hash), addr[0], addr[1])
        peer.socket = sock
        sock.sendall(build_handshake(info_hash, peer_id))
        sock.sendall(extended_message(0, bencoding.encode({"m": {"ut_metadata": UT_METADATA_ID}, "v": "AT-Client"})))

        remote_id = None
        size = None
        pieces = {}
        while True:
            if stop_event is not None and stop_event.is_set():
                raise ProtocolError("stopped")
            data = sock.recv(1 << 16)
            if not data:
                raise ProtocolError("connection closed")
            for msg_id, payload in peer.feed(data):
                if msg_id != EXTENDED or not payload:
                    continue
                ext_id, body = payload[0], payload[1:]
                if ext_id == 0:  # extension handshake
                    hs = bencoding.decode(body, prefix=True)[0]
                    remote_id = (hs.get(b"m") or {}).get(b"ut_metadata")
                    size = hs.get(b"metadata_size")
                    if not remote_id or not isinstance(size, int) or not 0 < size <= MAX_METADATA:
                        raise ProtocolError("peer does not offer metadata")
                    for i in range(int(math.ceil(size / float(METADATA_PIECE)))):
                        sock.sendall(extended_message(remote_id, bencoding.encode({"msg_type": 0, "piece": i})))
                elif ext_id == UT_METADATA_ID and size:
                    header, end = bencoding.decode(body, prefix=True)
                    kind = header.get(b"msg_type")
                    if kind == 2:
                        raise ProtocolError("peer rejected metadata request")
                    if kind == 1:
                        pieces[header.get(b"piece")] = body[end:]
                        total = sum(len(p) for p in pieces.values())
                        if total >= size:
                            raw = b"".join(pieces[i] for i in sorted(pieces))[:size]
                            if hashlib.sha1(raw).digest() != info_hash:
                                raise ProtocolError("metadata hash mismatch")
                            return raw
    finally:
        sock.close()


def fetch_metadata(info_hash, peers_queue, peer_id, timeout=120, workers=8):
    """Try peers from peers_queue in parallel until one returns valid metadata.

    Returns the raw info dict bytes, or None on timeout.
    """
    done = threading.Event()
    result = []
    tried = set()
    tried_lock = threading.Lock()

    def worker():
        while not done.is_set():
            try:
                addr = peers_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            addr = (addr[0], int(addr[1]))
            with tried_lock:
                if addr in tried:
                    continue
                tried.add(addr)
            try:
                raw = fetch_from_peer(addr, info_hash, peer_id, stop_event=done)
                if not done.is_set():
                    result.append(raw)
                    done.set()
            except Exception as e:
                logger.debug("metadata from %s failed: %s", addr, e)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(workers)]
    for t in threads:
        t.start()
    done.wait(timeout)
    done.set()
    logger.info("metadata fetch tried %d peers", len(tried))
    return result[0] if result else None
