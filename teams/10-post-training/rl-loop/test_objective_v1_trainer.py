"""objective_v1 (the lead's Session 18 objective, rl/objective_v1.md) inside the real trainer.

The lead's reference module rl/objective_v1.py is the oracle: values, masks and denominators computed by the batched
trainer are compared with it on the same numbers. Trainer-level cases go through train.train (real advantage
function, real backward, real AdamW) on a tiny random OLMoE with scripted rewards: test fixtures only, no text.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grpo  # noqa: E402
import train  # noqa: E402
from policy import completion_logprobs  # noqa: E402
from test_rl_loop import (ALL_FAIL, ALL_PASS, MIXED, MIXED_B, _TINY, ScriptedTask, _PromptSeeded,  # noqa: E402
                          _RecAdamW, _uneven_group)

_spec = importlib.util.spec_from_file_location("lead_objective_v1", HERE.parent / "rl" / "objective_v1.py")
ref = importlib.util.module_from_spec(_spec)
sys.modules["lead_objective_v1"] = ref  # dataclasses need the module registered
_spec.loader.exec_module(ref)
V1 = grpo.OBJECTIVE_V1


def _reference(groups, eps=0.2):
    """groups: list of (rewards, new_lp [k,T], sampler_lp [k,T], cmask [k,T]) -> lead objective_v1 result."""
    out = []
    for rewards, new, samp, cm in groups:
        rolls = []
        for i, r in enumerate(rewards):
            m = cm[i]
            lp = new[i][m].double()
            ratio = torch.exp(new[i][m].double() - samp[i][m].double())
            rolls.append(ref.Rollout(reward=float(r), logprobs=tuple(lp.tolist()), ratios=tuple(ratio.tolist())))
        out.append(rolls)
    return ref.objective_v1(out, eps)


# 1. advantages: constant, singleton, mixed through the trainer's advantage function -------------------------------
def test_v1_advantages_match_the_reference_for_constant_singleton_and_mixed_groups():
    for rewards in ([1, 1, 1, 1], [0, 0, 0, 0], [0.5, 0.5], [1], [0]):
        assert grpo.advantages(torch.tensor(rewards, dtype=torch.float), V1) is None
        assert ref.group_advantage(rewards) is None
    for rewards in ([0, 1], [0, 1, 0, 1], [1, 0, 0, 0, 0, 0, 0, 0], [0.2, 0.9, 0.4]):
        a = grpo.advantages(torch.tensor(rewards, dtype=torch.float), V1)
        assert torch.isfinite(a).all()
        assert a.tolist() == pytest.approx(list(ref.group_advantage(rewards)), abs=1e-7)
    # no std division: [0, 1] gives +-0.5, not +-1
    assert grpo.advantages(torch.tensor([0.0, 1.0]), V1).tolist() == [-0.5, 0.5]
    # the legacy algorithms are untouched
    assert grpo.ALGOS == ("grpo", "dr_grpo", "rloo", "gspo")


# 2. boundaries ------------------------------------------------------------------------------------------------------
def test_v1_mask_bounds_are_closed_and_match_the_reference():
    ratios = [0.0, 0.5, 0.7, 0.7999999, 0.8, 0.9, 1.0, 1.1, 1.2, 1.2000001, 1.3, 5.0]
    ours = grpo.trust_region_mask(torch.tensor(ratios, dtype=torch.float64), 0.2).int().tolist()
    assert ours == list(ref.trust_region_mask(ratios, 0.2))
    assert ours == [0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0]
    assert grpo.trust_region_mask(torch.tensor([1.0, 1.0 + 1e-12], dtype=torch.float64), 0.0).tolist() == [True, False]
    with pytest.raises(ValueError):
        grpo.trust_region_mask(torch.ones(2), -0.1)


def _random_case(seed, k=6, T=9, lengths=None, spread=0.35):
    g = torch.Generator().manual_seed(seed)
    new = -torch.rand(k, T, generator=g) * 3 - 0.05
    samp = new + spread * torch.randn(k, T, generator=g)
    lengths = lengths or [int(x) for x in torch.randint(0, T + 1, (k,), generator=g)]
    cm = torch.arange(T)[None, :] < torch.tensor(lengths)[:, None]
    return new, samp, cm


# 3. loss, mask, denominator and gradient vs the reference, padding excluded --------------------------------------
def test_v1_terms_match_the_reference_loss_tokens_and_gradient():
    for seed in range(5):
        cases = []
        for j in range(3):
            new, samp, cm = _random_case(100 * seed + j)
            rewards = [[0, 1, 1, 0, 1, 0], [1, 1, 1, 1, 1, 1], [0.0, 0.5, 1.0, 0.0, 0.0, 0.25]][j]
            cases.append((rewards, new, samp, cm))
        want = _reference(cases)
        kept = [(r, n, s, c) for r, n, s, c in cases if grpo.advantages(torch.tensor(r, dtype=torch.float), V1)
                is not None]
        T = sum(int(c.sum()) for _, _, _, c in kept)
        assert T == want.tokens
        leaves, total, inside = [], 0.0, 0
        for r, n, s, c in kept:
            leaf = n.clone().requires_grad_(True)
            adv = grpo.advantages(torch.tensor(r, dtype=torch.float), V1)
            num, st = grpo.objective_v1_terms(leaf, s, adv, c)
            (num / T).backward()
            total += float(num.detach()) / T
            inside += int(st["inside"])
            leaves.append((leaf, s, adv, c))
        assert total == pytest.approx(want.loss, rel=1e-5, abs=1e-7) and inside == want.tokens_inside
        for leaf, s, adv, c in leaves:
            ratio = torch.exp(leaf.detach().double() - s.double())
            m = grpo.trust_region_mask(ratio) & c
            expected = torch.where(m, -adv[:, None].expand_as(leaf) / T, torch.zeros_like(leaf))
            assert torch.allclose(leaf.grad, expected, atol=1e-8)
            assert torch.all(leaf.grad[~m] == 0)  # out-of-region AND padding tokens get exactly zero gradient


def test_v1_padding_is_excluded_but_masked_real_tokens_stay_in_the_denominator():
    new, samp, cm = _random_case(7, k=4, T=8, lengths=[3, 8, 0, 5], spread=0.0)
    adv = grpo.advantages(torch.tensor([0.0, 1.0, 1.0, 0.0]), V1)
    base, st = grpo.objective_v1_loss(new, samp, adv, cm)
    assert int(st["tokens"]) == 16 and int(st["inside"]) == 16
    junk = samp.clone()
    junk[~cm] = torch.tensor(float("inf"))  # garbage in padded slots must not matter
    padded, st2 = grpo.objective_v1_loss(new, junk, adv, cm)
    assert torch.equal(base, padded) and int(st2["tokens"]) == 16
    out = samp.clone()
    out[1, 0] = new[1, 0] - math.log(1.5)  # push one real token out of the region
    l2, st3 = grpo.objective_v1_loss(new, out, adv, cm)
    assert int(st3["tokens"]) == 16 and int(st3["inside"]) == 15 and int(st3["masked_pos"]) == 1
    keep = cm.clone()
    keep[1, 0] = False
    num_rest = -(new * adv[:, None] * keep).sum()
    assert float(l2) == pytest.approx(float(num_rest) / 16, rel=1e-6)  # same T = 16, not 15


# 4. the trainer's chunked backward: unequal lengths, micro_rows, and splitting across groups ----------------------
def _v1_backward(model, pol, groups, n_tok, micro):
    model.zero_grad(set_to_none=True)
    total = 0.0
    for g in groups:
        lv, _ = train.backward_objective_v1(pol, g, 0.2, n_tok, micro)
        total += float(lv)
    return total, {n: p.grad.clone() for n, p in model.named_parameters() if p.grad is not None}


def test_v1_micro_rows_and_group_split_match_unchunked_and_the_reference():
    model, pol, seq, cmask, _, old, _, plen = _uneven_group()
    rewards = [0.0, 1.0, 1.0, 0.0, 1.0]
    adv = grpo.advantages(torch.tensor(rewards), V1)
    with torch.no_grad():
        cur = completion_logprobs(pol, seq, plen)
    n_tok = int(cmask.sum())
    want = _reference([(rewards, cur, old, cmask)])
    t0, g0 = _v1_backward(model, pol, [(seq, cmask, adv, old, None, plen, None)], n_tok, None)
    assert t0 == pytest.approx(want.loss, rel=1e-5, abs=1e-7)
    assert 0 < want.tokens_inside < want.tokens  # the case exercises masked real tokens
    for micro in (1, 2, 3, 4):
        t, g = _v1_backward(model, pol, [(seq, cmask, adv, old, None, plen, None)], n_tok, micro)
        assert t == pytest.approx(t0, abs=1e-7)
        for n in g0:
            assert torch.allclose(g[n], g0[n], atol=1e-7, rtol=1e-5), (micro, n)
    # the same rows split into two "groups" with the batch-global T give the same gradient
    a, b = slice(0, 2), slice(2, 5)
    split = [(seq[a], cmask[a], adv[a], old[a], None, plen, None), (seq[b], cmask[b], adv[b], old[b], None, plen, None)]
    t, g = _v1_backward(model, pol, split, n_tok, None)
    assert t == pytest.approx(t0, abs=1e-7)
    for n in g0:
        assert torch.allclose(g[n], g0[n], atol=1e-7, rtol=1e-5)
    # and the model gradient equals autograd of the hand-written masked loss with the reference's mask
    model.zero_grad(set_to_none=True)
    lp = completion_logprobs(pol, seq, plen)
    m = torch.zeros_like(cmask)
    for i in range(seq.shape[0]):
        ratios = torch.exp(cur[i].double() - old[i].double()).tolist()
        m[i] = torch.tensor(ref.trust_region_mask(ratios)).bool() & cmask[i]
    (-(lp * adv[:, None] * m).sum() / n_tok).backward()
    for n, p in model.named_parameters():
        if p.grad is not None:
            assert torch.allclose(g0[n], p.grad, atol=1e-7, rtol=1e-5)


# 5-9. trainer-level runs ----------------------------------------------------------------------------------------
class _Wrap:
    """Sampler wrapper for fixtures: optional empty completions or a synthetic rollout_lp (a stand-in vLLM)."""

    def __init__(self, inner, empty=False, rollout_shift=None, policy=None):
        self.inner, self.empty, self.shift, self.policy = inner, empty, rollout_shift, policy

    def sample(self, prompts, k, max_new, temperature, generator=None):
        rolls = self.inner.sample(prompts, k, max_new, temperature, generator)
        for p, r in zip(prompts, rolls):
            if self.empty:
                r.cmask = torch.zeros_like(r.cmask)
            if self.shift is not None:
                with torch.no_grad():
                    lp = completion_logprobs(self.policy, r.seq, len(p))
                r.rollout_lp = lp + self.shift.to(lp.dtype)[None, : lp.shape[1]]
        return rolls


def _run_v1(monkeypatch, tmp_path, name, scripts, k=4, steps=1, ppo_epochs=1, lr=0.01, bf16=False,
            fp32_master=False, wrap=None, **extra):
    rec = {"logprob_calls": 0, "groups": []}
    real_lp, real_make, real_build = train.chunked_logprobs, train.rollout.make_sampler, train.build_model
    real_bg = train.backward_objective_v1
    holder = {}

    def lp(pol, seq, plen, micro):
        rec["logprob_calls"] += 1
        return real_lp(pol, seq, plen, micro)

    def bg(pol, group, *a, **kw):
        rec["groups"].append(tuple(group[0][0, :group[5]].tolist()))
        return real_bg(pol, group, *a, **kw)

    def build(mcfg, device):
        pol, tok = real_build(mcfg, device)
        if bf16:
            pol.model.to(torch.bfloat16)
        holder["policy"] = pol
        return pol, tok

    def make(*a, **kw):
        s = _PromptSeeded(real_make(*a, **kw))
        return _Wrap(s, policy=holder["policy"], **(wrap or {})) if wrap else s

    monkeypatch.setattr(train, "chunked_logprobs", lp)
    monkeypatch.setattr(train, "backward_objective_v1", bg)
    monkeypatch.setattr(train, "build_model", build)
    monkeypatch.setattr(train.rollout, "make_sampler", make)
    monkeypatch.setattr(train, "build_task", lambda tcfg, tok, seed: ScriptedTask(scripts))
    monkeypatch.setattr(torch.optim, "AdamW", _RecAdamW)
    _RecAdamW.made = []
    cfg = {"seed": 1234, "device": "cpu", "out_dir": str(tmp_path / name), "verbose": False,
           "model": {"kind": "tiny_olmoe", "config": dict(_TINY)}, "task": {"kind": "scripted"},
           "train": {"algo": V1, "steps": steps, "prompts_per_step": len(scripts), "k": k, "max_new": 3,
                     "temperature": 1.0, "lr": lr, "ppo_epochs": ppo_epochs, "kl_coef": 0.0,
                     "eval_every": 100, "eval_k": 2, "sampler": "policy", "fp32_master": fp32_master, **extra}}
    summary = train.train(cfg)
    recs = [json.loads(x) for x in (tmp_path / name / "metrics.jsonl").read_text().splitlines()]
    return summary, _RecAdamW.made[0], recs, rec


def test_v1_trainer_mixed_group_updates_stored_weights(monkeypatch, tmp_path):
    s, opt, recs, rec = _run_v1(monkeypatch, tmp_path, "m",
                                {ALL_PASS: [1, 1, 1, 1], ALL_FAIL: [0, 0, 0, 0], MIXED: [0, 1, 0, 1]})
    r = recs[0]
    assert r["group_kinds"] == {"all_one": 1, "all_zero": 1, "tied_other": 0, "singleton": 0, "mixed": 1}
    assert r["groups_used"] == 1 and r["groups_dropped"] == 2 and rec["groups"] == [MIXED]
    assert rec["logprob_calls"] == 1  # old log-probs only for the kept group; no reference policy exists
    assert r["optimizer_stepped"] and opt.n_steps == 1 and r["tokens"] == 4 * 3
    assert r["ratio_source"] == "old_lp" and r["masked_frac"] == 0.0  # fresh rollouts, epoch 1: ratio is 1
    assert r["stored_update_share"] > 0 and s["trainable_weight_change"]["share_changed"] > 0
    assert "kl" not in r and "clip_frac" not in r and s["objective"]["name"] == V1
    assert r["passes"] == 6 and r["rollouts"] == 12
    assert math.isfinite(r["loss"]) and r["grad_norm"] > 0


def test_v1_adding_a_dropped_group_leaves_the_update_unchanged(monkeypatch, tmp_path):
    mixed = {MIXED: [0, 1, 0, 1], MIXED_B: [1, 1, 0, 0]}
    s0, o0, r0, _ = _run_v1(monkeypatch, tmp_path, "d0", dict(mixed), ppo_epochs=2)
    s1, o1, r1, rec1 = _run_v1(monkeypatch, tmp_path, "d1", {**mixed, ALL_PASS: [1, 1, 1, 1]}, ppo_epochs=2)
    assert r1[0]["groups_dropped"] == 1 and r0[0]["groups_dropped"] == 0 and ALL_PASS not in rec1["groups"]
    assert r0[0]["tokens"] == r1[0]["tokens"]  # the dropped group is not in the denominator
    assert r1[0]["loss"] == pytest.approx(r0[0]["loss"], abs=1e-7)
    for p0, p1 in zip(o0.params(), o1.params()):
        assert torch.allclose(p0, p1, atol=1e-7, rtol=0)
        for key in ("exp_avg", "exp_avg_sq"):
            assert torch.allclose(o0.state[p0][key], o1.state[p1][key], atol=1e-9, rtol=1e-5)


def test_v1_all_dropped_skips_the_optimizer_and_creates_no_state(monkeypatch, tmp_path):
    s, opt, recs, rec = _run_v1(monkeypatch, tmp_path, "z", {ALL_PASS: [1, 1, 1, 1], ALL_FAIL: [0, 0, 0, 0]},
                                steps=2)
    assert [r["groups_used"] for r in recs] == [0, 0] and not any(r["optimizer_stepped"] for r in recs)
    assert opt.n_steps == 0 and len(opt.state) == 0 and all(p.grad is None for p in opt.params())
    assert all(torch.equal(p, p0) for p, p0 in zip(opt.params(), opt.start))
    assert rec["logprob_calls"] == 0 and rec["groups"] == [] and s["trainable_weight_change"]["share_changed"] == 0
    assert s["objective"]["steps_with_optimizer_update"] == 0
    # singletons too
    s, opt, recs, rec = _run_v1(monkeypatch, tmp_path, "z1", {MIXED: [0, 1, 0, 1]}, k=1)
    assert recs[0]["group_kinds"]["singleton"] == 1 and opt.n_steps == 0 and len(opt.state) == 0


def test_v1_kept_groups_without_real_tokens_skip_the_optimizer(monkeypatch, tmp_path):
    s, opt, recs, rec = _run_v1(monkeypatch, tmp_path, "e", {MIXED: [0, 1, 0, 1]}, wrap={"empty": True})
    assert recs[0]["groups_used"] == 1 and recs[0]["tokens"] == 0 and not recs[0]["optimizer_stepped"]
    assert opt.n_steps == 0 and len(opt.state) == 0 and all(p.grad is None for p in opt.params())


def test_v1_ratio_uses_the_sampler_logprobs_when_present(monkeypatch, tmp_path):
    # stand-in sampler whose log-prob of token 0 is log(1.5) higher than the trainer's: ratio 1/1.5 < 0.8 -> masked
    shift = torch.tensor([math.log(1.5), 0.0, 0.0])
    s, opt, recs, rec = _run_v1(monkeypatch, tmp_path, "r", {MIXED: [0, 1, 0, 1]}, wrap={"rollout_shift": shift})
    r = recs[0]
    assert r["ratio_source"] == "rollout_lp" and r["tokens"] == 12 and r["tokens_inside"] == 8
    assert r["masked_frac"] == pytest.approx(4 / 12, abs=1e-6) and r["masked_frac_pos"] == pytest.approx(1 / 3)
    assert r["masked_frac_neg"] == pytest.approx(1 / 3) and "mismatch_k3" in r and opt.n_steps == 1


def test_v1_stale_epoch_masks_tokens_only_after_the_policy_moved(monkeypatch, tmp_path):
    s, opt, recs, rec = _run_v1(monkeypatch, tmp_path, "st", {MIXED: [0, 1, 0, 1], MIXED_B: [1, 0, 0, 1]},
                                ppo_epochs=3, lr=0.3, grad_clip=100.0)
    eps = recs[0]["epochs"]
    assert eps[0]["masked_frac"] == 0.0 and max(e["masked_frac"] for e in eps[1:]) > 0
    assert opt.n_steps == 3


def test_v1_refuses_silent_kl_or_importance_weighting(monkeypatch, tmp_path):
    for extra in ({"kl_coef": 0.1}, {"tis_clip": 2.0}):
        cfg = {"seed": 1, "device": "cpu", "out_dir": str(tmp_path / "x"), "verbose": False,
               "model": {"kind": "tiny_olmoe", "config": dict(_TINY)}, "task": {"kind": "toy"},
               "train": {"algo": V1, "steps": 1, "prompts_per_step": 1, "k": 2, "max_new": 2, "temperature": 1.0,
                         "lr": 0.01, **extra}}
        with pytest.raises(ValueError):
            train.train(cfg)


def test_v1_lost_bf16_update_is_detected_and_fp32_master_keeps_it(monkeypatch, tmp_path):
    scripts = {MIXED: [0, 1, 0, 1]}
    with pytest.raises(RuntimeError, match="lost update"):
        _run_v1(monkeypatch, tmp_path, "b0", scripts, lr=1e-9, bf16=True)
    s, opt, recs, _ = _run_v1(monkeypatch, tmp_path, "b1", scripts, lr=1e-9, bf16=True, fail_on_lost_update=False)
    r = recs[0]
    assert r["grad_norm"] > 0 and r["grad_nonzero_share"] > 0.5 and r["stored_update_share"] < 0.01
    s, opt, recs, _ = _run_v1(monkeypatch, tmp_path, "b2", scripts, lr=1e-9, bf16=True, fp32_master=True)
    r = recs[0]
    assert r["stored_update_share"] >= 0.5 * r["grad_nonzero_share"] > 0 and s["fp32_master_params"] > 0


# WP5 plumbing: parallel scoring, mixed-band screen, time cap, stdio task -----------------------------------------
def _toy_cfg(tmp_path, name, **train_extra):
    return {"seed": 1234, "device": "cpu", "out_dir": str(tmp_path / name), "verbose": False,
            "model": {"kind": "tiny_olmoe", "config": dict(_TINY)},
            "task": {"kind": "toy", "vocab": 16, "prompt_len": 4, "offset": 3, "n_train": 64, "n_heldout": 8},
            "train": {"algo": V1, "steps": 2, "prompts_per_step": 4, "k": 8, "max_new": 2, "temperature": 1.0,
                      "lr": 0.01, "eval_every": 100, "eval_k": 2, **train_extra}}


def test_parallel_scoring_gives_the_same_rewards_in_order():
    class T:
        def reward(self, p, c):
            return float(sum(c) % 3 == 0)
    pairs = [([1, 2], [i, i + 1, i * 2]) for i in range(50)]
    assert train.score_completions(T(), pairs, 8) == train.score_completions(T(), pairs, 1)


def test_screen_keeps_mixed_train_prompts_and_stops_on_no_go(tmp_path):
    s = train.train(_toy_cfg(tmp_path, "go", screen={"n": 32, "k": 8, "min_mixed": 1}, reward_workers=4))
    sc = json.loads((tmp_path / "go" / "screen.json").read_text())
    assert sc["n"] == 32 and sc["mixed"] >= 1 and sum(sc["histogram"].values()) == 32
    assert sc["mixed"] == sum(v for k_, v in sc["histogram"].items() if k_ not in ("0", "8"))
    assert "status" not in s and s["steps"] == 2
    evals = [json.loads(line) for line in (tmp_path / "go" / "evals.jsonl").read_text().splitlines()]
    fingerprints = {row["prompt_order_sha256"] for row in evals if row["name"] == "heldout"}
    assert len(fingerprints) == 1 and len(fingerprints.pop()) == 64
    s = train.train(_toy_cfg(tmp_path, "nogo", screen={"n": 32, "k": 8, "min_mixed": 33}))
    assert s["status"] == "NO_GO_MIXED_BAND" and (tmp_path / "nogo" / "metrics.jsonl").read_text() == ""


def test_max_train_seconds_stops_and_still_evaluates_where_it_stopped(tmp_path):
    s = train.train(_toy_cfg(tmp_path, "cap", steps=50, max_train_seconds=0.0))
    assert s["steps"] == 1 and s["steps_planned"] == 50 and [c[0] for c in s["heldout_curve"]] == [0, 1]


def test_stdio_task_scores_a_program_with_the_rl_data_checker(tmp_path, monkeypatch):
    monkeypatch.setenv("G10_STDIO_RUNNER", "local_unisolated")  # trusted fixture program
    rec = {"id": "fx-1", "kind": "stdio", "statement": "fixture: add two numbers", "time_limit_s": 4,
           "tests": [{"input": "1 2\n", "output": "3\n"}, {"input": "5 7\n", "output": "12\n"}]}
    (tmp_path / "t.jsonl").write_text(json.dumps(rec) + "\n")
    (tmp_path / "tr.txt").write_text("fx-1\n")
    (tmp_path / "ho.txt").write_text("")

    class Tok:
        def apply_chat_template(self, msgs, add_generation_prompt, tokenize):
            return [ord(ch) % 50 for ch in msgs[0]["content"]]

        def decode(self, ids, skip_special_tokens=True):
            return "".join(chr(i) for i in ids)
    config = {"tasks": str(tmp_path / "t.jsonl"), "train_ids": str(tmp_path / "tr.txt"),
              "heldout_ids": str(tmp_path / "ho.txt"), "require_verifier": True}
    task = train.stdio_task(config, Tok())
    good = "```python\na, b = map(int, input().split())\nprint(a + b)\n```"
    bad = good.replace("a + b", "a - b")
    p = task.train[0]
    assert task.reward(p, [ord(c) for c in good]) == 1.0 and task.reward(p, [ord(c) for c in bad]) == 0.0

    class Pool:
        startup_fails = False

        def score(self, samples):
            if len(samples) == 2 and not self.startup_fails:
                assert all(record["id"] == "stdio-preflight" for record, _ in samples)
                return [{"reward": 1}, {"reward": 0, "reason": "wrong answer on a test"}]
            return [{"reward": 0, "reason": "runner exited with 125"} for _ in samples]

    pool = Pool()
    pooled_task = train.stdio_task(config, Tok(), pool)
    with pytest.raises(RuntimeError, match="stdio verifier runner failed: runner exited with 125"):
        train.score_completions(pooled_task, [(p, [ord(c) for c in good])])
    pool.startup_fails = True
    with pytest.raises(RuntimeError, match="stdio verifier runner failed: runner exited with 125"):
        train.stdio_task(config, Tok(), pool)


def test_dense_qwen2_model_trains_attention_only_with_objective_v1(tmp_path, monkeypatch):
    from transformers import Qwen2Config, Qwen2ForCausalLM
    from policy import hf_policy

    def build(mcfg, device):
        torch.manual_seed(0)
        cfg = Qwen2Config(vocab_size=16, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4,
                          num_key_value_heads=2, max_position_embeddings=64, eos_token_id=None, bos_token_id=None,
                          pad_token_id=None)
        return hf_policy(Qwen2ForCausalLM(cfg), None, device), None
    monkeypatch.setattr(train, "build_model", build)
    cfg = _toy_cfg(tmp_path, "dense", steps=3, trainable=[r"\.self_attn\."])
    cfg["model"] = {"kind": "hf", "dense": True}
    with pytest.raises(ValueError, match="router"):  # without the explicit flag a dense model is still refused
        train.train({**cfg, "model": {"kind": "hf"}})
    s = train.train(cfg)
    assert s["router_unchanged"] and s["router_params_frozen"] == []
    assert s["trainable_weight_change"]["share_changed"] > 0 and s["objective"]["steps_with_optimizer_update"] >= 1


def test_v1_rejects_non_finite_real_tokens_and_ignores_padding():
    adv = torch.tensor([0.5, -0.5])
    real = torch.ones(2, 1, dtype=torch.bool)
    for new, samp in (([[float("nan")], [-1.0]], [[-1.0], [-1.0]]), ([[-1.0], [-1.0]], [[float("-inf")], [-1.0]]),
                      ([[float("inf")], [-1.0]], [[-1.0], [-1.0]]),
                      ([[0.0], [-1.0]], [[-1000.0], [-1.0]])):
        with pytest.raises(ValueError, match="non-finite"):
            grpo.objective_v1_loss(torch.tensor(new), torch.tensor(samp), adv, real)
        _, st = grpo.objective_v1_terms(torch.tensor(new), torch.tensor(samp), adv, real)
        assert int(st["nonfinite"]) == 1
    # NaN only in padding: accepted, same value as without it
    new = torch.tensor([[-1.0, float("nan")], [-2.0, float("nan")]])
    samp = torch.tensor([[-1.0, float("nan")], [-2.0, float("inf")]])
    pad = torch.tensor([[True, False], [True, False]])
    loss, st = grpo.objective_v1_loss(new, samp, adv, pad)
    want = ref.objective_v1([[ref.Rollout(1.0, (-1.0,), (1.0,)), ref.Rollout(0.0, (-2.0,), (1.0,))]])
    assert int(st["nonfinite"]) == 0 and float(loss) == pytest.approx(want.loss)


def test_v1_trainer_stops_before_the_optimizer_on_a_non_finite_current_logprob(monkeypatch, tmp_path):
    real_lp = train.completion_logprobs

    def nan_lp(pol, seq, plen):
        lp = real_lp(pol, seq, plen)
        return lp + torch.where(torch.arange(lp.shape[1]) == 0, float("nan"), 0.0)[None] if lp.requires_grad else lp
    monkeypatch.setattr(train, "completion_logprobs", nan_lp)
    with pytest.raises(ValueError, match="non-finite current"):
        _run_v1(monkeypatch, tmp_path, "nan", {MIXED: [0, 1, 0, 1]})
    assert _RecAdamW.made[0].n_steps == 0 and len(_RecAdamW.made[0].state) == 0
