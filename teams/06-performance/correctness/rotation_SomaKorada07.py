"""G6 Week-3 rotation (SomaKorada07): MoE sorted / grouped dispatch vs an fp64 reference under imbalanced routing.

test_moe.py covers balanced routing, a single idle expert, top-3 and bf16. Here the routing is badly skewed:
the cases where the packed buffer of the fast paths is most uneven (sorted: cap = N, the most one expert can
get; grouped: almost every row of its E * N * k buffer is padding).

Pairs, for each fast dispatch <d> in FAST (sorted, grouped):
    moe_rot.<d>.hot          expert 0 takes every token's first slot, experts 4..7 are never chosen (4 of 8 idle)
    moe_rot.<d>.hot.swiglu   the same routing through the SwiGLU expert path (fused gate/up bmm, no biases)
    moe_rot.<d>.pair         replayed routing: every token on experts {3, 5} (6 of 8 idle), half the tokens list
                             them as (5, 3), so the order inside a token's top-k must not matter
    moe_rot.<d>.tiny         3 tokens for 8 experts (top-2): fewer routes than experts, at least 2 idle
    moe_rot.<d>.hot.bf16     the hot routing under bf16 autocast, the bf16 choice replayed in the reference
Every pair compares the output, the input gradient and every parameter gradient (check()), then two fast runs
must be bit-identical. Idle experts get None from the reference and zeros from the fast paths; check() counts
None as zeros, so an idle expert with a non-zero gradient fails.

Reference: written from the models/moe.py docstring, one token at a time in fp64, reading only the weights:
softmax(router(x)); top-k of (scores + router_bias) by a sort; gates = chosen scores renormalised; sum of
gate * expert(x) + every shared expert. It never calls a dispatch function or an ExpertMLP forward.

Plain tests: the hot case really is skewed (counts), the 1.01 drill fails every fp32 pair, and sorted / grouped
match the loop dispatch (the in-repo reference path) on the hot case, outputs and gradients, with idle experts
given exact zeros (loop leaves None).

Pair names start with "moe_rot." (not "moe."), so conftest does not tie them to configs/base.yaml's
model.ffn: the module is built directly, like the ce.* pairs. Run:
    python -m pytest teams/06-performance/correctness/rotation_SomaKorada07.py -q -rs
"""
from __future__ import annotations

import math

import pytest
import torch
import torch.nn as nn

from correctness.framework import PAIRS, Case, check, pair, pairs_in, rel_err, scaled, to64
from models.config import ModelConfig
from models.gpt import _residual_std
from models.moe import SparseMoE, record_routing, replay_routing


FAST = ("sorted", "grouped")
DIM, E, K, SEED = 64, 8, 2, 0
B, T = 2, 37                       # N = 74 tokens: not a multiple of E, so no expert count comes out even
N = B * T
HOT, IDLE = 0, (4, 5, 6, 7)        # .hot routing: expert 0 always first, these never chosen
PAIR_EXPERTS = (3, 5)              # .pair routing (replayed)
TINY_N = 3
ROUTER_STD = 0.5                   # logits std ~ 4: clear gaps between the scores of experts 1..3
MIN_MARGIN = 1e-6


# ------------------------------------------------------------------------------ fp64 reference

def ref_gelu(h):
    return 0.5 * h * (1.0 + torch.erf(h / math.sqrt(2.0)))


def ref_silu(z):
    return z * (1.0 / (1.0 + torch.exp(-z)))


def ref_expert(m, x):
    """One expert on one token x [dim] from its weights. GELU: W2 gelu(W1 x + b1) + b2. SwiGLU (c_gate present):
    W2 (silu(Wg x) * (W1 x)), no biases."""
    if hasattr(m, "c_gate"):
        return m.c_proj.weight @ (ref_silu(m.c_gate.weight @ x) * (m.c_fc.weight @ x))
    return m.c_proj.weight @ ref_gelu(m.c_fc.weight @ x + m.c_fc.bias) + m.c_proj.bias


def ref_moe(m, x, forced=None, routes=None, margins=None):
    """fp64 MoE, token by token. m: an fp64 copy of the module; x [..., dim] fp64.
    forced [N, k] (CPU): use this expert choice. routes / margins: lists to append each token's chosen experts
    and its k-th minus (k+1)-th biased score to."""
    shape = x.shape
    flat = x.reshape(-1, shape[-1])
    k = m.top_k
    rows = []
    for n in range(flat.shape[0]):
        xt = flat[n]
        logits = m.router.weight @ xt + m.router.bias
        z = torch.exp(logits - logits.max())
        scores = z / z.sum()
        biased = (scores + m.router_bias).detach()
        order = torch.sort(biased, descending=True, stable=True).indices.tolist()
        if margins is not None and k < len(order):
            margins.append((biased[order[k - 1]] - biased[order[k]]).item())
        chosen = order[:k] if forced is None else [int(j) for j in forced[n]]
        if routes is not None:
            routes.append(chosen)
        norm = sum(scores[j] for j in chosen)
        y = sum((scores[j] / norm) * ref_expert(m.experts[j], xt) for j in chosen)
        for s in m.shared:
            y = y + ref_expert(s, xt)
        rows.append(y)
    return torch.stack(rows).reshape(shape)


# ------------------------------------------------------------------------------ modules and inputs

def _set_hot(m):
    """Expert 0 wins every first slot (+10 > any score), IDLE never win (-10), 1..3 compete on the scores."""
    with torch.no_grad():
        m.router_bias.zero_()
        m.router_bias[HOT] = 10.0
        m.router_bias[list(IDLE)] = -10.0


def _moe(dispatch, activation="gelu", hot=False, seed=SEED):
    torch.manual_seed(seed)
    m = SparseMoE(DIM, E, K, num_shared=1, dispatch=dispatch, router_init_std=ROUTER_STD, activation=activation)
    g = torch.Generator().manual_seed(seed + 1)
    with torch.no_grad():
        m.router.bias.copy_(torch.randn(E, generator=g) * 0.5)
        m.router_bias.copy_(torch.randn(E, generator=g) * 0.05)
        for mod in m.modules():                      # non-zero biases, so a dropped bias term shows
            if isinstance(mod, nn.Linear) and mod is not m.router and mod.bias is not None:
                mod.bias.copy_(torch.randn(mod.bias.shape, generator=g) * 0.02)
        if activation == "swiglu":                   # SiLU(W_gate x) away from its near-linear region at 0
            for e in [*m.experts, *m.shared]:
                e.c_gate.weight.mul_(10.0)
                e.c_fc.weight.mul_(10.0)
    if hot:
        _set_hot(m)
    return m


def _x(n=None, device="cpu", seed=SEED):
    g = torch.Generator().manual_seed(seed + 2)      # CPU generator: the same x on every device
    shape = (B, T, DIM) if n is None else (n, DIM)
    return torch.randn(shape, generator=g).to(device).requires_grad_(True)


def _pair_routes(n):
    """[n, 2] every token on PAIR_EXPERTS, odd tokens in the reverse order."""
    a, b = PAIR_EXPERTS
    r = torch.tensor([[a, b], [b, a]], dtype=torch.long)
    return r.repeat((n + 1) // 2, 1)[:n]


def _counts(routes):
    return torch.bincount(torch.as_tensor(routes, dtype=torch.long).reshape(-1), minlength=E)


# ------------------------------------------------------------------------------ pairs

def _natural_case(name, dispatch, activation="gelu", hot=False, n=None):
    """The module routes on its own; the builder checks the fp64 routing has clear margins and, for .hot, is
    the skew the pair claims."""
    def build(device):
        fast = _moe(dispatch, activation=activation, hot=hot).to(device)
        ref = to64(fast)
        x = _x(n=n, device=device)
        routes, margins = [], []
        with torch.no_grad():
            ref_moe(ref, x.double(), routes=routes, margins=margins)
        assert min(margins) > MIN_MARGIN, f"{name}: routing near tie (margin {min(margins):.1e}); change SEED"
        c = _counts(routes)
        if hot:
            assert c[HOT] == len(routes) and c[list(IDLE)].sum() == 0, f"{name}: not the hot routing: {c.tolist()}"
        assert (c == 0).sum() >= 2, f"{name}: expected idle experts, counts {c.tolist()}"
        return Case(ref=lambda i: ref_moe(ref, i), fast=fast, inputs=[x],
                    params_ref=list(ref.parameters()), params_fast=list(fast.parameters()))
    return build


def _pair_case(dispatch):
    """Replayed routing: both sides use _pair_routes; the gates still come from the router (it gets a gradient)."""
    def build(device):
        fast = _moe(dispatch).to(device)
        ref = to64(fast)
        forced = _pair_routes(N)
        forced_dev = forced.to(device)

        def fast_fn(i):
            with replay_routing(fast, forced_dev):
                return fast(i)

        return Case(ref=lambda i: ref_moe(ref, i, forced=forced), fast=fast_fn, inputs=[_x(device=device)],
                    params_ref=list(ref.parameters()), params_fast=list(fast.parameters()))
    return build


def _bf16_hot_case(dispatch):
    """Lab init (proj_std from the lab config), hot routing, bf16 autocast. The bf16 expert choice on the bf16
    input is recorded and replayed in the reference: slot 2 among experts 1..3 may differ from fp64 rounding."""
    def build(device):
        torch.manual_seed(SEED)
        fast = SparseMoE(DIM, E, K, num_shared=1, dispatch=dispatch,
                         proj_std=_residual_std(ModelConfig(n_embd=DIM)))
        _set_hot(fast)
        fast = fast.to(device)
        ref = to64(fast)
        x = _x(device=device)

        def amp():
            return torch.autocast(device.type, dtype=torch.bfloat16)

        rec = []
        with torch.no_grad(), amp(), record_routing(fast, rec):
            fast(x.to(torch.bfloat16))
        forced = rec[0].long().cpu()
        c = _counts(forced)
        assert c[HOT] == N and c[list(IDLE)].sum() == 0, f"moe_rot.{dispatch}.hot.bf16: not hot: {c.tolist()}"

        def fast_fn(i):
            with amp():
                return fast(i)

        return Case(ref=lambda i: ref_moe(ref, i, forced=forced), fast=fast_fn, inputs=[x],
                    params_ref=list(ref.parameters()), params_fast=list(fast.parameters()))
    return build


for _d in FAST:
    pair(f"moe_rot.{_d}.hot")(_natural_case(f"moe_rot.{_d}.hot", _d, hot=True))
    pair(f"moe_rot.{_d}.hot.swiglu")(_natural_case(f"moe_rot.{_d}.hot.swiglu", _d, activation="swiglu", hot=True))
    pair(f"moe_rot.{_d}.pair")(_pair_case(_d))
    pair(f"moe_rot.{_d}.tiny")(_natural_case(f"moe_rot.{_d}.tiny", _d, n=TINY_N))
    pair(f"moe_rot.{_d}.hot.bf16", dtype=torch.bfloat16)(_bf16_hot_case(_d))

PAIR_NAMES = pairs_in(__name__)
FP32_PAIRS = [n for n in PAIR_NAMES if PAIRS[n].dtype == torch.float32]


def test_registered_pairs():
    want = [f"moe_rot.{d}.{s}" for d in FAST for s in ("hot", "hot.swiglu", "pair", "tiny", "hot.bf16")]
    assert sorted(PAIR_NAMES) == sorted(want)


@pytest.mark.parametrize("name", PAIR_NAMES)
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    assert "out[0]" in errors and "grad_in[0]" in errors, f"{name}: output and input gradient must be compared"
    n_params = len(PAIRS[name].build(device).params_fast)
    got = len([k for k in errors if k.startswith("grad_param")])
    assert got == n_params, f"{name}: {got} of {n_params} parameter gradients compared"


@pytest.mark.parametrize("name", FP32_PAIRS)
def test_pair_fails_the_1_01_drill(name, device):
    # must fail on the numerical comparison of the output, not on any other assertion
    with pytest.raises(AssertionError, match=r"out\[0\]: rel_err="):
        check(PAIRS[name], device, fast_override=scaled(1.01))


# ------------------------------------------------------------------------------ plain checks

@pytest.mark.parametrize("dispatch", FAST)
def test_hot_routing_is_skewed(dispatch, device):
    """The fast module's own counts: expert 0 has every token, IDLE none, max / mean = E / K = 4."""
    m = _moe(dispatch, hot=True).to(device).train()
    with torch.no_grad():
        m(_x(device=device))
    c = m._counts.cpu()
    assert c[HOT] == N and c[list(IDLE)].sum() == 0 and c.sum() == N * K
    assert c.max() / c.mean() == E / K


@pytest.mark.parametrize("dispatch", FAST)
def test_matches_loop_dispatch_on_hot_routing(dispatch, device):
    """Fast dispatch vs the loop dispatch (same weights, fp32): outputs and every gradient within the fp32
    tolerances. Idle experts: loop leaves None, the fast path must give exact zeros."""
    x = _x(device=device).detach()
    cot = torch.randn(x.shape, generator=torch.Generator().manual_seed(SEED + 3)).to(device)
    res = {}
    for d in ("loop", dispatch):
        m = _moe(d, hot=True).to(device)
        xi = x.clone().requires_grad_(True)
        y = m(xi)
        y.backward(cot)
        res[d] = (m, y.detach(), xi.grad)
    (ml, yl, gl), (mf, yf, gf) = res["loop"], res[dispatch]
    assert rel_err(yf, yl) < 1e-5
    assert rel_err(gf, gl) < 5e-5
    for (name, pl), pf in zip(ml.named_parameters(), mf.parameters()):
        idle = any(name.startswith(f"experts.{e}.") for e in IDLE)
        if idle:
            assert pl.grad is None, f"loop: idle {name} got a gradient"
            assert pf.grad is not None and torch.count_nonzero(pf.grad) == 0, f"{dispatch}: idle {name} not zero"
        else:
            assert rel_err(pf.grad, pl.grad) < 5e-5, f"{dispatch}: {name}"
    assert torch.count_nonzero(mf.experts[HOT].c_fc.weight.grad) > 0
