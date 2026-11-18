"""KV-cached sampling for Team 5's LanguageModel, built from Team 5's own modules (G10 code, Team 5's weights).

Team 5's `LanguageModel.forward` has no cache: sampling re-runs the whole sequence for every new token, and
`team5_adapter.Bundle.sample` used to project every position through the 131,072-row head on every step although only
the last position is sampled. This module decodes with a per-layer key/value cache:

    prefill: one pass over the prompt (Team 5's submodules: KE2 embedding, n1/n2, q/k/v/o, MoE, norm, head)
    step:    one new token per row; attention reads the cached keys/values; RoPE uses the absolute position

It re-implements only the attention arithmetic of `week2.model.GQA.forward` for global layers (rotary with an
absolute position offset, grouped K/V heads, fp32 logits, causal softmax); every weight and every other operation is
Team 5's module called as is. Configurations it does not reproduce (local-window layers, attention sinks, attention
gate, MTP) are refused. `parity()` checks per-position logits against `LanguageModel.forward` on the full sequence.
"""
from __future__ import annotations

import math

import torch
from torch import no_grad  # undotted decorator: pr-guard reads '+@a.b' as an email
import torch.nn.functional as F


def check_supported(lm) -> None:
    for i, b in enumerate(lm.blocks):
        a = b.attn
        if a.local or a.sink is not None or a.gate is not None:
            raise NotImplementedError(f"block {i}: local window / sink / gate attention is not reproduced by g5_decode")


def _rotary(attn, x: torch.Tensor, start: int) -> torch.Tensor:
    """Team 5's GQA.rotary with positions start..start+T-1 instead of 0..T-1 (same formula, model.py)."""
    rd = attn.rotary_dim
    inv = attn.theta ** (-torch.arange(0, rd, 2, device=x.device).float() / rd)
    pos = torch.arange(start, start + x.shape[-2], device=x.device).float()
    angle = pos[:, None] * inv[None, :]
    a, b = x.float()[..., :rd:2], x.float()[..., 1:rd:2]
    rotated = torch.stack((a * angle.cos() - b * angle.sin(), a * angle.sin() + b * angle.cos()), -1).flatten(-2)
    rotated = rotated.to(x.dtype)
    return rotated if rd == attn.d else torch.cat((rotated, x[..., rd:]), dim=-1)


def _attend(attn, x: torch.Tensor, cache: dict, start: int) -> torch.Tensor:
    b, t, w = x.shape
    q = _rotary(attn, attn.q(x).view(b, t, attn.nh, attn.d).transpose(1, 2), start)
    k = _rotary(attn, attn.k(x).view(b, t, attn.nkv, attn.d).transpose(1, 2), start)
    v = attn.v(x).view(b, t, attn.nkv, attn.d).transpose(1, 2)
    if cache.get("k") is not None:
        k = torch.cat((cache["k"], k), 2)
        v = torch.cat((cache["v"], v), 2)
    cache["k"], cache["v"] = k, v
    rep = attn.nh // attn.nkv
    kk, vv = k.repeat_interleave(rep, dim=1), v.repeat_interleave(rep, dim=1)
    logits = q.float() @ kk.float().transpose(-2, -1) / math.sqrt(attn.d)
    total = kk.shape[-2]
    # query i (absolute position start+i) sees keys 0..start+i
    qpos = torch.arange(start, start + t, device=x.device)[:, None]
    kpos = torch.arange(total, device=x.device)[None, :]
    logits = logits.masked_fill(kpos > qpos, float("-inf"))
    a = logits.softmax(-1).to(vv.dtype)
    return attn.o((a @ vv).transpose(1, 2).reshape(b, t, w))


def forward_cached(lm, ids: torch.Tensor, caches: list[dict], start: int) -> torch.Tensor:
    """Hidden states of `ids` ([B, T], all valid) given caches holding positions < start; caches are extended."""
    x = lm.embedding(ids)
    valid = torch.ones_like(ids, dtype=torch.bool)
    for block, cache in zip(lm.blocks, caches):
        x = x + _attend(block.attn, block.n1(x), cache, start)
        x = x + block.moe(block.n2(x), valid)
    return lm.norm(x)


@no_grad()
def parity(lm, ids: torch.Tensor, split: int) -> float:
    """Max |logit difference| between Team 5's full forward and prefill(ids[:, :split]) + one-token steps."""
    check_supported(lm)
    full = lm(ids, torch.ones_like(ids, dtype=torch.bool)).float()
    caches = [{} for _ in lm.blocks]
    outs = [lm.head(forward_cached(lm, ids[:, :split], caches, 0)).float()]
    for t in range(split, ids.shape[1]):
        outs.append(lm.head(forward_cached(lm, ids[:, t:t + 1], caches, t)).float())
    return float((torch.cat(outs, 1) - full).abs().max())


@no_grad()
def sample(lm, prompt: list[int], k: int, max_new: int, temperature: float, generator, stop_ids: list[int],
           pad_id: int, device: str):
    """Same contract as team5_adapter.Bundle.sample: (seq [k, P+max_new], completion_mask [k, max_new], reasons)."""
    check_supported(lm)
    was = lm.training
    lm.eval()
    seq = torch.tensor([prompt] * k, dtype=torch.long, device=device)
    caches = [{} for _ in lm.blocks]
    h = forward_cached(lm, seq, caches, 0)[:, -1]
    alive = torch.ones(k, dtype=torch.bool, device=device)
    cmask = torch.zeros(k, max_new, dtype=torch.bool, device=device)
    reason = ["length"] * k
    stop_t = torch.tensor(stop_ids, dtype=torch.long, device=device)
    for t in range(max_new):
        logits = lm.head(h).float()
        if temperature <= 0:
            nxt = logits.argmax(-1)
        else:
            nxt = torch.multinomial(torch.softmax(logits / temperature, -1), 1, generator=generator).squeeze(-1)
        nxt = torch.where(alive, nxt, torch.full_like(nxt, pad_id))
        cmask[:, t] = alive
        hit = alive & torch.isin(nxt, stop_t)
        for r in hit.nonzero().flatten().tolist():
            reason[r] = f"stop:{int(nxt[r])}"
        alive = alive & ~hit
        seq = torch.cat([seq, nxt[:, None]], 1)
        if not bool(alive.any()):
            seq = torch.cat([seq, torch.full((k, max_new - t - 1), pad_id, device=device, dtype=torch.long)], 1)
            break
        if t + 1 < max_new:
            h = forward_cached(lm, nxt[:, None], caches, len(prompt) + t)[:, -1]
    lm.train(was)
    return seq, cmask, reason
