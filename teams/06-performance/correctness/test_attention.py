"""Attention: models.gpt.GQAttention against a naive fp64 attention.

Reference (written from the definition, never by calling the fast code): from the module's c_attn / c_proj weights,
q, k, v (GQA: k, v have n_kv_head heads; query head h uses kv head h // (n_head / n_kv_head)) ->
softmax(q k^T / sqrt(d_head) + causal mask) v -> c_proj. One loop iteration per query head, an explicit mask and
an explicit softmax: no F.scaled_dot_product_attention and no repeat_interleave.
RoPE (model.position = rope) in the reference: ref_rope rotates each query and key head pair by pair, from the
formula: pair i = (x[i], x[i + hd/2]), angle t * theta^(-2i / hd) with the angle of each pair from Python floats
(no models.gpt.rope_tables, no apply_rope).

Pairs (fast fp32 vs reference fp64; outputs, the input gradient and all parameter gradients):
  attention.causal              n_kv_head = n_head / 2, SDPA enable_gqa path
  attention.causal.mha          n_kv_head = n_head      (plain multi-head)
  attention.causal.mqa          n_kv_head = 1, SDPA enable_gqa path
  attention.causal.lab          n_kv_head = n_head / 4 (lab_small: 8 query heads share 2 kv heads), SDPA enable_gqa
  attention.causal.fallback     n_kv_head = n_head / 2, repeat_interleave path (models.gpt._SDPA_GQA = False)
  attention.causal.mqa_fallback n_kv_head = 1, repeat_interleave path
  attention.causal.lab_fallback n_kv_head = n_head / 4, repeat_interleave path
  attention.causal.eager        n_kv_head = n_head / 2, attn_impl = eager (explicit softmax, G5 config_v0)
  attention.causal.eager_mha    n_kv_head = n_head,     eager
  attention.causal.eager_mqa    n_kv_head = 1,          eager
  attention.causal.eager_lab    n_kv_head = n_head / 4, eager
  attention.causal.eager_bf16   n_kv_head = n_head / 2, eager under bf16 autocast (TOLERANCES[bfloat16])
  attention.rope                position = rope, theta 10000, n_kv_head = n_head / 2, SDPA enable_gqa path
  attention.rope.mha / .mqa     position = rope, n_kv_head = n_head / 1, SDPA
  attention.rope.fallback       position = rope, n_kv_head = n_head / 2, repeat_interleave path
  attention.rope.eager          position = rope, n_kv_head = n_head / 2, eager
  attention.rope.theta500       position = rope, theta 500: the angles wrap many times within T = 37
  attention.rope.bf16           position = rope, SDPA under bf16 autocast (TOLERANCES[bfloat16])
T = 37 is not a power of 2. Weights and biases are random and large enough that the softmax is not uniform, so
the bias terms and the mask matter.

The 1.01 drill for every pair runs in test_framework.py (test_every_registered_pair_scaled_fails).

Property tests (no pair): causality on every code path (a change in the future leaves the past unchanged),
the two GQA code paths agree with each other, and eager agrees with SDPA. RoPE: the scores depend only on the
relative position (a query and key shifted together give the same score), the rotation keeps every pair's norm,
and position 0 is not rotated.

The gradient of the k part of c_attn.bias is exactly 0: adding q . b_k to every score of a query shifts its
softmax row by a constant. That is why errors are taken over whole tensors; a k-bias-only error would be 0 / 0.
"""
from __future__ import annotations

import math

import pytest
import torch

import models.gpt as gpt
from correctness.framework import PAIRS, Case, check, pair, pairs_in, rel_err, to64
from models.config import ModelConfig
from models.gpt import GQAttention


N_HEAD, N_EMBD, B, T = 8, 64, 2, 37
WEIGHT_STD, BIAS_STD = 0.15, 0.1


def ref_rope(x, theta):
    """RoPE from the formula. x: [..., T, hd] fp64. Pair i = (x[i], x[i + hd/2]) turns by t * theta^(-2i / hd)."""
    Tn, hd = x.shape[-2], x.shape[-1]
    half = hd // 2
    t = torch.arange(Tn, dtype=torch.float64, device=x.device).unsqueeze(-1)
    out = torch.empty_like(x)
    for i in range(half):
        ang = t * (theta ** (-2.0 * i / hd))                 # [T, 1]
        a, b = x[..., i:i + 1], x[..., half + i:half + i + 1]
        out[..., i:i + 1] = a * torch.cos(ang) - b * torch.sin(ang)
        out[..., half + i:half + i + 1] = b * torch.cos(ang) + a * torch.sin(ang)
    return out


def naive_attention(x, w_attn, b_attn, w_proj, b_proj, n_head, n_kv_head, rope_theta=None):
    """Reference attention from the definition. x: [B, T, C]; all tensors fp64. rope_theta: None = no RoPE."""
    Bsz, Tn, C = x.shape
    hd = C // n_head
    group = n_head // n_kv_head
    qkv = x @ w_attn.T + b_attn
    q = qkv[..., :C]
    k = qkv[..., C:C + n_kv_head * hd]
    v = qkv[..., C + n_kv_head * hd:]
    future = torch.triu(torch.ones(Tn, Tn, dtype=torch.bool, device=x.device), diagonal=1)
    heads = []
    for h in range(n_head):
        g = h // group                                   # the kv head this query head reads
        qh, kh, vh = q[..., h * hd:(h + 1) * hd], k[..., g * hd:(g + 1) * hd], v[..., g * hd:(g + 1) * hd]
        if rope_theta is not None:
            qh, kh = ref_rope(qh, rope_theta), ref_rope(kh, rope_theta)
        scores = (qh @ kh.transpose(-1, -2)) / math.sqrt(hd)
        scores = scores.masked_fill(future, float("-inf"))
        heads.append(torch.softmax(scores, dim=-1) @ vh)
    return torch.cat(heads, dim=-1) @ w_proj.T + b_proj


def _module(n_kv_head, seed=0, attn_impl="sdpa", rope_theta=None):
    pos = dict(position="rope", rope_theta=rope_theta) if rope_theta is not None else {}
    cfg = ModelConfig(n_head=N_HEAD, n_kv_head=n_kv_head, n_embd=N_EMBD, attn_impl=attn_impl, **pos)
    mod = GQAttention(cfg, "attn")
    g = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        for name, p in mod.named_parameters():
            p.copy_(torch.randn(p.shape, generator=g) * (WEIGHT_STD if name.endswith("weight") else BIAS_STD))
    return mod


def _with_sdpa_gqa(flag, fn):
    """Run fn() with models.gpt._SDPA_GQA forced to flag (restored afterwards)."""
    old = gpt._SDPA_GQA
    gpt._SDPA_GQA = flag
    try:
        return fn()
    finally:
        gpt._SDPA_GQA = old


def _register(name, n_kv_head, sdpa_gqa, attn_impl="sdpa", rope_theta=None):
    @pair(name, tol=1e-5, grad_tol=1e-4)
    def build(device):
        if attn_impl == "sdpa" and sdpa_gqa and n_kv_head != N_HEAD and not gpt._SDPA_GQA:
            pytest.skip("SDPA enable_gqa needs torch >= 2.5")
        fast_mod = _module(n_kv_head, attn_impl=attn_impl, rope_theta=rope_theta).to(device)
        ref_mod = to64(fast_mod)
        x = torch.randn(B, T, N_EMBD, device=device,
                        generator=torch.Generator(device=device).manual_seed(1)).requires_grad_(True)

        def fast(inp):
            return _with_sdpa_gqa(sdpa_gqa, lambda: fast_mod(inp))

        def ref(inp):
            return naive_attention(inp, ref_mod.c_attn.weight, ref_mod.c_attn.bias,
                                   ref_mod.c_proj.weight, ref_mod.c_proj.bias, N_HEAD, n_kv_head, rope_theta)

        params = lambda m: [m.c_attn.weight, m.c_attn.bias, m.c_proj.weight, m.c_proj.bias]
        return Case(ref=ref, fast=fast, inputs=[x], params_ref=params(ref_mod), params_fast=params(fast_mod))
    return build


_register("attention.causal", N_HEAD // 2, sdpa_gqa=True)
_register("attention.causal.mha", N_HEAD, sdpa_gqa=True)
_register("attention.causal.mqa", 1, sdpa_gqa=True)
_register("attention.causal.lab", N_HEAD // 4, sdpa_gqa=True)
_register("attention.causal.fallback", N_HEAD // 2, sdpa_gqa=False)
_register("attention.causal.mqa_fallback", 1, sdpa_gqa=False)
_register("attention.causal.lab_fallback", N_HEAD // 4, sdpa_gqa=False)
_register("attention.causal.eager", N_HEAD // 2, sdpa_gqa=False, attn_impl="eager")
_register("attention.causal.eager_mha", N_HEAD, sdpa_gqa=False, attn_impl="eager")
_register("attention.causal.eager_mqa", 1, sdpa_gqa=False, attn_impl="eager")
_register("attention.causal.eager_lab", N_HEAD // 4, sdpa_gqa=False, attn_impl="eager")
_register("attention.rope", N_HEAD // 2, sdpa_gqa=True, rope_theta=10000.0)
_register("attention.rope.mha", N_HEAD, sdpa_gqa=True, rope_theta=10000.0)
_register("attention.rope.mqa", 1, sdpa_gqa=True, rope_theta=10000.0)
_register("attention.rope.fallback", N_HEAD // 2, sdpa_gqa=False, rope_theta=10000.0)
_register("attention.rope.eager", N_HEAD // 2, sdpa_gqa=False, attn_impl="eager", rope_theta=10000.0)
_register("attention.rope.theta500", N_HEAD // 2, sdpa_gqa=True, rope_theta=500.0)


def _bf16_build(attn_impl, rope_theta=None):
    def build(device):
        return _bf16_case(device, attn_impl, rope_theta)
    return build


def _bf16_case(device, attn_impl="sdpa", rope_theta=None):
    fast_mod = _module(N_HEAD // 2, attn_impl=attn_impl, rope_theta=rope_theta).to(device)
    ref_mod = to64(fast_mod)
    x = torch.randn(B, T, N_EMBD, device=device,
                    generator=torch.Generator(device=device).manual_seed(1)).requires_grad_(True)

    def fast(inp):
        with torch.autocast(device.type, dtype=torch.bfloat16):
            return fast_mod(inp)

    def ref(inp):
        return naive_attention(inp, ref_mod.c_attn.weight, ref_mod.c_attn.bias,
                               ref_mod.c_proj.weight, ref_mod.c_proj.bias, N_HEAD, N_HEAD // 2, rope_theta)

    params = lambda m: [m.c_attn.weight, m.c_attn.bias, m.c_proj.weight, m.c_proj.bias]
    return Case(ref=ref, fast=fast, inputs=[x], params_ref=params(ref_mod), params_fast=params(fast_mod))


pair("attention.causal.bf16", dtype=torch.bfloat16)(_bf16_build("sdpa"))
pair("attention.causal.eager_bf16", dtype=torch.bfloat16)(_bf16_build("eager"))
pair("attention.rope.bf16", dtype=torch.bfloat16)(_bf16_build("sdpa", rope_theta=10000.0))


@pytest.mark.parametrize("name", pairs_in(__name__))
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    assert "out[0]" in errors and "grad_in[0]" in errors, f"{name}: output and input gradient must be compared"
    assert len([k for k in errors if k.startswith("grad_param")]) == 4, f"{name}: all 4 param gradients must be compared"


@pytest.mark.parametrize("attn_impl,sdpa_gqa", [("sdpa", True), ("sdpa", False), ("eager", False)],
             ids=["sdpa_gqa", "repeat_interleave", "eager"])
@pytest.mark.parametrize("n_kv_head", [N_HEAD, N_HEAD // 2, N_HEAD // 4, 1])
def test_causal(n_kv_head, attn_impl, sdpa_gqa, device):
    if attn_impl == "sdpa" and sdpa_gqa and n_kv_head != N_HEAD and not gpt._SDPA_GQA:
        pytest.skip("SDPA enable_gqa needs torch >= 2.5")
    mod = _module(n_kv_head, attn_impl=attn_impl).to(device)
    g = torch.Generator(device=device).manual_seed(2)
    x = torch.randn(B, T, N_EMBD, device=device, generator=g)
    cut = 20
    x2 = x.clone()
    x2[:, cut:] += torch.randn(x2[:, cut:].shape, device=device, generator=g)
    with torch.no_grad():
        y, y2 = _with_sdpa_gqa(sdpa_gqa, lambda: (mod(x), mod(x2)))
    assert torch.equal(y[:, :cut], y2[:, :cut]) or (y[:, :cut] - y2[:, :cut]).abs().max() < 1e-6, \
        "output before the change moved: attention is not causal"
    assert (y[:, cut:] - y2[:, cut:]).abs().max() > 1e-3, "the change had no effect after the cut"


@pytest.mark.parametrize("n_kv_head", [N_HEAD // 2, N_HEAD // 4, 1])
def test_gqa_paths_agree(n_kv_head, device):
    if not gpt._SDPA_GQA:
        pytest.skip("SDPA enable_gqa needs torch >= 2.5")
    mod = _module(n_kv_head).to(device)
    x = torch.randn(B, T, N_EMBD, device=device, generator=torch.Generator(device=device).manual_seed(3))
    with torch.no_grad():
        a = _with_sdpa_gqa(True, lambda: mod(x))
        b = _with_sdpa_gqa(False, lambda: mod(x))
    assert rel_err(a, b) < 1e-5


@pytest.mark.parametrize("n_kv_head", [N_HEAD, N_HEAD // 2, N_HEAD // 4, 1])
def test_eager_matches_sdpa(n_kv_head, device):
    """Same weights, both attn_impl values: outputs and every gradient agree (fp32 rounding only)."""
    x = torch.randn(B, T, N_EMBD, device=device, generator=torch.Generator(device=device).manual_seed(4))
    out = {}
    for impl in ("sdpa", "eager"):
        mod = _module(n_kv_head, attn_impl=impl).to(device)
        xi = x.clone().requires_grad_(True)
        y = mod(xi)
        y.square().sum().backward()
        out[impl] = [y.detach(), xi.grad] + [p.grad for p in mod.parameters()]
    for a, b in zip(out["eager"], out["sdpa"]):
        assert rel_err(a, b) < 1e-5


@pytest.mark.parametrize("theta", [10000.0, 500.0])
def test_rope_scores_depend_on_relative_position(theta, device):
    """q at m and k at n give the same score as q at m + s and k at n + s (fast apply_rope, fp32)."""
    hd, Tn, shift = N_EMBD // N_HEAD, 48, 11
    cos, sin = (t.to(device) for t in gpt.rope_tables(Tn, hd, theta))
    g = torch.Generator(device=device).manual_seed(5)
    q1 = torch.randn(1, 1, 1, hd, device=device, generator=g)
    k1 = torch.randn(1, 1, 1, hd, device=device, generator=g)
    q, k = torch.zeros(1, 1, Tn, hd, device=device), torch.zeros(1, 1, Tn, hd, device=device)
    q[..., :] = q1
    k[..., :] = k1
    s = (gpt.apply_rope(q, cos, sin) @ gpt.apply_rope(k, cos, sin).transpose(-1, -2))[0, 0]
    for m, n in [(7, 2), (20, 20), (30, 5), (3, 9)]:
        assert abs(s[m, n] - s[m + shift, n + shift]) < 1e-4 * s.abs().max(), (m, n)


def test_rope_keeps_norms_and_leaves_position_0(device):
    hd, Tn = N_EMBD // N_HEAD, 37
    cos, sin = (t.to(device) for t in gpt.rope_tables(Tn, hd, 10000.0))
    x = torch.randn(2, 3, Tn, hd, device=device, generator=torch.Generator(device=device).manual_seed(6))
    y = gpt.apply_rope(x, cos, sin)
    half = hd // 2
    pair_norm = lambda t: t[..., :half] ** 2 + t[..., half:] ** 2
    assert rel_err(pair_norm(y), pair_norm(x)) < 1e-6, "RoPE must rotate each pair, not scale it"
    assert torch.equal(y[..., 0, :], x[..., 0, :]), "position 0 has angle 0"
    assert (y[..., 1:, :] - x[..., 1:, :]).abs().max() > 1e-2, "RoPE had no effect"


def test_rope_needs_theta():
    """position=rope has no default theta: a config without one is refused, not silently 10000."""
    with pytest.raises(AssertionError, match="needs model.rope_theta"):
        ModelConfig(n_head=N_HEAD, n_embd=N_EMBD, position="rope")
    ModelConfig(n_head=N_HEAD, n_embd=N_EMBD, position="rope", rope_theta=10000.0)
    ModelConfig(n_head=N_HEAD, n_embd=N_EMBD, position="learned")      # learned: theta unused, null is fine


def test_rope_buffers_not_in_state_dict():
    """RoPE adds no parameters and no checkpoint entries to the attention module: its state_dict keys are the same
    as without RoPE. (A whole learned-position GPT checkpoint still has pos.weight, which a rope GPT does not.)"""
    plain, rope = _module(N_HEAD // 2), _module(N_HEAD // 2, rope_theta=10000.0)
    assert plain.state_dict().keys() == rope.state_dict().keys()
    assert sum(p.numel() for p in plain.parameters()) == sum(p.numel() for p in rope.parameters())
