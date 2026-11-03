#!/usr/bin/env python3
"""Append one runs/runs.csv row per format from an eval_code_indic run folder.

    python to_runs_csv.py results/raw/runs_bf16-Q8_0-Q4_K_M-Q3_K_M [--csv ../runs/runs.csv] [--dry-run]

score = unweighted mean of the 11 primary metrics (acc; GSM8K exact_match flexible-extract; HumanEval+ and MBPP+
plus pass@1), per task in score_by_kind. bpw is 16 x size / bf16 size, as the week-1 rows (bf16 = 16.0).
"""
import argparse, csv, json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ["date", "model", "revision", "format", "bpw", "size_gb", "router_type", "output_type", "eval_set", "n_items",
          "score", "score_by_kind", "quant_time_s", "eval_time_s", "gen_tok_s", "machine", "runtime", "notes"]


def types_from_logs(logs: Path, fmt: str) -> dict:
    """Router (ffn_gate_inp) and output.weight types as written by convert_hf_to_gguf (bf16) or llama-quantize."""
    if fmt == "bf16":
        f, pat = logs / "convert.log", r"^.*?{name}.*?-> (\w+),"
    else:
        f, pat = logs / f"quantize_{fmt}.log", r"^.*?{name}.*?(?:converting to (\w+)|type = +(\w+) *, *size)"
    if not f.exists():
        return {}
    text = f.read_text(errors="replace")
    out = {}
    for key, name in (("router", r"ffn_gate_inp\.weight"), ("output", r"\boutput\.weight")):
        found = {next(g for g in m.groups() if g).upper() for m in re.finditer(pat.format(name=name), text, re.M)}
        if len(found) == 1:
            out[key] = found.pop()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", type=Path)
    ap.add_argument("--csv", type=Path, default=HERE.parent / "runs" / "runs.csv")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--week1-types", action="store_true",
                    help="runs made before the notebook read tensor types: fill router/output types from week 1's "
                         "identical quantization (llama.cpp b11669, same command; perplexity/screenshots/03-router-output-check.png)")
    args = ap.parse_args()

    env = json.loads((args.runs / "environment.json").read_text())
    summaries = {p.parent.name: json.loads(p.read_text()) for p in sorted(args.runs.glob("*/summary.json"))}
    bf16_bytes = summaries["bf16"]["run_meta"]["gguf_bytes"] if "bf16" in summaries else env["bf16_gguf_bytes"]
    gpus = env.get("gpu", "").splitlines()
    machine = f"Kaggle {len(gpus)}x {gpus[0].split(',')[0]}" if gpus else env["platform"]
    rows = []
    for fmt in env["settings"]["FORMATS"]:
        s = summaries[fmt]; meta = s["run_meta"]
        assert not meta.get("limit"), f"{fmt}: a LIMIT run is not a result"
        prim = [r for r in s["records"] if r["filter"] != "base"]
        by_task = {r["task"]: round(r["value"], 4) for r in prim}
        tasks = list(by_task)
        n = sum(r["n_items"] for r in prim)
        types = env["formats"][fmt].get("tensor_types", {})
        from_logs = False
        if not types:
            types = types_from_logs(args.runs / "logs", fmt)
            from_logs = bool(types)
        assumed = not types and args.week1_types
        if assumed:
            types = {"router": "F32", "output": "BF16" if fmt == "bf16" else "Q8_0"}
        rows.append({
            "date": meta["run_date"], "model": meta["model"], "revision": meta["model_revision"][:12], "format": fmt,
            "bpw": round(16 * meta["gguf_bytes"] / bf16_bytes, 2), "size_gb": round(meta["gguf_bytes"] / 1e9, 2),
            "router_type": types.get("router", ""), "output_type": types.get("output", ""),
            "eval_set": f"G9 eval-mini v0 code + Indic ({', '.join(t + ' ' + str(r['n_items']) for t, r in zip(tasks, prim))}; "
                        f"5-shot except code; spec sha256 {meta['spec_sha256'][:12]})",
            "n_items": n, "score": round(sum(by_task.values()) / len(by_task), 4),
            "score_by_kind": json.dumps(by_task), "quant_time_s": "",
            "eval_time_s": round(sum(r["wall_clock_s"] for r in prim)), "gen_tok_s": "", "machine": machine,
            "runtime": f"llama-cpp-python {meta['llama_cpp_python']} (GGUFs: llama.cpp {env['settings']['LLAMA_TAG']}), "
                       f"lm_eval {meta['lm_eval']}, evalplus {meta.get('evalplus', '')}",
            "notes": (f"score = unweighted mean of the {len(by_task)} primary metrics (acc; gsm8k exact_match "
                      f"flexible-extract; humaneval_plus/mbpp_plus plus pass@1); n_ctx {meta['n_ctx']}, longer 5-shot "
                      f"prompts left-truncated ({sum(r.get('truncated_requests') or 0 for r in prim)} requests); "
                      f"per-item comparison with bf16 in eval_code_indic/results/; run by {env.get('run_by', '')}"
                      + ("; router/output types read from this run's convert/llama-quantize log" if from_logs else "")
                      + ("; router/output types not re-read in this run: same llama.cpp b11669 llama-quantize command "
                         "as week 1, where they were checked" if assumed else "")),
        })
    for r in rows:
        print(r["format"], r["bpw"], r["size_gb"], r["router_type"], r["output_type"], r["n_items"], r["score"], r["eval_time_s"])
    if not args.dry_run:
        with open(args.csv, "a", newline="") as fh:
            csv.DictWriter(fh, FIELDS).writerows(rows)
        print(f"appended {len(rows)} rows to {args.csv}")


if __name__ == "__main__":
    main()
