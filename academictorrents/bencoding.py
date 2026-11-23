"""Minimal bencode that keeps strings as bytes.

Used where exact bytes matter: DHT/extension messages (binary ids) and
locating the raw ``info`` dict so its hash matches the torrent exactly.
"""


class BencodeError(ValueError):
    pass


def _decode(data, i):
    if i >= len(data):
        raise BencodeError("truncated")
    c = data[i:i + 1]
    if c == b'i':
        end = data.index(b'e', i)
        return int(data[i + 1:end]), end + 1
    if c == b'l':
        i += 1
        out = []
        while data[i:i + 1] != b'e':
            v, i = _decode(data, i)
            out.append(v)
        return out, i + 1
    if c == b'd':
        i += 1
        out = {}
        while data[i:i + 1] != b'e':
            k, i = _decode(data, i)
            v, i = _decode(data, i)
            out[k] = v
        return out, i + 1
    if c.isdigit():
        colon = data.index(b':', i)
        n = int(data[i:colon])
        start = colon + 1
        if start + n > len(data):
            raise BencodeError("truncated string")
        return bytes(data[start:start + n]), start + n
    raise BencodeError("bad token at %d" % i)


def decode(data, prefix=False):
    """Decode bytes. With prefix=True, return (value, end) and allow trailing data."""
    try:
        value, end = _decode(data, 0)
    except (ValueError, IndexError) as e:
        raise BencodeError(str(e))
    if prefix:
        return value, end
    if end != len(data):
        raise BencodeError("trailing data")
    return value


def encode(obj):
    if isinstance(obj, bool):
        obj = int(obj)
    if isinstance(obj, int):
        return b'i%de' % obj
    if isinstance(obj, str):
        obj = obj.encode('utf-8')
    if isinstance(obj, (bytes, bytearray)):
        return b'%d:%s' % (len(obj), bytes(obj))
    if isinstance(obj, (list, tuple)):
        return b'l' + b''.join(encode(v) for v in obj) + b'e'
    if isinstance(obj, dict):
        items = sorted((k.encode('utf-8') if isinstance(k, str) else k, v) for k, v in obj.items())
        return b'd' + b''.join(encode(k) + encode(v) for k, v in items) + b'e'
    raise TypeError("cannot bencode %r" % type(obj))


def info_bytes(torrent_data):
    """Return the raw bytes of the top-level ``info`` dict of a .torrent."""
    data = bytes(torrent_data)
    if data[:1] != b'd':
        raise BencodeError("not a torrent")
    i = 1
    while data[i:i + 1] != b'e':
        key, i = _decode(data, i)
        _, end = _decode(data, i)
        if key == b'info':
            return data[i:end]
        i = end
    raise BencodeError("no info dict")
