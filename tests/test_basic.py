import unittest

from .context import academictorrents

class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""

    def test_absolute_truth_and_meaning(self):
        assert True

    def test_get_torrent(self):
        
        filename = academictorrents.get('d984f67af9917b214cd8b6048ab5624c7df6a07a') # test torrent
        
        self.assertEqual(filename, "test_folder") # just test if the folder name is correct

if __name__ == '__main__':
    unittest.main()
