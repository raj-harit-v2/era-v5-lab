#!/usr/bin/env python3
"""Task 5: check that the KE2 input path folds into a normal ``V x d_model`` embedding table.

The KE2 code of a token depends only on its id, and the projection is linear, so for every id

    E[id] = W · z(id) = low(L) · Σ_j W[:, j] + (high(L) − low(L)) · Σ_{p<L} W[:, b_p·P + p]

with ``high`` and ``low`` from ``ke2.codec.code_values`` (Lemma 1). Team 12 writes ``E`` as ``token_embd.weight``
(GGUF) or ``model.embed_tokens.weight`` (HF); ``teams/12-quantization/scripts/export_hf.py`` (``fold_ke2``) builds it
by running Team 5's ``KE2`` module over every id. This script folds all 131,072 ids of the frozen p1536 table and measures:

1. fold == trainer: rows of the folded table, looked up for eight random ``(8, 256)`` batches (16,384 sampled ids),
   are bit-identical to Team 5's ``KE2(ids)``, the forward pass dry run 1 trains;
2. fp32 fold vs float64 closed form, on all ids: the largest absolute and relative row error;
3. bf16 storage, on all ids: the error of rounding the folded table to bf16, relative to each row's largest entry;
4. special tokens: the role ids and all 356 special ids have a finite, non-zero row.

The projection is a seeded random ``normal(0, 1/sqrt(8192))`` matrix (Team 5's init) unless ``--checkpoint`` gives a
trained one (a ``train_week2.py`` ``checkpoint.pt`` with ``embedding.projection.weight``, ``embedding.rows`` and
``embedding.lengths``). Writes ``results/fold/fold_check_P32.{json,md}`` (``--out`` to change).

    python teams/04-ke2/src/export/fold_check.py [--width 512] [--checkpoint PATH/checkpoint.pt]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import torch

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ke2.codec import code_values  # noqa: E402
from ke2.config import CHAR_DIM, FROZEN_TABLES_DIR, FROZEN_TOKENIZER_SHA256, RESULTS_DIR, TEAM_DIR  # noqa: E402

TEAMS_DIR = TEAM_DIR.parent
sys.path.insert(0, str(TEAMS_DIR / "05-architecture" / "harness"))
from week2.model import KE2  # noqa: E402  Team 5: the class dry run 1 trains

P = 32
TABLE = FROZEN_TABLES_DIR / f"raw_table_P{P}.npz"
TABLE_CONTENT_SHA256 = "21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a"
TOKENIZER_MANIFEST = TEAMS_DIR / "03-tokenizer" / "train" / "p1536_s0_manifest.json"
ROLE_IDS = {"id 36 (no role)": 36, "bos": 130725, "pad": 130726, "unk": 130727, "eos": 130822}
OUT_DIR = RESULTS_DIR / "fold"
CHUNK = 8192  # the chunk export_hf.fold_ke2 uses


def table_content_sha256(rows: np.ndarray, lengths: np.ndarray) -> str:
    """Content hash of a raw table, as Team 5's ``Artifacts`` and ``trainer_adapter.md`` define it."""
    h = hashlib.sha256(f"ke2-table-v2|raw|{rows.shape[1]}|".encode())
    h.update(np.ascontiguousarray(rows, dtype=np.uint8).tobytes())
    h.update(np.ascontiguousarray(lengths, dtype="<i2").tobytes())
    return h.hexdigest()


def load_inputs(checkpoint: Path | None, width: int, seed: int):
    """Byte table and projection weight ``W`` (d_model x 8192), from a checkpoint or seeded at Team 5's init."""
    z = np.load(TABLE)
    rows, lengths = z["bytes"], z["lengths"]
    source = {"table": str(TABLE.relative_to(TEAM_DIR)), "tokenizer_sha256": str(z["tokenizer_sha256"])}
    if checkpoint is not None:
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)
        state = state.get("model", state)
        weight = state["embedding.projection.weight"].float()
        if not torch.equal(state["embedding.rows"].cpu(), torch.from_numpy(rows)) or not torch.equal(
            state["embedding.lengths"].cpu().long(), torch.from_numpy(lengths.astype(np.int64))
        ):
            sys.exit("the checkpoint's embedding.rows / embedding.lengths are not the frozen p1536 table")
        source["projection"] = f"checkpoint {checkpoint.name}"
    else:
        g = torch.Generator().manual_seed(seed)
        weight = torch.randn(width, CHAR_DIM * P, generator=g) / np.sqrt(CHAR_DIM * P)
        source["projection"] = f"random normal(0, 1/sqrt({CHAR_DIM * P})), seed {seed}"
    return rows, lengths, weight, source


def fold_trainer(module: KE2, vocab: int) -> torch.Tensor:
    """The folded table exactly as export_hf.fold_ke2 builds it: Team 5's module over every id, in chunks."""
    with torch.no_grad():
        return torch.cat([module(torch.arange(i, min(i + CHUNK, vocab))) for i in range(0, vocab, CHUNK)])


def fold_f64_chunk(rows: np.ndarray, lengths: np.ndarray, w64: torch.Tensor, w_sum: torch.Tensor) -> torch.Tensor:
    """Closed-form float64 fold of a block of ids: (high - low) · Σ_p W[:, b_p·P + p] + low · Σ_j W[:, j]."""
    high, low = code_values(lengths.astype(np.int64), P)
    idx = torch.from_numpy(rows.astype(np.int64) * P + np.arange(P))
    valid = torch.from_numpy(np.arange(P)[None, :] < lengths[:, None])
    support = (w64[idx] * valid[:, :, None]).sum(1)
    return torch.from_numpy(high - low)[:, None] * support + torch.from_numpy(low)[:, None] * w_sum


def special_ids(vocab: int) -> list[int]:
    """The 356 special ids from Team 3's p1536 manifest: the ids outside the top block, then the top block itself."""
    spec = json.loads(TOKENIZER_MANIFEST.read_text(encoding="utf-8"))["layout"]["specials"]
    outside = spec["ids_outside_top_block"]
    ids = sorted({*outside, *range(vocab - (spec["count"] - len(outside)), vocab)})
    if len(ids) != spec["count"]:
        sys.exit(f"special ids: {len(ids)} found, the manifest says {spec['count']}")
    return ids


def check(rows, lengths, weight: torch.Tensor, seed: int = 0, n_batches: int = 8) -> dict:
    vocab, width = len(rows), weight.shape[0]
    module = KE2(rows, lengths, width)
    module.projection.weight.data.copy_(weight)

    t0 = time.perf_counter()
    folded = fold_trainer(module, vocab)
    fold_seconds = time.perf_counter() - t0

    # 1. lookup in the folded table == the trainer's forward, bit for bit, on random (B, T) batches
    g = torch.Generator().manual_seed(seed)
    n_diff = 0
    for _ in range(n_batches):
        ids = torch.randint(0, vocab, (8, 256), generator=g)
        with torch.no_grad():
            n_diff += int((module(ids) != folded[ids]).any(-1).sum())

    # 2 and 3: fp32 fold and its bf16 rounding against the float64 closed form, row by row
    w64 = weight.double().t().contiguous()  # (8192, d_model)
    w_sum = w64.sum(0)
    abs32 = np.empty(vocab)
    rel32 = np.empty(vocab)
    rel16 = np.empty(vocab)
    row_max = np.empty(vocab)
    for i in range(0, vocab, CHUNK):
        j = min(i + CHUNK, vocab)
        ref = fold_f64_chunk(rows[i:j], lengths[i:j], w64, w_sum)
        scale = ref.abs().amax(-1)
        e32 = (folded[i:j].double() - ref).abs().amax(-1)
        e16 = (folded[i:j].bfloat16().double() - ref).abs().amax(-1)
        abs32[i:j], rel32[i:j], rel16[i:j], row_max[i:j] = (t.numpy() for t in (e32, e32 / scale, e16 / scale, scale))

    # 4. special tokens
    specials = special_ids(vocab)
    spec = folded[specials]
    roles = {name: {"id": i, "length": int(lengths[i]), "row_max_abs": float(folded[i].abs().max())}
             for name, i in ROLE_IDS.items()}

    worst32 = int(np.argmax(rel32))
    worst16 = int(np.argmax(rel16))
    return {
        "vocab": vocab,
        "width": width,
        "fold_seconds_cpu": round(fold_seconds, 2),
        "folded_finite": bool(torch.isfinite(folded).all()),
        "lookup_vs_trainer": {"batches": n_batches, "tokens": n_batches * 8 * 256, "rows_differ": n_diff},
        "fp32_fold_vs_f64": {
            "max_abs": float(abs32.max()),
            "max_rel_to_row_max": float(rel32.max()),
            "worst_id": worst32,
            "worst_id_length": int(lengths[worst32]),
        },
        "bf16_storage_vs_f64": {
            "max_rel_to_row_max": float(rel16.max()),
            "median_rel_to_row_max": float(np.median(rel16)),
            "worst_id": worst16,
            "bf16_unit_roundoff": 2.0**-8,
        },
        "row_max_abs": {"min": float(row_max.min()), "median": float(np.median(row_max)), "max": float(row_max.max())},
        "special_tokens": {
            "count": len(specials),
            "all_finite": bool(torch.isfinite(spec).all()),
            "all_nonzero": bool((spec.abs().amax(-1) > 0).all()),
            "roles": roles,
        },
        "parameters": {
            "projection_trained": CHAR_DIM * P * width,
            "folded_table": vocab * width,
            "folded_table_bf16_bytes": vocab * width * 2,
        },
    }


def write_md(path: Path, rec: dict) -> None:
    r = rec["result"]
    f32, b16, lk, sp = r["fp32_fold_vs_f64"], r["bf16_storage_vs_f64"], r["lookup_vs_trainer"], r["special_tokens"]
    ok = rec["pass"]
    lines = [
        f"# Task 5: KE2 fold check, P = {P} (generated by `src/export/fold_check.py`; do not edit)",
        "",
        f"**{'PASS' if ok else 'FAIL'}.** Frozen p1536 table, content sha256 `{rec['inputs']['table_content_sha256']}`; "
        f"tokenizer `{rec['inputs']['tokenizer_sha256']}`. Projection: {rec['inputs']['projection']}, "
        f"d_model {r['width']}. CPU, torch {rec['environment']['torch']}.",
        "",
        "| Check | Ids | Result |",
        "|---|---:|---|",
        f"| folded lookup vs Team 5 `KE2(ids)`, sampled ids | {lk['tokens']:,} | {lk['rows_differ']} rows differ (bit-for-bit) |",
        f"| fp32 fold vs float64 closed form | {r['vocab']:,} | max abs {f32['max_abs']:.1e}, "
        f"max relative to row max {f32['max_rel_to_row_max']:.1e} (id {f32['worst_id']}, L = {f32['worst_id_length']}) |",
        f"| bf16-stored fold vs float64 | {r['vocab']:,} | max relative {b16['max_rel_to_row_max']:.2e}, "
        f"median {b16['median_rel_to_row_max']:.2e} (bf16 unit roundoff 2^-8 = {b16['bf16_unit_roundoff']:.2e}) |",
        f"| special tokens (Team 3 p1536 manifest) | {sp['count']} | finite {sp['all_finite']}, non-zero {sp['all_nonzero']} |",
        f"| all rows finite | {r['vocab']:,} | {r['folded_finite']} |",
        "",
        "| Role | Id | Bytes | Row max abs |",
        "|---|---:|---:|---:|",
        *[f"| {k} | {v['id']} | {v['length']} | {v['row_max_abs']:.4f} |" for k, v in sp["roles"].items()],
        "",
        f"Fold time on CPU: {r['fold_seconds_cpu']} s. Parameters: projection {r['parameters']['projection_trained']:,} "
        f"(trained), folded table {r['parameters']['folded_table']:,} "
        f"({r['parameters']['folded_table_bf16_bytes'] / 2**20:.0f} MiB in bf16).",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--width", type=int, default=512, help="d_model for the random projection (T2 width 512)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--checkpoint", type=Path, help="train_week2.py checkpoint.pt (uses its trained projection)")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    rows, lengths, weight, source = load_inputs(args.checkpoint, args.width, args.seed)
    content = table_content_sha256(rows, lengths)
    if content != TABLE_CONTENT_SHA256:
        sys.exit(f"table content sha256 {content} is not the frozen p1536 table {TABLE_CONTENT_SHA256}")
    if source["tokenizer_sha256"] != FROZEN_TOKENIZER_SHA256:
        sys.exit(f"table built from tokenizer {source['tokenizer_sha256']}, not p1536 {FROZEN_TOKENIZER_SHA256}")

    result = check(rows, lengths, weight, seed=args.seed)
    ok = (
        result["folded_finite"]
        and result["lookup_vs_trainer"]["rows_differ"] == 0
        and result["fp32_fold_vs_f64"]["max_rel_to_row_max"] < 1e-5
        and result["bf16_storage_vs_f64"]["max_rel_to_row_max"] <= 2.0**-8
        and result["special_tokens"]["all_finite"]
        and result["special_tokens"]["all_nonzero"]
    )
    rec = {
        "pass": bool(ok),
        "inputs": {"table_content_sha256": content, **source, "pos_dim": P},
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__,
                        "platform": platform.system(), "device": "cpu"},
        "tolerances": {"fp32_fold_max_rel": 1e-5, "bf16_storage_max_rel": 2.0**-8, "lookup_rows_differ": 0},
        "result": result,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"fold_check_P{P}.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    write_md(args.out / f"fold_check_P{P}.md", rec)
    print(json.dumps({"pass": rec["pass"], **{k: result[k] for k in ("lookup_vs_trainer", "fp32_fold_vs_f64",
                                                                      "bf16_storage_vs_f64")}}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
