import socket
import struct
import random
import logging

from datetime import datetime, timedelta
from collections import defaultdict

from tornado.gen import coroutine, Return, Task
from tornado.concurrent import Future
from tornado.ioloop import IOLoop

from bittorrent import bencode, utils
from bittorrent.udp import UDPStream
from bittorrent.peer import Peer
from bittorrent.tracker.common import TrackerResponse, TrackerFailure

class UDPTracker(object):
    events = {
        None: 0,
        'none': 0,
        'completed': 1,
        'started': 2,
        'stopped': 3
    }

    def __init__(self, host, port, torrent, tier=0):
        self.host = host
        self.port = port

        self.torrent = torrent
        self.tier = tier

        self.connection_id = None
        self.connection_id_age = datetime.min
        self.requesting_connection_id = False

        self.pending_retries = defaultdict(int)
        self.pending_futures = {}
        self.pending_timers = {}

        self.socket = None
        self.stream = None

    @property
    def url(self):
        return 'udp://{self.host}:{self.port}'.format(self=self)

    def data_received(self, data):
        if not data:
            return

        logging.debug('Received some data')

        action, transaction_id = struct.unpack('!II', data[:8])

        if transaction_id in self.pending_retries:
            del self.pending_retries[transaction_id]

        if transaction_id in self.pending_timers:
            handle = self.pending_timers[transaction_id]
            IOLoop.instance().remove_timeout(handle)
            del self.pending_timers[transaction_id]

        if action == 0:  # CONNECT
            logging.debug('Received a CONNECT response for transaction %d', transaction_id)
            result = self.receive_connect(data[8:])
        elif action == 1:  # ANNOUNCE
            logging.debug('Received an ANNOUNCE response for transaction %d', transaction_id)
            result = self.receive_announce(data[8:])
        elif action == 2:  # SCRAPE
            logging.debug('Received a SCRAPE response for transaction %d', transaction_id)
            result = None
        elif action == 3:  # ERROR
            logging.debug('Received an ERROR response for transaction %d', transaction_id)
            raise Exception(data[8:])

        self.pending_futures[transaction_id].set_result(result)
        del self.pending_futures[transaction_id]

    def request_connection_id(self):
        self.connection_id = 0x41727101980

        return self.send_request(0)

    def receive_connect(self, data):
        self.connection_id = struct.unpack('!Q', data)[0]
        self.connection_id_age = datetime.now()

        logging.debug('Received a connection id: %d', self.connection_id)

    def receive_announce(self, data):
        interval, leechers, seeders = struct.unpack('!III', data[:12])
        num_peers = seeders + leechers
        peers = []

        for chunk in utils.grouper(6, data[12:12 + 6 * num_peers]):
            peers.append(Peer(*utils.unpack_peer_address(''.join(chunk))))

        return TrackerResponse(peers, interval)

    @coroutine
    def send_request(self, action, structure=None, arguments=None, transaction_id=None, attempt=1):
        logging.debug('Sending a type %d message', action)

        if action != 0 and datetime.now() - self.connection_id_age > timedelta(minutes=1):
            logging.debug('Connection id is too old or has not been established. Doing that before sending the actual message...')

            self.requesting_connection_id = True
            yield self.request_connection_id()

        if transaction_id is None:
            transaction_id = random.getrandbits(32)
            logging.debug('No transaction id was given. Generated a new one: %s', transaction_id)

        data = struct.pack('!QII', self.connection_id, action, transaction_id)

        if structure is not None and arguments is not None:
            data += struct.pack(structure, *arguments)

        if transaction_id not in self.pending_retries:
            self.pending_futures[transaction_id] = Future()

        self.pending_retries[transaction_id] += 1
        count = self.pending_retries[transaction_id]

        if count > 8:
            logging.error('Tracker did not respond to transaction %d after 8 tries', transaction_id)
            raise RuntimeError('Request was retried 8 times with no response')

        if transaction_id in self.pending_timers:
            IOLoop.instance().remove_timeout(self.pending_timers[transaction_id])

        retry_request = lambda: self.send_request(action, structure, arguments, transaction_id, attempt=attempt + 1)
        self.pending_timers[transaction_id] = IOLoop.instance().add_timeout(timedelta(seconds=15 * 2 ** count), retry_request)

        logging.debug('Current transaction has already been sent %d times.', self.pending_retries[transaction_id] - 1)
        logging.debug('Resending in %d seconds.', 15 * 2 ** count)

        self.stream.write(data)
        result = yield self.pending_futures[transaction_id]

        raise Return(result)

    @coroutine
    def announce(self, peer_id, port, event=None, num_wanted=-1):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stream = UDPStream(self.socket)

        try:
            self.stream.connect((self.host, self.port))
        except socket.error:
            raise TrackerFailure('Could not connect to tracker')

        self.stream.read_until_close(self.data_received, self.data_received)
        logging.debug('Announcing to UDP tracker...')

        try:
            response = yield self.send_request(
                action=1,
                structure='!20s20sQQQIIIiH',
                arguments=[
                    self.torrent.info_hash(),
                    peer_id,
                    self.torrent.downloaded,
                    self.torrent.remaining,
                    self.torrent.uploaded,
                    self.events[event],
                    0,
                    0,
                    -1,
                    port
                ]
            )

            logging.debug('Tracker responded with %s', repr(response))

            raise Return(response)
        except RuntimeError:
            raise TrackerFailure('Tracker did not respond after 8 attempts')
