"""Tests for gradient_clipping_applied in metrics_writer.py.

    cd teams/08-monitoring/metrics_logger && python -m pytest test_gradient_clipping.py -q
"""
import json
import math

import pytest
import torch

from metrics_writer import MetricsWriter, gradient_clipping_applied


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("norm, clip, flag", [
    (2.5, 1.0, 1),                 # above the threshold: scaled down
    (0.4, 1.0, 0),                 # below: left alone
    (1.0, 1.0, 0),                 # equal is not above (same rule as G5's train_week2.py)
    (math.inf, 1.0, 1),            # an infinite norm is clipped
    (torch.tensor(3.0), 1.0, 1),   # what clip_grad_norm_ returns
    (torch.tensor(0.5), 1, 0),
])
def test_flag(norm, clip, flag):
    assert gradient_clipping_applied(norm, clip) == flag


@pytest.mark.parametrize("norm, clip", [
    (None, 1.0), (2.0, None),      # one of the two is missing
    (math.nan, 1.0),               # NaN norm: cannot be told
    (2.0, 0.0), (2.0, -1.0), (2.0, math.inf), (2.0, True), (2.0, "x"),   # not a usable threshold
])
def test_cannot_be_told(norm, clip):
    assert gradient_clipping_applied(norm, clip) is None


def test_clip_grad_norm_really_clips_when_flag_is_1():
    """The rule matches what torch does: the gradients shrink exactly when the flag is 1."""
    for scale, flag in [(10.0, 1), (0.01, 0)]:
        w = torch.nn.Parameter(torch.ones(4))
        (w * scale).sum().backward()
        before = w.grad.clone()
        norm = torch.nn.utils.clip_grad_norm_([w], 1.0)
        assert gradient_clipping_applied(norm, 1.0) == flag
        assert (not torch.equal(w.grad, before)) == bool(flag)


def test_writer_works_it_out_and_does_not_store_the_threshold(tmp_path):
    path = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(path), flush_every=1) as w:
        w.write(1, loss_ntp=2.0, gradient_norm=torch.tensor(2.5), grad_clip=1.0)
        w.write(2, loss_ntp=2.0, gradient_norm=0.3, grad_clip=1.0)
        w.write(3, loss_ntp=2.0, gradient_norm=0.3)                    # no threshold: no flag
        w.write(4, loss_ntp=2.0, gradient_norm=float("nan"), grad_clip=1.0)
    r = rows(path)
    assert [x.get("gradient_clipping_applied") for x in r] == [1, 0, None, None]
    assert r[0]["gradient_norm"] == 2.5 and r[3]["gradient_norm"] == "nan"
    assert all("grad_clip" not in x for x in r)


def test_flag_from_trainer_wins_and_bool_becomes_int(tmp_path):
    path = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(path), flush_every=1) as w:
        w.write(1, gradient_norm=0.3, gradient_clipping_applied=True)      # G5 train_week2.py writes a bool
        w.write(2, gradient_norm=5.0, grad_clip=1.0, gradient_clipping_applied=False)
        w.write(3, gradient_clipping_applied=torch.tensor(True))
    r = rows(path)
    assert [x["gradient_clipping_applied"] for x in r] == [1, 0, 1]
    assert all(type(x["gradient_clipping_applied"]) is int for x in r)
