# Official sources: https://github.com/linkedin/Liger-Kernel
#                  https://github.com/apple/ml-cross-entropy
"""Cross-entropy implementations against the plain path and a CE definition.

GPT(ce_impl="chunked" or "fused") must match ce_impl="torch" for masked targets and MTP. Chunked loss tiles
positions; fused computes and caches head gradients in token chunks. Fused checks always cover CPU and cover CUDA
when available. No tokenizer is needed: the model is tiny and uses a plain embedding table.
"""
from __future__ import annotations

import pytest
import torch
import torch.nn.functional as F

from models.config import ModelConfig
from models.gpt import GPT, IGNORE_INDEX
from models.linear_ce import (linear_cross_entropy_cached, linear_cross_entropy_fused,
                              linear_cross_entropy_cce, linear_cross_entropy_liger)
from correctness.framework import Case, PAIRS, check, pair, pairs_in, rel_err, scaled

VOCAB = 97
BLOCK = 16


def _models(device, chunks, ce_impl="chunked", mtp=False):
    cfg = dict(vocab_size=VOCAB, block_size=BLOCK, n_layer=1, n_head=2, n_embd=32)
    torch.manual_seed(0)
    plain = GPT(ModelConfig(**cfg, ce_impl="torch", mtp=mtp)).to(device).train()
    candidate = GPT(ModelConfig(**cfg, ce_impl=ce_impl, ce_chunks=chunks, mtp=mtp)).to(device).train()
    candidate.load_state_dict(plain.state_dict())
    return plain, candidate


def _padded_models(device, ce_impl, mode, mtp):
    cfg = dict(vocab_size=VOCAB, block_size=BLOCK, n_layer=1, n_head=2, n_embd=32,
               vocab_pad_multiple=128, vocab_pad_mode=mode)
    torch.manual_seed(0)
    plain = GPT(ModelConfig(**cfg, ce_impl="torch", mtp=mtp)).to(device).train()
    candidate = GPT(ModelConfig(**cfg, ce_impl=ce_impl, mtp=mtp)).to(device).train()
    candidate.load_state_dict(plain.state_dict())
    return plain, candidate


def _data(device, B, T, masked=()):
    g = torch.Generator().manual_seed(1)
    idx = torch.randint(0, VOCAB, (B, T), generator=g).to(device)
    y = torch.randint(0, VOCAB, (B, T), generator=g).to(device)
    for b, t in masked:
        y[b, t] = IGNORE_INDEX
    return idx, y


def _mean_ce(logits, y):
    """Mean of -log p(target) over the non-ignored positions, from the definition, in fp64."""
    lp = torch.log_softmax(logits.double().reshape(-1, logits.shape[-1]), dim=-1)
    y = y.reshape(-1)
    keep = y != IGNORE_INDEX
    return -lp[keep, y[keep]].mean()


def _grads(model):
    return {n: p.grad.clone() for n, p in model.named_parameters() if p.grad is not None}


def _loss_and_grads(model, idx, y):
    model.zero_grad(set_to_none=True)
    loss = model(idx, y)[1]
    loss.backward()
    return loss.detach(), _grads(model)


def _same(a, b, what):
    torch.testing.assert_close(a, b, rtol=1e-5, atol=1e-6, msg=lambda m: f"{what}: {m}")


def _linear_ce_pair(device, impl, dtype=torch.float32):
    _require_official_device(device, impl)
    torch.manual_seed(140)
    x = torch.randn(5, 7, device=device, dtype=dtype, requires_grad=True)
    weight = torch.randn(23, 7, device=device, dtype=dtype, requires_grad=True)
    targets = torch.tensor([2, -100, 21, -100, 0], device=device)

    def reference(x, w, y):
        return F.cross_entropy(F.linear(x, w), y, ignore_index=-100)

    def fast(x, w, y):
        if impl == "fused":
            return linear_cross_entropy_fused(x, w, y, chunks=3, ignore_index=-100)
        if impl == "triton_cce":
            return linear_cross_entropy_cce(x, w, y, ignore_index=-100)
        if impl == "triton_liger":
            return linear_cross_entropy_liger(x, w, y, ignore_index=-100)
        raise ValueError(f"unknown CE implementation {impl!r}")

    return Case(ref=reference, fast=fast, inputs=[x, weight, targets])


def _require_official_device(device, impl):
    if impl not in ("triton_liger", "triton_cce"):
        return
    if device.type != "cuda":
        pytest.skip("official CE kernels require CUDA")
    pytest.importorskip("triton")
    if impl == "triton_cce" and torch.cuda.get_device_capability(device)[0] < 8:
        pytest.skip("official Apple CCE requires compute capability >= 8")


def _official(impl, x, weight, targets, *, bias=None):
    if impl == "triton_liger":
        return linear_cross_entropy_liger(x, weight, targets, bias=bias, ignore_index=-100)
    if impl == "triton_cce":
        return linear_cross_entropy_cce(x, weight, targets, bias=bias, ignore_index=-100)
    raise ValueError(f"unknown official CE implementation {impl!r}")


@pair("ce.fused", tol=1e-5, grad_tol=1e-4)
def _fused_pair(device):
    """The token-chunked cached-gradient implementation against the torch reference."""
    return _linear_ce_pair(device, "fused")


@pair("ce.fused.bf16", dtype=torch.bfloat16)
def _fused_bf16_pair(device):
    return _linear_ce_pair(device, "fused", torch.bfloat16)


@pair("ce.triton_liger", tol=1e-5, grad_tol=1e-4)
def _triton_liger_pair(device):
    return _linear_ce_pair(device, "triton_liger")


@pair("ce.triton_liger.bf16", dtype=torch.bfloat16)
def _triton_liger_bf16_pair(device):
    return _linear_ce_pair(device, "triton_liger", torch.bfloat16)


# Apple uses lock-based reductions; repeatability is numerical, not bitwise.
@pair("ce.triton_cce", tol=1e-5, grad_tol=1e-4, deterministic=False)
def _triton_cce_pair(device):
    return _linear_ce_pair(device, "triton_cce")


@pair("ce.triton_cce.bf16", dtype=torch.bfloat16, deterministic=False)
def _triton_cce_bf16_pair(device):
    return _linear_ce_pair(device, "triton_cce", torch.bfloat16)


MASKS = {
    "none": (),
    "scattered": ((0, 0), (0, 5), (1, 3), (1, 15)),
    "half": tuple((b, t) for b in range(2) for t in range(8)),
    "one_row": tuple((0, t) for t in range(16)),
    "one_left": tuple((b, t) for b in range(2) for t in range(16) if (b, t) != (1, 7)),
}


@pytest.mark.parametrize("mask", MASKS)
def test_chunked_matches_plain_and_definition(device, mask):
    plain, chunked = _models(device, chunks=4)
    idx, y = _data(device, 2, 16, MASKS[mask])
    with torch.no_grad():
        reference = _mean_ce(plain(idx)[0], y)         # logits of the plain model, loss from the definition
    lp, gp = _loss_and_grads(plain, idx, y)
    lc, gc = _loss_and_grads(chunked, idx, y)
    _same(lp.double(), reference, f"plain vs definition ({mask})")
    _same(lc.double(), reference, f"chunked vs definition ({mask})")
    assert gp.keys() == gc.keys()
    for name in gp:
        _same(gc[name], gp[name], f"gradient of {name} ({mask})")


@pytest.mark.parametrize("B, T, chunks", [(3, 7, 4), (1, 5, 8), (2, 16, 3), (2, 16, 32)])
def test_chunked_when_chunks_do_not_divide_the_token_count(device, B, T, chunks):
    plain, chunked = _models(device, chunks=chunks)
    idx, y = _data(device, B, T, masked=((0, 1), (B - 1, T - 1)))
    lp, gp = _loss_and_grads(plain, idx, y)
    lc, gc = _loss_and_grads(chunked, idx, y)
    _same(lc, lp, f"loss B={B} T={T} chunks={chunks}")
    for name in gp:
        _same(gc[name], gp[name], f"gradient of {name} B={B} T={T} chunks={chunks}")


def test_chunked_loss_is_zero_when_every_target_is_ignored(device):
    _, chunked = _models(device, chunks=4)
    idx, _ = _data(device, 2, 16)
    y = torch.full((2, 16), IGNORE_INDEX, device=device)
    loss, grads = _loss_and_grads(chunked, idx, y)
    assert loss.item() == 0.0, "no target counts, so the loss is 0 (the plain path gives NaN here)"
    assert all(torch.isfinite(g).all() and not g.any() for g in grads.values()), "no target, so no gradient"


def _available_test_devices():
    devices = [torch.device("cpu")]
    if torch.cuda.is_available():
        devices.append(torch.device("cuda"))
    return devices


@pytest.mark.parametrize("device", _available_test_devices(), ids=lambda d: d.type)
@pytest.mark.parametrize("mtp", [False, True], ids=["ntp", "mtp"])
@pytest.mark.parametrize("mask", ["none", "scattered", "one_row", "one_left"])
def test_fused_matches_plain_loss_and_all_gradients(device, mtp, mask):
    plain, fused = _models(device, chunks=4, ce_impl="fused", mtp=mtp)
    idx, y = _data(device, 2, 16, masked=MASKS[mask])

    plain_logits, _ = plain(idx)
    fused_logits, _ = fused(idx)
    assert fused_logits.shape == plain_logits.shape
    lp, gp = _loss_and_grads(plain, idx, y)
    lf, gf = _loss_and_grads(fused, idx, y)

    _same(lf, lp, f"fused loss ({device}, mtp={mtp}, mask={mask})")
    assert gp.keys() == gf.keys()
    for name in gp:
        _same(gf[name], gp[name], f"fused gradient of {name} ({device}, mtp={mtp}, mask={mask})")


@pytest.mark.parametrize("impl", ["triton_liger", "triton_cce"])
@pytest.mark.parametrize("mask", MASKS)
@pytest.mark.parametrize("mtp", [False, True])
def test_official_impls_match_plain_loss_and_all_gradients(device, impl, mask, mtp):
    _require_official_device(device, impl)
    plain, candidate = _models(device, chunks=4, ce_impl=impl, mtp=mtp)
    idx, y = _data(device, 2, 16, MASKS[mask])
    lp, gp = _loss_and_grads(plain, idx, y)
    lc, gc = _loss_and_grads(candidate, idx, y)
    _same(lc.double(), lp.double(), f"{impl} loss ({device}, mask={mask}, mtp={mtp})")
    assert gp.keys() == gc.keys()
    for name in gp:
        _same(gc[name], gp[name], f"{impl} gradient of {name} ({device}, mask={mask}, mtp={mtp})")


@pytest.mark.parametrize("impl", ["triton_liger", "triton_cce"])
@pytest.mark.parametrize("device", _available_test_devices(), ids=lambda d: d.type)
def test_official_impls_all_targets_ignored(device, impl):
    _require_official_device(device, impl)
    _, model = _models(device, chunks=4, ce_impl=impl)
    idx, _ = _data(device, 2, 16)
    targets = torch.full((2, 16), IGNORE_INDEX, device=device)
    logits, loss = model(idx, targets)
    assert logits is None
    assert loss.item() == 0.0
    loss.backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() and not p.grad.any()
               for p in model.parameters() if p.requires_grad)


@pytest.mark.parametrize("impl", ["triton_liger", "triton_cce"])
@pytest.mark.parametrize("vocab,hidden", [(257, 65), (131072, 64)])
def test_official_impls_large_vocab_and_hidden_tiles(device, impl, vocab, hidden):
    _require_official_device(device, impl)
    torch.manual_seed(149)
    x = torch.randn(3, hidden, device=device, requires_grad=True)
    weight = (torch.randn(vocab, hidden, device=device) * 0.02).requires_grad_()
    targets = torch.tensor([0, vocab - 1, -100], device=device)
    xr, wr = (t.detach().double().requires_grad_() for t in (x, weight))
    reference = F.cross_entropy(F.linear(xr, wr), targets, ignore_index=-100)
    actual = _official(impl, x, weight, targets)
    assert rel_err(actual, reference) < 1e-5
    for got, want in zip(torch.autograd.grad(actual, (x, weight)),
                         torch.autograd.grad(reference, (xr, wr))):
        assert rel_err(got, want) < 1e-4


def test_liger_chunk_size_heuristic_scales_and_caps_memory():
    pytest.importorskip("triton")
    from kernels.triton_liger import _token_chunk_size

    assert _token_chunk_size(4096, 256, 131072, 2) == 512
    assert _token_chunk_size(16384, 8192, 131072, 2) == 1024
    assert _token_chunk_size(16384, 8192, 131072, 4) == 512
    assert _token_chunk_size(16384, 8192, 1_000_000, 2) == 128
    assert _token_chunk_size(511, 256, 131072, 2) == 511


@pytest.mark.parametrize("tokens", [511, 512, 513, 1025])
def test_liger_512_minimum_chunk_crosses_boundaries(device, tokens):
    _require_official_device(device, "triton_liger")
    torch.manual_seed(153)
    vocab, hidden = 257, 7
    x = torch.randn(tokens, hidden, device=device, requires_grad=True)
    weight = (torch.randn(vocab, hidden, device=device) * 0.02).requires_grad_()
    targets = torch.randint(0, vocab, (tokens,), device=device)
    targets[::17] = -100
    xr, wr = (t.detach().double().requires_grad_() for t in (x, weight))
    reference = F.cross_entropy(F.linear(xr, wr), targets, ignore_index=-100)
    actual = _official("triton_liger", x, weight, targets)
    assert rel_err(actual, reference) < 1e-5
    for got, want in zip(torch.autograd.grad(actual, (x, weight)),
                         torch.autograd.grad(reference, (xr, wr))):
        assert rel_err(got, want) < 1e-4


@pytest.mark.parametrize("impl", ["triton_liger", "triton_cce"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.bfloat16, torch.float16],
                         ids=["fp32", "bf16", "fp16"])
def test_official_impls_bias_and_low_precision(device, impl, dtype):
    _require_official_device(device, impl)
    if dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("CUDA device does not support bf16")
    torch.manual_seed(151)
    x = torch.randn(5, 33, device=device, dtype=dtype, requires_grad=True)
    weight = torch.randn(97, 33, device=device, dtype=dtype, requires_grad=True)
    bias = torch.randn(97, device=device, requires_grad=True)
    targets = torch.tensor([2, -100, 21, -100, 0], device=device)
    xr, wr, br = (t.detach().double().requires_grad_() for t in (x, weight, bias))
    reference = F.cross_entropy(F.linear(xr, wr, br), targets, ignore_index=-100)
    actual = _official(impl, x, weight, targets, bias=bias)
    loss_tol, grad_tol = {
        torch.float32: (1e-5, 1e-4),
        torch.bfloat16: (1e-2, 3e-2),
        torch.float16: (5e-3, 5e-3),
    }[dtype]
    assert rel_err(actual, reference) < loss_tol
    for got, want in zip(torch.autograd.grad(actual, (x, weight, bias)),
                         torch.autograd.grad(reference, (xr, wr, br))):
        assert rel_err(got, want) < grad_tol


@pytest.mark.parametrize("impl", ["triton_liger", "triton_cce"])
@pytest.mark.parametrize("mode", ["slice", "mask"])
@pytest.mark.parametrize("mtp", [False, True], ids=["ntp", "mtp"])
def test_official_impls_with_padded_vocab(device, impl, mode, mtp):
    _require_official_device(device, impl)
    plain, candidate = _padded_models(device, impl, mode, mtp)
    idx, targets = _data(device, 2, BLOCK, masked=((0, 1), (1, 7)))
    plain.zero_grad(set_to_none=True)
    candidate.zero_grad(set_to_none=True)
    logits, reference = plain(idx, targets)
    assert logits is not None and reference is not None
    actual = candidate(idx, targets)[1]
    assert rel_err(actual, reference) < 1e-5
    reference.backward()
    actual.backward()
    ref_grads = _grads(plain)
    got_grads = _grads(candidate)
    assert ref_grads.keys() == got_grads.keys()
    for name, grad in ref_grads.items():
        assert rel_err(got_grads[name], grad) < 1e-4, name
    assert candidate.head.weight.grad[VOCAB:].abs().max() == 0
    if mtp:
        assert candidate.mtp_head.weight.grad[VOCAB:].abs().max() == 0


def test_official_impls_reject_cpu_without_fallback():
    x = torch.randn(3, 7)
    weight = torch.randn(23, 7)
    targets = torch.tensor([1, 2, 3])
    for fn in (linear_cross_entropy_liger, linear_cross_entropy_cce):
        with pytest.raises(ValueError, match="requires CUDA"):
            fn(x, weight, targets)


@pytest.mark.parametrize("impl", ["triton_liger", "triton_cce"])
def test_official_impls_reject_out_of_vocabulary_targets(device, impl):
    _require_official_device(device, impl)
    x = torch.randn(2, 7, device=device)
    weight = torch.randn(23, 7, device=device)
    for bad in (-1, 23):
        with pytest.raises(ValueError, match="outside vocabulary"):
            _official(impl, x, weight, torch.tensor([1, bad], device=device))


def test_portable_ce_rejects_invalid_chunking_and_inputs():
    x = torch.randn(2, 3)
    weight = torch.randn(5, 3)
    targets = torch.tensor([1, 2])
    with pytest.raises(ValueError, match="chunks must be positive"):
        linear_cross_entropy_fused(x, weight, targets, chunks=0)
    with pytest.raises(ValueError, match="token_chunk must be positive"):
        linear_cross_entropy_cached(x, weight, targets, token_chunk=0)
    with pytest.raises(ValueError, match="expects x"):
        linear_cross_entropy_cached(x.flatten(), weight, targets)
    with pytest.raises(ValueError, match="hidden sizes differ"):
        linear_cross_entropy_cached(x, torch.randn(5, 4), targets)
    with pytest.raises(TypeError, match="targets must"):
        linear_cross_entropy_cached(x, weight, targets.float())
    with pytest.raises(ValueError, match="target count"):
        linear_cross_entropy_cached(x, weight, torch.tensor([1]))


@pytest.mark.parametrize("device", _available_test_devices(), ids=lambda d: d.type)
@pytest.mark.parametrize("mtp", [False, True], ids=["ntp", "mtp"])
def test_fused_returns_loss_without_logits_and_handles_all_ignored_targets(device, mtp):
    _, fused = _models(device, chunks=4, ce_impl="fused", mtp=mtp)
    idx, _ = _data(device, 2, 16)
    y = torch.full((2, 16), IGNORE_INDEX, device=device)
    logits, loss = fused(idx, y)
    assert logits is None
    assert loss.item() == 0.0
    loss.backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() and not p.grad.any()
               for p in fused.parameters() if p.requires_grad)


@pytest.mark.parametrize("device", _available_test_devices(), ids=lambda d: d.type)
def test_fused_linear_cross_entropy_supports_a_bias(device):
    torch.manual_seed(4)
    x = torch.randn(7, 11, device=device, requires_grad=True)
    weight = torch.randn(37, 11, device=device, requires_grad=True)
    bias = torch.randn(37, device=device, requires_grad=True)
    targets = torch.randint(0, 37, (7,), device=device)

    reference = F.cross_entropy(F.linear(x, weight, bias), targets)
    actual = linear_cross_entropy_fused(x, weight, targets, bias=bias, chunks=3)
    reference_grads = torch.autograd.grad(reference, (x, weight, bias))
    actual_grads = torch.autograd.grad(actual, (x, weight, bias))

    _same(actual, reference, f"biased fused CE ({device})")
    for name, got, expected in zip(("x", "weight", "bias"), actual_grads, reference_grads):
        _same(got, expected, f"biased fused CE gradient {name} ({device})")


@pytest.mark.parametrize("device", _available_test_devices(), ids=lambda d: d.type)
@pytest.mark.parametrize("chunks", [1, 3, 16])
@pytest.mark.parametrize("mask", ["none", "partial", "row", "all"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.bfloat16], ids=["fp32", "bf16"])
def test_fused_token_chunk_counts_masks_and_dtypes(device, chunks, mask, dtype):
    if device.type == "cuda" and dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        pytest.skip("CUDA device does not support bf16")
    torch.manual_seed(40)
    x = torch.randn(11, 9, device=device, dtype=dtype, requires_grad=True)
    weight = torch.randn(31, 9, device=device, dtype=dtype, requires_grad=True)
    y = torch.randint(0, 31, (11,), device=device)
    if mask == "partial":
        y[1::3] = IGNORE_INDEX
    elif mask == "row":
        y[:4] = IGNORE_INDEX
    elif mask == "all":
        y.fill_(IGNORE_INDEX)
    expected = F.cross_entropy(F.linear(x, weight).float(), y, reduction="sum")
    expected = expected / (y != IGNORE_INDEX).sum().clamp_min(1)
    actual = linear_cross_entropy_fused(x, weight, y, chunks=chunks)
    want = torch.autograd.grad(expected, (x, weight))
    got = torch.autograd.grad(actual, (x, weight))
    if dtype == torch.float32:
        _same(actual, expected, "fp32 chunked loss")
        for g, w in zip(got, want):
            _same(g, w, "fp32 chunked gradient")
    else:
        torch.testing.assert_close(actual, expected, rtol=1e-3, atol=1e-4)
        for g, w in zip(got, want):
            torch.testing.assert_close(g, w, rtol=0.03, atol=0.002)
    if mask == "all":
        assert actual.item() == 0
        assert all(not g.any() for g in got)


@pytest.mark.parametrize("device", _available_test_devices(), ids=lambda d: d.type)
@pytest.mark.parametrize("amp", [False, True], ids=["native", "autocast"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.bfloat16], ids=["fp32", "bf16"])
def test_fused_matmul_dtype_saved_state_and_no_backward_recompute(device, amp, dtype, monkeypatch):
    if device.type == "cuda" and (amp or dtype == torch.bfloat16) and not torch.cuda.is_bf16_supported():
        pytest.skip("CUDA device does not support bf16")
    x = torch.randn(11, 9, device=device, dtype=dtype, requires_grad=True)
    weight = torch.randn(31, 9, device=device, dtype=dtype, requires_grad=True)
    targets = torch.randint(0, 31, (11,), device=device)
    calls, products, saved = [], [], []
    original_linear = F.linear
    original_matmul = torch.Tensor.__matmul__

    def record_linear(xc, wc, bias=None):
        out = original_linear(xc, wc, bias)
        calls.append((xc.dtype, wc.dtype, out.dtype, out.shape))
        return out

    def record_matmul(left, right):
        products.append((left.dtype, right.dtype))
        return original_matmul(left, right)

    def pack(t):
        saved.append((t.shape, t.dtype))
        return t

    monkeypatch.setattr(F, "linear", record_linear)
    monkeypatch.setattr(torch.Tensor, "__matmul__", record_matmul)
    with torch.autograd.graph.saved_tensors_hooks(pack, lambda t: t):
        with torch.autocast(device.type, dtype=torch.bfloat16, enabled=amp):
            loss = linear_cross_entropy_fused(x, weight, targets, chunks=3)
    expected_dtype = torch.bfloat16 if amp else dtype
    assert len(calls) == 3
    assert all(a == b == c == expected_dtype and shape[0] <= 4 for a, b, c, shape in calls)
    assert products == [(expected_dtype, expected_dtype)] * 6
    assert saved == [(x.shape, torch.float32), (weight.shape, torch.float32)]
    loss.backward()
    assert len(calls) == 3, "backward must return cached gradients without another head matmul"
    assert x.grad.dtype == x.dtype and weight.grad.dtype == weight.dtype


@pytest.mark.parametrize("device", _available_test_devices(), ids=lambda d: d.type)
@pytest.mark.parametrize("mtp", [False, True], ids=["ntp", "mtp"])
def test_fused_bf16_autocast_model_matches_torch(device, mtp):
    if device.type == "cuda" and not torch.cuda.is_bf16_supported():
        pytest.skip("CUDA device does not support bf16")
    plain, fused = _models(device, chunks=3, ce_impl="fused", mtp=mtp)
    idx, targets = _data(device, 2, 7, masked=((0, 0), (1, 2)))
    with torch.autocast(device.type, dtype=torch.bfloat16):
        lp, gp = _loss_and_grads(plain, idx, targets)
        lf, gf = _loss_and_grads(fused, idx, targets)
    torch.testing.assert_close(lf, lp, rtol=0.01, atol=1e-4)
    assert gp.keys() == gf.keys()
    for name in gp:
        torch.testing.assert_close(gf[name], gp[name], rtol=0.03, atol=0.002,
                                   msg=lambda m: f"bf16 model gradient {name}: {m}")


@pytest.mark.parametrize("device", _available_test_devices(), ids=lambda d: d.type)
def test_fused_pair_rejects_one_percent_error(device):
    with pytest.raises(AssertionError):
        check(PAIRS["ce.fused"], device, fast_override=scaled(1.01))


@pytest.mark.parametrize("device", _available_test_devices(), ids=lambda d: d.type)
def test_fused_gradients_respect_loss_scaling_and_repeated_backward(device):
    torch.manual_seed(43)
    x = torch.randn(11, 9, device=device, requires_grad=True)
    w = torch.randn(31, 9, device=device, requires_grad=True)
    b = torch.randn(31, device=device, requires_grad=True)
    y = torch.randint(0, 31, (11,), device=device)
    y[1::3] = IGNORE_INDEX
    expected = F.cross_entropy(F.linear(x, w, b), y)
    actual = linear_cross_entropy_fused(x, w, y, bias=b, chunks=3)
    for scale in (3.25, -0.5):
        want = torch.autograd.grad(expected * scale, (x, w, b), retain_graph=True)
        got = torch.autograd.grad(actual * scale, (x, w, b), retain_graph=True)
        for got_grad, want_grad in zip(got, want):
            _same(got_grad, want_grad, "scaled/reused cached gradient")


@pytest.mark.parametrize("name", pairs_in(__name__))
@pytest.mark.parametrize("device", _available_test_devices(), ids=lambda d: d.type)
def test_pair(name, device):
    check(PAIRS[name], device)
