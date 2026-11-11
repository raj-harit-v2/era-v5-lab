"""StructuredScorer must reproduce decode_ref.CodeTable.cosine_scores and its tie rule."""

import numpy as np
import pytest
import torch

import decode_ref as dr
import ke2.scoring as scoring
from ke2.codec import encode_f64
from ke2.scoring import StructuredScorer
from ke2.tables import ByteTable

P = 16


def synthetic_table(n=300, seed=0):
    rng = np.random.default_rng(seed)
    rows = set()
    while len(rows) < n - 2:
        L = int(rng.integers(1, P + 1))
        rows.add(bytes(rng.integers(0, 256, L, dtype=np.uint8)))
    rows = [*sorted(rows), b"dup", b"dup"]  # a duplicate pair: exact tie, lowest id must win
    buf = np.zeros((len(rows), P), dtype=np.uint8)
    lens = np.zeros(len(rows), dtype=np.int16)
    for i, r in enumerate(rows):
        buf[i, : len(r)] = np.frombuffer(r, dtype=np.uint8)
        lens[i] = len(r)
    return ByteTable("raw", P, buf, lens, 0, 0, 0, "synthetic"), rows


def test_fp64_cosine_matches_decode_ref_reference():
    table, _ = synthetic_table()
    ct = dr.CodeTable.from_byte_table(table)
    rng = np.random.default_rng(1)
    Q = rng.standard_normal((37, ct.dim))
    want = ct.cosine_scores(Q)  # (n, V)
    got = StructuredScorer(ct, "cpu", torch.float64).cosine(torch.from_numpy(Q)).T.numpy()
    assert np.abs(got - want).max() < 1e-12


def test_top2_matches_decode_ref_ids_and_margins_and_tie_rule():
    table, rows = synthetic_table()
    ct = dr.CodeTable.from_byte_table(table)
    ids = np.arange(table.vocab_size)
    Q = encode_f64(table.bytes[ids], table.lengths[ids].astype(np.int64), P)
    ref = dr.decode(Q, ct)
    best_id, best, second_id, second = StructuredScorer(ct, "cpu", torch.float64).top2(torch.from_numpy(Q))
    assert np.array_equal(best_id.numpy(), ref.token_ids)
    assert np.abs((best - second).numpy() - ref.margins).max() < 1e-12
    dup = len(rows) - 2  # both "dup" rows decode to the lower id, margin 0
    assert best_id[dup].item() == dup and best_id[dup + 1].item() == dup
    assert abs((best - second)[dup + 1].item()) < 1e-12


def test_fp32_path_recovers_every_id_on_clean_codes():
    table, _ = synthetic_table()
    ct = dr.CodeTable.from_byte_table(table)
    ids = np.arange(table.vocab_size - 2)  # skip the duplicate pair
    Q = encode_f64(table.bytes[ids], table.lengths[ids].astype(np.int64), P).astype(np.float32)
    best_id, *_ = StructuredScorer(ct, "cpu", torch.float32).top2(torch.from_numpy(Q))
    assert np.array_equal(best_id.numpy(), ids)


def test_gather_path_matches_reference(monkeypatch):
    table, _ = synthetic_table()
    ct = dr.CodeTable.from_byte_table(table)
    Q = np.random.default_rng(2).standard_normal((11, ct.dim))
    want = ct.cosine_scores(Q).T
    monkeypatch.setattr(scoring, "_GATHER_CHUNK", 7)
    sc = StructuredScorer(ct, "cpu", torch.float64)
    sc.use_sparse = False
    sc._build_gather_index()
    assert np.abs(sc.cosine(torch.from_numpy(Q)).numpy() - want).max() < 1e-12


def test_zero_query_raises():
    table, _ = synthetic_table()
    ct = dr.CodeTable.from_byte_table(table)
    Q = np.random.default_rng(3).standard_normal((4, ct.dim))
    Q[2] = 0
    with pytest.raises(ValueError, match=r"zero query vector at rows \[2\]"):
        StructuredScorer(ct, "cpu", torch.float64).cosine(torch.from_numpy(Q))


def test_empty_token_scores_zero_without_nan():
    table, _ = synthetic_table()
    table.bytes[0, :] = 0
    table.lengths[0] = 0
    ct = dr.CodeTable.from_byte_table(table)
    Q = np.random.default_rng(4).standard_normal((5, ct.dim))
    got = StructuredScorer(ct, "cpu", torch.float64).cosine(torch.from_numpy(Q)).numpy()
    assert not np.isnan(got).any()
    assert np.all(got[0] == 0)
    assert np.abs(got - ct.cosine_scores(Q).T).max() < 1e-12


def test_rejects_bf16_scoring_dtype_and_non_finite_queries(synthetic_p8):
    ct = dr.CodeTable.from_byte_table(synthetic_p8)
    with pytest.raises(ValueError, match="float32 or float64"):
        StructuredScorer(ct, "cpu", torch.bfloat16)
    scorer = StructuredScorer(ct, "cpu", torch.float32)
    q = encode_f64(synthetic_p8.bytes[:3], synthetic_p8.lengths[:3].astype(np.int64), synthetic_p8.pos_dim)
    q[1, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        scorer.top2(torch.from_numpy(q))
