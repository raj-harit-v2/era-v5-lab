# Official sources: https://github.com/linkedin/Liger-Kernel
#                  https://github.com/apple/ml-cross-entropy
"""Portable cached-gradient CE and lazy adapters to the official Triton backends.

  linear_cross_entropy_fused           portable cached-gradient token chunks
  linear_cross_entropy_cached          internal fixed-token-tile primitive
  linear_cross_entropy_liger / _cce    official Triton kernels (CUDA only)

Official sources and required helpers are consolidated in kernels/triton_liger.py
and kernels/triton_cce.py. They are imported only when selected.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch.autograd.function import once_differentiable


class _CachedGradientLinearCrossEntropy(torch.autograd.Function):
    """Token-chunked CE that computes the head gradients in forward while the logits are live, and saves only those.
    The weight-gradient buffer is the size of the head: measure memory as well as time."""

    @staticmethod
    def forward(ctx, x, weight, bias, targets, token_chunk: int, ignore_index: int):
        if x.ndim != 2 or weight.ndim != 2:
            raise ValueError("linear cross-entropy expects x [tokens, hidden] and weight [vocab, hidden]")
        if x.shape[1] != weight.shape[1]:
            raise ValueError(f"hidden sizes differ: {x.shape[1]} vs {weight.shape[1]}")
        if token_chunk <= 0:
            raise ValueError("token_chunk must be positive")
        if targets.dtype != torch.long:
            raise TypeError("linear cross-entropy targets must have dtype torch.long")
        if not x.is_floating_point() or not weight.is_floating_point():
            raise TypeError("linear cross-entropy inputs and weights must be floating point")
        targets = targets.reshape(-1)
        if targets.numel() != x.shape[0]:
            raise ValueError("target count must match the number of input rows")

        # Respect native bf16/fp16 tensors and the enclosing training autocast context. Only
        # the head matmul uses this dtype; reductions and gradient accumulation stay fp32.
        compute_dtype = (torch.get_autocast_dtype(x.device.type)
                         if torch.is_autocast_enabled(x.device.type)
                         else torch.promote_types(x.dtype, weight.dtype))
        with torch.autocast(device_type=x.device.type, enabled=False):
            return _CachedGradientLinearCrossEntropy._forward(
                ctx, x, weight, bias, targets, token_chunk, ignore_index, compute_dtype)

    @staticmethod
    def _forward(ctx, x, weight, bias, y, token_chunk, ignore_index, compute_dtype):
        xc_all, wc = x.to(compute_dtype), weight.to(compute_dtype)
        bc = None if bias is None else bias.to(compute_dtype)
        w32 = None if compute_dtype == torch.bfloat16 else wc.float()
        n = x.shape[0]
        valid = y != ignore_index
        count = valid.sum().clamp_min(1)
        grad_x = torch.zeros(x.shape, dtype=torch.float32, device=x.device)
        grad_weight = torch.zeros(weight.shape, dtype=torch.float32, device=weight.device)
        grad_bias = None if bias is None else torch.zeros_like(bias, dtype=torch.float32)
        loss_sum = torch.zeros((), dtype=torch.float32, device=x.device)

        for start in range(0, n, token_chunk):
            end = min(start + token_chunk, n)
            xc, yc = xc_all[start:end], y[start:end]
            keep = valid[start:end]
            logits = F.linear(xc_all[start:end], wc, bc).float()
            log_z = torch.logsumexp(logits, dim=-1)
            # Only ignored labels are replaced. Invalid non-ignored labels must raise
            # rather than being silently clamped into the vocabulary.
            safe_y = torch.where(keep, yc, 0)
            target_logit = logits.gather(1, safe_y[:, None]).squeeze(1)
            loss_sum += torch.where(keep, log_z - target_logit, 0.0).sum()

            # Reuse the logits storage for dlogits; no chunk logits survive this iteration.
            probabilities = logits.sub_(log_z[:, None]).exp_()
            probabilities.mul_(keep[:, None])
            probabilities[torch.arange(end - start, device=x.device), safe_y] -= keep.to(probabilities.dtype)
            probabilities.div_(count)
            # A bf16 forward should also use bf16 matmuls for the two expensive
            # gradient products (tensor cores on supported CUDA GPUs). Accumulate
            # their results in fp32. fp16
            # keeps fp32 products because its small softmax gradients can underflow
            # before the external GradScaler multiplies the returned gradients.
            if compute_dtype == torch.bfloat16:
                grad_logits = probabilities.to(torch.bfloat16)
                grad_x[start:end] = (grad_logits @ wc).float()
                grad_weight.add_((grad_logits.T @ xc).float())
            else:
                grad_x[start:end] = probabilities @ w32
                grad_weight.add_(probabilities.T @ xc.float())
            if grad_bias is not None:
                grad_bias.add_(probabilities.sum(dim=0))
            del logits, probabilities

        if grad_bias is None:
            ctx.save_for_backward(grad_x, grad_weight)
        else:
            ctx.save_for_backward(grad_x, grad_weight, grad_bias)
        ctx.bias_is_none = bias is None
        ctx.x_dtype, ctx.weight_dtype = x.dtype, weight.dtype
        ctx.bias_dtype = None if bias is None else bias.dtype
        return loss_sum / count

    @staticmethod
    @once_differentiable
    def backward(ctx, grad_output):
        grad_x, grad_weight = ctx.saved_tensors[:2]
        grad_bias = None if ctx.bias_is_none else ctx.saved_tensors[2]
        scale = grad_output.float()
        return (grad_x.mul(scale).to(ctx.x_dtype), grad_weight.mul(scale).to(ctx.weight_dtype),
                None if ctx.bias_is_none else grad_bias.mul(scale).to(ctx.bias_dtype),
                None, None, None)


def linear_cross_entropy_fused(x, weight, targets, *, bias=None, chunks=8, ignore_index=-100):
    """Fused CE (ce_impl=fused): tokens in at most `chunks` pieces (need not divide), head gradients cached.
    Logits in the input or autocast dtype; reductions and gradient buffers in fp32."""
    if chunks <= 0:
        raise ValueError("chunks must be positive")
    token_chunk = max(1, (x.shape[0] + chunks - 1) // chunks)     # ceil(tokens / chunks)
    return linear_cross_entropy_cached(x, weight, targets, bias=bias, token_chunk=token_chunk,
                                       ignore_index=ignore_index)


def linear_cross_entropy_cached(x, weight, targets, *, bias=None, token_chunk=16, ignore_index=-100):
    """Portable cached-gradient CE with `token_chunk` rows of logits per tile."""
    return _CachedGradientLinearCrossEntropy.apply(
        x, weight, bias, targets, int(token_chunk), int(ignore_index)
    )


def linear_cross_entropy_liger(x, weight, targets, *, bias=None, ignore_index=-100):
    """Official Liger Triton CE. No CPU fallback."""
    if x.device.type != "cuda":
        raise ValueError("triton_liger requires CUDA and Triton; use fused on CPU")
    from kernels.triton_liger import linear_cross_entropy_liger as official
    return official(x, weight, targets, bias=bias, ignore_index=ignore_index)


def linear_cross_entropy_cce(x, weight, targets, *, bias=None, ignore_index=-100):
    """Official Apple CCE, without gradient filtering. No CPU fallback."""
    if x.device.type != "cuda":
        raise ValueError("triton_cce requires CUDA and Triton; use fused on CPU")
    from kernels.triton_cce import linear_cross_entropy_cce as official
    return official(x, weight, targets, bias=bias, ignore_index=ignore_index)
