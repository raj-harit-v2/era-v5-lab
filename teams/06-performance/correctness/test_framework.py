"""The framework must catch broken code.

  * every fp32 pair fails under the 1.01 drill (check with fast_override=scaled(1.01))
  * a toy pair: correct passes; a wrong gradient, NaN or a wrong shape fails; rel_err(x * 1.01, x) == 0.01
  * model-like cases: a backward that runs once, a parameter with no gradient, a detached fast output fails
  * tolerances: fp32 >= 1e-2 refused, bf16 pairs kept out of the drill
  * nested outputs (tuples, lists, None, floats) must match in structure and values
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import torch

from correctness.framework import Case, PAIRS, Pair, check, pair, rel_err, scaled



def _import_all_test_modules() -> None:
    here = Path(__file__).resolve().parent
    for path in sorted(here.glob("test_*.py")):
        if path.name == Path(__file__).name:
            continue
        importlib.import_module(path.stem)


_import_all_test_modules()


@pair("_framework.toy", tol=1e-4)
def _toy_pair(device):
    def ref_fn(x):
        return x * 2

    def fast_fn(x):
        return x * 2

    x = torch.randn(3, 3, device=device, dtype=torch.float32, requires_grad=True)
    return Case(ref=ref_fn, fast=fast_fn, inputs=[x], grads=True)


class _ScaleBwd(torch.autograd.Function):
    @staticmethod
    def forward(ctx, y, k):
        ctx.k = k
        return y

    @staticmethod
    def backward(ctx, g):
        return g * ctx.k, None


def test_rel_err_one_percent():
    x = torch.randn(8, 8, dtype=torch.float64)
    err = rel_err(x * 1.01, x)
    assert abs(err - 0.01) < 1e-9


def test_rel_err_shape_mismatch():
    with pytest.raises(AssertionError, match="shape"):
        rel_err(torch.zeros(2), torch.zeros(3))


def test_rel_err_nan():
    a = torch.tensor([1.0, float("nan")])
    b = torch.tensor([1.0, 1.0])
    with pytest.raises(AssertionError, match="NaN/Inf"):
        rel_err(a, b)


def test_toy_correct_passes(device):
    errors = check(PAIRS["_framework.toy"], device)
    assert "out[0]" in errors
    assert errors["out[0]"] < 1e-4


def test_toy_scaled_fails(device):
    with pytest.raises(AssertionError):
        check(PAIRS["_framework.toy"], device, fast_override=scaled(1.01))


def test_wrong_gradient_fails(device):
    def build(dev):
        def ref_fn(x):
            return x * 2

        def fast_fn(x):
            return _ScaleBwd.apply(x * 2, 1.01)

        x = torch.randn(5, device=dev, dtype=torch.float32, requires_grad=True)
        return Case(ref=ref_fn, fast=fast_fn, inputs=[x], grads=True)

    p = Pair("_framework.bad_grad", build, tol=1e-4)
    with pytest.raises(AssertionError, match="grad"):
        check(p, device)


def test_nan_output_fails(device):
    def build(dev):
        def ref_fn(x):
            return x * 2

        def fast_fn(x):
            return x * 2 + torch.nan

        x = torch.randn(2, 2, device=dev, dtype=torch.float32, requires_grad=True)
        return Case(ref=ref_fn, fast=fast_fn, inputs=[x], grads=False)

    p = Pair("_framework.nan", build, tol=1e-4)
    with pytest.raises(AssertionError, match="NaN/Inf"):
        check(p, device)


def test_wrong_shape_fails(device):
    def build(dev):
        def ref_fn(x):
            return x * 2

        def fast_fn(x):
            return (x * 2).flatten()

        x = torch.randn(2, 2, device=dev, dtype=torch.float32, requires_grad=True)
        return Case(ref=ref_fn, fast=fast_fn, inputs=[x], grads=False)

    p = Pair("_framework.shape", build, tol=1e-4)
    with pytest.raises(AssertionError, match="shape"):
        check(p, device)


@pytest.mark.parametrize("name", sorted(n for n, p in PAIRS.items() if p.drill))
def test_every_registered_pair_scaled_fails(name, device):
    with pytest.raises(AssertionError):
        check(PAIRS[name], device, fast_override=scaled(1.01))


class _OnceBackward(torch.autograd.Function):
    """Like ReversibleStack: the backward frees its state, so a second backward fails."""

    @staticmethod
    def forward(ctx, x):
        ctx.state = "saved"
        return x * 2

    @staticmethod
    def backward(ctx, g):
        assert ctx.state is not None, "backward ran twice"
        ctx.state = None
        return g * 2


def test_two_outputs_one_backward(device):
    def build(dev):
        def ref_fn(x):
            y = x * 2
            return y, y.sum()

        def fast_fn(x):
            y = _OnceBackward.apply(x)
            return y, y.sum()

        x = torch.randn(4, device=dev, dtype=torch.float32, requires_grad=True)
        return Case(ref=ref_fn, fast=fast_fn, inputs=[x])

    errors = check(Pair("_framework.two_outputs", build), device)
    assert {"out[0]", "out[1]", "grad_in[0]"} <= set(errors)


def test_unused_param_has_no_grad_on_both_sides(device):
    def build(dev):
        w_fast = torch.randn(3, device=dev, requires_grad=True)
        unused_fast = torch.randn(3, device=dev, requires_grad=True)
        w_ref, unused_ref = (t.detach().double().requires_grad_(True) for t in (w_fast, unused_fast))
        return Case(ref=lambda x: x * w_ref, fast=lambda x: x * w_fast,
                    inputs=[torch.randn(3, device=dev)],
                    params_ref=[w_ref, unused_ref], params_fast=[w_fast, unused_fast])

    errors = check(Pair("_framework.unused_param", build), device)
    assert "grad_param[0]" in errors and "grad_param[1]" not in errors


def test_detached_fast_output_fails(device):
    def build(dev):
        x = torch.randn(3, device=dev, requires_grad=True)
        return Case(ref=lambda x: x * 2, fast=lambda x: (x * 2).detach(), inputs=[x])

    with pytest.raises(AssertionError, match="requires_grad"):
        check(Pair("_framework.detached", build), device)


def test_tolerances_per_dtype():
    from correctness.framework import TOLERANCES
    fp32 = Pair("_framework.fp32", _toy_pair)
    assert (fp32.tol, fp32.gtol) == TOLERANCES[torch.float32] and fp32.drill
    with pytest.raises(AssertionError, match="fp32 tolerance"):
        pair("_framework.too_loose", tol=1e-2)
    bf16 = Pair("_framework.bf16", _toy_pair, *TOLERANCES[torch.bfloat16], dtype=torch.bfloat16)
    assert not bf16.drill
    with pytest.raises(AssertionError, match="no tolerances"):
        pair("_framework.fp8", dtype=torch.float8_e4m3fn)


def _structure_pair(ref_fn, fast_fn):
    def build(device):
        x = torch.tensor([1.0], device=device)
        return Case(ref=ref_fn, fast=fast_fn, inputs=[x], grads=False)

    return Pair("_framework.output_structure", build)


def test_output_structure_matching_metadata_passes(device):
    p = _structure_pair(lambda x: (x * 2, 3, "ok"),
                        lambda x: (x * 2, 3, "ok"))
    assert "out[0]" in check(p, device)


def test_output_structure_tensor_vs_none_fails(device):
    p = _structure_pair(lambda x: (x * 2, None),
                        lambda x: (x * 2, x * 3))
    with pytest.raises(AssertionError, match="output type mismatch"):
        check(p, device)


def test_output_structure_tuple_length_mismatch_fails(device):
    p = _structure_pair(lambda x: (x * 2, 3),
                        lambda x: (x * 2, 3, 4))
    with pytest.raises(AssertionError, match="output structure mismatch"):
        check(p, device)


def test_output_structure_metadata_value_mismatch_fails(device):
    p = _structure_pair(lambda x: (x * 2, 3),
                        lambda x: (x * 2, 4))
    with pytest.raises(AssertionError, match="non-tensor output mismatch"):
        check(p, device)


def test_output_structure_list_vs_tuple_fails(device):
    p = _structure_pair(lambda x: [x * 2, 3],
                        lambda x: (x * 2, 3))
    with pytest.raises(AssertionError, match="output structure mismatch"):
        check(p, device)


def test_output_structure_python_float_precision_difference_passes(device):
    p = _structure_pair(lambda x: (x * 2, (x.double() / 3).item()),
                        lambda x: (x * 2, (x / 3).item()))
    assert "out[0]" in check(p, device)


def test_output_structure_python_float_large_difference_fails(device):
    p = _structure_pair(lambda x: (x * 2, 1.0),
                        lambda x: (x * 2, 1.1))
    with pytest.raises(AssertionError, match="non-tensor float output mismatch"):
        check(p, device)


@pytest.mark.parametrize("ref_value,fast_value", [
    (float("nan"), float("nan")),
    (float("inf"), float("inf")),
])
def test_output_structure_nonfinite_float_fails(device, ref_value, fast_value):
    p = _structure_pair(lambda x: (x * 2, ref_value),
                        lambda x: (x * 2, fast_value))
    with pytest.raises(AssertionError, match="non-tensor float output mismatch"):
        check(p, device)


def test_output_structure_python_float_near_zero_passes(device):
    p = _structure_pair(lambda x: (x * 2, 0.0),
                        lambda x: (x * 2, 1e-7))
    assert "out[0]" in check(p, device)


def test_output_structure_nested_tensor_wrong_value_fails(device):
    p = _structure_pair(lambda x: (x * 2, (x * 3,)),
                        lambda x: (x * 2, (x * 999,)))
    with pytest.raises(AssertionError, match=r"out\[1\]"):
        check(p, device)


def test_output_structure_nested_tensors_correct_pass(device):
    p = _structure_pair(lambda x: (x * 2, [None, (x * 3,)]),
                        lambda x: (x * 2, [None, (x * 3,)]))
    errors = check(p, device)
    assert {"out[0]", "out[1]"} <= set(errors)


def test_output_structure_nested_metadata_still_fails(device):
    p = _structure_pair(lambda x: (x * 2, ("ok", 3)),
                        lambda x: (x * 2, ("bad", 3)))
    with pytest.raises(AssertionError, match="non-tensor output mismatch"):
        check(p, device)


def test_output_structure_nested_container_type_mismatch_fails(device):
    p = _structure_pair(lambda x: (x * 2, (x * 3,)),
                        lambda x: (x * 2, [x * 3]))
    with pytest.raises(AssertionError, match="output structure mismatch"):
        check(p, device)
