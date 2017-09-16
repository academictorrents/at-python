import os
import hashlib
import logging

from bittorrent.utils import ceil_div, create_and_open, mkdirs

class PiecedFile(object):
    def __init__(self, handle, size, offset=None):
        self.handle = handle
        self.size = size
        self.offset = offset

class DiskStorage(object):
    def __init__(self, files, block_size, block_hashes):
        self.files = []
        self.size = 0

        for file in files:
            file.offset = self.size

            self.size += file.size
            self.files.append(file)

        self.block_size = block_size
        self.num_blocks = ceil_div(self.size, block_size)
        self.last_block_size = self.size % self.block_size

        if self.last_block_size == 0:
            self.last_block_size = self.block_size

        self.block_hashes = block_hashes
        self.blocks = [None] * self.num_blocks

    @classmethod
    def from_torrent(cls, torrent, base_path=None):
        files = []
        hashes = list(torrent.piece_hashes)
        block_size = torrent.meta['info']['piece length']

        if 'length' in torrent.meta['info']:
            path = torrent.meta['info']['name']
            size = torrent.meta['info']['length']

            if base_path is not None:
                mkdirs(base_path)
                path = os.path.join(base_path, path)

            handle = create_and_open(path, 'r+b', size=size)

            files.append(PiecedFile(handle, size))
        else:
            for info in torrent.meta['info']['files']:
                folders = [torrent.meta['info']['name']] + info['path'][:-1]

                if base_path is not None:
                    folders = [base_path] + folders

                filename = info['path'][-1]
                directory = os.path.join(*folders)

                mkdirs(directory)

                size = info['length']
                handle = create_and_open(os.path.join(directory, filename), 'r+b', size=size)

                files.append(PiecedFile(handle, size))

        return cls(files, block_size, hashes)

    def get_file_by_offset(self, offset):
        total_offset = 0

        for file in self.files:
            if total_offset <= offset < total_offset + file.size:
                file.handle.seek(offset - total_offset)
                return file
            else:
                total_offset += file.size

        raise ValueError('Invalid offset')

    def read_piece(self, index, offset, length):
        if offset >= self.block_size:
            raise ValueError('Offset must be smaller than the block size')

        if offset + length > self.block_size:
            raise ValueError('Invalid piece length: pieces cannot span across blocks')

        if index == self.num_blocks - 1 and offset + length > self.last_block_size:
            raise ValueError('Cannot read past end of last block')

        data = ''
        position = self.block_size * index + offset

        while length != 0:
            file = self.get_file_by_offset(position)

            to_read = min(length, file.offset + file.size - position)
            data += file.handle.read(to_read)

            length -= to_read
            position += to_read

        return data

    def write_piece(self, index, offset, data):
        if offset >= self.block_size:
            raise ValueError('Offset must be smaller than the block size')

        if offset + len(data) > self.block_size:
            raise ValueError('Cannot write across blocks')

        if index == self.num_blocks - 1 and offset + len(data) > self.last_block_size:
            raise ValueError('Cannot write past end of last block')

        position = self.block_size * index + offset

        while len(data) != 0:
            file = self.get_file_by_offset(position)

            to_write = min(len(data), file.size - position + file.offset)
            file.handle.write(data[:to_write])
            data = data[to_write:]

            position += to_write

        self.verify_block(index, force=True)

    def read_block(self, index):
        if index == self.num_blocks - 1:
            return self.read_piece(index, 0, self.last_block_size)
        else:
            return self.read_piece(index, 0, self.block_size)

    def write_block(self, index, data):
        if len(data) != self.block_size or (index == self.num_blocks - 1 and len(data) != self.last_block_size):
            raise ValueError('Data must fill an entire block')

        self.write_piece(index, 0, data)
        self.verify_block(index, force=True)

    def verify_block(self, index, force=False):
        if not 0 <= index < self.num_blocks:
            raise ValueError('Invalid block index')

        if not force and self.blocks[index] is not None:
            return self.blocks[index]

        verified = hashlib.sha1(self.read_block(index)).digest() == self.block_hashes[index]
        self.blocks[index] = verified

        return verified

    def verify(self):
        for index in range(self.num_blocks):
            self.verify_block(index)

        return all(self.blocks)

    def to_bitfield(self):
        return {index: self.verify_block(index) for index in range(self.num_blocks)}

    def piece_chart(self):
        return ''.join(['*' if self.verify_block(index) else '.' for index in range(self.num_blocks)])

    def percentage(self):
        b = self.to_bitfield()

        return 100 * float(sum(b.values())) / float(len(b))

    def __str__(self):
        return '<{self.__class__.__name__} {chart} {percent}%>'.format(
            self=self,
            chart=self.piece_chart(),
            percent=self.percentage()
        )

    def __del__(self):
        for file in self.files:
            file.handle.close()
            del file

if __name__ == '__main__':
    from torrent import Torrent

    torrent = Torrent('ubuntu-13.04-desktop-amd64.iso.torrent')
    f = PiecedFileSystem.from_torrent(torrent)
