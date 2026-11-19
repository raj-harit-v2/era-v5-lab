"""Half-split RoPE of q and k in one CUDA kernel each way (model.rope_impl=triton).

    y[i] = x[i] c - x[i + hd/2] s,   y[i + hd/2] = x[i + hd/2] c + x[i] s      (c, s of angle t * theta^(-2i/hd))
    backward: the same rotation by -angle

models.gpt.apply_rope is 3 kernels each way (x * cos, roll, addcmul). This reads the strided q|k view of the qkv
matmul output directly (no copy) and writes a contiguous [B, T, heads, hd] in x's dtype, fp32 math, the same
tables (rope_tables: cos = [c, c], sin = [-s, s]). Without CUDA or Triton, rope() is models.gpt.apply_rope.
"""
from __future__ import annotations

import torch
from torch.autograd.function import once_differentiable

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None


if triton is not None:
    @triton.jit(do_not_specialize=["T", "X0", "X1", "X2", "C0"])
    def _rotate(X, COS, SIN, Y, T, X0, X1, X2, C0, HEADS: tl.constexpr, HALF: tl.constexpr,
                BH: tl.constexpr, BD: tl.constexpr, SIGN: tl.constexpr):
        pid = tl.program_id(0).to(tl.int64)
        b, t = pid // T, pid % T
        h = tl.arange(0, BH).to(tl.int64)
        d = tl.arange(0, BD).to(tl.int64)
        mask = (h[:, None] < HEADS) & (d[None, :] < HALF)
        x = X + b * X0 + t * X1 + h[:, None] * X2 + d[None, :]
        x1 = tl.load(x, mask, 0.).to(tl.float32)
        x2 = tl.load(x + HALF, mask, 0.).to(tl.float32)
        c = tl.load(COS + t * C0 + d, d < HALF, 0.)[None, :]
        s = tl.load(SIN + t * C0 + HALF + d, d < HALF, 0.)[None, :]       # sin table second half = +sin
        y = Y + pid * (HEADS * 2 * HALF) + h[:, None] * (2 * HALF) + d[None, :]
        tl.store(y, x1 * c - SIGN * x2 * s, mask)
        tl.store(y + HALF, x2 * c + SIGN * x1 * s, mask)


def _launch(x, cos, sin, sign):
    B, T, heads, hd = x.shape
    if x.stride(-1) != 1:
        x = x.contiguous()
    y = torch.empty((B, T, heads, hd), device=x.device, dtype=x.dtype)
    with torch.cuda.device(x.device):
        _rotate[(B * T,)](x, cos, sin, y, T, x.stride(0), x.stride(1), x.stride(2), cos.stride(0),
                          heads, hd // 2, triton.next_power_of_2(heads), triton.next_power_of_2(hd // 2),
                          sign, num_warps=1 if heads * hd <= 1024 else 4)
    return y


class _Rope(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, cos, sin):
        ctx.save_for_backward(cos, sin)
        return _launch(x, cos, sin, 1.0)

    @staticmethod
    @once_differentiable
    def backward(ctx, g):
        cos, sin = ctx.saved_tensors
        return _launch(g, cos, sin, -1.0), None, None


def supported(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> bool:
    """x [B, T, heads, hd]; cos, sin [>= T, 1, hd] fp32 contiguous rows (GQAttention's buffers)."""
    return (triton is not None and x.device.type == "cuda" and x.ndim == 4 and x.shape[-1] % 2 == 0
            and x.numel() > 0 and x.dtype in (torch.float16, torch.bfloat16, torch.float32)
            and cos.dtype == sin.dtype == torch.float32 and cos.device == x.device
            and cos.ndim == 3 and cos.shape[1:] == (1, x.shape[-1]) and cos.shape[0] >= x.shape[1]
            and cos.stride() == sin.stride() and cos.stride(-1) == 1 and sin.shape == cos.shape)


def rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """Triton rotation where supported, else models.gpt.apply_rope. Without grad, no autograd.Function."""
    if not supported(x, cos, sin):
        from models.gpt import apply_rope
        return apply_rope(x, cos, sin)
    if torch.is_grad_enabled() and x.requires_grad:
        return _Rope.apply(x, cos, sin)
    return _launch(x, cos, sin, 1.0)
