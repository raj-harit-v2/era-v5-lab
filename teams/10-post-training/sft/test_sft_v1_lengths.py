"""Tests for sft_v1_lengths.py (context-length table). Synthetic rows only."""

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sft_v1_lengths as sl  # noqa: E402


def test_whole_row_fit_counts_rows_tokens_and_targets():
    tokens = np.array([100, 2048, 2049, 5000, 40000])
    targets = np.array([10, 20, 30, 40, 50])
    t = sl.table(tokens, targets)
    at = t["by_limit"]["2048"]
    assert at["rows_fit"] == 2 and at["tokens_fit"] == 2148 and at["shifted_targets_fit"] == 30
    assert at["tokens_if_truncated"] == 100 + 2048 * 4
    assert t["by_limit"]["32768"]["rows_fit"] == 4 and t["by_limit"]["32768"]["rows_fit_share"] == 0.8
    assert t["length"]["max"] == 40000 and t["rows"] == 5 and t["tokens"] == int(tokens.sum())


def test_rows_are_read_from_conversions_and_from_row_stats_with_filters(tmp_path):
    conv = tmp_path / "part0000.jsonl.gz"
    with gzip.open(conv, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"id": "a", "input_ids": [1, 2, 3, 4], "loss_mask": [1, 1, 0, 1]}) + "\n")
        f.write(json.dumps({"id": "b", "input_ids": [1, 2], "loss_mask": [0, 1]}) + "\n")
    tok, tgt, seen = sl.read_lengths([conv], {"a"}, None)
    assert tok.tolist() == [4] and tgt.tolist() == [2] and seen == 2  # position 0 is never a target
    stats = tmp_path / "rowstats.jsonl"
    stats.write_text("".join(json.dumps(r) + "\n" for r in (
        {"id": "x", "status": "pack", "tokens": 3000, "targets": 900},
        {"id": "y", "status": "heldout", "tokens": 100, "targets": 50},
        {"id": "z", "status": "screened_out", "tokens": 10, "targets": 5})))
    tok, tgt, _ = sl.read_lengths([stats], None, "pack")
    assert tok.tolist() == [3000] and tgt.tolist() == [900]


def test_cli_refuses_when_keep_ids_do_not_all_match(tmp_path):
    rows = tmp_path / "r.jsonl"
    rows.write_text(json.dumps({"id": "a", "tokens": 5, "targets": 1}) + "\n")
    keep = tmp_path / "keep.txt"
    keep.write_text("a\nb\n")
    with pytest.raises(SystemExit, match="1 rows matched"):
        sl.main(["--set", "s", "--area", "code", "--rows", str(rows), "--keep-ids", str(keep),
                 "--tokenizer-sha256", "0" * 64, "--out", str(tmp_path / "o.json")])
    keep.write_text("a\n")
    assert sl.main(["--set", "s", "--area", "code", "--rows", str(rows), "--keep-ids", str(keep),
                    "--tokenizer-sha256", "0" * 64, "--out", str(tmp_path / "o.json")]) == 0
    out = json.loads((tmp_path / "o.json").read_text())
    assert out["rows"] == 1 and out["by_limit"]["2048"]["rows_fit"] == 1 and "id" not in json.dumps(out["by_limit"])


def test_rows_of_excluded_families_are_left_out(tmp_path):
    stats = tmp_path / "rowstats.jsonl"
    stats.write_text("".join(json.dumps(r) + "\n" for r in (
        {"id": "x", "status": "pack", "family": "sha256:" + "a" * 64, "tokens": 3000, "targets": 900},
        {"id": "y", "status": "pack", "family": "sha256:" + "b" * 64, "tokens": 100, "targets": 50})))
    tok, _, _ = sl.read_lengths([stats], None, "pack", frozenset({"sha256:" + "a" * 64}))
    assert tok.tolist() == [100]
