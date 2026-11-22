import time
import logging
from queue import Empty
from threading import Thread
from . import Peer

logger = logging.getLogger(__name__)


class PeerSeeker(Thread):
    """Connects to peers found by the tracker and hands them to the PeerManager."""

    def __init__(self, new_peers_queue, torrent, peer_manager, stop_event):
        Thread.__init__(self, daemon=True)
        self.stop_event = stop_event
        self.peer_manager = peer_manager
        self.new_peers_queue = new_peers_queue
        self.torrent = torrent

    def request_stop(self):
        self.stop_event.set()

    def run(self):
        failed_peers = set()
        reset_time = time.time()
        while not self.stop_event.is_set():
            # forget failures periodically so we can try again
            if time.time() - reset_time > 10:
                failed_peers = set()
                reset_time = time.time()
            try:
                ip, port = self.new_peers_queue.get(timeout=1)
            except Empty:
                continue
            try:
                if (ip, port) in failed_peers or (ip, port) in self.peer_manager.known_addresses():
                    continue
                peer = Peer.Peer(self.torrent, ip, port)
                if peer.connect(5):
                    self.peer_manager.add_peer(peer)
                else:
                    failed_peers.add((ip, port))
            except Exception:
                logger.exception("peer seeker error")
