import json

import numpy as np
import pytest

from metrics_writer import MetricsWriter
from tokens_per_byte import tokens_per_byte

# Two rows of 4 positions, -100 at padding. Row 0: 3 tokens, 2+3+1 = 6 bytes. Row 1: 2 tokens, 3+3 = 6 bytes.
Y = [[5, 6, 7, -100], [8, 9, -100, -100]]
B = [[2, 3, 1, 0], [3, 3, 0, 0]]


def test_batch_total_skips_padding():
    assert tokens_per_byte(Y, B) == {"tokens_per_byte": 5 / 12}


def test_by_lang():
    stats = tokens_per_byte(Y, B, langs=["en", "hi"])
    assert stats["tokens_per_byte"] == 5 / 12
    assert stats["tokens_per_byte_by_lang"] == {"en": 3 / 6, "hi": 2 / 6}


def test_untagged_rows_count_only_in_total():
    stats = tokens_per_byte(Y, B, langs=[None, "hi"])
    assert stats["tokens_per_byte"] == 5 / 12
    assert stats["tokens_per_byte_by_lang"] == {"hi": 2 / 6}


def test_no_tags_no_by_lang():
    assert "tokens_per_byte_by_lang" not in tokens_per_byte(Y, B, langs=[None, None])


def test_padding_bytes_ignored_even_if_nonzero():
    # Bytes at an ignored target do not count, so a loader bug there cannot move the metric.
    assert tokens_per_byte([[5, -100]], [[4, 9]]) == {"tokens_per_byte": 1 / 4}


def test_empty_batch_writes_nothing():
    assert tokens_per_byte([[-100, -100]], [[0, 0]]) == {}


def test_one_row_and_numpy():
    assert tokens_per_byte(np.array([5, 6, -100]), np.array([1, 3, 0])) == {"tokens_per_byte": 2 / 4}


def test_torch_tensors():
    torch = pytest.importorskip("torch")
    stats = tokens_per_byte(torch.tensor(Y), torch.tensor(B), langs=["en", "hi"])
    assert stats["tokens_per_byte"] == 5 / 12


@pytest.mark.parametrize("y, b, langs", [
    ([[1, 2]], [[1]], None),           # row lengths differ
    ([[1], [2]], [[1]], None),         # row counts differ
    (Y, B, ["en"]),                    # one tag short
    ([[1]], [[-1]], None),             # negative bytes
])
def test_bad_input_raises(y, b, langs):
    with pytest.raises(ValueError):
        tokens_per_byte(y, b, langs=langs)


def test_writer_keeps_both_names(tmp_path):
    path = str(tmp_path / "metrics.jsonl")
    with MetricsWriter(path) as w:
        w.write(1, **tokens_per_byte(Y, B, langs=["en", "hi"]))
    with open(path, encoding="utf-8") as f:
        row = json.loads(f.readline())
    assert row["tokens_per_byte"] == 5 / 12
    assert row["tokens_per_byte_by_lang"] == {"en": 0.5, "hi": 2 / 6}
