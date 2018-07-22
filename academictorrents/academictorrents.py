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


def get(hash, datastore=None, name=None):
    torrent_dir = utils.get_torrent_dir(datastore=datastore, name=name)
    torrent = Torrent(hash, torrent_dir)
    timestamp = utils.read_timestamp(hash)
    if utils.timestamp_is_recent(timestamp) and utils.filenames_present(torrent, datastore):
        return torrent_dir + torrent.torrentFile['info']['name']
    else:
        return Client(hash, torrent_dir).start()
