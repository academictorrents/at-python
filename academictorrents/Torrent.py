import time
import bencode
import logging
import os
import requests
import tempfile
from urllib.parse import quote
from . import utils
from . import bencoding

logger = logging.getLogger(__name__)


def fetch_from_academictorrents(info_hash, cache_path):
    """Download a .torrent by hash from academictorrents.com and cache it."""
    # Send the AT-Client user-agent: the default Python-urllib one gets a 403.
    response = requests.get("https://academictorrents.com/download/" + info_hash, timeout=30, headers=utils.HEADERS)
    response.raise_for_status()
    contents = response.content
    bencoding.info_bytes(contents)  # don't cache an error page as a .torrent
    tmp_path = cache_path + ".part"
    with open(tmp_path, 'wb') as f:
        f.write(contents)
    os.replace(tmp_path, cache_path)
    return contents


class Torrent(object):
    def __init__(self, hash=None, datastore="", contents=None):
        """Load a torrent by info hash (cache, then academictorrents.com) or from raw .torrent bytes."""
        self.hash = hash.lower() if hash else None
        self.datastore = utils.get_datastore(datastore=datastore)
        if not os.path.isdir(self.datastore):
            os.makedirs(self.datastore)
        if contents is None:
            contents = self.get_from_file()
            if not contents:
                contents = self.get_from_url()
        if not contents:
            raise Exception("Could not find a torrent with this hash on the tracker or in the data directory:" + str(self.datastore))

        # Hash the info dict exactly as it appears in the file.
        info_raw = bencoding.info_bytes(contents)
        self.info_hash = utils.sha1_hash(info_raw)
        if self.hash and self.hash != self.info_hash.hex():
            raise ValueError("torrent info hash %s does not match %s" % (self.info_hash.hex(), self.hash))
        self.hash = self.info_hash.hex()

        self.contents = bencode.decode(contents)
        self.total_length = 0
        self.piece_length = self.contents['info']['piece length']
        self.pieces = bencoding.decode(info_raw)[b'pieces']
        self.single_file = 'files' not in self.contents['info']
        self.private = self.contents['info'].get('private') == 1
        self.peer_id = self.generate_peer_id()
        self.trackers = self.get_trackers()
        self.filenames = []
        self.get_files()
        self.number_of_pieces = -(-self.total_length // self.piece_length)  # ceil, as int
        self.urls = []
        self.add_web_seeds(self.contents.get('url-list') or [])

        logger.debug(self.trackers)
        logger.debug(self.filenames)

        assert(self.total_length > 0)
        assert(len(self.filenames) > 0)

        name = self.contents['info']['name']
        print("Torrent name: " + name + ", Size: {0:.2f}MB".format(self.total_length / 1000. / 1000.))

    # ---- web seeds (BEP 19) -------------------------------------------------

    def add_web_seeds(self, urls):
        if isinstance(urls, (str, bytes)):
            urls = [urls]
        for url in urls:
            if isinstance(url, bytes):
                url = url.decode('utf-8', 'replace')
            if not url:
                continue
            base = self.resolve_web_seed(url)
            if base and base not in self.urls:
                self.urls.append(base)
        return self.urls

    def get_urls(self):
        return self.urls

    def web_seed_candidates(self, url):
        """Possible bases for a web seed URL, most standard first.

        For a single-file torrent a base is the file's URL. For a multi-file
        torrent it is the directory that the files' relative paths are
        appended to.
        """
        name = quote(self.contents['info']['name'])
        slash = url if url.endswith('/') else url + '/'
        if self.single_file:
            if url.endswith('/'):
                return [url + name]
            return [url, slash + name]
        # BEP 19: <url>/<name>/<path>. Also accept a URL that points at the
        # torrent's directory itself or at a file inside it.
        return [slash + name + '/', slash, url.rsplit('/', 1)[0] + '/']

    def web_seed_url(self, base, relpath):
        if self.single_file:
            return base
        return base + quote(relpath)

    def resolve_web_seed(self, url):
        probe = self.filenames[0]['relpath']
        seen = set()
        for base in self.web_seed_candidates(url):
            if base in seen:
                continue
            seen.add(base)
            try:
                resp = requests.head(self.web_seed_url(base, probe), headers=utils.HEADERS,
                                     timeout=10, allow_redirects=True, verify=False)
                resp.close()
            except Exception as e:
                logger.info("web seed %s unreachable: %s", base, e)
                continue
            ranges = resp.headers.get('Accept-Ranges', '').lower()
            if resp.status_code < 400 and ranges and ranges != 'none':
                return base
        logger.info("web seed %s does not serve this torrent with range requests", url)
        return None

    # ---- .torrent file ------------------------------------------------------

    def torrent_cache_path(self):
        return os.path.join(tempfile.gettempdir(), self.hash + '.torrent')

    def get_from_file(self):
        try:
            with open(self.torrent_cache_path(), 'rb') as f:
                return f.read()
        except Exception:
            return None

    def get_from_url(self):
        return fetch_from_academictorrents(self.hash, self.torrent_cache_path())

    def get_files(self):
        name = self.contents['info']['name']
        if name in ('', '.', '..') or '/' in name or '\\' in name:
            raise ValueError("unsafe torrent name: " + repr(name))
        root = self.datastore + name
        if 'files' in self.contents['info']:
            for f in self.contents['info']['files']:
                parts = [p.decode('utf-8', 'replace') if isinstance(p, bytes) else p for p in f["path"]]
                if any(p in ('', '.', '..') or '/' in p or '\\' in p for p in parts):
                    raise ValueError("unsafe path in torrent: " + repr(f["path"]))
                path = os.path.join(root, *parts)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                self.filenames.append({"path": path, "relpath": "/".join(parts), "length": f["length"]})
                self.total_length += f["length"]
        else:
            self.filenames.append({"path": root, "relpath": name, "length": self.contents['info']['length']})
            self.total_length = self.contents['info']['length']

    def get_trackers(self):
        if 'announce-list' in self.contents:
            return self.contents['announce-list']
        return [[self.contents.get('announce', '')]]

    def add_trackers(self, urls):
        known = {u for tier in self.trackers for u in tier}
        for url in urls:
            if url and url not in known:
                self.trackers.append([url])
                known.add(url)

    def generate_peer_id(self):
        seed = str(time.time())
        return utils.sha1_hash(seed.encode())
