import academictorrents as at
import unittest
import os
import shutil
import time
import sys
from academictorrents.utils import clean_path

class AcademicTorrentsTestSuite(unittest.TestCase):
    """Test cases on the academictorrents.py file."""

    def test_absolute_truth_and_meaning(self):
        assert True

    def test_urls(self):
        path = at.get("4e9022e7abc519733bf81a4fa353165633c371f1", urls=["https://s3.amazonaws.com/mila-genomics/testfile0.rtf"])
        self.assertTrue(os.path.isfile(path))

    def test_set_datastore(self):
        test_config_filename = clean_path("~/.test_academictorrents.config")
        self.assertFalse(os.path.isfile(test_config_filename))
        at.set_datastore("/data/lisa/data/academictorrents-datastore/", test_config_filename)
        self.assertTrue(os.path.isfile(test_config_filename))
        os.remove(test_config_filename)

    def test_empty_url(self):
        path = at.get("4d563087fb327739d7ec9ee9a0d32c4cb8b0355e")
        self.assertTrue(os.path.isfile(path))

if __name__ == '__main__':
    unittest.main()
