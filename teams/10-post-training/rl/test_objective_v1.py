"""Tests for the Session 18 objective.

    python -m pytest teams/10-post-training/rl/test_objective_v1.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("g10_objective_v1_under_test", HERE / "objective_v1.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


objective = _load()
Rollout = objective.Rollout


def test_group_advantage_is_centered_and_not_divided_by_std():
    advantages = objective.group_advantage([0.0, 1.0])
    assert advantages == (-0.5, 0.5)
    # Population std of [0, 1] is 0.5, so a divided advantage would be (-1, 1).
    assert advantages != (-1.0, 1.0)


def test_equal_rewards_drop_the_group():
    assert objective.group_advantage([1.0, 1.0, 1.0]) is None
    assert objective.group_advantage([0.0]) is None


def test_trust_region_mask_uses_closed_bounds():
    assert objective.trust_region_mask([0.7, 0.8, 1.0, 1.2, 1.3], epsilon=0.2) == (0, 1, 1, 1, 0)


def test_loss_matches_the_hand_formula_and_ignores_a_tied_group():
    useful = [
        Rollout(1.0, (-0.2, -0.4), (1.0, 1.3)),
        Rollout(0.0, (-0.1,), (0.9,)),
    ]
    tied = [Rollout(1.0, (-0.3,), (1.0,)), Rollout(1.0, (-0.3,), (1.0,))]
    alone = objective.objective_v1([useful])
    both = objective.objective_v1([useful, tied])

    # A = (0.5, -0.5). Mask drops the ratio 1.3 term.
    # terms = 0.5 * -0.2 + -0.5 * -0.1 = -0.05. Three tokens. L = 0.05 / 3.
    assert alone.advantages == ((0.5, -0.5),)
    assert alone.tokens == 3
    assert alone.tokens_inside == 2
    assert alone.loss == pytest.approx(0.05 / 3)
    assert both.loss == pytest.approx(alone.loss)
    assert both.groups_in == 2
    assert both.groups_kept == 1
    assert both.groups_dropped == 1


def test_all_tied_groups_have_zero_loss():
    tied = [Rollout(1.0, (-0.2,), (1.0,)), Rollout(1.0, (-0.4,), (1.0,))]
    result = objective.objective_v1([tied, tied])
    assert result.loss == 0.0
    assert result.groups_kept == 0
    assert result.groups_dropped == 2
    assert result.tokens == 0


def test_bad_inputs_raise():
    with pytest.raises(ValueError):
        Rollout(1.0, (-0.2,), (1.0, 1.0))
    with pytest.raises(ValueError):
        Rollout(float("nan"), (-0.2,), (1.0,))
    with pytest.raises(ValueError):
        objective.trust_region_mask([-0.1])
    with pytest.raises(ValueError):
        objective.objective_v1([])
    with pytest.raises(ValueError):
        objective.objective_v1([[]])
