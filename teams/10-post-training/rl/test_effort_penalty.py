"""Tests for effort subgroups and length penalty in RL post-training.

    python -m pytest teams/10-post-training/rl/test_effort_penalty.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ep = _load("g10_effort_penalty_under_test", "effort_penalty.py")
obj = _load("g10_objective_v1_under_test", "objective_v1.py")


def test_zero_penalty_when_within_budget():
    for label, budget in ep.EFFORT_BUDGETS.items():
        assert ep.length_penalty(budget, label, beta=0.01) == 0.0
        assert ep.length_penalty(budget // 2, label, beta=0.01) == 0.0
        assert ep.length_penalty(0, label, beta=0.01) == 0.0


def test_positive_penalty_when_exceeding_budget():
    # Budget for 1k is 1024
    pen = ep.length_penalty(2048, "1k", beta=0.01, penalty_type="relative_excess")
    # (2048 - 1024) / 1024 = 1.0; 1.0 * 0.01 = 0.01
    assert pytest.approx(pen, rel=1e-5) == 0.01


def test_penalized_reward_respects_floor():
    reward = ep.penalized_reward(base_reward=0.0, token_length=5000, effort_label="1k", beta=0.05, floor=0.0)
    assert reward == 0.0

    reward_pos = ep.penalized_reward(base_reward=1.0, token_length=2048, effort_label="1k", beta=0.01)
    assert pytest.approx(reward_pos, rel=1e-5) == 0.99


def test_manifest_audit_identifies_100_slots():
    manifest_path = TEAM / "eval" / "effort_manifest.json"
    audit = ep.evaluate_manifest_slots(manifest_path)
    assert audit["total_slots"] == 100
    assert audit["resolved_count"] == 55
    assert audit["unavailable_count"] == 45
    assert audit["categories"]["code"]["total"] == 30
    assert audit["categories"]["code"]["resolved"] == 30
    assert audit["categories"]["math"]["total"] == 25
    assert audit["categories"]["math"]["resolved"] == 25
    assert audit["categories"]["tool_agentic"]["total"] == 20
    assert audit["categories"]["tool_agentic"]["unavailable"] == 20
    assert audit["categories"]["indic"]["total"] == 15
    assert audit["categories"]["indic"]["unavailable"] == 15
    assert audit["categories"]["general"]["total"] == 10
    assert audit["categories"]["general"]["unavailable"] == 10


def test_effort_penalty_integrates_with_objective_v1():
    # 2 completions: one concise (1000 tokens, reward 1.0), one verbose (2048 tokens, reward 1.0)
    # under 1k effort (budget 1024)
    r1 = ep.penalized_reward(1.0, 1000, "1k", beta=0.05)
    r2 = ep.penalized_reward(1.0, 2048, "1k", beta=0.05)
    assert r1 == 1.0
    # 2048 tokens: excess is 1024 / 1024 = 1.0 -> penalty 0.05 -> r2 = 0.95
    assert pytest.approx(r2, rel=1e-5) == 0.95

    # Group advantage should award positive advantage to the concise completion
    adv = obj.group_advantage([r1, r2])
    assert adv is not None
    assert adv[0] > 0.0
    assert adv[1] < 0.0
    assert pytest.approx(adv[0] + adv[1], abs=1e-7) == 0.0
