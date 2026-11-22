import hashlib
import os
import json
import datetime
import calendar
import time
import requests
from .version import __version__

# Identify as the AT client. Never include "Mozilla": we are not a browser, and
# academictorrents.com rejects some generic library agents (e.g. Python-urllib).
USER_AGENT = "AT-Client/" + __version__ + " " + requests.utils.default_user_agent()
HEADERS = {'user-agent': USER_AGENT}


class Bitfield(object):
    """Fixed-size bit array, MSB-first like the BitTorrent wire format."""

    def __init__(self, length=0, data=None):
        if data is None:
            data = bytes((length + 7) // 8)
        self._bytes = bytearray(data)
        self._length = length if length else len(self._bytes) * 8

    @classmethod
    def from_bytes(cls, data):
        return cls(len(data) * 8, data)

    def __len__(self):
        return self._length

    def __getitem__(self, index):
        if not 0 <= index < self._length:
            raise IndexError("bitfield index out of range")
        return bool(self._bytes[index >> 3] & (0x80 >> (index & 7)))

    def __setitem__(self, index, value):
        if not 0 <= index < self._length:
            raise IndexError("bitfield index out of range")
        if value:
            self._bytes[index >> 3] |= 0x80 >> (index & 7)
        else:
            self._bytes[index >> 3] &= ~(0x80 >> (index & 7)) & 0xFF

    def __iter__(self):
        return (self[i] for i in range(self._length))

    def count(self):
        """Number of set bits (fast, unlike sum())."""
        full, rem = divmod(self._length, 8)
        n = sum(bin(b).count("1") for b in self._bytes[:full])
        if rem:
            n += bin(self._bytes[full] & (0xFF << (8 - rem)) & 0xFF).count("1")
        return n

    def tobytes(self):
        return bytes(self._bytes)


def convert_bytes_to_decimal(headerBytes):
    size = 0
    power = len(headerBytes) - 1
    for ch in headerBytes:
        if isinstance(ch, int):
            size += ch * 256 ** power
        else:
            size += int(ord(ch)) * 256 ** power
        power -= 1
    return size


def sha1_hash(string):
    """Return 20-byte sha1 hash of string."""
    return hashlib.sha1(string).digest()


def get_timestamp_filename():
    return clean_path("~/.academictorrents_timestamps.json")


def get_datastore(datastore="", path_to_config_file="~/.academictorrents.config"):
    if datastore:
        datastore = clean_path(datastore)
    else:
        datastore = json.loads(open(clean_path(path_to_config_file)).read()).get("datastore", os.getcwd() + "/datastore/")
    if datastore[-1] != "/":
        datastore = datastore + "/"
    return datastore

def clean_path(path=None):
    if path.startswith("~"):
        return os.path.expanduser(path)
    else:
        return os.path.abspath(path)

def write_timestamp(at_hash):
    filename = get_timestamp_filename()
    try:
        f = open(filename, 'r')
        timestamps = json.load(f)
        f.close()
    except Exception:
        timestamps = {}
    timestamps[at_hash] = int(datetime.datetime.timestamp(datetime.datetime.now()))
    f = open(filename, 'w')
    json.dump(timestamps, f)

def read_timestamp(at_hash):
    filename = get_timestamp_filename()
    try:
        f = open(filename, 'r')
        timestamp = json.load(f).get(at_hash, 0)
        f.close()
    except Exception:
        timestamp = 0
    return timestamp


def timestamp_is_within_30_days(timestamp):
    seconds_in_a_month = 86400 * 30
    if timestamp > int(calendar.timegm(time.gmtime())) - seconds_in_a_month:
        return True
    return False


def timestamp_is_within_10_seconds(timestamp):
    ten_seconds = 10
    if timestamp > int(calendar.timegm(time.gmtime())) - ten_seconds:
        return True
    return False


def filenames_present(torrent):
    return torrent.contents['info']['name'] in os.listdir(torrent.datastore)
