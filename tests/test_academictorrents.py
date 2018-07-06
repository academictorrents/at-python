import academictorrents as at
import unittest
import os
import shutil
import os
import sys, os, time


class AcademicTorrentsTestSuite(unittest.TestCase):
    """Test cases on the academictorrents.py file."""

    def test_absolute_truth_and_meaning(self):
        assert True

    def test_load_from_torrent(self):
        contents = at.get_from_file("55a8925a8d546b9ca47d309ab438b91f7959e77f", torrent_dir="./tests/")
        self.assertTrue(len(contents)==7)

    # TODO: Add a test for get_from_url

    ### Integration-style tests ###

    def test_get_file_http(self):
        filename = at.get('55a8925a8d546b9ca47d309ab438b91f7959e77f') # test torrent
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names

    def test_get_multiple_files(self):
        path = at.get('b79869ca12787166de88311ca1f28e3ebec12dec') # test torrent
        files = os.listdir(path) #assert is a folder
        self.assertTrue(len(files) == 174) #assert contains the correct file names

    def test_redownload_only_one_file(self):
        path = at.get('b79869ca12787166de88311ca1f28e3ebec12dec') # test torrent
        files = os.listdir(path)
        self.assertTrue(len(files) == 174)
        datastore = os.getcwd() + "/datastore/"
        os.remove(datastore + "/BreastCancerCell_dataset/ytma55_030603_benign2.TIF")
        files = os.listdir(path)
        self.assertTrue(len(files) == 173)
        path = at.get('b79869ca12787166de88311ca1f28e3ebec12dec') # test torrent
        files = os.listdir(path)
        self.assertTrue(len(files) == 174)

    def test_get_single_file(self):
        filename = at.get('323a0048d87ca79b68f12a6350a57776b6a3b7fb') # test torrent
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names

    def test_find_downloaded_torrent(self):
        filename = at.get('323a0048d87ca79b68f12a6350a57776b6a3b7fb') # test torrent
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names

    # Test with different datastore
    def test_different_datastore(self):
        filename = at.get('323a0048d87ca79b68f12a6350a57776b6a3b7fb', datastore=os.getcwd() + '/datastore/alt/') # test torrent
        assert filename == os.getcwd() + '/datastore/alt/mnist.pkl.gz'
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names



if __name__ == '__main__':
    unittest.main()
