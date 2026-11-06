"""Correctness coverage for the in-repo Triton linear CE backend."""
from __future__ import annotations

import pytest
import torch
import torch.nn.functional as F

from correctness.framework import Case, PAIRS, check, pair, pairs_in, scaled
from models.config import ModelConfig
from models.gpt import GPT
from kernels.linear_ce_fused import linear_cross_entropy_fused_triton
from kernels import linear_ce_fused as ce


def _require_cuda(device):
    if device.type != "cuda" or ce.triton is None:
        pytest.skip("triton_ce runs on CUDA; CPU reference modes remain available")


@pair("ce.triton", tol=1e-4, grad_tol=5e-4)
def _triton_pair(device):
    _require_cuda(device)
    torch.manual_seed(13)
    x = torch.randn(7, 16, device=device, requires_grad=True)
    weight = torch.randn(37, 16, device=device, requires_grad=True)
    bias = torch.randn(37, device=device, requires_grad=True)
    targets = torch.randint(0, 37, (7,), device=device)
    targets[::3] = -100

    def ref(a, w, b, y):
        return F.cross_entropy(F.linear(a, w, b), y, ignore_index=-100)

    def fast(a, w, b, y):
        return linear_cross_entropy_fused_triton(a, w, y, bias=b)

    return Case(ref=ref, fast=fast, inputs=[x, weight, bias, targets])


@pytest.mark.parametrize("n,h,v", [(5, 13, 53), (11, 13, 53), (17, 13, 53),
                                    (37, 70, 513)])
@pytest.mark.parametrize("mask", ["none", "partial", "all"])
@pytest.mark.parametrize("backward_impl", ["chunked", "recompute"])
def test_triton_loss_and_gradients_cover_masks_and_uneven_tiles(device, n, h, v, mask, backward_impl):
    _require_cuda(device)
    torch.manual_seed(19)
    x = torch.randn(n, h, device=device, requires_grad=True)
    weight = torch.randn(v, h, device=device, requires_grad=True)
    bias = torch.randn(v, device=device, requires_grad=True)
    targets = torch.randint(0, v, (n,), device=device)
    if mask == "partial":
        targets[1::3] = -100
    elif mask == "all":
        targets.fill_(-100)
    xr, wr, br = (v.detach().clone().requires_grad_() for v in (x, weight, bias))
    ref_sum = F.cross_entropy(F.linear(xr, wr, br), targets, ignore_index=-100, reduction="sum")
    ref = ref_sum / (targets != -100).sum().clamp_min(1)
    got = linear_cross_entropy_fused_triton(x, weight, targets, bias=bias,
                                           backward_impl=backward_impl, token_chunk=16)
    ref_grads = torch.autograd.grad(ref, (xr, wr, br))
    got_grads = torch.autograd.grad(got, (x, weight, bias))
    torch.testing.assert_close(got, ref, atol=1e-5, rtol=1e-5)
    for actual, expected in zip(got_grads, ref_grads):
        torch.testing.assert_close(actual, expected, atol=2e-5, rtol=2e-5)
    if mask == "all":
        assert got.item() == 0.0
        assert all(not grad.any() for grad in got_grads)


def test_triton_negative_logits_tail_and_scaled_gradients(device):
    _require_cuda(device)
    torch.manual_seed(41)
    x = torch.randn(3, 16, device=device, requires_grad=True)
    weight = torch.randn(257, 16, device=device, requires_grad=True) * 0.01
    bias = torch.full((257,), -1000., device=device, requires_grad=True)
    targets = torch.tensor([0, 256, -100], device=device)
    xr = x.detach().clone().requires_grad_()
    wr = weight.detach().clone().requires_grad_()
    br = bias.detach().clone().requires_grad_()
    ref = F.cross_entropy(F.linear(xr, wr, br), targets, ignore_index=-100)
    got = linear_cross_entropy_fused_triton(x, weight, targets, bias=bias)
    ref_grads = torch.autograd.grad(ref * 1.7, (xr, wr, br))
    got_grads = torch.autograd.grad(got * 1.7, (x, weight, bias))
    torch.testing.assert_close(got, ref, atol=2e-4, rtol=2e-4)
    for actual, expected in zip(got_grads, ref_grads):
        assert torch.isfinite(actual).all()
        torch.testing.assert_close(actual, expected, atol=2e-4, rtol=2e-4)


def test_triton_noncontiguous_inputs(device):
    _require_cuda(device)
    torch.manual_seed(43)
    x = torch.randn(70, 35, device=device)[:67, ::2].requires_grad_()
    weight = torch.randn(75, 35, device=device)[:71, ::2].requires_grad_()
    targets = torch.randint(0, 71, (67,), device=device)
    xr = x.detach().clone().requires_grad_()
    wr = weight.detach().clone().requires_grad_()
    ref = F.cross_entropy(F.linear(xr, wr), targets)
    got = linear_cross_entropy_fused_triton(x, weight, targets)
    torch.testing.assert_close(got, ref, atol=2e-5, rtol=2e-5)
    for actual, expected in zip(torch.autograd.grad(got, (x, weight)),
                                torch.autograd.grad(ref, (xr, wr))):
        torch.testing.assert_close(actual, expected, atol=3e-5, rtol=3e-5)


@pytest.mark.parametrize("mtp", [False, True], ids=["ntp", "mtp"])
@pytest.mark.parametrize("backward_impl", ["chunked", "recompute"])
def test_triton_gpt_path_matches_torch(device, mtp, backward_impl):
    _require_cuda(device)
    cfg = dict(vocab_size=53, block_size=8, n_layer=1, n_head=2, n_embd=16, mtp=mtp)
    torch.manual_seed(23)
    ref = GPT(ModelConfig(**cfg, ce_impl="torch")).to(device).train()
    got = GPT(ModelConfig(**cfg, ce_impl="triton_ce", ce_triton_chunk=3,
                          ce_triton_backward=backward_impl)).to(device).train()
    got.load_state_dict(ref.state_dict())
    ids = torch.randint(0, 53, (2, 7), device=device)
    targets = torch.randint(0, 53, (2, 7), device=device)
    targets[:, 2] = -100
    _, lr = ref(ids, targets)
    logits, lg = got(ids, targets)
    assert logits is None
    lr.backward()
    lg.backward()
    torch.testing.assert_close(lg, lr, atol=1e-5, rtol=1e-5)
    for (name, p), (got_name, q) in zip(ref.named_parameters(), got.named_parameters()):
        assert name == got_name
        torch.testing.assert_close(q.grad, p.grad, atol=5e-5, rtol=5e-5, msg=name)


def test_triton_bf16_autocast_matches_torch(device):
    _require_cuda(device)
    if not torch.cuda.is_bf16_supported():
        pytest.skip("device does not support bf16")
    torch.manual_seed(31)
    x = torch.randn(9, 32, device=device, requires_grad=True)
    weight = torch.randn(71, 32, device=device, requires_grad=True)
    targets = torch.randint(0, 71, (9,), device=device)
    targets[::4] = -100
    xr = x.detach().clone().requires_grad_()
    wr = weight.detach().clone().requires_grad_()
    with torch.autocast("cuda", dtype=torch.bfloat16):
        ref = F.cross_entropy(F.linear(xr, wr), targets, ignore_index=-100)
        got = linear_cross_entropy_fused_triton(x, weight, targets, token_chunk=4)
    ref_grads = torch.autograd.grad(ref, (xr, wr))
    got_grads = torch.autograd.grad(got, (x, weight))
    torch.testing.assert_close(got, ref, atol=1e-2, rtol=1e-2)
    for actual, expected in zip(got_grads, ref_grads):
        torch.testing.assert_close(actual, expected, atol=3e-2, rtol=3e-2)


@pytest.mark.parametrize("dtype", [torch.float16, torch.bfloat16])
def test_triton_native_low_precision_matches_torch(device, dtype):
    _require_cuda(device)
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("device does not support bf16")
    torch.manual_seed(47)
    x = torch.randn(5, 32, device=device, dtype=dtype, requires_grad=True)
    weight = torch.randn(71, 32, device=device, dtype=dtype, requires_grad=True)
    targets = torch.randint(0, 71, (5,), device=device)
    xr = x.detach().clone().requires_grad_()
    wr = weight.detach().clone().requires_grad_()
    ref = F.cross_entropy(F.linear(xr, wr).float(), targets)
    got = linear_cross_entropy_fused_triton(x, weight, targets, token_chunk=3)
    ref_grads = torch.autograd.grad(ref, (xr, wr))
    got_grads = torch.autograd.grad(got, (x, weight))
    torch.testing.assert_close(got, ref, atol=3e-2, rtol=3e-2)
    for actual, expected in zip(got_grads, ref_grads):
        torch.testing.assert_close(actual, expected, atol=5e-2, rtol=5e-2)


def test_triton_rejects_invalid_shapes_before_launch():
    x = torch.randn(2, 4)
    w = torch.randn(7, 4)
    y = torch.tensor([1, 2])
    with pytest.raises(ValueError, match="hidden sizes"):
        linear_cross_entropy_fused_triton(x, torch.randn(7, 5), y)
    with pytest.raises(ValueError, match="one label"):
        linear_cross_entropy_fused_triton(x, w, y[:1])
    with pytest.raises(ValueError, match="bias"):
        linear_cross_entropy_fused_triton(x, w, y, bias=torch.randn(6))
    with pytest.raises(TypeError, match="integer"):
        linear_cross_entropy_fused_triton(x, w, y.float())
    with pytest.raises(TypeError, match="same dtype"):
        linear_cross_entropy_fused_triton(x, w.double(), y)
    with pytest.raises(ValueError, match="backward_impl"):
        linear_cross_entropy_fused_triton(x, w, y, backward_impl="unknown")
    with pytest.raises(ValueError, match="token_chunk"):
        linear_cross_entropy_fused_triton(x, w, y, token_chunk=0)


@pytest.mark.parametrize("token_chunk", [1, 17, 128])
def test_chunked_backward_matches_recompute_with_scaled_retained_graph(device, token_chunk):
    _require_cuda(device)
    torch.manual_seed(53)
    x = torch.randn(37, 70, device=device, requires_grad=True)
    w = torch.randn(257, 70, device=device, requires_grad=True)
    b = torch.randn(257, device=device, requires_grad=True)
    y = torch.randint(0, 257, (37,), device=device)
    y[::5] = -100
    ref_args = [p.detach().clone().requires_grad_() for p in (x, w, b)]
    ref = linear_cross_entropy_fused_triton(ref_args[0], ref_args[1], y, bias=ref_args[2],
                                           backward_impl="recompute")
    loss = linear_cross_entropy_fused_triton(x, w, y, bias=b, token_chunk=token_chunk)
    expected = torch.autograd.grad(ref * 1.7, ref_args)
    for _ in range(2):
        actual = torch.autograd.grad(loss * 1.7, (x, w, b), retain_graph=True)
        for got, want in zip(actual, expected):
            torch.testing.assert_close(got, want, atol=4e-5, rtol=4e-5)


@pytest.mark.parametrize("hidden", [32, 256])
def test_projection_is_once_per_chunk_and_scratch_is_bounded(device, hidden, monkeypatch):
    _require_cuda(device)
    calls = []
    original = ce._chunk_dlogits

    class RecordProjection:
        def __getitem__(self, grid):
            launch = original[grid]

            def run(*args, **kwargs):
                calls.append((grid, args[8], tuple(args[7].shape)))
                return launch(*args, **kwargs)
            return run

    monkeypatch.setattr(ce, "_chunk_dlogits", RecordProjection())
    x = torch.randn(35, hidden, device=device, requires_grad=True)
    w = torch.randn(257, hidden, device=device, requires_grad=True)
    y = torch.randint(0, 257, (35,), device=device)
    loss = linear_cross_entropy_fused_triton(x, w, y, token_chunk=16)
    loss.backward()
    # Both hidden sizes use exactly three projection launches, not one per
    # hidden output tile. All launches reuse a 16x257 derivative scratch buffer.
    assert [c for _, c, _ in calls] == [16, 16, 3]
    assert all(shape == (16, 257) for _, _, shape in calls)
    assert all(len(grid) == 2 for grid, _, _ in calls)


@pytest.mark.parametrize("device", [torch.device("cuda")])
def test_triton_pair_rejects_101_percent_error(device):
    if not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    with pytest.raises(AssertionError):
        check(PAIRS["ce.triton"], device, fast_override=scaled(1.01))


@pytest.mark.parametrize("name", pairs_in(__name__))
@pytest.mark.parametrize("device", [torch.device("cuda")])
def test_pair(name, device):
    if not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    check(PAIRS[name], device)
