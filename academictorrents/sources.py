"""Turn what the user passed to get() into a Torrent.

Accepted: a 40-char hex or 32-char base32 info hash, a magnet link, a path to
a local .torrent file, or an http(s) URL of a .torrent file. Hashes and
magnet links are looked up in the local cache, then on academictorrents.com,
then fetched from peers found through the DHT and public trackers.
"""
import os
import re
import queue
import base64
import logging
import tempfile
import threading
from types import SimpleNamespace
from urllib.parse import urlparse, parse_qs
import requests
from . import utils
from . import bencoding
from .Torrent import Torrent, fetch_from_academictorrents
from .Tracker import Tracker
from .Metadata import fetch_metadata

logger = logging.getLogger(__name__)

# Used only to find peers for metadata when a hash isn't on academictorrents.com.
PUBLIC_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://exodus.desync.com:6969/announce",
]


class TorrentNotFound(Exception):
    pass


def parse_hash(text):
    text = text.strip()
    if re.fullmatch(r"[0-9a-fA-F]{40}", text):
        return text.lower()
    if re.fullmatch(r"[A-Za-z2-7]{32}", text):
        return base64.b32decode(text.upper()).hex()
    return None


def parse_magnet(uri):
    q = parse_qs(urlparse(uri).query)
    info_hash = None
    for xt in q.get("xt", []):
        if xt.lower().startswith("urn:btih:"):
            info_hash = parse_hash(xt[9:])
    if not info_hash:
        raise ValueError("magnet link has no BitTorrent info hash: " + uri)
    return SimpleNamespace(info_hash=info_hash, trackers=q.get("tr", []),
                           web_seeds=q.get("ws", []), name=(q.get("dn") or [None])[0])


def cache_path(info_hash):
    return os.path.join(tempfile.gettempdir(), info_hash + ".torrent")


def write_cache(info_hash, contents):
    path = cache_path(info_hash)
    tmp = path + ".part"
    try:
        with open(tmp, "wb") as f:
            f.write(contents)
        os.replace(tmp, path)
    except OSError as e:
        logger.info("could not cache torrent: %s", e)


def download_torrent_file(url):
    resp = requests.get(url, headers=utils.HEADERS, timeout=30)
    resp.raise_for_status()
    bencoding.info_bytes(resp.content)  # must be a real .torrent, not an error page
    return resp.content


def torrent_from_metadata(info_raw, trackers):
    meta = b"d"
    if trackers:
        meta += bencoding.encode("announce") + bencoding.encode(trackers[0])
        meta += bencoding.encode("announce-list") + bencoding.encode([[t] for t in trackers])
    return meta + bencoding.encode("info") + info_raw + b"e"


def find_metadata(info_hash, trackers, get_dht, timeout):
    """Find peers via DHT and trackers, then fetch the info dict from them."""
    raw_hash = bytes.fromhex(info_hash)
    peer_id = os.urandom(20)
    peers = queue.Queue()
    stop = threading.Event()
    print("Looking up metadata for %s from peers..." % info_hash)

    tracker_urls = list(dict.fromkeys(list(trackers) + PUBLIC_TRACKERS))
    if tracker_urls:
        stub = SimpleNamespace(info_hash=raw_hash, peer_id=peer_id, total_length=1 << 30,
                               trackers=[[t] for t in tracker_urls])
        tracker = Tracker(stub, peers, 0, stop)
        threading.Thread(target=tracker.announce_all, args=("started",), daemon=True).start()

    dht = get_dht()
    if dht is not None:
        threading.Thread(target=dht.get_peers, args=(raw_hash,),
                         kwargs={"timeout": timeout, "on_peer": peers.put, "stop_event": stop},
                         daemon=True).start()
    try:
        return fetch_metadata(raw_hash, peers, peer_id, timeout=timeout)
    finally:
        stop.set()


def load_torrent(source, datastore, get_dht=lambda: None, metadata_timeout=120):
    """Resolve source to a Torrent; see the module docstring for what is accepted."""
    source = str(source).strip()
    extra_trackers, extra_seeds = [], []

    if source.startswith("magnet:"):
        magnet = parse_magnet(source)
        info_hash, extra_trackers, extra_seeds = magnet.info_hash, magnet.trackers, magnet.web_seeds
    elif re.match(r"https?://", source, re.I):
        return Torrent(datastore=datastore, contents=download_torrent_file(source))
    elif parse_hash(source) and not os.path.isfile(source):
        info_hash = parse_hash(source)
    else:
        path = os.path.expanduser(source)
        if not os.path.isfile(path):
            raise TorrentNotFound("not an info hash, magnet link, URL or existing file: " + source)
        with open(path, "rb") as f:
            return Torrent(datastore=datastore, contents=f.read())

    contents = None
    try:
        with open(cache_path(info_hash), "rb") as f:
            contents = f.read()
        bencoding.info_bytes(contents)
    except Exception:
        contents = None
    if contents is None:
        try:
            contents = fetch_from_academictorrents(info_hash, cache_path(info_hash))
        except Exception as e:
            logger.info("academictorrents.com does not have %s: %s", info_hash, e)
    if contents is None:
        info_raw = find_metadata(info_hash, extra_trackers, get_dht, metadata_timeout)
        if info_raw is None:
            raise TorrentNotFound("could not find %s on academictorrents.com, in the cache, or from peers "
                                  "within %ss" % (info_hash, metadata_timeout))
        contents = torrent_from_metadata(info_raw, extra_trackers)
        write_cache(info_hash, contents)

    torrent = Torrent(info_hash, datastore, contents=contents)
    torrent.add_trackers(extra_trackers)
    torrent.add_web_seeds(extra_seeds)
    return torrent
