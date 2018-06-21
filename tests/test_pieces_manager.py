from academictorrents import academictorrents as at
from pytorrent import PiecesManager
from pytorrent import Torrent
import unittest
import os
import shutil
import os
import sys, os, time


class PiecesManagerTestSuite(unittest.TestCase):
    """Test cases on the HttpPeer.py file."""

    # TODO: handshake
    def test_handshake(self):
        assert True
