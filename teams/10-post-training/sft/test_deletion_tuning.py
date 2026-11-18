"""Tests for the Deletion Tuning port and the equal-step comparison.

    python -m pytest teams/10-post-training/sft/test_deletion_tuning.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dt = _load("g10_deletion_tuning_under_test", "deletion_tuning.py")
compare_mod = _load("g10_dt_vs_fft_under_test", "dt_vs_fft.py")


def test_sharpness_ramps_from_1e3_to_1e4():
    assert dt.sharpness(0, 100) == 1e3
    assert dt.sharpness(100, 100) == 1e4
    assert dt.sharpness(50, 100) == 5.5e3


def test_soft_mask_is_one_half_at_zero_and_hard_mask_drops_zero():
    assert dt.soft_mask([0.0], 1e3) == [0.5]
    assert dt.hard_keep([0.03, 0.0, -0.03]) == [True, False, False]


def test_masked_weight_leaves_the_frozen_copy_unchanged():
    weight = [[1.0, -2.0]]
    masked = dt.apply_mask(weight, [1.0, 0.0])
    assert masked == [[1.0, 0.0]]
    assert weight == [[1.0, -2.0]]


def test_deletion_loss_subtracts_the_weight_penalty():
    masked = [[3.0, 4.0]]
    assert dt.deletion_loss(1.0, masked, lam=1e-5) == 1.0 - 1e-5 * 25.0


def test_three_methods_take_equal_steps_and_only_fft_changes_the_base():
    report = compare_mod.compare(steps=5, seed=0)
    methods = report["methods"]
    assert [methods[name]["steps"] for name in ("dt", "lora", "fft")] == [5, 5, 5]
    assert methods["dt"]["base_changed"] is False
    assert methods["lora"]["base_changed"] is False
    assert methods["fft"]["base_changed"] is True
    assert methods["fft"]["loss_end"] < methods["fft"]["loss_start"]


def test_sweep_covers_all_three_layer_targets_and_deletion_fractions():
    report = compare_mod.compare_sweep(steps=2, seed=0)
    assert report["layer_targets"] == ["mlp_gate", "all_mlp", "attention"]
    assert report["deletion_fractions"] == [0.20, 0.50, 0.80]
    # 3 layers x (1 FFT + 1 LoRA + 3 DT) = 15 records
    assert len(report["records"]) == 15
    for r in report["records"]:
        if r["method"] == "dt":
            assert r["base_changed"] is False
            assert r["forgetting"] == 0.0
            assert 0.0 < r["deleted_fraction"] < 1.0
        elif r["method"] == "lora":
            assert r["base_changed"] is False
        elif r["method"] == "fft":
            assert r["base_changed"] is True

