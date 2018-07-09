__author__ = 'alexisgallepe'

import time
import bencode
import logging
import os
from . import utils
try:
    from urllib.parse import urlparse, urlencode
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urlparse import urlparse
    from urllib import urlencode
    from urllib2 import urlopen, Request, HTTPError


class Torrent(object):
    def __init__(self, hash, torrent_dir):
        self.hash = hash
        self.torrent_dir = torrent_dir
        if not self.get_from_url() and not self.get_from_file():
            raise Exception("Could not find a torrent with this hash on the tracker or in the torrent directory:" + str(self.torrent_dir))

        with open(torrent_dir + hash + '.torrent', 'rb') as file:
            contents = file.read()

        self.torrentFile = bencode.decode(contents)
        self.totalLength = 0
        self.pieceLength = self.torrentFile['info']['piece length']
        self.pieces = self.torrentFile['info']['pieces']

        self.info_hash = utils.sha1_hash(bencode.encode(self.torrentFile['info']))
        self.peer_id = self.generate_peer_id()
        self.announceList = self.getTrakers()
        self.fileNames = []

        self.get_files()
        if self.totalLength % self.pieceLength == 0:
            self.numberOfPieces = self.totalLength / self.pieceLength
        else:
            self.numberOfPieces = int(self.totalLength / self.pieceLength) + 1

        logging.debug(self.announceList)
        logging.debug(self.fileNames)

        assert(self.totalLength > 0)
        assert(len(self.fileNames) > 0)

    def get_from_file(self):
        try:
            torrent_path = os.path.join(self.torrent_dir, self.hash + '.torrent')
            return bencode.decode(open(torrent_path, 'rb').read())
        except Exception:
            return False

    def get_from_url(self):
        contents = None
        try:
            url = "http://academictorrents.com/download/" + self.hash
            torrent_path = os.path.join(self.torrent_dir, self.hash + '.torrent')
            if not os.path.isdir(self.torrent_dir):
                os.makedirs(self.torrent_dir)
            response = urlopen(url).read()
            open(torrent_path, 'wb').write(response)
            contents = bencode.decode(open(torrent_path, 'rb').read())
        except Exception as e:
            print("could not download the torrent")
        return contents

    def get_files(self):
        root = self.torrent_dir + self.torrentFile['info']['name']  # + "/"
        if 'files' in self.torrentFile['info']:
            if not os.path.exists(root):
                os.mkdir(root, 0o766)

            for f in self.torrentFile['info']['files']:
                pathFile = os.path.join(root, *f["path"])

                if not os.path.exists(os.path.dirname(pathFile)):
                    os.makedirs(os.path.dirname(pathFile))

                self.fileNames.append({"path": pathFile, "length": f["length"]})
                self.totalLength += f["length"]

        else:
            self.fileNames.append({"path": root, "length": self.torrentFile['info']['length']})
            self.totalLength = self.torrentFile['info']['length']

    def getTrakers(self):
        if 'announce-list' in self.torrentFile:
            return self.torrentFile['announce-list']
        else:
            return [[self.torrentFile['announce']]]

    def generate_peer_id(self):
        seed = str(time.time())
        return utils.sha1_hash(seed.encode())
