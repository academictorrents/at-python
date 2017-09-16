import logging
import socket

from bittorrent.peer import Peer
from bittorrent.torrent import Torrent
from bittorrent.tracker import TrackerFailure
from bittorrent.storage import DiskStorage

from tornado.concurrent import Future
from tornado.iostream import IOStream
from tornado.tcpserver import TCPServer
from tornado.gen import coroutine, Task, Return

from bittorrent.utils import peer_id, gen_debuggable
from bittorrent.p2p import Client

class Server(TCPServer):
    @gen_debuggable
    def __init__(self, torrent, max_peers=50, download_path='downloads', peer_id=peer_id(), storage_class=DiskStorage):
        TCPServer.__init__(self)

        self.peer_id = peer_id
        self.torrent = torrent

        self.max_peers = max_peers
        self.connected_peers = set()
        self.connecting_peers = set()
        self.unconnected_peers = set()

        self.storage = storage_class.from_torrent(torrent, base_path=download_path)

    @coroutine
    @gen_debuggable
    def start(self, num_processes=1):
        TCPServer.start(self, num_processes)

        self.connect_to_peers()

    @coroutine
    @gen_debuggable
    def connect_to_peers(self):
        self.peer_stats()

        num_active = len(self.connected_peers) + len(self.connecting_peers)

        if num_active != self.max_peers and not self.unconnected_peers:
            logging.info('No peers to choose from. Scraping trackers..')
            yield self.scrape_trackers()

        for i in range(min(len(self.unconnected_peers), self.max_peers - num_active)):
            self.connect(self.unconnected_peers.pop())

    @coroutine
    @gen_debuggable
    def scrape_tracker(self, tracker):
        logging.info('Announcing to tracker %s', tracker.url)

        seen_peers = self.connected_peers.union(self.connecting_peers)

        try:
            tracker_response = yield tracker.announce(self.peer_id, self.port, event='started', num_wanted=50)
            self.unconnected_peers.update(set(tracker_response.peers) - seen_peers)
        except TrackerFailure as e:
            print e
        finally:
            raise Return(tracker_response)

    @gen_debuggable
    def scrape_trackers(self):
        result = Future()

        for tracker in self.torrent.trackers:
            logging.info('Announcing to tracker %s', tracker.url)

            future = tracker.announce(self.peer_id, self.port, event='started', num_wanted=50)
            future.add_done_callback(lambda future: self.tracker_done(future, result))

        return result

    @gen_debuggable
    def tracker_done(self, future, result_future):
        if future.exception():
            logging.warning('Tracker could not be scraped: %s', future.exception())
            return

        result = future.result()
        seen_peers = self.connected_peers.union(self.connecting_peers)
        self.unconnected_peers.update(set(result.peers) - seen_peers)

        logging.info('Scraped tracker %s', result)

        if self.unconnected_peers:
            result_future.set_result(True)

    @coroutine
    @gen_debuggable
    def connect(self, peer):
        logging.info('Connecting to %s', peer)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        stream = IOStream(sock)
        yield Task(stream.connect, (peer.address, peer.port))

        self.handle_stream(stream, (peer.address, peer.port), peer)

    @coroutine
    @gen_debuggable
    def handle_stream(self, stream, address, peer=None):
        if peer is None:
            peer = Peer(*address)

        logging.info('Received a connection from %s', peer)

        client = Client(stream, peer, self)
        stream.set_close_callback(lambda: self.peer_not_connected(client))

        self.connecting_peers.add(client)

        try:
            yield Task(client.handshake)
            self.peer_connected(client)
        except Exception as e:
            logging.exception(e)

    @gen_debuggable
    def peer_not_connected(self, client):
        if client in self.connecting_peers:
            logging.error('Could not connect to %s', client.peer)
            self.connecting_peers.remove(client)
        elif client in self.connected_peers:
            logging.error('Peer disconnected: %s', client.peer)
            self.connected_peers.remove(client)

        self.connect_to_peers()

    @gen_debuggable
    def peer_connected(self, client):
        self.peer_stats()
        logging.info('Connected to %s', client.peer)

        self.connecting_peers.remove(client)
        self.connected_peers.add(client)

    @gen_debuggable
    def announce_message(self, message):
        for client in self.connected_peers:
            if not client.peer_choking:
                client.send_message(message)

    @gen_debuggable
    def listen(self, port, address=""):
        self.port = port

        TCPServer.listen(self, port, address)

    def peer_stats(self):
        logging.error('We have {:>4} connected, {:>4} connecting, and {:>4} reserved.'.format(
            len(self.connected_peers),
            len(self.connecting_peers),
            len(self.unconnected_peers)
        ))
