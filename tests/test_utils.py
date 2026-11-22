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
        path = utils.get_datastore("~/.academictorrents-datastore")
        self.assertTrue(path == utils.clean_path("~/.academictorrents-datastore") + "/")

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
        utils.write_timestamp("test")
        timestamp = utils.read_timestamp("test")
        self.assertTrue(isinstance(timestamp, int))

    def test_check_timestamp_now(self):
        ret = utils.timestamp_is_within_30_days(int(datetime.datetime.timestamp(datetime.datetime.now())))
        self.assertTrue(ret)

    def test_check_timestamp_two_weeks(self):
        ret = utils.timestamp_is_within_30_days(int(datetime.datetime.timestamp(datetime.datetime.now())) - 86400 * 14)
        self.assertTrue(ret)

    def test_check_timestamp_2_months(self):
        ret = utils.timestamp_is_within_30_days(int(datetime.datetime.timestamp(datetime.datetime.now())) - 86400 * 60)
        self.assertFalse(ret)

    def test_filename_checker(self):
        torrent = Torrent.Torrent(hash="55a8925a8d546b9ca47d309ab438b91f7959e77f", datastore="./tests/")
        self.assertFalse(utils.filenames_present(torrent))

    def test_filename_checker_true(self):
        torrent = Torrent.Torrent(hash="55a8925a8d546b9ca47d309ab438b91f7959e77f", datastore="~/.academictorrents-datastore/")
        self.assertTrue(utils.filenames_present(torrent))

    def test_bitfield(self):
        bf = utils.Bitfield(13)
        self.assertEqual(len(bf), 13)
        self.assertEqual(bf.count(), 0)
        bf[0] = 1
        bf[12] = True
        self.assertTrue(bf[0] and bf[12] and not bf[1])
        self.assertEqual(bf.count(), 2)
        self.assertEqual(sum(bf), 2)
        self.assertEqual(bf.tobytes(), b'\x80\x08')
        bf[0] = 0
        self.assertEqual(bf.count(), 1)
        with self.assertRaises(IndexError):
            bf[13] = 1

    def test_bitfield_from_peer_bytes(self):
        bf = utils.Bitfield.from_bytes(b'\xf0\x01')  # MSB-first, as on the wire
        self.assertEqual(len(bf), 16)
        self.assertEqual([i for i in range(16) if bf[i]], [0, 1, 2, 3, 15])
        self.assertEqual(bf.count(), 5)

    def test_bitfield_count_ignores_padding(self):
        bf = utils.Bitfield(3, b'\xff')
        self.assertEqual(bf.count(), 3)

    def test_user_agent(self):
        self.assertTrue(utils.USER_AGENT.startswith("AT-Client/" + at.__version__))
        self.assertNotIn("mozilla", utils.USER_AGENT.lower())
        self.assertNotIn("urllib", utils.USER_AGENT.lower())

    def test_torrent_download_not_rejected(self):
        import requests
        resp = requests.get("https://academictorrents.com/download/55a8925a8d546b9ca47d309ab438b91f7959e77f",
                            headers=utils.HEADERS, timeout=30)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.content.startswith(b"d"))  # bencoded dict, not an error page

    # Test with different datastore
    def test_different_datastore(self):
        filename = at.get('323a0048d87ca79b68f12a6350a57776b6a3b7fb', datastore='~/.academictorrent-datastore/alt/', use_timestamp=False)
        assert filename == os.path.expanduser('~/.academictorrent-datastore/alt/mnist.pkl.gz')
        self.assertTrue(os.path.isfile(filename))
