# Academic Torrents Python API

[![Build Status](https://travis-ci.org/AcademicTorrents/at-python.svg?branch=master)](https://travis-ci.org/AcademicTorrents/at-python)
[![codecov](https://codecov.io/gh/AcademicTorrents/at-python/branch/master/graph/badge.svg)](https://codecov.io/gh/AcademicTorrents/at-python)

This repository is an implementation of the BitTorrent protocol written in Python and downloadable as a `pip` module. You can download datasets from AcademicTorrents.com in two lines of code in any Python script:
```python
import academictorrents as at
path_of_giant_dataset = at.get("323a0048d87ca79b68f12a6350a57776b6a3b7fb") # Download mnist dataset
```

You can also use the `at-get` command to download datasets directly from your terminal:

```bash
at-get 323a0048d87ca79b68f12a6350a57776b6a3b7fb -o ~/Downloads
```

## For people who want to download datasets

We are compatible with Python versions: 2.7, 3.4, 3.5, 3.6.

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
  hash                  Hash of the torrent to download

optional arguments:
  -h, --help            show this help message and exit
  -o DATASTORE, --datastore DATASTORE
                        Location where to place the files
  -v, --verbose         Show logs

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
```

or more direct:

```
python -m pip install git+https://github.com/AcademicTorrents/at-python.git
```

Done!

### Testing
We have a test suite that you can run with `pytest -s tests/`. These tests also run on travis after every push to github. Some of our tests are empty -- usually in parts of the codebase that have been changing quickly -- but we should continue increasing our coverage. If you want to just run one little download, use `python examples/basic_test.py` (example code above).

### Architecture
The `academictorrents` module only has one "public" function, `.get`. This function checks for the torrent data on the filesystem. If it is not present, then it initiates a `Client` to download the data for us.

`Client` is our main thread, it manages the lifecycle of our other threads including `Tracker`, `PeerManager`, `PieceManager`, and many `WebSeedManager` threads. The `Client` thread uses the `PieceManager` class (not thread) to keep track of all the pieces of data. The main thread makes socket requests to `Peer`s, and enqueues jobs to request data from `HttpPeer`s. Socket responses are handled by `PeerManager`, whereas a fleet of `WebSeedManagers` threads handles the `HttpPeer`s.
