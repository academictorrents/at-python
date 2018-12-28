import academictorrents as at
import unittest
import os
import shutil
import time
import sys


class HttpDownloadTestSuite(unittest.TestCase):
    """Test cases on the academictorrents.py file."""

    def test_get_file_http(self):
        filename = at.get('55a8925a8d546b9ca47d309ab438b91f7959e77f')
        self.assertTrue(os.path.isfile(filename))

if __name__ == '__main__':
    unittest.main()
