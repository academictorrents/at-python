
__author__ = 'alexisgallepe'

import time
from . import PeersManager
from . import PeerSeeker
from . import PiecesManager
from . import Torrent
from . import Tracker
import logging
import Queue
import os
import requests


class Client(object):
    def __init__(self, torrent_path, file_store, http_timeout=10):
        newpeersQueue = Queue.Queue()
        self.torrent = Torrent.Torrent(torrent_path, file_store)
        self.http_timeout = 10
        self.file_store = file_store
        self.tracker = Tracker.Tracker(self.torrent,newpeersQueue)

        self.peerSeeker = PeerSeeker.PeerSeeker(newpeersQueue, self.torrent)
        self.piecesManager = PiecesManager.PiecesManager(self.torrent)
        self.peersManager = PeersManager.PeersManager(self.torrent,self.piecesManager)

        self.peersManager.start()
        logging.info("Peers-manager Started")

        self.peerSeeker.start()
        logging.info("Peer-seeker Started")

        self.piecesManager.start()
        logging.info("Pieces-manager Started")

    def start(self):
        old=0
        while not self.piecesManager.arePiecesCompleted() and self.http_timeout > 0.0:
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
                            self.peersManager.requestNewPiece(peer,index, offset, length)

                        piece.isComplete()

                ##########################
                        for block in piece.blocks:
                            if ( int(time.time()) - block[3] ) > 8 and block[0] == "Pending" :
                                block[0] = "Free"
                                block[3] = 0

                b=0
                for i in range(self.piecesManager.numberOfPieces):
                    for j in range(self.piecesManager.pieces[i].num_blocks):
                        if self.piecesManager.pieces[i].blocks[j][0]=="Full":
                            b+=len(self.piecesManager.pieces[i].blocks[j][2])

                if b == old:
                    continue

                old = b
                print("Number of peers: ",len(self.peersManager.unchokedPeers)," Completed: ",float((float(b) / self.torrent.totalLength)*100),"%")
                print(self.peersManager.unchokedPeers[0].ip)
               ##########################
            else:
                time.sleep(0.1)
                self.http_timeout -= .1
        print("No Peers Found -- Trying HTTP Backup")

        if self.http_timeout <= 0.0:
            urls_to_try = self.torrent.torrentFile.get('url-list', [])
            if len(urls_to_try) > 0:
                print("Downloading from backup URL: " + urls_to_try[0])
                if self.torrent.torrentFile.get('info', {}).get('files') is not None:
                    for f in self.torrent.torrentFile.get('info', {}).get('files'):
                        response = requests.get(urls_to_try[0], stream=True, allow_redirects=True)
                        #response.raise_for_status() # Throw an error for bad status codes
                        with open(self.torrent.torrentFile.get('info', {}).get('name', '') + "/" + f['path'][0], 'wb') as handle:
                            for block in response.iter_content(1024):
                                handle.write(block)
                        #urllib.urlretrieve(urls_to_try[0], self.torrent.torrentFile.get('info', {}).get('name', '') + "/" + f['path'][0])
                else:
                    response = requests.get(urls_to_try[0], stream=True, allow_redirects=True)
                    #response.raise_for_status() # Throw an error for bad status codes
                    with open(self.file_store + self.torrent.torrentFile.get('info', {}).get('name', ''), 'wb') as handle:
                        for block in response.iter_content(1024):
                            handle.write(block)
                    #urllib.urlretrieve(urls_to_try[0], self.file_store + self.torrent.torrentFile.get('info', {}).get('name', ''))
            else:
                print("No Backup URL Present")

        # gotta kill the threads
        self.peerSeeker.requestStop()
        self.peersManager.requestStop()
