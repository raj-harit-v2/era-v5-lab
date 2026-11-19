"""ce_impl=fused_triton (kernels/linear_ce_cublas.py): cuBLAS head matmuls + one Triton softmax-gradient pass.

CPU (always): the fallback is ce_impl=fused bit for bit; the model path returns no logits.
CUDA: loss and every gradient against F.cross_entropy on the full logits (fp32), against ce_impl=fused under bf16
autocast (same numerics), with ignored targets, a bias, uneven chunks and a vocabulary that is not a multiple of
the kernel block; grad_output scaling, frozen inputs, an invalid target (NaN) and the bitwise repeat.
"""
from __future__ import annotations

import pytest
import torch
import torch.nn.functional as F

from kernels import linear_ce_cublas as ce_k
from kernels.linear_ce_cublas import linear_cross_entropy_cublas
from models.config import ModelConfig
from models.gpt import GPT
from models.linear_ce import linear_cross_entropy_fused

IGNORE = -100


def _cuda(device):
    if device.type != "cuda" or ce_k.triton is None:
        pytest.skip("fused_triton needs CUDA and Triton")


def _inputs(device, n, h, v, dtype=torch.float32, bias=False, ignore="none", seed=0):
    torch.manual_seed(seed)
    x = torch.randn(n, h, device=device, dtype=dtype, requires_grad=True)
    w = (0.2 * torch.randn(v, h, device=device, dtype=dtype)).requires_grad_()
    b = (0.1 * torch.randn(v, device=device, dtype=dtype)).requires_grad_() if bias else None
    y = torch.randint(0, v, (n,), device=device)
    if ignore == "some":
        y[::3] = IGNORE
    elif ignore == "all":
        y[:] = IGNORE
    return x, w, b, y


def _leaves(*ts):
    return [None if t is None else t.detach().clone().requires_grad_() for t in ts]


def _reference(x, w, b, y):
    logits = F.linear(x.float(), w.float(), None if b is None else b.float())
    keep = y != IGNORE
    return F.cross_entropy(logits, y, ignore_index=IGNORE, reduction="sum") / keep.sum().clamp_min(1)


def _grads(loss, ts):
    return torch.autograd.grad(loss, [t for t in ts if t is not None])


# ------------------------------------------------------------------------------ CPU

@pytest.mark.parametrize("bias", [False, True])
def test_cpu_fallback_is_ce_fused_bit_for_bit(bias):
    x, w, b, y = _inputs(torch.device("cpu"), 37, 16, 50, bias=bias, ignore="some")
    xr, wr, br = _leaves(x, w, b)
    got = linear_cross_entropy_cublas(x, w, y, bias=b, chunks=3, ignore_index=IGNORE)
    ref = linear_cross_entropy_fused(xr, wr, y, bias=br, chunks=3, ignore_index=IGNORE)
    assert torch.equal(got, ref)
    for a, c in zip(_grads(got, (x, w, b)), _grads(ref, (xr, wr, br))):
        assert torch.equal(a, c)


def test_model_path_returns_no_logits():
    model = GPT(ModelConfig(vocab_size=71, block_size=8, n_layer=1, n_head=2, n_embd=16, ce_impl="fused_triton"))
    ids = torch.randint(0, 71, (2, 8))
    logits, loss = model(ids, ids)
    assert logits is None and torch.isfinite(loss)


def test_rejects_zero_chunks():
    x, w, _, y = _inputs(torch.device("cpu"), 4, 8, 10)
    with pytest.raises(ValueError):
        linear_cross_entropy_cublas(x, w, y, chunks=0)


# ------------------------------------------------------------------------------ CUDA

@pytest.mark.parametrize("n,h,v,chunks", [(1, 8, 3, 1), (37, 16, 1000, 4), (64, 32, 4099, 3), (513, 64, 2048, 8)])
@pytest.mark.parametrize("bias", [False, True])
@pytest.mark.parametrize("ignore", ["none", "some", "all"])
def test_fp32_matches_full_logits_cross_entropy(device, n, h, v, chunks, bias, ignore):
    _cuda(device)
    x, w, b, y = _inputs(device, n, h, v, bias=bias, ignore=ignore)
    xr, wr, br = _leaves(x, w, b)
    got = linear_cross_entropy_cublas(x, w, y, bias=b, chunks=chunks, ignore_index=IGNORE)
    ref = _reference(xr, wr, br, y)
    torch.testing.assert_close(got, ref, atol=1e-5, rtol=1e-5)
    for a, c in zip(_grads(got, (x, w, b)), _grads(ref, (xr, wr, br))):
        torch.testing.assert_close(a, c, atol=1e-5, rtol=1e-4)


@pytest.mark.parametrize("v", [131, 131072])
def test_bf16_autocast_matches_ce_fused(device, v):
    _cuda(device)
    if not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    x, w, _, y = _inputs(device, 256, 64, v, ignore="some")
    xr, wr = _leaves(x, w)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        got = linear_cross_entropy_cublas(x, w, y, chunks=4, ignore_index=IGNORE)
        ref = linear_cross_entropy_fused(xr, wr, y, chunks=4, ignore_index=IGNORE)
    assert got.dtype == torch.float32
    torch.testing.assert_close(got, ref, atol=1e-4, rtol=1e-4)
    for a, c in zip(_grads(got, (x, w)), _grads(ref, (xr, wr))):
        torch.testing.assert_close(a, c, atol=1e-3, rtol=2e-2)


def test_grad_output_scales_and_frozen_weight_has_no_gradient(device):
    _cuda(device)
    x, w, _, y = _inputs(device, 40, 16, 300)
    w.requires_grad_(False)
    xr = _leaves(x)[0]
    got = 3.0 * linear_cross_entropy_cublas(x, w, y, chunks=3)
    ref = 3.0 * _reference(xr, w, None, y)
    got.backward()
    ref.backward()
    torch.testing.assert_close(x.grad, xr.grad, atol=1e-5, rtol=1e-4)
    assert w.grad is None


def test_invalid_target_gives_nan(device):
    _cuda(device)
    x, w, _, y = _inputs(device, 8, 8, 20)
    y[2] = 25
    assert torch.isnan(linear_cross_entropy_cublas(x, w, y, chunks=2))


def test_backward_repeats_bitwise(device):
    _cuda(device)
    x, w, _, y = _inputs(device, 1024, 64, 8192, ignore="some")
    runs = []
    for _ in range(2):
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = linear_cross_entropy_cublas(x, w, y, chunks=4)
        runs.append((loss, *_grads(loss, (x, w))))
    assert all(torch.equal(a, b) for a, b in zip(*runs))


def test_model_matches_torch_ce(device):
    _cuda(device)
    cfg = dict(vocab_size=257, block_size=16, n_layer=2, n_head=2, n_embd=32)
    torch.manual_seed(3)
    ref = GPT(ModelConfig(**cfg, ce_impl="torch")).to(device)
    got = GPT(ModelConfig(**cfg, ce_impl="fused_triton", ce_chunks=3)).to(device)
    got.load_state_dict(ref.state_dict())
    ids = torch.randint(0, 257, (2, 16), device=device)
    _, a = ref(ids, ids)
    _, b = got(ids, ids)
    a.backward()
    b.backward()
    torch.testing.assert_close(b, a, atol=1e-5, rtol=1e-5)
    for (name, p), (_, q) in zip(ref.named_parameters(), got.named_parameters()):
        torch.testing.assert_close(q.grad, p.grad, atol=1e-5, rtol=1e-4, msg=name)
