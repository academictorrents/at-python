__author__ = 'alexisgallepe'

from . import Piece
import bitstring
import logging
from threading import Thread
from pubsub import pub


class PiecesManager(Thread):
    def __init__(self, torrent):
        Thread.__init__(self)
        self.torrent = torrent
        self.piecesCompleted = False

        self.numberOfPieces = torrent.numberOfPieces
        self.bitfield = bitstring.BitArray(self.numberOfPieces)
        self.pieces = self.generate_pieces()
        self.files = self.get_files()

        for file in self.files:
            idPiece = file['idPiece']
            self.pieces[idPiece].files.append(file)

        # Create events
        pub.subscribe(self.receive_block_piece, 'PiecesManager.Piece')
        pub.subscribe(self.update_bit_field, 'PiecesManager.PieceCompleted')

    def check_percent_finished(self):
        b = 0
        for i in range(self.numberOfPieces):
            if self.pieces[i].finished:
                b += self.pieces[i].pieceSize
        return b


    def check_disk_pieces(self):
        for piece in self.pieces:
            piece.isCompleteOnDisk()  # this should set all the finished bools on the finished pieces

    def update_bit_field(self, pieceIndex):
        self.bitfield[pieceIndex] = 1

    def receive_block_piece(self,piece):
        piece_index, piece_offset, piece_data = piece
        self.pieces[int(piece_index)].setBlock(piece_offset, piece_data)

    def generate_pieces(self):
        pieces = []
        for i in range(self.numberOfPieces):
            start = i * 20
            end = start + 20

            if i == (self.numberOfPieces-1):
                pieceLength = self.torrent.totalLength - (self.numberOfPieces-1) * self.torrent.pieceLength
                pieces.append(Piece.Piece(i, pieceLength, self.torrent.pieces[start:end]))
            else:
                pieces.append(Piece.Piece(i, self.torrent.pieceLength, self.torrent.pieces[start:end]))
        return pieces

    def are_pieces_completed(self):
        for piece in self.pieces:
            if not piece.finished:
                return False

        self.piecesCompleted = True
        logging.info("File(s) downloaded")
        return True

    def get_files(self):
        files = []
        pieceOffset = 0
        pieceSizeUsed = 0

        for f in self.torrent.fileNames:

            currentSizeFile = f["length"]
            fileOffset = 0

            while currentSizeFile > 0:
                idPiece = int(pieceOffset / self.torrent.pieceLength)
                pieceSize = self.pieces[idPiece].pieceSize - pieceSizeUsed

                if currentSizeFile - pieceSize < 0:
                    file = {"length": currentSizeFile,"idPiece":idPiece ,"fileOffset":fileOffset, "pieceOffset":pieceSizeUsed ,"path":f["path"]}
                    pieceOffset +=  currentSizeFile
                    fileOffset +=  currentSizeFile
                    pieceSizeUsed += currentSizeFile
                    currentSizeFile = 0

                else:
                    currentSizeFile -= pieceSize
                    file = {"length":pieceSize,"idPiece":idPiece ,"fileOffset":fileOffset,"pieceOffset":pieceSizeUsed , "path":f["path"]}
                    pieceOffset += pieceSize
                    fileOffset += pieceSize
                    pieceSizeUsed = 0

                files.append(file)
        return files


    def get_block(self, piece_index, block_offset, block_length):
        for piece in self.pieces:
            if piece_index == piece.pieceIndex:
                if piece.finished:
                    return piece.get_block(block_offset,block_length)
                else:
                    break

        return None
