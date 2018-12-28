import academictorrents as at
import unittest
import os
import shutil
import time
import sys


class HttpDownloadTestSuite(unittest.TestCase):
    """Test cases on the academictorrents.py file."""

    def test_get_file_http(self):
        filename = at.get('0a8cb3446b0de5690fee29a2c68922ff691c7f9a')
        self.assertTrue(os.path.isfile(filename))

if __name__ == '__main__':
    unittest.main()
