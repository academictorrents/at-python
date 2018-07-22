__author__ = 'alexisgallepe'

import time
from . import Peer
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

    def requestStop(self):
        self.stopRequested = True

    def run(self):
        while not self.stopRequested:
            peer = self.newpeersQueue.get()
            if not (peer[0], peer[1]) in self.peerFailed:
                p = Peer.Peer(self.torrent, peer[0], peer[1])
                if not p.connectToPeer(3):
                    self.peerFailed.append((peer[0], peer[1]))
                else:
                    print("add new peer: " + p.ip)
                    pub.sendMessage('PeersManager.newPeer', peer=p)
