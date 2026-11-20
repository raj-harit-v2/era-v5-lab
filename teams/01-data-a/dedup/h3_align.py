"""The vector steps of H3, in torch on the encoder's device: nearest neighbours across two languages, and the sentence
alignment that confirms a pair, for a whole batch of pairs in one step. Every vector is a unit row, so a dot product is
a cosine. No Python loop over documents, sentences or pairs, and no copy to the host until a stage's result is
complete. align() is the plain one-pair reference that test_h3_align.py checks align_batch() against.

    python3 -B -m pytest dedup/tests/test_h3_align.py
"""
import numpy as np
import torch
import torch.nn.functional as F


def unit(m):
    """Rows scaled to length 1, as a float32 tensor on m's device; a zero row stays zero."""
    return F.normalize(torch.as_tensor(m).float(), dim=1)


@torch.inference_mode()
def cross_topk(A, B, k, block=512, check=None):
    """Nearest neighbours across two sets of unit rows, by exact cosine.

    Returns numpy (i, j, cosine, side) for every pair in the union of each A row's k best B rows and each B row's k best
    A rows, sorted by (i, j). side is 1 when the pair is only in A's list, 2 when only in B's, 3 when in both (mutual).
    One pass over A in blocks of rows, on A's device: A's lists come from each block (topk over the row), B's are kept
    as running lists and merged block by block (topk over the column), so the full A x B matrix is never held. The
    lists stay on the device until the end. check() is called before each block (the time limit)."""
    A = torch.as_tensor(A)
    B = torch.as_tensor(B, device=A.device).to(A.dtype)
    nA, nB = len(A), len(B)
    if nA == 0 or nB == 0:
        e = np.zeros(0, np.int64)
        return e, e, np.zeros(0, np.float32), np.zeros(0, np.int8)
    kA, kB = min(k, nB), min(k, nA)
    BT = B.T
    best_val = torch.full((nB, kB), float("-inf"), device=A.device)
    best_idx = torch.full((nB, kB), -1, dtype=torch.long, device=A.device)
    ai, aj, av = [], [], []
    for lo in range(0, nA, block):                               # blocks of rows: one matmul and two topk each
        if check:
            check()
        hi = min(lo + block, nA)
        S = (A[lo:hi] @ BT).float()                               # (rows of the block) x nB
        v, j = S.topk(kA, dim=1)
        ai.append(torch.arange(lo, hi, device=A.device).repeat_interleave(kA))
        aj.append(j.reshape(-1))
        av.append(v.reshape(-1))
        cv, ci = S.topk(min(kB, hi - lo), dim=0)                 # each column's best rows in the block
        best_val, sel = torch.cat([best_val, cv.T], 1).topk(kB, dim=1)
        best_idx = torch.cat([best_idx, (ci + lo).T], 1).gather(1, sel)
    host = lambda t: t.cpu().numpy()                              # the stage's one copy to the host
    a_i, a_j, a_v = host(torch.cat(ai)), host(torch.cat(aj)), host(torch.cat(av))
    b_j, b_i, b_v = np.repeat(np.arange(nB), kB), host(best_idx.reshape(-1)), host(best_val.reshape(-1))
    key = np.concatenate([a_i * nB + a_j, b_i * nB + b_j])
    cos = np.concatenate([a_v, b_v])
    side = np.concatenate([np.full(len(a_i), 1, np.int8), np.full(len(b_i), 2, np.int8)])
    order = np.argsort(key, kind="stable")
    key, cos, side = key[order], cos[order], side[order]
    uniq, start = np.unique(key, return_index=True)
    return uniq // nB, uniq % nB, cos[start], np.bitwise_or.reduceat(side, start)


def align(SA, SB, threshold):
    """Sentence alignment of two documents from their sentence vectors: the sentence pairs that are each other's best
    match (mutual best, so one to one) with cosine >= threshold. Returns (aligned pairs, their mean cosine). The
    reference for align_batch()."""
    SA, SB = np.asarray(SA, dtype=np.float32), np.asarray(SB, dtype=np.float32)
    if len(SA) == 0 or len(SB) == 0:
        return 0, 0.0
    S = SA @ SB.T
    best_b, best_a = S.argmax(axis=1), S.argmax(axis=0)
    rows = np.arange(len(S))
    cos = S[rows, best_b]
    ok = (best_a[best_b] == rows) & (cos >= threshold)
    n = int(ok.sum())
    return n, (float(cos[ok].mean()) if n else 0.0)


@torch.inference_mode()
def align_batch(E, start, count, A, B, threshold, width):
    """align() for a batch of pairs at once.

    E: the sentence vectors of all documents, unit rows, document d's count[d] sentences (at most width) in the rows
    from start[d]. A, B: the two documents of each pair. threshold: one cosine for every pair, or a tensor with one per
    pair (the threshold of each pair's language pair). All tensors on one device. Each pair's sentences are gathered
    into padded (pairs x width x dim) tensors, compared in one bmm and matched by argmax both ways. Returns (aligned
    sentence pairs, their mean cosine) per pair, as tensors on that device."""
    P, dev = len(A), E.device
    if P == 0 or len(E) == 0:
        return torch.zeros(P, dtype=torch.long, device=dev), torch.zeros(P, device=dev)
    s = torch.arange(width, device=dev)

    def side(D):
        valid = s < count[D, None]                                # pairs x width
        X = E[(start[D, None] + s).clamp_max(len(E) - 1)] * valid[..., None].to(E.dtype)
        return X, valid

    (XA, va), (XB, vb) = side(A), side(B)
    M = torch.bmm(XA, XB.transpose(1, 2)).float()                # pairs x width x width
    M = M.masked_fill(~(va[:, :, None] & vb[:, None, :]), float("-inf"))
    best_b, best_a = M.argmax(2), M.argmax(1)
    cos = M.gather(2, best_b[..., None]).squeeze(2)
    if torch.is_tensor(threshold):
        threshold = threshold.to(device=dev, dtype=cos.dtype)[:, None]   # pairs x 1, against each pair's sentences
    ok = (best_a.gather(1, best_b) == s) & va & (cos >= threshold)
    n = ok.sum(1)
    mean = torch.where(ok, cos, torch.zeros_like(cos)).sum(1) / n.clamp_min(1)
    return n, mean
