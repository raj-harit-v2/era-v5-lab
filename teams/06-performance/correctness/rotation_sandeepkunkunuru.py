"""G6 Week-3 rotation (sandeepkunkunuru): fast tiled Linear Cross-Entropy vs an independent fp64 reference.

Tests both the portable fast Linear-CE paths (`models/linear_ce.py`: `cached` token-chunked gradient cache and
`cce` vocabulary-streamed log-sum-exp recompute, running on CPU and CUDA) and the 32-token-tiled Triton fused
Linear-CE kernel (`kernels/linear_ce_fused.py`: `linear_cross_entropy_fused_triton`, `BM=32, BV=128, BK=32`,
across `vocab`, `chunked`, and `recompute` backward paths on CUDA) against a standalone fp64 reference written
from the mathematical definition (never calling `F.linear`, `F.cross_entropy`, or `log_softmax`).

Regimes covered per fast backend:
  * `tail33`         N=33 (BM+1: 1 full 32-token tile + 1-row tail), H=65 (2*BK+1), V=257 (2*BV+1), with bias
                     and partial `ignore_index=-100` including the tail row check.
  * `masked_tile0`   N=64 (2*BM): tile 0 (rows 0..31) is 100% `ignore_index=-100`, tile 1 (rows 32..63) is active;
                     verifies divisor counts only active rows and masked rows get exact zero gradients.
  * `hot_target`     N=45 tokens with 75%+ hitting one hot vocabulary ID (`v_hot = V - 1`, e.g. `<|im_end|>` / EOS
                     concentration in packed SFT), stressing cross-tile `grad_weight[v_hot]` accumulation.
  * `logit_shift`    Adds large per-row constant logit offsets via bias/hidden scale to verify max-shifted LSE
                     numerical stability without overflow or underflow across streamed vocab tiles.
  * `tail33.bf16`    `tail33` in native `bfloat16` against the `fp64` reference (`TOLERANCES[bf16] = (1e-2, 3e-2)`).

Pair names start with `ce.rot.` so `conftest._pair_needs` runs them by default without `--all-configs`.
Run:
    python -m pytest teams/06-performance/correctness/rotation_sandeepkunkunuru.py -q -rs
"""
from __future__ import annotations

import pytest
import torch

from correctness.framework import PAIRS, Case, check, pair, pairs_in, rel_err, scaled
from kernels import linear_ce_fused as triton_ce_mod
from kernels.linear_ce_fused import BM, BK, BV, linear_cross_entropy_fused_triton
from models.linear_ce import linear_cross_entropy_cached, linear_cross_entropy_cce

IGNORE_INDEX = -100
SEED = 20261116

PORTABLE_BACKENDS = ("cached", "cce")
TRITON_BACKWARD_IMPLS = ("vocab", "chunked", "recompute")


# ------------------------------------------------------------------------------ standalone fp64 reference

def ref_linear_ce_fp64(
    x: torch.Tensor,
    weight: torch.Tensor,
    bias: torch.Tensor | None,
    targets: torch.Tensor,
    ignore_index: int = IGNORE_INDEX,
) -> torch.Tensor:
    """Mean cross-entropy of a linear head from first principles in fp64 (no F.linear / F.cross_entropy)."""
    x64 = x.to(torch.float64)
    w64 = weight.to(torch.float64)
    logits = x64 @ w64.transpose(0, 1)
    if bias is not None:
        logits = logits + bias.to(torch.float64).unsqueeze(0)

    valid = targets != ignore_index
    n_valid = int(valid.sum().item())
    if n_valid == 0:
        return (logits * 0.0).sum()

    row_max = logits.max(dim=-1, keepdim=True).values
    shifted = logits - row_max
    log_z = row_max.squeeze(-1) + torch.log(torch.exp(shifted).sum(dim=-1))

    safe_y = torch.where(valid, targets, torch.zeros_like(targets))
    picked = logits.gather(1, safe_y.unsqueeze(1)).squeeze(1)
    nll = torch.where(valid, log_z - picked, torch.zeros_like(log_z))
    return nll.sum() / float(n_valid)


# ------------------------------------------------------------------------------ fast backend runners

def _require_triton_cuda(device: torch.device) -> None:
    if device.type != "cuda" or triton_ce_mod.triton is None:
        pytest.skip("triton_ce requires CUDA and Triton; portable CPU/CUDA CE pairs still run")


def _run_portable(backend: str, x: torch.Tensor, w: torch.Tensor, b: torch.Tensor | None, y: torch.Tensor):
    if backend == "cached":
        return linear_cross_entropy_cached(x, w, y, bias=b, token_chunk=17, ignore_index=IGNORE_INDEX)
    if backend == "cce":
        return linear_cross_entropy_cce(x, w, y, bias=b, vocab_chunk=71, ignore_index=IGNORE_INDEX)
    raise ValueError(f"unknown portable backend {backend}")


def _run_triton(bwd_impl: str, x: torch.Tensor, w: torch.Tensor, b: torch.Tensor | None, y: torch.Tensor):
    return linear_cross_entropy_fused_triton(
        x,
        w,
        y,
        bias=b,
        ignore_index=IGNORE_INDEX,
        backward_impl=bwd_impl,
        token_chunk=BM,       # 32-token chunks matching PR #77 BM=32
        vocab_chunk=BV,       # 128-vocab chunks matching BV=128 so multi-chunk streaming always triggers
    )


# ------------------------------------------------------------------------------ scenario builders

def _make_scenario(kind: str, device: torch.device):
    """Deterministic fp32 base inputs on `device`; `framework.check` casts ref->fp64 and fast->pair.dtype."""
    g = torch.Generator(device="cpu").manual_seed(SEED + abs(hash(kind)) % 10_000)

    if kind == "tail33":
        # BM+1 = 33 tokens (1 full 32-row tile + 1 single-row tail), 2*BK+1 = 65 hidden, 2*BV+1 = 257 vocab
        n, h, v = BM + 1, 2 * BK + 1, 2 * BV + 1
        x = (torch.randn(n, h, generator=g) * 0.5).to(device).requires_grad_(True)
        w = (torch.randn(v, h, generator=g) * 0.25).to(device).requires_grad_(True)
        b = (torch.randn(v, generator=g) * 0.1).to(device).requires_grad_(True)
        y = torch.randint(0, v, (n,), generator=g).to(device)
        y[0] = IGNORE_INDEX
        y[15] = IGNORE_INDEX
        y[BM - 1] = v - 1     # last row of tile 0 hits last vocab element (2*BV)
        y[BM] = 0             # single-row tail tile (row 32) is active and hits class 0
        return x, w, b, y

    if kind == "masked_tile0":
        # 2*BM = 64 tokens: tile 0 (rows 0..31) completely masked, tile 1 (rows 32..63) active
        n, h, v = 2 * BM, BK + 7, BV + 19
        x = (torch.randn(n, h, generator=g) * 0.4).to(device).requires_grad_(True)
        w = (torch.randn(v, h, generator=g) * 0.3).to(device).requires_grad_(True)
        b = (torch.randn(v, generator=g) * 0.1).to(device).requires_grad_(True)
        y = torch.randint(0, v, (n,), generator=g).to(device)
        y[:BM] = IGNORE_INDEX
        return x, w, b, y

    if kind == "hot_target":
        # 45 tokens across 2 tiles where >75% target the same hot token (v - 1)
        n, h, v = BM + 13, 2 * BK + 3, 2 * BV + 5
        x = (torch.randn(n, h, generator=g) * 0.5).to(device).requires_grad_(True)
        w = (torch.randn(v, h, generator=g) * 0.2).to(device).requires_grad_(True)
        b = (torch.randn(v, generator=g) * 0.05).to(device).requires_grad_(True)
        y = torch.full((n,), v - 1, dtype=torch.long)
        # Sprinkle a few non-hot and ignored tokens across both tiles
        y[3] = 0
        y[17] = BV
        y[29] = IGNORE_INDEX
        y[BM + 4] = 7
        y = y.to(device)
        return x, w, b, y

    if kind == "logit_shift":
        # Large positive bias offset (+60) plus mixed sign structure: softmax / CE must be shift-invariant
        n, h, v = BM + 5, BK + 11, BV + 33
        x = (torch.randn(n, h, generator=g) * 0.6).to(device).requires_grad_(True)
        w = (torch.randn(v, h, generator=g) * 0.4).to(device).requires_grad_(True)
        b_cpu = torch.randn(v, generator=g) * 0.5 + 60.0
        b = b_cpu.to(device).requires_grad_(True)
        y = torch.randint(0, v, (n,), generator=g).to(device)
        y[7] = IGNORE_INDEX
        return x, w, b, y

    raise ValueError(f"unknown scenario {kind}")


# ------------------------------------------------------------------------------ pair registrations

SCENARIOS = ("tail33", "masked_tile0", "hot_target", "logit_shift")


def _register_portable(backend: str, scenario: str, dtype: torch.dtype = torch.float32):
    suffix = f"{scenario}.bf16" if dtype == torch.bfloat16 else scenario
    name = f"ce.rot.{backend}.{suffix}"

    @pair(name, dtype=dtype)
    def _build(device, backend=backend, scenario=scenario):
        x, w, b, y = _make_scenario(scenario, device)
        return Case(
            ref=lambda a, wt, bs, tg: ref_linear_ce_fp64(a, wt, bs, tg),
            fast=lambda a, wt, bs, tg: _run_portable(backend, a, wt, bs, tg),
            inputs=[x, w, b, y],
        )


def _register_triton(bwd_impl: str, scenario: str, dtype: torch.dtype = torch.float32):
    suffix = f"{scenario}.bf16" if dtype == torch.bfloat16 else scenario
    name = f"ce.rot.triton_{bwd_impl}.{suffix}"

    @pair(name, dtype=dtype)
    def _build(device, bwd_impl=bwd_impl, scenario=scenario):
        _require_triton_cuda(device)
        x, w, b, y = _make_scenario(scenario, device)
        return Case(
            ref=lambda a, wt, bs, tg: ref_linear_ce_fp64(a, wt, bs, tg),
            fast=lambda a, wt, bs, tg: _run_triton(bwd_impl, a, wt, bs, tg),
            inputs=[x, w, b, y],
        )


for _b in PORTABLE_BACKENDS:
    for _sc in SCENARIOS:
        _register_portable(_b, _sc, torch.float32)
    _register_portable(_b, "tail33", torch.bfloat16)

for _impl in TRITON_BACKWARD_IMPLS:
    for _sc in ("tail33", "masked_tile0", "hot_target"):
        _register_triton(_impl, _sc, torch.float32)
    _register_triton(_impl, "tail33", torch.bfloat16)


PAIR_NAMES = pairs_in(__name__)
FP32_PAIRS = [n for n in PAIR_NAMES if PAIRS[n].dtype == torch.float32]


# ------------------------------------------------------------------------------ framework pair & drill tests

def test_registered_pairs_count():
    # 2 portable * (4 fp32 + 1 bf16) = 10 portable pairs; 3 triton * (3 fp32 + 1 bf16) = 12 triton pairs
    assert len(PAIR_NAMES) == 22


@pytest.mark.parametrize("name", PAIR_NAMES)
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    assert "out[0]" in errors
    # x, w, b all require grad -> grad_in[0], grad_in[1], grad_in[2] must all be checked
    for idx in (0, 1, 2):
        assert f"grad_in[{idx}]" in errors, f"{name}: missing grad_in[{idx}] check"


@pytest.mark.parametrize("name", FP32_PAIRS)
def test_pair_fails_the_1_01_drill(name, device):
    with pytest.raises(AssertionError, match=r"out\[0\]: rel_err="):
        check(PAIRS[name], device, fast_override=scaled(1.01))


# ------------------------------------------------------------------------------ structural & mutation checks

@pytest.mark.parametrize("backend", PORTABLE_BACKENDS)
def test_masked_tile0_gives_exact_zero_input_grads_portable(backend, device):
    """Rows 0..BM-1 are all ignore_index=-100: their dx rows must be exact zeros, while active rows are nonzero."""
    x, w, b, y = _make_scenario("masked_tile0", device)
    loss = _run_portable(backend, x, w, b, y)
    loss.backward()
    assert torch.count_nonzero(x.grad[:BM]) == 0, f"{backend}: masked tile 0 leaked non-zero dx"
    assert torch.count_nonzero(x.grad[BM:]) > 0, f"{backend}: active tile 1 has zero dx"


@pytest.mark.parametrize("bwd_impl", TRITON_BACKWARD_IMPLS)
def test_masked_tile0_gives_exact_zero_input_grads_triton(bwd_impl, device):
    """Same exact-zero masked-tile check on the BM=32 Triton kernel across all backward modes."""
    _require_triton_cuda(device)
    x, w, b, y = _make_scenario("masked_tile0", device)
    loss = _run_triton(bwd_impl, x, w, b, y)
    loss.backward()
    assert torch.count_nonzero(x.grad[:BM]) == 0, f"triton_{bwd_impl}: masked tile 0 leaked non-zero dx"
    assert torch.count_nonzero(x.grad[BM:]) > 0, f"triton_{bwd_impl}: active tile 1 has zero dx"


def test_dropping_single_tail_row_is_rejected(device):
    """Mutation check: if a fast path accidentally drops or masks the 33rd (BM+1) tail row, check() rejects it."""
    p = PAIRS["ce.rot.cached.tail33"]

    def buggy_fast_override(fast_fn):
        def wrapped(a, wt, bs, tg):
            tg_mut = tg.clone()
            tg_mut[BM] = IGNORE_INDEX  # silently drop the 1-token tail tile
            return fast_fn(a, wt, bs, tg_mut)
        return wrapped

    with pytest.raises(AssertionError, match=r"rel_err=.* > tol="):
        check(p, device, fast_override=buggy_fast_override)


def test_portable_and_triton_agree_on_all_masked_zero_loss_and_grads(device):
    """When 100% of rows across multiple tiles are ignore_index=-100, loss and every gradient are exact 0."""
    x, w, b, y = _make_scenario("tail33", device)
    y_all_masked = torch.full_like(y, IGNORE_INDEX)

    ref_loss = ref_linear_ce_fp64(x, w, b, y_all_masked)
    assert ref_loss.item() == 0.0

    for backend in PORTABLE_BACKENDS:
        xi, wi, bi = (t.detach().clone().requires_grad_(True) for t in (x, w, b))
        loss = _run_portable(backend, xi, wi, bi, y_all_masked)
        loss.backward()
        assert loss.item() == 0.0
        assert all(torch.count_nonzero(t.grad) == 0 for t in (xi, wi, bi))

    if device.type == "cuda" and triton_ce_mod.triton is not None:
        for bwd_impl in TRITON_BACKWARD_IMPLS:
            xi, wi, bi = (t.detach().clone().requires_grad_(True) for t in (x, w, b))
            loss = _run_triton(bwd_impl, xi, wi, bi, y_all_masked)
            loss.backward()
            assert loss.item() == 0.0
            assert all(torch.count_nonzero(t.grad) == 0 for t in (xi, wi, bi))
            assert rel_err(loss, ref_loss) == 0.0
