"""Optimizer parameter assignment, numerical updates, state restore, and scaler checks."""
import copy
import os
import pytest
import torch
from torch import nn

from correctness.framework import PAIRS, Case, check, pair, pairs_in
from dataio.loader import Loader
from dataio.tokenizer import BrahmicTokenizer
from models.config import ModelConfig
from models.gpt import GPT
from models.ke1 import KroneckerEmbedding
from models.optim import (Muon, MuonAdamW, Optimizers, build_optimizer,
                          zeropower_via_newtonschulz5, zeropower_via_newtonschulz5_batched)



@pytest.mark.parametrize("embedding", ["table", "ke1"])
@pytest.mark.parametrize("muon_impl", ["loop", "batched"])
def test_optimizer_ownership_and_norm_gains(embedding, muon_impl):
    # Small vocabulary here is a unit fixture, never a performance configuration.
    cfg = ModelConfig(vocab_size=16, block_size=4, n_layer=1, n_head=2, n_embd=8,
                      embedding=embedding, ffn="moe",
                      moe=dict(num_experts=2, top_k=1, num_shared=1))
    from models.ke1 import token_bytes_random
    model = GPT(cfg, token_bytes_random(16) if embedding == "ke1" else None)
    opt = build_optimizer(model, dict(name="muon", muon_impl=muon_impl,
                                      lr=0.001, muon_lr=0.02, weight_decay=0.01))
    optimizers = dict(opt.named)
    assert isinstance(optimizers["opt.muon"], Muon)
    assert optimizers["opt.muon"].param_groups[0]["impl"] == muon_impl
    assert isinstance(optimizers["opt.adamw"], torch.optim.AdamW)
    assert optimizers["opt.adamw"].defaults["betas"] == (0.9, 0.95)
    assert optimizers["opt.adamw"].defaults["fused"] == next(model.parameters()).is_cuda
    groups = {name: {id(p) for g in o.param_groups for p in g["params"]} for name, o in opt.named}
    muon, adamw = groups["opt.muon"], groups["opt.adamw"]
    assert not muon & adamw
    assert muon | adamw == {id(p) for p in model.parameters() if p.requires_grad}
    for name, p in model.named_parameters():
        expected = muon if name.startswith("blocks.") and p.ndim == 2 else adamw
        assert id(p) in expected, name
    assert id(model.head.weight) in adamw
    norms = [m for m in model.modules() if isinstance(m, torch.nn.LayerNorm)]
    assert norms and all(m.weight.requires_grad and id(m.weight) in adamw for m in norms)
    adamw_optimizer = optimizers["opt.adamw"]
    assert all(group["weight_decay"] == 0.0 for group in adamw_optimizer.param_groups
               if any(p.ndim < 2 for p in group["params"]))
    assert all(all(p.ndim < 2 for p in group["params"])
               for group in adamw_optimizer.param_groups if group["weight_decay"] == 0.0)
    model(torch.tensor([[1, 2, 3, 4]]), torch.tensor([[2, 3, 4, 5]]))[1].backward()
    assert all(m.weight.grad is not None for m in norms)
    opt.step()
    assert all(torch.isfinite(p).all() for p in model.parameters())


def test_pure_adamw_owns_every_parameter_and_uses_expected_settings():
    cfg = ModelConfig(vocab_size=16, block_size=4, n_layer=1, n_head=2, n_embd=8)
    model = GPT(cfg)
    opt = build_optimizer(model, dict(name="adamw", lr=0.001, weight_decay=0.1))
    assert len(opt.named) == 1
    name, adamw = opt.named[0]
    assert name == "opt.adamw"
    assert isinstance(adamw, torch.optim.AdamW)
    assert adamw.defaults["betas"] == (0.9, 0.95)
    assert adamw.defaults["fused"] == next(model.parameters()).is_cuda
    assigned = {id(p) for group in adamw.param_groups for p in group["params"]}
    assert assigned == {id(p) for p in model.parameters() if p.requires_grad}
    for group in adamw.param_groups:
        has_bias_or_gain = any(p.ndim < 2 for p in group["params"])
        assert group["weight_decay"] == (0.0 if has_bias_or_gain else 0.1)


def test_muon_update_and_missing_gradient_skip():
    p = torch.nn.Parameter(torch.tensor([[2.0]]))
    opt = Muon([p], lr=0.1, momentum=0.9, ns_steps=0, weight_decay=0.1)
    p.grad = torch.tensor([[3.0]])
    opt.step()
    # NS with zero iterations returns the normalized positive scalar update (+1).
    assert torch.allclose(p, torch.tensor([[1.88]]), atol=1e-6)
    old_param = p.detach().clone()
    old_momentum = opt.state[p]["buf"].clone()
    p.grad = None
    opt.step()
    assert torch.equal(p, old_param)
    assert torch.equal(opt.state[p]["buf"], old_momentum)

    adamw_p = torch.nn.Parameter(torch.tensor([[2.0]]))
    adamw = torch.optim.AdamW([adamw_p], lr=0.1, weight_decay=0.1)
    adamw_p.grad = torch.ones_like(adamw_p)
    adamw.step()
    after_used_step = adamw_p.detach().clone()
    adamw_p.grad = None
    adamw.step()
    assert torch.equal(adamw_p, after_used_step)


def _reference_muon_step(param, grad, momentum_buffer, lr, momentum, weight_decay, ns_steps=5):
    """Independent small-tensor Muon calculation, including the production bf16 NS path on CPU."""
    if momentum_buffer is None:
        momentum_buffer = torch.zeros_like(grad)
    momentum_buffer = momentum_buffer.clone().lerp(grad, 1 - momentum)
    nesterov_grad = grad.lerp(momentum_buffer, momentum)

    # Match only the documented compute precision; implement the NS iteration here rather than
    # calling zeropower_via_newtonschulz5 so this can detect mistakes in that implementation.
    x = nesterov_grad.to(torch.bfloat16)
    transposed = x.shape[0] > x.shape[1]
    if transposed:
        x = x.T
    x = x / (x.norm() + 1e-7)
    a, b, c = 3.4445, -4.7750, 2.0315
    for _ in range(ns_steps):
        gram = x @ x.T
        x = a * x + (b * gram + c * (gram @ gram)) @ x
    if transposed:
        x = x.T

    scale = max(1.0, param.shape[0] / param.shape[1]) ** 0.5
    expected = param * (1 - lr * weight_decay)
    expected = expected - x.to(param.dtype) * (lr * scale)
    return expected, momentum_buffer


@pytest.mark.parametrize("shape", [(2, 3), (3, 2)])
def test_muon_five_step_update_matches_independent_reference(shape):
    lr, momentum, weight_decay = 0.03, 0.8, 0.04
    initial = torch.arange(1, shape[0] * shape[1] + 1, dtype=torch.float32).reshape(shape) / 3
    param = torch.nn.Parameter(initial.clone())
    opt = Muon([param], lr=lr, momentum=momentum, ns_steps=5, weight_decay=weight_decay)
    expected = initial.clone()
    ref_buffer = None

    for step in range(3):
        grad = torch.arange(1, param.numel() + 1, dtype=param.dtype).reshape(shape)
        grad = grad * (0.07 * (step + 1)) - 0.2
        expected, ref_buffer = _reference_muon_step(
            expected, grad, ref_buffer, lr, momentum, weight_decay, ns_steps=5)
        param.grad = grad.clone()
        opt.step()
        torch.testing.assert_close(param, expected, rtol=0, atol=1e-6)
        torch.testing.assert_close(opt.state[param]["buf"], ref_buffer, rtol=0, atol=1e-7)


@pytest.mark.parametrize("shape", [(4, 3), (3, 4), (3, 3)])
def test_batched_newton_schulz_matches_per_matrix_reference(shape):
    batch = torch.linspace(-0.8, 1.1, 5 * shape[0] * shape[1]).reshape(5, *shape)
    expected = torch.stack([zeropower_via_newtonschulz5(g, steps=5) for g in batch])
    actual = zeropower_via_newtonschulz5_batched(batch, steps=5)
    assert actual.shape == batch.shape
    torch.testing.assert_close(actual, expected, rtol=2e-3, atol=2e-3)


def test_optimizer_flops_counts_newton_schulz_for_muon_matrices_only():
    wide = torch.nn.Parameter(torch.zeros(2, 3))
    tall = torch.nn.Parameter(torch.zeros(3, 2))
    adamw_param = torch.nn.Parameter(torch.zeros(5, 5))
    combined_adamw_param = torch.nn.Parameter(torch.zeros(7, 7))
    optimizers = Optimizers([
        ("opt.muon", Muon([wide, tall], ns_steps=3)),
        ("opt.adamw", torch.optim.AdamW([adamw_param])),
        ("opt.polar_muon_adamw", MuonAdamW([
            {"params": [combined_adamw_param], "kind": "adamw", "lr": 0.001},
            {"params": [torch.nn.Parameter(torch.zeros(2, 3))], "kind": "muon", "lr": 0.001,
             "ns_steps": 2},
        ])),
    ])
    # Each 2x3 / 3x2 NS step is 4*m^2*n + 2*m^3 = 64 FLOPs.
    assert optimizers.flops() == 3 * 64 * 2 + 2 * 64


@pytest.mark.parametrize("shape", [(4, 3), (3, 4)])
def test_batched_muon_matches_loop_with_momentum_decay_and_missing_grad(shape):
    torch.manual_seed(41)
    initial = [torch.randn(shape), torch.randn(shape), torch.randn(shape)]
    loop_params = [torch.nn.Parameter(p.clone()) for p in initial]
    batch_params = [torch.nn.Parameter(p.clone()) for p in initial]
    kwargs = dict(lr=0.025, momentum=0.8, ns_steps=5, weight_decay=0.03)
    loop = Muon(loop_params, impl="loop", **kwargs)
    batched = Muon(batch_params, impl="batched", **kwargs)

    for step in range(3):
        for i, (lp, bp) in enumerate(zip(loop_params, batch_params)):
            if step == 1 and i == 1:
                lp.grad = bp.grad = None
                continue
            grad = torch.linspace(-0.3, 0.4, lp.numel()).reshape_as(lp) * (step + i + 1)
            lp.grad, bp.grad = grad.clone(), grad.clone()
        loop.step()
        batched.step()
        for lp, bp in zip(loop_params, batch_params):
            torch.testing.assert_close(bp, lp, rtol=2e-3, atol=2e-3)
            if "buf" in loop.state.get(lp, {}):
                torch.testing.assert_close(batched.state[bp]["buf"], loop.state[lp]["buf"], rtol=0, atol=0)


@pytest.mark.skipif(
    not torch.cuda.is_available() or not torch.cuda.is_bf16_supported(),
    reason="CUDA bf16 comparison is intended for the GPU correctness job",
)
@pytest.mark.parametrize("shape", [(4, 3), (3, 4), (4, 4)])
def test_batched_muon_matches_loop_on_cuda_bf16(shape):
    # Batched GEMMs change bf16 accumulation order. Keep this device-specific tolerance
    # explicit and report measured errors if the GPU correctness job exceeds it.
    torch.manual_seed(41)
    loop_p = torch.nn.Parameter(torch.randn(shape, device="cuda", dtype=torch.bfloat16))
    batch_p = torch.nn.Parameter(loop_p.detach().clone())
    kwargs = dict(lr=0.01, momentum=0.8, ns_steps=5, weight_decay=0.01)
    loop = Muon([loop_p], impl="loop", **kwargs)
    batched = Muon([batch_p], impl="batched", **kwargs)
    for step in range(2):
        grad = torch.randn(shape, device="cuda", dtype=torch.bfloat16) * (step + 1)
        loop_p.grad = grad.clone()
        batch_p.grad = grad.clone()
        loop.step()
        batched.step()
    max_abs_error = (batch_p.float() - loop_p.float()).abs().max().item()
    torch.testing.assert_close(
        batch_p, loop_p, rtol=0.04, atol=0.02,
        msg=f"CUDA bf16 Muon loop/batched exceeded tolerance; max_abs_error={max_abs_error:.6g}",
    )


def test_build_optimizer_selects_batched_muon_from_config():
    cfg = ModelConfig(vocab_size=16, block_size=4, n_layer=1, n_head=2, n_embd=8)
    model = GPT(cfg)
    opt = build_optimizer(model, dict(name="muon", muon_impl="batched", lr=0.001,
                                      muon_lr=0.02, weight_decay=0.0))
    assert dict(opt.named)["opt.muon"].param_groups[0]["impl"] == "batched"


def test_pure_adamw_two_steps_match_independent_reference():
    class TinyParams(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.matrix = torch.nn.Parameter(torch.tensor([[1.5, -0.75], [0.25, 2.0]]))
            self.bias = torch.nn.Parameter(torch.tensor([0.5, -1.0]))

    model = TinyParams()
    opt = build_optimizer(model, dict(name="adamw", lr=0.02, weight_decay=0.1))
    adamw = dict(opt.named)["opt.adamw"]
    params = {"matrix": model.matrix, "bias": model.bias}
    expected = {name: p.detach().clone() for name, p in params.items()}
    moments = {name: (torch.zeros_like(p), torch.zeros_like(p)) for name, p in params.items()}
    decay = {"matrix": 0.1, "bias": 0.0}
    beta1, beta2, eps, lr = 0.9, 0.95, adamw.defaults["eps"], 0.02

    for step in range(1, 3):
        grads = {
            "matrix": torch.tensor([[0.2, -0.1], [0.3, 0.4]]) * step,
            "bias": torch.tensor([-0.25, 0.15]) * step,
        }
        for name, param in params.items():
            param.grad = grads[name].clone()
            m, v = moments[name]
            m.mul_(beta1).add_(grads[name], alpha=1 - beta1)
            v.mul_(beta2).addcmul_(grads[name], grads[name], value=1 - beta2)
            m_hat = m / (1 - beta1 ** step)
            v_hat = v / (1 - beta2 ** step)
            expected[name].mul_(1 - lr * decay[name])
            expected[name].addcdiv_(m_hat, v_hat.sqrt().add(eps), value=-lr)
        opt.step()
        for name, param in params.items():
            torch.testing.assert_close(param, expected[name], rtol=1e-6, atol=1e-7)


def _reference_polar_muon_step(param, grad, momentum_buffer, second_buffer, lr, weight_decay):
    """Small CPU reference for Polar Express Muon; does not call production helpers."""
    momentum = 0.95
    if momentum_buffer is None:
        momentum_buffer = torch.zeros_like(grad)
        rows, cols = param.shape
        second_buffer = torch.zeros((rows, 1) if rows >= cols else (1, cols))
    momentum_buffer = momentum_buffer.clone().lerp(grad, 1 - momentum)
    x = grad.lerp(momentum_buffer, momentum).float()
    rows, cols = x.shape
    target = x.norm() / rows ** 0.5
    x = x * (target / x.norm(dim=-1, keepdim=True).clamp_min(1e-6))
    x = x / (x.norm() * 1.01 + 1e-6)
    coeffs = (
        (8.156554524902461, -22.48329292557795, 15.878769915207462),
        (4.042929935166739, -2.808917465908714, 0.5000178451051316),
        (3.8916678022926607, -2.772484153217685, 0.5060648178503393),
        (3.285753657755655, -2.3681294933425376, 0.46449024233003106),
        (2.3465413258596377, -1.7097828382687081, 0.42323551169305323),
    )
    if rows > cols:
        for a, b, c in coeffs:
            gram = x.T @ x
            x = a * x + x @ (b * gram + c * (gram @ gram))
    else:
        for a, b, c in coeffs:
            gram = x @ x.T
            x = a * x + (b * gram + c * (gram @ gram)) @ x
    x = x * (min(rows, cols) ** 0.5 / x.norm().clamp_min(1e-6))
    red_dim = -1 if rows >= cols else -2
    variance = x.square().mean(dim=red_dim, keepdim=True)
    second_buffer = second_buffer.clone().lerp(variance, 1 - 0.95)
    step_size = second_buffer.clamp_min(1e-10).rsqrt()
    reduction_size = x.size(red_dim)
    norm_before = (variance.sum() * reduction_size).sqrt()
    norm_after = ((variance * reduction_size) * step_size.square()).sum().sqrt()
    x = x * step_size * (norm_before / norm_after.clamp_min(1e-10))
    lr *= max(1.0, rows / cols) ** 0.5
    expected = param - lr * x - lr * weight_decay * param * (x * param >= 0)
    return expected, momentum_buffer, second_buffer


def test_polar_muon_adamw_is_one_optimizer_and_matches_reference():
    class TinyBlock(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.linear = torch.nn.Linear(3, 2)

    class TinyModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = torch.nn.Embedding(4, 3)
            self.blocks = torch.nn.ModuleList([TinyBlock()])
            self.norm = torch.nn.LayerNorm(2)
            self.head = torch.nn.Linear(2, 4, bias=False)

    model = TinyModel()
    lr, muon_lr, weight_decay = 0.01, 0.02, 0.03
    opt = build_optimizer(model, dict(name="polar_muon_adamw", lr=lr, muon_lr=muon_lr,
                                      weight_decay=weight_decay))
    assert len(opt.named) == 1
    name, combined = opt.named[0]
    assert name == "opt.polar_muon_adamw"
    assert isinstance(combined, MuonAdamW)
    muon_group = next(group for group in combined.param_groups if group["kind"] == "muon")
    muon_ids = {id(p) for p in muon_group["params"]}
    expected_muon = {id(model.blocks[0].linear.weight)}
    assert muon_ids == expected_muon
    assert id(model.embedding.weight) not in muon_ids
    assert id(model.head.weight) not in muon_ids
    assert id(model.norm.weight) not in muon_ids

    torch.manual_seed(31)
    refs = {}
    ref_momentum = ref_second = None
    for i, param in enumerate(model.parameters()):
        grad = torch.linspace(-0.2, 0.3, param.numel()).reshape_as(param) + i * 0.01
        param.grad = grad.clone()
        if id(param) in muon_ids:
            refs[id(param)], ref_momentum, ref_second = _reference_polar_muon_step(
                param.detach().clone(), grad, ref_momentum, ref_second,
                muon_lr, weight_decay)
        else:
            decay = weight_decay if param.ndim >= 2 else 0.0
            ref_param = torch.nn.Parameter(param.detach().clone())
            ref_opt = torch.optim.AdamW([ref_param], lr=lr, betas=(0.9, 0.95),
                                        weight_decay=decay, foreach=False, fused=False)
            ref_param.grad = grad.clone()
            ref_opt.step()
            refs[id(param)] = ref_param.detach().clone()

    opt.step()
    for param in model.parameters():
        torch.testing.assert_close(param, refs[id(param)], rtol=2e-5, atol=2e-6)


@pytest.mark.parametrize("shape", [(2, 3), (3, 2)])
def test_polar_muon_rectangular_scaling_matches_reference(shape):
    p = torch.nn.Parameter(torch.arange(1, shape[0] * shape[1] + 1, dtype=torch.float32).reshape(shape) / 5)
    grad = torch.linspace(-0.3, 0.4, p.numel()).reshape(shape)
    lr, weight_decay = 0.015, 0.02
    expected, _, _ = _reference_polar_muon_step(
        p.detach().clone(), grad, None, None, lr, weight_decay)
    opt = MuonAdamW([{
        "params": [p], "kind": "muon", "lr": lr, "momentum": 0.95,
        "beta2": 0.95, "ns_steps": 5, "weight_decay": weight_decay,
    }])
    p.grad = grad.clone()
    opt.step()
    torch.testing.assert_close(p, expected, rtol=2e-5, atol=2e-6)


def test_hybrid_optimizer_state_dict_resumes_identically():
    cfg = ModelConfig(vocab_size=16, block_size=4, n_layer=1, n_head=2, n_embd=8,
                      ffn="moe", moe=dict(num_experts=2, top_k=1, num_shared=1))
    model = GPT(cfg)
    optim = build_optimizer(model, dict(name="muon", lr=0.001, muon_lr=0.02, weight_decay=0.01))

    def set_grads(module, multiplier):
        for i, param in enumerate(module.parameters()):
            param.grad = torch.full_like(param, multiplier * (i + 1) / 100)

    set_grads(model, 1.0)
    optim.step()
    saved_optimizer_state = copy.deepcopy(optim.state_dict())
    resumed_model = GPT(cfg)
    resumed_model.load_state_dict(model.state_dict())
    resumed_optim = build_optimizer(
        resumed_model, dict(name="muon", lr=0.001, muon_lr=0.02, weight_decay=0.01))
    resumed_optim.load_state_dict(saved_optimizer_state)

    set_grads(model, 2.0)
    set_grads(resumed_model, 2.0)
    optim.step()
    resumed_optim.step()
    for live, resumed in zip(model.parameters(), resumed_model.parameters()):
        torch.testing.assert_close(resumed, live, rtol=0, atol=1e-7)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="GradScaler overflow behavior requires CUDA")
def test_grad_scaler_skips_both_hybrid_optimizers_on_overflow():
    muon_param = torch.nn.Parameter(torch.tensor([[1.0, 2.0], [3.0, 4.0]], device="cuda"))
    adamw_param = torch.nn.Parameter(torch.tensor([2.0, -1.0], device="cuda"))
    optim = Optimizers([
        ("opt.muon", Muon([muon_param], lr=0.1, weight_decay=0.1)),
        ("opt.adamw", torch.optim.AdamW([adamw_param], lr=0.1, weight_decay=0.1, fused=True)),
    ])
    scaler = torch.amp.GradScaler("cuda", init_scale=8.0)
    before = (muon_param.detach().clone(), adamw_param.detach().clone())
    scaler.scale(muon_param.sum() + adamw_param.sum()).backward()
    muon_param.grad[0, 0] = torch.inf
    adamw_param.grad[0] = torch.inf

    optim.unscale(scaler)
    optim.step(scaler)
    scaler.update()

    torch.testing.assert_close(muon_param, before[0], rtol=0, atol=0)
    torch.testing.assert_close(adamw_param, before[1], rtol=0, atol=0)
    assert scaler.get_scale() < 8.0


def test_cosine_learning_rate_schedule():
    p = torch.nn.Parameter(torch.ones(()))
    optimizers = Optimizers([("opt", torch.optim.SGD([p], lr=0.2))])
    optimizers.set_lr(0, 5, schedule="cosine", warmup_steps=2, min_lr_ratio=0.1)
    assert optimizers.named[0][1].param_groups[0]["lr"] == pytest.approx(0.1)
    optimizers.set_lr(1, 5, schedule="cosine", warmup_steps=2, min_lr_ratio=0.1)
    assert optimizers.named[0][1].param_groups[0]["lr"] == pytest.approx(0.2)
    optimizers.set_lr(4, 5, schedule="cosine", warmup_steps=2, min_lr_ratio=0.1)
    assert optimizers.named[0][1].param_groups[0]["lr"] == pytest.approx(0.02)


# ---- @pair correctness checks (Task 3) -----------------------------------------

@pair("opt.muon.batched", tol=2e-3, grad_tol=5e-5)
def _(device):
    # Keep loop as the reference; batched is fast.  Same 3 params, 3 steps, missing grad
    # on step 1 param 1 — matches the existing non-pair test so we can cross-check.
    torch.manual_seed(42)
    shape = (4, 3)
    initial = [torch.randn(shape), torch.randn(shape), torch.randn(shape)]
    step_grads = [
        [torch.linspace(-0.3, 0.4, shape[0] * shape[1]).reshape(shape) * (s + i + 1)
         for i in range(3)]
        for s in range(3)
    ]
    kwargs = dict(lr=0.025, momentum=0.8, ns_steps=5, weight_decay=0.03)

    def _run(impl, *init):
        # CPU-only: NS uses bf16 internally on CUDA (bmm vs mm accumulation differs
        # ~4% on A100), already covered by test_batched_muon_matches_loop_on_cuda_bf16.
        # This pair tests fp32 math correctness of batched vs loop.
        params = [nn.Parameter(p.float().cpu().clone()) for p in init]
        opt = Muon(params, impl=impl, **kwargs)
        for s in range(3):
            for i, p in enumerate(params):
                p.grad = None if (s == 1 and i == 1) else step_grads[s][i].float().to(p.device).clone()
            opt.step()
        return torch.stack([p.detach() for p in params])

    return Case(
        ref=lambda *inputs: _run("loop", *inputs),
        fast=lambda *inputs: _run("batched", *inputs),
        inputs=initial,
        grads=False,
    )


@pair("opt.adamw.foreach", tol=1e-6, grad_tol=5e-5)
def _(device):
    # Two 2D params share one _foreach bucket (same step count); one 1D param runs alone.
    # Loop is the reference; foreach is fast.
    torch.manual_seed(42)
    initial = [torch.randn(3, 4), torch.randn(2, 3), torch.randn(5)]
    adamw_kw = dict(lr=0.001, betas=(0.9, 0.95), eps=1e-8)

    def _grads(step):
        return [
            torch.linspace(-0.1, 0.1, 12).reshape(3, 4) * (step + 1) * 0.1,
            torch.linspace(0.05, 0.15, 6).reshape(2, 3) * (step + 2) * 0.1,
            torch.ones(5) * (step + 3) * 0.01,
        ]

    def _run(impl, *init):
        params = [nn.Parameter(p.float().clone()) for p in init]
        groups = [
            {"params": [params[0], params[1]], "kind": "adamw", "weight_decay": 0.01,
             "impl": impl, **adamw_kw},
            {"params": [params[2]], "kind": "adamw", "weight_decay": 0.0,
             "impl": impl, **adamw_kw},
        ]
        opt = MuonAdamW(groups)
        for step in range(3):
            for p, g in zip(params, _grads(step)):
                p.grad = g.float().to(p.device).clone()
            opt.step()
        return torch.cat([p.detach().flatten() for p in params])

    return Case(
        ref=lambda *inputs: _run("loop", *inputs),
        fast=lambda *inputs: _run("foreach", *inputs),
        inputs=initial,
        grads=False,
    )


@pair("data.prefetch", tol=0.0, grad_tol=5e-5)
def _(device):
    # prefetch=True pre-samples the next batch while the GPU is busy; both paths must yield
    # identical token IDs because they advance the RNG in the same order.
    batch_size, block_size, n_steps, seed = 2, 8, 4, 17
    tokenizer_path = os.environ.get("BRAHMIC_TOKENIZER_PATH")

    def _run(prefetch, _dummy):
        loader = Loader("synthetic", batch_size, block_size, "cpu", seed=seed,
                        prefetch=prefetch, tokenizer_path=tokenizer_path)
        chunks = []
        for _ in range(n_steps):
            if prefetch:
                loader.prefetch()
            x, y = loader.next_batch()
            chunks.append(x.float())
            chunks.append(y.float())
        return torch.cat([c.flatten() for c in chunks])

    return Case(
        ref=lambda d: _run(False, d),
        fast=lambda d: _run(True, d),
        inputs=[torch.zeros(1)],
        grads=False,
    )


@pytest.mark.parametrize("name", pairs_in(__name__))
def test_pair(name, device):
    errors = check(PAIRS[name], device)
    assert "out[0]" in errors, f"{name}: output must be compared"


# ---- fixtures and integration tests --------------------------------------------

@pytest.fixture(scope="module")
def tokenizer():
    return BrahmicTokenizer(os.environ.get("BRAHMIC_TOKENIZER_PATH"))


class _TinyKeModel(nn.Module):
    def __init__(self, token_bytes):
        super().__init__()
        self.embedding = KroneckerEmbedding(token_bytes, d_model=8)
        self.blocks = nn.ModuleList([nn.Linear(8, 8, bias=False)])
        self.norm = nn.LayerNorm(8)
        self.head = nn.Linear(8, 1)

    def forward(self, token_ids):
        x = self.embedding(token_ids)
        x = torch.tanh(self.blocks[0](x))
        return self.head(self.norm(x))


def test_real_tokenizer_ke_model_takes_optimizer_step(tokenizer):
    token_ids = tokenizer.encode("\u092d\u093e\u0930\u0924 \u090f\u0915 \u0926\u0947\u0936 \u0939\u0948")
    assert token_ids == [66526, 2420, 13092, 732]
    model = _TinyKeModel(tokenizer.token_bytes())
    opt = build_optimizer(model, {
        "name": "muon", "lr": 0.001, "muon_lr": 0.02, "weight_decay": 0.01,
    })
    optimizers = dict(opt.named)
    assert isinstance(optimizers["opt.muon"], Muon)
    assert isinstance(optimizers["opt.adamw"], torch.optim.AdamW)
    ids = torch.tensor([token_ids], dtype=torch.long)
    before = model.embedding.proj.weight.detach().clone()
    loss = model(ids).square().mean()
    loss.backward()
    opt.step()
    assert torch.isfinite(loss)
    assert model.embedding.proj.weight.grad is not None
    assert not torch.equal(model.embedding.proj.weight, before)
    assert all(torch.isfinite(parameter).all() for parameter in model.parameters())
