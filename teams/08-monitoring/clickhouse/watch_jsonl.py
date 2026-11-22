#!/usr/bin/env python3
"""Load a growing metrics.jsonl into ClickHouse while it is being written (Issue #27).

Usage:
    python -I teams/08-monitoring/clickhouse/watch_jsonl.py runs/r7/g8/metrics.jsonl --poll 2
    python -I teams/08-monitoring/clickhouse/watch_jsonl.py path/metrics.jsonl --run-id dryrun1-watch --idle-exit 10

Every `--poll` seconds the watcher reads the file from the byte where its last batch ended, keeps the complete
lines (the ones ending in a newline), parses them with `load_jsonl.py`'s parser and inserts the rows into
`metrics_raw`. Then it writes one row to `ingest_batches`; `max(end_offset)` of those rows is where a restarted
watcher continues. A half-written last line stays in the file and is read again from its first byte on the next
poll. The watcher never deletes rows.

Run id: `--run-id`, else the `run_id` field of the file's first line, else the parent folder name (the file name
for a file not called `metrics.jsonl`), as in `load_jsonl.py`.

A resumed trainer (#606) starts a new G8 file that repeats the old steps. At startup the watcher reads the
`(step, rank)` pairs already stored for the run and skips lines that repeat one; `ingest_batches.skipped_lines`
counts them. Start the watcher for a new segment after the old segment's watcher has caught up.

Run one watcher per file. A lock in the temp folder stops a second one on the same machine; two watchers
reading one file would insert its rows twice.

Any ClickHouse error (server down, timeout, rejected SQL) stops the watcher with exit code 1. Restart it and it
resumes from `ingest_batches`. If it stopped between inserting rows and writing their `ingest_batches` row, the
restarted watcher finds those steps already stored and skips them.

Only per-step JSONL metric files are supported (Team 5 `metrics.jsonl`, `MetricsWriter` output). Use
`load_jsonl.py` for Team 6 run JSON and Team 9 eval files.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Callable
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_jsonl import (  # noqa: E402
    DEFAULT_CH_URL,
    HERE,
    REPO_ROOT,
    _format_utc,
    _parse_jsonl_content,
    ch_Exec,
    ensure_schema,
    execute_sql_file,
)

BATCH_COLUMNS = (
    "run_id", "source_file", "start_offset", "end_offset", "first_step", "last_step",
    "lines", "rows", "skipped_lines", "seen_at", "inserted_at",
)
# Errors that stop the watcher with exit code 1. A ClickHouse error is never retried in place: a watcher that
# keeps polling a dead server looks alive while nothing loads.
STOP_ERRORS = (RuntimeError, urllib.error.URLError, ConnectionError, TimeoutError)


class WatchError(RuntimeError):
    """The file can't be loaded safely; a person has to look at it."""


@dataclass
class Batch:
    start_offset: int
    end_offset: int
    first_step: int
    last_step: int
    lines: int
    rows: int
    skipped_lines: int
    seen_at: str
    inserted_at: str

    def describe(self) -> str:
        return (
            f"steps {self.first_step}..{self.last_step} lines={self.lines} rows={self.rows} "
            f"skipped={self.skipped_lines} bytes {self.start_offset}..{self.end_offset} inserted_at={self.inserted_at}"
        )


def canonical_source(path: Path) -> str:
    """Repo-relative path for files in the repo, absolute path otherwise."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(resolved)


def default_run_id(path: Path) -> str:
    return path.parent.name if path.name == "metrics.jsonl" else path.stem


def sql_str(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def utc_now() -> str:
    return _format_utc(datetime.now(timezone.utc))


def lock_source(path: Path):
    """Hold an exclusive lock for this file, so a second watcher on the same machine can't load it twice.

    Returns the open lock file; the lock lasts until it is closed or the process ends. Raises WatchError if
    another watcher holds it. No lock on systems without `fcntl` (Windows).
    """
    try:
        import fcntl
    except ImportError:
        return None
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:16]
    handle = open(Path(tempfile.gettempdir()) / f"watch_jsonl-{digest}.lock", "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise WatchError(f"another watch_jsonl.py is already loading {path}") from None
    return handle


def prepare_schema(url: str = DEFAULT_CH_URL) -> None:
    ensure_schema(url=url)
    execute_sql_file(HERE / "ingest_batches.sql", url=url)


class Watcher:
    """Loads the complete lines a file has gained since the last batch. `exec_fn(sql, data=None)` runs SQL."""

    def __init__(
        self,
        path: str | Path,
        run_id: str | None = None,
        exec_fn: Callable[..., str] | None = None,
        url: str = DEFAULT_CH_URL,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.path = Path(path)
        self.source_file = canonical_source(self.path)
        self.run_id_override = run_id
        self.run_id = run_id
        self._exec = exec_fn or (lambda sql, data=None: ch_Exec(sql, data=data, url=url))
        self._clock = clock
        self.offset = 0
        self.line_index = 0
        self.stored: set[tuple[int, int]] = set()
        self.started = False
        self.totals = {"batches": 0, "lines": 0, "rows": 0, "skipped_lines": 0}

    def _select(self, sql: str) -> list[list[str]]:
        out = self._exec(f"{sql} FORMAT TabSeparated")
        return [ln.split("\t") for ln in out.splitlines() if ln]

    def _first_line(self) -> bytes | None:
        """The file's first non-blank complete line, or None if there is none yet."""
        try:
            with self.path.open("rb") as f:
                data = b""
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        return None
                    data += chunk
                    *complete, _rest = data.split(b"\n")
                    for raw in complete:
                        if raw.strip():
                            return raw
        except FileNotFoundError:
            return None

    def start(self) -> bool:
        """Pick the run id and read the resume point. False while the run id still needs a first line."""
        if self.run_id is None:
            first = self._first_line()
            if first is None:
                return False
            try:
                rec = json.loads(first)
            except ValueError:
                rec = None
            rid = rec.get("run_id") if isinstance(rec, dict) else None
            self.run_id = rid.strip() if isinstance(rid, str) and rid.strip() else default_run_id(self.path)

        run = sql_str(self.run_id)
        resume = self._select(
            f"SELECT max(end_offset), sum(lines) FROM ingest_batches "
            f"WHERE run_id = {run} AND source_file = {sql_str(self.source_file)}"
        )
        self.offset, self.line_index = (int(resume[0][0]), int(resume[0][1])) if resume else (0, 0)
        stored = self._select(f"SELECT DISTINCT step, rank FROM metrics_raw WHERE run_id = {run}")
        self.stored = {(int(step), int(rank)) for step, rank in stored}
        self.started = True
        return True

    def _parse_lines(self, complete: bytes) -> list[tuple[int, int, list[dict]]]:
        """Parse whole lines into `(step, rank, rows)`; any bad line fails the whole batch."""
        parsed_lines = []
        pos, index = self.offset, self.line_index
        for raw in complete.split(b"\n")[:-1]:
            line_start, pos = pos, pos + len(raw) + 1
            if not raw.strip():
                continue
            where = f"{self.source_file}: line {index + 1} at byte {line_start}"
            try:
                parsed = _parse_jsonl_content(raw.decode("utf-8"), self.run_id, self.run_id_override, start_index=index)
            except (ValueError, TypeError, OverflowError) as exc:
                raise WatchError(f"{where} can't be parsed: {exc}") from exc
            if parsed["jsonl_lines"] != 1:
                raise WatchError(f"{where} holds a line break the writer did not write")
            if parsed["run_id"] != self.run_id:
                raise WatchError(f"{where} has run_id {parsed['run_id']!r}, expected {self.run_id!r}")
            # A wide line always gives a row; a Team 6 event line with no metrics gives none.
            first_row = parsed["rows"][0] if parsed["rows"] else {"step": index, "rank": 0}
            parsed_lines.append((first_row["step"], first_row["rank"], parsed["rows"]))
            index += 1
        return parsed_lines

    def _save_batch(self, batch: Batch) -> None:
        row = {"run_id": self.run_id, "source_file": self.source_file, **batch.__dict__}
        self._exec(
            f"INSERT INTO ingest_batches ({', '.join(BATCH_COLUMNS)}) FORMAT JSONEachRow",
            data=(json.dumps(row) + "\n").encode("utf-8"),
        )
        self.offset = batch.end_offset
        self.line_index += batch.lines
        self.totals["batches"] += 1
        for key in ("lines", "rows", "skipped_lines"):
            self.totals[key] += getattr(batch, key)

    def poll_once(self) -> Batch | None:
        """Load the complete lines added since the last batch. None when there is nothing new."""
        if not self.started and not self.start():
            return None

        try:
            size = self.path.stat().st_size
        except FileNotFoundError:
            if self.offset == 0:
                return None
            raise WatchError(f"{self.path} disappeared after {self.offset} bytes were loaded") from None
        if size < self.offset:
            raise WatchError(
                f"{self.path} is {size} bytes, shorter than the resume offset {self.offset}: truncated or replaced"
            )
        if size == self.offset:
            return None

        with self.path.open("rb") as f:
            f.seek(self.offset)
            chunk = f.read(size - self.offset)
        seen_at = self._clock()
        cut = chunk.rfind(b"\n")
        if cut < 0:
            return None  # only a half-written line so far

        parsed_lines = self._parse_lines(chunk[: cut + 1])
        rows: list[dict] = []
        skipped = 0
        for step, rank, line_rows in parsed_lines:
            if (step, rank) in self.stored:
                skipped += 1
            else:
                rows.extend(line_rows)
        if rows:
            body = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows).encode("utf-8")
            self._exec("INSERT INTO metrics_raw FORMAT JSONEachRow", data=body)

        batch = Batch(
            start_offset=self.offset,
            end_offset=self.offset + cut + 1,
            first_step=parsed_lines[0][0] if parsed_lines else 0,
            last_step=parsed_lines[-1][0] if parsed_lines else 0,
            lines=len(parsed_lines),
            rows=len(rows),
            skipped_lines=skipped,
            seen_at=seen_at,
            inserted_at=self._clock(),
        )
        self._save_batch(batch)
        return batch

    def run(
        self,
        poll: float = 2.0,
        idle_exit: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        """Poll until `idle_exit` seconds pass with no new complete line (forever if None). Errors propagate."""
        last_progress = monotonic()
        while True:
            batch = self.poll_once()
            if batch is not None:
                last_progress = monotonic()
                print(batch.describe(), flush=True)
            elif idle_exit is not None and monotonic() - last_progress >= idle_exit:
                return
            sleep(poll)

    def summary(self) -> str:
        t = self.totals
        text = (
            f"run_id={self.run_id!r} source={self.source_file} batches={t['batches']} lines={t['lines']} "
            f"rows={t['rows']} skipped={t['skipped_lines']} offset={self.offset}"
        )
        try:
            with self.path.open("rb") as f:
                f.seek(self.offset)
                rest = f.read()
        except FileNotFoundError:
            rest = b""
        if b"\n" in rest:
            text += f" NOT LOADED: {len(rest)} bytes after the offset"
        elif rest:
            text += f" ({len(rest)} bytes of an unfinished last line not loaded)"
        return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Load a growing metrics.jsonl into ClickHouse as it is written.")
    ap.add_argument("path", help="JSONL file to watch")
    ap.add_argument("--run-id", default=None, help="run_id to store (default: the rows' run_id, else the folder name)")
    ap.add_argument("--poll", type=float, default=2.0, help="seconds between reads (default: 2)")
    ap.add_argument("--idle-exit", type=float, default=None, metavar="SECONDS",
                    help="exit after this many seconds with no new complete line (default: run until stopped)")
    ap.add_argument("--url", default=DEFAULT_CH_URL, help=f"ClickHouse HTTP URL (default: {DEFAULT_CH_URL})")
    args = ap.parse_args(argv)
    if args.poll <= 0:
        ap.error("--poll must be greater than 0")

    try:
        lock = lock_source(Path(args.path))  # noqa: F841  (held until exit)
    except WatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    watcher = Watcher(args.path, run_id=args.run_id, url=args.url)
    print(f"watching {watcher.source_file} every {args.poll:g} s", flush=True)
    try:
        prepare_schema(args.url)
        watcher.run(poll=args.poll, idle_exit=args.idle_exit)
    except KeyboardInterrupt:
        print("stopped", flush=True)
    except WatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(watcher.summary())
        return 1
    except STOP_ERRORS as exc:
        print(f"error: ClickHouse at {args.url} failed, watcher stopped: {exc}", file=sys.stderr)
        print(watcher.summary())
        return 1
    print(watcher.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
