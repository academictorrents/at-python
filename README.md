# Academic Torrents Pure Python API

![Build Status](https://github.com/AcademicTorrents/at-python/actions/workflows/tests.yml/badge.svg)

This repository is an implementation of the BitTorrent protocol written in Python and downloadable as a `pip` module. You can download datasets from AcademicTorrents.com in two lines of code in any Python script:
```python
import academictorrents as at
path_of_giant_dataset = at.get("323a0048d87ca79b68f12a6350a57776b6a3b7fb") # Download mnist dataset
```

You can also use the `at-get` command to download datasets directly from your terminal:

```bash
at-get 323a0048d87ca79b68f12a6350a57776b6a3b7fb -o ~/Downloads
```

### Other ways to point at a torrent

`at.get` (and `at-get`) work with any BitTorrent info hash, not just ones on academictorrents.com; a bare hash is treated like a magnet link. They also accept a magnet link, a path to a local `.torrent` file, or a URL of a `.torrent` file:

```python
at.get("08ada5a7a6183aae1e09d831df6748d566095a10")  # any info hash (this one is Sintel)
at.get("magnet:?xt=urn:btih:323a0048d87ca79b68f12a6350a57776b6a3b7fb")
at.get("~/Downloads/dataset.torrent")
at.get("https://example.org/dataset.torrent")
```

If an info hash isn't on academictorrents.com, its metadata is fetched from peers found through the BitTorrent DHT and public trackers (`metadata_timeout`, default 120 s). The DHT is also used to find peers during every download, except for private torrents. Disable it with `at.get(..., dht=False)` or `at-get --no-dht`.

## For people who want to download datasets

We are compatible with Python 3.10 and newer.

To install:
`pip install academictorrents`

This package works with the academictorrents tracker. You can add a hash from [academictorrents.com](academictorrents.com) for your torrent, and download datasets into your project.

### Python example

Here is a little example (it is implemented in `examples/basic_test.py` in case you want to play with our source code):
```python
# Import the library
import academictorrents as at

# Download the data (or verify existing data)
filename = at.get("323a0048d87ca79b68f12a6350a57776b6a3b7fb")

# Then work with the data
import pickle, gzip
import sys, os, time

mnist = gzip.open(filename, 'rb')
train_set, valid_set, test_set = pickle.load(mnist, encoding='latin1')
mnist.close()
```

### Command line options

Run `at-get --help` in the environment where `academictorrents` is installed to get more information about the CLI:

```bash
usage: at-get [-h] [-o DATASTORE] [-v] hash

Academic Torrents simple command line tool

positional arguments:
  hash                  Info hash, magnet link, .torrent file path or .torrent
                        URL to download

optional arguments:
  -h, --help            show this help message and exit
  -o DATASTORE, --datastore DATASTORE
                        Location where to place the files
  -v, --verbose         Show logs
  --no-dht              Don't use the DHT to find peers

```

## For Contributors to the AcademicTorrents Python client
### Introduction
We use Github issues and pull requests to manage development of this repository. The following is a guide for setting up the codebase to contribute PRs or try to debug issues.

### Installation
Getting setup to work on this client is pretty easy. First, install the source code, then install the dependencies with `pip`:

```
git clone https://github.com/AcademicTorrents/at-python.git
cd at-python
pip install -r requirements.txt
pip install -e .
```

or more direct:

```
python -m pip install git+https://github.com/AcademicTorrents/at-python.git
```

Done!

### Testing
Run `pytest tests/` for the offline suite: it downloads generated torrents from a local HTTP web seed, so it needs no internet. Tests that use live trackers and web seeds are marked `network` and skipped by default; run them with `pytest tests/ --network`. If you want to just run one little download, use `python examples/basic_test.py` (example code above).

### Architecture
The `academictorrents` module only has one "public" function, `.get`. This function checks for the torrent data on the filesystem. If it is not present, then it initiates a `Client` to download the data for us.

`sources.load_torrent` turns a hash, magnet link, file or URL into a `Torrent`, falling back to `DHT` + `Metadata` (BEP 9/10) to fetch metadata from peers. `Client` runs the main loop and owns the worker threads: `Tracker` (HTTP and UDP announces), `DHTPeerFinder` (periodic DHT lookups), `PeerSeeker` (connects to new peers), `PeerManager` (reads, parses and requests on all BitTorrent sockets) and a pool of `WebSeedManager` threads that stream HTTP range requests from `HttpPeer` web seeds. All threads are daemons; `get()` raises `DownloadStalled` if no piece completes for `stall_timeout` seconds.

`PieceManager` is the thread-safe store of piece state. A `Piece` only holds a buffer while it is in flight; once its SHA-1 matches it is written to disk through `Storage` (cached file handles) and dropped, and the piece's bit is set in the bitfield. A resume file (`.<name>.at-resume.json` in the datastore) records the bitfield plus each file's size and mtime, so a restart only re-hashes pieces whose files changed, using a thread pool.
