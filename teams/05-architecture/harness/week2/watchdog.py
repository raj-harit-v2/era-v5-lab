"""Opt-in timer for the G5 optimizer step, using Team 7's retry contract."""

import faulthandler
import os
import sys
import threading
import time

from common.events import emit
from common.reasons import EXIT_RETRY, write_exit_note


class StepWatchdog:
    def __init__(self, limit_s):
        self.limit_s = limit_s
        self._condition = threading.Condition()
        self._started_at = None
        self._closed = False
        self._thread = threading.Thread(target=self._watch, name="g5-step-watchdog", daemon=True)
        self._thread.start()

    def arm(self, completed):
        with self._condition:
            self._completed = completed
            self._started_at = time.monotonic()
            self._condition.notify()

    def disarm(self):
        with self._condition:
            self._started_at = None
            self._condition.notify()

    def close(self):
        with self._condition:
            self._closed = True
            self._condition.notify()
        self._thread.join()

    def _watch(self):
        with self._condition:
            while not self._closed:
                if self._started_at is None:
                    self._condition.wait()
                    continue
                idle_s = time.monotonic() - self._started_at
                remaining = self.limit_s - idle_s
                if remaining <= 0:
                    step = self._completed
                    break
                self._condition.wait(min(remaining, threading.TIMEOUT_MAX))
            else:
                return

        detail = f"No optimizer step completed for {idle_s:.2f}s after step {step}"
        try:
            print(f"G5 step watchdog: {detail}", file=sys.stderr, flush=True)
            faulthandler.dump_traceback(all_threads=True)
            emit("train.watchdog", step=step, idle_s=round(idle_s, 2), limit_s=self.limit_s)
        finally:
            try:
                rank = int(os.environ.get("RANK", os.environ.get("SLURM_PROCID", "0")))
                write_exit_note(EXIT_RETRY, "hang_watchdog", step, detail, rank=rank)
            finally:
                os._exit(EXIT_RETRY)
