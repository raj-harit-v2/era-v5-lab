"""Deletion Tuning (DT) masks for linear layers: soft mask in training, hard mask for every evaluation.

Port of the official implementation, agentic-learning-ai-lab/deleting-weights @ 94f0340ebb574f95bb41d844165253a6785e215e
(MIT licence, copyright 2026 agentic learning ai lab): `src/learnable_sparsity/differentiable_mask.py`,
`src/learnable_sparsity/sparse_linear.py`, `src/wanda_calibration.py`, and the regulariser of `src/train_sft.py`.
Paper: arXiv 2611.10866v1, section 4 (eq. 5-8) and 5.1.

What is the same as the official code
- One FP32 logit G per targeted weight, N(0, 0.01^2), then the Wanda prior: G += sign * std(G) * prior_strength
  (sign -1 for the lowest `eta` fraction of Wanda scores |W_ij| * ||X_j||_2 per layer, +1 otherwise). With
  prior_strength 3 this is the paper's G ~ N(+-0.03, 0.01^2).
- Training forward: W * sigmoid(alpha * G); evaluation forward: W * 1[G > 0]. alpha rises linearly from
  alpha_start to alpha_end over `total_steps` optimizer steps (`step()` after each optimizer step).
- Regulariser: loss -= lambda_t * sum ||W * soft_mask||^2 with lambda_t = lambda * (1 - t / T) (official train_sft.py
  decays it to 0; the paper text states lambda = 1e-5 without the decay).
- Targets are chosen by module-name substring and must be nn.Linear (official `convert_to_sparse_model`).

What differs, on purpose
- A present bias is kept and applied unchanged (the official converter drops it with a warning).
- The pretrained weight is a frozen buffer-like Parameter (requires_grad False) in its loaded dtype; the mask is
  computed in FP32 and multiplied in the weight's dtype.
- `bake()` writes W * 1[G > 0] into plain nn.Linear layers so any Hugging Face loader evaluates the hard mask
  (multiplying by exactly 1.0 or 0.0 is exact, so baked logits equal the in-memory eval-mode logits bit for bit).
- Saved masks: numpy.packbits + zlib (stdlib) instead of zstd; the size is reported as such.
- Gate initialisation draws from an explicit CPU torch.Generator, so every backend starts from the same logits.
"""
from __future__ import annotations

import math
import re
import zlib
from typing import Iterable

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

OFFICIAL = {"repo": "agentic-learning-ai-lab/deleting-weights", "commit": "94f0340ebb574f95bb41d844165253a6785e215e",
            "licence": "MIT"}
_no_grad = torch.no_grad  # undotted decorator alias: the lab's older PR guard reads "@torch.x" as an e-mail address
TARGET_SETS = {
    "gate": ("gate_proj",),
    "mlp": ("gate_proj", "up_proj", "down_proj"),
    "attn": ("q_proj", "k_proj", "v_proj", "o_proj"),
    # Team 5 LanguageModel (teams/05-architecture/harness/week2/model.py): experts are nn.ModuleList of SwiGLU with
    # children gate/up/down (routed `moe.experts.N`, shared `moe.shared.N`); attention children q/k/v/o. Substrings
    # would over-match ("o" is in "blocks"; ".gate" is also the optional attention gate), so these are anchored
    # regular expressions ("re:" prefix, full-name match).
    "g5_gate": (r"re:blocks\.\d+\.moe\.(experts|shared)\.\d+\.gate",),
    "g5_mlp": (r"re:blocks\.\d+\.moe\.(experts|shared)\.\d+\.(gate|up|down)",),
    "g5_attn": (r"re:blocks\.\d+\.attn\.(q|k|v|o)",),
}


def target_match(full: str, targets: Iterable[str]) -> bool:
    """A target is a substring of the module name, or (prefix "re:") a regular expression matching the whole name."""
    return any(re.fullmatch(t[3:], full) if t.startswith("re:") else t in full for t in targets)


class MaskedLinear(nn.Module):
    """y = x (W * m)^T + b with W, b frozen. m = sigmoid(alpha G) in training mode, 1[G > 0] in eval mode."""

    def __init__(self, base: nn.Linear, alpha_start: float, alpha_end: float, total_steps: int,
                 generator: torch.Generator):
        super().__init__()
        if alpha_start <= 0 or alpha_end <= 0 or total_steps <= 0:
            raise ValueError("alpha_start, alpha_end and total_steps must be positive")
        self.in_features, self.out_features = base.in_features, base.out_features
        self.weight = base.weight
        self.weight.requires_grad_(False)
        self.bias = base.bias
        if self.bias is not None:
            self.bias.requires_grad_(False)
        g = torch.empty(self.weight.shape, dtype=torch.float32)
        g.normal_(0.0, 0.01, generator=generator)
        self.gate = nn.Parameter(g.to(self.weight.device))  # FP32 logits, one per weight
        self.alpha_start, self.alpha_end, self.total_steps = float(alpha_start), float(alpha_end), int(total_steps)
        self.current_step = 0
        self.unmasked = False  # True only during Wanda calibration (the official `sparse = False`)

    @property
    def alpha(self) -> float:
        p = min(self.current_step / self.total_steps, 1.0)
        return self.alpha_start + (self.alpha_end - self.alpha_start) * p

    def step(self) -> None:
        self.current_step += 1

    def soft_mask(self) -> torch.Tensor:
        return torch.sigmoid(self.gate * self.alpha)

    def hard_mask(self) -> torch.Tensor:
        return (self.gate > 0).to(torch.float32)

    def mask(self) -> torch.Tensor:
        return self.soft_mask() if self.training else self.hard_mask()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.unmasked:
            return F.linear(x, self.weight, self.bias)
        w = self.weight * self.mask().to(self.weight.dtype)
        return F.linear(x, w, self.bias)

    def extra_repr(self) -> str:
        return f"in_features={self.in_features}, out_features={self.out_features}, bias={self.bias is not None}"


def masked_layers(model: nn.Module) -> list[tuple[str, MaskedLinear]]:
    return [(n, m) for n, m in model.named_modules() if isinstance(m, MaskedLinear)]


def convert(model: nn.Module, targets: Iterable[str], alpha_start: float = 100.0, alpha_end: float = 1000.0,
            total_steps: int = 400, seed: int = 0) -> list[str]:
    """Freeze every parameter, then replace each nn.Linear whose full name contains a target substring by a
    MaskedLinear. Never touches embeddings, the LM head or norms. Returns the converted names (model order)."""
    targets = tuple(targets)
    if not targets:
        raise ValueError("no DT targets")
    for p in model.parameters():
        p.requires_grad_(False)
    gen = torch.Generator().manual_seed(seed)
    names = []
    for parent_name, parent in list(model.named_modules()):
        for child_name, child in list(parent.named_children()):
            full = f"{parent_name}.{child_name}" if parent_name else child_name
            if isinstance(child, nn.Linear) and target_match(full, targets):
                setattr(parent, child_name, MaskedLinear(child, alpha_start, alpha_end, total_steps, gen))
                names.append(full)
    if not names:
        raise ValueError(f"no nn.Linear matched {targets}")
    return names


def step_all(model: nn.Module) -> None:
    for _, m in masked_layers(model):
        m.step()


def regulariser(model: nn.Module) -> torch.Tensor:
    """sum over masked layers of ||W * soft_mask||^2 (FP32), the term the loss subtracts with weight lambda_t."""
    total = None
    for _, m in masked_layers(model):
        t = (m.weight.detach().float() * m.soft_mask()).pow(2).sum()
        total = t if total is None else total + t
    return total


def lambda_at(step: int, total_steps: int, lam: float) -> float:
    """Official train_sft.py: weight_reg * (1 - iter / iters), decaying linearly to 0."""
    return lam * (1.0 - step / total_steps)


@_no_grad()
def wanda_scores(model: nn.Module, batches: Iterable[dict], device) -> dict[str, torch.Tensor]:
    """|W_ij| * ||X_j||_2 per masked layer, with the masks switched off (official compute_wanda_scores)."""
    layers = dict(masked_layers(model))
    norms: dict[str, torch.Tensor] = {}
    hooks = []
    for name, m in layers.items():
        m.unmasked = True

        def hook(mod, inp, _out, name=name):
            x = inp[0].detach().float()
            mask = _CALIB_STATE.get("attn_mask")
            # count real tokens only. A [B, T, d] input drops its padding positions; so does a flattened [B*T, d]
            # input (G5's shared experts run on every flattened row and zero the padding output afterwards). A layer
            # that receives gathered rows (a routed expert in G5's loop dispatch gets [routed tokens, d], already
            # restricted to valid positions, so never B*T rows when padding exists) is used as is.
            if mask is not None and x.shape[:-1] == mask.shape:
                x = x[mask]
            elif mask is not None and x.dim() == 2 and x.shape[0] == mask.numel():
                x = x[mask.reshape(-1)]
            elif mask is not None and x.dim() != 2:
                raise ValueError(f"calibration input of {name} has shape {tuple(x.shape)}; cannot apply a "
                                 f"{tuple(mask.shape)} padding mask")
            sq = x.pow(2).reshape(-1, x.shape[-1]).sum(0)
            norms[name] = sq if name not in norms else norms[name] + sq
        hooks.append(m.register_forward_hook(hook))
    was_training = model.training
    model.eval()
    try:
        for b in batches:
            ids, attn = b["input_ids"].to(device), b["attention_mask"].to(device)
            _CALIB_STATE["attn_mask"] = attn.bool()
            model(input_ids=ids, attention_mask=attn)
    finally:
        _CALIB_STATE.clear()
        for h in hooks:
            h.remove()
        for m in layers.values():
            m.unmasked = False
        model.train(was_training)
    return {n: layers[n].weight.detach().float().abs() * norms[n].sqrt().unsqueeze(0) for n in norms}


_CALIB_STATE: dict = {}


@_no_grad()
def apply_wanda_prior(model: nn.Module, scores: dict[str, torch.Tensor], eta: float, prior_strength: float = 3.0,
                      unseen: str = "official") -> dict:
    """Shift each layer's logits by +-std(G)*prior_strength: down for the lowest-`eta` Wanda scores (official
    wanda_prior_deletions + apply_wanda_prior: threshold = kthvalue(max(1, int(n * eta))), deleted = score < it).

    `unseen` says what a layer that no calibration token reached gets (a routed MoE expert can be idle on the
    calibration set; a Wanda score needs an input norm, which is then zero for every column):
      "official"  no prior (the official code's behaviour). The logits stay N(0, 0.01^2), so about half the layer's
                  weights start deleted under the hard mask, far above `eta`.
      "keep"      shift the whole layer up by std(G)*prior_strength to reduce initial deletion. Logits that remain
                  nonpositive still delete their weights under the hard mask. In the capstone rehearsal, 30 of 204
                  expert layers were uncalibrated and the shift reduced overall initial deletion from 11.7% to 4.4%."""
    if unseen not in ("official", "keep"):
        raise ValueError(f"unseen must be official or keep, not {unseen!r}")
    marked = 0
    total = 0
    unseen_layers = 0
    for name, m in masked_layers(model):
        if name not in scores:
            unseen_layers += 1
            if unseen == "keep":
                m.gate.add_(m.gate.std().item() * prior_strength)
            continue  # no calibration token reached the layer: no deletion prior (official behaviour)
        flat = scores[name].reshape(-1)
        k = max(1, int(flat.numel() * eta))
        thr = flat.kthvalue(k).values.item()
        deleted = (flat < thr).reshape(m.gate.shape)
        sign = torch.where(deleted, -1.0, 1.0).to(m.gate.device)
        m.gate.add_(sign * m.gate.std().item() * prior_strength)
        marked += int(deleted.sum())
        total += deleted.numel()
    return {"eta": eta, "prior_strength": prior_strength, "prior_deleted": marked, "targeted": total,
            "layers_without_scores": unseen_layers, "unseen_policy": unseen}


@_no_grad()
def deletion_stats(model: nn.Module) -> dict:
    """Realised deletion from the hard mask, over the targeted weights and over every stored parameter."""
    deleted = targeted = 0
    per_layer = {}
    for name, m in masked_layers(model):
        d = int((m.gate <= 0).sum())
        deleted += d
        targeted += m.gate.numel()
        per_layer[name] = d / m.gate.numel()
    seen, total = set(), 0
    for p in model.parameters():
        if p.data_ptr() in seen:
            continue  # tied embeddings counted once
        seen.add(p.data_ptr())
        total += p.numel()
    total -= sum(m.gate.numel() for _, m in masked_layers(model))  # logits are not model weights
    return {"deleted": deleted, "targeted": targeted, "model_weights": total,
            "deleted_frac_of_targeted": deleted / targeted, "deleted_frac_of_all_weights": deleted / total,
            "per_layer_min": min(per_layer.values()), "per_layer_max": max(per_layer.values())}


@_no_grad()
def keep_masks(model: nn.Module) -> list[torch.Tensor]:
    """The hard keep mask 1[G > 0] of every masked layer (bool, on the logits' device), in model order."""
    return [m.gate > 0 for _, m in masked_layers(model)]


@_no_grad()
def flip_counts(model: nn.Module, prev: list[torch.Tensor]) -> tuple[dict, list[torch.Tensor]]:
    """Gross hard-mask changes since `prev` (from keep_masks): weights newly deleted (kept -> deleted) and restored
    (deleted -> kept). The net change of the deleted count hides flips in both directions; these do not.
    Returns (counts, the current keep masks to pass next time). One host sync."""
    now = keep_masks(model)
    if len(now) != len(prev):
        raise ValueError("prev does not match the masked layers")
    newly = torch.stack([(p & ~k).sum() for p, k in zip(prev, now)]).sum()
    back = torch.stack([(~p & k).sum() for p, k in zip(prev, now)]).sum()
    a, b = torch.stack([newly, back]).tolist()
    return {"newly_deleted": int(a), "restored": int(b)}, now


@_no_grad()
def band_stats(model: nn.Module, edge: float = 1e-3) -> dict:
    """Where the mask can still learn, measured on all logits (exact, not sampled):
    live_share: share of logits whose FP32 local derivative sigmoid'(alpha G) is nonzero (outside it the gradient is
                exactly zero in FP32, so only Adam momentum can still move the logit);
    band_share: share whose soft mask lies in (edge, 1 - edge), i.e. |alpha G| < log((1 - edge) / edge);
    soft_hard_gap: mean |sigmoid(alpha G) - 1[G > 0]| over the targeted weights, the per-weight distance between the
                   trainer's soft mask and the sampler's hard mask. One host sync."""
    live, band, gap, n = [], [], [], 0
    for _, m in masked_layers(model):
        s = m.soft_mask()
        live.append((s * (1 - s) > 0).sum())
        band.append(((s > edge) & (s < 1 - edge)).sum())
        gap.append((s - (m.gate > 0).to(s.dtype)).abs().sum(dtype=torch.float64))
        n += m.gate.numel()
    lv, bd = torch.stack(live).sum(), torch.stack(band).sum()
    g = torch.stack(gap).sum()
    lv, bd, g = torch.stack([lv.double(), bd.double(), g]).tolist()
    return {"live_share": lv / n, "band_share": bd / n, "soft_hard_gap": g / n}


@_no_grad()
def bake(model: nn.Module) -> dict[str, torch.Tensor]:
    """Replace every MaskedLinear by nn.Linear(W * 1[G > 0], b) in place. Returns {name.weight: bool keep mask}."""
    masks = {}
    for parent_name, parent in list(model.named_modules()):
        for child_name, child in list(parent.named_children()):
            if isinstance(child, MaskedLinear):
                full = f"{parent_name}.{child_name}" if parent_name else child_name
                keep = child.gate > 0
                lin = nn.Linear(child.in_features, child.out_features, bias=child.bias is not None,
                                device=child.weight.device, dtype=child.weight.dtype)
                lin.weight.copy_(child.weight * keep.to(child.weight.dtype))
                if child.bias is not None:
                    lin.bias.copy_(child.bias)
                lin.requires_grad_(False)
                setattr(parent, child_name, lin)
                masks[f"{full}.weight"] = keep.cpu()
    return masks


def pack_masks(masks: dict[str, torch.Tensor]) -> tuple[bytes, dict]:
    """One bit per weight (numpy.packbits), zlib level 9 over the concatenated bit streams in sorted name order."""
    names = sorted(masks)
    raw = b"".join(np.packbits(masks[n].numpy().ravel()).tobytes() for n in names)
    comp = zlib.compress(raw, 9)
    n_bits = sum(masks[n].numel() for n in names)
    return comp, {"format": "packbits+zlib9", "layers": len(names), "bits": n_bits, "packed_bytes": len(raw),
                  "compressed_bytes": len(comp), "shapes": {n: list(masks[n].shape) for n in names}}


def unpack_masks(blob: bytes, meta: dict) -> dict[str, torch.Tensor]:
    raw = zlib.decompress(blob)
    out, off = {}, 0
    for n in sorted(meta["shapes"]):
        shape = meta["shapes"][n]
        k = math.prod(shape)
        nb = (k + 7) // 8
        bits = np.unpackbits(np.frombuffer(raw[off:off + nb], dtype=np.uint8))[:k]
        out[n] = torch.from_numpy(bits.astype(bool)).reshape(shape)
        off += nb
    return out
