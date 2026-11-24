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
