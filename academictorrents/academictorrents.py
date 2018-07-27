import time
import logging
import json
import io
import os
import bencode
import requests
from . import utils
import pkg_resources
from .Client import Client
from .Torrent import Torrent
from .PiecesManager import PiecesManager


def get(hash, datastore=None, name=None):
    torrent_dir = utils.get_torrent_dir(datastore=datastore, name=name)
    torrent = Torrent(hash, torrent_dir)

    timestamp = utils.read_timestamp(hash)
    if utils.timestamp_is_within_30_days(timestamp) and utils.filenames_present(torrent, datastore):
        return torrent_dir + torrent.torrentFile['info']['name']

    piecesManager = PiecesManager(torrent)
    piecesManager.check_disk_pieces()
    new_size = piecesManager.check_percent_finished()
    if float(new_size) / torrent.totalLength == 1.0:
        return torrent_dir + torrent.torrentFile['info']['name']

    return Client(hash, torrent_dir, piecesManager).start(new_size)
