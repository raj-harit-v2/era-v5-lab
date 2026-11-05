"""Triton LayerNorm for the model's last-dimension normalization.

The row-wise forward and backward equations follow Triton's LayerNorm tutorial.
Parameter gradients use grouped partial sums and a deterministic second kernel,
without global atomics or locks.
"""
from __future__ import annotations

import torch
from torch import nn

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None


if triton is not None:
    @triton.jit
    def _forward(X, W, B, Y, MEAN, RSTD, N: tl.constexpr, EPS: tl.constexpr,
                 BLOCK: tl.constexpr):
        row = tl.program_id(0)
        col = tl.arange(0, BLOCK)
        x = tl.load(X + row * N + col, col < N, 0).to(tl.float32)
        mean = tl.sum(x, 0) / N
        centered = tl.where(col < N, x - mean, 0.)
        var = tl.sum(centered * centered, 0) / N
        rstd = tl.rsqrt(var + EPS)
        w = tl.load(W + col, col < N, 0).to(tl.float32)
        b = tl.load(B + col, col < N, 0).to(tl.float32)
        y = centered * rstd * w + b
        tl.store(Y + row * N + col, y, col < N)
        tl.store(MEAN + row, mean)
        tl.store(RSTD + row, rstd)

    @triton.jit
    def _backward_rows(X, DY, W, MEAN, RSTD, DX, PART_DW, PART_DB,
                       M: tl.constexpr, N: tl.constexpr, BLOCK: tl.constexpr,
                       GROUP: tl.constexpr):
        group = tl.program_id(0)
        col = tl.arange(0, BLOCK)
        w = tl.load(W + col, col < N, 0).to(tl.float32)
        dw = tl.full((BLOCK,), 0., tl.float32)
        db = tl.full((BLOCK,), 0., tl.float32)
        for i in range(GROUP):
            row = group * GROUP + i
            if row < M:
                x = tl.load(X + row * N + col, col < N, 0).to(tl.float32)
                dy = tl.load(DY + row * N + col, col < N, 0).to(tl.float32)
                mean = tl.load(MEAN + row)
                rstd = tl.load(RSTD + row)
                xhat = tl.where(col < N, (x - mean) * rstd, 0.)
                dy = tl.where(col < N, dy, 0.)
                wdy = dy * w
                c1 = tl.sum(xhat * wdy, 0) / N
                c2 = tl.sum(wdy, 0) / N
                dx = (wdy - xhat * c1 - c2) * rstd
                tl.store(DX + row * N + col, dx, col < N)
                dw += dy * xhat
                db += dy
        tl.store(PART_DW + group * N + col, dw, col < N)
        tl.store(PART_DB + group * N + col, db, col < N)

    @triton.jit
    def _backward_params(PART_DW, PART_DB, DW, DB, GROUPS: tl.constexpr,
                         N: tl.constexpr, ROWS: tl.constexpr, COLS: tl.constexpr):
        col = tl.program_id(0) * COLS + tl.arange(0, COLS)
        r = tl.arange(0, ROWS)
        acc_w = tl.full((ROWS, COLS), 0., tl.float32)
        acc_b = tl.full((ROWS, COLS), 0., tl.float32)
        for start in range(tl.cdiv(GROUPS, ROWS)):
            row = start * ROWS + r
            offsets = row[:, None] * N + col[None, :]
            mask = (row[:, None] < GROUPS) & (col[None, :] < N)
            acc_w += tl.load(PART_DW + offsets, mask, 0.)
            acc_b += tl.load(PART_DB + offsets, mask, 0.)
        tl.store(DW + col, tl.sum(acc_w, 0), col < N)
        tl.store(DB + col, tl.sum(acc_b, 0), col < N)


class _LayerNorm(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, weight, bias, eps):
        if triton is None or x.device.type != "cuda":
            raise RuntimeError("triton_ln requires CUDA and Triton")
        if x.ndim < 1 or x.numel() == 0:
            raise ValueError("triton_ln requires a nonempty input with a feature dimension")
        if x.shape[-1] != weight.numel() or weight.shape != bias.shape:
            raise ValueError("LayerNorm weight and bias must match the last input dimension")
        if x.device != weight.device or x.device != bias.device:
            raise ValueError("LayerNorm input, weight, and bias must share a device")
        n = x.shape[-1]
        if n < 1 or n > 8192:
            raise ValueError("triton_ln supports hidden sizes from 1 to 8192")
        xc = x.contiguous()
        m = xc.numel() // n
        y = torch.empty_like(xc)
        mean = torch.empty((m,), device=x.device, dtype=torch.float32)
        rstd = torch.empty_like(mean)
        block = triton.next_power_of_2(n)
        _forward[(m,)](xc, weight.contiguous(), bias.contiguous(), y, mean, rstd,
                       n, eps, block, num_warps=4)
        ctx.save_for_backward(xc, weight, mean, rstd)
        ctx.block = block
        return y.reshape(x.shape)

    @staticmethod
    def backward(ctx, grad_output):
        x, weight, mean, rstd = ctx.saved_tensors
        n = x.shape[-1]
        m = x.numel() // n
        groups = triton.cdiv(m, 4)
        dy = grad_output.contiguous()
        dx = torch.empty_like(x)
        partial_w = torch.empty((groups, n), device=x.device, dtype=torch.float32)
        partial_b = torch.empty_like(partial_w)
        dw = torch.empty_like(weight)
        db = torch.empty_like(weight)
        _backward_rows[(groups,)](x, dy, weight.contiguous(), mean, rstd, dx,
                                  partial_w, partial_b, m, n, ctx.block, 4,
                                  num_warps=4)
        _backward_params[(triton.cdiv(n, 32),)](partial_w, partial_b, dw, db,
                                                groups, n, 32, 32, num_warps=4)
        return dx, dw, db, None


class TritonLayerNorm(nn.LayerNorm):
    """Drop-in affine LayerNorm with the same state-dict keys as nn.LayerNorm."""

    def forward(self, input: torch.Tensor) -> torch.Tensor:
        if len(self.normalized_shape) != 1 or self.weight is None or self.bias is None:
            raise ValueError("triton_ln requires one normalized dimension and affine weight/bias")
        return _LayerNorm.apply(input, self.weight, self.bias, self.eps)


def layer_norm_triton(x: torch.Tensor, weight: torch.Tensor, bias: torch.Tensor,
                      eps: float = 1e-5) -> torch.Tensor:
    """Functional form for direct correctness checks and kernel experiments."""
    return _LayerNorm.apply(x, weight, bias, eps)
