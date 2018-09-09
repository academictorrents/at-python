__author__ = 'alexisgallepe'

import select
import struct
from threading import Thread, Timer
from . import utils
from pubsub import pub
from . import RarestPieces
import logging
from . import HttpPeer, Peer
import time


class PeersManager(Thread):
    def __init__(self, torrent, piecesManager):
        Thread.__init__(self)
        self.peers = []
        self.httpPeers = []
        self.torrent = torrent
        self.piecesManager = piecesManager
        self.rarestPieces = RarestPieces.RarestPieces(piecesManager)
        self.stopRequested = False
        self.setDaemon(True)

        self.piecesByPeer = []
        for i in range(self.piecesManager.numberOfPieces):
            self.piecesByPeer.append([0, []])

        for url in self.torrent.torrentFile.get('url-list'):
            try:
                peer = HttpPeer.HttpPeer(torrent, url)
                self.httpPeers.append(peer)
                print("adding HttpPeer: " + peer.url)
            except Exception:
                pass

        # Events
        pub.subscribe(self.addPeer, 'PeersManager.newPeer')
        pub.subscribe(self.peersBitfield, 'PeersManager.updatePeersBitfield')

    def requestStop(self):
        self.stopRequested = True

    def peersBitfield(self, bitfield=None, peer=None, pieceIndex=None):
        if pieceIndex is not None:
            self.piecesByPeer[pieceIndex] = ["", []]
            return

        for i in range(len(self.piecesByPeer)):
            if bitfield[i] == 1 and peer not in self.piecesByPeer[i][1] and not self.piecesByPeer[i][0] == "":
                self.piecesByPeer[i][1].append(peer)
                self.piecesByPeer[i][0] = len(self.piecesByPeer[i][1])

    def getPeer(self, index):
        for peer in self.peers:
            if isinstance(peer, HttpPeer.HttpPeer) or (isinstance(peer, Peer.Peer) and peer.hasPiece(index)):
                return peer
        return False

    def run(self):
        while not self.stopRequested:
            self.startConnectionToPeers()
            read = [p.socket for p in self.peers]
            readList, _, _ = select.select(read, [], [], 1)

            # Receive from peers
            for socket in readList:
                peer = self.getPeerBySocket(socket)
                try:
                    msg = socket.recv(1024)
                except Exception as e:
                    print(peer.ip + ": removing peer because of: " + e)
                    self.removePeer(peer)
                    print("new number of peers: " + str(len(self.peers)))
                    continue

                if len(msg) == 0:
                    print(peer.ip + ": removing peer because we received a message of 0 length")
                    self.removePeer(peer)
                    print("new number of peers: " + str(len(self.peers)))
                    continue

                peer.readBuffer += msg
                self.manageMessageReceived(peer)

    def startConnectionToPeers(self):
        for peer in self.peers:
            if not peer.hasHandshaked:
                if peer.lastHandshakeAttempt < time.time() - 10:
                    peer.lastHandshakeAttempt = time.time()
                    try:
                        peer.sendToPeer(peer.handshake)
                        interested = peer.build_interested()
                        peer.sendToPeer(interested)
                    except Exception as e:
                        print(peer.ip + ": removing peer because of: " + e)
                        self.removePeer(peer)
                        print("new number of peers: " + str(len(self.peers)))

    def addPeer(self, peer):
        self.peers.append(peer)

    def removePeer(self, peer):
        if peer in self.peers:
            try:
                peer.socket.close()
            except Exception:
                pass

            self.peers.remove(peer)

        if peer in self.peers:
            self.peers.remove(peer)

        for rarestPiece in self.rarestPieces.rarestPieces:
            if peer in rarestPiece["peers"]:
                rarestPiece["peers"].remove(peer)

    def getPeerBySocket(self, socket):
        for peer in self.peers:
            if socket == peer.socket:
                return peer

        raise ("peer not present in PeerList")

    def manageMessageReceived(self, peer):
        while len(peer.readBuffer) > 0:
            if peer.hasHandshaked is False:
                peer.checkHandshake(peer.readBuffer)
                return

            msgLength = utils.convertBytesToDecimal(peer.readBuffer[0:4])

            # handle keep alive
            if peer.keep_alive(peer.readBuffer):
                return

            # len 0
            try:
                msgCode = int(ord(peer.readBuffer[4:5]))
                payload = peer.readBuffer[5:4 + msgLength]
            except Exception as e:
                logging.info(e)
                return

            # Message is not complete. Return
            if len(payload) < msgLength - 1:
                return

            peer.readBuffer = peer.readBuffer[msgLength + 4:]
            try:
                peer.idFunction[msgCode](payload)
            except Exception as e:
                logging.debug("error id:", msgCode, " ->", e)
                return

    def requestNewPiece(self, peer, pieceIndex, blockOffset, length):
        request = peer.build_request(pieceIndex, blockOffset, length)
        peer.sendToPeer(request)
