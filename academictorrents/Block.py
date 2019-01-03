import time
from collections import defaultdict

class Block(object):
    def __init__(self, size, time=time.time(), status="Free", data=None):
        self.size = size
        self.status = status
        self.data = defaultdict(list)
        self.time = time

    def set_pending(self):
        self.status = "Pending"
        self.time = int(time.time())

    def reset_pending(self):
        if(int(time.time()) - self.time) > 8 and self.status == "Pending":
            self.status = "Free"
            self.time = 0
