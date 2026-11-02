"""MoE: every dispatch in models.moe.DISPATCH against a token-by-token fp64 reference.

Reference (written from the models/moe.py docstring, never by calling SparseMoE.forward or a dispatch; it reads only
the module's weights): for each token on its own, fp64 router logits -> softmax -> top-k on (scores + router_bias)
by a plain sort -> gates = the chosen scores renormalised to 1 -> sum gate * expert(token) + every shared expert.
GELU by its erf formula. Only the chosen experts run, so an expert with no tokens has no gradient on either side.

Pairs, one set per dispatch (a new fast dispatch in DISPATCH is tested with no change here):
  moe.<d>            lab shape: 8 experts, top-2, 1 shared; x [2, 37, 64]; fp32, outputs and every gradient
  moe.<d>.idle       as above, expert 7 never chosen (router_bias -10): the dispatch skips it, its gradient is None
  moe.<d>.top3       top-3 of 4, no shared expert. Not top-1: renormalised top-1 gates are s / s = 1, so the router
                     gradient is exactly 0 and fp32 rounding noise (~1e-8) against 0 is not a relative error
  moe.<d>.bf16       the lab init under bf16 autocast, TOLERANCES[bfloat16]. In bf16 a token can pick other experts
                     than in fp64, so this reference REPLAYS the fast routing (the expert choice only; gates and
                     experts are still fp64). bf16 pairs are not in the 1.01 drill (framework.py: Precision).
  moe.<d>.swiglu     as moe.<d>, every routed and shared expert SwiGLU (model.activation=swiglu): the reference
                     expert is W_down @ (SiLU(W_gate x) * W_up x), SiLU by its formula, no biases. Gate and up
                     weights x10 so SiLU works in its curved region, not at z ~ 0 where SiLU(z) ~ z/2.
  moe.<d>.swiglu.bf16  moe.<d>.bf16 with SwiGLU experts (routing replayed, as above).
The fp32 pairs route in the reference on their own (no replay), so the pairs check the expert choice too, not only
expert math, gates and gradients. They use a large router init (logits std ~4) and a non-zero router_bias, and the
builder asserts every routing margin is > 1e-6, so fp32 and fp64 never pick different experts. The seed is fixed, so
the margins are too; if that assert fires after a change, change SEED.
The 1.01 drill and the determinism check run on every registered pair (test_framework.py, framework.check).

Routing replay (models/reversible.py relies on it), deterministic:
  * replay_routing(moe, idx) with idx from record_routing gives exactly the normal forward and gradients.
  * near tie: router row 2 = row 1 + 1e-6 * noise, and a selection bias that makes experts 1 and 2 compete for the
    second slot of every token. Record on x, then run x + 1e-4 * noise: without replay some token's top-k changes,
    with replay none does, and the router still gets a gradient (the gates come from the router scores).
    Measured: without the selection bias the flips depend on the seed (0 flips for 2 seeds of 5 at 74 tokens).
    This is the reversible failure: a reconstructed input ~1e-5 off flips a near-tie token.
  * clear switch: experts 1 and 2 differ only on coordinate 0, and x moves from -1e-3 to +1e-3 there, so every token
    switches from expert 1 to expert 2 without replay, and replay must hold expert 1. No dependence on rounding.

Property tests (no pair): router_bias changes the selection but not the gate values; update_bias() moves the bias
by +-gamma toward balance and clears the counts; counts sum to N * top_k in training and are not kept in eval;
the shared expert runs on every token; the router runs in fp32 under bf16 autocast (same expert choice as
fp32); with the lab init f is on the dense MLP's scale (measured 1.22x at
lab_small width; PyTorch's default Linear init gives 9.4x).
"""
from __future__ import annotations

import math

import pytest
import torch
import torch.nn as nn

from correctness.framework import PAIRS, Case, check, pair, pairs_in, rel_err, to64
from models.config import ModelConfig
from models.gpt import MLP, _residual_std
from models.moe import DISPATCH, SparseMoE, record_routing, replay_routing


DIM, B, T, SEED = 64, 2, 37, 0
ROUTER_STD = 0.5          # logits std ~ 0.5 * sqrt(64) = 4: peaked scores, clear top-k margins
MIN_MARGIN = 1e-6


# ------------------------------------------------------------------------------ the reference

def ref_gelu(h):
    return 0.5 * h * (1.0 + torch.erf(h / math.sqrt(2.0)))


def ref_silu(z):
    return z / (1.0 + torch.exp(-z))


def ref_expert(m, x):
    """One ExpertMLP on one token x [dim], fp64. GELU: c_proj(GELU(c_fc x + b) ) + b. SwiGLU (the module has a
    c_gate): c_proj(SiLU(c_gate x) * c_fc x), no biases."""
    if hasattr(m, "c_gate"):
        return m.c_proj.weight @ (ref_silu(m.c_gate.weight @ x) * (m.c_fc.weight @ x))
    return m.c_proj.weight @ ref_gelu(m.c_fc.weight @ x + m.c_fc.bias) + m.c_proj.bias


def reference_moe(moe, x, forced=None, margins=None):
    """fp64 MoE one token at a time. moe: an fp64 copy of the module; x [..., dim] fp64.

    forced [N, k]: use this expert choice instead of the top-k (the replayed routing). margins: if a list, the gap
    between the k-th and (k+1)-th biased score of every token is appended (a near tie could flip fp32 vs fp64).
    """
    shape = x.shape
    x = x.reshape(-1, shape[-1])
    E, k = moe.num_experts, moe.top_k
    rows = []
    for n in range(x.shape[0]):
        xt = x[n]
        logits = moe.router.weight @ xt + moe.router.bias
        e = torch.exp(logits - logits.max())
        scores = e / e.sum()
        biased = [(scores[j] + moe.router_bias[j]).item() for j in range(E)]
        order = sorted(range(E), key=lambda j: -biased[j])
        if margins is not None and k < E:
            margins.append(biased[order[k - 1]] - biased[order[k]])
        chosen = order[:k] if forced is None else [int(j) for j in forced[n]]
        total = sum(scores[j] for j in chosen)
        y = sum((scores[j] / total) * ref_expert(moe.experts[j], xt) for j in chosen)
        for s in moe.shared:
            y = y + ref_expert(s, xt)
        rows.append(y)
    return torch.stack(rows).reshape(shape)


# ------------------------------------------------------------------------------ pairs

def _moe(dispatch, num_experts=8, top_k=2, num_shared=1, seed=SEED, router_std=ROUTER_STD, bias_std=0.05,
         activation="gelu"):
    torch.manual_seed(seed)
    m = SparseMoE(DIM, num_experts, top_k, num_shared=num_shared, dispatch=dispatch, router_init_std=router_std,
                  activation=activation)
    g = torch.Generator().manual_seed(seed + 1)
    with torch.no_grad():
        m.router.bias.copy_(torch.randn(num_experts, generator=g) * 0.5)
        m.router_bias.copy_(torch.randn(num_experts, generator=g) * bias_std)
        # random biases everywhere, so a dropped bias term shows (the init zeros them; SwiGLU has none)
        for mod in m.modules():
            if isinstance(mod, nn.Linear) and mod is not m.router and mod.bias is not None:
                mod.bias.copy_(torch.randn(mod.bias.shape, generator=g) * 0.02)
        if activation == "swiglu":       # gate and up std 0.2: SiLU(W_gate x) away from its linear part near 0
            for e in [*m.experts, *m.shared]:
                e.c_gate.weight.mul_(10.0)
                e.c_fc.weight.mul_(10.0)
    return m


def _x(seed=SEED, n=None, device="cpu"):
    g = torch.Generator().manual_seed(seed + 2)       # CPU generator: the same x on every device
    shape = (B, T, DIM) if n is None else (n, DIM)
    return torch.randn(shape, generator=g).to(device).requires_grad_(True)


def _fp32_case(name, dispatch, **kw):
    idle = kw.pop("idle", False)

    def build(device):
        fast = _moe(dispatch, **kw)
        if idle:
            with torch.no_grad():
                fast.router_bias[-1] = -10.0
        fast = fast.to(device)
        ref = to64(fast)
        x = _x(device=device)
        margins = []
        with torch.no_grad():
            reference_moe(ref, x.double(), margins=margins)
        assert min(margins) > MIN_MARGIN, f"{name}: routing near tie (margin {min(margins):.1e}); change SEED"
        return Case(ref=lambda i: reference_moe(ref, i), fast=fast, inputs=[x],
                    params_ref=list(ref.parameters()), params_fast=list(fast.parameters()))
    return build


def _bf16_case(dispatch, activation="gelu"):
    def build(device):
        torch.manual_seed(SEED)
        cfg = ModelConfig(n_embd=DIM)
        fast = SparseMoE(DIM, 8, 2, num_shared=1, dispatch=dispatch, proj_std=_residual_std(cfg),
                         activation=activation).to(device)
        # small: at the lab init the scores are ~1/8 +- 1e-3, and a 0.05 bias would route alone (4 experts idle)
        with torch.no_grad():
            fast.router_bias.copy_(torch.randn(8, generator=torch.Generator().manual_seed(SEED)) * 1e-3)
        ref = to64(fast)
        x = _x(device=device)

        def amp():
            return torch.autocast(device.type, dtype=torch.bfloat16)

        routes = []                                  # the bf16 expert choice, on the bf16 input check() feeds
        with torch.no_grad(), amp(), record_routing(fast, routes):
            fast(x.to(torch.bfloat16))

        def fast_fn(i):
            with amp():
                return fast(i)

        return Case(ref=lambda i: reference_moe(ref, i, forced=routes[0]), fast=fast_fn, inputs=[x],
                    params_ref=list(ref.parameters()), params_fast=list(fast.parameters()))
    return build


for _d in DISPATCH:
    pair(f"moe.{_d}")(_fp32_case(f"moe.{_d}", _d))
    pair(f"moe.{_d}.idle")(_fp32_case(f"moe.{_d}.idle", _d, idle=True))
    pair(f"moe.{_d}.top3")(_fp32_case(f"moe.{_d}.top3", _d, num_experts=4, top_k=3, num_shared=0))
    pair(f"moe.{_d}.bf16", dtype=torch.bfloat16)(_bf16_case(_d))
    pair(f"moe.{_d}.swiglu")(_fp32_case(f"moe.{_d}.swiglu", _d, activation="swiglu"))
    pair(f"moe.{_d}.swiglu.bf16", dtype=torch.bfloat16)(_bf16_case(_d, activation="swiglu"))


@pytest.mark.parametrize("name", pairs_in(__name__))
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    assert "out[0]" in errors and "grad_in[0]" in errors, f"{name}: output and input gradient must be compared"
    assert len([k for k in errors if k.startswith("grad_param")]) >= 5, f"{name}: too few gradients compared"


def test_one_set_of_pairs_per_dispatch():
    want = [f"moe.{d}{s}" for d in DISPATCH for s in ("", ".idle", ".top3", ".bf16", ".swiglu", ".swiglu.bf16")]
    assert sorted(pairs_in(__name__)) == sorted(want)


def test_idle_expert_gets_no_tokens(device):
    m = _moe("loop").to(device)
    with torch.no_grad():
        m.router_bias[-1] = -10.0
    out = m(_x(device=device))
    out.sum().backward()
    assert m.experts[-1].c_fc.weight.grad is None, "expert 7 should get no tokens, so no gradient"


# ------------------------------------------------------------------------------ routing replay

@pytest.mark.parametrize("dispatch", list(DISPATCH))
def test_replay_reproduces_forward(dispatch, device):
    m, x = _moe(dispatch).to(device), _x(device=device)
    rec = []
    with record_routing(m, rec):
        y = m(x)
    assert len(rec) == 1
    y.sum().backward()
    gx, gw = x.grad.clone(), m.router.weight.grad.clone()
    x.grad = None
    m.zero_grad()
    with replay_routing(m, rec[0]):
        y2 = m(x)
    y2.sum().backward()
    assert torch.equal(y, y2) and torch.equal(gx, x.grad) and torch.equal(gw, m.router.weight.grad)


@pytest.mark.parametrize("dispatch", list(DISPATCH))
def test_replay_holds_a_near_tie(dispatch, device):
    m = _moe(dispatch, router_std=1.0)
    g = torch.Generator().manual_seed(SEED + 3)
    with torch.no_grad():
        m.router.weight[2] = m.router.weight[1] + 1e-6 * torch.randn(DIM, generator=g)
        m.router.bias[2] = m.router.bias[1]
        m.router_bias.zero_()
        m.router_bias[0] = 10.0                       # expert 0 always takes the first slot ...
        m.router_bias[1] = m.router_bias[2] = 5.0     # ... and experts 1, 2 compete for the second on every token
    m = m.to(device)
    x = _x(n=256).detach()
    x2 = (x + 1e-4 * torch.randn(x.shape, generator=g)).to(device)
    x = x.to(device)
    rec, free, held = [], [], []
    with torch.no_grad(), record_routing(m, rec):
        m(x)
    with torch.no_grad(), record_routing(m, free):
        m(x2)
    sort = lambda t: t.sort(dim=1).values
    flips = (sort(rec[0]) != sort(free[0])).any(dim=1).sum().item()
    assert flips > 0, "no token changed experts without replay: the test proves nothing; change SEED"
    x2.requires_grad_(True)
    with replay_routing(m, rec[0]), record_routing(m, held):
        y = m(x2)
    assert torch.equal(held[0], rec[0]), "with replay a token changed experts"
    y.sum().backward()
    assert m.router.weight.grad is not None and m.router.weight.grad.abs().sum() > 0, "router got no gradient"
    assert x2.grad is not None and x2.grad.abs().sum() > 0, "input got no gradient under replay"


@pytest.mark.parametrize("dispatch", list(DISPATCH))
def test_replay_overrides_a_clear_switch(dispatch, device):
    m = _moe(dispatch, router_std=1.0)
    with torch.no_grad():
        # Make the expected flip deterministic: expert 0 owns the first slot, while
        # experts 1 and 2 have equal selection bias and differ only on coordinate 0.
        m.router.weight.zero_()
        m.router.weight[2, 0] = 1.0
        m.router.bias.zero_()
        m.router_bias.zero_()
        m.router_bias[0] = 10.0                       # expert 0 always takes the first slot ...
        m.router_bias[1] = m.router_bias[2] = 5.0     # ... and experts 1, 2 compete for the second on every token
    m = m.to(device)
    x = torch.zeros(256, DIM)
    x[:, 0] = -1e-3
    x2 = x.clone()
    x2[:, 0] = 1e-3
    x, x2 = x.to(device), x2.to(device)
    rec, free, held = [], [], []
    with torch.no_grad(), record_routing(m, rec):
        m(x)
    with torch.no_grad(), record_routing(m, free):
        m(x2)
    sort = lambda t: t.sort(dim=1).values
    assert torch.all(sort(rec[0])[:, 1] == 1), "negative coordinate should select expert 1"
    assert torch.all(sort(free[0])[:, 1] == 2), "positive coordinate should select expert 2 without replay"
    x2.requires_grad_(True)
    with replay_routing(m, rec[0]), record_routing(m, held):
        y = m(x2)
    assert torch.equal(held[0], rec[0]), "with replay a token changed experts"
    y.sum().backward()
    assert m.router.weight.grad is not None and m.router.weight.grad.abs().sum() > 0, "router got no gradient"
    assert x2.grad is not None and x2.grad.abs().sum() > 0, "input got no gradient under replay"


# ------------------------------------------------------------------------------ properties

def test_router_bias_steers_selection_not_gates(device):
    m, x = _moe("loop").to(device), _x(device=device).detach()
    ref = to64(m)
    # a constant shift of every bias keeps the order, so nothing may change
    before = m(x)
    with torch.no_grad():
        m.router_bias += 3.0
    assert torch.equal(before, m(x))
    # a large bias on expert 3 puts it in every token's top-2; the gates still come from the plain scores
    with torch.no_grad():
        m.router_bias[3] += 10.0
    rec = []
    with record_routing(m, rec):
        out = m(x)
    assert (rec[0] == 3).any(dim=1).all(), "the bias did not change the selection"
    with torch.no_grad():
        want = reference_moe(ref, x.double(), forced=rec[0])     # ref has the old bias: forced choice, plain gates
    assert rel_err(out, want) < 1e-5


def test_router_runs_in_fp32_under_autocast(device):
    # models/moe.py: the router casts x to fp32 with autocast off. Then the expert choice under bf16 autocast is
    # bit-identical to a plain fp32 run on the same (bf16-valued) input. A router left in bf16 changes it: at the
    # lab init the scores are ~1/8 +- 1e-3, finer than bf16 logits resolve.
    cfg = ModelConfig(n_embd=DIM)
    torch.manual_seed(SEED)
    m = SparseMoE(DIM, 8, 2, num_shared=1, proj_std=_residual_std(cfg)).to(device)
    x = _x(n=512, device=device).detach().to(torch.bfloat16)
    amp, plain = [], []
    with torch.no_grad(), torch.autocast(device.type, dtype=torch.bfloat16), record_routing(m, amp):
        m(x)
    with torch.no_grad(), record_routing(m, plain):
        m(x.float())
    assert torch.equal(amp[0], plain[0]), "routing under bf16 autocast differs from fp32: the router is not in fp32"


@pytest.mark.parametrize("dispatch", list(DISPATCH))
def test_update_bias_moves_toward_balance(dispatch, device):
    m = _moe(dispatch).to(device)
    with torch.no_grad():
        m.router_bias.zero_()
    m.train()
    x = _x(device=device).detach()
    rec = []
    with torch.no_grad(), record_routing(m, rec):
        m(x)
    counts = m._counts.clone()
    assert torch.equal(counts, torch.bincount(rec[0].long().reshape(-1), minlength=m.num_experts).float())
    assert counts.sum().item() == x.shape[0] * x.shape[1] * m.top_k
    m.update_bias()
    step = m.gamma * torch.sign(counts.mean() - counts)
    assert torch.equal(m.router_bias, step), "bias must move by +-gamma toward the mean count (0 at the mean)"
    assert (m.router_bias[counts > counts.mean()] < 0).all() and (m.router_bias[counts < counts.mean()] > 0).all()
    assert m._counts is None, "update_bias must clear the counts"
    m.update_bias()
    assert torch.equal(m.router_bias, step), "a second call with no new counts must not move the bias"


def test_no_counts_in_eval(device):
    m = _moe("loop").to(device).eval()
    with torch.no_grad():
        m(_x(device=device))
    assert m._counts is None


def test_shared_expert_runs_on_every_token(device):
    m, x = _moe("loop").to(device), _x(device=device).detach()
    with torch.no_grad():
        for e in m.experts:                          # routed experts output 0, only the shared one is left
            e.c_proj.weight.zero_()
            e.c_proj.bias.zero_()
        out = m(x)
        shared = m.shared[0](x)
    assert torch.equal(out, shared)
    assert (shared.reshape(-1, DIM).norm(dim=1) > 0).all()


def test_lab_init_matches_dense_scale():
    cfg = ModelConfig(n_embd=256, n_layer=9)          # lab_small width and depth
    d, ps = cfg.n_embd, _residual_std(cfg)
    torch.manual_seed(SEED)
    x = torch.randn(512, d)
    dense = MLP(cfg, "mlp")
    moe = SparseMoE(d, 8, 2, expert_hidden=cfg.mlp_ratio * d, num_shared=1, proj_std=ps)
    default = SparseMoE(d, 8, 2, expert_hidden=cfg.mlp_ratio * d, num_shared=1, proj_std=ps)
    for mod in default.modules():
        if isinstance(mod, nn.Linear):
            mod.reset_parameters()                   # PyTorch's default Linear init
    with torch.no_grad():
        base = dense(x).std()
        lab, dflt = (moe(x).std() / base).item(), (default(x).std() / base).item()
    assert 0.5 < lab < 2.0, f"lab init f is {lab:.2f}x the dense MLP"
    assert dflt > 4.0, f"default init gives {dflt:.2f}x: the bound above would not catch a lost init"
