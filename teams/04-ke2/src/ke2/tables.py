"""Per-token byte tables: the input of the Kronecker codec.

``decode`` table  upstream behaviour (``decode([id])`` then UTF-8). Partial-character tokens become
                  U+FFFD and share one row: the known issue, kept as the baseline.
``raw`` table     the fix: exact token bytes from the inverted ByteLevel alphabet.

A table is a ``(V, P)`` uint8 array plus ``(V,)`` int16 lengths, bound to the SHA-256 of the
``tokenizer.json`` it came from and to a content hash that is re-verified on every load.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import CHAR_DIM, HF_ID, POS_DIMS, TOKENIZER_SHA256
from .tokenizer import (
    U_FFFD,
    TokenizerBundle,
    VocabHoleError,
    decode_bytes_for_id,
    raw_bytes_for_id,
)
from .truncation import TruncateRule, byte_truncate, continuation_truncate

log = logging.getLogger(__name__)

TABLE_FORMAT_VERSION = 2
"""Bump whenever the on-disk layout or the hashing rule changes."""

KINDS = ("decode", "raw")


class TableContractError(RuntimeError):
    """A byte table failed an integrity or compatibility check."""


def table_content_sha256(kind: str, pos_dim: int, byte_rows: np.ndarray, lengths: np.ndarray) -> str:
    """Content hash of a table: ``ke2-table-v2|kind|P|`` + bytes (uint8) + lengths (int16)."""
    h = hashlib.sha256(f"ke2-table-v{TABLE_FORMAT_VERSION}|{kind}|{pos_dim}|".encode())
    h.update(np.ascontiguousarray(byte_rows, dtype=np.uint8).tobytes())
    h.update(np.ascontiguousarray(lengths, dtype=np.int16).tobytes())
    return h.hexdigest()


@dataclass
class ByteTable:
    """A ``(V, P)`` byte table plus the provenance needed to trust it.

    * ``tokenizer_sha256``: the table is valid only with that exact ``tokenizer.json``.
    * :meth:`sha256`: content hash, stored on save and re-verified on load.
    * :meth:`load` refuses to return a table unless the caller names the tokenizer it is for
      (``tokenizer=`` or ``tokenizer_sha256=``) or opts out with ``allow_unverified=True``.
    """

    kind: str
    pos_dim: int
    bytes: np.ndarray  # uint8 (V, P)
    lengths: np.ndarray  # int16 (V,)
    n_truncated: int
    n_fffd_rows: int  # rows containing EF BF BD
    n_empty_rows: int = 0  # rows with L == 0; they all share the zero code
    tokenizer_sha256: str = ""

    @property
    def vocab_size(self) -> int:
        return int(self.bytes.shape[0])

    def row(self, tid: int) -> bytes:
        """The bytes of token ``tid`` (without padding)."""
        return self.bytes[tid, : int(self.lengths[tid])].tobytes()

    def sha256(self) -> str:
        return table_content_sha256(self.kind, self.pos_dim, self.bytes, self.lengths)

    def check_tokenizer(self, tokenizer_sha256: str) -> None:
        if not self.tokenizer_sha256:
            raise TableContractError("table carries no tokenizer_sha256; rebuild it with build_tables.py")
        if tokenizer_sha256 != self.tokenizer_sha256:
            raise TableContractError(
                f"table was built for tokenizer {self.tokenizer_sha256[:12]}… but caller has "
                f"{tokenizer_sha256[:12]}… — rebuild the table for this tokenizer"
            )

    def check_integrity(self, expected_sha256: str) -> None:
        actual = self.sha256()
        if actual != expected_sha256:
            raise TableContractError(
                f"table content hash {actual[:12]}… != recorded {expected_sha256[:12]}… (file corrupted?)"
            )

    def save(self, path: Path) -> str:
        """Write the table and its contract to ``path`` (compressed .npz); return the content hash."""
        if not self.tokenizer_sha256:
            raise TableContractError("refusing to save a table without tokenizer_sha256")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        digest = self.sha256()
        np.savez_compressed(
            path,
            bytes=self.bytes,
            lengths=self.lengths,
            pos_dim=np.int64(self.pos_dim),
            kind=np.array(self.kind),
            format_version=np.int64(TABLE_FORMAT_VERSION),
            tokenizer_sha256=np.array(self.tokenizer_sha256),
            table_sha256=np.array(digest),
            n_truncated=np.int64(self.n_truncated),
            n_empty_rows=np.int64(self.n_empty_rows),
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
    ) -> ByteTable:
        """Load and verify a table (see the class docstring for the contract)."""
        with np.load(path, allow_pickle=False) as z:
            fmt = int(z["format_version"]) if "format_version" in z else 1
            if fmt != TABLE_FORMAT_VERSION:
                raise TableContractError(
                    f"{path}: table format v{fmt}, expected v{TABLE_FORMAT_VERSION}; rebuild with build_tables.py"
                )
            t = cls(
                kind=str(z["kind"]),
                pos_dim=int(z["pos_dim"]),
                bytes=z["bytes"],
                lengths=z["lengths"],
                n_truncated=int(z["n_truncated"]),
                n_fffd_rows=-1,
                n_empty_rows=int(z["n_empty_rows"]),
                tokenizer_sha256=str(z["tokenizer_sha256"]),
            )
            recorded = str(z["table_sha256"])
        t.check_integrity(recorded)
        if tokenizer is not None:
            tokenizer_sha256 = tokenizer.sha256
        if tokenizer_sha256 is not None:
            t.check_tokenizer(tokenizer_sha256)
        elif not allow_unverified:
            raise TableContractError(
                "ByteTable.load needs tokenizer= or tokenizer_sha256= to verify the table, or allow_unverified=True"
            )
        t.n_fffd_rows = sum(U_FFFD in t.row(i) for i in range(t.vocab_size))
        return t


def _fill(
    rows: Iterable[bytes],
    vocab_size: int,
    pos_dim: int,
    kind: str,
    truncate: TruncateRule,
    *,
    strict: bool,
    tokenizer_sha256: str,
) -> ByteTable:
    buf = np.zeros((vocab_size, pos_dim), dtype=np.uint8)
    lens = np.zeros((vocab_size,), dtype=np.int16)
    n_trunc = n_fffd = n_empty = 0
    for tid, raw in enumerate(rows):
        if len(raw) > pos_dim:
            raw = truncate(raw, pos_dim)
            n_trunc += 1
        length = len(raw)
        if length:
            buf[tid, :length] = np.frombuffer(raw, dtype=np.uint8, count=length)
        else:
            n_empty += 1
            if strict:
                raise VocabHoleError(
                    f"token id {tid} yields an empty byte string in the {kind} table; "
                    "all empty rows collide on the zero vector"
                )
        lens[tid] = length
        if U_FFFD in raw:
            n_fffd += 1
    return ByteTable(kind, pos_dim, buf, lens, n_trunc, n_fffd, n_empty, tokenizer_sha256)


def build_decode_table(tb: TokenizerBundle, pos_dim: int, *, strict: bool = False) -> ByteTable:
    """Baseline table (upstream semantics). Not strict: empty rows are counted, not refused."""
    rows = (decode_bytes_for_id(tb, i) for i in range(tb.vocab_size))
    return _fill(
        rows, tb.vocab_size, pos_dim, "decode", continuation_truncate, strict=strict, tokenizer_sha256=tb.sha256
    )


def build_raw_table(tb: TokenizerBundle, pos_dim: int, *, strict: bool = True) -> ByteTable:
    """Fixed table: exact token bytes. Strict by default: a hole or an empty token is an error."""
    rows = (raw_bytes_for_id(tb, i, missing_ok=not strict) for i in range(tb.vocab_size))
    return _fill(rows, tb.vocab_size, pos_dim, "raw", byte_truncate, strict=strict, tokenizer_sha256=tb.sha256)


BUILDERS = {"decode": build_decode_table, "raw": build_raw_table}


def table_path(out_dir: Path, kind: str, pos_dim: int) -> Path:
    return Path(out_dir) / f"{kind}_table_P{pos_dim}.npz"


def load_table(out_dir: Path, kind: str, pos_dim: int, tb: TokenizerBundle) -> ByteTable:
    """Load a saved table verified against ``tb`` (the sanctioned way to load one)."""
    return ByteTable.load(table_path(out_dir, kind, pos_dim), tokenizer=tb)


def build_all(tb: TokenizerBundle, out_dir: Path, pos_dims: Sequence[int] = POS_DIMS) -> dict:
    """Build, save and describe both tables for every P; write ``manifest.json``; return the manifest."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "format_version": TABLE_FORMAT_VERSION,
        "tokenizer": {
            "file": tb.path.name,
            "sha256": tb.sha256,
            "vocab_size": tb.vocab_size,
            "added_tokens": len(tb.added),
            "special_ids": len(tb.special_ids),
        },
        "char_dim": CHAR_DIM,
        "tables": {},
    }
    if tb.sha256 == TOKENIZER_SHA256:
        manifest["tokenizer"]["hf_id"] = HF_ID
    raw_lens = [len(raw_bytes_for_id(tb, i)) for i in range(tb.vocab_size)]  # raises on holes
    manifest["max_raw_byte_length"] = int(max(raw_lens))
    for P in pos_dims:
        for kind in KINDS:
            t = BUILDERS[kind](tb, P)
            p = table_path(out_dir, kind, P)
            digest = t.save(p)
            unique = len({t.row(i) for i in range(t.vocab_size)})
            manifest["tables"][p.name] = {
                "kind": kind,
                "pos_dim": P,
                "shape": list(t.bytes.shape),
                "ke2_output_dim": CHAR_DIM * P,
                "n_truncated": t.n_truncated,
                "n_empty_rows": t.n_empty_rows,
                "n_rows_containing_U+FFFD": t.n_fffd_rows,
                "n_unique_rows": unique,
                "n_colliding_tokens": t.vocab_size - unique,
                "tokenizer_sha256": t.tokenizer_sha256,
                "sha256": digest,
            }
            log.info(
                "[%-6s P=%2d] shape=%s truncated=%d empty=%d U+FFFD rows=%d unique rows=%d/%d sha256=%s…",
                kind, P, t.bytes.shape, t.n_truncated, t.n_empty_rows, t.n_fffd_rows, unique, t.vocab_size,
                digest[:12],
            )  # fmt: skip
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
