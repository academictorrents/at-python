import time
from queue import Queue
from . import progress_bar
from .PeerSeeker import PeerSeeker
from .PeerManager import PeerManager
from .Tracker import Tracker
from .WebSeedManager import WebSeedManager


class Client(object):
    @classmethod
    def __init__(self, torrent, downloaded_amount, piece_manager):
        self.torrent = torrent
        self.downloaded_amount = downloaded_amount
        self.start_time = time.time()
        self.new_peers_queue = Queue()
        self.request_queue = Queue()

        self.piece_manager = piece_manager
        self.peer_manager = PeerManager(self.torrent, self.piece_manager, self.request_queue)
        self.peer_seeker = PeerSeeker(self.new_peers_queue, self.torrent, self.peer_manager)
        self.tracker = Tracker(torrent, self.new_peers_queue, downloaded_amount)

        self.tracker.start()
        self.peer_manager.start()
        self.peer_seeker.start()

        self.web_seed_managers = []
        num_web_seed_managers = len(self.peer_manager.http_peers) * 5
        for i in range(num_web_seed_managers):
            t = WebSeedManager(torrent, self.request_queue, self.peer_manager.http_peers)
            t.setDaemon(True)
            t.start()
            self.web_seed_managers.append(t)

    def start(self):
        rate = 10000000
        while not self.piece_manager.finished():
            self.piece_manager.reset_pending()
            pieces_by_file = self.piece_manager.pieces_by_file()
            self.peer_manager.make_requests(pieces_by_file)
            self.peer_manager.enqueue_http_requests(pieces_by_file)

            # Record progress
            cur_downloaded = self.piece_manager.check_finished_pieces()
            rate = (cur_downloaded - self.downloaded_amount)/(time.time()-self.start_time)/1000. # rate in KBps
            progress_bar.print_progress(cur_downloaded, self.torrent.total_length, "BT:{}, Web:{}".format(len(self.peer_manager.peers), len(self.peer_manager.http_peers)), "({0:.2f}kB/s)".format(rate)) # + " Downloaded " + str(round(cur_downloaded/1000000., 2)) + "MB" )
            self.tracker.set_downloaded(cur_downloaded)
            time.sleep(0.5)

        print("\n Complete. Downloaded " + str(cur_downloaded/1000000.) + " MB in " + str(time.time()-self.start_time) + " seconds.")
        self.piece_manager = None
        self.tracker.request_stop()
        self.peer_seeker.request_stop()
        self.peer_manager.request_stop()
        for web_seed_manager in self.web_seed_managers:
            web_seed_manager.request_stop()

        return self.torrent.torrent_file['info']['name']
