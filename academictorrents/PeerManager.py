import time
import select
import struct
import logging
import threading
from threading import Thread
from . import Peer as peer_mod

logger = logging.getLogger(__name__)

MAX_OUTSTANDING = 32  # block requests in flight per peer
PEER_SILENCE_TIMEOUT = 30  # forget outstanding requests a peer never answered


class PeerManager(Thread):
    """Owns all BitTorrent peer sockets: reads, parses and requests in one thread."""

    def __init__(self, piece_manager, stop_event):
        Thread.__init__(self, daemon=True)
        self.peers = []
        self.lock = threading.Lock()
        self.piece_manager = piece_manager
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.tick()
            except Exception:
                logger.exception("peer manager error")
                self.stop_event.wait(1)
        with self.lock:
            for peer in self.peers:
                peer.close()
            self.peers = []

    def tick(self):
        with self.lock:
            peers = list(self.peers)
        self.start_connection_to_peers(peers)
        peers = [p for p in peers if p.socket]
        if not peers:
            self.stop_event.wait(0.5)
            return
        readable, _, _ = select.select([p.socket for p in peers], [], [], 0.5)
        by_socket = {p.socket: p for p in peers}
        for sock in readable:
            peer = by_socket[sock]
            try:
                data = sock.recv(1 << 16)
                if not data:
                    raise ConnectionError("connection closed")
                for msg_id, payload in peer.feed(data):
                    self.handle_message(peer, msg_id, payload)
            except Exception as e:
                logger.info("%s: removing peer because of: %s", peer.ip, e)
                self.remove_peer(peer)
        self.make_requests(peers)

    def handle_message(self, peer, msg_id, payload):
        if msg_id == peer_mod.CHOKE:
            peer.state['peer_choking'] = True
            peer.outstanding = 0  # a choke discards our pending requests
        elif msg_id == peer_mod.UNCHOKE:
            peer.state['peer_choking'] = False
        elif msg_id == peer_mod.INTERESTED:
            peer.state['peer_interested'] = True
        elif msg_id == peer_mod.NOT_INTERESTED:
            peer.state['peer_interested'] = False
        elif msg_id == peer_mod.HAVE and len(payload) == 4:
            peer.set_have(struct.unpack('!I', payload)[0])
        elif msg_id == peer_mod.BITFIELD:
            peer.set_bitfield(payload)
        elif msg_id == peer_mod.PIECE and len(payload) >= 8:
            index, offset = struct.unpack('!II', payload[:8])
            peer.outstanding = max(0, peer.outstanding - 1)
            peer.last_block_time = time.time()
            self.piece_manager.receive(index, offset, payload[8:])
        # REQUEST/CANCEL/PORT: we don't upload

    def make_requests(self, peers):
        now = time.time()
        for peer in peers:
            if not peer.has_handshaked or peer.state['peer_choking']:
                continue
            if peer.outstanding and now - peer.last_block_time > PEER_SILENCE_TIMEOUT:
                peer.outstanding = 0
                peer.last_block_time = now
            wanted = MAX_OUTSTANDING - peer.outstanding
            if wanted <= 0:
                continue
            requests = self.piece_manager.next_bt_requests(peer.has_piece, wanted)
            try:
                for index, offset, length in requests:
                    peer.send(peer.build_request(index, offset, length))
                    peer.outstanding += 1
            except Exception as e:
                logger.info("%s: removing peer because of: %s", peer.ip, e)
                self.remove_peer(peer)

    def start_connection_to_peers(self, peers):
        now = time.time()
        for peer in peers:
            if peer.socket and not peer.has_handshaked and peer.last_handshake_attempt < now - 10:
                peer.last_handshake_attempt = now
                try:
                    peer.handshake()
                    peer.send(peer.build_interested())
                except Exception as e:
                    logger.info("%s: removing peer because of: %s", peer.ip, e)
                    self.remove_peer(peer)

    def add_peer(self, peer):
        with self.lock:
            self.peers.append(peer)

    def remove_peer(self, peer):
        peer.close()
        with self.lock:
            if peer in self.peers:
                self.peers.remove(peer)

    def known_addresses(self):
        with self.lock:
            return {(p.ip, p.port) for p in self.peers}

    def request_stop(self):
        self.stop_event.set()
