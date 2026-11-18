"""Tests for parallel_layout_v1.py against Team 5's real model, optimizer and config resolver.

CPU only, no training: the models are built on the meta device (sizes) or at a tiny shape (one forward, one
optimizer step). Run from the repository root or teams/07-infrastructure:

    python -m pytest teams/07-infrastructure/layout/test_parallel_layout_v1.py -q
"""
import copy
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import yaml

torch = pytest.importorskip("torch")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parallel_layout_v1 as v1  # noqa: E402
from week2.config import load_runtime  # noqa: E402  (v1 put Team 5's harness on the path)
from week2.evaluation import token_nll  # noqa: E402
from week2.model import LanguageModel  # noqa: E402
from week2.optim import build_optimizer, uses_muon  # noqa: E402

ARMS = v1.TEAM5 / "configs" / "arms"

# Config v1 as PR 447 writes it (Gate 2, 14 Nov 2026): the decided values, sizes empty.
PR447 = {"run.seed": 1234, "run.grad_clip": 1.0, "optim.name": "muon", "optim.lr": 0.001,
         "tokenizer.name": "BrahmicTokenizer-131K", "tokenizer.vocab_size": 131072, "embedding.type": "kronecker",
         "embedding.pos_dim": 32, "embedding.ke2_output_dim": None, "model.n_layer": None, "model.d_model": None,
         "model.n_head": None, "model.d_ff": None, "attention.impl": "eager", "moe.n_expert": 16, "moe.n_shared": 1,
         "moe.top_k": 2, "loss.train_on": "ntp", "data.seq_len": None, "precision": None}


def decisions(tmp_path, **change):
    values = {**PR447, **change}
    path = tmp_path / "config_v1.yaml"
    path.write_text(yaml.safe_dump({"settings": [{"key": k, "value": v} for k, v in values.items()]}))
    return str(path)


def team5_model(m, device="cpu"):
    rng = np.random.default_rng(7)
    rows = rng.integers(0, 256, (m["vocab_size"], m["ke_max_pos"]), dtype=np.uint8)
    lengths = rng.integers(1, m["ke_max_pos"] + 1, m["vocab_size"], dtype=np.int16)
    with torch.device(device):
        return LanguageModel(m, rows, lengths)


def tiny(arm="exp2_muon", **change):
    """Team 5's resolved arm at a small size, and the matching v1 Shape."""
    cfg = load_runtime(ARMS / f"{arm}.yaml")
    m = copy.deepcopy(cfg["model"])
    moe = {k: change.pop(k) for k in ("num_experts", "top_k", "num_shared", "ffn_hidden") if k in change}
    m.update(dict(n_layer=2, n_embd=128, n_head=4, n_kv_head=2, vocab_size=512, block_size=64, ke_max_pos=4),
             **change)
    m["moe"].update(dict(num_experts=4, top_k=2, num_shared=1, ffn_hidden=192), **moe)
    s = v1.Shape(vocab=m["vocab_size"], seq=m["block_size"], layers=m["n_layer"], d=m["n_embd"],
                  n_head=m["n_head"], n_kv=m["n_kv_head"], ffn_hidden=m["moe"]["ffn_hidden"],
                  n_exp=m["moe"]["num_experts"], top_k=m["moe"]["top_k"], n_shared=m["moe"]["num_shared"],
                  ke_pos=m["ke_max_pos"], mtp=bool(m["mtp"]), optimizer=cfg["optim"]["name"])
    return cfg, m, s


# ---------------------------------------------------------------- parameters
@pytest.mark.parametrize("arm", ["t2", "t3", "exp2_muon"])
def test_param_counts_equal_team5_model_at_full_size(arm):
    s, _ = v1.shape_from_arm(ARMS / f"{arm}.yaml")
    s = replace(s, optimizer="muon")
    model = team5_model(load_runtime(ARMS / f"{arm}.yaml")["model"], device="meta")
    named = list(model.named_parameters())
    pc = v1.param_counts(s)
    assert pc["total"] == sum(p.numel() for _, p in named)
    assert pc["muon"] == sum(p.numel() for n, p in named if uses_muon(n, p))
    assert pc["routed_experts"] == sum(p.numel() for n, p in named if ".moe.experts." in n)


@pytest.mark.parametrize("change", [{}, {"mtp": True}, {"num_shared": 0}, {"n_kv_head": 1}, {"n_kv_head": 4},
                                    {"num_experts": 8, "top_k": 1}])
def test_param_counts_equal_team5_model_for_other_shapes(change):
    _, m, s = tiny(**change)
    named = list(team5_model(m, device="meta").named_parameters())
    assert v1.param_counts(s)["total"] == sum(p.numel() for _, p in named)
    assert v1.param_counts(s)["muon"] == sum(p.numel() for n, p in named if uses_muon(n, p))


def test_t2_and_t3_sizes():
    t2, _ = v1.shape_from_arm(ARMS / "t2.yaml")
    t3, _ = v1.shape_from_arm(ARMS / "t3.yaml")
    assert v1.param_counts(replace(t2, optimizer="muon"))["total"] == 237_052_416
    assert v1.param_counts(replace(t3, optimizer="muon"))["total"] == 391_529_600
    assert (t2.ffn_hidden, t3.ffn_hidden) == (768, 896)                 # the explicit widths, not a ratio


# ---------------------------------------------------------------- optimizer state
@pytest.mark.parametrize("arm", ["exp2_muon", "t2"])
def test_optimizer_bytes_equal_team5_optimizer_state(arm):
    """Muon keeps one fp32 buffer per block matrix (4 bytes), AdamW two fp32 moments (8 bytes)."""
    torch.manual_seed(0)
    cfg, m, s = tiny(arm)
    model = team5_model(m)
    opt = build_optimizer(model, cfg["optim"])
    x = torch.randint(0, m["vocab_size"], (4, m["block_size"]))
    token_nll(model(x, torch.ones_like(x, dtype=torch.bool)), x).mean().backward()
    assert all(p.grad is not None for p in model.parameters())              # every expert got tokens
    opt.step()
    inner = [o for _, o in opt.named] if hasattr(opt, "named") else [opt]
    state = sum(t.numel() * t.element_size() for o in inner for st in o.state.values() for t in st.values()
                if torch.is_tensor(t) and t.dim() > 0)                     # the 0-dim AdamW step counters aside
    assert v1.memory(s, v1.Layout())["optimizer"] == state


# ---------------------------------------------------------------- activations
def saved_bytes(model, x, amp):
    """Bytes of the tensors autograd keeps for backward (unique storages, parameters excluded)."""
    params = {p.untyped_storage().data_ptr() for p in model.parameters()}
    seen, keep = {}, []

    def pack(t):
        keep.append(t)
        st = t.untyped_storage()
        if st.data_ptr() not in params:
            seen[st.data_ptr()] = st.nbytes()
        return t

    ctx = torch.autocast("cpu", dtype=torch.bfloat16) if amp else torch.autocast("cpu", enabled=False)
    with torch.autograd.graph.saved_tensors_hooks(pack, lambda t: t), ctx:
        token_nll(model(x, torch.ones_like(x, dtype=torch.bool)), x).mean()
    return sum(seen.values())


@pytest.mark.parametrize("dtype", ["bf16", "fp32"])
@pytest.mark.parametrize("change", [{}, {"n_embd": 256, "n_head": 8}, {"ffn_hidden": 384}, {"block_size": 128},
                                    {"num_shared": 0}, {"top_k": 1}, {"n_layer": 3}])
def test_activation_formula_matches_saved_tensors_on_cpu(dtype, change):
    """The fitted per-token constants and the bf16 weight copies, against Team 5's real forward pass. The
    held logits (not saved by autograd) are left out; CUDA's fp32 softmax is not on CPU, so device=cpu."""
    torch.manual_seed(1)
    _, m, s = tiny(**change)
    s = replace(s, dtype=dtype)
    model = team5_model(m)
    lay = v1.Layout(b=2)
    x = torch.randint(0, m["vocab_size"], (lay.b, m["block_size"]))
    got = saved_bytes(model, x, amp=dtype == "bf16")
    mem = v1.memory(s, lay, device="cpu")
    want = mem["activations"] + mem["cast_copies"] + v1.activation_terms(s, lay, "cpu")["log_softmax"]
    assert abs(want - got) / got < 0.01, (want, got)          # 0.4 % at most when written


def test_cuda_scores_cost_three_times_the_cpu_scores():
    _, _, s = tiny()
    cpu = v1.activation_terms(s, v1.Layout(), "cpu")["per_layer"]
    cuda = v1.activation_terms(s, v1.Layout(), "cuda")["per_layer"]
    assert cuda - cpu == 4 * s.n_head * s.seq * s.seq


# ---------------------------------------------------------------- config v1 decisions
def test_pr447_decisions_accept_t2_and_t3_and_count_muon(tmp_path):
    for arm in ("t2", "t3"):
        s, _, notes = v1.load_shape(ARMS / f"{arm}.yaml", decisions(tmp_path))
        assert (s.n_exp, s.n_shared, s.top_k, s.optimizer) == (16, 1, 2, "muon")
        assert any("optim.name" in n and "adamw" in n for n in notes)       # the arm trains AdamW; v1 says Muon
        assert any("model.n_layer: empty" in n for n in notes)


def test_t1_has_8_experts_and_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="moe.n_expert 16 vs arm 8"):
        v1.load_shape(ARMS / "t1.yaml", decisions(tmp_path))


def test_the_pr447_shared_expert_key_is_read(tmp_path):
    """v0 reads moe.num_shared; PR 447 writes moe.n_shared. A wrong value must stop v1, not pass silently."""
    with pytest.raises(SystemExit, match="moe.n_shared 0 vs arm 1"):
        v1.load_shape(ARMS / "t2.yaml", decisions(tmp_path, **{"moe.n_shared": 0}))


def test_a_filled_size_must_agree_with_the_arm(tmp_path):
    v1.load_shape(ARMS / "t2.yaml", decisions(tmp_path, **{"model.d_ff": 768, "data.seq_len": 2048}))
    with pytest.raises(SystemExit, match="model.d_ff 896 vs arm 768"):
        v1.load_shape(ARMS / "t2.yaml", decisions(tmp_path, **{"model.d_ff": 896}))


# ---------------------------------------------------------------- Muon and layouts
@pytest.mark.parametrize("text,ok", [("dp=2", True), ("pp=2,m=8", True), ("cp=2", True), ("dp=2,ep=2", True),
                                     ("dp=2,zero=1", False), ("dp=2,zero=2", False), ("dp=2,zero=3", False),
                                     ("tp=2", False)])
def test_muon_conflict_is_flagged_for_layouts_that_split_a_matrix(text, ok):
    _, _, s = tiny()
    assert (v1.muon_check(s, v1.parse_layout(text)) == "ok") == ok
    assert v1.muon_check(replace(s, optimizer="adamw"), v1.parse_layout(text)) == "n/a"


def test_ddp_does_not_divide_newton_schulz_work_and_ep_does():
    _, _, s = tiny()
    one = v1.muon_tflop(s, v1.Layout())
    assert v1.muon_tflop(s, v1.parse_layout("dp=2")) == one
    assert v1.muon_tflop(s, v1.parse_layout("dp=2,ep=2")) < one


def test_zero_1_and_2_send_what_ddp_sends_and_zero_3_one_and_a_half_times():
    _, _, s = tiny()
    ddp = v1.traffic(s, v1.parse_layout("dp=4"))["dp"]
    assert v1.traffic(s, v1.parse_layout("dp=4,zero=1"))["dp"] == pytest.approx(ddp)
    assert v1.traffic(s, v1.parse_layout("dp=4,zero=2"))["dp"] == pytest.approx(ddp)
    assert v1.traffic(s, v1.parse_layout("dp=4,zero=3"))["dp"] == pytest.approx(1.5 * ddp)


@pytest.mark.parametrize("world", [1, 2, 4])
def test_standard_layouts_are_valid_and_one_device_keeps_the_global_batch(world):
    s, _ = v1.shape_from_arm(ARMS / "t2.yaml")
    lays = v1.standard_layouts(s, world, v1.parse_layout("b=1,m=8"))
    assert lays and all(not v1.layout_problems(s, lay, world) for lay in lays)
    if world == 1:
        assert [(lay.b, lay.m) for lay in lays] == [(1, 8), (2, 4), (4, 2), (8, 1)]
        assert all(v1.runs_today(lay) == "yes" for lay in lays)


@pytest.mark.parametrize("text,word", [("tp=3", "n_head"), ("ep=3,dp=3", "routed experts"), ("pp=9,m=9", "layers"),
                                       ("pp=2,m=1", "never fills"), ("cp=3", "sequence")])
def test_bad_layouts_are_refused(text, word):
    s, _ = v1.shape_from_arm(ARMS / "t2.yaml")
    assert any(word in p for p in v1.layout_problems(s, v1.parse_layout(text)))


def test_command_line(tmp_path, capsys):
    assert v1.main(["--arm", str(ARMS / "t2.yaml"), "--decisions", decisions(tmp_path), "--world", "1",
                     "--device-gib", "80", "--markdown"]) == 0
    out = capsys.readouterr().out
    assert "muon=165,740,544" in out and "| single | 8 | 1 | 16384 |" in out
