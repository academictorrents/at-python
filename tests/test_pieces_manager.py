import academictorrents as at
from academictorrents import PieceManager
from academictorrents import Torrent
import unittest
import os
import shutil
import os
import sys, os, time


class PieceManagerTestSuite(unittest.TestCase):
    """Test cases on the HttpPeer.py file."""

    def test_init(self):
        torrent_dir = "tests/"
        torrent = Torrent.Torrent("55a8925a8d546b9ca47d309ab438b91f7959e77f", torrent_dir)
        torrent.number_of_pieces = 3
        torrent.total_length = 12
        torrent.piece_length = 4
        torrent.filenames = [{'length': 12, 'path': 'tests/vangogh.tar.gz'}]
        torrent.pieces = b"\xae\x04\xf4\xbaT\xb8\xe2O\xa6!\xfa\xf4\x97\x94+\x86"
        pieces_manager = PieceManager.PieceManager(torrent)
        self.assertTrue(len(pieces_manager.pieces) == 3)
        self.assertTrue(len(pieces_manager.pieces[0].files) == 1)
        self.assertTrue(pieces_manager.pieces[0].files[0].get('piece_offset')==0)
        self.assertTrue(pieces_manager.pieces[1].files[0].get('piece_offset')==0)
        self.assertTrue(pieces_manager.pieces[2].files[0].get('piece_offset')==0)

        self.assertTrue(pieces_manager.pieces[0].files[0].get('file_offset')==0)
        self.assertTrue(pieces_manager.pieces[1].files[0].get('file_offset')==4)
        self.assertTrue(pieces_manager.pieces[2].files[0].get('file_offset')==8)
