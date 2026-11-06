"""Torch and Triton LayerNorm forward, backward, and model integration."""
from __future__ import annotations

import os
from contextlib import contextmanager

import pytest
import torch
import torch.nn.functional as F

from correctness.framework import Case, PAIRS, check, pair, pairs_in, scaled
from kernels import layer_norm as ln
from kernels.layer_norm import (TritonLayerNorm, backward_groups, launch_config,
                                layer_norm_backend_report, layer_norm_triton)
from models.config import ModelConfig
from models.gpt import GPT
from perfkit.regions import phase, use_recorder


def _cuda(device):
    if device.type != "cuda" or ln.triton is None:
        pytest.skip("triton_ln requires CUDA and Triton")


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


@pytest.mark.parametrize("shape", [(1, 1), (3, 3), (1, 127), (3, 17), (7, 256),
                                    (2, 5, 513), (7, 1000), (3, 8192), (4096, 256)])
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


@pytest.mark.parametrize("reversible", [False, True])
@pytest.mark.parametrize("autocast", [False, True])
def test_layer_norm_full_model_matches_torch(device, reversible, autocast):
    _cuda(device)
    if autocast and not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    torch.manual_seed(107)
    cfg = dict(vocab_size=71, block_size=8, n_layer=2, n_head=2, n_embd=32,
               reversible=reversible)
    ref = GPT(ModelConfig(**cfg, ln_impl="torch_ln")).to(device)
    got = GPT(ModelConfig(**cfg, ln_impl="triton_ln")).to(device)
    got.load_state_dict(ref.state_dict())
    ids = torch.randint(0, 71, (2, 5), device=device)
    targets = torch.randint(0, 71, (2, 5), device=device)
    with torch.autocast("cuda", dtype=torch.bfloat16, enabled=autocast):
        _, ref_loss = ref(ids, targets)
        _, got_loss = got(ids, targets)
    ref_loss.backward()
    got_loss.backward()
    tol = 3e-2 if autocast else 3e-4
    torch.testing.assert_close(got_loss, ref_loss, atol=tol, rtol=tol)
    for (name, p), (other, q) in zip(ref.named_parameters(), got.named_parameters()):
        assert name == other
        torch.testing.assert_close(q.grad, p.grad, atol=tol, rtol=tol, msg=name)


def test_layer_norm_rejects_cuda_free_call():
    x = torch.randn(2, 8)
    with pytest.raises(ValueError, match="cannot handle"):
        layer_norm_triton(x, torch.ones(8), torch.zeros(8))


@pytest.mark.parametrize("shape,kwargs,dtype", [
    ((2, 8), {}, torch.float32), ((2, 8), {}, torch.float64),
    ((2, 8), {"elementwise_affine": False}, torch.float32),
    ((2, 8), {"bias": False}, torch.float32),
    ((2, 3, 4), {}, torch.float32), ((2, 8193), {}, torch.float32),
    ((0, 8), {}, torch.float32),
])
def test_module_falls_back_on_cpu(shape, kwargs, dtype):
    normalized_shape = shape[-2:] if len(shape) == 3 else shape[-1]
    ref = torch.nn.LayerNorm(normalized_shape, **kwargs).to(dtype)
    got = TritonLayerNorm(normalized_shape, **kwargs).to(dtype)
    got.load_state_dict(ref.state_dict())
    x = torch.randn(shape, dtype=dtype, requires_grad=True)
    xr = x.detach().clone().requires_grad_()
    y, yr = got(x), ref(xr)
    torch.testing.assert_close(y, yr, atol=0, rtol=0)
    y.sum().backward()
    yr.sum().backward()
    torch.testing.assert_close(x.grad, xr.grad, atol=0, rtol=0)
    assert got.backend_info(x.device, dtype)["backend"] == "torch_ln"


@pytest.mark.parametrize("kwargs", [{"elementwise_affine": False}, {"bias": False}, {}])
def test_backend_report_exposes_fallback(kwargs):
    module = TritonLayerNorm(8, **kwargs)
    entry = layer_norm_backend_report(module)[0]
    assert entry["backend"] == "torch_ln"
    assert entry["reason"]


@pytest.mark.parametrize("dtype", [torch.float16, torch.bfloat16])
def test_autocast_output_dtype_and_gradients(device, dtype):
    _cuda(device)
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    torch.manual_seed(109)
    x = torch.randn(7, 127, device=device, dtype=dtype, requires_grad=True)
    w = torch.randn(127, device=device, requires_grad=True)
    b = torch.randn(127, device=device, requires_grad=True)
    xr, wr, br = (p.detach().clone().requires_grad_() for p in (x, w, b))
    with torch.autocast("cuda", dtype=dtype):
        y = layer_norm_triton(x, w, b)
        yr = F.layer_norm(xr, (127,), wr, br)
    assert y.dtype == yr.dtype == torch.float32
    dy = torch.randn_like(y)
    torch.testing.assert_close(y, yr, atol=3e-4, rtol=3e-4)
    for actual, expected in zip(torch.autograd.grad(y, (x, w, b), dy),
                                torch.autograd.grad(yr, (xr, wr, br), dy)):
        torch.testing.assert_close(actual, expected, atol=3e-2, rtol=3e-2)


@pytest.mark.parametrize("needs", [(True, False, False), (True, False, True),
                                  (False, True, False), (False, False, True),
                                  (True, True, True)])
def test_frozen_gradients_and_repeated_results(device, needs, monkeypatch):
    _cuda(device)
    torch.manual_seed(113)
    values = (torch.randn(73, 127, device=device), torch.randn(127, device=device),
              torch.randn(127, device=device))
    selected = [i for i, flag in enumerate(needs) if flag]
    dy = torch.randn_like(values[0])
    results = []
    if not needs[1] and not needs[2]:
        class NoParameterKernel:
            def __getitem__(self, grid):
                raise AssertionError("parameter reduction must be skipped")
        monkeypatch.setattr(ln, "_backward_params", NoParameterKernel())
    for _ in range(2):
        args = [p.detach().clone().requires_grad_(flag) for p, flag in zip(values, needs)]
        y = layer_norm_triton(*args)
        grads = torch.autograd.grad(y, [args[i] for i in selected], dy)
        results.append(grads)
    for a, b in zip(*results):
        assert torch.equal(a, b)
    refs = [p.detach().clone().requires_grad_(flag) for p, flag in zip(values, needs)]
    ref = F.layer_norm(refs[0], (127,), refs[1], refs[2])
    for actual, expected in zip(results[0], torch.autograd.grad(ref, [refs[i] for i in selected], dy)):
        torch.testing.assert_close(actual, expected, atol=3e-4, rtol=3e-4)


@pytest.mark.parametrize("grad_dtype", [torch.float32, torch.float16, torch.bfloat16])
def test_noncontiguous_input_and_grad_output(device, grad_dtype):
    _cuda(device)
    if grad_dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    x = torch.randn(2, 7, 254, device=device)[..., ::2].requires_grad_()
    w = torch.randn(254, device=device)[::2].requires_grad_()
    b = torch.randn(254, device=device)[::2].requires_grad_()
    refs = [p.detach().clone().requires_grad_() for p in (x, w, b)]
    dy = torch.randn(2, 7, 254, device=device, dtype=grad_dtype)[..., ::2]
    y, yr = layer_norm_triton(x, w, b), F.layer_norm(refs[0], (127,), refs[1], refs[2])
    torch.testing.assert_close(y, yr, atol=3e-4, rtol=3e-4)
    for actual, expected in zip(torch.autograd.grad(y, (x, w, b), dy),
                                torch.autograd.grad(yr, refs, dy)):
        torch.testing.assert_close(actual, expected, atol=3e-4, rtol=3e-4)


def test_double_backward_is_rejected(device):
    _cuda(device)
    x = torch.randn(3, 127, device=device, requires_grad=True)
    g = torch.randn_like(x, requires_grad=True)
    y = layer_norm_triton(x, torch.ones(127, device=device), torch.zeros(127, device=device))
    dx = torch.autograd.grad(y, x, g, create_graph=True)[0]
    with pytest.raises(RuntimeError):
        torch.autograd.grad(dx.sum(), x)


def test_scratch_group_count_is_bounded():
    for n in (1, 256, 1024, 8192):
        _, rows, _ = launch_config(n)
        assert backward_groups(1, rows, 108) == 1
        assert backward_groups(10**6, rows, 108) == 108 * 4
        assert backward_groups(10**9, rows, 108) == 108 * 4


def test_launch_config_heuristics_are_pinned():
    expected = {1: (1, 4, 1), 33: (64, 4, 1), 127: (128, 4, 1), 256: (256, 4, 1),
                513: (1024, 4, 4), 1024: (1024, 4, 4), 1025: (2048, 1, 8),
                8192: (8192, 1, 8)}
    for n, geometry in expected.items():
        assert launch_config(n) == geometry, n


def test_backward_stage_regions_are_recorded(device):
    _cuda(device)

    class Recorder:
        max_level = 3

        def __init__(self):
            self.names = []

        @contextmanager
        def region(self, name, level):
            self.names.append(name)
            yield

    x = torch.randn(7, 127, device=device, requires_grad=True)
    w = torch.ones(127, device=device, requires_grad=True)
    b = torch.zeros(127, device=device, requires_grad=True)
    y = layer_norm_triton(x, w, b)
    rec = Recorder()
    with use_recorder(rec), phase("bwd"):
        y.sum().backward()
    assert "bwd:ln.triton.rows" in rec.names
    assert "bwd:ln.triton.params" in rec.names


def test_noncurrent_cuda_device(device):
    _cuda(device)
    if torch.cuda.device_count() < 2:
        pytest.skip("requires two CUDA devices")
    with torch.cuda.device(0):
        x = torch.randn(5, 127, device="cuda:1", requires_grad=True)
        w = torch.randn(127, device="cuda:1", requires_grad=True)
        b = torch.randn(127, device="cuda:1", requires_grad=True)
        y = layer_norm_triton(x, w, b)
        refs = [p.detach().clone().requires_grad_() for p in (x, w, b)]
        yr = F.layer_norm(refs[0], (127,), refs[1], refs[2])
        dy = torch.randn_like(y)
        for actual, expected in zip(torch.autograd.grad(y, (x, w, b), dy),
                                    torch.autograd.grad(yr, refs, dy)):
            torch.testing.assert_close(actual, expected, atol=3e-4, rtol=3e-4)
        assert torch.cuda.current_device() == 0


def test_compile_fullgraph_forward_backward(device):
    _cuda(device)
    compiled = torch.compile(layer_norm_triton, fullgraph=True)
    for m in (7, 11):
        args = [torch.randn(m, 127, device=device, requires_grad=True),
                torch.randn(127, device=device, requires_grad=True),
                torch.randn(127, device=device, requires_grad=True)]
        refs = [p.detach().clone().requires_grad_() for p in args]
        y = compiled(*args)
        yr = F.layer_norm(refs[0], (127,), refs[1], refs[2])
        torch.testing.assert_close(y, yr, atol=3e-4, rtol=3e-4)
        g = torch.randn_like(y)
        for actual, expected in zip(torch.autograd.grad(y, args, g), torch.autograd.grad(yr, refs, g)):
            torch.testing.assert_close(actual, expected, atol=3e-4, rtol=3e-4)


@pytest.mark.parametrize("shape,dtype,kwargs,reason", [
    ((2, 8), torch.float64, {}, "unsupported_dtype"),
    ((2, 8193), torch.float32, {}, "unsupported_hidden_size"),
    ((2, 3, 4), torch.float32, {}, "multiple_normalized_dimensions"),
    ((2, 8), torch.float32, {"elementwise_affine": False}, "affine_weight_and_bias_required"),
    ((2, 8), torch.float32, {"bias": False}, "affine_weight_and_bias_required"),
])
def test_cuda_module_fallback_is_explicit(device, shape, dtype, kwargs, reason):
    _cuda(device)
    normalized = shape[-2:] if len(shape) == 3 else shape[-1]
    module = TritonLayerNorm(normalized, **kwargs).to(device=device, dtype=dtype)
    x = torch.randn(shape, device=device, dtype=dtype, requires_grad=True)
    expected = F.layer_norm(x, module.normalized_shape, module.weight, module.bias, module.eps)
    torch.testing.assert_close(module(x), expected, atol=0, rtol=0)
    assert module.backend_info(device, dtype) == {"backend": "torch_ln", "reason": reason}


def test_strict_function_rejects_fp64(device):
    _cuda(device)
    with pytest.raises(ValueError, match="unsupported_dtype"):
        layer_norm_triton(torch.randn(3, 8, device=device, dtype=torch.float64),
                           torch.ones(8, device=device, dtype=torch.float64),
                           torch.zeros(8, device=device, dtype=torch.float64))


def test_functional_rejects_cross_device_parameters(device):
    _cuda(device)
    x = torch.randn(2, 8, device=device)
    with pytest.raises(ValueError, match="parameter_device_mismatch"):
        layer_norm_triton(x, torch.ones(8), torch.zeros(8))


def test_module_reports_and_natively_errors_on_parameter_device_mismatch(device):
    _cuda(device)
    module = TritonLayerNorm(8)
    x = torch.randn(2, 8, device=device)
    assert module.backend_info(x.device, torch.float32) == {
        "backend": "torch_ln", "reason": "parameter_device_mismatch"}
    with pytest.raises(RuntimeError):
        module(x)


def test_functional_rejects_unsupported_parameter_dtype_combination(device):
    _cuda(device)
    x = torch.randn(2, 8, device=device)
    with pytest.raises(ValueError, match="unsupported_parameter_dtype_combination"):
        layer_norm_triton(x, torch.ones(8, device=device),
                          torch.zeros(8, device=device, dtype=torch.bfloat16))
    with pytest.raises(ValueError, match="unsupported_parameter_dtype_combination"):
        layer_norm_triton(x, torch.ones(8, device=device, dtype=torch.bfloat16),
                          torch.zeros(8, device=device, dtype=torch.bfloat16))


@pytest.mark.parametrize("input_dtype", [torch.float16, torch.bfloat16])
def test_functional_accepts_mixed_precision_parameters(device, input_dtype):
    _cuda(device)
    if input_dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("bf16 unsupported")
    torch.manual_seed(211)
    x = torch.randn(5, 17, device=device, dtype=input_dtype, requires_grad=True)
    w = torch.randn(17, device=device, requires_grad=True)
    b = torch.randn(17, device=device, requires_grad=True)
    y = layer_norm_triton(x, w, b)
    assert y.dtype == input_dtype
    dx, dw, db = torch.autograd.grad(y, (x, w, b), torch.randn_like(y))
    assert dx.dtype == input_dtype and dw.dtype == db.dtype == torch.float32
    ref = F.layer_norm(x.detach().float(), (17,), w, b).to(input_dtype)
    torch.testing.assert_close(y, ref, atol=1e-2, rtol=1e-2)


if ln.triton is not None:
    from triton import language as tl
    from kernels.layer_norm import _offset

    @ln.triton.jit
    def _offset_probe(ROWS, OUT, N: tl.constexpr):
        i = tl.arange(0, 4)
        row = tl.load(ROWS + i)
        tl.store(OUT + i, _offset(row, i, N))


def test_int64_offsets_without_a_multigigabyte_allocation(device):
    _cuda(device)
    rows = torch.tensor([2**21, 2**24, 2**31 - 1, 2**31 + 7], dtype=torch.int64, device=device)
    out = torch.empty_like(rows)
    with torch.cuda.device(device):
        _offset_probe[(1,)](rows, out, 1280)
    torch.testing.assert_close(out, rows * 1280 + torch.arange(4, device=device), atol=0, rtol=0)


@pytest.mark.skipif(os.environ.get("G6_LN_LARGE_TEST") != "1",
                    reason="opt-in >2^31-element server stress case; needs at least 24 GiB free")
def test_large_tensor_crosses_int32_offset_boundary(device):
    _cuda(device)
    with torch.cuda.device(device):
        if torch.cuda.mem_get_info()[0] < 24 * 1024**3:
            pytest.skip("not enough free CUDA memory for the large-index test")
        m, n = 2**21, 1025
        x = torch.zeros((m, n), device=device, dtype=torch.float16, requires_grad=True)
        w = torch.ones(n, device=device, requires_grad=True)
        b = torch.zeros(n, device=device, requires_grad=True)
        y = layer_norm_triton(x, w, b)
        dx, dw, db = torch.autograd.grad(y.sum(), (x, w, b))
        assert not dx[-1].any()
        torch.testing.assert_close(dw, torch.zeros_like(dw), atol=0, rtol=0)
        torch.testing.assert_close(db, torch.full_like(db, m), atol=0, rtol=0)


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
