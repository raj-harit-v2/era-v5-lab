"""SwiGLU (model.activation=swiglu, G6 week-2 Task 0): the dense MLP against an fp64 formula, and its properties.

Formula (Shazeer 2020, "GLU Variants Improve Transformer"; the LLaMA FFN), no biases:

    SwiGLU(x) = W_down @ (SiLU(W_gate @ x) * (W_up @ x)),    SiLU(z) = z * sigmoid(z) = z / (1 + exp(-z))

In the code W_gate = c_gate, W_up = c_fc, W_down = c_proj (models/gpt.py MLP, models/moe.py ExpertMLP).
The reference below is written from that formula in fp64: SiLU by its definition (no F.silu), plain matmuls on the
module's own weights (no nn.Linear call), so a wrong branch, a swapped gate/up, a missing SiLU or a stray bias in
the fast code shows up as an error.

Pairs (outputs, the input gradient and the gradient of all 3 weights):
  mlp.swiglu        gpt.MLP, d=64, h=3*64 (mlp_ratio 3: not a power of 2), x [2, 37, 64], fp32
  mlp.swiglu.bf16   the same under bf16 autocast, TOLERANCES[bfloat16] (bf16 pairs are not in the 1.01 drill:
                    a bf16 tolerance cannot see a 1% error, framework.py: Precision)
The routed and shared experts are paired in test_moe.py (moe.<dispatch>.swiglu, for every dispatch) and the whole
model in test_model.py (model.base.activation_swiglu, .bf16 and .moe). The 1.01 drill runs on every fp32 pair
(test_framework.py).

Weights are drawn with std 0.15, so W_gate @ x has std ~1.2 and SiLU works in its curved region; at the 0.02
training init SiLU(z) ~ z/2 and a reference with the wrong nonlinearity could still pass.

Properties (no pair): GELU modules keep their layout and their init draws (the GELU model is unchanged);
SwiGLU has exactly c_gate, c_fc, c_proj and no biases; loop and sorted dispatch agree and an idle expert gets no
gradient in the loop path; c_gate is trained by Muon like the other block matrices; the parameter count and the
MFU FLOPs count 3 matrices; an unknown activation is refused.
"""
from __future__ import annotations

import math

import pytest
import torch
import torch.nn as nn

from correctness.framework import PAIRS, Case, check, pair, pairs_in, rel_err, to64
from models.config import ModelConfig
from models.gpt import GPT, MLP
from models.moe import ExpertMLP, SparseMoE

D, RATIO, B, T, SEED = 64, 3, 2, 37, 0
WEIGHT_STD = 0.15


# ------------------------------------------------------------------------------ the reference

def ref_silu(z):
    return z / (1.0 + torch.exp(-z))


def ref_swiglu(w_gate, w_up, w_down, x):
    """fp64 SwiGLU from the formula. x [..., d]; w_gate, w_up [h, d]; w_down [d, h]."""
    return (ref_silu(x @ w_gate.T) * (x @ w_up.T)) @ w_down.T


# ------------------------------------------------------------------------------ pairs

def _mlp(device):
    cfg = ModelConfig(n_embd=D, n_head=8, mlp_ratio=RATIO, activation="swiglu")
    m = MLP(cfg, "mlp")
    g = torch.Generator().manual_seed(SEED)
    with torch.no_grad():
        for p in m.parameters():
            p.copy_(torch.randn(p.shape, generator=g) * WEIGHT_STD)
    return m.to(device)


def _x(device):
    g = torch.Generator().manual_seed(SEED + 1)                   # CPU generator: the same x on every device
    return torch.randn(B, T, D, generator=g).to(device).requires_grad_(True)


def _weights(m):
    return [m.c_gate.weight, m.c_fc.weight, m.c_proj.weight]


def _case(device, autocast):
    fast, x = _mlp(device), _x(device)
    ref = to64(fast)

    def fast_fn(i):
        with torch.autocast(device.type, dtype=torch.bfloat16, enabled=autocast):
            return fast(i)

    return Case(ref=lambda i: ref_swiglu(*_weights(ref), i), fast=fast_fn, inputs=[x],
                params_ref=_weights(ref), params_fast=_weights(fast))


pair("mlp.swiglu")(lambda device: _case(device, autocast=False))
pair("mlp.swiglu.bf16", dtype=torch.bfloat16)(lambda device: _case(device, autocast=True))


@pytest.mark.parametrize("name", pairs_in(__name__))
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    assert "out[0]" in errors and "grad_in[0]" in errors, f"{name}: output and input gradient must be compared"
    assert len([k for k in errors if k.startswith("grad_param")]) == 3, f"{name}: all 3 weight gradients"


# ------------------------------------------------------------------------------ properties

def test_gelu_layout_and_init_are_unchanged():
    """The GELU path keeps its two biased Linears, and builds them with the same random draws as before SwiGLU
    existed: a GELU model built from the same seed has the same weights (so week-1 baselines still apply)."""
    torch.manual_seed(SEED)
    gelu = MLP(ModelConfig(n_embd=D, n_head=8, mlp_ratio=RATIO), "mlp")
    assert not hasattr(gelu, "c_gate") and gelu.c_fc.bias is not None and gelu.c_proj.bias is not None
    torch.manual_seed(SEED)
    expected_fc, expected_proj = nn.Linear(D, RATIO * D), nn.Linear(RATIO * D, D)    # the draws MLP makes
    nn.init.normal_(expected_fc.weight, std=0.02)
    torch.testing.assert_close(gelu.c_fc.weight, expected_fc.weight, rtol=0, atol=0)
    e = ExpertMLP(D, 2 * D)
    assert not hasattr(e, "c_gate") and e.c_fc.bias is not None


@pytest.mark.parametrize("module", ["mlp", "expert", "moe"])
def test_swiglu_has_three_matrices_and_no_bias(module):
    if module == "mlp":
        m = MLP(ModelConfig(n_embd=D, n_head=8, mlp_ratio=RATIO, activation="swiglu"), "mlp")
        ffns = [m]
    elif module == "expert":
        ffns = [ExpertMLP(D, 2 * D, activation="swiglu")]
    else:
        moe = SparseMoE(D, 4, 2, expert_hidden=2 * D, num_shared=1, activation="swiglu")
        ffns = list(moe.experts) + list(moe.shared)
    for f in ffns:
        names = sorted(n for n, _ in f.named_parameters())
        assert names == ["c_fc.weight", "c_gate.weight", "c_proj.weight"], names
        h = f.c_gate.weight.shape[0]
        assert f.c_fc.weight.shape == (h, D) and f.c_proj.weight.shape == (D, h)


def test_unknown_activation_is_refused():
    with pytest.raises(AssertionError, match="activation"):
        ModelConfig(activation="relu")
    with pytest.raises(AssertionError, match="activation"):
        ExpertMLP(D, 2 * D, activation="geglu")


def test_loop_and_sorted_dispatch_agree_and_idle_expert_has_no_loop_gradient(device):
    """Both dispatch paths run the same SwiGLU experts. The sorted path packs the gate and up weights into one
    batched matmul, so this compares that packing with the per-expert path directly."""
    torch.manual_seed(SEED)
    loop = SparseMoE(D, 4, 2, expert_hidden=2 * D, num_shared=1, dispatch="loop", activation="swiglu").to(device)
    sorted_ = SparseMoE(D, 4, 2, expert_hidden=2 * D, num_shared=1, dispatch="sorted", activation="swiglu").to(device)
    sorted_.load_state_dict(loop.state_dict())
    with torch.no_grad():
        for m in (loop, sorted_):
            m.router_bias[-1] = -10.0                                 # expert 3 is never chosen
    x = _x(device)
    xs = x.detach().clone().requires_grad_(True)
    y_loop, y_sorted = loop(x), sorted_(xs)
    assert rel_err(y_sorted, y_loop) < 1e-5
    y_loop.square().sum().backward()
    y_sorted.square().sum().backward()
    assert rel_err(xs.grad, x.grad) < 1e-5
    for e in range(3):
        for n in ("c_gate", "c_fc", "c_proj"):
            a = getattr(sorted_.experts[e], n).weight.grad
            b = getattr(loop.experts[e], n).weight.grad
            assert rel_err(a, b) < 1e-5, f"expert {e} {n}"
    assert loop.experts[3].c_gate.weight.grad is None, "the loop path must not run an expert with no tokens"


def test_gate_matrices_are_trained_by_muon():
    from models.optim import build_optimizer
    cfg = ModelConfig(vocab_size=16, block_size=4, n_layer=1, n_head=2, n_embd=8, activation="swiglu",
                      ffn="moe", moe=dict(num_experts=2, top_k=1, num_shared=1))
    model = GPT(cfg)
    opt = build_optimizer(model, dict(name="muon", lr=0.001, muon_lr=0.02, weight_decay=0.01))
    muon = {id(p) for g in dict(opt.named)["opt.muon"].param_groups for p in g["params"]}
    gates = [p for n, p in model.named_parameters() if n.endswith("c_gate.weight")]
    assert len(gates) == 3 and all(id(p) in muon for p in gates)       # 2 routed + 1 shared expert


@pytest.mark.parametrize("ffn", ["mlp", "moe"])
def test_param_count_has_three_ffn_matrices(ffn):
    """N_active (the MFU numerator) from shapes, not from param_counts: 3 * d * h per FFN for SwiGLU."""
    L, d, ratio, V = 2, 16, 3, 32
    kw = dict(vocab_size=V, block_size=8, n_layer=L, n_head=2, n_embd=d, mlp_ratio=ratio, ffn=ffn,
              moe=dict(num_experts=4, top_k=2, num_shared=1))
    h = ratio * d
    attn = d * (d + 2 * d) + d * d                                    # c_attn (n_kv_head = n_head) + c_proj
    ffn_mats = {"gelu": 2 * d * h, "swiglu": 3 * d * h}
    for act, mats in ffn_mats.items():
        model = GPT(ModelConfig(activation=act, **kw))
        per_layer = attn + (mats if ffn == "mlp" else d * 4 + mats * (2 + 1))   # router + (top_k + shared) experts
        assert model.param_counts()[1] == V * d + L * per_layer, act


@pytest.mark.parametrize("ffn", ["mlp", "moe"])
def test_lab_init_scale_is_close_to_gelu(ffn):
    """At the lab init (0.02, residual std on c_proj) a SwiGLU FFN must not be wildly larger or smaller than
    the GELU one; the reversible stack's bf16 reconstruction depends on f being small (test_moe.py)."""
    from models.gpt import _residual_std
    d = 256
    cfg = dict(n_embd=d, n_head=8, n_layer=9)
    torch.manual_seed(SEED)
    x = torch.randn(512, d)
    with torch.no_grad():
        if ffn == "mlp":
            gelu = MLP(ModelConfig(**cfg), "mlp")(x).std()
            swiglu = MLP(ModelConfig(activation="swiglu", **cfg), "mlp")(x).std()
        else:
            ps = _residual_std(ModelConfig(**cfg))
            gelu = SparseMoE(d, 8, 2, expert_hidden=4 * d, num_shared=1, proj_std=ps)(x).std()
            swiglu = SparseMoE(d, 8, 2, expert_hidden=4 * d, num_shared=1, proj_std=ps, activation="swiglu")(x).std()
    ratio = (swiglu / gelu).item()
    assert 0.05 < ratio < 2.0, f"SwiGLU output std is {ratio:.3f}x the GELU one at the lab init"
