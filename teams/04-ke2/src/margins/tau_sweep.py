#!/usr/bin/env python3
"""Margin table per script class and the tau (acceptance threshold) sweep, P = 32 (Gate 2).

Margin = best cosine minus second-best cosine over the whole raw byte table, for every token's own
code as the query, encoded by the upstream codec in fp32 and in bf16. The table reports, per script
class (``ke2.script_class``), the smallest margin and the token pair that produces it, next to the
Theorem 3 closed form for that pair.

tau sweep. A query is "valid" when its best cosine is at least tau. Clean fp32 and bf16 codes always
have best cosine 1 (to rounding), so tau only matters for imperfect vectors. Until Team 5 delivers
predicted vectors, three synthetic error models stand in:

* ``noise_cos_<c>``: isotropic Gaussian noise added to the clean code, sigma chosen so the expected
  cosine to the true code is c in {0.95, 0.9, 0.8, 0.7, 0.5, 0.3}:  sigma = ||z|| / sqrt(D) * sqrt(1/c^2 - 1).
  In D = 8,192 dimensions such noise is nearly orthogonal to every code, so it lowers the best cosine
  without flipping the argmax.
* ``garbage``: isotropic Gaussian vectors (N(0, 1) per coordinate) with no true token; every accept is a
  wrong accept. Best cosine about sqrt(2 ln V / D), about 0.05.
* ``rival_mix_<a>``: q = (1 - a) z_true + a z_rival with z_rival the code of the token's full-vocabulary
  runner-up (from the fp32 margin pass), a in {0.3, 0.45, 0.55, 0.7}. The argmax flips near a = 0.5 while
  the best cosine stays close to 1: a wrong answer that tau cannot see.
* ``external`` (``--vectors team5.npz``): predicted vectors in code space, an npz with ``vectors`` (N, D)
  float and ``true_ids`` (N,) int64, -1 where the true token is unknown (then the query counts as not
  correct and has no true cosine).

For each condition and each tau in {0, 0.3, 0.5, 0.7, 0.9}: accept rate, accuracy among accepted,
wrong-accept rate, reject-correct rate, accept rate among correct decodes, plus the argmax accuracy and
the structural (Theorem 2) accuracy for comparison. ``propose_tau`` applies the rule in its docstring
(also stated in decision_input.md section 3): tau is a garbage filter, chosen to reject garbage without rejecting
correct decodes under mild noise.

Outputs, next to build_min_margin.py's in results/min_margin/: margins_P32_{fp32,bf16}.{npz,csv} (the per-token pass the
sweep needs: best and second-best cosine and the rival id for every token), tau_margin_pass_P32.md (the per-class minima
of that pass; they agree with min_margin_P32.md in every class minimum, though a tie may name another token of the pair), tau_rates_P32.{json,md} and tau_summary_P32.json.

usage: python src/margins/tau_sweep.py --tokenizer <tokenizer.json or folder> [--out results/min_margin] [--sample 10000] [--chunk 4096]
       python src/margins/tau_sweep.py --skip-margins [--vectors team5.npz]   # reuse the saved margin passes, redo only the tau sweep
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "proofs"))
    from ke2.upstream import ensure_kronecker_embeddings

    ensure_kronecker_embeddings()

import numpy as np
import torch
from decode_theorems import closed_form_cosine, decode_structural_batch, match_count

import decode_ref as dr
from ke2.codec import encode_f64, encode_ids
from ke2.config import RESULTS_DIR, TABLES_DIR, TOKENIZER_SHA256
from ke2.scoring import StructuredScorer
from ke2.script_class import classify_vocab
from ke2.tables import ByteTable
from ke2.tokenizer import load_tokenizer, resolve_tokenizer_path

TAUS = (0.0, 0.3, 0.5, 0.7, 0.9)
NOISE_TARGETS = (0.95, 0.9, 0.8, 0.7, 0.5, 0.3)
RIVAL_MIXES = (0.3, 0.45, 0.55, 0.7)
QUALITY_FLOOR_COS = 0.7  # isotropic conditions with target cosine >= this must keep >= 99% of correct decodes
DTYPES = {"fp32": torch.float32, "bf16": torch.bfloat16}


def score_vocabulary(table: ByteTable, ct, scorer: StructuredScorer, dtype: torch.dtype, chunk: int = 4096) -> dict:
    """Every token's own code (upstream codec in ``dtype``) scored against the whole table."""
    V = table.vocab_size
    best_id, second_id = np.empty(V, np.int64), np.empty(V, np.int64)
    best, second = np.empty(V), np.empty(V)
    for s in range(0, V, chunk):
        ids = np.arange(s, min(s + chunk, V))
        Q = encode_ids(ids, table, out_dtype=dtype).to(torch.float64)
        bi, b, si, sc = scorer.top2(Q)
        best_id[s : s + ids.size], best[s : s + ids.size] = bi.numpy(), b.numpy()
        second_id[s : s + ids.size], second[s : s + ids.size] = si.numpy(), sc.numpy()
    return {"best_id": best_id, "best": best, "second_id": second_id, "second": second, "margin": best - second}


def _text(b: bytes) -> str:
    return b.decode("utf-8", errors="replace")


def margin_rows(table: ByteTable, res: dict, classes: list[str]) -> list[dict]:
    """One row per script class: the smallest margin and the pair that produces it."""
    rows = []
    cls = np.asarray(classes)
    for c in sorted(set(classes)):
        idx = np.flatnonzero(cls == c)
        q = int(idx[np.argmin(res["margin"][idx])])
        r = int(res["second_id"][q])
        qb, rb = table.row(q), table.row(r)
        L, Lp, k = int(table.lengths[q]), int(table.lengths[r]), match_count(qb, rb)
        rows.append(
            {
                "script_class": c,
                "n_tokens": int(idx.size),
                "min_margin": float(res["margin"][q]),
                "query_id": q,
                "query_bytes_hex": qb.hex(),
                "query_text": _text(qb),
                "query_len": L,
                "runner_up_id": r,
                "runner_up_bytes_hex": rb.hex(),
                "runner_up_text": _text(rb),
                "runner_up_len": Lp,
                "overlap_k": k,
                "measured_runner_cos": float(res["second"][q]),
                "closed_form_runner_cos": float(closed_form_cosine(L, Lp, k, table.pos_dim)),
                "best_cos": float(res["best"][q]),
                "decoded_correctly": bool(res["best_id"][q] == q),
            }
        )
    return rows


def margin_markdown(rows_by_dtype: dict[str, list[dict]], P: int) -> str:
    out = []
    for name, rows in rows_by_dtype.items():
        V = sum(r["n_tokens"] for r in rows)
        out += [
            f"**Queries encoded in {name}**, P = {P}, raw byte table, cosine over all {V:,} codes.",
            "",
            "| script class | tokens | smallest margin | query (id, bytes) | runner-up (id, bytes) | L, L', shared cells k | measured runner cos | Theorem 3 cos |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in sorted(rows, key=lambda r: r["min_margin"]):
            out.append(
                f"| {r['script_class']} | {r['n_tokens']:,} | {r['min_margin']:.5f} | {r['query_id']} `{r['query_bytes_hex']}` {r['query_text']!r} | "
                f"{r['runner_up_id']} `{r['runner_up_bytes_hex']}` {r['runner_up_text']!r} | {r['query_len']}, {r['runner_up_len']}, {r['overlap_k']} | "
                f"{r['measured_runner_cos']:.6f} | {r['closed_form_runner_cos']:.6f} |"
            )
        out.append("")
    return "\n".join(out)


def _noisy(z: np.ndarray, target_cos: float, rng: np.random.Generator) -> np.ndarray:
    D = z.shape[1]
    sigma = np.linalg.norm(z, axis=1, keepdims=True) / np.sqrt(D) * np.sqrt(1 / target_cos**2 - 1)
    return z + sigma * rng.standard_normal(z.shape)


def load_external_vectors(path: Path, D: int) -> tuple[np.ndarray, np.ndarray]:
    """Team 5's predicted vectors: npz with ``vectors`` (N, D) float and ``true_ids`` (N,) int64 (-1 = unknown)."""
    with np.load(path) as z:
        if "vectors" not in z or "true_ids" not in z:
            raise ValueError(f"{path}: expected arrays 'vectors' and 'true_ids', found {sorted(z.files)}")
        vectors = np.asarray(z["vectors"], dtype=np.float64)
        true_ids = np.asarray(z["true_ids"], dtype=np.int64).reshape(-1)
    if vectors.ndim != 2 or vectors.shape[1] != D:
        raise ValueError(f"{path}: vectors must have shape (N, {D}), got {vectors.shape}")
    if true_ids.shape[0] != vectors.shape[0]:
        raise ValueError(f"{path}: true_ids has {true_ids.shape[0]} entries for {vectors.shape[0]} vectors")
    bad = np.flatnonzero(~np.isfinite(vectors).all(axis=1))
    if bad.size:
        raise ValueError(f"{path}: {bad.size} vectors contain NaN or inf (first rows {bad[:5].tolist()})")
    zero = np.flatnonzero(~vectors.any(axis=1))
    if zero.size:
        raise ValueError(
            f"{path}: {zero.size} vectors are all zero and have no direction (first rows {zero[:5].tolist()})"
        )
    return vectors, true_ids


def tau_sweep(
    table: ByteTable,
    ct,
    scorer: StructuredScorer,
    ids: np.ndarray,
    taus=TAUS,
    noise_targets=NOISE_TARGETS,
    seed: int = 0,
    chunk: int = 4096,
    runner_up_ids: np.ndarray | None = None,
    rival_mixes=RIVAL_MIXES,
    external: tuple[np.ndarray, np.ndarray] | None = None,
) -> dict:
    """Accept / wrong-accept bookkeeping per condition and tau.

    Conditions: ``clean_fp32``, ``clean_bf16``, ``noise_cos_<c>`` for c in ``noise_targets``, ``garbage``
    (isotropic vectors, no true token), ``rival_mix_<a>`` for a in ``rival_mixes`` when ``runner_up_ids``
    (the full-vocabulary runner-up of every token, indexed by token id) is given, and ``external`` when
    ``external = (vectors, true_ids)`` is given (see ``load_external_vectors``).
    """
    rng = np.random.default_rng(seed)
    P, D = table.pos_dim, ct.dim
    specs = [("clean_fp32", "fp32", None), ("clean_bf16", "bf16", None)]
    specs += [(f"noise_cos_{c}", "noise", c) for c in noise_targets]
    specs += [("garbage", "garbage", None)]
    if runner_up_ids is not None:
        specs += [(f"rival_mix_{a}", "rival", a) for a in rival_mixes]
    if external is not None:
        specs += [("external", "external", None)]

    def codes(tids):
        return encode_f64(table.bytes[tids], table.lengths[tids].astype(np.int64), P)

    conditions = []
    for name, kind, param in specs:
        if kind == "external":
            vectors, truth = external
            n = vectors.shape[0]
        else:
            n, truth = ids.size, ids
        best_id, best = np.empty(n, np.int64), np.empty(n)
        true_cos, struct_ok = np.full(n, np.nan), np.zeros(n, bool)
        known = truth >= 0  # all True except for external queries with unknown truth
        for s in range(0, n, chunk):
            sl = slice(s, min(s + chunk, n))
            t = truth[sl]
            z64 = codes(np.where(t >= 0, t, 0))  # placeholder code for unknown truth, masked out below
            if kind == "noise":
                Q = _noisy(z64, param, rng)
            elif kind == "garbage":
                Q = rng.standard_normal((t.size, D))
            elif kind == "rival":
                Q = (1 - param) * z64 + param * codes(np.asarray(runner_up_ids)[t])
            elif kind == "external":
                Q = vectors[sl]
            else:
                Q = encode_ids(t, table, out_dtype=DTYPES[kind]).to(torch.float64).numpy()
            bi, b, _, _ = scorer.top2(torch.from_numpy(np.ascontiguousarray(Q)))
            best_id[sl], best[sl] = bi.numpy(), b.numpy()
            if kind != "garbage":
                tc = (Q * z64).sum(1) / (np.linalg.norm(Q, axis=1) * np.linalg.norm(z64, axis=1))
                true_cos[sl] = np.where(t >= 0, tc, np.nan)
                want = [table.row(int(i)) if i >= 0 else None for i in t]
                struct_ok[sl] = [
                    w is not None and g == w for g, w in zip(decode_structural_batch(Q, P), want, strict=False)
                ]
        correct = np.zeros(n, bool) if kind == "garbage" else (best_id == truth) & known
        rows = []
        for tau in taus:
            acc = best >= tau
            rows.append(
                {
                    "tau": tau,
                    "accept_rate": float(acc.mean()),
                    "accuracy_among_accepted": float(correct[acc].mean()) if acc.any() else None,
                    "accept_rate_among_correct": float(acc[correct].mean()) if correct.any() else None,
                    "correct_accept_rate": float((acc & correct).mean()),
                    "wrong_accept_rate": float((acc & ~correct).mean()),
                    "reject_correct_rate": float((~acc & correct).mean()),
                }
            )
        has_truth = kind != "garbage" and bool(known.any())
        conditions.append(
            {
                "name": name,
                "kind": kind,
                "queries": int(n),
                "unknown_truth": int((~known).sum()),
                "target_cos": param if kind == "noise" else None,
                "mix": param if kind == "rival" else None,
                "mean_true_cos": float(np.nanmean(true_cos)) if has_truth else None,
                "mean_best_cos": float(best.mean()),
                "min_best_cos": float(best.min()),
                "max_best_cos": float(best.max()),
                "argmax_accuracy": float(correct.mean()),
                "structural_accuracy": float(struct_ok[known].mean()) if has_truth else None,
                "taus": rows,
            }
        )
    return {
        "P": int(P),
        "vocab_size": int(table.vocab_size),
        "queries": int(ids.size),
        "seed": seed,
        "taus": list(taus),
        "conditions": conditions,
    }


def _row(cond: dict, tau: float) -> dict:
    return next(r for r in cond["taus"] if r["tau"] == tau)


def _quality_conditions(sweep: dict, floor_cos: float = QUALITY_FLOOR_COS) -> list[dict]:
    return [c for c in sweep["conditions"] if c.get("kind") == "noise" and c["target_cos"] >= floor_cos]


def propose_tau(
    sweep: dict,
    max_garbage_accept: float = 0.01,
    min_correct_accept: float = 0.99,
    floor_cos: float = QUALITY_FLOOR_COS,
) -> float:
    """tau is a garbage filter. Rule: the smallest tau in the grid that rejects at least 99% of ``garbage``
    queries (wrong-accept <= 1% on that condition) while accepting at least 99% of the correct decodes in
    every isotropic condition with target cosine >= 0.7 (``noise_cos_0.95``, ``_0.9``, ``_0.8``, ``_0.7``).
    If no tau satisfies both, the smallest that satisfies the garbage criterion is returned (and
    ``proposal_report`` sets ``proposal_satisfies_quality_floor`` to False); if none rejects garbage,
    the largest tau in the grid. Raises ValueError when the sweep has no ``garbage`` condition."""
    return proposal_report(sweep, max_garbage_accept, min_correct_accept, floor_cos)["proposed_tau"]


def proposal_report(
    sweep: dict,
    max_garbage_accept: float = 0.01,
    min_correct_accept: float = 0.99,
    floor_cos: float = QUALITY_FLOOR_COS,
) -> dict:
    """``propose_tau`` plus its bookkeeping: whether the quality floor held, and the wrong-accept rate at the
    proposed tau in every ``rival_mix`` condition (the confusions tau does not catch)."""
    garbage = next((c for c in sweep["conditions"] if c["name"] == "garbage"), None)
    if garbage is None:
        raise ValueError("propose_tau needs the 'garbage' condition; run tau_sweep with it included")
    quality = _quality_conditions(sweep, floor_cos)

    def rejects_garbage(tau):
        return _row(garbage, tau)["wrong_accept_rate"] <= max_garbage_accept

    def keeps_correct(tau):
        return all((_row(c, tau)["accept_rate_among_correct"] or 0.0) >= min_correct_accept for c in quality)

    both = [t for t in sweep["taus"] if rejects_garbage(t) and keeps_correct(t)]
    garbage_only = [t for t in sweep["taus"] if rejects_garbage(t)]
    if both:
        tau, ok = min(both), True
    elif garbage_only:
        tau, ok = min(garbage_only), False
    else:
        tau, ok = max(sweep["taus"]), False
    rivals = {c["name"]: _row(c, tau)["wrong_accept_rate"] for c in sweep["conditions"] if c.get("kind") == "rival"}
    return {
        "proposed_tau": float(tau),
        "proposal_satisfies_quality_floor": ok,
        "rule": {
            "max_garbage_accept": max_garbage_accept,
            "min_correct_accept": min_correct_accept,
            "quality_floor_cos": floor_cos,
            "quality_conditions": [c["name"] for c in quality],
        },
        "rival_wrong_accept_at_tau": rivals,
    }


def _fmt(x, spec=".3f") -> str:
    return "-" if x is None else format(x, spec)


def tau_markdown(sweep: dict, report: dict) -> str:
    proposed = report["proposed_tau"]
    out = [
        f"{sweep['queries']:,} query tokens (seed {sweep['seed']}), P = {sweep['P']}, raw byte table of {sweep['vocab_size']:,} codes. "
        f"Proposed tau = **{proposed}**"
        + ("" if report["proposal_satisfies_quality_floor"] else " (quality floor NOT met; garbage criterion only)")
        + ".",
        "",
        "| condition | mean cos to true code | argmax accuracy | structural (Theorem 2) accuracy | "
        + " | ".join(f"tau {t}: accept / acc. among accepted / wrong-accept" for t in sweep["taus"])
        + " |",
        "|---|---|---|---|" + "---|" * len(sweep["taus"]),
    ]
    for c in sweep["conditions"]:
        cells = [
            f"{r['accept_rate']:.3f} / {_fmt(r['accuracy_among_accepted'])} / {r['wrong_accept_rate']:.3f}"
            for r in c["taus"]
        ]
        label = c["name"] + (
            f" ({c['queries']:,} vectors, {c['unknown_truth']:,} without known truth)"
            if c.get("kind") == "external"
            else ""
        )
        out.append(
            f"| {label} | {_fmt(c['mean_true_cos'])} | {c['argmax_accuracy']:.4f} | {_fmt(c['structural_accuracy'], '.4f')} | "
            + " | ".join(cells)
            + " |"
        )
    rivals = [c for c in sweep["conditions"] if c.get("kind") == "rival"]
    rule = report["rule"]
    out += [
        "",
        f"Rule: tau is the smallest value in the grid that accepts at most {rule['max_garbage_accept']:.0%} of `garbage` queries "
        f"while keeping at least {rule['min_correct_accept']:.0%} of the correct decodes in every isotropic condition with target "
        f"cosine >= {rule['quality_floor_cos']} ("
        + ", ".join(f"`{n}`" for n in rule["quality_conditions"])
        + "); if no tau "
        "satisfies both, the smallest that rejects garbage is returned and the quality floor is reported as not met; if none "
        "rejects garbage, the largest tau in the grid.",
    ]
    if rivals:
        floor = min(c["min_best_cos"] for c in rivals)
        caught = ", ".join(f"{k}: {v:.3f}" for k, v in report["rival_wrong_accept_at_tau"].items())
        out += [
            "",
            "tau is a garbage filter: it rejects vectors far from every code; it cannot separate a near-code wrong answer "
            f"from a right one (best cosine above {np.floor(floor * 100) / 100:.2f} in every rival_mix condition). Wrong-accept rate at "
            f"tau = {proposed} by condition (the confusions tau does not catch): {caught}. The margin (best minus second-best "
            "cosine) is the quantity that detects rival confusions, and Team 5's decoder should report both.",
        ]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", default=None, help="tokenizer.json or folder (default: $KE2_TOKENIZER)")
    ap.add_argument("--table", type=Path, default=TABLES_DIR / "raw_table_P32.npz")
    ap.add_argument("--out", type=Path, default=RESULTS_DIR / "min_margin")
    ap.add_argument("--sample", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--chunk", type=int, default=4096, help="queries scored per block")
    ap.add_argument(
        "--skip-margins",
        action="store_true",
        help="reuse the saved margins_P32_*.npz and tau_summary_P32.json in --out; redo only the tau sweep",
    )
    ap.add_argument(
        "--vectors",
        type=Path,
        default=None,
        help="npz with 'vectors' (N, D) and 'true_ids' (N,) (-1 = unknown): added to the sweep as condition 'external'",
    )
    a = ap.parse_args(argv)
    t0 = time.perf_counter()
    tb = load_tokenizer(str(resolve_tokenizer_path(a.tokenizer)), expected_sha256=TOKENIZER_SHA256)
    table = ByteTable.load(a.table, tokenizer=tb)
    ct = dr.CodeTable.from_byte_table(table)
    scorer = StructuredScorer(ct, "cpu", torch.float64)
    external = load_external_vectors(a.vectors, ct.dim) if a.vectors is not None else None
    a.out.mkdir(parents=True, exist_ok=True)
    P = table.pos_dim
    if a.skip_margins:
        summary_path = a.out / f"tau_summary_P{P}.json"
        if not summary_path.is_file():
            raise SystemExit(f"--skip-margins needs {summary_path}; run once without it first")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary["table_sha256"] != ct.table_sha256:
            raise SystemExit(
                f"saved tau_summary is for table {summary['table_sha256'][:12]}..., not {ct.table_sha256[:12]}..."
            )
        with np.load(a.out / f"margins_P{P}_fp32.npz") as z:
            runner_up = np.asarray(z["second_id"])
        print("skip-margins: reusing saved margin passes", flush=True)
    else:
        classes = classify_vocab(tb)
        rows_by_dtype, summary = (
            {},
            {"P": P, "table_sha256": ct.table_sha256, "tokenizer_sha256": tb.sha256, "dtypes": {}},
        )
        runner_up = None
        for name, dtype in DTYPES.items():
            res = score_vocabulary(table, ct, scorer, dtype, chunk=a.chunk)
            if name == "fp32":
                runner_up = res["second_id"]  # the rival_mix conditions use the fp32 runner-up
            np.savez_compressed(a.out / f"margins_P{P}_{name}.npz", **res)
            rows = margin_rows(table, res, classes)
            rows_by_dtype[name] = rows
            with open(a.out / f"margins_P{P}_{name}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            summary["dtypes"][name] = {
                "decoded_correctly": int((res["best_id"] == np.arange(table.vocab_size)).sum()),
                "min_margin": float(res["margin"].min()),
                "argmin_id": int(res["margin"].argmin()),
                "median_margin": float(np.median(res["margin"])),
                "min_best_cos": float(res["best"].min()),
            }
            print(
                f"{name}: decoded {summary['dtypes'][name]['decoded_correctly']}/{table.vocab_size}, min margin {summary['dtypes'][name]['min_margin']:.5f}",
                flush=True,
            )
        (a.out / f"tau_margin_pass_P{P}.md").write_text(margin_markdown(rows_by_dtype, P), encoding="utf-8")
        summary["margin_pass_seconds"] = round(time.perf_counter() - t0, 1)
    t1 = time.perf_counter()
    ids = np.random.default_rng(a.seed).choice(table.vocab_size, a.sample, replace=False)
    sweep = tau_sweep(table, ct, scorer, ids, seed=a.seed, chunk=a.chunk, runner_up_ids=runner_up, external=external)
    report = proposal_report(sweep)
    (a.out / f"tau_rates_P{P}.json").write_text(json.dumps({**sweep, **report}, indent=2) + "\n", encoding="utf-8")
    (a.out / f"tau_rates_P{P}.md").write_text(tau_markdown(sweep, report), encoding="utf-8")
    summary.update(
        **report,
        external_vectors=str(a.vectors) if a.vectors is not None else None,
        tau_sweep_seconds=round(time.perf_counter() - t1, 1),
        environment={
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "device": "cpu",
        },
    )
    (a.out / f"tau_summary_P{P}.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if not a.skip_margins:
        print((a.out / f"tau_margin_pass_P{P}.md").read_text())
    print((a.out / f"tau_rates_P{P}.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
