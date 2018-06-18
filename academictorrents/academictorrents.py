import time
import logging
from pytorrent import Client
import logging
import json
import io
import os
import bencode
import requests
try:
    from urllib.parse import urlparse, urlencode
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urlparse import urlparse
    from urllib import urlencode
    from urllib2 import urlopen, Request, HTTPError



at_client = None
def get_client():
    global at_client
    if at_client is None:
        at_client = ATClient()
    return at_client

def get(hash, datastore=None):
    if not datastore:
        datastore = os.getcwd() + "/datastore/"
    url = "http://academictorrents.com/download/" + hash

    torrent_dir = datastore + hash + '/'
    torrent_path = os.path.join(torrent_dir, hash + '.torrent')
    if not os.path.isdir(torrent_dir):
        os.makedirs(torrent_dir)
    response = urlopen(url).read()
    open(torrent_path, 'wb').write(response)
    contents = bencode.decode(open(torrent_path, 'rb').read())
    Client.Client(torrent_path, torrent_dir).start()
    return torrent_dir + contents['info']['name']
