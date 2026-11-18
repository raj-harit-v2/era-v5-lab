"""Standalone variable-row expert GEMM against independent per-expert linear ops."""
from __future__ import annotations

import pytest
import torch
import torch.nn.functional as F

from correctness.framework import PAIRS, Case, check, pair, pairs_in, scaled
from kernels import grouped_gemm as gg
from kernels.moe_dispatch import RouteMap, pack_tokens, combine_tokens

parametrize = pytest.mark.parametrize


def _cuda(device):
    if device.type != "cuda" or gg.triton is None:
        pytest.skip("grouped GEMM requires CUDA and Triton")


def _offsets(counts, device):
    return torch.tensor([0, *counts], dtype=torch.int64, device=device).cumsum(0)


def _reference(x, weight, counts, bias=None):
    pieces, start = [], 0
    for expert, count in enumerate(counts):
        pieces.append(F.linear(x[start:start + count], weight[expert],
                               None if bias is None else bias[expert]))
        start += count
    return torch.cat(pieces)


@pair("moe_kernel.grouped_linear", tol=1e-5, grad_tol=5e-5)
def _grouped_pair(device):
    _cuda(device)
    torch.manual_seed(129)
    counts = [0, 3, 1, 5]
    x = torch.randn(sum(counts), 17, device=device, requires_grad=True)
    w = (torch.randn(4, 35, 17, device=device) * 0.1).requires_grad_()
    bias = (torch.randn(4, 35, device=device) * 0.1).requires_grad_()
    segments = gg.ExpertSegments(_offsets(counts, device), sum(counts))
    return Case(ref=lambda a, b, c: _reference(a, b, counts, c),
                fast=lambda a, b, c: gg.grouped_linear(a, b, segments, c), inputs=[x, w, bias])


@pair("moe_kernel.grouped_linear.split_rows", tol=1e-5, grad_tol=5e-5)
def _split_grouped_pair(device):
    case = _grouped_pair(device)
    segments = gg.ExpertSegments(_offsets([0, 3, 1, 5], device), 9)
    case.fast = lambda a, b, c: gg.grouped_linear(a, b, segments, c, split_r=4)
    return case


@parametrize("name", pairs_in(__name__))
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    assert all(key in errors for key in ("out[0]", "grad_in[0]", "grad_in[1]", "grad_in[2]"))


@parametrize("name", pairs_in(__name__))
def test_pair_rejects_one_percent_error(name, device):
    with pytest.raises(AssertionError, match=r"out\[0\].*rel_err"):
        check(PAIRS[name], device, fast_override=scaled(1.01))


@parametrize("case", [([1, 0], 1, 1), ([0, 1, 0, 2], 17, 33), ([37], 65, 70),
                      ([33, 0, 2, 67], 33, 65), ([1, 0, 129, 2], 70, 35), ([0, 0], 3, 5)])
@parametrize("dtype", [torch.float32, torch.float16, torch.bfloat16])
def test_forward_backward_tails_idle_experts_and_empty_rows(device, case, dtype):
    _cuda(device)
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    counts, inner, width = case
    torch.manual_seed(131)
    x = torch.randn(sum(counts), inner, device=device, dtype=dtype, requires_grad=True)
    w = (torch.randn(len(counts), width, inner, device=device, dtype=dtype) * 0.1).requires_grad_()
    bias = torch.randn(len(counts), width, device=device, requires_grad=True)
    xr, wr, br = (a.detach().double().requires_grad_() for a in (x, w, bias))
    got = gg.grouped_linear(x, w, _offsets(counts, device), bias)
    ref = _reference(xr, wr, counts, br)
    cot = torch.randn_like(got) * 2.7
    actual = torch.autograd.grad(got, (x, w, bias), cot)
    expected = torch.autograd.grad(ref, (xr, wr, br), cot.double())
    tol = 3e-2 if dtype == torch.bfloat16 else 3e-3 if dtype == torch.float16 else 5e-5
    torch.testing.assert_close(got, ref.to(dtype), atol=tol, rtol=tol)
    for a, b in zip(actual, expected):
        torch.testing.assert_close(a, b.to(a.dtype), atol=tol, rtol=tol)
    for e, count in enumerate(counts):
        if count == 0:
            assert torch.count_nonzero(actual[1][e]) == 0
            assert torch.count_nonzero(actual[2][e]) == 0


def test_no_bias_strided_inputs_weights_and_cotangent(device):
    _cuda(device)
    counts = [2, 0, 7]
    x = torch.randn(17, 9, device=device).T.requires_grad_()
    w = torch.randn(3, 17, 35, device=device).transpose(1, 2).requires_grad_()
    offsets = _offsets(counts, device).repeat_interleave(2)[::2]
    assert not x.is_contiguous() and not w.is_contiguous() and not offsets.is_contiguous()
    got = gg.grouped_linear(x, w, offsets)
    ref = _reference(x.double(), w.double(), counts)
    cot = torch.randn(35, 9, device=device).T
    torch.testing.assert_close(got, ref.float(), atol=3e-5, rtol=3e-5)
    for a, b in zip(torch.autograd.grad(got, (x, w), cot),
                    torch.autograd.grad(ref, (x, w), cot.double())):
        torch.testing.assert_close(a, b, atol=5e-5, rtol=5e-5)


@parametrize("needs", [(True, False, False), (False, True, False),
                       (False, False, True), (True, True, True)])
def test_frozen_inputs_and_repeatability(device, needs, monkeypatch):
    _cuda(device)
    counts = [1, 0, 4]
    x = torch.randn(5, 17, device=device, requires_grad=needs[0])
    w = torch.randn(3, 33, 17, device=device, requires_grad=needs[1])
    bias = torch.randn(3, 66, device=device)[:, ::2].requires_grad_(needs[2])
    segments = gg.ExpertSegments(_offsets(counts, device), 5)
    if not needs[1]:
        class NoWeightGradient:
            def __getitem__(self, grid):
                raise AssertionError("frozen weights should not launch weight-gradient GEMM")
        monkeypatch.setattr(gg, "_weight_backward", NoWeightGradient())
    watched = [a for a in (x, w, bias) if a.requires_grad]
    cot = torch.randn(5, 33, device=device)
    runs = []
    for _ in range(2):
        got = gg.grouped_linear(x, w, segments, bias)
        runs.append((got, *torch.autograd.grad(got, watched, cot)))
    for a, b in zip(*runs):
        assert torch.equal(a, b)
    ref = _reference(x.double(), w.double(), counts, bias.double())
    for a, b in zip(runs[0][1:], torch.autograd.grad(ref, watched, cot.double())):
        torch.testing.assert_close(a, b, atol=3e-5, rtol=3e-5)


def test_prepared_segments_reuse_and_mutation_guards(device, monkeypatch):
    _cuda(device)
    offsets = _offsets([2, 0, 3], device)
    segments = gg.ExpertSegments(offsets, 5)
    offsets.zero_()
    assert torch.equal(segments.offsets, _offsets([2, 0, 3], device))

    def no_validation(*args):
        raise AssertionError("prepared boundaries should not validate again")

    monkeypatch.setattr(gg, "_validate_offsets", no_validation)
    x = torch.randn(5, 17, device=device, requires_grad=True)
    w = torch.randn(3, 19, 17, device=device, requires_grad=True)
    got = gg.grouped_linear(x, w, segments)
    segments.offsets.add_(0)
    with pytest.raises(RuntimeError, match="metadata was modified"):
        gg.grouped_linear(x, w, segments)
    with pytest.raises(RuntimeError, match="modified by an inplace operation"):
        got.sum().backward()


def test_tf32x3_precision_matches_reference(device):
    _cuda(device)
    if torch.cuda.get_device_capability()[0] < 8:
        pytest.skip("tf32x3 requires supported tensor-core instructions")
    counts = [5, 0, 34]
    x = torch.randn(39, 65, device=device, requires_grad=True)
    w = torch.randn(3, 70, 65, device=device, requires_grad=True)
    got = gg.grouped_linear(x, w, _offsets(counts, device), precision="tf32x3")
    ref = _reference(x.double(), w.double(), counts)
    torch.testing.assert_close(got, ref.float(), atol=5e-5, rtol=5e-5)
    cot = torch.randn_like(got)
    for a, b in zip(torch.autograd.grad(got, (x, w), cot),
                    torch.autograd.grad(ref, (x, w), cot.double())):
        torch.testing.assert_close(a, b, atol=8e-5, rtol=8e-5)


def test_persistent_workers_cross_experts_and_tile_iterations(device, monkeypatch):
    _cuda(device)
    # Limit workers so each must process several tiles and traverse idle experts.
    monkeypatch.setattr(gg, "_sm_count", lambda index: 1)
    counts = [33] + [0] * 14 + [65]
    x = torch.randn(98, 17, device=device, requires_grad=True)
    w = torch.randn(16, 33, 17, device=device, requires_grad=True)
    bias = torch.randn(16, 33, device=device, requires_grad=True)
    out = gg.grouped_linear(x, w, _offsets(counts, device), bias)
    ref = _reference(x.double(), w.double(), counts, bias.double())
    torch.testing.assert_close(out, ref.float(), atol=3e-5, rtol=3e-5)
    cot = torch.randn_like(out)
    for a, b in zip(torch.autograd.grad(out, (x, w, bias), cot),
                    torch.autograd.grad(ref, (x, w, bias), cot.double())):
        torch.testing.assert_close(a, b, atol=5e-5, rtol=5e-5)


@parametrize("dtype", [torch.float16, torch.bfloat16])
def test_low_precision_bias_and_explicit_autocast_contract(device, dtype):
    _cuda(device)
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    x = torch.randn(5, 17, device=device, dtype=dtype, requires_grad=True)
    w = torch.randn(2, 33, 17, device=device, dtype=dtype, requires_grad=True)
    bias = torch.randn(2, 33, device=device, dtype=dtype, requires_grad=True)
    offsets = _offsets([2, 3], device)
    with torch.autocast("cuda", dtype=dtype):
        out = gg.grouped_linear(x, w, offsets, bias)
    assert out.dtype == dtype
    ref = _reference(x.double(), w.double(), [2, 3], bias.double())
    tol = 3e-2 if dtype == torch.bfloat16 else 3e-3
    torch.testing.assert_close(out, ref.to(dtype), atol=tol, rtol=tol)
    cot = torch.randn_like(out)
    for a, b in zip(torch.autograd.grad(out, (x, w, bias), cot),
                    torch.autograd.grad(ref, (x, w, bias), cot.double())):
        assert a.dtype == dtype
        torch.testing.assert_close(a, b, atol=tol, rtol=tol)
    with torch.autocast("cuda", dtype=dtype):
        fp32 = gg.grouped_linear(x.float(), w.float(), offsets, bias.float())
    assert fp32.dtype == torch.float32


def test_pack_grouped_linear_combine_pipeline(device):
    _cuda(device)
    assignments = torch.tensor([[0, 2], [2, 0], [0, 3], [3, 2], [2, 0]])
    counts = torch.bincount(assignments.flatten(), minlength=4).tolist()
    order = assignments.flatten().argsort(stable=True).to(device)
    routes = RouteMap(order, top_k=2)
    segments = gg.ExpertSegments(_offsets(counts, device), 10)
    x = torch.randn(5, 17, device=device, requires_grad=True)
    w = torch.randn(4, 9, 17, device=device, requires_grad=True)
    gates = torch.rand(5, 2, device=device, requires_grad=True)
    got = combine_tokens(gg.grouped_linear(pack_tokens(x, routes, 2), w, segments), gates, routes)
    rows = []
    for token in range(5):
        rows.append(sum(gates[token, slot].double() * F.linear(x[token].double(),
                    w[int(assignments[token, slot])].double()) for slot in range(2)))
    ref = torch.stack(rows)
    torch.testing.assert_close(got, ref.float(), atol=3e-5, rtol=3e-5)
    cot = torch.randn_like(got)
    for a, b in zip(torch.autograd.grad(got, (x, w, gates), cot),
                    torch.autograd.grad(ref, (x, w, gates), cot.double())):
        torch.testing.assert_close(a, b, atol=5e-5, rtol=5e-5)


@parametrize("bad", [[1, 2, 5], [0, 4, 3], [0, -1, 5], [0, 2, 6]])
def test_invalid_boundaries_rejected_before_launch(device, bad):
    _cuda(device)
    offsets = torch.tensor(bad, device=device)
    with pytest.raises(ValueError, match="nondecreasing"):
        gg.grouped_linear(torch.zeros(5, 3, device=device), torch.zeros(2, 7, 3, device=device), offsets)
    with pytest.raises(ValueError, match="nondecreasing"):
        gg.ExpertSegments(offsets, 5)


def test_device_and_bias_guards(device):
    _cuda(device)
    x = torch.randn(5, 3, device=device)
    w = torch.randn(2, 7, 3, device=device)
    offsets = _offsets([2, 3], device)
    with pytest.raises(ValueError, match="same device"):
        gg.grouped_linear(x, w.cpu(), offsets)
    with pytest.raises(ValueError, match="same device"):
        gg.grouped_linear(x, w, offsets.cpu())
    with pytest.raises(ValueError, match="bias must"):
        gg.grouped_linear(x, w, offsets, torch.zeros(2, 7))
    with pytest.raises(ValueError, match="bias must"):
        gg.grouped_linear(x, w, offsets, torch.zeros(2, 7, device=device, dtype=torch.float64))


def test_zero_expert_segments_rejected(device):
    _cuda(device)
    with pytest.raises(ValueError, match="at least one expert"):
        gg.ExpertSegments(torch.tensor([0], device=device), 0)


def test_unchecked_offsets_and_prepared_segments_match(device):
    _cuda(device)
    counts = [2, 0, 3]
    offsets = _offsets(counts, device)
    x = torch.randn(5, 17, device=device, requires_grad=True)
    w = torch.randn(3, 9, 17, device=device, requires_grad=True)
    bias = torch.randn(3, 9, device=device, requires_grad=True)
    segments = gg.ExpertSegments(offsets, 5, validate_offsets=False)
    checked = gg.grouped_linear(x, w, offsets, bias)
    raw = gg.grouped_linear(x, w, offsets, bias, validate_offsets=False)
    prepared = gg.grouped_linear(x, w, segments, bias)
    assert torch.equal(checked, raw) and torch.equal(checked, prepared)
    cot = torch.randn_like(checked)
    expected = torch.autograd.grad(checked, (x, w, bias), cot)
    for out in (raw, prepared):
        got = torch.autograd.grad(out, (x, w, bias), cot)
        for a, b in zip(got, expected):
            assert torch.equal(a, b)


def test_validate_offsets_false_skips_validation(device, monkeypatch):
    _cuda(device)
    def no_validation(*args):
        raise AssertionError("validate_offsets=False must skip boundary validation")
    monkeypatch.setattr(gg, "_validate_offsets", no_validation)
    offsets = _offsets([2, 3], device)
    gg.grouped_linear(torch.zeros(5, 3, device=device), torch.zeros(2, 7, 3, device=device),
                      offsets, validate_offsets=False)
    gg.ExpertSegments(offsets, 5, validate_offsets=False)


def test_segment_shape_mismatch_and_index_dtypes(device):
    _cuda(device)
    x = torch.randn(5, 3, device=device)
    w = torch.randn(2, 7, 3, device=device)
    offsets = _offsets([2, 3], device)
    assert torch.equal(gg.grouped_linear(x, w, offsets), gg.grouped_linear(x, w, offsets.int()))
    segments = gg.ExpertSegments(_offsets([2, 2], device), 4)
    with pytest.raises(ValueError, match="row/expert count"):
        gg.grouped_linear(x, w, segments)


def test_double_backward_is_explicitly_unsupported(device):
    _cuda(device)
    x = torch.randn(3, 5, device=device, requires_grad=True)
    w = torch.randn(2, 7, 5, device=device, requires_grad=True)
    out = gg.grouped_linear(x, w, _offsets([1, 2], device))
    dx, = torch.autograd.grad(out.square().sum(), (x,), create_graph=True)
    with pytest.raises(RuntimeError):
        torch.autograd.grad(dx.sum(), x)


def test_noncurrent_cuda_device(device):
    _cuda(device)
    if torch.cuda.device_count() < 2:
        pytest.skip("requires two CUDA devices")
    with torch.cuda.device(0):
        other = torch.device("cuda:1")
        x = torch.randn(3, 5, device=other, requires_grad=True)
        w = torch.randn(2, 7, 5, device=other, requires_grad=True)
        gg.grouped_linear(x, w, _offsets([1, 2], other)).sum().backward()
        assert torch.cuda.current_device() == 0 and x.grad.device == other


def test_shape_dtype_and_cpu_guards():
    x, w, offsets = torch.zeros(5, 3), torch.zeros(2, 7, 3), torch.tensor([0, 2, 5])
    with pytest.raises(ValueError, match="x must"):
        gg.grouped_linear(x.flatten(), w, offsets)
    with pytest.raises(ValueError, match="matching input widths"):
        gg.grouped_linear(x, torch.zeros(2, 7, 4), offsets)
    with pytest.raises(ValueError, match="share an fp16"):
        gg.grouped_linear(x.double(), w.double(), offsets)
    with pytest.raises(ValueError, match="share an fp16"):
        gg.grouped_linear(x, w.half(), offsets)
    with pytest.raises(ValueError, match="bias must"):
        gg.grouped_linear(x, w, offsets, torch.zeros(2, 8))
    with pytest.raises(ValueError, match="shape"):
        gg.grouped_linear(x, w, torch.tensor([0, 5]))
    with pytest.raises(ValueError, match="int32 or int64"):
        gg.grouped_linear(x, w, offsets.float())
    with pytest.raises(ValueError, match="precision must"):
        gg.grouped_linear(x, w, offsets, precision="invalid")
    with pytest.raises(ValueError, match="requires CUDA and Triton"):
        gg.grouped_linear(x, w, offsets)


@parametrize("bad", [-1, True, 1.5])
def test_invalid_row_count_on_cpu(bad):
    with pytest.raises(ValueError, match="num_rows"):
        gg.ExpertSegments(torch.tensor([0, 0]), bad)


def test_cpu_backend_rejection_precedes_boundary_validation(monkeypatch):
    def no_validation(*args):
        raise AssertionError("unsupported backends must fail without synchronization")
    monkeypatch.setattr(gg, "_validate_offsets", no_validation)
    with pytest.raises(ValueError, match="requires CUDA and Triton"):
        gg.ExpertSegments(torch.tensor([0, 5]), 5)
    with pytest.raises(ValueError, match="requires CUDA and Triton"):
        gg.grouped_linear(torch.zeros(5, 3), torch.zeros(1, 7, 3), torch.tensor([0, 5]))


@parametrize("dtype", [torch.float32, torch.float16, torch.bfloat16])
@parametrize("splits", [2, 4, 32])
def test_split_rows_all_gradients_and_repeatability(device, dtype, splits):
    _cuda(device)
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    torch.manual_seed(141)
    counts = [0, 513, 1, 0, 35]
    x = torch.randn(sum(counts), 65, device=device, dtype=dtype, requires_grad=True)
    w = (torch.randn(5, 70, 65, device=device, dtype=dtype) * .1).requires_grad_()
    b = torch.randn(5, 70, device=device, requires_grad=True)
    segments = gg.ExpertSegments(_offsets(counts, device), sum(counts))
    cot = torch.randn(sum(counts), 70, device=device, dtype=dtype)
    runs = []
    for _ in range(2):
        out = gg.grouped_linear(x, w, segments, b, split_r=splits)
        runs.append((out, *torch.autograd.grad(out, (x, w, b), cot)))
    for a, c in zip(*runs):
        assert torch.equal(a, c)
    xr, wr, br = (a.detach().double().requires_grad_() for a in (x, w, b))
    ref = _reference(xr, wr, counts, br)
    expected = (ref, *torch.autograd.grad(ref, (xr, wr, br), cot.double()))
    tol = .03 if dtype == torch.bfloat16 else .003 if dtype == torch.float16 else 5e-5
    for a, c in zip(runs[0], expected):
        torch.testing.assert_close(a, c.to(a.dtype), atol=tol, rtol=tol)
    # Same operands and cotangent as the original single-pass implementation.
    direct = gg.grouped_linear(x, w, segments, b, split_r=1)
    direct_results = (direct, *torch.autograd.grad(direct, (x, w, b), cot))
    for a, c in zip(runs[0], direct_results):
        torch.testing.assert_close(a, c, atol=tol, rtol=tol)


def test_snapshot_is_validated_after_clone(device, monkeypatch):
    _cuda(device)
    source = _offsets([2, 3], device)
    validate = gg._validate_offsets

    def inspect(snapshot, rows):
        assert snapshot.data_ptr() != source.data_ptr()
        source.zero_()
        validate(snapshot, rows)

    monkeypatch.setattr(gg, "_validate_offsets", inspect)
    segments = gg.ExpertSegments(source, 5)
    assert torch.equal(segments.offsets, _offsets([2, 3], device))


def test_tf32_precision_has_explicit_relaxed_error_budget(device):
    _cuda(device)
    if torch.cuda.get_device_capability()[0] < 8:
        pytest.skip("tf32 requires supported tensor-core instructions")
    torch.manual_seed(145)
    counts = [0, 67, 3]
    x = torch.randn(70, 65, device=device, requires_grad=True)
    w = torch.randn(3, 70, 65, device=device, requires_grad=True)
    got = gg.grouped_linear(x, w, _offsets(counts, device), precision="tf32", split_r=2)
    xr, wr = (t.detach().double().requires_grad_() for t in (x, w))
    ref = _reference(xr, wr, counts)
    cot = torch.randn_like(got)
    actual = (got, *torch.autograd.grad(got, (x, w), cot))
    expected = (ref, *torch.autograd.grad(ref, (xr, wr), cot.double()))
    from correctness.framework import rel_err
    for a, b in zip(actual, expected):
        assert rel_err(a, b) < 2e-3


def test_large_low_precision_launch_bucket(device):
    _cuda(device)
    torch.manual_seed(147)
    counts = [129, 1]
    x = torch.randn(130, 65, device=device, dtype=torch.float16, requires_grad=True)
    w = torch.randn(2, 129, 65, device=device, dtype=torch.float16, requires_grad=True)
    got = gg.grouped_linear(x, w, _offsets(counts, device))
    ref = _reference(x.double(), w.double(), counts)
    cot = torch.randn_like(got)
    for a, b in zip((got, *torch.autograd.grad(got, (x, w), cot)),
                    (ref, *torch.autograd.grad(ref, (x, w), cot.double()))):
        torch.testing.assert_close(a, b.to(a.dtype), atol=.003, rtol=.003)


def test_prepared_segments_cuda_graph_forward_and_backward(device):
    _cuda(device)
    x = torch.randn(5, 17, device=device, requires_grad=True)
    w = torch.randn(3, 33, 17, device=device, requires_grad=True)
    segments = gg.ExpertSegments(_offsets([2, 0, 3], device), 5)

    def operation():
        out = gg.grouped_linear(x, w, segments, split_r=2)
        return out, *torch.autograd.grad(out, (x, w), torch.ones_like(out))

    stream = torch.cuda.Stream(device=device)
    stream.wait_stream(torch.cuda.current_stream(device))
    with torch.cuda.stream(stream):
        for _ in range(3):
            expected = operation()
    torch.cuda.current_stream(device).wait_stream(stream)
    graph = torch.cuda.CUDAGraph()
    with torch.cuda.graph(graph):
        actual = operation()
    graph.replay()
    for a, b in zip(actual, expected):
        assert torch.equal(a, b)


def test_launch_config_and_split_guards_on_cpu():
    assert gg.launch_config("project", 100, 4, 65, 70, torch.float32) == (32, 64, 32, 4, 2)
    assert gg.launch_config("project", 256, 4, 65, 70, torch.float16) == (64, 128, 32, 4, 3)
    assert gg.launch_config("weight_backward", 100, 4, 65, 70, torch.float32) == (64, 64, 32, 4, 2)
    with pytest.raises(ValueError, match="unknown operation"):
        gg.launch_config("invalid", 1, 1, 1, 1, torch.float32)
    for invalid in (0, -1, True, 1.5, 33):
        with pytest.raises(ValueError, match="split_r"):
            gg.grouped_linear(torch.zeros(1, 3), torch.zeros(1, 5, 3), torch.tensor([0, 1]), split_r=invalid)


def test_split_scratch_budget_on_cpu(monkeypatch):
    monkeypatch.setattr(gg, "MAX_SPLIT_SCRATCH", 1)
    with pytest.raises(ValueError, match="64 MiB"):
        gg.grouped_linear(torch.zeros(1, 3), torch.zeros(1, 5, 3, requires_grad=True),
                          torch.tensor([0, 1]), split_r=2)
