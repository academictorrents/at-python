__author__ = 'alexisgallepe'

import time
from . import Peer
import logging
from threading import Thread
from pubsub import pub


class PeerSeeker(Thread):
    def __init__(self, newpeersQueue, torrent):
        Thread.__init__(self)
        self.stopRequested = False
        self.newpeersQueue = newpeersQueue
        self.torrent = torrent
        self.peerFailed = [("", "")]
        self.setDaemon(True)
        self.reset_time = time.time()

    def requestStop(self):
        self.stopRequested = True

    def run(self):
        while not self.stopRequested:

            # reset failed peers so we can try again
            if (time.time() - self.reset_time) > 30:
                logging.info("Resetting peerFailed list " + str(self.peerFailed))
                self.peerFailed = [("", "")]
                self.reset_time = time.time()

            peer = self.newpeersQueue.get()
            if not (peer[0], peer[1]) in self.peerFailed:
                p = Peer.Peer(self.torrent, peer[0], peer[1])
                if not p.connectToPeer(3):
                    self.peerFailed.append((peer[0], peer[1]))
                else:
                    logging.info(p.ip + ": added new peer")
                    pub.sendMessage('PeersManager.newPeer', peer=p)
