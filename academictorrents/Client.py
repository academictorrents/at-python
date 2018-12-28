
__author__ = 'alexisgallepe'

import time
import logging
import os
import requests
import json
import datetime
from queue import Queue
from threading import Thread

from . import PeersManager
from . import PeerSeeker
from . import PiecesManager
from . import Torrent
from . import Tracker
from . import HttpPeer
from . import utils
from . import progress_bar

class Client(object):
    @classmethod
    def __init__(self, hash, torrent_dir, piecesManager):
        self.hash = hash
        self.torrent_dir = torrent_dir

        newpeersQueue = Queue()
        self.requestQueue = Queue(maxsize=10)

        self.torrent = Torrent.Torrent(self.hash, self.torrent_dir)
        self.tracker = Tracker.Tracker(self.torrent, newpeersQueue)
        self.piecesManager = piecesManager
        self.peerSeeker = PeerSeeker.PeerSeeker(newpeersQueue, self.torrent)
        self.peersManager = PeersManager.PeersManager(self.torrent, self.piecesManager, self.requestQueue)

        self.tracker.start()
        self.peersManager.start()
        self.peerSeeker.start()
        self.piecesManager.start()

        for url in self.torrent.torrentFile.get('url-list'):
            try:
                peer = HttpPeer.HttpPeer(self.torrent, url)
                self.peersManager.httpPeers.append(peer)
            except Exception:
                pass
        for i in self.peersManager.httpPeers:
            t = Thread(target=self.peersManager.httpRequest)
            t.daemon = True
            t.start()

    def start(self, starting_size):
        new_size = starting_size
        old_size = 0
        MAX_PIECES_TO_REQ = 100
        start_time = time.time()

        while not self.piecesManager.are_pieces_completed():
            unfinished_pieces = list(filter(lambda x: x.finished is False, self.piecesManager.pieces))
            for piece in unfinished_pieces:
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
                    pieces_by_file = httpPeer.construct_pieces_by_file(pieces)  # set all those blocks to Pending
                    self.requestQueue.put((httpPeer, pieces_by_file))

            new_size = self.piecesManager.check_percent_finished()
            rate = (new_size-starting_size)/(time.time()-start_time)/1000. # rate in KBps
            progress_bar.print_progress(new_size, self.torrent.totalLength, "BT:{}, Web:{}".format(len(self.peersManager.peers),len(self.peersManager.httpPeers)), "({0:.2f}kB/s)".format(rate))

            if new_size == old_size:
                time.sleep(0.1)
                continue

            old_size = new_size
            downloaded = new_size - starting_size
            remaining = self.torrent.totalLength - (starting_size + downloaded)
            self.tracker.downloading_message(downloaded, remaining)

        new_size = self.piecesManager.check_percent_finished()
        downloaded = new_size - starting_size
        remaining = self.torrent.totalLength - (starting_size + downloaded)
        self.tracker.stop_message(downloaded, remaining)
        self.tracker.requestStop()
        self.peerSeeker.requestStop()
        self.peersManager.requestStop()


        rate = (new_size-starting_size)/(time.time()-start_time)/1000. # rate in KBps
        progress_bar.print_progress(new_size, self.torrent.totalLength, "BT:{}, Web:{}".format(len(self.peersManager.peers),len(self.peersManager.httpPeers)), "({0:.2f}kB/s)".format(rate))

        if remaining == 0:
            utils.write_timestamp(self.hash)
        print("\nDownload Complete!")
        return self.torrent_dir + self.torrent.torrentFile['info']['name']
