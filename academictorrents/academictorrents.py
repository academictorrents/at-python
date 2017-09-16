from bittorrent.torrent import Torrent
from bittorrent.p2p.server import Server
from bittorrent.storage import DiskStorage
from bittorrent.utils import peer_id
from tornado.ioloop import IOLoop
import urllib
import os


def get(infohash, dest=None):
    torrent_dir = create_torrent_directory(infohash, dest)
    torrent_file_path = os.path.join(torrent_dir, infohash + '.torrent')
    download_torrent_file(infohash, torrent_file_path)
    download_torrent(torrent_file_path, torrent_dir)

    return infohash


def create_torrent_directory(dirname, dest=None):
    if dest is None:
        dest = os.getcwd()

    dirname = os.path.join(dest, dirname)

    if not os.path.exists(dirname):
        os.makedirs(dirname)

    return dirname


def download_torrent_file(infohash, dest):
    urllib.urlretrieve('http://academictorrents.com/download/' + infohash, dest)


def download_torrent(torrent_file_path, torrent_dir):
    server = Server(
        torrent=Torrent(torrent_file_path),
        download_path=torrent_dir,
        storage_class=DiskStorage,
        peer_id=peer_id(),
        max_peers=20
    )

    server.listen(55308)
    server.start()

    IOLoop.instance().start()
