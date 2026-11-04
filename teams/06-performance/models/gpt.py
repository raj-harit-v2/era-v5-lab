"""NanoGPT, driven only by ModelConfig.  [implemented: dense core; MoE / KE v1 / reversible plug in]

Parts and where they come from:
  * GQAttention (grouped-query attention): hd = d / n_head; c_attn = Linear(d, (n_head + 2 * n_kv_head) * hd) gives
    q, k, v; F.scaled_dot_product_attention(is_causal=True, enable_gqa=True) shares each k/v head with
    n_head / n_kv_head query heads without copying (torch >= 2.5; older torch: repeat_interleave copies).
    c_proj = Linear(d, d). Both Linears have bias.
    Attributes n_head, n_kv_head. n_kv_head == n_head is plain multi-head. The attention test reads these names.
    cfg.attn_impl "eager" (G5 config_v0: fast attention backward does not repeat, so two seeds would not match):
    repeat_interleave k, v to n_head heads, then softmax(q k^T / sqrt(hd) + causal mask) v by explicit matmuls.
    Same region names as SDPA (".sdpa" times the attention core either way).
    cfg.position "rope": q and k are rotated before attention (RoFormer, half-split layout as in GPT-NeoX / LLaMA):
    head dim hd, pair i = (x[i], x[i + hd/2]) for i < hd/2, angle t * rope_theta^(-2i / hd) at position t;
        rope(x)[i] = x[i] cos - x[i + hd/2] sin,   rope(x)[i + hd/2] = x[i + hd/2] cos + x[i] sin.
    Every dim of the head is rotated (no partial RoPE). cos / sin are non-persistent fp32 buffers [block_size, 1, hd]
    (not in the state_dict); under autocast the rotation runs in fp32 and is written in q's dtype. Inside ".qkv".
    q and k are rotated in one call, x * cos + roll(x) * sin, 3 kernels (apply_rope). The model is launch-bound at
    d = 256, so RoPE's cost is mostly host time per kernel: the first per-element form (9 kernels per call, q and k
    apart) added 456 kernels per step and 19% to the step on an A100.
  * MLP, h = mlp_ratio*d. cfg.activation "gelu": c_fc = Linear(d, h), GELU, c_proj = Linear(h, d), with biases.
    "swiglu": c_proj(SiLU(c_gate(x)) * c_fc(x)), c_gate and c_fc = Linear(d, h), c_proj = Linear(h, d), no biases
    (Shazeer 2020; LLaMA). Three matrices instead of two: at the same h it has 1.5x the FFN parameters and FLOPs.
    The routed and shared experts of models.moe use the same two forms (ExpertMLP).
  * Block i: pre-LN. ffn = MLP, or models.moe.SparseMoE when cfg.ffn == "moe".
        f(p) = a + FFN(LN2(p + a)),  a = Attn(LN1(p))
    Pre-LN only: Post-LN, LN(x + f(x)), normalises the residual stream, and a LayerNorm cannot be
    inverted, so the midpoint stack could not rebuild its inputs. The plain stack uses the same f:
    forward(x) = x + f(x).
    For the reversible stack the block also has update() and invert() (models/reversible.py):
        update(prev, curr) = prev + 2h * f(curr)          invert(prev_out, curr_out) = curr_out - 2h * f(prev_out)
  * GPT: token embedding (nn.Embedding tied with the head, or models.ke1.KroneckerEmbedding with an
    untied head: the codec dim is not d_model), learned position table (cfg.position "learned"; none with
    "rope"), blocks (plain loop or
    models.reversible.ReversibleStack), ln_f, head, fp32 cross-entropy.
  * Init (NanoGPT): weights normal(0, 0.02), biases zero, residual projections (c_proj)
    normal(0, 0.02 / sqrt(2 * n_layer)); MoE experts get the same (proj_std). KE initialises its projection.
  * MTP (cfg.mtp, G5 config_v0): a second untied head, mtp_head = Linear(d, V, bias=False), reads the same ln_f
    output and predicts token t+2 (targets shifted by one more; the last position has none). The returned loss is
    ntp + mtp, the sum G5 backpropagates; model.loss_parts holds both, detached, for logging (G5 logs ntp as loss).
  * Loss: cfg.ce_impl "torch" materialises logits [B*T, V]; "chunked" checkpoints position chunks;
    "fused" tiles tokens by ce_chunks and saves head gradients computed while logits are resident;
    "fused_cached" / "fused_liger" use fixed token tile sizes; "fused_cce" streams vocabulary tiles
    and recomputes logits during backward. "triton_ce" uses the in-repo Triton CE reduction kernel.
    Memory-bounded paths return logits=None when targets are given. Loss averages non-ignored targets.

Timing markers (roofline and report read these names; keep them)
  region("embed", 2)                       around tok (+ pos) embedding (KE adds "embed.ke" at level 3 inside)
  region("stack", 1)                       around all blocks
  region(f"block{i}", 2)                   around each block (plain stack; the reversible stack sets its own)
  region(f"block{i}.ln1" / ".ln2", 3)      each LayerNorm
  region(f"block{i}.attn.qkv" / ".attn.sdpa" / ".attn.proj", 3)
  region(f"block{i}.mlp", 3)               dense FFN (MoE regions are set inside models/moe.py)
  region("head+loss", 2)                   ln_f + head + cross-entropy (+ MTP head and its loss)
  region("head+loss.mtp", 3)               MTP head + its cross-entropy (cfg.mtp only)
  mark(x, "stack", 1)                      on the embedding output (backward of the stack ends here)
  mark(x, f"block{i}", 2)                  on each block input (plain stack only)
  mark(x, "head+loss", 1)                  on the stack output
  How bench turns these points into bwd:<name> segments (bwd:stack = the whole stack): perfkit/bench.py step 6.

The optional in-repo Triton CE path is in kernels/linear_ce_fused.py; aux / z loss for non-reversible MoE
remains a follow-up.
"""
from __future__ import annotations

import math

import torch
import torch.utils.checkpoint
import torch.nn as nn
import torch.nn.functional as F

from models.config import ModelConfig
from models.linear_ce import (linear_cross_entropy_fused, linear_cross_entropy_cached,
                              linear_cross_entropy_cce, linear_cross_entropy_liger)
from kernels.linear_ce_fused import linear_cross_entropy_fused_triton
from perfkit.regions import mark, region


_SDPA_GQA = tuple(int(v) for v in torch.__version__.split(".")[:2]) >= (2, 5)

IGNORE_INDEX = -100              # a target with this value is left out of the loss and of its divisor (loss masks)
MEMORY_BOUNDED_CE_IMPLS = ("chunked", "fused", "fused_cached", "fused_liger", "fused_cce",
                           "triton_ce")


def _init_linear(lin: nn.Linear, std: float = 0.02):
    nn.init.normal_(lin.weight, mean=0.0, std=std)
    if lin.bias is not None:
        nn.init.zeros_(lin.bias)


def _residual_std(cfg: ModelConfig) -> float:
    return 0.02 / math.sqrt(2 * cfg.n_layer)


def _matmul_weights(module: nn.Module) -> int:
    """Weights of every nn.Linear in an FFN (dense MLP or one expert): 2 * d * h for GELU, 3 * d * h for SwiGLU."""
    return sum(m.weight.numel() for m in module.modules() if isinstance(m, nn.Linear))


def rope_tables(T: int, hd: int, theta: float, device=None):
    """cos, sin [T, hd] fp32 of the RoPE angles t * theta^(-2i / hd), computed in fp64, full width for apply_rope:
    cos = [cos, cos], sin = [-sin, sin] (the sign of the first half is in the table)."""
    inv_freq = theta ** (-torch.arange(0, hd, 2, dtype=torch.float64, device=device) / hd)
    ang = torch.outer(torch.arange(T, dtype=torch.float64, device=device), inv_freq)
    cos, sin = ang.cos(), ang.sin()
    return torch.cat([cos, cos], -1).float(), torch.cat([-sin, sin], -1).float()


def _rotate(x, cos, sin, sign=1.0):
    """x * cos + sign * roll(x, hd/2) * sin. fp32 tables promote a bf16 x, so it is computed in fp32; addcmul writes
    the result in x's dtype itself (out=, same rounding as .to()): 3 kernels, no separate cast."""
    return torch.addcmul(x * cos, x.roll(x.size(-1) // 2, -1), sin, value=sign, out=torch.empty_like(x))


class _Rope(torch.autograd.Function):
    """y = x * cos + R(x) * sin with R = roll by hd/2. R is its own inverse and transpose, and R(sin) = -sin, so
    dx = g * cos + R(g * sin) = g * cos - R(g) * sin: the backward is the rotation by -angle, 3 kernels like the
    forward (autograd's own backward of the forward ops took about twice as many)."""

    @staticmethod
    def forward(ctx, x, cos, sin):
        ctx.save_for_backward(cos, sin)
        return _rotate(x, cos, sin)

    @staticmethod
    def backward(ctx, g):
        cos, sin = ctx.saved_tensors
        return _rotate(g, cos, sin, -1.0), None, None


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """Half-split rotation of the last dim. cos, sin: rope_tables rows, broadcastable to x.
    roll(x, hd/2) = [x2, x1], so x * cos + roll(x) * sin = [x1 cos - x2 sin, x2 cos + x1 sin] (the first per-element
    form was 9 kernels per call). The model is launch-bound (host-bound) at d = 256, so the host cost per call counts:
    without grad (the reversible forward and invert, 2 of the 3 calls per layer and step) no autograd.Function."""
    if torch.is_grad_enabled() and x.requires_grad:
        return _Rope.apply(x, cos, sin)
    return _rotate(x, cos, sin)


class GQAttention(nn.Module):
    def __init__(self, cfg: ModelConfig, name: str):
        super().__init__()
        d = cfg.n_embd
        self.n_head, self.n_kv_head, self.name = cfg.n_head, cfg.n_kv_head, name
        self.eager = cfg.attn_impl == "eager"
        self.rope = cfg.position == "rope"
        if self.rope:
            # fp32 on purpose: train under autocast, not model.to(bf16), which would cast these to bf16 as well and
            # lose the angle precision at large t (test_attention's pairs fail with bf16 tables).
            cos, sin = rope_tables(cfg.block_size, d // cfg.n_head, cfg.rope_theta)
            self.register_buffer("rope_cos", cos[:, None], persistent=False)   # [block_size, 1, hd]: broadcasts over
            self.register_buffer("rope_sin", sin[:, None], persistent=False)   # the heads, no reshape per call
        self.c_attn = nn.Linear(d, (cfg.n_head + 2 * cfg.n_kv_head) * (d // cfg.n_head))
        self.c_proj = nn.Linear(d, d)
        _init_linear(self.c_attn)
        _init_linear(self.c_proj, _residual_std(cfg))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        hd, kv = C // self.n_head, self.n_kv_head
        with region(f"{self.name}.qkv", 3):
            qkv = self.c_attn(x)
            if self.rope:                            # q and k heads side by side: one rotation for both
                qk, v = qkv.split([C + kv * hd, kv * hd], dim=2)   # split: its backward is one cat (two slices: 5 kernels)
                qk = qk.view(B, T, self.n_head + kv, hd)
                cos, sin = self.rope_cos, self.rope_sin
                if T != cos.size(0):
                    cos, sin = cos[:T], sin[:T]
                q, k = apply_rope(qk, cos, sin).split([self.n_head, kv], dim=2)
                v = v.view(B, T, kv, hd)
            else:
                q, k, v = qkv.split([C, kv * hd, kv * hd], dim=2)
                q, k, v = q.view(B, T, self.n_head, hd), k.view(B, T, kv, hd), v.view(B, T, kv, hd)
            q, k, v = q.transpose(1, 2), k.transpose(1, 2), v.transpose(1, 2)
            gqa = kv != self.n_head
            if gqa and (self.eager or not _SDPA_GQA):
                k = k.repeat_interleave(self.n_head // kv, dim=1)
                v = v.repeat_interleave(self.n_head // kv, dim=1)
        with region(f"{self.name}.sdpa", 3):
            if self.eager:
                future = torch.triu(torch.ones(T, T, dtype=torch.bool, device=x.device), diagonal=1)
                att = (q @ k.transpose(-2, -1)) / math.sqrt(hd)
                y = F.softmax(att.masked_fill(future, float("-inf")), dim=-1) @ v
            elif gqa and _SDPA_GQA:
                y = F.scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=True)
            else:
                y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        with region(f"{self.name}.proj", 3):
            return self.c_proj(y.transpose(1, 2).contiguous().view(B, T, C))


class MLP(nn.Module):
    def __init__(self, cfg: ModelConfig, name: str):
        super().__init__()
        d, h = cfg.n_embd, cfg.mlp_ratio * cfg.n_embd
        self.name, self.swiglu = name, cfg.activation == "swiglu"
        bias = not self.swiglu                       # SwiGLU: no biases (G6 Task 0, until G5 says otherwise)
        self.c_fc = nn.Linear(d, h, bias=bias)       # gelu: the input projection; swiglu: the "up" (linear) branch
        self.c_proj = nn.Linear(h, d, bias=bias)
        _init_linear(self.c_fc)
        _init_linear(self.c_proj, _residual_std(cfg))
        if self.swiglu:                              # made last, so the GELU model draws the same init as before
            self.c_gate = nn.Linear(d, h, bias=False)
            _init_linear(self.c_gate)

    def forward(self, x):
        with region(self.name, 3):
            if self.swiglu:
                return self.c_proj(F.silu(self.c_gate(x)) * self.c_fc(x))
            return self.c_proj(F.gelu(self.c_fc(x)))


class Block(nn.Module):
    def __init__(self, cfg: ModelConfig, i: int):
        super().__init__()
        d = cfg.n_embd
        self.name, self.h = f"block{i}", cfg.rev_h
        self.ln1 = nn.LayerNorm(d)
        self.attn = GQAttention(cfg, f"{self.name}.attn")
        self.ln2 = nn.LayerNorm(d)
        if cfg.ffn == "moe":
            from models.moe import SparseMoE
            hidden = cfg.moe.get("ffn_hidden")
            if hidden is None:
                hidden = cfg.mlp_ratio * d
            moe_kwargs = {
                key: value for key, value in cfg.moe.items()
                if key != "ffn_hidden"
            }
            self.ffn = SparseMoE(
                d, expert_hidden=hidden, name=f"{self.name}.moe",
                proj_std=_residual_std(cfg), activation=cfg.activation, **moe_kwargs
            )
        else:
            self.ffn = MLP(cfg, f"{self.name}.mlp")

    def _ln(self, ln, x, tag):
        with region(f"{self.name}.{tag}", 3):
            return ln(x)

    def f(self, p):
        """Residual function: both stacks add (a multiple of) it to the stream."""
        a = self.attn(self._ln(self.ln1, p, "ln1"))
        return a + self.ffn(self._ln(self.ln2, p + a, "ln2"))

    def update(self, prev, curr):
        return prev + 2 * self.h * self.f(curr)

    def invert(self, prev_out, curr_out):
        return curr_out - 2 * self.h * self.f(prev_out)

    def forward(self, x):
        """Plain residual block: x + f(x)."""
        return x + self.f(x)


class GPT(nn.Module):
    def __init__(self, cfg: ModelConfig, token_bytes=None):
        """token_bytes: (bytes [V, P] uint8, lens [V]) from models.ke1, only when cfg.embedding == 'ke1'."""
        super().__init__()
        self.cfg = cfg
        d = cfg.n_embd
        if cfg.embedding == "ke1":
            if token_bytes is None:
                raise ValueError("embedding=ke1 needs the tokenizer's byte table (token_bytes)")
            if token_bytes[0].size(0) != cfg.vocab_size or token_bytes[1].size(0) != cfg.vocab_size:
                raise ValueError("KE byte table must match model.vocab_size")
            from models.ke1 import KroneckerEmbedding
            self.tok = KroneckerEmbedding(token_bytes, d, cfg.ke_max_pos, cfg.ke_mode)
        elif cfg.embedding == "ke2":
            from models.ke2 import KE2Embedding
            self.tok = KE2Embedding(cfg.vocab_size, d, cfg.ke_max_pos, token_bytes)   # G4's raw table by default
        else:
            self.tok = nn.Embedding(cfg.vocab_size, d)
            nn.init.normal_(self.tok.weight, mean=0.0, std=0.02)
        self.pos = None
        if cfg.position == "learned":
            self.pos = nn.Embedding(cfg.block_size, d)
            nn.init.normal_(self.pos.weight, mean=0.0, std=0.02)
        self.blocks = nn.ModuleList(Block(cfg, i) for i in range(cfg.n_layer))
        self.ln_f = nn.LayerNorm(d)
        self.head = nn.Linear(d, cfg.vocab_size, bias=False)
        # Tie when embedding=table and tie_embeddings is not False (None keeps the legacy table-tied default).
        if cfg.embedding == "table" and cfg.tie_embeddings is not False:
            self.head.weight = self.tok.weight
        else:
            nn.init.normal_(self.head.weight, mean=0.0, std=0.02)
        if cfg.mtp:
            self.mtp_head = nn.Linear(d, cfg.vocab_size, bias=False)
            nn.init.normal_(self.mtp_head.weight, mean=0.0, std=0.02)
        self.loss_parts = None

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None):
        """idx, targets: [B, T] int64. Returns (logits, loss); loss is None without targets."""
        B, T = idx.shape
        if T > self.cfg.block_size:
            raise ValueError(f"sequence length {T} > block_size {self.cfg.block_size}")
        if self.cfg.mtp and targets is not None and T < 2:
            raise ValueError("mtp needs T >= 2: the t+2 target of the last position does not exist")
        with region("embed", 2):
            x = self.embed(idx)
        x = mark(x, "stack", 1)
        with region("stack", 1):
            if self.cfg.reversible:
                from models.reversible import ReversibleOnePassStack, ReversibleStack
                stack = ReversibleOnePassStack if self.cfg.rev_impl == "one_pass" else ReversibleStack
                x = stack.apply(x, self.blocks)
            else:
                for i, blk in enumerate(self.blocks):
                    x = mark(x, f"block{i}", 2)
                    with region(f"block{i}", 2):
                        x = blk(x)
        x = mark(x, "head+loss", 1)
        with region("head+loss", 2):
            x = self.ln_f(x)
            if targets is not None and self.cfg.ce_impl in MEMORY_BOUNDED_CE_IMPLS:
                loss = self._head_ce(self.head, x.reshape(B * T, -1), targets.reshape(B * T))
                return None, self._add_mtp(loss, x, targets)
            logits = self.head(x)
            loss = None
            if targets is not None:
                loss = F.cross_entropy(logits.view(B * T, -1).float(), targets.reshape(B * T),
                                       ignore_index=IGNORE_INDEX)
                loss = self._add_mtp(loss, x, targets)
        return logits, loss

    def embed(self, idx: torch.Tensor) -> torch.Tensor:
        """Stack input: token embedding, plus the position table when cfg.position == 'learned'."""
        x = self.tok(idx)
        if self.pos is not None:
            x = x + self.pos(torch.arange(idx.shape[1], device=idx.device))
        return x

    def _add_mtp(self, ntp, x, targets):
        """ntp + the t+2 loss of mtp_head (cfg.mtp); ntp unchanged otherwise. x: ln_f output [B, T, d]."""
        if not self.cfg.mtp:
            return ntp
        with region("head+loss.mtp", 3):
            xm, ym = x[:, :-1].reshape(-1, x.shape[-1]), targets[:, 1:].reshape(-1)
            if self.cfg.ce_impl in MEMORY_BOUNDED_CE_IMPLS:
                mtp = self._head_ce(self.mtp_head, xm, ym)
            else:
                mtp = F.cross_entropy(self.mtp_head(xm).float(), ym, ignore_index=IGNORE_INDEX)
        self.loss_parts = {"ntp": ntp.detach(), "mtp": mtp.detach()}
        return ntp + mtp

    def _chunked_ce(self, head, x, y):
        """Compute mean CE of head(x) in checkpointed position chunks to bound saved logits memory.

        Same value as the plain path: the mean is over the targets that are not IGNORE_INDEX, so masked
        positions (SFT loss masks) do not count in the divisor. If every target is ignored the loss is 0
        (the plain path gives NaN there)."""
        def piece(xc, yc):
            return F.cross_entropy(head(xc).float(), yc, reduction="sum", ignore_index=IGNORE_INDEX)
        total = sum(torch.utils.checkpoint.checkpoint(piece, xc, yc, use_reentrant=False)
                    for xc, yc in zip(x.chunk(self.cfg.ce_chunks), y.chunk(self.cfg.ce_chunks)))
        return total / (y != IGNORE_INDEX).sum().clamp_min(1)

    def _head_ce(self, head, x, y):
        if self.cfg.ce_impl == "triton_ce":
            return linear_cross_entropy_fused_triton(x.reshape(-1, x.shape[-1]), head.weight,
                                                      y.reshape(-1), bias=head.bias,
                                                      ignore_index=IGNORE_INDEX)
        if self.cfg.ce_impl == "fused":
            return linear_cross_entropy_fused(
                x, head.weight, y, bias=head.bias,
                chunks=self.cfg.ce_chunks, ignore_index=IGNORE_INDEX,
            )
        if self.cfg.ce_impl == "fused_cached":
            return linear_cross_entropy_cached(
                x, head.weight, y, bias=head.bias,
                token_chunk=self.cfg.ce_token_chunk, ignore_index=IGNORE_INDEX,
            )
        if self.cfg.ce_impl == "fused_liger":
            return linear_cross_entropy_liger(
                x, head.weight, y, bias=head.bias,
                token_chunk=self.cfg.ce_token_chunk, ignore_index=IGNORE_INDEX,
            )
        if self.cfg.ce_impl == "fused_cce":
            return linear_cross_entropy_cce(
                x, head.weight, y, bias=head.bias,
                vocab_chunk=self.cfg.ce_vocab_chunk, ignore_index=IGNORE_INDEX,
            )
        return self._chunked_ce(head, x, y)

    def param_counts(self):
        """(total, active). active = matmul weights one token multiplies with: attention, router,
        top_k + shared experts, KE projection, LM head (and MTP head). Not biases, norms, lookup tables. Used for MFU.
        An FFN counts every Linear weight it has: 2 matrices for GELU, 3 for SwiGLU (c_gate, c_fc, c_proj).
        Counted by module, not by parameter name: a tied head shares its tensor with the embedding
        table and would otherwise drop out of the count."""
        total = sum(p.numel() for p in self.parameters())
        active = self.head.weight.numel() + (self.mtp_head.weight.numel() if self.cfg.mtp else 0)
        if self.cfg.embedding in ("ke1", "ke2"):
            active += self.tok.proj.weight.numel()
        for blk in self.blocks:
            active += blk.attn.c_attn.weight.numel() + blk.attn.c_proj.weight.numel()
            ffn = blk.ffn
            if isinstance(ffn, MLP):
                active += _matmul_weights(ffn)
            else:
                per_expert = _matmul_weights(ffn.experts[0])
                active += ffn.router.weight.numel() + per_expert * (ffn.top_k + len(ffn.shared))
        return total, active

    def moe_layers(self):
        """All SparseMoE modules (the bench calls update_bias() on each after every step)."""
        if self.cfg.ffn != "moe":
            return []
        return [blk.ffn for blk in self.blocks]
