"""P0-2: positions/s, scored tokens/s, bytes/s (hand-made batch + compute_metrics guard)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from models.config import ModelConfig
from models.gpt import GPT
from perfkit.bench import compute_metrics, throughput_rates


def test_throughput_rates_on_handmade_masked_batch():
    # 16 positions, 10 scored (mask), 25 scored bytes, 10 ms step -> 1600 / 1000 / 2500 per second
    out = throughput_rates(10.0, positions_per_step=16, scored_tokens_per_step=10, scored_bytes_per_step=25)
    assert out["positions_per_s"] == pytest.approx(1600.0)
    assert out["scored_tokens_per_s"] == pytest.approx(1000.0)
    assert out["bytes_per_s"] == pytest.approx(2500.0)


def test_throughput_rates_rejects_non_positive_step_ms():
    with pytest.raises(ValueError, match="step_ms"):
        throughput_rates(0.0, positions_per_step=8, scored_tokens_per_step=8, scored_bytes_per_step=8)


def test_compute_metrics_keeps_tokens_per_s_and_adds_three_rates():
    # No mask: positions == scored; bytes from explicit scored_bytes_per_step
    core = GPT(ModelConfig(n_layer=1, n_embd=32, n_head=2, block_size=8, vocab_size=64,
                           embedding="table", reversible=False))
    s = SimpleNamespace(core=core, loader=SimpleNamespace(B=2, T=4), opt=SimpleNamespace(flops=lambda: 0.0))
    out = compute_metrics(s, 10.0, 312.0, scored_bytes_per_step=40)
    assert out["tokens_per_s"] == pytest.approx(800.0)          # old key unchanged (B*T / 0.01 s)
    assert out["tokens_per_step"] == 8
    assert out["positions_per_s"] == pytest.approx(800.0)
    assert out["scored_tokens_per_s"] == pytest.approx(800.0)   # synthetic / no mask
    assert out["bytes_per_s"] == pytest.approx(4000.0)          # 40 bytes / 0.01 s


def test_compute_metrics_scored_tokens_can_be_below_positions():
    core = GPT(ModelConfig(n_layer=1, n_embd=32, n_head=2, block_size=8, vocab_size=64,
                           embedding="table", reversible=False))
    s = SimpleNamespace(core=core, loader=SimpleNamespace(B=2, T=4), opt=SimpleNamespace(flops=lambda: 0.0))
    out = compute_metrics(s, 10.0, None, scored_tokens_per_step=5, scored_bytes_per_step=15)
    assert out["tokens_per_s"] == pytest.approx(800.0)          # still positions-based
    assert out["positions_per_s"] == pytest.approx(800.0)
    assert out["scored_tokens_per_s"] == pytest.approx(500.0)
    assert out["bytes_per_s"] == pytest.approx(1500.0)
