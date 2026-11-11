"""Dense fp32 / bf16 scorer check (src/margins/dense_check.py) against the exact margins."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "margins"))

import dense_check as dc
import pair_margins as pm

# Aliases: pr-guard's email check misreads dotted pytest decorators as addresses.
fixture = pytest.fixture
parametrize = pytest.mark.parametrize

EXACT_31_32 = 0.015809320  # fp64 margin of a 31-byte token whose rival is its 32-byte extension, P = 32


def test_fp32_and_bf16_accumulate_agree_with_exact_margins(synthetic_p8):
    t, ids = synthetic_p8, np.arange(0, synthetic_p8.vocab_size, 3)
    checks = dc.dense_check(t, ids, chunk_rows=16)
    exact = pm.self_margins(t, [pm.exact_values(t)], query_ids=ids)["fp64"]
    for mode in ("fp32", "bf16_fp32acc"):
        # rivals are not compared: exact ties among candidates may break differently in fp32
        assert np.array_equal(checks[mode].decoded_ids, ids)
        np.testing.assert_allclose(checks[mode].margins, exact.margins, rtol=0, atol=1e-4)


def test_bf16_score_rounding_shrinks_the_tightest_p32_margin(make_byte_table):
    t = make_byte_table([b"a" * 31, b"a" * 31 + b"b", b"z"], P=32)
    checks = dc.dense_check(t, np.array([0]))
    assert checks["fp32"].margins[0] == pytest.approx(EXACT_31_32, abs=1e-4)
    assert checks["bf16_fp32acc"].margins[0] == pytest.approx(EXACT_31_32, abs=1e-4)
    assert 0 < checks["bf16_out"].margins[0] < 0.8 * EXACT_31_32  # probe: 0.01214
    assert (int(checks["bf16_out"].decoded_ids[0]), int(checks["bf16_out"].rival_ids[0])) == (0, 1)


def test_chunk_rows_do_not_change_dense_decisions(synthetic_p8):
    ids = np.arange(0, synthetic_p8.vocab_size, 5)
    a, b = dc.dense_check(synthetic_p8, ids, chunk_rows=5), dc.dense_check(synthetic_p8, ids)
    for mode in dc.MODES:
        assert np.array_equal(a[mode].decoded_ids, b[mode].decoded_ids)
        # fp32 matrix products round differently per block shape (measured up to 1.2e-5 here)
        np.testing.assert_allclose(a[mode].margins, b[mode].margins, rtol=0, atol=1e-4)


def test_unknown_mode_is_refused(synthetic_p8):
    with pytest.raises(ValueError, match="mode"):
        dc.dense_check(synthetic_p8, np.array([0]), modes=("fp16",))
