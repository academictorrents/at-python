import time
from queue import Queue
from . import progress_bar
from .PeerSeeker import PeerSeeker
from .PeersManager import PeersManager
from .Tracker import Tracker
from .WebSeedManager import WebSeedManager
from .HttpPeer import HttpPeer


class Client(object):
    @classmethod
    def __init__(self, torrent, start_downloaded, piecesManager):
        self.torrent = torrent
        self.start_downloaded = start_downloaded
        self.start_time = time.time()
        self.requestQueue = Queue(maxsize=10)
        self.newpeersQueue = Queue()

        self.piecesManager = piecesManager
        self.peerSeeker = PeerSeeker(self.newpeersQueue, torrent)
        self.peersManager = PeersManager(self.torrent, self.piecesManager)
        self.tracker = Tracker(torrent, self.newpeersQueue, start_downloaded)
        self.webSeedManagers = []

        self.tracker.start()
        self.peersManager.start()
        self.peerSeeker.start()
        self.piecesManager.start()

        self.httpPeers = []
        for url in self.torrent.torrentFile.get('url-list'):
            peer = HttpPeer(self.torrent, url)
            if not peer:
                continue
            self.httpPeers.append(peer)

        for i in range(len(self.httpPeers)):
            t = WebSeedManager(torrent, self.requestQueue, self.httpPeers)
            t.start()
            self.webSeedManagers.append(t)

    def start(self):
        while True:
            unfinished_pieces = list(filter(lambda x: x.finished is False, self.piecesManager.pieces))
            if not unfinished_pieces:
                break

            self.piecesManager.reset_all_pending_blocks(unfinished_pieces)
            self.peersManager.make_requests(unfinished_pieces)

            # Make WebSeed requests
            if 2 * len(self.httpPeers) > self.requestQueue.qsize():
                for httpPeer in self.httpPeers:
                    pieces = httpPeer.get_pieces(self.piecesManager)
                    if pieces:
                        pieces_by_file = httpPeer.construct_pieces_by_file(pieces)
                        self.requestQueue.put((httpPeer, pieces_by_file))

            # Record progress
            cur_downloaded = self.piecesManager.check_percent_finished()
            rate = (cur_downloaded - self.start_downloaded)/(time.time()-self.start_time)/1000. # rate in KBps
            progress_bar.print_progress(cur_downloaded, self.torrent.totalLength, "BT:{}, Web:{}".format(len(self.peersManager.peers),len(self.peersManager.httpPeers)), "({0:.2f}kB/s)".format(rate))
            self.tracker.set_downloaded(cur_downloaded)
            time.sleep(0.1)

        print("\nDownload Complete! " + str(time.time()))
        self.tracker.requestStop()
        self.peerSeeker.requestStop()
        self.peersManager.requestStop()
        self.piecesManager.requestStop()
        for webSeedManager in self.webSeedManagers:
            webSeedManager.requestStop()

        return self.torrent.torrentFile['info']['name']
