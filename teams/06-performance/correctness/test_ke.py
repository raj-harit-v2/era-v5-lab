"""Kronecker Embedding v1 (models/ke1.py) against an fp64 codec built byte by byte from its docstring definition.

  * one @pair per mode in models.ke1.MODES ("ke1.<mode>"), outputs and the projection gradient
  * ".edge" pairs on awkward tokens: one byte, exactly P bytes, all 0x00, all 0xFF, repeats
  * properties: the modes agree, rows are z-normalised, bytes past lens[t] are ignored, bad arguments fail
The 1.01 drill and determinism check run on every pair in test_framework.py. The source byte table is tested in
test_tokenizer.py.
"""
from __future__ import annotations

import math

import pytest
import torch

from correctness.framework import PAIRS, Case, check, pair, pairs_in, rel_err
from models.ke1 import MODES, N_BYTES, KroneckerEmbedding, kronecker_codec, token_bytes_random

P = 32                    # byte positions per token (ke_max_pos); the codec has D = 256 * P = 8192 columns
D_MODEL = 64
VOCAB = 512
B, T = 2, 37              # T is not a power of 2, like the attention pairs


# ------------------------------------------------------------------------------ the reference

def reference_codec(byte_table, lens, ids, pos_dim=P, eps=1e-6):
    """fp64 kappa(t) for each id, built one byte at a time from the models/ke1.py definition; shares no code with
    kronecker_codec. Returns [len(ids), 256 * pos_dim] fp64 (CPU)."""
    rows = []
    for t in ids.tolist():
        n_bytes = min(int(lens[t]), pos_dim)             # docstring: L = number of bytes, truncated to P
        kappa = torch.zeros(N_BYTES * pos_dim, dtype=torch.float64)
        for p in range(n_bytes):
            kappa[int(byte_table[t, p]) * pos_dim + p] += 1.0 / math.sqrt(n_bytes)
        # std with Bessel correction (n - 1), as torch.Tensor.std and the upstream implementation do
        rows.append((kappa - kappa.mean()) / (kappa.std() + eps))
    return torch.stack(rows)


def make_case(mode, token_bytes, ids_fn):
    """A Case: the fast KroneckerEmbedding (fp32) against the fp64 reference, both with the same weights."""

    def build(device):
        tb, lens = token_bytes()
        fast = KroneckerEmbedding((tb, lens), D_MODEL, P, mode).to(device)
        # The reference gets its OWN copy of the projection weight (fp64), so its gradient is separate from the
        # fast module's. params_ref / params_fast below are what check() compares, one by one.
        w_ref = fast.proj.weight.detach().double().clone().requires_grad_(True)
        ids = ids_fn().to(device)

        def ref(i):
            kappa = reference_codec(tb, lens, i.reshape(-1).cpu()).to(i.device)      # [N, D] fp64, no grad needed
            return (kappa @ w_ref.T).view(*i.shape, D_MODEL)

        return Case(ref=ref, fast=fast, inputs=[ids], params_ref=[w_ref], params_fast=[fast.proj.weight])

    return build


def make_bf16_case(mode):
    """A Case: the fast module under bf16 autocast against the same fp64 reference (TOLERANCES[bfloat16])."""

    def build(device):
        tb, lens = random_table()
        fast = KroneckerEmbedding((tb, lens), D_MODEL, P, mode).to(device)
        w_ref = fast.proj.weight.detach().double().clone().requires_grad_(True)
        ids = random_ids().to(device)

        def ref(i):
            kappa = reference_codec(tb, lens, i.reshape(-1).cpu()).to(i.device)
            return (kappa @ w_ref.T).view(*i.shape, D_MODEL)

        def fast_fn(i):
            with torch.autocast(device.type, dtype=torch.bfloat16):
                return fast(i)

        return Case(ref=ref, fast=fast_fn, inputs=[ids], params_ref=[w_ref], params_fast=[fast.proj.weight])

    return build


def random_table():
    return token_bytes_random(VOCAB, P)


def random_ids():
    g = torch.Generator().manual_seed(1)
    return torch.randint(0, VOCAB, (B, T), generator=g)


def edge_table():
    """Six tokens chosen to break a careless implementation. lens >= 1 and <= P (the tokenizer guarantees it)."""
    tb = torch.zeros(6, P, dtype=torch.uint8)
    lens = torch.tensor([1, P, P, P, 3, 5])
    tb[0, 0] = 0x61                                  # a single byte
    tb[1, :] = 0                                     # P bytes, all 0x00: every byte lands in row 0 of the codec
    tb[2, :] = 255                                   # P bytes, all 0xFF: the last row of the codec
    tb[3, :] = torch.arange(P, dtype=torch.uint8)    # P distinct bytes 0..31
    tb[4, :3] = 7                                    # the same byte three times (different slots, no collision)
    tb[5, :5] = torch.tensor([200, 1, 200, 1, 200], dtype=torch.uint8)   # bytes that come back in other slots
    return tb, lens


def edge_ids():
    return torch.tensor([[0, 1, 2, 3, 4, 5, 5, 0], [3, 3, 2, 1, 5, 4, 0, 2]])     # repeats on purpose


# One pair per mode and per table. Looping over MODES means a new mode (the planned "sparse") is tested the
# moment it is added to models.ke1.MODES. tol and grad_tol are the fp32 defaults of framework.TOLERANCES
# (1e-5 outputs, 5e-5 gradients), so these pairs are in the 1.01x drill like every fp32 pair.
for _mode in MODES:
    pair(f"ke1.{_mode}")(make_case(_mode, random_table, random_ids))
    pair(f"ke1.{_mode}.edge")(make_case(_mode, edge_table, edge_ids))
    # bf16 autocast pair, like moe.<d>.bf16 in test_moe.py: tolerances from TOLERANCES[bfloat16], kept out
    # of the 1.01 drill (a bf16 tolerance cannot catch a 1% error, framework.py: TOLERANCES).
    pair(f"ke1.{_mode}.bf16", dtype=torch.bfloat16)(make_bf16_case(_mode))


@pytest.mark.parametrize("name", pairs_in(__name__))
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    assert "out[0]" in errors and "grad_param[0]" in errors, "the output and the projection gradient must be compared"


def test_one_pair_per_mode_and_table():
    assert sorted(pairs_in(__name__)) == sorted(f"ke1.{m}{s}" for m in MODES for s in ("", ".edge", ".bf16"))


# ------------------------------------------------------------------------------ properties

def _module(mode, device="cpu", table=random_table):
    return KroneckerEmbedding(table(), D_MODEL, P, mode).to(device)


def test_dynamic_and_cached_agree(device):
    dyn = _module("dynamic", device)
    cached = _module("cached", device)
    cached.proj.weight.data.copy_(dyn.proj.weight.data)          # only the weights differ otherwise
    ids = random_ids().to(device)
    # Both modes build the codec with the same function, but "cached" builds it once for the whole vocabulary
    # and "dynamic" for the batch only. On a GPU the mean / std reductions of the z-normalisation can then add up
    # in a different order, so the answers agree to fp32 rounding (about 1e-7), not bit for bit. We found this
    # by running it: torch.equal passed on the CPU and failed on the GPU.
    assert rel_err(dyn(ids), cached(ids)) < 1e-6


@pytest.mark.parametrize("mode", MODES)
def test_codec_rows_are_z_normalised(mode, device):
    ke = _module(mode, device)
    kappa = ke.codec(random_ids().to(device))                    # [B, T, D]
    assert kappa.shape == (B, T, N_BYTES * P)
    mean, std = kappa.mean(dim=-1), kappa.std(dim=-1)
    assert mean.abs().max() < 1e-6
    # std is divided by (std + 1e-6), so it is 1 up to about 1e-4 (the raw std of a row is about 0.011).
    assert (std - 1).abs().max() < 2e-4


@pytest.mark.parametrize("mode", MODES)
def test_bytes_past_lens_are_ignored(mode, device):
    tb, lens = random_table()
    tb2 = tb.clone()
    for t in range(VOCAB):                                      # scribble over every byte past lens[t]
        tb2[t, int(lens[t]):] = 255 - tb[t, int(lens[t]):]
    a = KroneckerEmbedding((tb, lens), D_MODEL, P, mode).to(device)
    b = KroneckerEmbedding((tb2, lens), D_MODEL, P, mode).to(device)
    b.proj.weight.data.copy_(a.proj.weight.data)
    ids = random_ids().to(device)
    assert torch.equal(a(ids), b(ids))                          # the contract in ke1.py: bytes past lens ignored


@pytest.mark.parametrize("mode", MODES)
def test_the_same_id_gives_the_same_vector(mode, device):
    ke = _module(mode, device)
    idx = torch.tensor([[5, 9, 5]], device=device)
    kappa = ke.codec(idx)
    assert torch.equal(kappa[0, 0], kappa[0, 2]) and not torch.equal(kappa[0, 0], kappa[0, 1])
    out = ke(idx)
    # In a batched GEMM (e.g. oneDNN on CPU), rows 0 and 2 of the batch can accumulate the 8192-wide
    # dot product in slightly different registers, differing by ~1 ULP (~5e-7) despite identical codec rows.
    assert rel_err(out[0, 0], out[0, 2]) < 1e-6 and rel_err(out[0, 0], out[0, 1]) > 0.1


def test_real_brahmic_tokenizer_byte_table_codec(device):
    from dataio.tokenizer import BrahmicTokenizer, VOCAB_SIZE
    tb, lens = BrahmicTokenizer().token_bytes(P)
    assert tb.shape == (VOCAB_SIZE, P) and lens.shape == (VOCAB_SIZE,)
    # Boundary and multilingual token IDs from the 131072-token Brahmic vocabulary.
    ids = torch.tensor([[0, 1, 66526, 2420, 13092, 732, VOCAB_SIZE - 1]], device=device)
    ref = reference_codec(tb, lens, ids.reshape(-1).cpu(), P).to(device)
    dyn = KroneckerEmbedding((tb, lens), D_MODEL, P, "dynamic").to(device)
    assert rel_err(dyn.codec(ids).reshape(-1, N_BYTES * P), ref) < 1e-6


@pytest.mark.parametrize("mode", MODES)
def test_leading_dimensions_are_kept(mode, device):
    ke = _module(mode, device)
    for shape in ((7,), (2, 3), (2, 3, 4)):
        ids = torch.randint(0, VOCAB, shape, device=device)
        assert ke(ids).shape == (*shape, D_MODEL)


def test_projection_has_no_bias_and_the_documented_init():
    ke = _module("dynamic")
    assert ke.proj.bias is None
    # init: normal(0, 1/sqrt(D)). With 64 x 8192 weights the sample std is within a few percent of that.
    assert ke.proj.weight.std().item() == pytest.approx(1 / math.sqrt(N_BYTES * P), rel=0.05)


def test_constructor_guards():
    with pytest.raises(AssertionError, match="not in"):
        KroneckerEmbedding(random_table(), D_MODEL, P, "nonsense")
    tb, lens = random_table()
    with pytest.raises(AssertionError, match="byte table"):
        KroneckerEmbedding((tb[:, :16], lens), D_MODEL, P, "dynamic")   # table is [V, 16], max_pos says 32


# ------------------------------------------------------------------------------ a contract gap, recorded

@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    "models/ke1.py says L is 'the number of bytes (truncated to P)', but kronecker_codec uses the raw lens in "
    "1/sqrt(L) when lens > P (it differs by about 2e-4 for L = 40, P = 32). The tokenizer refuses tokens longer "
    "than ke_max_pos, so real runs never reach this; fix the code or the docstring, then remove this xfail."))
def test_a_token_longer_than_P_is_normalised_with_L_truncated_to_P():
    tb = torch.randint(0, 256, (1, P), dtype=torch.uint8)
    lens = torch.tensor([40])
    got = kronecker_codec(tb, lens, P)[0].double()
    ref = reference_codec(tb, lens, torch.tensor([0]))[0]       # the docstring definition: L = min(40, 32)
    assert (got - ref).abs().max() < 1e-6
