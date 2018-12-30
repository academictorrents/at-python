import logging
from queue import Queue
from .PiecesManager import PiecesManager
from .Torrent import Torrent
from .Client import Client
from .utils import get_torrent_dir, read_timestamp, timestamp_is_within_30_days, filenames_present, write_timestamp

def get(path, datastore=None, name=None, showlogs=False):
    logging.getLogger().setLevel(logging.CRITICAL)
    if showlogs:
        logging.getLogger().setLevel(level=logging.INFO)


    if "/" not in path:
        torrent_dir = get_torrent_dir(datastore=datastore, name=name)
        torrent = Torrent(path, torrent_dir)

        name = torrent.torrentFile['info']['name']
        if "length" in torrent.torrentFile['info']:
            size_mb = torrent.torrentFile['info']['length']/1000./1000.
        else:
            total_length = 0
            for f in torrent.torrentFile['info']['files']:
                total_length += f['length']
            size_mb = total_length/1000./1000.

        print("Torrent name: " + name + ", Size: {0:.2f}MB".format(size_mb))

        timestamp = read_timestamp(path)
        if timestamp_is_within_30_days(timestamp) and filenames_present(torrent, datastore):
            return torrent_dir + torrent.torrentFile['info']['name']

        piecesManager = PiecesManager(torrent)
        piecesManager.check_disk_pieces()
        start_downloaded = piecesManager.check_percent_finished()

        if float(start_downloaded) / torrent.totalLength == 1.0:
            return torrent_dir + torrent.torrentFile['info']['name']

        client = Client(torrent, start_downloaded, piecesManager)
        downloaded_path = client.start()
        write_timestamp(path)

        return torrent_dir + downloaded_path
    else:
        return path
