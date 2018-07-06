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
        self.assertTrue(path == '/data/lisa/data/LUNA16/')

    def test_get_torrent_dir_no_trailing_slash(self):
        path = at.get_torrent_dir(datastore='/data/lisa/data', name="LUNA16")
        self.assertTrue(path == '/data/lisa/data/LUNA16/')

    def test_get_torrent_dir_slashes_on_name(self):
        path = at.get_torrent_dir(datastore='/data/lisa/data/', name="/LUNA16/")
        self.assertTrue(path == '/data/lisa/data/LUNA16/')

    def test_get_torrent_dir_no_name(self):
        path = at.get_torrent_dir(datastore='/data/lisa/data/')
        self.assertTrue(path == '/data/lisa/data/')

    def test_get_torrent_dir_default(self):
        path = at.get_torrent_dir()
        self.assertTrue(path == os.getcwd() + "/datastore/")

    def test_get_torrent_dir_relative(self):
        path = at.get_torrent_dir(datastore="datastore/")
        self.assertTrue(path == os.getcwd() + "/datastore/")

    def test_get_torrent_dir_relative_dot(self):
        path = at.get_torrent_dir(".")
        print(path)
        self.assertTrue(path == "./")

    def test_get_torrent_dir_relative_tilde(self):
        path = at.get_torrent_dir("~/mycooldatastore")
        self.assertTrue(path == "~/mycooldatastore/")
