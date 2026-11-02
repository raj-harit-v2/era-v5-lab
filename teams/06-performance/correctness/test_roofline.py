"""Tests for the analytical roofline estimates; no device timing is performed here."""
import pytest

from perfkit.roofline import compare_measured, estimate_costs, forward_costs, render_table


def _cfg(**overrides):
    cfg = {
        "vocab_size": 16, "block_size": 4, "n_layer": 1, "n_head": 2,
        "n_kv_head": 1, "n_embd": 8, "mlp_ratio": 2, "embedding": "table",
        "ffn": "mlp", "reversible": False, "ce_impl": "torch",
        "moe": {"num_experts": 2, "top_k": 1, "num_shared": 0, "dispatch": "loop"},
    }
    cfg.update(overrides)
    return cfg


def test_forward_costs_uses_model_shapes_and_named_leaf_regions():
    costs = forward_costs(_cfg(), B=2, T=4, dtype="bf16")
    regions = costs["regions"]
    m, d, h = 8, 8, 16
    assert regions["fwd:block0.attn.qkv"]["flops"] == 2 * m * d * (d + 2 * 4) + m * (d + 2 * 4)
    assert regions["fwd:block0.mlp"]["flops"] == 4 * m * d * h + 8 * m * h
    assert regions["fwd:head+loss"]["flops"] == 2 * m * d * 16 + 8 * m * 16 + 8 * m * d
    assert regions["fwd:block0"]["inclusive"] is True
    assert regions["fwd:stack"]["count_in_total"] is True
    assert costs["totals"]["flops"] == sum(regions[name]["flops"] for name in
                                             ("fwd:embed", "fwd:stack", "fwd:head+loss"))


def test_forward_costs_exposes_moe_ke_and_dtype_bytes():
    moe = _cfg(ffn="moe", moe={"num_experts": 4, "top_k": 2, "num_shared": 1, "dispatch": "sorted"})
    costs = forward_costs(moe, B=2, T=4, dtype="bf16")
    assert "fwd:block0.moe.router" in costs["regions"]
    assert "fwd:block0.moe.dispatch" in costs["regions"]
    assert "fwd:block0.moe.shared" in costs["regions"]
    assert "sorted" in costs["regions"]["fwd:block0.moe.dispatch"]["assumption"]

    ke = _cfg(embedding="ke1", ke_max_pos=4, ke_mode="dynamic")
    bf16 = forward_costs(ke, B=2, T=4, dtype="bf16")
    fp32 = forward_costs(ke, B=2, T=4, dtype="fp32")
    assert bf16["regions"]["fwd:embed.ke"]["flops"] == fp32["regions"]["fwd:embed.ke"]["flops"]
    assert fp32["regions"]["fwd:embed.ke"]["bytes"] > bf16["regions"]["fwd:embed.ke"]["bytes"]


@pytest.mark.parametrize("args", [(0, 4, "bf16"), (1, 0, "bf16"), (1, 4, "int8")])
def test_forward_costs_rejects_invalid_shapes_and_dtypes(args):
    with pytest.raises(ValueError):
        forward_costs(_cfg(), *args)


def test_estimate_costs_reports_separate_compute_bandwidth_and_launch_bounds():
    costs = {
        "dtype": "bf16", "notes": [],
        "regions": {
            "compute_case": {"flops": 1_000_000_000_000, "bytes": 1_000_000_000,
                             "kernels": 1, "count_in_total": True},
            "launch_case": {"flops": 0, "bytes": 0, "kernels": 200, "count_in_total": True},
        },
    }
    result = estimate_costs(costs, "A100", compute_tflops=100, bandwidth_gbs=50, launch_us=5)
    compute = result["regions"]["compute_case"]
    launch = result["regions"]["launch_case"]
    assert compute["compute_ms"] == pytest.approx(10)
    assert compute["bandwidth_ms"] == pytest.approx(20)
    assert compute["bound"] == "bandwidth"
    assert launch["launch_ms"] == pytest.approx(1)
    assert launch["bound"] == "launch"
    assert result["totals"]["predicted_ms"] == pytest.approx(20)


def test_compare_measured_joins_only_matching_forward_regions():
    costs = forward_costs(_cfg(), B=1, T=4, dtype="bf16")
    estimate = estimate_costs(costs, "A100")
    run = {"layer": {"regions": {
        "fwd:block0.attn.qkv": {"median": 0.2, "level": 3},
        "bwd:block0": {"median": 0.5, "level": 2},
    }}}
    rows = compare_measured(estimate, run)
    assert len(rows) == 1
    assert rows[0]["region"] == "fwd:block0.attn.qkv"
    assert rows[0]["measured_ms"] == 0.2
    assert rows[0]["measured_over_predicted"] > 0


def test_render_table_includes_aligned_estimates_and_optional_measurements():
    costs = forward_costs(_cfg(), B=2, T=4, dtype="bf16")
    estimate = estimate_costs(costs, "A100", compute_tflops=100, bandwidth_gbs=1000)
    estimate["measured_regions"] = [{
        "region": "fwd:block0.attn.qkv", "measured_ms": 0.2,
        "measured_over_predicted": 2.5,
    }]
    estimate["measured_run"] = "saved-run.json"

    table = render_table(estimate)
    assert "region" in table and "estimate ms" in table and "meas/est" in table
    assert "fwd:block0.attn.qkv" in table
    assert "0.200" in table and "2.50x" in table
    assert "Total (top-level regions)" in table
    assert "saved-run.json" in table


def test_forward_costs_swiglu_has_three_ffn_matrices():
    """SwiGLU: gate, up and down matmuls (6 * M * d * h) and 3 weight matrices of traffic; GELU stays at 2."""
    B, T = 2, 4
    M, d, h = B * T, 8, 16
    gelu = forward_costs(_cfg(), B=B, T=T, dtype="bf16")["regions"]["fwd:block0.mlp"]
    swiglu = forward_costs(_cfg(activation="swiglu"), B=B, T=T, dtype="bf16")["regions"]["fwd:block0.mlp"]
    assert gelu["flops"] == 4 * M * d * h + 8 * M * h
    assert swiglu["flops"] == 6 * M * d * h + 6 * M * h
    assert swiglu["bytes"] - gelu["bytes"] == d * h * 2 + M * h * 2          # one more bf16 matrix and hidden read
    moe = _cfg(ffn="moe", activation="swiglu", moe={"num_experts": 2, "top_k": 1, "num_shared": 1, "dispatch": "loop"})
    regions = forward_costs(moe, B=B, T=T, dtype="bf16")["regions"]
    assert regions["fwd:block0.moe.shared"]["flops"] == 6 * M * d * h + 6 * M * h
    with pytest.raises(ValueError, match="activation"):
        forward_costs(_cfg(activation="relu"), B=B, T=T, dtype="bf16")
