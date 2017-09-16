import urllib
import struct

from bittorrent import bencode, utils
from bittorrent.peer import Peer
from bittorrent.tracker import TrackerResponse, TrackerFailure

from tornado.gen import coroutine, Return
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat

class HTTPTracker(object):
    def __init__(self, url, torrent, tier=0):
        self.url = url
        self.tier = tier
        self.torrent = torrent

        self.client = AsyncHTTPClient()

    @coroutine
    def announce(self, peer_id, port, event=None, num_wanted=None, compact=True, no_peer_id=None):
        params = {
            'info_hash': self.torrent.info_hash(),
            'peer_id': peer_id,
            'port': port,
            'uploaded': self.torrent.uploaded,
            'downloaded': self.torrent.downloaded,
            'left': self.torrent.remaining,
            'compact': int(compact)
        }

        if num_wanted is not None:
            params['numwant'] = num_wanted

        if compact is not None:
            params['compact'] = int(bool(compact))

        if no_peer_id is not None:
            params['no_peer_id'] = int(bool(no_peer_id))

        if event is not None:
            params['event'] = event

        tracker_url = url_concat(self.url, params)

        response = yield self.client.fetch(tracker_url)
        decoded_body = bencode.decode(response.body)

        if 'failure reason' in decoded_body:
            raise TrackerFailure(decoded_body['failure reason'])

        peers = list(self.get_peers(decoded_body))
        result = TrackerResponse(peers, decoded_body['interval'])

        raise Return(result)

    def get_peers(self, data):
        peers = data['peers']

        if isinstance(peers, list):
            for peer_dict in peers:
                yield Peer(peer_dict['ip'], peer_dict['port'], peer_dict['peer_id'])
        else:
            for chunk in utils.grouper(6, peers):
                yield Peer(*utils.unpack_peer_address(''.join(chunk)))
