import time
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
        self.newpeersQueue = Queue()

        self.piecesManager = piecesManager
        self.peerSeeker = PeerSeeker(self.newpeersQueue, torrent)
        self.peersManager = PeersManager(self.torrent, self.piecesManager)
        self.tracker = Tracker(torrent, self.newpeersQueue, start_downloaded)

        self.tracker.start()
        self.peersManager.start()
        self.peerSeeker.start()
        self.piecesManager.start()

        for url in self.torrent.torrentFile.get('url-list'):
            try:
                peer = HttpPeer.HttpPeer(self.torrent, url, self.requestQueue)
                peer.start()
                self.peersManager.httpPeers.append(peer)
            except Exception:
                pass

    def start(self):
        MAX_BLOCKS_TO_REQ = 50

        while not self.piecesManager.are_pieces_completed():
            # Reset Pending Blocks
            unfinished_pieces = list(filter(lambda x: x.finished is False, self.piecesManager.pieces))
            for piece in self.piecesManager.pieces:
                piece.reset_pending_blocks()

            # Make P2P requests
            if len(self.peersManager.peers) > 0:
                blocks_requested = 0
                for piece in unfinished_pieces:
                    if blocks_requested > MAX_BLOCKS_TO_REQ:
                        break
                    for block in [block for block in piece.blocks if block[0] == "Free"]:
                        peer = self.peersManager.getUnchokedPeer(piece.pieceIndex)

                        if not peer:
                            continue
                        data = piece.getEmptyBlock()

                        if data:
                            index, offset, length = data
                            self.peersManager.requestNewPiece(peer, index, offset, length)
                    blocks_requested += 1

            # Make WebSeed requests
            if len(self.peersManager.httpPeers) > self.requestQueue.qsize():
                for httpPeer in self.peersManager.httpPeers:
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
        for httpPeer in self.peersManager.httpPeers:
            httpPeer.requestStop()

        return self.torrent.torrentFile['info']['name']
