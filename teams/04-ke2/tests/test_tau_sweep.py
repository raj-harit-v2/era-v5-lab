"""Margin table rows and the tau sweep bookkeeping (src/margins/tau_sweep.py), on a synthetic vocabulary with known rivals."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "margins"))

from decode_theorems import closed_form_cosine

import decode_ref as dr
import tau_sweep as mg
from ke2.codec import encode_f64
from ke2.config import RESULTS_DIR
from ke2.scoring import StructuredScorer
from ke2.tables import ByteTable

P = 16


def table_with_rivals():
    rows = [
        b"cat",
        b"cut",
        b"ca",
        b"dog",
        b"dogs",
        b"x",
        b"\xe0\xa4\x95",
        b"\xe0\xa4",
    ]  # one-byte change, prefix, partial UTF-8
    buf = np.zeros((len(rows), P), dtype=np.uint8)
    lens = np.zeros(len(rows), dtype=np.int16)
    for i, r in enumerate(rows):
        buf[i, : len(r)] = np.frombuffer(r, dtype=np.uint8)
        lens[i] = len(r)
    return ByteTable("raw", P, buf, lens, 0, 0, 0, "synthetic"), rows


def test_margin_rows_pick_the_closed_form_rival_per_class():
    table, rows = table_with_rivals()
    ct = dr.CodeTable.from_byte_table(table)
    scorer = StructuredScorer(ct, "cpu", torch.float64)
    classes = ["Latin", "Latin", "Latin", "Latin", "Latin", "Latin", "Devanagari", "Partial-UTF8"]
    res = mg.score_vocabulary(table, ct, scorer, torch.float32, chunk=3)
    assert res["best_id"].tolist() == list(range(len(rows)))
    table_rows = mg.margin_rows(table, res, classes)
    latin = next(r for r in table_rows if r["script_class"] == "Latin")
    # the prefix pair "dog" / "dogs" (L=3, L'=4, k=3) is the closest Latin pair, closer than "cat" / "cut" (k=2);
    # Theorem 3's formula is symmetric in the pair, so the query may be either token
    assert {latin["query_bytes_hex"], latin["runner_up_bytes_hex"]} == {b"dog".hex(), b"dogs".hex()}
    assert abs(latin["min_margin"] - (1 - closed_form_cosine(4, 3, 3, P))) < 1e-5
    assert latin["overlap_k"] == 3 and abs(latin["closed_form_runner_cos"] - latin["measured_runner_cos"]) < 1e-5
    assert 1 - closed_form_cosine(4, 3, 3, P) < 1 - closed_form_cosine(3, 3, 2, P)


def test_tau_sweep_rates_are_consistent():
    table, rows = table_with_rivals()
    ct = dr.CodeTable.from_byte_table(table)
    scorer = StructuredScorer(ct, "cpu", torch.float64)
    ids = np.arange(len(rows))
    out = mg.tau_sweep(table, ct, scorer, ids, taus=(0.0, 0.5, 0.9), noise_targets=(1.0, 0.5), seed=0)
    for cond in out["conditions"]:
        for row in cond["taus"]:
            assert 0 <= row["accept_rate"] <= 1 and 0 <= row["wrong_accept_rate"] <= row["accept_rate"] + 1e-12
            assert abs(row["accept_rate"] - (row["wrong_accept_rate"] + row["correct_accept_rate"])) < 1e-12
        if cond["name"] == "garbage":  # no true token: every accept is a wrong accept, true cosine undefined
            assert cond["mean_true_cos"] is None and cond["argmax_accuracy"] == 0.0
            assert all(r["correct_accept_rate"] == 0.0 for r in cond["taus"])
        else:
            assert cond["mean_true_cos"] is not None
    clean = next(c for c in out["conditions"] if c["name"] == "clean_fp32")
    assert clean["argmax_accuracy"] == 1.0 and clean["structural_accuracy"] == 1.0
    assert all(r["accept_rate"] == 1.0 for r in clean["taus"])  # clean best cosine is 1 (to fp32 rounding)
    assert isinstance(mg.propose_tau(out), float)
    report = mg.proposal_report(out)
    assert report["proposed_tau"] == mg.propose_tau(out) and isinstance(
        report["proposal_satisfies_quality_floor"], bool
    )


def test_garbage_is_rejected_above_small_tau():
    table, rows = table_with_rivals()
    ct = dr.CodeTable.from_byte_table(table)
    scorer = StructuredScorer(ct, "cpu", torch.float64)
    ids = np.arange(len(rows))
    out = mg.tau_sweep(table, ct, scorer, ids, taus=(0.0, 0.5), noise_targets=(), seed=0)
    garbage = next(c for c in out["conditions"] if c["name"] == "garbage")
    at_half = next(r for r in garbage["taus"] if r["tau"] == 0.5)
    assert at_half["accept_rate"] == 0.0 and at_half["wrong_accept_rate"] == 0.0
    assert garbage["mean_best_cos"] < 0.5  # about sqrt(2 ln V / D) for isotropic vectors


def test_rival_mix_flips_argmax_above_half():
    table, rows = table_with_rivals()
    ct = dr.CodeTable.from_byte_table(table)
    scorer = StructuredScorer(ct, "cpu", torch.float64)
    res = mg.score_vocabulary(table, ct, scorer, torch.float32)
    ids = np.arange(len(rows))
    out = mg.tau_sweep(
        table,
        ct,
        scorer,
        ids,
        taus=(0.0, 0.5),
        noise_targets=(),
        seed=0,
        runner_up_ids=res["second_id"],
        rival_mixes=(0.3, 0.7),
    )
    low = next(c for c in out["conditions"] if c["name"] == "rival_mix_0.3")
    high = next(c for c in out["conditions"] if c["name"] == "rival_mix_0.7")
    assert low["argmax_accuracy"] == 1.0
    assert high["argmax_accuracy"] < 0.5 and high["min_best_cos"] > 0.9  # wrong answer, but still close to a code
    report = mg.proposal_report(out)
    assert set(report["rival_wrong_accept_at_tau"]) == {"rival_mix_0.3", "rival_mix_0.7"}


def _sweep(taus, noise_targets=()):
    table, rows = table_with_rivals()
    ct = dr.CodeTable.from_byte_table(table)
    scorer = StructuredScorer(ct, "cpu", torch.float64)
    return (
        table,
        ct,
        scorer,
        mg.tau_sweep(table, ct, scorer, np.arange(len(rows)), taus=taus, noise_targets=noise_targets, seed=0),
    )


def test_propose_tau_ignores_grid_order_and_needs_garbage():
    _, _, _, shuffled = _sweep(taus=(0.9, 0.0, 0.5, 0.3))
    _, _, _, sorted_ = _sweep(taus=(0.0, 0.3, 0.5, 0.9))
    assert mg.propose_tau(shuffled) == mg.propose_tau(sorted_) == 0.3
    without = {**sorted_, "conditions": [c for c in sorted_["conditions"] if c["name"] != "garbage"]}
    with pytest.raises(ValueError):
        mg.propose_tau(without)


def test_proposal_falls_back_to_garbage_criterion_when_quality_floor_fails():
    _, _, _, out = _sweep(
        taus=(0.0, 0.3, 0.9), noise_targets=(0.7,)
    )  # best cos about 0.7: tau 0.9 rejects the correct decodes
    out = {**out, "conditions": [c for c in out["conditions"] if c["name"] in ("garbage", "noise_cos_0.7")]}
    out["taus"] = [0.0, 0.9]  # drop tau 0.3, the only value that satisfies both criteria
    for c in out["conditions"]:
        c["taus"] = [r for r in c["taus"] if r["tau"] in (0.0, 0.9)]
    report = mg.proposal_report(out)
    assert report["proposed_tau"] == 0.9 and report["proposal_satisfies_quality_floor"] is False


def test_external_vectors_round_trip(tmp_path):
    table, rows = table_with_rivals()
    ct = dr.CodeTable.from_byte_table(table)
    scorer = StructuredScorer(ct, "cpu", torch.float64)
    ids = np.arange(len(rows))
    vectors = encode_f64(table.bytes[ids], table.lengths[ids].astype(np.int64), P)
    true_ids = ids.copy()
    true_ids[-1] = -1  # last query: truth unknown
    path = tmp_path / "team5.npz"
    np.savez(path, vectors=vectors, true_ids=true_ids)
    ext_vectors, ext_true = mg.load_external_vectors(path, ct.dim)
    out = mg.tau_sweep(
        table, ct, scorer, ids, taus=(0.0, 0.5), noise_targets=(), seed=0, external=(ext_vectors, ext_true)
    )
    cond = next(c for c in out["conditions"] if c["name"] == "external")
    assert cond["queries"] == len(rows) and cond["unknown_truth"] == 1
    assert cond["argmax_accuracy"] == (len(rows) - 1) / len(rows)  # the unknown one counts as not correct
    assert abs(cond["mean_true_cos"] - 1.0) < 1e-9  # mean over the known ones
    at_half = next(r for r in cond["taus"] if r["tau"] == 0.5)
    assert at_half["accept_rate"] == 1.0 and at_half["wrong_accept_rate"] == 1 / len(rows)


def test_proposal_takes_the_largest_tau_when_nothing_rejects_garbage():
    _, _, _, out = _sweep(taus=(0.0, 0.3, 0.9))
    for c in out["conditions"]:
        if c["name"] == "garbage":
            for r in c["taus"]:
                r["wrong_accept_rate"] = 1.0
    report = mg.proposal_report(out)
    assert report["proposed_tau"] == 0.9 and report["proposal_satisfies_quality_floor"] is False


def test_external_vectors_loader_rejects_bad_files(tmp_path):
    table, rows = table_with_rivals()
    ct = dr.CodeTable.from_byte_table(table)
    ids = np.arange(len(rows))
    good = encode_f64(table.bytes[ids], table.lengths[ids].astype(np.int64), P)

    def save(name, **arrays):
        path = tmp_path / name
        np.savez(path, **arrays)
        return path

    with pytest.raises(ValueError, match="expected arrays"):
        mg.load_external_vectors(save("a.npz", vectors=good), ct.dim)
    with pytest.raises(ValueError, match="shape"):
        mg.load_external_vectors(save("b.npz", vectors=good[:, :-1], true_ids=ids), ct.dim)
    with pytest.raises(ValueError, match="entries for"):
        mg.load_external_vectors(save("c.npz", vectors=good, true_ids=ids[:-1]), ct.dim)
    nan = good.copy()
    nan[2, 0] = np.nan
    with pytest.raises(ValueError, match="NaN or inf"):
        mg.load_external_vectors(save("d.npz", vectors=nan, true_ids=ids), ct.dim)
    zero = good.copy()
    zero[1] = 0.0
    with pytest.raises(ValueError, match="all zero"):
        mg.load_external_vectors(save("e.npz", vectors=zero, true_ids=ids), ct.dim)


def test_committed_tau_rates_reproduce_their_proposal():
    sweep = json.loads((RESULTS_DIR / "min_margin" / "tau_rates_P32.json").read_text(encoding="utf-8"))
    report = mg.proposal_report(sweep)
    assert report["proposed_tau"] == sweep["proposed_tau"] == 0.3
    assert report["proposal_satisfies_quality_floor"] is sweep["proposal_satisfies_quality_floor"] is True
    assert report["rule"] == sweep["rule"] and report["rival_wrong_accept_at_tau"] == sweep["rival_wrong_accept_at_tau"]
    assert sweep["P"] == 32 and sweep["vocab_size"] == 131072 and sweep["queries"] == 10000
    for c in sweep["conditions"]:
        for r in c["taus"]:
            assert 0.0 <= r["wrong_accept_rate"] <= r["accept_rate"] <= 1.0
    garbage = next(c for c in sweep["conditions"] if c["name"] == "garbage")
    assert (
        garbage["argmax_accuracy"] == 0.0 and garbage["max_best_cos"] < 0.3
    )  # every non-zero tau in the grid rejects it
    summary = json.loads((RESULTS_DIR / "min_margin" / "tau_summary_P32.json").read_text(encoding="utf-8"))
    assert summary["proposed_tau"] == 0.3 and summary["dtypes"]["fp32"]["decoded_correctly"] == 131072
    assert abs(summary["dtypes"]["fp32"]["min_margin"] - 0.015809) < 1e-6
