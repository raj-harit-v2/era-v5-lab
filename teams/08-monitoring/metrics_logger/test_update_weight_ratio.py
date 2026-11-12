"""Tests for compute_update_weight_ratio and step_with_update_weight_ratio in metrics_writer.py.

    cd teams/08-monitoring/metrics_logger && python -m pytest test_update_weight_ratio.py -q
"""
import json
import math

import numpy as np
import pytest
import torch

from metrics_writer import FLUSH_EVERY, MetricsWriter, compute_update_weight_ratio, step_with_update_weight_ratio


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_single_param_pairs_and_lr_scale():
    # ||W|| = 5, ||u|| = 1 → ratio 0.2; with lr=2 → ||2u||/||W|| = 0.4
    pairs = [(torch.tensor([3.0, 4.0]), torch.tensor([0.0, 1.0]))]
    assert compute_update_weight_ratio(pairs, every_n_steps=1) == pytest.approx(0.2)
    assert compute_update_weight_ratio(pairs, lr=2.0, every_n_steps=1) == pytest.approx(0.4)


def test_global_norm_over_several_params():
    # W: ||[3,4]||^2 + ||[0,0,12]||^2 = 25 + 144 = 169 → ||W|| = 13
    # U: ||[0,5]||^2 + ||[12,0,0]||^2 = 25 + 144 = 169 → ||U|| = 13 → ratio 1.0
    weights = [torch.tensor([3.0, 4.0]), torch.tensor([0.0, 0.0, 12.0])]
    updates = [torch.tensor([0.0, 5.0]), torch.tensor([12.0, 0.0, 0.0])]
    assert compute_update_weight_ratio(weights, updates, every_n_steps=1) == pytest.approx(1.0)


def test_weights_after_matches_delta():
    before = [torch.tensor([1.0, 2.0, 2.0]), torch.ones(4)]
    after = [torch.tensor([1.5, 2.0, 2.0]), torch.ones(4) * 1.25]
    # Δ0 = [0.5, 0, 0], Δ1 = 0.25 * ones(4); ||W||^2 = 9 + 4 = 13; ||Δ||^2 = 0.25 + 0.25 = 0.5
    expected = math.sqrt(0.5) / math.sqrt(13.0)
    assert compute_update_weight_ratio(before, weights_after=after, every_n_steps=1) == pytest.approx(expected)


def test_numpy_and_python_pairs():
    pairs = [([3.0, 4.0], [0.6, 0.8])]  # ||W||=5, ||U||=1 → 0.2
    assert compute_update_weight_ratio(pairs, every_n_steps=1) == pytest.approx(0.2)
    assert compute_update_weight_ratio(
        [np.array([3.0, 4.0])], [np.array([0.6, 0.8])], every_n_steps=1,
    ) == pytest.approx(0.2)


def test_cadence_default_every_10_steps():
    pairs = [(torch.ones(2), torch.ones(2) * 0.1)]
    assert compute_update_weight_ratio(pairs, step=0) == pytest.approx(0.1)
    assert compute_update_weight_ratio(pairs, step=10) == pytest.approx(0.1)
    assert compute_update_weight_ratio(pairs, step=7) is None
    assert compute_update_weight_ratio(pairs, step=7, every_n_steps=1) == pytest.approx(0.1)
    unit = [(torch.ones(1), torch.ones(1))]
    assert compute_update_weight_ratio(unit, step=FLUSH_EVERY - 1) is None
    assert compute_update_weight_ratio(unit, step=FLUSH_EVERY) == pytest.approx(1.0)


@pytest.mark.parametrize("weights, updates, kwargs", [
    ([], None, {"every_n_steps": 1}),                          # no parameters
    ([(torch.zeros(3), torch.ones(3))], None, {"every_n_steps": 1}),  # zero weight norm
    ([(torch.ones(2), torch.ones(2))], None, {"lr": float("nan"), "every_n_steps": 1}),
    ([(torch.ones(2), torch.ones(2))], None, {"lr": True, "every_n_steps": 1}),
    ([(torch.tensor([1.0, float("nan")]), torch.ones(2))], None, {"every_n_steps": 1}),
])
def test_cannot_be_told(weights, updates, kwargs):
    assert compute_update_weight_ratio(weights, updates, **kwargs) is None


def test_nonfinite_update_is_nan():
    pairs = [(torch.ones(2), torch.tensor([1.0, float("inf")]))]
    assert math.isnan(compute_update_weight_ratio(pairs, every_n_steps=1))


def test_bad_shapes_and_module_return_none():
    model = torch.nn.Linear(2, 2)
    assert compute_update_weight_ratio(model, every_n_steps=1) is None
    assert compute_update_weight_ratio(
        [torch.ones(2), torch.ones(2)], [torch.ones(2)], every_n_steps=1,
    ) is None
    assert compute_update_weight_ratio(
        [torch.ones(2)], updates=[torch.ones(2)], weights_after=[torch.ones(2)], every_n_steps=1,
    ) is None


def test_every_n_steps_must_be_positive():
    with pytest.raises(ValueError):
        compute_update_weight_ratio([(torch.ones(1), torch.ones(1))], every_n_steps=0)


def test_writer_accepts_scalar_ratio(tmp_path):
    path = tmp_path / "metrics.jsonl"
    pairs = [(torch.tensor([3.0, 4.0]), torch.tensor([0.0, 1.0]))]
    ratio = compute_update_weight_ratio(pairs, step=10)
    assert ratio == pytest.approx(0.2)
    with MetricsWriter(str(path), flush_every=1) as w:
        w.write(10, loss_ntp=1.0, update_weight_ratio=ratio)
    assert rows(path)[0]["update_weight_ratio"] == pytest.approx(0.2)


def test_writer_skips_none_only_when_omitted(tmp_path):
    """Trainer pattern: only pass the metric when the helper returns a value."""
    path = tmp_path / "metrics.jsonl"
    pairs = [(torch.ones(4), 0.05 * torch.ones(4))]
    with MetricsWriter(str(path), flush_every=1) as w:
        for step in (1, 10):
            metrics = {"loss_ntp": 1.0}
            ratio = compute_update_weight_ratio(pairs, step=step)
            if ratio is not None:
                metrics["update_weight_ratio"] = ratio
            w.write(step, **metrics)
    r = rows(path)
    assert "update_weight_ratio" not in r[0]
    assert r[1]["update_weight_ratio"] == pytest.approx(0.05)


def test_matches_manual_global_l2():
    torch.manual_seed(0)
    weights = [torch.randn(3, 3), torch.randn(5), torch.randn(2, 2, 2)]
    updates = [0.01 * torch.randn_like(w) for w in weights]
    got = compute_update_weight_ratio(weights, updates, lr=3e-4, every_n_steps=1)
    w_norm = math.sqrt(sum(float(w.norm() ** 2) for w in weights))
    u_norm = math.sqrt(sum(float(u.norm() ** 2) for u in updates))
    assert got == pytest.approx((3e-4 * u_norm) / w_norm)


def sgd_model(lr=0.1):
    torch.manual_seed(0)
    model = torch.nn.Linear(4, 2)
    optimizer = torch.optim.SGD(model.parameters(), lr=lr)
    model(torch.randn(8, 4)).pow(2).mean().backward()
    return model, optimizer


def test_step_sgd_matches_lr_times_grad():
    # Plain SGD moves the weights by lr * grad, so the ratio is lr * |grad| / |W|.
    model, optimizer = sgd_model(lr=0.1)
    params = list(model.parameters())
    grad = math.sqrt(sum(float(p.grad.pow(2).sum()) for p in params))
    weight = math.sqrt(sum(float(p.detach().pow(2).sum()) for p in params))
    assert step_with_update_weight_ratio(optimizer, 10) == pytest.approx(0.1 * grad / weight)


def test_step_off_steps_still_step_and_give_none():
    model, optimizer = sgd_model()
    before = model.weight.detach().clone()
    assert step_with_update_weight_ratio(optimizer, 7) is None
    assert not torch.equal(model.weight, before)


def test_step_every_n_steps():
    _, optimizer = sgd_model()
    got = [step_with_update_weight_ratio(optimizer, s, every_n_steps=3) for s in range(1, 7)]
    assert [g is not None for g in got] == [False, False, True, False, False, True]


def test_step_written_as_one_number(tmp_path):
    path = tmp_path / "metrics.jsonl"
    _, optimizer = sgd_model()
    with MetricsWriter(str(path)) as w:
        w.write(10, update_weight_ratio=step_with_update_weight_ratio(optimizer, 10))
    row = rows(path)[0]
    assert isinstance(row["update_weight_ratio"], float) and row["update_weight_ratio"] > 0
