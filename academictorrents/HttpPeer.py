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
        try:
            self.handshake(url)
        except Exception:
            return False

    def handshake(self, url):
        if not url:
            raise Exception
        resp = requests.head(url)
        if resp.headers.get('Accept-Ranges', False):  # if it was a full-url
            self.url = '/'.join(url.split('/')[0:-1]) + '/'
            return
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
                return
        raise Exception  # if we don't hit either of the above returns, we should raise an exception.

    def request_ranges(self, filename, pieces):
        start = pieces[0].get_file_offset(filename)
        end = start
        for piece in pieces:
            end += piece.get_length(filename)
        try:
            return self.sess.get(self.url + filename, headers={'Range': 'bytes=' + str(start) + '-' + str(end)}, verify=False)
        except Exception as e:
            return False

    def publish_responses(self, response, filename, pieces):
        response_offset = 0
        for piece in pieces:
            data_length = piece.get_length(filename)
            data = response.content[response_offset: response_offset + data_length]
            response_offset += data_length
            offset = int(piece.get_offset(filename))
            import pdb; pdb.set_trace()
            for idx in range(int(math.ceil(data_length/piece.BLOCK_SIZE))):
                size = piece.blocks[idx].size
                start = idx * piece.BLOCK_SIZE
                pub.sendMessage('PiecesManager.receive_block_piece', piece=(piece.index, offset, data[start: start + size]))
                offset += size
