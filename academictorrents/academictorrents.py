import logging
import json
from .PieceManager import PieceManager
from .sources import load_torrent
from .DHT import DHT
from .Client import Client
from .utils import read_timestamp, timestamp_is_within_30_days, filenames_present, write_timestamp, clean_path

logger = logging.getLogger("academictorrents")


def _enable_logs():
    logger.setLevel(logging.INFO)
    if not any(not isinstance(h, logging.NullHandler) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
        logger.addHandler(handler)


def get(at_hash, datastore="", urls=[], showlogs=False, use_timestamp=True, stall_timeout=600,
        dht=True, metadata_timeout=120):
    """Download a torrent and return the path to the data.

    at_hash: an info hash (hex or base32), a magnet link, a path to a local
        .torrent file, or an http(s) URL of a .torrent file. Hashes not on
        academictorrents.com are looked up from peers via the DHT and
        public trackers.
    urls: extra web seed URLs.
    stall_timeout: raise DownloadStalled if no piece completes for this many
        seconds (None or 0 waits forever).
    dht: use the Mainline DHT to find peers (never for private torrents).
    metadata_timeout: seconds to spend fetching a torrent's metadata from peers.
    """
    if showlogs:
        _enable_logs()

    if not datastore:
        datastore = "~/.academictorrents-datastore"

    dht_node = []

    def get_dht():
        if dht and not dht_node:
            try:
                dht_node.append(DHT())
            except OSError as e:
                logger.info("DHT unavailable: %s", e)
                dht_node.append(None)
        return dht_node[0] if dht_node else None

    try:
        torrent = load_torrent(at_hash, datastore, get_dht=get_dht, metadata_timeout=metadata_timeout)
        torrent.add_web_seeds(urls)
        path = torrent.datastore + torrent.contents['info']['name']

        # Check timestamp
        timestamp = read_timestamp(torrent.hash)
        if timestamp_is_within_30_days(timestamp) and filenames_present(torrent) and use_timestamp:
            print("File verified recently. Assumed still correct. Set use_timestamp=False to check again.")
            return path

        # Check if downloaded and finished
        piece_manager = PieceManager(torrent)
        try:
            piece_manager.check_disk_pieces()
            if piece_manager.finished():
                print("Found dataset at " + path)
            else:
                print("Downloading to " + path)
                piece_manager.preallocate()
                Client(torrent, piece_manager.check_finished_pieces(), piece_manager,
                       stall_timeout=stall_timeout,
                       dht=None if torrent.private else get_dht()).start()
            piece_manager.save_resume()
        finally:
            piece_manager.close()
    finally:
        for node in dht_node:
            if node is not None:
                node.close()

    if use_timestamp:
        write_timestamp(torrent.hash)
    return path


def set_datastore(datastore, path_to_config_file="~/.academictorrents.config"):
    with open(clean_path(path_to_config_file), "w+") as f:
        json.dump({"datastore": datastore}, f)
