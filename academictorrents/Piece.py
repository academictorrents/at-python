import math
import time
from . import utils
import itertools
from collections import defaultdict, OrderedDict
from pubsub import pub
from . import Block
BLOCK_SIZE = 2 ** 14


class Piece(object):
    def __init__(self, index, size, data_hash):
        self.index = index
        self.size = size
        self.data_hash = data_hash
        self.files_pending = {}
        self.files = []
        self.BLOCK_SIZE = BLOCK_SIZE
        self.blocks = []
        self.init_blocks()

    def init_blocks(self):
        num_full_blocks = int(math.floor(float(self.size) / self.BLOCK_SIZE))
        self.blocks = []
        for _ in range(num_full_blocks):
            self.blocks.append(Block.Block(size=self.BLOCK_SIZE))
        if (self.size % BLOCK_SIZE) > 0:
            self.blocks.append(Block.Block(size=self.size % BLOCK_SIZE))

    def get_block_statuses(self):
        return [block.status for block in self.blocks]

    def set_block(self, offset, data):
        index = int(offset / BLOCK_SIZE)
        offset = offset % self.BLOCK_SIZE
        self.blocks[index].data[offset] = bytearray(data)
        # print(self.get_block_statuses())
        if len(data) == self.blocks[index].size:
            self.blocks[index].status = "Full"
        else:
            print("len(data):" + str(len(data)))
            print("index:" + str(index))
            print("self.files:" + str(self.files))
            import pdb; pdb.set_trace()
            self.blocks[index].status = "Partial"
            data = bytearray(b"")
            for b in OrderedDict(sorted(self.blocks[index].data.items())).values():
                data.extend(b)
            if len(data) == self.blocks[index].size:
                self.blocks[index].data = {0: data}
        if all([block.status == "Full" for block in self.blocks]):
            # print("complete")
            self.complete()

    def set_all_blocks_pending(self):
        for block in self.blocks:
            block.set_pending()

    def reset_pending_blocks(self):
        for block in self.blocks:
            block.reset_pending()

    def set_file_pending(self, filename):
        self.files_pending[filename] = time.time()

    def remove_file_pending(self, filename):
        del self.files_pending[filename]

    def reset_pending_files(self):
        new_files_pending = {}
        for filename, timestamp in self.files_pending.items():
            if(int(time.time()) - timestamp) < 8:
                new_files_pending[filename] = timestamp
        self.files_pending = new_files_pending

    def complete(self):
        # If there is at least one block Free|Pending -> Piece not complete -> return false
        buf = bytearray(b"")
        for block in self.blocks:
            buf.extend(block.data[0])
        if self.isHashPieceCorrect(buf):
            self.writeFilesOnDisk(buf)
            pub.sendMessage('PieceManager.update_bit_field', index=self.index)


    def isHashPieceCorrect(self, data):
        if utils.sha1_hash(data) == self.data_hash:
            return True
        return False

    def isCompleteOnDisk(self):
        block_offset = 0
        data = b''
        for f in self.files:
            try:
                f_ptr = open(f["path"], 'rb')
            except IOError:
                break
            f_ptr.seek(f["file_offset"])
            data += f_ptr.read(f["length"])
            f_ptr.close()
            block_offset += f['length']

        if data and self.isHashPieceCorrect(data):
            data = bytearray(b'')
            for block in self.blocks:
                block.status = "Full"
            return True
        return False

    def writeFunction(self, pathFile, data, offset):
        try:
            f = open(pathFile, 'r+b')
        except IOError:
            f = open(pathFile, 'wb')
        f.seek(offset)
        f.write(data)
        f.close()

    def writeFilesOnDisk(self, data):
        for f in self.files:
            pathFile = f["path"]
            file_offset = f["file_offset"]
            piece_offset = f["piece_offset"]
            length = f["length"]
            self.writeFunction(pathFile, data[piece_offset: piece_offset + length], file_offset)
        for block in self.blocks:
            block.data = {0: bytearray(b'')}


    def get_file_offset(self, filename):
        for f in self.files:
            if f.get('path').split('/')[-1] == filename:
                return f.get('file_offset')

    def get_length(self, filename):
        for f in self.files:
            if f.get('path').split('/')[-1] == filename:
                return f.get('length')

    def get_offset(self, filename):
        for f in self.files:
            if f.get('path').split('/')[-1] == filename:
                return math.floor(f.get('piece_offset'))
