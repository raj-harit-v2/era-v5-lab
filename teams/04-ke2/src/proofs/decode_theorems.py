"""Decode helpers for proof.md Theorem 2 (exact structural decode) and Theorem 3 (nearest-code cosine).

The codec is the public V1 Kronecker codec (``kronecker_embeddings``), as in Lemma 1 and Theorem 1.

  THETA                fixed cut-off of the structural decoder (Theorem 2)
  decode_structural    one vector -> byte string, or None (invalid)
  decode_structural_batch
                       many vectors at once; the same answers as decode_structural row by row
  error_room           delta = min(high - theta, theta - low) over string lengths (Theorem 2 (b))
  match_count          m(a, b): positions where two strings have the same byte
  closed_form_cosine   cosine of two codes from (La, Lb, m) alone (Theorem 3)
  worst_case_cosine    the largest cosine between two different strings of at most L_max bytes (Theorem 3 (c))
  guarantee_cosine     sqrt((1 + c*) / 2): above it, nearest-code decoding is certain (Theorem 3 (d))

Needs the ``ke2`` package (teams/04-ke2/src) on the import path; tests/conftest.py and the entry points arrange it.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ke2.codec import code_values

THETA = 8.0
CHAR_DIM = 256

__all__ = [
    "THETA", "closed_form_cosine", "decode_structural", "decode_structural_batch", "error_room",
    "guarantee_cosine", "match_count", "worst_case_cosine",
]  # fmt: skip


def _as_rows(vectors: Any) -> np.ndarray:
    """A 2-D float array view of numpy or torch input (bf16 is widened exactly to float32)."""
    if hasattr(vectors, "detach"):
        vectors = vectors.detach().float().cpu().numpy()
    q = np.asarray(vectors)
    return q[None, :] if q.ndim == 1 else q


def decode_structural(q: Any, pos_dim: int, theta: float = THETA) -> bytes | None:
    """Theorem 2's decoder for one vector: the cells above theta must be one per position 0..L-1.

    Returns the byte string (b"" if no cell is above theta), or None if the cells above theta are not
    a valid pattern. Uses only comparisons with theta and integer arithmetic.
    """
    return decode_structural_batch(q, pos_dim, theta)[0]


def decode_structural_batch(vectors: Any, pos_dim: int, theta: float = THETA) -> list[bytes | None]:
    """decode_structural for every row of an (N, 256 * pos_dim) array."""
    q = _as_rows(vectors)
    if q.shape[1] != CHAR_DIM * pos_dim:
        raise ValueError(f"expected width {CHAR_DIM * pos_dim}, got {q.shape[1]}")
    rows, cells = np.nonzero(q > theta)  # row-major: grouped by row, cells ascending
    out: list[bytes | None] = [b""] * q.shape[0]
    if rows.size == 0:
        return out
    starts = np.flatnonzero(np.r_[True, rows[1:] != rows[:-1]])
    ends = np.r_[starts[1:], rows.size]
    for s, e in zip(starts.tolist(), ends.tolist(), strict=True):
        c = cells[s:e]
        pos = c % pos_dim
        n = e - s
        by_pos = np.full(n, -1, dtype=np.int64)
        if pos.max() >= n:  # a position outside 0..n-1 means a gap or an extra cell
            out[int(rows[s])] = None
            continue
        if np.unique(pos).size != n:  # two cells at one position
            out[int(rows[s])] = None
            continue
        by_pos[pos] = c // pos_dim
        out[int(rows[s])] = bytes(by_pos.tolist())
    return out


def error_room(pos_dim: int, max_len: int | None = None, theta: float = THETA, eps: float = 1e-6) -> float:
    """delta = min over L in 1..max_len of min(high(L) - theta, theta - low(L)) (Theorem 2 (b))."""
    max_len = pos_dim if max_len is None else max_len
    high, low = code_values(np.arange(1, max_len + 1), pos_dim, eps=eps)
    return float(min((high - theta).min(), (theta - low).min()))


def match_count(a: bytes, b: bytes) -> int:
    """m(a, b): the number of positions where a and b have the same byte."""
    return sum(1 for x, y in zip(a, b, strict=False) if x == y)


def closed_form_cosine(La: Any, Lb: Any, m: Any, pos_dim: int) -> Any:
    """cos(code(a), code(b)) = (m / sqrt(La Lb) - sqrt(La Lb) / D) / sqrt((1 - La/D)(1 - Lb/D)), D = 256 P.

    Exact for non-empty strings of at most pos_dim bytes; does not depend on eps. Works on arrays.
    """
    D = float(CHAR_DIM * pos_dim)
    La, Lb, m = (np.asarray(x, dtype=np.float64) for x in (La, Lb, m))
    s = np.sqrt(La * Lb)
    return (m / s - s / D) / np.sqrt((1.0 - La / D) * (1.0 - Lb / D))


def worst_case_cosine(max_len: int, pos_dim: int) -> tuple[float, int, int, int]:
    """(c*, La, Lb, m): the largest cosine between two different strings of at most max_len bytes.

    The cosine depends only on (La, Lb, m), so every case is enumerated: 1 <= La <= Lb <= max_len,
    0 <= m <= La, and m < La when La == Lb (equal strings excluded).
    """
    best = (-math.inf, 0, 0, 0)
    for La in range(1, max_len + 1):
        for Lb in range(La, max_len + 1):
            top = La - 1 if La == Lb else La
            if top < 0:
                continue
            c = float(closed_form_cosine(La, Lb, top, pos_dim))  # cosine grows with m, so m = top is enough
            if c > best[0]:
                best = (c, La, Lb, top)
    return best


def guarantee_cosine(c_star: float) -> float:
    """cos(phi*/2) with phi* = arccos(c*): a vector closer than this to code(t) decodes to t."""
    return math.sqrt((1.0 + c_star) / 2.0)
