from academictorrents import academictorrents as at
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
        #contents = at.get_from_file("55a8925a8d546b9ca47d309ab438b91f7959e77f", torrent_dir)
        #PiecesManager.PiecesManager()
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
