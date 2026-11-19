"""Causal grouped-query flash attention with a deterministic backward (model.attn_impl=triton).

    o = softmax(q k^T / sqrt(hd) + causal mask) v,     query head h reads key/value head h // (n_head / n_kv_head)

Forward: online softmax over key blocks (FlashAttention-2), fp32 accumulators, the log-sum-exp per row saved.
Backward without atomics, so two runs give the same bits (why base.yaml uses attn_impl=eager over SDPA):
  1. dq pass, one program per (query block, head): delta = rowsum(o * do), dq = sum over key blocks.
  2. dk/dv pass, one program per (key block, kv head): loops over the query heads that share the kv head and
     the query blocks at or after the key block, in a fixed order.
No repeat_interleave copies of k and v. o, dq, dk, dv are stored as [B, T, heads, hd] and returned as transposed
views, so the transpose(1, 2).contiguous() before c_proj (and in the qkv backward) is free.
fp32 inputs use IEEE fp32 dot products (no TF32), like the eager path's fp32 matmuls. Products with `scale` are cast
back to fp32: under torch.compile, Inductor passes the Python float as fp64, which would change the loop types.
"""
from __future__ import annotations

import math

import torch
from torch.autograd.function import once_differentiable

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None

DTYPES = (torch.float16, torch.bfloat16, torch.float32)
MAX_HEAD_DIM = 128


def _blocks(dtype, hd):
    """(block, head-dim width, warps, stages); query and key blocks are the same size (the causal skip uses it)."""
    bd = max(16, 1 << (hd - 1).bit_length())
    block = 32 if (dtype == torch.float32 or bd > 64) else 64
    return block, bd, 4, 2


if triton is not None:
    @triton.jit
    def _dot(a, b, IEEE: tl.constexpr):
        if IEEE:
            return tl.dot(a, b, input_precision="ieee")
        return tl.dot(a, b)

    @triton.jit(do_not_specialize=["T", "QB", "QH", "QT", "KB", "KH", "KT", "VB", "VH", "VT"])
    def _forward(Q, K, V, O, LSE, scale, T, QB, QH, QT, KB, KH, KT, VB, VH, VT,
                 H: tl.constexpr, GROUP: tl.constexpr, D: tl.constexpr, BD: tl.constexpr,
                 BLOCK: tl.constexpr, IEEE: tl.constexpr):
        start_m = tl.program_id(0)
        bh = tl.program_id(1).to(tl.int64)
        b, h = bh // H, bh % H
        kvh = h // GROUP
        rows = start_m * BLOCK + tl.arange(0, BLOCK)
        d = tl.arange(0, BD)
        dmask = d[None, :] < D
        rmask = rows < T
        q = tl.load(Q + b * QB + h * QH + rows[:, None].to(tl.int64) * QT + d[None, :],
                    rmask[:, None] & dmask, 0.)
        m_i = tl.full((BLOCK,), -float("inf"), tl.float32)
        l_i = tl.full((BLOCK,), 0., tl.float32)
        acc = tl.full((BLOCK, BD), 0., tl.float32)
        kbase = K + b * KB + kvh * KH
        vbase = V + b * VB + kvh * VH
        for start_n in range(0, tl.minimum((start_m + 1) * BLOCK, T), BLOCK):
            cols = start_n + tl.arange(0, BLOCK)
            cmask = cols < T
            k = tl.load(kbase + cols[:, None].to(tl.int64) * KT + d[None, :], cmask[:, None] & dmask, 0.)
            s = (_dot(q, tl.trans(k), IEEE) * scale).to(tl.float32)
            s = tl.where((rows[:, None] >= cols[None, :]) & cmask[None, :], s, -float("inf"))
            m_new = tl.maximum(m_i, tl.max(s, 1))       # finite: key 0 is in the first block of every row
            p = tl.exp(s - m_new[:, None])
            alpha = tl.exp(m_i - m_new)
            l_i = l_i * alpha + tl.sum(p, 1)
            v = tl.load(vbase + cols[:, None].to(tl.int64) * VT + d[None, :], cmask[:, None] & dmask, 0.)
            acc = acc * alpha[:, None] + _dot(p.to(v.dtype), v, IEEE)
            m_i = m_new
        out = O + (b * T + rows[:, None].to(tl.int64)) * (H * D) + h * D + d[None, :]
        tl.store(out, acc / l_i[:, None], rmask[:, None] & dmask)
        tl.store(LSE + bh * T + rows, m_i + tl.log(l_i), rmask)

    @triton.jit(do_not_specialize=["T", "QB", "QH", "QT", "KB", "KH", "KT", "VB", "VH", "VT",
                                   "DB", "DH", "DT"])
    def _backward_dq(Q, K, V, O, DO, LSE, DELTA, DQ, scale, T, QB, QH, QT, KB, KH, KT, VB, VH, VT,
                     DB, DH, DT, H: tl.constexpr, GROUP: tl.constexpr, D: tl.constexpr, BD: tl.constexpr,
                     BLOCK: tl.constexpr, IEEE: tl.constexpr):
        start_m = tl.program_id(0)
        bh = tl.program_id(1).to(tl.int64)
        b, h = bh // H, bh % H
        kvh = h // GROUP
        rows = start_m * BLOCK + tl.arange(0, BLOCK)
        d = tl.arange(0, BD)
        dmask = d[None, :] < D
        rmask = rows < T
        mask = rmask[:, None] & dmask
        r64 = rows[:, None].to(tl.int64)
        q = tl.load(Q + b * QB + h * QH + r64 * QT + d[None, :], mask, 0.)
        do = tl.load(DO + b * DB + h * DH + r64 * DT + d[None, :], mask, 0.)
        o = tl.load(O + (b * T + r64) * (H * D) + h * D + d[None, :], mask, 0.)
        delta = tl.sum(o.to(tl.float32) * do.to(tl.float32), 1)
        tl.store(DELTA + bh * T + rows, delta, rmask)
        lse = tl.load(LSE + bh * T + rows, rmask, 0.)
        dq = tl.full((BLOCK, BD), 0., tl.float32)
        kbase = K + b * KB + kvh * KH
        vbase = V + b * VB + kvh * VH
        for start_n in range(0, tl.minimum((start_m + 1) * BLOCK, T), BLOCK):
            cols = start_n + tl.arange(0, BLOCK)
            cmask = cols < T
            k = tl.load(kbase + cols[:, None].to(tl.int64) * KT + d[None, :], cmask[:, None] & dmask, 0.)
            v = tl.load(vbase + cols[:, None].to(tl.int64) * VT + d[None, :], cmask[:, None] & dmask, 0.)
            s = (_dot(q, tl.trans(k), IEEE) * scale).to(tl.float32)
            valid = (rows[:, None] >= cols[None, :]) & cmask[None, :] & rmask[:, None]
            p = tl.where(valid, tl.exp(s - lse[:, None]), 0.)
            dp = _dot(do, tl.trans(v), IEEE)
            ds = p * (dp - delta[:, None])
            dq += _dot(ds.to(k.dtype), k, IEEE)
        out = DQ + (b * T + r64) * (H * D) + h * D + d[None, :]
        tl.store(out, (dq * scale).to(tl.float32), mask)

    @triton.jit(do_not_specialize=["T", "QB", "QH", "QT", "KB", "KH", "KT", "VB", "VH", "VT",
                                   "DB", "DH", "DT"])
    def _backward_dkdv(Q, K, V, DO, LSE, DELTA, DK, DV, scale, T, QB, QH, QT, KB, KH, KT, VB, VH, VT,
                       DB, DH, DT, H: tl.constexpr, GROUP: tl.constexpr, KV: tl.constexpr, D: tl.constexpr,
                       BD: tl.constexpr, BLOCK: tl.constexpr, IEEE: tl.constexpr):
        start_n = tl.program_id(0)
        bkv = tl.program_id(1).to(tl.int64)
        b, kvh = bkv // KV, bkv % KV
        cols = start_n * BLOCK + tl.arange(0, BLOCK)
        d = tl.arange(0, BD)
        dmask = d[None, :] < D
        cmask = cols < T
        c64 = cols[:, None].to(tl.int64)
        k = tl.load(K + b * KB + kvh * KH + c64 * KT + d[None, :], cmask[:, None] & dmask, 0.)
        v = tl.load(V + b * VB + kvh * VH + c64 * VT + d[None, :], cmask[:, None] & dmask, 0.)
        dk = tl.full((BLOCK, BD), 0., tl.float32)
        dv = tl.full((BLOCK, BD), 0., tl.float32)
        for g in range(GROUP):
            h = kvh * GROUP + g
            bh = b * H + h
            for start_m in range(start_n * BLOCK, T, BLOCK):    # query blocks at or after the key block
                rows = start_m + tl.arange(0, BLOCK)
                rmask = rows < T
                r64 = rows[:, None].to(tl.int64)
                q = tl.load(Q + b * QB + h * QH + r64 * QT + d[None, :], rmask[:, None] & dmask, 0.)
                do = tl.load(DO + b * DB + h * DH + r64 * DT + d[None, :], rmask[:, None] & dmask, 0.)
                lse = tl.load(LSE + bh * T + rows, rmask, 0.)
                delta = tl.load(DELTA + bh * T + rows, rmask, 0.)
                st = (_dot(k, tl.trans(q), IEEE) * scale).to(tl.float32)   # [keys, queries]
                valid = (rows[None, :] >= cols[:, None]) & rmask[None, :] & cmask[:, None]
                pt = tl.where(valid, tl.exp(st - lse[None, :]), 0.)
                dv += _dot(pt.to(do.dtype), do, IEEE)
                dpt = _dot(v, tl.trans(do), IEEE)
                dst = pt * (dpt - delta[None, :])
                dk += _dot(dst.to(q.dtype), q, IEEE)
        off = (b * T + c64) * (KV * D) + kvh * D + d[None, :]
        tl.store(DK + off, (dk * scale).to(tl.float32), cmask[:, None] & dmask)
        tl.store(DV + off, dv, cmask[:, None] & dmask)


def _unit_last(t):
    return t if t.stride(-1) == 1 else t.contiguous()


def _strides(t):
    return t.stride(0), t.stride(1), t.stride(2)


class _Attention(torch.autograd.Function):
    @staticmethod
    def forward(ctx, q, k, v):
        q, k, v = _unit_last(q), _unit_last(k), _unit_last(v)
        B, H, T, D = q.shape
        group = H // k.shape[1]
        block, bd, warps, stages = _blocks(q.dtype, D)
        scale = 1.0 / math.sqrt(D)
        o = torch.empty((B, T, H, D), device=q.device, dtype=q.dtype)
        lse = torch.empty((B, H, T), device=q.device, dtype=torch.float32)
        with torch.cuda.device(q.device):
            _forward[(triton.cdiv(T, block), B * H)](q, k, v, o, lse, scale, T, *_strides(q), *_strides(k),
                                                     *_strides(v), H, group, D, bd, block,
                                                     q.dtype == torch.float32, num_warps=warps,
                                                     num_stages=stages)
        ctx.save_for_backward(q, k, v, o, lse)
        ctx.meta = (group, block, bd, warps, stages, scale)
        return o.transpose(1, 2)

    @staticmethod
    @once_differentiable
    def backward(ctx, do):
        q, k, v, o, lse = ctx.saved_tensors
        group, block, bd, warps, stages, scale = ctx.meta
        B, H, T, D = q.shape
        kv = H // group
        do = _unit_last(do)
        ieee = q.dtype == torch.float32
        dq = torch.empty((B, T, H, D), device=q.device, dtype=q.dtype)
        dk = torch.empty((B, T, kv, D), device=q.device, dtype=k.dtype)
        dv = torch.empty((B, T, kv, D), device=q.device, dtype=v.dtype)
        delta = torch.empty((B, H, T), device=q.device, dtype=torch.float32)
        strides = (*_strides(q), *_strides(k), *_strides(v), *_strides(do))
        with torch.cuda.device(q.device):
            _backward_dq[(triton.cdiv(T, block), B * H)](q, k, v, o, do, lse, delta, dq, scale, T, *strides,
                                                         H, group, D, bd, block, ieee,
                                                         num_warps=warps, num_stages=stages)
            _backward_dkdv[(triton.cdiv(T, block), B * kv)](q, k, v, do, lse, delta, dk, dv, scale, T,
                                                           *strides, H, group, kv, D, bd, block, ieee,
                                                           num_warps=warps, num_stages=stages)
        return dq.transpose(1, 2), dk.transpose(1, 2), dv.transpose(1, 2)


def supported(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor) -> bool:
    """q [B, H, T, hd], k and v [B, KV, T, hd], H a multiple of KV, one dtype and device."""
    return (triton is not None and q.device.type == "cuda" and q.ndim == k.ndim == v.ndim == 4
            and k.shape == v.shape and q.shape[0] == k.shape[0] and q.shape[2:] == k.shape[2:]
            and q.shape[1] % k.shape[1] == 0 and 0 < q.shape[-1] <= MAX_HEAD_DIM and q.shape[2] > 0
            and q.dtype in DTYPES and q.dtype == k.dtype == v.dtype
            and q.device == k.device == v.device)


def attention(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    """Causal attention [B, H, T, hd] (a transposed view of a [B, T, H, hd] tensor). Strict: check supported()."""
    if not supported(q, k, v):
        raise ValueError("triton attention needs CUDA, Triton, q [B, H, T, hd <= 128], k = v [B, KV, T, hd], "
                         "H % KV == 0 and one dtype")
    return _Attention.apply(q, k, v)
