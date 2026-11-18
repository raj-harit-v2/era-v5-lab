#!/usr/bin/env python3
"""Score each new lab checkpoint and load its eval-mini v1 result into ClickHouse (week-3 work order, task 1).

In simple words: the watcher follows one run in the checkpoint store. Each time Team 7's checkpointer commits a
checkpoint (a new line in ``commits.jsonl``), the watcher scores that step with ``run_lab_ckpt.py`` in its own
process and loads the result into Team 8's ``eval_mini`` table. Nobody has to start an eval by hand.

    # CPU test on Team 7's tiny store (no ClickHouse needed: --no-load only parses the rows)
    python teams/07-infrastructure/jobs/restore_test/restore_test.py
    python teams/09-evaluation/harness_lab/eval_watcher.py \\
        --run-dir teams/07-infrastructure/jobs/restore_test/out/ckpt_store/restore-b --once --no-load

    # dry run 1, on the eval slot (never on a training node): Tier A on every commit, polled every 60 s, until the
    # run's final checkpoint is scored. Arguments after -- go to run_lab_ckpt.py and its scorer unchanged.
    python teams/09-evaluation/harness_lab/eval_watcher.py --run-dir <remote_root>/<run_id> --label tier-a --until-final \\
        --scorer lm_eval_lab:team5 --clickhouse-url http://<host>:8123 -- --device cuda --tier A \\
        --model-config <arm.yaml> --tokenizer <tokenizer.json> --tokenizer-sha256 <sha256> --byte-table <table.npz> \\
        --hf-home <HF cache> --offline

    # Tier B on every 10th commit (TSAI, #357): a second watcher with its own label; both share one GPU slot lock
    python teams/09-evaluation/harness_lab/eval_watcher.py --run-dir <remote_root>/<run_id> --label tier-b --every 10 --until-final \\
        --scorer lm_eval_lab:team5 --clickhouse-url http://<host>:8123 -- --device cuda --tier B <same inputs>

    # dry run 1 (TSAI on #475: finished, p1536, one final checkpoint): a Team 5 train_week2.py run folder. Its one
    # checkpoint is scored once summary.json says COMPLETED, then the watcher exits. Run once per tier.
    python teams/09-evaluation/harness_lab/eval_watcher.py --team5-run ./out/dryrun1-1234 --label tier-a \\
        --scorer lm_eval_lab:team5 --clickhouse-url http://<host>:8123 -- --device cuda --tier A \\
        --model-config ./out/dryrun1-1234/manifest.json --tokenizer <p1536 tokenizer.json> \\
        --tokenizer-sha256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b \\
        --byte-table teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz --hf-home <HF cache> --offline

Rules it keeps (results/eval_mini_v1_schema.md section 6; Team 7 docs/checkpoint_design_v0.md sections 5 and 8,
docs/checkpoint_interval.md):

- It reads ``commits.jsonl``, never a directory listing. Team 7 appends a line there only after MANIFEST.json and
  the conditional write of latest.json, so every complete line is a committed checkpoint. A line without its
  newline is an append still in flight; it is read on the next poll. A poll is one stat call until the file grows.
- It is read-only on the store. It writes only its own out folder (results, logs, state) and the slot lock.
- One process per checkpoint: a crash, a leak or an out-of-memory error while scoring cannot stop the watcher, and
  the scorer's memory (GPU too) is freed after each checkpoint. On Linux the scorer gets its own process group, and a
  timeout or a stop ends the whole group.
- One scorer at a time per GPU slot: every watcher takes the slot lock (default ``out/watcher/gpu_slot.lock``) around
  a scorer run, so the Tier A and Tier B watchers never load two models at once.
- Each checkpoint loads under its own ClickHouse ``run_id``: ``<run>:<commit path>:<label>:<model_revision[:12]>``.
  ``load_jsonl.py`` deletes every row of a run_id before it inserts (its idempotent reload), so a shared run_id would
  delete the scores of other checkpoints, other tiers or another run with the same name.
- ``--every N`` scores commit number N, 2N, 3N ... of commits.jsonl, the count Team 7's retention uses for
  ``protect_every`` ((i + 1) % N == 0). With N equal to protect_every, retention never deletes a checkpoint before it
  is scored. Dry run 1 retention is ``--keep 9 --protect-every 15`` at a 600 s interval, so an unprotected checkpoint
  stays about 90 minutes.
- ``run_lab_ckpt.py --step N`` scores the last commits.jsonl line of step N. When a restore commits the same step
  again, the older commit is marked ``superseded`` and only the newer one is scored.
- A checkpoint whose MANIFEST.json is gone (deleted by retention before or while it was scored) is marked ``gone``,
  but only while commits.jsonl can still be read, so a store that drops out for a while marks nothing.
- A scoring failure is retried on the next poll, ``--max-attempts`` times in all (default 2, as in JOB_REQUEST.md
  rule 5). A ClickHouse failure keeps the scored file and retries only the load.
- The time per checkpoint (the scorer's wall time) and the lag from commit to score are printed and kept in the
  state file, and summed up at the end. Each checkpoint's log is appended to, so a retry keeps the first attempt.
- With ``--until-final`` it exits by itself once the run's final checkpoint (reason "final") is committed and every
  owned commit is done. Otherwise it runs until a signal: SIGTERM saves the state and exits 75, and a restart goes on.

Exit codes (Team 7's contract: 0 done, 75 run again, 78 fatal): 0 all owned commits are done; 1 a checkpoint
failed ``--max-attempts`` times (see the state file and its log); 75 stopped by a signal, the store could not be
read, or work is left that a rerun can finish; 78 fatal (bad arguments, no run folder, a bad commits.jsonl line,
a state file of another run or label, or another watcher holds the state file).
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAMS = HERE.parents[1]
RUN_LAB_CKPT = HERE / "run_lab_ckpt.py"
LOAD_JSONL = TEAMS / "08-monitoring" / "clickhouse" / "load_jsonl.py"
sys.path.insert(0, str(TEAMS / "07-infrastructure"))
from common.events import emit  # noqa: E402  stdlib only; one JSON line per event when V5_EVENTS_DIR is set

STATE_VERSION = 1
MANIFEST = "MANIFEST.json"
EXIT_OK, EXIT_FAILED, EXIT_RETRY, EXIT_FATAL = 0, 1, 75, 78
TIMEOUT_CODE = 124          # returned for a scorer that ran past --timeout (as coreutils `timeout` does)
FINAL = frozenset({"gone", "superseded", "failed"})   # statuses that never need more work
POSIX = os.name != "nt"


class Stopped(Exception):
    """SIGINT or SIGTERM arrived while a checkpoint was being scored or was waiting for the slot."""


class StoreUnavailable(Exception):
    """commits.jsonl cannot be read now (store or mount down); nothing is decided until it can."""


def fatal(message: str) -> SystemExit:
    print(f"eval_watcher: {message}", file=sys.stderr)
    return SystemExit(EXIT_FATAL)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def tail(path: Path, n_bytes: int = 4096) -> str:
    """The end of a log, without reading the whole file."""
    try:
        with open(path, "rb") as f:
            f.seek(max(0, f.seek(0, os.SEEK_END) - n_bytes))
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


# ---- the store: commits.jsonl ---------------------------------------------------------------------------------------

class CommitLog:
    """``<run_dir>/commits.jsonl``, parsed again only when its size or mtime changes (a poll is one stat call)."""

    def __init__(self, run_dir: Path):
        self.path = run_dir / "commits.jsonl"
        self._sig: tuple[int, int] | None = None
        self._commits: list[dict] = []

    def read(self) -> list[dict]:
        try:
            st = self.path.stat()
        except FileNotFoundError:
            if self._commits:
                raise StoreUnavailable(f"{self.path} is gone after {len(self._commits)} line(s) were read") from None
            return []  # nothing committed yet
        except OSError as e:
            raise StoreUnavailable(f"{self.path}: {e}") from None
        sig = (st.st_size, st.st_mtime_ns)
        if sig != self._sig:
            try:
                raw = self.path.read_bytes()
            except OSError as e:
                raise StoreUnavailable(f"{self.path}: {e}") from None
            complete = raw[: raw.rfind(b"\n") + 1]  # Team 7 writes line + newline in one write; drop a torn tail
            commits = []
            for number, line in enumerate(complete.splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    c = json.loads(line)
                    if not (isinstance(c, dict) and isinstance(c.get("step"), int) and isinstance(c.get("path"), str)):
                        raise ValueError("no integer step or no string path")
                except ValueError as e:  # json.JSONDecodeError is a ValueError
                    raise fatal(f"{self.path} line {number} is not a commit ({e}): {line[:200]!r}") from None
                commits.append(c)
            if len(commits) < len(self._commits):  # Team 7 only appends
                raise StoreUnavailable(f"{self.path} shrank from {len(self._commits)} to {len(commits)} lines")
            self._commits, self._sig = commits, sig
        return self._commits


class Team5Run:
    """A Team 5 ``train_week2.py`` run folder (dry run 1): one checkpoint, ``checkpoint.pt``, written before
    ``summary.json``. It reads as one commit with reason "final" once ``summary.json`` says COMPLETED, so the watcher
    loop, the slot lock, the state, the run_id rule and the exit codes stay the same as for a Team 7 store."""

    CHECKPOINT = "checkpoint.pt"

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.path = run_dir / "summary.json"

    def read(self) -> list[dict]:
        try:
            raw = self.path.read_bytes()
            mtime = self.path.stat().st_mtime
        except FileNotFoundError:
            return []  # the run has not finished yet
        except OSError as e:
            raise StoreUnavailable(f"{self.path}: {e}") from None
        try:
            summary = json.loads(raw)
        except ValueError:
            return []  # summary.json is written in one call; a partial read is retried on the next poll
        status, steps = summary.get("status"), summary.get("steps")
        if status != "COMPLETED":
            raise fatal(f"{self.path}: status {status!r}; only a COMPLETED run is scored (Team 5: anything else is "
                        "not a result)")
        if not isinstance(steps, int) or not isinstance(summary.get("final_model_sha256"), str):
            raise fatal(f"{self.path}: no integer steps or no final_model_sha256")
        return [{"step": steps, "branch": "main", "epoch": None, "path": self.CHECKPOINT, "reason": "final",
                 "time": mtime}]


def owned(commits: list[dict], every: int, from_step: int):
    """(ordinal, commit, superseded) for each commit this watcher scores, oldest first.

    ordinal is the 1-based line number in commits.jsonl (Team 7 retention counts the same way). A commit is
    superseded when a later line commits the same step again: run_lab_ckpt.py --step scores the last one.
    """
    last_path = {c["step"]: c["path"] for c in commits}
    for ordinal, c in enumerate(commits, 1):
        if ordinal % every == 0 and c["step"] >= from_step:
            yield ordinal, c, last_path[c["step"]] != c["path"]


# ---- state and locks ------------------------------------------------------------------------------------------------

class State:
    """One JSON file, written atomically. It belongs to one run folder and one label."""

    def __init__(self, path: Path, run_dir: str, label: str, every: int):
        self.path, self.head = path, {"run_dir": run_dir, "label": label, "every": every}
        self.items: dict[str, dict] = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("version") != STATE_VERSION:
                raise fatal(f"{path}: state version {data.get('version')!r}, this watcher reads {STATE_VERSION}")
            for key, want in self.head.items():
                if data.get(key) != want:
                    raise fatal(f"{path} has {key} {data.get(key)!r}, not {want!r}; use another --out-dir or --state")
            self.items = data["checkpoints"]

    def save(self) -> None:
        data = json.dumps({"version": STATE_VERSION, **self.head, "checkpoints": self.items},
                          indent=1, sort_keys=True).encode("utf-8")
        tmp = self.path.with_name(self.path.name + ".tmp")
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)  # atomic: a crash leaves the old state or the new one, never half of one


class FileLock:
    """An exclusive OS lock on a file. The OS releases it when the handle closes or the process dies, so a crash
    leaves no stale lock."""

    def __init__(self, path: Path):
        self.path = path
        self._f = None

    def try_acquire(self) -> bool:
        f = open(self.path, "a+b")
        try:
            if POSIX:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            f.close()
            return False
        self._f = f
        return True

    def release(self) -> None:
        if self._f is not None:
            self._f.close()  # closing the handle releases the lock on both systems
            self._f = None


class StateLock(FileLock):
    """One watcher per state file."""

    def __init__(self, state_path: Path):
        super().__init__(state_path.with_name(state_path.name + ".lock"))

    def __enter__(self):
        if not self.try_acquire():
            raise fatal(f"another watcher holds {self.path}")
        return self

    def __exit__(self, *exc):
        self.release()


# ---- scoring and loading --------------------------------------------------------------------------------------------

def _end(proc: subprocess.Popen) -> None:
    """Stop a scorer and, on Linux, everything it started (its own process group)."""
    def send(sig):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            pass

    send(signal.SIGTERM) if POSIX else proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        send(signal.SIGKILL) if POSIX else proc.kill()
        proc.wait()


def run_scorer(argv: list[str], log_path: Path, timeout: float, stop: threading.Event) -> int:
    """Run one scorer process; stdout and stderr go straight to log_path (nothing is held in memory). The log is
    appended to, so a retry keeps the first attempt's output (JOB_REQUEST.md rule 5 sends both back to the team)."""
    with open(log_path, "ab") as log:
        log.write(f"=== {now_utc()}\n$ {subprocess.list2cmdline(argv)}\n".encode("utf-8"))
        log.flush()
        proc = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=POSIX)
        deadline = time.monotonic() + timeout
        while True:
            try:
                code = proc.wait(timeout=1.0)
                if POSIX:  # a child the scorer left behind would keep its GPU memory
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
                return code
            except subprocess.TimeoutExpired:
                if stop.is_set() or time.monotonic() > deadline:
                    _end(proc)
                    if stop.is_set():
                        raise Stopped() from None
                    log.write(f"\neval_watcher: stopped after --timeout {timeout:g} s\n".encode("utf-8"))
                    return TIMEOUT_CODE


@functools.cache
def loader():
    """Team 8's load_jsonl.py (no package, so loaded by path; stdlib only)."""
    spec = importlib.util.spec_from_file_location("load_jsonl", LOAD_JSONL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_output(out: Path, commit: dict) -> tuple[int, str]:
    """The file must score exactly this commit. Returns the number of records and the model_revision."""
    records = json.loads(out.read_text(encoding="utf-8"))["records"]
    if not records:
        raise ValueError(f"{out}: no records")
    revisions = {r.get("model_revision") for r in records}
    if len(revisions) != 1 or not all(isinstance(x, str) and x for x in revisions):
        raise ValueError(f"{out}: records name {len(revisions)} model_revision(s), expected one")
    for r in records:
        ck = r.get("checkpoint") or {}
        if ck.get("step") != commit["step"] or not str(ck.get("path", "")).endswith("/" + commit["path"]):
            raise ValueError(f"{out}: scored {ck.get('path')} step {ck.get('step')}, expected "
                             f"{commit['path']} step {commit['step']}")
    return len(records), revisions.pop()


class Watcher:
    def __init__(self, a: argparse.Namespace, stop: threading.Event):
        self.a, self.stop = a, stop
        self.team5 = a.team5_run is not None
        self.run_dir = Path(a.team5_run if self.team5 else a.run_dir).resolve()
        self.run_name = a.run_name or self.run_dir.name
        self.log = Team5Run(self.run_dir) if self.team5 else CommitLog(self.run_dir)
        self.state = State(a.state, self.run_dir.as_posix(), a.label, a.every)
        self.slot = FileLock(a.slot_lock)
        self.commits: list[dict] = []    # the last commits.jsonl read that succeeded
        self.unavailable: str | None = None
        self.session: list[tuple[float, float | None]] = []   # (scorer seconds, lag after commit) of this process
        (a.out_dir / "logs").mkdir(parents=True, exist_ok=True)

    def argv(self, commit: dict, out: Path) -> list[str]:
        source = (["--team5-run", self.a.team5_run] if self.team5 else
                  ["--run-dir", self.a.run_dir, "--step", str(commit["step"])])
        cmd = [self.a.python, str(RUN_LAB_CKPT), *source, "--out", str(out), "--scorer", self.a.scorer]
        if self.a.run_name:
            cmd += ["--run-name", self.a.run_name]
        return cmd + self.a.scorer_args

    def read_commits(self) -> list[dict]:
        commits = self.log.read()
        if not commits and self.state.items:
            raise StoreUnavailable(f"{self.log.path} not found, but the state holds {len(self.state.items)} checkpoint(s)")
        self.commits, self.unavailable = commits, None
        return commits

    def store_down(self, why: str) -> None:
        if self.unavailable != why:  # say it once, not on every poll
            print(f"eval_watcher: store unavailable, nothing decided until it is back: {why}", file=sys.stderr,
                  flush=True)
            emit("eval.store_unavailable", detail=why[:500])
        self.unavailable = why

    def manifest_gone(self, key: str) -> bool:
        """True only if the checkpoint (a store commit's MANIFEST.json, or a Team 5 run's checkpoint.pt) is missing
        while commits.jsonl (summary.json) is still readable (else the store is down)."""
        if (self.run_dir / key if self.team5 else self.run_dir / key / MANIFEST).exists():
            return False
        if not self.log.path.exists():
            raise StoreUnavailable(f"{self.log.path} vanished while {key} was checked")
        return True

    def poll(self) -> None:
        """One pass over the owned commits, oldest first. Saves the state after each change."""
        try:
            for ordinal, commit, superseded in owned(self.read_commits(), self.a.every, self.a.from_step):
                if self.stop.is_set():
                    return
                key = commit["path"]
                rec = self.state.items.get(key)
                if rec is None:
                    rec = self.state.items[key] = {"step": commit["step"], "branch": commit.get("branch"),
                                                   "epoch": commit.get("epoch"), "ordinal": ordinal, "attempts": 0}
                status = rec.get("status")
                if status in FINAL or (status == "scored" and (rec["loaded"] or self.a.no_load)):
                    continue
                if status != "scored":
                    if superseded:
                        self.finish(rec, "superseded", f"step {commit['step']} was committed again later")
                        continue
                    if self.manifest_gone(key):
                        self.finish(rec, "gone", f"{key}/{MANIFEST} not found (deleted by retention before scoring)")
                        continue
                    if not self.score(commit, rec):
                        continue
                self.load(commit, rec)
        except StoreUnavailable as e:
            self.store_down(str(e))

    def finish(self, rec: dict, status: str, why: str) -> None:
        rec.update(status=status, detail=why, time=now_utc())
        self.state.save()
        emit("eval.skipped", step=rec["step"], status=status, detail=why)
        print(f"step {rec['step']}: {status} ({why})", flush=True)

    def take_slot(self) -> float:
        """Wait for the GPU slot; returns the seconds waited. A stop while waiting raises Stopped."""
        t0, said = time.monotonic(), False
        while not self.slot.try_acquire():
            if not said:
                print(f"waiting for the GPU slot ({self.slot.path})", flush=True)
                said = True
            if self.stop.wait(1.0):
                raise Stopped()
        return round(time.monotonic() - t0, 2)

    def score(self, commit: dict, rec: dict) -> bool:
        stem = commit["path"].replace("/", "__")
        out = self.a.out_dir / f"{stem}.json"
        log_path = self.a.out_dir / "logs" / f"{stem}.log"
        out.unlink(missing_ok=True)  # a file left by an earlier attempt must never pass for this one
        waited = self.take_slot()
        try:
            t0 = time.monotonic()
            code = run_scorer(self.argv(commit, out), log_path, self.a.timeout, self.stop)  # Stopped propagates
            seconds = round(time.monotonic() - t0, 2)
        finally:
            self.slot.release()
        rec["attempts"] += 1
        error = None
        if code != 0:
            error = f"run_lab_ckpt.py exit {code}" + (" (timeout)" if code == TIMEOUT_CODE else "")
        else:
            try:
                rec["records"], revision = check_output(out, commit)
            except (OSError, ValueError, KeyError) as e:
                error = str(e)
        if error:
            try:
                gone = self.manifest_gone(commit["path"])
            except StoreUnavailable:
                rec["attempts"] -= 1  # the store dropped out: this attempt says nothing about the checkpoint
                raise
            if gone:  # retention deleted it while it was being scored: not a failure of the checkpoint
                self.finish(rec, "gone", f"{commit['path']}/{MANIFEST} deleted while it was scored ({error})")
                return False
            final = rec["attempts"] >= self.a.max_attempts
            rec.update(status="failed" if final else "error", detail=error, log=log_path.as_posix(),
                       seconds=seconds, time=now_utc())
            self.state.save()
            emit("eval.failed", step=commit["step"], path=commit["path"], attempt=rec["attempts"], final=final,
                 detail=error, seconds=seconds)
            print(f"step {commit['step']}: {error}, attempt {rec['attempts']}/{self.a.max_attempts}"
                  f"{' (giving up)' if final else ''}; log {log_path}\n{tail(log_path)}", file=sys.stderr, flush=True)
            return False
        committed = commit.get("time")
        lag = round(time.time() - committed, 1) if isinstance(committed, (int, float)) and committed > 0 else None
        rec.update(status="scored", loaded=False, out=out.as_posix(), sha256=sha256_file(out), log=log_path.as_posix(),
                   seconds=seconds, slot_wait_s=waited, lag_s=lag, time=now_utc(), detail=None,
                   run_id=f"{self.run_name}:{commit['path']}:{self.a.label}:{revision[:12]}")
        self.state.save()
        self.session.append((seconds, lag))
        emit("eval.scored", step=commit["step"], path=commit["path"], records=rec["records"], seconds=seconds,
             slot_wait_s=waited, lag_s=lag, label=self.a.label)
        print(f"step {commit['step']} ({commit['path']}): scored in {seconds} s"
              f"{'' if lag is None else f', {lag} s after its commit'}, {rec['records']} record(s) -> {out}", flush=True)
        return True

    def load(self, commit: dict, rec: dict) -> None:
        t0 = time.monotonic()
        try:
            if self.a.no_load:  # parse exactly as the load would, but write nothing
                info = loader().parse_source(rec["out"], run_id_override=rec["run_id"])
            else:
                info = loader().load_source(rec["out"], run_id_override=rec["run_id"], url=self.a.clickhouse_url)
            if info["target_table"] != "eval_mini" or info["metric_rows"] != rec["records"]:
                raise ValueError(f"loader read {info['metric_rows']} row(s) into {info['target_table']}, "
                                 f"expected {rec['records']} into eval_mini")
        except Exception as e:  # noqa: BLE001 - ClickHouse down, HTTP error, bad file: keep the score, retry the load
            rec["load_error"] = f"{type(e).__name__}: {e}"[:500]
            self.state.save()
            emit("eval.load_failed", step=commit["step"], path=commit["path"], detail=rec["load_error"])
            print(f"step {commit['step']}: load failed, retried next poll: {rec['load_error']}", file=sys.stderr,
                  flush=True)
            return
        seconds = round(time.monotonic() - t0, 2)
        rec.update(loaded=not self.a.no_load, load_error=None, load_seconds=seconds)
        self.state.save()
        verb = "parsed (--no-load)" if self.a.no_load else f"loaded into eval_mini at {self.a.clickhouse_url}"
        emit("eval.loaded", step=commit["step"], path=commit["path"], run_id=rec["run_id"], rows=info["metric_rows"],
             dry_run=self.a.no_load, seconds=seconds)
        print(f"step {commit['step']}: {info['metric_rows']} row(s) {verb} as run_id {rec['run_id']} in {seconds} s",
              flush=True)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for _, c, _ in owned(self.commits, self.a.every, self.a.from_step):
            r = self.state.items.get(c["path"]) or {}
            s = r.get("status", "pending")
            s = "loaded" if s == "scored" and r.get("loaded") else ("parsed" if s == "scored" and self.a.no_load else s)
            out[s] = out.get(s, 0) + 1
        return out

    def outcome(self) -> int:
        """Exit code from the state of every owned commit (see the module docstring)."""
        if self.unavailable:
            return EXIT_RETRY
        items = [self.state.items.get(c["path"]) for _, c, _ in owned(self.commits, self.a.every, self.a.from_step)]
        if any(r is None or r.get("status") not in FINAL | {"scored"} or (r.get("status") == "scored"
               and not (r["loaded"] or self.a.no_load)) for r in items):
            return EXIT_RETRY
        return EXIT_FAILED if any(r["status"] == "failed" for r in items) else EXIT_OK

    def run_ended(self) -> bool:
        """The run committed its final checkpoint (Team 7's trainer saves it with reason "final") and every commit this
        watcher owns is done."""
        return any(c.get("reason") == "final" for c in self.commits) and self.outcome() in (EXIT_OK, EXIT_FAILED)

    def timing(self) -> str:
        """Time per checkpoint in this process: the scorer's wall time, and the lag from commit to score."""
        if not self.session:
            return "no checkpoint scored in this run"
        secs = [s for s, _ in self.session]
        lags = [x for _, x in self.session if x is not None]
        text = (f"{len(secs)} checkpoint(s) scored, {sum(secs) / len(secs):.1f} s mean and {max(secs):.1f} s max "
                f"per checkpoint")
        return text + (f", lag after commit {max(lags):.1f} s max" if lags else "")


# ---- command line ---------------------------------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__, allow_abbrev=False)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--run-dir",
                        help="<remote_root>/<run_id> on a local or mounted path: the folder with commits.jsonl")
    source.add_argument("--team5-run",
                        help="a Team 5 train_week2.py run folder (manifest.json, checkpoint.pt, summary.json), as dry "
                             "run 1 left it: its one checkpoint is scored once summary.json says COMPLETED, then the "
                             "watcher exits (implies --until-final)")
    ap.add_argument("--every", type=int, default=1,
                    help="score commit N, 2N, ... (Tier B: 10, TSAI on #357). The count Team 7 retention's "
                         "--protect-every uses; dry run 1 protects every 15th and keeps the newest 9")
    ap.add_argument("--from-step", type=int, default=0, help="ignore commits before this step")
    ap.add_argument("--scorer", default="smoke", help="passed to run_lab_ckpt.py --scorer (smoke, lm_eval_lab:team5)")
    ap.add_argument("--label", help="names this watcher's results, state and ClickHouse run_ids, e.g. tier-a "
                                    "(default: the scorer, plus a hash of the arguments after --)")
    ap.add_argument("--run-name", help="passed to run_lab_ckpt.py --run-name (queue jobs: <job_run_id>/<arm>)")
    ap.add_argument("--python", default=sys.executable, help="interpreter of the scoring environment")
    ap.add_argument("--out-dir", type=Path, help="results, logs and state (default: out/watcher/<run>.<label>.every<N>)")
    ap.add_argument("--state", type=Path, help="state file (default: <out-dir>/state.json)")
    ap.add_argument("--slot-lock", type=Path,
                    help="lock file shared by every watcher on one GPU slot (default: gpu_slot.lock next to the out "
                         "folder, so watchers with default out folders share it)")
    ap.add_argument("--clickhouse-url", default=os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8123"))
    ap.add_argument("--no-load", action="store_true", help="parse the rows with load_jsonl.py but write nothing; "
                                                           "a later run without it loads the stored results")
    ap.add_argument("--interval", type=float, default=60.0, help="seconds between polls")
    ap.add_argument("--timeout", type=float, default=1800.0,
                    help="seconds before one scorer process is stopped as hung (default 1,800). A checkpoint should "
                         "score within Team 7's save interval (600 s in dry run 1); the printed time per checkpoint "
                         "shows whether it does")
    ap.add_argument("--max-attempts", type=int, default=2, help="scoring attempts per checkpoint")
    ap.add_argument("--once", action="store_true", help="one pass, then exit (tests, catch-up)")
    ap.add_argument("--until-final", action="store_true",
                    help="exit once the run's final commit (reason \"final\") is in commits.jsonl and every owned "
                         "commit is done, so a job ends by itself")
    ap.add_argument("scorer_args", nargs=argparse.REMAINDER, help="after --: passed to run_lab_ckpt.py unchanged")
    a = ap.parse_args(argv)
    if a.scorer_args[:1] == ["--"]:
        a.scorer_args = a.scorer_args[1:]
    for name in ("every", "max_attempts"):
        if getattr(a, name) < 1:
            ap.error(f"--{name.replace('_', '-')} must be 1 or more")
    if a.interval <= 0 or a.timeout <= 0:
        ap.error("--interval and --timeout must be above 0")
    if a.team5_run is not None:
        if a.every != 1:
            ap.error("--team5-run has one checkpoint: --every must be 1")
        a.until_final = True
    run_dir = Path(a.team5_run if a.team5_run is not None else a.run_dir)
    if not run_dir.is_dir():
        raise fatal(f"{'--team5-run' if a.team5_run is not None else '--run-dir'} {run_dir} is not a folder")
    if a.label is None:
        a.label = re.sub(r"[^A-Za-z0-9_.-]+", "_", a.scorer)
        if a.scorer_args:
            a.label += "-" + hashlib.sha256("\0".join(a.scorer_args).encode("utf-8")).hexdigest()[:8]
    elif not re.fullmatch(r"[A-Za-z0-9_.-]+", a.label):
        ap.error("--label may hold only letters, digits, '_', '.' and '-'")
    a.out_dir = (a.out_dir or HERE / "out" / "watcher" / f"{run_dir.resolve().name}.{a.label}.every{a.every}").resolve()
    a.state = (a.state or a.out_dir / "state.json").resolve()
    a.slot_lock = (a.slot_lock or a.out_dir.parent / "gpu_slot.lock").resolve()
    return a


def main(argv=None) -> int:
    a = parse_args(argv)
    for folder in (a.out_dir, a.state.parent, a.slot_lock.parent):
        folder.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    with StateLock(a.state):
        w = Watcher(a, stop)
        emit("eval.watcher_started", run_dir=w.run_dir.as_posix(), every=a.every, scorer=a.scorer, label=a.label,
             once=a.once, load=not a.no_load)
        print(f"watching {w.run_dir} (label {a.label}, every {a.every}, scorer {a.scorer}, "
              f"{'no load' if a.no_load else a.clickhouse_url}); out {a.out_dir}", flush=True)
        try:
            while True:
                w.poll()
                if a.once or stop.is_set():
                    break
                if a.until_final and w.run_ended():
                    print("the run committed its final checkpoint and every owned commit is done", flush=True)
                    break
                stop.wait(a.interval)
        except Stopped:
            print("stopped: the checkpoint in progress is scored again on the next start", file=sys.stderr)
        code = EXIT_RETRY if stop.is_set() else w.outcome()
        counts = w.counts()
        emit("eval.watcher_stopped", exit_code=code, **counts)
        print(f"time: {w.timing()}", flush=True)
        print(f"done: {json.dumps(counts, sort_keys=True)}; exit {code}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
