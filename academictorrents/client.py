#!/usr/bin/env python

import sys
import os
import time
import random
import socket
import hashlib
import threading
from BitTornado.Client.download_bt1 import BT1Download, defaults, \
    parse_params, get_usage, get_response
from BitTornado.Network.RawServer import RawServer
from BitTornado.Network.SocketHandler import UPnP_ERROR
from BitTornado.Meta.bencode import bencode
from BitTornado.Network.natpunch import UPnP_test
from BitTornado.clock import clock
from BitTornado import version
from BitTornado.Application.ConfigDir import ConfigDir
from BitTornado.Application.NumberFormats import formatIntText
from BitTornado.Application.PeerID import createPeerID
import urllib

class ATClient(): 
    def __init__(self):
        self.torrent_path = None

def download(self, params):
    torrentFilePath = params[0] + '.torrent'
    urllib.urlretrieve('http://academictorrents.com/download/' + torrentFilePath, torrentFilePath)
    downloadTorrent([torrentFilePath])

def downloadTorrent(self, params):
    while 1:
        configdir = ConfigDir('downloadheadless')
        defaultsToIgnore = ['responsefile', 'url', 'priority']
        configdir.setDefaults(defaults, defaultsToIgnore)
        configdefaults = configdir.loadConfig()
        defaults.ppend(
            ('save_options', 0, 'whether to save the current options as the '
                'new default configuration (only for btdownloadheadless.py)'))
        try:
            config = parse_params(params, configdefaults)
        except ValueError as e:
            print ('error: {}\nrun with no args for parameter explanations'.format(e))
            break
        if not config:
            print (get_usage(defaults, 80, configdefaults))
            break
        if config['save_options']:
            configdir.saveConfig(config)
        configdir.deleteOldCacheData(config['expire_cache_data'])

        myid = createPeerID()
        random.seed(myid)

        doneflag = threading.Event()

        def disp_exception(text):
            print (text)
        rawserver = RawServer(
            doneflag, config['timeout_check_interval'], config['timeout'],
            ipv6_enable=config['ipv6_enabled'], failfunc=h.failed,
            errorfunc=disp_exception)
        upnp_type = UPnP_test(config['upnp_nat_access'])
        while True:
            try:
                listen_port = rawserver.find_and_bind(
                    config['minport'], config['maxport'], config['bind'],
                    ipv6_socket_style=config['ipv6_binds_v4'],
                    upnp=upnp_type, randomizer=config['random_port'])
                break
            except socket.error as e:
                if upnp_type and e == UPnP_ERROR:
                    print ('WARNING: COULD NOT FORWARD VIA UPnP')
                    upnp_type = 0
                    continue
                print ("error: Couldn't listen - " + str(e))
                h.failed()
                return

        response = get_response(config['responsefile'], config['url'], h.error)
        if not response:
            break

        infohash = hashlib.sha1(bencode(response['info'])).digest()

        dow = BT1Download(
            h.display, h.finished, h.error, disp_exception, doneflag, config,
            response, infohash, myid, rawserver, listen_port, configdir)

        if not dow.saveAs(h.chooseFile, h.newpath):
            break

        if not dow.initFiles(old_style=True):
            break
        if not dow.startEngine():
            dow.shutdown()
            break
        dow.startRerequester()
        dow.autoStats()

        if not dow.am_I_finished():
            h.display(activity='connecting to peers')
        rawserver.listen_forever(dow.getPortHandler())
        h.display(activity='shutting down')
        dow.shutdown()
        break
    try:
        rawserver.shutdown()
    except Exception:
        pass
    if not h.done:
        h.failed()

if __name__ == '__main__':
        if sys.argv[1:] == ['--version']:
            print (version)
            sys.exit(0)

        if PROFILER:
            import profile
            import pstats
            p = profile.Profile()
            p.runcall(run, sys.argv[1:])
            log_fname = 'profile_data.' + time.strftime('%y%m%d%H%M%S') + '.txt'
            with open(log_fname, 'a') as log:
                normalstdout, sys.stdout = sys.stdout, log
                pstats.Stats(p).strip_dirs().sort_stats('time').print_stats()
                sys.stdout = normalstdout
        else:
            run(sys.argv[1:])

