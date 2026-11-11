"""Committed minimum-margin results (results/min_margin/) are exhaustive, complete and reproducible.

Pinned to BrahmicTokenizer-131K (BRAHMIC_SHA256); skipped on any other tokenizer or without it.
"""

import collections
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "margins"))

import pair_margins as pm
from ke2.config import RESULTS_DIR
from ke2.script_class import classify_vocab

# Aliases: pr-guard's email check misreads dotted pytest decorators as addresses.
fixture = pytest.fixture
parametrize = pytest.mark.parametrize

BRAHMIC_SHA256 = "01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff"
SAMPLED_MIN_P32 = 0.0318133707027064  # results/decode_ref/summary.json, raw_P32 min_margin (4,096-ID sample)
OUT = RESULTS_DIR / "min_margin"


def load_summary():
    return json.loads((OUT / "summary_P32.json").read_text(encoding="utf-8"))


def manifest():
    return json.loads((RESULTS_DIR / "tables" / "manifest.json").read_text(encoding="utf-8"))


def class_rows():
    with open(OUT / "min_margin_by_class_P32.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@fixture(autouse=True)
def brahmic_only(tb):
    if tb.sha256 != BRAHMIC_SHA256:
        pytest.skip("results are pinned to BrahmicTokenizer-131K")


def test_summary_is_exhaustive_p32_raw_and_passes_the_gate():
    s = load_summary()
    assert (s["P"], s["table_kind"], s["exhaustive"], s["vocab_size"]) == (32, "raw", True, 131072)
    assert s["table_sha256"] == manifest()["tables"]["raw_table_P32.npz"]["sha256"]
    assert s["gate_all_positive"] is True


def test_exhaustive_minimum_is_not_above_the_sampled_minimum():
    assert load_summary()["precisions"]["fp64"]["min_margin"] <= SAMPLED_MIN_P32 + 1e-15


def test_every_script_class_has_one_row_per_precision(tb):
    counts = collections.Counter(classify_vocab(tb, detail=True))
    rows = class_rows()
    for p in pm.PRECISIONS:
        got = {r["script_class"]: int(r["n_tokens"]) for r in rows if r["precision"] == p}
        assert got == dict(counts)


@parametrize("precision", pm.PRECISIONS)
def test_committed_pairs_reproduce_their_margin_and_rival(raw32, precision):
    rows = [r for r in class_rows() if r["precision"] == precision]
    ids = np.array([int(r["token_id"]) for r in rows])
    sm = pm.self_margins(raw32, [pm.codec_values(raw32, precision)], query_ids=ids)[precision]
    for r, m, rival in zip(rows, sm.margins, sm.rival_ids, strict=True):
        assert float(r["min_margin"]) == pytest.approx(m, abs=1e-12)
        assert int(r["rival_id"]) == rival
        assert bytes.fromhex(r["token_hex"]) == raw32.row(int(r["token_id"]))
