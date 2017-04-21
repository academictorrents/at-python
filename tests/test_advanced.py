from .context import academictorrents

import unittest


class AdvancedTestSuite(unittest.TestCase):
    """Advanced test cases."""

    //TODO fix this unit test
    def test_thoughts(self):
        self.assertEqual(academictorrents.get('fakeinfohash'), 'fakeinfohash')

if __name__ == '__main__':
    unittest.main()
