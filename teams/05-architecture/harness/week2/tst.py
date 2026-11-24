"""TST ("Secret Sauce"), TSAI's 21 Nov recipe: bag training for the first part of the run. UNCONFIRMED ON KE2.

TSAI's definition: for the first 30% of steps only, position j's input is the plain mean (fp32) of the token
embeddings [s*j, s*j + s), plus the normal position for index j; position j predicts the next bag, tokens
[s*(j+1), s*(j+1) + s), from one log-softmax shared across the s targets; loss_j = sum_i w_i * (-log p(target_i)),
with power weights w_i = (1/i) / H_s (s = 6: 0.408, 0.204, 0.136, 0.102, 0.082, 0.068). No change to the optimizer
or the learning-rate schedule. Evidence (TSAI): dense only, one seed, +0.004 bpb at equal compute; zero gain on
KE2 at s = 4, 8, 16. Keep it labelled "unconfirmed on KE2".

Positions: the lab model has no added position embedding; attention applies RoPE by sequence index, so bag j sits
at position j (asked in G5, 21 Nov, not yet confirmed). Everything is batched tensor work: no Python loop over
tokens, bags or experts.
"""

from __future__ import annotations
import torch
from torch.nn import functional as F


def power_weights(s):
    w = torch.tensor([1.0 / i for i in range(1, s + 1)])
    return w / w.sum()


def active(step, total, run):
    """TST runs on 1-based steps 1 .. round(tst_frac * total) when run.tst is on; normal training after."""
    return bool(run.get("tst")) and step <= round(run["tst_frac"] * total)


def bag_count(seq_len, s):
    """Bags whose next bag is complete inside the window: bag j needs inputs [s*j, s*j + s) and targets up to
    y[s*j + 2s - 2], so j < (seq_len - s + 1) / s."""
    return max(0, (seq_len - s + 1) // s)


def tst_batch(x, y, s):
    """Bag inputs, bag validity and next-bag targets for one batch.

    y[t] is the target of x[t] (x[t + 1], or -100 where not scored). The next bag's tokens x[s(j+1) + i - 1],
    i = 1..s, are y[s(j+1) + i - 2], so the targets are y[:, s - 1 : s - 1 + s*n] in rows of s.
    """
    n = bag_count(x.shape[1], s)
    inputs = x[:, : s * n]
    targets = y[:, s - 1 : s - 1 + s * n].reshape(x.shape[0], n, s)
    valid = (y[:, : s * n] != -100).reshape(x.shape[0], n, s).any(-1)
    return inputs, valid & (targets != -100).any(-1), targets


def scored_bags(y, s):
    """How many bag positions score at least one target: the normaliser, like the token count in normal training."""
    _, valid, _ = tst_batch(torch.zeros_like(y), y, s)
    return int(valid.sum())


def tst_loss(model, x, y, s):
    """Sum over scored bags of the power-weighted next-bag NLL (one log-softmax per bag)."""
    inputs, valid, targets = tst_batch(x, y, s)
    b, n = valid.shape
    emb = model.embedding(inputs)
    h = emb.float().reshape(b, n, s, -1).mean(2).to(emb.dtype)
    # The model's own stack on recipe-supplied embeddings (#717's hook), so TST follows any change to it.
    h = model.hidden_from_embeddings(h, valid)
    logp = F.log_softmax(model.head(h[valid]).float(), dim=-1)
    t = targets[valid]
    keep = t != -100
    nll = -logp.gather(1, t.clamp_min(0)) * keep
    return (nll * power_weights(s).to(nll.device)).sum()
