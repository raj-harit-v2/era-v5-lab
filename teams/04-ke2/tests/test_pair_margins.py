"""Exact per-token decode margins (src/margins/pair_margins.py).

Synthetic tables always run; the real-tokenizer check is skipped without BrahmicTokenizer-131K.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "margins"))

import decode_ref as dr
import pair_margins as pm
from ke2.codec import encode_f64, encode_ids

# Aliases: pr-guard's email check misreads dotted pytest decorators as addresses.
fixture = pytest.fixture
parametrize = pytest.mark.parametrize

SAMPLED_MIN_P32 = 0.0318133707027064  # results/decode_ref/summary.json, raw_P32 min_margin (4,096-ID sample)


def test_overlap_counts_compare_bytes_only_inside_both_lengths(make_byte_table):
    t = make_byte_table([b"abc", b"abd", b"ab", b"xbc", b"a\x00", b"a"], P=4)
    k = pm.overlap_counts(t.bytes, t.lengths, t.bytes, t.lengths)
    assert k.dtype == np.int16
    assert k[0].tolist() == [3, 2, 2, 2, 1, 1]
    assert k[3].tolist() == [2, 1, 1, 3, 0, 0]
    assert k[4, 5] == 1 and k[4, 4] == 2  # a 0x00 byte is a byte; padding is not


def test_pair_cosines_equal_dense_float64_cosines(synthetic_p8):
    t = synthetic_p8
    k = pm.overlap_counts(t.bytes[:10], t.lengths[:10], t.bytes, t.lengths)
    codes = encode_f64(t.bytes, t.lengths, t.pos_dim)
    unit = codes / np.linalg.norm(codes, axis=1, keepdims=True)
    got = pm.pair_cosines(np.arange(10), k, pm.exact_values(t))
    np.testing.assert_allclose(got, unit[:10] @ unit.T, rtol=0, atol=1e-12)


def test_self_margins_equal_decode_ref_margins(synthetic_p8):
    t = synthetic_p8
    ct = dr.CodeTable.from_byte_table(t)
    sm = pm.self_margins(t, [pm.exact_values(t)])["fp64"]
    ref = dr.decode(ct.codes(np.arange(t.vocab_size)), ct)
    assert np.array_equal(sm.token_ids, np.arange(t.vocab_size))
    np.testing.assert_allclose(sm.margins, ref.margins, rtol=0, atol=1e-12)
    assert (sm.rival_ids != sm.token_ids).all()


def test_prefix_pair_reproduces_the_sampled_p32_minimum(make_byte_table):
    t = make_byte_table([b"x" * 15, b"x" * 15 + b"y", b"q"], P=32)
    sm = pm.self_margins(t, [pm.exact_values(t)])["fp64"]
    assert sm.margins[0] == pytest.approx(SAMPLED_MIN_P32, abs=1e-12)
    assert (int(sm.rival_ids[0]), int(sm.overlaps[0])) == (1, 15)


def test_duplicate_rows_have_zero_margin_and_point_at_each_other(make_byte_table):
    t = make_byte_table([b"ab", b"zz", b"ab"], P=4)
    sm = pm.self_margins(t, [pm.exact_values(t)])["fp64"]
    assert sm.margins[[0, 2]].tolist() == [0.0, 0.0]
    assert sm.rival_ids[[0, 2]].tolist() == [2, 0]


def test_chunk_size_and_query_subset_do_not_change_results(synthetic_p8):
    t, v = synthetic_p8, [pm.exact_values(synthetic_p8)]
    full = pm.self_margins(t, v, chunk_rows=64)["fp64"]
    one = pm.self_margins(t, v, chunk_rows=1)["fp64"]
    sub = pm.self_margins(t, v, query_ids=np.array([9, 3, 50]), chunk_rows=2)["fp64"]
    assert np.array_equal(full.margins, one.margins) and np.array_equal(full.rival_ids, one.rival_ids)
    assert sub.token_ids.tolist() == [9, 3, 50]
    assert np.array_equal(sub.margins, full.margins[[9, 3, 50]])


def test_real_raw_p32_sample_matches_decode_ref(raw32, tb):
    ids = dr.sample_token_ids(raw32.vocab_size, tb.special_ids, n=256, seed=5)
    ct = dr.CodeTable.from_byte_table(raw32)
    sm = pm.self_margins(raw32, [pm.exact_values(raw32)], query_ids=ids)["fp64"]
    np.testing.assert_allclose(sm.margins, dr.decode(ct.codes(ids), ct).margins, rtol=0, atol=1e-12)
    assert (sm.margins > 0).all()


def test_two_values_reads_high_and_low_per_row():
    high, low = pm.two_values(np.array([[5.0, -1.0, -1.0, 5.0], [-2.0, -2.0, 3.0, -2.0]]), np.array([2, 1]))
    assert high.tolist() == [5.0, 3.0] and low.tolist() == [-1.0, -2.0]


@parametrize("row, length", [([5.0, -1.0, -1.5, 5.0], 2), ([5.0, -1.0, -1.0, -1.0], 2)])
def test_two_values_rejects_codes_that_are_not_two_valued(row, length):
    with pytest.raises(pm.TwoValueError, match="token 7"):
        pm.two_values(np.array([row]), np.array([length]), first_id=7)


def test_codec_values_follow_the_upstream_codec(synthetic_p8):
    t = synthetic_p8
    exact, f32, b16 = (pm.codec_values(t, p, chunk_rows=7) for p in pm.PRECISIONS)
    assert (f32.precision, b16.precision) == ("fp32", "bf16")
    np.testing.assert_allclose(f32.high, exact.high, rtol=1e-5)
    np.testing.assert_allclose(f32.low, exact.low, rtol=1e-5)
    codes = encode_ids(np.arange(t.vocab_size), t).to(torch.bfloat16).double().numpy()
    assert np.array_equal(b16.high, codes.max(axis=1)) and np.array_equal(b16.low, codes.min(axis=1))
    assert (np.abs(b16.high / exact.high - 1) <= 2.0**-8).all()


def test_codec_values_rejects_an_unknown_precision(synthetic_p8):
    with pytest.raises(ValueError, match="precision"):
        pm.codec_values(synthetic_p8, "fp16")


def test_value_pairs_per_length_counts_distinct_pairs():
    v = pm.CodeValues("fp32", 4, 256, np.array([1, 1, 2]), np.array([3.0, 3.5, 2.0]), np.array([-0.1, -0.1, -0.2]))
    assert pm.value_pairs_per_length(v) == {1: 2, 2: 1}


@parametrize("precision", ["fp32", "bf16"])
def test_pair_cosines_with_rounded_values_equal_dense_cosines_of_those_codes(synthetic_p8, precision):
    t = synthetic_p8
    codes = encode_ids(np.arange(t.vocab_size), t)
    if precision == "bf16":
        codes = codes.to(torch.bfloat16)
    dense = codes.double().numpy()
    unit = dense / np.linalg.norm(dense, axis=1, keepdims=True)
    k = pm.overlap_counts(t.bytes, t.lengths, t.bytes, t.lengths)
    got = pm.pair_cosines(np.arange(t.vocab_size), k, pm.codec_values(t, precision))
    np.testing.assert_allclose(got, unit @ unit.T, rtol=0, atol=1e-12)
