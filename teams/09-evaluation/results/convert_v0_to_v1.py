"""Convert eval-mini v0 result files to the v1 schema (results/eval_mini_v1_schema.md).

Two v0 shapes are read, and the shape is detected from the file:
    records   a flat `records` list in fractions 0-1: results/eval_mini_v0.json (PR #21), and Team 12's summary.json
    by model  nested by model, in points: results/eval_mini_v0_code_indic.json (PR #88), with its eval-mini spec

Every record is checked (schema section 7) before anything is written; any failure stops the script with exit code 1.

Usage (from this folder):
    python convert_v0_to_v1.py                                  # both repo files -> eval_mini_v1.json (expects 98 records)
    python convert_v0_to_v1.py --inputs <summary.json> --out <file> --expect 0
                                                                # Team 12: convert your own v0 records
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

RESULTS = Path(__file__).resolve().parent
DEFAULT_INPUTS = ["eval_mini_v0.json", "eval_mini_v0_code_indic.json"]
DEFAULT_OUT = "eval_mini_v1.json"
DEFAULT_EXPECT = 98  # 59 (PR #21) + 27 lm-eval scores + 12 code scores (PR #88)

KEY = ("model", "model_revision", "format", "item_set", "task", "num_fewshot", "metric", "filter")
REQUIRED = ("model", "model_revision", "checkpoint", "format", "backend", "dtype", "task", "metric", "filter", "primary",
            "value", "stderr", "n_items", "item_set", "num_fewshot", "decoding", "seed", "harness", "hardware", "run_date")
FORMAT_OF_DTYPE = {"bfloat16": "bf16", "float16": "fp16", "float32": "fp32"}
GENERATIVE = {"gsm8k"}
LOGLIKELIHOOD = {"arc_challenge", "arc_easy", "arc_average", "hellaswag", "mmlu", "truthfulqa_mc2", "leaderboard_mmlu_pro"}
LOGLIKELIHOOD_PREFIXES = ("belebele_", "milu_")
LM_EVAL_DEFAULT_SEEDS = {"random": 0, "numpy": 1234, "torch": 1234, "fewshot": 1234}  # lm_eval 0.4.13 defaults.py
FILE_NOTES = [
    "GSM8K: our 4-shot full-set scores are 6-7 points under Qwen's own report. The gap is prompt format: lm-eval and the "
    "SmolLM2 card's lighteval agree with each other and not with Qwen's figure (results/compare_v0.md).",
    "HellaSwag: its items are internal only (the Hugging Face copy states no licence). This file holds scores of public "
    "models, not items.",
]


def decoding_of(task):
    if task in GENERATIVE:
        return "greedy"
    if task in LOGLIKELIHOOD or task.startswith(LOGLIKELIHOOD_PREFIXES):
        return "loglikelihood"
    sys.exit(f"unknown task {task!r}: add it to GENERATIVE or LOGLIKELIHOOD")


def points(fraction):
    return None if fraction is None else round(100 * fraction, 2)


def from_records(data):
    """PR #21 shape (also Team 12's summary.json): fractions 0-1, one seed for all four generators."""
    meta = data.get("run_meta") or {}
    out = []
    for x in data["records"]:
        harness = {"name": "lm_eval", "version": x["harness_version"]}
        if meta.get("g9_harness_sha256"):
            harness["script_sha256"] = meta["g9_harness_sha256"]
        seed = x["seed"]
        out.append({
            "model": x["model"], "model_revision": x["model_revision"], "checkpoint": None,
            "format": meta.get("format") or FORMAT_OF_DTYPE[x["dtype"]], "backend": meta.get("backend") or "hf",
            "dtype": x["dtype"], "task": x["task"], "metric": x["metric"], "filter": x["filter"], "primary": x["primary"],
            "value": points(x["value"]), "stderr": points(x["stderr"]),
            "n_items": x["n_items"], "n_items_total": x.get("n_items_total"),
            "item_set": "full" if x["limit"] is None else f"limit:{x['limit']}", "profile": x.get("profile"),
            "num_fewshot": x["num_fewshot"], "decoding": decoding_of(x["task"]),
            "seed": None if seed is None else {"random": seed, "numpy": seed, "torch": seed, "fewshot": seed},
            "harness": harness, "hardware": x["hardware"], "run_date": x["run_date"],
            "derived_from": x.get("derived_from"), "notes": [],
        })
        if out[-1]["value"] != round(100 * x["value"], 2):
            sys.exit(f"value check failed for {x['model']} {x['task']}")
    return out


def from_by_model(data, team_dir):
    """PR #88 shape: points already; item sets, shots and item totals come from the eval-mini spec."""
    spec_path = team_dir / data["spec_file"]
    spec_bytes = spec_path.read_bytes()
    if hashlib.sha256(spec_bytes).hexdigest() != data["spec_sha256"]:
        sys.exit(f"{spec_path}: sha256 differs from spec_sha256 in the results file")
    spec = json.loads(spec_bytes)
    evalplus = spec["code"]["harness"].split()  # "evalplus 0.3.1"
    out = []
    for m in data["models"].values():
        if m["status"] != "done":
            continue
        common = {"model": m["hf_id"], "model_revision": m["revision"], "checkpoint": None, "format": "bf16",
                  "backend": "hf", "dtype": "bfloat16",  # run_lm_eval.py and run_codegen.py load in bf16
                  "primary": True, "profile": "code_indic", "hardware": m["gpu"]["before"]["gpu"],
                  "run_date": data["generated"], "derived_from": None}
        for task, s in m["scores"].items():
            t = spec["tasks"][task]
            if s["n"] != len(t["doc_ids"]):
                sys.exit(f"{m['hf_id']} {task}: n={s['n']} but the spec lists {len(t['doc_ids'])} items")
            metric, filt = s["metric"].split(",", 1)
            out.append({**common, "task": task, "metric": metric, "filter": filt, "value": s["value"], "stderr": s["stderr"],
                        "n_items": s["n"], "n_items_total": t["n_test_docs"], "item_set": f"spec:{data['spec_sha256']}",
                        "num_fewshot": t["num_fewshot"], "decoding": decoding_of(task), "seed": dict(LM_EVAL_DEFAULT_SEEDS),
                        "harness": {"name": "lm_eval", "version": m["env"]["lm_eval"]}, "notes": []})
        for ds, c in m.get("code", {}).items():
            for split in ("base", "plus"):
                out.append({**common, "task": ds if split == "base" else f"{ds}_plus", "metric": "pass@1", "filter": "none",
                            "value": c[split], "stderr": None, "n_items": c["n"], "n_items_total": c["n"], "item_set": "full",
                            "num_fewshot": 0, "decoding": "greedy", "seed": None,
                            "harness": {"name": evalplus[0], "version": evalplus[1]},
                            "notes": ["samples generated on this GPU, executed on Linux (Colab)"]})
    return out


def build(inputs, team_dir, generated):
    records, sources, notes = [], [], list(FILE_NOTES)
    for path in inputs:
        raw = path.read_bytes()
        data = json.loads(raw)
        if "records" in data and all("model" in x for x in data["records"]):
            records += from_records(data)
        elif "models" in data and "spec_sha256" in data:
            records += from_by_model(data, team_dir)
            notes += [n for n in (data.get("note"), data.get("noise_note")) if n and n not in notes]
        else:
            sys.exit(f"{path}: neither v0 shape (no 'records' list with a model on each record, no 'models' + 'spec_sha256')")
        try:
            shown = path.resolve().relative_to(team_dir.resolve().parent.parent).as_posix()
        except ValueError:
            shown = path.name
        sources.append({"path": shown, "sha256": hashlib.sha256(raw).hexdigest(),
                        "schema_version": data.get("schema_version", "eval_mini_v0")})
    records.sort(key=lambda r: tuple(r[k] for k in KEY))
    doc = {"schema_version": "eval_mini_v1", "generated": generated, "sources": sources, "notes": notes, "records": records}
    return doc, (json.dumps(doc, indent=1, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def check(doc, expect):
    recs = doc["records"]
    keys = [tuple(r[k] for k in KEY) for r in recs]
    results = [
        ("record count", len(recs), expect if expect else len(recs)),
        ("records missing a required field", sum(any(k not in r for k in REQUIRED) for r in recs), 0),
        ("values outside 0-100", sum(not 0 <= r["value"] <= 100 for r in recs), 0),
        ("stderr neither null nor a number >= 0",
         sum(not (r["stderr"] is None or (type(r["stderr"]) in (int, float) and r["stderr"] >= 0)) for r in recs), 0),
        ("duplicate keys", len(keys) - len(set(keys)), 0),
        ("records with an empty model_revision", sum(not r["model_revision"] for r in recs), 0),
        ("records with neither a seed nor greedy decoding", sum(r["seed"] is None and r["decoding"] != "greedy" for r in recs), 0),
    ]
    ok = True
    for name, got, want in results:
        ok &= got == want
        print(f"  {'ok ' if got == want else 'FAIL'} {name}: {got} (expected {want})")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", nargs="+", type=Path, help="v0 files (default: the two files in this folder)")
    ap.add_argument("--out", type=Path, help=f"output file (default: {DEFAULT_OUT} in this folder)")
    ap.add_argument("--team-dir", type=Path, default=RESULTS.parent,
                    help="teams/09-evaluation, used to find the eval-mini spec (default: this folder's parent)")
    ap.add_argument("--expect", type=int, help=f"expected record count; 0 skips the check (default: {DEFAULT_EXPECT} "
                                                "for the two repo files)")
    ap.add_argument("--generated", default=str(date.today()), help="date written as 'generated' (default: today)")
    a = ap.parse_args()
    inputs = a.inputs or [RESULTS / f for f in DEFAULT_INPUTS]
    expect = a.expect if a.expect is not None else (DEFAULT_EXPECT if not a.inputs else 0)
    out = a.out or RESULTS / DEFAULT_OUT

    doc, data = build(inputs, a.team_dir, a.generated)
    _, again = build(inputs, a.team_dir, a.generated)
    print(f"{len(doc['records'])} records from {len(inputs)} file(s)")
    ok = check(doc, expect)
    print(f"  {'ok ' if data == again else 'FAIL'} a second build is byte-identical: {data == again}")
    if not (ok and data == again):
        sys.exit("checks failed; nothing written")
    out.write_bytes(data)
    print(f"wrote {out} ({len(data):,} bytes, sha256 {hashlib.sha256(data).hexdigest()[:16]})")


if __name__ == "__main__":
    main()
