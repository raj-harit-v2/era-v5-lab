"""Standalone compact route permutation/combine; no model or optimizer integration."""
from __future__ import annotations

import pytest
import torch

from correctness.framework import PAIRS, Case, check, pair, pairs_in, scaled
from kernels import moe_dispatch as md

parametrize = pytest.mark.parametrize


def _cuda(device):
    if device.type != "cuda" or md.triton is None:
        pytest.skip("standalone MoE kernels require CUDA and Triton")


def _order(n, k, device):
    return torch.randperm(n * k, generator=torch.Generator().manual_seed(81)).to(device)


def _pack_ref(x, order, k):
    return x.index_select(0, torch.div(order, k, rounding_mode="floor"))


def _combine_ref(y, gates, order):
    n, k = gates.shape
    return (y[order.argsort()].reshape(n, k, y.shape[-1]) * gates[..., None]).sum(1)


@pair("moe_kernel.pack", tol=1e-5, grad_tol=5e-5)
def _pack_pair(device):
    _cuda(device)
    x = torch.randn(19, 513, device=device, requires_grad=True)
    order = _order(19, 2, device)
    return Case(ref=lambda a: _pack_ref(a, order, 2),
                fast=lambda a: md.pack_tokens(a, order, 2), inputs=[x])


@pair("moe_kernel.combine", tol=1e-5, grad_tol=5e-5)
def _combine_pair(device):
    _cuda(device)
    y = torch.randn(38, 513, device=device, requires_grad=True)
    gates = torch.rand(19, 2, device=device, requires_grad=True)
    order = _order(19, 2, device)
    return Case(ref=lambda a, g: _combine_ref(a, g, order),
                fast=lambda a, g: md.combine_tokens(a, g, order), inputs=[y, gates])


@parametrize("name", pairs_in(__name__))
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    assert "out[0]" in errors and "grad_in[0]" in errors
    if name.endswith("combine"):
        assert "grad_in[1]" in errors


@parametrize("name", pairs_in(__name__))
def test_pair_rejects_one_percent_error(name, device):
    with pytest.raises(AssertionError, match=r"out\[0\].*rel_err"):
        check(PAIRS[name], device, fast_override=scaled(1.01))


@parametrize("shape", [(1, 1, 1), (3, 3, 3), (3, 3, 17), (19, 2, 513), (5, 4, 1025),
                       (3, 8, 7168), (3, 16, 127), (2, 2, 8193)])
@parametrize("dtype", [torch.float32, torch.float16, torch.bfloat16])
def test_pack_and_combine_forward_backward(device, shape, dtype):
    _cuda(device)
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    n, k, d = shape
    torch.manual_seed(83)
    order = _order(n, k, device)
    x = torch.randn(n, d, device=device, dtype=dtype, requires_grad=True)
    xr = x.detach().double().requires_grad_()
    packed = md.pack_tokens(x, order, k)
    torch.testing.assert_close(packed, _pack_ref(x, order, k), atol=0, rtol=0)
    cot = torch.randn_like(packed) * 2.7
    dx, = torch.autograd.grad(packed, (x,), cot)
    dxr, = torch.autograd.grad(_pack_ref(xr, order, k), (xr,), cot.double())
    torch.testing.assert_close(dx, dxr.to(dtype), atol=2e-6, rtol=2e-6)

    y = torch.randn(n * k, d, device=device, dtype=dtype, requires_grad=True)
    # Real router gates are fp32 even when expert activations use a lower precision.
    gates = torch.rand(n, k, device=device, requires_grad=True)
    yr, gr = (v.detach().double().requires_grad_() for v in (y, gates))
    out = md.combine_tokens(y, gates, order)
    ref = _combine_ref(yr, gr, order)
    cot = torch.randn_like(out) * 3.1
    grads = torch.autograd.grad(out, (y, gates), cot)
    ref_grads = torch.autograd.grad(ref, (yr, gr), cot.double())
    tol = 3e-2 if dtype == torch.bfloat16 else 3e-3 if dtype == torch.float16 else 5e-5
    torch.testing.assert_close(out, ref.to(dtype), atol=tol, rtol=tol)
    for got, expected in zip(grads, ref_grads):
        torch.testing.assert_close(got, expected.to(got.dtype), atol=tol, rtol=tol)


def test_round_trip_and_gate_slot_mutation(device):
    _cuda(device)
    x = torch.randn(7, 33, device=device, requires_grad=True)
    gates = torch.softmax(torch.randn(7, 2, device=device), 1).requires_grad_()
    order = _order(7, 2, device)
    packed = md.pack_tokens(x, order, 2)
    # Route-specific expert output makes swapping gate slots detectable.
    expert_out = packed * (order[:, None] + 1)
    got = md.combine_tokens(expert_out, gates, order)
    expected = _combine_ref(_pack_ref(x, order, 2) * (order[:, None] + 1), gates, order)
    torch.testing.assert_close(got, expected)
    wrong = md.combine_tokens(expert_out, gates.flip(1), order)
    assert not torch.allclose(wrong, expected)
    actual_grad = torch.autograd.grad(got.sum(), (x, gates), retain_graph=True)
    expected_grad = torch.autograd.grad(expected.sum(), (x, gates))
    for a, b in zip(actual_grad, expected_grad):
        torch.testing.assert_close(a, b)


def test_noncontiguous_inputs_and_gradient(device):
    _cuda(device)
    x = torch.randn(5, 66, device=device)[:, ::2].requires_grad_()
    order = _order(5, 3, device).repeat_interleave(2)[::2]
    gates = torch.rand(5, 6, device=device)[:, ::2].requires_grad_()
    y = torch.randn(15, 66, device=device)[:, ::2].requires_grad_()
    assert not x.is_contiguous() and not gates.is_contiguous() and not order.is_contiguous()
    torch.testing.assert_close(md.pack_tokens(x, order, 3), _pack_ref(x, order, 3))
    actual = md.combine_tokens(y, gates, order)
    expected = _combine_ref(y, gates, order)
    dy = torch.randn(5, 66, device=device)[:, ::2]
    for a, b in zip(torch.autograd.grad(actual, (y, gates), dy),
                    torch.autograd.grad(expected, (y, gates), dy)):
        torch.testing.assert_close(a, b, atol=2e-5, rtol=2e-5)


def test_transposed_and_broadcast_strides(device):
    _cuda(device)
    order = _order(5, 3, device)
    x = torch.randn(33, 5, device=device).T.requires_grad_()
    y = torch.randn(33, 15, device=device).T.requires_grad_()
    gates = torch.rand(1, 3, device=device).expand(5, 3).requires_grad_()
    cot = torch.randn(33, 5, device=device).T
    packed = md.pack_tokens(x, order, 3)
    torch.testing.assert_close(packed, _pack_ref(x, order, 3))
    pack_cot = torch.randn(33, 15, device=device).T
    dx, = torch.autograd.grad(packed, (x,), pack_cot)
    dxr, = torch.autograd.grad(_pack_ref(x, order, 3), (x,), pack_cot)
    torch.testing.assert_close(dx, dxr, atol=2e-6, rtol=2e-6)
    got, ref = md.combine_tokens(y, gates, order), _combine_ref(y, gates, order)
    torch.testing.assert_close(got, ref)
    for a, b in zip(torch.autograd.grad(got, (y, gates), cot),
                    torch.autograd.grad(ref, (y, gates), cot)):
        torch.testing.assert_close(a, b, atol=3e-5, rtol=3e-5)


def test_route_map_reuses_inverse_and_skips_repeat_validation(device, monkeypatch):
    _cuda(device)
    order = _order(5, 2, device)
    routes = md.RouteMap(order, top_k=2)
    # Metadata owns its snapshot; changing the caller's original order is harmless.
    expected_order = order.clone()
    order.copy_(order.flip(0))
    torch.testing.assert_close(routes.order, expected_order, atol=0, rtol=0)
    original_check = md._check_order

    def check_once(order, count, device, validate):
        assert validate is False, "RouteMap should not validate again"
        return original_check(order, count, device, validate)

    def no_inverse(*args):
        raise AssertionError("RouteMap should reuse its inverse")

    monkeypatch.setattr(md, "_check_order", check_once)
    monkeypatch.setattr(md, "_inverse_order", no_inverse)
    x = torch.randn(5, 33, device=device, requires_grad=True)
    gates = torch.rand(5, 2, device=device, requires_grad=True)
    packed = md.pack_tokens(x, routes, 2)
    y = packed * (routes.order[:, None] + 1)
    got = md.combine_tokens(y, gates, routes)
    ref = _combine_ref(_pack_ref(x, expected_order, 2) * (expected_order[:, None] + 1),
                       gates, expected_order)
    torch.testing.assert_close(got, ref)
    for a, b in zip(torch.autograd.grad(got.sum(), (x, gates)),
                    torch.autograd.grad(ref.sum(), (x, gates))):
        torch.testing.assert_close(a, b, atol=3e-5, rtol=3e-5)


def test_device_and_dtype_guards(device):
    _cuda(device)
    x = torch.randn(3, 17, device=device)
    order = _order(3, 2, device)
    gates = torch.rand(3, 2, device=device)
    with pytest.raises(ValueError, match="same device"):
        md.pack_tokens(x, order.cpu(), 2)
    with pytest.raises(ValueError, match="same device"):
        md.combine_tokens(torch.randn(6, 17, device=device), gates.cpu(), order)
    with pytest.raises(ValueError, match="gates must"):
        md.combine_tokens(torch.randn(6, 17, device=device),
                          torch.ones(3, 2, device=device, dtype=torch.float64), order)
    with pytest.raises(ValueError, match="fp16, bf16 or fp32"):
        md.combine_tokens(torch.randn(6, 17, device=device, dtype=torch.float64), gates, order)


def test_route_map_validate_indices_false_skips_validation(device, monkeypatch):
    _cuda(device)
    def no_validation(*args):
        raise AssertionError("validate_indices=False must skip permutation validation")
    monkeypatch.setattr(md, "_validate_permutation", no_validation)
    order = _order(5, 2, device)
    routes = md.RouteMap(order, top_k=2, validate_indices=False)
    x = torch.randn(5, 33, device=device, requires_grad=True)
    gates = torch.rand(5, 2, device=device, requires_grad=True)
    packed = md.pack_tokens(x, routes, 2)
    got = md.combine_tokens(packed, gates, routes)
    ref = _combine_ref(_pack_ref(x, order, 2), gates, order)
    torch.testing.assert_close(got, ref)
    for a, b in zip(torch.autograd.grad(got.sum(), (x, gates)),
                    torch.autograd.grad(ref.sum(), (x, gates))):
        torch.testing.assert_close(a, b, atol=3e-5, rtol=3e-5)


@parametrize("field", ["order", "inverse"])
def test_route_map_rejects_mutation_on_reuse_and_backward(device, field):
    _cuda(device)
    routes = md.RouteMap(_order(3, 2, device), top_k=2)
    x = torch.randn(3, 17, device=device, requires_grad=True)
    gates = torch.rand(3, 2, device=device, requires_grad=True)
    out = md.combine_tokens(md.pack_tokens(x, routes, 2), gates, routes)
    getattr(routes, field).add_(0)
    with pytest.raises(RuntimeError, match="RouteMap metadata was modified"):
        md.pack_tokens(x, routes, 2)
    with pytest.raises(RuntimeError, match="modified by an inplace operation"):
        out.sum().backward()


@parametrize("width,expected_stages", [(127, 0), (1024, 0), (1025, 1), (8193, 1)])
def test_gate_gradient_selects_single_or_two_stages(device, monkeypatch, width, expected_stages):
    _cuda(device)
    original = md._gate_backward
    calls = []

    class Spy:
        def __getitem__(self, grid):
            calls.append(grid)
            return original[grid]

    monkeypatch.setattr(md, "_gate_backward", Spy())
    order = _order(3, 2, device)
    y = torch.randn(6, width, device=device, requires_grad=True)
    gates = torch.rand(3, 2, device=device, requires_grad=True)
    got, ref = md.combine_tokens(y, gates, order), _combine_ref(y, gates, order)
    cot = torch.randn_like(got)
    for a, b in zip(torch.autograd.grad(got, (y, gates), cot),
                    torch.autograd.grad(ref, (y, gates), cot)):
        torch.testing.assert_close(a, b, atol=5e-5, rtol=5e-5)
    assert len(calls) == expected_stages


def test_route_map_inference_and_cuda_graph_capture(device):
    _cuda(device)
    with torch.inference_mode():
        routes = md.RouteMap(_order(3, 2, device), top_k=2)
        x = torch.randn(3, 17, device=device)
        gates = torch.rand(3, 2, device=device)
        for _ in range(2):
            md.combine_tokens(md.pack_tokens(x, routes, 2), gates, routes)
        torch.cuda.synchronize()
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph):
            out = md.combine_tokens(md.pack_tokens(x, routes, 2), gates, routes)
        x.add_(1)
        graph.replay()
        torch.testing.assert_close(out, x * gates.sum(1, keepdim=True))


@parametrize("needs", [(True, False), (False, True), (True, True)])
def test_frozen_gradients_and_bitwise_repeatability(device, needs):
    _cuda(device)
    order = _order(5, 2, device)
    y = torch.randn(10, 513, device=device, requires_grad=needs[0])
    gates = torch.rand(5, 2, device=device, requires_grad=needs[1])
    cot = torch.randn(5, 513, device=device)
    watched = [t for t in (y, gates) if t.requires_grad]
    runs = []
    for _ in range(2):
        out = md.combine_tokens(y, gates, order, validate_indices=False)
        runs.append((out, *torch.autograd.grad(out, watched, cot)))
    for a, b in zip(*runs):
        assert torch.equal(a, b)
    expected = _combine_ref(y, gates, order)
    for a, b in zip(runs[0][1:], torch.autograd.grad(expected, watched, cot)):
        torch.testing.assert_close(a, b, atol=3e-5, rtol=3e-5)


def test_empty_tokens(device):
    _cuda(device)
    x = torch.empty(0, 17, device=device, requires_grad=True)
    gates = torch.empty(0, 2, device=device, requires_grad=True)
    order = torch.empty(0, device=device, dtype=torch.int64)
    packed = md.pack_tokens(x, order, 2)
    out = md.combine_tokens(packed, gates, order)
    out.sum().backward()
    assert out.shape == x.shape and x.grad.shape == x.shape and gates.grad.shape == gates.shape


@parametrize("dtype", [torch.int32, torch.int64])
def test_index_dtypes_and_checked_unchecked_agree(device, dtype):
    _cuda(device)
    x = torch.randn(3, 17, device=device)
    order = _order(3, 2, device).to(dtype)
    a = md.pack_tokens(x, order, 2)
    b = md.pack_tokens(x, order, 2, validate_indices=False)
    assert torch.equal(a, b)
    gates = torch.rand(3, 2, device=device)
    assert torch.equal(md.combine_tokens(a, gates, order),
                       md.combine_tokens(b, gates, order, validate_indices=False))


@parametrize("dtype", [torch.float16, torch.bfloat16])
def test_low_precision_gates_and_autocast_contract(device, dtype):
    _cuda(device)
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    y = torch.randn(14, 33, device=device, dtype=dtype, requires_grad=True)
    gates = torch.rand(7, 2, device=device, dtype=dtype, requires_grad=True)
    yr, gr = (t.detach().double().requires_grad_() for t in (y, gates))
    order = _order(7, 2, device)
    with torch.autocast("cuda", dtype=dtype):
        out = md.combine_tokens(y, gates, order)
    assert out.dtype == dtype
    expected = _combine_ref(yr, gr, order)
    tol = 3e-2 if dtype == torch.bfloat16 else 3e-3
    torch.testing.assert_close(out, expected.to(dtype), atol=tol, rtol=tol)
    cot = torch.randn_like(out)
    for a, b in zip(torch.autograd.grad(out, (y, gates), cot),
                    torch.autograd.grad(expected, (yr, gr), cot.double())):
        assert a.dtype == dtype
        torch.testing.assert_close(a, b.to(dtype), atol=tol, rtol=tol)
    with torch.autocast("cuda", dtype=dtype):
        fp32_out = md.combine_tokens(y.float(), gates.float(), order)
    assert fp32_out.dtype == torch.float32


def test_saved_permutation_mutation_is_rejected(device):
    _cuda(device)
    x = torch.randn(3, 17, device=device, requires_grad=True)
    order = _order(3, 2, device)
    packed = md.pack_tokens(x, order, 2)
    order.copy_(order.flip(0))
    with pytest.raises(RuntimeError, match="modified by an inplace operation"):
        packed.sum().backward()


def test_double_backward_is_explicitly_unsupported(device):
    _cuda(device)
    y = torch.randn(6, 17, device=device, requires_grad=True)
    gates = torch.rand(3, 2, device=device, requires_grad=True)
    out = md.combine_tokens(y, gates, _order(3, 2, device))
    dy, = torch.autograd.grad(out.square().sum(), (y,), create_graph=True)
    with pytest.raises(RuntimeError):
        torch.autograd.grad(dy.sum(), y)


def test_noncurrent_cuda_device(device):
    _cuda(device)
    if torch.cuda.device_count() < 2:
        pytest.skip("requires two CUDA devices")
    with torch.cuda.device(0):
        other = torch.device("cuda:1")
        x = torch.randn(3, 17, device=other, requires_grad=True)
        gates = torch.rand(3, 2, device=other, requires_grad=True)
        order = _order(3, 2, other)
        packed = md.pack_tokens(x, order, 2)
        md.combine_tokens(packed, gates, order).sum().backward()
        assert torch.cuda.current_device() == 0 and x.grad.device == other


@parametrize("bad", [0, -1, True, 1.5])
def test_invalid_top_k_is_rejected_on_cpu(bad):
    with pytest.raises(ValueError, match="top_k"):
        md.pack_tokens(torch.zeros(3, 7), torch.arange(6), bad)


@parametrize("order", [torch.tensor([0, 0, 2, 3, 4, 5]),
                       torch.tensor([-1, 1, 2, 3, 4, 5]),
                       torch.tensor([0, 1, 2, 3, 4, 6])])
def test_invalid_permutation_rejected_before_launch(order, device):
    _cuda(device)
    order = order.to(device)
    with pytest.raises(ValueError, match="permutation"):
        md.pack_tokens(torch.zeros(3, 7, device=device), order, 2)
    with pytest.raises(ValueError, match="permutation"):
        md.combine_tokens(torch.zeros(6, 7, device=device), torch.ones(3, 2, device=device), order)
    with pytest.raises(ValueError, match="permutation"):
        md.RouteMap(order, top_k=2)


def test_shape_dtype_and_cpu_guards():
    with pytest.raises(ValueError, match="hidden"):
        md.pack_tokens(torch.zeros(3, 0), torch.arange(6), 2)
    with pytest.raises(ValueError, match="fp16, bf16 or fp32"):
        md.pack_tokens(torch.zeros(3, 7, dtype=torch.float64), torch.arange(6), 2)
    with pytest.raises(ValueError, match="one entry per route"):
        md.pack_tokens(torch.zeros(3, 7), torch.arange(5), 2)
    with pytest.raises(ValueError, match="int32 or int64"):
        md.pack_tokens(torch.zeros(3, 7), torch.arange(6).float(), 2)
    with pytest.raises(ValueError, match="one row per gate"):
        md.combine_tokens(torch.zeros(5, 7), torch.ones(3, 2), torch.arange(6))
    with pytest.raises(ValueError, match="gates must"):
        md.combine_tokens(torch.zeros(6, 7), torch.ones(6), torch.arange(6))
    with pytest.raises(ValueError, match="require CUDA and Triton"):
        md.pack_tokens(torch.zeros(3, 7), torch.arange(6), 2)
    with pytest.raises(ValueError, match="require CUDA and Triton"):
        md.combine_tokens(torch.zeros(6, 7), torch.ones(3, 2), torch.arange(6))
    with pytest.raises(ValueError, match="require CUDA and Triton"):
        md.RouteMap(torch.arange(6), top_k=2)


def test_route_map_rejects_different_token_top_k_factorization(device):
    _cuda(device)
    routes = md.RouteMap(_order(8, 2, device), top_k=2)
    assert (routes.n_tokens, routes.top_k) == (8, 2)
    with pytest.raises(ValueError, match="token count/top_k"):
        md.pack_tokens(torch.randn(4, 17, device=device), routes, 4)
    with pytest.raises(ValueError, match="token count/top_k"):
        md.combine_tokens(torch.randn(16, 17, device=device),
                          torch.rand(4, 4, device=device), routes)


@parametrize("bad", [0, -1, True, 1.5])
def test_invalid_route_map_top_k_on_cpu(bad):
    with pytest.raises(ValueError, match="top_k"):
        md.RouteMap(torch.arange(6), top_k=bad)


def test_invalid_route_map_divisibility_on_cpu():
    with pytest.raises(ValueError, match="divisible"):
        md.RouteMap(torch.arange(5), top_k=2)


def test_cpu_backend_rejection_precedes_value_validation(monkeypatch):
    def no_validation(*args):
        raise AssertionError("CPU rejection should not sort or synchronize")

    monkeypatch.setattr(md, "_validate_permutation", no_validation)
    x = torch.zeros(3, 7)
    order = torch.arange(6)
    with pytest.raises(ValueError, match="require CUDA and Triton"):
        md.pack_tokens(x, order, 2)
    with pytest.raises(ValueError, match="require CUDA and Triton"):
        md.combine_tokens(torch.zeros(6, 7), torch.ones(3, 2), order)
    with pytest.raises(ValueError, match="require CUDA and Triton"):
        md.RouteMap(order, top_k=2)
