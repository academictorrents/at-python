from bittorrent.torrent import Torrent
from bittorrent.p2p.server import Server
from bittorrent.storage import DiskStorage
from bittorrent.utils import peer_id
from tornado.ioloop import IOLoop

import urllib
import os


class __AcademicTorrents:

    AT_TORRENT_FILE_DOWNLOAD_PATH = 'http://academictorrents.com/download/'

    def __init__(self):
        self.__data_store = './torrents_data'

    def get(self, info_hash, datastore=None):
        torrent_dir = self.__create_torrent_directory(info_hash, datastore)
        torrent_file_path = self.__download_dot_torrent_file(info_hash, torrent_dir)

        self.__download_torrent(torrent_file_path, torrent_dir)

        return info_hash

    def set_datastore(self, datastore):
        self.__data_store = datastore

        return self.__data_store

    def get_datastore(self):

        return self.__data_store

    def __create_torrent_directory(self, info_hash, datastore=None):
        if datastore is None:
            datastore = self.__data_store

        dir_name = os.path.join(datastore, info_hash)

        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        return dir_name

    def __download_dot_torrent_file(self, infohash, torrent_dir):
        constructed_dot_torrent_url = self.AT_TORRENT_FILE_DOWNLOAD_PATH + infohash
        dot_torrent_file_path = os.path.join(torrent_dir, infohash + '.torrent')

        result = urllib.urlretrieve(constructed_dot_torrent_url, dot_torrent_file_path)

        return result[0]

    def __download_torrent(self, torrent_file_path, torrent_dir):
        server = Server(
            torrent=Torrent(torrent_file_path),
            download_path=torrent_dir,
            storage_class=DiskStorage,
            peer_id=peer_id(),
            max_peers=20
        )

        server.listen(55309)
        server.start()

        IOLoop.instance().start()

academictorrents = __AcademicTorrents()
