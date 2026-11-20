"""Frozen bf16 KE2 codes: a compact per-length form, a streamed (V, D) matrix, and their hashes.

By Lemma 1 a token of L bytes has the code ``low[L]`` everywhere and ``high[L]`` on its L support
cells (byte ``b`` at position ``p`` is cell ``b * P + p``). Cast to bf16, the whole ``(V, D)``
matrix therefore follows from two things:

* the **compact codes** ``high_bits[L]``, ``low_bits[L]`` for ``L = 0 .. P`` (bf16 bit patterns
  stored as uint16; numpy has no bf16 dtype), and
* the **raw byte table** (``ke2.tables``), which gives every token's bytes and L.

The compact codes are taken from the upstream float32 ``kronecker_codec`` output cast with
``.to(torch.bfloat16)`` (round to nearest even), the same route as ``margins/pair_margins.py``.
:func:`stream_rows` rebuilds the matrix in chunks from (compact codes, raw table), so neither the
builder nor the checks ever hold the 2 GiB matrix (P = 32) in memory.

Hashes
------
``codes_sha256``   ``ke2-bf16-codes-v1|P|char_dim|tokenizer_sha256|raw_table_sha256|`` + high bits
                   + low bits (uint16 little-endian). Bound to the tokenizer and to the raw table.
``matrix_sha256``  SHA-256 of the row-major little-endian bf16 bytes of the ``(V, D)`` matrix, no
                   header: ``hashlib.sha256(m.view(torch.int16).numpy().tobytes())`` reproduces it.
``row_hashes_sha256``  SHA-256 of the ``(V, 32)`` array of per-row SHA-256 digests, in id order.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import CHAR_DIM
from .tables import ByteTable, TableContractError
from .tokenizer import TokenizerBundle

BF16_FORMAT_VERSION = 1
BF16_FORMAT = f"ke2-bf16-codes-v{BF16_FORMAT_VERSION}"


def codes_content_sha256(
    pos_dim: int, char_dim: int, tokenizer_sha256: str, raw_table_sha256: str, high_bits, low_bits
) -> str:
    """Content hash of the compact codes, bound to the tokenizer and the raw table (module docstring)."""
    h = hashlib.sha256(f"{BF16_FORMAT}|{pos_dim}|{char_dim}|{tokenizer_sha256}|{raw_table_sha256}|".encode())
    h.update(np.ascontiguousarray(high_bits, dtype="<u2").tobytes())
    h.update(np.ascontiguousarray(low_bits, dtype="<u2").tobytes())
    return h.hexdigest()


def bits_to_float(bits) -> np.ndarray:
    """bf16 bit patterns (uint16) to float64 values (exact: bf16 is the top half of an fp32)."""
    b = np.asarray(bits, dtype=np.uint16).astype(np.uint32) << 16
    return b.view(np.float32).astype(np.float64)


def float_to_bits(values) -> np.ndarray:
    """Round float64 values to bf16 (nearest even, as torch does) and return the bit patterns."""
    import torch

    t = torch.as_tensor(np.asarray(values, dtype=np.float64)).to(torch.bfloat16)
    return t.view(torch.int16).numpy().view(np.uint16).copy()


def codec_bf16_bits(byte_rows: np.ndarray, lengths: np.ndarray, pos_dim: int, char_dim: int = CHAR_DIM) -> np.ndarray:
    """Upstream float32 ``kronecker_codec`` output cast to bf16, as uint16 bits, shape ``(n, D)``."""
    import torch
    from kronecker_embeddings.codec import kronecker_codec

    out = kronecker_codec(
        torch.from_numpy(np.ascontiguousarray(byte_rows, dtype=np.uint8)),
        torch.from_numpy(np.asarray(lengths, dtype=np.int64)),
        char_dim=char_dim,
        pos_dim=pos_dim,
    )
    return out.to(torch.bfloat16).view(torch.int16).numpy().view(np.uint16)


def expand(byte_rows: np.ndarray, lengths: np.ndarray, high_bits, low_bits, pos_dim: int, char_dim: int = CHAR_DIM):
    """Materialise bf16 rows (uint16 bits, ``(n, D)``) from bytes, lengths and the compact codes."""
    lengths = np.asarray(lengths, dtype=np.int64)
    high_bits, low_bits = np.asarray(high_bits, np.uint16), np.asarray(low_bits, np.uint16)
    out = np.repeat(low_bits[lengths][:, None], char_dim * pos_dim, axis=1)
    rows, cols = np.nonzero(np.arange(pos_dim)[None, :] < lengths[:, None])
    out[rows, np.asarray(byte_rows)[rows, cols].astype(np.int64) * pos_dim + cols] = high_bits[lengths[rows]]
    return out


def compact_from_codec(pos_dim: int, char_dim: int = CHAR_DIM) -> tuple[np.ndarray, np.ndarray]:
    """``(high_bits, low_bits)`` for ``L = 0 .. P``, read from the codec on one probe string per length.

    The probe for length L is ``b"a" * L``. Each probe row is checked to be exactly the two-valued
    row :func:`expand` predicts; the vocabulary pass in :func:`stream_rows` then checks every token.
    """
    lengths = np.arange(pos_dim + 1, dtype=np.int64)
    probes = np.zeros((pos_dim + 1, pos_dim), dtype=np.uint8)
    probes[np.arange(pos_dim)[None, :] < lengths[:, None]] = ord("a")
    bits = codec_bf16_bits(probes, lengths, pos_dim, char_dim)
    high = np.zeros(pos_dim + 1, np.uint16)
    low = bits[:, 0].copy()  # cell 0 is byte 0x00 at position 0: never lit by a probe
    for L in range(1, pos_dim + 1):
        high[L] = bits[L, ord("a") * pos_dim]
    high[0] = low[0]  # the empty string: one value everywhere
    if not np.array_equal(bits, expand(probes, lengths, high, low, pos_dim, char_dim)):
        raise TableContractError("codec output for a probe string is not two-valued as Lemma 1 predicts")
    return high, low


@dataclass
class Bf16Codes:
    """Compact bf16 codes plus the provenance that binds them to one tokenizer and raw table."""

    pos_dim: int
    char_dim: int
    high_bits: np.ndarray  # uint16 (P + 1,), index L
    low_bits: np.ndarray  # uint16 (P + 1,), index L
    tokenizer_sha256: str
    raw_table_sha256: str
    vocab_size: int
    matrix_sha256: str = ""
    row_hashes_sha256: str = ""

    @property
    def output_dim(self) -> int:
        return self.char_dim * self.pos_dim

    @property
    def high(self) -> np.ndarray:
        return bits_to_float(self.high_bits)

    @property
    def low(self) -> np.ndarray:
        return bits_to_float(self.low_bits)

    def sha256(self) -> str:
        return codes_content_sha256(
            self.pos_dim, self.char_dim, self.tokenizer_sha256, self.raw_table_sha256, self.high_bits, self.low_bits
        )

    def check_table(self, table: ByteTable) -> None:
        """Refuse a raw table other than the one these codes were built from."""
        if table.kind != "raw" or table.pos_dim != self.pos_dim:
            raise TableContractError(f"need the raw table at P={self.pos_dim}, got {table.kind} P={table.pos_dim}")
        if table.tokenizer_sha256 != self.tokenizer_sha256:
            raise TableContractError(
                f"raw table is for tokenizer {table.tokenizer_sha256[:12]}…, codes for {self.tokenizer_sha256[:12]}…"
            )
        if table.sha256() != self.raw_table_sha256:
            raise TableContractError(f"raw table {table.sha256()[:12]}… != recorded {self.raw_table_sha256[:12]}…")

    def save(self, path: Path) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        digest = self.sha256()
        np.savez_compressed(
            path,
            format=np.array(BF16_FORMAT),
            high_bits=self.high_bits.astype(np.uint16),
            low_bits=self.low_bits.astype(np.uint16),
            pos_dim=np.int64(self.pos_dim),
            char_dim=np.int64(self.char_dim),
            vocab_size=np.int64(self.vocab_size),
            tokenizer_sha256=np.array(self.tokenizer_sha256),
            raw_table_sha256=np.array(self.raw_table_sha256),
            codes_sha256=np.array(digest),
            matrix_sha256=np.array(self.matrix_sha256),
            row_hashes_sha256=np.array(self.row_hashes_sha256),
        )
        return digest

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        tokenizer: TokenizerBundle | None = None,
        tokenizer_sha256: str | None = None,
        allow_unverified: bool = False,
    ) -> Bf16Codes:
        """Load and verify (content hash always; tokenizer unless ``allow_unverified``), like ``ByteTable.load``."""
        with np.load(path, allow_pickle=False) as z:
            if str(z["format"]) != BF16_FORMAT:
                raise TableContractError(f"{path}: format {z['format']}, expected {BF16_FORMAT}")
            c = cls(
                pos_dim=int(z["pos_dim"]),
                char_dim=int(z["char_dim"]),
                high_bits=z["high_bits"].astype(np.uint16),
                low_bits=z["low_bits"].astype(np.uint16),
                tokenizer_sha256=str(z["tokenizer_sha256"]),
                raw_table_sha256=str(z["raw_table_sha256"]),
                vocab_size=int(z["vocab_size"]),
                matrix_sha256=str(z["matrix_sha256"]),
                row_hashes_sha256=str(z["row_hashes_sha256"]),
            )
            recorded = str(z["codes_sha256"])
        if c.sha256() != recorded:
            raise TableContractError(f"{path}: codes hash {c.sha256()[:12]}… != recorded {recorded[:12]}…")
        if tokenizer is not None:
            tokenizer_sha256 = tokenizer.sha256
        if tokenizer_sha256 is not None:
            if tokenizer_sha256 != c.tokenizer_sha256:
                raise TableContractError(
                    f"codes were built for tokenizer {c.tokenizer_sha256[:12]}…, caller has {tokenizer_sha256[:12]}…"
                )
        elif not allow_unverified:
            raise TableContractError("Bf16Codes.load needs tokenizer= or tokenizer_sha256=, or allow_unverified=True")
        return c


def codes_for_table(table: ByteTable) -> Bf16Codes:
    """Compact bf16 codes for a raw table (hashes of the matrix are filled in by :func:`stream_rows`)."""
    if table.kind != "raw":
        raise TableContractError("bf16 codes are built from the raw table only")
    high, low = compact_from_codec(table.pos_dim)
    return Bf16Codes(
        pos_dim=table.pos_dim,
        char_dim=CHAR_DIM,
        high_bits=high,
        low_bits=low,
        tokenizer_sha256=table.tokenizer_sha256,
        raw_table_sha256=table.sha256(),
        vocab_size=table.vocab_size,
    )


@dataclass
class StreamResult:
    matrix_sha256: str
    row_digests: np.ndarray  # uint8 (V, 32): SHA-256 of each row's bf16 bytes

    @property
    def row_hashes_sha256(self) -> str:
        return hashlib.sha256(self.row_digests.tobytes()).hexdigest()


def iter_rows(codes: Bf16Codes, table: ByteTable, *, chunk_rows: int = 1024) -> Iterator[tuple[int, np.ndarray]]:
    """Yield ``(first_id, bits)`` chunks of the bf16 matrix, rebuilt from the compact codes."""
    codes.check_table(table)
    for start in range(0, table.vocab_size, chunk_rows):
        stop = min(start + chunk_rows, table.vocab_size)
        yield (
            start,
            expand(table.bytes[start:stop], table.lengths[start:stop], codes.high_bits, codes.low_bits, codes.pos_dim),
        )


def stream_rows(
    codes: Bf16Codes,
    table: ByteTable,
    *,
    chunk_rows: int = 1024,
    verify_codec: bool = False,
    out: np.ndarray | None = None,
) -> StreamResult:
    """Hash every row of the bf16 matrix (and the whole matrix) without holding it in memory.

    ``verify_codec``: also run the upstream codec on every token and require its bf16 output to equal
    the rebuilt rows bit for bit (the builder does this; the checks rebuild from the artifact alone).
    ``out``: a ``(V, D)`` uint16 array (e.g. a ``np.lib.format.open_memmap``) to write the matrix into.
    """
    whole = hashlib.sha256()
    digests = np.empty((table.vocab_size, 32), dtype=np.uint8)
    for start, bits in iter_rows(codes, table, chunk_rows=chunk_rows):
        stop = start + bits.shape[0]
        if verify_codec:
            ref = codec_bf16_bits(table.bytes[start:stop], table.lengths[start:stop], codes.pos_dim, codes.char_dim)
            if not np.array_equal(ref, bits):
                bad = start + int(np.flatnonzero((ref != bits).any(axis=1))[0])
                raise TableContractError(f"token {bad}: codec bf16 row differs from the compact codes")
        le = np.ascontiguousarray(bits, dtype="<u2")
        whole.update(le.tobytes())
        for i in range(le.shape[0]):
            digests[start + i] = np.frombuffer(hashlib.sha256(le[i].tobytes()).digest(), np.uint8)
        if out is not None:
            out[start:stop] = bits
    return StreamResult(whole.hexdigest(), digests)
