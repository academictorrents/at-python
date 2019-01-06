import academictorrents as at
import unittest
import shutil
import sys, os, time
import datetime
from academictorrents import utils
from academictorrents import Torrent
from os.path import expanduser
home = expanduser("~")


class UtilsTestSuite(unittest.TestCase):
    """Test cases on the utils.py file."""
    def test_get_datastore(self):
        path = utils.get_datastore(datastore="/data/lisa/data/LUNA16")
        self.assertTrue(path == '/data/lisa/data/LUNA16/')

    def test_get_datastore_default(self):
        path = utils.get_datastore()
        self.assertTrue(path == os.getcwd() + "/datastore/")

    def test_get_datastore_relative(self):
        path = utils.get_datastore(datastore="datastore/")
        self.assertTrue(path == os.getcwd() + "/datastore/")

    def test_get_datastore_relative_dot(self):
        path = utils.get_datastore(".")
        self.assertTrue(path == os.getcwd() + "/")

    def test_get_datastore_relative_dot_slash(self):
        path = utils.get_datastore("./")
        self.assertTrue(path == os.getcwd() + "/")

    def test_get_datastore_relative_dot_slash_dir(self):
        path = utils.get_datastore("./apples")
        self.assertTrue(path == os.getcwd() + "/apples/")

    def test_get_datastore_relative_tilde(self):
        path = utils.get_datastore("~/mycooldatastore")
        self.assertTrue(path == home + "/mycooldatastore/")

    def test_relative_back(self):
        path = utils.get_datastore("..")
        self.assertTrue(path == os.path.abspath("..") + "/")

    def test_write_timestamp(self):
        utils.write_timestamp("55a8925a8d546b9ca47d309ab438b91f7959e77f")
        timestamp = utils.read_timestamp("55a8925a8d546b9ca47d309ab438b91f7959e77f")
        self.assertTrue(isinstance(timestamp, int))

    def test_check_timestamp_now(self):
        ret = utils.timestamp_is_within_30_days(int(datetime.datetime.now().strftime("%s")))
        self.assertTrue(ret)

    def test_check_timestamp_two_weeks(self):
        ret = utils.timestamp_is_within_30_days(int(datetime.datetime.now().strftime("%s")) - 86400 * 14)
        self.assertTrue(ret)

    def test_check_timestamp_2_months(self):
        ret = utils.timestamp_is_within_30_days(int(datetime.datetime.now().strftime("%s")) - 86400 * 60)
        self.assertFalse(ret)

    def test_filename_checker(self):
        torrent = Torrent.Torrent(hash="55a8925a8d546b9ca47d309ab438b91f7959e77f", datastore= "./tests/")
        self.assertFalse(utils.filenames_present(torrent))

    def test_filename_checker_true(self):
        torrent = Torrent.Torrent(hash="55a8925a8d546b9ca47d309ab438b91f7959e77f", datastore="./datastore/")
        self.assertTrue(utils.filenames_present(torrent))

    # Test with different datastore
    def test_different_datastore(self):
        filename = at.get('323a0048d87ca79b68f12a6350a57776b6a3b7fb', datastore=os.getcwd() + '/datastore/alt/')
        assert filename == os.getcwd() + '/datastore/alt/mnist.pkl.gz'
        self.assertTrue(os.path.isfile(filename))
