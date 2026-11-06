"""Top-k sparse Mixture of Experts (model.ffn=moe: 1 shared + top-2 of 8 routed experts).

Attributes the fp64 test reference reads (keep these names):
    router       nn.Linear(dim, num_experts), run in fp32 with autocast off
    router_bias  buffer [num_experts]: steers selection only, never the gate weights
    experts      ModuleList of ExpertMLP ("gelu" or "swiglu", as gpt.MLP; swiglu has no biases)
    shared       ModuleList of ExpertMLP, always on, same hidden size as a routed expert
    top_k, num_experts

forward(x [..., dim]) -> same shape:
    scores = softmax(router(x)); top-k on (scores + router_bias); gates = scores of the chosen, renormalised to
    sum 1; out = sum gate * expert(x) + sum shared(x).
update_bias(): router_bias += gamma * sign(mean_count - count), counts summed since the last call (training only).
Routing replay (models/reversible.py): record_routing(moe, out) appends the chosen indices; replay_routing(moe, idx)
makes forward use idx. Gates are always recomputed from the scores, so the router still gets its gradient.
Init: as the dense MLP, c_proj normal(0, proj_std), router normal(0, router_init_std).

DISPATCH = {"loop", "sorted", "grouped"}: loop is the reference (default); sorted and grouped pack routes into a
padded buffer (see their docstrings). sorted gives idle experts zero gradients where loop leaves None.
Regions (level 3): {name}.router, {name}.dispatch, {name}.shared; inside dispatch, {name}.dispatch.expert{e} (loop),
{name}.dispatch.grouped (sorted), {name}.dispatch.grouped_fixed (grouped).
"""
from __future__ import annotations

from contextlib import contextmanager

import torch
import torch.nn as nn
import torch.nn.functional as F

from perfkit.regions import region


ACTIVATIONS = ("gelu", "swiglu")


class ExpertMLP(nn.Module):
    def __init__(self, dim, hidden, std=0.02, proj_std=0.02, activation="gelu"):
        super().__init__()
        assert activation in ACTIVATIONS, f"activation {activation!r} not in {ACTIVATIONS}"
        self.swiglu = activation == "swiglu"
        bias = not self.swiglu
        self.c_fc = nn.Linear(dim, hidden, bias=bias)      # gelu: input projection; swiglu: the "up" branch
        self.c_proj = nn.Linear(hidden, dim, bias=bias)
        layers = [(self.c_fc, std), (self.c_proj, proj_std)]
        if self.swiglu:                                    # made last, so the GELU experts draw the same init
            self.c_gate = nn.Linear(dim, hidden, bias=False)
            layers.append((self.c_gate, std))
        for lin, s in layers:
            nn.init.normal_(lin.weight, mean=0.0, std=s)
            if lin.bias is not None:
                nn.init.zeros_(lin.bias)

    def forward(self, x):
        if self.swiglu:
            return self.c_proj(F.silu(self.c_gate(x)) * self.c_fc(x))
        return self.c_proj(F.gelu(self.c_fc(x)))


def dispatch_loop(moe, x, topk_idx, gates):
    """x [N, dim], topk_idx [N, k], gates [N, k] -> (out [N, dim], counts [num_experts])."""
    out = torch.zeros_like(x)
    # No host sync: a per-expert `counts[e] = idx.numel()` copied a host int to the GPU (1 sync each), and
    # torch.bincount on CUDA reads max() back to size its output. Compare-and-sum needs neither, and no atomics.
    counts = (topk_idx.reshape(-1, 1) == torch.arange(moe.num_experts, device=x.device)).sum(0).float()
    for e in range(moe.num_experts):
        with region(f"{moe.name}.dispatch.expert{e}", 3):
            pos = topk_idx == e
            tok = pos.any(dim=1)
            if not tok.any():                                   # host sync
                continue
            idx = tok.nonzero(as_tuple=True)[0]                 # host sync
            w = (gates * pos.to(gates.dtype)).sum(dim=1)
            out.index_add_(0, idx, moe.experts[e](x[idx]) * w[idx].unsqueeze(1).to(x.dtype))
    return out, counts


def _batched_experts(moe, buf, region_name):
    """Every routed expert MLP on its own rows of buf [E, cap, dim] as batched matmuls; returns [E, cap, dim].
    Padded rows are never gathered back, so they change no output and get no gradient."""
    w2 = torch.stack([e.c_proj.weight for e in moe.experts]).to(buf.dtype)   # [E, dim, hidden]
    if moe.swiglu:
        w13 = torch.cat([torch.stack([e.c_gate.weight for e in moe.experts]),
                         torch.stack([e.c_fc.weight for e in moe.experts])], dim=1).to(buf.dtype)
        with region(region_name, 3):
            gate, up = torch.bmm(buf, w13.transpose(1, 2)).chunk(2, dim=-1)
            return torch.bmm(F.silu(gate) * up, w2.transpose(1, 2))
    w1 = torch.stack([e.c_fc.weight for e in moe.experts]).to(buf.dtype)     # [E, hidden, dim]
    b1 = torch.stack([e.c_fc.bias for e in moe.experts]).to(buf.dtype)
    b2 = torch.stack([e.c_proj.bias for e in moe.experts]).to(buf.dtype)
    with region(region_name, 3):
        h = torch.baddbmm(b1.unsqueeze(1), buf, w1.transpose(1, 2))
        return torch.baddbmm(b2.unsqueeze(1), F.gelu(h), w2.transpose(1, 2))


def dispatch_sorted(moe, x, topk_idx, gates):
    """Sort the routes, pack them into a padded [E, cap, dim] buffer and run each expert as one batched matmul.
    Unique-index scatters and gathers make gradients identical across runs. cap is the busiest expert's count:
    one host sync per call. Nothing is dropped, so the result matches the loop path."""
    n_tokens, dim = x.shape
    E, k = moe.num_experts, moe.top_k
    flat = topk_idx.reshape(-1)                                              # [N*k] expert of each route
    counts_i = (flat.reshape(-1, 1) == torch.arange(E, device=x.device)).sum(0)
    counts = counts_i.float()
    if flat.numel() == 0:
        return torch.zeros_like(x), counts
    order = torch.argsort(flat, stable=True)                                 # routes grouped by expert
    sorted_e = flat[order]
    start = counts_i.cumsum(0) - counts_i                                    # first sorted position of each expert
    pos = torch.arange(flat.numel(), device=x.device) - start[sorted_e]      # position inside its expert
    cap = int(counts_i.max())                                                # the one host sync
    slot = sorted_e * cap + pos                                              # unique buffer row per route

    routes_in = x.unsqueeze(1).expand(n_tokens, k, dim).reshape(-1, dim)     # backward: sum over k
    buf = x.new_zeros(E * cap, dim).index_copy(0, slot, routes_in[order])    # unique indices

    y = _batched_experts(moe, buf.view(E, cap, dim), f"{moe.name}.dispatch.grouped")    # [E, cap, dim]

    where = torch.empty_like(order)
    where[order] = slot                                                      # buffer row of route r, original order
    routes_out = y.reshape(E * cap, dim)[where].reshape(n_tokens, k, dim)
    out = (routes_out.to(x.dtype) * gates.unsqueeze(-1).to(x.dtype)).sum(dim=1)
    return out, counts


def dispatch_grouped(moe, x, topk_idx, gates):
    """dispatch_sorted with cap fixed to N * top_k (the most one expert can get), so there is no host sync.
    Same outputs and gradients as the loop path; costs an E * N * top_k row buffer."""
    n_tokens, dim = x.shape
    E, k = moe.num_experts, moe.top_k
    flat = topk_idx.reshape(-1)                                              # [N*k] expert of each route
    counts_i = (flat.reshape(-1, 1) == torch.arange(E, device=x.device)).sum(0)
    counts = counts_i.float()
    if flat.numel() == 0:
        return torch.zeros_like(x), counts
    order = torch.argsort(flat, stable=True)                                 # routes grouped by expert
    sorted_e = flat[order]
    start = counts_i.cumsum(0) - counts_i                                    # first sorted position of each expert
    pos = torch.arange(flat.numel(), device=x.device) - start[sorted_e]      # position inside its expert
    cap = n_tokens * k                                                       # fixed bound = N*k routes; host int, no sync
    slot = sorted_e * cap + pos                                              # unique buffer row per route

    routes_in = x.unsqueeze(1).expand(n_tokens, k, dim).reshape(-1, dim)     # backward: sum over k
    buf = x.new_zeros(E * cap, dim).index_copy(0, slot, routes_in[order])    # unique indices

    # Region named .grouped_fixed, not .grouped: dispatch_sorted already labels its batched GEMM
    # "{name}.dispatch.grouped", and the two are timed against each other, so a distinct name keeps the
    # two paths unambiguous in traces and in the per-part timing table.
    y = _batched_experts(moe, buf.view(E, cap, dim), f"{moe.name}.dispatch.grouped_fixed")   # [E, cap, dim]

    where = torch.empty_like(order)
    where[order] = slot                                                      # buffer row of route r, original order
    routes_out = y.reshape(E * cap, dim)[where].reshape(n_tokens, k, dim)
    out = (routes_out.to(x.dtype) * gates.unsqueeze(-1).to(x.dtype)).sum(dim=1)
    return out, counts


DISPATCH = {"loop": dispatch_loop, "sorted": dispatch_sorted, "grouped": dispatch_grouped}


@contextmanager
def record_routing(moe, out: list):
    """Inside the block, every forward of moe appends its chosen top-k indices to out."""
    moe._record = out
    try:
        yield
    finally:
        moe._record = None


@contextmanager
def replay_routing(moe, topk_idx):
    """Inside the block, every forward of moe uses topk_idx instead of its own top-k choice."""
    moe._forced = topk_idx
    try:
        yield
    finally:
        moe._forced = None


class SparseMoE(nn.Module):
    def __init__(self, dim, num_experts=8, top_k=2, expert_hidden=None, num_shared=0,
                 bias_gamma=0.01, dispatch="loop", name="moe", router_init_std=0.02, proj_std=0.02,
                 activation="gelu"):
        super().__init__()
        assert dispatch in DISPATCH, f"dispatch {dispatch!r} not in {list(DISPATCH)}"
        assert 0 < top_k <= num_experts
        self.dim, self.num_experts, self.top_k = dim, num_experts, top_k
        self.expert_hidden = expert_hidden or 4 * dim
        self.gamma, self.dispatch, self.name = bias_gamma, dispatch, name
        self.router = nn.Linear(dim, num_experts)
        nn.init.normal_(self.router.weight, std=router_init_std)
        nn.init.zeros_(self.router.bias)
        self.register_buffer("router_bias", torch.zeros(num_experts))
        self.activation, self.swiglu = activation, activation == "swiglu"
        expert = dict(proj_std=proj_std, activation=activation)
        self.experts = nn.ModuleList(ExpertMLP(dim, self.expert_hidden, **expert) for _ in range(num_experts))
        self.shared = nn.ModuleList(ExpertMLP(dim, self.expert_hidden, **expert) for _ in range(num_shared))
        self._counts = self._record = self._forced = None

    def forward(self, x):
        shape = x.shape
        x = x.reshape(-1, shape[-1])
        with region(f"{self.name}.router", 3):
            with torch.autocast(device_type=x.device.type, enabled=False):    # the router always runs in fp32
                logits = self.router(x.to(self.router.weight.dtype))
            scores = F.softmax(logits, dim=-1)
            if self._forced is not None:
                topk_idx = self._forced.long()
            else:
                # router_bias steers which experts are chosen; the gates below use the plain scores
                topk_idx = torch.topk(scores + self.router_bias, self.top_k, dim=1).indices
            if self._record is not None:
                # uint8: the reversible stack keeps every layer's routing until backward
                self._record.append(topk_idx.to(torch.uint8 if self.num_experts <= 256 else torch.int32))
            gates = torch.gather(scores, 1, topk_idx)
            gates = gates / gates.sum(dim=1, keepdim=True)
        with region(f"{self.name}.dispatch", 3):
            out, counts = DISPATCH[self.dispatch](self, x, topk_idx, gates)
        with region(f"{self.name}.shared", 3):
            for s in self.shared:
                out = out + s(x)
        if self.training:                    # route counts for update_bias, summed until it runs
            c = counts.detach()
            self._counts = c if self._counts is None else self._counts + c
        return out.reshape(shape)

    @torch.no_grad()
    def update_bias(self):
        """Move router_bias toward balance: +gamma for under-used experts, -gamma for over-used ones."""
        if self._counts is not None:
            self.router_bias += self.gamma * torch.sign(self._counts.mean() - self._counts)
            self._counts = None
