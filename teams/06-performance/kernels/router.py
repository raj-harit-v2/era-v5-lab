"""MoE router after the logits in one CUDA kernel each way (model.moe.router_impl=triton).

    scores = softmax(logits),   idx = top_k(scores + bias),   gates = scores[idx] / sum(scores[idx])

Same as models.moe.SparseMoE.forward (bias only chooses; gates use the plain scores), which is about 6 kernels
forward (softmax, add, topk, gather, sum, div) and as many backward. Backward to the logits only (top-k is not
differentiable, the bias is a buffer):

    S = sum_j scores[idx_j],   dscores[idx_j] = (dgates_j - sum_i dgates_i gates_i) / S,   0 elsewhere
    dlogits = scores * (dscores - sum(dscores * scores))

Ties: the lowest expert index wins (torch.topk does not promise an order for ties); idx is in descending order
of scores + bias like torch.topk(sorted=True). Without CUDA or Triton, route() raises; SparseMoE keeps torch.
"""
from __future__ import annotations

import torch
from torch.autograd.function import once_differentiable

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None

ROWS = 64


if triton is not None:
    @triton.jit
    def _softmax(L, BIAS, row, col, M, E: tl.constexpr):
        mask = (row[:, None] < M) & (col[None, :] < E)
        logits = tl.load(L + row[:, None] * E + col[None, :], mask, -float("inf")).to(tl.float32)
        logits = tl.where(row[:, None] < M, logits, 0.)          # padded rows: finite, never stored
        logits = tl.where(col[None, :] < E, logits, -float("inf"))
        p = tl.exp(logits - tl.max(logits, 1)[:, None])
        return p / tl.sum(p, 1)[:, None]

    @triton.jit(do_not_specialize=["M"])
    def _forward(L, BIAS, IDX, GATES, M, E: tl.constexpr, K: tl.constexpr,
                 BE: tl.constexpr, BK: tl.constexpr, ROWS: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * ROWS + tl.arange(0, ROWS).to(tl.int64)
        col = tl.arange(0, BE)
        kc = tl.arange(0, BK)
        scores = _softmax(L, BIAS, row, col, M, E)
        bias = tl.load(BIAS + col, col < E, 0.).to(tl.float32)
        choose = tl.where(col[None, :] < E, scores + bias[None, :], -float("inf"))
        idx = tl.full((ROWS, BK), 0, tl.int64)
        picked = tl.full((ROWS, BK), 0., tl.float32)
        for j in tl.static_range(K):
            best = tl.argmax(choose, 1, tie_break_left=True).to(tl.int64)
            hit = col[None, :] == best[:, None]
            idx = tl.where(kc[None, :] == j, best[:, None], idx)
            picked = tl.where(kc[None, :] == j, tl.sum(tl.where(hit, scores, 0.), 1)[:, None], picked)
            choose = tl.where(hit, -float("inf"), choose)
        gates = picked / tl.sum(tl.where(kc[None, :] < K, picked, 0.), 1)[:, None]
        mask = (row[:, None] < M) & (kc[None, :] < K)
        tl.store(IDX + row[:, None] * K + kc[None, :], idx, mask)
        tl.store(GATES + row[:, None] * K + kc[None, :], gates, mask)

    @triton.jit(do_not_specialize=["M"])
    def _backward(L, IDX, DGATES, DL, M, E: tl.constexpr, K: tl.constexpr,
                  BE: tl.constexpr, BK: tl.constexpr, ROWS: tl.constexpr):
        row = tl.program_id(0).to(tl.int64) * ROWS + tl.arange(0, ROWS).to(tl.int64)
        col = tl.arange(0, BE)
        kc = tl.arange(0, BK)
        scores = _softmax(L, L, row, col, M, E)
        kmask = (row[:, None] < M) & (kc[None, :] < K)
        idx = tl.load(IDX + row[:, None] * K + kc[None, :], kmask, 0)
        dg = tl.load(DGATES + row[:, None] * K + kc[None, :], kmask, 0.).to(tl.float32)
        chosen = (row[:, None] < 0) & (col[None, :] < 0)            # all False, [ROWS, BE]
        dfull = tl.full((ROWS, BE), 0., tl.float32)
        for j in tl.static_range(K):
            idx_j = tl.sum(tl.where(kc[None, :] == j, idx, 0), 1)
            dg_j = tl.sum(tl.where(kc[None, :] == j, dg, 0.), 1)
            hit = col[None, :] == idx_j[:, None]
            chosen = chosen | hit
            dfull = tl.where(hit, dg_j[:, None], dfull)
        picked = tl.where(chosen, scores, 0.)
        total = tl.sum(picked, 1)
        dot = tl.sum(dfull * picked, 1) / total                   # sum_i dgates_i gates_i
        dscores = tl.where(chosen, (dfull - dot[:, None]) / total[:, None], 0.)
        dl = scores * (dscores - tl.sum(dscores * scores, 1)[:, None])
        tl.store(DL + row[:, None] * E + col[None, :], dl, (row[:, None] < M) & (col[None, :] < E))


def _sizes(logits, top_k):
    e = logits.shape[1]
    return e, top_k, triton.next_power_of_2(e), triton.next_power_of_2(top_k)


class _Route(torch.autograd.Function):
    @staticmethod
    def forward(ctx, logits, bias, top_k):
        logits = logits.contiguous()
        n = logits.shape[0]
        e, k, be, bk = _sizes(logits, top_k)
        idx = torch.empty((n, k), device=logits.device, dtype=torch.int64)
        gates = torch.empty((n, k), device=logits.device, dtype=torch.float32)
        with torch.cuda.device(logits.device):
            _forward[(triton.cdiv(n, ROWS),)](logits, bias.contiguous(), idx, gates, n, e, k, be, bk, ROWS,
                                              num_warps=4)
        ctx.save_for_backward(logits, idx)
        ctx.top_k = top_k
        ctx.mark_non_differentiable(idx)
        return idx, gates

    @staticmethod
    @once_differentiable
    def backward(ctx, _didx, dgates):
        logits, idx = ctx.saved_tensors
        n = logits.shape[0]
        e, k, be, bk = _sizes(logits, ctx.top_k)
        dl = torch.empty_like(logits, dtype=torch.float32)
        if dgates is None:
            return dl.zero_().to(logits.dtype), None, None
        with torch.cuda.device(logits.device):
            _backward[(triton.cdiv(n, ROWS),)](logits, idx, dgates.contiguous(), dl, n, e, k, be, bk, ROWS,
                                               num_warps=4)
        return dl.to(logits.dtype), None, None


def supported(logits: torch.Tensor, bias: torch.Tensor, top_k: int) -> bool:
    return (triton is not None and logits.device.type == "cuda" and logits.ndim == 2 and logits.shape[0] > 0
            and 0 < top_k <= logits.shape[1] <= 1024 and logits.dtype == torch.float32
            and bias.shape == (logits.shape[1],) and bias.device == logits.device)


def route(logits: torch.Tensor, bias: torch.Tensor, top_k: int):
    """(topk_idx [N, k] int64, gates [N, k] fp32) from fp32 router logits [N, E]."""
    if not supported(logits, bias, top_k):
        raise ValueError("triton router needs CUDA, Triton, fp32 logits [N, E <= 1024] and a bias [E]")
    return _Route.apply(logits, bias, top_k)
