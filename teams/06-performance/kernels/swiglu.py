"""SwiGLU activation h = SiLU(g) * u in one CUDA kernel each way (model.swiglu_impl=triton).

    forward   h = g * sigmoid(g) * u
    backward  dg = dh * u * sig * (1 + g * (1 - sig)),   du = dh * g * sig,   sig = sigmoid(g)

Torch runs SiLU, then the product (2 kernels, 3 saved tensors: g, SiLU(g), u); backward is about 5 kernels. Here
fp32 math, one rounding to the output dtype, 2 saved tensors. g and u may be row-strided views (the batched
experts chunk one [.., 2h] matmul into gate and up): any 2D-viewable layout with unit stride in the last dim.
Without CUDA or Triton, swiglu() is F.silu(g) * u.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch.autograd.function import once_differentiable

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None

BLOCK_ROWS, BLOCK_COLS = 4, 1024


if triton is not None:
    @triton.jit(do_not_specialize=["M", "N", "G0", "U0"])
    def _forward(G, U, H, M, N, G0, U0, BR: tl.constexpr, BC: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BR + tl.arange(0, BR).to(tl.int64)
        col = tl.program_id(1).to(tl.int64) * BC + tl.arange(0, BC).to(tl.int64)
        mask = (row[:, None] < M) & (col[None, :] < N)
        g = tl.load(G + row[:, None] * G0 + col[None, :], mask, 0.).to(tl.float32)
        u = tl.load(U + row[:, None] * U0 + col[None, :], mask, 0.).to(tl.float32)
        tl.store(H + row[:, None] * N + col[None, :], g * tl.sigmoid(g) * u, mask)

    @triton.jit(do_not_specialize=["M", "N", "G0", "U0", "D0"])
    def _backward(G, U, DH, DG, DU, M, N, G0, U0, D0, BR: tl.constexpr, BC: tl.constexpr,
                  NEED_G: tl.constexpr, NEED_U: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * BR + tl.arange(0, BR).to(tl.int64)
        col = tl.program_id(1).to(tl.int64) * BC + tl.arange(0, BC).to(tl.int64)
        mask = (row[:, None] < M) & (col[None, :] < N)
        g = tl.load(G + row[:, None] * G0 + col[None, :], mask, 0.).to(tl.float32)
        dh = tl.load(DH + row[:, None] * D0 + col[None, :], mask, 0.).to(tl.float32)
        sig = tl.sigmoid(g)
        off = row[:, None] * N + col[None, :]
        if NEED_G:
            u = tl.load(U + row[:, None] * U0 + col[None, :], mask, 0.).to(tl.float32)
            tl.store(DG + off, dh * u * sig * (1. + g * (1. - sig)), mask)
        if NEED_U:
            tl.store(DU + off, dh * g * sig, mask)


def _rows(t):
    """2D [M, N] view with unit last-dim stride (reshape copies only when no such view exists)."""
    t2 = t.reshape(-1, t.shape[-1])
    return t2 if t2.stride(-1) == 1 else t2.contiguous()


def _grid(m, n):
    return (triton.cdiv(m, BLOCK_ROWS), triton.cdiv(n, BLOCK_COLS))


def _launch_forward(g, u):
    g2, u2 = _rows(g), _rows(u)
    m, n = g2.shape
    h = torch.empty(g.shape, device=g.device, dtype=torch.result_type(g, u))
    with torch.cuda.device(g.device):
        _forward[_grid(m, n)](g2, u2, h, m, n, g2.stride(0), u2.stride(0), BLOCK_ROWS, BLOCK_COLS)
    return h


class _SwiGLU(torch.autograd.Function):
    @staticmethod
    def forward(ctx, g, u):
        ctx.save_for_backward(g, u)
        return _launch_forward(g, u)

    @staticmethod
    @once_differentiable
    def backward(ctx, dh):
        g, u = ctx.saved_tensors
        need_g, need_u = ctx.needs_input_grad[:2]
        g2, u2, d2 = _rows(g), _rows(u), _rows(dh)
        m, n = g2.shape
        dg = torch.empty(g.shape, device=g.device, dtype=g.dtype) if need_g else None
        du = torch.empty(u.shape, device=u.device, dtype=u.dtype) if need_u else None
        with torch.cuda.device(g.device):
            _backward[_grid(m, n)](g2, u2, d2, g2 if dg is None else dg, g2 if du is None else du, m, n,
                                   g2.stride(0), u2.stride(0), d2.stride(0), BLOCK_ROWS, BLOCK_COLS,
                                   need_g, need_u)
        return dg, du


def supported(g: torch.Tensor, u: torch.Tensor) -> bool:
    return (triton is not None and g.device.type == "cuda" and g.shape == u.shape and g.numel() > 0
            and g.device == u.device and g.dtype in (torch.float16, torch.bfloat16, torch.float32)
            and u.dtype in (torch.float16, torch.bfloat16, torch.float32))


def swiglu(g: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
    """SiLU(g) * u: the Triton kernel where supported, else torch. Without grad, no autograd.Function."""
    if not supported(g, u):
        return F.silu(g) * u
    if torch.is_grad_enabled() and (g.requires_grad or u.requires_grad):
        return _SwiGLU.apply(g, u)
    return _launch_forward(g, u)
