"""Tests for the effort length penalty.

    python -m pytest teams/10-post-training/rl/test_effort_reward.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

parametrize = pytest.mark.parametrize  # a named decorator: pr-guard reads a dotted one as an email address

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


er = _load("g10_effort_reward_under_test", HERE / "effort_reward.py")
objective = _load("g10_objective_v1_for_effort_test", HERE / "objective_v1.py")


def test_budgets_are_the_chat_format_budgets():
    render = _load("g10_render_for_effort_test", HERE.parent / "chat-format" / "render.py")
    assert er.EFFORT_BUDGETS == dict(render.EFFORT_BUDGETS)


@parametrize("effort, budget", [("1k", 1024), ("4k", 4096), ("16k", 16384), ("64k", 65536)])
def test_a_trace_at_or_under_the_budget_keeps_its_score(effort, budget):
    assert er.shape_reward(1.0, 0, effort) == 1.0
    assert er.shape_reward(1.0, budget - 1, effort) == 1.0
    assert er.shape_reward(1.0, budget, effort) == 1.0  # the budget itself is inside it


@parametrize("effort, budget", [("1k", 1024), ("4k", 4096), ("16k", 16384), ("64k", 65536)])
def test_the_score_falls_in_a_straight_line_to_zero_over_the_ramp(effort, budget):
    assert er.shape_reward(1.0, budget + 1, effort) == pytest.approx(1 - 1 / 1024)
    assert er.shape_reward(1.0, budget + 512, effort) == pytest.approx(0.5)
    assert er.shape_reward(1.0, budget + 1024, effort) == 0.0
    assert er.shape_reward(1.0, budget + 50_000, effort) == 0.0


def test_the_same_trace_is_judged_against_the_label_asked_for():
    assert er.shape_reward(1.0, 3000, "4k") == 1.0
    assert er.shape_reward(1.0, 3000, "1k") == 0.0  # 1,976 over a 1,024 budget


def test_the_score_never_rises_as_the_trace_grows():
    values = [er.shape_reward(1.0, n, "4k") for n in range(0, 6000, 37)]
    assert all(a >= b for a, b in zip(values, values[1:]))


def test_a_wrong_answer_stays_zero_at_every_length():
    assert all(er.shape_reward(0.0, n, "4k") == 0.0 for n in (0, 100, 4096, 4097, 9000))


def test_a_malformed_trace_scores_zero_even_when_the_answer_was_right():
    assert er.shape_reward(1.0, None, "16k") == 0.0


def test_a_custom_ramp_moves_the_zero_point():
    assert er.shape_reward(1.0, 1024 + 100, "1k", ramp=200) == pytest.approx(0.5)
    assert er.shape_reward(1.0, 1024 + 200, "1k", ramp=200) == 0.0


@parametrize("args", [
    (1.0, 10, "2k"), (1.0, 10, ""), (1.0, 10, None),                       # unknown effort
    (1.5, 10, "1k"), (-0.1, 10, "1k"), (math.nan, 10, "1k"), (math.inf, 10, "1k"),  # reward outside 0 to 1
    (True, 10, "1k"), ("1", 10, "1k"),                                     # not a number
    (1.0, -1, "1k"), (1.0, 10.5, "1k"), (1.0, True, "1k"), (1.0, "10", "1k"),  # bad trace length
])
def test_bad_input_is_refused(args):
    with pytest.raises(ValueError):
        er.shape_reward(*args)


@parametrize("ramp", [0, -5, 1.5, True, None])
def test_a_bad_ramp_is_refused(ramp):
    with pytest.raises(ValueError):
        er.shape_reward(1.0, 10, "1k", ramp=ramp)


def test_a_group_of_correct_answers_that_differ_in_length_is_kept_and_prefers_the_shorter_one():
    # Three correct rollouts at 4k: one inside the budget, one 512 over, one far over. With raw 0/1 scores the group
    # is all equal and objective_v1 drops it; with shaped scores it is kept and the long rollout is pushed down.
    traces = [4000, 4096 + 512, 9000]
    raw = [[objective.Rollout(reward=1.0, logprobs=(-0.1,), ratios=(1.0,)) for _ in traces]]
    assert objective.objective_v1(raw).groups_kept == 0
    shaped = [[objective.Rollout(reward=er.shape_reward(1.0, n, "4k"), logprobs=(-0.1,), ratios=(1.0,)) for n in traces]]
    result = objective.objective_v1(shaped)
    assert result.groups_kept == 1
    adv = result.advantages[0]
    assert adv[0] > adv[1] > adv[2]
    assert adv[2] < 0 < adv[0]


def test_a_group_all_inside_the_budget_is_still_dropped_when_all_are_right():
    group = [[objective.Rollout(reward=er.shape_reward(1.0, n, "4k"), logprobs=(-0.1,), ratios=(1.0,))
              for n in (100, 2000, 4096)]]
    assert objective.objective_v1(group).groups_kept == 0
