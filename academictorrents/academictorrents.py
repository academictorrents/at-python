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


# delete one file, check if it downloads that one file

#def get(): # instantiate the client object

# make the torrent client its own module

# Iterate over urls to try randomly and download

# hit some endpoint on the academic torrent server with the size of the file and if it was from HTTP or peers. Maybe average speed todo

# Be able to pass in a url that lets you download on HTTP a torrent file
# Or, a path to a torrent file

# put this in the github: $ pip install --index-url https://test.pypi.org/simple/ your-package

# Python 3 compatibility

# graph conv presentation --> needs prior information, where does this prior come from?

at_client = None
def get_client():
    global at_client
    if at_client is None:
        at_client = ATClient()
    return at_client

def get(hash):
    return get_client().get_dataset(hash)

class ATClient(object):
    def __init__(self):
        self.datastore = os.getcwd() + "/datastore/"

    def set_datastore(self, path):
        self.datastore = path

    def get_torrent_dir(self, hash):
        return self.datastore + hash + '/'

    def get_dataset(self, name):
        url = "http://academictorrents.com/download/" + name
        torrent_path = os.path.join(self.get_torrent_dir(name), name + '.torrent')
        if not os.path.isdir(self.get_torrent_dir(name)):
            os.makedirs(self.get_torrent_dir(name))

        response = urlopen(url).read()
        open(torrent_path, 'wb').write(response)
        contents = bencode.decode(open(torrent_path, 'rb').read())

        if not os.path.isfile(self.get_torrent_dir(name) + contents['info']['name']):
            Client.Client(torrent_path, self.get_torrent_dir(name)).start()
        return self.get_torrent_dir(name) + contents['info']['name']
