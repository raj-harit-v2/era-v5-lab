"""Regression contract for G1/G9 word fingerprints versus G1 comparison keys.

Run: python -m pytest teams/01-data-a/spec_v1/tests/test_normalize_contract.py -q
All inputs are synthetic. These tests do not change fingerprints or clean.py.
"""

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "normalize.py"
SPEC = importlib.util.spec_from_file_location("g1_normalize_contract", MODULE_PATH)
n = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(n)


def test_g9_public_contract_is_stable():
    assert n.NORMALIZE_ID == "g1-spec-v1"
    assert isinstance(n.DESCRIPTION, str) and n.DESCRIPTION
    assert n.OFFSET_CONVENTION == "original_raw_word_start"
    text = "The first example"
    assert n.normalize(text) == [word for word, _ in n.words_with_offsets(text)]


def test_b1_decoding_is_key_only():
    text = "Fish &amp; chips"
    assert n.normalize(text) == ["fish", "amp", "chips"]
    assert n.match_key(text) == "fish & chips"
    assert "B1" in n.KEY_ONLY_STEPS


def test_a2_controls_are_key_only():
    text = "ab\x07cd"
    assert n.normalize(text) == ["ab", "cd"]
    assert n.match_key(text) == "abcd"
    assert "A2" in n.KEY_ONLY_STEPS


@pytest.mark.parametrize("source,equivalent", [
    ("com\u200bpute", "compute"),
    ("cafe\u0301", "café"),
    ("\ufb01rst", "first"),
    ("\uff26\uff4f\uff4f", "foo"),
    ("\u0958", "\u0915\u093c"),
])
def test_shared_a1_a5_equivalence(source, equivalent):
    assert n.normalize(source) == n.normalize(equivalent)
    assert n.match_key(source) == n.match_key(equivalent)


def test_fraction_expansion_uses_source_start_offsets():
    assert n.words_with_offsets("\u00bd") == [("1", 0), ("2", 0)]
    assert n.words_with_offsets("A \u00bd B") == [
        ("a", 0), ("1", 2), ("2", 2), ("b", 4)
    ]


def test_original_offsets_include_invisible_characters():
    text = "\ufeffcom\u200bpute next"
    assert n.words_with_offsets(text) == [("compute", 0), ("next", 10)]


def test_joiners_and_indic_digits_remain_distinguishable():
    assert n.normalize("क्\u200dष") != n.normalize("क्\u200cष")
    assert n.normalize("१२") != n.normalize("12")


def test_lossy_math_and_code_matching_is_documented():
    assert n.normalize("X = 2") == n.normalize("x = 2")
    assert n.normalize("def f():\n    return 1") == n.normalize("def f(): return 1")


def test_all_interfaces_leave_input_unchanged():
    row = {"doc_id": "synthetic", "text": "The café\u200b example"}
    original = dict(row)
    n.normalize(row["text"])
    n.words_with_offsets(row["text"])
    n.match_key(row["text"])
    n.line_keys(row["text"])
    n.explain(row["text"])
    assert row == original


def test_g1_key_and_g9_word_api_use_distinct_steps():
    assert n.KEY_ONLY_STEPS == ("B1", "A2", "space")
    assert n.normalize("Fish &amp; chips") != n.normalize(n.match_key("Fish &amp; chips"))
