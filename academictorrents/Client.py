
__author__ = 'alexisgallepe'

import time
from threading import Thread
from queue import Queue
from . import HttpPeer
from . import progress_bar
from .PeerSeeker import PeerSeeker
from .PeersManager import PeersManager
from .Tracker import Tracker


class Client(object):
    @classmethod
    def __init__(self, torrent, start_downloaded, piecesManager):
        self.torrent = torrent
        self.start_downloaded = start_downloaded
        self.start_time = time.time()
        self.requestQueue = Queue(maxsize=10)

        newpeersQueue = Queue()

        self.piecesManager = piecesManager
        self.peerSeeker = PeerSeeker(newpeersQueue, torrent)
        self.peersManager = PeersManager(self.torrent, self.piecesManager)
        self.tracker = Tracker(torrent, newpeersQueue, start_downloaded)

        self.tracker.start()
        self.peersManager.start()
        self.peerSeeker.start()
        self.piecesManager.start()

        self.HttpThreads = []
        for url in self.torrent.torrentFile.get('url-list'):
            try:
                peer = HttpPeer.HttpPeer(self.torrent, url, self.requestQueue)
                self.peersManager.httpPeers.append(peer)
            except Exception:
                pass
        for p in self.peersManager.httpPeers:
            t = Thread(target=p.httpRequest)
            t.daemon = True
            t.start()
            self.HttpThreads.append(t)

    def start(self):
        MAX_PIECES_TO_REQ = 100

        while not self.piecesManager.are_pieces_completed():
            unfinished_pieces = list(filter(lambda x: x.finished is False, self.piecesManager.pieces))
            for piece in self.piecesManager.pieces:
                piece.reset_pending_blocks()
            if len(self.peersManager.peers) > 0:
                pieces_requested = 0
                for piece in unfinished_pieces:
                    if pieces_requested > MAX_PIECES_TO_REQ:
                        break
                    peer = self.peersManager.getUnchokedPeer(piece.pieceIndex)
                    if not peer:
                        continue

                    data = piece.getEmptyBlock()
                    if data:
                        index, offset, length = data

                        self.peersManager.requestNewPiece(peer, index, offset, length)
                    pieces_requested += 1
            if len(self.peersManager.httpPeers) > self.requestQueue.qsize():
                for httpPeer in self.peersManager.httpPeers:
                    pieces = httpPeer.get_pieces(self.piecesManager)
                    if pieces:
                        pieces_by_file = httpPeer.construct_pieces_by_file(pieces)
                        self.requestQueue.put((httpPeer, pieces_by_file))

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
        for t in self.HttpThreads:
            t.requestStop()

        return self.torrent.torrentFile['info']['name']
