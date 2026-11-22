#!/usr/bin/env python3
"""Per-step latency of a replay_jsonl.py + watch_jsonl.py run (Issue #27).

Usage:
    python -I teams/08-monitoring/clickhouse/replay_latency.py /tmp/live/written.csv dryrun1-live \
        teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl

Each row of replay_jsonl.py's `--log` is matched to the `ingest_batches` row whose byte range holds it. The
script prints p50 / p95 / max of two delays:

- file write -> ClickHouse: `inserted_at - written_at`, the loader's poll and insert.
- step finished -> ClickHouse: `inserted_at - produced_at`, which adds the writer's 10-step buffer.

It also counts missing steps and duplicate (step, name, rank) pairs in `metrics_raw`, and pauses: gaps between
`produced_at` values more than 2 s longer than the step's `perf/step_ms`. A pause means the machine slept and
the run is not a fair measurement. Exits 1 if a log row matches no batch or more than one, or if a step is
missing, a pair is duplicated or the run paused.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_jsonl import DEFAULT_CH_URL, ch_Exec  # noqa: E402
from watch_jsonl import sql_str  # noqa: E402

PAUSE_SECONDS = 2.0
STEP_SECONDS = 1.9


def epoch(text: str) -> float:
    """`2026-11-21 01:47:57.123` (UTC, as replay_jsonl.py and ClickHouse print it) to epoch seconds."""
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc).timestamp()


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile."""
    values = sorted(values)
    return values[min(len(values) - 1, round(p / 100 * (len(values) - 1)))]


def measure(log_rows: list[dict], batches: list[tuple[int, int, float]], step_seconds: list[float]) -> dict:
    """`log_rows`: the replay log as dicts. `batches`: (start_offset, end_offset, inserted_at epoch).
    `step_seconds`: how long each source line's step took, by line index."""
    pauses = []
    for prev, cur in zip(log_rows, log_rows[1:]):
        extra = epoch(cur["produced_at"]) - epoch(prev["produced_at"]) - step_seconds[int(cur["step"])]
        if extra > PAUSE_SECONDS:
            pauses.append(extra)

    from_write, from_produce, unmatched = [], [], 0
    for row in log_rows:
        start, end = int(row["start_offset"]), int(row["end_offset"])
        hits = [ins for b_start, b_end, ins in batches if b_start <= start and end <= b_end]
        if len(hits) != 1:
            unmatched += 1
            continue
        from_write.append(hits[0] - epoch(row["written_at"]))
        from_produce.append(hits[0] - epoch(row["produced_at"]))
    return {"pauses": pauses, "unmatched": unmatched, "from_write": from_write, "from_produce": from_produce}


def step_durations(source: Path) -> list[float]:
    out = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ms = json.loads(line).get("perf/step_ms")
            out.append(ms / 1000.0 if isinstance(ms, (int, float)) and ms > 0 else STEP_SECONDS)
    return out


def query(sql: str, url: str) -> list[list[str]]:
    return [line.split("\t") for line in ch_Exec(sql + " FORMAT TSV", url=url).splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Latency of a replay + watch_jsonl.py run.")
    ap.add_argument("log", type=Path, help="replay_jsonl.py --log CSV")
    ap.add_argument("run_id", help="the --run-id watch_jsonl.py loaded the replay under")
    ap.add_argument("source", type=Path, help="the metrics.jsonl that was replayed")
    ap.add_argument("--url", default=DEFAULT_CH_URL, help=f"ClickHouse HTTP URL (default: {DEFAULT_CH_URL})")
    args = ap.parse_args(argv)

    where = f"run_id = {sql_str(args.run_id)}"
    batches = [(int(a), int(b), epoch(c)) for a, b, c in query(
        f"SELECT start_offset, end_offset, inserted_at FROM ingest_batches WHERE {where}", args.url)]
    with open(args.log, newline="", encoding="utf-8") as f:
        log_rows = list(csv.DictReader(f))
    result = measure(log_rows, batches, step_durations(args.source))

    (steps, lo, hi, rows), = query(
        f"SELECT uniqExact(step), min(step), max(step), count() FROM metrics_raw WHERE {where}", args.url)
    (dups,), = query(f"SELECT count() FROM (SELECT step, name, rank FROM metrics_raw WHERE {where} "
                     "GROUP BY step, name, rank HAVING count() > 1)", args.url)
    missing = int(hi) - int(lo) + 1 - int(steps) if int(steps) else 0

    print(f"run_id {args.run_id}: steps {steps} ({lo}..{hi}), rows {rows}, missing {missing}, duplicate pairs {dups}")
    print(f"log lines {len(log_rows)}, matched to one batch {len(result['from_write'])}, unmatched {result['unmatched']}")
    print(f"pauses over {PAUSE_SECONDS:.0f} s: {len(result['pauses'])} ({sum(result['pauses']):.1f} s in total)")
    for name, key in (("file write -> ClickHouse", "from_write"), ("step finished -> ClickHouse", "from_produce")):
        values = result[key]
        if values:
            print(f"{name:28s} p50 {percentile(values, 50):6.2f} s  p95 {percentile(values, 95):6.2f} s"
                  f"  max {max(values):6.2f} s")
    bad = result["unmatched"] or missing or int(dups) or result["pauses"] or not log_rows
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
