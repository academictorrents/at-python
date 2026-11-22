"""Per-piece download state.

A piece only holds memory while it is in flight: ``buf`` and the received
ranges are allocated on the first write and dropped once the piece is written
to disk or reset. Finished pieces are tracked by PieceManager's bitfield.
"""
BLOCK_SIZE = 2 ** 14


class Piece(object):
    __slots__ = ("index", "size", "data_hash", "files", "buf", "ranges",
                 "block_pending", "file_pending", "verifying")

    def __init__(self, index, size, data_hash):
        self.index = index
        self.size = size
        self.data_hash = data_hash
        self.files = []  # segments: dicts with relpath, path, file_offset, piece_offset, length
        self.reset()

    @property
    def num_blocks(self):
        return -(-self.size // BLOCK_SIZE)

    def block_length(self, block):
        return min(BLOCK_SIZE, self.size - block * BLOCK_SIZE)

    def reset(self):
        # Containers are created on demand so idle pieces stay small.
        self.buf = None
        self.ranges = ()  # sorted, merged [start, end) byte ranges received
        self.block_pending = None  # block index -> time requested
        self.file_pending = None  # relpath -> time requested
        self.verifying = False

    def get_segment(self, relpath):
        for f in self.files:
            if f["relpath"] == relpath:
                return f
        return None

    def covered(self, start, end):
        for a, b in self.ranges:
            if a <= start and end <= b:
                return True
            if a > start:
                return False
        return False

    def is_full(self):
        return len(self.ranges) == 1 and self.ranges[0] == (0, self.size)

    def write(self, offset, data):
        """Store data at offset. Returns True if the piece is now full."""
        end = offset + len(data)
        if offset < 0 or end > self.size or not data:
            return False
        if self.buf is None:
            self.buf = bytearray(self.size)
        self.buf[offset:end] = data
        merged = []
        start = offset
        for a, b in self.ranges:
            if b < start or a > end:
                merged.append((a, b))
            else:
                start, end = min(a, start), max(b, end)
        merged.append((start, end))
        merged.sort()
        self.ranges = merged
        return self.is_full()

    def set_block_pending(self, block, now):
        if self.block_pending is None:
            self.block_pending = {}
        self.block_pending[block] = now

    def set_file_pending(self, relpath, now):
        if self.file_pending is None:
            self.file_pending = {}
        self.file_pending[relpath] = now

    def clear_file_pending(self, relpath):
        if self.file_pending:
            self.file_pending.pop(relpath, None)

    def missing_blocks(self, now, timeout):
        """Blocks not received and not requested in the last `timeout` seconds."""
        out = []
        for i in range(self.num_blocks):
            start = i * BLOCK_SIZE
            if self.covered(start, start + self.block_length(i)):
                continue
            t = self.block_pending.get(i) if self.block_pending else None
            if t is not None and now - t < timeout:
                continue
            out.append(i)
        return out

    def segment_needed(self, seg, now, timeout):
        if self.covered(seg["piece_offset"], seg["piece_offset"] + seg["length"]):
            return False
        t = self.file_pending.get(seg["relpath"]) if self.file_pending else None
        return t is None or now - t >= timeout
