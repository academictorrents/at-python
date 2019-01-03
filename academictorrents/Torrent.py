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
    def __init__(self, hash, data_dir):
        self.hash = hash
        self.data_dir = data_dir
        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir)

        if not self.get_from_url() and not self.get_from_file():
            raise Exception("Could not find a torrent with this hash on the tracker or in the data directory:" + str(self.data_dir))

        with open("/tmp/" + hash + '.torrent', 'rb') as file:
            contents = file.read()
        self.torrent_file = bencode.decode(contents)
        self.total_length = 0
        self.piece_length = self.torrent_file['info']['piece length']
        self.pieces = self.torrent_file['info']['pieces']

        self.info_hash = utils.sha1_hash(bencode.encode(self.torrent_file['info']))
        self.peer_id = self.generate_peer_id()
        self.announceList = self.getTrakers()
        self.filenames = []

        self.get_files()
        if self.total_length % self.piece_length == 0:
            self.number_of_pieces = self.total_length / self.piece_length
        else:
            self.number_of_pieces = int(self.total_length / self.piece_length) + 1

        logging.debug(self.announceList)
        logging.debug(self.filenames)

        assert(self.total_length > 0)
        assert(len(self.filenames) > 0)

    def get_from_file(self):
        try:
            torrent_path = os.path.join("/tmp/", self.hash + '.torrent')
            return bencode.decode(open(torrent_path, 'rb').read())
        except Exception:
            return False

    def get_from_url(self):
        contents = None
        try:
            url = "http://academictorrents.com/download/" + self.hash
            torrent_path = os.path.join("/tmp/", self.hash + '.torrent')
            response = urlopen(url).read()
            open(torrent_path, 'wb').write(response)
            contents = bencode.decode(open(torrent_path, 'rb').read())
        except Exception as e:
            print("could not download the torrent")
        return contents

    def get_files(self):
        root = self.data_dir + self.torrent_file['info']['name']  # + "/"
        if 'files' in self.torrent_file['info']:
            if not os.path.exists(root):
                os.mkdir(root, 0o766)

            for f in self.torrent_file['info']['files']:
                pathFile = os.path.join(root, *f["path"])

                if not os.path.exists(os.path.dirname(pathFile)):
                    os.makedirs(os.path.dirname(pathFile))

                self.filenames.append({"path": pathFile, "length": f["length"]})
                self.total_length += f["length"]

        else:
            self.filenames.append({"path": root, "length": self.torrent_file['info']['length']})
            self.total_length = self.torrent_file['info']['length']

    def getTrakers(self):
        if 'announce-list' in self.torrent_file:
            return self.torrent_file['announce-list']
        else:
            return [[self.torrent_file['announce']]]

    def generate_peer_id(self):
        seed = str(time.time())
        return utils.sha1_hash(seed.encode())
