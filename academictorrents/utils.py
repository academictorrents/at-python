import hashlib
import os
import json
import datetime


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
    return "/tmp/torrent_timestamps.json"


def get_datastore(datastore="", config_filename="~/.academictorrents.config"):
    if not datastore:
        with open(clean_path(config_filename), "w+") as f:
            return json.loads(f).get("datastore", os.getcwd() + "/datastore/")
    return clean_path(datastore)

def clean_path(path=None):
    if path.startswith("~"):
        return os.path.expanduser(path) + "/"
    else:
        return os.path.abspath(path) + "/"


def write_timestamp(at_hash):
    filename = get_timestamp_filename()
    with open(filename, 'w+') as f:
        try:
            timestamps = json.loads(f.read())
        except ValueError:
            timestamps = {}
        timestamps[at_hash] = int(datetime.datetime.now().strftime("%s"))
        json.dump(timestamps, f)


def read_timestamp(at_hash):
    filename = get_timestamp_filename()
    try:
        with open(filename) as f:
            return json.load(f).get(at_hash, 0)
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


def filenames_present(torrent):
    return torrent.contents['info']['name'] in os.listdir(torrent.datastore)
