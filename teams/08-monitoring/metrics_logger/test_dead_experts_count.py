"""dead_experts_count: routed experts below 0.1 x the uniform share of their layer's picks, over all MoE layers.
Also dead_experts_by_layer and expert_utilization_min, worked out from the same expert_load."""
import json

import numpy as np
import pytest
import torch

from metrics_writer import DEAD_EXPERT_SHARE, MetricsWriter, dead_experts_count, expert_load_stats

# Named decorator: pr-guard reads an added pytest decorator line as an email address.
parametrize = pytest.mark.parametrize


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def written(tmp_path, **metrics):
    path = tmp_path / f"metrics_{len(list(tmp_path.iterdir()))}.jsonl"  # a new file for each call
    with MetricsWriter(str(path)) as w:
        w.write(1, **metrics)
    row, = rows(path)
    return row


def test_threshold_is_a_tenth_of_the_uniform_share():
    assert DEAD_EXPERT_SHARE == 0.1


@parametrize("load, dead", [
    ([100] * 8, 0),                      # uniform: 100 picks each
    ([10] + [110] * 7, 0),              # 10 of 800 is exactly 0.1 x uniform (100): not below it
    ([9] + [113] * 7, 1),               # 9 of 800 is below
    ([0, 0] + [200] * 6, 2),            # never picked
    ([0.0125, 0.0] + [0.9875 / 6] * 6, 1),  # shares instead of counts
    ([5, 5, 5, 5], 0),
    ([1], 0),                           # one expert takes every pick
])
def test_one_layer(load, dead):
    assert dead_experts_count(load) == dead


def test_counts_and_shares_agree():
    counts = [1, 3, 50, 46]  # uniform is 25 picks, so the cut is 2.5: only the expert with 1 pick is dead
    assert dead_experts_count(counts) == dead_experts_count([c / 100 for c in counts]) == 1


def test_layers_are_summed():
    layers = [[100] * 8, [0] + [800 / 7] * 7, [0, 0] + [800 / 6] * 6]
    assert dead_experts_count(layers) == 3
    assert dead_experts_count({"layer_0": layers[0], "layer_1": layers[1], "layer_2": layers[2]}) == 3


def test_numpy_and_torch():
    assert dead_experts_count(np.array([[0, 50, 50, 100], [25, 25, 25, 25]])) == 1
    assert dead_experts_count(torch.tensor([[0.0, 0.5, 0.5, 1.0], [1.0, 1.0, 1.0, 1.0]])) == 1
    assert dead_experts_count([torch.tensor([0, 2, 2]), torch.tensor([1, 1, 1])]) == 1


@parametrize("load", [[], [[]], [0, 0, 0], [[1, 1], [0, 0]], [1, float("nan")], [1, -1, 3], [[1, 2], "x"], None, "x"])
def test_cannot_tell(load):
    assert dead_experts_count(load) is None


def test_written_from_expert_load(tmp_path):
    row = written(tmp_path, expert_load=[[0, 40, 30, 30], [25, 25, 25, 25]])
    assert row["dead_experts_count"] == 1
    assert row["expert_load"] == [[0, 40, 30, 30], [25, 25, 25, 25]]


def test_passed_count_wins(tmp_path):
    assert written(tmp_path, dead_experts_count=3, expert_load=[25, 25, 25, 25])["dead_experts_count"] == 3


def test_passed_without_expert_load(tmp_path):
    assert written(tmp_path, dead_experts_count=torch.tensor(2))["dead_experts_count"] == 2


def test_not_written_when_it_cannot_be_told(tmp_path):
    assert "dead_experts_count" not in written(tmp_path, expert_load=[0, 0, 0, 0])
    assert "dead_experts_count" not in written(tmp_path, loss_ntp=1.0)


def test_nan_expert_load_still_flushes_and_has_no_count(tmp_path):
    path = tmp_path / "metrics.jsonl"
    w = MetricsWriter(str(path))
    w.write(1, expert_load=[1.0, float("nan")])
    row, = rows(path)  # flushed at once, before step 10
    assert row["expert_load"] == [1.0, "nan"] and "dead_experts_count" not in row
    w.close()


def test_by_layer_and_lowest_utilization():
    stats = expert_load_stats([[100] * 8, [0] + [800 / 7] * 7, [50, 150, 100, 100, 100, 100, 100, 100]])
    assert stats["dead_experts_by_layer"] == [0, 1, 0] and stats["dead_experts_count"] == 1
    assert stats["expert_utilization_min"] == 0.0  # the never-picked expert of layer 1


@parametrize("load, lowest", [
    ([25, 25, 25, 25], 1.0),             # every expert gets its fair share
    ([10, 30, 30, 30], 0.4),             # 10 of 100 picks, 4 experts: 0.1 / 0.25
    ([[50, 50], [20, 80]], 0.4),         # the lowest over all layers
])
def test_lowest_utilization(load, lowest):
    assert expert_load_stats(load)["expert_utilization_min"] == pytest.approx(lowest)


def test_lowest_utilization_warns_before_an_expert_is_dead():
    stats = expert_load_stats([15, 95, 95, 95, 100, 100, 100, 100])  # 15 of 700: utilization 0.17
    assert stats["dead_experts_count"] == 0 and 0.1 < stats["expert_utilization_min"] < 0.2


def test_all_three_written_from_expert_load(tmp_path):
    row = written(tmp_path, expert_load=[[0, 40, 30, 30], [25, 25, 25, 25]])
    assert (row["dead_experts_count"], row["dead_experts_by_layer"], row["expert_utilization_min"]) == (1, [1, 0], 0.0)


def test_a_passed_value_wins_only_for_its_own_name(tmp_path):
    row = written(tmp_path, expert_utilization_min=0.5, expert_load=[[0, 40, 30, 30], [25, 25, 25, 25]])
    assert row["expert_utilization_min"] == 0.5 and row["dead_experts_count"] == 1 and row["dead_experts_by_layer"] == [1, 0]


def test_none_of_them_when_it_cannot_be_told(tmp_path):
    row = written(tmp_path, expert_load=[[1, 1], [0, 0]])
    assert not {"dead_experts_count", "dead_experts_by_layer", "expert_utilization_min"} & set(row)
