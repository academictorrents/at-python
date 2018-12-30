import select
import time
from . import utils
import logging
from threading import Thread
from pubsub import pub
from . import RarestPieces
from . import Peer


class PeersManager(Thread):
    def __init__(self, torrent, piecesManager):
        Thread.__init__(self)
        self.peers = []
        self.torrent = torrent
        self.piecesManager = piecesManager
        self.rarestPieces = RarestPieces.RarestPieces(piecesManager)
        self.stopRequested = False
        self.setDaemon(True)

        self.piecesByPeer = []
        for i in range(self.piecesManager.numberOfPieces):
            self.piecesByPeer.append([0, []])

        # Events
        pub.subscribe(self.addPeer, 'PeersManager.newPeer')
        pub.subscribe(self.peersBitfield, 'PeersManager.updatePeersBitfield')

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
                    logging.info(peer.ip + ": removing peer because of: " + str(e))
                    self.removePeer(peer)
                    logging.info("new number of peers: " + str(len(self.peers)))
                    continue

                if len(msg) == 0:
                    logging.error(peer.ip + ": removing peer because we received a message of 0 length")
                    self.removePeer(peer)
                    logging.info("new number of peers: " + str(len(self.peers)))
                    continue
                peer.readBuffer += msg
                self.manageMessageReceived(peer)

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

    def getUnchokedPeer(self, index):
        for peer in self.peers:
            if isinstance(peer, Peer.Peer) and peer.hasPiece(index) and not peer.state["peer_choking"]:
                return peer
        return False

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
                        logging.error(peer.ip + ": removing peer because of: " + e)
                        self.removePeer(peer)
                        logging.info("new number of peers: " + str(len(self.peers)))

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
                logging.debug("error id: " + str(msgCode) +  " ->" + str(e))
                return

    def requestNewPiece(self, peer, pieceIndex, blockOffset, length):
        request = peer.build_request(pieceIndex, blockOffset, length)
        peer.sendToPeer(request)

    def make_requests(self, unfinished_pieces):
        max_requests = 50
        requests = 0
        i = 0
        if not self.peers:
            return

        while requests < max_requests:
            i += 1
            piece = unfinished_pieces[i % len(unfinished_pieces)]
            peer = self.getUnchokedPeer(piece.pieceIndex)
            if not peer:
                continue

            for block in piece.get_free_blocks():
                piece.set_pending_block(block)
                self.requestNewPiece(peer, piece.pieceIndex, block[4] * piece.BLOCK_SIZE, block[1])
                requests += 1
