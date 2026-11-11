#!/usr/bin/env python3
"""Ingest node health reports (v5-health/1) and TSAI GPU telemetry logs into ClickHouse.

Tables targeted:
  - `node_health`: flattened node health validation reports from Team 07's health_check.py
  - `metrics_raw`: GPU temperature and telemetry time-series (temp_c, power_w, gpu_utilization, mem_used_mib)
  - `ingest_manifest`: verification manifest tracking line counts and metric row counts

Usage:
  python -I load_node_logs.py --defaults
  python -I load_node_logs.py teams/07-infrastructure/health/results/health_sample_v5.json
  python -I load_node_logs.py --selftest
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_CH_URL = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8123")
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]

DEFAULT_SOURCES = (
    "teams/07-infrastructure/health/results/health_sample_v5.json",
)

STATUSES = ("pass", "warn", "fail", "skipped")


def ch_exec(sql: str, data: bytes | None = None, url: str = DEFAULT_CH_URL) -> str:
    """Execute a SQL statement against ClickHouse over HTTP."""
    params = urllib.parse.urlencode({"wait_end_of_query": 1})
    req_url = f"{url.rstrip('/')}/?{params}"
    body = sql.encode("utf-8") if data is None else sql.encode("utf-8") + b"\n" + data
    req = urllib.request.Request(req_url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ClickHouse HTTP {exc.code}: {detail.strip()}") from exc


def ensure_schema(url: str = DEFAULT_CH_URL) -> None:
    """Ensure schema_v1.sql is executed."""
    schema_path = HERE / "schema_v1.sql"
    if schema_path.exists():
        text = schema_path.read_text(encoding="utf-8")
        lines = [line for line in text.splitlines() if not line.strip().startswith("--")]
        for stmt in "\n".join(lines).split(";"):
            stmt = stmt.strip()
            if stmt:
                ch_exec(stmt, url=url)


def _format_utc(dt: datetime) -> str:
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt_utc.microsecond // 1000:03d}"


def _parse_time(raw_time: object, fallback_dt: datetime | None = None) -> str:
    fallback = fallback_dt or datetime.now(timezone.utc)
    if isinstance(raw_time, (int, float)) and not isinstance(raw_time, bool) and math.isfinite(raw_time):
        return _format_utc(datetime.fromtimestamp(float(raw_time), tz=timezone.utc))
    if isinstance(raw_time, str) and raw_time.strip():
        s = raw_time.strip()
        if s.endswith(" UTC"):
            s = s[:-4] + "+00:00"
        elif s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return _format_utc(dt)
        except ValueError:
            pass
    return _format_utc(fallback)


def _to_nullable_float(val: object) -> float | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return 1.0 if val else 0.0
    if isinstance(val, (int, float)):
        f = float(val)
        return f if math.isfinite(f) else None
    if isinstance(val, str):
        s = val.strip().lower()
        if s in ("nan", "inf", "-inf", "+inf", "null", "none", ""):
            return None
        try:
            f = float(s)
            return f if math.isfinite(f) else None
        except ValueError:
            return None
    return None


def to_clickhouse_node_health_row(doc: dict) -> dict:
    """Flatten one v5-health/1 JSON report into a ClickHouse node_health row.

    Matches schema_v1.sql definition:
      timestamp_utc, host, mode, expected_gpus, gpus_seen, verdict, admit_training,
      drain_reason, checks_pass, checks_warn, checks_fail, checks_skipped,
      xid_codes, ecc_uncorrectable_total, nccl_status, runtime_seconds, raw_json.
    """
    checks = doc.get("checks", [])
    if not isinstance(checks, list):
        checks = []

    by_name = {c["name"]: c for c in checks if isinstance(c, dict) and "name" in c}
    inv = by_name.get("gpu_inventory", {}).get("metrics", {})
    xid_metrics = by_name.get("xid", {}).get("metrics", {})
    ecc_values = by_name.get("ecc_uncorrectable", {}).get("metrics", {}).get("values", [])
    nccl = by_name.get("nccl_all_reduce", {}) or by_name.get("nccl_probe", {})

    counts = {
        s: sum(1 for c in checks if isinstance(c, dict) and c.get("status") == s)
        for s in STATUSES
    }

    xid_codes: list[int] = []
    counts_dict = xid_metrics.get("counts") if isinstance(xid_metrics, dict) else {}
    if isinstance(counts_dict, dict):
        xid_codes = sorted(int(k) for k in counts_dict.keys() if str(k).isdigit())
    if not xid_codes and isinstance(xid_metrics, dict) and isinstance(xid_metrics.get("events"), list):
        seen_codes = set()
        for ev in xid_metrics["events"]:
            if isinstance(ev, dict) and "code" in ev and isinstance(ev["code"], int):
                seen_codes.add(ev["code"])
        xid_codes = sorted(seen_codes)

    ecc_total = 0
    if isinstance(ecc_values, list):
        for v in ecc_values:
            if isinstance(v, (int, float)) and math.isfinite(v):
                ecc_total += int(v)

    gpus_seen = 0
    if isinstance(inv, dict) and "count" in inv and isinstance(inv["count"], int):
        gpus_seen = inv["count"]
    elif isinstance(inv, dict) and isinstance(inv.get("gpus"), list):
        gpus_seen = len(inv["gpus"])

    expected = int(doc.get("expected_gpus") or 0)
    admit = 1 if doc.get("admit_training") else 0
    ts = str(doc.get("timestamp_utc") or doc.get("time") or _format_utc(datetime.now(timezone.utc)))

    return {
        "timestamp_utc": ts,
        "host": str(doc.get("host") or "unknown-host"),
        "mode": str(doc.get("mode") or "prolog"),
        "expected_gpus": expected,
        "gpus_seen": gpus_seen,
        "verdict": str(doc.get("verdict") or "unknown"),
        "admit_training": admit,
        "drain_reason": str(doc.get("drain_reason") or ""),
        "checks_pass": counts["pass"],
        "checks_warn": counts["warn"],
        "checks_fail": counts["fail"],
        "checks_skipped": counts["skipped"],
        "xid_codes": xid_codes,
        "ecc_uncorrectable_total": ecc_total,
        "nccl_status": str(nccl.get("status") or "not_run"),
        "runtime_seconds": float(doc.get("runtime_seconds") or 0.0),
        "raw_json": json.dumps(doc, sort_keys=True),
    }


def extract_telemetry_metrics(doc: dict, run_id: str) -> list[dict]:
    """Extract GPU temperature, memory, utilization, and host metrics into metrics_raw rows."""
    metrics_rows: list[dict] = []
    checks = doc.get("checks", [])
    if not isinstance(checks, list):
        return metrics_rows

    base_time = _parse_time(doc.get("timestamp_utc") or doc.get("time"))

    for c in checks:
        if not isinstance(c, dict):
            continue
        c_name = c.get("name")
        c_gpu = c.get("gpu")
        rank = int(c_gpu) if isinstance(c_gpu, int) and c_gpu >= 0 else 0
        c_metrics = c.get("metrics")
        if not isinstance(c_metrics, dict):
            continue

        if c_name == "gpu_temperature" and "temp_c" in c_metrics:
            val = _to_nullable_float(c_metrics["temp_c"])
            metrics_rows.append({
                "run_id": run_id,
                "step": 0,
                "time": base_time,
                "name": "temp_c",
                "value": val,
                "rank": rank,
            })
        elif c_name == "host_mem" and "available_gb" in c_metrics:
            val = _to_nullable_float(c_metrics["available_gb"])
            metrics_rows.append({
                "run_id": run_id,
                "step": 0,
                "time": base_time,
                "name": "host_mem_available_gb",
                "value": val,
                "rank": 0,
            })
        elif c_name == "gpu_inventory" and "count" in c_metrics:
            val = _to_nullable_float(c_metrics["count"])
            metrics_rows.append({
                "run_id": run_id,
                "step": 0,
                "time": base_time,
                "name": "gpus_seen",
                "value": val,
                "rank": 0,
            })

    return metrics_rows


def parse_node_log_text(text: str, default_run_id: str, run_id_override: str | None = None) -> dict:
    """Parse node health logs (single JSON or JSONL stream) into node_health and metrics_raw rows."""
    stripped = text.strip()
    resolved_run_id = run_id_override or default_run_id

    # 1. Single JSON document
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            doc = json.loads(stripped)
            if isinstance(doc, dict) and (doc.get("schema") == "v5-health/1" or "verdict" in doc or "checks" in doc):
                node_row = to_clickhouse_node_health_row(doc)
                metric_rows = extract_telemetry_metrics(doc, resolved_run_id)
                null_rows = sum(1 for r in metric_rows if r["value"] is None)
                return {
                    "run_id": resolved_run_id,
                    "jsonl_lines": 1,
                    "node_health_rows": [node_row],
                    "metrics_raw_rows": metric_rows,
                    "metric_rows": len(metric_rows),
                    "null_rows": null_rows,
                }
        except json.JSONDecodeError:
            pass

    # 2. JSONL stream (multiple lines: node_health reports and/or live gpu_sample lines)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    node_rows: list[dict] = []
    metrics_rows: list[dict] = []
    null_rows = 0

    for idx, line in enumerate(lines):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue

        if rec.get("schema") == "v5-health/1" or ("verdict" in rec and "checks" in rec):
            node_row = to_clickhouse_node_health_row(rec)
            node_rows.append(node_row)
            m_rows = extract_telemetry_metrics(rec, resolved_run_id)
            metrics_rows.extend(m_rows)
            for mr in m_rows:
                if mr["value"] is None:
                    null_rows += 1
            continue

        # TSAI GPU telemetry event (gpu_sample)
        if rec.get("event") == "gpu_sample" and isinstance(rec.get("metrics"), dict):
            step = int(rec.get("step") or idx)
            time_str = _parse_time(rec.get("timestamp") or rec.get("time"))
            rank = 0
            if isinstance(rec.get("gpu"), dict) and isinstance(rec["gpu"].get("index"), int):
                rank = rec["gpu"]["index"]

            for m_name, m_val in rec["metrics"].items():
                val = _to_nullable_float(m_val)
                if val is None:
                    null_rows += 1
                canonical_name = "gpu_utilization" if m_name == "gpu_util_pct" else str(m_name)
                metrics_rows.append({
                    "run_id": resolved_run_id,
                    "step": step,
                    "time": time_str,
                    "name": canonical_name,
                    "value": val,
                    "rank": rank,
                })

    return {
        "run_id": resolved_run_id,
        "jsonl_lines": len(lines),
        "node_health_rows": node_rows,
        "metrics_raw_rows": metrics_rows,
        "metric_rows": len(metrics_rows),
        "null_rows": null_rows,
    }


def resolve_file(path_str: str) -> tuple[str, Path]:
    p = Path(path_str)
    if not p.is_absolute():
        cand = REPO_ROOT / p
        if cand.exists():
            p = cand
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path_str}")
    try:
        rel = str(p.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        rel = str(p)
    return rel, p


def load_node_logs(
    source_path: str,
    run_id_override: str | None = None,
    url: str = DEFAULT_CH_URL,
    dry_run: bool = False,
) -> dict:
    """Parse node logs and load into ClickHouse node_health and metrics_raw tables."""
    rel_path, abs_path = resolve_file(source_path)
    text = abs_path.read_text(encoding="utf-8")
    default_run_id = abs_path.stem
    parsed = parse_node_log_text(text, default_run_id, run_id_override=run_id_override)
    parsed["source_file"] = rel_path

    if dry_run:
        return parsed

    ensure_schema(url=url)
    run_id = parsed["run_id"]
    safe_run = run_id.replace("'", "''")
    safe_src = rel_path.replace("'", "''")

    # Ingest node_health rows
    if parsed["node_health_rows"]:
        body = ("\n".join(json.dumps(r, separators=(",", ":")) for r in parsed["node_health_rows"]) + "\n").encode("utf-8")
        ch_exec("INSERT INTO node_health FORMAT JSONEachRow", data=body, url=url)

    # Ingest metrics_raw rows (if telemetry metrics extracted)
    if parsed["metrics_raw_rows"]:
        ch_exec(
            f"ALTER TABLE metrics_raw DELETE WHERE run_id = '{safe_run}' SETTINGS mutations_sync = 2",
            url=url,
        )
        body_m = ("\n".join(json.dumps(r, separators=(",", ":")) for r in parsed["metrics_raw_rows"]) + "\n").encode("utf-8")
        ch_exec("INSERT INTO metrics_raw FORMAT JSONEachRow", data=body_m, url=url)

    # Ingest manifest record
    ch_exec(
        f"ALTER TABLE ingest_manifest DELETE WHERE run_id = '{safe_run}' AND source_file = '{safe_src}' SETTINGS mutations_sync = 2",
        url=url,
    )
    manifest_row = {
        "run_id": run_id,
        "source_file": rel_path,
        "jsonl_lines": parsed["jsonl_lines"],
        "metric_rows": len(parsed["node_health_rows"]) + len(parsed["metrics_raw_rows"]),
        "null_rows": parsed["null_rows"],
    }
    ch_exec(
        "INSERT INTO ingest_manifest (run_id, source_file, jsonl_lines, metric_rows, null_rows) FORMAT JSONEachRow",
        data=(json.dumps(manifest_row) + "\n").encode("utf-8"),
        url=url,
    )

    return parsed


def run_selftest() -> bool:
    """Self-test parsing and row conversion offline without requiring ClickHouse server."""
    synthetic_report = {
        "schema": "v5-health/1",
        "timestamp_utc": "2026-11-03T10:00:00.000Z",
        "time": "2026-11-03T10:00:00.000Z",
        "host": "h200-node-01",
        "mode": "prolog",
        "expected_gpus": 8,
        "verdict": "pass",
        "admit_training": True,
        "drain_reason": None,
        "runtime_seconds": 0.42,
        "checks": [
            {
                "name": "gpu_inventory",
                "status": "pass",
                "required": True,
                "metrics": {"count": 8, "gpus": ["0", "1", "2", "3", "4", "5", "6", "7"]},
                "gpu": None,
            },
            {
                "name": "gpu_temperature",
                "status": "pass",
                "required": True,
                "metrics": {"temp_c": 38.5},
                "gpu": 0,
            },
            {
                "name": "xid",
                "status": "pass",
                "required": False,
                "metrics": {"counts": {}, "events": []},
                "gpu": None,
            },
            {
                "name": "ecc_uncorrectable",
                "status": "pass",
                "required": True,
                "metrics": {"values": [0, 0, 0, 0, 0, 0, 0, 0]},
                "gpu": None,
            },
        ],
    }

    parsed = parse_node_log_text(json.dumps(synthetic_report), "selftest_run")
    assert parsed["jsonl_lines"] == 1
    assert len(parsed["node_health_rows"]) == 1
    row = parsed["node_health_rows"][0]
    assert row["host"] == "h200-node-01"
    assert row["verdict"] == "pass"
    assert row["admit_training"] == 1
    assert row["gpus_seen"] == 8
    assert row["expected_gpus"] == 8
    assert row["checks_pass"] == 4
    assert row["ecc_uncorrectable_total"] == 0
    assert row["xid_codes"] == []

    # Telemetry metrics extraction
    assert len(parsed["metrics_raw_rows"]) == 2
    metrics_map = {r["name"]: r["value"] for r in parsed["metrics_raw_rows"]}
    assert metrics_map["gpus_seen"] == 8.0
    assert metrics_map["temp_c"] == 38.5

    # Test JSONL stream parsing with both health report and gpu_sample telemetry
    telemetry_line = json.dumps({
        "schema_version": 1,
        "event": "gpu_sample",
        "timestamp": "2026-11-03T10:00:01.000Z",
        "step": 1,
        "gpu": {"index": 0, "name": "H200"},
        "metrics": {"gpu_util_pct": 78.0, "power_w": 280.5, "temp_c": 44.0},
    })
    jsonl_text = json.dumps(synthetic_report) + "\n" + telemetry_line
    parsed_jsonl = parse_node_log_text(jsonl_text, "jsonl_selftest")
    assert parsed_jsonl["jsonl_lines"] == 2
    assert len(parsed_jsonl["node_health_rows"]) == 1
    assert len(parsed_jsonl["metrics_raw_rows"]) == 5  # 2 from report + 3 from gpu_sample
    print("[PASS] load_node_logs self-test passed (node_health & metrics_raw parsing verified)")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest node health and telemetry logs into ClickHouse.")
    ap.add_argument("sources", nargs="*", help="File paths or JSONL node logs to load")
    ap.add_argument("--defaults", action="store_true", help="Load default sample health report")
    ap.add_argument("--run-id", default=None, help="Explicit run_id override")
    ap.add_argument("--url", default=DEFAULT_CH_URL, help=f"ClickHouse HTTP URL (default: {DEFAULT_CH_URL})")
    ap.add_argument("--dry-run", action="store_true", help="Parse without inserting into ClickHouse")
    ap.add_argument("--selftest", action="store_true", help="Run offline parsing selftest")
    args = ap.parse_args(argv)

    if args.selftest:
        run_selftest()
        if not args.sources and not args.defaults:
            return 0

    targets = list(args.sources)
    if args.defaults or not targets:
        targets.extend(DEFAULT_SOURCES)

    for src in targets:
        res = load_node_logs(src, run_id_override=args.run_id, url=args.url, dry_run=args.dry_run)
        mode = "DRY-RUN" if args.dry_run else "LOADED"
        print(
            f"[{mode}] run_id={res['run_id']!r} source={res['source_file']} "
            f"node_rows={len(res['node_health_rows'])} metric_rows={len(res['metrics_raw_rows'])} null_rows={res['null_rows']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
