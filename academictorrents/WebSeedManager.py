from threading import Thread
import urllib3
from . import HttpPeer
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WebSeedManager(Thread):
    def __init__(self, torrent, requestQueue, httpPeers):
        Thread.__init__(self)
        self.readBuffer = b""
        self.requestQueue = requestQueue
        self.stopRequested = False
        self.torrent = torrent
        self.httpPeers = httpPeers
        self.setDaemon(True)

    def run(self):
        while not self.stopRequested:
            httpPeer, pieces_by_file = self.requestQueue.get()
            print("request!")
            responses = httpPeer.request_ranges(pieces_by_file)
            print("response!")
            if not responses:
                continue
            codes = [response[0].status_code for response in responses.values()]
            if any(code != 206 for code in codes):
                continue
            httpPeer.publish_responses(responses, pieces_by_file)
            self.requestQueue.task_done()

    def requestStop(self):
        self.stopRequested = True
