"""MoE active -> idle -> reactivated expert: the packed dispatches against an fp64 reference over three AdamW steps.

G6 week 3 rotation test (plan sheet: "one correctness test for a fast kernel; the test compares the reference and
the fast output"). Fast paths: every entry of models.moe.DISPATCH except loop (today sorted and grouped, the
stable-sorted batched-GEMM paths). Reference: written here from the models/moe.py docstring in fp64, one token at
a time, never by calling the dispatch code.

One expert (IDLE) is routed to on step 1, gets no route on step 2 and is routed to again on step 3. Routing is
replayed (replay_routing), so the schedule is exact; the gates still come from the router scores. Each step:
  1. check() from framework.py: output, input gradient and every parameter gradient within the fp32 tolerances,
     then a second fast run that must be bit-identical.
  2. Exact checks on IDLE: step 2 its gradients exist and are exactly zero (a zero tensor, not None), and the
     reference gives it no gradient at all; steps 1 and 3 every IDLE gradient is nonzero.
  3. One AdamW step on each side, then parameters and AdamW state (exp_avg, exp_avg_sq, step) compared.

Convention under test: the packed paths hand AdamW a zero gradient for an idle expert (models/moe.py: "sorted
gives idle experts zero gradients where loop leaves None"). The reference fills its None gradients with zeros
before its own step, so both sides apply the same update; step 2 asserts that this update really moves IDLE
(momentum), so zero and absent are not interchangeable under AdamW, and a change of convention
in either direction fails step 3. This test does not claim the packed paths train like the loop path.

Mutation case: test_perturbed_packing_order_is_rejected shifts the packed route order by one inside the fast call
only; the parity check must reject it.
"""
from __future__ import annotations

import math
from contextlib import contextmanager, nullcontext

import pytest
import torch
import torch.nn as nn

from correctness.framework import TOLERANCES, Case, Pair, check, rel_err, to64
from models.moe import DISPATCH, SparseMoE, replay_routing


DIM, N_TOKENS, NUM_EXPERTS, TOP_K, SEED = 64, 24, 4, 2, 0
IDLE = NUM_EXPERTS - 1
SCHEDULE = ("active", "idle", "active")             # what IDLE does on steps 1, 2, 3
# lr and weight_decay as configs/base.yaml. eps=1e-6, not torch's 1e-8: at 1e-8 the first step g / (|g| + eps) has
# slope 1/eps near g = 0, so one element of 16384 with |g| = 5e-9 (median 1.4e-2) and an ordinary fp32 rounding
# error of 5e-9 moved 0.17 * lr, and the parameter rel_err reached 6.7e-5 > 5e-5. The loop dispatch gives the same
# 6.7e-5, so it is AdamW conditioning, not packing; eps=1e-6 bounds the slope and keeps the tolerance at 5e-5.
ADAMW = dict(lr=6e-4, betas=(0.9, 0.999), eps=1e-6, weight_decay=0.0)
FAST = [d for d in DISPATCH if d != "loop"]         # loop is the reference dispatch, not a fast path
TOL, GRAD_TOL = TOLERANCES[torch.float32]           # 1e-5 outputs, 5e-5 gradients: the framework's fp32 values
_REAL_ARGSORT = torch.argsort


# ------------------------------------------------------------------------------ the reference

def ref_gelu(h):
    return 0.5 * h * (1.0 + torch.erf(h / math.sqrt(2.0)))


def ref_silu(z):
    return z / (1.0 + torch.exp(-z))


def ref_expert(m, x):
    """One ExpertMLP on one token x [dim], fp64. GELU: c_proj(GELU(c_fc x + b)) + b. SwiGLU: c_proj(SiLU(c_gate x)
    * c_fc x), no biases."""
    if hasattr(m, "c_gate"):
        return m.c_proj.weight @ (ref_silu(m.c_gate.weight @ x) * (m.c_fc.weight @ x))
    return m.c_proj.weight @ ref_gelu(m.c_fc.weight @ x + m.c_fc.bias) + m.c_proj.bias


def reference_forced(moe, x, topk_idx):
    """fp64 MoE with the expert choice topk_idx [N, k] replayed: softmax(router x) -> gates = scores of the chosen,
    renormalised -> sum gate * expert(x) + every shared expert. Only chosen experts enter the graph."""
    rows = []
    for n in range(x.shape[0]):
        xt = x[n]
        logits = moe.router.weight @ xt + moe.router.bias
        e = torch.exp(logits - logits.max())
        scores = e / e.sum()
        chosen = [int(j) for j in topk_idx[n]]
        total = sum(scores[j] for j in chosen)
        y = sum((scores[j] / total) * ref_expert(moe.experts[j], xt) for j in chosen)
        for s in moe.shared:
            y = y + ref_expert(s, xt)
        rows.append(y)
    return torch.stack(rows)


# ------------------------------------------------------------------------------ setup

def _moe(dispatch, activation):
    torch.manual_seed(SEED)
    m = SparseMoE(DIM, NUM_EXPERTS, TOP_K, num_shared=1, dispatch=dispatch, router_init_std=0.5,
                  activation=activation)
    g = torch.Generator().manual_seed(SEED + 1)
    with torch.no_grad():                            # nonzero biases everywhere, so a dropped bias term shows
        m.router.bias.copy_(torch.randn(NUM_EXPERTS, generator=g) * 0.5)
        for mod in m.modules():
            if isinstance(mod, nn.Linear) and mod is not m.router and mod.bias is not None:
                mod.bias.copy_(torch.randn(mod.bias.shape, generator=g) * 0.02)
    return m


def _schedule():
    """[(topk_idx [N, k], x [N, dim])] for the three steps. Active steps route every expert; the idle step routes
    every expert but IDLE. CPU generator: the same routes and inputs on every device."""
    g = torch.Generator().manual_seed(SEED + 2)
    steps = []
    for what in SCHEDULE:
        allowed = torch.arange(NUM_EXPERTS) if what == "active" else torch.arange(IDLE)
        idx = torch.stack([allowed[torch.randperm(len(allowed), generator=g)[:TOP_K]] for _ in range(N_TOKENS)])
        counts = torch.bincount(idx.reshape(-1), minlength=NUM_EXPERTS)
        assert (counts[allowed] > 0).all(), f"{what} step leaves an expert unrouted; change SEED"
        assert (counts[IDLE] > 0) == (what == "active")
        steps.append((idx, torch.randn(N_TOKENS, DIM, generator=g)))
    return steps


def _shift_by_one(real_argsort):
    """The mutation: the packed route order rotated by one position, so routes cross expert groups."""
    def argsort(t, *args, **kwargs):
        return real_argsort(t, *args, **kwargs).roll(1)
    return argsort


@contextmanager
def _perturbed_packing():
    torch.argsort = _shift_by_one(_REAL_ARGSORT)
    try:
        yield
    finally:
        torch.argsort = _REAL_ARGSORT


def _grads_by_name(module):
    return {n: p.grad for n, p in module.named_parameters()}


def run_active_idle(dispatch, activation, device, fast_ctx=nullcontext):
    """The three steps. fast_ctx wraps only the fast forward (the mutation case uses it). Returns per-step errors."""
    fast = _moe(dispatch, activation).to(device)
    ref = to64(fast)
    opt_fast = torch.optim.AdamW(fast.parameters(), **ADAMW)
    opt_ref = torch.optim.AdamW(ref.parameters(), **ADAMW)
    idle_prefix = f"experts.{IDLE}."
    report = []

    for step, ((idx, x), what) in enumerate(zip(_schedule(), SCHEDULE), start=1):
        name = f"moe.{dispatch}.active_idle.{activation}.step{step}"
        idx = idx.to(device)

        def fast_fn(i, idx=idx):
            with fast_ctx(), replay_routing(fast, idx):
                return fast(i)

        def build(dev, idx=idx, x=x):
            return Case(ref=lambda i: reference_forced(ref, i, idx), fast=fast_fn,
                        inputs=[x.to(dev).requires_grad_(True)],
                        params_ref=list(ref.parameters()), params_fast=list(fast.parameters()))

        # 1. framework parity: outputs, input and parameter gradients, then bit-identical repeat
        errors = check(Pair(name, build, TOL, GRAD_TOL), device)
        assert "out[0]" in errors and "grad_in[0]" in errors, f"{name}: output and input gradient not compared"

        # 2. exact checks on the IDLE expert (no tolerance)
        g_fast, g_ref = _grads_by_name(fast), _grads_by_name(ref)
        idle_names = [n for n in g_fast if n.startswith(idle_prefix)]
        assert idle_names, f"{name}: no parameters found for expert {IDLE}"
        absent_ref = sorted(n for n, g in g_ref.items() if g is None)
        absent_fast = sorted(n for n, g in g_fast.items() if g is None)
        assert absent_fast == [], f"{name}: fast path left gradients absent (None): {absent_fast}"
        if what == "idle":
            assert absent_ref == sorted(idle_names), (
                f"{name}: the reference should give exactly expert {IDLE} no gradient, got None on {absent_ref}")
            for n in idle_names:
                nz = int(torch.count_nonzero(g_fast[n]))
                assert nz == 0, f"{name}: idle expert gradient {n} has {nz} nonzero elements, must be exactly zero"
            for n in idle_names:                     # the packed convention: an idle expert gets a zero gradient
                p = dict(ref.named_parameters())[n]
                p.grad = torch.zeros_like(p)
        else:
            assert absent_ref == [], f"{name}: every expert is routed this step, but the reference has None on {absent_ref}"
            for n in idle_names:
                assert int(torch.count_nonzero(g_fast[n])) > 0, f"{name}: expert {IDLE} is routed but {n} is all zero"

        # 3. one AdamW step on each side; parameters and optimizer state must still agree
        before = {n: p.detach().clone() for n, p in fast.named_parameters() if n.startswith(idle_prefix)}
        opt_fast.step()
        opt_ref.step()
        if what == "idle":
            moved = [n for n, p in fast.named_parameters() if n in before and not torch.equal(p, before[n])]
            assert sorted(moved) == sorted(before), (
                f"{name}: AdamW left {sorted(set(before) - set(moved))} unmoved on a zero gradient; the test assumes "
                f"zero and absent gradients step differently (AdamW momentum)")
        for (n, pf), pr in zip(fast.named_parameters(), ref.parameters()):
            for what_t, a, b in (("param", pf, pr), ("exp_avg", opt_fast.state[pf]["exp_avg"], opt_ref.state[pr]["exp_avg"]),
                                 ("exp_avg_sq", opt_fast.state[pf]["exp_avg_sq"], opt_ref.state[pr]["exp_avg_sq"])):
                err = rel_err(a, b)
                assert err <= GRAD_TOL, f"{name}: after AdamW, {what_t} of {n}: rel_err={err:.6e} > tol={GRAD_TOL}"
                errors[f"{what_t}:{n}"] = err
            assert float(opt_fast.state[pf]["step"]) == float(opt_ref.state[pr]["step"]) == step, (
                f"{name}: AdamW step count of {n} is {float(opt_fast.state[pf]['step'])}, want {step}")
        fast.zero_grad(set_to_none=True)
        ref.zero_grad(set_to_none=True)
        report.append((name, errors))
    return report


# ------------------------------------------------------------------------------ tests

@pytest.mark.parametrize("activation", ["gelu", "swiglu"])
@pytest.mark.parametrize("dispatch", FAST)
def test_active_idle_reactivated(dispatch, activation, device):
    report = run_active_idle(dispatch, activation, device)
    assert [n.rsplit(".", 1)[-1] for n, _ in report] == ["step1", "step2", "step3"]
    for name, errors in report:
        n_param_grads = len([k for k in errors if k.startswith("grad_param")])
        assert n_param_grads == len(list(_moe(dispatch, activation).parameters())), f"{name}: a gradient was skipped"


@pytest.mark.parametrize("dispatch", FAST)
def test_perturbed_packing_order_is_rejected(dispatch, device):
    """The mutation case: the same run with the packed route order rotated by one must fail the parity check."""
    with pytest.raises(AssertionError, match=r"rel_err=.* > tol=") as exc:
        run_active_idle(dispatch, "gelu", device, fast_ctx=_perturbed_packing)
    print(f"\n[mutation rejected] {dispatch}: {exc.value}")
    assert torch.argsort is _REAL_ARGSORT, "the mutation leaked out of the fast call"
