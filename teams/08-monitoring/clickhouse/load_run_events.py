#!/usr/bin/env python3
"""Load run events (restarts, checkpoints, alarm hits) into ClickHouse `run_events`.

Two inputs, both already written by existing code; neither needs to change:

1. Team 07's event lines, schema `v5-event/1` (`teams/07-infrastructure/common/events.py`): one JSON object per
   line in `$V5_EVENTS_DIR/<host>-<pid>.jsonl`. A line may carry a text prefix, as in Team 07's results files
   (`restore.done: {...}`). A torn last line from a killed process is skipped and counted.
2. Alarm hits, one JSON object per line, as `alarms/alarms.py --jsonl metrics.jsonl` prints them
   ({"step", "metric", "rule", "severity", "detail", ...}).

What each event counts as (`kind`):
- `restart`            restore.done: a new process restored a committed checkpoint and carried on.
- `restart_failed`     restore.failed.
- `checkpoint`         checkpoint.committed.
- `checkpoint_failed`  checkpoint.failed, checkpoint.fenced.
- `alarm`              an alarm hit; `severity` is stop, page or warn, `event` is `alarm.<rule>`.
- `other`              every other v5-event (started, claimed, backpressure, retention, ...). Stored, so nothing is
                       hidden, but not counted by the panels.
- `coverage`           one marker row per run and input type (`events.loaded`, `alarms.loaded`), written whenever a
                       file is loaded, even one with no hits. The panels show a blank, not 0, for a run whose events
                       or alarms were never loaded, so "not checked" never looks like "checked, nothing found".

Public-safety rule: host names, job ids, store paths and file names are never stored. Only the fields in
SAFE_EVENT_FIELDS / SAFE_ALARM_FIELDS go into `detail`.

Each row has a stable `event_key` (sha256 of the source record), and the table is a ReplacingMergeTree on
(run_id, event_key), so loading the same file again does not double-count. Alarm keys use (rule, metric, step,
severity), so re-running alarms.py over the same metrics.jsonl gives the same keys.

Usage:
    python load_run_events.py --events $V5_EVENTS_DIR --run-id dryrun2-1234 --dry-run
    python alarms/alarms.py --jsonl metrics.jsonl > alarms.jsonl
    python load_run_events.py --alarms alarms.jsonl --run-id dryrun2-1234
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
SCHEMA_SQL = HERE / "run_events.sql"
EVENT_SCHEMA = "v5-event/1"

KIND_BY_EVENT = {
    "restore.done": "restart",
    "restore.failed": "restart_failed",
    "checkpoint.committed": "checkpoint",
    "checkpoint.failed": "checkpoint_failed",
    "checkpoint.fenced": "checkpoint_failed",
}
# Fields kept from a v5-event. Not kept: host, job_id, job, store, path, from_path, env_override, free-text detail,
# throughput numbers (bytes, upload_gbps): they name machines or imply hardware.
SAFE_EVENT_FIELDS = ("branch", "reason", "cause", "epoch", "previous", "phase", "skip", "resharded")
SAFE_ALARM_FIELDS = ("metric", "rule", "value", "detail")
SEVERITIES = ("stop", "page", "warn")
MAX_DETAIL_CHARS = 300


def _key(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _step(val):
    if val is None or isinstance(val, bool):
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _time(val):
    """v5-event time (ISO 8601 UTC, e.g. 2026-11-04T16:30:08.442Z) -> ClickHouse DateTime64 text, or None."""
    if not isinstance(val, str) or not val.strip():
        return None
    try:
        dt = datetime.fromisoformat(val.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _detail(rec: dict, fields) -> str:
    kept = {k: rec[k] for k in fields if k in rec and rec[k] is not None}
    if isinstance(kept.get("detail"), str):
        kept["detail"] = kept["detail"][:MAX_DETAIL_CHARS]
    return json.dumps(kept, sort_keys=True, default=str)


def _json_from_line(line: str):
    """The JSON object on a line, allowing a text prefix before the first '{'. None for blank or torn lines."""
    start = line.find("{")
    if start < 0:
        return None
    try:
        obj = json.loads(line[start:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _lines(path: Path):
    """Lines of a file, or of every *.jsonl file in a directory (a V5_EVENTS_DIR), in name order."""
    files = sorted(path.glob("*.jsonl")) if path.is_dir() else [path]
    for f in files:
        with open(f, encoding="utf-8") as fh:
            yield from fh


def event_row(rec: dict, run_id: str = "") -> dict | None:
    """One v5-event record -> a run_events row; None if it is not a v5-event. run_id overrides the record's."""
    if rec.get("schema") != EVENT_SCHEMA or not isinstance(rec.get("event"), str):
        return None
    rid = (run_id or str(rec.get("run_id") or "")).strip()
    if not rid:
        raise ValueError(f"{rec['event']} event has no run_id; pass --run-id")
    name = rec["event"]
    return {
        "run_id": rid,
        "event_time": _time(rec.get("time")),
        "step": _step(rec.get("step")),
        "kind": KIND_BY_EVENT.get(name, "other"),
        "event": name,
        "severity": "",
        "detail": _detail(rec, SAFE_EVENT_FIELDS),
        "source": "v5-event",
        "event_key": _key("v5-event", rec),
    }


def alarm_row(rec: dict, run_id: str) -> dict | None:
    """One alarms.py hit -> a run_events row; None if the record is not an alarm hit."""
    rule, severity = rec.get("rule"), rec.get("severity")
    if not isinstance(rule, str) or severity not in SEVERITIES:
        return None
    if not run_id:
        raise ValueError("alarm hits carry no run_id; pass --run-id")
    step = _step(rec.get("step"))
    return {
        "run_id": run_id,
        "event_time": None,  # alarms.py reports the step, not a wall time
        "step": step,
        "kind": "alarm",
        "event": f"alarm.{rule}",
        "severity": severity,
        "detail": _detail(rec, SAFE_ALARM_FIELDS),
        "source": "alarms",
        "event_key": _key("alarm", rule, rec.get("metric"), step, severity),
    }


def coverage_row(run_id: str, source: str) -> dict:
    """Marker that `source` ("events" or "alarms") was loaded for run_id. One per run and source: reloads replace it."""
    return {
        "run_id": run_id,
        "event_time": None,
        "step": None,
        "kind": "coverage",
        "event": f"{source}.loaded",
        "severity": "",
        "detail": "{}",
        "source": source if source == "alarms" else "v5-event",
        "event_key": _key("coverage", source, run_id),
    }


def parse_events(path: Path, run_id: str = "") -> tuple[list[dict], int]:
    """Rows from Team 07 v5-event lines, and the number of lines skipped (blank lines are not counted)."""
    rows, skipped = [], 0
    for line in _lines(path):
        if not line.strip():
            continue
        rec = _json_from_line(line)
        row = event_row(rec, run_id) if rec is not None else None
        if row is None:
            skipped += 1
        else:
            rows.append(row)
    return rows, skipped


def parse_alarms(path: Path, run_id: str) -> tuple[list[dict], int]:
    """Rows from alarms.py --jsonl output, and the number of lines skipped (e.g. its stderr summary, if captured)."""
    rows, skipped = [], 0
    for line in _lines(path):
        if not line.strip():
            continue
        rec = _json_from_line(line)
        row = alarm_row(rec, run_id) if rec is not None else None
        if row is None:
            skipped += 1
        else:
            rows.append(row)
    return rows, skipped


def _ch_post(sql: str, data: bytes = b"", url: str = "http://127.0.0.1:8123") -> str:
    endpoint = f"{url.rstrip('/')}/?{urllib.parse.urlencode({'query': sql})}"
    req = urllib.request.Request(endpoint, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def ensure_table(url: str = "http://127.0.0.1:8123") -> None:
    for stmt in SCHEMA_SQL.read_text(encoding="utf-8").split(";"):
        cleaned = "\n".join(ln for ln in stmt.splitlines() if ln.strip() and not ln.strip().startswith("--")).strip()
        if cleaned:
            _ch_post(cleaned, url=url)


def insert_rows(rows: list[dict], url: str = "http://127.0.0.1:8123") -> int:
    if not rows:
        return 0
    ensure_table(url=url)
    payload = ("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n").encode("utf-8")
    _ch_post("INSERT INTO run_events FORMAT JSONEachRow", data=payload, url=url)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Load restarts, checkpoints and alarm hits into ClickHouse run_events.")
    ap.add_argument("--events", type=Path, action="append", default=[],
                    help="Team 07 v5-event file or V5_EVENTS_DIR (repeatable)")
    ap.add_argument("--alarms", type=Path, action="append", default=[],
                    help="alarms.py --jsonl output file (repeatable)")
    ap.add_argument("--run-id", default="", help="run id to store; required for alarm hits, overrides event run_id")
    ap.add_argument("--url", default="http://127.0.0.1:8123", help="ClickHouse HTTP URL")
    ap.add_argument("--dry-run", action="store_true", help="print the rows as JSONEachRow, insert nothing")
    args = ap.parse_args(argv)
    if not args.events and not args.alarms:
        ap.error("pass at least one --events or --alarms input")

    if args.alarms and not args.run_id:
        ap.error("--alarms needs --run-id: alarm hits carry no run id")
    rows, skipped = [], 0
    for p in args.events:
        r, s = parse_events(p, run_id=args.run_id)
        rows += r
        skipped += s
        runs = {x["run_id"] for x in r} or ({args.run_id} if args.run_id else set())
        rows += [coverage_row(run, "events") for run in sorted(runs)]
    for p in args.alarms:
        r, s = parse_alarms(p, run_id=args.run_id)
        rows += r + [coverage_row(args.run_id, "alarms")]  # also when the file has no hits: checked, none found
        skipped += s

    if args.dry_run:
        for r in rows:
            print(json.dumps(r, sort_keys=True))
    else:
        insert_rows(rows, url=args.url)
    counts = {}
    for r in rows:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    action = "parsed" if args.dry_run else f"inserted into {args.url}"
    print(f"{action}: {len(rows)} run_events rows {dict(sorted(counts.items()))}, {skipped} line(s) skipped",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
