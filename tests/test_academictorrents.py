import academictorrents as at
import unittest
import os
import shutil
import time
import sys


class AcademicTorrentsTestSuite(unittest.TestCase):
    """Test cases on the academictorrents.py file."""

    def test_absolute_truth_and_meaning(self):
        assert True

    # Test with different datastore
    def test_different_datastore(self):
        filename = at.get('323a0048d87ca79b68f12a6350a57776b6a3b7fb', datastore=os.getcwd() + '/datastore/alt/')
        assert filename == os.getcwd() + '/datastore/alt/mnist.pkl.gz'
        self.assertTrue(os.path.isfile(filename))

if __name__ == '__main__':
    unittest.main()
