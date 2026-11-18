# Official repository: https://github.com/apple/ml-cross-entropy
# Pinned revision: 3de376c106a1916bc5e1b619f9c77c87a461ee1c
# Sources: cut_cross_entropy/tl_utils.py, cce_lse_forward.py, cce_backward.py
# Kernel bodies retained verbatim; host adapter targets this repo's API.
# Upstream license (retained in full):
# Copyright (C) 2024 Apple Inc. All Rights Reserved.
#
# IMPORTANT:  This Apple software is supplied to you by Apple
# Inc. ("Apple") in consideration of your agreement to the following
# terms, and your use, installation, modification or redistribution of
# this Apple software constitutes acceptance of these terms.  If you do
# not agree with these terms, please do not use, install, modify or
# redistribute this Apple software.
#
# In consideration of your agreement to abide by the following terms, and
# subject to these terms, Apple grants you a personal, non-exclusive
# license, under Apple's copyrights in this original Apple software (the
# "Apple Software"), to use, reproduce, modify and redistribute the Apple
# Software, with or without modifications, in source and/or binary forms;
# provided that if you redistribute the Apple Software in its entirety and
# without modifications, you must retain this notice and the following
# text and disclaimers in all such redistributions of the Apple Software.
# Neither the name, trademarks, service marks or logos of Apple Inc. may
# be used to endorse or promote products derived from the Apple Software
# without specific prior written permission from Apple.  Except as
# expressly stated in this notice, no other rights or licenses, express or
# implied, are granted by Apple herein, including but not limited to any
# patent rights that may be infringed by your derivative works or by other
# works in which the Apple Software may be incorporated.
#
# The Apple Software is provided by Apple on an "AS IS" basis.  APPLE
# MAKES NO WARRANTIES, EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION
# THE IMPLIED WARRANTIES OF NON-INFRINGEMENT, MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE, REGARDING THE APPLE SOFTWARE OR ITS USE AND
# OPERATION ALONE OR IN COMBINATION WITH YOUR PRODUCTS.
#
# IN NO EVENT SHALL APPLE BE LIABLE FOR ANY SPECIAL, INDIRECT, INCIDENTAL
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) ARISING IN ANY WAY OUT OF THE USE, REPRODUCTION,
# MODIFICATION AND/OR DISTRIBUTION OF THE APPLE SOFTWARE, HOWEVER CAUSED
# AND WHETHER UNDER THEORY OF CONTRACT, TORT (INCLUDING NEGLIGENCE),
# STRICT LIABILITY OR OTHERWISE, EVEN IF APPLE HAS BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#
# -------------------------------------------------------------------------------
# SOFTWARE DISTRIBUTED WITH CUT CROSS ENTROPY:
#
# The Cut Cross Entropy software includes a number of subcomponents with separate
# copyright notices and license terms - please see the file ACKNOWLEDGEMENTS.md.
# -------------------------------------------------------------------------------

import functools
import importlib.metadata

import torch
import triton
import triton.language as tl
from packaging.version import Version
from triton.language.extra import libdevice as tl_libdevice


@triton.jit
def tl_and_reduce_fn(a, b):
    return a & b


@triton.jit
def tl_tanh(a: tl.tensor) -> tl.tensor:
    return tl_libdevice.tanh(a)


@triton.jit
def tl_log1p(a: tl.tensor) -> tl.tensor:
    return tl_libdevice.log1p(a)


@triton.jit
def tl_softcapping(v: tl.tensor, softcap: float) -> tl.tensor:
    return tl_tanh(v / softcap) * softcap


@triton.jit
def tl_softcapping_grad(dv: tl.tensor, v: tl.tensor, softcap: float) -> tl.tensor:
    v = v / softcap
    return dv * (1 - v * v)


@triton.jit
def tl_logaddexp(a, b) -> tl.tensor:
    minx = tl.minimum(a, b)
    mx = tl.maximum(a, b)
    return tl_log1p(tl.exp(minx - mx)) + mx


@triton.jit
def tl_2sum(a: tl.tensor, b: tl.tensor) -> tuple[tl.tensor, tl.tensor]:
    s = a + b

    a_prime = s - b
    b_prime = s - a_prime

    delta_a = a - a_prime
    delta_b = b - b_prime

    t = delta_a + delta_b
    return s, t


@triton.jit
def tl_lock_kahan_sum(ptrs, c_ptrs, v, mask, lock_ptr):
    while tl.atomic_cas(lock_ptr, 0, 1) == 1:
        pass

    s = tl.load(ptrs, mask=mask, other=0.0, eviction_policy="evict_last")
    c = tl.load(c_ptrs, mask=mask, other=0.0, eviction_policy="evict_last")

    s, c = tl_2sum(s, c + v)

    tl.store(ptrs, s, mask=mask, eviction_policy="evict_last")
    tl.store(c_ptrs, c, mask=mask, eviction_policy="evict_last")

    tl.debug_barrier()
    tl.atomic_xchg(lock_ptr, 0)


@triton.jit
def tl_lock_add(ptrs, v, mask, lock_ptr):
    while tl.atomic_cas(lock_ptr, 0, 1) == 1:
        pass

    cur_v = tl.load(ptrs, mask=mask, other=0.0, eviction_policy="evict_last")
    new_v = v + cur_v
    tl.store(ptrs, new_v, mask=mask, eviction_policy="evict_last")

    tl.debug_barrier()
    tl.atomic_xchg(lock_ptr, 0)


def b_bin_fn(b: int) -> int:
    if b >= 1024:
        return 1024
    elif b <= 128:
        return 128
    else:
        return 512


@functools.cache
def _triton_at_least_3_2() -> bool:
    try:
        version = importlib.metadata.version("triton")
    except importlib.metadata.PackageNotFoundError:
        version = triton.__version__
    return Version(version) >= Version("3.2.0")


def _build_valids(targets: torch.Tensor, ignore_index: int) -> torch.Tensor | None:
    valids = (targets != ignore_index).nonzero().to(torch.int32)
    assert valids.size(1) == 1
    return valids.squeeze(1) if valids.numel() != targets.numel() else None


def _cce_lse_forward_kernel(
    E,
    C,
    Bias,
    LSE,
    LA,
    NegCorrectLogit,
    Locks,
    Valids,
    Targets,
    softcap,
    shift,
    B,
    V,
    D,
    BMax,
    stride_eb,
    stride_ed,
    stride_cv,
    stride_cd,
    stride_biasv,
    stride_vb,
    num_locks,
    # Meta-parameters
    B_BIN,
    HAS_BIAS: tl.constexpr,
    HAS_VALIDS: tl.constexpr,
    BLOCK_B: tl.constexpr,
    BLOCK_V: tl.constexpr,
    BLOCK_D: tl.constexpr,  #
    GROUP_B: tl.constexpr,  #
    EVEN_D: tl.constexpr,
    HAS_SOFTCAP: tl.constexpr,
    HAS_LA: tl.constexpr,
    DOT_PRECISION: tl.constexpr,
    HAS_TARGETS: tl.constexpr,
    HAS_SHIFT: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_b = tl.cdiv(B, BLOCK_B)
    num_pid_v = tl.cdiv(V, BLOCK_V)
    num_pid_in_group = GROUP_B * num_pid_v
    group_id = pid // num_pid_in_group
    first_pid_b = group_id * GROUP_B
    group_size_b = min(num_pid_b - first_pid_b, GROUP_B)
    pid_b = (first_pid_b + ((pid % num_pid_in_group) % group_size_b)).to(tl.int64)
    pid_v = ((pid % num_pid_in_group) // group_size_b).to(tl.int64)

    offs_b = (pid_b * BLOCK_B + tl.arange(0, BLOCK_B)).to(tl.int64)
    if HAS_VALIDS:
        offs_b = tl.load(Valids + stride_vb * offs_b, mask=offs_b < B, other=BMax).to(tl.int64)

    offs_v = (pid_v * BLOCK_V + tl.arange(0, BLOCK_V)).to(tl.int64)
    offs_d = tl.arange(0, BLOCK_D).to(tl.int64)
    e_ptrs = E + (offs_b[:, None] * stride_eb + offs_d[None, :] * stride_ed)
    c_ptrs = C + (offs_v[None, :] * stride_cv + offs_d[:, None] * stride_cd)

    accum = tl.zeros((BLOCK_B, BLOCK_V), dtype=tl.float32)
    for d in range(0, tl.cdiv(D, BLOCK_D)):
        e_mask = offs_b[:, None] < BMax
        if not EVEN_D:
            e_mask = e_mask & (offs_d[None, :] < (D - d * BLOCK_D))

        e = tl.load(e_ptrs, mask=e_mask, other=0.0)

        c_mask = offs_v[None, :] < V
        if not EVEN_D:
            c_mask = c_mask & (offs_d[:, None] < (D - d * BLOCK_D))

        c = tl.load(c_ptrs, mask=c_mask, other=0.0)

        accum = tl.dot(e, c, accum, input_precision=DOT_PRECISION)

        e_ptrs += BLOCK_D * stride_ed
        c_ptrs += BLOCK_D * stride_cd

    tl.debug_barrier()

    accum = accum.cast(E.dtype.element_ty, fp_downcast_rounding="rtne")
    if HAS_BIAS:
        bias = tl.load(Bias + offs_v * stride_biasv, mask=offs_v < V, other=0.0)
        accum += bias[None, :]

    logits = tl.where(offs_v[None, :] < V, accum, -float("inf"))
    if HAS_SOFTCAP:
        logits = tl_softcapping(logits, softcap)

    logits = logits.cast(tl.float32)
    if HAS_LA:
        this_avg_logit = tl.sum(logits, 0) / B
        tl.atomic_add(LA + offs_v, this_avg_logit, mask=offs_v < V)

    if HAS_TARGETS:
        if HAS_SHIFT:
            target_offs_b = offs_b + shift
        else:
            target_offs_b = offs_b

        this_targets = tl.load(Targets + target_offs_b, mask=target_offs_b < BMax, other=V + 1)

        offs_b = (pid_b * BLOCK_B + tl.arange(0, BLOCK_B)).to(tl.int64)

        neg_correct_logit_ptrs = NegCorrectLogit + offs_b

        neg_correct_logit_ptrs = tl.broadcast_to(
            neg_correct_logit_ptrs[:, None], (BLOCK_B, BLOCK_V)
        )
        tl.store(neg_correct_logit_ptrs, -logits, mask=this_targets[:, None] == offs_v[None, :])
    else:
        offs_b = (pid_b * BLOCK_B + tl.arange(0, BLOCK_B)).to(tl.int64)

    this_mx = tl.max(logits, axis=1)
    this_lse = this_mx + tl.log(tl.sum(tl.exp(logits - this_mx[:, None]), axis=1))

    o_mask = offs_b < B

    lse_ptrs = LSE + offs_b

    this_locks = Locks + (pid_b // tl.cdiv(B, BLOCK_B * num_locks))
    while tl.atomic_cas(this_locks, 0, 1) == 1:
        pass

    lse = tl.load(lse_ptrs, mask=o_mask, other=0.0, eviction_policy="evict_last")
    lse = tl_logaddexp(lse, this_lse)
    lse = tl.store(lse_ptrs, lse, mask=o_mask, eviction_policy="evict_last")

    tl.debug_barrier()
    tl.atomic_xchg(this_locks, 0)


_cce_lse_forward_kernel = triton.jit(_cce_lse_forward_kernel)
_cce_lse_forward_kernel = triton.heuristics(  # type: ignore
    {
        "EVEN_D": lambda args: args["D"] % args["BLOCK_D"] == 0,
        "HAS_BIAS": lambda args: args["Bias"] is not None,
        "HAS_VALIDS": lambda args: args["Valids"] is not None,
        "HAS_SOFTCAP": lambda args: args["softcap"] is not None,
        "HAS_LA": lambda args: args["LA"] is not None,
        "GROUP_B": lambda args: 8,
        "DOT_PRECISION": lambda args: "tf32"
        if torch.get_float32_matmul_precision() == "high"
        else "ieee",
        "HAS_TARGETS": lambda args: args["Targets"] is not None,
        "HAS_SHIFT": lambda args: args["shift"] != 0,
    }
)(_cce_lse_forward_kernel)
_cce_lse_forward_kernel = triton.heuristics(  # type: ignore
    {
        "BLOCK_B": lambda args: 32 if args["E"].dtype == torch.float32 else 128,
        "BLOCK_V": lambda args: 128,
        "BLOCK_D": lambda args: 32,
    }
)(_cce_lse_forward_kernel)


@triton.jit
def _mm_backward(
    do,
    da_ptrs,
    dac_ptrs,
    partial_mask_a,
    da_lock_ptr,
    n_locks,
    b_ptrs,
    partial_mask_b,
    stride_ad,
    stride_bd,
    D,
    BLOCK_D: tl.constexpr,
    EVEN_D: tl.constexpr,
    USE_KAHAN: tl.constexpr,
    DOT_PRECISION: tl.constexpr,
):
    d_inds = tl.arange(0, BLOCK_D)[None, :].to(tl.int64)

    b_ptrs = b_ptrs + d_inds * stride_bd
    da_ptrs = da_ptrs + d_inds * stride_ad
    if USE_KAHAN:
        dac_ptrs = dac_ptrs + d_inds * stride_ad

    for d in range(0, tl.cdiv(D, BLOCK_D)):
        if EVEN_D:
            mask = partial_mask_b
        else:
            mask = partial_mask_b & (d_inds < (D - d * BLOCK_D))

        b = tl.load(b_ptrs, mask=mask, other=0.0)

        da_i = tl.dot(do, b, input_precision=DOT_PRECISION).to(da_ptrs.dtype.element_ty)

        if EVEN_D:
            mask = partial_mask_a
        else:
            mask = partial_mask_a & (d_inds < (D - d * BLOCK_D))

        lock_offset = d // tl.cdiv(D, BLOCK_D * n_locks)
        this_da_lock_ptr = da_lock_ptr + lock_offset

        if USE_KAHAN:
            tl_lock_kahan_sum(da_ptrs, dac_ptrs, da_i, mask, this_da_lock_ptr)
        else:
            tl_lock_add(da_ptrs, da_i, mask, this_da_lock_ptr)

        b_ptrs += BLOCK_D * stride_bd
        da_ptrs += BLOCK_D * stride_ad
        if USE_KAHAN:
            dac_ptrs += BLOCK_D * stride_ad


@triton.jit
def _block_is_filtered(check_val: tl.tensor, filter_eps: tl.tensor) -> tl.tensor:
    return tl.reduce(check_val < filter_eps, None, tl_and_reduce_fn)


def _cce_backward_kernel(
    E,
    C,
    Bias,
    LSE,
    dOut,
    grad_scale,
    dLSE,
    Valids,
    VocabOrdering,
    softcap,
    Targets,
    dE,
    dEC,
    dELocks,
    dC,
    dCC,
    dCLocks,
    dBias,
    B,
    D,
    V,
    BMax,
    n_de_locks_0,
    n_de_locks_1,
    n_dc_locks_0,
    n_dc_locks_1,
    stride_eb,
    stride_ed,
    stride_cv,
    stride_cd,
    stride_biasv,
    stride_vb,
    filter_eps,
    shift,
    B_BIN,
    BLOCK_B: tl.constexpr,
    BLOCK_V: tl.constexpr,
    BLOCK_D: tl.constexpr,
    MM_BACK_BLOCK_D: tl.constexpr,
    GROUP_B: tl.constexpr,
    EVEN_D: tl.constexpr,
    MM_BACK_EVEN_D: tl.constexpr,
    ITEM_DO: tl.constexpr,
    HAS_BIAS: tl.constexpr,
    HAS_VALIDS: tl.constexpr,
    HAS_VOCAB_ORDERING: tl.constexpr,
    FILTER_E_GRAD: tl.constexpr,
    FILTER_C_GRAD: tl.constexpr,
    HAS_TARGETS: tl.constexpr,
    HAS_SOFTCAP: tl.constexpr,
    HAS_DLSE: tl.constexpr,
    HAS_SHIFT: tl.constexpr,
    KAHAN_E: tl.constexpr,
    KAHAN_C: tl.constexpr,
    COMPUTE_DC: tl.constexpr,
    COMPUTE_DE: tl.constexpr,
    COMPUTE_DBIAS: tl.constexpr,
    DOT_PRECISION: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_b_chunks = tl.cdiv(B, BLOCK_B)
    num_v_chunks = tl.cdiv(V, BLOCK_V)
    num_v_in_group = GROUP_B * num_v_chunks
    group_id = pid // num_v_in_group
    first_pid_b = group_id * GROUP_B
    group_size_b = min(num_b_chunks - first_pid_b, GROUP_B)
    pid_b = (first_pid_b + ((pid % num_v_in_group) % group_size_b)).to(tl.int64)
    pid_v = ((pid % num_v_in_group) // group_size_b).to(tl.int64)

    offs_b = (pid_b * BLOCK_B + tl.arange(0, BLOCK_B)).to(tl.int64)
    if HAS_VALIDS:
        offs_b = tl.load(Valids + stride_vb * offs_b, mask=offs_b < B, other=BMax).to(tl.int64)

    offs_v = (pid_v * BLOCK_V + tl.arange(0, BLOCK_V)).to(tl.int64)
    if HAS_VOCAB_ORDERING:
        offs_v = tl.load(VocabOrdering + offs_v, mask=offs_v < V, other=V).to(tl.int64)

    offs_d = tl.arange(0, BLOCK_D).to(tl.int64)
    e_ptrs = E + (offs_b[:, None] * stride_eb + offs_d[None, :] * stride_ed)
    c_ptrs = C + (offs_v[None, :] * stride_cv + offs_d[:, None] * stride_cd)

    accum = tl.zeros((BLOCK_B, BLOCK_V), dtype=tl.float32)
    for d in range(0, tl.cdiv(D, BLOCK_D)):
        e_mask = offs_b[:, None] < BMax
        if not EVEN_D:
            e_mask = e_mask & (offs_d[None, :] < (D - d * BLOCK_D))

        e = tl.load(e_ptrs, mask=e_mask, other=0.0)

        c_mask = offs_v[None, :] < V
        if not EVEN_D:
            c_mask = c_mask & (offs_d[:, None] < (D - d * BLOCK_D))

        c = tl.load(c_ptrs, mask=c_mask, other=0.0)

        accum = tl.dot(e, c, accum, input_precision=DOT_PRECISION)

        e_ptrs += BLOCK_D * stride_ed
        c_ptrs += BLOCK_D * stride_cd

    tl.debug_barrier()

    accum = accum.cast(E.dtype.element_ty, fp_downcast_rounding="rtne")
    if HAS_BIAS:
        bias = tl.load(Bias + offs_v * stride_biasv, mask=offs_v < V, other=0.0)
        accum += bias[None, :]

    if HAS_SOFTCAP:
        accum = tl_softcapping(accum, softcap)

    if HAS_VALIDS:
        direct_offs_b = (pid_b * BLOCK_B + tl.arange(0, BLOCK_B)).to(tl.int64)
        lse = tl.load(LSE + direct_offs_b, mask=direct_offs_b < B, other=float("inf"))
    else:
        lse = tl.load(LSE + offs_b, mask=offs_b < B, other=float("inf"))

    accum = accum.cast(tl.float32)
    d_accum = tl.exp(accum - lse[:, None])
    d_accum = tl.where(offs_v[None, :] < V, d_accum, 0.0)

    if HAS_TARGETS:
        if HAS_SHIFT:
            target_offs_b = offs_b + shift
        else:
            target_offs_b = offs_b

        targets = tl.load(Targets + target_offs_b, mask=target_offs_b < BMax, other=V + 1)
        is_target = targets[:, None] == offs_v[None, :]
        d_accum += tl.where(is_target, -1.0, 0.0)
    else:
        is_target = None

    should_skip = False
    if (FILTER_E_GRAD and COMPUTE_DE) and (FILTER_C_GRAD and COMPUTE_DC):
        if _block_is_filtered(tl.abs(d_accum), filter_eps):
            return
    elif (FILTER_E_GRAD and COMPUTE_DE) or (FILTER_C_GRAD and COMPUTE_DC):
        should_skip = _block_is_filtered(tl.abs(d_accum), filter_eps)

    if ITEM_DO:
        d_out = tl.load(dOut)
    else:
        if HAS_SHIFT:
            d_out_offs_b = offs_b + shift
        else:
            d_out_offs_b = offs_b

        d_out = tl.load(dOut + d_out_offs_b, mask=d_out_offs_b < BMax, other=0.0)[:, None]

    d_out = grad_scale * d_out

    if HAS_DLSE:
        if HAS_SHIFT:
            d_lse_offs_b = offs_b + shift
        else:
            d_lse_offs_b = offs_b

        d_lse = tl.load(dLSE + d_lse_offs_b, mask=d_lse_offs_b < BMax, other=0.0)[:, None]

        d_accum *= d_out + d_lse

        if HAS_TARGETS:
            # We have d_accum = d_mm - is_target
            # We then want to get d_accum = d_mm * (d_out + d_lse) - is_target * d_out
            # If we do d_accum * (d_out + d_lse), we get d_mm * (d_out + d_lse) - is_target * (d_out + d_lse)
            # So we need to do d_accum += is_target * d_lse

            d_accum += tl.where(is_target, d_lse, 0.0)
    else:
        d_accum = d_accum * d_out

    if HAS_SOFTCAP:
        d_accum = tl_softcapping_grad(d_accum, accum, softcap)

    if COMPUTE_DBIAS:
        tl.atomic_add(dBias + offs_v * stride_biasv, tl.sum(d_accum, 0), mask=offs_v < V)

    d_accum = d_accum.cast(E.dtype.element_ty, fp_downcast_rounding="rtne")

    if COMPUTE_DE:
        if FILTER_E_GRAD:
            should_skip_e = should_skip
        else:
            should_skip_e = False

        if not should_skip_e:
            lock_offset = (pid_b // tl.cdiv(B, BLOCK_B * n_de_locks_0)) * n_de_locks_1

            _mm_backward(
                d_accum,
                dE + (offs_b[:, None] * stride_eb),
                dEC + (offs_b[:, None] * stride_eb) if KAHAN_E else None,
                offs_b[:, None] < BMax,
                dELocks + lock_offset,
                n_de_locks_1,
                C + offs_v[:, None] * stride_cv,
                offs_v[:, None] < V,
                stride_ed,
                stride_cd,
                D,
                MM_BACK_BLOCK_D,
                MM_BACK_EVEN_D,
                KAHAN_E,
                DOT_PRECISION,
            )

    if COMPUTE_DC:
        if FILTER_C_GRAD:
            should_skip_c = should_skip
        else:
            should_skip_c = False

        if not should_skip_c:
            lock_offset = (pid_v // tl.cdiv(V, BLOCK_V * n_dc_locks_0)) * n_dc_locks_1

            _mm_backward(
                tl.trans(d_accum),
                dC + (offs_v[:, None] * stride_cv),
                dCC + (offs_v[:, None] * stride_cv) if KAHAN_C else None,
                offs_v[:, None] < V,
                dCLocks + lock_offset,
                n_dc_locks_1,
                E + (offs_b[:, None] * stride_eb),
                offs_b[:, None] < BMax,
                stride_cd,
                stride_ed,
                D,
                MM_BACK_BLOCK_D,
                MM_BACK_EVEN_D,
                KAHAN_C,
                DOT_PRECISION,
            )


def _cce_back_block_d(args) -> int:
    block_d = args["BLOCK_D"]
    return 2 * block_d


_cce_backward_kernel = triton.jit(_cce_backward_kernel)
_cce_backward_kernel = triton.heuristics(  # type: ignore
    {
        "EVEN_D": lambda args: (args["D"] % args["BLOCK_D"]) == 0,
        "MM_BACK_BLOCK_D": lambda args: _cce_back_block_d(args),
        "MM_BACK_EVEN_D": lambda args: (args["D"] % _cce_back_block_d(args)) == 0,
        "HAS_VALIDS": lambda args: args["Valids"] is not None,
        "HAS_BIAS": lambda args: args["Bias"] is not None,
        "HAS_VOCAB_ORDERING": lambda args: args["VocabOrdering"] is not None,
        "HAS_TARGETS": lambda args: args["Targets"] is not None,
        "HAS_SOFTCAP": lambda args: args["softcap"] is not None,
        "HAS_DLSE": lambda args: args["dLSE"] is not None,
        "HAS_SHIFT": lambda args: args["shift"] != 0,
        "ITEM_DO": lambda args: args["dOut"].numel() == 1,
        "GROUP_B": lambda args: 8,
        "COMPUTE_DC": lambda args: args["dC"] is not None,
        "COMPUTE_DE": lambda args: args["dE"] is not None,
        "KAHAN_E": lambda args: args["dEC"] is not None,
        "KAHAN_C": lambda args: args["dCC"] is not None,
        "COMPUTE_DBIAS": lambda args: args["dBias"] is not None,
        "DOT_PRECISION": lambda args: "tf32"
        if torch.get_float32_matmul_precision() == "high"
        else "ieee",
    }
)(_cce_backward_kernel)
_cce_backward_kernel = triton.heuristics(  # type: ignore
    {
        "BLOCK_B": lambda args: 32 if args["E"].dtype == torch.float32 else 128,
        "BLOCK_V": lambda args: 128,
        "BLOCK_D": lambda args: 32,
    }
)(_cce_backward_kernel)


def _cce_forward(e, c, bias, valids, targets):
    if valids is not None:
        B = valids.numel()
    else:
        B = e.size(0)

    V, D = c.shape
    lse = e.new_full((B,), -torch.inf, dtype=torch.float32)
    neg_correct_logit = e.new_full((B,), 0.0, dtype=torch.float32)
    locks = e.new_full((triton.cdiv(B, 128),), 0, dtype=torch.uint32)

    def grid(META):
        return (triton.cdiv(B, META["BLOCK_B"]) * triton.cdiv(V, META["BLOCK_V"]),)

    _cce_lse_forward_kernel[grid](
        e,
        c,
        bias,
        lse,
        None,
        neg_correct_logit,
        locks,
        valids,
        targets,
        None,
        0,
        B,
        V,
        D,
        e.size(0),
        e.stride(0),
        e.stride(1),
        c.stride(0),
        c.stride(1),
        1 if bias is None else bias.stride(0),
        1 if valids is None else valids.stride(0),
        num_locks=locks.size(0),
        B_BIN=b_bin_fn(B),
    )
    return lse, neg_correct_logit


def _cce_backward(do, e, c, bias, lse, valids, targets, grad_scale, need_de, need_dc, need_dbias):
    can_use_fp32_accum = _triton_at_least_3_2()

    do = do.contiguous()
    lse = lse.contiguous()

    de = torch.zeros_like(e, dtype=torch.float32 if can_use_fp32_accum else None) if need_de else None
    dc = torch.zeros_like(c, dtype=torch.float32 if can_use_fp32_accum else None) if need_dc else None
    dbias = torch.zeros_like(bias, dtype=torch.float32) if need_dbias else None

    if de is not None:
        assert de.stride() == e.stride()

    if dc is not None:
        assert dc.stride() == c.stride()

    if dbias is not None:
        assert dbias.stride() == bias.stride()

    dec = torch.zeros_like(e) if (need_de and not can_use_fp32_accum) else None
    dcc = torch.zeros_like(c) if (need_dc and not can_use_fp32_accum) else None

    if dec is not None:
        assert dec.stride() == e.stride()

    if dcc is not None:
        assert dcc.stride() == c.stride()

    if valids is not None:
        B = valids.size(0)
    else:
        B = e.size(0)

    nd_locks = triton.cdiv(c.size(1), 64)
    if de is not None:
        de_locks = e.new_zeros((triton.cdiv(B, 128), nd_locks), dtype=torch.int32)
        de_lock_sizes = de_locks.size()
    else:
        de_locks = None
        de_lock_sizes = (None, None)

    if dc is not None:
        dc_locks = c.new_zeros((triton.cdiv(c.size(0), 128), nd_locks), dtype=torch.int32)
        dc_lock_sizes = dc_locks.size()
    else:
        dc_locks = None
        dc_lock_sizes = (None, None)

    def grid(META):
        return (triton.cdiv(B, META["BLOCK_B"]) * triton.cdiv(c.size(0), META["BLOCK_V"]),)

    _cce_backward_kernel[grid](
        e,
        c,
        bias,
        lse,
        do,
        grad_scale,
        None,
        valids,
        None,
        None,
        targets,
        de,
        dec,
        de_locks,
        dc,
        dcc,
        dc_locks,
        dbias,
        B,
        e.size(1),
        c.size(0),
        e.size(0),
        *de_lock_sizes,
        *dc_lock_sizes,
        e.stride(0),
        e.stride(1),
        c.stride(0),
        c.stride(1),
        1 if bias is None else bias.stride(0),
        1 if valids is None else valids.stride(0),
        None,
        shift=0,
        B_BIN=b_bin_fn(B),
        FILTER_E_GRAD=False,
        FILTER_C_GRAD=False,
    )

    if dbias is not None:
        dbias = dbias.to(dtype=bias.dtype)

    if dc is not None:
        dc = dc.to(dtype=c.dtype)

    if de is not None:
        de = de.to(dtype=e.dtype)

    return de, dc, dbias


class _CCE(torch.autograd.Function):
    @staticmethod
    @torch.amp.custom_fwd(device_type="cuda")
    def forward(ctx, e, c, bias, targets, ignore_index):
        e_dtype, c_dtype, bias_dtype = e.dtype, c.dtype, None if bias is None else bias.dtype

        if torch.is_autocast_enabled():
            dtype = torch.get_autocast_dtype("cuda")
            e = e.to(dtype=dtype)
            c = c.to(dtype=dtype)
            if bias is not None:
                bias = bias.to(dtype=dtype)

        e = e.contiguous()
        c = c.contiguous()

        valids = _build_valids(targets, ignore_index)

        if (targets.data_ptr() % 16) != 0:
            targets = torch.nn.functional.pad(targets, (0, 1))[:-1]

        lse, neg_correct_logit = _cce_forward(e, c, bias, valids, targets)
        loss = neg_correct_logit.add_(lse).mean()

        ctx.save_for_backward(e, c, bias, lse, targets, valids)
        ctx.e_dtype = e_dtype
        ctx.c_dtype = c_dtype
        ctx.bias_dtype = bias_dtype
        return loss

    @staticmethod
    @torch.amp.custom_bwd(device_type="cuda")
    def backward(ctx, grad_out):
        e, c, bias, lse, targets, valids = ctx.saved_tensors
        need_de, need_dc, need_dbias = ctx.needs_input_grad[:3]
        grad_scale = 1.0 / max(lse.numel(), 1)

        de, dc, dbias = _cce_backward(
            grad_out, e, c, bias, lse, valids, targets, grad_scale, need_de, need_dc, need_dbias
        )

        if de is not None:
            de = de.to(dtype=ctx.e_dtype)

        if dc is not None:
            dc = dc.to(dtype=ctx.c_dtype)

        if dbias is not None:
            dbias = dbias.to(dtype=ctx.bias_dtype)

        return de, dc, dbias, None, None


def linear_cross_entropy_cce(x, weight, targets, *, bias=None, ignore_index=-100):
    if x.device.type != "cuda":
        raise ValueError("triton_cce requires CUDA and Triton")
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
        if torch.cuda.get_device_capability(x.device)[0] < 8:
            raise ValueError("official Apple CCE requires compute capability >= 8")
        if x.dtype == torch.float32 and not _triton_at_least_3_2():
            raise ValueError("official Apple CCE FP32 backward requires Triton >= 3.2")
        valid = targets != ignore_index
        if bool((valid & ((targets < 0) | (targets >= weight.shape[0]))).any()):
            raise ValueError("target is outside vocabulary")
        if not bool(valid.any()):
            zero = x.float().sum() * 0 + weight.float().sum() * 0
            return zero if bias is None else zero + bias.float().sum() * 0
        return _CCE.apply(
            x.contiguous(),
            weight.contiguous(),
            None if bias is None else bias.contiguous(),
            targets.contiguous(),
            ignore_index,
        )
