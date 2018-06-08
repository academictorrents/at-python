from academictorrents import academictorrents as at
import unittest
import os
import shutil
import os
import sys, os, time


class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""

    def test_absolute_truth_and_meaning(self):
        assert True

    def test_get_file_http(self):
        hash = '0332d23cc9909532b3b2c5ddcc3ac045f3f30ff4'
        if os.path.isdir(at.get_client().get_torrent_dir(hash)):
            shutil.rmtree(at.get_client().get_torrent_dir(hash))
        filename = at.get(hash) # test torrent
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names

    def test_get_multiple_files(self):
        hash = 'b79869ca12787166de88311ca1f28e3ebec12dec'
        if os.path.isdir(at.get_client().get_torrent_dir(hash)):
            shutil.rmtree(at.get_client().get_torrent_dir(hash))
        path = at.get(hash) # test torrent
        files = os.listdir(path) #assert is a folder
        self.assertTrue(len(files) == 174) #assert contains the correct file names

    def test_get_single_file(self):
        hash = '323a0048d87ca79b68f12a6350a57776b6a3b7fb'
        if os.path.isdir(at.get_client().get_torrent_dir(hash)):
            shutil.rmtree(at.get_client().get_torrent_dir(hash))
        filename = at.get(hash) # test torrent
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names

    def test_find_downloaded_torrent(self):
        filename = at.get('323a0048d87ca79b68f12a6350a57776b6a3b7fb') # test torrent
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names

    # Test with different datastore
    def test_different_datastore(self):
        hash = '323a0048d87ca79b68f12a6350a57776b6a3b7fb'
        at.get_client().set_datastore(os.getcwd() + '/datastore/alt/')
        assert at.get_client().datastore == os.getcwd() + '/datastore/alt/'
        filename = at.get(hash) # test torrent
        assert filename == os.getcwd() + '/datastore/alt/' + hash + '/mnist.pkl.gz'
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names


if __name__ == '__main__':
    unittest.main()
