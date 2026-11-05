"""Append-only JSONL event output for live benchmark consumers."""
from __future__ import annotations

import json
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


class JsonlWriter:
    """Write one flushed JSON object per line so readers can tail the file during a run."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._file = None
        self._lock = threading.Lock()

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("x", encoding="utf-8", newline="\n")    # "x": never overwrite an earlier run
        return self

    def __exit__(self, exc_type, exc, tb):
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None
        return False

    def write(self, record: dict) -> None:
        """Append and flush a record. The lock lets the GPU-sampler thread and the step-event thread share it."""
        line = json.dumps(record, separators=(",", ":"), allow_nan=False)
        with self._lock:
            if self._file is None:
                raise RuntimeError("JsonlWriter must be used inside a with block")
            self._file.write(line + "\n")
            self._file.flush()


def gpu_sample_record(*, run_id: str, node_id: str, gpu: dict, metrics: dict,
                      slowdown_flags: list[str] | None, step: int | None,
                      timestamp: str) -> dict:
    """Build the versioned G8 live GPU-sample record; memory remains in MiB for G8 conversion."""
    return {
        "schema_version": 1,
        "event": "gpu_sample",
        "timestamp": timestamp,
        "run_id": run_id,
        "node_id": node_id,
        "gpu": gpu,
        "step": step,
        "metrics": metrics,
        "slowdown_flags": slowdown_flags,
    }


def step_timing_record(*, run_id: str, node_id: str, rank: int, local_rank: int, step: int,
                       data_ms: float, raw_step_ms: float, timestamp: str) -> dict:
    """Build one clean-step timing record; data_ms is host time: next_batch(), plus prefetch() when it is on."""
    return {
        "schema_version": 1,
        "event": "step_timing",
        "timestamp": timestamp,
        "run_id": run_id,
        "node_id": node_id,
        "rank": rank,
        "local_rank": local_rank,
        "step": step,
        "data_ms": data_ms,
        "raw_step_ms": raw_step_ms,
    }


class StepTimingStreamer:
    """Resolve step timer pairs and write step events on a worker thread; the training thread never syncs or writes."""

    def __init__(self, writer: JsonlWriter, *, run_id: str, node_id: str, rank: int, local_rank: int,
                 poll_interval_s: float = 0.001):
        self.writer = writer
        self.run_id, self.node_id = run_id, node_id
        self.rank, self.local_rank = rank, local_rank
        self.poll_interval_s = poll_interval_s
        self._queue = queue.Queue()
        self._thread = None
        self.error = None

    def __enter__(self):
        self._thread = threading.Thread(target=self._run, name="perfkit-step-events", daemon=True)
        self._thread.start()
        return self

    def submit(self, step: int, data_ms: float, timer_kind: str, pair: tuple) -> None:
        """Queue an already-recorded timer pair. This is nonblocking and does not query/sync CUDA."""
        self._queue.put_nowait((step, data_ms, timer_kind, pair))

    def _run(self):
        """Worker: wait for each step's end event, then write its step_timing record; None stops it."""
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                step, data_ms, timer_kind, (start, end) = item
                if timer_kind == "event":
                    while not end.query():
                        time.sleep(self.poll_interval_s)
                    raw_step_ms = start.elapsed_time(end)
                else:
                    raw_step_ms = (end - start) * 1e3
                timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                self.writer.write(step_timing_record(
                    run_id=self.run_id, node_id=self.node_id, rank=self.rank, local_rank=self.local_rank,
                    step=step, data_ms=round(float(data_ms), 4), raw_step_ms=round(float(raw_step_ms), 4),
                    timestamp=timestamp,
                ))
            except Exception as exc:  # event logging must not interrupt training
                self.error = str(exc)
            finally:
                self._queue.task_done()

    def __exit__(self, exc_type, exc, tb):
        """Write every queued step, then stop the worker."""
        self._queue.put(None)
        self._queue.join()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        return False
