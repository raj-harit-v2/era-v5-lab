"""Identical-weights log-prob gate (train.logprob_gate) and train.update_mode.

A tiny OLMoE (no dropout anywhere) is the dense control. A stand-in head with train-mode vocabulary dropout plays the part
of a KE2/KAS head that drops vocabulary rows in train mode (work/kas-readiness-2026-11-21 B5): with it, the default
update forward (train mode) scores sampled tokens differently from the sampler (eval) at identical weights.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest
import torch
from pytest import fixture  # bare decorators: pr-guard reads '+@a.b' as an email
from torch import nn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grpo  # noqa: E402
import train  # noqa: E402
from test_objective_v1_trainer import _run_v1  # noqa: E402
from test_rl_loop import ALL_FAIL, ALL_PASS, MIXED, MIXED_B  # noqa: E402

parametrize = pytest.mark.parametrize


class VocabDropHead(nn.Module):
    """lm_head stand-in: in train mode a random share of vocabulary rows gets +2 on its logit (fresh mask per call), as the
    stand-in KAS head's `token` reading makes dropped rows more likely by dropping their log-prior."""

    def __init__(self, lin: nn.Linear, p: float = 0.5):
        super().__init__()
        self.lin, self.p = lin, p

    def forward(self, h):
        y = self.lin(h)
        if self.training:
            drop = (torch.rand(y.shape[-1], device=y.device) < self.p).to(y.dtype)
            y = y + 2.0 * drop
        return y


@fixture
def dropout_head(monkeypatch):
    real = train.build_model

    def build(mcfg, device):
        pol, tok = real(mcfg, device)
        pol.model.lm_head = VocabDropHead(pol.model.lm_head)
        return pol, tok

    monkeypatch.setattr(train, "build_model", build)


def _gate_file(tmp_path, name):
    return json.loads((tmp_path / name / "logprob_gate.json").read_text())


# --- the gate function itself -------------------------------------------------------------------------------

class _Pol:
    """Policy stand-in: completion log-probs come from a fixed table; train mode adds a fixed shift (a 'dropout')."""

    def __init__(self, model, lp, shift):
        self.model, self.lp, self.shift = model, lp, shift


def _gate_items(lp, cmask, ref=None):
    seq = torch.zeros(lp.shape[0], 2 + lp.shape[1], dtype=torch.long)
    return [(seq, cmask, 2, ref)]


def test_gate_function_reference_sources_tolerances_and_nonfinite(monkeypatch):
    model = nn.Linear(1, 1).eval()
    lp = torch.full((2, 3), -1.0)
    shift = torch.tensor([[0.0, 0.5, 0.0], [0.0, 0.0, 0.0]])
    cmask = torch.tensor([[True, True, True], [True, True, False]])
    monkeypatch.setattr(train, "chunked_logprobs",
                        lambda pol, seq, plen, micro: pol.lp + (pol.shift if pol.model.training else 0.0))
    pol = _Pol(model, lp, shift)
    g = train.logprob_gate(pol, model, _gate_items(lp, cmask), "train", 0.2, None)
    assert g["reference"] == ["eval_forward"] and g["tokens"] == 5 and g["max_abs"] == 0.5
    assert g["mean_abs"] == pytest.approx(0.1) and g["outside_frac"] == pytest.approx(0.2) and not g["ok"]
    g = train.logprob_gate(pol, model, _gate_items(lp, cmask), "eval", 0.2, None)
    assert g["ok"] and g["max_abs"] == 0.0 and g["outside_frac"] == 0.0
    assert not model.training  # the caller's mode is restored
    # a reported sampler log-prob (vLLM rollout_lp) is the reference; padding (cmask False) never counts
    ref = lp.clone()
    ref[1, 2] = float("nan")
    ref[0, 0] = -1.3
    g = train.logprob_gate(pol, model, _gate_items(lp, cmask, ref), "eval", 0.2, None)
    assert g["reference"] == ["rollout_lp"] and g["finite"] and g["max_abs"] == pytest.approx(0.3)
    assert g["outside_frac"] == pytest.approx(0.2) and not g["ok"]
    assert train.logprob_gate(pol, model, _gate_items(lp, cmask, ref), "eval", 0.2, None,
                              mean_abs_tol=1.0, outside_frac_tol=1.0)["ok"]
    ref[0, 1] = float("inf")
    g = train.logprob_gate(pol, model, _gate_items(lp, cmask, ref), "eval", 0.2, None, 1e9, 1.0)
    assert not g["finite"] and not g["ok"]
    assert train.logprob_gate(pol, model, _gate_items(lp, torch.zeros_like(cmask)), "train", 0.2, None)["tokens"] == 0


def test_refusals():
    base = {"algo": grpo.OBJECTIVE_V1, "k": 2, "max_new": 2, "temperature": 1.0}
    for extra, msg in (({"update_mode": "inference"}, "update_mode must be one of"),
                       ({"update_mode": "eval", "dt": {"targets": "gate"}}, "not for Deletion Tuning"),
                       ({"logprob_gate": True, "dt": {"targets": "gate"}}, "not for Deletion Tuning"),
                       ({"logprob_gate": 0.01}, "logprob_gate must be true or a mapping")):
        with pytest.raises(ValueError, match=msg):
            train.train({"model": {"kind": "tiny_olmoe"}, "task": {"kind": "scripted"}, "train": {**base, **extra}})


def test_state_identity_unchanged_for_default_update_mode():
    cfg = {"model": {"kind": "x"}, "task": {}, "train": {"algo": "grpo"}}
    a = train.state_identity(cfg, [])
    assert train.state_identity({**cfg, "train": {"algo": "grpo", "update_mode": "train", "logprob_gate": True}}, []) == a
    assert train.state_identity({**cfg, "train": {"algo": "grpo", "update_mode": "eval"}}, []) != a


# --- through the real trainer -------------------------------------------------------------------------------

def test_gate_fires_on_train_mode_dropout_and_eval_mode_passes(monkeypatch, tmp_path, dropout_head):
    scripts = {MIXED: [0, 1, 0, 1], MIXED_B: [1, 1, 0, 0]}
    with pytest.raises(RuntimeError, match="logprob gate.*update_mode: eval"):
        _run_v1(monkeypatch, tmp_path, "off", dict(scripts), logprob_gate=True)
    g = _gate_file(tmp_path, "off")
    assert not g["ok"] and g["update_mode"] == "train" and g["mean_abs"] > 0.01 and g["reference"] == ["eval_forward"]
    assert not (tmp_path / "off" / "metrics.jsonl").read_text().strip()  # stopped before the first step
    s, opt, recs, _ = _run_v1(monkeypatch, tmp_path, "on", dict(scripts), logprob_gate=True, update_mode="eval")
    g = _gate_file(tmp_path, "on")
    assert g["ok"] and g["max_abs"] == 0.0 and g["tokens"] == 4 * 3 and s["logprob_gate"] == g
    assert s["update_mode"] == "eval" and recs[0]["optimizer_stepped"] and opt.n_steps == 1
    assert recs[0]["masked_frac"] == 0.0  # epoch 1 at identical weights: every ratio is 1, nothing masked
    # what the gate protects against: default mode, same head, no gate -> the trust-region mask fires on dropout noise
    _, _, recs_d, _ = _run_v1(monkeypatch, tmp_path, "default", dict(scripts))
    assert recs_d[0]["masked_frac"] > 0.0


def test_dense_head_passes_in_both_modes_and_eval_mode_changes_nothing(monkeypatch, tmp_path):
    scripts = {MIXED: [0, 1, 0, 1], MIXED_B: [1, 1, 0, 0]}
    s0, o0, r0, _ = _run_v1(monkeypatch, tmp_path, "t", dict(scripts), logprob_gate=True)
    s1, o1, r1, _ = _run_v1(monkeypatch, tmp_path, "e", dict(scripts), logprob_gate=True, update_mode="eval")
    s2, o2, r2, _ = _run_v1(monkeypatch, tmp_path, "plain", dict(scripts))  # flags off: the old behaviour
    assert s0["logprob_gate"]["ok"] and s1["logprob_gate"]["ok"] and s0["logprob_gate"]["max_abs"] == 0.0
    assert "logprob_gate" not in s2 and "update_mode" not in s2 and not (tmp_path / "plain" / "logprob_gate.json").exists()
    assert r0[0]["loss"] == r1[0]["loss"] == r2[0]["loss"]  # no train-only layer: eval mode is the same computation
    for p0, p1, p2 in zip(o0.params(), o1.params(), o2.params()):
        assert torch.equal(p0, p1) and torch.equal(p0, p2)


@parametrize("flags", [{}, {"update_mode": "eval", "logprob_gate": True}], ids=["off", "on"])
def test_grpo_review_with_flags_off_and_on(monkeypatch, tmp_path, dropout_head, flags):
    """CLAUDE.md 'G10 GRPO review', with the stand-in dropout head: constant / singleton / mixed through the real advantage
    function; a dropped group leaves the mixed groups' update unchanged; an all-dropped batch skips the optimizer."""
    assert grpo.advantages(torch.tensor([1.0, 1.0, 1.0, 1.0]), grpo.OBJECTIVE_V1) is None
    assert grpo.advantages(torch.tensor([1.0]), grpo.OBJECTIVE_V1) is None
    a = grpo.advantages(torch.tensor([0.0, 1.0, 0.0, 1.0]), grpo.OBJECTIVE_V1)
    assert torch.isfinite(a).all() and a.tolist() == [-0.5, 0.5, -0.5, 0.5]
    mixed = {MIXED: [0, 1, 0, 1], MIXED_B: [1, 1, 0, 0]}
    torch.manual_seed(0)  # the dropout masks draw from the global stream: same seed for both arms
    _, o0, r0, _ = _run_v1(monkeypatch, tmp_path, "d0", dict(mixed), ppo_epochs=2, **flags)
    _, o1, r1, rec1 = _run_v1(monkeypatch, tmp_path, "d1", {**mixed, ALL_PASS: [1, 1, 1, 1]}, ppo_epochs=2, **flags)
    assert r1[0]["groups_dropped"] == 1 and ALL_PASS not in rec1["groups"] and r0[0]["tokens"] == r1[0]["tokens"]
    if flags:  # eval mode: no dropout draw, so the two runs are the same computation
        assert r1[0]["loss"] == pytest.approx(r0[0]["loss"], abs=1e-7)
        for p0, p1 in zip(o0.params(), o1.params()):
            assert torch.allclose(p0, p1, atol=1e-7, rtol=0)
            for key in ("exp_avg", "exp_avg_sq"):
                assert torch.allclose(o0.state[p0][key], o1.state[p1][key], atol=1e-9, rtol=1e-5)
    else:  # train mode draws masks from the global stream; finite and stepped is all that holds
        assert math.isfinite(r0[0]["loss"]) and math.isfinite(r1[0]["loss"]) and o0.n_steps == o1.n_steps == 2
    _, opt, recs, rec = _run_v1(monkeypatch, tmp_path, "z", {ALL_PASS: [1, 1, 1, 1], ALL_FAIL: [0, 0, 0, 0]}, steps=2,
                                **flags)
    assert not any(r["optimizer_stepped"] for r in recs) and opt.n_steps == 0 and len(opt.state) == 0
    assert all(torch.equal(p, p0) for p, p0 in zip(opt.params(), opt.start))
    assert rec["logprob_calls"] == (2 if flags else 0)  # the gate's two forwards; no old_lp for dropped groups
    _, opt, recs, _ = _run_v1(monkeypatch, tmp_path, "z1", {MIXED: [0, 1, 0, 1]}, k=1, **flags)
    assert recs[0]["group_kinds"]["singleton"] == 1 and opt.n_steps == 0 and len(opt.state) == 0


# --- update_mode auto (job ADP, 24 Nov): resolved from the module tree, never refused -----------------------------------

class KASLikeHead(nn.Module):
    """lm_head stand-in with Team 5's #717 KASHead correction term and its train-mode dropout, written out here (the team
    branch may not carry teams/05-architecture/harness/week2/kas_v2.py): logits = lin(h) + (h @ tok_c.T) @ dropped(tok_u).T,
    one keep mask of shape [V, 1] per forward (keep 0.95, inverted scaling), eval draws nothing. `tok_dropout` is the same
    attribute name as KASHead's. `tok_u_std`: 0.0025 is #717's init (an untrained stand-in); 1.0 plays a trained head."""

    def __init__(self, lin: nn.Linear, tok_u_std: float, p: float = 0.05, rank: int = 8):
        super().__init__()
        g = torch.Generator().manual_seed(7)
        self.lin, self.tok_dropout = lin, p
        self.in_features, self.out_features = lin.in_features, lin.out_features  # as KASHead
        self.tok_u = nn.Parameter(torch.randn(lin.out_features, rank, generator=g) * tok_u_std)
        self.tok_c = nn.Parameter(torch.randn(rank, lin.in_features, generator=g) * lin.in_features ** -0.5)

    def forward(self, h):
        u = self.tok_u
        if self.training and self.tok_dropout > 0:
            keep = 1.0 - self.tok_dropout
            u = u * (torch.rand((u.shape[0], 1), device=u.device) < keep).to(u.dtype) / keep
        return self.lin(h) + (h @ self.tok_c.t()) @ u.t()


def _kas_like(monkeypatch, tok_u_std):
    real = train.build_model

    def build(mcfg, device):
        pol, tok = real(mcfg, device)
        pol.model.lm_head = KASLikeHead(pol.model.lm_head, tok_u_std)
        return pol, tok

    monkeypatch.setattr(train, "build_model", build)


def test_auto_update_mode_is_resolved_from_the_modules_not_a_config_name():
    lin = nn.Linear(4, 6)
    plain, kas = nn.Sequential(nn.Linear(4, 4), nn.Dropout(0.0)), nn.Sequential(nn.Linear(4, 4), KASLikeHead(lin, 1.0))
    r = train.resolve_update_mode(None, plain, dt=False)
    assert (r["requested"], r["resolved"], r["train_mode_randomness"]) == ("auto", "train", [])
    r = train.resolve_update_mode("auto", kas, dt=False)
    assert r["resolved"] == "eval" and r["train_mode_randomness"] == ["1: KASLikeHead.tok_dropout=0.05"]
    assert train.resolve_update_mode(None, kas, dt=True)["resolved"] == "train_quiet"  # DT keeps its soft masks
    assert train.resolve_update_mode(None, nn.Sequential(nn.Dropout(0.1)), dt=False)["resolved"] == "eval"
    r = train.resolve_update_mode("train", kas, dt=False)  # explicit train stays possible, with the warning recorded
    assert r["resolved"] == "train" and "WARNING" in r["reason"]
    flag = nn.Linear(2, 2)
    flag.tok_dropout = True  # a bool is not a probability
    assert train.resolve_update_mode(None, flag, dt=False)["resolved"] == "train"


def test_train_quiet_puts_only_the_random_modules_in_eval():
    lin = nn.Linear(4, 6)
    m = nn.Sequential(nn.Linear(4, 4), KASLikeHead(lin, 1.0), nn.Dropout(0.2))
    train.update_forward_mode(m, "train_quiet")
    assert m.training and m[0].training and not m[1].training and not m[2].training and m[1].lin.training  # own flag only
    train.update_forward_mode(m, "train")
    assert all(x.training for x in m.modules())
    train.update_forward_mode(m, "eval")
    assert not any(x.training for x in m.modules())


def test_kas_head_with_trained_tok_u_auto_mode_passes_the_gate_and_explicit_train_fails_it(monkeypatch, tmp_path):
    """Broken variant (C0 decision 2): the old default, train mode, on a KAS-like head whose tok_u is trained-sized. The
    gate fires there; auto resolves to eval, the gate reads 0.0 and the summary says what was resolved and why."""
    scripts = {MIXED: [0, 1, 0, 1], MIXED_B: [1, 1, 0, 0]}
    _kas_like(monkeypatch, 1.0)
    with pytest.raises(RuntimeError, match="logprob gate"):
        _run_v1(monkeypatch, tmp_path, "train", dict(scripts), logprob_gate=True, update_mode="train")
    g = _gate_file(tmp_path, "train")
    assert not g["ok"] and g["update_mode"] == "train" and g["mean_abs"] > 0.01
    print(json.dumps({"kas_like_tok_u_std_1.0_train_mode_gate": {k_: g[k_] for k_ in ("mean_abs", "max_abs", "outside_frac")}}))
    # same wrapped build_model (a second _kas_like would wrap the head twice)
    s, opt, recs, _ = _run_v1(monkeypatch, tmp_path, "auto", dict(scripts), logprob_gate=True)
    g = _gate_file(tmp_path, "auto")
    assert g["ok"] and g["max_abs"] == 0.0 and g["update_mode"] == "eval"
    res = s["update_mode_resolution"]
    assert res["requested"] == "auto" and res["resolved"] == "eval" and s["update_mode"] == "eval"
    assert res["train_mode_randomness"] == ["lm_head: KASLikeHead.tok_dropout=0.05"]
    assert recs[0]["optimizer_stepped"] and recs[0]["masked_frac"] == 0.0


def test_an_untrained_kas_tok_u_hides_the_dropout_noise_from_the_gate(monkeypatch, tmp_path):
    """Why a CPU stand-in cannot show the hazard: at #717's init scale (std 0.0025) train-mode dropout moves log-probs by
    far less than the gate's 0.01-nat tolerance, so the gate passes in train mode. The real head is trained."""
    scripts = {MIXED: [0, 1, 0, 1], MIXED_B: [1, 1, 0, 0]}
    _kas_like(monkeypatch, 0.0025)
    s, _, _, _ = _run_v1(monkeypatch, tmp_path, "small", dict(scripts), logprob_gate=True, update_mode="train")
    g = _gate_file(tmp_path, "small")
    print(json.dumps({"kas_like_tok_u_std_0.0025_train_mode_gate": {k_: g[k_] for k_ in ("mean_abs", "max_abs", "outside_frac")}}))
    assert g["ok"] and g["mean_abs"] < 0.01 and g["update_mode"] == "train"


def test_a_router_bias_change_is_recorded_after_the_outputs_not_raised(monkeypatch, tmp_path):
    """C1 fix 2: a run whose router_bias moved (something called update_router_bias) still returns and writes its summary;
    the summary carries the failure, router_bias_unchanged False, and train.py's CLI exits non-zero. Nothing is lost."""
    scripts = {MIXED: [0, 1, 0, 1], MIXED_B: [1, 1, 0, 0]}
    real = train.build_model

    def build(mcfg, device):
        pol, tok = real(mcfg, device)
        pol.model.model.layers[0].mlp.register_buffer("router_bias", torch.zeros(4))
        return pol, tok

    monkeypatch.setattr(train, "build_model", build)
    real_bg = train.backward_objective_v1

    def bg(pol, *a, **kw):  # a trainer that moves the balancer bias, which G10 never does
        pol.model.model.layers[0].mlp.router_bias.add_(0.001)
        return real_bg(pol, *a, **kw)

    monkeypatch.setattr(train, "backward_objective_v1", bg)
    s, _, recs, _ = _run_v1(monkeypatch, tmp_path, "bias", dict(scripts))
    assert recs[0]["optimizer_stepped"] and s["router_bias_unchanged"] is False and s["router_bias_checksum"]
    assert any("router_bias changed" in f for f in s["failures"])
    on_disk = json.loads((tmp_path / "bias" / "summary.json").read_text())
    assert on_disk["router_bias_unchanged"] is False and on_disk["failures"] == s["failures"]


def test_bnp_c_trainer_fails_the_bias_check_when_the_arm_expects_a_bias_but_none_is_registered(monkeypatch, tmp_path):
    """Job BNP: a model whose config says MoE experts with bias_gamma > 0 but that registers no router_bias buffer used to
    report None == None as unchanged. Now the summary says router_bias_unchanged False with the reason, after the outputs,
    as for a moved bias. The same tiny model without such a config (dense control) still passes."""
    scripts = {MIXED: [0, 1, 0, 1], MIXED_B: [1, 1, 0, 0]}
    real = train.build_model

    def build(mcfg, device):
        pol, tok = real(mcfg, device)
        pol.model.spec = {"moe": {"num_experts": 4, "bias_gamma": 0.001}}  # the arm's config; no buffer anywhere
        return pol, tok

    monkeypatch.setattr(train, "build_model", build)
    s, _, recs, _ = _run_v1(monkeypatch, tmp_path, "nobias", dict(scripts))
    assert recs[0]["optimizer_stepped"] and s["router_bias_unchanged"] is False
    chk = s["router_bias_check"]
    assert chk["expected"] and chk["buffers"] == 0 and chk["before"] is None and chk["after"] is None
    assert any("router_bias check failed" in f for f in s["failures"])
    on_disk = json.loads((tmp_path / "nobias" / "summary.json").read_text())
    assert on_disk["router_bias_unchanged"] is False and on_disk["failures"] == s["failures"]
    monkeypatch.setattr(train, "build_model", real)
    d, _, _, _ = _run_v1(monkeypatch, tmp_path, "dense", dict(scripts))
    assert d["router_bias_unchanged"] is True and d["router_bias_check"]["expected"] is False and not d.get("failures")
