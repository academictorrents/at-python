
__author__ = 'alexisgallepe'

import time
from . import PeersManager
from . import PeerSeeker
from . import PiecesManager
from . import Torrent
from . import Tracker
from . import HttpPeer
import logging
from queue import Queue
import os
import requests


class Client(object):
    def __init__(self, hash, file_store):
        newpeersQueue = Queue()
        self.torrent = Torrent.Torrent(hash, file_store)
        self.file_store = file_store

        self.tracker = Tracker.Tracker(self.torrent, newpeersQueue)
        self.peerSeeker = PeerSeeker.PeerSeeker(newpeersQueue, self.torrent)
        self.piecesManager = PiecesManager.PiecesManager(self.torrent)
        self.peersManager = PeersManager.PeersManager(self.torrent,self.piecesManager)

        self.peersManager.start()
        logging.info("Peers-manager Started")

        self.peerSeeker.start()
        logging.info("Peer-seeker Started")

        self.piecesManager.start()
        logging.info("Pieces-manager Started")
        self.piecesManager.checkDiskPieces()

    def start(self):
        old_size = 0
        while not self.piecesManager.arePiecesCompleted():
            if len(self.peersManager.unchokedPeers) > 0:
                for piece in self.piecesManager.pieces:
                    if not piece.finished:
                        pieceIndex = piece.pieceIndex

                        peer = self.peersManager.getUnchokedPeer(pieceIndex)
                        if not peer:
                            continue

                        data = self.piecesManager.pieces[pieceIndex].getEmptyBlock()
                        if data:
                            index, offset, length = data
                            self.peersManager.requestNewPiece(peer, index, offset, length)

                        piece.isComplete()
                        self.reset_pending_blocks(piece)
            if len(self.peersManager.httpPeers) > 0:
                for httpPeer in self.peersManager.httpPeers:
                    pieces = httpPeer.get_pieces(self.piecesManager)
                    pieces_by_file = httpPeer.construct_pieces_by_file(pieces)  # set all those blocks to Pending
                    responses = httpPeer.request_ranges(pieces_by_file)
                    httpPeer.publish_responses(responses, pieces_by_file)

            new_size = self.checkPercentFinished()
            if new_size == old_size:
                continue

            old_size = new_size
            print("# Peers:",len(self.peersManager.unchokedPeers)," # HTTPSeeds:",len(self.peersManager.httpPeers)," Completed: ",float((float(new_size) / self.torrent.totalLength)*100),"%")

            time.sleep(0.1)

        self.peerSeeker.requestStop()
        self.peersManager.requestStop()
        return torrent_dir + self.torrent.torrentFile.get('info', {}).get('name')

    def reset_pending_blocks(self, piece):
        for block in piece.blocks:
            if ( int(time.time()) - block[3] ) > 8 and block[0] == "Pending" :
                block[0] = "Free"
                block[3] = 0

    def checkPercentFinished(self):
        b=0
        for i in range(self.piecesManager.numberOfPieces):
            for j in range(self.piecesManager.pieces[i].num_blocks):
                if self.piecesManager.pieces[i].blocks[j][0]=="Full":
                    b+=len(self.piecesManager.pieces[i].blocks[j][2])
        return b
