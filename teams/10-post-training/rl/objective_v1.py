"""Session 18 objective, v1.

Group advantage with no division by the standard deviation, drop groups whose
rewards are all equal, and a trust-region mask on the importance ratio.

The trainer already has verifier scores from reward(env_id, output). This
module does not call the verifier and does not see expected answers.

    from objective_v1 import Rollout, objective_v1

    result = objective_v1([
        [Rollout(reward, logprobs, ratios), ...],  # one prompt, G completions
    ])
    if result.groups_kept == 0:
        skip the step
    else:
        minimize result.loss
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

EPSILON = 0.2


@dataclass(frozen=True)
class Rollout:
    """One completion. logprobs and ratios are one pair per generated token."""

    reward: float
    logprobs: tuple[float, ...]
    ratios: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.logprobs) != len(self.ratios):
            raise ValueError("logprobs and ratios must have one entry per token")
        if not math.isfinite(self.reward):
            raise ValueError("reward must be finite")
        for value in self.logprobs:
            if not math.isfinite(value):
                raise ValueError("logprobs must be finite")
        for value in self.ratios:
            if not math.isfinite(value) or value < 0:
                raise ValueError("ratios must be finite and >= 0")


@dataclass(frozen=True)
class ObjectiveResult:
    loss: float
    groups_in: int
    groups_kept: int
    groups_dropped: int
    tokens: int
    tokens_inside: int
    advantages: tuple[tuple[float, ...], ...]


def group_advantage(rewards: Sequence[float]) -> tuple[float, ...] | None:
    """Return r - mean(r) for one group.

    No division by the standard deviation. None means the group is dropped:
    every reward is equal, or the group has fewer than two rewards.
    """
    if not rewards:
        raise ValueError("a group needs rewards")
    values = tuple(float(r) for r in rewards)
    for value in values:
        if not math.isfinite(value):
            raise ValueError("reward must be finite")
    if len(values) < 2 or max(values) == min(values):
        return None
    center = sum(values) / len(values)
    return tuple(value - center for value in values)


def trust_region_mask(ratios: Sequence[float], epsilon: float = EPSILON) -> tuple[int, ...]:
    """1 when the importance ratio is inside [1 - epsilon, 1 + epsilon], else 0."""
    if epsilon < 0 or not math.isfinite(epsilon):
        raise ValueError("epsilon must be finite and >= 0")
    low = 1.0 - epsilon
    high = 1.0 + epsilon
    mask: list[int] = []
    for ratio in ratios:
        if not math.isfinite(ratio) or ratio < 0:
            raise ValueError("ratios must be finite and >= 0")
        mask.append(1 if low <= ratio <= high else 0)
    return tuple(mask)


def objective_v1(
    groups: Sequence[Sequence[Rollout]],
    epsilon: float = EPSILON,
) -> ObjectiveResult:
    """Token mean of -mask * advantage * log π over groups that were kept.

    A dropped group is absent from the numerator and the denominator. A token
    outside the trust region adds 0 and still counts in the denominator.
    When every group is dropped, or no kept group has a token, the loss is 0.
    """
    if epsilon < 0 or not math.isfinite(epsilon):
        raise ValueError("epsilon must be finite and >= 0")
    if len(groups) == 0:
        raise ValueError("objective_v1 needs at least one group")

    kept_advantages: list[tuple[float, ...]] = []
    total = 0.0
    tokens = 0
    tokens_inside = 0
    dropped = 0

    for group in groups:
        if len(group) == 0:
            raise ValueError("a group needs rewards")
        advantages = group_advantage([rollout.reward for rollout in group])
        if advantages is None:
            dropped += 1
            continue
        kept_advantages.append(advantages)
        for rollout, advantage in zip(group, advantages):
            mask = trust_region_mask(rollout.ratios, epsilon)
            tokens += len(rollout.logprobs)
            for bit, logprob in zip(mask, rollout.logprobs):
                tokens_inside += bit
                total += bit * advantage * logprob

    kept = len(kept_advantages)
    loss = 0.0 if tokens == 0 else -total / tokens
    return ObjectiveResult(
        loss=loss,
        groups_in=len(groups),
        groups_kept=kept,
        groups_dropped=dropped,
        tokens=tokens,
        tokens_inside=tokens_inside,
        advantages=tuple(kept_advantages),
    )
