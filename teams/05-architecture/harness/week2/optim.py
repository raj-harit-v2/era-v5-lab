"""Week-2 optimizers: AdamW on every weight, or Muon on the 2D block weights and AdamW on the rest.

Muon is the plain loop path of teams/06-performance/models/optim.py (commit 0968eb8): momentum 0.95
with Nesterov, five Newton-Schulz steps with coefficients (3.4445, -4.7750, 2.0315), and the update
scaled by sqrt(max(1, rows/cols)). Timing regions, the batched path and polar_muon_adamw are not ported.
Muon takes optim.muon_lr and no weight decay (TSAI, 21 Nov); AdamW keeps optim.lr, betas, eps and weight_decay from
the arm chain.
"""

from __future__ import annotations
import torch

NS_COEFFS = (3.4445, -4.7750, 2.0315)
MUON = {"momentum": 0.95, "nesterov": True, "ns_steps": 5}


def _native_bf16():
    try:
        return torch.cuda.is_bf16_supported(including_emulation=False)
    except TypeError:
        return torch.cuda.get_device_capability()[0] >= 8


def zeropower_via_newtonschulz5(G, steps=5, eps=1e-7):
    """Approximately orthogonalise G (the U V^T of its SVD), in bf16 where the device has it."""
    a, b, c = NS_COEFFS
    X = G.to(torch.bfloat16 if (not G.is_cuda or _native_bf16()) else torch.float32)
    transpose = X.size(0) > X.size(1)
    if transpose:
        X = X.T
    X = X / (X.norm() + eps)
    for _ in range(steps):
        A = X @ X.T
        B = b * A + c * (A @ A)
        X = a * X + B @ X
    return X.T if transpose else X


def zeropower_batched(G, steps=5, eps=1e-7):
    """zeropower_via_newtonschulz5 for a stack G[n, rows, cols] of same-shape matrices."""
    a, b, c = NS_COEFFS
    X = G.to(torch.bfloat16 if (not G.is_cuda or _native_bf16()) else torch.float32)
    transpose = X.size(1) > 0 and X.size(1) > X.size(2)
    if transpose:
        X = X.transpose(1, 2)
    X = X / (X.flatten(1).norm(dim=1)[:, None, None] + eps)
    for _ in range(steps):
        A = X @ X.transpose(1, 2)
        B = b * A + c * (A @ A)
        X = a * X + B @ X
    return X.transpose(1, 2) if transpose else X


class Muon(torch.optim.Optimizer):
    def __init__(
        self, params, lr, momentum=0.95, nesterov=True, ns_steps=5, weight_decay=0.0
    ):
        super().__init__(
            params,
            dict(
                lr=lr,
                momentum=momentum,
                nesterov=nesterov,
                ns_steps=ns_steps,
                weight_decay=weight_decay,
            ),
        )

    @torch.no_grad()
    def step(self, closure=None):
        # Execution-only (TSAI): same update as the per-matrix loop, but matrices of one shape are
        # orthogonalised together in one batched Newton-Schulz call (far fewer kernel launches).
        for group in self.param_groups:
            by_shape = {}
            for p in group["params"]:
                # Like AdamW: an expert that saw no tokens gets no update and keeps its momentum.
                if p.grad is None:
                    continue
                state = self.state[p]
                if "buf" not in state:
                    state["buf"] = torch.zeros_like(p.grad)
                by_shape.setdefault((tuple(p.shape), p.dtype), []).append(p)
            for (shape, _), ps in by_shape.items():
                bufs = [self.state[p]["buf"] for p in ps]
                grads = [p.grad for p in ps]
                torch._foreach_lerp_(bufs, grads, 1 - group["momentum"])
                gs = torch._foreach_lerp(grads, bufs, group["momentum"]) if group["nesterov"] else bufs
                U = zeropower_batched(torch.stack(gs), group["ns_steps"])
                if group["weight_decay"]:
                    torch._foreach_mul_(ps, 1 - group["lr"] * group["weight_decay"])
                alpha = -group["lr"] * max(1.0, shape[0] / shape[1]) ** 0.5
                torch._foreach_add_(ps, [u.to(p.dtype) for u, p in zip(U.unbind(0), ps)], alpha=alpha)


class Optimizers:
    """Muon and AdamW behind one zero_grad()/step()/state_dict(), so the trainer loop is unchanged."""

    def __init__(self, named):
        self.named = named

    def zero_grad(self, set_to_none=True):
        for _, o in self.named:
            o.zero_grad(set_to_none=set_to_none)

    def step(self):
        for _, o in self.named:
            o.step()

    def state_dict(self):
        return {name: o.state_dict() for name, o in self.named}

    def load_state_dict(self, state):
        if set(state) != {name for name, _ in self.named}:
            raise ValueError("Optimizer state names differ: " + str(sorted(state)))
        for name, o in self.named:
            o.load_state_dict(state[name])


# Muon handles the selected block matrices. AdamW handles the remaining parameters.
def uses_muon(name, p, router_on_muon=True):
    """Attention, expert and router matrices inside the blocks. The embedding projection, heads and norm gains stay
    on AdamW. Router on Muon: TSAI, 23 Nov (default since #712 showed no quality or cost difference vs AdamW at one
    seed each, and current SOTA practice -- Kolibri, DeepSeek-V4.1-Flash -- treats the router as an ordinary 2D
    matrix). optim.router_on_muon: false moves it back to AdamW, for the router comparison run only."""
    return (
        p.ndim == 2
        and name.startswith("blocks.")
        and name.endswith(".weight")
        and (router_on_muon or ".moe.router." not in name)
    )


WSD_KEYS = ("warmup_frac", "decay_frac", "final_lr_frac")


def lr_scale(step, total, o):
    """Learning-rate multiplier at 1-based step `step` of a `total`-step run (TSAI's recipe, 21 Nov: WSD).

    constant: 1.0 at every step. wsd ("warmup, stable, decay"): linear warmup from 0 over the first
    round(warmup_frac * total) steps, flat at 1.0, then linear decay over the last round(decay_frac * total) steps,
    ending at final_lr_frac on the last step. The same multiplier scales every optimizer's own peak rate
    (Muon's muon_lr and AdamW's lr), as TSAI described ("same WSD shape as AdamW"). It depends only on the step,
    so a resumed run continues the same curve without saving any schedule state.
    """
    if o.get("schedule", "constant") == "constant":
        return 1.0
    warm = round(o["warmup_frac"] * total)
    decay = round(o["decay_frac"] * total)
    if warm and step <= warm:
        return step / warm
    start = total - decay
    if decay and step > start:
        return 1.0 - (1.0 - o["final_lr_frac"]) * (step - start) / decay
    return 1.0


def set_lr_scale(optimizer, scale):
    """Set every parameter group's rate to its peak rate times `scale`; works for AdamW alone and for Optimizers.

    The peak rate is kept in the group as base_lr, so it travels with the optimizer state through checkpoints.
    """
    inner = [o for _, o in optimizer.named] if isinstance(optimizer, Optimizers) else [optimizer]
    for opt in inner:
        for group in opt.param_groups:
            group.setdefault("base_lr", group["lr"])
            group["lr"] = group["base_lr"] * scale


def uses_head_sgd(name, o):
    """The whole output head group (TSAI, 21 Nov: "the whole head group together ... don't split it"), when
    optim.head_sgd is on. All output-head parameters live under head.* (Udit's convention, TSAI-approved)."""
    return bool(o.get("head_sgd", False)) and name.startswith("head.")


def build_optimizer(model, o):
    adamw = lambda params: torch.optim.AdamW(
        params,
        lr=o["lr"],
        betas=tuple(o["betas"]),
        eps=o["eps"],
        weight_decay=o["weight_decay"],
    )
    if o["name"] not in ["adamw", "muon"]:
        raise ValueError(
            "Unknown optimizer " + repr(o["name"]) + "; never replaced silently"
        )
    named = list(model.named_parameters())
    # Optional (TSAI recipe, 21 Nov): plain SGD with momentum on the head group only, off by default.
    head = [p for n, p in named if uses_head_sgd(n, o)]
    if o.get("head_sgd") and not head:
        raise ValueError("head_sgd is on but the model has no head.* parameters")
    sgd = (
        [("sgd", torch.optim.SGD(head, lr=o["head_sgd_lr"], momentum=o["head_sgd_momentum"]))]
        if head
        else []
    )
    if o["name"] == "adamw":
        if not sgd:
            return adamw(model.parameters())
        return Optimizers([("adamw", adamw([p for n, p in named if not uses_head_sgd(n, o)]))] + sgd)
    rom = bool(o.get("router_on_muon", True))
    muon = [p for n, p in named if uses_muon(n, p, rom)]
    rest = [p for n, p in named if not uses_muon(n, p, rom) and not uses_head_sgd(n, o)]
    if not muon or not rest:
        raise ValueError("Muon needs block matrices and AdamW parameters")
    return Optimizers(
        [
            (
                "muon",
                Muon(muon, lr=o["muon_lr"], weight_decay=0.0, **MUON),
            ),
            ("adamw", adamw(rest)),
        ]
        + sgd
    )


def describe(model, o):
    """What the run really used, for the manifest."""
    named = list(model.named_parameters())
    head_sgd = (
        {
            "head_sgd": True,
            "head_sgd_lr": o["head_sgd_lr"],
            "head_sgd_momentum": o["head_sgd_momentum"],
            "head_sgd_parameters": sum(p.numel() for n, p in named if uses_head_sgd(n, o)),
        }
        if o.get("head_sgd")
        else {"head_sgd": False}
    )
    if o["name"] == "adamw":
        return {"name": "adamw", "lr": o["lr"], "parameters": model.parameter_count(), **head_sgd}
    rom = bool(o.get("router_on_muon", True))
    return {
        "name": "muon",
        "source": "teams/06-performance/models/optim.py@0968eb8 (loop path)",
        "muon_lr": o["muon_lr"],
        "adamw_lr": o["lr"],
        **MUON,
        "ns_coefficients": list(NS_COEFFS),
        "router_on_muon": rom,
        "muon_parameters": sum(p.numel() for n, p in named if uses_muon(n, p, rom)),
        "adamw_parameters": sum(
            p.numel() for n, p in named if not uses_muon(n, p, rom) and not uses_head_sgd(n, o)
        ),
        **head_sgd,
    }
