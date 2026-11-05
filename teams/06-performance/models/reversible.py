"""Reversible midpoint stack: p_next = p_prev + 2h * f(p_curr), inverse p_prev = p_next - 2h * f(p_curr).

Blocks provide update(prev, curr) and invert(prev_out, curr_out) (models/gpt.py: Block); f must be pre-LN.

  * ReversibleStack.apply(x, blocks): forward under no_grad from a = b = x, saving only (a, b) and each layer's
    MoE routing. Backward per block, in reverse: invert, recompute f with grad, local backward, each timed
    (region block{i}, level 2; bwd.invert / bwd.recompute / block{i}.grad, level 3). Invert and recompute replay
    the routing, or near-tie tokens flip experts. Backward re-enters autocast with the forward's dtype.
  * ReversibleOnePassStack: one f evaluation in backward (model.rev_impl=one_pass); two_pass is the reference.
  * plain_forward(x, blocks): the same maths with normal autograd, the test reference.
  * reconstruction_error(x, blocks): ||x' - x|| / ||x|| after invert; grows with depth, check every new config.
"""
from __future__ import annotations

from contextlib import ExitStack

import torch

from models.moe import SparseMoE, record_routing, replay_routing
from perfkit.regions import phase, region

no_grad = torch.no_grad


def _autocast_state(device_type):
    """(enabled, dtype) of autocast on this device, so backward can re-enter the forward's precision."""
    try:
        return torch.is_autocast_enabled(device_type), torch.get_autocast_dtype(device_type)
    except TypeError:  # torch < 2.4
        if device_type == "cuda":
            return torch.is_autocast_enabled(), torch.get_autocast_gpu_dtype()
        return torch.is_autocast_cpu_enabled(), torch.get_autocast_cpu_dtype()


def _moes(blk):
    """Every SparseMoE in a block, in module order: the order routes are recorded and replayed in."""
    return [m for m in blk.modules() if isinstance(m, SparseMoE)]


def _forward_recording(blocks, x):
    """Forward under no_grad; returns (prev, final, routes) with routes[i] = [top-k per MoE of block i]."""
    a, b, routes = x, x, []
    for i, blk in enumerate(blocks):
        rec = [[] for _ in _moes(blk)]
        with region(f"block{i}", 2), ExitStack() as st:
            for m, r in zip(_moes(blk), rec):
                st.enter_context(record_routing(m, r))
            a, b = b, blk.update(a, b)
        routes.append([r[0] for r in rec])
    return a, b, routes


def _replaying(blk, route):
    """A context in which every MoE of blk replays its recorded routing."""
    st = ExitStack()
    for m, idx in zip(_moes(blk), route):
        st.enter_context(replay_routing(m, idx))
    return st


def plain_forward(x, blocks):
    """The same midpoint recurrence with ordinary autograd: the test reference."""
    a, b = x, x
    for blk in blocks:
        a, b = b, blk.update(a, b)
    return b


@no_grad()
def reconstruction_error(x, blocks) -> float:
    """||x' - x|| / ||x|| after running the stack forward and inverting every block."""
    po, co, routes = _forward_recording(blocks, x)
    for i in reversed(range(len(blocks))):
        with _replaying(blocks[i], routes[i]):
            po, co = blocks[i].invert(po, co), po
    return ((po.float() - x.float()).norm() / x.float().norm()).item()


class ReversibleStack(torch.autograd.Function):
    """Two-pass backward: per block, invert to rebuild prev, recompute f with grad, then the local backward."""

    @staticmethod
    def forward(ctx, x, blocks):
        ctx.blocks, ctx.dev = blocks, x.device.type
        ctx.amp_on, ctx.amp_dtype = _autocast_state(ctx.dev)
        with torch.no_grad():
            a, b, ctx.routes = _forward_recording(blocks, x)
        ctx.save_for_backward(a, b)
        return b

    @staticmethod
    def backward(ctx, grad_out):
        blocks = ctx.blocks
        po, co = ctx.saved_tensors

        def amp():
            return torch.autocast(device_type=ctx.dev, dtype=ctx.amp_dtype, enabled=ctx.amp_on)

        g_prev, g_curr = torch.zeros_like(grad_out), grad_out
        with torch.no_grad():
            for i in reversed(range(len(blocks))):
                blk = blocks[i]
                with region(f"block{i}", 2), _replaying(blk, ctx.routes[i]):
                    with phase("bwd.invert"), region(f"block{i}", 3), amp():
                        rec_prev = blk.invert(po, co)
                    with torch.enable_grad():
                        a = rec_prev.detach().requires_grad_(True)
                        b = po.detach().requires_grad_(True)
                        with phase("bwd.recompute"), region(f"block{i}", 3), amp():
                            d = blk.update(a, b)
                        with region(f"block{i}.grad", 3):
                            torch.autograd.backward(d, g_curr)
                    g_prev, g_curr = a.grad, g_prev + b.grad     # gradients of (prev, curr) from (curr, next)
                    po, co = rec_prev, po
        ctx.routes = None
        return g_prev + g_curr, None


class ReversibleOnePassStack(torch.autograd.Function):
    """Same forward as ReversibleStack; backward runs f once on the curr state."""

    @staticmethod
    def forward(ctx, x, blocks):
        ctx.blocks, ctx.dev = blocks, x.device.type
        ctx.amp_on, ctx.amp_dtype = _autocast_state(ctx.dev)
        with torch.no_grad():
            a, b, ctx.routes = _forward_recording(blocks, x)
        ctx.save_for_backward(a, b)
        return b

    @staticmethod
    def backward(ctx, grad_out):
        blocks = ctx.blocks
        po, co = ctx.saved_tensors

        def amp():
            return torch.autocast(device_type=ctx.dev, dtype=ctx.amp_dtype, enabled=ctx.amp_on)

        g_prev, g_curr = torch.zeros_like(grad_out), grad_out
        with torch.no_grad():
            for i in reversed(range(len(blocks))):
                blk = blocks[i]
                with region(f"block{i}", 2), _replaying(blk, ctx.routes[i]):
                    with torch.enable_grad():
                        b = po.detach().requires_grad_(True)
                        with phase("bwd.recompute"), region(f"block{i}", 3), amp():
                            f_b = blk.f(b)
                        with region(f"block{i}.grad", 3):
                            torch.autograd.backward(f_b, 2.0 * blk.h * g_curr)
                    rec_prev = (co - 2.0 * blk.h * f_b.detach())   # invert with the f just computed: no second pass
                    g_prev, g_curr = g_curr, g_prev + b.grad
                    po, co = rec_prev, po
        ctx.routes = None
        return g_prev + g_curr, None
