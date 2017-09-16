import time
import struct

from collections import deque, namedtuple
from operator import attrgetter

from tornado.gen import coroutine, Return

class DataSample(object):
    def __init__(self, time, data):
        self.time = time
        self.data = data

class Peer(object):
    def __init__(self, address, port, id=None):
        self.address = address
        self.port = port
        self.id = id

        self.speeds = deque([], maxlen=60)

    def add_data_sample(self, size):
        t = int(time.time())

        if not self.speeds:
            self.speeds.append(DataSample(t, size))
            return

        difference = t - self.speeds[-1].time

        for i in range(difference, -1, -1):
            self.speeds.append(DataSample(i, 0))

        self.speeds[difference].data += size

    @property
    def average_speed(self):
        if not self.speeds:
            return 0
        else:
            return sum(sample.data for sample in self.speeds) / float(self.speeds.maxlen)

    def __hash__(self):
        return hash((self.address, self.port, self.id))

    def __repr__(self):
        return '<Peer {self.address}:{self.port}>'.format(self=self)
