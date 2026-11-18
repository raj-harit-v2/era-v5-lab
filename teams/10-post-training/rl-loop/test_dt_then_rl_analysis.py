"""Task 11 comparisons require scores on the same ordered held-out prompts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "capstone"))
import dt_then_rl  # noqa: E402

PROMPT_ORDER = "a" * 64
OTHER_ORDER = "b" * 64


def write_run(directory, before, after, *, end_step=30, digest=PROMPT_ORDER, final_digest=None):
    directory.mkdir()
    records = [
        {"name": "heldout", "step": 0, "scores": before, "prompt_order_sha256": digest},
        {"name": "heldout", "step": end_step, "scores": after,
         "prompt_order_sha256": digest if final_digest is None else final_digest},
    ]
    (directory / "evals.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records))
    (directory / "metrics.jsonl").write_text(json.dumps({"step": 1, "groups_used": 1}) + "\n")
    return directory


def test_aligns_seed_and_arm_results_with_matching_prompt_order(tmp_path):
    dt1 = write_run(tmp_path / "dt1", [0, 0.5], [0.5, 1])
    dt2 = write_run(tmp_path / "dt2", [0.25, 0.5], [0.75, 1])
    lora = write_run(tmp_path / "lora", [0, 0.5], [0.25, 0.75])
    report = dt_then_rl.analyze({"dt": [dt1, dt2], "lora": [lora]})
    assert report["dt"]["prompt_order_sha256"] == PROMPT_ORDER
    assert report["_pairs"]["dt-lora"]["problems"] == 2
    assert report["_pairs"]["dt-lora"]["diff"] == 0.25


def test_refuses_diff_between_same_length_arms_with_different_prompt_order(tmp_path):
    dt = write_run(tmp_path / "dt", [0, 0.5], [0.5, 1])
    lora = write_run(tmp_path / "lora", [0.5, 0], [1, 0.5], digest=OTHER_ORDER)
    with pytest.raises(ValueError, match="dt and lora have different held-out prompts or prompt order"):
        dt_then_rl.analyze({"dt": [dt], "lora": [lora]})


def test_refuses_diff_between_arms_with_unequal_score_counts(tmp_path):
    dt = write_run(tmp_path / "dt", [0, 0.5], [0.5, 1])
    lora = write_run(tmp_path / "lora", [0], [0.5])
    with pytest.raises(ValueError, match="dt and lora have different held-out prompts or prompt order"):
        dt_then_rl.analyze({"dt": [dt], "lora": [lora]})


def test_refuses_diff_between_arms_with_different_endpoints(tmp_path):
    dt = write_run(tmp_path / "dt", [0, 0.5], [0.5, 1], end_step=30)
    lora = write_run(tmp_path / "lora", [0, 0.5], [0.5, 1], end_step=20)
    with pytest.raises(ValueError, match="dt and lora have different held-out evaluation endpoints"):
        dt_then_rl.analyze({"dt": [dt], "lora": [lora]})


def test_refuses_changed_prompt_order_within_run_or_between_seeds(tmp_path):
    changed = write_run(tmp_path / "changed", [0, 0.5], [0.5, 1], final_digest=OTHER_ORDER)
    with pytest.raises(ValueError, match="heldout prompt order changed at step 30"):
        dt_then_rl.analyze({"dt": [changed]})

    dt1 = write_run(tmp_path / "dt1", [0, 0.5], [0.5, 1])
    dt2 = write_run(tmp_path / "dt2", [0, 0.5], [0.5, 1], digest=OTHER_ORDER)
    with pytest.raises(ValueError, match="runs of one arm have different held prompts or prompt order"):
        dt_then_rl.analyze({"dt": [dt1, dt2]})


def test_refuses_historical_records_without_prompt_fingerprint(tmp_path):
    dt = write_run(tmp_path / "dt", [0, 0.5], [0.5, 1], digest=None)
    with pytest.raises(ValueError, match="heldout evaluations need a prompt_order_sha256 fingerprint"):
        dt_then_rl.analyze({"dt": [dt]})
