import logging
from queue import Queue
from .PieceManager import PieceManager
from .Torrent import Torrent
from .Client import Client
from .utils import datastore_path, read_timestamp, timestamp_is_within_30_days, filenames_present, write_timestamp

def get(at_hash, datastore=None, urls=[], showlogs=False):
    logging.getLogger().setLevel(logging.CRITICAL)
    if showlogs:
        logging.getLogger().setLevel(level=logging.INFO)

    datastore = datastore_path(datastore=datastore)
    torrent = Torrent(at_hash, datastore)

    name = torrent.torrent_file['info']['name']
    if "length" in torrent.torrent_file['info']:
        size_mb = torrent.torrent_file['info']['length']/1000./1000.
    else:
        total_length = 0
        for f in torrent.torrent_file['info']['files']:
            total_length += f['length']
        size_mb = total_length/1000./1000.

    print("Torrent name: " + name + ", Size: {0:.2f}MB".format(size_mb))

    timestamp = read_timestamp(at_hash)
    if timestamp_is_within_30_days(timestamp) and filenames_present(torrent, datastore):
        return datastore + torrent.torrent_file['info']['name']

    piece_manager = PieceManager(torrent)
    piece_manager.check_disk_pieces()
    downloaded_amount = piece_manager.check_finished_pieces()

    if float(downloaded_amount) / torrent.total_length == 1.0:
        return datastore + torrent.torrent_file['info']['name']

    client = Client(torrent, downloaded_amount, piece_manager)
    downloaded_path = client.start()
    write_timestamp(at_hash)

    return datastore + downloaded_path
