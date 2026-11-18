"""Tests for the local small-RL update. The verifier run is the script, not this file.

    python -m pytest teams/10-post-training/rl/test_small_rl.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("g10_small_rl_under_test", HERE / "small_rl.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rl = _load()


def test_one_group_raises_the_correct_completion():
    old = math.log(0.5)
    logits, loss, kept = rl.update_policy([0.0, 0.0], [0, 1], [1.0, 0.0], [old, old], lr=1.0)
    assert kept is True
    assert loss == 0.0  # equal logprobs cancel in the group sum; the gradient still moves
    assert logits[0] > 0
    assert logits[1] < 0


def test_equal_rewards_leave_the_policy_unchanged():
    logits, loss, kept = rl.update_policy([0.2, -0.2], [0, 1], [1.0, 1.0], [math.log(0.5)] * 2, lr=1.0)
    assert kept is False
    assert loss == 0.0
    assert logits == [0.2, -0.2]


def test_a_ratio_outside_the_trust_region_does_not_move_the_policy():
    # Current logprob is log(0.5). An old logprob of 0 makes the ratio about 0.5, outside [0.8, 1.2].
    logits, _, kept = rl.update_policy([0.0, 0.0], [0, 1], [1.0, 0.0], [0.0, 0.0], lr=1.0)
    assert kept is True
    assert logits == [0.0, 0.0]
