#!/usr/bin/env python3
"""Verify that ClickHouse row counts equal JSONL line counts and `null` values are stored as NULL.

Usage:
    python -I teams/08-monitoring/clickhouse/check_rows.py
    python -I teams/08-monitoring/clickhouse/check_rows.py \
        teams/05-architecture/experiments/evidence/run_a/metrics.jsonl \
        teams/05-architecture/experiments/evidence/run_b/metrics.jsonl \
        teams/06-performance/results/modal_gpu/h200_v1.json
    python -I teams/08-monitoring/clickhouse/check_rows.py --selftest
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_jsonl import (  # noqa: E402
    DEFAULT_CH_URL,
    DEFAULT_SOURCES,
    EVAL_MINI_NULLABLE_FIELDS,
    ch_Exec,
    ensure_schema,
    load_source,
    parse_source,
)


def query_run_counts(run_id: str, url: str = DEFAULT_CH_URL, target_table: str = "metrics_raw") -> dict:
    """Query line/record count, total metric row count, and NULL counts from ClickHouse."""
    safe_run = run_id.replace("'", "''")
    if target_table == "eval_mini":
        null_selects = ", ".join(
            f"countIf({col} IS NULL) AS null_{col}" for col in EVAL_MINI_NULLABLE_FIELDS
        )
        sql = (
            "SELECT "
            "count() AS ch_lines, "
            "count() AS ch_metric_rows, "
            f"countIf(stderr IS NULL) AS ch_null_rows, {null_selects} "
            f"FROM eval_mini FINAL WHERE run_id = '{safe_run}' "
            "FORMAT JSONEachRow"
        )
        out = ch_Exec(sql, url=url).strip()
        if not out:
            return {
                "ch_lines": 0,
                "ch_metric_rows": 0,
                "ch_null_rows": 0,
                "ch_nulls_by_col": {col: 0 for col in EVAL_MINI_NULLABLE_FIELDS},
            }
        row = json.loads(out.splitlines()[0])
        return {
            "ch_lines": int(row["ch_lines"]),
            "ch_metric_rows": int(row["ch_metric_rows"]),
            "ch_null_rows": int(row["ch_null_rows"]),
            "ch_nulls_by_col": {
                col: int(row[f"null_{col}"]) for col in EVAL_MINI_NULLABLE_FIELDS
            },
        }

    sql = (
        "SELECT "
        "uniqExact(tuple(step, time, rank)) AS ch_lines, "
        "count() AS ch_metric_rows, "
        "countIf(value IS NULL) AS ch_null_rows "
        f"FROM metrics_raw WHERE run_id = '{safe_run}' "
        "FORMAT JSONEachRow"
    )
    out = ch_Exec(sql, url=url).strip()
    if not out:
        return {"ch_lines": 0, "ch_metric_rows": 0, "ch_null_rows": 0}
    row = json.loads(out.splitlines()[0])
    return {
        "ch_lines": int(row["ch_lines"]),
        "ch_metric_rows": int(row["ch_metric_rows"]),
        "ch_null_rows": int(row["ch_null_rows"]),
    }


def list_manifest_sources(url: str = DEFAULT_CH_URL) -> list[tuple[str, str]]:
    """Return `[(source_file, run_id), ...]` from `ingest_manifest`."""
    ensure_schema(url=url)
    sql = (
        "SELECT source_file, run_id "
        "FROM ingest_manifest FINAL "
        "ORDER BY run_id, source_file "
        "FORMAT JSONEachRow"
    )
    out = ch_Exec(sql, url=url).strip()
    if not out:
        return []
    pairs = []
    for line in out.splitlines():
        if line.strip():
            r = json.loads(line)
            pairs.append((r["source_file"], r["run_id"]))
    return pairs


def verify_source(source: str, run_id_override: str | None = None, url: str = DEFAULT_CH_URL) -> dict:
    """Compare source file line/metric/null counts against ClickHouse (`metrics_raw` or `eval_mini`)."""
    parsed = parse_source(source, run_id_override=run_id_override)
    target_table = parsed.get("target_table", "metrics_raw")
    run_id = parsed["run_id"]
    ch = query_run_counts(run_id, url=url, target_table=target_table)

    lines_match = ch["ch_lines"] == parsed["jsonl_lines"]
    metrics_match = ch["ch_metric_rows"] == parsed["metric_rows"]
    nulls_match = ch["ch_null_rows"] == parsed["null_rows"]
    col_nulls_match = True
    if target_table == "eval_mini":
        col_nulls_match = ch.get("ch_nulls_by_col") == parsed.get("nulls_by_col")
    ok = lines_match and metrics_match and nulls_match and col_nulls_match

    res = {
        "ok": ok,
        "target_table": target_table,
        "run_id": run_id,
        "source_file": parsed["source_file"],
        "jsonl_lines": parsed["jsonl_lines"],
        "ch_lines": ch["ch_lines"],
        "expected_metric_rows": parsed["metric_rows"],
        "ch_metric_rows": ch["ch_metric_rows"],
        "expected_null_rows": parsed["null_rows"],
        "ch_null_rows": ch["ch_null_rows"],
    }
    if target_table == "eval_mini":
        res["expected_nulls_by_col"] = parsed.get("nulls_by_col")
        res["ch_nulls_by_col"] = ch.get("ch_nulls_by_col")
    return res


def run_selftest(url: str = DEFAULT_CH_URL) -> bool:
    """Verify `metrics_raw` JSONL and `eval_mini_v1.json` null-handling and row counts in ClickHouse."""
    test_run_id = "_check_rows_selftest"
    sample_lines = [
        {"step": 0, "time": "2026-10-31T00:00:00Z", "loss_ntp": 4.2, "validation_loss": None, "mfu": None},
        {"step": 1, "time": "2026-10-31T00:00:01Z", "loss_ntp": 3.9, "validation_loss": 4.0, "mfu": 0.35},
        {"step": 2, "time": "2026-10-31T00:00:02Z", "loss_ntp": "nan", "validation_loss": None, "mfu": 0.36},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        for row in sample_lines:
            tmp.write(json.dumps(row) + "\n")
        tmp_path = Path(tmp.name)

    eval_run_id = "_check_rows_eval_mini_selftest"
    sample_eval_doc = {
        "schema_version": "eval_mini_v1",
        "generated": "2026-11-03",
        "sources": [],
        "notes": [],
        "records": [
            {
                "model": "HuggingFaceTB/SmolLM2-1.7B",
                "model_revision": "effd688a12921b4cc83e3312b6feb579f70f9c71",
                "checkpoint": None,
                "format": "bf16",
                "backend": "hf",
                "dtype": "bfloat16",
                "task": "arc_average",
                "metric": "acc_norm",
                "filter": "none",
                "primary": True,
                "value": 60.34,
                "stderr": 0.86,
                "n_items": 3548,
                "n_items_total": 3548,
                "item_set": "full",
                "profile": "check",
                "num_fewshot": 0,
                "decoding": "loglikelihood",
                "seed": {"random": 42, "numpy": 42, "torch": 42, "fewshot": 42},
                "harness": {"name": "lm_eval", "version": "0.4.13"},
                "hardware": "Apple M2 Pro",
                "run_date": "2026-10-24",
                "derived_from": ["arc_easy", "arc_challenge"],
                "notes": [],
            },
            {
                "model": "lab:w2_run_a",
                "model_revision": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                "checkpoint": {
                    "run": "w2_run_a",
                    "branch": "main",
                    "step": 2000,
                    "epoch": 1,
                    "tokens_seen": 2048000,
                    "path": "out/ckpt_store/w2_run_a/main/step_00002000-e1",
                },
                "format": "bf16",
                "backend": "lab",
                "dtype": None,
                "task": "humaneval",
                "metric": "pass@1",
                "filter": "none",
                "primary": True,
                "value": 37.20,
                "stderr": None,
                "n_items": 164,
                "n_items_total": None,
                "item_set": "full",
                "profile": None,
                "num_fewshot": 0,
                "decoding": "greedy",
                "seed": None,
                "harness": {"name": "evalplus", "version": "0.3.1"},
                "hardware": "H200",
                "run_date": "2026-11-03",
                "derived_from": None,
                "notes": [],
            },
        ],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp_ev:
        json.dump(sample_eval_doc, tmp_ev)
        tmp_ev_path = Path(tmp_ev.name)

    try:
        load_source(str(tmp_path), run_id_override=test_run_id, url=url)
        res = verify_source(str(tmp_path), run_id_override=test_run_id, url=url)
        assert res["ok"], f"Self-test failed: {res}"
        assert res["jsonl_lines"] == 3 and res["ch_lines"] == 3, f"Line count mismatch: {res}"
        assert res["expected_metric_rows"] == 9 and res["ch_metric_rows"] == 9, f"Metric row mismatch: {res}"
        assert res["expected_null_rows"] == 4 and res["ch_null_rows"] == 4, f"NULL row mismatch: {res}"

        load_source(str(tmp_ev_path), run_id_override=eval_run_id, url=url)
        res_ev = verify_source(str(tmp_ev_path), run_id_override=eval_run_id, url=url)
        assert res_ev["ok"], f"eval_mini self-test failed: {res_ev}"
        assert res_ev["ch_lines"] == 2 and res_ev["ch_null_rows"] == 1, f"eval_mini counts mismatch: {res_ev}"
        assert res_ev["ch_nulls_by_col"] == {
            "checkpoint": 1,
            "derived_from": 1,
            "seed": 1,
            "stderr": 1,
            "dtype": 1,
            "n_items_total": 1,
            "profile": 1,
        }, f"eval_mini per-column NULL mismatch: {res_ev}"
        print(
            f"  [PASS] selftest: jsonl_lines={res['jsonl_lines']} == ch_lines={res['ch_lines']}, "
            f"metric_rows={res['ch_metric_rows']}, null_rows={res['ch_null_rows']} (stored as NULL); "
            f"eval_mini records={res_ev['ch_lines']} with nullable checkpoint/derived_from/seed/stderr verified"
        )
        return True
    finally:
        tmp_path.unlink(missing_ok=True)
        tmp_ev_path.unlink(missing_ok=True)
        ch_Exec(
            f"ALTER TABLE metrics_raw DELETE WHERE run_id = '{test_run_id}' SETTINGS mutations_sync = 2",
            url=url,
        )
        ch_Exec(
            f"ALTER TABLE eval_mini DELETE WHERE run_id = '{eval_run_id}' SETTINGS mutations_sync = 2",
            url=url,
        )
        ch_Exec(
            f"ALTER TABLE ingest_manifest DELETE WHERE run_id IN ('{test_run_id}', '{eval_run_id}') SETTINGS mutations_sync = 2",
            url=url,
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify ClickHouse rows equal JSONL lines for loaded files.")
    ap.add_argument("sources", nargs="*", help="Files or directories to check (default: all loaded files in manifest)")
    ap.add_argument("--run-id", default=None, help="Explicit run_id override (when checking a single file)")
    ap.add_argument("--selftest", action="store_true", help="Run null-handling and line-count self-test")
    ap.add_argument("--url", default=DEFAULT_CH_URL, help=f"ClickHouse HTTP URL (default: {DEFAULT_CH_URL})")
    args = ap.parse_args(argv)

    if args.selftest:
        run_selftest(url=args.url)

    targets: list[tuple[str, str | None]] = []
    if args.sources:
        for s in args.sources:
            targets.append((s, args.run_id if len(args.sources) == 1 else None))
    else:
        manifest = list_manifest_sources(url=args.url)
        if manifest:
            targets = [(src, rid) for src, rid in manifest]
        elif not args.selftest:
            targets = [(s, None) for s in DEFAULT_SOURCES]

    all_ok = True
    for src, rid in targets:
        res = verify_source(src, run_id_override=rid, url=args.url)
        status = "PASS" if res["ok"] else "FAIL"
        print(
            f"[{status}] run_id={res['run_id']!r} source={res['source_file']} | "
            f"lines: file={res['jsonl_lines']} ch={res['ch_lines']} | "
            f"metric_rows: file={res['expected_metric_rows']} ch={res['ch_metric_rows']} | "
            f"null_rows: file={res['expected_null_rows']} ch={res['ch_null_rows']}"
        )
        if not res["ok"]:
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
