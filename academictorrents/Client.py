import time
import logging
import threading
from queue import Queue
from tqdm.auto import tqdm
from .PeerSeeker import PeerSeeker
from .PeerManager import PeerManager
from .Tracker import Tracker
from .HttpPeer import HttpPeer
from .WebSeedManager import WebSeedManager

logger = logging.getLogger(__name__)

WORKERS_PER_WEB_SEED = 5
RESUME_SAVE_INTERVAL = 30


class DownloadStalled(Exception):
    pass


class Client(object):
    def __init__(self, torrent, downloaded_amount, piece_manager, stall_timeout=600):
        self.torrent = torrent
        self.downloaded_amount = downloaded_amount
        self.piece_manager = piece_manager
        self.stall_timeout = stall_timeout
        self.stop_event = threading.Event()
        self.new_peers_queue = Queue()
        self.request_queue = Queue()

        self.http_peers = [HttpPeer(url, torrent) for url in torrent.urls]
        self.peer_manager = PeerManager(piece_manager, self.stop_event)
        self.peer_seeker = PeerSeeker(self.new_peers_queue, torrent, self.peer_manager, self.stop_event)
        self.tracker = Tracker(torrent, self.new_peers_queue, downloaded_amount, self.stop_event)
        self.web_seed_managers = [WebSeedManager(self.request_queue, piece_manager, self.stop_event)
                                  for _ in range(len(self.http_peers) * WORKERS_PER_WEB_SEED)]
        self.threads = [self.tracker, self.peer_manager, self.peer_seeker] + self.web_seed_managers

    def choose_seed(self, relpath):
        now = time.time()
        for seed in self.http_peers:
            if seed.can_serve(relpath, now):
                return seed
        return None

    def enqueue_http_requests(self):
        if not self.http_peers:
            return
        free = len(self.web_seed_managers) - self.request_queue.unfinished_tasks
        if free <= 0:
            return
        for job in self.piece_manager.next_web_jobs(self.choose_seed, free):
            self.request_queue.put(job)

    def start(self):
        for t in self.threads:
            t.start()
        pm = self.piece_manager
        last_progress = pm.check_finished_pieces()
        last_progress_time = time.time()
        last_save = last_status = time.time()
        bar = tqdm(total=self.torrent.total_length, initial=last_progress, unit='B',
                   unit_scale=True, unit_divisor=1024)
        try:
            while not pm.finished():
                self.enqueue_http_requests()
                now = time.time()
                done = pm.check_finished_pieces()
                if done != last_progress:
                    bar.update(done - last_progress)
                    last_progress, last_progress_time = done, now
                    self.tracker.set_downloaded(done)
                elif self.stall_timeout and now - last_progress_time > self.stall_timeout:
                    raise DownloadStalled(
                        "no progress for {}s ({} of {} bytes; {} web seeds, {} peers, {} hash failures)".format(
                            self.stall_timeout, done, self.torrent.total_length, len(self.http_peers),
                            len(self.peer_manager.peers), pm.hash_failures))
                if now - last_status >= 1:  # redraw even when no piece completed
                    bar.set_postfix_str(self.status(), refresh=True)
                    last_status = now
                if now - last_save > RESUME_SAVE_INTERVAL:
                    pm.save_resume()
                    last_save = now
                self.stop_event.wait(0.1)
            bar.update(pm.check_finished_pieces() - last_progress)
        finally:
            bar.close()
            self.stop()
            pm.save_resume()
        print("Download Complete!")

    def status(self):
        pm = self.piece_manager
        parts = ["bt=%d" % len(self.peer_manager.peers), "web=%d" % len(self.http_peers),
                 "recv=%.1fMB" % (pm.received_bytes / 1e6)]
        if pm.hash_failures:
            parts.append("hashfail=%d" % pm.hash_failures)
        if not pm.received_bytes:
            parts.append("connecting")
        return " ".join(parts)

    def stop(self):
        self.stop_event.set()
        for t in self.threads:
            if t.is_alive():
                t.join(timeout=5)
        try:
            self.tracker.set_downloaded(self.piece_manager.check_finished_pieces())
            self.tracker.stop_message()
        except Exception as e:
            logger.info("tracker stop message failed: %s", e)
        for seed in self.http_peers:
            seed.close()
