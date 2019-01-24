import os
import unittest
import academictorrents as at
from academictorrents.utils import clean_path

class AcademicTorrentsTestSuite(unittest.TestCase):
    """Test cases on the academictorrents.py file."""

    def test_absolute_truth_and_meaning(self):
        assert True

    def test_urls(self):
        path = at.get("323a0048d87ca79b68f12a6350a57776b6a3b7fb", urls=["http://host1.academictorrents.com/share/mnist.pkl.gz"], use_timestamp=False)
        self.assertTrue(os.path.isfile(path))

    def test_set_datastore(self):
        test_path_to_config_file = clean_path("~/.test_academictorrents.config")
        self.assertFalse(os.path.isfile(test_path_to_config_file))
        at.set_datastore("/data/lisa/data/academictorrents-datastore/", test_path_to_config_file)
        self.assertTrue(os.path.isfile(test_path_to_config_file))
        os.remove(test_path_to_config_file)

    def test_empty_url(self):
        path = at.get("4d563087fb327739d7ec9ee9a0d32c4cb8b0355e", use_timestamp=False)
        self.assertTrue(os.path.isfile(path))

if __name__ == '__main__':
    unittest.main()
