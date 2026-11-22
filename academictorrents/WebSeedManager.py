import logging
from queue import Empty
from threading import Thread

logger = logging.getLogger(__name__)


class WebSeedManager(Thread):
    """Worker thread that runs web-seed range jobs from a queue."""

    def __init__(self, request_queue, piece_manager, stop_event):
        Thread.__init__(self, daemon=True)
        self.request_queue = request_queue
        self.piece_manager = piece_manager
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            try:
                job = self.request_queue.get(timeout=0.5)
            except Empty:
                continue
            try:
                self.run_job(*job)
            except Exception:
                logger.exception("web seed job crashed")
            finally:
                self.request_queue.task_done()

    def run_job(self, seed, relpath, segments):
        pm = self.piece_manager
        total = sum(s["length"] for s in segments)
        state = {"k": 0, "pos": 0}

        def sink(chunk):
            view = memoryview(chunk)
            while view and state["k"] < len(segments):
                seg = segments[state["k"]]
                take = min(len(view), seg["length"] - state["pos"])
                pm.receive(seg["id_piece"], seg["piece_offset"] + state["pos"], view[:take])
                view = view[take:]
                state["pos"] += take
                if state["pos"] == seg["length"]:
                    state["k"] += 1
                    state["pos"] = 0

        try:
            got = seed.fetch(relpath, segments[0]["file_offset"], total, sink)
            if got < total:
                raise IOError("short response: %d of %d bytes" % (got, total))
            seed.record_success()
        except Exception as e:
            logger.info("web seed %s failed for %s: %s", seed.url, relpath, e)
            seed.record_failure(relpath)
        finally:
            pm.clear_file_pending(segments)

    def request_stop(self):
        self.stop_event.set()
