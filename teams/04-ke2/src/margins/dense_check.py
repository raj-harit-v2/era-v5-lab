"""Dense fp32 / bf16 scoring of selected query tokens against the whole vocabulary.

``pair_margins`` measures what *storing* codes in a precision does, with exact float64 arithmetic.
This module measures what *scoring* in that precision does, the way a fast decoder would:

``fp32``          fp32 codes, fp32 matrix product, fp32 norms
``bf16_fp32acc``  codes cast to bf16, products accumulated in fp32 (bf16 x bf16 fits fp32 exactly)
``bf16_out``      as ``bf16_fp32acc``, then each dot product rounded to bf16 before normalising,
                  a model of a GEMM with fp32 accumulate and bf16 output

Queries are the upstream fp32 codes of ``query_ids`` (``ke2.codec.encode_ids``); candidates are
every token's code, encoded in chunks. Scores are cosines. This is a CPU model of the arithmetic:
it makes no GPU claim, and fp32 matrix products are not bitwise reproducible across BLAS builds.
Pure-bf16 accumulation is not modelled.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ke2.tables import ByteTable

MODES: tuple[str, ...] = ("fp32", "bf16_fp32acc", "bf16_out")


@dataclass(frozen=True)
class DenseCheck:
    """Dense decode of the query tokens in one scoring mode."""

    mode: str
    query_ids: np.ndarray  # int64 (n,)
    decoded_ids: np.ndarray  # int64 (n,): argmax over the vocabulary, lowest ID on ties
    self_scores: np.ndarray  # float64 (n,): score of the query's own token
    margins: np.ndarray  # float64 (n,): self score minus best other score (can be <= 0)
    rival_ids: np.ndarray  # int64 (n,): best other token, lowest ID on ties


def _cosine(dots, qnorm, cnorm):
    import torch

    denom = qnorm[:, None] * cnorm[None, :]
    return torch.where(denom > 0, dots / torch.where(denom > 0, denom, 1), 0)


def dense_check(
    table: ByteTable,
    query_ids: np.ndarray,
    *,
    modes: Sequence[str] = MODES,
    chunk_rows: int = 4096,
) -> dict[str, DenseCheck]:
    """Score ``query_ids`` against every token of ``table`` in each mode; results keyed by mode.

    Each candidate chunk is encoded once and reused by every mode. Score memory is
    ``4 * len(query_ids) * V`` bytes per mode.
    """
    import torch

    from ke2.codec import encode_ids

    unknown = [m for m in modes if m not in MODES]
    if unknown:
        raise ValueError(f"unknown mode {unknown[0]!r}; expected one of {MODES}")
    if chunk_rows < 1:
        raise ValueError("chunk_rows must be positive")
    ids = np.asarray(query_ids, dtype=np.int64)
    n, V = ids.shape[0], table.vocab_size

    def norm(x):
        return torch.linalg.vector_norm(x, dim=1)

    q32 = encode_ids(ids, table)
    qb = q32.to(torch.bfloat16).float()
    q32n, qbn = norm(q32), norm(qb)
    scores = {m: torch.empty((n, V), dtype=torch.float32) for m in modes}
    for start in range(0, V, chunk_rows):
        cols = slice(start, min(start + chunk_rows, V))
        c32 = encode_ids(np.arange(cols.start, cols.stop), table)
        if "fp32" in scores:
            scores["fp32"][:, cols] = _cosine(q32 @ c32.T, q32n, norm(c32))
        if "bf16_fp32acc" in scores or "bf16_out" in scores:
            cb = c32.to(torch.bfloat16).float()
            dots, cbn = qb @ cb.T, norm(cb)
            if "bf16_fp32acc" in scores:
                scores["bf16_fp32acc"][:, cols] = _cosine(dots, qbn, cbn)
            if "bf16_out" in scores:
                scores["bf16_out"][:, cols] = _cosine(dots.to(torch.bfloat16).float(), qbn, cbn)

    out = {}
    rows = np.arange(n)
    for m, s in scores.items():
        s = s.double().numpy()
        decoded = np.argmax(s, axis=1)  # first maximum: lowest ID on ties
        own = s[rows, ids].copy()
        s[rows, ids] = -np.inf
        rival = np.argmax(s, axis=1)
        out[m] = DenseCheck(m, ids.copy(), decoded, own, own - s[rows, rival], rival)
    return out
