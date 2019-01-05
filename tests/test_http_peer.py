import academictorrents as at
from academictorrents import PieceManager
from academictorrents import Torrent
import unittest
import os
import shutil
import os
import sys, os, time


class HttpPeerTestSuite(unittest.TestCase):
    """Test cases on the HttpPeer.py file."""

    # TODO: handshake
    def test_handshake(self):
        assert True

    def test_get_pieces(self):
        assert True

    # TODO: request_ranges
    def test_request_ranges(self):
        assert True

    # TODO: publish_responses
    def test_publish_responses(self):
        assert True

    # TODO: construct_pieces_by_file
    def test_construct_pieces_by_file(self):
        assert True
