"""Memory-bounded linear cross-entropy implementations.

``linear_cross_entropy_fused`` processes token chunks, computes loss and head gradients while
each chunk is resident, and saves only dh/dW for backward. The vocabulary-streaming alternative
keeps per-token log-sum-exp and target logits and recomputes tiles in backward. These are pure
PyTorch custom-autograd implementations, not single custom CUDA kernels.

The two source-inspired entry points below map the algorithms in the upstream projects onto
portable PyTorch custom-autograd implementations:

* ``linear_cross_entropy_cce`` follows Apple's Cut Cross-Entropy strategy: stream vocabulary
  tiles, maintaining log-sum-exp and the target logit, then recompute tiles for backward.
* ``linear_cross_entropy_liger`` follows Liger's chunked linear-CE strategy: materialize one
  token chunk's logits, compute its loss and head gradients while resident, then save gradients.

These are correctness/reference implementations, not copies of the upstream Triton kernels.
See docs/LINEAR_CE.md for source links, algorithm mapping, and limitations.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch.autograd.function import once_differentiable


class _LinearCrossEntropy(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, weight, bias, targets, vocab_chunk: int, ignore_index: int):
        if x.ndim != 2 or weight.ndim != 2:
            raise ValueError("linear cross-entropy expects x [tokens, hidden] and weight [vocab, hidden]")
        if x.shape[1] != weight.shape[1]:
            raise ValueError(f"hidden sizes differ: {x.shape[1]} vs {weight.shape[1]}")
        if vocab_chunk <= 0:
            raise ValueError("vocab_chunk must be positive")
        targets = targets.reshape(-1).long()
        if targets.numel() != x.shape[0]:
            raise ValueError("target count must match the number of input rows")

        x32, w32 = x.float(), weight.float()
        n, vocab = x.shape[0], weight.shape[0]
        log_z = torch.full((n,), -torch.inf, dtype=torch.float32, device=x.device)
        target_logits = torch.zeros((n,), dtype=torch.float32, device=x.device)
        rows = torch.arange(n, device=x.device)
        valid = targets != ignore_index
        for start in range(0, vocab, vocab_chunk):
            end = min(start + vocab_chunk, vocab)
            logits = F.linear(x32, w32[start:end], None if bias is None else bias[start:end].float())
            log_z = torch.logaddexp(log_z, torch.logsumexp(logits, dim=-1))
            in_tile = valid & (targets >= start) & (targets < end)
            local = (targets - start).clamp(min=0, max=end - start - 1)
            selected = logits[rows, local]
            target_logits = torch.where(in_tile, selected, target_logits)

        count = valid.sum().clamp_min(1)
        losses = torch.where(valid, log_z - target_logits, torch.zeros_like(log_z))
        loss = losses.sum() / count
        saved_bias = x.new_empty((0,)) if bias is None else bias
        ctx.save_for_backward(x, weight, targets, log_z, valid, saved_bias, count)
        ctx.bias_is_none = bias is None
        ctx.vocab_chunk = vocab_chunk
        ctx.input_shape = x.shape
        return loss

    @staticmethod
    def backward(ctx, grad_output):
        x, weight, targets, log_z, valid, saved_bias, count = ctx.saved_tensors
        x32, w32 = x.float(), weight.float()
        n, vocab = x.shape[0], weight.shape[0]
        grad_x = torch.zeros_like(x32)
        grad_weight = torch.empty_like(w32)
        grad_bias = None if ctx.bias_is_none else torch.empty((vocab,), dtype=torch.float32, device=x.device)
        rows = torch.arange(n, device=x.device)
        scale = grad_output.float() / count

        for start in range(0, vocab, ctx.vocab_chunk):
            end = min(start + ctx.vocab_chunk, vocab)
            w_tile = w32[start:end]
            logits = F.linear(x32, w_tile)
            if not ctx.bias_is_none:
                logits = logits + saved_bias[start:end].float()
            probs = torch.exp(logits - log_z[:, None])
            probs.mul_(valid[:, None])
            in_tile = valid & (targets >= start) & (targets < end)
            local = (targets - start).clamp(min=0, max=end - start - 1)
            probs[rows, local] -= in_tile.to(probs.dtype)
            probs.mul_(scale)
            grad_x.add_(probs @ w_tile)
            grad_weight[start:end] = probs.T @ x32
            if grad_bias is not None:
                grad_bias[start:end] = probs.sum(dim=0)

        return grad_x.reshape(ctx.input_shape).to(x.dtype), grad_weight.to(weight.dtype), \
            None if grad_bias is None else grad_bias.to(saved_bias.dtype), None, None, None


def linear_cross_entropy(x, weight, targets, *, bias=None, vocab_chunk=4096, ignore_index=-100):
    """Mean CE for a bias-free or biased linear head, without materializing full logits.

    ``x`` is [tokens, hidden], ``weight`` is [vocabulary, hidden], and ``targets`` is [tokens].
    Ignored targets do not contribute to either the sum or divisor. All-ignored targets return
    zero with zero gradients, matching the existing chunked-loss behavior.
    """
    return _LinearCrossEntropy.apply(x, weight, bias, targets, int(vocab_chunk), int(ignore_index))


def linear_cross_entropy_cce(x, weight, targets, *, bias=None, vocab_chunk=4096, ignore_index=-100):
    """Apple CCE-style streamed-vocabulary PyTorch reference implementation."""
    return linear_cross_entropy(x, weight, targets, bias=bias, vocab_chunk=vocab_chunk,
                                ignore_index=ignore_index)


class _CachedGradientLinearCrossEntropy(torch.autograd.Function):
    """Token-chunked CE that computes the linear-head gradients while logits are resident.

    This moves the head backward work into forward. The saved state is the resulting input/weight
    gradients (plus bias gradient when needed), rather than inputs and logits for recomputation.
    It is a memory/performance trade-off: the weight-gradient buffer is the size of the head.
    """

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
    """Task-5 fused CE: split tokens into at most ``chunks`` pieces and cache head gradients.

    ``chunks`` need not divide the token count and may exceed it. Logits use the native input
    dtype (or the enclosing autocast dtype); CE reductions and gradient buffers use fp32.
    Only dh/dW (and db when a bias is supplied) are saved for the first-order backward.
    """
    if chunks <= 0:
        raise ValueError("chunks must be positive")
    token_chunk = max(1, (x.shape[0] + chunks - 1) // chunks)
    return linear_cross_entropy_cached(x, weight, targets, bias=bias, token_chunk=token_chunk,
                                       ignore_index=ignore_index)


def linear_cross_entropy_cached(x, weight, targets, *, bias=None, token_chunk=16, ignore_index=-100):
    """Token-chunked linear CE that caches head gradients to avoid recomputing logits in backward.

    Unlike :func:`linear_cross_entropy`, this computes ``dh`` and ``dW`` in forward and saves them
    for autograd's backward. ``token_chunk`` bounds the temporary ``[token_chunk, vocab]`` logits;
    the cached ``dW`` is a full-size head-gradient buffer, so benchmark its memory cost as well as time.
    """
    return _CachedGradientLinearCrossEntropy.apply(
        x, weight, bias, targets, int(token_chunk), int(ignore_index)
    )


def linear_cross_entropy_liger(x, weight, targets, *, bias=None, token_chunk=16, ignore_index=-100):
    """Liger-style token-chunked PyTorch reference with gradients cached in forward."""
    return linear_cross_entropy_cached(x, weight, targets, bias=bias, token_chunk=token_chunk,
                                       ignore_index=ignore_index)
