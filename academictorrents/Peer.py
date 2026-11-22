import time
import socket
import logging
import struct
from .utils import Bitfield

logger = logging.getLogger(__name__)

PSTR = b"BitTorrent protocol"
HANDSHAKE_LEN = 49 + len(PSTR)
MAX_MESSAGE_LEN = 1 << 22  # larger than any block or bitfield we accept

CHOKE, UNCHOKE, INTERESTED, NOT_INTERESTED, HAVE, BITFIELD, REQUEST, PIECE, CANCEL, PORT = range(10)


class ProtocolError(Exception):
    pass


class Peer(object):
    def __init__(self, torrent, ip, port=6881):
        self.last_handshake_attempt = 0
        self.has_handshaked = False
        self.socket = None
        self.ip = ip
        self.port = port
        self.torrent = torrent
        self.buffer = bytearray()
        self.outstanding = 0  # block requests sent and not yet answered
        self.last_block_time = time.time()

        self.state = {
            'am_choking': True,
            'am_interested': False,
            'peer_choking': True,
            'peer_interested': False,
        }

        self.number_of_pieces = torrent.number_of_pieces
        self.bitfield = Bitfield(self.number_of_pieces)

    # ---- connection ---------------------------------------------------------

    def connect(self, timeout=10):
        if self.socket:
            return True
        try:
            self.socket = socket.create_connection((self.ip, self.port), timeout)
            logger.info("connected to peer ip: {0} - port: {1}".format(self.ip, self.port))
            return True
        except Exception as e:
            logger.debug("%s: connect failed: %s", self.ip, e)
        return False

    def send(self, msg):
        self.socket.sendall(msg)

    def close(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

    def handshake(self):
        self.send(self.build_handshake())

    # ---- parsing ------------------------------------------------------------

    def feed(self, data):
        """Add received bytes; return the complete messages as (id, payload).

        Keep-alives are consumed and not returned. Raises ProtocolError on a
        bad handshake or an absurd message length.
        """
        self.buffer += data
        messages = []
        if not self.has_handshaked:
            if len(self.buffer) < HANDSHAKE_LEN:
                return messages
            if self.buffer[0] != len(PSTR) or bytes(self.buffer[1:20]) != PSTR:
                raise ProtocolError("bad handshake from " + str(self.ip))
            if bytes(self.buffer[28:48]) != self.torrent.info_hash:
                raise ProtocolError("info hash mismatch from " + str(self.ip))
            del self.buffer[:HANDSHAKE_LEN]
            self.has_handshaked = True

        while len(self.buffer) >= 4:
            length = struct.unpack("!I", self.buffer[:4])[0]
            if length > MAX_MESSAGE_LEN:
                raise ProtocolError("message too long (%d) from %s" % (length, self.ip))
            if len(self.buffer) < 4 + length:
                break
            if length == 0:  # keep-alive
                del self.buffer[:4]
                continue
            msg_id = self.buffer[4]
            payload = bytes(self.buffer[5:4 + length])
            del self.buffer[:4 + length]
            messages.append((msg_id, payload))
        return messages

    def has_piece(self, index):
        try:
            return self.bitfield[index]
        except IndexError:
            return False

    def set_bitfield(self, payload):
        self.bitfield = Bitfield.from_bytes(payload)

    def set_have(self, index):
        try:
            self.bitfield[index] = True
        except IndexError:
            pass

    # ---- builders -----------------------------------------------------------

    def build_handshake(self):
        hs = struct.pack("B" + str(len(PSTR)) + "s8x20s20s",
                         len(PSTR), PSTR, self.torrent.info_hash, self.torrent.peer_id)
        assert len(hs) == HANDSHAKE_LEN
        return hs

    def build_interested(self):
        return struct.pack('!IB', 1, INTERESTED)

    def build_request(self, index, offset, length):
        return struct.pack('!IBIII', 13, REQUEST, index, offset, length)
