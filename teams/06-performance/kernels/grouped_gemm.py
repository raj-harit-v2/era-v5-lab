"""Standalone variable-row expert linear projection and first-order backward.

X is compact [R,K], W is [E,N,K], offsets is [E+1], and optional bias is [E,N].
Rows offsets[e]:offsets[e+1] are multiplied by W[e].T. No token capacity
padding, per-expert Python launches, gradient atomics, or training integration.
"""
from __future__ import annotations

from functools import lru_cache
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
PRECISIONS = ("ieee", "tf32x3", "tf32")
MAX_SPLIT_SCRATCH = 64 * 1024 * 1024


def launch_config(operation, rows, experts, inner, width, dtype):
    """Shape heuristics, not benchmark-selected settings: (BM, BN, BK, warps, stages)."""
    if operation == "project":
        if dtype != torch.float32 and rows >= experts * 64 and min(inner, width) >= 64:
            return 64, 128, 32, 4, 3
        return 32, 64, 32, 4, 2
    if operation == "weight_backward":
        # Here BM/BN tile the output's N/K axes, and BK reduces token rows.
        if min(inner, width) >= 64:
            return 64, 64, 32, 4, 2
        return 32, 32, 32, 4, 2
    raise ValueError(f"unknown operation {operation!r}")


def _split_count(value):
    try:
        splits = operator.index(value)
    except TypeError:
        raise ValueError("split_r must be an integer from 1 to 32") from None
    if isinstance(value, bool) or not 1 <= splits <= 32:
        raise ValueError("split_r must be an integer from 1 to 32")
    return splits


def _offset_shape(offsets, experts, device):
    if offsets.ndim != 1 or offsets.numel() != experts + 1:
        raise ValueError("offsets must have shape [num_experts + 1]")
    if offsets.dtype not in (torch.int32, torch.int64):
        raise ValueError("offsets must be int32 or int64")
    if offsets.device != device:
        raise ValueError("offsets and activations must be on the same device")


def _validate_offsets(offsets, rows):
    valid = ((offsets[0] == 0) & (offsets[-1] == rows)
             & (offsets[1:] >= offsets[:-1]).all())
    if not bool(valid):
        raise ValueError("offsets must start at zero, be nondecreasing, and end at the row count")


class ExpertSegments:
    """Validate and snapshot expert boundaries once, outside repeated operations.

    PyTorch mutation counters protect reuse/backward. External pointer writes
    cannot be detected; never mutate the exposed offsets tensor.
    """
    def __init__(self, offsets, num_rows, *, validate_offsets=True):
        try:
            rows = operator.index(num_rows)
        except TypeError:
            raise ValueError("num_rows must be a nonnegative integer") from None
        if isinstance(num_rows, bool) or rows < 0:
            raise ValueError("num_rows must be a nonnegative integer")
        experts = offsets.numel() - 1
        if experts < 1:
            raise ValueError("at least one expert is required")
        _offset_shape(offsets, experts, offsets.device)
        if offsets.device.type != "cuda" or triton is None:
            raise ValueError("grouped GEMM requires CUDA and Triton")
        with torch.inference_mode(False), torch.cuda.device(offsets.device):
            self._offsets = offsets.clone(memory_format=torch.contiguous_format)
            if validate_offsets:
                _validate_offsets(self._offsets, rows)
        self._version = self._offsets._version
        self._rows, self._experts = rows, experts

    @property
    def offsets(self):
        return self._offsets

    @property
    def num_rows(self):
        return self._rows

    @property
    def num_experts(self):
        return self._experts

    def _check_versions(self):
        if self._offsets._version != self._version:
            raise RuntimeError("ExpertSegments metadata was modified; construct new segments")


@lru_cache(maxsize=None)
def _sm_count(index):
    return torch.cuda.get_device_properties(index).multi_processor_count


if triton is not None:
    @triton.jit
    def _forward(X, W, Bias, Offsets, Y, E, SX0, SX1, SW0, SW1, SW2, SB0, SB1,
                 K: tl.constexpr, N: tl.constexpr, HAS_BIAS: tl.constexpr,
                 PRECISION: tl.constexpr, BM: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr):
        tile = tl.program_id(0).to(tl.int64)
        base = tl.full((), 0, tl.int64)
        for e in range(E):
            expert = e.to(tl.int64)
            start = tl.load(Offsets + expert).to(tl.int64)
            end = tl.load(Offsets + expert + 1).to(tl.int64)
            columns = tl.cdiv(N, BN)
            count = tl.cdiv(end - start, BM) * columns
            while (tile >= base) & (tile < base + count):
                local = tile - base
                row = start + (local // columns) * BM + tl.arange(0, BM).to(tl.int64)
                col = (local % columns) * BN + tl.arange(0, BN).to(tl.int64)
                acc = tl.full((BM, BN), 0., tl.float32)
                for block in range(tl.cdiv(K, BK)):
                    red = block.to(tl.int64) * BK + tl.arange(0, BK).to(tl.int64)
                    a = tl.load(X + row[:, None] * SX0 + red[None, :] * SX1,
                                (row[:, None] < end) & (red[None, :] < K), 0)
                    b = tl.load(W + expert * SW0 + col[None, :] * SW1 + red[:, None] * SW2,
                                (red[:, None] < K) & (col[None, :] < N), 0)
                    acc = tl.dot(a, b, acc, input_precision=PRECISION)
                if HAS_BIAS:
                    bias = tl.load(Bias + expert * SB0 + col * SB1, col < N, 0).to(tl.float32)
                    acc += bias[None, :]
                tl.store(Y + row[:, None] * N + col[None, :], acc,
                         (row[:, None] < end) & (col[None, :] < N))
                tile += tl.num_programs(0)
            base += count

    @triton.jit
    def _weight_backward(X, DY, Offsets, DW, DB, SX0, SX1, SY0, SY1,
                         K: tl.constexpr, N: tl.constexpr, NEED_BIAS: tl.constexpr, SPLITS: tl.constexpr,
                         PRECISION: tl.constexpr, BN: tl.constexpr, BK: tl.constexpr, BR: tl.constexpr):
        expert = tl.program_id(1).to(tl.int64)
        tile = tl.program_id(0).to(tl.int64)
        col_k = tile % tl.cdiv(K, BK) * BK + tl.arange(0, BK).to(tl.int64)
        col_n = tile // tl.cdiv(K, BK) * BN + tl.arange(0, BN).to(tl.int64)
        start = tl.load(Offsets + expert).to(tl.int64)
        end = tl.load(Offsets + expert + 1).to(tl.int64)
        split = tl.program_id(2).to(tl.int64)
        # Partition complete reduction blocks; split=1 retains the original order.
        blocks_per_split = tl.cdiv(tl.cdiv(end - start, BR), SPLITS)
        split_start = start + split * blocks_per_split * BR
        split_end = tl.minimum(end, split_start + blocks_per_split * BR)
        acc = tl.full((BN, BK), 0., tl.float32)
        bias_acc = tl.full((BN,), 0., tl.float32)
        for block in range(tl.cdiv(tl.maximum(split_end - split_start, 0), BR)):
            row = split_start + block.to(tl.int64) * BR + tl.arange(0, BR).to(tl.int64)
            dy = tl.load(DY + row[None, :] * SY0 + col_n[:, None] * SY1,
                         (row[None, :] < split_end) & (col_n[:, None] < N), 0)
            x = tl.load(X + row[:, None] * SX0 + col_k[None, :] * SX1,
                        (row[:, None] < split_end) & (col_k[None, :] < K), 0)
            acc = tl.dot(dy, x, acc, input_precision=PRECISION)
            if NEED_BIAS:
                if tile % tl.cdiv(K, BK) == 0:
                    bias_acc += tl.sum(dy.to(tl.float32), 1)
        tl.store(DW + ((expert * SPLITS + split) * N + col_n[:, None]) * K + col_k[None, :], acc,
                 (col_n[:, None] < N) & (col_k[None, :] < K))
        if NEED_BIAS:
            if tile % tl.cdiv(K, BK) == 0:
                tl.store(DB + (expert * SPLITS + split) * N + col_n, bias_acc, col_n < N)

    @triton.jit
    def _reduce_splits(Partial, Out, SIZE: tl.constexpr, SPLITS: tl.constexpr, BLOCK: tl.constexpr):
        expert = tl.program_id(1).to(tl.int64)
        col = tl.program_id(0).to(tl.int64) * BLOCK + tl.arange(0, BLOCK).to(tl.int64)
        acc = tl.full((BLOCK,), 0., tl.float32)
        for split in range(SPLITS):
            acc += tl.load(Partial + (expert * SPLITS + split) * SIZE + col, col < SIZE, 0)
        tl.store(Out + expert * SIZE + col, acc, col < SIZE)

    @triton.jit
    def _bias_backward(DY, Offsets, DB, SY0, SY1, N: tl.constexpr,
                       BN: tl.constexpr, BR: tl.constexpr):
        expert = tl.program_id(1).to(tl.int64)
        col = tl.program_id(0).to(tl.int64) * BN + tl.arange(0, BN).to(tl.int64)
        start = tl.load(Offsets + expert).to(tl.int64)
        end = tl.load(Offsets + expert + 1).to(tl.int64)
        acc = tl.full((BN,), 0., tl.float32)
        for block in range(tl.cdiv(end - start, BR)):
            row = start + block.to(tl.int64) * BR + tl.arange(0, BR).to(tl.int64)
            dy = tl.load(DY + row[:, None] * SY0 + col[None, :] * SY1,
                         (row[:, None] < end) & (col[None, :] < N), 0).to(tl.float32)
            acc += tl.sum(dy, 0)
        tl.store(DB + expert * N + col, acc, col < N)


def _project(x, weight, offsets, out, bias, precision, transpose=False):
    rows, inner = x.shape
    width, experts = out.shape[1], weight.shape[0]
    bm, bn, bk, warps, stages = launch_config("project", rows, experts, inner, width, x.dtype)
    # Sum ceil(M_e/BM) <= ceil(R/BM)+E-1; no expert counts are copied to the host.
    bound = (triton.cdiv(rows, bm) + experts - 1) * triton.cdiv(width, bn)
    # Two resident worker waves is an initial scheduling heuristic, not tuning evidence.
    workers = min(2 * _sm_count(x.device.index), bound)
    sw0, sw1, sw2 = weight.stride()
    if transpose:
        sw1, sw2 = sw2, sw1
    sb0, sb1 = bias.stride() if bias is not None else (0, 0)
    _forward[(workers,)](x, weight, bias if bias is not None else x, offsets, out,
                         experts, *x.stride(), sw0, sw1, sw2, sb0, sb1,
                         inner, width, bias is not None, precision, bm, bn, bk,
                         num_warps=warps, num_stages=stages, enable_fp_fusion=False)


class _GroupedLinear(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, weight, offsets, bias, precision, split_r):
        with torch.cuda.device(x.device):
            out = x.new_empty((x.shape[0], weight.shape[1]))
            if x.shape[0]:
                _project(x, weight, offsets, out, bias, precision)
        ctx.save_for_backward(x, weight, offsets, bias)
        ctx.precision = precision
        ctx.split_r = split_r
        return out

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_output):
        x, weight, offsets, bias = ctx.saved_tensors
        need_x, need_w, _, need_b = ctx.needs_input_grad[:4]
        experts, n, k = weight.shape
        with torch.cuda.device(x.device):
            dx = x.new_empty(x.shape) if need_x else None
            dw = weight.new_empty(weight.shape) if need_w else None
            db = bias.new_empty(bias.shape) if need_b else None
            if x.shape[0] == 0:
                if need_w:
                    dw.zero_()
                if need_b:
                    db.zero_()
            else:
                if need_x:
                    _project(grad_output, weight, offsets, dx, None, ctx.precision, transpose=True)
                if need_w:
                    splits = ctx.split_r
                    bn, bk, br, warps, stages = launch_config(
                        "weight_backward", x.shape[0], experts, k, n, x.dtype)
                    pw = (torch.empty((experts, splits, n, k), device=x.device, dtype=torch.float32)
                          if splits > 1 else dw)
                    pb = (torch.empty((experts, splits, n), device=x.device, dtype=torch.float32)
                          if need_b and splits > 1 else db if need_b else x)
                    _weight_backward[(triton.cdiv(n, bn) * triton.cdiv(k, bk), experts, splits)](
                        x, grad_output, offsets, pw, pb,
                        *x.stride(), *grad_output.stride(), k, n, need_b, splits, ctx.precision, bn, bk, br,
                        num_warps=warps, num_stages=stages, enable_fp_fusion=False)
                    if splits > 1:
                        _reduce_splits[(triton.cdiv(n * k, 256), experts)](
                            pw, dw, n * k, splits, 256, enable_fp_fusion=False)
                        if need_b:
                            _reduce_splits[(triton.cdiv(n, 256), experts)](
                                pb, db, n, splits, 256, enable_fp_fusion=False)
                elif need_b:
                    _bias_backward[(triton.cdiv(n, 64), experts)](
                        grad_output, offsets, db, *grad_output.stride(), n, 64, 32,
                        num_warps=4, enable_fp_fusion=False)
        return dx, dw, None, db, None, None


def grouped_linear(x, weight, offsets, bias=None, *, validate_offsets=True, precision="ieee", split_r=1):
    """Compact expert linear: X[e_rows] @ W[e].T + optional bias[e].

    Supports strided fp16/bf16/fp32 tensors. X/W must share dtype; bias may also
    be fp32. Accumulators are fp32. Dtypes are explicit, unaffected by autocast.
    Use ExpertSegments for one-time checked metadata. Unchecked raw offsets
    must obey the complete boundary contract or GPU memory accesses are unsafe.
    First-order gradients only. split_r>1 partitions weight-gradient reduction
    with fp32 scratch and a fixed-order second pass (at most 64 MiB scratch).
    """
    if x.ndim != 2 or weight.ndim != 3:
        raise ValueError("x must be [rows, in_features] and weight [experts, out_features, in_features]")
    if min(weight.shape) < 1 or x.shape[1] != weight.shape[2]:
        raise ValueError("positive expert/feature dimensions and matching input widths are required")
    if x.dtype not in DTYPES or weight.dtype != x.dtype:
        raise ValueError("x and weight must share an fp16, bf16 or fp32 dtype")
    if weight.device != x.device:
        raise ValueError("x and weight must be on the same device")
    if precision not in PRECISIONS:
        raise ValueError(f"precision must be one of {PRECISIONS}")
    splits = _split_count(split_r)
    if bias is not None:
        if bias.shape != weight.shape[:2] or bias.device != x.device:
            raise ValueError("bias must be [experts, out_features] on the same device")
        if bias.dtype not in (x.dtype, torch.float32):
            raise ValueError("bias must have the activation dtype or fp32")
    scratch = 4 * splits * (weight.numel() + (bias.numel() if bias is not None and bias.requires_grad else 0))
    if splits > 1 and weight.requires_grad and torch.is_grad_enabled() and x.shape[0] and scratch > MAX_SPLIT_SCRATCH:
        raise ValueError("split_r requires more than 64 MiB scratch; reduce split_r or use 1")
    if isinstance(offsets, ExpertSegments):
        offsets._check_versions()
        if offsets.num_rows != x.shape[0] or offsets.num_experts != weight.shape[0]:
            raise ValueError("ExpertSegments row/expert count does not match the operation")
        off = offsets.offsets
    else:
        off = offsets
    _offset_shape(off, weight.shape[0], x.device)
    if x.device.type != "cuda" or triton is None:
        raise ValueError("grouped GEMM requires CUDA and Triton")
    if not isinstance(offsets, ExpertSegments) and validate_offsets:
        _validate_offsets(off, x.shape[0])
    return _GroupedLinear.apply(x, weight, off.contiguous(), bias, precision, splits)
