import hashlib

from . import bencode
from .tracker import Tracker
from .utils import grouper

class Torrent(object):
    def __init__(self, handle=None):
        if isinstance(handle, dict):
            self.meta = handle
        elif isinstance(handle, basestring):
            try:
                self.meta = bencode.decode(handle)
            except ValueError:
                try:
                    with open(handle, 'rb') as input_file:
                        self.meta = bencode.decode(input_file.read())
                except IOError:
                    raise TypeError('handle must be a file, dict, path, or bencoded string. Got: {0}'.format(type(handle)))
        elif hasattr(handle, 'read'):
            self.meta = bencode.decode(handle.read())
        else:
            self.meta = {}

        self.uploaded = 1000000
        self.downloaded = 0
        self.remaining = self.calc_size()

        self.trackers = self._trackers()

    def bencode(self):
        return bencode.encode(self.meta)

    def save(self, filename):
        with open(filename, 'wb') as handle:
            handle.write(self.bencode())

    def info_hash(self, hex=False):
        hash = hashlib.sha1(bencode.encode(self.meta['info']))

        if hex:
            return hash.hexdigest()
        else:
            return hash.digest()

    def _trackers(self):
        trackers = self.meta.get('announce-list', [[self.meta['announce']]])
        result = []

        for tier, urls in enumerate(trackers):
            for url in urls:
                if url:
                    tracker = Tracker(url, torrent=self, tier=tier)
                    result.append(tracker)

        return result

    def calc_size(self):
        size = 0
        if 'length' in self.meta['info']:
            size = self.meta['info']['length']
        else:
            for info in self.meta['info']['files']:
                size += info['length']

        return size

    @property
    def tracker(self):
        return self.trackers[0]

    @property
    def piece_hashes(self):
        hashes = grouper(20, self.meta['info']['pieces'])

        for index, hash in enumerate(hashes):
            yield ''.join(hash)
