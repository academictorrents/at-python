import os
import json
import time
import base64
import hashlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from tqdm.auto import tqdm
from . import Piece
from .Storage import Storage
from .utils import Bitfield

logger = logging.getLogger(__name__)

BLOCK_TIMEOUT = 30  # seconds before an unanswered BitTorrent block request is retried
FILE_TIMEOUT = 300  # safety net; web jobs clear their own pending marks when they end
RESUME_VERSION = 1


class PieceManager(object):
    def __init__(self, torrent):
        self.torrent = torrent
        self.number_of_pieces = torrent.number_of_pieces
        self.bitfield = Bitfield(self.number_of_pieces)
        self.lock = threading.RLock()
        self.storage = Storage()
        self.completed_bytes = 0
        self.completed_pieces = 0
        self.hash_failures = 0
        self.received_bytes = 0  # raw bytes in, before hash checks
        self.pieces = self.generate_pieces()
        self.files = self.get_files()
        for f in self.files:
            self.pieces[f["id_piece"]].files.append(f)
        self._incomplete = list(range(self.number_of_pieces))

    def close(self):
        self.storage.close()

    # ---- progress ----------------------------------------------------------

    def finished(self):
        return self.completed_pieces == self.number_of_pieces

    def check_finished_pieces(self):
        return self.completed_bytes

    def _mark_complete(self, index):
        if not self.bitfield[index]:
            self.bitfield[index] = 1
            self.completed_pieces += 1
            self.completed_bytes += self.pieces[index].size

    def _incomplete_pieces(self):
        """Iterate unfinished pieces in order, compacting the list as we go."""
        stale = len(self._incomplete) - (self.number_of_pieces - self.completed_pieces)
        if stale > 64 and stale * 4 > len(self._incomplete):
            self._incomplete = [i for i in self._incomplete if not self.bitfield[i]]
        for i in self._incomplete:
            if not self.bitfield[i]:
                yield self.pieces[i]

    # ---- receiving data ----------------------------------------------------

    def receive(self, index, offset, data):
        """Store data for a piece (from a peer or a web seed); thread-safe."""
        if not 0 <= index < self.number_of_pieces:
            return
        piece = self.pieces[index]
        with self.lock:
            self.received_bytes += len(data)
            if self.bitfield[index] or piece.verifying:
                return
            if not piece.write(offset, data):
                return
            piece.verifying = True
            buf = piece.buf
        self._verify(piece, buf)

    def _verify(self, piece, buf):
        ok = hashlib.sha1(buf).digest() == piece.data_hash
        if ok:
            try:
                for f in piece.files:
                    start = f["piece_offset"]
                    self.storage.write(f["path"], f["file_offset"], memoryview(buf)[start:start + f["length"]])
            except Exception:
                logger.exception("failed writing piece %d", piece.index)
                ok = False
        with self.lock:
            piece.reset()
            if ok:
                self._mark_complete(piece.index)
            else:
                self.hash_failures += 1
                logger.warning("piece %d failed its hash check; re-downloading it", piece.index)

    # ---- scheduling --------------------------------------------------------

    def next_bt_requests(self, has_piece, max_requests):
        """Pick up to max_requests (index, offset, length) block requests for a peer."""
        out = []
        now = time.time()
        with self.lock:
            for piece in self._incomplete_pieces():
                if len(out) >= max_requests:
                    break
                if piece.verifying or not has_piece(piece.index):
                    continue
                for block in piece.missing_blocks(now, BLOCK_TIMEOUT):
                    piece.set_block_pending(block, now)
                    out.append((piece.index, block * Piece.BLOCK_SIZE, piece.block_length(block)))
                    if len(out) >= max_requests:
                        break
        return out

    def next_web_jobs(self, choose_seed, max_jobs, max_bytes=5000000):
        """Group needed file segments into contiguous per-file HTTP range jobs.

        choose_seed(relpath) returns a web seed able to serve that file, or None.
        Returns a list of (seed, relpath, [segment, ...]); each segment is
        contiguous in the file with the one before it.
        """
        jobs = []
        open_jobs = {}  # relpath -> (job, last piece index, bytes)
        now = time.time()
        with self.lock:
            for piece in self._incomplete_pieces():
                if piece.verifying:
                    continue
                for seg in piece.files:
                    relpath = seg["relpath"]
                    if not piece.segment_needed(seg, now, FILE_TIMEOUT):
                        continue
                    cur = open_jobs.get(relpath)
                    if cur and cur[1] == piece.index - 1 and cur[2] < max_bytes:
                        cur[0][2].append(seg)
                        open_jobs[relpath] = (cur[0], piece.index, cur[2] + seg["length"])
                    else:
                        if len(jobs) >= max_jobs:
                            continue
                        seed = choose_seed(relpath)
                        if seed is None:
                            continue
                        job = (seed, relpath, [seg])
                        jobs.append(job)
                        open_jobs[relpath] = (job, piece.index, seg["length"])
                    piece.set_file_pending(relpath, now)
                # stop once no open job can still be extended by later pieces
                if len(jobs) >= max_jobs and all(v[1] < piece.index for v in open_jobs.values()):
                    break
        return jobs

    def clear_file_pending(self, segments):
        with self.lock:
            for seg in segments:
                self.pieces[seg["id_piece"]].clear_file_pending(seg["relpath"])

    # ---- disk / resume -----------------------------------------------------

    def resume_path(self):
        return os.path.join(self.torrent.datastore, "." + self.torrent.contents["info"]["name"] + ".at-resume.json")

    def _file_stats(self):
        stats = {}
        for f in self.torrent.filenames:
            try:
                st = os.stat(f["path"])
                stats[f["relpath"]] = [st.st_size, st.st_mtime_ns]
            except OSError:
                stats[f["relpath"]] = None
        return stats

    def save_resume(self):
        with self.lock:
            bits = self.bitfield.tobytes()
        stats = self._file_stats()  # after the snapshot: later writes change mtime
        data = {
            "version": RESUME_VERSION,
            "info_hash": self.torrent.info_hash.hex(),
            "bitfield": base64.b64encode(bits).decode("ascii"),
            "files": stats,
        }
        path = self.resume_path()
        tmp = path + ".part"
        try:
            with open(tmp, "w") as fh:
                json.dump(data, fh)
            os.replace(tmp, path)
        except OSError as e:
            logger.info("could not write resume file: %s", e)

    def _load_resume(self, stats):
        """Bitfield of pieces the resume file vouches for, or None."""
        try:
            with open(self.resume_path()) as fh:
                data = json.load(fh)
            if data.get("version") != RESUME_VERSION or data.get("info_hash") != self.torrent.info_hash.hex():
                return None, set()
            bits = Bitfield(self.number_of_pieces, base64.b64decode(data["bitfield"]))
            saved = data["files"]
        except Exception:
            return None, set()
        unchanged = {rel for rel, st in stats.items() if st is not None and saved.get(rel) == st}
        return bits, unchanged

    def _piece_on_disk(self, piece):
        h = hashlib.sha1()
        for f in piece.files:
            data = self.storage.read(f["path"], f["file_offset"], f["length"])
            if len(data) != f["length"]:
                return False
            h.update(data)
        return h.digest() == piece.data_hash

    def check_disk_pieces(self, workers=None):
        stats = self._file_stats()
        resume_bits, unchanged = self._load_resume(stats)
        sizes = {rel: (st[0] if st else -1) for rel, st in stats.items()}

        to_hash = []
        trusted = 0
        for piece in self.pieces:
            rels = [f["relpath"] for f in piece.files]
            if resume_bits is not None and all(r in unchanged for r in rels):
                if resume_bits[piece.index]:
                    self._mark_complete(piece.index)
                    trusted += 1
                continue  # files untouched since the resume file: state is known
            # skip pieces whose files are missing or too short to hold them
            if all(sizes[f["relpath"]] >= f["file_offset"] + f["length"] for f in piece.files):
                to_hash.append(piece)

        if to_hash:
            print("Checking pieces on disk...")
            workers = workers or min(8, (os.cpu_count() or 2))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = pool.map(self._piece_on_disk, to_hash)
                for piece, ok in tqdm(zip(to_hash, results), total=len(to_hash)):
                    if ok:
                        self._mark_complete(piece.index)
        print("Found " + str(self.completed_pieces) + " finished pieces out of " + str(self.number_of_pieces) + " total pieces.")
        return trusted, len(to_hash)

    def preallocate(self):
        for f in self.torrent.filenames:
            try:
                self.storage.preallocate(f["path"], f["length"])
            except OSError as e:
                logger.info("could not preallocate %s: %s", f["path"], e)

    # ---- layout ------------------------------------------------------------

    def generate_pieces(self):
        pieces = []
        for i in range(self.number_of_pieces):
            start = i * 20
            if i == self.number_of_pieces - 1:
                length = self.torrent.total_length - (self.number_of_pieces - 1) * self.torrent.piece_length
            else:
                length = self.torrent.piece_length
            pieces.append(Piece.Piece(i, length, self.torrent.pieces[start:start + 20]))
        return pieces

    def get_files(self):
        """Split every file into per-piece segments."""
        segments = []
        offset = 0  # absolute offset in the torrent's byte stream
        for f in self.torrent.filenames:
            remaining = f["length"]
            file_offset = 0
            while remaining > 0:
                id_piece = offset // self.torrent.piece_length
                piece_offset = offset - id_piece * self.torrent.piece_length
                length = min(remaining, self.pieces[id_piece].size - piece_offset)
                segments.append({
                    "length": length,
                    "id_piece": id_piece,
                    "file_offset": file_offset,
                    "piece_offset": piece_offset,
                    "path": f["path"],
                    "relpath": f["relpath"],
                })
                offset += length
                file_offset += length
                remaining -= length
        return segments
