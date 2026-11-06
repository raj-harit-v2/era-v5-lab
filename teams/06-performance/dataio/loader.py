"""Brahmic uint32 shards or synthetic IDs; both use the real vocabulary and KE table."""
from __future__ import annotations

from pathlib import Path
import json

from dataio.tokenizer import BrahmicTokenizer, VOCAB_SIZE, REVISION, SHA256

import numpy as np
import torch

MAGIC, VERSION, HEADER_BYTES = 20261025, 2, 1024     # shard header: magic, version, token count (256 int32)
DEFAULT_DIR = "~/.cache/era-perf/fineweb-brahmic131k"


def open_shard(path: Path) -> np.memmap:
    """One shard's tokens as a read-only memmap, after checking its header and size."""
    header = np.fromfile(path, dtype="<i4", count=256)
    if len(header) != 256 or header[0] != MAGIC or header[1] != VERSION or header[2] <= 0:
        raise ValueError(f"{path}: not a Brahmic uint32 shard; prepare data again")
    if path.stat().st_size != HEADER_BYTES + int(header[2]) * 4:
        raise ValueError(f"{path}: truncated or oversized shard")
    return np.memmap(path, dtype="<u4", mode="r", offset=HEADER_BYTES, shape=(int(header[2]),))



class Loader:
    """next_batch() -> (x, y) on the device. With prefetch=True, prefetch() samples, checks and pins the next
    batch ahead of time (call it while the GPU is busy, e.g. right after backward is queued); next_batch() then
    only issues the non-blocking copy. The batches are the same with and without prefetch (same RNG order)."""

    def __init__(self, source, batch_size, block_size, device, data_dir=None, vocab_size=VOCAB_SIZE, seed=0,
                 split="train", tokenizer_path=None, prefetch=False):
        self.B, self.T = batch_size, block_size
        self.prefetch_enabled, self._next = prefetch, None
        self.source, self.device, self.vocab_size = source, torch.device(device), vocab_size
        self.pin = self.device.type == "cuda"
        self.rng = np.random.default_rng(seed)
        self.tokenizer = BrahmicTokenizer(tokenizer_path)
        if vocab_size != self.tokenizer.vocab_size:
            raise ValueError(f"model.vocab_size={vocab_size} differs from Brahmic vocabulary {self.tokenizer.vocab_size}")
        if source == "fineweb10b":
            d = Path(data_dir or DEFAULT_DIR).expanduser()
            metadata = d / "tokenizer.json.meta"
            if not metadata.exists():
                raise FileNotFoundError(f"No completed Brahmic dataset in {d}: run python -m dataio.prepare_fineweb")
            manifest = json.loads(metadata.read_text())
            if manifest != {"revision": REVISION, "sha256": SHA256, "vocab_size": vocab_size}:
                raise ValueError("Shard tokenizer metadata mismatch; prepare data again")
            paths = sorted(d.glob(f"fineweb_{split}_*.bin"))
            if not paths:
                raise FileNotFoundError(f"no fineweb_{split}_*.bin in {d}: run python -m dataio.prepare_fineweb")
            self.shards = [open_shard(p) for p in paths]
            sizes = np.array([len(s) - block_size for s in self.shards], dtype=np.float64)
            if (sizes <= 0).any():
                raise ValueError("Each shard must contain at least block_size + 1 tokens")
            self.p_shard = sizes / sizes.sum()       # pick shards in proportion to their size
        elif source != "synthetic":
            raise ValueError(f"data.source={source!r}: fineweb10b | synthetic")

    def prefetch(self):
        """Prepare the next host batch now (no-op when prefetch is off or one is already waiting)."""
        if self.prefetch_enabled and self._next is None:
            self._next = self._host_batch()

    def next_batch(self):
        """(x, y) [B, T] on the device; y is x shifted by one token."""
        buf, self._next = (self._next if self._next is not None else self._host_batch()), None
        buf = buf.to(self.device, non_blocking=True)
        return buf[:, :-1].contiguous(), buf[:, 1:].contiguous()

    def _host_batch(self):
        """[B, T + 1] int64 on the host: sampled, range-checked, pinned when the device is CUDA."""
        B, T = self.B, self.T
        if self.source == "synthetic":
            buf = torch.from_numpy(self.rng.integers(0, self.vocab_size, (B, T + 1), dtype=np.int64))
        else:
            shard = self.shards[self.rng.choice(len(self.shards), p=self.p_shard)]
            starts = self.rng.integers(0, len(shard) - T, B)
            buf = torch.from_numpy(np.stack([shard[s:s + T + 1] for s in starts]).astype(np.int64))
        if (buf >= self.vocab_size).any() or (buf < 0).any():
            raise ValueError("Batch contains IDs outside the Brahmic vocabulary")
        if self.pin:
            buf = buf.pin_memory()
        return buf

    def token_bytes(self, max_pos: int):
        """The tokenizer's KE byte table: (bytes [V, max_pos] uint8, lens [V])."""
        return self.tokenizer.token_bytes(max_pos)
