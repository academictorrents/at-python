from threading import Thread
import urllib3
from . import HttpPeer
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WebSeedManager(Thread):
    def __init__(self, torrent, request_queue, http_peers):
        Thread.__init__(self)
        self.request_queue = request_queue
        self.stop_requested = False
        self.torrent = torrent
        self.http_peers = http_peers
        self.setDaemon(True)

    def run(self):
        while not self.stop_requested:
            httpPeer, filename, pieces = self.request_queue.get()
            response = httpPeer.request_ranges(filename, pieces)
            if not response or response.status_code != 206:
                print("failed on " + str(response) + " for " + filename)
                continue
            print("response!")
            httpPeer.publish_responses(response, filename, pieces)
            self.request_queue.task_done()

    def request_stop(self):
        self.stop_requested = True
