"""Compare Triton causal GQA (6 query heads, 2 KV heads) with an FP64 reference."""

from __future__ import annotations

import math

import pytest
import torch

from correctness.framework import PAIRS, Case, Pair, check, pair, scaled
from kernels import attention as triton_attention

QUERY_HEADS = 6
KV_HEADS = 2
HEADS_PER_GROUP = 3
FP32_TOL = 2e-4
LOW_PRECISION_TOL = 3e-2


def _causal_gqa_reference(q, k, v):
    """Apply the attention definition separately to each group, in FP64."""
    tokens = q.shape[-2]
    positions = torch.arange(tokens, device=q.device)
    future = positions[:, None] < positions[None, :]
    scale = 1.0 / math.sqrt(q.shape[-1])
    outputs = []
    for queries, keys, values in zip(
        q.split(HEADS_PER_GROUP, dim=1), k.unbind(dim=1), v.unbind(dim=1), strict=True
    ):
        scores = (queries @ keys[:, None].transpose(-2, -1)) * scale
        probabilities = scores.masked_fill(future, -torch.inf).softmax(dim=-1)
        outputs.append(probabilities @ values[:, None])
    return torch.cat(outputs, dim=1)


def _build_case(device, dtype, head_dim, tokens):
    generator = torch.Generator().manual_seed(20261120)
    inputs = []
    for heads in (QUERY_HEADS, KV_HEADS, KV_HEADS):
        # Match the model's token-major Q/K/V views and round inputs once so
        # both implementations start from the same representable values.
        tensor = torch.randn(2, tokens, heads, head_dim, generator=generator)
        inputs.append(tensor.to(device=device, dtype=dtype).transpose(1, 2))

    if tokens == 1:
        # With a single key, dQ and dK are exactly zero. Keep one nonzero V
        # component so different reduction orders cannot add rounding noise
        # to that zero-gradient check. dV still sums all three query heads.
        inputs[2][..., 1:] = 0

    return Case(
        ref=_causal_gqa_reference,
        fast=triton_attention.attention,
        inputs=[tensor.requires_grad_() for tensor in inputs],
    )


def _candidate(dtype, head_dim, tokens):
    dtype_name = str(dtype).removeprefix("torch.")
    name = f"rotation.revantg.gqa.{dtype_name}.d{head_dim}.t{tokens}"
    tolerance = FP32_TOL if dtype == torch.float32 else LOW_PRECISION_TOL

    def build(device):
        return _build_case(device, dtype, head_dim, tokens)

    # The registry only accepts FP32/BF16. Pair still supports FP16 with
    # explicit tolerances, so keep the FP16 cases local to this file.
    if dtype == torch.float16:
        return Pair(name, build, tol=tolerance, grad_tol=tolerance, dtype=dtype)
    pair(name, tol=tolerance, grad_tol=tolerance, dtype=dtype)(build)
    return PAIRS[name]


CASES = [
    _candidate(dtype, head_dim, tokens)
    for dtype in (torch.float32, torch.bfloat16, torch.float16)
    for head_dim in (8, 64, 96, 128)
    for tokens in (1, 17, 100, 256)
]
CASES.extend(_candidate(torch.bfloat16, head_dim, 2048) for head_dim in (64, 128))


def _require_kernel(device, dtype):
    if device.type != "cuda" or triton_attention.triton is None:
        pytest.skip("Triton GQA requires CUDA and Triton")
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported(including_emulation=False):
        pytest.skip("BF16 Triton GQA requires native device support")


@pytest.mark.parametrize("candidate", CASES, ids=lambda case: case.name.rsplit("gqa.", 1)[-1])
def test_gqa_matches_fp64(device, candidate):
    _require_kernel(device, candidate.dtype)
    errors = check(candidate, device)
    assert set(errors) == {"out[0]", "grad_in[0]", "grad_in[1]", "grad_in[2]"}


def test_gqa_rejects_one_percent_output_error(device):
    _require_kernel(device, torch.float32)
    candidate = PAIRS["rotation.revantg.gqa.float32.d96.t100"]
    with pytest.raises(AssertionError, match=r"out\[0\]: rel_err="):
        check(candidate, device, fast_override=scaled(1.01))
