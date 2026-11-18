"""A pool of small scorer processes (rl-data/score_worker.py) for the stdio reward.

Create it BEFORE the models load: each worker is forked from this process, and a fork taken later would copy the
page tables of everything loaded since. Scoring order is preserved; a dead or failing worker is an error, never a
silent zero reward.
"""
from __future__ import annotations

import json
import queue
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

WORKER = Path(__file__).resolve().parents[1] / "rl-data" / "score_worker.py"
UID_BASE, UID_LIMIT = 61000, 65000


class ScorePool:
    def __init__(self, workers: int, env: dict | None = None):
        if workers < 1:
            raise ValueError("ScorePool needs at least one worker")
        span = (UID_LIMIT - UID_BASE) // workers
        if span < 8:
            raise ValueError(f"{workers} workers leave fewer than 8 sandbox uids each")
        self.workers = workers
        self.procs = [subprocess.Popen([sys.executable, "-B", str(WORKER), str(UID_BASE + i * span), str(span)],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1, env=env)
                      for i in range(workers)]
        self.idle: queue.Queue = queue.Queue()
        for p in self.procs:
            self.idle.put(p)
        self.threads = ThreadPoolExecutor(workers)

    def _one(self, item: tuple[dict, str]) -> dict:
        p = self.idle.get()
        try:
            p.stdin.write(json.dumps({"task": item[0], "text": item[1]}) + "\n")
            p.stdin.flush()
            line = p.stdout.readline()
            if not line:
                raise RuntimeError(f"scorer worker pid {p.pid} exited (returncode {p.poll()})")
            res = json.loads(line)
            if "worker_error" in res:
                raise RuntimeError(f"scorer worker failed: {res['worker_error']}")
            return res
        finally:
            self.idle.put(p)

    def score(self, items: list[tuple[dict, str]]) -> list[dict]:
        """stdio_check.score for every (task record, completion text), in order."""
        return list(self.threads.map(self._one, items))

    def close(self) -> None:
        self.threads.shutdown(wait=False, cancel_futures=True)
        for p in self.procs:
            try:
                p.stdin.close()
            except OSError:
                pass
        for p in self.procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
