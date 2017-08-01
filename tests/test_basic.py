import unittest

from .context import academictorrents


class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""

    def test_absolute_truth_and_meaning(self):
        assert True

    def test_get_torrent(self):
        self.assertEqual(academictorrents.get('f2221a292540ff3e6c85025754f775361c7cd886'), 'f2221a292540ff3e6c85025754f775361c7cd886')

if __name__ == '__main__':
    unittest.main()
