import academictorrents as at
import unittest
import os
import shutil
import os
import sys, os, time
from academictorrents import Torrent

class TorrentTestSuite(unittest.TestCase):
    """Test cases on the torrent.py file."""

    def test_load_from_file(self):
        contents = Torrent.Torrent(hash="55a8925a8d546b9ca47d309ab438b91f7959e77f", torrent_dir="./tests/").get_from_file()
        self.assertTrue(len(contents)==7)

    def test_load_from_url(self):
        pass
