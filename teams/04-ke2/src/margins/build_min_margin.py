#!/usr/bin/env python3
"""KE2 minimum decode margin per script class, with fp32 and bf16 checks.

For every token of the raw byte table at capacity P, the *self margin* is
``cos(z_t, z_t) - max over s != t of cos(z_t, z_s)``, against the whole vocabulary (it equals
decode_ref's margin when t decodes to itself). Two stages:

  storage  pair_margins: exact float64 scores from per-token code values held in fp64 (reference),
           fp32 (upstream codec output) and bf16 (that output cast down); every token, every pair
  scoring  dense_check: the k worst tokens of every class re-decoded with dense matrix products in
           fp32, bf16 with fp32 accumulation, and bf16 with bf16-rounded dot products

Outputs (default: teams/04-ke2/results/min_margin/):
  min_margin_by_class_P{P}.csv  one row per (precision, script class): minimum margin and its pair
  dense_check_P{P}.csv          one row per (mode, checked token)
  summary_P{P}.json             provenance, per-precision and per-mode totals, gate
  min_margin_P{P}.md            the same as Markdown tables (generated)

Usage:
  python build_min_margin.py [--tokenizer PATH_OR_HF_ID] [--allow-download] [--P 32] [--out DIR]
                             [--chunk-rows 64] [--worst-k 3] [--sample N]
The exhaustive run takes about 11 minutes at P = 32 on an Apple M1. Exit status 1 if the gate fails.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import logging
import re
import sys
import time
import unicodedata
from collections.abc import Sequence
from pathlib import Path

HERE = Path(__file__).resolve().parent  # teams/04-ke2/src/margins
SRC = HERE.parent  # teams/04-ke2/src (ke2 package, decode_ref.py)
for _p in (SRC, HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

from dense_check import MODES, dense_check  # noqa: E402
from ke2.config import HF_ID, POS_DIMS, RESULTS_DIR, TOKENIZER_SHA256  # noqa: E402
from ke2.tables import ByteTable  # noqa: E402
from pair_margins import (  # noqa: E402
    PRECISIONS,
    SelfMargins,
    codec_values,
    self_margins,
    value_pairs_per_length,
)

log = logging.getLogger("build_min_margin")

BF16_STEP_BELOW_ONE = 2.0**-8
"""Spacing of bf16 values just below 1.0: the unit of the ``bf16_steps`` column."""

CLASS_COLUMNS = [
    "P",
    "table",
    "precision",
    "script_class",
    "n_tokens",
    "min_margin",
    "bf16_steps",
    "token_id",
    "token_hex",
    "token_text",
    "token_len",
    "rival_id",
    "rival_hex",
    "rival_text",
    "rival_len",
    "rival_class",
    "overlap",
    "n_nonpositive",
]
DENSE_COLUMNS = [
    "P",
    "mode",
    "script_class",
    "token_id",
    "decoded_id",
    "rival_id",
    "correct",
    "tie",
    "margin",
    "exact_margin",
    "delta",
]
GATE_DEFINITION = (
    "gate: every token's margin is > 0 in all three storage precisions (fp64, fp32, bf16), and every "
    "dense-checked token decodes to itself with margin > 0 in `fp32` and `bf16_fp32acc`; "
    "`bf16_out` is reported, not gated"
)
DEFINITION = (
    "self margin = cos(z_t, z_t) - max over s != t of cos(z_t, z_s), over the whole vocabulary; "
    "equals decode_ref's margin whenever t decodes to itself; <= 0 means a tie or a wrong decode"
)


def display_text(raw: bytes) -> str:
    """Readable text for token bytes: invalid UTF-8 and control characters as ``\\xNN``."""
    text = raw.decode("utf-8", errors="backslashreplace")
    return "".join(f"\\x{ord(c):02x}" if unicodedata.category(c) == "Cc" else c for c in text)


def _lowest(margins: np.ndarray, token_ids: np.ndarray) -> np.ndarray:
    """Positions ordered by (margin, token ID)."""
    return np.lexsort((token_ids, margins))


def class_minima(classes: Sequence[str], sm: SelfMargins, table: ByteTable) -> list[dict]:
    """One row per class of the scored tokens: the lowest margin (lowest token ID on ties) and its pair."""
    cls = np.asarray(classes, dtype=object)
    query_cls = cls[sm.token_ids]
    rows = []
    for name in sorted(set(query_cls.tolist())):
        pos = np.flatnonzero(query_cls == name)
        best = pos[_lowest(sm.margins[pos], sm.token_ids[pos])[0]]
        tid, rid = int(sm.token_ids[best]), int(sm.rival_ids[best])
        token, rival = table.row(tid), table.row(rid)
        margin = float(sm.margins[best])
        rows.append(
            {
                "P": table.pos_dim,
                "table": table.kind,
                "precision": sm.precision,
                "script_class": name,
                "n_tokens": int(pos.size),
                "min_margin": margin,
                "bf16_steps": margin / BF16_STEP_BELOW_ONE,
                "token_id": tid,
                "token_hex": token.hex(),
                "token_text": display_text(token),
                "token_len": len(token),
                "rival_id": rid,
                "rival_hex": rival.hex(),
                "rival_text": display_text(rival),
                "rival_len": len(rival),
                "rival_class": str(cls[rid]),
                "overlap": int(sm.overlaps[best]),
                "n_nonpositive": int((sm.margins[pos] <= 0).sum()),
            }
        )
    return sorted(rows, key=lambda r: (r["min_margin"], r["script_class"]))


def worst_ids(classes: Sequence[str], margins: dict[str, SelfMargins], k: int) -> np.ndarray:
    """Sorted union, over precisions, of the k lowest-margin token IDs of every class."""
    cls = np.asarray(classes, dtype=object)
    picked: set[int] = set()
    for sm in margins.values():
        query_cls = cls[sm.token_ids]
        for name in set(query_cls.tolist()):
            pos = np.flatnonzero(query_cls == name)
            order = _lowest(sm.margins[pos], sm.token_ids[pos])[:k]
            picked.update(sm.token_ids[pos[order]].tolist())
    return np.array(sorted(picked), dtype=np.int64)


def run(
    table: ByteTable,
    classes: Sequence[str],
    *,
    worst_k: int = 3,
    chunk_rows: int = 64,
    query_ids: np.ndarray | None = None,
) -> tuple[list[dict], list[dict], dict]:
    """Both stages on one table; returns ``(class_rows, dense_rows, summary)``."""
    values = {p: codec_values(table, p) for p in PRECISIONS}
    log.info("code values read for %s; scoring %s tokens", ", ".join(PRECISIONS),
             table.vocab_size if query_ids is None else len(query_ids))  # fmt: skip
    margins = self_margins(table, list(values.values()), query_ids=query_ids, chunk_rows=chunk_rows)
    class_rows = [row for p in PRECISIONS for row in class_minima(classes, margins[p], table)]

    ref = margins["fp64"]
    exact_by_id = dict(zip(ref.token_ids.tolist(), ref.margins.tolist(), strict=True))
    worst = worst_ids(classes, margins, worst_k)
    log.info("dense check of %d tokens in %s", len(worst), ", ".join(MODES))
    checks = dense_check(table, worst)
    dense_rows = []
    for mode in MODES:
        c = checks[mode]
        for tid, dec, rid, m in zip(worst.tolist(), c.decoded_ids, c.rival_ids, c.margins, strict=True):
            exact = exact_by_id[tid]
            dense_rows.append(
                {
                    "P": table.pos_dim,
                    "mode": mode,
                    "script_class": classes[tid],
                    "token_id": tid,
                    "decoded_id": int(dec),
                    "rival_id": int(rid),
                    "correct": bool(dec == tid),
                    "tie": bool(m == 0),
                    "margin": float(m),
                    "exact_margin": exact,
                    "delta": float(m) - exact,
                }
            )

    precisions = {}
    for p in PRECISIONS:
        sm, norm_sq = margins[p], values[p].norms ** 2
        i = _lowest(sm.margins, sm.token_ids)[0]
        precisions[p] = {
            "min_margin": float(sm.margins[i]),
            "token_id": int(sm.token_ids[i]),
            "rival_id": int(sm.rival_ids[i]),
            "max_abs_delta_vs_fp64": float(np.abs(sm.margins - ref.margins).max()),
            "n_nonpositive": int((sm.margins <= 0).sum()),
            "value_pairs_per_length": value_pairs_per_length(values[p]),
            "norm_sq_min": float(norm_sq.min()),
            "norm_sq_max": float(norm_sq.max()),
        }
    dense = {}
    for mode in MODES:
        c = checks[mode]
        exact = np.array([exact_by_id[t] for t in worst.tolist()])
        delta = c.margins - exact  # negative = margin lost to the scoring precision
        dense[mode] = {
            "n_queries": len(worst),
            "n_wrong": int((c.decoded_ids != worst).sum()),
            "n_ties": int((c.margins == 0).sum()),
            "min_margin": float(c.margins.min()),
            "min_delta_vs_fp64": float(delta.min()),
            "max_delta_vs_fp64": float(delta.max()),
            "max_abs_delta_vs_fp64": float(np.abs(delta).max()),
        }
    gate = all((margins[p].margins > 0).all() for p in PRECISIONS) and all(
        (checks[m].decoded_ids == worst).all() and (checks[m].margins > 0).all() for m in ("fp32", "bf16_fp32acc")
    )
    summary = {
        "P": table.pos_dim,
        "table_kind": table.kind,
        "table_sha256": table.sha256(),
        "vocab_size": table.vocab_size,
        "exhaustive": query_ids is None,
        "n_queries": int(ref.token_ids.shape[0]),
        "definition": DEFINITION,
        "bf16_step_below_one": BF16_STEP_BELOW_ONE,
        "precisions": precisions,
        "dense": dense,
        "gate_all_positive": bool(gate),
        "gate_definition": GATE_DEFINITION,
    }
    return class_rows, dense_rows, summary


def _code(text: str) -> str:
    """Token text as a code span that is safe inside a Markdown table cell.

    A run of spaces only is shown as ``␠×N`` (code spans collapse spaces). The delimiter is one
    backtick longer than the longest backtick run in the text, and ``|`` is escaped for the table.
    """
    if text and text.strip(" ") == "":
        return f"␠×{len(text)}"
    fence = "`" * (max((len(run) for run in re.findall(r"`+", text)), default=1) + 1)
    return f"{fence} {text.replace('|', chr(92) + '|')} {fence}"


def render_markdown(class_rows: list[dict], dense_rows: list[dict], summary: dict) -> str:
    """The class table and the dense-check totals as Markdown."""
    P, kind = summary["P"], summary["table_kind"]
    by = {(r["precision"], r["script_class"]): r for r in class_rows}
    ref = sorted(
        (r for r in class_rows if r["precision"] == "fp64"), key=lambda r: (r["min_margin"], r["script_class"])
    )
    lines = [
        "<!-- generated by src/margins/build_min_margin.py; do not edit -->",
        "",
        f"# Minimum decode margin per script class (P = {P}, {kind} table)",
        "",
        f"Table `{summary['table_sha256'][:12]}…`, tokenizer `{summary.get('tokenizer_sha256', 'n/a')[:12]}…`, "
        f"V = {summary['vocab_size']:,}, exhaustive: {'yes' if summary['exhaustive'] else 'no (sample)'}, "
        f"gate: {'PASS' if summary['gate_all_positive'] else 'FAIL'}.",
        "",
        f"Margin: {summary['definition']}. The pair is the class's lowest-margin token and its rival "
        "(rival may be in another class). Bytes: (token length, rival length, positions with equal bytes). "
        "fp32 / bf16 columns: class minimum with codes stored in that precision, minus the fp64 minimum "
        "(exact float64 arithmetic). Same pair: yes, swapped (the same two tokens in the other direction) "
        "or no (another pair; check its margin). bf16 steps: fp64 minimum / 2^-8, the bf16 spacing just below 1.0.",
        "",
        f"The {GATE_DEFINITION}.",
        "",
        "| script class | tokens | min margin (fp64) | token → rival | bytes (L, L′, shared) "
        "| fp32 − fp64 | bf16 − fp64 | same pair | bf16 steps |",
        "|---|--:|--:|---|---|--:|--:|---|--:|",
    ]
    for r in ref:
        c = r["script_class"]
        r32, r16 = by["fp32", c], by["bf16", c]
        pairs = [(x["token_id"], x["rival_id"]) for x in (r32, r16)]
        if all(p == (r["token_id"], r["rival_id"]) for p in pairs):
            same = "yes"
        elif all(set(p) == {r["token_id"], r["rival_id"]} for p in pairs):
            same = "swapped"  # the same two tokens; equal fp64 margins, rounding picked the other direction
        else:
            same = "no"
        lines.append(
            f"| {c} | {r['n_tokens']:,} | {r['min_margin']:.6f} "
            f"| {_code(r['token_text'])} ({r['token_id']}) → {_code(r['rival_text'])} ({r['rival_id']}) "
            f"| {r['token_len']}, {r['rival_len']}, {r['overlap']} "
            f"| {r32['min_margin'] - r['min_margin']:+.2e} | {r16['min_margin'] - r['min_margin']:+.2e} "
            f"| {same} | {r['bf16_steps']:.1f} |"
        )
    lines += [
        "",
        "## Dense scorer check",
        "",
        "The lowest-margin tokens of every class (union over precisions), decoded against the whole "
        "vocabulary with dense matrix products. `fp32`: fp32 codes and arithmetic. `bf16_fp32acc`: bf16 codes, "
        "fp32 accumulation. `bf16_out`: as `bf16_fp32acc` with each dot product rounded to bf16 "
        "(a GEMM with bf16 output). Δ is the dense margin minus the exact fp64 margin of the same token; "
        "negative means margin lost.",
        "",
        "| mode | queries | wrong | ties | min margin | largest loss (min Δ) | largest gain (max Δ) |",
        "|---|--:|--:|--:|--:|--:|--:|",
    ]
    for mode, d in summary["dense"].items():
        lines.append(
            f"| `{mode}` | {d['n_queries']} | {d['n_wrong']} | {d['n_ties']} "
            f"| {d['min_margin']:.6f} | {d['min_delta_vs_fp64']:+.2e} | {d['max_delta_vs_fp64']:+.2e} |"
        )
    return "\n".join(lines) + "\n"


def write_outputs(out_dir: Path, class_rows: list[dict], dense_rows: list[dict], summary: dict) -> None:
    """Write the two CSVs, the summary JSON and the Markdown table for ``summary['P']``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    P = summary["P"]
    for name, cols, rows in (
        (f"min_margin_by_class_P{P}.csv", CLASS_COLUMNS, class_rows),
        (f"dense_check_P{P}.csv", DENSE_COLUMNS, dense_rows),
    ):
        with open(out_dir / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    (out_dir / f"summary_P{P}.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out_dir / f"min_margin_P{P}.md").write_text(render_markdown(class_rows, dense_rows, summary), encoding="utf-8")


def _versions() -> dict:
    v = {}
    for m in ("numpy", "torch", "kronecker_embeddings"):
        try:
            v[m] = __import__(m).__version__
        except Exception:
            v[m] = None
    return v


def main(argv: list[str] | None = None) -> int:
    """Build the minimum-margin outputs for one P; return 0 if the gate passes, else 1."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", default=None, help="tokenizer.json / dir / HF id")
    ap.add_argument("--allow-download", action="store_true", help="fetch the tokenizer from the HF Hub if needed")
    ap.add_argument("--P", type=int, choices=POS_DIMS, default=32)
    ap.add_argument("--out", type=Path, default=RESULTS_DIR / "min_margin")
    ap.add_argument("--chunk-rows", type=int, default=64)
    ap.add_argument("--worst-k", type=int, default=3)
    ap.add_argument("--sample", type=int, default=None, help="score only N sampled IDs (not exhaustive)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    from decode_ref import sample_token_ids
    from ke2.script_class import classify_vocab
    from ke2.tables import build_raw_table
    from ke2.tokenizer import load_tokenizer
    from ke2.upstream import ensure_kronecker_embeddings

    ensure_kronecker_embeddings()
    t0 = time.perf_counter()
    tb = load_tokenizer(a.tokenizer, allow_download=a.allow_download)
    table = build_raw_table(tb, a.P)
    classes = classify_vocab(tb, detail=True)
    query_ids = None if a.sample is None else sample_token_ids(tb.vocab_size, tb.special_ids, n=a.sample, seed=0)
    class_rows, dense_rows, summary = run(
        table, classes, worst_k=a.worst_k, chunk_rows=a.chunk_rows, query_ids=query_ids
    )
    name = HF_ID if tb.sha256 == TOKENIZER_SHA256 else "local tokenizer (identified by tokenizer_sha256)"
    summary = {
        "tokenizer": name,
        "tokenizer_sha256": tb.sha256,
        **summary,
        "versions": _versions(),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    write_outputs(a.out, class_rows, dense_rows, summary)

    counts = collections.Counter(r["precision"] for r in class_rows)
    print(f"\nP={a.P} {table.kind} table, {summary['n_queries']:,} tokens scored, {counts['fp64']} classes")
    print(f"{'script_class':<52} {'tokens':>7} {'fp64':>9} {'fp32-fp64':>10} {'bf16-fp64':>10}  token -> rival")
    by = {(r["precision"], r["script_class"]): r for r in class_rows}
    for r in (r for r in class_rows if r["precision"] == "fp64"):
        c = r["script_class"]
        print(
            f"{c:<52} {r['n_tokens']:>7} {r['min_margin']:>9.6f} {by['fp32', c]['min_margin'] - r['min_margin']:>+10.1e} "
            f"{by['bf16', c]['min_margin'] - r['min_margin']:>+10.1e}  {r['token_id']} -> {r['rival_id']}"
        )
    for mode, d in summary["dense"].items():
        print(f"dense {mode:<13} wrong {d['n_wrong']} ties {d['n_ties']} min margin {d['min_margin']:.6f}")
    print(f"gate: {'PASS' if summary['gate_all_positive'] else 'FAIL'}   wrote {Path(a.out).resolve()}")
    return 0 if summary["gate_all_positive"] else 1


if __name__ == "__main__":
    sys.exit(main())
