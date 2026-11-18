"""Week-2 optimizers: AdamW on every weight, or Muon on the 2D block weights and AdamW on the rest.

Muon is the plain loop path of teams/06-performance/models/optim.py (commit 0968eb8): momentum 0.95
with Nesterov, five Newton-Schulz steps with coefficients (3.4445, -4.7750, 2.0315), and the update
scaled by sqrt(max(1, rows/cols)). Timing regions, the batched path and polar_muon_adamw are not ported.
Muon takes optim.muon_lr; AdamW keeps optim.lr, betas, eps and weight_decay from the arm chain.
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
def uses_muon(name, p):
    """Attention, router and expert matrices inside the blocks. Embedding projection, heads and norm gains stay on AdamW."""
    return p.ndim == 2 and name.startswith("blocks.") and name.endswith(".weight")


def build_optimizer(model, o):
    adamw = lambda params: torch.optim.AdamW(
        params,
        lr=o["lr"],
        betas=tuple(o["betas"]),
        eps=o["eps"],
        weight_decay=o["weight_decay"],
    )
    if o["name"] == "adamw":
        return adamw(model.parameters())
    if o["name"] != "muon":
        raise ValueError(
            "Unknown optimizer " + repr(o["name"]) + "; never replaced silently"
        )
    named = list(model.named_parameters())
    muon = [p for n, p in named if uses_muon(n, p)]
    rest = [p for n, p in named if not uses_muon(n, p)]
    if not muon or not rest:
        raise ValueError("Muon needs block matrices and AdamW parameters")
    return Optimizers(
        [
            (
                "muon",
                Muon(muon, lr=o["muon_lr"], weight_decay=o["weight_decay"], **MUON),
            ),
            ("adamw", adamw(rest)),
        ]
    )


def describe(model, o):
    """What the run really used, for the manifest."""
    if o["name"] == "adamw":
        return {"name": "adamw", "lr": o["lr"], "parameters": model.parameter_count()}
    named = list(model.named_parameters())
    return {
        "name": "muon",
        "source": "teams/06-performance/models/optim.py@0968eb8 (loop path)",
        "muon_lr": o["muon_lr"],
        "adamw_lr": o["lr"],
        **MUON,
        "ns_coefficients": list(NS_COEFFS),
        "muon_parameters": sum(p.numel() for n, p in named if uses_muon(n, p)),
        "adamw_parameters": sum(p.numel() for n, p in named if not uses_muon(n, p)),
    }
