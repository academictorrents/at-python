import logging
from .academictorrents import get, set_datastore
from .Client import DownloadStalled
from .cli import cli
from .version import __version__

logging.getLogger(__name__).addHandler(logging.NullHandler())
