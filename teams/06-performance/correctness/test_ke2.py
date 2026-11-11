"""Kronecker Embedding v2 (models/ke2.py) against G4's dense fp64 encoder (teams/04-ke2/src/ke2/codec.py encode_f64).

Pairs: "ke2" (random table), "ke2.edge" (awkward tokens), "ke2.g4_table" (G4's committed table, sampled IDs) and
"ke2.bf16"; outputs and the projection gradient. The reference shares no code with the fast embedding_bag path.
"""
from __future__ import annotations

import pytest
import torch

from correctness.framework import PAIRS, Case, check, pair, pairs_in
from models.ke2 import N_BYTES, KE2Embedding, load_g4_table

parametrize = pytest.mark.parametrize    # see test_ke.py: a decorator at the start of a line trips pr-guard

P = 32                    # byte positions per token (ke_max_pos); the code has D = 256 * P = 8192 columns
D_MODEL = 64
VOCAB = 512
B, T = 2, 37
G4_VOCAB = 131072


def encode_f64(tb, lens, ids):
    """[len(ids), 256 * P] fp64 from G4's ke2.codec.encode_f64 (models.ke2 puts teams/04-ke2/src on sys.path)."""
    from ke2.codec import encode_f64 as g4_encode_f64
    flat = ids.reshape(-1).cpu()
    return torch.from_numpy(g4_encode_f64(tb[flat].numpy(), lens[flat].numpy(), P))


def make_case(token_bytes, ids_fn, vocab=VOCAB, autocast=False):
    """A Case: the fast KE2Embedding (fp32 or bf16 autocast) against the fp64 dense reference, same weights."""

    def build(device):
        tb, lens = token_bytes()
        fast = KE2Embedding(vocab, D_MODEL, P, (tb, lens)).to(device)
        w_ref = fast.proj.weight.detach().double().clone().requires_grad_(True)
        ids = ids_fn().to(device)

        def ref(i):
            return (encode_f64(tb, lens, i).to(i.device) @ w_ref.T).view(*i.shape, D_MODEL)

        def fast_fn(i):
            with torch.autocast(device.type, dtype=torch.bfloat16, enabled=autocast):
                return fast(i)

        return Case(ref=ref, fast=fast_fn, inputs=[ids], params_ref=[w_ref], params_fast=[fast.proj.weight])

    return build


def random_table():
    """Random bytes, lengths 1..8 like real BPE tokens."""
    g = torch.Generator().manual_seed(0)
    return (torch.randint(0, N_BYTES, (VOCAB, P), generator=g, dtype=torch.uint8),
            torch.randint(1, 9, (VOCAB,), generator=g))


def random_ids():
    g = torch.Generator().manual_seed(1)
    return torch.randint(0, VOCAB, (B, T), generator=g)


def edge_table():
    tb = torch.zeros(6, P, dtype=torch.uint8)
    lens = torch.tensor([1, P, P, P, 3, 5])
    tb[0, 0] = 0x61                                  # a single byte
    tb[1, :] = 0                                     # P bytes, all 0x00
    tb[2, :] = 255                                   # P bytes, all 0xFF: the last columns of W
    tb[3, :] = torch.arange(P, dtype=torch.uint8)    # P distinct bytes
    tb[4, :3] = 7                                    # the same byte in three slots
    tb[5, :5] = torch.tensor([200, 1, 200, 1, 200], dtype=torch.uint8)
    return tb, lens


def edge_ids():
    return torch.tensor([[0, 1, 2, 3, 4, 5, 5, 0], [3, 3, 2, 1, 5, 4, 0, 2]])


def g4_table():
    return load_g4_table(G4_VOCAB, P)


def g4_ids():
    """Sampled IDs plus the ends of the vocabulary and the longest tokens (L = P)."""
    tb, lens = g4_table()
    g = torch.Generator().manual_seed(2)
    longest = torch.nonzero(lens == int(lens.max())).flatten()[:4]
    ids = torch.cat([torch.randint(0, G4_VOCAB, (B * T - 6,), generator=g), torch.tensor([0, G4_VOCAB - 1]), longest])
    return ids[: B * T].view(B, T)


pair("ke2")(make_case(random_table, random_ids))
pair("ke2.edge")(make_case(edge_table, edge_ids, vocab=6))
pair("ke2.g4_table")(make_case(g4_table, g4_ids, vocab=G4_VOCAB))
pair("ke2.bf16", dtype=torch.bfloat16)(make_case(random_table, random_ids, autocast=True))


@parametrize("name", pairs_in(__name__))
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    assert "out[0]" in errors and "grad_param[0]" in errors, "the output and the projection gradient must be compared"


def test_g4_table_is_the_tokenizer():
    """G4's raw table has exactly our tokenizer's token bytes (needs the pinned tokenizer.json)."""
    try:
        from dataio.tokenizer import BrahmicTokenizer
        tok = BrahmicTokenizer()
    except Exception as e:                                     # offline and no local tokenizer.json
        pytest.skip(f"tokenizer not available: {e}")
    tb, lens = tok.token_bytes(P)
    g4_tb, g4_lens = g4_table()
    assert torch.equal(lens.long(), g4_lens)
    mask = torch.arange(P) < lens.unsqueeze(1)
    assert torch.equal(tb[mask], g4_tb[mask])


def test_keeps_leading_dims_and_dtype():
    m = KE2Embedding(VOCAB, D_MODEL, P, random_table())
    out = m(torch.zeros(3, 4, 5, dtype=torch.long))
    assert out.shape == (3, 4, 5, D_MODEL) and out.dtype == torch.float32


def test_bad_tables_fail():
    tb, lens = random_table()
    with pytest.raises(AssertionError):
        KE2Embedding(VOCAB, D_MODEL, P, (tb[:, :8], lens))      # wrong width
    with pytest.raises(AssertionError):
        KE2Embedding(VOCAB, D_MODEL, P, (tb, lens * 0))         # empty tokens
    with pytest.raises(ValueError):
        load_g4_table(1000, P)                                  # vocabulary size does not match the table
