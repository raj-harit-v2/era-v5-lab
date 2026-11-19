"""Standalone compact MoE permutation and weighted unpermutation kernels.

``order[p]`` is the original flattened route ID at packed row p. Route
``token * top_k + slot`` belongs to that token. Every route occurs exactly once;
expert sorting and expert GEMMs are deliberately outside this module.

The kernels use unique writes and fixed-order reductions, without gradient
atomics or expert-capacity padding. Checked entry points validate the permutation
(a device synchronization); trusted callers may disable that check explicitly.
"""
from __future__ import annotations

import operator

import torch
from torch.autograd.function import once_differentiable

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None

DTYPES = (torch.float16, torch.bfloat16, torch.float32)


def launch_config(operation, hidden):
    """(rows, columns, warps). Shape heuristics, not benchmark-selected settings."""
    width = 1 << (hidden - 1).bit_length()
    if operation == "pack":
        return 4, min(width, 1024), 4
    if operation in ("pack_backward", "combine"):
        return 2, min(width, 512), 4
    if operation == "combine_backward":
        return (1, width, 4) if hidden <= 1024 else (4, 512, 4)
    raise ValueError(f"unknown operation {operation!r}")


def _check_order(order, n_routes, device, validate_indices):
    if order.ndim != 1 or order.numel() != n_routes:
        raise ValueError("order must have one entry per route")
    if order.dtype not in (torch.int32, torch.int64):
        raise ValueError("order must be int32 or int64")
    if order.device != device:
        raise ValueError("data and order must be on the same device")
    if validate_indices:
        _validate_permutation(order, n_routes)


def _validate_permutation(order, n_routes):
    if not torch.equal(
            order.sort().values, torch.arange(n_routes, device=order.device, dtype=order.dtype)):
        raise ValueError("order must be a permutation of all route IDs")


def _positive_top_k(top_k):
    try:
        k = operator.index(top_k)
    except TypeError:
        raise ValueError("top_k must be a positive integer") from None
    if isinstance(top_k, bool) or k < 1:
        raise ValueError("top_k must be a positive integer")
    return k


def _check(data, order, n_routes, top_k, validate_indices):
    if data.ndim != 2 or data.shape[1] < 1:
        raise ValueError("data must have shape [rows, hidden] with positive hidden size")
    if data.dtype not in DTYPES:
        raise ValueError("data must be fp16, bf16 or fp32")
    if isinstance(order, RouteMap):
        order._check_versions()
        if order.top_k != top_k or order.n_tokens != n_routes // top_k:
            raise ValueError("RouteMap token count/top_k does not match this operation")
        _check_order(order.order, n_routes, data.device, False)
    else:
        _check_order(order, n_routes, data.device, False)
    if data.device.type != "cuda" or triton is None:
        raise ValueError("MoE Triton kernels require CUDA and Triton")
    if not isinstance(order, RouteMap) and validate_indices:
        _validate_permutation(order, n_routes)


class RouteMap:
    """Owned order snapshot/inverse bound to a token count and top_k.

    Build a new map when routing changes. Do not mutate its tensors. Mutation is
    PyTorch mutations are detected on reuse and through backward version checks.
    External pointer writes do not bump counters and must never mutate metadata.
    """
    def __init__(self, order, top_k, *, validate_indices=True):
        self._top_k = _positive_top_k(top_k)
        if order.numel() % self._top_k:
            raise ValueError("route count must be divisible by top_k")
        self._n_tokens = order.numel() // self._top_k
        _check_order(order, order.numel(), order.device, False)
        if order.device.type != "cuda" or triton is None:
            raise ValueError("MoE Triton kernels require CUDA and Triton")
        if validate_indices:
            _validate_permutation(order, order.numel())
        with torch.inference_mode(False), torch.cuda.device(order.device):
            self._order = order.clone(memory_format=torch.contiguous_format)
            self._inverse = _inverse_order(self._order)
        self._versions = (self._order._version, self._inverse._version)

    @property
    def order(self):
        return self._order

    @property
    def inverse(self):
        return self._inverse

    @property
    def top_k(self):
        return self._top_k

    @property
    def n_tokens(self):
        return self._n_tokens

    def _check_versions(self):
        if (self._order._version, self._inverse._version) != self._versions:
            raise RuntimeError("RouteMap metadata was modified; construct a new RouteMap")


if triton is not None:
    @triton.jit
    def _inverse(Order, Inverse, R, BLOCK: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BLOCK + tl.arange(0, BLOCK)
        route = tl.load(Order + row, row < R, 0).to(tl.int64)
        tl.store(Inverse + route, row.to(Inverse.dtype.element_ty), row < R)

    @triton.jit
    def _pack(X, Order, Y, Inverse, R, SX0, SX1, D: tl.constexpr, K: tl.constexpr, NEED_INVERSE: tl.constexpr,
              BR: tl.constexpr, BC: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BR + tl.arange(0, BR)
        col = tl.program_id(1).to(tl.int64) * BC + tl.arange(0, BC)
        route = tl.load(Order + row, row < R, 0).to(tl.int64)
        values = tl.load(X + (route // K)[:, None] * SX0 + col[None, :] * SX1,
                         (row[:, None] < R) & (col[None, :] < D), 0)
        tl.store(Y + row[:, None] * D + col[None, :], values,
                 (row[:, None] < R) & (col[None, :] < D))
        if NEED_INVERSE:
            if tl.program_id(1) == 0:
                tl.store(Inverse + route, row.to(Inverse.dtype.element_ty), row < R)

    @triton.jit
    def _pack_backward(DY, Inverse, DX, N, S0, S1, D: tl.constexpr, K: tl.constexpr,
                       BR: tl.constexpr, BC: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BR + tl.arange(0, BR)
        col = tl.program_id(1).to(tl.int64) * BC + tl.arange(0, BC)
        acc = tl.full((BR, BC), 0., tl.float32)
        for k in range(K):
            packed = tl.load(Inverse + row * K + k, row < N, 0).to(tl.int64)
            acc += tl.load(DY + packed[:, None] * S0 + col[None, :] * S1,
                           (row[:, None] < N) & (col[None, :] < D), 0).to(tl.float32)
        tl.store(DX + row[:, None] * D + col[None, :], acc,
                 (row[:, None] < N) & (col[None, :] < D))

    @triton.jit
    def _combine(Y, Gates, Inverse, Out, N, SY0, SY1, SG0, SG1, D: tl.constexpr, K: tl.constexpr,
                 BR: tl.constexpr, BC: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BR + tl.arange(0, BR)
        col = tl.program_id(1).to(tl.int64) * BC + tl.arange(0, BC)
        acc = tl.full((BR, BC), 0., tl.float32)
        for k in range(K):
            route = row * K + k
            packed = tl.load(Inverse + route, row < N, 0).to(tl.int64)
            gate = tl.load(Gates + row * SG0 + k * SG1, row < N, 0).to(tl.float32)
            y = tl.load(Y + packed[:, None] * SY0 + col[None, :] * SY1,
                        (row[:, None] < N) & (col[None, :] < D), 0).to(tl.float32)
            acc += y * gate[:, None]
        tl.store(Out + row[:, None] * D + col[None, :], acc,
                 (row[:, None] < N) & (col[None, :] < D))

    @triton.jit
    def _combine_backward(Y, Gates, Order, DO, DY, Partial, R, SY0, SY1, SG0, SG1, SO0, SO1,
                          D: tl.constexpr, K: tl.constexpr, TILES: tl.constexpr,
                          NEED_Y: tl.constexpr, NEED_G: tl.constexpr,
                          BR: tl.constexpr, BC: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BR + tl.arange(0, BR)
        tile = tl.program_id(1).to(tl.int64)
        col = tile * BC + tl.arange(0, BC)
        route = tl.load(Order + row, row < R, 0).to(tl.int64)
        mask = (row[:, None] < R) & (col[None, :] < D)
        dy = tl.load(DO + (route // K)[:, None] * SO0 + col[None, :] * SO1, mask, 0).to(tl.float32)
        if NEED_Y:
            gate = tl.load(Gates + (route // K) * SG0 + (route % K) * SG1, row < R, 0).to(tl.float32)
            tl.store(DY + row[:, None] * D + col[None, :], dy * gate[:, None], mask)
        if NEED_G:
            y = tl.load(Y + row[:, None] * SY0 + col[None, :] * SY1, mask, 0).to(tl.float32)
            dot = tl.sum(dy * y, 1)
            tl.store(Partial + route * TILES + tile, dot, row < R)

    @triton.jit
    def _gate_backward(Partial, DG, R, TILES: tl.constexpr,
                       BR: tl.constexpr, BT: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BR + tl.arange(0, BR)
        tile = tl.arange(0, BT)
        values = tl.load(Partial + row[:, None] * TILES + tile[None, :],
                         (row[:, None] < R) & (tile[None, :] < TILES), 0)
        tl.store(DG + row, tl.sum(values, 1), row < R)


def _inverse_order(order):
    inverse = torch.empty_like(order)
    if order.numel():
        _inverse[(triton.cdiv(order.numel(), 256),)](
            order, inverse, order.numel(), 256, enable_fp_fusion=False)
    return inverse


class _PackTokens(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, order, top_k, cached_inverse):
        n, d = x.shape
        r = order.numel()
        with torch.cuda.device(x.device):
            out = x.new_empty((r, d))
            build_inverse = ctx.needs_input_grad[0] and cached_inverse is None
            inverse = cached_inverse if cached_inverse is not None else (
                torch.empty_like(order) if build_inverse else order)
            rows, cols, warps = launch_config("pack", d)
            if r:
                _pack[(triton.cdiv(r, rows), triton.cdiv(d, cols))](
                    x, order, out, inverse, r, *x.stride(), d, top_k, build_inverse,
                    rows, cols, num_warps=warps, enable_fp_fusion=False)
        ctx.save_for_backward(order, inverse)
        ctx.shape = (n, d, top_k)
        return out

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_output):
        order, inverse = ctx.saved_tensors
        n, d, k = ctx.shape
        with torch.cuda.device(grad_output.device):
            dx = grad_output.new_empty((n, d))
            rows, cols, warps = launch_config("pack_backward", d)
            if n:
                _pack_backward[(triton.cdiv(n, rows), triton.cdiv(d, cols))](
                    grad_output, inverse, dx, n, *grad_output.stride(), d, k,
                    rows, cols, num_warps=warps, enable_fp_fusion=False)
        return dx, None, None, None


class _CombineTokens(torch.autograd.Function):
    @staticmethod
    def forward(ctx, y, gates, order, cached_inverse):
        n, k = gates.shape
        d = y.shape[1]
        with torch.cuda.device(y.device):
            inverse = cached_inverse if cached_inverse is not None else _inverse_order(order)
            out = y.new_empty((n, d))
            rows, cols, warps = launch_config("combine", d)
            if n:
                _combine[(triton.cdiv(n, rows), triton.cdiv(d, cols))](
                    y, gates, inverse, out, n, *y.stride(), *gates.stride(), d, k, rows, cols,
                    num_warps=warps, enable_fp_fusion=False)
        ctx.save_for_backward(y, gates, order, inverse)
        return out

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_output):
        y, gates, order, inverse = ctx.saved_tensors
        n, k = gates.shape
        r, d = y.shape
        need_y, need_g = ctx.needs_input_grad[:2]
        with torch.cuda.device(y.device):
            dy = y.new_empty(y.shape) if need_y else None
            dg = gates.new_empty(gates.shape) if need_g else None
            rows, cols, warps = launch_config("combine_backward", d)
            tiles = triton.cdiv(d, cols)
            partial = (torch.empty((r, tiles), device=y.device, dtype=torch.float32)
                       if need_g and tiles > 1 else dg if need_g else y)
            if r:
                _combine_backward[(triton.cdiv(r, rows), tiles)](
                    y, gates, order, grad_output, dy if need_y else y, partial,
                    r, *y.stride(), *gates.stride(), *grad_output.stride(),
                    d, k, tiles, need_y, need_g, rows, cols,
                    num_warps=warps, enable_fp_fusion=False)
                if need_g and tiles > 1:
                    _gate_backward[(triton.cdiv(r, 4),)](
                        partial, dg, r, tiles, 4, triton.next_power_of_2(tiles), num_warps=4,
                        enable_fp_fusion=False)
        return dy, dg, None, None


def pack_tokens(x, order, top_k, *, validate_indices=True):
    """Pack [N,D] into [N*top_k,D]; order[p] identifies the route at row p.

    No padding, capacity limit, token dropping or CPU fallback. Strided data is
    loaded directly. Pass a RouteMap to reuse validated inverse metadata.
    With validate_indices=False the caller guarantees an in-bounds permutation.
    """
    k = _positive_top_k(top_k)
    _check(x, order, x.shape[0] * k if x.ndim else 0, k, validate_indices)
    if isinstance(order, RouteMap):
        return _PackTokens.apply(x, order.order, k, order.inverse)
    return _PackTokens.apply(x, order.contiguous(), k, None)


def combine_tokens(expert_output, gates, order, *, validate_indices=True):
    """Weighted unpermutation: out[n] = sum_k gate[n,k] * expert_output[packed(n,k)].

    Products and reductions use fp32; output has expert_output.dtype, while each
    gradient has its input's dtype. Small widths write gate gradients directly;
    wider rows use deterministic tiled reduction. A RouteMap avoids repeated
    validation and inverse construction. No gradient atomics are used.
    """
    if gates.ndim != 2 or gates.shape[1] < 1 or gates.dtype not in DTYPES:
        raise ValueError("gates must have shape [tokens, top_k] and be fp16, bf16 or fp32")
    if gates.device != expert_output.device:
        raise ValueError("gates and expert_output must be on the same device")
    if expert_output.ndim != 2 or expert_output.shape[0] != gates.numel():
        raise ValueError("expert_output must have one row per gate")
    _check(expert_output, order, gates.numel(), gates.shape[1], validate_indices)
    if isinstance(order, RouteMap):
        return _CombineTokens.apply(expert_output, gates, order.order, order.inverse)
    return _CombineTokens.apply(expert_output, gates, order.contiguous(), None)
