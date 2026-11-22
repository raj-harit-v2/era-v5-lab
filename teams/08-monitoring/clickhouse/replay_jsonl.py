#!/usr/bin/env python3
"""Replay a finished metrics.jsonl at its real pace, flushing like MetricsWriter (Issue #27).

Usage:
    python -I teams/08-monitoring/clickhouse/replay_jsonl.py \
        teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl \
        --out /tmp/live/metrics.jsonl --log /tmp/live/written.csv --speed 1

Run `watch_jsonl.py` on `--out` beside it without `--idle-exit`, or with one longer than the gap between flushes
(about 20 s at 1.9 s per step; the first gap is 22 s). A shorter one makes the watcher exit between flushes.

TSAI returns a job's logs only after the job ends, so the live path (trainer -> file -> watch_jsonl.py ->
ClickHouse -> Grafana) can't be timed on a real job yet. This script stands in for the trainer:

- Pace. A line is produced when its step would have finished: the running sum of each line's `perf/step_ms`,
  divided by `--speed`. A line without `perf/step_ms` (dry run 1's step 0, the initial evaluation) takes
  `--step-seconds`.
- Flushes. Like `MetricsWriter.flush()`: buffered lines are written in one `write`, then `flush()` and
  `os.fsync()`, at every step divisible by `--flush-every` (10), at a line holding a `null` value (the writer
  flushes a non-finite metric at once), and at the end.
- Content. The output holds the source's non-blank lines byte for byte, so a load of it gives the same rows.
- Log. `--log` gets one CSV row per line: `step, produced_at, written_at, start_offset, end_offset`.
  `produced_at` is when the line entered the buffer, `written_at` when its flush's `fsync` returned (UTC, ms),
  and the offsets are its bytes in `--out`. The log is written at each flush, so it is complete up to the last
  flush even if the replay is stopped.

The output file must not exist (pass `--overwrite` to replace it): a watcher that loaded an earlier replay of
the same path would otherwise read a different file at its saved offset.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Callable

FLUSH_EVERY = 10
STEP_SECONDS = 1.9
LOG_COLUMNS = ("step", "produced_at", "written_at", "start_offset", "end_offset")


@dataclass
class Line:
    step: int
    data: bytes  # the line without its newline
    seconds: float  # how long the step took before this line was produced
    has_null: bool


def utc_text(epoch: float) -> str:
    dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


def read_lines(path: Path, step_seconds: float = STEP_SECONDS, limit: int | None = None) -> list[Line]:
    """Parse every non-blank line up front, so a bad source fails before anything is written."""
    lines: list[Line] = []
    for number, raw in enumerate(path.read_bytes().split(b"\n"), start=1):
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except ValueError as exc:
            raise ValueError(f"{path}: line {number} is not valid JSON: {exc}") from exc
        step = rec.get("step") if isinstance(rec, dict) else None
        if not isinstance(step, int) or isinstance(step, bool) or step < 0:
            raise ValueError(f"{path}: line {number} has no non-negative integer 'step'")
        step_ms = rec.get("perf/step_ms")
        ok_ms = isinstance(step_ms, (int, float)) and not isinstance(step_ms, bool) and step_ms > 0
        lines.append(Line(
            step=step,
            data=raw.rstrip(b"\r"),
            seconds=step_ms / 1000.0 if ok_ms else step_seconds,
            has_null=any(v is None for v in rec.values()),
        ))
        if limit is not None and len(lines) >= limit:
            break
    return lines


def replay(
    lines: list[Line],
    out: Path,
    log: Path,
    speed: float = 1.0,
    flush_every: int = FLUSH_EVERY,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    wall: Callable[[], float] = time.time,
    report: Callable[[str], None] = print,
) -> dict:
    """Write `lines` to `out` on the replay schedule and log each line's times to `log`."""
    out.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    offset = 0
    buffer: list[tuple[Line, str]] = []
    flushes = 0
    start = monotonic()
    due = 0.0

    with open(out, "xb") as f, open(log, "x", newline="", encoding="utf-8") as log_f:
        writer = csv.writer(log_f)
        writer.writerow(LOG_COLUMNS)

        def flush() -> None:
            nonlocal offset, flushes
            if not buffer:
                return
            f.write(b"\n".join(line.data for line, _ in buffer) + b"\n")
            f.flush()
            os.fsync(f.fileno())
            written_at = utc_text(wall())
            for line, produced_at in buffer:
                end = offset + len(line.data) + 1
                writer.writerow((line.step, produced_at, written_at, offset, end))
                offset = end
            log_f.flush()
            flushes += 1
            report(f"flushed steps {buffer[0][0].step}..{buffer[-1][0].step} at {written_at} ({offset} bytes)")
            buffer.clear()

        for line in lines:
            due += line.seconds / speed
            wait = start + due - monotonic()
            if wait > 0:
                sleep(wait)
            buffer.append((line, utc_text(wall())))
            if line.has_null or line.step % flush_every == 0:
                flush()
        flush()

    return {"lines": len(lines), "flushes": flushes, "bytes": offset, "seconds": monotonic() - start}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Replay a finished metrics.jsonl at its real pace.")
    ap.add_argument("source", type=Path, help="finished metrics.jsonl to replay")
    ap.add_argument("--out", type=Path, required=True, help="file to write, as the trainer would")
    ap.add_argument("--log", type=Path, required=True, help="CSV of each line's produced and written times")
    ap.add_argument("--speed", type=float, default=1.0, help="1 = real pace, 10 = ten times faster (default: 1)")
    ap.add_argument("--step-seconds", type=float, default=STEP_SECONDS,
                    help=f"duration of a line without perf/step_ms (default: {STEP_SECONDS})")
    ap.add_argument("--flush-every", type=int, default=FLUSH_EVERY, help=f"default: {FLUSH_EVERY}, as MetricsWriter")
    ap.add_argument("--limit", type=int, default=None, help="replay only the first N lines")
    ap.add_argument("--overwrite", action="store_true", help="replace --out and --log if they exist")
    args = ap.parse_args(argv)
    if args.speed <= 0 or args.step_seconds <= 0 or args.flush_every < 1:
        ap.error("--speed and --step-seconds must be > 0, --flush-every >= 1")
    if args.limit is not None and args.limit < 1:
        ap.error("--limit must be >= 1")

    for path in (args.out, args.log):
        if path.exists():
            if not args.overwrite:
                print(f"error: {path} exists; pass --overwrite to replace it", file=sys.stderr)
                return 1
            path.unlink()

    try:
        lines = read_lines(args.source, args.step_seconds, args.limit)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    total = sum(line.seconds for line in lines) / args.speed
    print(f"replaying {len(lines)} lines of {args.source} into {args.out}, about {total / 60:.1f} min", flush=True)
    try:
        info = replay(lines, args.out, args.log, speed=args.speed, flush_every=args.flush_every,
                      report=lambda msg: print(msg, flush=True))
    except KeyboardInterrupt:
        print(f"stopped; {args.log} covers every line flushed so far", flush=True)
        return 130
    print(f"done: {info['lines']} lines, {info['flushes']} flushes, {info['bytes']} bytes in {info['seconds']:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
