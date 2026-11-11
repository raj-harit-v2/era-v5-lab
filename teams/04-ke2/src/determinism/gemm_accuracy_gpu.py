#!/usr/bin/env python3
"""Measure the float32 GEMM error of KE cosine scores on a CUDA GPU, with TF32 off and on.

Explains why decode_gpu.py's float scores depend on the batch size. The same unit-norm query and candidate
codes (upstream codec, float32) are multiplied in float32 by cuBLAS at several batch sizes and compared with a
float64 product of the same float32 inputs. A float32 elementwise multiply-and-sum (a reduction tree, no cuBLAS)
is measured as a control.

Output: ``results/decode_gpu/gemm_accuracy_P<P>.json``. See ``../../determinism_gpu.md``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ in (None, ""):  # run as a script: make the ke2 package and decode_gpu importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from decode_gpu import (
    CUBLAS_WORKSPACE_CONFIG,
    OUT_DIR,
    candidate_codes,
    configure_cuda,
    gpu_environment,
    load_table,
    unit_rows,
)
from ke2.config import CHAR_DIM, TABLES_DIR, TOKENIZER_SHA256
from ke2.upstream import ensure_kronecker_embeddings


def errors(scores, exact, query_ids, candidate_ids) -> dict:
    """Largest and median absolute error, where the largest sits, and the largest error on a query's own code."""
    err = (scores.double() - exact).abs()
    i, j = divmod(int(err.argmax()), err.shape[1])
    own = candidate_ids[None, :] == query_ids[:, None]
    return {
        "max_abs_error": float(err.max()),
        "median_abs_error": float(err.median()),
        "at": {"query_id": int(query_ids[i]), "candidate_id": int(candidate_ids[j]), "exact": float(exact[i, j])},
        "max_abs_error_own_code": float(err[own].max()) if bool(own.any()) else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", type=Path, default=TABLES_DIR)
    ap.add_argument("--pos-dim", type=int, default=32)
    ap.add_argument("--candidates", type=int, default=16384, help="the first N token IDs are the candidates")
    ap.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 7, 64, 512, 1024, 4096])
    ap.add_argument("--control-queries", type=int, default=64)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", CUBLAS_WORKSPACE_CONFIG)

    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; this measurement needs an NVIDIA GPU")
    ensure_kronecker_embeddings()
    from kronecker_embeddings.codec import kronecker_codec

    configure_cuda(torch)
    table = load_table(args.tables, "raw", args.pos_dim, TOKENIZER_SHA256)
    P, n_cand, n_query = table.pos_dim, args.candidates, max(args.batch_sizes)
    device = torch.device("cuda")
    with torch.inference_mode():
        byte_rows = torch.from_numpy(table.bytes[:n_cand]).to(device)
        lengths = torch.from_numpy(table.lengths[:n_cand].astype(np.int64)).to(device)
        codes = candidate_codes(kronecker_codec, byte_rows, lengths, P)
        queries = unit_rows(kronecker_codec(byte_rows[:n_query], lengths[:n_query], char_dim=CHAR_DIM, pos_dim=P))
        exact = queries.double() @ codes.double().T
        query_ids = torch.arange(n_query, device=device)
        candidate_ids = torch.arange(n_cand, device=device)
        rows = {}
        for label, tf32 in (("tf32_off", False), ("tf32_on", True)):
            torch.backends.cuda.matmul.allow_tf32 = tf32
            torch.set_float32_matmul_precision("high" if tf32 else "highest")
            rows[label] = {
                str(B): errors(queries[:B] @ codes.T, exact[:B], query_ids[:B], candidate_ids) for B in args.batch_sizes
            }
        configure_cuda(torch)
        k = args.control_queries
        control = torch.stack([(queries[i] * codes).sum(dim=1) for i in range(k)])
        report = {
            "measurement": "float32 cosine scores of unit-norm KE codes vs float64 products of the same float32 inputs",
            "inputs": {
                "table": f"results/tables/raw_table_P{P}.npz",
                "table_sha256": table.sha256(),
                "candidates": f"token IDs 0..{n_cand - 1}",
                "queries": f"token IDs 0..{n_query - 1} (a batch of size B uses the first B)",
                "code_dim": CHAR_DIM * P,
            },
            "nvidia_tf32_override": os.environ.get("NVIDIA_TF32_OVERRIDE"),
            "cublas_matmul": rows,
            "control_elementwise_sum_tf32_off": {
                "queries": k,
                **errors(control, exact[:k], query_ids[:k], candidate_ids),
            },
            "environment": gpu_environment(torch),
        }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"gemm_accuracy_P{P}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for label, by_size in rows.items():
        print(label, {b: f"{r['max_abs_error']:.2e}" for b, r in by_size.items()})
    print("control (elementwise sum):", f"{report['control_elementwise_sum_tf32_off']['max_abs_error']:.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
