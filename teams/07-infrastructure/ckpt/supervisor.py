"""Supervisor: restart a training job from its last COMPLETE checkpoint, with a limit on restarts (ADR 0002).

In simple words:
- The supervisor is a small parent process. It starts the trainer as a child process and waits for it.
- When the child ends, the exit code says what happens next (the same three codes as queue/job_queue.py):
      0   finished                      -> the supervisor stops, exit 0
      75  "I saved, run me again"       -> restart
      78  "stop, a person must look"    -> no restart, exit 78
      anything else (exception, SIGKILL, segfault) is a crash -> restart, unless it is a crash loop
- A restart runs the SAME command again. The trainer always calls Checkpointer.restore(), which picks the
  newest committed checkpoint from latest.json. A checkpoint is COMPLETE when its MANIFEST.json is written
  (it is written last, and latest.json moves only after it). So the restarted trainer can never load a
  half-written checkpoint, and the supervisor does not need to know anything about the model.
- Limits, so a broken job does not burn machine hours in a loop:
      --max-restarts N              at most N restarts after a CRASH, in total (default 10)
      CRASHLOOP_N in CRASHLOOP_WINDOW_S   3 crashes in 30 minutes = crash loop -> exit 78 (same numbers and
                                    environment variables as queue/job_queue.py)
      --max-stops N                 at most N restarts after a 75 (default 100)
  Crashes and 75s are counted apart on purpose: on a long run 75 is the normal path (saved at the time limit,
  or preempted), so a healthy run must not be held after a few of them. The separate, larger 75 limit only
  catches a trainer that keeps exiting 75 without getting anywhere.
  The crash count lives in this process's memory: unlike the Slurm wrapper, the supervisor itself is not
  restarted between attempts, so it sees every crash.
- Every attempt is logged: one JSON line per child exit in --log (attempt, exit code, what it means, what the
  supervisor does), and the same as supervisor.* events (common/events.py, so Team 08 can read them).
  `pointer_step` is the step latest.json points to (with its MANIFEST.json) when the restart is decided. It is
  NOT proof of what the trainer loaded: if that checkpoint fails its checks, Checkpointer.restore() falls back
  to an older commit. The trainer's own `restore.done` event has the step it really restored.
- Signals. The child runs in its own session (process group), so it gets only the signals we pass on: a Ctrl-C
  in a terminal does not reach it twice. SIGTERM and SIGUSR1 are passed on as they are; SIGINT (Ctrl-C) is
  passed on as SIGTERM, because the trainer saves on SIGTERM and SIGUSR1 (support/simulation/trainer/train.py)
  and would crash on SIGINT. After SIGTERM or SIGINT the supervisor starts no new trainer, also when the signal
  arrives between attempts: it exits 75 so the outer scheduler (Slurm, the TSAI runner) decides, and the log
  says whether the child really saved (exit 75) or not.
- If the supervisor itself is killed with SIGKILL, the child keeps running (it is in its own session). That is
  safe: when a new attempt of the run starts, it claims latest.json (fencing in ckpt.py), and the old child's
  next commit is refused, so it stops without moving the pointer.
- Platforms: Linux and macOS. On Windows it runs too, without SIGUSR1 and without the new session (those do
  not exist there), and a killed child shows as exit 1, not -9.

Use (everything after -- is the trainer command; RUN_ID and V5_REMOTE_ROOT name the checkpoint folder, as in
queue/job_queue.py):

    RUN_ID=r1 V5_REMOTE_ROOT=/shared/ckpt python ckpt/supervisor.py --log out/supervisor.jsonl -- \\
        python my_train.py --config c.yaml

The child gets V5_RESTART_COUNT (0 on the first start) in its environment. It is for logs only (the restart
test labels its rows with it); a trainer must not behave differently on it. Under Slurm the same number is
SLURM_RESTART_COUNT; we do not set that name here, so nothing mistakes this for a Slurm requeue.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ckpt.store import open_store  # noqa: E402
from common.events import emit  # noqa: E402

EXIT_DONE, EXIT_RETRY, EXIT_FATAL = 0, 75, 78       # common/reasons.py, ADR 0001 §6
MANIFEST = "MANIFEST.json"                          # ckpt/ckpt.py: written last, marks a commit COMPLETE
CRASHLOOP_N = int(os.environ.get("CRASHLOOP_N", "3"))
CRASHLOOP_WINDOW_S = float(os.environ.get("CRASHLOOP_WINDOW_S", "1800"))
STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT)
# SIGUSR1 ("save soon") does not exist on Windows
HANDLED = tuple(s for s in (signal.SIGTERM, signal.SIGINT, getattr(signal, "SIGUSR1", None)) if s is not None)
POSIX = os.name == "posix"


def meaning(rc: int) -> str:
    if rc == EXIT_DONE:
        return "done"
    if rc == EXIT_RETRY:
        return "saved_and_stopped"
    if rc == EXIT_FATAL:
        return "fatal"
    if rc < 0:
        return f"crash: killed by {signal.Signals(-rc).name}" if -rc in signal.valid_signals() else "crash"
    return f"crash: exit {rc}"


def last_complete(run_url: str) -> dict:
    """What latest.json points to, if its MANIFEST.json exists; None = nothing committed (fresh start).

    For the log only: the trainer's Checkpointer.restore() makes the real choice and may fall back to an
    older commit if this one fails its checks."""
    try:
        st = open_store(run_url)
        if not st.exists("latest.json"):
            return None
        ptr = st.get_json("latest.json")
        if not ptr.get("path") or not st.exists(f"{ptr['path']}/{MANIFEST}"):
            return None
        return {"step": ptr.get("step"), "path": ptr["path"], "epoch": ptr.get("epoch")}
    except Exception as e:  # noqa: BLE001 - reporting only; the trainer's restore() is what decides
        return {"error": f"{type(e).__name__}: {e}"[:300]}


class Supervisor:
    def __init__(self, cmd: list, run_url: str = None, log_path: str = None, max_restarts: int = 10,
                 max_stops: int = 100, crash_n: int = CRASHLOOP_N, crash_window_s: float = CRASHLOOP_WINDOW_S,
                 backoff_s: float = 5.0, on_start=None):
        self.cmd = list(cmd)
        self.run_url = run_url
        self.log_path = log_path
        self.max_restarts = max_restarts    # restarts after a crash
        self.max_stops = max_stops          # restarts after a 75 (saved and stopped)
        self.crash_n = crash_n
        self.crash_window_s = crash_window_s
        self.backoff_s = backoff_s
        self.on_start = on_start        # on_start(child, attempt): tests and the restart test use it
        self.child = None
        self.stopping = False
        self.crashes = []               # times of crashes, for the crash-loop limit
        self.rows = []

    def _log(self, row: dict) -> None:
        self.rows.append(row)
        if self.log_path:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
            with open(self.log_path, "a") as f:
                f.write(json.dumps(row) + "\n")
        print(f"[supervisor] attempt {row['attempt']}: exit {row['rc']} ({row['meaning']}) -> {row['action']}"
              f" ({row['reason']})" + (f", latest.json at step {row['pointer_step']}" if "pointer_step" in row else ""),
              file=sys.stderr, flush=True)

    def _forward(self, signum, _frame):
        if signum in STOP_SIGNALS:
            self.stopping = True
        # the trainer saves on SIGTERM / SIGUSR1; SIGINT (Ctrl-C) would make it crash instead of save
        send = signal.SIGTERM if signum == signal.SIGINT else signum
        emit("supervisor.signal", signal=signal.Signals(signum).name, sent=signal.Signals(send).name)
        if self.child is not None and self.child.poll() is None:
            self.child.send_signal(send)

    def _sleep(self, seconds: float) -> None:
        """Backoff that ends early on a stop signal."""
        end = time.time() + seconds
        while not self.stopping and time.time() < end:
            time.sleep(min(0.1, max(0.0, end - time.time())))

    def _decide(self, rc: int, crash_restarts: int, stop_restarts: int, now: float) -> tuple:
        """(action, exit code if stopping, reason)."""
        if rc == EXIT_DONE:
            return "stop", EXIT_DONE, "finished"
        if rc == EXIT_FATAL:
            return "stop", EXIT_FATAL, "the trainer asked for a person (78)"
        if self.stopping:
            # 75 either way, so the outer runner may run it again; the reason says if work since the last
            # commit was lost
            saved = "saved" if rc == EXIT_RETRY else "not saved, work since the last commit is lost"
            return "stop", EXIT_RETRY, f"told to stop; child exit {rc}, {saved}"
        if rc == EXIT_RETRY:
            if stop_restarts >= self.max_stops:
                return "stop", EXIT_FATAL, f"limit on restarts after 75 reached ({self.max_stops})"
            return "restart", None, "saved and stopped"
        self.crashes = [t for t in self.crashes if now - t <= self.crash_window_s] + [now]
        if len(self.crashes) >= self.crash_n:
            return "stop", EXIT_FATAL, f"crash loop: {len(self.crashes)} crashes in {int(self.crash_window_s)} s"
        if crash_restarts >= self.max_restarts:
            return "stop", EXIT_FATAL, f"limit on restarts after a crash reached ({self.max_restarts})"
        return "restart", None, "crash: retry"

    def run(self) -> int:
        old = {s: signal.signal(s, self._forward) for s in HANDLED}
        restarts = crash_restarts = stop_restarts = 0
        emit("supervisor.started", cmd=self.cmd, max_restarts=self.max_restarts, max_stops=self.max_stops,
             crash_n=self.crash_n, crash_window_s=self.crash_window_s)
        try:
            while True:
                if self.stopping:      # a stop signal before the first start or during the backoff
                    row = {"attempt": restarts, "pid": None, "rc": None, "meaning": "not started",
                           "action": "stop", "reason": "told to stop before this attempt started; no trainer "
                           "started", "seconds": 0.0, "exit": EXIT_RETRY}
                    self._log(row)
                    emit("supervisor.stopped", **row)
                    return EXIT_RETRY
                start = time.time()
                env = dict(os.environ, V5_RESTART_COUNT=str(restarts))
                # own session: only the signals we pass on reach the trainer (not a terminal's Ctrl-C twice)
                self.child = subprocess.Popen(self.cmd, env=env, start_new_session=POSIX)
                emit("supervisor.child_started", attempt=restarts, pid=self.child.pid)
                if self.on_start:
                    self.on_start(self.child, restarts)
                rc = self.child.wait()
                end = time.time()
                action, code, reason = self._decide(rc, crash_restarts, stop_restarts, end)
                row = {"attempt": restarts, "pid": self.child.pid, "rc": rc, "meaning": meaning(rc),
                       "action": action, "reason": reason, "seconds": round(end - start, 3)}
                if action == "restart":
                    ck = last_complete(self.run_url) if self.run_url else None
                    row["pointer_step"] = ck.get("step", 0) if ck else 0
                    row["pointer"] = ck
                    self._log(row)
                    emit("supervisor.restart", **row)
                    restarts += 1
                    if rc == EXIT_RETRY:
                        stop_restarts += 1
                    else:
                        crash_restarts += 1
                    self._sleep(self.backoff_s)
                    continue
                row["exit"] = code
                self._log(row)
                emit("supervisor.done" if code == EXIT_DONE else "supervisor.stopped", **row)
                return code
        finally:
            for s, h in old.items():
                signal.signal(s, h)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--" not in argv:
        print("usage: supervisor.py [options] -- <trainer command>", file=sys.stderr)
        return 2
    i = argv.index("--")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--max-restarts", type=int, default=10, help="most restarts after a crash (default 10)")
    ap.add_argument("--max-stops", type=int, default=100, help="most restarts after exit 75 (default 100)")
    ap.add_argument("--backoff", type=float, default=5.0, help="seconds to wait before a restart (default 5)")
    ap.add_argument("--log", default=None, help="append one JSON line per child exit here")
    ap.add_argument("--run-url", default=None,
                    help="checkpoint folder of the run, only to log the restart step "
                         "(default: $V5_REMOTE_ROOT/$RUN_ID when both are set)")
    a = ap.parse_args(argv[:i])
    cmd = argv[i + 1:]
    if not cmd:
        ap.error("no trainer command after --")
    run_url = a.run_url
    if run_url is None and os.environ.get("V5_REMOTE_ROOT") and os.environ.get("RUN_ID"):
        run_url = os.environ["V5_REMOTE_ROOT"].rstrip("/") + "/" + os.environ["RUN_ID"]
    return Supervisor(cmd, run_url=run_url, log_path=a.log, max_restarts=a.max_restarts,
                      max_stops=a.max_stops, backoff_s=a.backoff).run()


if __name__ == "__main__":
    sys.exit(main())
