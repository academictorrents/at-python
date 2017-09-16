import inspect

from bittorrent.protocol.common import Message
from bittorrent import utils
from struct import Struct

class Message(object):
    id = None
    header_struct = Struct('!IB')
    body_struct = None

    def header(self, body):
        return self.header_struct.pack(len(body) + 1, self.id)

    def pack_body(self):
        raise NotImplementedError()

    @classmethod
    def unpack_body(cls, data):
        return cls.body_struct.unpack(data)

    def pack(self, with_header=True):
        body = self.pack_body()

        if not with_header:
            return body
        else:
            return self.header(body) + body

    @classmethod
    def unpack(cls, data, with_header=False):
        if with_header:
            header, body = data[:cls.header_struct.size], data[cls.header_struct.size:]
            length, id = cls.header_struct.unpack(header)

            assert len(body) == length - 1
            assert id == cls.id

            data = body

        return cls(*cls.unpack_body(data))

class BodylessMessage(Message):
    def pack_body(self):
        return ''

    @classmethod
    def unpack_body(cls, data):
        assert data == ''

        return ()

class KeepAlive(BodylessMessage):
    def header(self, body):
        return '\x00\x00\x00\x00'

    @classmethod
    def unpack(cls, data, with_header=False):
        if with_header:
            assert data == '\x00\x00\x00\x00'
        else:
            assert data == ''

        return cls()

class Choke(BodylessMessage):
    id = 0

class Unchoke(BodylessMessage):
    id = 1

class Interested(BodylessMessage):
    id = 2

class NotInterested(BodylessMessage):
    id = 3

class Have(Message):
    id = 4
    body_struct = Struct('!I')

    def __init__(self, piece):
        self.piece = piece

    def pack_body(self):
        return self.body_struct.pack(self.piece)

class Bitfield(Message):
    id = 5

    def __init__(self, bitfield):
        self.bitfield = bitfield

    def pack_body(self):
        data = ''
        bits = ['0'] * (max(self.bitfield.keys()) + 1)

        for piece, state in self.bitfield.items():
            bits[piece] = '1' if state else '0'

        for chunk in utils.grouper(8, bits, fillvalue='0'):
            data += chr(int(''.join(chunk), 2))

        return data

    @classmethod
    def unpack_body(cls, data):
        d = {}
        index = 0

        for char in data:
            for bit in bin(ord(char))[2:]:
                d[index] = bool(int(bit))
                index += 1

        return (d,)

    def __nonzero__(self):
        return any(self.bitfield.values())

class Request(Message):
    id = 6
    body_struct = Struct('!III')

    def __init__(self, index, begin, length):
        self.index = index
        self.begin = begin
        self.length = length

    def pack_body(self):
        return self.body_struct.pack(self.index, self.begin, self.length)

class Piece(Message):
    id = 7
    body_struct = Struct('!II')

    def __init__(self, index, begin, block):
        self.index = index
        self.begin = begin
        self.block = block

    def pack_body(self):
        return self.body_struct.pack(self.index, self.begin) + self.block

    @classmethod
    def unpack_body(cls, data):
        index, begin = cls.body_struct.unpack(data[:cls.body_struct.size])

        return index, begin, data[cls.body_struct.size:]

class Cancel(Message):
    id = 8
    structure = '!III'

    def __init__(self, index, begin, length):
        self.index = index
        self.begin = begin
        self.length = length

    def pack_body(self):
        return self.body_struct.pack(self.index, self.begin, self.length)

class Port(Message):
    id = 9
    structure = '!I'

    def __init__(self, port):
        self.port = port

    def pack_body(self):
        return self.body_struct.pack(self.port)

Messages = {cls.id: cls for name, cls in locals().items() if inspect.isclass(cls) and issubclass(cls, Message)}
