import academictorrents as at
import unittest
import os
import shutil
import time
import sys


class PeerDownloadTestSuite(unittest.TestCase):
    """Test cases on the academictorrents.py file."""

    def test_get_multiple_files(self):
        path = at.get('b79869ca12787166de88311ca1f28e3ebec12dec')
        files = os.listdir(path)
        self.assertTrue(len(files) == 174)

    def test_redownload_only_one_file(self):
        path = at.get('b79869ca12787166de88311ca1f28e3ebec12dec')  # test torrent
        files = os.listdir(path)
        self.assertTrue(len(files) == 174)
        datastore = os.getcwd() + "/datastore/"
        os.remove(datastore + "/BreastCancerCell_dataset/ytma55_030603_benign2.TIF")
        files = os.listdir(path)
        self.assertTrue(len(files) == 173)
        path = at.get('b79869ca12787166de88311ca1f28e3ebec12dec')  # test torrent
        files = os.listdir(path)
        self.assertTrue(len(files) == 174)

    def test_get_single_file(self):
        filename = at.get('323a0048d87ca79b68f12a6350a57776b6a3b7fb')
        self.assertTrue(os.path.isfile(filename))

if __name__ == '__main__':
    unittest.main()
