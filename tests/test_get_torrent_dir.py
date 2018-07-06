import academictorrents as at
import unittest
import os
import shutil
import os
import sys, os, time


class GetTestSuite(unittest.TestCase):
    """Test cases on the academictorrents.py file."""

    def test_get_torrent_dir(self):
        path = at.get_torrent_dir(datastore='/data/lisa/data/', name="LUNA16")
        print(path)
        self.assertTrue(path == '/data/lisa/data/LUNA16/')

    def test_get_torrent_dir_no_name(self):
        path = at.get_torrent_dir(datastore='/data/lisa/data/')
        print(path)
        self.assertTrue(path == '/data/lisa/data/')

    def test_get_torrent_dir_default(self):
        path = at.get_torrent_dir()
        print(path)
        self.assertTrue(path == os.getcwd() + "/datastore/")
