import requests
from pubsub import pub


class HttpPeer(object):
    def __init__(self, torrent, url):
        self.readBuffer = b""
        self.torrent = torrent
        self.url = url
        resp = requests.head(url, allow_redirects=True)
        self.etag = resp.headers.get('etag', None)
        self.hasHandshaked = True if resp.headers.get('Accept-Ranges', False) and resp.headers.get('ETag', False) else False

    def make_request(self, piece_index, fileOffset, pieceOffset, blockOffset, length):
        offset = fileOffset + pieceOffset + blockOffset
        resp = requests.get(self.url, allow_redirects=True, headers={'If-Range': self.etag, 'Range': 'bytes='+ str(offset) + '-' + str(offset + length-1)})
        if resp.status_code == 206:
            pub.sendMessage('PiecesManager.Piece', piece=(piece_index, blockOffset, resp.content))
        self.choke()

    def choke(self):
        pub.sendMessage('PeersManager.chokePeer', peer=self)
