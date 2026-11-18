"""Effort length penalty, v1 (proposal, see `effort_v1.md`).

The verifier gives 0 or 1. This module scales a score of 1 down when the rollout's reasoning trace is longer
than the budget of the effort label the prompt asked for. The trace is the think, tool-call and tool-result
spans, counted in tokens by the same rule as `sft/convert.py` (the final reply is not counted).

    from effort_reward import shape_reward

    shaped = shape_reward(reward=1.0, trace_tokens=4300, effort="4k")   # 1 - (4300 - 4096) / 1024

Pure Python, no model, no verifier call. Pass the result to `objective_v1` in place of the raw verifier score.
"""
from __future__ import annotations

import math

# Budgets of the four effort labels (chat-format v0, `render.EFFORT_BUDGETS`). A test keeps the two in step.
EFFORT_BUDGETS = {"1k": 1024, "4k": 4096, "16k": 16384, "64k": 65536}

# Tokens over the budget at which a correct answer is worth 0. Not tuned: no run supports this number.
RAMP = 1024


def shape_reward(reward: float, trace_tokens: int | None, effort: str, ramp: int = RAMP) -> float:
    """Scale a verifier score by how far the trace runs past the effort budget.

    - `trace_tokens` at or under the budget: the score is unchanged.
    - over the budget: the score falls in a straight line to 0 at `budget + ramp` tokens, and stays 0 beyond.
    - `trace_tokens` of None (a malformed or unclosed trace, as the effort suite reports it): 0.
    - a score of 0 stays 0, so a short wrong answer is never worth more than a long one.
    """
    if effort not in EFFORT_BUDGETS:
        raise ValueError(f"effort must be one of {', '.join(EFFORT_BUDGETS)}, got {effort!r}")
    if isinstance(ramp, bool) or not isinstance(ramp, int) or ramp <= 0:
        raise ValueError(f"ramp must be a positive integer, got {ramp!r}")
    if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward) \
            or not 0.0 <= reward <= 1.0:
        raise ValueError(f"reward must be a number from 0 to 1, got {reward!r}")
    if trace_tokens is None:
        return 0.0
    if isinstance(trace_tokens, bool) or not isinstance(trace_tokens, int) or trace_tokens < 0:
        raise ValueError(f"trace_tokens must be a non-negative integer or None, got {trace_tokens!r}")
    over = trace_tokens - EFFORT_BUDGETS[effort]
    if over <= 0:
        return float(reward)
    return float(reward) * max(0.0, 1.0 - over / ramp)
