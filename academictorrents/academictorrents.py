import logging
import json
from .PieceManager import PieceManager
from .Torrent import Torrent
from .Client import Client
from .utils import read_timestamp, timestamp_is_within_30_days, filenames_present, write_timestamp, clean_path

logger = logging.getLogger("academictorrents")


def _enable_logs():
    logger.setLevel(logging.INFO)
    if not any(not isinstance(h, logging.NullHandler) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s"))
        logger.addHandler(handler)


def get(at_hash, datastore="", urls=[], showlogs=False, use_timestamp=True, stall_timeout=600):
    """Download a torrent by hash and return the path to the data.

    stall_timeout: raise DownloadStalled if no piece completes for this many
    seconds (None or 0 waits forever).
    """
    if showlogs:
        _enable_logs()

    if not datastore:
        datastore = "~/.academictorrents-datastore"

    torrent = Torrent(at_hash, datastore)
    torrent.add_web_seeds(urls)
    path = torrent.datastore + torrent.contents['info']['name']

    # Check timestamp
    timestamp = read_timestamp(at_hash)
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
                   stall_timeout=stall_timeout).start()
        piece_manager.save_resume()
    finally:
        piece_manager.close()

    if use_timestamp:
        write_timestamp(at_hash)
    return path


def set_datastore(datastore, path_to_config_file="~/.academictorrents.config"):
    with open(clean_path(path_to_config_file), "w+") as f:
        json.dump({"datastore": datastore}, f)
