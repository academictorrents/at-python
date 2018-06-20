
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
from collections import defaultdict
from pubsub import pub


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
                    pieces = self.get_pieces()
                    if pieces:
                        pieces_by_file = self.construct_pieces_by_file(pieces)  # set all those blocks to Pending
                        responses = self.request_ranges(httpPeer, pieces_by_file)
                        self.publish_responses(responses, pieces_by_file)

            new_size = self.checkPercentFinished()
            if new_size == old_size:
                continue

            old_size = new_size
            print("Number of peers: ",len(self.peersManager.unchokedPeers)," Completed: ",float((float(new_size) / self.torrent.totalLength)*100),"%")

            time.sleep(0.1)

        self.peerSeeker.requestStop()
        self.peersManager.requestStop()

    def publish_responses(self, responses, pieces_by_file):
        offset = 0
        for filename, pieces in pieces_by_file.items():
            blockOffset = 0
            resp = responses.get(filename)
            for piece in pieces:
                for block in piece.blocks:
                    start = offset + blockOffset
                    end = offset + blockOffset + piece.BLOCK_SIZE
                    pub.sendMessage('PiecesManager.Piece', piece=(piece.pieceIndex, blockOffset, resp.content[start: end]))
                    blockOffset += piece.BLOCK_SIZE
                blockOffset = 0
                offset += piece.pieceSize

    def get_pieces(self):
        # TODO: Add another way to exit this loop when we don't hit the max size
        size = 0
        temp_size = 0
        max_size_to_download = 15000000
        temp_pieces = []
        pieces = []
        for idx, b in enumerate(self.piecesManager.bitfield):
            piece = self.piecesManager.pieces[idx]
            if not b:
                temp_pieces.append(piece)
                temp_size += piece.pieceSize

            if size < temp_size:
                size = temp_size
                pieces = temp_pieces

            if size > max_size_to_download:
                return pieces

            if b:
                temp_pieces = []
                temp_size = 0
        return pieces

    def request_ranges(self, httpPeer, pieces_by_file):
        responses = {}
        for filename, pieces in pieces_by_file.items():
            start = pieces[0].files[0].get('fileOffset')
            filename = pieces[0].files[0].get('path').split('/')[-1]
            url = httpPeer.url
            directory = httpPeer.torrent.torrentFile.get('name')
            end = start
            for piece in pieces:
                end += piece.pieceSize
            resp = requests.get(url, headers={'Range': 'bytes=' + str(start) + '-' + str(end)})
            responses[filename] = resp
        return responses


    def construct_pieces_by_file(self, pieces):
        pieces_by_file = defaultdict(list)
        for piece in pieces:
            if len(piece.files) == 1:
                filename = piece.files[0].get('path').split('/')[-1]
                pieces_by_file[filename].append(piece)
            else:
                pieces_by_file[str(len(pieces_by_file))].append(piece)
        return pieces_by_file


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
