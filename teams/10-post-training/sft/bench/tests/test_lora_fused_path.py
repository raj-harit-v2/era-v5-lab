"""LoRA on G5's fused expert path (#521): LoRALinear presents its effective weight W + scale * B A as `.weight`.

Fixture models are random tiny test inputs, never training data.

    python -m pytest teams/10-post-training/sft/bench/tests/test_lora_fused_path.py -q
"""
from __future__ import annotations

import copy
import importlib.util
import math
import sys
from argparse import Namespace
from pathlib import Path

import pytest
import torch
import torch.nn as nn

_parametrize = pytest.mark.parametrize  # avoid dotted-decorator false positives in the lab's older PR email guard
HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
TEAM10 = BENCH.parents[1]
TEAMS = TEAM10.parent
sys.path.insert(0, str(BENCH))


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod




class OldLoRALinear(nn.Module):
    """LoRALinear exactly as before this change (no `weight` property): the reference for 'no change when called'."""

    def __init__(self, base, r, alpha, seed_gen):
        super().__init__()
        self.base = base
        self.r, self.scale = r, alpha / r
        a = torch.empty(r, base.in_features, dtype=base.weight.dtype)
        a.uniform_(-1 / math.sqrt(base.in_features), 1 / math.sqrt(base.in_features), generator=seed_gen)
        self.lora_A = nn.Parameter(a.to(base.weight.device))
        self.lora_B = nn.Parameter(torch.zeros(base.out_features, r, dtype=base.weight.dtype, device=base.weight.device))
        base.weight.requires_grad_(False)
        if base.bias is not None:
            base.bias.requires_grad_(False)

    def forward(self, x):
        return self.base(x) + (x @ self.lora_A.t() @ self.lora_B.t()) * self.scale

    def merged_weight(self):
        return self.base.weight + self.scale * (self.lora_B @ self.lora_A)


# --- Team 5 LanguageModel (G5's model.py of this checkout, post-#521) ---------------------------------------------

def tiny_g5(attn_gate=False):
    spec_ = importlib.util.spec_from_file_location("g5_model_for_lora_test", TEAMS / "05-architecture" / "harness" / "week2" / "model.py")
    g5 = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(g5)
    import numpy as np  # noqa: PLC0415
    rows = np.zeros((64, 4), dtype=np.uint8)
    rows[:, 0] = np.arange(64)
    lengths = np.ones(64, dtype=np.int16)
    m = {"vocab_size": 64, "n_embd": 16, "n_head": 2, "n_kv_head": 1, "n_layer": 2, "rope_theta": 10000.0,
         "norm_eps": 1e-5, "mtp": False, "moe": {"num_experts": 4, "top_k": 2, "num_shared": 1, "ffn_hidden": 32,
                                                  "bias": False}}
    if attn_gate:
        m.update(attn_gate=True, attn_gate_input="normalized", attn_gate_bias=False, attn_gate_init="zero")
    torch.manual_seed(0)
    return g5.LanguageModel(m, rows, lengths)


IDS = torch.tensor([[3, 7, 9, 11, 13, 5, 6, 8], [4, 10, 12, 1, 2, 3, 0, 0]])
VALID = torch.tensor([[True] * 8, [True] * 6 + [False] * 2])


def sft_g5():
    sys.path.insert(0, str(TEAM10 / "capstone"))
    sys.path.insert(0, str(TEAM10 / "rl-loop"))
    import sft_g5 as mod  # noqa: PLC0415
    return mod


bench = sft_g5().bench  # the same module object sft_g5 wraps with, so isinstance checks agree


def lora_args(r=4, alpha=8.0, seed=0):
    return Namespace(lora_r=r, lora_alpha=alpha, seed=seed)


def g5_lora(seed=0, randomise=False, arm="lora"):
    """tiny_g5 wrapped by the real sft_g5.apply_method (the code behind arms `lora` and `lora_markers`)."""
    lm = tiny_g5()
    info = sft_g5().apply_method(lm, "lora", lora_args(seed=seed))
    assert info["wrapped_modules"] > 0
    if randomise:
        gen = torch.Generator().manual_seed(seed + 100)
        with torch.no_grad():
            for m in lm.modules():
                if isinstance(m, bench.LoRALinear):
                    m.lora_A.copy_(torch.randn(m.lora_A.shape, generator=gen) * 0.3)
                    m.lora_B.copy_(torch.randn(m.lora_B.shape, generator=gen) * 0.3)
    return lm


def routed(lm):
    return [(n, m) for n, m in lm.named_modules() if isinstance(m, bench.LoRALinear) and ".moe.experts." in n]


def old_loop_moe_forward(self, x, valid):
    """The MoE.forward of 380376c8 (parent of #521): every routed expert is CALLED on its routed rows."""
    import torch.nn.functional as F  # noqa: PLC0415
    shape = x.shape
    flat = x.reshape(-1, shape[-1])
    active = valid.reshape(-1)
    scores = F.linear(flat.float(), self.router.weight.float()).softmax(-1)
    gates, choice = scores.topk(self.topk, dim=-1)
    gates = gates / gates.sum(-1, keepdim=True)
    output = torch.zeros_like(flat)
    for e, expert in enumerate(self.experts):
        selected = (choice == e) & active[:, None]
        rows = selected.any(-1).nonzero().flatten()
        if rows.numel():
            weight = (gates[rows] * selected[rows]).sum(-1, keepdim=True)
            values = expert(flat[rows]) * weight.to(flat.dtype)
            output = output + torch.zeros_like(flat).index_copy(0, rows, values)
    for expert in self.shared:
        output = output + expert(flat) * active[:, None]
    return output.reshape(shape)


# a. both LoRA arms run one forward and one backward on the post-#521 model.py ----------------------------------------

@_parametrize("marker_rows", [False, True])
def test_a_lora_and_lora_markers_forward_backward_run(marker_rows):
    """`lora_markers` = `--method lora --marker-rows`: the same wrapping plus the trainable output-head marker rows."""
    mod = sft_g5()
    lm = g5_lora(randomise=True)
    if marker_rows:
        mod.enable_head_rows(lm, [1, 2, 3])
    lm.train()
    lm(IDS, VALID).square().mean().backward()
    n_a = sum(1 for _, m in routed(lm) if m.lora_A.grad is not None)
    print(f"a: marker_rows={marker_rows}: routed LoRA layers with a grad on lora_A: {n_a} of {len(routed(lm))}")
    assert n_a > 0
    if marker_rows:
        assert lm.head.weight.grad is not None


# b. a fresh adapter equals the unwrapped model ------------------------------------------------------------------------

def test_b_fresh_adapter_logits_equal_unwrapped_model():
    plain = tiny_g5().eval()
    lm = g5_lora().eval()  # B = 0
    with torch.no_grad():
        diff = float((plain(IDS, VALID) - lm(IDS, VALID)).abs().max())
    print(f"b: max |fresh LoRA - unwrapped| = {diff:.3e}")
    assert diff <= 1e-6


# c. fused path equals the old per-expert loop that CALLS the module -------------------------------------------------

@_parametrize("train_mode", [False, True])
def test_c_fused_path_equals_old_per_expert_loop_with_module_calls(train_mode, monkeypatch):
    lm = g5_lora(seed=1, randomise=True).train(train_mode)
    with torch.no_grad():
        fused = lm(IDS, VALID)
        monkeypatch.setattr(type(lm.blocks[0].moe), "forward", old_loop_moe_forward)
        loop = lm(IDS, VALID)
    diff = float((fused - loop).abs().max())
    print(f"c: max |fused - old loop| = {diff:.3e} (train_mode={train_mode})")
    assert diff < 1e-5
    # the adapter matters in that comparison: a model with B = 0 differs from both
    base_lm = g5_lora(seed=1).train(train_mode)
    with torch.no_grad():
        assert float((base_lm(IDS, VALID) - loop).abs().max()) > 1e-3


# d. gradients: routed lora_A/B finite and non-zero, base weights none and not in the optimizer ------------------------

def test_d_routed_adapters_get_gradients_base_weights_get_none_and_are_not_optimised():
    lm = g5_lora(seed=2, randomise=True).train()
    lm(IDS, VALID).square().mean().backward()
    layers = routed(lm)
    assert len(layers) == 2 * 4 * 3  # 2 blocks x 4 routed experts x gate/up/down
    for name, m in layers:
        for p in (m.lora_A, m.lora_B):
            assert p.grad is None or torch.isfinite(p.grad).all(), name
        assert m.base.weight.grad is None, name  # frozen
        assert not m.base.weight.requires_grad
    live = [(n, m) for n, m in layers if m.lora_A.grad is not None and float(m.lora_A.grad.abs().sum()) > 0
            and float(m.lora_B.grad.abs().sum()) > 0]
    print(f"d: routed layers with non-zero lora_A and lora_B grads: {len(live)} of {len(layers)} "
          f"(experts no token was routed to get none)")
    assert len(live) >= len(layers) // 2
    trainable = [p for p in lm.parameters() if p.requires_grad]  # what sft_g5 hands to the optimizer
    base_ids = {id(m.base.weight) for m in lm.modules() if isinstance(m, bench.LoRALinear)}
    assert not base_ids & {id(p) for p in trainable}
    assert all(any(p is q for q in trainable) for _, m in layers for p in (m.lora_A, m.lora_B))


# e. no double counting, state_dict unchanged, merge bit-identical ---------------------------------------------------

def _wrap_both(seed=3):
    """Two copies of the same random tiny G5, wrapped by the OLD and the NEW LoRALinear with identical A and B."""
    lm_new = g5_lora(seed=seed, randomise=True)
    lm_old = tiny_g5()
    # wrap with the old class by hand (same targets, same order as sft_g5.apply_method), then copy A and B across
    for p in lm_old.parameters():
        p.requires_grad_(False)
    gen = torch.Generator().manual_seed(seed)
    for name, module in list(lm_old.named_modules()):
        if name.endswith(".router") or name == "head":
            continue
        for child_name, child in list(module.named_children()):
            if child_name in sft_g5().G5_LORA_TARGETS and isinstance(child, nn.Linear):
                setattr(module, child_name, OldLoRALinear(child, 4, 8.0, gen))
    new_mods = dict(lm_new.named_modules())
    with torch.no_grad():
        for n, m in lm_old.named_modules():
            if isinstance(m, OldLoRALinear):
                m.lora_A.copy_(new_mods[n].lora_A)
                m.lora_B.copy_(new_mods[n].lora_B)
    return lm_old, lm_new


def test_e1_modules_called_as_modules_are_bit_identical_to_before():
    """Attention q/k/v/o and shared experts are CALLED (never read): same bits as the class before the change. The
    old-loop MoE calls the routed experts too, so with it the whole model is bit-identical."""
    lm_old, lm_new = _wrap_both()
    with torch.no_grad():
        for mode in (False, True):
            lm_old.train(mode)
            lm_new.train(mode)
            for (n, mo), (_, mn) in zip(lm_old.named_modules(), lm_new.named_modules()):
                if isinstance(mn, bench.LoRALinear) and ".moe.experts." not in n:
                    xin = torch.randn(3, mn.base.in_features, generator=torch.Generator().manual_seed(11))
                    assert torch.equal(mo(xin), mn(xin)), n
    import unittest.mock as um  # noqa: PLC0415
    with torch.no_grad(), um.patch.object(type(lm_old.blocks[0].moe), "forward", old_loop_moe_forward), \
            um.patch.object(type(lm_new.blocks[0].moe), "forward", old_loop_moe_forward):  # one MoE class per model
        assert torch.equal(lm_old(IDS, VALID), lm_new(IDS, VALID))
    print("e1: every non-routed LoRALinear call, and the old-loop whole model, are torch.equal old vs new")


def test_e1b_dense_model_wrapped_everywhere_is_bit_identical_to_before():
    """A dense model (no fused path at all): the whole forward is unchanged by the new class."""
    torch.manual_seed(0)

    class Dense(nn.Module):
        def __init__(self):
            super().__init__()
            self.q_proj, self.up_proj, self.down_proj = nn.Linear(16, 16), nn.Linear(16, 32), nn.Linear(32, 16)

        def forward(self, x):
            return self.down_proj(torch.relu(self.up_proj(self.q_proj(x))))

    base = Dense()
    old, new = copy.deepcopy(base), copy.deepcopy(base)
    g1, g2 = torch.Generator().manual_seed(5), torch.Generator().manual_seed(5)
    for mod, cls, g in ((old, OldLoRALinear, g1), (new, bench.LoRALinear, g2)):
        for n in ("q_proj", "up_proj", "down_proj"):
            setattr(mod, n, cls(getattr(mod, n), 4, 8.0, g))
    with torch.no_grad():
        for mod in (old, new):
            for m in mod.modules():
                if isinstance(m, (OldLoRALinear, bench.LoRALinear)):
                    m.lora_B.copy_(torch.full_like(m.lora_B, 0.05))
        x = torch.randn(5, 16)
        assert torch.equal(old(x), new(x))


def test_e2_state_dict_keys_unchanged_old_adapter_loads_and_gives_same_logits():
    lm_old, lm_new = _wrap_both()
    sd_old, sd_new = lm_old.state_dict(), lm_new.state_dict()
    assert list(sd_old) == list(sd_new)  # same keys, same order
    assert any(k.endswith(".lora_A") for k in sd_new) and not any(k.endswith(".q.weight") for k in sd_new)
    # an adapter saved by the OLD class loads strict into the new one and gives the new model's logits
    fresh = g5_lora(seed=3)
    fresh.load_state_dict(sd_old, strict=True)
    with torch.no_grad():
        assert torch.equal(fresh.eval()(IDS, VALID), lm_new.eval()(IDS, VALID))
    # and the other way round
    lm_old.load_state_dict(sd_new, strict=True)
    print(f"e2: {len(sd_new)} state_dict keys, same order, old->new and new->old load strict, logits torch.equal")


def test_e3_merge_lora_is_bit_identical_to_before():
    lm_old, lm_new = _wrap_both()
    # the old merge_lora, written out: isinstance check on the OLD class
    for name, module in list(lm_old.named_modules()):
        for child_name, child in list(module.named_children()):
            if isinstance(child, OldLoRALinear):
                with torch.no_grad():
                    child.base.weight.copy_(child.merged_weight())
                setattr(module, child_name, child.base)
    bench.merge_lora(lm_new)
    assert not any(isinstance(m, bench.LoRALinear) for m in lm_new.modules())
    sd_old, sd_new = lm_old.state_dict(), lm_new.state_dict()
    assert list(sd_old) == list(sd_new)
    assert all(torch.equal(sd_old[k], sd_new[k]) for k in sd_old)
    with torch.no_grad():
        assert torch.equal(lm_old.eval()(IDS, VALID), lm_new.eval()(IDS, VALID))
    print(f"e3: merged state dicts ({len(sd_new)} tensors) torch.equal old vs new; merged logits torch.equal")


def test_e4_merged_model_equals_the_unmerged_fused_path_logits():
    """The weight the fused path reads is the weight merge bakes in (attention and shared experts differ only by the
    rounding of one fused matmul against base(x) + low-rank branch)."""
    lm = g5_lora(seed=4, randomise=True).eval()
    with torch.no_grad():
        before = lm(IDS, VALID)
    bench.merge_lora(lm)
    with torch.no_grad():
        after = lm(IDS, VALID)
    diff = float((before - after).abs().max())
    print(f"e4: max |unmerged fused - merged| = {diff:.3e}")
    assert diff < 1e-5


# dropout guard: the effective weight cannot express it -------------------------------------------------------------

def test_weight_property_refuses_if_dropout_is_ever_set():
    lin = nn.Linear(8, 8, bias=False)
    layer = bench.LoRALinear(lin, 2, 4.0, torch.Generator().manual_seed(0))
    assert layer.dropout == 0.0 and layer.weight.shape == lin.weight.shape
    layer.dropout = 0.1
    with pytest.raises(ValueError, match="dropout"):
        layer.weight
