"""Linear cross-entropy with cuBLAS matmuls and one Triton pass for the softmax gradient (ce_impl=fused_triton).

Per token chunk (ce_chunks pieces, as ce_impl=fused):
    logits = x W^T (+ b)                              cuBLAS, in the matmul dtype (bf16 under autocast)
    lse, loss, g = (softmax(logits) - onehot) / count  one Triton kernel, two reads of each row, g written over
                                                       the logits (bf16) or into an fp32 buffer (fp16 / fp32)
    dx = g W,   dW += g^T x,   db += sum(g)             cuBLAS
backward only scales the cached gradients by grad_output. 3 head matmuls per step, all on cuBLAS (PR 52's
triton_ce does 4 in its own tiles), and no fp32 copy of the logits: ce_impl=fused spends about 8 elementwise
passes per chunk on fp32 logits (cast, logsumexp, gather, sub, exp, mask, scatter, div).

Same numerics as ce_impl=fused (models/linear_ce.py): fp32 reductions, bf16 gradient matmuls under bf16, fp32
products otherwise (fp16 softmax gradients can underflow before the GradScaler). The mean is over non-ignored
targets; an invalid non-ignored target gives a NaN loss. Without CUDA or Triton: ce_impl=fused.
"""
from __future__ import annotations

from contextlib import nullcontext

import torch
import torch.nn.functional as F
from torch.autograd.function import once_differentiable

from perfkit.regions import region

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None

BLOCK = 2048


def _timed(name):
    return nullcontext() if torch.compiler.is_compiling() else region(name, 3)


if triton is not None:
    @triton.jit(do_not_specialize=["V", "LS", "GS"])
    def _softmax_grad(L, Y, G, LOSS, COUNT, V, LS, GS, IGNORE: tl.constexpr, BLOCK: tl.constexpr):
        row = tl.program_id(0).to(tl.int64)
        y = tl.load(Y + row)
        keep = y != IGNORE
        bad = keep & ((y < 0) | (y >= V))
        base = L + row * LS
        cols = tl.arange(0, BLOCK)
        m = tl.full((BLOCK,), -float("inf"), tl.float32)        # per-lane online max and sum
        s = tl.full((BLOCK,), 0., tl.float32)
        for start in range(0, V, BLOCK):
            c = start + cols
            x = tl.load(base + c, c < V, -float("inf")).to(tl.float32)
            m_new = tl.maximum(m, x)
            m_safe = tl.where(m_new == -float("inf"), 0., m_new)  # lanes past V stay -inf: no inf - inf
            s = s * tl.exp(m - m_safe) + tl.exp(x - m_safe)
            m = m_new
        top = tl.max(m, 0)
        lse = top + tl.log(tl.sum(s * tl.exp(m - top), 0))
        target = tl.load(base + tl.where(keep & ~bad, y, 0)).to(tl.float32)
        loss = tl.where(keep, lse - target, 0.)
        tl.store(LOSS + row, tl.where(bad, float("nan"), loss))
        inv = tl.where(keep, 1. / tl.load(COUNT).to(tl.float32), 0.)
        gbase = G + row * GS
        for start in range(0, V, BLOCK):
            c = start + cols
            x = tl.load(base + c, c < V, 0.).to(tl.float32)
            g = tl.exp(x - lse) * inv
            g = tl.where(c == y, g - inv, g)
            tl.store(gbase + c, g, c < V)


def supported(x: torch.Tensor, weight: torch.Tensor) -> bool:
    return triton is not None and x.is_cuda and weight.is_cuda


class _CublasLinearCE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, weight, bias, targets, chunks: int, ignore_index: int):
        if x.ndim != 2 or weight.ndim != 2 or x.shape[1] != weight.shape[1]:
            raise ValueError("linear cross-entropy expects x [tokens, hidden] and weight [vocab, hidden]")
        y = targets.reshape(-1).long().contiguous()
        if y.numel() != x.shape[0]:
            raise ValueError("target count must match the number of input rows")
        compute = (torch.get_autocast_dtype("cuda") if torch.is_autocast_enabled("cuda")
                   else torch.promote_types(x.dtype, weight.dtype))
        need_x, need_w, need_b = ctx.needs_input_grad[:3]
        with torch.autocast(device_type="cuda", enabled=False):
            out = _CublasLinearCE._run(x, weight, bias, y, chunks, ignore_index, compute, need_x, need_w, need_b)
        loss, dx, dw, db = out
        ctx.save_for_backward(*(t for t in (dx, dw, db) if t is not None))
        ctx.present = (dx is not None, dw is not None, db is not None)
        ctx.dtypes = (x.dtype, weight.dtype, None if bias is None else bias.dtype)
        return loss

    @staticmethod
    def _run(x, weight, bias, y, chunks, ignore_index, compute, need_x, need_w, need_b):
        n, v = x.shape[0], weight.shape[0]
        xc, wc = x.to(compute).contiguous(), weight.to(compute).contiguous()
        bc = None if bias is None else bias.to(compute)
        low = compute == torch.bfloat16                 # bf16 gradient products, as ce_impl=fused
        wg = wc if low else wc.float()
        count = (y != ignore_index).sum().clamp_min(1)
        losses = torch.empty(n, device=x.device, dtype=torch.float32)
        dx = torch.empty(x.shape, device=x.device, dtype=torch.float32) if need_x else None
        dw = torch.zeros(weight.shape, device=x.device, dtype=torch.float32) if need_w else None
        db = torch.zeros(v, device=x.device, dtype=torch.float32) if (need_b and bias is not None) else None
        rows = max(1, -(-n // chunks))
        for start in range(0, n, rows):
            end = min(start + rows, n)
            with _timed("ce.cublas.logits"):
                logits = F.linear(xc[start:end], wc, bc)
            g = logits if low else torch.empty(logits.shape, device=x.device, dtype=torch.float32)
            with _timed("ce.cublas.softmax_grad"):
                _softmax_grad[(end - start,)](logits, y[start:end], g, losses[start:end], count, v,
                                              logits.stride(0), g.stride(0), ignore_index, BLOCK, num_warps=8)
            with _timed("ce.cublas.grads"):
                xg = xc[start:end] if low else xc[start:end].float()
                if dx is not None:
                    dx[start:end] = g @ wg
                if dw is not None:
                    dw.add_(g.T @ xg)
                if db is not None:
                    db.add_(g.sum(0, dtype=torch.float32))
            del logits, g
        return losses.sum() / count, dx, dw, db

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_output):
        saved = iter(ctx.saved_tensors)
        grads = [next(saved) if p else None for p in ctx.present]
        scale = grad_output.float()
        out = [None if g is None else g.mul(scale).to(dt) for g, dt in zip(grads, ctx.dtypes)]
        return out[0], out[1], out[2], None, None, None


def linear_cross_entropy_cublas(x, weight, targets, *, bias=None, chunks=8, ignore_index=-100):
    """Mean CE of x W^T (+ b) over non-ignored targets; fp32 loss. CUDA + Triton, else ce_impl=fused."""
    if chunks <= 0:
        raise ValueError("chunks must be positive")
    if not supported(x, weight):
        from models.linear_ce import linear_cross_entropy_fused
        return linear_cross_entropy_fused(x, weight, targets, bias=bias, chunks=chunks, ignore_index=ignore_index)
    return _CublasLinearCE.apply(x, weight, bias, targets, int(chunks), int(ignore_index))
