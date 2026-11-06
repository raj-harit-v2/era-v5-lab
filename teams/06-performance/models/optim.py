"""Optimizers: adamw, muon (Muon + AdamW) or polar_muon_adamw (Polar Express Muon + AdamW, the default).

  build_optimizer(model, ocfg) -> Optimizers: zero_grad(), step(scaler=None), unscale(scaler), flops(), set_lr(...),
  state_dict(), load_state_dict(), and .named = [(region name, torch optimizer)]. ocfg = cfg["optim"].

Muon takes the 2D block weights (routers included); AdamW takes the embedding parameters (KE projection too), head,
norm gains and biases. Weight decay applies to AdamW matrices only. A parameter with grad=None is skipped.
muon: momentum 0.95 nesterov, NS5 (3.4445, -4.7750, 2.0315) in bf16 (fp32 without bf16), scaled by
max(1, rows / cols) ** 0.5. muon_impl loop | batched (same-shaped matrices stacked); adamw_impl loop | foreach.
flops(): Newton-Schulz FLOPs per step, sum of 5 * (4 m^2 n + 2 m^3), m <= n.
Regions: level 2 "opt.muon", "opt.adamw", "opt.polar_muon_adamw"; level 3 "opt.muon.ns", "opt.zero_grad".
"""
from __future__ import annotations

import math

import torch

from perfkit.regions import region

# Quintic Newton-Schulz coefficients of the original Muon (5 steps).
NS_COEFFS = (3.4445, -4.7750, 2.0315)

# Polar Express Muon coefficients (five iterations).
POLAR_EXPRESS_COEFFS = (
    (8.156554524902461, -22.48329292557795, 15.878769915207462),
    (4.042929935166739, -2.808917465908714, 0.5000178451051316),
    (3.8916678022926607, -2.772484153217685, 0.5060648178503393),
    (3.285753657755655, -2.3681294933425376, 0.46449024233003106),
    (2.3465413258596377, -1.7097828382687081, 0.42323551169305323),
)


def _native_bf16():
    """True when the GPU has native (not emulated) bf16."""
    try:
        return torch.cuda.is_bf16_supported(including_emulation=False)
    except TypeError:  # torch < 2.4
        return torch.cuda.get_device_capability()[0] >= 8


def zeropower_via_newtonschulz5(G: torch.Tensor, steps: int = 5, eps: float = 1e-7) -> torch.Tensor:
    """Approximately orthogonalise G (the U V^T of its SVD), in bf16 where the GPU has it."""
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


def zeropower_via_newtonschulz5_batched(G: torch.Tensor, steps: int = 5,
                                        eps: float = 1e-7) -> torch.Tensor:
    """Apply the same Newton-Schulz iteration independently to [batch, rows, cols]."""
    if G.ndim != 3 or G.size(0) == 0:
        raise ValueError(f"expected a nonempty [batch, rows, cols] tensor, got {tuple(G.shape)}")
    a, b, c = NS_COEFFS
    X = G.to(torch.bfloat16 if (not G.is_cuda or _native_bf16()) else torch.float32)
    transpose = X.size(1) > X.size(2)
    if transpose:
        X = X.transpose(1, 2)
    norms = torch.linalg.vector_norm(X, dim=(1, 2), keepdim=True)
    X = X / (norms + eps)
    for _ in range(steps):
        A = torch.bmm(X, X.transpose(1, 2))
        B = b * A + c * torch.bmm(A, A)
        X = a * X + torch.bmm(B, X)
    return X.transpose(1, 2) if transpose else X


class Muon(torch.optim.Optimizer):
    """Nesterov momentum, then the Newton-Schulz orthogonalised update scaled by max(1, rows / cols) ** 0.5."""

    def __init__(self, params, lr=0.02, momentum=0.95, nesterov=True, ns_steps=5,
                 weight_decay=0.0, impl="loop"):
        if impl not in ("loop", "batched"):
            raise ValueError(f"Muon impl {impl!r}: loop | batched")
        super().__init__(params, dict(lr=lr, momentum=momentum, nesterov=nesterov,
                                      ns_steps=ns_steps, weight_decay=weight_decay, impl=impl))

    @staticmethod
    def _update_one(p, group, state):
        if p.grad is None:
            return
        if "buf" not in state:
            state["buf"] = torch.zeros_like(p.grad)
        buf = state["buf"]
        buf.lerp_(p.grad, 1 - group["momentum"])
        g = p.grad.lerp(buf, group["momentum"]) if group["nesterov"] else buf
        with region("opt.muon.ns", 3):
            u = zeropower_via_newtonschulz5(g, group["ns_steps"])
        if group["weight_decay"]:
            p.mul_(1 - group["lr"] * group["weight_decay"])
        p.add_(u.to(p.dtype), alpha=-group["lr"] * max(1.0, p.size(0) / p.size(1)) ** 0.5)

    def _update_batched(self, params, group):
        # Momentum buffers remain attached to their parameters; only the transient NS inputs are stacked.
        grads = []
        for p in params:
            state = self.state[p]
            if "buf" not in state:
                state["buf"] = torch.zeros_like(p.grad)
            buf = state["buf"]
            buf.lerp_(p.grad, 1 - group["momentum"])
            grads.append(p.grad.lerp(buf, group["momentum"]) if group["nesterov"] else buf)
        with region("opt.muon.ns", 3):
            updates = zeropower_via_newtonschulz5_batched(torch.stack(grads), group["ns_steps"])
        for p, update in zip(params, updates.unbind(0)):
            if group["weight_decay"]:
                p.mul_(1 - group["lr"] * group["weight_decay"])
            scale = group["lr"] * max(1.0, p.size(0) / p.size(1)) ** 0.5
            p.add_(update.to(p.dtype), alpha=-scale)

    @torch.no_grad()
    def step(self, closure=None):
        for group in self.param_groups:
            if group.get("impl", "loop") == "loop":
                for p in group["params"]:
                    # Match AdamW: an unused expert receives no update and its moments stay unchanged.
                    self._update_one(p, group, self.state[p])
                continue

            # Same-shaped matrices share one batched NS chain. Group by device and dtype as
            # well as shape so the stack operation is always valid for general callers.
            by_shape = {}
            for p in group["params"]:
                if p.grad is not None:
                    key = (tuple(p.shape), p.device, p.dtype)
                    by_shape.setdefault(key, []).append(p)
            for params in by_shape.values():
                self._update_batched(params, group)


class MuonAdamW(torch.optim.Optimizer):
    """Single-process Polar Express Muon + AdamW, ported from
    https://github.com/karpathy/nanochat/blob/master/nanochat/optim.py (MIT, Copyright 2025 Andrej Karpathy).
    Plain PyTorch ops; the collectives, sharded state and fused kernels are not ported."""

    def __init__(self, param_groups):
        super().__init__(param_groups, defaults={})

    @staticmethod
    def _adamw_step(p, grad, state, group):
        if not state:
            state["step"] = 0
            state["exp_avg"] = torch.zeros_like(p, dtype=torch.float32)
            state["exp_avg_sq"] = torch.zeros_like(p, dtype=torch.float32)
        state["step"] += 1
        step = state["step"]
        p32, grad32 = p.float(), grad.float()
        exp_avg, exp_avg_sq = state["exp_avg"], state["exp_avg_sq"]
        beta1, beta2 = group["betas"]
        p32.mul_(1 - group["lr"] * group["weight_decay"])          # decoupled weight decay
        exp_avg.lerp_(grad32, 1 - beta1)
        exp_avg_sq.lerp_(grad32.square(), 1 - beta2)
        denom = (exp_avg_sq / (1 - beta2 ** step)).sqrt().add_(group["eps"])
        p32.addcdiv_(exp_avg / (1 - beta1 ** step), denom, value=-group["lr"])
        p.copy_(p32)

    @staticmethod
    def _muon_step(p, grad, state, group):
        if not state:
            state["momentum_buffer"] = torch.zeros_like(p)
            rows, cols = p.shape
            state_shape = (rows, 1) if rows >= cols else (1, cols)
            state["second_momentum_buffer"] = torch.zeros(state_shape, device=p.device, dtype=p.dtype)
        momentum = group["momentum"]
        momentum_buffer = state["momentum_buffer"]
        momentum_buffer.lerp_(grad, 1 - momentum)
        g = grad.lerp(momentum_buffer, momentum)

        # Row equilibration: every row to the same norm, then the whole matrix just below norm 1.
        x = g.to(torch.bfloat16 if p.is_cuda and _native_bf16() else torch.float32)
        rows, cols = x.shape
        target = x.float().norm() / (rows ** 0.5)
        row_norm = x.float().norm(dim=-1, keepdim=True).clamp_min(1e-6)
        x = x * (target / row_norm).to(x.dtype)
        x = x / (x.norm() * 1.01 + 1e-6)
        red_dim = -1 if rows >= cols else -2
        if rows > cols:                      # Polar Express iterations on the smaller Gram matrix
            for a, b, c in POLAR_EXPRESS_COEFFS[:group["ns_steps"]]:
                gram = x.T @ x
                x = a * x + x @ (b * gram + c * (gram @ gram))
        else:
            for a, b, c in POLAR_EXPRESS_COEFFS[:group["ns_steps"]]:
                gram = x @ x.T
                x = a * x + (b * gram + c * (gram @ gram)) @ x

        g = x.to(p.dtype)
        target_norm = min(rows, cols) ** 0.5        # norm correction: the norm of an orthogonal matrix
        g = g * (target_norm / g.float().norm().clamp_min(1e-6)).to(g.dtype)
        # Factored variance reduction: an EMA of the per-row (or per-column) mean square, then keep g's norm.
        v_mean = g.float().square().mean(dim=red_dim, keepdim=True)
        second = state["second_momentum_buffer"]
        second.lerp_(v_mean.to(second.dtype), 1 - group["beta2"])
        step_size = second.clamp_min(1e-10).rsqrt()
        reduction_size = g.size(red_dim)
        v_norm = (v_mean.sum() * reduction_size).sqrt()
        v_norm_new = ((v_mean * reduction_size) * step_size.float().square()).sum().sqrt()
        g = g * (step_size * (v_norm / v_norm_new.clamp_min(1e-10))).to(g.dtype)

        lr = group["lr"] * max(1.0, rows / cols) ** 0.5
        wd = group["weight_decay"]
        mask = (g * p) >= 0                  # cautious decay: only where the update and the weight agree in sign
        p.sub_(lr * g + lr * wd * p * mask)

    @staticmethod
    def _muon_step_batched(params, states, group):
        """_muon_step on same-shaped matrices at once: one chain of launches per shape instead of per matrix.
        The state stays per parameter (same keys as the loop, so checkpoints work with either impl).
        Fewer launches than the loop (the step is host-bound): each Polar Express iteration is one Gram matmul and
        two baddbmm (scale and add inside the matmul), one fp32 copy feeds both input norms, and the cautious weight
        decay terms are skipped when weight_decay is 0. Same math; rounding differs slightly from the loop."""
        rows, cols = params[0].shape
        for p, state in zip(params, states):
            if not state:
                state["momentum_buffer"] = torch.zeros_like(p)
                state_shape = (rows, 1) if rows >= cols else (1, cols)
                state["second_momentum_buffer"] = torch.zeros(state_shape, device=p.device, dtype=p.dtype)
        momentum = group["momentum"]
        grads = [p.grad for p in params]
        momentum_buffers = [s["momentum_buffer"] for s in states]
        torch._foreach_lerp_(momentum_buffers, grads, 1 - momentum)
        g = torch.stack(torch._foreach_lerp(grads, momentum_buffers, momentum))      # [n, rows, cols]

        # The same steps as _muon_step, on [n, rows, cols].
        x = g.to(torch.bfloat16 if g.is_cuda and _native_bf16() else torch.float32)
        xf = x.float()
        target = torch.linalg.vector_norm(xf, dim=(1, 2), keepdim=True) / (rows ** 0.5)
        row_norm = xf.norm(dim=-1, keepdim=True).clamp_min(1e-6)
        x = x * (target / row_norm).to(x.dtype)
        x = x / (torch.linalg.vector_norm(x, dim=(1, 2), keepdim=True) * 1.01 + 1e-6)
        red_dim = -1 if rows >= cols else -2
        # b * gram + c * gram @ gram, then a * x + (x @ that or that @ x): two baddbmm instead of seven launches
        if rows > cols:
            for a, b, c in POLAR_EXPRESS_COEFFS[:group["ns_steps"]]:
                gram = x.mT @ x
                x = torch.baddbmm(x, x, torch.baddbmm(gram, gram, gram, beta=b, alpha=c), beta=a)
        else:
            for a, b, c in POLAR_EXPRESS_COEFFS[:group["ns_steps"]]:
                gram = x @ x.mT
                x = torch.baddbmm(x, torch.baddbmm(gram, gram, gram, beta=b, alpha=c), x, beta=a)

        g = x.to(params[0].dtype)
        target_norm = min(rows, cols) ** 0.5
        g_norm = torch.linalg.vector_norm(g.float(), dim=(1, 2), keepdim=True).clamp_min(1e-6)
        g = g * (target_norm / g_norm).to(g.dtype)
        v_mean = g.float().square().mean(dim=red_dim, keepdim=True)
        seconds = [s["second_momentum_buffer"] for s in states]
        second = torch.stack(seconds)
        second.lerp_(v_mean.to(second.dtype), 1 - group["beta2"])
        torch._foreach_copy_(seconds, list(second.unbind(0)))
        step_size = second.clamp_min(1e-10).rsqrt()
        reduction_size = g.size(red_dim)
        v_norm = (v_mean.sum(dim=(1, 2), keepdim=True) * reduction_size).sqrt()
        v_norm_new = ((v_mean * reduction_size) * step_size.float().square()).sum(dim=(1, 2), keepdim=True).sqrt()
        g = g * (step_size * (v_norm / v_norm_new.clamp_min(1e-10))).to(g.dtype)

        lr = group["lr"] * max(1.0, rows / cols) ** 0.5
        wd = group["weight_decay"]
        if wd:
            p = torch.stack(params)
            mask = (g * p) >= 0
            g = g + wd * p * mask
        torch._foreach_add_(params, list(g.unbind(0)), alpha=-lr)

    @staticmethod
    def _adamw_step_foreach(params, states, group):
        """_adamw_step on fp32 parameters with the same step count, as torch._foreach ops (one launch per op)."""
        for p, state in zip(params, states):
            if not state:
                state["step"] = 0
                state["exp_avg"] = torch.zeros_like(p, dtype=torch.float32)
                state["exp_avg_sq"] = torch.zeros_like(p, dtype=torch.float32)
            state["step"] += 1
        step = states[0]["step"]
        grads = [p.grad.float() for p in params]
        exp_avgs = [s["exp_avg"] for s in states]
        exp_avg_sqs = [s["exp_avg_sq"] for s in states]
        beta1, beta2 = group["betas"]
        torch._foreach_mul_(params, 1 - group["lr"] * group["weight_decay"])
        torch._foreach_lerp_(exp_avgs, grads, 1 - beta1)
        torch._foreach_lerp_(exp_avg_sqs, torch._foreach_mul(grads, grads), 1 - beta2)
        denom = torch._foreach_div(exp_avg_sqs, 1 - beta2 ** step)
        torch._foreach_sqrt_(denom)
        torch._foreach_add_(denom, group["eps"])
        torch._foreach_addcdiv_(params, torch._foreach_div(exp_avgs, 1 - beta1 ** step), denom, value=-group["lr"])

    @staticmethod
    def _buckets(params, states, key):
        """Parameters with a gradient, grouped so each bucket can be stacked or passed to one _foreach op."""
        buckets = {}
        for p in params:
            if p.grad is not None:
                buckets.setdefault(key(p, states[p]), []).append(p)
        return buckets.values()

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()
        for group in self.param_groups:
            kind = group["kind"]
            region_name = "opt.muon" if kind == "muon" else "opt.adamw"
            with region(region_name, 2):
                impl = group.get("impl", "loop")
                if kind == "muon" and impl == "batched":
                    for ps in self._buckets(group["params"], self.state,
                                            lambda p, s: (tuple(p.shape), p.device, p.dtype)):
                        with region("opt.muon.ns", 3):
                            self._muon_step_batched(ps, [self.state[p] for p in ps], group)
                    continue
                if kind == "adamw" and impl == "foreach":
                    # fp32 parameters with the same step count share one set of _foreach launches; others loop
                    for ps in self._buckets(group["params"], self.state,
                                            lambda p, s: (p.device, p.dtype, s.get("step", 0))):
                        if ps[0].dtype == torch.float32:
                            self._adamw_step_foreach(ps, [self.state[p] for p in ps], group)
                        else:
                            for p in ps:
                                self._adamw_step(p, p.grad, self.state[p], group)
                    continue
                for p in group["params"]:
                    if p.grad is None:
                        continue
                    if kind == "muon":
                        with region("opt.muon.ns", 3):
                            self._muon_step(p, p.grad, self.state[p], group)
                    elif kind == "adamw":
                        self._adamw_step(p, p.grad, self.state[p], group)
                    else:
                        raise ValueError(f"unknown MuonAdamW optimizer group kind {kind!r}")
        return loss


class Optimizers:
    """One or two torch optimizers behind one zero_grad() / step(), with timed regions."""

    def __init__(self, named: list):
        self.named = named          # [(region name, torch optimizer)]
        names = [name for name, _ in named]
        if len(names) != len(set(names)):
            raise ValueError("optimizer region names must be unique")
        for _, optimizer in named:
            for group in optimizer.param_groups:
                group.setdefault("initial_lr", group["lr"])

    def state_dict(self):
        """Return checkpoint state for every optimizer managed by this wrapper."""
        return {name: optimizer.state_dict() for name, optimizer in self.named}

    def load_state_dict(self, state_dict):
        """Restore optimizer states, requiring the same named optimizer set."""
        expected = {name for name, _ in self.named}
        received = set(state_dict)
        if received != expected:
            raise ValueError(f"optimizer state names differ: expected {sorted(expected)}, got {sorted(received)}")
        for name, optimizer in self.named:
            optimizer.load_state_dict(state_dict[name])

    def set_lr(self, step: int, total_steps: int, schedule="constant", warmup_steps=0,
               min_lr_ratio=0.1):
        """Set each group's LR from its base LR: cosine (linear warmup from zero, decay to min_lr_ratio) or constant."""
        if schedule not in ("constant", "cosine"):
            raise ValueError(f"optim.schedule={schedule!r}: constant | cosine")
        if total_steps <= 0 or warmup_steps < 0 or warmup_steps >= total_steps:
            raise ValueError("Require total_steps > warmup_steps >= 0")
        if not 0.0 <= min_lr_ratio <= 1.0:
            raise ValueError("min_lr_ratio must be in [0, 1]")
        if step < 0 or step >= total_steps:
            raise ValueError("step must be in [0, total_steps)")
        warmup = (step + 1) / warmup_steps if warmup_steps and step < warmup_steps else 1.0
        if schedule == "cosine" and step >= warmup_steps:
            progress = (step - warmup_steps) / max(1, total_steps - warmup_steps - 1)
            decay = min_lr_ratio + (1 - min_lr_ratio) * 0.5 * (1 + math.cos(progress * math.pi))
        else:
            decay = 1.0
        multiplier = warmup * decay
        for _, optimizer in self.named:
            for group in optimizer.param_groups:
                group["lr"] = group["initial_lr"] * multiplier

    def zero_grad(self):
        with region("opt.zero_grad", 3):
            for _, o in self.named:
                o.zero_grad(set_to_none=True)

    def step(self, scaler=None):
        for name, o in self.named:
            with region(name, 2):
                scaler.step(o) if scaler is not None else o.step()

    def unscale(self, scaler):
        for _, o in self.named:
            scaler.unscale_(o)

    def flops(self):
        """Newton-Schulz FLOPs per step (Muon is not free; counted in HFU, not in MFU)."""
        total = 0
        for _, o in self.named:
            if isinstance(o, (Muon, MuonAdamW)):
                for g in o.param_groups:
                    if isinstance(o, MuonAdamW) and g["kind"] != "muon":
                        continue
                    for p in g["params"]:
                        m, n = sorted(p.shape[:2])
                        steps = g.get("ns_steps", 5)
                        total += steps * (4 * m * m * n + 2 * m ** 3)
        return total


def build_optimizer(model, ocfg: dict):
    """Optimizers for cfg["optim"]: 2D block weights to Muon, the rest to AdamW (everything to AdamW for adamw)."""
    named_params = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
    params = [p for _, p in named_params]
    fused = params[0].is_cuda

    def adamw(named):
        decay, no_decay = [], []
        for name, p in named:                # no decay for biases, norm gains and other 1D parameters
            (decay if p.ndim >= 2 and not name.endswith(".bias") else no_decay).append(p)
        groups = []
        if decay:
            groups.append({"params": decay, "weight_decay": ocfg["weight_decay"]})
        if no_decay:
            groups.append({"params": no_decay, "weight_decay": 0.0})
        return torch.optim.AdamW(groups, lr=ocfg["lr"], betas=(0.9, 0.95), fused=fused)

    if ocfg["name"] == "adamw":
        return Optimizers([("opt.adamw", adamw(named_params))])
    if ocfg["name"] == "polar_muon_adamw":
        if ocfg.get("muon_impl", "loop") not in ("loop", "batched"):
            raise ValueError(f"optim.muon_impl={ocfg['muon_impl']!r}: loop | batched")
        adamw_impl = ocfg.get("adamw_impl", "loop")
        if adamw_impl not in ("loop", "foreach"):
            raise ValueError(f"optim.adamw_impl={adamw_impl!r}: loop | foreach")
        # 2D block weights go to Muon; embeddings, head, norms and biases to AdamW
        muon_params = [p for n, p in named_params
                       if p.dim() == 2 and n.startswith("blocks.") and n.endswith(".weight")]
        muon_ids = {id(p) for p in muon_params}
        adamw_params = [(n, p) for n, p in named_params if id(p) not in muon_ids]
        groups = []
        if muon_params:
            groups.append({
                "params": muon_params, "kind": "muon", "lr": ocfg["muon_lr"],
                "momentum": 0.95, "beta2": 0.95, "ns_steps": 5,
                "weight_decay": ocfg["weight_decay"], "impl": ocfg.get("muon_impl", "loop"),
            })
        decay, no_decay = [], []
        for name, p in adamw_params:
            (decay if p.ndim >= 2 and not name.endswith(".bias") else no_decay).append(p)
        if decay:
            groups.append({"params": decay, "kind": "adamw", "lr": ocfg["lr"],
                           "betas": (0.9, 0.95), "eps": 1e-8,
                           "weight_decay": ocfg["weight_decay"], "impl": adamw_impl})
        if no_decay:
            groups.append({"params": no_decay, "kind": "adamw", "lr": ocfg["lr"],
                           "betas": (0.9, 0.95), "eps": 1e-8, "weight_decay": 0.0, "impl": adamw_impl})
        return Optimizers([("opt.polar_muon_adamw", MuonAdamW(groups))])
    if ocfg["name"] == "muon":
        if "muon_params" in ocfg and ocfg["muon_params"] != "hidden":
            raise ValueError("Remove optim.muon_params: embeddings and head must use AdamW")

        def use_muon(name, p):
            return p.dim() == 2 and name.startswith("blocks.") and name.endswith(".weight")
        two_d = [p for n, p in named_params if use_muon(n, p)]
        rest = [(n, p) for n, p in named_params if not use_muon(n, p)]
        named = []
        if two_d:
            named.append(("opt.muon", Muon(two_d, lr=ocfg["muon_lr"], weight_decay=ocfg["weight_decay"],
                                            impl=ocfg.get("muon_impl", "loop"))))
        if rest:
            named.append(("opt.adamw", adamw(rest)))
        return Optimizers(named)
    raise ValueError(f"optim.name={ocfg['name']!r}: adamw | muon | polar_muon_adamw")
