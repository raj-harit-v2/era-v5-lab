"""In-repo tiled linear CE with bounded scratch and deterministic gradients.

Forward streams token chunks of partial log-sum-exp statistics. Backward can
stream tokens or vocabulary; auto chooses the smaller gradient to accumulate.
FP16 gradient products use FP32 operands; BF16 tensor-core products are optional.
"""
from __future__ import annotations

from contextlib import nullcontext
import operator

import torch
from torch.autograd.function import once_differentiable
from perfkit.regions import region

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None

BM, BV, BK = 16, 128, 32
BACKWARD_IMPLS = ("auto", "vocab", "chunked", "recompute")
GRAD_PRECISIONS = ("auto", "fp32")
LAUNCH = dict(num_warps=4, num_stages=1, enable_fp_fusion=True)
DTYPES = (torch.float16, torch.bfloat16, torch.float32)


def _positive_int(value, name):
    try:
        result = operator.index(value)
    except TypeError:
        raise ValueError(f"{name} must be a positive integer") from None
    if isinstance(value, bool) or result < 1:
        raise ValueError(f"{name} must be a positive integer")
    return result


def streaming_plan(n, v, token_chunk, vocab_chunk, budget, mode):
    """Pure shape arithmetic: direction and maximum extent within DP byte budget."""
    if mode == "auto":
        mode = "vocab" if n <= v else "chunked"
    fixed = n if mode == "vocab" else v
    capacity = budget // (4 * fixed)
    if capacity < 1:
        raise ValueError("scratch budget cannot hold one derivative slice; increase scratch_mb")
    extent = min(v if mode == "vocab" else n,
                 vocab_chunk if mode == "vocab" else token_chunk, capacity)
    return mode, extent


def forward_chunk_rows(n, nt, budget):
    capacity = budget // (12 * nt)  # three fp32 partial-statistic buffers
    if capacity < 1:
        raise ValueError("scratch budget cannot hold one forward statistic row")
    return min(n, capacity)


def _timed(name):
    return nullcontext() if torch.compiler.is_compiling() else region(name, 3)


if triton is not None:
    @triton.jit
    def _offset(row, col, stride: tl.constexpr):
        return row.to(tl.int64) * stride + col.to(tl.int64)

    @triton.jit
    def _probabilities(logits, lz, y, valid_rows, cols, class_start,
                       LOCAL_V: tl.constexpr, TOTAL_V: tl.constexpr, IGNORE: tl.constexpr):
        logits = tl.where(cols[None, :] < LOCAL_V, logits, -float("inf"))
        p = tl.exp(logits - lz[:, None])
        p = tl.where(cols[None, :] + class_start == y[:, None], p - 1., p)
        invalid = (y != IGNORE) & ((y < 0) | (y >= TOTAL_V))
        p = tl.where(invalid[:, None], float("nan"), p)
        valid = valid_rows[:, None] & (cols[None, :] < LOCAL_V) & (y[:, None] != IGNORE)
        return tl.where(valid, p, 0.)

    @triton.jit
    def _grad_dot(a, b, FP32: tl.constexpr):
        if FP32:
            return tl.dot(a.to(tl.float32), b.to(tl.float32), input_precision="ieee")
        return tl.dot(a.to(b.dtype), b, input_precision="ieee")

    @triton.jit(do_not_specialize=["N"])
    def _forward(X, W, B, Y, PM, PS, PT, N, H: tl.constexpr, V: tl.constexpr,
                 X0: tl.constexpr, X1: tl.constexpr, W0: tl.constexpr, W1: tl.constexpr,
                 NT: tl.constexpr, HAS_BIAS: tl.constexpr,
                 BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        rows = tl.program_id(0).to(tl.int64) * BM + tl.arange(0, BM)
        cols = tl.program_id(1).to(tl.int64) * BV + tl.arange(0, BV)
        rk = tl.arange(0, BK)
        acc = tl.full((BM, BV), 0., tl.float32)
        for kt in range(tl.cdiv(H, BK)):
            ks = kt * BK + rk
            a = tl.load(X + rows[:, None] * X0 + ks[None, :] * X1,
                        (rows[:, None] < N) & (ks[None, :] < H), 0.)
            b = tl.load(W + cols[:, None] * W0 + ks[None, :] * W1,
                        (cols[:, None] < V) & (ks[None, :] < H), 0.)
            acc += tl.dot(a, tl.trans(b), input_precision="ieee")
        if HAS_BIAS:
            acc += tl.load(B + cols, cols < V, 0.).to(tl.float32)[None, :]
        z = tl.where((rows[:, None] < N) & (cols[None, :] < V), acc, -float("inf"))
        m = tl.max(z, 1)
        safe_m = tl.where(rows < N, m, 0.)
        s = tl.sum(tl.exp(z - safe_m[:, None]), 1)
        y = tl.load(Y + tl.minimum(rows, N - 1))
        selected = tl.sum(tl.where(cols[None, :] == y[:, None], z, 0.), 1)
        off = _offset(rows, tl.program_id(1), NT)
        tl.store(PM + off, m, rows < N)
        tl.store(PS + off, s, rows < N)
        tl.store(PT + off, selected, rows < N)

    @triton.jit
    def _reduce(Y, PM, PS, PT, LOSS, LZ, NT: tl.constexpr, V: tl.constexpr,
                IGNORE: tl.constexpr, BT: tl.constexpr):
        row = tl.program_id(0).to(tl.int64)
        t = tl.arange(0, BT)
        off = _offset(row, t, NT)
        mi = tl.load(PM + off, t < NT, -float("inf"))
        si = tl.load(PS + off, t < NT, 0.)
        yi = tl.load(PT + off, t < NT, 0.)
        m = tl.max(mi, 0)
        lz = tl.log(tl.sum(si * tl.exp(mi - m), 0)) + m
        target = tl.load(Y + row)
        loss = tl.where((target >= 0) & (target < V), lz - tl.sum(yi, 0), float("nan"))
        tl.store(LZ + row, lz)
        tl.store(LOSS + row, tl.where(target == IGNORE, 0., loss))

    @triton.jit(do_not_specialize=["N"])
    def _grad_x(X, W, B, Y, LZ, COUNT, GO, DX, N, H: tl.constexpr, V: tl.constexpr,
                IGNORE: tl.constexpr, HAS_BIAS: tl.constexpr, FP32: tl.constexpr,
                BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        rows = tl.program_id(0).to(tl.int64) * BM + tl.arange(0, BM)
        k = tl.program_id(1).to(tl.int64) * BK + tl.arange(0, BK)
        rk, vc = tl.arange(0, BK), tl.arange(0, BV)
        safe_rows = tl.minimum(rows, N - 1)
        y, lz = tl.load(Y + safe_rows), tl.load(LZ + safe_rows)
        acc = tl.full((BM, BK), 0., tl.float32)
        for vt in range(tl.cdiv(V, BV)):
            cols = vt.to(tl.int64) * BV + vc
            logits = tl.full((BM, BV), 0., tl.float32)
            for kt in range(tl.cdiv(H, BK)):
                ks = kt * BK + rk
                a = tl.load(X + _offset(rows[:, None], ks[None, :], H),
                            (rows[:, None] < N) & (ks[None, :] < H), 0.)
                b = tl.load(W + _offset(cols[:, None], ks[None, :], H),
                            (cols[:, None] < V) & (ks[None, :] < H), 0.)
                logits += tl.dot(a, tl.trans(b), input_precision="ieee")
            if HAS_BIAS:
                logits += tl.load(B + cols, cols < V, 0.).to(tl.float32)[None, :]
            p = _probabilities(logits, lz, y, rows < N, cols, 0, V, V, IGNORE)
            w = tl.load(W + _offset(cols[:, None], k[None, :], H),
                        (cols[:, None] < V) & (k[None, :] < H), 0.)
            acc += _grad_dot(p, w, FP32)
        scale = tl.load(GO).to(tl.float32) / tl.load(COUNT).to(tl.float32)
        tl.store(DX + _offset(rows[:, None], k[None, :], H), acc * scale,
                 (rows[:, None] < N) & (k[None, :] < H))

    @triton.jit(do_not_specialize=["N"])
    def _grad_w(X, W, B, Y, LZ, COUNT, GO, DW, DB, N, H: tl.constexpr, V: tl.constexpr,
                IGNORE: tl.constexpr, HAS_BIAS: tl.constexpr, FP32: tl.constexpr,
                NEED_W: tl.constexpr, NEED_B: tl.constexpr,
                BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        cols = tl.program_id(0).to(tl.int64) * BV + tl.arange(0, BV)
        ht = tl.program_id(1)
        k = ht.to(tl.int64) * BK + tl.arange(0, BK)
        rm, rk = tl.arange(0, BM), tl.arange(0, BK)
        acc = tl.full((BV, BK), 0., tl.float32)
        db = tl.full((BV,), 0., tl.float32)
        for mt in range(tl.cdiv(N.to(tl.int64), BM)):
            rows = mt.to(tl.int64) * BM + rm
            safe_rows = tl.minimum(rows, N - 1)
            y, lz = tl.load(Y + safe_rows), tl.load(LZ + safe_rows)
            logits = tl.full((BM, BV), 0., tl.float32)
            for kt in range(tl.cdiv(H, BK)):
                ks = kt * BK + rk
                a = tl.load(X + _offset(rows[:, None], ks[None, :], H),
                            (rows[:, None] < N) & (ks[None, :] < H), 0.)
                w = tl.load(W + _offset(cols[:, None], ks[None, :], H),
                            (cols[:, None] < V) & (ks[None, :] < H), 0.)
                logits += tl.dot(a, tl.trans(w), input_precision="ieee")
            if HAS_BIAS:
                logits += tl.load(B + cols, cols < V, 0.).to(tl.float32)[None, :]
            p = _probabilities(logits, lz, y, rows < N, cols, 0, V, V, IGNORE)
            if NEED_W:
                x = tl.load(X + _offset(rows[:, None], k[None, :], H),
                            (rows[:, None] < N) & (k[None, :] < H), 0.)
                acc += _grad_dot(tl.trans(p), x, FP32)
            if NEED_B and ht == 0:
                db += tl.sum(p, 0)
        scale = tl.load(GO).to(tl.float32) / tl.load(COUNT).to(tl.float32)
        if NEED_W:
            tl.store(DW + _offset(cols[:, None], k[None, :], H), acc * scale,
                     (cols[:, None] < V) & (k[None, :] < H))
        if NEED_B and ht == 0:
            tl.store(DB + cols, db * scale, cols < V)

    @triton.jit(do_not_specialize=["C", "CLASS_START"])
    def _chunk_dlogits(X, W, B, Y, LZ, DP, C, H: tl.constexpr, V: tl.constexpr,
                       CLASS_START, TOTAL_V: tl.constexpr, IGNORE: tl.constexpr,
                       HAS_BIAS: tl.constexpr, BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BM + tl.arange(0, BM)
        col = tl.program_id(1).to(tl.int64) * BV + tl.arange(0, BV)
        rk = tl.arange(0, BK)
        logits = tl.full((BM, BV), 0., tl.float32)
        for kt in range(tl.cdiv(H, BK)):
            k = kt * BK + rk
            a = tl.load(X + _offset(row[:, None], k[None, :], H),
                        (row[:, None] < C) & (k[None, :] < H), 0.)
            b = tl.load(W + _offset(col[:, None], k[None, :], H),
                        (col[:, None] < V) & (k[None, :] < H), 0.)
            logits += tl.dot(a, tl.trans(b), input_precision="ieee")
        if HAS_BIAS:
            logits += tl.load(B + col, col < V, 0.).to(tl.float32)[None, :]
        safe_rows = tl.minimum(row, C - 1)
        lz, y = tl.load(LZ + safe_rows), tl.load(Y + safe_rows)
        p = _probabilities(logits, lz, y, row < C, col, CLASS_START, V, TOTAL_V, IGNORE)
        tl.store(DP + _offset(row[:, None], col[None, :], V), p,
                 (row[:, None] < C) & (col[None, :] < V))

    @triton.jit(do_not_specialize=["C"])
    def _chunk_dx(DP, W, DX, COUNT, GO, C, H: tl.constexpr, V: tl.constexpr,
                  FIRST: tl.constexpr, SCALE_NOW: tl.constexpr, FP32: tl.constexpr,
                  BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BM + tl.arange(0, BM)
        k = tl.program_id(1).to(tl.int64) * BK + tl.arange(0, BK)
        vc = tl.arange(0, BV)
        acc = tl.full((BM, BK), 0., tl.float32)
        for vt in range(tl.cdiv(V, BV)):
            col = vt.to(tl.int64) * BV + vc
            p = tl.load(DP + _offset(row[:, None], col[None, :], V),
                        (row[:, None] < C) & (col[None, :] < V), 0.)
            w = tl.load(W + _offset(col[:, None], k[None, :], H),
                        (col[:, None] < V) & (k[None, :] < H), 0.)
            acc += _grad_dot(p, w, FP32)
        mask = (row[:, None] < C) & (k[None, :] < H)
        off = _offset(row[:, None], k[None, :], H)
        if not FIRST:
            acc += tl.load(DX + off, mask, 0.)
        if SCALE_NOW:
            acc *= tl.load(GO).to(tl.float32) / tl.load(COUNT).to(tl.float32)
        tl.store(DX + off, acc, mask)

    @triton.jit(do_not_specialize=["C"])
    def _chunk_dw(DP, X, DW, DB, COUNT, GO, C, H: tl.constexpr, V: tl.constexpr,
                  FIRST: tl.constexpr, SCALE_NOW: tl.constexpr, FP32: tl.constexpr,
                  NEED_W: tl.constexpr, NEED_B: tl.constexpr,
                  BM: tl.constexpr, BV: tl.constexpr, BK: tl.constexpr):
        col = tl.program_id(0).to(tl.int64) * BV + tl.arange(0, BV)
        ht = tl.program_id(1)
        k = ht.to(tl.int64) * BK + tl.arange(0, BK)
        rm = tl.arange(0, BM)
        acc = tl.full((BV, BK), 0., tl.float32)
        db = tl.full((BV,), 0., tl.float32)
        for mt in range(tl.cdiv(C.to(tl.int64), BM)):
            row = mt.to(tl.int64) * BM + rm
            p = tl.load(DP + _offset(row[:, None], col[None, :], V),
                        (row[:, None] < C) & (col[None, :] < V), 0.)
            if NEED_W:
                x = tl.load(X + _offset(row[:, None], k[None, :], H),
                            (row[:, None] < C) & (k[None, :] < H), 0.)
                acc += _grad_dot(tl.trans(p), x, FP32)
            if NEED_B and ht == 0:
                db += tl.sum(p, 0)
        mask = (col[:, None] < V) & (k[None, :] < H)
        off = _offset(col[:, None], k[None, :], H)
        if NEED_W and not FIRST:
            acc += tl.load(DW + off, mask, 0.)
        if NEED_B and ht == 0 and not FIRST:
            db += tl.load(DB + col, col < V, 0.)
        if SCALE_NOW:
            scale = tl.load(GO).to(tl.float32) / tl.load(COUNT).to(tl.float32)
            acc *= scale
            db *= scale
        if NEED_W:
            tl.store(DW + off, acc, mask)
        if NEED_B and ht == 0:
            tl.store(DB + col, db, col < V)

    @triton.jit(do_not_specialize=["SIZE"])
    def _scale_cast(SRC, OUT, COUNT, GO, SIZE, BLOCK: tl.constexpr):
        off = tl.program_id(0).to(tl.int64) * BLOCK + tl.arange(0, BLOCK)
        scale = tl.load(GO).to(tl.float32) / tl.load(COUNT).to(tl.float32)
        tl.store(OUT + off, tl.load(SRC + off, off < SIZE, 0.) * scale, off < SIZE)


def _finish(src, dtype, count, go):
    if src is None:
        return None
    out = src if src.dtype == dtype else torch.empty(src.shape, device=src.device, dtype=dtype)
    with _timed("ce.triton.scale"):
        _scale_cast[(triton.cdiv(src.numel(), 1024),)](src, out, count, go, src.numel(), 1024, **LAUNCH)
    return out


def _stream_backward(ctx, x, w, b, y, lz, count, go):
    n, h = x.shape
    v = w.shape[0]
    need_x, need_w, need_b = ctx.needs_input_grad[:3]
    mode, extent = streaming_plan(n, v, ctx.token_chunk, ctx.vocab_chunk, ctx.budget, ctx.backward_impl)
    vocab = mode == "vocab"
    dp = torch.empty((n, extent) if vocab else (extent, v), device=x.device, dtype=torch.float32)
    dx = torch.empty(x.shape, device=x.device, dtype=torch.float32 if vocab else ctx.x_dtype) if need_x else None
    dw = torch.empty(w.shape, device=x.device, dtype=ctx.w_dtype if vocab else torch.float32) if need_w else None
    db = torch.empty((v,), device=x.device, dtype=ctx.b_dtype if vocab else torch.float32) if need_b else None
    # Flags compile away all accesses to dummy pointers for absent gradients.
    dummy = x
    limit = v if vocab else n
    for start in range(0, limit, extent):
        end = min(start + extent, limit)
        xc, wc = (x, w[start:end]) if vocab else (x[start:end], w)
        bc = (b[start:end] if vocab else b) if b is not None else dummy
        yc, lc = (y, lz) if vocab else (y[start:end], lz[start:end])
        c, nv = xc.shape[0], wc.shape[0]
        with _timed("ce.triton.dlogits"):
            _chunk_dlogits[(triton.cdiv(c, BM), triton.cdiv(nv, BV))](
                xc, wc, bc, yc, lc, dp, c, h, nv, start if vocab else 0, v,
                ctx.ignore_index, b is not None, BM, BV, BK, **LAUNCH)
        if need_x:
            with _timed("ce.triton.dx"):
                _chunk_dx[(triton.cdiv(c, BM), triton.cdiv(h, BK))](
                    dp, wc, dx if vocab else dx[start:end], count, go, c, h, nv,
                    start == 0 if vocab else True, not vocab, ctx.fp32_grad, BM, BV, BK, **LAUNCH)
        if need_w or need_b:
            with _timed("ce.triton.dw"):
                _chunk_dw[(triton.cdiv(nv, BV), triton.cdiv(h, BK) if need_w else 1)](
                    dp, xc, (dw[start:end] if vocab else dw) if need_w else dummy,
                    (db[start:end] if vocab else db) if need_b else dummy, count, go, c, h, nv,
                    True if vocab else start == 0, vocab, ctx.fp32_grad, need_w, need_b, BM, BV, BK, **LAUNCH)
    if vocab:
        dx = _finish(dx, ctx.x_dtype, count, go)
    else:
        dw = _finish(dw, ctx.w_dtype, count, go)
        db = _finish(db, ctx.b_dtype, count, go)
    return dx, dw, db


class _FusedLinearCE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, weight, bias, targets, ignore_index, backward_impl, token_chunk,
                vocab_chunk, scratch_mb, grad_precision, validate_targets):
        if backward_impl not in BACKWARD_IMPLS:
            raise ValueError(f"backward_impl must be one of {BACKWARD_IMPLS}")
        if grad_precision not in GRAD_PRECISIONS:
            raise ValueError(f"grad_precision must be one of {GRAD_PRECISIONS}")
        token_chunk = _positive_int(token_chunk, "token_chunk")
        vocab_chunk = _positive_int(vocab_chunk, "vocab_chunk")
        budget = _positive_int(scratch_mb, "scratch_mb") * 1024**2
        if type(validate_targets) is not bool:
            raise TypeError("validate_targets must be boolean")
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
        if x.dtype not in DTYPES or weight.dtype not in DTYPES or (bias is not None and bias.dtype not in DTYPES):
            raise TypeError("x, weight, and bias must use fp16, bf16, or fp32")
        use_amp = torch.is_autocast_enabled("cuda")
        if not use_amp and (weight.dtype != x.dtype or (bias is not None and bias.dtype != x.dtype)):
            raise TypeError("x, weight, and bias must have the same dtype")
        if weight.device != x.device or targets.device != x.device or (bias is not None and bias.device != x.device):
            raise ValueError("x, weight, bias, and targets must share a device")
        if triton is None or x.device.type != "cuda":
            raise RuntimeError("triton_ce requires CUDA and Triton available in the PyTorch environment")
        targets = targets.reshape(-1).long().contiguous()
        if validate_targets and bool(((targets != ignore_index) & ((targets < 0) | (targets >= v))).any().item()):
            raise ValueError("Target token ID outside vocabulary")
        dtype = torch.get_autocast_dtype("cuda") if use_amp else x.dtype
        xc, wc = x.to(dtype).contiguous(), weight.to(dtype).contiguous()
        bc = None if bias is None else bias.to(dtype).contiguous()
        nt = triton.cdiv(v, BV)
        rows = forward_chunk_rows(n, nt, budget)
        with torch.cuda.device(x.device):
            pm = torch.empty((rows, nt), device=x.device, dtype=torch.float32)
            ps, pt = torch.empty_like(pm), torch.empty_like(pm)
            loss = torch.empty((n,), device=x.device, dtype=torch.float32)
            lz = torch.empty_like(loss)
            for start in range(0, n, rows):
                end = min(start + rows, n)
                c = end - start
                with _timed("ce.triton.forward_stats"):
                    _forward[(triton.cdiv(c, BM), nt)](xc[start:end], wc, xc if bc is None else bc,
                        targets[start:end], pm, ps, pt, c, h, v, h, 1, h, 1, nt, bc is not None,
                        BM, BV, BK, **LAUNCH)
                    _reduce[(c,)](targets[start:end], pm, ps, pt, loss[start:end], lz[start:end],
                                  nt, v, ignore_index, triton.next_power_of_2(nt), **LAUNCH)
        count = (targets != ignore_index).sum().clamp_min(1)
        # Keep original tensors for version checks and saved compute casts to
        # avoid materializing the entire low-precision head again in backward.
        empty_bias = x.new_empty(0) if bias is None else bias
        ctx.save_for_backward(x, weight, empty_bias, xc, wc, xc if bc is None else bc, targets, lz, count)
        ctx.has_bias, ctx.ignore_index = bias is not None, ignore_index
        ctx.x_dtype, ctx.w_dtype = x.dtype, weight.dtype
        ctx.b_dtype = None if bias is None else bias.dtype
        ctx.backward_impl, ctx.token_chunk, ctx.vocab_chunk, ctx.budget = backward_impl, token_chunk, vocab_chunk, budget
        ctx.fp32_grad = grad_precision == "fp32" or dtype != torch.bfloat16
        return loss.sum() / count

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_output):
        _, _, _, x, w, saved_bias, y, lz, count = ctx.saved_tensors
        b = saved_bias if ctx.has_bias else None
        n, h = x.shape
        v = w.shape[0]
        need_x, need_w, need_b = ctx.needs_input_grad[:3]
        with torch.cuda.device(x.device):
            if ctx.backward_impl != "recompute":
                dx, dw, db = _stream_backward(ctx, x, w, b, y, lz, count, grad_output)
            else:
                dx = torch.empty(x.shape, device=x.device, dtype=ctx.x_dtype) if need_x else None
                dw = torch.empty(w.shape, device=x.device, dtype=ctx.w_dtype) if need_w else None
                db = torch.empty((v,), device=x.device, dtype=ctx.b_dtype) if need_b else None
                dummy = x
                if need_x:
                    _grad_x[(triton.cdiv(n, BM), triton.cdiv(h, BK))](x, w, dummy if b is None else b,
                        y, lz, count, grad_output, dx, n, h, v, ctx.ignore_index, b is not None,
                        ctx.fp32_grad, BM, BV, BK, **LAUNCH)
                if need_w or need_b:
                    _grad_w[(triton.cdiv(v, BV), triton.cdiv(h, BK) if need_w else 1)](
                        x, w, dummy if b is None else b, y, lz, count, grad_output,
                        dw if need_w else dummy, db if need_b else dummy, n, h, v, ctx.ignore_index,
                        b is not None, ctx.fp32_grad, need_w, need_b, BM, BV, BK, **LAUNCH)
        return dx, dw, db, None, None, None, None, None, None, None, None


def linear_cross_entropy_fused_triton(x, weight, targets, *, bias=None, ignore_index=-100,
                                     backward_impl="auto", token_chunk=128, vocab_chunk=4096,
                                     scratch_mb=64, grad_precision="auto", validate_targets=False):
    """Mean linear CE, fp32 loss, zero for all-ignored input; first derivatives only.

    No class weights or label smoothing. validate_targets=True performs one
    explicit host synchronization and raises for invalid IDs; unchecked invalid
    IDs produce a NaN loss instead of a plausible but incorrect finite loss.
    """
    return _FusedLinearCE.apply(x, weight, bias, targets, operator.index(ignore_index), backward_impl,
                                token_chunk, vocab_chunk, scratch_mb, grad_precision, validate_targets)
