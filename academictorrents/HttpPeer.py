import requests
import math
from pubsub import pub
from threading import Thread
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class HttpPeer(object):
    def __init__(self, torrent, url):
        self.torrent = torrent
        self.url = url
        self.sess = requests.Session()
        self.accepts_ranges = self.handshake(url)
        self.fail_files = []

    def handshake(self, url):
        if not url:
            return False
        resp = requests.head(url)
        if resp.headers.get('Accept-Ranges', False):  # if it was a full-url
            self.url = '/'.join(url.split('/')[0:-1]) + '/'
            return True
        else:  # maybe we need to construct a full-url
            directory = self.torrent.torrent_file.get('info', {}).get('name')
            some_filename = self.torrent.torrent_file.get('info', {}).get('files', [{'path': ['']}])[0].get('path')[0]
            if url[-1] == '/':
                compound_url = url + directory + '/'
            else:
                compound_url = url + '/' + directory + '/'
            resp = requests.head(compound_url + some_filename)
            if resp.headers.get('Accept-Ranges', False):  # if it wasn't a full-url
                self.url = compound_url
                return True
        return False

    def request_ranges(self, filename, pieces):
        start = pieces[0].get_file_offset(filename)
        end = start
        for piece in pieces:
            end += piece.get_length(filename)
        try:
            return self.sess.get(self.url + filename, headers={'Range': 'bytes=' + str(start) + '-' + str(end)}, verify=False, timeout=3)
        except Exception as e:
            print(e)
            return False

    def publish_responses(self, response, filename, pieces):
        offset = 0
        for piece in pieces:
            size = piece.get_length(filename)
            pub.sendMessage('PieceManager.receive_file', piece=(piece.index, filename, response.content[offset: offset + size]))
            offset += size
