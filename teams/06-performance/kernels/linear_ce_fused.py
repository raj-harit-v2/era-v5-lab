"""Fully fused linear-head cross entropy using in-repo Triton kernels.

Forward computes tiled logits and softmax statistics. The default backward
reconstructs each token chunk once and reuses a bounded fp32 dLogits buffer for
both gradient products. The original recompute-per-hidden-tile path remains an
explicit comparison option. Neither path uses gradient atomics.
"""
from __future__ import annotations

import torch

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None

# Keep the live logits tile small enough for the backward kernels' shared
# memory budget on Ampere as well as H100. Tune these only after profiling.
BM, BV, BK = 16, 128, 32
BACKWARD_IMPLS = ("chunked", "recompute")

if triton is not None:
    @triton.jit
    def _forward(X, W, B, Y, PM, PS, PT,
                 N: tl.constexpr, H: tl.constexpr, V: tl.constexpr,
                 X0: tl.constexpr, X1: tl.constexpr, W0: tl.constexpr, W1: tl.constexpr,
                 NT: tl.constexpr, HAS_BIAS: tl.constexpr,
                 BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        mt, vt = tl.program_id(0), tl.program_id(1)
        rows = mt * BM + tl.arange(0, BM)
        cols = vt * BV + tl.arange(0, BV)
        rk = tl.arange(0, BK)
        acc = tl.full((BM, BV), 0., tl.float32)
        for kt in range(tl.cdiv(H, BK)):
            ks = kt * BK + rk
            a = tl.load(X + rows[:, None] * X0 + ks[None, :] * X1,
                        (rows[:, None] < N) & (ks[None, :] < H), 0)
            b = tl.load(W + cols[:, None] * W0 + (rk[None, :] + kt * BK) * W1,
                        (cols[:, None] < V) & (rk[None, :] + kt * BK < H), 0)
            acc += tl.dot(a, tl.trans(b), input_precision="ieee")
        if HAS_BIAS:
            acc += tl.load(B + cols, cols < V, 0)[None, :].to(tl.float32)
        z = tl.where((rows[:, None] < N) & (cols[None, :] < V), acc, -float("inf"))
        m = tl.max(z, 1)
        s = tl.sum(tl.exp(z - m[:, None]), 1)
        y = tl.load(Y + rows, rows < N, -1)
        hit = (y[:, None] >= vt * BV) & (y[:, None] < (vt + 1) * BV)
        selected = tl.sum(tl.where(hit & (cols[None, :] == y[:, None]), z, 0.), 1)
        off = rows * NT + vt
        tl.store(PM + off, m, rows < N)
        tl.store(PS + off, s, rows < N)
        tl.store(PT + off, selected, rows < N)

    @triton.jit
    def _reduce(Y, PM, PS, PT, LOSS, LZ,
                N: tl.constexpr, NT: tl.constexpr, IGNORE: tl.constexpr, BT: tl.constexpr):
        row = tl.program_id(0)
        t = tl.arange(0, BT)
        off = row * NT + t
        m_i = tl.load(PM + off, t < NT, -float("inf"))
        s_i = tl.load(PS + off, t < NT, 0.)
        y_i = tl.load(PT + off, t < NT, 0.)
        m = tl.max(m_i, 0)
        lz = tl.log(tl.sum(s_i * tl.exp(m_i - m), 0)) + m
        target = tl.load(Y + row)
        tl.store(LZ + row, lz)
        tl.store(LOSS + row, tl.where(target == IGNORE, 0., lz - tl.sum(y_i, 0)))

    @triton.jit
    def _grad_x(X, W, B, Y, LZ, COUNT, GO, DX,
                N: tl.constexpr, H: tl.constexpr, V: tl.constexpr,
                X0: tl.constexpr, X1: tl.constexpr, W0: tl.constexpr, W1: tl.constexpr,
                DX0: tl.constexpr, DX1: tl.constexpr, IGNORE: tl.constexpr,
                HAS_BIAS: tl.constexpr, BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        mt, ht = tl.program_id(0), tl.program_id(1)
        rows = mt * BM + tl.arange(0, BM)
        out_k = ht * BK + tl.arange(0, BK)
        rk, vc = tl.arange(0, BK), tl.arange(0, BV)
        y = tl.load(Y + rows, rows < N, IGNORE)
        lz = tl.load(LZ + rows, rows < N, 0.)
        scale = tl.load(GO).to(tl.float32) / tl.load(COUNT).to(tl.float32)
        result = tl.full((BM, BK), 0., tl.float32)
        for vt in range(tl.cdiv(V, BV)):
            cols = vt * BV + vc
            logits = tl.full((BM, BV), 0., tl.float32)
            for kt in range(tl.cdiv(H, BK)):
                ks = kt * BK + rk
                a = tl.load(X + rows[:, None] * X0 + ks[None, :] * X1,
                            (rows[:, None] < N) & (ks[None, :] < H), 0)
                b = tl.load(W + cols[:, None] * W0 + (rk[None, :] + kt * BK) * W1,
                            (cols[:, None] < V) & (kt * BK + rk[None, :] < H), 0)
                logits += tl.dot(a, tl.trans(b), input_precision="ieee")
            if HAS_BIAS:
                logits += tl.load(B + cols, cols < V, 0)[None, :].to(tl.float32)
            # Padded vocabulary slots have no logit. Mask before exp so a large
            # negative log-normalizer cannot turn a padded zero into +inf.
            logits = tl.where(cols[None, :] < V, logits, -float("inf"))
            p = tl.exp(logits - lz[:, None])
            p = tl.where(cols[None, :] == y[:, None], p - 1., p)
            p = tl.where((rows[:, None] < N) & (y[:, None] != IGNORE) &
                         (cols[None, :] < V), p * scale, 0.)
            w = tl.load(W + cols[:, None] * W0 + out_k[None, :] * W1,
                        (cols[:, None] < V) & (out_k[None, :] < H), 0)
            result += tl.dot(p.to(w.dtype), w, input_precision="ieee")
        tl.store(DX + rows[:, None] * DX0 + out_k[None, :] * DX1,
                 result, (rows[:, None] < N) & (out_k[None, :] < H))

    @triton.jit
    def _grad_w(X, W, B, Y, LZ, COUNT, GO, DW, DB,
                N: tl.constexpr, H: tl.constexpr, V: tl.constexpr,
                X0: tl.constexpr, X1: tl.constexpr, W0: tl.constexpr, W1: tl.constexpr,
                DW0: tl.constexpr, DW1: tl.constexpr, IGNORE: tl.constexpr,
                HAS_BIAS: tl.constexpr, BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        vt, ht = tl.program_id(0), tl.program_id(1)
        cols = vt * BV + tl.arange(0, BV)
        out_k = ht * BK + tl.arange(0, BK)
        rows_i, rk = tl.arange(0, BM), tl.arange(0, BK)
        dw = tl.full((BV, BK), 0., tl.float32)
        db = tl.full((BV,), 0., tl.float32)
        scale = tl.load(GO).to(tl.float32) / tl.load(COUNT).to(tl.float32)
        for mt in range(tl.cdiv(N, BM)):
            rows = mt * BM + rows_i
            # Tail lanes safely reuse the final valid row; their gradients are
            # zeroed below. This also avoids a Triton 3.0 masked-load layout
            # conversion failure when the final token tile has one valid row.
            safe_rows = tl.minimum(rows, N - 1)
            y = tl.load(Y + safe_rows)
            lz = tl.load(LZ + safe_rows)
            logits = tl.full((BM, BV), 0., tl.float32)
            for kt in range(tl.cdiv(H, BK)):
                ks = kt * BK + rk
                a = tl.load(X + rows[:, None] * X0 + ks[None, :] * X1,
                            (rows[:, None] < N) & (ks[None, :] < H), 0)
                w = tl.load(W + cols[:, None] * W0 + ks[None, :] * W1,
                            (cols[:, None] < V) & (ks[None, :] < H), 0)
                logits += tl.dot(a, tl.trans(w), input_precision="ieee")
            if HAS_BIAS:
                logits += tl.load(B + cols, cols < V, 0)[None, :].to(tl.float32)
            logits = tl.where(cols[None, :] < V, logits, -float("inf"))
            p = tl.exp(logits - lz[:, None])
            p = tl.where(cols[None, :] == y[:, None], p - 1., p)
            p = tl.where((rows[:, None] < N) & (y[:, None] != IGNORE) &
                         (cols[None, :] < V), p * scale, 0.)
            x = tl.load(X + rows[:, None] * X0 + out_k[None, :] * X1,
                        (rows[:, None] < N) & (out_k[None, :] < H), 0)
            dw += tl.dot(tl.trans(p.to(x.dtype)), x, input_precision="ieee")
            if HAS_BIAS and ht == 0:
                db += tl.sum(p, 0)
        tl.store(DW + cols[:, None] * DW0 + out_k[None, :] * DW1,
                 dw, (cols[:, None] < V) & (out_k[None, :] < H))
        if HAS_BIAS and ht == 0:
            tl.store(DB + cols, db, cols < V)

    @triton.jit
    def _chunk_dlogits(X, W, B, Y, LZ, COUNT, GO, DP,
                       C: tl.constexpr, H: tl.constexpr, V: tl.constexpr,
                       IGNORE: tl.constexpr, HAS_BIAS: tl.constexpr,
                       BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        # No hidden-output-tile axis: each logit tile is reconstructed once.
        row = tl.program_id(0).to(tl.int64) * BM + tl.arange(0, BM)
        col = tl.program_id(1).to(tl.int64) * BV + tl.arange(0, BV)
        rk = tl.arange(0, BK)
        logits = tl.full((BM, BV), 0., tl.float32)
        for kt in range(tl.cdiv(H, BK)):
            k = kt * BK + rk
            a = tl.load(X + row[:, None] * H + k[None, :],
                        (row[:, None] < C) & (k[None, :] < H), 0.)
            b = tl.load(W + col[:, None] * H + k[None, :],
                        (col[:, None] < V) & (k[None, :] < H), 0.)
            logits += tl.dot(a, tl.trans(b), input_precision="ieee")
        if HAS_BIAS:
            logits += tl.load(B + col, col < V, 0.).to(tl.float32)[None, :]
        logits = tl.where(col[None, :] < V, logits, -float("inf"))
        lz = tl.load(LZ + row, row < C, 0.)
        y = tl.load(Y + row, row < C, IGNORE)
        p = tl.exp(logits - lz[:, None])
        p = tl.where(col[None, :] == y[:, None], p - 1., p)
        scale = tl.load(GO).to(tl.float32) / tl.load(COUNT).to(tl.float32)
        valid = (row[:, None] < C) & (col[None, :] < V) & (y[:, None] != IGNORE)
        tl.store(DP + row[:, None] * V + col[None, :],
                 tl.where(valid, p * scale, 0.), (row[:, None] < C) & (col[None, :] < V))

    @triton.jit
    def _chunk_dx(DP, W, DX, C: tl.constexpr, H: tl.constexpr, V: tl.constexpr,
                  BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BM + tl.arange(0, BM)
        k = tl.program_id(1).to(tl.int64) * BK + tl.arange(0, BK)
        vc = tl.arange(0, BV)
        acc = tl.full((BM, BK), 0., tl.float32)
        for vt in range(tl.cdiv(V, BV)):
            col = vt * BV + vc
            p = tl.load(DP + row[:, None] * V + col[None, :],
                        (row[:, None] < C) & (col[None, :] < V), 0.)
            w = tl.load(W + col[:, None] * H + k[None, :],
                        (col[:, None] < V) & (k[None, :] < H), 0.)
            acc += tl.dot(p.to(w.dtype), w, input_precision="ieee")
        tl.store(DX + row[:, None] * H + k[None, :], acc,
                 (row[:, None] < C) & (k[None, :] < H))

    @triton.jit
    def _chunk_dw(DP, X, DW, DB, C: tl.constexpr, H: tl.constexpr, V: tl.constexpr,
                  HAS_BIAS: tl.constexpr, FIRST: tl.constexpr,
                  BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        col = tl.program_id(0).to(tl.int64) * BV + tl.arange(0, BV)
        ht = tl.program_id(1)
        k = ht.to(tl.int64) * BK + tl.arange(0, BK)
        rm = tl.arange(0, BM)
        acc = tl.full((BV, BK), 0., tl.float32)
        db = tl.full((BV,), 0., tl.float32)
        for mt in range(tl.cdiv(C, BM)):
            row = mt * BM + rm
            p = tl.load(DP + row[:, None].to(tl.int64) * V + col[None, :],
                        (row[:, None] < C) & (col[None, :] < V), 0.)
            x = tl.load(X + row[:, None].to(tl.int64) * H + k[None, :],
                        (row[:, None] < C) & (k[None, :] < H), 0.)
            acc += tl.dot(tl.trans(p.to(x.dtype)), x, input_precision="ieee")
            if HAS_BIAS and ht == 0:
                db += tl.sum(p, 0)
        offsets = col[:, None] * H + k[None, :]
        mask = (col[:, None] < V) & (k[None, :] < H)
        if not FIRST:
            acc += tl.load(DW + offsets, mask, 0.)
        tl.store(DW + offsets, acc, mask)
        if HAS_BIAS and ht == 0:
            if not FIRST:
                db += tl.load(DB + col, col < V, 0.)
            tl.store(DB + col, db, col < V)


def _chunked_backward(x, weight, bias, targets, lz, count, grad_output, token_chunk,
                       dx_dtype, dw_dtype, db_dtype, ignore_index):
    n, h = x.shape
    v = weight.shape[0]
    # Allocate once and reuse across all token chunks. Accumulate dW/dBias in
    # fp32 across chunks, casting once at the end for native low-precision params.
    dp = torch.empty((min(n, token_chunk), v), device=x.device, dtype=torch.float32)
    dx = torch.empty(x.shape, device=x.device, dtype=dx_dtype)
    dw = torch.empty(weight.shape, device=x.device, dtype=torch.float32)
    db = torch.empty((v if bias is not None else 0,), device=x.device, dtype=torch.float32)
    b = x if bias is None else bias
    for start in range(0, n, token_chunk):
        end = min(start + token_chunk, n)
        c = end - start
        _chunk_dlogits[(triton.cdiv(c, BM), triton.cdiv(v, BV))](
            x[start:end], weight, b, targets[start:end], lz[start:end], count, grad_output,
            dp, c, h, v, ignore_index, bias is not None, BM, BV, BK, num_warps=4)
        _chunk_dx[(triton.cdiv(c, BM), triton.cdiv(h, BK))](
            dp, weight, dx[start:end], c, h, v, BM, BV, BK, num_warps=4)
        _chunk_dw[(triton.cdiv(v, BV), triton.cdiv(h, BK))](
            dp, x[start:end], dw, db, c, h, v, bias is not None, start == 0,
            BM, BV, BK, num_warps=4)
    return dx, dw.to(dw_dtype), db.to(db_dtype) if bias is not None else None


class _FusedLinearCE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, weight, bias, targets, ignore_index, backward_impl, token_chunk):
        if backward_impl not in BACKWARD_IMPLS:
            raise ValueError(f"backward_impl must be one of {BACKWARD_IMPLS}")
        if type(token_chunk) is not int or token_chunk < 1:
            raise ValueError("token_chunk must be a positive integer")
        if x.ndim != 2 or weight.ndim != 2:
            raise ValueError("x and weight must be [tokens, hidden] and [vocab, hidden]")
        n, h = x.shape
        v, weight_h = weight.shape
        if n < 1 or h < 1 or v < 1 or weight_h != h:
            raise ValueError("x and weight need nonzero dimensions and matching hidden sizes")
        if targets.numel() != n:
            raise ValueError("targets must contain exactly one label per input token")
        if bias is not None and (bias.ndim != 1 or bias.numel() != v):
            raise ValueError("bias must have shape [vocab]")
        if targets.dtype not in (torch.uint8, torch.int8, torch.int16, torch.int32, torch.int64):
            raise TypeError("targets must contain integer token IDs")
        if x.dtype not in (torch.float32, torch.float16, torch.bfloat16):
            raise TypeError("x must have a supported floating point dtype")
        use_amp = torch.is_autocast_enabled("cuda")
        if not use_amp and (weight.dtype != x.dtype or
                            (bias is not None and bias.dtype != x.dtype)):
            raise TypeError("x, weight, and bias must have the same dtype")
        if weight.device != x.device or targets.device != x.device or (
                bias is not None and bias.device != x.device):
            raise ValueError("x, weight, bias, and targets must share a device")
        if triton is None or x.device.type != "cuda":
            raise RuntimeError("triton_ce requires CUDA and Triton available in the PyTorch environment")
        x, weight = x.contiguous(), weight.contiguous()
        targets = targets.reshape(-1).long().contiguous()
        dtype = torch.get_autocast_dtype("cuda") if use_amp else x.dtype
        xc, wc = x.to(dtype), weight.to(dtype)
        bc = xc if bias is None else bias.to(dtype).contiguous()
        nt = triton.cdiv(v, BV)
        pm = torch.empty((n, nt), device=x.device, dtype=torch.float32)
        ps, pt = torch.empty_like(pm), torch.empty_like(pm)
        loss = torch.empty((n,), device=x.device, dtype=torch.float32)
        lz = torch.empty_like(loss)
        with torch.cuda.device(x.device):
            _forward[(triton.cdiv(n, BM), nt)](xc, wc, bc, targets, pm, ps, pt, n, h, v,
                xc.stride(0), xc.stride(1), wc.stride(0), wc.stride(1), nt, bias is not None,
                BM, BV, BK, num_warps=4)
            _reduce[(n,)](targets, pm, ps, pt, loss, lz, n, nt, ignore_index,
                          triton.next_power_of_2(nt), num_warps=4)
        count = (targets != ignore_index).sum().clamp_min(1)
        result = loss.sum() / count
        bsave = x.new_empty((0,)) if bias is None else bias
        ctx.save_for_backward(x, weight, targets, lz, bsave, count)
        ctx.has_bias, ctx.ignore_index, ctx.dtype = bias is not None, ignore_index, dtype
        ctx.backward_impl, ctx.token_chunk = backward_impl, token_chunk
        return result

    @staticmethod
    def backward(ctx, grad_output):
        x, weight, targets, lz, bsave, count = ctx.saved_tensors
        bias = bsave if ctx.has_bias else None
        n, h, v = x.shape[0], x.shape[1], weight.shape[0]
        xc, wc = x.to(ctx.dtype).contiguous(), weight.to(ctx.dtype).contiguous()
        bc = xc if bias is None else bias.to(ctx.dtype).contiguous()
        if ctx.backward_impl == "chunked":
            with torch.cuda.device(x.device):
                dx, dw, db = _chunked_backward(
                    xc, wc, None if bias is None else bc, targets, lz, count, grad_output,
                    ctx.token_chunk, x.dtype, weight.dtype, None if bias is None else bias.dtype,
                    ctx.ignore_index)
            return dx, dw, db, None, None, None, None
        dx, dw = torch.empty_like(x), torch.empty_like(weight)
        db = torch.empty_like(bias) if bias is not None else torch.empty((0,), device=x.device)
        with torch.cuda.device(x.device):
            _grad_x[(triton.cdiv(n, BM), triton.cdiv(h, BK))](xc, wc, bc, targets, lz, count, grad_output, dx,
                n, h, v, xc.stride(0), xc.stride(1), wc.stride(0), wc.stride(1), dx.stride(0), dx.stride(1),
                ctx.ignore_index, ctx.has_bias, BM, BV, BK, num_warps=4)
            _grad_w[(triton.cdiv(v, BV), triton.cdiv(h, BK))](xc, wc, bc, targets, lz, count, grad_output, dw, db,
                n, h, v, xc.stride(0), xc.stride(1), wc.stride(0), wc.stride(1), dw.stride(0), dw.stride(1),
                ctx.ignore_index, ctx.has_bias, BM, BV, BK, num_warps=4)
        return dx, dw, db if ctx.has_bias else None, None, None, None, None


def linear_cross_entropy_fused_triton(x, weight, targets, *, bias=None, ignore_index=-100,
                                     backward_impl="chunked", token_chunk=128):
    """Tiled forward; bounded-chunk backward by default, or old recompute comparison."""
    return _FusedLinearCE.apply(x, weight, bias, targets, ignore_index, backward_impl, token_chunk)
