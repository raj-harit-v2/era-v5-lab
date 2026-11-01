"""perfkit/report.py.

  * compare(): refuses a baseline pair that does not time the same committed code (other commit, dirty or unknown
    tree) or that changes a MoE setting other than dispatch; accepts and labels A/B a pair that differs only in
    optim.muon_impl or model.moe.dispatch.
  * render(): the CUDA timing-event allocation diagnostics per stage and the run's warnings, word for word.
"""
from __future__ import annotations

import copy

import pytest

from perfkit import report
from perfkit.schema import example_run


def _pair(**b_meta):
    a = example_run()
    b = copy.deepcopy(a)
    b["meta"].update(tag="b", **b_meta)
    return a, b


def test_same_clean_commit_passes():
    _, ok, problems = report.compare(*_pair(), 5.0, 2, 0.0)
    assert ok and problems == []


def test_same_commit_muon_implementation_variants_can_be_compared():
    a, b = _pair()
    a["config"]["optim"].update(name="muon", muon_impl="loop")
    b["config"]["optim"].update(name="muon", muon_impl="batched")
    _, ok, problems = report.compare(a, b, 5.0, 2, 0.0)
    assert ok and problems == []


def test_same_commit_moe_dispatch_variants_can_be_compared():
    a, b = _pair()
    a["config"]["model"]["moe"] = {"dispatch": "loop", "num_experts": 8}
    b["config"]["model"]["moe"] = {"dispatch": "sorted", "num_experts": 8}
    _, ok, problems = report.compare(a, b, 5.0, 2, 0.0)
    assert ok and problems == []
    assert "model.moe.dispatch: loop vs sorted" in report.ab_note(a, b)
    assert "A/B" in report.baseline_md(a, b, [], ok, problems)


def test_same_implementation_is_not_labelled_ab():
    a, b = _pair()
    assert report.ab_note(a, b) is None
    assert "A/B" not in report.baseline_md(a, b, [], True, [])


def test_moe_setting_other_than_dispatch_is_still_refused():
    a, b = _pair()
    a["config"]["model"]["moe"] = {"dispatch": "loop", "num_experts": 8}
    b["config"]["model"]["moe"] = {"dispatch": "sorted", "num_experts": 4}
    _, ok, problems = report.compare(a, b, 5.0, 2, 0.0)
    assert not ok and "different model config" in problems


def test_different_commit_is_refused():
    _, ok, problems = report.compare(*_pair(commit="1" * 40), 5.0, 2, 0.0)
    assert not ok and any("different commit" in p for p in problems)


def test_dirty_or_unknown_tree_is_refused():
    for dirty in (True, None):
        _, ok, problems = report.compare(*_pair(dirty=dirty), 5.0, 2, 0.0)
        assert not ok and any(f"dirty={dirty}" in p for p in problems)


@pytest.mark.parametrize(
    ("b_ms", "expected"),
    [(104.9, True), (105.1, False), (95.3, True), (95.0, False)],
)
def test_compare_applies_five_percent_gate_at_boundary(b_ms, expected):
    a, b = _pair()
    a["clean"]["step_ms"]["median"] = 100.0
    b["clean"]["step_ms"]["median"] = b_ms
    rows, ok, problems = report.compare(a, b, 5.0, 2, 0.0)
    assert problems == []
    assert ok is expected
    step = next(row for row in rows if row[0] == "step (clean)")
    assert step[4] == ("ok" if expected else "FAIL")


# ------------------------------------------------------------------------------ exact timing diagnostics in Markdown

def test_render_shows_per_stage_cuda_allocation_diagnostics():
    run = example_run()
    run["clean"]["events_created_during_steps"] = 0
    run["layer"] = {"events_created_during_steps": 2,
                    "inner_pass": {"events_created_during_steps": 4}}
    run["comm"] = {"moe_a2a": {"events_created_during_steps": 3}}
    run["warnings"] = ["9 CUDA timing events were created during measured steps"]
    md = report.render(run)
    assert "[OK] clean: events_created_during_steps=0" in md
    assert "[WARN] layer: events_created_during_steps=2" in md
    assert "[WARN] layer.inner_pass: events_created_during_steps=4" in md
    assert "[WARN] communication.max_rank: events_created_during_steps=3" in md
    assert "[warn] 9 CUDA timing events were created during measured steps" in md


def test_render_preserves_exact_warning_text_and_no_false_ke_claim():
    run = example_run()
    run["warnings"] = ["recorder overhead 3.2% > 2.0%: layer numbers are flagged"]
    md = report.render(run)
    assert "[warn] recorder overhead 3.2% > 2.0%: layer numbers are flagged" in md
    assert md.count("[warn] recorder overhead 3.2%") == 1
    assert "# Bench report" in md
    assert "## Step (clean)" in md
    assert "- MFU: 3.1%  |  HFU: 5.2%" in md
    assert "## Diagnostics" in md
    assert "## Regions" in md and "| fwd:block0 |" in md
    assert "## Five slowest leaf parts" in md


# Sunil PR24 review regression: distinct pool-counter diagnostics
def test_render_flags_inner_pool_allocation_when_timer_count_is_zero():
    run = example_run()
    run["layer"] = {"events_created_during_steps": 0,
                    "inner_pass": {"events_created_during_steps": 0,
                                   "events_created_while_measuring": 57}}
    run["warnings"] = ["57 recorder-pool CUDA events were created during layer.inner_pass measured steps"]
    md = report.render(run)
    assert "[OK] layer: events_created_during_steps=0" in md
    assert "[WARN] layer.inner_pass.recorder_pool: events_created_while_measuring=57" in md
    assert "[warn] 57 recorder-pool CUDA events" in md


def test_baseline_md_renders_run_metadata_comparison_and_gate_verdict():
    a, b = _pair()
    b["meta"]["tag"] = "candidate"
    rows, ok, problems = report.compare(a, b, 5.0, 2, 0.0)
    md = report.baseline_md(a, b, rows, ok, problems)
    assert "# Baseline comparison — PASS" in md
    assert "**GPU:** EXAMPLE-GPU (vs EXAMPLE-GPU)" in md
    assert "**commit a:**" in md and "**commit b:**" in md
    assert "## Comparison table" in md
    assert "| step (clean) |" in md
    assert "| ok |" in md


def test_a_model_key_added_later_counts_as_its_default():
    """A run written before model.activation existed compares equal to a new GELU run (the default keeps the old
    behaviour), and is refused against a SwiGLU run: a different model."""
    old, new = _pair()
    old["config"]["model"].pop("activation", None)
    new["config"]["model"]["activation"] = "gelu"
    _, ok, problems = report.compare(old, new, 5.0, 2, 0.0)
    assert ok and problems == []
    new["config"]["model"]["activation"] = "swiglu"
    _, ok, problems = report.compare(old, new, 5.0, 2, 0.0)
    assert not ok and "different model config" in problems
