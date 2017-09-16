import struct
import random
import logging

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.gen import coroutine, Task, Return

from bittorrent.utils import gen_debuggable
from bittorrent.protocol.message import (Messages, KeepAlive, Choke,
                                         Unchoke, Interested, NotInterested,
                                         Have, Bitfield, Request,
                                         Piece, Cancel, Port)

class Client(object):
    protocol = 'BitTorrent protocol'

    @gen_debuggable
    def __init__(self, stream, peer, server):
        self.stream = stream
        self.stream.set_close_callback(self.disconnected)

        self.peer = peer
        self.server = server

        self.am_choking = True
        self.peer_choking = True

        self.am_interested = False
        self.peer_interested = False

        self.peer_blocks = {}
        self.message_queue = []

        self.keepalive_callback = PeriodicCallback(lambda: self.send_message(KeepAlive()), 30 * 1000)
        self.keepalive_callback.start()

    @gen_debuggable
    def read_bytes(self, bytes):
        return Task(self.stream.read_bytes, bytes)

    @gen_debuggable
    def write(self, data):
        return Task(self.stream.write, data)

    @coroutine
    @gen_debuggable
    def get_message(self):
        bytes = yield self.read_bytes(4)
        length = struct.unpack('!I', bytes)[0]

        if length == 0:
            raise Return((KeepAlive, KeepAlive()))

        id = ord((yield self.read_bytes(1)))

        if id not in Messages:
            raise ValueError('Invalid message type')

        data = yield self.read_bytes(length - 1)
        result = (Messages[id], Messages[id].unpack(data))

        raise Return(result)

    @coroutine
    @gen_debuggable
    def send_message(self, message):
        logging.debug('Sending a %s', message.__class__.__name__)
        yield Task(self.stream.write, message.pack())
        logging.debug('Sent a %s', message.__class__.__name__)

    @coroutine
    @gen_debuggable
    def handshake(self):
        message = chr(len(self.protocol))
        message += self.protocol
        message += '\0\0\0\0\0\0\0\0'
        message += self.server.torrent.info_hash()
        message += self.server.peer_id

        logging.debug('Sending a handshake')
        logging.debug(repr(message))

        yield self.write(message)

        logging.debug('Listening for a handshake')

        protocol_length = yield self.read_bytes(1)

        if ord(protocol_length) != len(self.protocol):
            raise ValueError('Invalid protocol length')

        protocol = yield self.read_bytes(ord(protocol_length))

        if protocol != self.protocol:
            raise ValueError('Invalid protocol name')

        reserved_bytes = yield self.read_bytes(8)
        info_hash = yield self.read_bytes(20)

        if info_hash != self.server.torrent.info_hash():
            raise ValueError('Wrong info hash', info_hash)

        peer_id = yield self.read_bytes(20)

        if self.peer.id is not None and peer_id != self.peer.id:
            raise ValueError('Wrong peer id')

        # Set the peer's id if we didn't know it beforehand
        self.peer.id = peer_id

        logging.debug('Shook hands with %s', repr(peer_id))

        self.message_loop()

    @coroutine
    @gen_debuggable
    def message_loop(self):
        logging.debug('Starting the message loop...')
        bitfield = Bitfield(self.server.storage.to_bitfield())

        if bitfield:
            logging.debug('First message is a bitfield. Recording...')
            self.send_message(bitfield)

        while True:
            message_type, message = yield self.get_message()

            logging.debug('Client sent us a %s', message.__class__.__name__)

            try:
                if isinstance(message, KeepAlive):
                    self.got_keepalive(message)
                elif isinstance(message, Choke):
                    self.got_choke(message)
                elif isinstance(message, Unchoke):
                    self.got_unchoke(message)
                elif isinstance(message, Interested):
                    self.got_interested(message)
                elif isinstance(message, NotInterested):
                    self.got_notinterested(message)
                elif isinstance(message, Have):
                    self.got_have(message)
                elif isinstance(message, Bitfield):
                    self.got_bitfield(message)
                elif isinstance(message, Request):
                    self.got_request(message)
                elif isinstance(message, Piece):
                    self.got_piece(message)
                    self.maybe_request_piece()
                elif isinstance(message, Cancel):
                    self.got_cancel(message)
                elif isinstance(message, Port):
                    self.got_port(message)
                else:
                    logging.error('Invalid message received %s', repr(message))
            except Exception as e:
                logging.exception(e)

            continue

            if self.is_endgame:
                if self.server.storage.verify():
                    logging.info('We got the file!')
                    IOLoop.instance().stop()

                for piece in self.missing_pieces:
                    for start in range(0, self.server.storage.block_size, 2**14):
                        self.server.announce_message(Request(piece, start, 2**14))

    def got_choke(self, message):
        self.peer_choking = True

    def got_unchoke(self, message):
        self.maybe_express_interest()
        self.maybe_request_piece()

    def maybe_request_piece(self):
        if not self.am_interested:
            return

        self.stop_if_completed()

        piece = random.choice(self.desired_pieces())

        if piece == self.server.storage.num_blocks - 1:
            size = self.server.storage.last_block_size
        else:
            size = self.server.storage.block_size

        length = min(size, 2**14)

        for start in range(0, size, length):
            self.send_message(Request(piece, start, length))

        if size % length != 0:
            end = length * (size // length)
            self.send_message(Request(piece, end, size - end))

    def stop_if_completed(self):
        if not self.desired_pieces() and self.server.storage.verify():
            logging.info('We got the file!')
            IOLoop.instance().stop()

    def got_bitfield(self, message):
        truncated = {key: value for key, value in message.bitfield.items() if key < self.server.storage.num_blocks}

        self.peer_blocks = truncated
        self.maybe_express_interest()

    def got_have(self, message):
        self.peer_blocks[message.piece] = True
        self.maybe_express_interest()

    def got_piece(self, message):
        logging.debug('Piece info: %d, %d, %d', message.index, message.begin, len(message.block))
        #self.peer.add_data_sample(len(message.block))
        self.server.storage.write_piece(message.index, message.begin, message.block)

        if self.server.storage.verify_block(message.index):
            logging.info('Got a complete block!')
            logging.critical(self.server.storage)

            self.stop_if_completed()
            self.server.announce_message(Have(message.index))

    def got_request(self, message):
        if message.length > 2**15:
            raise ValueError('Requested too much data')

        data = self.server.storage.read_piece(message.index, message.begin, message.length)
        self.send_message(Piece(message.index, message.begin, data))
    
    def got_interested(self, message):
        self.peer_interested = True

    def got_keepalive(self, message):
        pass

    @gen_debuggable
    def desired_pieces(self):
        want = [p for p in self.peer_blocks if not self.server.storage.blocks[p]]
        logging.debug('I want %s', repr(want))

        return want

    @gen_debuggable
    def maybe_express_interest(self):
        logging.debug('Possibly expressing interest')

        if not self.am_interested:
            logging.debug('I am not currently interested')

            if self.is_endgame:
                logging.debug('It\'s the endgame, so we\'re always interested')
            elif self.desired_pieces():
                logging.debug('Peer has something good. I am interested.')
            else:
                logging.debug('I am not interested and this peer has nothing.')
                return

            self.am_interested = True
            self.send_message(Interested())
        elif not self.desired_pieces():
            logging.debug('I was interested, but this peer has nothing. Now I am not interested')
            self.am_interested = False
            self.send_message(NotInterested())

        logging.debug('I am interested and this peer has stuff. This should not happen')

    @property
    @gen_debuggable
    def missing_pieces(self):
        return [i for i in range(self.server.storage.num_blocks) if not self.server.storage.blocks[i]]

    @property
    @gen_debuggable
    def is_endgame(self):
        return len(self.missing_pieces) / float(self.server.storage.num_blocks) < 0.05

    @gen_debuggable
    def disconnected(self, result=None):
        logging.info('Peer disconnected %s', self.peer)
        self.keepalive_callback.stop()
