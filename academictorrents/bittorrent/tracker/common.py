class TrackerResponse(object):
    def __init__(self, peers, request_interval):
        self.peers = peers
        self.request_interval = request_interval

class TrackerFailure(Exception):
    pass
