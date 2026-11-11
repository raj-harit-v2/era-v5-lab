"""Structured cosine scoring of KE1 codes in torch, on any device, in one sparse product.

Same arithmetic as ``decode_ref.CodeTable.cosine_scores`` (the numpy float64 reference), written so a
whole batch of queries is scored against every token at once:

    on_support[v, q] = sum over the L_v cells i of token v of Q[q, i]     (0/1 occupancy CSR  x  Q^T)
    dot[v, q]        = low_v * sum_i Q[q, i] + (high_v - low_v) * on_support[v, q]
    cos[v, q]        = dot[v, q] / (||z_v|| * ||Q[q]||)

Ties go to the lowest token id: ``torch.argmax`` returns the first maximal index. The empty token's
zero code has no direction and scores 0. ``tests/test_scoring.py`` pins the float64 CPU path to the
reference to 1e-12. On MPS (no sparse kernels) the product is a gather plus ``index_add_``.
"""

from __future__ import annotations

import numpy as np
import torch

_GATHER_CHUNK = 1 << 17  # cells per index_add_ chunk on the gather path


class StructuredScorer:
    """Scores queries against every token of a ``decode_ref.CodeTable``."""

    def __init__(self, code_table, device: str | torch.device = "cpu", dtype: torch.dtype = torch.float32) -> None:
        if dtype not in (torch.float32, torch.float64):
            raise ValueError(
                f"StructuredScorer scores in float32 or float64, not {dtype}; bf16 queries are cast on entry"
            )
        self.V = int(code_table.vocab_size)
        self.D = int(code_table.dim)
        self.device = torch.device(device)
        self.dtype = dtype
        self._lengths = torch.from_numpy(np.asarray(code_table.lengths, dtype=np.int64))
        col_cpu = torch.from_numpy(np.asarray(code_table.support, dtype=np.int64))
        self.col = col_cpu.to(self.device)
        self.use_sparse = self.device.type != "mps"
        if self.use_sparse:
            crow = torch.cat([torch.zeros(1, dtype=torch.int64), self._lengths.cumsum(0)])
            self.occ = torch.sparse_csr_tensor(
                crow, col_cpu, torch.ones(col_cpu.numel(), dtype=dtype), size=(self.V, self.D)
            ).to(self.device)
        else:
            self._build_gather_index()

        def f(a):
            return torch.from_numpy(np.asarray(a, dtype=np.float64)).to(self.device, dtype)

        self.low = f(code_table.low)
        self.gap = f(np.asarray(code_table.high) - np.asarray(code_table.low))
        self.norms = f(code_table.norms)

    def _build_gather_index(self) -> None:
        """Token id of every support cell, for the gather plus ``index_add_`` path."""
        self.tok_of_cell = torch.repeat_interleave(torch.arange(self.V), self._lengths).to(self.device)

    def _on_support(self, Q: torch.Tensor) -> torch.Tensor:
        """(V, n): the sum of each token's support cells, per query."""
        if self.use_sparse:
            return torch.sparse.mm(self.occ, Q.t().contiguous())
        QT = Q.t().contiguous()  # (D, n)
        out = torch.zeros(self.V, Q.shape[0], dtype=Q.dtype, device=Q.device)
        for s in range(0, self.col.numel(), _GATHER_CHUNK):
            e = min(s + _GATHER_CHUNK, self.col.numel())
            out.index_add_(0, self.tok_of_cell[s:e], QT.index_select(0, self.col[s:e]))
        return out

    def cosine(self, queries) -> torch.Tensor:
        """Cosine of every token (rows) to every query (columns): shape (V, n)."""
        Q = torch.as_tensor(queries).to(self.device, self.dtype)
        if Q.ndim == 1:
            Q = Q[None, :]
        if Q.shape[1] != self.D:
            raise ValueError(f"queries must have width {self.D}, got {Q.shape[1]}")
        if not torch.isfinite(Q).all():
            bad = torch.nonzero(~torch.isfinite(Q).all(dim=1)).flatten()[:5].tolist()
            raise ValueError(f"non-finite query vector at rows {bad}")
        qnorm = torch.linalg.vector_norm(Q, dim=1)
        if (qnorm == 0).any():
            bad = torch.nonzero(qnorm == 0).flatten()[:5].tolist()
            raise ValueError(f"zero query vector at rows {bad}: no direction to match")
        out = self._on_support(Q)
        out.mul_(self.gap[:, None]).add_(self.low[:, None] * Q.sum(dim=1)[None, :])
        denom = self.norms[:, None] * qnorm[None, :]
        zero = denom <= 0  # the empty token's zero code has no direction
        denom.masked_fill_(zero, 1.0)
        return out.div_(denom).masked_fill_(zero, 0.0)

    def top2(self, queries):
        """(best_id, best_cos, second_id, second_cos), each shape (n,), on the CPU. Ties: lowest id."""
        cos = self.cosine(queries)
        n = cos.shape[1]
        ar = torch.arange(n, device=cos.device)
        best_id = cos.argmax(dim=0)
        best = cos[best_id, ar]
        cos[best_id, ar] = -float("inf")
        second_id = cos.argmax(dim=0)
        second = cos[second_id, ar]
        return best_id.cpu(), best.cpu(), second_id.cpu(), second.cpu()
