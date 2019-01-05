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
    def test_clean_path(self):
        path = utils.clean_path(datastore="/data/lisa/data/LUNA16")
        self.assertTrue(path == '/data/lisa/data/LUNA16/')

    def test_clean_path_default(self):
        path = utils.clean_path()
        self.assertTrue(path == os.getcwd() + "/datastore/")

    def test_clean_path_relative(self):
        path = utils.clean_path(datastore="datastore/")
        self.assertTrue(path == os.getcwd() + "/datastore/")

    def test_clean_path_relative_dot(self):
        path = utils.clean_path(".")
        self.assertTrue(path == os.getcwd() + "/")

    def test_clean_path_relative_dot_slash(self):
        path = utils.clean_path("./")
        self.assertTrue(path == os.getcwd() + "/")

    def test_clean_path_relative_dot_slash_dir(self):
        path = utils.clean_path("./apples")
        self.assertTrue(path == os.getcwd() + "/apples/")

    def test_clean_path_relative_tilde(self):
        path = utils.clean_path("~/mycooldatastore")
        self.assertTrue(path == home + "/mycooldatastore/")

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
