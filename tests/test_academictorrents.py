import os
import unittest
import academictorrents as at
from academictorrents.utils import clean_path
import gzip
import pickle

class AcademicTorrentsTestSuite(unittest.TestCase):
    """Test cases on the academictorrents.py file."""

    def test_absolute_truth_and_meaning(self):
        assert True

    # def test_ridiculously_massive_dataset(self):
    #    import pdb; pdb.set_trace()
	# path = at.get("7967a1633f7f89d3035838067a40cd807d935b3d", use_timestamp=False)
    #    self.assertTrue(os.path.isfile(path))

    def test_urls(self):
        path = at.get("323a0048d87ca79b68f12a6350a57776b6a3b7fb", urls=["http://host1.academictorrents.com/share/mnist.pkl.gz"], use_timestamp=False)
        self.assertTrue(os.path.isfile(path))
        mnist = gzip.open(path, 'rb')
        
        #a hack to open py2 pickles in py3
        u = pickle._Unpickler(mnist)
        u.encoding = 'latin1'
        train_set, validation_set, test_set = u.load()
        assert train_set[0].shape[0] == 50000
        
        mnist.close()

    # def test_set_datastore(self):
    #     test_path_to_config_file = clean_path("~/.test_academictorrents.config")
    #     self.assertFalse(os.path.isfile(test_path_to_config_file))
    #     at.set_datastore("/data/lisa/data/academictorrents-datastore/", test_path_to_config_file)
    #     self.assertTrue(os.path.isfile(test_path_to_config_file))
    #     os.remove(test_path_to_config_file)
    #
    # def test_empty_url(self):
    #     path = at.get("4d563087fb327739d7ec9ee9a0d32c4cb8b0355e", use_timestamp=False)
    #     self.assertTrue(os.path.isfile(path))

if __name__ == '__main__':
    unittest.main()
