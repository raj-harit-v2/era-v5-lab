"""Original G5 implementation of Team 4's public #765 KAS V2 contract."""

import hashlib
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .kas_terms import correction_row_dropout, initialize_unigram_
from .unigram import load_counts

TEAMS = Path(__file__).resolve().parents[3]
FIXTURE = TEAMS / "04-ke2/fixtures/kas_v2/kas_v2_fixture.npz"
FIXTURE_SHA = "1d77a48ed3fc1e2609dcb9eb91a2036f9ca773613f7a4b4be45d4c198b7cd50f"
COUNTS_SHA = "0768b5982825645a796abc76ec23c737837cfacc8f6b089335e5ce5446def3a6"
TOKENIZER_SHA = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"


def checked_rows(rows, lengths):
    rows = torch.as_tensor(rows).clone()
    lengths = torch.as_tensor(lengths).clone()
    if rows.dtype != torch.uint8 or lengths.is_floating_point() or lengths.dtype == torch.bool:
        raise ValueError("KAS needs raw uint8 bytes and integer lengths")
    lengths = lengths.long()
    if rows.ndim != 2 or rows.shape[1] > 32 or lengths.shape != (len(rows),):
        raise ValueError("KAS requires a byte table with at most 32 positions and one length per ID")
    if bool(((lengths <= 0) | (lengths > rows.shape[1])).any()):
        raise ValueError("KAS token lengths must be in [1, 32] without truncation")
    return rows, lengths


class KASCodec(nn.Module):
    """Fixed public G/Phi constants; canonical construction uses float64."""

    def __init__(self):
        super().__init__()
        if hashlib.sha256(FIXTURE.read_bytes()).hexdigest() != FIXTURE_SHA:
            raise ValueError("KAS V2 public fixture hash mismatch")
        with np.load(FIXTURE, allow_pickle=False) as source:
            self.register_buffer("G", torch.from_numpy(source["G"].copy()))
            self.register_buffer("Phi", torch.from_numpy(source["Phi"].copy()))

    def _apply(self, fn, recurse=True):
        # Model precision conversion must preserve the exact fixed codebook.
        original = {name: value for name, value in self._buffers.items()}
        super()._apply(fn, recurse=recurse)
        for name, value in original.items():
            self._buffers[name] = value.to(device=self._buffers[name].device, dtype=torch.float64)
        return self

    def positions(self, rows, lengths):
        p = rows.shape[-1]
        valid = torch.arange(p, device=rows.device) < lengths[..., None]
        values = self.G[rows.long()] * valid[..., None]
        values = values / lengths.double().sqrt()[..., None, None]
        return F.pad(values.transpose(-1, -2), (0, 32 - p))

    def codes(self, rows, lengths):
        # Canonical diagnostic/export representation matches the public NumPy
        # fingerprint. Training projects byte occupancy directly on device below.
        shape = rows.shape[:-1]
        raw = rows.detach().cpu().numpy().reshape(-1, rows.shape[-1])
        lens = lengths.detach().cpu().numpy().reshape(-1)
        values = self.G.detach().cpu().numpy()[raw] / np.sqrt(lens)[:, None, None]
        valid = np.arange(raw.shape[1])[None, :] < lens[:, None]
        values = np.where(valid[:, :, None], values, 0.0)
        positions = np.zeros((len(raw), 64, 32), dtype=np.float64)
        positions[:, :, :raw.shape[1]] = values.transpose(0, 2, 1)
        codes = (positions @ self.Phi.detach().cpu().numpy()).reshape(*shape, 2048)
        return torch.from_numpy(codes).to(rows.device)


class KASInput(nn.Module):
    def __init__(self, rows, lengths, width, codec):
        super().__init__()
        rows, lengths = checked_rows(rows, lengths)
        self.register_buffer("rows", rows)
        self.register_buffer("lengths", lengths)
        # The model owns the shared fixed codec once, with no parameter tying.
        object.__setattr__(self, "codec", codec)
        self.projection = nn.Linear(2048, width, bias=False)
        nn.init.normal_(self.projection.weight, std=2048 ** -0.5)

    def forward(self, ids):
        shape = ids.shape
        flat = ids.reshape(-1)
        rows, lengths = self.rows[flat], self.lengths[flat]
        with torch.autocast(device_type=ids.device.type, enabled=False):
            weight = self.projection.weight
            # K @ W is evaluated via a position/byte lookup, without allocating
            # token x 2048 codes or token x position x model-width gathers.
            rotated = torch.einsum("pk,dck->pcd", self.codec.Phi.to(weight.dtype), weight.reshape(-1, 64, 32))
            lookup = torch.einsum("bc,pcd->pbd", self.codec.G.to(weight.dtype), rotated).reshape(8192, -1)
            valid = torch.arange(rows.shape[1], device=ids.device)[None, :] < lengths[:, None]
            indices = (torch.arange(rows.shape[1], device=ids.device)[None, :] * 256 + rows.long())[valid]
            offsets = F.pad(lengths.cumsum(0), (1, 0))
            scales = lengths.to(weight.dtype).rsqrt().repeat_interleave(lengths)
            output = F.embedding_bag(indices, lookup, offsets, mode="sum", per_sample_weights=scales,
                                     include_last_offset=True)
        return output.reshape(*shape, self.projection.out_features)


class KASHead(nn.Module):
    def __init__(self, rows, lengths, width, codec):
        super().__init__()
        rows, lengths = checked_rows(rows, lengths)
        object.__setattr__(self, "codec", codec)
        self.out_features = len(rows)
        self.in_features = width
        self.tok_dropout = 0.05
        self.W_out = nn.Parameter(torch.randn(width, 2048) * 2048 ** -0.5)
        self.beta = nn.Parameter(torch.ones(33))
        self.unigram = nn.Parameter(torch.zeros(len(rows)))
        self.tok_u = nn.Parameter(torch.randn(len(rows), 64) * (0.02 * 64 ** -0.5))
        self.tok_c = nn.Parameter(torch.randn(64, width) * width ** -0.5)
        valid = torch.arange(rows.shape[1])[None, :] < lengths[:, None]
        indices = torch.arange(rows.shape[1])[None, :] * 256 + rows.long()
        self.register_buffer("indices", indices[valid], persistent=False)
        self.register_buffer("offsets", F.pad(lengths.cumsum(0), (1, 0)), persistent=False)
        self.register_buffer("lengths", lengths, persistent=False)
        # Keep canonical double weights for float64 parity and cast at use.
        self.register_buffer("scales", lengths.double().rsqrt().repeat_interleave(lengths), persistent=False)

    def forward(self, hidden):
        shape = hidden.shape[:-1]
        with torch.autocast(device_type=hidden.device.type, enabled=False):
            h = hidden.reshape(-1, self.in_features).to(self.W_out.dtype)
            position_scores = (h @ self.W_out).reshape(-1, 64, 32)
            byte_scores = torch.einsum("ncp,bc->npb", position_scores, self.codec.G.to(h.dtype))
            scores = F.embedding_bag(
                self.indices, byte_scores.flatten(1).t().contiguous(), self.offsets,
                mode="sum", per_sample_weights=self.scales.to(h.dtype), include_last_offset=True,
            ).t()
            correction = correction_row_dropout(self.tok_u, probability=self.tok_dropout, training=self.training)
            logits = scores * self.beta[self.lengths] + self.unigram + (h @ self.tok_c.t()) @ correction.t()
        return logits.reshape(*shape, self.out_features)


def initialize_prior(head, settings):
    """Use the public raw counts unless the config explicitly adapts EOS."""
    defaults = {
        "path": "03-tokenizer/counts/p1536_counts.json",
        "sha256": COUNTS_SHA,
        "tokenizer_sha256": TOKENIZER_SHA,
        "add_eos_per_document": False,
    }
    settings = {**defaults, **settings}
    extra = set(settings) - set(defaults)
    if extra:
        raise ValueError("Unsupported KAS prior settings: " + str(sorted(extra)))
    path = Path(settings["path"])
    if not path.is_absolute():
        path = TEAMS / path
    counts = load_counts(path, expected_sha256=settings["sha256"],
                         expected_tokenizer_sha256=settings["tokenizer_sha256"],
                         expected_vocab_size=head.out_features, checksum_mode="lf")
    return initialize_unigram_(head.unigram, counts, add_eos_per_document=settings["add_eos_per_document"])


@torch.no_grad()
def checkpoint_probe(model):
    """Match Team 9/10's seeded mean-NLL probe without consuming training RNG."""
    training = model.training
    device = next(model.parameters()).device
    vocab = model.head.out_features
    ids = torch.randint(0, vocab, (2, 32), generator=torch.Generator().manual_seed(1234)).to(device)
    try:
        model.eval()
        logits = model(ids, torch.ones_like(ids, dtype=torch.bool))
        return float(F.cross_entropy(logits[:, :-1].reshape(-1, vocab).float(), ids[:, 1:].reshape(-1)))
    finally:
        model.train(training)
