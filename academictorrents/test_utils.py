import academictorrents as at
import unittest
import shutil
import sys, os, time
import datetime
from academictorrents import utils
from academictorrents import Torrent



class UtilsTestSuite(unittest.TestCase):
    def test_datastore_path_no_trailing_slash(self):
        path = utils.datastore_path(datastore="/data/lisa/data/LUNA16")
        self.assertTrue(path == '/data/lisa/data/LUNA16/')

    def test_datastore_path_slashes_on_name(self):
        path = utils.datastore_path(datastore="/data/lisa/data/LUNA16/")
        self.assertTrue(path == '/data/lisa/data/LUNA16/')

    def test_datastore_path_default(self):
        path = utils.datastore_path()
        self.assertTrue(path == os.getcwd() + "/datastore/")

    def test_datastore_path_relative(self):
        path = utils.datastore_path(datastore="datastore/")
        self.assertTrue(path == "~/datastore/")

    def test_datastore_path_relative_dot(self):
        path = utils.datastore_path(datastore=".")
        self.assertTrue(path == "./")

    def test_datastore_path_relative_dot_slash(self):
        path = utils.datastore_path(datastore="./")
        self.assertTrue(path == "./")

    def test_datastore_path_relative_tilde(self):
        path = utils.datastore_path(datastore="~/mycooldatastore")
        self.assertTrue(path == "~/mycooldatastore/")

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
        torrent_dir = "./tests/"
        torrent = Torrent.Torrent(hash="55a8925a8d546b9ca47d309ab438b91f7959e77f", data_dir=torrent_dir).get_from_file()
        ret = utils.filenames_present(torrent, torrent_dir)
        self.assertFalse(ret)

    def test_filename_checker_true(self):
        torrent_dir = "./datastore/"
        torrent = Torrent.Torrent(hash="55a8925a8d546b9ca47d309ab438b91f7959e77f", data_dir=torrent_dir).get_from_file()
        ret = utils.filenames_present(torrent, torrent_dir)
        self.assertTrue(ret)

    # Test with different datastore
    def test_different_datastore(self):
        filename = at.get('323a0048d87ca79b68f12a6350a57776b6a3b7fb', datastore=os.getcwd() + '/datastore/alt/')
        assert filename == os.getcwd() + '/datastore/alt/mnist.pkl.gz'
        self.assertTrue(os.path.isfile(filename))

    # Test with different datastore
    def test_home_datastore(self):
        import pdb; pdb.set_trace()
        filename = at.get('323a0048d87ca79b68f12a6350a57776b6a3b7fb', datastore="~/whatever/you/want")
        assert filename == "~/whatever/you/want/mnist.pkl.gz"
        self.assertTrue(os.path.isfile(filename))
