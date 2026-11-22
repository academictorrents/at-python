import random
import socket
import struct
import logging
import threading
from threading import Thread
from urllib.parse import urlparse
import bencode
import requests
from . import utils

logger = logging.getLogger(__name__)

UDP_MAGIC = 0x41727101980
UDP_EVENTS = {None: 0, 'completed': 1, 'started': 2, 'stopped': 3}
ANNOUNCE_INTERVAL = 60
LISTEN_PORT = 6881


def parse_compact_peers(data):
    peers = []
    for i in range(0, len(data) - len(data) % 6, 6):
        ip = socket.inet_ntoa(data[i:i + 4])
        port = struct.unpack('!H', data[i + 4:i + 6])[0]
        peers.append((ip, port))
    return peers


class Tracker(Thread):
    def __init__(self, torrent, new_peers_queue, downloaded, stop_event=None):
        Thread.__init__(self, daemon=True)
        self.torrent = torrent
        self.new_peers_queue = new_peers_queue
        self.stop_event = stop_event or threading.Event()
        self.downloaded = downloaded
        self.started = False

    def request_stop(self):
        self.stop_event.set()

    def set_downloaded(self, size):
        self.downloaded = size

    def tracker_urls(self):
        urls = []
        for tier in self.torrent.trackers:
            for url in tier:
                if isinstance(url, bytes):
                    url = url.decode('utf-8', 'replace')
                if url and url not in urls:
                    urls.append(url)
        return urls

    def run(self):
        while not self.stop_event.is_set():
            self.announce_all(None if self.started else 'started')
            self.started = True
            self.stop_event.wait(ANNOUNCE_INTERVAL)

    def announce_all(self, event):
        threads = []
        for url in self.tracker_urls():
            t = Thread(target=self._announce_safe, args=(url, event), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(35)

    def _announce_safe(self, url, event):
        try:
            for peer in self.announce(url, event):
                self.new_peers_queue.put(peer)
        except Exception as e:
            logger.info("tracker %s: %s", url, e)

    def announce(self, url, event=None):
        if url.startswith('http'):
            return self.announce_http(url, event)
        if url.startswith('udp'):
            return self.announce_udp(url, event)
        return []

    def _params(self, event):
        params = {
            'info_hash': self.torrent.info_hash,
            'peer_id': self.torrent.peer_id,
            'uploaded': 0,
            'downloaded': self.downloaded,
            'left': max(0, self.torrent.total_length - self.downloaded),
            'port': LISTEN_PORT,
            'compact': 1,
        }
        if event:
            params['event'] = event
        return params

    def announce_http(self, url, event=None, timeout=30):
        resp = requests.get(url, params=self._params(event), timeout=timeout, headers=utils.HEADERS)
        reply = bencode.decode(resp.content)
        if 'failure reason' in reply:
            raise Exception(reply['failure reason'])
        peers = reply.get('peers', [])
        if isinstance(peers, (bytes, bytearray)):
            return parse_compact_peers(peers)
        if isinstance(peers, str):
            return parse_compact_peers(peers.encode('utf-8'))  # bencode.py decodes valid utf-8
        return [(p['ip'], p['port']) for p in peers]

    def _udp_request(self, sock, addr, msg, action, trans_id, min_len, attempts=2):
        for _ in range(attempts):
            sock.sendto(msg, addr)
            try:
                resp, _ = sock.recvfrom(65536)
            except socket.timeout:
                continue
            if len(resp) < 8:
                continue
            r_action, r_trans = struct.unpack('!II', resp[:8])
            if r_trans != trans_id:
                continue
            if r_action == 3:
                raise Exception("udp tracker error: " + resp[8:].decode('utf-8', 'replace'))
            if r_action == action and len(resp) >= min_len:
                return resp
        raise Exception("udp tracker did not answer")

    def announce_udp(self, url, event=None, timeout=15):
        """BEP 15 UDP tracker announce."""
        parsed = urlparse(url)
        addr = (parsed.hostname, parsed.port or 80)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            trans_id = random.getrandbits(32)
            resp = self._udp_request(sock, addr, struct.pack('!QII', UDP_MAGIC, 0, trans_id), 0, trans_id, 16)
            conn_id = struct.unpack('!Q', resp[8:16])[0]

            trans_id = random.getrandbits(32)
            p = self._params(event)
            msg = struct.pack('!QII20s20sQQQIIIiH', conn_id, 1, trans_id,
                              self.torrent.info_hash, self.torrent.peer_id,
                              p['downloaded'], p['left'], p['uploaded'],
                              UDP_EVENTS.get(event, 0), 0, random.getrandbits(32), -1, LISTEN_PORT)
            resp = self._udp_request(sock, addr, msg, 1, trans_id, 20)
            return parse_compact_peers(resp[20:])
        finally:
            sock.close()

    def stop_message(self):
        """Tell HTTP trackers we stopped (or completed). Returns (params, response) of the last one."""
        event = "completed" if self.torrent.total_length == self.downloaded else "stopped"
        params, resp = None, requests.models.Response()
        for url in self.tracker_urls():
            if not url.startswith('http'):
                continue
            params = self._params(event)
            try:
                resp = requests.get(url, params=params, timeout=10, headers=utils.HEADERS)
            except Exception as e:
                logger.info("tracker %s: %s", url, e)
        return params, resp
