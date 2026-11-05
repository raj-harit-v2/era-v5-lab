import json
import math

import numpy as np
import pytest
import torch

from metrics_writer import MetricsWriter, router_max_vio, router_max_vio_per_layer


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "metrics.jsonl")


def rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_flush_at_step_10(path):
    w = MetricsWriter(path)
    for step in range(1, 10):
        w.write(step, loss_ntp=1.0)
    assert rows(path) == []
    w.write(10, loss_ntp=1.0)
    assert [r["step"] for r in rows(path)] == list(range(1, 11))
    w.close()


@pytest.mark.parametrize("bad, stored", [
    (float("nan"), "nan"), (float("inf"), "inf"), (float("-inf"), "-inf")])
def test_nonfinite_flushes_at_once(path, bad, stored):
    w = MetricsWriter(path)
    w.write(1, loss_ntp=1.0)
    w.write(2, loss_ntp=bad)
    assert [r["loss_ntp"] for r in rows(path)] == [1.0, stored]
    w.close()


def test_alias_gpu_alloc_gb(path):
    with MetricsWriter(path) as w:
        w.write(1, gpu_alloc_gb=1.5)
    row = rows(path)[0]
    assert row["gpu_alloc_gib"] == 1.5
    assert "gpu_alloc_gb" not in row


def test_unknown_name_skipped_with_one_warning(path, capsys):
    with MetricsWriter(path) as w:
        w.write(1, gradient_nrom=1.0, loss_ntp=1.0)
        w.write(2, gradient_nrom=2.0)
    assert all("gradient_nrom" not in r for r in rows(path))
    assert rows(path)[0]["loss_ntp"] == 1.0
    assert capsys.readouterr().err.count("gradient_nrom") == 1


def test_numpy_scalar(path):
    with MetricsWriter(path) as w:
        w.write(1, lr=np.float32(0.5), loss_ntp=np.float32("nan"))
    row = rows(path)[0]
    assert row["lr"] == 0.5
    assert row["loss_ntp"] == "nan"


def test_torch_scalar(path):
    with MetricsWriter(path) as w:
        w.write(1, gradient_norm=torch.tensor(2.5), loss_mtp=torch.tensor(float("inf")))
    row = rows(path)[0]
    assert row["gradient_norm"] == 2.5
    assert row["loss_mtp"] == "inf"


def test_list_of_tensors_and_arrays(path):
    with MetricsWriter(path) as w:
        w.write(1, expert_load=np.array([0.25, 0.75]), update_weight_ratio=[torch.tensor(1.0)])
    row = rows(path)[0]
    assert row["expert_load"] == [0.25, 0.75]
    assert row["update_weight_ratio"] == [1.0]


def test_close_twice(path):
    w = MetricsWriter(path)
    w.write(1, loss_ntp=1.0)
    w.close()
    w.close()
    assert len(rows(path)) == 1


# router_max_vio: DeepSeek MaxVio, (max load - mean load) / mean load, from expert_load.

def test_router_max_vio_balanced_is_zero():
    assert router_max_vio([0.25, 0.25, 0.25, 0.25]) == 0.0


def test_router_max_vio_one_layer():
    # mean 0.25, busiest expert 0.5 -> (0.5 - 0.25) / 0.25 = 1.0
    assert router_max_vio([0.5, 0.25, 0.125, 0.125]) == pytest.approx(1.0)


def test_router_max_vio_per_layer_and_max():
    layers = [[0.25, 0.25, 0.25, 0.25], [0.4, 0.2, 0.2, 0.2], [0.5, 0.25, 0.125, 0.125]]
    assert router_max_vio_per_layer(layers) == pytest.approx([0.0, 0.6, 1.0])
    assert router_max_vio(layers) == pytest.approx(1.0)
    as_dict = {"layer_3": layers[1], "layer_5": layers[2]}
    assert router_max_vio(as_dict) == pytest.approx(1.0)


def test_router_max_vio_numpy_and_torch():
    assert router_max_vio(np.array([[0.4, 0.2, 0.2, 0.2]])) == pytest.approx(0.6)
    assert router_max_vio(torch.tensor([0.4, 0.2, 0.2, 0.2])) == pytest.approx(0.6)
    assert router_max_vio([torch.tensor([0.4, 0.2, 0.2, 0.2])]) == pytest.approx(0.6)


def test_router_max_vio_bad_input():
    assert router_max_vio([]) is None
    assert math.isnan(router_max_vio([0.0, 0.0]))
    assert math.isnan(router_max_vio([[0.25, 0.75], [float("nan"), 1.0]]))


def test_writer_adds_router_max_vio(path):
    with MetricsWriter(path) as w:
        w.write(1, expert_load=[[0.25, 0.25, 0.25, 0.25], [0.4, 0.2, 0.2, 0.2]])
        w.write(2, loss_ntp=1.0)
    first, second = rows(path)
    assert first["router_max_vio"] == pytest.approx(0.6)
    assert first["expert_load"] == [[0.25, 0.25, 0.25, 0.25], [0.4, 0.2, 0.2, 0.2]]
    assert "router_max_vio" not in second


def test_writer_keeps_explicit_router_max_vio(path):
    with MetricsWriter(path) as w:
        w.write(1, expert_load=[0.4, 0.2, 0.2, 0.2], router_max_vio=0.123)
    assert rows(path)[0]["router_max_vio"] == 0.123


def test_writer_router_max_vio_nan_flushes_at_once(path):
    w = MetricsWriter(path)
    w.write(1, expert_load=[0.0, 0.0])
    assert rows(path)[0]["router_max_vio"] == "nan"
    w.close()


def test_router_max_vio_flat_list_of_numpy_scalars():
    assert router_max_vio([np.float32(0.4), np.float32(0.2), np.float32(0.2), np.float32(0.2)]) == pytest.approx(0.6)
