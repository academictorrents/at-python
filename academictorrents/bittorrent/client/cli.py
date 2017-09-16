#!/usr/bin/env python

import sys
import logging

from tornado.log import enable_pretty_logging
from tornado.ioloop import IOLoop
from tornado.options import define, options, parse_command_line, print_help

from bittorrent.p2p import Server
from bittorrent.torrent import Torrent
from bittorrent.storage import DiskStorage

from bittorrent.utils import peer_id, gen_debuggable

define(
    name='torrent',
    type=str,
    help='torrent file to download'
)

define(
    name='path',
    type=str,
    default='downloads',
    help='download directory'
)

define(
    name='port',
    type=int,
    default=6881,
    help='port on which we listen for connections'
)

define(
    name='max_peers',
    type=int,
    default=20,
    help='maximum number of connected peers'
)

define(
    name='scrape_trackers',
    type=bool,
    default=True,
    help='scrape trackers for peers'
)

define(
    name='peer_ip',
    help='manually connect to this peer\'s address'
)

define(
    name='peer_port',
    type=int,
    help='manually connect to this peer\'s port'
)

if __name__ == '__main__':
    parse_command_line()
    enable_pretty_logging()

    if not options.torrent:
        logging.error('Required argument <torrent> not provided')

        print
        print_help()

        sys.exit(1)


    torrent = Torrent(options.torrent)

    server = Server(
        torrent=torrent,
        download_path=options.path,
        storage_class=DiskStorage,
        peer_id=peer_id(),
        max_peers=options.max_peers
    )
    server.listen(options.port)
    server.start()

    if options.peer_ip and options.peer_port:
        server.connect(Peer(options.peer_ip, options.peer_port))

    IOLoop.instance().start()
