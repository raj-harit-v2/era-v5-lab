"""R2 comparison for the attn-3 (Half RoPE) rotation run at seed 1240.

Standard library only. Reads t2_table.json (hand-entered values, each with a cited
source) and, when TSAI returns the run files, the run directory. Writes one CSV row
per reading and metric with the seed statistics and the not-worse rule of
jobs/2026-11-10-attention-t2.md, which covers three-group, code and Indic:

    mean(attn-3) - mean(reference) <= max(range(attn-3), range(reference))

Two readings, as the job request promises: "seed_1240_alone" (attn-3 = the seed-1240
value only) and "all_seeds" (attn-3 = every posted attn-3 seed plus 1240). The bpb row
gets the gap and the spreads but no verdict, because the rule does not cover it.

A seed-1240 value is used only from a complete run: from the run directory (summary.json
says 1,221 steps, no timeout, and metrics.jsonl has the step-1,221 evaluation), or,
without run files, from t2_table.json together with its "attn3_1240_run" block
(steps, timed_out, source). Anything else exits 2 and writes no CSV.

From the repo root:
    python teams/05-architecture/jobs/evidence/2026-11-17-rotation-attn3-seed1240/compare_rotation.py \
        --table teams/05-architecture/jobs/evidence/2026-11-17-rotation-attn3-seed1240/t2_table.json \
        [--run-dir teams/05-architecture/jobs/evidence/2026-11-17-rotation-attn3-seed1240/run] \
        --out teams/05-architecture/jobs/evidence/2026-11-17-rotation-attn3-seed1240/rotation-comparison.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

STEPS = 1221
SEED = "1240"
# Metric name in t2_table.json -> key in the trainer's metrics.jsonl.
METRICS = {
    "three_group": "val/three_group_bpb",
    "code": "val/groups/code_bpb",
    "indic": "val/groups/indic_mean_bpb",
    "bpb": "val/bpb",
}
RULE_METRICS = ("three_group", "code", "indic")
READINGS = ("seed_1240_alone", "all_seeds")
COLUMNS = [
    "reading", "metric", "attn3_1240",
    "attn3_n", "attn3_mean", "attn3_range",
    "reference_n", "reference_mean", "reference_range", "reference_sd",
    "diff", "allowance", "passes", "formal",
]


def seed_stats(values: list[float]) -> dict:
    """n, mean, range (max - min) and sample SD (None for fewer than 2 values)."""
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "range": max(values) - min(values),
        "sd": statistics.stdev(values) if len(values) >= 2 else None,
    }


def not_worse(candidate: list[float], reference: list[float]) -> dict:
    """The not-worse rule for attention alternatives 1 to 3. Lower BPB is better."""
    c, r = seed_stats(candidate), seed_stats(reference)
    diff = c["mean"] - r["mean"]
    allowance = max(c["range"], r["range"])
    return {
        "diff": diff,
        "allowance": allowance,
        "passes": diff <= allowance,
        "formal": c["n"] >= 3 and r["n"] >= 3,
    }


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_run(summary: dict, metrics_rows: list[dict]) -> dict:
    """C1: all 1,221 steps, no timeout. C2: every logged number finite."""
    c1 = summary.get("steps") == STEPS and summary.get("timed_out") is False
    c2 = all(math.isfinite(v) for row in metrics_rows for v in row.values() if _is_number(v))
    if not c1:
        status = "INCOMPLETE_NOT_A_RESULT"
    elif not c2:
        status = "VOID_NONFINITE"
    else:
        status = "OK"
    return {"C1_complete": c1, "C2_finite": c2, "status": status}


def _read_run(run_dir: Path) -> tuple[dict, list[dict]] | None:
    """None when summary.json or metrics.jsonl is missing (at 71bc0fb a non-finite
    value raises inside the training loop, so summary.json is never written)."""
    summary_path, metrics_path = run_dir / "summary.json", run_dir / "metrics.jsonl"
    if not (summary_path.is_file() and metrics_path.is_file()):
        return None
    summary = json.loads(summary_path.read_text())
    rows = [json.loads(line) for line in metrics_path.read_text().splitlines() if line.strip()]
    return summary, rows


def _final_values(rows: list[dict]) -> dict:
    """Seed-1240 values from the last logged row at step 1,221 (may be partial)."""
    final = [r for r in rows if r.get("step") == STEPS]
    row = final[-1] if final else {}
    return {name: row.get(key) for name, key in METRICS.items()}


def _seeds(block: dict, metric: str, exclude: str | None = None) -> list[float]:
    return [float(v) for s, v in (block.get(metric) or {}).items() if v is not None and s != exclude]


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (bool, int, str)):
        return str(v)
    return f"{v:.6f}"


def compare(table: dict, run_values: dict | None = None) -> list[dict]:
    """One row per reading and metric. Run-file values, when given, replace the
    hand-entered seed-1240 values entirely (no per-metric mixing)."""
    values = run_values if run_values is not None else (table.get("attn3_1240") or {})
    rows = []
    for reading in READINGS:
        for metric in METRICS:
            value = values.get(metric)
            arm = [float(value)] if value is not None else []
            if reading == "all_seeds":
                arm = _seeds(table.get("attn3", {}), metric, exclude=SEED) + arm
            ref = _seeds(table.get("reference", {}), metric)
            row = {k: None for k in COLUMNS}
            row.update(reading=reading, metric=metric, attn3_1240=value)
            if arm:
                a = seed_stats(arm)
                row.update(attn3_n=a["n"], attn3_mean=a["mean"], attn3_range=a["range"])
            if ref:
                r = seed_stats(ref)
                row.update(reference_n=r["n"], reference_mean=r["mean"],
                           reference_range=r["range"], reference_sd=r["sd"])
            if arm and ref:
                rule = not_worse(arm, ref)
                row.update(diff=rule["diff"], allowance=rule["allowance"])
                if metric in RULE_METRICS:
                    row.update(passes=rule["passes"], formal=rule["formal"])
            rows.append(row)
    return rows


def _refuse(status: str, why: str) -> int:
    print(f"{status}: {why}. No BPB comparison is written.")
    return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--table", type=Path, required=True)
    p.add_argument("--run-dir", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)

    table = json.loads(args.table.read_text())
    run_values = None
    if args.run_dir:
        run = _read_run(args.run_dir)
        if run is None:
            return _refuse("INCOMPLETE_NOT_A_RESULT", f"no summary.json or metrics.jsonl in {args.run_dir}")
        checks = check_run(*run)
        for name, ok in checks.items():
            print(f"{name}: {ok if name == 'status' else ('pass' if ok else 'FAIL')}")
        if checks["status"] != "OK":
            return _refuse(checks["status"], "the run did not complete cleanly")
        run_values = _final_values(run[1])
        missing = [METRICS[m] for m, v in run_values.items() if not _is_number(v)]
        if missing:
            return _refuse("MISSING_FINAL_EVAL", f"step {STEPS} row lacks {', '.join(missing)}")
    elif any(v is not None for v in (table.get("attn3_1240") or {}).values()):
        block = table.get("attn3_1240_run")
        if not block:
            return _refuse("INCOMPLETE_NOT_A_RESULT", "attn3_1240 values have no attn3_1240_run block")
        status = check_run(block, [])["status"]
        if status != "OK":
            return _refuse(status, f"attn3_1240_run says steps={block.get('steps')}, "
                                   f"timed_out={block.get('timed_out')}")

    result = compare(table, run_values)
    with args.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for row in result:
            w.writerow({k: _fmt(v) for k, v in row.items()})
    print(f"wrote {args.out} ({len(result)} rows); source: {table.get('source', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
