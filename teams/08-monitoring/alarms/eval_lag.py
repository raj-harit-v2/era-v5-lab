#!/usr/bin/env python3
"""Eval-watcher lag alarm: page when Team 9's Tier A scores fall behind training (week 4, Team 08 task 1).

Rule (`teams/09-evaluation/eval_schedule.md` section 6): page when a run's newest Tier A score in `eval_mini` is for
a step more than 2 checkpoint intervals of training older than the run's newest training step. At dry run 2's
600 s interval (#720) the limit is 1,200 s. Normal worst case: up to 600 s until the next commit, then Tier B and
Tier A on the shared eval slot (about 159 s + 207 s, `eval_schedule.md` section 3), then the load: about 1,000 s.
So the alarm pages when one Tier A score lands more than about 600 s after its commit, or when the watcher stops.
If Tier A runs on every k-th commit only, pass `--intervals k+1`.

Usage (dry run 2; the kill drill restarts the trainer with a fresh --out, so `watch_jsonl.py` may load the resumed
segments under their folder names; each one is mapped to the run the eval watcher scores):
    python -I teams/08-monitoring/alarms/eval_lag.py --interval-s 600 --run dryrun2-1234 \\
        --run dryrun2-1234-resume-a=dryrun2-1234 --run dryrun2-1234-resume-b=dryrun2-1234 --poll 60
    python -I teams/08-monitoring/alarms/eval_lag.py --interval-s 600 --once      # one check, exit 1 on a page

Where the numbers come from
- Training: `ingest_batches`, written by `clickhouse/watch_jsonl.py` while it streams a growing `metrics.jsonl`.
  `seen_at` is the wall-clock time a batch of lines was read, `first_step` and `last_step` are its steps. Not
  `metrics_raw.time`: Team 05's trainer writes no time field, so `load_jsonl.py` stores an invented time
  (28 Oct 2026 plus one second per line).
- Eval: `eval_mini` rows whose run_id holds `:tier-a:` (the watcher writes `<run>:<commit>:<label>:<rev>`), per
  `checkpoint_run` (the run id in Team 07's manifest, which is the trainer's --run-id, #606). Tier B rows (every
  10th commit) and Tier C rows don't count.

How the lag is measured
- The lag is the training time from the batch that reached the newest Tier A step to the newest batch.
- Restore: a batch whose first step is at or below the last step before it means the trainer went back to its
  commit at step R. The training after R was lost: it and the downtime don't count, so a planned failure doesn't
  page. The training up to R still counts, so a restore doesn't wipe out a lag that was building: a dead watcher
  still pages on time, and only once. While training is behind the newest Tier A step, the lag is 0.
- Pause: a gap between two batches counts as at most --pause-s (default: half an interval), so a stalled trainer
  is not reported as an eval problem (`continuity_rules.py` loader_stall covers stalls).
- No Tier A row yet: the lag runs from the run's first batch, so with --run, a run whose watcher never started pages
  2 intervals in.
- Batches of blank lines (stored as steps 0..0) are ignored.

When it pages
- Only while the run trains: its newest batch is at most --live-s old (default: the limit). A run that finished or
  died stays quiet. A run that ends with its last commit unscored is not paged; the watcher's exit code covers it.
- Once per episode, like `continuity_rules.LoaderStallMonitor`: the page fires when the lag first goes over the
  limit, and re-arms when it drops back or the run stops. A restarted alarm pages an ongoing lag once more.
- Which runs: with --run TRAIN_RUN[=EVAL_RUN] (repeatable; several training run ids may share one eval run),
  those. Without --run, each training run whose id has Tier A rows, so unrelated streams never page.

Output
- A page: one JSON line on stdout, in the event shape of `alarms.py` (step, metric, rule, severity, detail).
- Each check: one status line per run on stderr, and one row per run in `eval_lag_checks`
  (`clickhouse/eval_lag_checks.sql`, created on start; --no-write skips it). Grafana shows that table during the run
  (`grafana/private_v1.json` panels 29 to 31); a `checked_at` that stops moving while training goes on means the
  alarm stopped. Each stderr line starts with the UTC time; the first one gives the settings (no password).
- --once exits 0 (no page), 1 (page) or 2 (any error, and no page). --poll keeps going after any error (one that is
  not a ClickHouse error is logged with its traceback) and says how long it has gone without a complete check.

Needs `watch_jsonl.py` streaming the run into the same ClickHouse; without it the run is never seen training.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import http.client
import json
import math
from pathlib import Path
import re
import sys
import time
import traceback
from typing import Callable, Iterable, NamedTuple, Sequence
import urllib.parse

CLICKHOUSE_DIR = Path(__file__).resolve().parents[1] / "clickhouse"
sys.path.insert(0, str(CLICKHOUSE_DIR))
from load_jsonl import DEFAULT_CH_URL, _format_utc, ch_Exec  # noqa: E402
from watch_jsonl import STOP_ERRORS, sql_str  # noqa: E402

TABLE = "eval_lag_checks"
TABLE_SQL = CLICKHOUSE_DIR / f"{TABLE}.sql"
RULE = "eval_lag"
EXIT_OK, EXIT_PAGE, EXIT_ERROR = 0, 1, 2
# A failed check: ClickHouse down, timeout, a bad URL, rejected SQL (RuntimeError, incl. EvalLagError) or an
# unexpected answer. Anything else is a bug and is logged with its traceback.
CHECK_ERRORS = STOP_ERRORS + (OSError, ValueError, http.client.HTTPException)
MISSING_TABLE_HINTS = (
    ("ingest_batches", "is clickhouse/watch_jsonl.py streaming the run into this ClickHouse?"),
    ("eval_mini", "is clickhouse/schema_v1.sql applied (load_jsonl.py creates it)?"),
)

ExecFn = Callable[..., str]  # exec_fn(sql, data=None) -> response text, as in watch_jsonl.Watcher


class EvalLagError(RuntimeError):
    """ClickHouse rejected one of the alarm's queries; the message says the likely reason."""


class Batch(NamedTuple):
    """One `ingest_batches` row: when `watch_jsonl.py` read the lines (UTC ms), and their first and last step."""

    seen_ms: int
    first_step: int
    last_step: int


def active_lag_ms(batches: Sequence[Batch], eval_step: int | None, pause_ms: int) -> int:
    """Training time in ms, not lost to a restore, from the batch that reached `eval_step` to the newest batch.

    `batches` are one run's batches in training order. A batch that starts at or below the last step before it is a
    restore to step R = its first step - 1: the steps after R were lost, so the batches after R are dropped (one that
    straddles R is cut at R), and the gap across the restore (the downtime) counts 0. Every other gap between two
    batches counts as at most `pause_ms`. So a restore neither adds to the lag nor wipes out what built up before R.
    `eval_step` None (no Tier A row yet) measures from the first batch; training behind `eval_step` gives 0.

    Batches with `last_step < eval_step` may be left out, as the alarm does, if the newest batch is kept: within a
    pass steps only grow, so the batches left out come before the one that reached `eval_step`; and after a restore,
    the first batch kept starts at or below `eval_step`, so it is seen as a restore too and cuts the same batches, or
    ones that are cut below `eval_step` and so never start the lag.
    """
    kept: list[tuple[Batch, bool]] = []  # (batch, first batch after a restore)
    for batch in batches:
        restored = bool(kept) and batch.first_step <= kept[-1][0].last_step
        if restored:
            while kept and kept[-1][0].first_step >= batch.first_step:
                kept.pop()  # lost: the trainer redoes these steps after the restore
            if kept and kept[-1][0].last_step >= batch.first_step:
                kept[-1] = (kept[-1][0]._replace(last_step=batch.first_step - 1), kept[-1][1])
        kept.append((batch, restored))
    if not kept or (eval_step is not None and kept[-1][0].last_step < eval_step):
        return 0  # nothing yet, or restored to before the newest scored step: nothing new to score
    start = 0 if eval_step is None else next(i for i, (b, _) in enumerate(kept) if b.last_step >= eval_step)
    return sum(0 if restored else min(max(batch.seen_ms - kept[i - 1][0].seen_ms, 0), pause_ms)
               for i, (batch, restored) in enumerate(kept[start + 1:], start + 1))


def _seconds(ms: int | None) -> float | None:
    return None if ms is None else round(ms / 1000, 1)


def _utc(ms: int | None) -> str | None:
    return None if ms is None else _format_utc(datetime.fromtimestamp(ms / 1000, tz=timezone.utc))


def _sql_list(values: Iterable[str]) -> str:
    return "(" + ", ".join(sql_str(v) for v in sorted(set(values))) + ")"


_TSV_ESCAPE = re.compile(r"\\(.)")
_TSV_ESCAPES = {"b": "\b", "f": "\f", "r": "\r", "n": "\n", "t": "\t", "0": "\0"}


def tsv_fields(line: str) -> list[str]:
    """One line of ClickHouse's TabSeparated output as values: it escapes \\, ', tab, newline and the like."""
    fields = line.split("\t")
    if "\\" not in line:  # nearly every line: numbers and plain run ids
        return fields
    return [_TSV_ESCAPE.sub(lambda m: _TSV_ESCAPES.get(m.group(1), m.group(1)), field) for field in fields]


class RunCheck(NamedTuple):
    """One check of one eval run (with all its training run ids)."""

    run_id: str                  # the eval run: eval_mini.checkpoint_run
    train_runs: tuple[str, ...]  # its run ids in ingest_batches
    train_step: int              # newest training step
    train_seen_ms: int           # when the newest batch was read
    eval_step: int | None        # newest Tier A step; None if there is none yet
    eval_loaded_ms: int | None   # when the newest Tier A row was loaded
    lag_ms: int | None           # None while the run is not training (not checked)
    threshold_ms: int
    label: str
    paged: bool                  # True on the check that pages

    @property
    def live(self) -> bool:
        return self.lag_ms is not None

    @property
    def over(self) -> bool:
        return self.lag_ms is not None and self.lag_ms > self.threshold_ms

    def detail(self) -> str:
        lag, limit = _seconds(self.lag_ms) or 0.0, _seconds(self.threshold_ms)
        if self.eval_step is None:
            return (f"no {self.label} score yet for {self.run_id} after {lag:,.0f} s of training (limit "
                    f"{limit:,.0f} s): is the {self.label} eval watcher running?")
        return (f"{self.label} for {self.run_id} is {lag:,.0f} s of training behind (limit {limit:,.0f} s): newest "
                f"scored step {self.eval_step}, newest training step {self.train_step}. Is the {self.label} eval "
                f"watcher running?")

    def event(self) -> dict:
        return {
            "step": self.train_step, "metric": "eval_mini", "rule": RULE, "severity": "page", "run_id": self.run_id,
            "train_runs": list(self.train_runs), "eval_step": self.eval_step, "lag_s": _seconds(self.lag_ms),
            "threshold_s": _seconds(self.threshold_ms), "eval_loaded_at": _utc(self.eval_loaded_ms),
            "detail": self.detail(),
        }

    def row(self, checked_ms: int) -> dict:
        """The `eval_lag_checks` row of a live check."""
        return {
            "checked_at": _utc(checked_ms), "run_id": self.run_id, "train_runs": list(self.train_runs),
            "train_step": self.train_step, "train_seen_at": _utc(self.train_seen_ms), "eval_step": self.eval_step,
            "eval_loaded_at": _utc(self.eval_loaded_ms), "lag_s": _seconds(self.lag_ms),
            "threshold_s": _seconds(self.threshold_ms), "over_limit": int(self.over), "paged": int(self.paged),
            "detail": self.detail() if self.over else "",
        }

    def status(self, now_ms: int) -> str:
        head = f"eval_lag {self.run_id}: training step {self.train_step}"
        if not self.live:
            return f"{head}, not training (newest batch {(now_ms - self.train_seen_ms) / 1000:,.0f} s ago): not checked"
        state = "PAGE" if self.paged else "over the limit, paged earlier" if self.over else "ok"
        scored = "none" if self.eval_step is None else self.eval_step
        return (f"{head}, {self.label} step {scored}, lag {_seconds(self.lag_ms):,.0f} s of "
                f"{_seconds(self.threshold_ms):,.0f} s: {state}")


class EvalLagMonitor:
    """Checks the lag of every eval run in three reads, however many runs there are.

    `runs` maps training run ids (in `ingest_batches`) to eval run ids (`eval_mini.checkpoint_run`); None checks each
    training run that has Tier A rows under its own id. `check()` only reads; `save()` writes the rows.
    """

    def __init__(
        self,
        exec_fn: ExecFn,
        *,
        interval_s: float,
        intervals: float = 2.0,
        label: str = "tier-a",
        runs: dict[str, str] | None = None,
        live_s: float | None = None,
        pause_s: float | None = None,
        write: bool = True,
    ) -> None:
        for name, value in (("interval_s", interval_s), ("intervals", intervals), ("live_s", live_s),
                            ("pause_s", pause_s)):
            if value is not None and not (math.isfinite(value) and value > 0):
                raise ValueError(f"{name} must be a positive number, got {value!r}")
        if not label or ":" in label:
            raise ValueError(f"label must be non-empty and hold no ':', got {label!r}")
        self._exec = exec_fn
        self.label = label
        self.runs = dict(runs) if runs else None
        self.write = write
        self.threshold_ms = round(intervals * interval_s * 1000)
        self.live_ms = self.threshold_ms if live_s is None else round(live_s * 1000)
        self.pause_ms = round((interval_s / 2 if pause_s is None else pause_s) * 1000)
        self.waiting: tuple[str, ...] = ()  # eval runs named by `runs` with no ingest_batches row yet
        self._fired: set[str] = set()
        self._table_ready = False
        self._unsaved_pages: list[dict] = []  # page rows a failed save could not write

    def check(self, now_ms: int) -> list[RunCheck]:
        """One check of every run. Raises on a ClickHouse error, before any page state changes."""
        trains = self._newest_batches()
        evals = self._newest_scores()
        groups = self._groups(trains, evals)
        self.waiting = tuple(sorted(set(self.runs.values()) - set(groups))) if self.runs else ()

        base: dict[str, dict] = {}
        lags: dict[str, int | None] = {}
        to_read: dict[str, tuple[tuple[str, ...], int]] = {}  # run -> (training run ids, lowest last_step to read)
        for run, members in groups.items():
            seen_ms, step = max(trains[m] for m in members)  # the group's newest batch
            eval_step, loaded_ms = evals.get(run, (None, None))
            base[run] = dict(run_id=run, train_runs=members, train_step=step, train_seen_ms=seen_ms,
                             eval_step=eval_step, eval_loaded_ms=loaded_ms)
            if now_ms - seen_ms > self.live_ms:
                lags[run] = None
            elif eval_step is not None and step < eval_step:
                lags[run] = 0
            else:
                to_read[run] = (members, eval_step or 0)
        for run, batches in self._batches(to_read).items():
            lags[run] = active_lag_ms(batches, base[run]["eval_step"], self.pause_ms)

        checks = []
        for run in sorted(base):
            lag = lags[run]
            over = lag is not None and lag > self.threshold_ms
            paged = over and run not in self._fired
            if over:
                self._fired.add(run)
            else:
                self._fired.discard(run)  # back under the limit, or not training: the next episode pages again
            checks.append(RunCheck(**base[run], lag_ms=lag, threshold_ms=self.threshold_ms, label=self.label,
                                   paged=paged))
        return checks

    def save(self, checks: Sequence[RunCheck], now_ms: int) -> int:
        """Write one `eval_lag_checks` row per live check; creates the table first. Returns the rows written.

        A page row that could not be written is kept and sent with the next save: the page fires only once, so
        without it Grafana would never show that page.
        """
        if not self.write:
            return 0
        rows = self._unsaved_pages + [c.row(now_ms) for c in checks if c.live]
        try:
            if not self._table_ready:
                self._create_table()
            if rows:
                body = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows).encode("utf-8")
                self._exec(f"INSERT INTO {TABLE} FORMAT JSONEachRow", data=body)
        except BaseException:
            self._unsaved_pages = [r for r in rows if r["paged"]]
            raise
        self._unsaved_pages = []
        return len(rows)

    def _create_table(self) -> None:
        # As load_jsonl.execute_sql_file, but through exec_fn: drop comment lines, run each statement.
        text = "\n".join(ln for ln in TABLE_SQL.read_text(encoding="utf-8").splitlines()
                         if not ln.strip().startswith("--"))
        for stmt in (s.strip() for s in text.split(";")):
            if stmt:
                self._exec(stmt)
        self._table_ready = True

    def _groups(self, trains: dict, evals: dict) -> dict[str, tuple[str, ...]]:
        if self.runs is None:
            return {run: (run,) for run in trains if run in evals}
        groups: dict[str, list[str]] = {}
        for train, run in self.runs.items():
            if train in trains:
                groups.setdefault(run, []).append(train)
        return {run: tuple(sorted(members)) for run, members in groups.items()}

    def _select(self, sql: str) -> list[list[str]]:
        try:
            out = self._exec(f"{sql} FORMAT TabSeparated")
        except RuntimeError as exc:  # ClickHouse answered with an error
            message = str(exc).strip()
            if "UNKNOWN_TABLE" in message or "Code: 60." in message:
                for table, hint in MISSING_TABLE_HINTS:
                    if table in message:
                        raise EvalLagError(f"table {table} is missing: {hint} ({message})") from exc
            raise EvalLagError(message) from exc
        return [tsv_fields(line) for line in out.splitlines() if line]

    def _newest_batches(self) -> dict[str, tuple[int, int]]:
        """Training run id -> (newest seen_at in ms, the last step of that batch).

        `lines > 0` here and in `_batches`: a batch of blank lines is stored with steps 0..0, which would read as a
        restore to step 0.
        """
        where = f" AND run_id IN {_sql_list(self.runs)}" if self.runs else ""
        rows = self._select("SELECT run_id, toUnixTimestamp64Milli(max(seen_at)), argMax(last_step, seen_at) "
                            f"FROM ingest_batches WHERE lines > 0{where} GROUP BY run_id")
        return {run: (int(ms), int(step)) for run, ms, step in rows}

    def _newest_scores(self) -> dict[str, tuple[int, int]]:
        """Eval run id -> (newest Tier A checkpoint_step, newest loaded_at in ms)."""
        where = f" AND checkpoint_run IN {_sql_list(self.runs.values())}" if self.runs else ""
        rows = self._select(
            "SELECT checkpoint_run, max(checkpoint_step), toUnixTimestamp64Milli(max(loaded_at)) FROM eval_mini "
            f"WHERE position(run_id, {sql_str(f':{self.label}:')}) > 0 AND checkpoint_run IS NOT NULL "
            f"AND checkpoint_step IS NOT NULL{where} GROUP BY checkpoint_run")
        return {run: (int(step), int(ms)) for run, step, ms in rows}

    def _batches(self, to_read: dict[str, tuple[tuple[str, ...], int]]) -> dict[str, list[Batch]]:
        """Each run's batches at or after its newest Tier A step, in one read, in seen_at order."""
        if not to_read:
            return {}
        where = " OR ".join(f"(run_id IN {_sql_list(members)} AND last_step >= {int(low)})"
                            for members, low in to_read.values())
        rows = self._select("SELECT run_id, toUnixTimestamp64Milli(seen_at), first_step, last_step "
                            f"FROM ingest_batches WHERE lines > 0 AND ({where}) "
                            "ORDER BY seen_at, source_file, start_offset")
        owner = {member: run for run, (members, _) in to_read.items() for member in members}
        out: dict[str, list[Batch]] = {run: [] for run in to_read}
        for train, ms, first, last in rows:
            out[owner[train]].append(Batch(int(ms), int(first), int(last)))
        return out


def _log(now_ms: int, text: str) -> None:
    print(f"{_utc(now_ms)} {text}", file=sys.stderr, flush=True)


def _describe(exc: BaseException) -> str:
    """One line for an expected ClickHouse error; the traceback for anything else (a bug to report)."""
    if isinstance(exc, CHECK_ERRORS):
        return f"{type(exc).__name__}: {exc}"
    trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip()
    return f"unexpected {type(exc).__name__}: {exc}\n{trace}"


def _safe_url(url: str) -> str:
    """The URL without a user or password, for the log (`ch_Exec` sends no login, so none should be there)."""
    parts = urllib.parse.urlsplit(url)
    if "@" not in parts.netloc:
        return url
    return urllib.parse.urlunsplit(parts._replace(netloc=parts.netloc.rsplit("@", 1)[1]))


def run_check(monitor: EvalLagMonitor, now_ms: int) -> tuple[bool, str | None]:
    """One check: page events on stdout, status on stderr, rows to ClickHouse. Returns (paged, error or None).

    It never raises: a crash would end a long-running alarm, and `--once` must not exit 1 (a page) on a bug.
    """
    try:
        checks = monitor.check(now_ms)
    except Exception as exc:  # noqa: BLE001 - see the docstring
        return False, _describe(exc)
    paged = any(c.paged for c in checks)
    try:
        for c in checks:
            if c.paged:
                print(json.dumps(c.event()), flush=True)
        for c in checks:
            _log(now_ms, c.status(now_ms))
        for run in monitor.waiting:
            trains = sorted(t for t, r in (monitor.runs or {}).items() if r == run)
            _log(now_ms, f"eval_lag {run}: no ingest_batches rows yet for {', '.join(trains)}: not checked")
        monitor.save(checks, now_ms)
    except Exception as exc:  # noqa: BLE001 - see the docstring
        return paged, f"writing {TABLE} failed: {_describe(exc)}"
    return paged, None


def _positive(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        value = math.nan
    if not (math.isfinite(value) and value > 0):
        raise argparse.ArgumentTypeError(f"must be a positive number, got {text!r}")
    return value


def _run_pair(text: str) -> tuple[str, str]:
    train, sep, run = (part.strip() for part in text.partition("="))
    run = run if sep else train
    # A tab or newline in a run id would split the one-line status and log output.
    if not train or not run or any(ch in text for ch in "\t\n"):
        raise argparse.ArgumentTypeError(f"use TRAIN_RUN or TRAIN_RUN=EVAL_RUN, got {text!r}")
    return train, run


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Page when Tier A eval scores lag training by more than N checkpoint "
                                             "intervals (eval_schedule.md section 6).")
    ap.add_argument("--url", default=DEFAULT_CH_URL,
                    help="ClickHouse HTTP URL (default: $CLICKHOUSE_URL or %(default)s)")
    ap.add_argument("--interval-s", type=_positive, required=True,
                    help="the run's checkpoint interval in seconds (--checkpoint-interval-s; 600 for dry run 2)")
    ap.add_argument("--intervals", type=_positive, default=2.0,
                    help="page above this many intervals of lag (default 2; k+1 if Tier A scores every k-th commit)")
    ap.add_argument("--label", default="tier-a", help="the eval watcher's --label to follow (default tier-a)")
    ap.add_argument("--run", type=_run_pair, action="append", metavar="TRAIN_RUN[=EVAL_RUN]",
                    help="check this run (repeatable); map a training run id in ingest_batches to the eval run id in "
                         "eval_mini.checkpoint_run. Default: every training run with Tier A rows")
    ap.add_argument("--live-s", type=_positive,
                    help="a run counts as training while its newest batch is at most this old (default: the limit)")
    ap.add_argument("--pause-s", type=_positive,
                    help="count a gap between two batches as at most this long (default: half an interval)")
    ap.add_argument("--no-write", action="store_true", help=f"don't create or write {TABLE}")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="check once; exit 0, 1 on a page, 2 on an error")
    mode.add_argument("--poll", type=_positive, default=60.0, help="seconds between checks (default 60)")
    a = ap.parse_args(argv)
    if not a.label or ":" in a.label:
        ap.error(f"--label must be non-empty and hold no ':', got {a.label!r}")
    runs: dict[str, str] = {}
    for train, run in a.run or ():
        if runs.setdefault(train, run) != run:
            ap.error(f"--run maps {train} to both {runs[train]} and {run}")
    a.runs = runs or None
    return a


def main(
    argv: Sequence[str] | None = None,
    *,
    exec_fn: ExecFn | None = None,
    now_ms: Callable[[], int] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    a = parse_args(argv)
    exec_fn = exec_fn or (lambda sql, data=None: ch_Exec(sql, data=data, url=a.url))
    clock = now_ms or (lambda: int(time.time() * 1000))
    monitor = EvalLagMonitor(exec_fn, interval_s=a.interval_s, intervals=a.intervals, label=a.label, runs=a.runs,
                             live_s=a.live_s, pause_s=a.pause_s, write=not a.no_write)
    started = clock()
    runs = ", ".join(f"{t}={r}" for t, r in sorted(a.runs.items())) if a.runs else f"every run with {a.label} rows"
    _log(started, f"eval_lag: {_safe_url(a.url)}, limit {monitor.threshold_ms / 1000:,.0f} s ({a.intervals:g} x "
                  f"{a.interval_s:g} s), label {a.label}, runs {runs}, live {monitor.live_ms / 1000:,.0f} s, "
                  f"pause {monitor.pause_ms / 1000:,.0f} s, {TABLE} {'on' if monitor.write else 'off'}, "
                  f"{'once' if a.once else f'every {a.poll:g} s'}")
    if a.once:
        paged, error = run_check(monitor, started)
        if error:
            _log(started, f"eval_lag: check failed: {error}")
        return EXIT_PAGE if paged else EXIT_ERROR if error else EXIT_OK
    last_complete: int | None = None
    try:
        while True:
            now = clock()
            _, error = run_check(monitor, now)
            if error is None:
                last_complete = now
            else:
                if last_complete is None:
                    since = f"no complete check in the {(now - started) / 1000:,.0f} s since start"
                else:
                    since = f"{(now - last_complete) / 1000:,.0f} s since the last complete check"
                _log(now, f"eval_lag: check failed ({since}): {error}")
            sleep(a.poll)
    except KeyboardInterrupt:
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
