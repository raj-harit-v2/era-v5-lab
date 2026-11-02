"""Top-k sparse Mixture of Experts.  [implemented: MVP]

Lab setting (model.ffn=moe in configs/base.yaml): 1 shared expert (always on) + top-2 routed of 8.

  * SparseMoE(dim, num_experts=8, top_k=2, expert_hidden=None, num_shared=0, bias_gamma=0.01,
              dispatch="loop", name="moe", router_init_std=0.02, proj_std=0.02)
  * Attributes the fp64 test reference reads (keep these names):
      router       nn.Linear(dim, num_experts), run in fp32 (cast x to router.weight.dtype, autocast off)
      router_bias  buffer [num_experts]: steers *selection* only, never the gate weights
      experts      ModuleList of ExpertMLP (c_fc: Linear(dim, hidden), GELU, c_proj: Linear(hidden, dim))
      shared       ModuleList of ExpertMLP, always on, same hidden size as a routed expert
      top_k, num_experts
  * Init as the dense NanoGPT MLP: weights normal(0, 0.02), biases zero, c_proj normal(0, proj_std)
    (gpt.py passes the residual std 0.02 / sqrt(2 n_layer)). Router normal(0, router_init_std = 0.02).
    PyTorch's default Linear init makes f ~8x larger than the dense model at init, which breaks the
    reversible reconstruction in bf16 (2.5e-2 vs 1.8e-4 at 9 layers).
  * forward(x [..., dim]) -> same shape:
      scores = softmax(router(x)); top-k on (scores + router_bias); gates = scores of the chosen,
      renormalised to sum 1; out = sum gate * expert(x) + sum shared(x).
  * update_bias(): router_bias += gamma * sign(mean_count - count), counts summed since the last call.
    Counts are kept only in training mode (not in eval). In the reversible stack the forward runs 3 times
    per step (forward, invert, recompute) with the same routing (replayed), so counts triple exactly;
    sign() makes the update the same.
  * Routing replay (used by models/reversible.py): with `record_routing(moe, out_list)` the chosen top-k
    indices are appended to out_list; with `replay_routing(moe, idx)` forward uses idx instead of top-k.
    Without it a reconstructed input that differs by 1e-5 can flip a near-tie token to other experts,
    and the reversible backward rebuilds the wrong state (bf16: gradient errors up to 23%).
    Gates are always recomputed from the router scores, so the router still gets its gradient.
  * DISPATCH = {"loop": dispatch_loop, "sorted": dispatch_sorted, "grouped": dispatch_grouped}. The loop path
    gathers per expert and is the reference. The sorted path sorts token/expert assignments, packs them into a
    padded [experts, cap, dim] buffer and runs each expert MLP as one batched matmul. Every scatter and gather uses
    unique indices, so two runs give identical gradients on CUDA. It reads only the largest per-expert route
    count back to the host (one sync per call; the loop syncs twice per expert). The grouped path is sorted with
    a fixed cap = N*k (N tokens, k = top_k): the worst-case route count for one expert, so nothing is dropped and
    the result matches, but cap is a host-side constant (no int(counts.max()) read) so the dispatch has zero host
    syncs, at the cost of a larger (E * N*k) buffer.
    Both paths compute token counts with a device-side compare-and-sum over topk_idx. Since sorted packs all
    expert parameters together, idle experts receive zero gradients rather than None; the loop remains default
    until the optimizer-state effect of that difference is resolved and server timings are collected.
  * Regions (level 3): f"{name}.router", f"{name}.dispatch", f"{name}.shared"; inside dispatch, the loop path
    has f"{name}.dispatch.expert{e}", the sorted path f"{name}.dispatch.grouped" and the grouped path
    f"{name}.dispatch.grouped_fixed".

Extra: "dense" dispatch (every expert on every token, exact, slow), capacity factor, aux / z loss.
Done when: correctness/test_moe.py passes for every entry in DISPATCH.
"""
from __future__ import annotations

from contextlib import contextmanager

import torch
import torch.nn as nn
import torch.nn.functional as F

from perfkit.regions import region


class ExpertMLP(nn.Module):
    def __init__(self, dim, hidden, std=0.02, proj_std=0.02):
        super().__init__()
        self.c_fc = nn.Linear(dim, hidden)
        self.c_proj = nn.Linear(hidden, dim)
        for lin, s in ((self.c_fc, std), (self.c_proj, proj_std)):
            nn.init.normal_(lin.weight, mean=0.0, std=s)
            nn.init.zeros_(lin.bias)

    def forward(self, x):
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


def dispatch_sorted(moe, x, topk_idx, gates):
    """Sort the (token, expert) routes, pack them into a padded [experts, cap, dim] buffer, and run each expert
    MLP as one batched matmul over its own tokens.

    Every expert weight is read once per call (not once per route), and every scatter or gather below uses
    unique indices (a permutation or distinct slots), so the backward has no colliding atomics and two runs
    give identical gradients. The fan-out of a token to its k experts is an expand, whose backward is a sum.
    `cap` is the busiest expert's route count, read back once per call (one host sync, against two per expert
    in the loop path); nothing is dropped, so the result matches the loop path.
    """
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

    w1 = torch.stack([e.c_fc.weight for e in moe.experts]).to(buf.dtype)     # [E, hidden, dim]
    b1 = torch.stack([e.c_fc.bias for e in moe.experts]).to(buf.dtype)
    w2 = torch.stack([e.c_proj.weight for e in moe.experts]).to(buf.dtype)   # [E, dim, hidden]
    b2 = torch.stack([e.c_proj.bias for e in moe.experts]).to(buf.dtype)
    with region(f"{moe.name}.dispatch.grouped", 3):
        h = torch.baddbmm(b1.unsqueeze(1), buf.view(E, cap, dim), w1.transpose(1, 2))
        y = torch.baddbmm(b2.unsqueeze(1), F.gelu(h), w2.transpose(1, 2))    # [E, cap, dim]

    where = torch.empty_like(order)
    where[order] = slot                                                      # buffer row of route r, original order
    routes_out = y.reshape(E * cap, dim)[where].reshape(n_tokens, k, dim)
    out = (routes_out.to(x.dtype) * gates.unsqueeze(-1).to(x.dtype)).sum(dim=1)
    return out, counts


def dispatch_grouped(moe, x, topk_idx, gates):
    """Like dispatch_sorted, but with a fixed buffer height, so there is no host sync at all.

    dispatch_sorted reads cap = int(counts_i.max()) back to the host (one sync) to size the
    [E, cap, dim] buffer to the busiest expert. Here cap is fixed to N*k (N = number of tokens, k =
    top_k), the total number of routes, which is the most any single expert could ever receive. It is a
    host-side constant from x.shape and moe.top_k, never read from the GPU, so the whole dispatch runs
    without a sync and the CPU can queue ahead (and the step can later be captured as a CUDA graph).

    Nothing is dropped (N*k can never overflow), so the output and every gradient match the loop
    reference exactly, as dispatch_sorted does. The trade is memory: the buffer is E * N*k rows rather
    than E * (busiest count). The extra padded rows are run through the expert GEMM but never gathered
    back, and the gradient flowing into them is zero, so they change neither the output nor any weight
    gradient (dispatch_sorted already relies on this for its own padding).
    """
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

    w1 = torch.stack([e.c_fc.weight for e in moe.experts]).to(buf.dtype)     # [E, hidden, dim]
    b1 = torch.stack([e.c_fc.bias for e in moe.experts]).to(buf.dtype)
    w2 = torch.stack([e.c_proj.weight for e in moe.experts]).to(buf.dtype)   # [E, dim, hidden]
    b2 = torch.stack([e.c_proj.bias for e in moe.experts]).to(buf.dtype)
    # Region named .grouped_fixed, not .grouped: dispatch_sorted already labels its batched GEMM
    # "{name}.dispatch.grouped", and Task 4 times sorted against grouped, so a distinct name keeps the
    # two paths unambiguous in traces and in the per-part timing table.
    with region(f"{moe.name}.dispatch.grouped_fixed", 3):
        h = torch.baddbmm(b1.unsqueeze(1), buf.view(E, cap, dim), w1.transpose(1, 2))
        y = torch.baddbmm(b2.unsqueeze(1), F.gelu(h), w2.transpose(1, 2))    # [E, cap, dim]

    where = torch.empty_like(order)
    where[order] = slot                                                      # buffer row of route r, original order
    routes_out = y.reshape(E * cap, dim)[where].reshape(n_tokens, k, dim)
    out = (routes_out.to(x.dtype) * gates.unsqueeze(-1).to(x.dtype)).sum(dim=1)
    return out, counts


DISPATCH = {"loop": dispatch_loop, "sorted": dispatch_sorted, "grouped": dispatch_grouped}


@contextmanager
def record_routing(moe, out: list):
    moe._record = out
    try:
        yield
    finally:
        moe._record = None


@contextmanager
def replay_routing(moe, topk_idx):
    moe._forced = topk_idx
    try:
        yield
    finally:
        moe._forced = None


class SparseMoE(nn.Module):
    def __init__(self, dim, num_experts=8, top_k=2, expert_hidden=None, num_shared=0,
                 bias_gamma=0.01, dispatch="loop", name="moe", router_init_std=0.02, proj_std=0.02):
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
        self.experts = nn.ModuleList(ExpertMLP(dim, self.expert_hidden, proj_std=proj_std) for _ in range(num_experts))
        self.shared = nn.ModuleList(ExpertMLP(dim, self.expert_hidden, proj_std=proj_std) for _ in range(num_shared))
        self._counts = self._record = self._forced = None

    def forward(self, x):
        shape = x.shape
        x = x.reshape(-1, shape[-1])
        with region(f"{self.name}.router", 3):
            with torch.autocast(device_type=x.device.type, enabled=False):
                logits = self.router(x.to(self.router.weight.dtype))
            scores = F.softmax(logits, dim=-1)
            if self._forced is not None:
                topk_idx = self._forced.long()
            else:
                topk_idx = torch.topk(scores + self.router_bias, self.top_k, dim=1).indices
            if self._record is not None:
                self._record.append(topk_idx.to(torch.uint8 if self.num_experts <= 256 else torch.int32))
            gates = torch.gather(scores, 1, topk_idx)
            gates = gates / gates.sum(dim=1, keepdim=True)
        with region(f"{self.name}.dispatch", 3):
            out, counts = DISPATCH[self.dispatch](self, x, topk_idx, gates)
        with region(f"{self.name}.shared", 3):
            for s in self.shared:
                out = out + s(x)
        if self.training:
            c = counts.detach()
            self._counts = c if self._counts is None else self._counts + c
        return out.reshape(shape)

    @torch.no_grad()
    def update_bias(self):
        if self._counts is not None:
            self.router_bias += self.gamma * torch.sign(self._counts.mean() - self._counts)
            self._counts = None
