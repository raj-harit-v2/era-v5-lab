"""Frozen MoE router: freeze the router weights, checksum them, and prove they did not change.

Gate 4 (TSAI plan, week 4): "Run the RL loop on the small MoE model with frozen router weights. Check that the router
checksum stays the same after RL." Evidence for freezing: in the MiMo-V2.6 report (arXiv 2610.11959) a trainable
router collapsed expert load within 20 RL steps, and freezing it fixed that.

Router parameter names (regex, matched against `model.named_parameters()`):
    OLMoE (Hugging Face)       model.layers.N.mlp.gate.weight      (not experts.gate_up_proj)
    Team 5 (harness/week2)     blocks.N.moe.router.weight
"""
from __future__ import annotations

import hashlib
import re

import torch
from torch import nn

ROUTER_PATTERNS = (r"(^|\.)mlp\.gate\.weight$", r"(^|\.)moe\.router\.weight$")


def router_params(model: nn.Module, patterns=ROUTER_PATTERNS) -> list[tuple[str, nn.Parameter]]:
    rx = [re.compile(p) for p in patterns]
    return [(n, p) for n, p in model.named_parameters() if any(r.search(n) for r in rx)]


def freeze_router(model: nn.Module, patterns=ROUTER_PATTERNS) -> list[str]:
    """Set requires_grad=False on every router weight. Raises if the model has none (wrong patterns)."""
    found = router_params(model, patterns)
    if not found:
        raise ValueError(f"no router parameters match {patterns}; is this an MoE model?")
    for _, p in found:
        p.requires_grad_(False)
    return [n for n, _ in found]


def router_checksum(model: nn.Module, patterns=ROUTER_PATTERNS) -> str:
    """SHA-256 over the router tensors' names, shapes, dtypes and exact bytes (in name order)."""
    h = hashlib.sha256()
    for name, p in sorted(router_params(model, patterns), key=lambda x: x[0]):
        t = p.detach().to("cpu").contiguous()
        h.update(f"{name}|{tuple(t.shape)}|{t.dtype}|".encode())
        h.update(t.view(torch.uint8).numpy().tobytes())  # raw bytes; works for bf16 too
    return h.hexdigest()


def router_bias_checksum(model: nn.Module) -> str | None:
    """SHA-256 over every `*.router_bias` buffer (Team 5's loss-free balancer, #748): never a parameter, so neither the
    trainable set nor router_checksum covers it, yet it changes which experts fire. None when the model has none.
    G10's trainers never call model.update_router_bias(); the owner's rule (23 Nov): the bias stays as delivered."""
    found = sorted((n, b) for n, b in model.named_buffers() if n.endswith("router_bias"))
    if not found:
        return None
    h = hashlib.sha256()
    for name, b in found:
        t = b.detach().to("cpu").contiguous()
        h.update(f"{name}|{tuple(t.shape)}|{t.dtype}|".encode())
        h.update(t.view(torch.uint8).numpy().tobytes())
    return h.hexdigest()


def router_bias_expected(spec) -> bool:
    """True when the arm's model config says a router bias exists and is read: MoE experts and moe.bias_gamma > 0
    (Team 5's MoE reads `router_bias` only then, #748). Dense or gamma 0: False."""
    moe = spec.get("moe") if isinstance(spec, dict) else None
    if not isinstance(moe, dict):
        return False
    return int(moe.get("num_experts") or 0) > 0 and float(moe.get("bias_gamma") or 0.0) > 0.0


def router_bias_record(model: nn.Module, before: str | None, after: str | None, spec=None) -> dict:
    """`router_bias_unchanged` for a report. The checksum is None when no buffer ends with `router_bias`; that is a pass
    only when the arm expects none. If the arm's config says a bias exists (router_bias_expected) and no buffer is found,
    pass is False with a reason: a renamed or unregistered buffer would otherwise compare None == None."""
    spec = spec if spec is not None else getattr(model, "spec", None)
    expected = router_bias_expected(spec)
    found = sum(1 for n, _ in model.named_buffers() if n.endswith("router_bias"))
    rec = {"before": before, "after": after, "expected": expected, "buffers": found, "pass": before == after,
           "rule": "the bias stays as delivered; update_router_bias() is never called"}
    if expected and found == 0:
        rec.update(passed_checksums=rec["pass"], **{"pass": False},
                   reason="the arm's config has MoE experts and bias_gamma > 0 but no buffer ends with router_bias "
                          "(renamed or not registered): the bias cannot be checked")
    elif before != after:
        rec["reason"] = "router_bias changed: something called update_router_bias()"
    return rec


def clear_router_bias_load(model: nn.Module) -> None:
    """Drop Team 5's per-layer train-mode load counts (`_balance_load`, not a buffer, so `.to()` does not move it) before a
    save or a device move. They only matter to update_router_bias(), which G10 never calls."""
    fn = getattr(model, "clear_router_bias_load", None)
    if callable(fn):
        fn()


def assert_router_frozen(model: nn.Module, patterns=ROUTER_PATTERNS) -> None:
    """Fails if any router weight is trainable."""
    trainable = [n for n, p in router_params(model, patterns) if p.requires_grad]
    if trainable:
        raise AssertionError(f"router weights are trainable: {trainable}")
