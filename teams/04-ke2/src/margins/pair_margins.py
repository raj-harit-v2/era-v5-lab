"""Exact decode margins of every token against the whole vocabulary, from the two-valued code structure.

Self margin of token t: ``cos(z_t, z_t) - max over s != t of cos(z_t, z_s)``. The maximiser is the
*rival* (lowest ID on ties). When t decodes to itself this is ``decode_ref``'s margin (best minus
second-best cosine); a value <= 0 means t ties with or loses to its rival.

Why this is cheap and exact
---------------------------
Every code is two-valued (Lemma 1): ``high`` on the L support cells ``b_p * P + p`` and ``low``
everywhere else. For a query token s and a candidate t that agree on k byte positions
(``p < min(L_s, L_t)`` with ``b_s[p] == b_t[p]``), with D = char_dim * P:

    dot = k*h_s*h_t + (L_s - k)*h_s*l_t + (L_t - k)*l_s*h_t + (D - L_s - L_t + k)*l_s*l_t
    cos = dot / (|z_s| * |z_t|)          (0 where the norm product is 0, as decode_ref does)

so all pairs need only the overlap counts k and per-token ``(high, low)``. The code evaluates the
same dot in decode_ref's arrangement, ``l_t * sum(z_s) + (h_t - l_t) * (k*(h_s - l_s) + L_t*l_s)``.
``(high, low)`` may come from the float64 reference or from rounded fp32 / bf16 codes; the arithmetic
is float64 either way, so the result measures the effect of *storing* codes in that precision.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ke2.codec import code_values
from ke2.config import CHAR_DIM
from ke2.tables import ByteTable

log = logging.getLogger("pair_margins")

PRECISIONS: tuple[str, ...] = ("fp64", "fp32", "bf16")


@dataclass(frozen=True)
class CodeValues:
    """Per-token code values: ``high`` on the support, ``low`` elsewhere (both float64)."""

    precision: str
    pos_dim: int
    char_dim: int
    lengths: np.ndarray  # int64 (V,)
    high: np.ndarray  # float64 (V,)
    low: np.ndarray  # float64 (V,)

    @property
    def dim(self) -> int:
        """Code width D = char_dim * pos_dim."""
        return self.char_dim * self.pos_dim

    @property
    def norms(self) -> np.ndarray:
        """Euclidean norm of every code, float64 (V,)."""
        L = self.lengths.astype(np.float64)
        return np.sqrt(L * self.high**2 + (self.dim - L) * self.low**2)


def exact_values(table: ByteTable) -> CodeValues:
    """Float64 reference values (``ke2.codec.code_values``, upstream codec defaults)."""
    lengths = table.lengths.astype(np.int64)
    high, low = code_values(lengths, table.pos_dim, char_dim=CHAR_DIM)
    return CodeValues("fp64", table.pos_dim, CHAR_DIM, lengths, high, low)


def overlap_counts(q_rows: np.ndarray, q_lens: np.ndarray, c_rows: np.ndarray, c_lens: np.ndarray) -> np.ndarray:
    """Number of positions ``p < min(L_q, L_c)`` where the bytes agree, int16 (n, V).

    Rows are zero-padded, so positions past either length never count (a real 0x00 byte does).
    """
    q_lens = np.asarray(q_lens, dtype=np.int64)
    c_lens = np.asarray(c_lens, dtype=np.int64)
    out = np.zeros((q_rows.shape[0], c_rows.shape[0]), dtype=np.int16)
    top = min(int(q_lens.max(initial=0)), q_rows.shape[1])
    for p in range(top):  # one (n, V) slice per position, never an (n, V, P) broadcast
        same = q_rows[:, p, None] == c_rows[None, :, p]
        same &= (p < q_lens)[:, None]
        same &= (p < c_lens)[None, :]
        out += same
    return out


def pair_cosines(query_ids: np.ndarray, overlaps: np.ndarray, values: CodeValues) -> np.ndarray:
    """Cosine of each query token's code to every code, float64 (n, V), from overlap counts."""
    q = np.asarray(query_ids, dtype=np.int64)
    hs, ls = values.high[q][:, None], values.low[q][:, None]
    Ls = values.lengths[q].astype(np.float64)[:, None]
    Lt = values.lengths.astype(np.float64)[None, :]
    ht, lt = values.high[None, :], values.low[None, :]
    query_sum = Ls * hs + (values.dim - Ls) * ls  # sum of the query code's entries
    on_support = overlaps * (hs - ls) + Lt * ls  # sum of the query over t's support cells
    dots = lt * query_sum + (ht - lt) * on_support
    norms = values.norms
    denom = norms[q][:, None] * norms[None, :]
    out = np.zeros_like(dots)
    np.divide(dots, denom, out=out, where=denom > 0)
    return out


@dataclass(frozen=True)
class SelfMargins:
    """Self margin, rival and shared-byte count of each query token, for one precision."""

    precision: str
    token_ids: np.ndarray  # int64 (n,)
    self_scores: np.ndarray  # float64 (n,): cos(z_t, z_t)
    margins: np.ndarray  # float64 (n,): self score minus best rival score
    rival_ids: np.ndarray  # int64 (n,): best other token, lowest ID on ties
    overlaps: np.ndarray  # int64 (n,): k between the token and its rival


def self_margins(
    table: ByteTable,
    values: Sequence[CodeValues],
    *,
    query_ids: np.ndarray | None = None,
    chunk_rows: int = 64,
) -> dict[str, SelfMargins]:
    """Exhaustive self margins of the query tokens for every set of code values, keyed by precision.

    ``query_ids=None`` scores every token in ID order; otherwise results follow the caller's order.
    Overlap counts are computed once per chunk and shared by all precisions. Results are bitwise
    independent of ``chunk_rows``. Scoring temporaries are about ``4 * 8 * chunk_rows * V`` bytes.
    """
    if chunk_rows < 1:
        raise ValueError("chunk_rows must be positive")
    V = table.vocab_size
    if V < 2:
        raise ValueError("a margin needs at least two tokens")
    for v in values:
        if v.pos_dim != table.pos_dim or v.lengths.shape[0] != V:
            raise ValueError(f"{v.precision} values do not match the table (P={table.pos_dim}, V={V})")
    ids = np.arange(V, dtype=np.int64) if query_ids is None else np.asarray(query_ids, dtype=np.int64)
    n = ids.shape[0]
    lengths = table.lengths.astype(np.int64)
    order = np.argsort(lengths[ids], kind="stable")  # short chunks loop over few positions
    out = {
        v.precision: {
            "self": np.empty(n),
            "margin": np.empty(n),
            "rival": np.empty(n, np.int64),
            "k": np.empty(n, np.int64),
        }
        for v in values
    }
    n_chunks = -(-n // chunk_rows)
    every = max(1, n_chunks // 20)  # progress about every 5%
    for c, start in enumerate(range(0, n, chunk_rows)):
        if c % every == 0 and n_chunks > 1:
            log.info("self margins: chunk %d / %d", c, n_chunks)
        where = order[start : start + chunk_rows]
        q = ids[where]
        k = overlap_counts(table.bytes[q], lengths[q], table.bytes, lengths)
        rows = np.arange(q.shape[0])
        for v in values:
            cos = pair_cosines(q, k, v)
            own = cos[rows, q].copy()
            cos[rows, q] = -np.inf
            rival = np.argmax(cos, axis=1)  # first maximum: lowest ID on ties
            o = out[v.precision]
            o["self"][where] = own
            o["margin"][where] = own - cos[rows, rival]
            o["rival"][where] = rival
            o["k"][where] = k[rows, rival]
    return {p: SelfMargins(p, ids.copy(), o["self"], o["margin"], o["rival"], o["k"]) for p, o in out.items()}


class TwoValueError(ValueError):
    """A code is not two-valued, so the closed-form scores would not apply to it."""


def two_values(codes: np.ndarray, lengths: np.ndarray, *, first_id: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Per-row ``(high, low)`` of codes ``(n, D)`` with ``lengths`` (n,), as float64.

    A row is valid when every entry is its maximum or its minimum and exactly L entries equal the
    maximum (with high > low), or when L == 0 and the row is all zeros. Otherwise this raises
    :class:`TwoValueError` naming the token ID (``first_id`` + row index).
    """
    codes = np.asarray(codes, dtype=np.float64)
    lengths = np.asarray(lengths, dtype=np.int64)
    high, low = codes.max(axis=1), codes.min(axis=1)
    is_high = codes == high[:, None]
    two = (is_high | (codes == low[:, None])).all(axis=1)
    valid = np.where(
        lengths > 0,
        two & (is_high.sum(axis=1) == lengths) & (high > low),
        ~codes.any(axis=1),
    )
    if not valid.all():
        row = int(np.flatnonzero(~valid)[0])
        raise TwoValueError(
            f"token {first_id + row}: code is not two-valued with {int(lengths[row])} high cells "
            f"({int(is_high[row].sum())} cells at the maximum, {np.unique(codes[row]).size} distinct values)"
        )
    return high, low


def codec_values(table: ByteTable, precision: str, *, chunk_rows: int = 2048) -> CodeValues:
    """Per-token values of the codes held in ``precision``.

    ``fp64`` is :func:`exact_values`. ``fp32`` reads the upstream float32 ``kronecker_codec`` output
    (``ke2.codec.encode_ids``, what G5 gets); ``bf16`` reads that output after
    ``.to(torch.bfloat16)`` (round to nearest even). Every code is checked to be two-valued.
    """
    if precision not in PRECISIONS:
        raise ValueError(f"unknown precision {precision!r}; expected one of {PRECISIONS}")
    if precision == "fp64":
        return exact_values(table)
    if chunk_rows < 1:
        raise ValueError("chunk_rows must be positive")
    import torch

    from ke2.codec import encode_ids

    V = table.vocab_size
    lengths = table.lengths.astype(np.int64)
    high, low = np.empty(V), np.empty(V)
    for start in range(0, V, chunk_rows):
        ids = np.arange(start, min(start + chunk_rows, V))
        codes = encode_ids(ids, table)
        if precision == "bf16":
            codes = codes.to(torch.bfloat16)
        high[ids], low[ids] = two_values(codes.double().numpy(), lengths[ids], first_id=start)
    return CodeValues(precision, table.pos_dim, CHAR_DIM, lengths, high, low)


def value_pairs_per_length(values: CodeValues) -> dict[int, int]:
    """Number of distinct ``(high, low)`` pairs among the tokens of each length present."""
    out: dict[int, int] = {}
    for L in np.unique(values.lengths).tolist():
        sel = values.lengths == L
        out[int(L)] = len(set(zip(values.high[sel].tolist(), values.low[sel].tolist(), strict=True)))
    return out
