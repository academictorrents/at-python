from academictorrents import Client
import unittest
import os
import shutil
import os
import cPickle, gzip
import sys, os, time
import numpy as np


class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""

    def test_absolute_truth_and_meaning(self):
        assert True

    def test_get_file_http(self):
        client = Client()
        hash = '0332d23cc9909532b3b2c5ddcc3ac045f3f30ff4'
        if os.path.isdir(client.get_torrent_dir(hash)):
            shutil.rmtree(client.get_torrent_dir(hash))
        filename = client.get_dataset(hash) # test torrent
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names

    def test_get_multiple_files(self):
        client = Client()
        hash = 'b79869ca12787166de88311ca1f28e3ebec12dec'
        if os.path.isdir(client.get_torrent_dir(hash)):
            shutil.rmtree(client.get_torrent_dir(hash))
        path = client.get_dataset(hash) # test torrent
        files = os.listdir(path) #assert is a folder
        self.assertTrue(len(files) == 174) #assert contains the correct file names

    def test_get_single_file(self):
        client = Client()
        hash = '323a0048d87ca79b68f12a6350a57776b6a3b7fb'
        if os.path.isdir(client.get_torrent_dir(hash)):
            shutil.rmtree(client.get_torrent_dir(hash))
        filename = client.get_dataset(hash) # test torrent
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names

    def test_find_downloaded_torrent(self):
        client = Client()
        filename = client.get_dataset('323a0048d87ca79b68f12a6350a57776b6a3b7fb') # test torrent
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names

    # Test with different datastore
    def test_different_datastore(self):
        client = Client()
        hash = '323a0048d87ca79b68f12a6350a57776b6a3b7fb'
        client.set_datastore(os.getcwd() + '/datastore/alt/')
        assert client.datastore == os.getcwd() + '/datastore/alt/'
        filename = client.get_dataset(hash) # test torrent
        assert filename == os.getcwd() + '/datastore/alt/' + hash + '/mnist.pkl.gz'
        self.assertTrue(os.path.isfile(filename)) #assert contains the correct file names


#print "About to open the file"


#mnist = gzip.open(filename, 'rb')
#train_set, validation_set, test_set = cPickle.load(mnist)
#mnist.close()

if __name__ == '__main__':
    unittest.main()
