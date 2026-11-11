"""Theorem 3: nearest-code cosine (proof.md section 7).

Synthetic strings run everywhere (a few seconds). The real-tokenizer part reads results/decode_checks.json and is
skipped unless BrahmicTokenizer-131K is found (BRAHMIC_TOKENIZER_DIR, set by conftest.py).
"""

import json
import math
import os
import random
from pathlib import Path

import numpy as np
import pytest
import torch
from decode_theorems import closed_form_cosine, guarantee_cosine, match_count, worst_case_cosine

from forward import codes

PS = (32, 64)
RESULTS = Path(__file__).resolve().parents[1] / "results" / "decode_checks.json"


def rand_bytes(rng, L):
    return bytes(rng.randrange(256) for _ in range(L))


def near_pairs(P, rng, n=400):
    """Pairs that share many cells: one byte changed, a prefix, two bytes swapped, plus random pairs."""
    pairs = [(b" " * 31, b" " * 32), (b"a", b"a" * P), (b"\x00", b"\xff")]
    for _ in range(n):
        s = rand_bytes(rng, rng.randrange(2, P + 1))
        i = rng.randrange(len(s))
        pairs.append((s, s[:i] + bytes([(s[i] + 1) % 256]) + s[i + 1 :]))
        pairs.append((s[:-1], s))
        pairs.append((s, rand_bytes(rng, rng.randrange(1, P + 1))))
    return pairs


def codec_cosine(a, b, P, dtype):
    z = codes([a, b], P, dtype).double()
    return float(z[0] @ z[1] / (z[0].norm() * z[1].norm()))


def test_formula_matches_the_codec():
    rng = random.Random(0)
    for P in PS:
        for a, b in near_pairs(P, rng):
            cf = float(closed_form_cosine(len(a), len(b), match_count(a, b), P))
            assert abs(codec_cosine(a, b, P, torch.float32) - cf) < 1e-6, (P, a, b)
            assert abs(codec_cosine(a, b, P, torch.bfloat16) - cf) < 1e-4, (P, a, b)


def test_formula_does_not_depend_on_eps():
    from ke2.codec import encode_f64

    rows = np.zeros((2, 32), dtype=np.uint8)
    rows[0, :3] = list(b"cat")
    rows[1, :4] = list(b"cart")
    for eps in (0.0, 1e-6, 1e-2):
        z = encode_f64(rows, np.array([3, 4]), 32, eps=eps)
        cos = z[0] @ z[1] / (np.linalg.norm(z[0]) * np.linalg.norm(z[1]))
        assert abs(cos - float(closed_form_cosine(3, 4, 2, 32))) < 1e-12, eps


def test_cosine_is_one_only_for_equal_strings():
    rng = random.Random(1)
    for P in PS:
        for a, b in near_pairs(P, rng, n=100):
            if a != b:
                assert float(closed_form_cosine(len(a), len(b), match_count(a, b), P)) < 1.0
        s = rand_bytes(rng, 10)
        assert math.isclose(float(closed_form_cosine(10, 10, 10, P)), 1.0, abs_tol=1e-15)
        assert math.isclose(codec_cosine(s, s, P, torch.float32), 1.0, abs_tol=1e-6)


def test_worst_case_is_31_against_32_bytes():
    c32, *lens32 = worst_case_cosine(32, 32)
    c64, *lens64 = worst_case_cosine(32, 64)
    assert lens32 == [31, 32, 31] and lens64 == [31, 32, 31]
    assert abs(c32 - 0.984191) < 1e-6 and abs(c64 - 0.984221) < 1e-6
    assert abs(guarantee_cosine(c32) - 0.996040) < 1e-6
    rng = random.Random(2)
    for a, b in near_pairs(32, rng, n=300):  # no pair of different strings of at most 32 bytes beats it
        if a != b:
            assert float(closed_form_cosine(len(a), len(b), match_count(a, b), 32)) <= c32 + 1e-12


def test_guarantee_holds_inside_and_is_tight():
    for P in PS:
        c, *_ = worst_case_cosine(32, P)
        g = guarantee_cosine(c)
        z = codes([b" " * 32, b" " * 31], P).double()
        u = z / z.norm(dim=1, keepdim=True)
        for s, closer_to_first in ((0.5 - 1e-3, True), (0.5 + 1e-3, False)):
            q = (1 - s) * u[0] + s * u[1]
            q = q / q.norm()
            cos0, cos1 = float(q @ u[0]), float(q @ u[1])
            assert (cos0 > cos1) == closer_to_first
            assert (cos0 > g) == closer_to_first  # just inside the guarantee it decodes right, just outside it need not


tok_dir = os.environ.get("BRAHMIC_TOKENIZER_DIR")


def saved():
    r = json.loads(RESULTS.read_text(encoding="utf-8"))
    from ke2.config import TOKENIZER_SHA256

    if r["tokenizer_json_sha256"] != TOKENIZER_SHA256:
        pytest.skip("results/decode_checks.json was made with another tokenizer.json")
    return r


def test_real_tokenizer_results():
    if not (tok_dir and (Path(tok_dir) / "tokenizer.json").is_file()) or not RESULTS.is_file():
        pytest.skip("needs BrahmicTokenizer-131K (BRAHMIC_TOKENIZER_DIR) and results/decode_checks.json")
    r = saved()
    assert r["pairs_total"] >= 10000
    for P in PS:
        s = r[f"P{P}"]
        assert s["worst_lengths"] == [31, 32, 31] and s["pairs_reaching_c_star"] >= 1
        assert abs(s["example_pair_cosine_from_codec"] - s["c_star"]) < 1e-6
        for name, g in s["groups"].items():
            assert g["float64_within_tolerance"], (P, name)
            assert g["max_cosine_at_most_c_star"] and g["pairs_with_cosine_1"] == 0, (P, name)
            assert g["max_abs_err"]["bfloat16"] < (1 - s["c_star"]) / 10, (P, name)
        assert s["clean_decode_sample"]["all_own_id"] and s["clean_decode_sample"]["min_margin_is_1_minus_c_star"]
        assert s["guarantee"]["worst_pair_edge"]["just_inside"]["decoded_is_t"]
        assert s["guarantee"]["random_noise"]["all_decoded_correctly"]
        t2 = s["theorem2"]
        for key in ("clean_float32", "clean_bfloat16"):
            assert t2[key]["own_id"] == r["vocab"], (P, key)
        assert t2["noise_inside_room"]["uniform_all_own_id"] and t2["noise_inside_room"]["worst_shape_all_own_id"]
        assert all(t2["order_and_batch_size"].values())


def test_the_worst_pair_in_the_real_vocabulary():
    if not (tok_dir and (Path(tok_dir) / "tokenizer.json").is_file()):
        pytest.skip("needs BrahmicTokenizer-131K (BRAHMIC_TOKENIZER_DIR)")
    from tokenizers import Tokenizer

    tk = Tokenizer.from_file(str(Path(tok_dir) / "tokenizer.json"))
    ids = [tk.token_to_id("Ġ" * n) for n in (31, 32)]  # the byte-level symbol for a space
    if None in ids:
        pytest.skip("this tokenizer has no 31- and 32-space tokens")
    for P in PS:
        c, *_ = worst_case_cosine(32, P)
        assert abs(codec_cosine(b" " * 31, b" " * 32, P, torch.float32) - c) < 1e-6
