"""Kronecker Embedding v1 (input side), drop-in for nn.Embedding.

Ported from https://github.com/theschoolofai/kronecker-embeddings (codec.py, embedding.py; Apache-2.0,
Copyright 2026 The School of AI). Same maths and defaults; the constructor takes our byte table, not a tokenizer.

Definition (correctness/test_ke.py is written from this):
    kappa(t) = (1/sqrt(L)) * sum_p onehot256(b_p) (x) onehot_P(p)        D = 256 * P (P = 32: 8192)
    index of byte b at slot p = b * P + p;  L = number of bytes (truncated to P)
    kappa is then z-normalised per token: (kappa - mean) / (std + 1e-6)  (std with Bessel correction)
    embedding(t) = W @ kappa(t),  W learned [d_model, D], no bias, init normal(0, 1/sqrt(D)).

Byte table (the data contract, used by tests too): (bytes [V, P] uint8, lens [V] int64); bytes past lens[t]
are ignored; lens >= 1.

Modes: dynamic recomputes the codec every forward (default); cached precomputes the [V, D] table
(4 GiB fp32 at V = 131072). Both give the same output.
"""
from __future__ import annotations

import math

import torch
import torch.nn as nn

from perfkit.regions import region

N_BYTES = 256
MODES = ("dynamic", "cached")


def token_bytes_random(vocab_size: int, max_pos: int = 32, seed: int = 0):
    """Synthetic byte table for tests and offline runs (lengths 1..8, like real BPE tokens)."""
    g = torch.Generator().manual_seed(seed)
    tb = torch.randint(0, N_BYTES, (vocab_size, max_pos), generator=g, dtype=torch.uint8)
    lens = torch.randint(1, 9, (vocab_size,), generator=g)
    return tb, lens


def kronecker_codec(byte_seqs: torch.Tensor, lens: torch.Tensor, pos_dim: int = 32,
                    length_normalize: bool = True, z_normalize: bool = True, eps: float = 1e-6) -> torch.Tensor:
    """byte_seqs [N, pos_dim] uint8/long, lens [N] -> [N, 256 * pos_dim] fp32 (upstream kronecker_codec)."""
    N, dev = byte_seqs.size(0), byte_seqs.device
    pos = torch.arange(pos_dim, device=dev).unsqueeze(0).expand(N, -1)
    lin_idx = byte_seqs.long() * pos_dim + pos          # column of byte b at slot p
    lens = lens.long()
    src = (pos < lens.unsqueeze(1)).float()             # 1 on the token's bytes, 0 past its length
    if length_normalize:
        src = src * torch.rsqrt(lens.clamp_min(1).float()).unsqueeze(1)
    out = torch.zeros((N, N_BYTES * pos_dim), device=dev, dtype=torch.float32)
    out.scatter_add_(1, lin_idx, src)
    if z_normalize:                                   # in place: same values as upstream, 1 temporary less
        out.sub_(out.mean(dim=-1, keepdim=True))
        out.div_(out.std(dim=-1, keepdim=True) + eps)
    return out


class KroneckerEmbedding(nn.Module):
    """The fixed Kronecker codec of each token's bytes, then a learned projection to d_model."""

    def __init__(self, token_bytes, d_model: int, max_pos: int = 32, mode: str = "dynamic"):
        super().__init__()
        assert mode in MODES, f"KE mode {mode!r} not in {MODES}"
        tb, lens = token_bytes
        assert tb.dim() == 2 and tb.size(1) == max_pos, f"byte table must be [V, {max_pos}], got {tuple(tb.shape)}"
        self.max_pos, self.mode, self.D = max_pos, mode, N_BYTES * max_pos
        self.register_buffer("byte_table", tb.to(torch.uint8), persistent=False)
        self.register_buffer("lens", lens.to(torch.int64), persistent=False)
        self.proj = nn.Linear(self.D, d_model, bias=False)
        nn.init.normal_(self.proj.weight, mean=0.0, std=1.0 / math.sqrt(self.D))
        if mode == "cached":
            with torch.no_grad():
                self.register_buffer("codec_table", kronecker_codec(self.byte_table, self.lens, max_pos),
                                     persistent=False)

    def codec(self, idx: torch.Tensor) -> torch.Tensor:
        """idx [...] -> kappa [..., D] fp32."""
        flat = idx.reshape(-1)
        if self.mode == "cached":
            out = self.codec_table.index_select(0, flat)
        else:
            out = kronecker_codec(self.byte_table.index_select(0, flat), self.lens.index_select(0, flat),
                                  self.max_pos)
        return out.view(*idx.shape, self.D)

    def forward(self, idx: torch.Tensor) -> torch.Tensor:
        with region("embed.ke", 3):
            return self.proj(self.codec(idx).to(self.proj.weight.dtype))
