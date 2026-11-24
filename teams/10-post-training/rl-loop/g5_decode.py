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


# --- many prompts in one decode: left padding, per-row positions, a key mask, a preallocated cache ---------------------

def _rotary_table(attn, pos: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """cos and sin of Team 5's RoPE angles for positions pos [R, T]: [R, 1, T, rd/2] each (same formula as _rotary)."""
    rd = attn.rotary_dim
    inv = attn.theta ** (-torch.arange(0, rd, 2, device=pos.device).float() / rd)
    angle = pos.float()[:, None, :, None] * inv  # [R, 1, T, rd/2]
    return angle.cos(), angle.sin()


def _rotary_rows(attn, x: torch.Tensor, pos: torch.Tensor, table=None) -> torch.Tensor:
    """Team 5's GQA.rotary with a position per row and token: x [R, H, T, d], pos [R, T] (same formula as _rotary).
    `table` = _rotary_table(attn, pos), computed once per step and shared by every layer's q and k (same values)."""
    rd = attn.rotary_dim
    cos, sin = table if table is not None else _rotary_table(attn, pos)
    a, b = x.float()[..., :rd:2], x.float()[..., 1:rd:2]
    rotated = torch.stack((a * cos - b * sin, a * sin + b * cos), -1).flatten(-2)
    rotated = rotated.to(x.dtype)
    return rotated if rd == attn.d else torch.cat((rotated, x[..., rd:]), dim=-1)


def _step_tables(attn, x: torch.Tensor, slot: int, pos: torch.Tensor, key_ok: torch.Tensor) -> dict:
    """What every layer of one forward_rows call shares (Team 5's blocks all use one rope_theta and rotary_dim, checked
    in forward_rows): the RoPE cos/sin and the [R, 1, T, S] attention mask. Computed once per call instead of per layer."""
    t = x.shape[1]
    total = slot + t
    qs = torch.arange(slot, total, device=x.device)[:, None]
    ks = torch.arange(total, device=x.device)[None, :]
    allowed = (ks <= qs)[None] & (key_ok[:, None, :total] | (ks == qs)[None])  # [R, T, S]
    return {"rot": _rotary_table(attn, pos), "not_allowed": ~allowed[:, None]}


def _attend_rows(attn, x: torch.Tensor, cache: dict, slot: int, pos: torch.Tensor, key_ok: torch.Tensor,
                 tables: dict | None = None) -> torch.Tensor:
    """_attend for left-padded rows. x [R, T, w] fills cache slots slot..slot+T-1 (written in place, no torch.cat);
    pos [R, T] are the RoPE positions (0 at each row's first real token); key_ok [R, S] marks real slots. A query sees
    real keys at or before its own slot; a padding query sees only itself, so its row stays finite and is never read."""
    b, t, w = x.shape
    if tables is None:
        tables = _step_tables(attn, x, slot, pos, key_ok)
    q = _rotary_rows(attn, attn.q(x).view(b, t, attn.nh, attn.d).transpose(1, 2), pos, tables["rot"])
    k = _rotary_rows(attn, attn.k(x).view(b, t, attn.nkv, attn.d).transpose(1, 2), pos, tables["rot"])
    v = attn.v(x).view(b, t, attn.nkv, attn.d).transpose(1, 2)
    if cache.get("k") is None:
        cache["k"] = k.new_zeros(b, attn.nkv, cache["size"], attn.d)
        cache["v"] = v.new_zeros(b, attn.nkv, cache["size"], attn.d)
    cache["k"][:, :, slot:slot + t] = k
    cache["v"][:, :, slot:slot + t] = v
    total = slot + t
    rep = attn.nh // attn.nkv
    kk, vv = cache["k"][:, :, :total], cache["v"][:, :, :total]  # views: no copy of the cache per step
    # Grouped heads instead of repeat_interleave: query head h = g*rep + j reads K/V group g, as in Team 5's GQA, so
    # q [R, nh, T, d] is viewed as [R, nkv, rep*T, d] against the group's [R, nkv, S, d]. Team 5 takes fp32 logits
    # (q.float() @ k.float()); under autocast that matmul runs in the autocast dtype anyway, so the fp32 copy of the
    # cache is skipped there (same values) and kept without autocast (fp32 on CPU).
    amp = torch.is_autocast_enabled(x.device.type)
    qg = q.reshape(b, attn.nkv, rep * t, attn.d)
    logits = ((qg if amp else qg.float()) @ (kk if amp else kk.float()).transpose(-2, -1) / math.sqrt(attn.d))
    logits = logits.view(b, attn.nh, t, total)
    logits = logits.masked_fill(tables["not_allowed"], float("-inf"))
    a = logits.softmax(-1).to(vv.dtype).view(b, attn.nkv, rep * t, total)
    return attn.o((a @ vv).view(b, attn.nh, t, attn.d).transpose(1, 2).reshape(b, t, w))


def forward_rows(lm, ids: torch.Tensor, caches: list[dict], slot: int, pos: torch.Tensor, key_ok: torch.Tensor):
    """Hidden states of ids [R, T] at cache slots slot..slot+T-1; padding tokens get no MoE output (valid False)."""
    x = lm.embedding(ids)
    valid = key_ok[:, slot:slot + ids.shape[1]]
    a0 = lm.blocks[0].attn
    shared = all(b.attn.theta == a0.theta and b.attn.rotary_dim == a0.rotary_dim for b in lm.blocks)
    tables = _step_tables(a0, ids, slot, pos, key_ok) if shared else None  # else: per layer, as before
    for block, cache in zip(lm.blocks, caches):
        x = x + _attend_rows(block.attn, block.n1(x), cache, slot, pos, key_ok, tables)
        x = x + block.moe(block.n2(x), valid)
    return lm.norm(x)


@no_grad()
def parity_many(lm, rows: list[list[int]], steps: int) -> float:
    """Max |logit difference| between Team 5's full forward of each row alone and the left-padded batched path:
    one prefill of every row's prompt (all but its last `steps` tokens; rows may differ in length), then `steps`
    one-token steps. Covers every prompt position and every stepped position."""
    check_supported(lm)
    dev = next(lm.parameters()).device  # not lm.head.weight: a KAS V2 head (#717) has no .weight
    lens = [len(r) - steps for r in rows]
    if min(lens) < 1:
        raise ValueError("every row needs at least one prompt token")
    width = max(lens)
    off = torch.tensor([width - L for L in lens], device=dev)
    ids = torch.tensor([[0] * (width - L) + r[:L] for r, L in zip(rows, lens)], device=dev)
    key_ok = torch.arange(width + steps, device=dev)[None, :] >= off[:, None]
    caches = [{"size": width + steps} for _ in lm.blocks]
    pos = (torch.arange(width, device=dev)[None, :] - off[:, None]).clamp_min(0)
    got = [lm.head(forward_rows(lm, ids, caches, 0, pos, key_ok)).float()]
    for t in range(steps):
        nxt = torch.tensor([[r[L + t]] for r, L in zip(rows, lens)], device=dev)
        got.append(lm.head(forward_rows(lm, nxt, caches, width + t, (off.new_tensor(lens) + t)[:, None], key_ok)).float())
    got = torch.cat(got, 1)  # [R, width + steps, V]; row i's real positions start at off[i]
    worst = 0.0
    for i, r in enumerate(rows):
        full = lm(torch.tensor([r], device=dev), torch.ones(1, len(r), dtype=torch.bool, device=dev)).float()[0]
        worst = max(worst, float((got[i, int(off[i]):] - full).abs().max()))
    return worst


@no_grad()
def sample_many(lm, prompts: list[list[int]], k: int, max_new: int, temperature: float, generator, stop_ids: list[int],
                pad_id: int, device: str):
    """k completions of EVERY prompt in one decode (rows = len(prompts) x k, prompt-major). Returns one
    (seq [k, len(prompt)+max_new], completion_mask [k, max_new], reasons) per prompt, the contract of sample().

    Each prompt is prefilled once (P rows, left-padded to the longest prompt) and its cache and last hidden state are
    copied to its k rows; then one token per row per step. RoPE positions count from each row's first real token, and
    padding slots are masked out of every attention, so each row computes what sample() computes for its prompt alone
    (within float reduction order: checked by parity_many). The random draws differ from per-prompt calls (one
    multinomial over all rows per step), so temperature > 0 gives different, equally distributed tokens."""
    check_supported(lm)
    if not prompts or any(not p for p in prompts) or k <= 0 or max_new <= 0:
        raise ValueError("need non-empty prompts, k > 0 and max_new > 0")
    was = lm.training
    lm.eval()
    n_p = len(prompts)
    lens = torch.tensor([len(p) for p in prompts], device=device)
    width = int(lens.max())
    off = width - lens
    ids = torch.tensor([[pad_id] * (width - len(p)) + list(p) for p in prompts], dtype=torch.long, device=device)
    key_ok_p = torch.arange(width + max_new, device=device)[None, :] >= off[:, None]
    caches = [{"size": width + max_new} for _ in lm.blocks]
    pos = (torch.arange(width, device=device)[None, :] - off[:, None]).clamp_min(0)
    h = forward_rows(lm, ids, caches, 0, pos, key_ok_p)[:, -1]
    for c in caches:  # one prefill per prompt, then k rows per prompt
        c["k"], c["v"] = c["k"].repeat_interleave(k, 0), c["v"].repeat_interleave(k, 0)
    h, key_ok, lens_r = h.repeat_interleave(k, 0), key_ok_p.repeat_interleave(k, 0), lens.repeat_interleave(k)
    rows = n_p * k
    comp = torch.full((rows, max_new), pad_id, dtype=torch.long, device=device)
    alive = torch.ones(rows, dtype=torch.bool, device=device)
    cmask = torch.zeros(rows, max_new, dtype=torch.bool, device=device)
    reason = ["length"] * rows
    stop_t = torch.tensor(stop_ids, dtype=torch.long, device=device)
    for t in range(max_new):
        logits = lm.head(h).float()
        if temperature <= 0:
            nxt = logits.argmax(-1)
        else:
            nxt = torch.multinomial(torch.softmax(logits / temperature, -1), 1, generator=generator).squeeze(-1)
        nxt = torch.where(alive, nxt, torch.full_like(nxt, pad_id))
        cmask[:, t] = alive
        comp[:, t] = nxt
        hit = alive & torch.isin(nxt, stop_t)
        for r in hit.nonzero().flatten().tolist():
            reason[r] = f"stop:{int(nxt[r])}"
        alive = alive & ~hit
        if not bool(alive.any()):
            break
        if t + 1 < max_new:
            h = forward_rows(lm, nxt[:, None], caches, width + t, (lens_r + t)[:, None], key_ok)[:, -1]
    lm.train(was)
    out = []
    for i, p in enumerate(prompts):
        sl = slice(i * k, (i + 1) * k)
        prompt = torch.tensor([list(p)] * k, dtype=torch.long, device=device)
        out.append((torch.cat([prompt, comp[sl]], 1), cmask[sl], reason[sl]))
    return out
