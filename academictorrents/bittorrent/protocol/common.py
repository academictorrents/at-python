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
