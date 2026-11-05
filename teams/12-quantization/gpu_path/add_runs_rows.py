#!/usr/bin/env python3
"""Turn GPU-path results into runs/runs.csv rows (one per format), in the team's columns.

    python add_runs_rows.py --runs runs_vllm --manifests manifest_bf16.json manifest_W4A16.json [--write]

Reads <runs>/<format>/summary.json (run_mini_vllm.py) and the manifest of each format (model_check.py, matched on
its label). Without --write it prints the rows; with --write it appends them to ../runs/runs.csv.
score is the unweighted mean of the five eval_mini primary metrics, as in the llama.cpp rows. A test run (any task
with a limit below the profile's) is refused.
"""
from __future__ import annotations

import argparse, csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS_CSV = HERE.parent / "runs" / "runs.csv"
FIELDS = ["date", "model", "revision", "format", "bpw", "size_gb", "router_type", "output_type", "eval_set", "n_items",
          "score", "score_by_kind", "quant_time_s", "eval_time_s", "gen_tok_s", "machine", "runtime", "notes"]
TASKS = ["arc_challenge", "hellaswag", "mmlu", "gsm8k", "truthfulqa_mc2"]
FULL = {"arc_challenge": 500, "hellaswag": 400, "mmlu": 10, "gsm8k": 200, "truthfulqa_mc2": 200}
EVAL_SET = ("G9 eval_mini mini (arc_challenge 500, hellaswag 400, mmlu 570, gsm8k 5-shot 200, truthfulqa_mc2 200; "
            "seed 42)")


def row(summary: dict, man: dict) -> dict:
    meta, recs = summary["run_meta"], summary["records"]
    prim = {r["task"]: r for r in recs if r["primary"]}
    missing = [t for t in TASKS if t not in prim]
    if missing:
        raise SystemExit(f"{meta['format']}: tasks not scored: {missing}")
    short = [t for t in TASKS if prim[t]["limit"] != FULL[t]]
    if short:
        raise SystemExit(f"{meta['format']}: {short} ran with a test limit; rerun without --limit")
    chk, q = man["check"], meta.get("quantize_meta") or {}
    by_kind = {t: round(prim[t]["value"], 4) for t in TASKS}
    tool = (f"llm-compressor {q['versions']['llmcompressor']} {q['method'].upper()} W4A16 g128, "
            f"compressed-tensors {q['versions']['compressed_tensors']}" if q else "none (bf16 checkpoint)")
    calib = q.get("calibration")
    notes = (f"GPU path (gpu_path/). Quantizer: {tool}"
             + (f", calibration {calib['samples']} x {calib['seq_len']} tokens of {calib['dataset']}" if calib else "")
             + f". Served by {meta['backend']}, compute dtype {meta['dtype']}, TP={meta['tensor_parallel']}, "
             f"max_model_len {meta['max_model_len']}, lm_eval {meta['lm_eval']}. Compare only with the vLLM bf16 row "
             f"(same runtime, same eval set), not with the llama.cpp rows. gen_tok_s: one stream, 256 tokens. "
             f"SHA-256 of every file: gpu_path/results/{Path(man.get('_path', 'manifest.json')).name}")
    return {
        "date": prim["arc_challenge"]["run_date"], "model": meta["model"], "revision": meta["model_revision"][:12],
        "format": meta["format"], "bpw": chk["bpw"], "size_gb": chk["size_gb"],
        "router_type": "|".join(chk["router_dtypes"]), "output_type": chk["output_dtype"], "eval_set": EVAL_SET,
        "n_items": sum(prim[t]["n_items"] for t in TASKS),
        "score": round(sum(by_kind.values()) / len(TASKS), 4), "score_by_kind": json.dumps(by_kind),
        "quant_time_s": q.get("quant_time_s", 0.0),
        "eval_time_s": round(sum(prim[t]["wall_clock_s"] for t in TASKS)), "gen_tok_s": meta["gen_tok_s"],
        "machine": meta["hardware"], "runtime": meta["backend"].split(" via ")[0], "notes": notes,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True, type=Path)
    ap.add_argument("--manifests", required=True, nargs="+", type=Path)
    ap.add_argument("--csv", type=Path, default=RUNS_CSV)
    ap.add_argument("--write", action="store_true", help="append to the csv (default: print only)")
    args = ap.parse_args()

    mans = {}
    for p in args.manifests:
        m = json.loads(p.read_text()); m["_path"] = str(p); mans[m["label"]] = m
    rows = []
    for s in sorted(args.runs.glob("*/summary.json")):
        summary = json.loads(s.read_text())
        fmt = summary["run_meta"]["format"]
        if fmt not in mans:
            sys.exit(f"{fmt}: no manifest with that label")
        rows.append(row(summary, mans[fmt]))
    w = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
    w.writeheader(); w.writerows(rows)
    if args.write:
        with open(args.csv, "a", newline="") as fh:
            csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n").writerows(rows)   # runs.csv uses LF
        print(f"appended {len(rows)} rows to {args.csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
