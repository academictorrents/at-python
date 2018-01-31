import unittest

from .context import academictorrents


class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""

    def test_absolute_truth_and_meaning(self):
        assert True

    def test_get_torrent(self):
        filename = academictorrents.get('968a3ff5e4182cdecd239980ecfd257a37451003')#'d984f67af9917b214cd8b6048ab5624c7df6a07a') # test torrent
        
        import os
        files = os.listdir(filename) #assert is a folder

        self.assertEqual(files == ['images', 'README']) #assert contains the correct file names
        
        
    def test_get_torrent_to_datastore(self):
        
        academictorrents.set_datastore("/tmp/")
        filename = academictorrents.get('968a3ff5e4182cdecd239980ecfd257a37451003') # d984f67af9917b214cd8b6048ab5624c7df6a07a test torrent
        
        self.assertTrue(filename.startswith("/tmp/")) # make sure the data was stored where specified

if __name__ == '__main__':
    unittest.main()
