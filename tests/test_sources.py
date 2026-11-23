"""Torrent sources (hash, magnet, file, URL), DHT and metadata exchange; offline."""
import os
import base64
import hashlib
import tempfile
from queue import Queue
import pytest
import academictorrents as at
from academictorrents import bencoding, sources, DHT
from academictorrents.Metadata import fetch_metadata
from tests.helpers import (LocalServer, FakeMetadataPeer, FakeDHTNode, make_torrent,
                           serve_torrent, random_bytes)

pytestmark = pytest.mark.timeout(120)


@pytest.fixture
def server():
    s = LocalServer()
    yield s
    s.close()


def build(server, name, files, piece_length=16384, seeds=None):
    """Make a torrent, serve its data, and move the .torrent out of the cache."""
    serve_torrent(server, name, files)
    h, cached = make_torrent(name, files, piece_length, web_seeds=[server.url] if seeds is None else seeds)
    with open(cached, 'rb') as f:
        data = f.read()
    os.remove(cached)
    return h, data


def test_bencoding_roundtrip_and_info_bytes():
    obj = {b'a': [1, b'x', {b'k': b'\xff\x00'}], b'info': {b'name': b'n', b'pieces': b'\x00' * 20}}
    data = bencoding.encode(obj)
    assert bencoding.decode(data) == obj
    assert bencoding.info_bytes(data) == bencoding.encode(obj[b'info'])
    with pytest.raises(bencoding.BencodeError):
        bencoding.decode(b'd1:ai1e')


def test_info_hash_uses_raw_bytes(tmp_path):
    # Keys out of order: re-encoding would change the hash, the raw bytes must not.
    info = b'd6:lengthi5e4:name1:x12:piece lengthi16384e6:pieces20:' + b'\x01' * 20 + b'e'
    data = b'd4:info' + info + b'8:announce0:e'
    path = tmp_path / 'x.torrent'
    path.write_bytes(data)
    t = sources.load_torrent(str(path), str(tmp_path / 'ds'))
    assert t.hash == hashlib.sha1(info).hexdigest()


def test_parse_hash_and_magnet():
    h = 'c9e15763f722f23e98a29decdfae341b98d53056'
    b32 = base64.b32encode(bytes.fromhex(h)).decode()
    assert sources.parse_hash(h.upper()) == h
    assert sources.parse_hash(b32) == h
    m = sources.parse_magnet('magnet:?xt=urn:btih:%s&dn=x&tr=udp%%3A%%2F%%2Ft%%3A1&ws=http%%3A%%2F%%2Fw%%2F' % b32)
    assert (m.info_hash, m.trackers, m.web_seeds, m.name) == (h, ['udp://t:1'], ['http://w/'], 'x')
    assert sources.parse_hash('not a hash') is None


def test_get_from_local_torrent_file(server, tmp_path):
    files = {'a/1.bin': random_bytes(30000, 1), 'b/1.bin': random_bytes(20000, 2)}
    h, data = build(server, 'local', files)
    path = tmp_path / 'local.torrent'
    path.write_bytes(data)
    out = at.get(str(path), datastore=str(tmp_path / 'ds'), use_timestamp=False, stall_timeout=30)
    with open(os.path.join(out, 'a', '1.bin'), 'rb') as f:
        assert f.read() == files['a/1.bin']


def test_get_from_torrent_url(server, tmp_path):
    payload = random_bytes(50000, 3)
    h, data = build(server, 'url.bin', payload)
    server.add('files/url.torrent', data)
    out = at.get(server.url + 'files/url.torrent', datastore=str(tmp_path), use_timestamp=False, stall_timeout=30)
    with open(out, 'rb') as f:
        assert f.read() == payload


def test_missing_source_raises(tmp_path):
    with pytest.raises(sources.TorrentNotFound):
        sources.load_torrent(str(tmp_path / 'nope.torrent'), str(tmp_path))


def test_metadata_exchange_rejects_bad_peer(server):
    h, data = build(server, 'meta.bin', random_bytes(40000, 4))
    info_raw = bencoding.info_bytes(data)
    bad = FakeMetadataPeer(info_raw, bytes.fromhex(h), corrupt=True)
    good = FakeMetadataPeer(info_raw, bytes.fromhex(h))
    try:
        q = Queue()
        q.put(bad.addr)
        q.put(good.addr)
        raw = fetch_metadata(bytes.fromhex(h), q, b'p' * 20, timeout=20, workers=1)
        assert raw == info_raw
        assert bad.connections == 1
    finally:
        bad.close()
        good.close()


def test_metadata_larger_than_one_piece(server):
    files = {'f%04d' % i: b'x' for i in range(2000)}  # long file list -> multi-piece metadata
    h, data = build(server, 'many', files)
    info_raw = bencoding.info_bytes(data)
    assert len(info_raw) > 16384
    peer = FakeMetadataPeer(info_raw, bytes.fromhex(h))
    try:
        q = Queue()
        q.put(peer.addr)
        assert fetch_metadata(bytes.fromhex(h), q, b'p' * 20, timeout=20) == info_raw
    finally:
        peer.close()


def test_dht_lookup_follows_nodes():
    target = os.urandom(20)
    far = FakeDHTNode(peers=[('10.1.2.3', 4567)])
    near = FakeDHTNode(nodes=[(target[:19] + b'\x00', far.addr)])
    dht = DHT.DHT(bootstrap=[near.addr])
    try:
        found = []
        peers = dht.get_peers(target, timeout=10, on_peer=found.append)
        assert ('10.1.2.3', 4567) in peers and found
        assert near.queries and far.queries
    finally:
        dht.close()
        near.close()
        far.close()


def test_dht_answers_ping():
    import socket
    dht = DHT.DHT(bootstrap=[])
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(5)
    try:
        s.sendto(bencoding.encode({'t': b'aa', 'y': 'q', 'q': 'ping', 'a': {'id': b'x' * 20}}), ('127.0.0.1', dht.port))
        reply = bencoding.decode(s.recvfrom(1024)[0])
        assert reply[b'y'] == b'r' and reply[b'r'][b'id'] == dht.node_id
    finally:
        s.close()
        dht.close()


def test_magnet_download_via_dht_metadata(server, tmp_path, monkeypatch):
    files = {'d/x.bin': random_bytes(60000, 5), 'd/y.bin': random_bytes(10000, 6)}
    h, data = build(server, 'magnet', files, seeds=[])
    peer = FakeMetadataPeer(bencoding.info_bytes(data), bytes.fromhex(h))
    node = FakeDHTNode(peers=[peer.addr])
    monkeypatch.setattr(DHT, 'BOOTSTRAP', [node.addr])
    try:
        magnet = 'magnet:?xt=urn:btih:%s&ws=%s' % (h, server.url)
        out = at.get(magnet, datastore=str(tmp_path), use_timestamp=False, stall_timeout=30, metadata_timeout=20)
        with open(os.path.join(out, 'd', 'x.bin'), 'rb') as f:
            assert f.read() == files['d/x.bin']
        assert node.queries
    finally:
        peer.close()
        node.close()
        cached = os.path.join(tempfile.gettempdir(), h + '.torrent')
        if os.path.exists(cached):
            os.remove(cached)


def test_unknown_hash_without_peers_fails_fast(tmp_path):
    with pytest.raises(sources.TorrentNotFound):
        at.get('0' * 40, datastore=str(tmp_path), use_timestamp=False, dht=False, metadata_timeout=2)


@pytest.mark.network
def test_metadata_from_dht_and_public_trackers(tmp_path):
    """Fetch vangogh's metadata from peers only (skips academictorrents.com)."""
    h = '55a8925a8d546b9ca47d309ab438b91f7959e77f'
    node = DHT.DHT()
    try:
        raw = sources.find_metadata(h, [], lambda: node, timeout=120)
    finally:
        node.close()
    assert raw is not None and hashlib.sha1(raw).hexdigest() == h
