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

    def test_urls(self):
        path = at.get("4e9022e7abc519733bf81a4fa353165633c371f1", urls=["https://s3.amazonaws.com/mila-genomics/testfile0.rtf"])
        assert(path)

if __name__ == '__main__':
    unittest.main()
