"""Numerical checks for proof.md Theorem 2 (exact structural decode) and Theorem 3 (nearest-code cosine).

usage: python decode_checks.py [--tokenizer PATH] [--out results/decode_checks.json] [--pairs 2500] [--seed 0]

Runs on the real tokenizer (BrahmicTokenizer-131K; found like the other scripts: --tokenizer, $KE2_TOKENIZER,
$BRAHMIC_TOKENIZER_DIR, then the Hugging Face cache). Raw byte table only; P = 32 and 64.

Theorem 3, on real token pairs (--pairs per group, at least 10,000 in all):
  random      two tokens drawn at random
  prefix      a token and the token that is it minus its last byte
  one_byte    two tokens of the same length that differ in exactly one position
  nearest     a sampled token and its nearest other token by cosine over the whole vocabulary (P = 32)
  edge        hand-picked: the space runs of 30, 31 and 32 bytes, length 1 against length 32, the longest tokens
  For every pair: the closed form against the codec's own cosine in float64, float32 and bfloat16.
  The worst case (c) over the vocabulary, clean decoding with margins (b), and the guarantee (d) at its edge.
Theorem 2: every token's clean code (fp32 and bf16) decodes to its own ID; noise inside the room for error
  never changes the answer; a push just outside it can (an example is recorded); batch size and order do not matter.

Needs torch, numpy, tokenizers and kronecker-embeddings. Takes a few minutes on a laptop CPU.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

if __package__ in (None, ""):  # run as a script: make ke2, forward and the upstream codec importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ke2.upstream import ensure_kronecker_embeddings

    ensure_kronecker_embeddings()

import numpy as np
import torch
from decode_theorems import (
    THETA,
    closed_form_cosine,
    decode_structural_batch,
    error_room,
    guarantee_cosine,
    match_count,
    worst_case_cosine,
)

from decode_ref import CodeTable, decode
from forward import codes
from ke2.codec import encode_f64
from ke2.config import RESULTS_DIR, TOKENIZER_SHA256
from ke2.tables import build_raw_table
from ke2.tokenizer import load_tokenizer, raw_bytes_for_id

DEFAULT_OUT = RESULTS_DIR / "decode_checks.json"
PS = (32, 64)
FP64_TOL = 1e-12
CHUNK = 512


# --------------------------------------------------------------------------- pairs
def build_pairs(raw: list[bytes], table32: CodeTable, n: int, rng: np.random.Generator) -> dict[str, list]:
    V = len(raw)
    by_bytes = {r: i for i, r in enumerate(raw)}
    groups: dict[str, list[tuple[int, int]]] = {}

    seen: set[tuple[int, int]] = set()
    random_pairs = []
    while len(random_pairs) < min(n, V * (V - 1) // 2):
        a, b = (int(x) for x in rng.integers(0, V, 2))
        key = (min(a, b), max(a, b))
        if a != b and key not in seen:
            seen.add(key)
            random_pairs.append(key)
    groups["random"] = random_pairs

    prefix = [(by_bytes[r[:-1]], i) for i, r in enumerate(raw) if len(r) >= 2 and r[:-1] in by_bytes]
    groups["prefix"] = _sample(prefix, n, rng)

    buckets = defaultdict(list)
    for i, r in enumerate(raw):
        for j in range(len(r)):
            buckets[(len(r), j, r[:j], r[j + 1 :])].append(i)
    one_byte = [(g[k], g[k + 1]) for g in buckets.values() if len(g) > 1 for k in range(len(g) - 1)]
    groups["one_byte"] = _sample(one_byte, n, rng)

    queries = rng.choice(V, size=min(n, V), replace=False)
    groups["nearest"] = [(int(t), nearest_other(table32, int(t))) for t in queries]

    edge = []
    spaces = [by_bytes.get(b" " * k) for k in (30, 31, 32)]
    if None not in spaces:
        edge += [(spaces[1], spaces[2]), (spaces[0], spaces[1]), (spaces[0], spaces[2])]
    longest = sorted(range(V), key=lambda i: (-len(raw[i]), i))[:4]
    shortest = sorted(range(V), key=lambda i: (len(raw[i]), i))[:4]
    edge += [(longest[k], longest[k + 1]) for k in range(3)]
    edge += [(s, longest[0]) for s in shortest]
    groups["edge"] = [(a, b) for a, b in edge if a != b]
    return groups


def _sample(pairs: list, n: int, rng: np.random.Generator) -> list:
    if len(pairs) <= n:
        return list(pairs)
    return [pairs[k] for k in sorted(rng.choice(len(pairs), size=n, replace=False).tolist())]


def nearest_other(table: CodeTable, t: int) -> int:
    """The token whose code is closest by cosine to code(t), over the whole vocabulary, t excluded."""
    s = table.cosine_scores(table.codes(np.array([t])))[0]
    s[t] = -np.inf
    return int(np.argmax(s))


# --------------------------------------------------------------------------- Theorem 3
def cosines(za: np.ndarray, zb: np.ndarray) -> np.ndarray:
    za, zb = za.astype(np.float64), zb.astype(np.float64)
    return (za * zb).sum(1) / (np.linalg.norm(za, axis=1) * np.linalg.norm(zb, axis=1))


def check_pairs(raw: list[bytes], pairs: list[tuple[int, int]], P: int, c_star: float) -> dict:
    out = {"pairs": len(pairs), "max_abs_err": {"float64": 0.0, "float32": 0.0, "bfloat16": 0.0}}
    max_cos, cos_one = -1.0, 0
    for s in range(0, len(pairs), CHUNK):
        chunk = pairs[s : s + CHUNK]
        ids = sorted({i for p in chunk for i in p})
        pos = {t: k for k, t in enumerate(ids)}
        a = np.array([pos[x] for x, _ in chunk])
        b = np.array([pos[y] for _, y in chunk])
        strs = [raw[t] for t in ids]
        La = np.array([len(raw[x]) for x, _ in chunk])
        Lb = np.array([len(raw[y]) for _, y in chunk])
        m = np.array([match_count(raw[x], raw[y]) for x, y in chunk])
        cf = closed_form_cosine(La, Lb, m, P)
        rows = np.zeros((len(ids), P), dtype=np.uint8)
        for k, r in enumerate(strs):
            rows[k, : len(r)] = np.frombuffer(r, dtype=np.uint8)
        z64 = encode_f64(rows, np.array([len(r) for r in strs]), P)
        z32 = codes(strs, P, torch.float32).numpy()
        z16 = codes(strs, P, torch.bfloat16).float().numpy()
        for name, z in (("float64", z64), ("float32", z32), ("bfloat16", z16)):
            err = float(np.abs(cosines(z[a], z[b]) - cf).max())
            out["max_abs_err"][name] = max(out["max_abs_err"][name], err)
        c64 = cosines(z64[a], z64[b])
        max_cos = max(max_cos, float(c64.max()))
        cos_one += int((c64 >= 1.0 - 1e-12).sum())
    out.update(max_cosine=max_cos, pairs_with_cosine_1=cos_one, max_cosine_at_most_c_star=max_cos <= c_star + 1e-12)
    out["float64_within_tolerance"] = out["max_abs_err"]["float64"] <= FP64_TOL
    return out


def check_guarantee(table: CodeTable, t: int, t2: int, g: float, rng: np.random.Generator, ids: np.ndarray) -> dict:
    """Theorem 3 (d) at its edge, on the worst pair (t, t2), and with random noise on sampled tokens."""
    u = table.codes(np.array([t, t2]))
    u = u / np.linalg.norm(u, axis=1, keepdims=True)
    edge = {}
    for name, s in (("just_inside", 0.5 - 1e-3), ("just_outside", 0.5 + 1e-3)):
        q = (1 - s) * u[0] + s * u[1]
        q = q / np.linalg.norm(q)
        r = decode(q, table)
        edge[name] = {"cos_to_t": float(q @ u[0]), "above_guarantee": float(q @ u[0]) > g,
                      "decoded": int(r.token_ids[0]), "decoded_is_t": int(r.token_ids[0]) == t}  # fmt: skip
    z = table.codes(ids)
    z = z / np.linalg.norm(z, axis=1, keepdims=True)
    noise = rng.standard_normal(z.shape)
    noise -= (noise * z).sum(1, keepdims=True) * z  # orthogonal to the code
    noise /= np.linalg.norm(noise, axis=1, keepdims=True)
    target = g + 1e-4
    q = target * z + math.sqrt(1 - target * target) * noise
    r = decode(q, table)
    return {
        "worst_pair_edge": edge,
        "random_noise": {"vectors": len(ids), "cos_to_true_code": target,
                         "all_decoded_correctly": bool((r.token_ids == ids).all())},
    }  # fmt: skip


# --------------------------------------------------------------------------- Theorem 2
def check_structural(raw: list[bytes], P: int, rng: np.random.Generator, n_noise: int) -> dict:
    V = len(raw)
    by_bytes = {r: i for i, r in enumerate(raw)}
    out: dict = {"theta": THETA, "error_room_real_tokens": error_room(P, max(len(r) for r in raw)),
                 "error_room_any_string": error_room(P)}  # fmt: skip
    for dtype in (torch.float32, torch.bfloat16):
        right = invalid = other = 0
        for s in range(0, V, 2048):
            got = decode_structural_batch(codes(raw[s : s + 2048], P, dtype), P)
            for k, g in enumerate(got):
                if g is None:
                    invalid += 1
                elif by_bytes.get(g) == s + k:
                    right += 1
                else:
                    other += 1
        out[f"clean_{str(dtype).split('.')[-1]}"] = {"tokens": V, "own_id": right, "invalid": invalid, "other": other}

    delta = out["error_room_real_tokens"]
    ids = rng.choice(V, size=n_noise, replace=False)
    strs = [raw[t] for t in ids]
    z = codes(strs, P, torch.float32).numpy().astype(np.float64)
    noisy = z + rng.uniform(-0.999 * delta, 0.999 * delta, size=z.shape)
    hi = z.max(1, keepdims=True)
    lo = z.min(1, keepdims=True)
    worst = np.where(z == hi, hi - 0.999 * delta, lo + 0.999 * delta)  # every cell pushed towards theta
    out["noise_inside_room"] = {
        "vectors": n_noise,
        "uniform_all_own_id": all(by_bytes.get(g) == t for g, t in zip(decode_structural_batch(noisy, P), ids, strict=True)),
        "worst_shape_all_own_id": all(by_bytes.get(g) == t for g, t in zip(decode_structural_batch(worst, P), ids, strict=True)),
    }  # fmt: skip

    spaces32 = by_bytes.get(b" " * 32)
    if spaces32 is not None:
        q = codes([raw[spaces32]], P, torch.float32).numpy().astype(np.float64)[0]
        last = 0x20 * P + 31  # the cell of byte 0x20 (space) at position 31
        q[last] = THETA - 0.01  # one cell moved by just more than the room for error
        g = decode_structural_batch(q, P)[0]
        out["push_outside_room_example"] = {
            "token": spaces32, "moved_cells": 1, "move": float(codes([raw[spaces32]], P)[0, last]) - (THETA - 0.01),
            "decoded_bytes_len": None if g is None else len(g), "decoded_id": by_bytes.get(g) if g else None,
        }  # fmt: skip

    batch = codes(strs, P, torch.float32)
    whole = decode_structural_batch(batch, P)
    single = [decode_structural_batch(batch[k], P)[0] for k in range(min(64, n_noise))]
    perm = rng.permutation(n_noise)
    shuffled = decode_structural_batch(batch[torch.from_numpy(perm)], P)
    out["order_and_batch_size"] = {
        "one_at_a_time_equals_batch": single == whole[: len(single)],
        "shuffled_equals_batch": [shuffled[k] for k in np.argsort(perm)] == whole,
    }
    return out


# --------------------------------------------------------------------------- run
def run(tok_path: str | None, n_pairs: int, seed: int) -> dict:
    t0 = time.time()
    tb = load_tokenizer(tok_path)
    raw = [raw_bytes_for_id(tb, i) for i in range(tb.vocab_size)]
    if any(len(r) == 0 for r in raw):
        raise ValueError("an empty token: Theorem 3 needs non-empty strings")
    max_len = max(len(r) for r in raw)
    res: dict = {"tokenizer_json_sha256": tb.sha256, "pinned_tokenizer": tb.sha256 == TOKENIZER_SHA256,
                 "vocab": len(raw), "max_token_bytes": max_len, "seed": seed, "pairs_per_group": n_pairs}  # fmt: skip
    rng = np.random.default_rng(seed)
    tables = {P: CodeTable.from_byte_table(build_raw_table(tb, P)) for P in PS}
    groups = build_pairs(raw, tables[32], n_pairs, rng)
    res["pairs_total"] = sum(len(p) for p in groups.values())
    by_bytes = {r: i for i, r in enumerate(raw)}
    for P in PS:
        if max_len > P:
            raise ValueError(f"a token has {max_len} bytes, more than P={P}; Theorems 2 and 3 assume no cut")
        c_star, La, Lb, m = worst_case_cosine(max_len, P)
        g = guarantee_cosine(c_star)
        attain = [(by_bytes[raw[i][:-1]], i) for i, r in enumerate(raw)
                  if len(r) == Lb and La == Lb - 1 and r[:-1] in by_bytes]  # fmt: skip
        sec: dict = {"c_star": c_star, "worst_lengths": [La, Lb, m], "min_margin": 1 - c_star, "guarantee_cosine": g,
                     "pairs_reaching_c_star": len(attain), "example_pair": list(attain[0]) if attain else None}  # fmt: skip
        sec["groups"] = {name: check_pairs(raw, pairs, P, c_star) for name, pairs in groups.items()}
        if attain:
            t2, t = attain[0]  # t = the longer token, t2 = it minus its last byte
            za = codes([raw[t], raw[t2]], P, torch.float32).numpy()
            sec["example_pair_cosine_from_codec"] = float(cosines(za[:1], za[1:2])[0])
            sample = np.unique(np.r_[t, t2, rng.choice(len(raw), size=min(n_pairs, 500, len(raw)), replace=False)])
            r = decode(tables[P].codes(sample), tables[P])
            sec["clean_decode_sample"] = {"tokens": len(sample), "all_own_id": bool((r.token_ids == sample).all()),
                                          "min_margin": float(r.margins.min()),
                                          "min_margin_is_1_minus_c_star": abs(float(r.margins.min()) - (1 - c_star)) < 1e-9}  # fmt: skip
            sec["guarantee"] = check_guarantee(
                tables[P], t, t2, g, rng, rng.choice(len(raw), min(500, len(raw)), replace=False)
            )
        sec["theorem2"] = check_structural(raw, P, rng, n_noise=min(n_pairs, 2000, len(raw)))
        res[f"P{P}"] = sec
    res["seconds"] = round(time.time() - t0, 1)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", default=None, help="tokenizer.json or its folder (default: found locally)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pairs", type=int, default=2500, help="pairs per group (5 groups; default gives > 10,000)")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)

    import kronecker_embeddings
    import tokenizers

    res = run(a.tokenizer, a.pairs, a.seed)
    res["env"] = {"torch": torch.__version__, "numpy": np.__version__, "tokenizers": tokenizers.__version__,
                  "kronecker_embeddings": kronecker_embeddings.__version__}  # fmt: skip
    a.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(res, indent=2)
    a.out.write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)
    print(f"written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
