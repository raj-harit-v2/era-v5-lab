"""RMSNorm (model.norm), and the Triton kernels behind swiglu_impl, rope_impl, attn_impl=triton,
moe.router_impl and ln_impl=triton_ln with norm=rmsnorm.

CPU (always): config checks, the torch RMSNorm against the G5 formula, every Triton switch falling back to the
torch path bit for bit, the report treating the switches as implementation A/Bs.
CUDA (skipped without CUDA and Triton): each kernel against its torch reference, forward and backward, in fp32
and bf16, on uneven shapes and strided inputs; bitwise repeat of the backward; the whole model with every
switch on against the torch model.
"""
from __future__ import annotations

import copy
import math

import pytest
import torch
import torch.nn.functional as F

from kernels import attention as attn_k, rms_norm as rms_k, rope as rope_k, router as router_k, swiglu as swiglu_k
from kernels.layer_norm import layer_norm_backend_report
from models.config import ModelConfig
from models.gpt import GPT, apply_rope, rope_tables
from models.moe import SparseMoE
from models.norm import RMSNorm

TRITON_SWITCHES = dict(ln_impl="triton_ln", attn_impl="triton", rope_impl="triton", swiglu_impl="triton")


def _cuda(device):
    if device.type != "cuda" or rms_k.triton is None:
        pytest.skip("Triton kernels need CUDA and Triton")


def _bf16(device):
    if not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")


def _leaf(t):
    return t.detach().clone().requires_grad_()


def _tol(dtype):
    return dict(atol=2e-4, rtol=2e-4) if dtype == torch.float32 else dict(atol=3e-2, rtol=3e-2)


def _model_cfg(**kw):
    base = dict(vocab_size=71, block_size=16, n_layer=2, n_head=4, n_kv_head=2, n_embd=32,
                position="rope", rope_theta=10000.0, activation="swiglu", attn_impl="eager")
    base.update(kw)
    return ModelConfig(**base)


# ------------------------------------------------------------------------------ CPU: config and references

@pytest.mark.parametrize("bad", [dict(norm="batchnorm"), dict(norm_eps=0.0), dict(swiglu_impl="cuda"),
                                 dict(rope_impl="fast"), dict(attn_impl="flash"),
                                 dict(moe=dict(router_impl="cuda"))])
def test_config_rejects_unknown_choices(bad):
    with pytest.raises(AssertionError):
        ModelConfig(**bad)


def test_rms_norm_matches_g5_formula():
    torch.manual_seed(0)
    norm = RMSNorm(24, eps=1e-6)
    with torch.no_grad():
        norm.weight.normal_()
    x = torch.randn(3, 5, 24)                       # G5 computes in fp32 (x.float()), so compare at fp32 accuracy
    x64 = x.double()
    ref = x64 * torch.rsqrt(x64.pow(2).mean(-1, keepdim=True) + 1e-6) * norm.weight.double()
    torch.testing.assert_close(norm(x).double(), ref, atol=1e-6, rtol=1e-6)
    r = torch.randn_like(x)
    torch.testing.assert_close(norm(x, r), norm(x + r))


def test_rms_norm_keeps_input_dtype():
    norm = RMSNorm(8)
    assert norm(torch.randn(2, 8, dtype=torch.bfloat16)).dtype == torch.bfloat16


def test_model_builds_rms_norms_everywhere():
    model = GPT(_model_cfg(norm="rmsnorm", norm_eps=1e-6))
    norms = [m for m in model.modules() if isinstance(m, RMSNorm)]
    assert len(norms) == 2 * 2 + 1 and all(m.eps == 1e-6 for m in norms)
    assert not any(isinstance(m, torch.nn.LayerNorm) for m in model.modules())
    assert all(not hasattr(m, "bias") for m in norms)


def test_norm_eps_reaches_layer_norm():
    model = GPT(_model_cfg(norm_eps=1e-6))
    assert all(m.eps == 1e-6 for m in model.modules() if isinstance(m, torch.nn.LayerNorm))


def test_backend_report_lists_rms_norms():
    model = GPT(_model_cfg(norm="rmsnorm", ln_impl="triton_ln"))
    entries = layer_norm_backend_report(model)
    assert len(entries) == 5
    assert all(e["backend"] == "torch_ln" and e["reason"] for e in entries)      # CPU: fallback with a reason


@pytest.mark.parametrize("norm", ["layernorm", "rmsnorm"])
@pytest.mark.parametrize("ffn", ["mlp", "moe"])
@pytest.mark.parametrize("reversible", [False, True])
def test_triton_switches_fall_back_to_torch_bit_for_bit_on_cpu(norm, ffn, reversible):
    """Off CUDA every switch is the torch path: the same loss and gradients, exactly."""
    moe = dict(num_experts=4, top_k=2, num_shared=1, dispatch="sorted")
    kw = dict(norm=norm, ffn=ffn, reversible=reversible)
    torch.manual_seed(1)
    ref = GPT(_model_cfg(**kw, moe=dict(moe)))
    got = GPT(_model_cfg(**kw, **TRITON_SWITCHES, moe=dict(moe, router_impl="triton")))
    got.load_state_dict(ref.state_dict())
    ids = torch.randint(0, 71, (2, 9))
    _, a = ref(ids, ids)
    _, b = got(ids, ids)
    a.backward()
    b.backward()
    assert torch.equal(a, b)
    for (name, p), (_, q) in zip(ref.named_parameters(), got.named_parameters()):
        assert torch.equal(p.grad, q.grad), name


def test_strict_kernel_apis_reject_cpu():
    x = torch.randn(2, 4, 3, 8)
    with pytest.raises(ValueError):
        attn_k.attention(x, x, x)
    with pytest.raises(ValueError):
        router_k.route(torch.randn(3, 4), torch.zeros(4), 2)
    with pytest.raises(ValueError):
        rms_k.rms_norm_triton(torch.randn(2, 8), torch.ones(8))


@pytest.mark.parametrize("path,a,b", [(("attn_impl",), "eager", "triton"), (("rope_impl",), "torch", "triton"),
                                      (("swiglu_impl",), "torch", "triton"),
                                      (("moe", "router_impl"), "torch", "triton")])
def test_report_treats_switches_as_implementation_ab(path, a, b):
    from perfkit import report
    run_a = {"config": {"model": {"moe": {}}}}
    run_b = copy.deepcopy(run_a)
    for run, value in ((run_a, a), (run_b, b)):
        sect = run["config"]["model"]
        for key in path[:-1]:
            sect = sect[key]
        sect[path[-1]] = value
    assert report.compare_config_value(run_a["config"], "model", None) == \
        report.compare_config_value(run_b["config"], "model", None)
    assert report.impl_differences(run_a, run_b)


def test_report_does_not_treat_norm_as_implementation_switch():
    from perfkit import report
    a = {"model": {"norm": "layernorm"}}
    b = {"model": {"norm": "rmsnorm"}}
    assert report.compare_config_value(a, "model", None) != report.compare_config_value(b, "model", None)


# ------------------------------------------------------------------------------ CUDA: RMSNorm

@pytest.mark.parametrize("shape", [(1, 1), (3, 17), (7, 256), (2, 5, 513), (4096, 256), (3, 8192)])
@pytest.mark.parametrize("dtype", [torch.float32, torch.bfloat16])
@pytest.mark.parametrize("residual", [False, True])
def test_rms_norm_matches_torch(device, shape, dtype, residual):
    _cuda(device)
    if dtype == torch.bfloat16:
        _bf16(device)
    torch.manual_seed(11)
    n = shape[-1]
    ref = RMSNorm(n).to(device)
    got = rms_k.TritonRMSNorm(n).to(device)
    with torch.no_grad():
        ref.weight.normal_()
    got.load_state_dict(ref.state_dict())
    x = torch.randn(shape, device=device, dtype=dtype, requires_grad=True)
    r = torch.randn(shape, device=device, dtype=torch.float32, requires_grad=True) if residual else None
    xr, rr = _leaf(x), (_leaf(r) if residual else None)
    assert got.backend_info(x.device, x.dtype)["backend"] == "triton_ln"
    y, yr = got(x, r), ref(xr, rr)
    assert y.dtype == yr.dtype
    torch.testing.assert_close(y, yr, **_tol(dtype))
    dy = torch.randn_like(y)
    y.backward(dy)
    yr.backward(dy)
    torch.testing.assert_close(x.grad, xr.grad, **_tol(dtype))
    if residual:
        torch.testing.assert_close(r.grad, rr.grad, **_tol(dtype))
    torch.testing.assert_close(got.weight.grad, ref.weight.grad, **_tol(torch.float32 if n < 512 else dtype))


def test_rms_norm_backward_repeats_bitwise(device):
    _cuda(device)
    torch.manual_seed(13)
    norm = rms_k.TritonRMSNorm(256).to(device)
    x = torch.randn(8192, 256, device=device, requires_grad=True)
    r = torch.randn_like(x, requires_grad=True)
    grads = []
    for _ in range(2):
        x.grad = r.grad = norm.weight.grad = None
        norm(x, r).square().sum().backward()
        grads.append((x.grad.clone(), r.grad.clone(), norm.weight.grad.clone()))
    assert all(torch.equal(a, b) for a, b in zip(*grads))


def test_rms_norm_no_grad_path(device):
    _cuda(device)
    norm = rms_k.TritonRMSNorm(64).to(device)
    x, r = torch.randn(5, 64, device=device), torch.randn(5, 64, device=device)
    with torch.no_grad():
        torch.testing.assert_close(norm(x, r), RMSNorm(64).to(device)(x, r), **_tol(torch.float32))


# ------------------------------------------------------------------------------ CUDA: SwiGLU

@pytest.mark.parametrize("dtype", [torch.float32, torch.bfloat16])
@pytest.mark.parametrize("strided", [False, True])
@pytest.mark.parametrize("shape", [(1, 1), (3, 7, 1000), (4096, 1024), (2, 3, 4097)])
def test_swiglu_matches_torch(device, dtype, strided, shape):
    _cuda(device)
    if dtype == torch.bfloat16:
        _bf16(device)
    torch.manual_seed(17)
    if strided:          # gate and up as the two halves of one [.., 2h] tensor (the batched experts' chunk)
        both = torch.randn(*shape[:-1], 2 * shape[-1], device=device, dtype=dtype, requires_grad=True)
        g, u = both.chunk(2, dim=-1)
        both_r = _leaf(both)
        gr, ur = both_r.chunk(2, dim=-1)
        leaves, ref_leaves = [both], [both_r]
    else:
        g = torch.randn(shape, device=device, dtype=dtype, requires_grad=True)
        u = torch.randn(shape, device=device, dtype=dtype, requires_grad=True)
        gr, ur = _leaf(g), _leaf(u)
        leaves, ref_leaves = [g, u], [gr, ur]
    assert swiglu_k.supported(g, u)
    h, hr = swiglu_k.swiglu(g, u), F.silu(gr) * ur
    assert h.dtype == hr.dtype and h.shape == hr.shape
    torch.testing.assert_close(h, hr, **_tol(dtype))
    dh = torch.randn_like(h)
    h.backward(dh)
    hr.backward(dh)
    for a, b in zip(leaves, ref_leaves):
        torch.testing.assert_close(a.grad, b.grad, **_tol(dtype))


# ------------------------------------------------------------------------------ CUDA: RoPE

@pytest.mark.parametrize("dtype", [torch.float32, torch.bfloat16])
@pytest.mark.parametrize("heads,kv,hd", [(8, 8, 32), (8, 2, 32), (4, 1, 64), (3, 3, 6)])
@pytest.mark.parametrize("T", [1, 17, 256])
def test_rope_matches_apply_rope_on_the_qkv_view(device, dtype, heads, kv, hd, T):
    _cuda(device)
    if dtype == torch.bfloat16:
        _bf16(device)
    torch.manual_seed(19)
    B = 3
    cos, sin = (t[:, None].to(device) for t in rope_tables(T + 5, hd, 10000.0))
    cos, sin = cos[:T], sin[:T]
    qkv = torch.randn(B, T, (heads + 2 * kv) * hd, device=device, dtype=dtype, requires_grad=True)
    qkv_r = _leaf(qkv)
    outs = []
    for src, fn in ((qkv, rope_k.rope), (qkv_r, apply_rope)):
        qk = src.split([(heads + kv) * hd, kv * hd], dim=2)[0].view(B, T, heads + kv, hd)
        outs.append(fn(qk, cos, sin))
    assert rope_k.supported(qkv.split([(heads + kv) * hd, kv * hd], dim=2)[0].view(B, T, heads + kv, hd),
                            cos, sin)
    torch.testing.assert_close(outs[0], outs[1], **_tol(dtype))
    dy = torch.randn_like(outs[0])
    outs[0].backward(dy)
    outs[1].backward(dy)
    torch.testing.assert_close(qkv.grad, qkv_r.grad, **_tol(dtype))


# ------------------------------------------------------------------------------ CUDA: attention

def _eager(q, k, v):
    rep = q.shape[1] // k.shape[1]
    k, v = k.repeat_interleave(rep, dim=1), v.repeat_interleave(rep, dim=1)
    T = q.shape[2]
    future = torch.triu(torch.ones(T, T, dtype=torch.bool, device=q.device), diagonal=1)
    att = (q.float() @ k.float().transpose(-2, -1)) / math.sqrt(q.shape[-1])
    return (F.softmax(att.masked_fill(future, float("-inf")), dim=-1) @ v.float()).to(q.dtype)


def _qkv(device, dtype, B, H, KV, T, hd, seed=23):
    torch.manual_seed(seed)
    qkv = torch.randn(B, T, (H + 2 * KV) * hd, device=device, dtype=dtype)
    q, k, v = qkv.split([H * hd, KV * hd, KV * hd], dim=2)
    views = [t.reshape(B, T, -1, hd).transpose(1, 2) for t in (q, k, v)]      # GQAttention's strided views
    return qkv, views


@pytest.mark.parametrize("dtype", [torch.float32, torch.bfloat16])
@pytest.mark.parametrize("H,KV,hd", [(8, 8, 32), (8, 2, 32), (4, 1, 64), (2, 2, 16), (2, 1, 8)])
@pytest.mark.parametrize("T", [1, 17, 64, 100, 256])
def test_attention_matches_eager(device, dtype, H, KV, hd, T):
    _cuda(device)
    if dtype == torch.bfloat16:
        _bf16(device)
    qkv, _ = _qkv(device, dtype, 2, H, KV, T, hd)
    leaves = [_leaf(qkv), _leaf(qkv)]
    outs = []
    for leaf, fn in zip(leaves, (attn_k.attention, _eager)):
        q, k, v = (t.reshape(2, T, -1, hd).transpose(1, 2) for t in leaf.split([H * hd, KV * hd, KV * hd], 2))
        outs.append(fn(q, k, v))
    assert outs[0].dtype == dtype and outs[0].shape == (2, H, T, hd)
    assert outs[0].transpose(1, 2).is_contiguous()
    torch.testing.assert_close(outs[0], outs[1], **_tol(dtype))
    dy = torch.randn_like(outs[0])
    outs[0].backward(dy)
    outs[1].backward(dy)
    torch.testing.assert_close(leaves[0].grad, leaves[1].grad, **_tol(dtype))


def test_attention_backward_repeats_bitwise(device):
    _cuda(device)
    _bf16(device)
    qkv, _ = _qkv(device, torch.bfloat16, 4, 8, 2, 512, 32)
    grads = []
    for _ in range(2):
        leaf = _leaf(qkv)
        q, k, v = (t.reshape(4, 512, -1, 32).transpose(1, 2) for t in leaf.split([256, 64, 64], 2))
        attn_k.attention(q, k, v).float().square().sum().backward()
        grads.append(leaf.grad)
    assert torch.equal(grads[0], grads[1])


# ------------------------------------------------------------------------------ CUDA: router

@pytest.mark.parametrize("n,e,k", [(1, 8, 2), (77, 8, 2), (4096, 8, 2), (100, 5, 3), (33, 64, 6), (9, 4, 4)])
def test_router_matches_torch(device, n, e, k):
    _cuda(device)
    torch.manual_seed(29)
    logits = torch.randn(n, e, device=device, requires_grad=True)
    bias = 0.1 * torch.randn(e, device=device)
    lr = _leaf(logits)
    idx, gates = router_k.route(logits, bias, k)
    scores = F.softmax(lr, dim=-1)
    ref_idx = torch.topk(scores + bias, k, dim=1).indices
    ref_gates = torch.gather(scores, 1, ref_idx)
    ref_gates = ref_gates / ref_gates.sum(1, keepdim=True)
    assert torch.equal(idx, ref_idx)
    torch.testing.assert_close(gates, ref_gates, atol=1e-6, rtol=1e-5)
    dg = torch.randn_like(gates)
    gates.backward(dg)
    ref_gates.backward(dg)
    torch.testing.assert_close(logits.grad, lr.grad, atol=1e-6, rtol=1e-5)


def test_moe_router_switch_and_forced_routing(device):
    _cuda(device)
    torch.manual_seed(31)
    kw = dict(num_experts=8, top_k=2, num_shared=1, dispatch="sorted")
    ref = SparseMoE(32, **kw).to(device)
    got = SparseMoE(32, **kw, router_impl="triton").to(device)
    got.load_state_dict(ref.state_dict())
    x = torch.randn(3, 20, 32, device=device, requires_grad=True)
    xr = _leaf(x)
    y, yr = got(x), ref(xr)
    torch.testing.assert_close(y, yr, **_tol(torch.float32))
    y.square().sum().backward()
    yr.square().sum().backward()
    torch.testing.assert_close(x.grad, xr.grad, **_tol(torch.float32))
    torch.testing.assert_close(got.router.weight.grad, ref.router.weight.grad, **_tol(torch.float32))


# ------------------------------------------------------------------------------ CUDA: whole model

@pytest.mark.parametrize("norm", ["layernorm", "rmsnorm"])
@pytest.mark.parametrize("ffn", ["mlp", "moe"])
@pytest.mark.parametrize("reversible", [False, True])
@pytest.mark.parametrize("autocast", [False, True])
def test_full_model_with_every_triton_switch_matches_torch(device, norm, ffn, reversible, autocast):
    _cuda(device)
    if autocast:
        _bf16(device)
    moe = dict(num_experts=4, top_k=2, num_shared=1, dispatch="sorted")
    kw = dict(norm=norm, ffn=ffn, reversible=reversible)
    torch.manual_seed(37)
    ref = GPT(_model_cfg(**kw, moe=dict(moe))).to(device)
    got = GPT(_model_cfg(**kw, **TRITON_SWITCHES, moe=dict(moe, router_impl="triton"))).to(device)
    got.load_state_dict(ref.state_dict())
    ids = torch.randint(0, 71, (2, 13), device=device)
    with torch.autocast("cuda", dtype=torch.bfloat16, enabled=autocast):
        _, a = ref(ids, ids)
        _, b = got(ids, ids)
    a.backward()
    b.backward()
    tol = _tol(torch.bfloat16 if autocast else torch.float32)
    torch.testing.assert_close(b, a, **tol)
    for (name, p), (_, q) in zip(ref.named_parameters(), got.named_parameters()):
        torch.testing.assert_close(q.grad, p.grad, **tol, msg=name)


def test_full_model_triton_switches_under_compile(device):
    _cuda(device)
    torch.manual_seed(41)
    cfg = _model_cfg(norm="rmsnorm", **TRITON_SWITCHES)
    model = GPT(cfg).to(device)
    ref = copy.deepcopy(model)
    compiled = torch.compile(model)
    ids = torch.randint(0, 71, (2, 16), device=device)
    _, a = ref(ids, ids)
    _, b = compiled(ids, ids)
    a.backward()
    b.backward()
    torch.testing.assert_close(b, a, **_tol(torch.float32))
    for (name, p), (_, q) in zip(ref.named_parameters(), model.named_parameters()):
        torch.testing.assert_close(q.grad, p.grad, **_tol(torch.float32), msg=name)
