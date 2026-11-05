"""Torch and Triton LayerNorm forward, backward, and model integration."""
from __future__ import annotations

import pytest
import torch
import torch.nn.functional as F

from correctness.framework import Case, PAIRS, check, pair, pairs_in, scaled
from kernels.layer_norm import layer_norm_triton
from models.config import ModelConfig
from models.gpt import GPT


def _cuda(device):
    if device.type != "cuda":
        pytest.skip("triton_ln requires CUDA")


@pair("ln.triton", tol=1e-4, grad_tol=1e-4)
def _ln_pair(device):
    _cuda(device)
    torch.manual_seed(101)
    x = torch.randn(7, 33, device=device, requires_grad=True)
    w = torch.randn(33, device=device, requires_grad=True)
    b = torch.randn(33, device=device, requires_grad=True)

    def ref(a, gain, bias):
        return F.layer_norm(a, (33,), gain, bias)

    def fast(a, gain, bias):
        return layer_norm_triton(a, gain, bias)

    return Case(ref=ref, fast=fast, inputs=[x, w, b])


@pytest.mark.parametrize("shape", [(3, 17), (7, 256), (2, 5, 513)])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float16, torch.bfloat16])
def test_layer_norm_matches_torch_forward_and_backward(device, shape, dtype):
    _cuda(device)
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    torch.manual_seed(103)
    n = shape[-1]
    x = torch.randn(shape, device=device, dtype=dtype, requires_grad=True)
    w = torch.randn(n, device=device, dtype=dtype, requires_grad=True)
    b = torch.randn(n, device=device, dtype=dtype, requires_grad=True)
    xr, wr, br = (p.detach().clone().requires_grad_() for p in (x, w, b))
    dy = torch.randn_like(x)
    ref = F.layer_norm(xr, (n,), wr, br, 1e-5)
    got = layer_norm_triton(x, w, b)
    ref_grads = torch.autograd.grad(ref, (xr, wr, br), dy)
    got_grads = torch.autograd.grad(got, (x, w, b), dy)
    tol = 3e-4 if dtype == torch.float32 else 3e-2
    torch.testing.assert_close(got, ref, atol=tol, rtol=tol)
    for actual, expected in zip(got_grads, ref_grads):
        torch.testing.assert_close(actual, expected, atol=tol, rtol=tol)


def test_layer_norm_full_model_matches_torch(device):
    _cuda(device)
    torch.manual_seed(107)
    cfg = dict(vocab_size=71, block_size=8, n_layer=2, n_head=2, n_embd=32)
    ref = GPT(ModelConfig(**cfg, ln_impl="torch_ln")).to(device)
    got = GPT(ModelConfig(**cfg, ln_impl="triton_ln")).to(device)
    got.load_state_dict(ref.state_dict())
    ids = torch.randint(0, 71, (2, 5), device=device)
    targets = torch.randint(0, 71, (2, 5), device=device)
    _, ref_loss = ref(ids, targets)
    _, got_loss = got(ids, targets)
    ref_loss.backward()
    got_loss.backward()
    torch.testing.assert_close(got_loss, ref_loss, atol=2e-4, rtol=2e-4)
    for (name, p), (other, q) in zip(ref.named_parameters(), got.named_parameters()):
        assert name == other
        torch.testing.assert_close(q.grad, p.grad, atol=3e-4, rtol=3e-4, msg=name)


def test_layer_norm_rejects_cuda_free_call():
    x = torch.randn(2, 8)
    with pytest.raises(RuntimeError, match="CUDA and Triton"):
        layer_norm_triton(x, torch.ones(8), torch.zeros(8))


@pytest.mark.parametrize("device", [torch.device("cuda")])
def test_layer_norm_pair_rejects_101_percent_error(device):
    if not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    with pytest.raises(AssertionError):
        check(PAIRS["ln.triton"], device, fast_override=scaled(1.01))


@pytest.mark.parametrize("name", pairs_in(__name__))
@pytest.mark.parametrize("device", [torch.device("cuda")])
def test_pair(name, device):
    if not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    check(PAIRS[name], device)
