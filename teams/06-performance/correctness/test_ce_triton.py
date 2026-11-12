"""Correctness coverage for the in-repo Triton linear CE backend."""
from __future__ import annotations

import pytest
import numpy as np
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


@pytest.mark.parametrize("n,h,v", [(5, 13, 53), (11, 13, 53), (17, 65, 129),
                                    (37, 70, 513)])
@pytest.mark.parametrize("mask", ["none", "partial", "all"])
@pytest.mark.parametrize("backward_impl", ["auto", "vocab", "chunked", "recompute"])
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
@pytest.mark.parametrize("backward_impl", ["auto", "vocab", "chunked", "recompute"])
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
@pytest.mark.parametrize("backward_impl", ["auto", "chunked", "recompute"])
def test_triton_native_low_precision_matches_torch(device, dtype, backward_impl):
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
    got = linear_cross_entropy_fused_triton(x, weight, targets, token_chunk=3,
                                           vocab_chunk=33, backward_impl=backward_impl)
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
    with pytest.raises(TypeError, match="fp16, bf16, or fp32"):
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
    loss = linear_cross_entropy_fused_triton(x, w, y, bias=b, token_chunk=token_chunk,
                                            backward_impl="chunked")
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
                calls.append((grid, args[6], tuple(args[5].shape), args[9]))
                return launch(*args, **kwargs)
            return run

    monkeypatch.setattr(ce, "_chunk_dlogits", RecordProjection())
    x = torch.randn(35, hidden, device=device, requires_grad=True)
    w = torch.randn(257, hidden, device=device, requires_grad=True)
    y = torch.randint(0, 257, (35,), device=device)
    loss = linear_cross_entropy_fused_triton(x, w, y, token_chunk=16, backward_impl="chunked")
    loss.backward()
    # Both hidden sizes use exactly three projection launches, not one per
    # hidden output tile. All launches reuse a 16x257 derivative scratch buffer.
    assert [c for _, c, _, _ in calls] == [16, 16, 3]
    assert all(shape == (16, 257) for _, _, shape, _ in calls)
    assert all(len(grid) == 2 for grid, _, _, _ in calls)


def test_scratch_plans_are_bounded_independently_of_total_tokens():
    budget = 64 * 1024**2
    for n, v in [(4096, 131072), (65537, 131072), (131072, 513)]:
        for mode in ("auto", "vocab", "chunked"):
            direction, size = ce.streaming_plan(n, v, 2048, 4096, budget, mode)
            elements = n * size if direction == "vocab" else size * v
            assert elements * 4 <= budget
        nt = (v + ce.BV - 1) // ce.BV
        assert ce.forward_chunk_rows(n, nt, budget) * nt * 12 <= budget


@pytest.mark.parametrize("mode", ["vocab", "chunked", "recompute"])
@pytest.mark.parametrize("needs", [(True, False, False), (False, True, False),
                                  (False, False, True), (True, False, True)])
def test_frozen_inputs_skip_unneeded_products(device, mode, needs, monkeypatch):
    _require_cuda(device)
    torch.manual_seed(59)
    args = [torch.randn(17, 65, device=device, requires_grad=needs[0]),
            torch.randn(129, 65, device=device, requires_grad=needs[1]),
            torch.randn(129, device=device, requires_grad=needs[2])]
    refs = [p.detach().clone().requires_grad_(flag) for p, flag in zip(args, needs)]
    y = torch.randint(0, 129, (17,), device=device)

    class Forbidden:
        def __getitem__(self, grid):
            raise AssertionError("unneeded product kernel was launched")

    if not needs[0]:
        monkeypatch.setattr(ce, "_grad_x" if mode == "recompute" else "_chunk_dx", Forbidden())
    if not needs[1] and not needs[2]:
        monkeypatch.setattr(ce, "_grad_w" if mode == "recompute" else "_chunk_dw", Forbidden())
    actual_loss = linear_cross_entropy_fused_triton(args[0], args[1], y, bias=args[2],
                                                   backward_impl=mode, token_chunk=7, vocab_chunk=33)
    ref_loss = F.cross_entropy(F.linear(*refs), y)
    selected = [i for i, flag in enumerate(needs) if flag]
    actual = torch.autograd.grad(actual_loss, [args[i] for i in selected])
    expected = torch.autograd.grad(ref_loss, [refs[i] for i in selected])
    for a, b in zip(actual, expected):
        torch.testing.assert_close(a, b, atol=4e-5, rtol=4e-5)


def test_vocab_streaming_writes_each_weight_slice_once(device, monkeypatch):
    _require_cuda(device)
    calls = []
    original = ce._chunk_dw

    class RecordDW:
        def __getitem__(self, grid):
            launch = original[grid]

            def run(*args, **kwargs):
                calls.append((args[2].data_ptr(), args[9], args[10]))
                return launch(*args, **kwargs)
            return run

    monkeypatch.setattr(ce, "_chunk_dw", RecordDW())
    x = torch.randn(17, 65, device=device, requires_grad=True)
    w = torch.randn(129, 65, device=device, requires_grad=True)
    y = torch.randint(0, 129, (17,), device=device)
    linear_cross_entropy_fused_triton(x, w, y, backward_impl="vocab", vocab_chunk=33).backward()
    assert len(calls) == 4
    assert len({ptr for ptr, _, _ in calls}) == 4
    assert all(first and scale_now for _, first, scale_now in calls)


def test_fp16_large_mean_does_not_round_away_non_target_gradients(device):
    _require_cuda(device)
    n, v = 65537, 513
    x = torch.ones(n, 1, device=device)
    w = torch.zeros(v, 1, device=device, requires_grad=True)
    y = torch.zeros(n, dtype=torch.long, device=device)
    with torch.autocast("cuda", dtype=torch.float16):
        loss = linear_cross_entropy_fused_triton(x, w, y, backward_impl="chunked", token_chunk=2048)
    dw = torch.autograd.grad(loss, w)[0]
    expected = torch.full_like(dw, 1. / v)
    expected[0] -= 1
    assert (dw[1:] > 0).all()
    torch.testing.assert_close(dw, expected, atol=3e-5, rtol=3e-3)


@pytest.mark.parametrize("bad", [-1, 129])
def test_target_debug_validation_and_unchecked_nan(device, bad):
    _require_cuda(device)
    x = torch.randn(3, 17, device=device)
    w = torch.randn(129, 17, device=device)
    y = torch.tensor([0, bad, -100], device=device)
    with pytest.raises(ValueError, match="outside vocabulary"):
        linear_cross_entropy_fused_triton(x, w, y, validate_targets=True)
    assert torch.isnan(linear_cross_entropy_fused_triton(x, w, y))


def test_positive_ignore_index_and_numpy_integer_arguments(device):
    _require_cuda(device)
    x = torch.randn(17, 65, device=device, requires_grad=True)
    w = torch.randn(129, 65, device=device, requires_grad=True)
    y = torch.randint(0, 129, (17,), device=device)
    y[::3] = 2
    args = [p.detach().clone().requires_grad_() for p in (x, w)]
    got = linear_cross_entropy_fused_triton(x, w, y, ignore_index=2, token_chunk=np.int64(7),
                                           vocab_chunk=np.int64(33), validate_targets=True)
    ref = F.cross_entropy(F.linear(*args), y, ignore_index=2)
    torch.testing.assert_close(got, ref, atol=2e-5, rtol=2e-5)
    for a, b in zip(torch.autograd.grad(got, (x, w)), torch.autograd.grad(ref, args)):
        torch.testing.assert_close(a, b, atol=4e-5, rtol=4e-5)


def test_forward_streams_partial_statistics_and_reuses_compute_cast(device, monkeypatch):
    _require_cuda(device)
    calls, weight_ptrs = [], []
    fwd, project = ce._forward, ce._chunk_dlogits
    monkeypatch.setattr(ce, "forward_chunk_rows", lambda n, nt, budget: min(n, 3))

    class Forward:
        def __getitem__(self, grid):
            launch = fwd[grid]

            def run(*args, **kw):
                calls.append((args[7], args[4].shape[0]))
                weight_ptrs.append(args[1].data_ptr())
                return launch(*args, **kw)
            return run

    class Backward:
        def __getitem__(self, grid):
            launch = project[grid]

            def run(*args, **kw):
                weight_ptrs.append(args[1].data_ptr())
                return launch(*args, **kw)
            return run

    monkeypatch.setattr(ce, "_forward", Forward())
    monkeypatch.setattr(ce, "_chunk_dlogits", Backward())
    x = torch.randn(7, 17, device=device, requires_grad=True)
    w = torch.randn(129, 17, device=device, requires_grad=True)
    y = torch.randint(0, 129, (7,), device=device)
    with torch.autocast("cuda", dtype=torch.float16):
        loss = linear_cross_entropy_fused_triton(x, w, y, backward_impl="chunked", token_chunk=3)
    loss.backward()
    assert calls == [(3, 3), (3, 3), (1, 3)]
    assert len(set(weight_ptrs)) == 1


def test_triton_double_backward_is_explicitly_unsupported(device):
    _require_cuda(device)
    x = torch.randn(7, 17, device=device, requires_grad=True)
    w = torch.randn(129, 17, device=device, requires_grad=True)
    y = torch.randint(0, 129, (7,), device=device)
    loss = linear_cross_entropy_fused_triton(x, w, y)
    dx = torch.autograd.grad(loss, x, create_graph=True)[0]
    with pytest.raises(RuntimeError):
        torch.autograd.grad(dx.sum(), x)


@pytest.mark.parametrize("mode", ["auto", "chunked", "recompute"])
def test_gradients_are_bitwise_repeatable(device, mode):
    _require_cuda(device)
    x = torch.randn(17, 65, device=device, requires_grad=True)
    w = torch.randn(129, 65, device=device, requires_grad=True)
    b = torch.randn(129, device=device, requires_grad=True)
    y = torch.randint(0, 129, (17,), device=device)
    loss = linear_cross_entropy_fused_triton(x, w, y, bias=b, backward_impl=mode,
                                            token_chunk=7, vocab_chunk=33)
    first = torch.autograd.grad(loss, (x, w, b), retain_graph=True)
    second = torch.autograd.grad(loss, (x, w, b))
    assert all(torch.equal(a, b) for a, b in zip(first, second))


def test_fp32_gradient_mode_with_native_bf16(device):
    _require_cuda(device)
    if not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    x = (torch.randn(17, 65, device=device, dtype=torch.bfloat16) * 0.1).requires_grad_()
    w = (torch.randn(129, 65, device=device, dtype=torch.bfloat16) * 0.1).requires_grad_()
    xr, wr = (p.detach().clone().requires_grad_() for p in (x, w))
    y = torch.randint(0, 129, (17,), device=device)
    actual = linear_cross_entropy_fused_triton(x, w, y, grad_precision="fp32", vocab_chunk=33)
    # The kernel keeps the projection's fp32 accumulator rather than rounding
    # logits back to bf16. This is the corresponding mathematical reference.
    expected = F.cross_entropy(F.linear(xr.float(), wr.float()), y)
    torch.testing.assert_close(actual, expected, atol=2e-5, rtol=2e-5)
    for a, b in zip(torch.autograd.grad(actual, (x, w)), torch.autograd.grad(expected, (xr, wr))):
        torch.testing.assert_close(a, b, atol=2e-4, rtol=1e-2)


if ce.triton is not None:
    from triton import language as tl
    from kernels.linear_ce_fused import _offset

    @ce.triton.jit
    def _probe_offsets(ROWS, OUT, STRIDE: tl.constexpr):
        i = tl.arange(0, 4)
        row = tl.load(ROWS + i)
        tl.store(OUT + i, _offset(row, i, STRIDE))


@pytest.mark.parametrize("stride", [1024, 4096])
def test_offsets_cross_int32_boundary_without_a_large_allocation(device, stride):
    _require_cuda(device)
    rows = torch.tensor([2**21, 2**24, 2**31 - 1, 2**31 + 7], device=device, dtype=torch.int64)
    out = torch.empty_like(rows)
    with torch.cuda.device(device):
        _probe_offsets[(1,)](rows, out, stride, enable_fp_fusion=True)
    torch.testing.assert_close(out, rows * stride + torch.arange(4, device=device), atol=0, rtol=0)


def test_frozen_head_does_not_allocate_a_weight_gradient(device, monkeypatch):
    _require_cuda(device)
    x = torch.randn(17, 65, device=device, requires_grad=True)
    w = torch.randn(129, 65, device=device)
    y = torch.randint(0, 129, (17,), device=device)
    loss = linear_cross_entropy_fused_triton(x, w, y, vocab_chunk=33)
    original, shapes = torch.empty, []

    def allocate(shape, *args, **kwargs):
        if isinstance(shape, (tuple, list, torch.Size)):
            shapes.append(tuple(shape))
        return original(shape, *args, **kwargs)

    monkeypatch.setattr(torch, "empty", allocate)
    loss.backward()
    assert (129, 65) not in shapes
    assert x.grad is not None and w.grad is None


def test_noncurrent_cuda_device(device):
    _require_cuda(device)
    if torch.cuda.device_count() < 2:
        pytest.skip("requires two CUDA devices")
    with torch.cuda.device(0):
        x = torch.randn(17, 65, device="cuda:1", requires_grad=True)
        w = torch.randn(129, 65, device="cuda:1", requires_grad=True)
        y = torch.randint(0, 129, (17,), device="cuda:1")
        loss = linear_cross_entropy_fused_triton(x, w, y)
        loss.backward()
        assert torch.cuda.current_device() == 0
        assert x.grad.device == w.grad.device == torch.device("cuda:1")


@pytest.mark.parametrize("vocab", [3, 131072])
def test_auto_streaming_in_both_directions_and_real_vocabulary(device, vocab):
    _require_cuda(device)
    torch.manual_seed(61)
    x = torch.randn(17, 65, device=device, requires_grad=True)
    w = (torch.randn(vocab, 65, device=device) * 0.1).requires_grad_()
    xr, wr = (p.detach().clone().requires_grad_() for p in (x, w))
    y = torch.randint(0, vocab, (17,), device=device)
    y[::5] = -100
    y[-1] = vocab - 1
    got = linear_cross_entropy_fused_triton(x, w, y)
    expected = F.cross_entropy(F.linear(xr, wr), y)
    torch.testing.assert_close(got, expected, atol=3e-5, rtol=3e-5)
    for a, b in zip(torch.autograd.grad(got, (x, w)), torch.autograd.grad(expected, (xr, wr))):
        torch.testing.assert_close(a, b, atol=4e-5, rtol=4e-5)


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
