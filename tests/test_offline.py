"""Download tests against a local HTTP web seed; no internet needed."""
import os
import struct
import threading
import time
import pytest
import academictorrents as at
from academictorrents import Torrent, PieceManager, Piece, Peer, Client
from academictorrents.Tracker import parse_compact_peers
from tests.helpers import LocalServer, make_torrent, serve_torrent, random_bytes

pytestmark = pytest.mark.timeout(120)


@pytest.fixture
def server():
    s = LocalServer()
    yield s
    s.close()


@pytest.fixture
def torrent_factory(server):
    paths = []

    def make(name, files, piece_length, seeds=None):
        serve_torrent(server, name, files)
        h, p = make_torrent(name, files, piece_length, web_seeds=[server.url] if seeds is None else seeds)
        paths.append(p)
        return h
    yield make
    for p in paths:
        if os.path.exists(p):
            os.remove(p)


def read_tree(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            full = os.path.join(d, f)
            with open(full, 'rb') as fh:
                out[os.path.relpath(full, root).replace(os.sep, '/')] = fh.read()
    return out


def test_same_named_files_in_subdirs(server, torrent_factory, tmp_path):
    files = {
        'train/001.png': random_bytes(70000, 1),
        'test/001.png': random_bytes(50000, 2),
        'with space/a b.txt': random_bytes(12345, 3),
        'top.bin': random_bytes(1, 4),
    }
    h = torrent_factory('ds', files, 32768)
    path = at.get(h, datastore=str(tmp_path), use_timestamp=False, stall_timeout=30)
    assert read_tree(path) == files


def test_exact_multiple_of_piece_size(server, torrent_factory, tmp_path):
    data = random_bytes(4 * 16384, 5)
    h = torrent_factory('exact.bin', data, 16384)
    path = at.get(h, datastore=str(tmp_path), use_timestamp=False, stall_timeout=30)
    with open(path, 'rb') as f:
        assert f.read() == data


def test_single_file_and_user_url(server, tmp_path):
    data = random_bytes(100000, 6)
    server.add('elsewhere/single.bin', data)
    h, p = make_torrent('single.bin', data, 16384)  # no url-list in the torrent
    try:
        path = at.get(h, datastore=str(tmp_path), use_timestamp=False, stall_timeout=30,
                      urls=[server.url + 'elsewhere/single.bin'])
        with open(path, 'rb') as f:
            assert f.read() == data
    finally:
        os.remove(p)


def test_hash_failure_is_retried(server, torrent_factory, tmp_path):
    server.set_mode("corrupt_once")
    files = {'a.bin': random_bytes(50000, 7), 'b.bin': random_bytes(30000, 8)}
    h = torrent_factory('retry', files, 16384)
    path = at.get(h, datastore=str(tmp_path), use_timestamp=False, stall_timeout=30)
    assert read_tree(path) == files


def test_stall_raises_instead_of_hanging(server, torrent_factory, tmp_path):
    server.set_mode("corrupt")
    h = torrent_factory('bad.bin', random_bytes(40000, 9), 16384)
    start = time.time()
    with pytest.raises(at.DownloadStalled):
        at.get(h, datastore=str(tmp_path), use_timestamp=False, stall_timeout=3)
    assert time.time() - start < 30
    time.sleep(0.5)
    assert not [t for t in threading.enumerate()
                if t.__class__.__module__.startswith('academictorrents') and t.is_alive()]


def test_server_ignoring_range_is_not_buffered(server, torrent_factory, tmp_path):
    good = LocalServer()
    try:
        files = random_bytes(60000, 10)
        serve_torrent(good, 'mixed.bin', files)
        server.set_mode("ignore_range")
        h = torrent_factory('mixed.bin', files, 16384, seeds=[server.url, good.url])
        path = at.get(h, datastore=str(tmp_path), use_timestamp=False, stall_timeout=30)
        with open(path, 'rb') as f:
            assert f.read() == files
    finally:
        good.close()


def test_resume_file_skips_rehash(server, torrent_factory, tmp_path):
    files = {'x/1.bin': random_bytes(40000, 11), 'x/2.bin': random_bytes(40000, 12)}
    h = torrent_factory('resume', files, 16384)
    path = at.get(h, datastore=str(tmp_path), use_timestamp=False, stall_timeout=30)

    torrent = Torrent.Torrent(h, str(tmp_path))
    pm = PieceManager.PieceManager(torrent)
    trusted, hashed = pm.check_disk_pieces()
    pm.close()
    assert pm.finished() and hashed == 0 and trusted == pm.number_of_pieces

    # Damage one file: only its pieces are re-checked, then re-downloaded.
    with open(os.path.join(path, 'x', '2.bin'), 'r+b') as f:
        f.seek(100)
        f.write(b'\0' * 10)
    pm = PieceManager.PieceManager(torrent)
    trusted, hashed = pm.check_disk_pieces()
    pm.close()
    assert not pm.finished() and 0 < hashed < pm.number_of_pieces

    path = at.get(h, datastore=str(tmp_path), use_timestamp=False, stall_timeout=30)
    assert read_tree(path) == files


def test_layout_segments(server, torrent_factory, tmp_path):
    files = {'a': b'a' * 10, 'b': b'b' * 3, 'c': b'c' * 20}
    h = torrent_factory('layout', files, 8)
    pm = PieceManager.PieceManager(Torrent.Torrent(h, str(tmp_path)))
    assert pm.number_of_pieces == 5
    segs = [(s['relpath'], s['id_piece'], s['piece_offset'], s['file_offset'], s['length']) for s in pm.files]
    assert segs == [('a', 0, 0, 0, 8), ('a', 1, 0, 8, 2), ('b', 1, 2, 0, 3), ('c', 1, 5, 0, 3),
                    ('c', 2, 0, 3, 8), ('c', 3, 0, 11, 8), ('c', 4, 0, 19, 1)]
    pm.close()


def test_piece_ranges_and_reset():
    p = Piece.Piece(0, 40000, b'')
    assert p.missing_blocks(0, 30) == [0, 1, 2]
    assert not p.write(16384, b'x' * 16384)
    assert p.missing_blocks(0, 30) == [0, 2]
    assert not p.write(0, b'x' * 100)
    assert not p.write(100, b'x' * 16284)
    assert p.ranges == [(0, 32768)]
    assert p.write(32768, b'x' * (40000 - 32768))
    p.reset()
    assert p.buf is None and not p.ranges and p.missing_blocks(0, 30) == [0, 1, 2]


class FakeTorrent(object):
    number_of_pieces = 10
    info_hash = b'i' * 20
    peer_id = b'p' * 20


def msg(msg_id, payload=b''):
    return struct.pack('!IB', 1 + len(payload), msg_id) + payload


def test_peer_message_parsing():
    peer = Peer.Peer(FakeTorrent(), '1.2.3.4')
    handshake = struct.pack('B19s8x20s20s', 19, b'BitTorrent protocol', b'i' * 20, b'q' * 20)
    block = struct.pack('!II', 3, 0) + b'z' * 16384
    stream = (handshake + b'\0\0\0\0' + msg(Peer.UNCHOKE) + msg(Peer.HAVE, struct.pack('!I', 2))
              + b'\0\0\0\0' + msg(Peer.PIECE, block) + msg(Peer.HAVE, struct.pack('!I', 5)))
    out = []
    for i in range(0, len(stream), 7):  # arbitrary split points
        out += peer.feed(stream[i:i + 7])
    assert [m[0] for m in out] == [Peer.UNCHOKE, Peer.HAVE, Peer.PIECE, Peer.HAVE]
    assert out[2][1] == block
    assert out[3][1] == struct.pack('!I', 5)
    assert peer.buffer == bytearray()


def test_peer_rejects_wrong_info_hash():
    peer = Peer.Peer(FakeTorrent(), '1.2.3.4')
    handshake = struct.pack('B19s8x20s20s', 19, b'BitTorrent protocol', b'x' * 20, b'q' * 20)
    with pytest.raises(Peer.ProtocolError):
        peer.feed(handshake)


def test_compact_peers():
    assert parse_compact_peers(bytes([10, 0, 0, 1, 0x1A, 0xE1, 1, 2, 3, 4, 0, 80])) == [
        ('10.0.0.1', 6881), ('1.2.3.4', 80)]


def test_client_state_is_per_instance():
    assert not isinstance(Client.Client.__dict__['__init__'], classmethod)


def test_get_leaves_root_logger_alone(server, torrent_factory, tmp_path):
    import logging
    root = logging.getLogger()
    before = root.level
    h = torrent_factory('log.bin', random_bytes(1000, 13), 16384)
    at.get(h, datastore=str(tmp_path), use_timestamp=False, showlogs=True, stall_timeout=30)
    assert root.level == before
