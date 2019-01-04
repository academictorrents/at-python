import time
from queue import Queue
from . import progress_bar
from .PeerSeeker import PeerSeeker
from .PeerManager import PeerManager
from .Tracker import Tracker


class Client(object):
    @classmethod
    def __init__(self, torrent, downloaded_amount, pieces_manager):
        self.http_peers = []

        self.torrent = torrent
        self.downloaded_amount = downloaded_amount
        self.start_time = time.time()
        self.new_peers_queue = Queue()

        self.pieces_manager = pieces_manager
        self.peer_manager = PeerManager(self.torrent, self.pieces_manager)
        self.peer_seeker = PeerSeeker(self.new_peers_queue, self.torrent, self.peer_manager)
        self.tracker = Tracker(torrent, self.new_peers_queue, downloaded_amount)

        self.tracker.start()
        self.peer_manager.start()
        self.peer_seeker.start()
        self.pieces_manager.start()

    def start(self):
        rate = 10000000
        while not self.pieces_manager.finished():
            self.pieces_manager.reset_pending()
            pieces_by_file = self.pieces_manager.pieces_by_file()
            #self.peer_manager.make_requests(pieces_by_file)
            self.peer_manager.enqueue_http_requests(pieces_by_file)

            # Record progress
            cur_downloaded = self.pieces_manager.check_finished_pieces()
            rate = (cur_downloaded - self.downloaded_amount)/(time.time()-self.start_time)/1000. # rate in KBps
            progress_bar.print_progress(cur_downloaded, self.torrent.total_length, "BT:{}, Web:{}".format(len(self.peer_manager.peers), len(self.peer_manager.http_peers)), "({0:.2f}kB/s)".format(rate) + " cur_downloaded:" + str(cur_downloaded))
            self.tracker.set_downloaded(cur_downloaded)
            time.sleep(0.1)

        print("\n Complete. Downloaded " + str(cur_downloaded/1000000.) + " MB in " + str(time.time()-self.start_time) + " seconds.")
        self.tracker.request_stop()
        self.peer_seeker.request_stop()
        self.peer_manager.request_stop()
        self.pieces_manager.request_stop()

        return self.torrent.torrent_file['info']['name']
