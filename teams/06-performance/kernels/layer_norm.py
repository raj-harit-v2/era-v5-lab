"""CUDA LayerNorm with bounded, deterministic parameter-gradient scratch.

Equations: https://triton-lang.org/main/getting-started/tutorials/05-layer-norm.html
The module falls back to nn.LayerNorm; the functional API is strict.
"""
from __future__ import annotations

from functools import lru_cache

import torch
from torch import nn
from torch.autograd.function import once_differentiable
from perfkit.regions import region

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None

DTYPES = (torch.float16, torch.bfloat16, torch.float32)
MAX_FEATURES = 8192


def launch_config(n: int) -> tuple[int, int, int]:
    """(width, rows per program, warps); heuristic, not an autotuned result."""
    block = 1 << (n - 1).bit_length()
    return block, 4 if n <= 1024 else 1, min(max(block // 256, 1), 8)


@torch.compiler.assume_constant_result
@lru_cache(maxsize=None)
def _sm_count(index: int) -> int:
    # Device index is fixed for each compiled graph. This query does not sync.
    return torch.cuda.get_device_properties(index).multi_processor_count


def backward_groups(m: int, rows: int, sms: int) -> int:
    return min((m + rows - 1) // rows, sms * 4)


def _support_reason(device, dtype, normalized_shape, weight, bias):
    if triton is None:
        return "triton_unavailable"
    if device.type != "cuda":
        return "non_cuda_device"
    if len(normalized_shape) != 1:
        return "multiple_normalized_dimensions"
    if weight is None or bias is None:
        return "affine_weight_and_bias_required"
    if not 1 <= normalized_shape[0] <= MAX_FEATURES:
        return "unsupported_hidden_size"
    if dtype not in DTYPES or weight.dtype not in DTYPES or bias.dtype not in DTYPES:
        return "unsupported_dtype"
    if weight.device != device or bias.device != device:
        return "parameter_device_mismatch"
    if not torch.is_autocast_enabled("cuda") and (weight.dtype != bias.dtype or
            (dtype != weight.dtype and not (dtype in (torch.float16, torch.bfloat16)
                                           and weight.dtype == torch.float32))):
        return "unsupported_parameter_dtype_combination"
    return None


if triton is not None:
    @triton.jit
    def _offset(row, col, N: tl.constexpr):
        return row.to(tl.int64) * N + col.to(tl.int64)

    @triton.jit(do_not_specialize=["M"])
    def _forward(X, W, B, Y, MEAN, RSTD, M, N: tl.constexpr,
                 EPS: tl.constexpr, BLOCK: tl.constexpr, ROWS: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * ROWS + tl.arange(0, ROWS).to(tl.int64)
        col = tl.arange(0, BLOCK)
        mask = (row[:, None] < M) & (col[None, :] < N)
        x = tl.load(X + _offset(row[:, None], col[None, :], N), mask, 0.,
                    eviction_policy="evict_first").to(tl.float32)
        mean = tl.sum(x, 1) / N
        centered = tl.where(col[None, :] < N, x - mean[:, None], 0.)
        var = tl.sum(centered * centered, 1) / N
        rstd = tl.rsqrt(var + EPS)
        w = tl.load(W + col, col < N, 0., eviction_policy="evict_last").to(tl.float32)
        b = tl.load(B + col, col < N, 0., eviction_policy="evict_last").to(tl.float32)
        y = centered * rstd[:, None] * w[None, :] + b[None, :]
        tl.store(Y + _offset(row[:, None], col[None, :], N), y, mask)
        tl.store(MEAN + row, mean, row < M)
        tl.store(RSTD + row, rstd, row < M)

    @triton.jit(do_not_specialize=["M", "GROUPS"])
    def _backward_rows(X, DY, W, MEAN, RSTD, DX, PART_DW, PART_DB, M, GROUPS,
                       N: tl.constexpr, BLOCK: tl.constexpr, ROWS: tl.constexpr,
                       NEED_DX: tl.constexpr, NEED_DW: tl.constexpr, NEED_DB: tl.constexpr):
        group = tl.program_id(0).to(tl.int64)
        offsets = tl.arange(0, ROWS).to(tl.int64)
        col = tl.arange(0, BLOCK)
        if NEED_DX:
            w = tl.load(W + col, col < N, 0., eviction_policy="evict_last").to(tl.float32)
        acc_w = tl.full((ROWS, BLOCK), 0., tl.float32)
        acc_b = tl.full((ROWS, BLOCK), 0., tl.float32)
        stride = GROUPS.to(tl.int64) * ROWS
        for tile in range(tl.cdiv(M.to(tl.int64), stride)):
            row = group * ROWS + tile.to(tl.int64) * stride + offsets
            mask = (row[:, None] < M) & (col[None, :] < N)
            dy = tl.load(DY + _offset(row[:, None], col[None, :], N), mask, 0.,
                         eviction_policy="evict_first").to(tl.float32)
            if NEED_DX or NEED_DW:
                x = tl.load(X + _offset(row[:, None], col[None, :], N), mask, 0.,
                            eviction_policy="evict_first").to(tl.float32)
                mean = tl.load(MEAN + row, row < M, 0.)
                rstd = tl.load(RSTD + row, row < M, 0.)
                xhat = tl.where(mask, (x - mean[:, None]) * rstd[:, None], 0.)
            if NEED_DX:
                wdy = dy * w[None, :]
                c1 = tl.sum(xhat * wdy, 1) / N
                c2 = tl.sum(wdy, 1) / N
                dx = (wdy - xhat * c1[:, None] - c2[:, None]) * rstd[:, None]
                tl.store(DX + _offset(row[:, None], col[None, :], N), dx, mask)
            if NEED_DW:
                acc_w += dy * xhat
            if NEED_DB:
                acc_b += dy
        if NEED_DW:
            tl.store(PART_DW + _offset(group, col, N), tl.sum(acc_w, 0), col < N)
        if NEED_DB:
            tl.store(PART_DB + _offset(group, col, N), tl.sum(acc_b, 0), col < N)

    @triton.jit(do_not_specialize=["GROUPS"])
    def _backward_params(PART_DW, PART_DB, DW, DB, GROUPS, N: tl.constexpr,
                         ROWS: tl.constexpr, COLS: tl.constexpr,
                         NEED_DW: tl.constexpr, NEED_DB: tl.constexpr):
        col = tl.program_id(0).to(tl.int64) * COLS + tl.arange(0, COLS)
        r = tl.arange(0, ROWS).to(tl.int64)
        acc_w = tl.full((ROWS, COLS), 0., tl.float32)
        acc_b = tl.full((ROWS, COLS), 0., tl.float32)
        for start in range(tl.cdiv(GROUPS, ROWS)):
            row = start.to(tl.int64) * ROWS + r
            offsets = _offset(row[:, None], col[None, :], N)
            mask = (row[:, None] < GROUPS) & (col[None, :] < N)
            if NEED_DW:
                acc_w += tl.load(PART_DW + offsets, mask, 0.)
            if NEED_DB:
                acc_b += tl.load(PART_DB + offsets, mask, 0.)
        if NEED_DW:
            tl.store(DW + col, tl.sum(acc_w, 0), col < N)
        if NEED_DB:
            tl.store(DB + col, tl.sum(acc_b, 0), col < N)


class _LayerNorm(torch.autograd.Function):
    @staticmethod
    @torch.amp.custom_fwd(device_type="cuda", cast_inputs=torch.float32)
    def forward(ctx, x, weight, bias, eps):
        reason = _support_reason(x.device, x.dtype, weight.shape, weight, bias)
        if reason is not None:
            raise ValueError(f"triton_ln cannot handle this input: {reason}")
        if x.ndim < 1 or x.numel() == 0 or weight.ndim != 1 or bias.ndim != 1:
            raise ValueError("triton_ln requires nonempty input and 1D affine parameters")
        if x.shape[-1] != weight.numel() or weight.shape != bias.shape:
            raise ValueError("LayerNorm parameters must match the last input dimension")
        if x.device != weight.device or x.device != bias.device:
            raise ValueError("LayerNorm input and parameters must share a device")
        if weight.dtype != bias.dtype or (x.dtype != weight.dtype and
                not (x.dtype in (torch.float16, torch.bfloat16) and weight.dtype == torch.float32)):
            raise ValueError("unsupported LayerNorm input/parameter dtype combination")
        n = x.shape[-1]
        xc, wc, bc = x.contiguous(), weight.contiguous(), bias.contiguous()
        m = xc.numel() // n
        block, rows, warps = launch_config(n)
        with torch.cuda.device(x.device):
            groups = backward_groups(m, rows, _sm_count(x.device.index))
            y = torch.empty_like(xc)
            mean = torch.empty((m,), device=x.device, dtype=torch.float32)
            rstd = torch.empty_like(mean)
            _forward[(triton.cdiv(m, rows),)](xc, wc, bc, y, mean, rstd, m,
                                              n, eps, block, rows, num_warps=warps)
        ctx.save_for_backward(xc, wc, mean, rstd)
        ctx.geometry = (block, rows, warps, groups)
        ctx.bias_dtype = bias.dtype
        return y

    @staticmethod
    @torch.amp.custom_bwd(device_type="cuda")
    @once_differentiable
    def backward(ctx, grad_output):
        x, weight, mean, rstd = ctx.saved_tensors
        n, m = x.shape[-1], x.numel() // x.shape[-1]
        block, rows, warps, groups = ctx.geometry
        need_x, need_w, need_b = ctx.needs_input_grad[:3]
        with torch.cuda.device(x.device):
            dy = grad_output.contiguous()
            dx = torch.empty_like(x) if need_x else x
            partial_w = torch.empty((groups, n), device=x.device, dtype=torch.float32) if need_w else x
            partial_b = torch.empty((groups, n), device=x.device, dtype=torch.float32) if need_b else x
            dw = torch.empty_like(weight) if need_w else weight
            db = torch.empty_like(weight, dtype=ctx.bias_dtype) if need_b else weight

            def rows_kernel():
                _backward_rows[(groups,)](x, dy, weight, mean, rstd, dx, partial_w, partial_b,
                                          m, groups, n, block, rows, need_x, need_w, need_b,
                                          num_warps=warps)

            def params_kernel():
                _backward_params[(triton.cdiv(n, 32),)](partial_w, partial_b, dw, db, groups,
                                                        n, 32, 32, need_w, need_b, num_warps=4)

            if torch.compiler.is_compiling():
                rows_kernel()
                if need_w or need_b:
                    params_kernel()
            else:
                with region("ln.triton.rows", 3):
                    rows_kernel()
                if need_w or need_b:
                    with region("ln.triton.params", 3):
                        params_kernel()
        return dx if need_x else None, dw if need_w else None, db if need_b else None, None


class TritonLayerNorm(nn.LayerNorm):
    """nn.LayerNorm-compatible module with an explicit, inspectable fallback."""

    def backend_info(self, device, dtype) -> dict:
        reason = _support_reason(device, dtype, self.normalized_shape, self.weight, self.bias)
        return {"backend": "triton_ln" if reason is None else "torch_ln", "reason": reason}

    def forward(self, input: torch.Tensor) -> torch.Tensor:
        if self.backend_info(input.device, input.dtype)["backend"] != "triton_ln" or input.numel() == 0:
            return super().forward(input)
        return layer_norm_triton(input, self.weight, self.bias, self.eps)


def layer_norm_triton(x: torch.Tensor, weight: torch.Tensor, bias: torch.Tensor,
                      eps: float = 1e-5) -> torch.Tensor:
    """Strict functional API; module fallback is provided by TritonLayerNorm."""
    return _LayerNorm.apply(x, weight, bias, eps)


def layer_norm_backend_report(model: nn.Module) -> list[dict]:
    """Resolve backends at setup, without a forward call or module mutation."""
    entries = []
    for name, module in model.named_modules():
        if isinstance(module, nn.LayerNorm):
            param = next(module.parameters(), None)
            if param is None:
                param = next(model.parameters(), torch.empty(0))
            info = module.backend_info(param.device, param.dtype) if isinstance(module, TritonLayerNorm) else {
                "backend": "torch_ln", "reason": None}
            entries.append({"module": name, **info})
    return entries
