"""Evaluation-only per-row NLL and paired cluster bootstrap for the WP2 supplement.

Uses the existing bench loss and byte-count functions. No training or generation.
The measured collection used one row per forward, FP32, TF32 off. Bootstrap
matches the study's 10,000 paired cluster resamples and empirical endpoints.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import random
import sys
from pathlib import Path


def collect(a):
    import torch

    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    bench = Path(__file__).resolve().parents[1] / "sft" / "bench"
    spec = importlib.util.spec_from_file_location("wp2_eval_rows", bench / "evaluate.py")
    ev = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ev
    spec.loader.exec_module(ev)
    train = ev._load("wp2_train_rows", bench / "train.py")
    rows = [json.loads(line) for line in Path(a.split_file).read_text().splitlines() if line.strip()]
    if any(row.get("split") == "train" for row in rows):
        raise ValueError("evaluation collector refuses training rows")
    if a.max_rows is not None:
        rows = rows[:a.max_rows]
    if not rows:
        raise ValueError("empty evaluation input")
    model = ev.load_model(a.model, a.revision, a.device)
    result = []
    for row in rows:
        b = train.collate([row], 0)
        b = train.probe.Batch(b.input_ids.to(a.device), b.attention_mask.to(a.device),
                              b.labels.to(a.device), b.kinds.to(a.device))
        with torch.no_grad():
            nats, _ = train.target_nll_sum(model, b)
        result.append({"id": row["id"], "cluster": row["cluster"], "nats": float(nats),
                       "bytes": ev.retok.target_bytes_of(row["surrogate_text"])})
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result))
    print(json.dumps({"rows": len(result), "clusters": len({r['cluster'] for r in result}),
                      "bpb": sum(r["nats"] for r in result) / math.log(2) / sum(r["bytes"] for r in result),
                      "device": a.device, "dtype": "float32", "tf32": False}))


def bootstrap(a):
    arms, contract = {}, None
    for item in a.arm:
        label, path = item.split("=", 1)
        rows = json.loads(Path(path).read_text())
        current = {(r["id"], r["cluster"], r["bytes"]) for r in rows}
        if len(current) != len(rows) or any(r["bytes"] <= 0 or not math.isfinite(r["nats"]) for r in rows):
            raise ValueError("duplicate or invalid per-row input")
        if contract is not None and current != contract:
            raise ValueError("arms differ in row IDs, clusters or byte denominators")
        contract = current
        grouped = {}
        for row in rows:
            n, b = grouped.get(row["cluster"], (0.0, 0))
            grouped[row["cluster"]] = (n + row["nats"], b + row["bytes"])
        arms[label] = grouped
    keys = sorted(next(iter(arms.values())))
    if not keys:
        raise ValueError("empty evaluation input")

    def bpb(c, sample):
        return sum(c[k][0] for k in sample) / math.log(2) / sum(c[k][1] for k in sample)

    rng, result = random.Random(0), {}
    for item in a.pair:
        left, right = item.split(":", 1)
        values = []
        for _ in range(10000):
            sample = [rng.choice(keys) for _ in keys]
            values.append(bpb(arms[left], sample) - bpb(arms[right], sample))
        values.sort()
        result[f"{left} - {right}"] = {
            "diff": round(bpb(arms[left], keys) - bpb(arms[right], keys), 5),
            "ci95": [round(values[249], 5), round(values[9749], 5)]}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--model", required=True)
    c.add_argument("--revision")
    c.add_argument("--split-file", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--device", default="cpu", choices=["cpu", "cuda", "mps"])
    c.add_argument("--max-rows", type=int)
    b = sub.add_parser("bootstrap")
    b.add_argument("--arm", action="append", required=True, help="label=per-row.json")
    b.add_argument("--pair", action="append", required=True, help="left:right; order affects the fixed RNG stream")
    b.add_argument("--out", required=True)
    a = ap.parse_args()
    if getattr(a, "max_rows", None) is not None and a.max_rows <= 0:
        ap.error("--max-rows must be positive")
    (collect if a.command == "collect" else bootstrap)(a)


if __name__ == "__main__":
    main()
