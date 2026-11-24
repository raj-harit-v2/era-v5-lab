"""Tables for results/b5_sampler_2026-11-23.md from the raw files of capstone/bench_rl_step_g5.py (every number in the
result file is printed here from a raw line).

    python capstone/b5_tables.py results/b5_sampler_2026-11-23/raw
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def load(root: Path):
    recs = []
    for f in sorted(root.glob("*/raw.jsonl")):
        for line in f.read_text().splitlines():
            r = json.loads(line)
            r["arm"] = f.parent.name
            recs.append(r)
    return recs


def main(argv=None) -> int:
    root = Path((argv or sys.argv[1:])[0])
    recs = load(root)
    for f in sorted(root.glob("*/env.json")):
        e = json.loads(f.read_text())
        print(f"env {f.parent.name}: gpu {e['gpu']} torch {e['torch']} dtype {e['dtype']} tier {e['tier']} params {e['params']:,}")
    print("\n## decode (stop disabled: rows x max_new tokens)")
    print("| arm | tier | dtype | mode | rows | prompts x k | max_new | seconds | tok/s | ms per decode step | peak GB |")
    print("|---|---|---|---|---:|---|---:|---:|---:|---:|---:|")
    for r in recs:
        if r["kind"] == "decode" and "seconds" in r:
            print(f"| {r['arm']} | {r['tier']} | {r['dtype']} | {r['mode']} | {r['rows']} | {r['prompts']} x {r['k']} | {r['max_new']} | "
                  f"{r['seconds']} | {r['tok_per_s']} | {r['ms_per_step']} | {r['peak_gb']} |")
        elif r["kind"] == "decode" and (r.get("oom") or r.get("stopped_after_rows") or r.get("skipped")):
            print(f"| {r['arm']} | {r['tier']} | {r.get('dtype', '')} | {r['mode']} | {r.get('rows', r.get('stopped_after_rows'))} | | | "
                  f"{'OOM' if r.get('oom') else r.get('reason') or r.get('skipped')} | | | |")
    print("\n## matched pairs: batched (sample_many) vs per_prompt (one call per prompt), same prompts, same rows")
    by = {}
    for r in recs:
        if r["kind"] == "decode" and "seconds" in r:
            by[(r["arm"], r["mode"], r["rows"], r["max_new"])] = r
    for (arm, mode, rows, mx), r in sorted(by.items()):
        if mode == "batched" and (arm, "per_prompt", rows, mx) in by:
            p = by[(arm, "per_prompt", rows, mx)]
            print(f"- {arm} rows {rows} max_new {mx}: per_prompt {p['seconds']} s, batched {r['seconds']} s, "
                  f"speedup {p['seconds'] / r['seconds']:.2f}x; seconds per prompt's k samples (r): per_prompt "
                  f"{p['seconds'] / p['prompts']:.2f}, batched {r['seconds'] / r['prompts']:.2f}")
    print("\n## attention fix before/after (same T4, same command; arms named v1_* = before, v2_* = after)")
    dec = [r for r in recs if r["kind"] == "decode" and "seconds" in r and r["mode"] == "batched"]
    before = [r for r in dec if "_v1_" in r["arm"]]
    for r in [r for r in dec if "_v2_" in r["arm"]]:
        for b in before:
            if b["rows"] == r["rows"] and b["max_new"] == r["max_new"]:
                print(f"- rows {r['rows']} max_new {r['max_new']}: before ({b['arm']}) {b['seconds']} s {b['tok_per_s']} tok/s "
                      f"peak {b['peak_gb']} GB; after ({r['arm']}) {r['seconds']} s {r['tok_per_s']} tok/s peak {r['peak_gb']} GB; "
                      f"{b['seconds'] / r['seconds']:.2f}x")
    print("\n## time per decode step against position (instrumented call)")
    for r in recs:
        if r["kind"] == "positions" and r.get("steps"):
            st = r["steps"]
            n = len(st)
            q = [st[int(n * f)] for f in (0.0, 0.25, 0.5, 0.75)] + [st[-1]]
            med = statistics.median(s["step_ms"] for s in st)
            first = statistics.median(s["step_ms"] for s in st[: max(1, n // 10)])
            last = statistics.median(s["step_ms"] for s in st[-max(1, n // 10):])
            print(f"- {r['arm']} rows {r['rows']} prompt {r['prompt_len']}: prefill {r['prefill_ms']} ms; median step {med:.2f} ms; "
                  f"first-10% median {first:.2f}, last-10% median {last:.2f} ms; forward share of step "
                  f"{statistics.median(s['forward_ms'] / s['step_ms'] for s in st):.2f}; samples "
                  + ", ".join(f"pos {s['pos']}: {s['step_ms']}" for s in q))
    print("\n## one decode step split into Team 5's modules (median of 20 synced calls, ms)")
    print("| arm | dtype | rows | cache | embed | attention (1 layer) | cat (1 layer) | MoE (1 layer) | head | softmax+draw | step est. | shares |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in recs:
        if r["kind"] == "parts" and "head_ms" in r:
            sh = ", ".join(f"{k} {v}" for k, v in r["share"].items())
            print(f"| {r['arm']} | {r['dtype']} | {r['rows']} | {r['cache_len']} | {r['embedding_ms']} | {r['attention_ms']} | "
                  f"{r['cache_cat_ms']} | {r['moe_ms']} | {r['head_ms']} | {r['sample_ms']} | {r['step_estimate_ms']} | {sh} |")
        elif r["kind"] == "parts":
            print(f"| {r['arm']} | {r['dtype']} | {r['rows']} | {r['cache_len']} | OOM | | | | | | | |")
    print("\n## the trainer's update on one group (k rows of prompt + max_new)")
    print("| arm | tier | dtype | rows | micro rows | seq len | old log-probs s | fwd+bwd s | clip+AdamW s | peak GB |")
    print("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in recs:
        if r["kind"] == "update":
            if r.get("oom"):
                print(f"| {r['arm']} | {r['tier']} | {r['dtype']} | {r['rows']} | {r['micro_rows']} | {r['seq_len']} | OOM | | | |")
            else:
                print(f"| {r['arm']} | {r['tier']} | {r['dtype']} | {r['rows']} | {r['micro_rows']} | {r['seq_len']} | "
                      f"{r['old_logprobs_s']} | {r['fwd_bwd_s']} | {r['opt_step_s']} | {r['peak_gb']} |")
    print("\n## parity under each dtype (max |dlogit| vs Team 5's full forward; tolerance 1e-4 is for fp32)")
    for r in recs:
        if r["kind"] == "parity":
            print(f"- {r['arm']} ({r['tier']}): {r['max_abs_dlogit']:.3g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
