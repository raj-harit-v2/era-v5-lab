"""CUDA RMSNorm (G5 form, models/norm.py) with an optional residual add in the same kernel.

    s = x (+ r),   y = s * rstd * w,   rstd = 1 / sqrt(mean(s^2) + eps)       (fp32 math, y in s's dtype)
    ds = rstd * (w dy - xhat * mean(xhat * w dy)),   dw = sum_rows(dy * xhat),   xhat = s * rstd

x + r is rounded to its torch dtype before the norm, as `x + r` would be. With r, forward writes s for the
backward (the add's output a plain add would write anyway) and the norm in one launch; ds is the gradient of
both x and r. dw is reduced in two deterministic passes (the LayerNorm kernel's partial sums, no atomics).
The module falls back to models.norm.RMSNorm; the functional API is strict.
"""
from __future__ import annotations

import torch
from torch.autograd.function import once_differentiable

from kernels.layer_norm import DTYPES, MAX_FEATURES, _sm_count, backward_groups, launch_config
from models.norm import RMSNorm
from perfkit.regions import region

try:
    import triton
    import triton.language as tl
    from kernels.layer_norm import _backward_params
except ImportError:
    triton = None
    tl = None


def _support_reason(device, dtype, width, weight, residual_dtype=None):
    if triton is None:
        return "triton_unavailable"
    if device.type != "cuda":
        return "non_cuda_device"
    if not 1 <= width <= MAX_FEATURES:
        return "unsupported_hidden_size"
    if dtype not in DTYPES or weight.dtype not in DTYPES or (residual_dtype is not None
                                                             and residual_dtype not in DTYPES):
        return "unsupported_dtype"
    if weight.device != device:
        return "parameter_device_mismatch"
    return None


if triton is not None:
    @triton.jit
    def _offset(row, col, N: tl.constexpr):
        return row.to(tl.int64) * N + col.to(tl.int64)

    @triton.jit(do_not_specialize=["M"])
    def _forward(X, R, S, Y, W, RSTD, M, N: tl.constexpr, EPS: tl.constexpr,
                 BLOCK: tl.constexpr, ROWS: tl.constexpr,
                 HAS_R: tl.constexpr, STORE_S: tl.constexpr, STORE_RSTD: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * ROWS + tl.arange(0, ROWS).to(tl.int64)
        col = tl.arange(0, BLOCK)
        mask = (row[:, None] < M) & (col[None, :] < N)
        off = _offset(row[:, None], col[None, :], N)
        s = tl.load(X + off, mask, 0., eviction_policy="evict_first").to(tl.float32)
        if HAS_R:
            r = tl.load(R + off, mask, 0., eviction_policy="evict_first").to(tl.float32)
            s = (s + r).to(S.dtype.element_ty).to(tl.float32)     # the rounding of torch's x + r
            if STORE_S:
                tl.store(S + off, s, mask)
        rstd = tl.rsqrt(tl.sum(s * s, 1) / N + EPS)
        w = tl.load(W + col, col < N, 0., eviction_policy="evict_last").to(tl.float32)
        tl.store(Y + off, s * rstd[:, None] * w[None, :], mask)
        if STORE_RSTD:
            tl.store(RSTD + row, rstd, row < M)

    @triton.jit(do_not_specialize=["M", "GROUPS"])
    def _backward_rows(S, DY, W, RSTD, DS, PART_DW, M, GROUPS, N: tl.constexpr,
                       BLOCK: tl.constexpr, ROWS: tl.constexpr,
                       NEED_DS: tl.constexpr, NEED_DW: tl.constexpr):
        group = tl.program_id(0).to(tl.int64)
        offsets = tl.arange(0, ROWS).to(tl.int64)
        col = tl.arange(0, BLOCK)
        w = tl.load(W + col, col < N, 0., eviction_policy="evict_last").to(tl.float32)
        acc_w = tl.full((BLOCK,), 0., tl.float32)
        stride = GROUPS.to(tl.int64) * ROWS
        for tile in range(tl.cdiv(M.to(tl.int64), stride)):
            row = group * ROWS + tile.to(tl.int64) * stride + offsets
            mask = (row[:, None] < M) & (col[None, :] < N)
            off = _offset(row[:, None], col[None, :], N)
            dy = tl.load(DY + off, mask, 0., eviction_policy="evict_first").to(tl.float32)
            s = tl.load(S + off, mask, 0., eviction_policy="evict_first").to(tl.float32)
            rstd = tl.load(RSTD + row, row < M, 0.)
            xhat = s * rstd[:, None]
            if NEED_DS:
                wdy = dy * w[None, :]
                c = tl.sum(xhat * wdy, 1) / N
                tl.store(DS + off, (wdy - xhat * c[:, None]) * rstd[:, None], mask)
            if NEED_DW:
                acc_w += tl.sum(dy * xhat, 0)
        if NEED_DW:
            tl.store(PART_DW + _offset(group, col, N), acc_w, col < N)


def _check(x, residual, weight):
    reason = _support_reason(x.device, x.dtype, weight.numel(), weight,
                             None if residual is None else residual.dtype)
    if reason is not None:
        raise ValueError(f"triton rms_norm cannot handle this input: {reason}")
    if x.ndim < 1 or x.numel() == 0 or weight.ndim != 1 or x.shape[-1] != weight.numel():
        raise ValueError("triton rms_norm requires a nonempty input normalized along its last dimension "
                         "and a 1D weight of matching width")
    if residual is not None and (residual.shape != x.shape or residual.device != x.device):
        raise ValueError("residual must have the input's shape and device (no broadcasting)")


def _launch_forward(x, residual, weight, eps, save):
    """(y, s, rstd); s and rstd are None unless save (the backward needs them)."""
    n = x.shape[-1]
    xc, wc = x.contiguous(), weight.contiguous()
    rc = None if residual is None else residual.contiguous()
    m = xc.numel() // n
    sum_dtype = x.dtype if rc is None else torch.result_type(x, residual)
    block, rows, warps = launch_config(n)
    with torch.cuda.device(x.device):
        y = torch.empty(xc.shape, device=x.device, dtype=sum_dtype)
        s = torch.empty_like(y) if (save and rc is not None) else (y if rc is not None else xc)
        rstd = torch.empty((m,), device=x.device, dtype=torch.float32) if save else y
        _forward[(triton.cdiv(m, rows),)](xc, xc if rc is None else rc, s, y, wc, rstd, m, n, eps,
                                          block, rows, rc is not None, save and rc is not None, save,
                                          num_warps=warps)
    return y, (s if save else None), (rstd if save else None)


class _RMSNorm(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, residual, weight, eps):
        _check(x, residual, weight)
        y, s, rstd = _launch_forward(x, residual, weight, eps, save=True)
        n = x.shape[-1]
        block, rows, warps = launch_config(n)
        ctx.save_for_backward(s, weight, rstd)
        ctx.geometry = (block, rows, warps, backward_groups(s.numel() // n, rows, _sm_count(x.device.index)))
        ctx.dtypes = (x.dtype, None if residual is None else residual.dtype)
        return y

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_output):
        s, weight, rstd = ctx.saved_tensors
        n, m = s.shape[-1], s.numel() // s.shape[-1]
        block, rows, warps, groups = ctx.geometry
        need_x, need_r, need_w = ctx.needs_input_grad[:3]
        need_s = need_x or need_r
        with torch.cuda.device(s.device):
            dy = grad_output.contiguous()
            ds = torch.empty_like(s) if need_s else s
            partial_w = torch.empty((groups, n), device=s.device, dtype=torch.float32) if need_w else s
            dw = torch.empty_like(weight) if need_w else weight

            def rows_kernel():
                _backward_rows[(groups,)](s, dy, weight, rstd, ds, partial_w, m, groups, n, block, rows,
                                          need_s, need_w, num_warps=warps)

            def params_kernel():
                _backward_params[(triton.cdiv(n, 32),)](partial_w, partial_w, dw, dw, groups, n, 32, 32,
                                                        True, False, num_warps=4)

            if torch.compiler.is_compiling():
                rows_kernel()
                if need_w:
                    params_kernel()
            else:
                with region("rms.triton.rows", 3):
                    rows_kernel()
                if need_w:
                    with region("rms.triton.params", 3):
                        params_kernel()
        x_dtype, r_dtype = ctx.dtypes
        dx = ds.to(x_dtype) if need_x else None
        dr = ds.to(r_dtype) if need_r else None      # the same tensor when the dtypes match, as add's backward
        return dx, dr, dw if need_w else None, None


def rms_norm_triton(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-5,
                    residual: torch.Tensor | None = None) -> torch.Tensor:
    """Strict functional API: RMSNorm(x + residual). Without grad, no autograd.Function (host cost per call)."""
    if torch.is_grad_enabled() and (x.requires_grad or weight.requires_grad
                                    or (residual is not None and residual.requires_grad)):
        return _RMSNorm.apply(x, residual, weight, eps)
    _check(x, residual, weight)
    return _launch_forward(x, residual, weight, eps, save=False)[0]


class TritonRMSNorm(RMSNorm):
    """models.norm.RMSNorm-compatible module with an explicit, inspectable fallback."""

    def backend_info(self, device, dtype, residual_dtype=None) -> dict:
        reason = _support_reason(device, dtype, self.weight.numel(), self.weight, residual_dtype)
        return {"backend": "triton_ln" if reason is None else "torch_ln", "reason": reason}

    def forward(self, x: torch.Tensor, residual: torch.Tensor | None = None) -> torch.Tensor:
        if (x.ndim < 1 or x.numel() == 0 or x.shape[-1] != self.weight.numel()
                or (residual is not None and residual.shape != x.shape)
                or self.backend_info(x.device, x.dtype,
                                     None if residual is None else residual.dtype)["backend"] != "triton_ln"):
            return super().forward(x, residual)
        return rms_norm_triton(x, self.weight, self.eps, residual)
