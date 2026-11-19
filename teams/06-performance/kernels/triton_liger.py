# Official repository: https://github.com/linkedin/Liger-Kernel
# Pinned revision: 44a8f2fb40cd90269b84818cd9ca0d981e88b148
# Source: src/liger_kernel/ops/cross_entropy.py
# Kernel body retained verbatim; host wrapper adapted to this repo's API.
# Upstream license (retained in full):
# BSD 2-CLAUSE LICENSE
# Copyright 2024 LinkedIn Corporation
# All Rights Reserved.
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided
# with the distribution.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import torch
import triton
import triton.language as tl

try:
    from triton.language.extra.libdevice import tanh
except ModuleNotFoundError:
    try:
        from triton.language.extra.cuda.libdevice import tanh
    except ModuleNotFoundError:
        from triton.language.math import tanh


@triton.jit
def liger_cross_entropy_kernel(
    X_ptr,
    X_stride,
    Y_ptr,
    Y_stride,
    weight_ptr,
    loss_ptr,
    z_loss_ptr,
    loss_stride,
    n_cols,
    n_non_ignore,
    sum_non_ignore_weight,
    weight_sum,
    ignore_index,
    lse_square_scale: tl.constexpr,
    label_smoothing: tl.constexpr,
    reduction: tl.constexpr,  # set it as constexpr since reduction is always known at compile time
    softcap,
    RETURN_Z_LOSS: tl.constexpr,
    BLOCK_SIZE: tl.constexpr,
    HAS_WEIGHT: tl.constexpr,
    HAS_SOFTCAPPING: tl.constexpr,
):
    """
    This kernel computes both cross entropy loss and the gradient of the input.
    We only consider hard label + mean reduction for now. Please refer to https://pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html for the math.

    Parameters:
    X_ptr: Pointer to input tensor.
    X_stride (int): The stride of the input tensor.
    Y_ptr: Pointer to target tensor.
    Y_stride (int): The stride of the target tensor.
    weight_ptr: Pointer to weight tensor.
    loss_ptr: Pointer to tensor to store the loss.
    z_loss_ptr: Pointer to tensor to store the z loss. No operation if RETURN_Z_LOSS is 0.
    loss_stride (int): The stride of the loss tensor.
    n_cols (int): The number of columns in the input tensor.
    n_non_ignore (float): The number of non-ignored elements in the batch.
    sum_non_ignore_weight (float): The sum of non-ignored target's weights in the batch.
    weight_sum (float): The sum of weight tensor.
    ignore_index (int): The index to ignore in the target.
    label_smoothing (float): The amount of smoothing when computing the loss, where 0.0 means no smoothing.
    lse_square_scale (float): The scaler of (logsumexp(_input)) ^ 2 adding to the loss for the stability of training.
    reduction (str): The string for the reduction to apply
    softcap (float): The upper threshold for scaling logits to the range (-softcap, +softcap).
    RETURN_Z_LOSS (int): The boolean value to decide whether storing z loss to z_loss_ptr or not. It must be 0 or 1.
    BLOCK_SIZE (int): The block size for Triton operations.
    HAS_WEIGHT (bool): The boolean value to determine whether assigning weight to each of the classes.
    HAS_SOFTCAPPING (bool): The boolean value to determine whether applying soft-capping or not.
    """

    # https://github.com/triton-lang/triton/issues/1058
    # If B*T*V is too large, program_id * stride will overflow out of int32, so we convert to int64
    program_id = tl.program_id(0).to(tl.int64)

    # 1. Load Y_ptr first because if the target is ignore_index, we can return right away
    Y_ptr += program_id * Y_stride
    y = tl.load(Y_ptr)

    # 2. locate the start index
    X_ptr += program_id * X_stride

    if y == ignore_index:
        # set all X_ptr as 0
        for i in range(0, n_cols, BLOCK_SIZE):
            X_offsets = i + tl.arange(0, BLOCK_SIZE)
            tl.store(X_ptr + X_offsets, 0.0, mask=X_offsets < n_cols)
        return

    loss_ptr += program_id * loss_stride
    if RETURN_Z_LOSS:
        z_loss_ptr += program_id * loss_stride

    if HAS_WEIGHT:
        weight_y = tl.load(weight_ptr + y).cast(tl.float32)

    # Online softmax: 2 loads + 1 store (compared with 3 loads + 1 store for the safe softmax)
    # Refer to Algorithm 3 in the paper: https://arxiv.org/pdf/1805.02867

    # 3. [Online softmax] first pass: find max + sum
    m = float("-inf")  # m is the max value. use the notation from the paper
    d = 0.0  # d is the sum. use the notation from the paper
    ori_X_y = tl.load(X_ptr + y).cast(tl.float32)  # we need to store the original value of X_y for the loss calculation
    if HAS_SOFTCAPPING:
        ori_X_y = softcap * tanh(ori_X_y / softcap)

    # Label smoothing is a general case of normal cross entropy
    # See the full derivation at https://github.com/linkedin/Liger-Kernel/pull/198#issue-2503665310
    scaled_x_sum = 0.0
    eps = label_smoothing / n_cols

    for i in range(0, n_cols, BLOCK_SIZE):
        X_offsets = i + tl.arange(0, BLOCK_SIZE)
        X_block = tl.load(
            X_ptr + X_offsets,
            mask=X_offsets < n_cols,
            other=float("-inf"),
            # Ensure float32 precision for softmax calculation
        ).cast(tl.float32)
        if HAS_SOFTCAPPING:
            X_block = softcap * tanh(X_block / softcap)
        block_max = tl.max(X_block)
        if label_smoothing > 0:
            # scale X beforehand to avoid overflow
            if HAS_WEIGHT:
                weight_block = tl.load(weight_ptr + X_offsets, mask=X_offsets < n_cols)
                scaled_x_sum += tl.sum(tl.where(X_offsets < n_cols, -eps * X_block * weight_block, 0.0))
            else:
                scaled_x_sum += tl.sum(tl.where(X_offsets < n_cols, -eps * X_block, 0.0))
        m_new = tl.maximum(m, block_max)
        d = d * tl.exp(m - m_new) + tl.sum(tl.exp(X_block - m_new))
        m = m_new

    # log (sum(e^(X_i))) = log (sum(e ^ (max(X) * e ^ (X_i - max(X)))))
    #                    = log (e^(max(X)) * sum(e ^ (X_i - max(X))))
    #                    = max(X) + log (sum(e ^ (X_i - max(X)))) = m + log d
    lse = m + tl.log(d)

    # 4. [Online Softmax] Second pass: compute gradients
    # For 'mean' reduction, gradients are normalized by number of non-ignored elements (N)
    # dx_y = (softmax(x_y) - 1) / N
    # dx_i = softmax(x_i) / N, i != y
    # For label smoothing:
    # dx_i = (softmax(x_i) - label_smoothing / V) / N, V = n_cols, i != y
    # dx_y = (softmax(x_y) - label_smoothing / V - (1 - label_smoothing)) / N
    #      = dx_i - (1 - label_smoothing) / N
    # With Z loss:
    # dx_i = ((1 + 2 * lse_square_scale * lse) * softmax(x_i) - label_smoothing / V) / N, i != y
    # dx_y = dx_i - (1 - label_smoothing) / N
    # For 'sum' reduction, no normalization is applied:
    # dx_y = softmax(x_y) - 1
    # dx_i = softmax(x_i), for i ≠ y

    for i in range(0, n_cols, BLOCK_SIZE):
        X_offsets = i + tl.arange(0, BLOCK_SIZE)
        X_block = tl.load(
            X_ptr + X_offsets,
            mask=X_offsets < n_cols,
            other=float("-inf"),
            # Ensure float32 precision for softmax calculation
        ).cast(tl.float32)
        if HAS_SOFTCAPPING:
            intermediate = tanh(X_block / softcap)
            X_block = softcap * intermediate

        if not HAS_WEIGHT:
            # softmax(x_i)
            X_block = tl.exp(X_block - m) / d
            # derivative of z-loss: 2 * lse_square_scale * lse * softmax(x_i)
            X_block += 2 * lse_square_scale * lse * X_block
            # smoothing term
            X_block += -eps
            # special handle dx_y
            X_block = tl.where(X_offsets != y, X_block, X_block - (1 - label_smoothing))
            # reduction scale
            if reduction == "mean":
                X_block = X_block / n_non_ignore
        else:
            weight_block = tl.load(weight_ptr + X_offsets, mask=X_offsets < n_cols)
            softmax_X = tl.exp(X_block - m) / d
            # derivative of original_loss
            dloss_ori = (1 - label_smoothing) * softmax_X
            # specially handle dx_y
            dloss_ori = tl.where(X_offsets != y, dloss_ori, dloss_ori - (1 - label_smoothing))
            dloss_ori = dloss_ori * weight_y
            # derivative of smooth_loss
            dloss_smooth = eps * (-weight_block + softmax_X * weight_sum)
            # derivative of z-loss
            dz_loss = 2 * lse_square_scale * lse * softmax_X
            # reduction scale
            if reduction == "mean":
                dloss_ori = dloss_ori / sum_non_ignore_weight
                dloss_smooth = dloss_smooth / sum_non_ignore_weight
                # TODO: Implement weighted z_loss. Currently, z_loss is not scaled by weight.
                dz_loss = dz_loss / n_non_ignore
            # derivative of total_loss
            X_block = dloss_ori + dloss_smooth + dz_loss

        # chain rule softcapping
        # d(softcap * tanh(x / softcap)) = (1 - tanh^2(x / softcap))
        if HAS_SOFTCAPPING:
            X_block = X_block * (1 - intermediate * intermediate)

        tl.store(X_ptr + X_offsets, X_block, mask=X_offsets < n_cols)

    # We need tl.debug_barrier() to ensure the new result of X_ptr is written as mentioned in
    # https://github.com/triton-lang/triton/blob/ba42a5c68fd0505f8c42f4202d53be0f8d9a5fe0/python/triton/ops/cross_entropy.py#L34
    tl.debug_barrier()

    # 5. Calculate the loss

    # loss = log (softmax(X_y)) = log ((e ^ (X_y - max(X)) / sum(e ^ (X - max(X))))
    #      = (X_y - max(X)) - log(sum(e ^ (X - max(X))))
    #      = X_y - m - log d = X_y - lse
    # sum(e ^ (X - max(X))) must >= 1 because the max term is e ^ 0 = 1
    # So we can safely calculate log (softmax(X_y)) without overflow
    loss = lse - ori_X_y
    if HAS_WEIGHT:
        loss = weight_y * loss

    # Original loss = H(q, p),  with label smoothing regularization = H(q', p) and (label_smoothing / V) = eps
    # H(q', p) = (1 - label_smoothing) * H(q, p) + label_smoothing * H(u, p)
    #          = (1 - label_smoothing) * H(q, p) + eps * sum(logsoftmax(x_i))
    # By using m (global max of xi) and d (sum of e^(xi-m)), we can simplify as:
    #          = (1 - label_smoothing) * H(q, p) + (sum(-eps * x_i) + label_smoothing * (m + logd))
    # Refer to H(q', p) in section 7 of the paper: https://arxiv.org/pdf/1512.00567
    # pytorch: https://github.com/pytorch/pytorch/blob/2981534f54d49fa3a9755c9b0855e7929c2527f0/aten/src/ATen/native/LossNLL.cpp#L516
    # See full derivation at https://github.com/linkedin/Liger-Kernel/pull/198#issuecomment-2333753087
    if label_smoothing > 0:
        if HAS_WEIGHT:
            smooth_loss = scaled_x_sum + eps * lse * weight_sum
        else:
            smooth_loss = scaled_x_sum + label_smoothing * lse
        loss = loss * (1 - label_smoothing) + smooth_loss

    # An auxiliary loss, z_loss
    # Refer to Page14 Loss function section in the paper PaLM: https://www.jmlr.org/papers/v24/22-1144.html
    z_loss = lse_square_scale * lse * lse
    # Normalize the loss by the number of non-ignored elements if reduction is "mean"
    if reduction == "mean":
        if HAS_WEIGHT:
            loss = loss / sum_non_ignore_weight
        else:
            loss = loss / n_non_ignore
        # TODO: Implement weighted z_loss. Currently, z_loss is not scaled by weight.
        z_loss = z_loss / n_non_ignore
    loss += z_loss

    tl.store(loss_ptr, loss)
    if RETURN_Z_LOSS:
        tl.store(z_loss_ptr, z_loss)


MAX_FUSED_SIZE = 65536 // 2
MIN_TOKEN_CHUNK = 512
MAX_LOGITS_BYTES = 256 << 20


def _is_hip():
    return torch.version.hip is not None


def _token_chunk_size(BT, H, V, element_size):
    natural = triton.next_power_of_2(triton.cdiv(BT, triton.cdiv(V, H)))
    memory_cap = max(1, MAX_LOGITS_BYTES // (V * element_size))
    memory_cap = 1 << (memory_cap.bit_length() - 1)
    return max(1, min(BT, max(natural, MIN_TOKEN_CHUNK), memory_cap))


def _linear_cross_entropy_forward(_input, weight, target, bias, ignore_index):
    BT, H = _input.shape
    V = weight.shape[0]
    BLOCK_SIZE = min(MAX_FUSED_SIZE, triton.next_power_of_2(V))

    chunk_size = _token_chunk_size(BT, H, V, _input.element_size())
    num_chunks = triton.cdiv(BT, chunk_size)

    grad_weight = torch.zeros_like(weight) if weight.requires_grad else None
    grad_input = torch.zeros_like(_input)
    grad_bias = torch.zeros_like(bias) if bias is not None else None
    loss_1d = torch.zeros(BT, dtype=torch.float32, device=_input.device)

    total_n_non_ignore = (target != ignore_index).sum().item()

    for chunk_id in range(num_chunks):
        start_idx = chunk_id * chunk_size
        end_idx = min((chunk_id + 1) * chunk_size, BT)
        _input_chunk = _input[start_idx:end_idx]

        logits_chunk = _input_chunk @ weight.t()
        if bias is not None:
            logits_chunk = logits_chunk + bias.to(logits_chunk.dtype)

        target_chunk = target[start_idx:end_idx]
        n_rows = logits_chunk.shape[0]
        loss_1d_slice = loss_1d[start_idx:end_idx]

        logits_chunk = logits_chunk.contiguous()
        target_chunk = target_chunk.contiguous()

        liger_cross_entropy_kernel[(n_rows,)](
            X_ptr=logits_chunk,
            X_stride=logits_chunk.stride(-2),
            Y_ptr=target_chunk,
            Y_stride=target_chunk.stride(-1),
            weight_ptr=None,
            loss_ptr=loss_1d_slice,
            z_loss_ptr=None,
            loss_stride=loss_1d_slice.stride(-1),
            n_cols=V,
            n_non_ignore=total_n_non_ignore,
            sum_non_ignore_weight=total_n_non_ignore,
            weight_sum=0.0,
            ignore_index=ignore_index,
            lse_square_scale=0.0,
            label_smoothing=0.0,
            reduction="mean",
            softcap=None,
            RETURN_Z_LOSS=False,
            HAS_WEIGHT=False,
            HAS_SOFTCAPPING=False,
            BLOCK_SIZE=BLOCK_SIZE,
            num_warps=32 if not _is_hip() else 16,
        )

        grad_logits_chunk = logits_chunk
        grad_input[start_idx:end_idx] = grad_logits_chunk @ weight

        if grad_weight is not None:
            torch.addmm(
                input=grad_weight,
                mat1=logits_chunk.t().to(_input_chunk.dtype),
                mat2=_input_chunk,
                out=grad_weight,
                alpha=1.0,
                beta=1.0,
            )

        if bias is not None:
            torch.add(
                input=grad_bias,
                other=logits_chunk.sum(dim=0),
                out=grad_bias,
                alpha=1.0,
            )

    return torch.sum(loss_1d), grad_input, grad_weight, grad_bias


class _LigerLinearCrossEntropy(torch.autograd.Function):
    @staticmethod
    @torch.amp.custom_fwd(device_type="cuda")
    def forward(ctx, x, weight, targets, bias, ignore_index):
        loss, dx, dw, db = _linear_cross_entropy_forward(x, weight, targets, bias, ignore_index)
        ctx.save_for_backward(dx, dw, db)
        return loss

    @staticmethod
    @torch.amp.custom_bwd(device_type="cuda")
    @torch.autograd.function.once_differentiable
    def backward(ctx, grad_output):
        dx, dw, db = ctx.saved_tensors
        return (
            (dx * grad_output).to(dx.dtype),
            None if dw is None else (dw * grad_output).to(dw.dtype),
            None,
            None if db is None else (db * grad_output).to(db.dtype),
            None,
        )


def linear_cross_entropy_liger(x, weight, targets, *, bias=None, ignore_index=-100):
    if x.device.type != "cuda":
        raise ValueError("triton_liger requires CUDA and Triton")
    if x.ndim != 2 or weight.ndim != 2 or min(weight.shape) < 1 or x.shape[1] != weight.shape[1]:
        raise ValueError("expected x [tokens, hidden] and weight [vocab, hidden] with matching positive widths")
    if x.dtype not in (torch.float16, torch.bfloat16, torch.float32) or weight.dtype != x.dtype:
        raise ValueError("x and weight must share fp16, bf16 or fp32 dtype")
    if weight.device != x.device or targets.device != x.device:
        raise ValueError("inputs and targets must be on the same device")
    if targets.ndim != 1 or targets.numel() != x.shape[0] or targets.dtype != torch.int64:
        raise ValueError("targets must be int64 [tokens]")
    if bias is not None:
        if bias.shape != (weight.shape[0],) or bias.device != x.device or bias.dtype not in (x.dtype, torch.float32):
            raise ValueError("bias must be [vocab] on the same device with input dtype or fp32")
    with torch.cuda.device(x.device):
        valid = targets != ignore_index
        if bool((valid & ((targets < 0) | (targets >= weight.shape[0]))).any()):
            raise ValueError("target is outside vocabulary")
        if not bool(valid.any()):
            zero = x.float().sum() * 0 + weight.float().sum() * 0
            return zero if bias is None else zero + bias.float().sum() * 0
        return _LigerLinearCrossEntropy.apply(
            x.contiguous(),
            weight.contiguous(),
            targets.contiguous(),
            None if bias is None else bias.contiguous(),
            ignore_index,
        )
