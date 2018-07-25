__author__ = 'martin weiss, alexis gallepe'

import hashlib
import os
import json
import datetime


def convertBytesToDecimal(headerBytes):
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
    return os.getcwd() + "/torrent_timestamps.json"


def get_torrent_dir(datastore=None, name=None):
    if not datastore:
        datastore = os.getcwd() + "/datastore/"
    elif datastore == "." or datastore == "./":
        datastore = "./"
    elif datastore[-1] != "/":
        datastore = datastore + "/"
    elif datastore[0] != "/":
        datastore = os.getcwd() + "/" + datastore
    if not name:
        return datastore
    if isinstance(name, str):
        name = name.strip("/")
    return datastore + name + '/'


def write_timestamp(hash):
    filename = get_timestamp_filename()
    with open(filename, 'w+') as f:
        try:
            timestamps = json.loads(f.read())
        except ValueError:
            timestamps = {}
        timestamps[hash] = int(datetime.datetime.now().strftime("%s"))
        json.dump(timestamps, f)


def read_timestamp(hash):
    filename = get_timestamp_filename()
    try:
        with open(filename) as f:
            return json.load(f).get('hash', 0)
    except Exception:
        return 0


def timestamp_is_within_30_days(timestamp):
    seconds_in_a_month = 86400 * 30
    if timestamp > int(datetime.datetime.now().strftime("%s")) - seconds_in_a_month:
        return True
    return False


def timestamp_is_within_10_seconds(timestamp):
    ten_seconds = 10
    if timestamp > int(datetime.datetime.now().strftime("%s")) - ten_seconds:
        return True
    return False


def filenames_present(torrent, datastore):
    name = torrent['info']['name']
    return name in os.listdir(datastore)
