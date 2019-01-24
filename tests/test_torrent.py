import academictorrents as at
import unittest
import os
import shutil
import os
import sys, os, time
from academictorrents import Torrent

class TorrentTestSuite(unittest.TestCase):
    """Test cases on the torrent.py file."""
    def test_get_file_http(self):
        filename = at.get('55a8925a8d546b9ca47d309ab438b91f7959e77f', use_timestamp=False)
        self.assertTrue(os.path.isfile(filename))
        time.sleep(3)

    def test_load_from_file(self):
        contents = Torrent.Torrent(hash="55a8925a8d546b9ca47d309ab438b91f7959e77f", datastore="./tests/").contents
        self.assertTrue(len(contents)==7)

    def test_load_from_url(self):
        pass
