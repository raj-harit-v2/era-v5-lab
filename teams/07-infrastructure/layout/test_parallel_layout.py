"""Parallel layout v0 (docs/parallel_layout_v0.md) and its calculator, layout/parallel_layout.py. CPU only.

    cd teams/07-infrastructure && python -m pytest layout/test_parallel_layout.py -q

The parameter formula is checked against Team 6's real model (teams/06-performance/models/gpt.py) when that
folder and torch are present; the memory formula against a real AdamW state on CPU.
"""
import math
import os
import sys
from dataclasses import replace

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TEAMS = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import parallel_layout as pl  # noqa: E402

TEAM6 = os.path.join(TEAMS, "06-performance")
MOE = pl.Shape(vocab=512, seq=32, layers=4, d=64, n_head=8, n_kv=2, mlp_ratio=2, ffn="moe", n_exp=8, top_k=2,
               n_shared=1, embedding="table")
DENSE = replace(MOE, ffn="mlp", n_exp=0, top_k=0, n_shared=0)


def team6_gpt(shape):
    torch = pytest.importorskip("torch")
    if not os.path.isdir(TEAM6):
        pytest.skip("teams/06-performance is not in this checkout")
    sys.path.insert(0, TEAM6)
    try:
        from models.config import ModelConfig
        from models.gpt import GPT
    except Exception as e:                       # Team 6 code changed or needs a package we do not have
        pytest.skip(f"Team 6 model does not import: {e}")
    finally:
        sys.path.remove(TEAM6)
    cfg = ModelConfig(vocab_size=shape.vocab, block_size=shape.seq, n_layer=shape.layers, n_head=shape.n_head,
                      n_kv_head=shape.n_kv, n_embd=shape.d, mlp_ratio=shape.mlp_ratio, embedding=shape.embedding,
                      ke_max_pos=shape.ke_max_pos, ffn=shape.ffn, reversible=False, mtp=shape.mtp,
                      moe=dict(num_experts=max(shape.n_exp, 1), top_k=max(shape.top_k, 1),
                               num_shared=shape.n_shared, bias_gamma=0.01, dispatch="loop"))
    token_bytes = None
    if shape.embedding in ("ke1", "ke2"):
        g = torch.Generator().manual_seed(0)
        tb = torch.randint(0, 256, (shape.vocab, shape.ke_max_pos), generator=g, dtype=torch.uint8)
        token_bytes = (tb, torch.randint(1, shape.ke_max_pos + 1, (shape.vocab,), generator=g))
    torch.manual_seed(0)
    try:
        return GPT(cfg, token_bytes=token_bytes)
    except RuntimeError as e:                    # e.g. ke2 needs a torch built for this NumPy
        pytest.skip(f"Team 6 model does not build here: {e}")


# ---- A. parameter counts
@pytest.mark.parametrize("shape", [
    MOE, DENSE, replace(MOE, mtp=True), replace(MOE, n_kv=8), replace(MOE, embedding="ke2", ke_max_pos=4),
    replace(DENSE, embedding="ke1", ke_max_pos=4, mtp=True), replace(MOE, n_shared=0),
], ids=["moe", "dense", "mtp", "mha", "ke2", "ke1-mtp", "no-shared"])
def test_param_formula_equals_team6_model(shape):
    model = team6_gpt(shape)
    pc = pl.param_counts(shape)
    total, active = model.param_counts()
    assert pc["total"] == total
    assert pc["active_matmul"] == active
    routed = sum(p.numel() for n, p in model.named_parameters() if ".ffn.experts." in n)
    assert pc["routed_experts"] == routed


def test_routed_experts_are_the_only_expert_parallel_part():
    pc = pl.param_counts(MOE)
    assert pc["total"] == MOE.layers * (pc["dense_layer"] + pc["expert_layer"]) + pc["embed"] + pc["head"]
    assert pl.param_counts(DENSE)["expert_layer"] == 0


# ---- B. memory per device: model states
def one_layer_states(shape, **lay):
    """Model-state bytes for a shape with only dense, no embedding: compare with the ZeRO paper ratios."""
    lay = pl.Layout(**lay)
    m = pl.memory(shape, lay)
    return m["weights"] + m["grads"] + m["optimizer"], pl.param_counts(shape)["total"]


@pytest.mark.parametrize("zero,want", [(0, lambda n: 16), (1, lambda n: 4 + 12 / n), (2, lambda n: 2 + 14 / n),
                                       (3, lambda n: 16 / n)])
def test_zero_stages_match_the_zero_paper(zero, want):
    """Rajbhandari et al. 2020, fig. 1: bf16 weights and grads + fp32 master/momentum/variance = 2+2+12 bytes."""
    for n in (1, 2, 8, 64):
        got, psi = one_layer_states(MOE, dp=n, zero=zero, precision="bf16")
        assert got == pytest.approx(want(n) * psi)


def test_amp_keeps_fp32_weights_and_grads():
    got, psi = one_layer_states(MOE, precision="amp")
    assert got == pytest.approx((4 + 4 + 8) * psi)


def test_tensor_parallel_divides_dense_and_expert_parallel_divides_experts():
    pc = pl.param_counts(MOE)
    base = pl.memory(MOE, pl.Layout())["params"]
    assert pl.memory(MOE, pl.Layout(tp=2))["params"] == pytest.approx(
        (MOE.layers * pc["dense_layer"] + pc["embed"] + pc["head"]) / 2 + MOE.layers * pc["expert_layer"])
    assert pl.memory(MOE, pl.Layout(dp=4, ep=4))["params"] == pytest.approx(
        base - MOE.layers * pc["expert_layer"] * 3 / 4)


def test_pipeline_puts_the_embedding_and_the_head_on_different_stages():
    pc = pl.param_counts(MOE)
    m = pl.memory(MOE, pl.Layout(pp=2, m=4))
    layers = (pc["dense_layer"] + pc["expert_layer"]) * MOE.layers / 2
    assert m["params"] == pytest.approx(layers + max(pc["embed"], pc["head"]))


def test_adamw_state_on_cpu_is_eight_bytes_per_parameter():
    """The `opt_bytes=8` default is what torch.optim.AdamW really keeps (exp_avg and exp_avg_sq, fp32)."""
    torch = pytest.importorskip("torch")
    model = torch.nn.Sequential(torch.nn.Linear(64, 128), torch.nn.GELU(), torch.nn.Linear(128, 64))
    opt = torch.optim.AdamW(model.parameters())
    model(torch.randn(4, 64)).sum().backward()
    opt.step()
    n = sum(p.numel() for p in model.parameters())
    moments = sum(st[k].numel() * st[k].element_size() for st in opt.state.values() for k in ("exp_avg", "exp_avg_sq"))
    assert moments == pl.Layout().opt_bytes * n


# ---- C. activations
def test_activation_formula_is_korthikanti_eq_2_and_4():
    """Without parallelism: s*b*h*(34 + 5*a*s/h) bytes per layer; with t-way TP + SP everything divides by t."""
    s = replace(DENSE, seq=2048, d=1024, n_head=16, n_kv=16)
    a = pl.activation_bytes_per_layer(s, pl.Layout(b=2))
    assert a == pytest.approx(2048 * 2 * 1024 * (34 + 5 * 16 * 2048 / 1024))
    assert pl.activation_bytes_per_layer(s, pl.Layout(b=2, tp=4)) == pytest.approx(a / 4)
    assert pl.activation_bytes_per_layer(s, pl.Layout(b=2, recompute="selective")) == pytest.approx(34 * 2048 * 2 * 1024)
    assert pl.activation_bytes_per_layer(s, pl.Layout(b=2, recompute="full")) == pytest.approx(2 * 2048 * 2 * 1024)


def test_context_parallel_splits_the_sequence():
    s = replace(DENSE, seq=1024)
    full = pl.activation_bytes_per_layer(s, pl.Layout())
    half = pl.activation_bytes_per_layer(s, pl.Layout(cp=2))
    assert half < full / 2 + 1e-6                     # the s^2 attention term falls by 4


def test_first_pipeline_stage_holds_pp_micro_batches():
    """1F1B: the first stage keeps pp micro-batches in flight, so its activations equal one full model's."""
    one = pl.activation_bytes_per_layer(MOE, pl.Layout())
    first, last = pl.memory_stages(replace(MOE, layers=8), pl.Layout(pp=4, m=8))
    assert first["stage"] == "first" and first["activations"] == pytest.approx(2 * 4 * one)   # 8/4 layers x 4
    assert last["activations"] == pytest.approx(2 * one) and last["logits"] > 0 == first["logits"]


# ---- D. traffic per device per step
def test_zero_1_and_2_send_what_ddp_sends_and_zero_3_one_and_a_half_times():
    """ZeRO paper section 7: ZeRO-1/2 = DDP volume; ZeRO-3 = 1.5x (with weights and grads of the same size)."""
    ddp = pl.traffic(MOE, pl.Layout(dp=8, precision="bf16"))["dp"]
    assert pl.traffic(MOE, pl.Layout(dp=8, zero=1, precision="bf16"))["dp"] == pytest.approx(ddp)
    assert pl.traffic(MOE, pl.Layout(dp=8, zero=2, precision="bf16"))["dp"] == pytest.approx(ddp)
    assert pl.traffic(MOE, pl.Layout(dp=8, zero=3, precision="bf16"))["dp"] == pytest.approx(1.5 * ddp)


def test_ddp_all_reduce_volume():
    psi = pl.param_counts(MOE)["total"]
    assert pl.traffic(MOE, pl.Layout(dp=4))["dp"] == pytest.approx(2 * 3 / 4 * 4 * psi)   # fp32 grads under amp
    assert pl.traffic(MOE, pl.Layout(dp=1))["dp"] == 0


def test_tensor_parallel_traffic_is_four_all_reduces_per_layer():
    t = pl.traffic(MOE, pl.Layout(tp=2, b=2, m=3))
    msg = 2 * MOE.seq * MOE.d * 2
    assert t["tp"] == pytest.approx(3 * MOE.layers * 4 * 2 * 0.5 * msg)


def test_expert_parallel_traffic_is_four_all_to_alls_per_moe_layer():
    t = pl.traffic(MOE, pl.Layout(dp=4, ep=4, b=2))
    assert t["ep"] == pytest.approx(MOE.layers * 4 * 0.75 * 2 * MOE.seq * MOE.top_k * MOE.d * 2)


def test_pipeline_bubble():
    assert pl.traffic(MOE, pl.Layout(pp=4, m=12))["bubble"] == pytest.approx(3 / 12)
    assert pl.traffic(MOE, pl.Layout(pp=1, m=12))["bubble"] == 0


# ---- E. layout checks and the config loaders
@pytest.mark.parametrize("lay,word", [
    (pl.Layout(tp=3), "n_head"), (pl.Layout(tp=4), "n_kv"), (pl.Layout(pp=8, m=8), "layers"),
    (pl.Layout(dp=3, ep=3), "experts"), (pl.Layout(dp=2, ep=4), "dp x cp"), (pl.Layout(cp=5), "sequence"),
    (pl.Layout(pp=2, m=1), "never fills"), (pl.Layout(dp=4, zero=2, shard=2), "HSDP"),
])
def test_bad_layouts_are_refused(lay, word):
    assert any(word in p for p in pl.layout_problems(MOE, lay)), pl.layout_problems(MOE, lay)


def test_world_must_match():
    assert pl.layout_problems(MOE, pl.Layout(dp=2, tp=2), world=8)
    assert not pl.layout_problems(MOE, pl.Layout(dp=2, tp=2, pp=2, m=4), world=8)


def test_standard_layouts_are_all_valid():
    for lay in pl.standard_layouts(MOE, 8, pl.Layout(b=2)):
        assert not pl.layout_problems(MOE, lay, 8)


def test_team6_config_with_inherit(tmp_path):
    (tmp_path / "base.yaml").write_text("model:\n  vocab_size: 512\n  block_size: 32\n  n_layer: 4\n  n_head: 8\n"
                                        "  n_kv_head: null\n  n_embd: 64\n  mlp_ratio: 2\n  embedding: table\n"
                                        "  ffn: mlp\n  moe: {num_experts: 8, top_k: 2, num_shared: 1}\n")
    (tmp_path / "arm.yaml").write_text("inherit: base.yaml\nmodel:\n  n_kv_head: 2\n  ffn: moe\n")
    assert pl.load_shape(str(tmp_path / "arm.yaml")) == replace(MOE, source=str(tmp_path / "arm.yaml"))
    dense = pl.load_shape(str(tmp_path / "base.yaml"))
    assert dense.ffn == "mlp" and dense.n_kv == 8
    assert pl.param_counts(dense) == pl.param_counts(replace(DENSE, n_kv=8))      # moe: ignored when ffn is mlp


def test_team5_settings_with_open_sizes_are_refused_not_guessed(tmp_path):
    p = tmp_path / "config_v0.yaml"
    p.write_text("settings:\n  - key: model.n_layer\n    value: null\n    open: true\n    source: x\n"
                 "  - key: tokenizer.vocab_size\n    value: 512\n    source: x\n")
    with pytest.raises(SystemExit, match="no value for"):
        pl.load_shape(str(p))
    sets = dict(seq=32, layers=4, d=64, n_head=8, n_kv=2, mlp_ratio=2, ffn="moe", n_exp=8, top_k=2, n_shared=1)
    assert pl.load_shape(str(p), sets) == replace(MOE, source=str(p))


def test_real_team6_configs_load_when_present():
    for rel in ("06-performance/configs/base.yaml", "06-performance/configs/tiny_cpu.yaml",
                "05-architecture/configs/arms/t1.yaml"):
        path = os.path.join(TEAMS, rel)
        if os.path.exists(path):
            s = pl.load_shape(path)
            assert not s.problems() and pl.param_counts(s)["total"] > 0


def test_command_line(tmp_path, capsys):
    cfg = os.path.join(TEAM6, "configs", "tiny_cpu.yaml")
    if not os.path.exists(cfg):
        pytest.skip("teams/06-performance is not in this checkout")
    assert pl.main(["--config", cfg, "--world", "2", "--markdown", "--unit", "MiB"]) == 0
    out = capsys.readouterr().out
    assert "| dp=2,zero=3 |" in out and "estimates, not measured" in out
    assert pl.main(["--config", cfg, "--layout", "tp=3"]) == 1
