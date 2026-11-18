"""Deletion Tuning, ported from arXiv 2611.10866.

The repository read for this port is
https://github.com/agentic-learning-ai-lab/deleting-weights
(MIT), module src/learnable_sparsity. The formulas below are equations (5) to (8)
and the SFT regularizer in section 4 of the paper.

A target weight W stays frozen. One logit G per weight is the only trained value.
During training the layer uses W * sigmoid(alpha(t) * G). At evaluation it uses
W * 1[G > 0]. alpha rises linearly from 1e3 to 1e4. The SFT loss adds
-lambda * ||W * mask||^2 with lambda 1e-5.
"""
from __future__ import annotations

import math
import random

SHARPNESS_START = 1e3
SHARPNESS_END = 1e4
LAMBDA_SFT = 1e-5
ETA = 1 / 2048
WANDA_MEAN = 0.03
WANDA_STD = 0.01


def sharpness(step: int, total_steps: int, start: float = SHARPNESS_START, end: float = SHARPNESS_END) -> float:
    """Linear mask sharpening. Step 0 is the start value. Step total_steps is the end value."""
    if total_steps <= 0:
        raise ValueError("total_steps must be positive")
    if start <= 0 or end <= 0:
        raise ValueError("sharpness endpoints must be positive")
    progress = min(max(step, 0) / total_steps, 1.0)
    return start + (end - start) * progress


def soft_mask(logits: list[float], alpha: float) -> list[float]:
    """sigmoid(alpha * G), one value per logit."""
    if alpha <= 0 or not math.isfinite(alpha):
        raise ValueError("alpha must be finite and positive")
    masks = []
    for logit in logits:
        if not math.isfinite(logit):
            raise ValueError("logits must be finite")
        scaled = alpha * logit
        if scaled >= 0:
            masks.append(1.0 / (1.0 + math.exp(-scaled)))
        else:
            exponent = math.exp(scaled)
            masks.append(exponent / (1.0 + exponent))
    return masks


def hard_keep(logits: list[float]) -> list[bool]:
    """True keeps the pretrained weight. A logit of 0 is deleted, matching 1[G > 0]."""
    return [logit > 0 for logit in logits]


def apply_mask(weight: list[list[float]], mask: list[float]) -> list[list[float]]:
    """Return W * mask. weight is out by in, and mask is that matrix flattened row by row."""
    expected = sum(len(row) for row in weight)
    if len(mask) != expected:
        raise ValueError("mask length does not match the weight")
    out = []
    cursor = 0
    for row in weight:
        width = len(row)
        out.append([value * bit for value, bit in zip(row, mask[cursor:cursor + width])])
        cursor += width
    return out


def weight_norm_sq(weight: list[list[float]]) -> float:
    """||W||^2."""
    return sum(value * value for row in weight for value in row)


def deletion_loss(task_loss: float, masked_weight: list[list[float]], lam: float = LAMBDA_SFT) -> float:
    """Task loss minus lambda * ||masked weight||^2."""
    if lam < 0 or not math.isfinite(lam) or not math.isfinite(task_loss):
        raise ValueError("task loss and lambda must be finite, and lambda must be >= 0")
    return task_loss - lam * weight_norm_sq(masked_weight)


def importance_means(scores: list[float], eta: float = ETA) -> list[float]:
    """+0.03 for the top 1-eta fraction of Wanda scores, otherwise -0.03."""
    if not scores:
        raise ValueError("scores are empty")
    if not 0 <= eta < 1:
        raise ValueError("eta must be in [0, 1)")
    order = sorted(range(len(scores)), key=lambda index: scores[index])
    n_low = int(round(eta * len(scores)))
    means = [WANDA_MEAN] * len(scores)
    for index in order[:n_low]:
        means[index] = -WANDA_MEAN
    return means


def wanda_scores(weight: list[list[float]], column_norm: list[float]) -> list[float]:
    """|W_ij| * ||X_j|| for each weight, row by row."""
    if any(len(row) != len(column_norm) for row in weight):
        raise ValueError("each weight row must match the column norms")
    return [abs(value) * column_norm[col] for row in weight for col, value in enumerate(row)]


def init_logits(scores: list[float], rng: random.Random, eta: float = ETA, std: float = WANDA_STD) -> list[float]:
    """Draw each logit from the Wanda Gaussian in equation (8)."""
    return [rng.gauss(mean, std) for mean in importance_means(scores, eta)]
