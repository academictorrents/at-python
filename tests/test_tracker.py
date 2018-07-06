import academictorrents as at
import unittest
import os
import shutil
import os
import sys, os, time
from queue import Queue
from academictorrents import Torrent, Tracker


class TrackerTestSuite(unittest.TestCase):
    """Test cases on the tracker.py file."""

    def test_stop_message_already_downloaded(self):
        torrent = Torrent.Torrent("55a8925a8d546b9ca47d309ab438b91f7959e77f", "./tests/")
        q = Queue()
        tracker = Tracker.Tracker(torrent, q)
        downloaded = 0
        remaining = 0
        self.assertTrue(tracker.stop_message(downloaded, remaining))

    def test_stop_message_stopped(self):
        torrent = Torrent.Torrent("55a8925a8d546b9ca47d309ab438b91f7959e77f", "./tests/")
        q = Queue()
        tracker = Tracker.Tracker(torrent, q)
        downloaded = 23811085
        remaining = 23811086
        params, resp = tracker.stop_message(downloaded, remaining)
        self.assertTrue(resp.status_code == 200)
        self.assertTrue(params['event'] == 'stopped')

    def test_stop_message_finished(self):
        torrent = Torrent.Torrent("55a8925a8d546b9ca47d309ab438b91f7959e77f", "./tests/")
        q = Queue()
        tracker = Tracker.Tracker(torrent, q)
        downloaded = 47622171
        remaining = 0
        params, resp = tracker.stop_message(downloaded, remaining)
        self.assertTrue(resp.status_code == 200)
        self.assertTrue(params['event'] == 'finished')
