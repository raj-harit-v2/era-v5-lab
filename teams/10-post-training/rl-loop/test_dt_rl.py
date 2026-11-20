"""Deletion Tuning as the RL method (train.dt): only mask logits train, base weights never change, state resumes.

Toy task, tiny random OLMoE, CPU. Fixtures, not training data.
"""
import copy
import json
import sys
from pathlib import Path

import pytest
import torch
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import train  # noqa: E402

TIMING = {"times_s", "step_s", "seconds", "rollout_tokens_per_s", "peak_torch_gb", "gpu_used_gb", "gpu_total_gb"}


def cfg_dt(out: Path, steps: int) -> dict:
    cfg = yaml.safe_load((HERE / "config" / "smoke_objective_v1.yaml").read_text())
    cfg["out_dir"] = str(out)
    cfg["verbose"] = False
    cfg["train"].update(steps=steps, eval_every=4, state_every=2, state_dir=str(out / "state"), ppo_epochs=1, lr=0.01,
                        dt={"targets": "attn", "alpha_start": 5.0, "alpha_end": 50.0, "eta": 0.05, "calib_prompts": 8,
                            "alpha_steps": 8})
    return cfg


def rows(out: Path, name: str) -> list[dict]:
    return [{k: v for k, v in json.loads(line).items() if k not in TIMING}
            for line in (out / name).read_text().splitlines()]


def final_state(out: Path) -> dict:
    latest = json.loads((out / "state" / "LATEST.json").read_text())
    return torch.load(out / "state" / latest["file"], map_location="cpu", weights_only=False)


def test_dt_trains_only_mask_logits_and_reports_deletions(tmp_path):
    s = train.train(cfg_dt(tmp_path / "run", 8))
    d = s["deletion_tuning"]
    assert d["masked_layers"] > 0 and d["optimizer_steps"] == s["objective"]["steps_with_optimizer_update"]
    assert d["wanda_prior"]["prior_deleted"] > 0
    assert 0.0 <= d["band_at_init"]["band_share"] <= d["band_at_init"]["live_share"] <= 1.0
    assert 0 < d["deletion_final"]["deleted_frac_of_targeted"] < 1
    st = final_state(tmp_path / "run")
    assert st["trainable"] and all(n.endswith(".gate") for n in st["trainable"])  # nothing but logits is trainable
    assert st["dt_steps"] == d["optimizer_steps"]
    assert s["router_unchanged"]
    recs = rows(tmp_path / "run", "metrics.jsonl")
    stepped = [r for r in recs if r.get("optimizer_stepped")]
    assert stepped and all("dt_deleted" in r and r["dt_alpha"] >= 5.0 for r in stepped)
    assert stepped[-1]["dt_alpha"] > stepped[0]["dt_alpha"]  # the sharpness schedule advances with optimizer steps
    assert s["trainable_weight_change"]["share_changed"] > 0


def test_dt_base_weights_are_bitwise_unchanged(tmp_path, monkeypatch):
    seen = {}
    real_convert = None

    def spy(model, *a, **kw):
        seen["before"] = {n: p.detach().clone() for n, p in model.named_parameters()}
        seen["model"] = model
        return real_convert(model, *a, **kw)

    dt = train.load_dt()
    real_convert = dt.convert
    monkeypatch.setattr(dt, "convert", spy)
    monkeypatch.setattr(train, "load_dt", lambda: dt)
    train.train(cfg_dt(tmp_path / "run", 6))
    after = dict(seen["model"].named_parameters())
    assert any(n.endswith(".gate") for n in after)
    for n, p in seen["before"].items():
        assert torch.equal(p, after[n].detach()), n  # every pretrained tensor, routers included


def test_dt_stop_and_continue_equals_uninterrupted(tmp_path):
    whole = train.train(cfg_dt(tmp_path / "whole", 8))
    cfg = cfg_dt(tmp_path / "split", 8)
    cfg["train"]["max_steps_this_call"] = 3
    assert train.train(copy.deepcopy(cfg))["status"] == "PAUSED_AT_DEADLINE"
    del cfg["train"]["max_steps_this_call"]
    done = train.train(copy.deepcopy(cfg))
    assert done["status"] == "COMPLETE" and done["resumed_from_step"] == 3
    assert rows(tmp_path / "whole", "metrics.jsonl") == rows(tmp_path / "split", "metrics.jsonl")
    assert rows(tmp_path / "whole", "evals.jsonl") == rows(tmp_path / "split", "evals.jsonl")
    a, b = final_state(tmp_path / "whole"), final_state(tmp_path / "split")
    assert a["dt_steps"] == b["dt_steps"] > 0
    for n in a["trainable"]:
        assert torch.equal(a["trainable"][n], b["trainable"][n]), n
    assert whole["deletion_tuning"]["deletion_final"] == done["deletion_tuning"]["deletion_final"]


def test_dt_refuses_other_algorithms_and_trainable_patterns(tmp_path):
    cfg = cfg_dt(tmp_path / "a", 2)
    cfg["train"]["algo"] = "dr_grpo"
    with pytest.raises(ValueError, match="train.dt"):
        train.train(cfg)
    cfg = cfg_dt(tmp_path / "b", 2)
    cfg["train"]["trainable"] = ["attn"]
    with pytest.raises(ValueError, match="train.dt"):
        train.train(cfg)


# --- E7 (16 Nov 2026): constant sharpness and the mask-dynamics / soft-vs-hard logging ----------------------------

def _one_layer(alpha_start: float, alpha_end: float, total: int = 10):
    dt = train.load_dt()
    net = torch.nn.Sequential(torch.nn.Linear(4, 3, bias=False))
    dt.convert(net, ["0"], alpha_start, alpha_end, total, seed=0)
    return dt, net, dt.masked_layers(net)[0][1]


def test_constant_alpha_schedule_stays_constant_and_lambda_decay_is_unchanged():
    dt, net, m = _one_layer(1000.0, 1000.0, total=100)
    seen = []
    for _ in range(25):
        seen.append(m.alpha)
        dt.step_all(net)
    assert seen == [1000.0] * 25
    # the regulariser's decay depends on alpha_steps only, so E7 keeps E4b's lambda schedule exactly
    assert [dt.lambda_at(s, 100, 1e-5) for s in (0, 6, 20)] == [1e-5, 1e-5 * 0.94, 1e-5 * 0.8]


def test_flip_counts_and_band_stats_are_exact_on_known_logits():
    dt, net, m = _one_layer(10.0, 10.0)
    with torch.no_grad():
        m.gate.copy_(torch.tensor([[0.5, -0.5, 0.01, -0.01], [5.0, -5.0, 0.2, -0.2], [0.0, 3.0, -3.0, 0.05]]))
    prev = dt.keep_masks(net)
    with torch.no_grad():  # 0.5 -> -0.5 (deleted), -0.5 -> 0.5 (restored), 0.01 -> -0.02 (deleted), 0.0 -> 0.1 (restored)
        m.gate[0, 0], m.gate[0, 1], m.gate[0, 2], m.gate[2, 0] = -0.5, 0.5, -0.02, 0.1
    counts, now = dt.flip_counts(net, prev)
    assert counts == {"newly_deleted": 2, "restored": 2}
    assert torch.equal(now[0], m.gate > 0)
    assert dt.flip_counts(net, now)[0] == {"newly_deleted": 0, "restored": 0}
    b = dt.band_stats(net, edge=1e-3)
    s = torch.sigmoid(10.0 * m.gate.detach())
    assert b["band_share"] == pytest.approx(float(((s > 1e-3) & (s < 1 - 1e-3)).float().mean()))
    assert b["live_share"] == pytest.approx(float((s * (1 - s) > 0).float().mean()))
    assert b["soft_hard_gap"] == pytest.approx(float((s - (m.gate > 0).float()).abs().mean()), rel=1e-6)


def test_soft_hard_terms_match_hand_numbers():
    soft = torch.tensor([[-1.0, -2.0, -0.5, 0.0]])
    hard = torch.tensor([[-1.0, -1.5, -0.8, -9.0]])
    cmask = torch.tensor([[True, True, True, False]])  # the last position is padding and must not count
    t = train.soft_hard_terms(soft, hard, cmask, 0.2)
    r = torch.tensor([0.0, -0.5, 0.3])
    assert float(t["sh_k3_sum"]) == pytest.approx(float((torch.exp(r) - 1 - r).sum()), rel=1e-6)
    assert float(t["sh_abs_sum"]) == pytest.approx(0.8, rel=1e-6)
    assert int(t["sh_outside"]) == 2  # exp(-0.5) = 0.61 and exp(0.3) = 1.35 are outside [0.8, 1.2]


def _dt_const(out: Path, alpha: float, steps: int = 6) -> dict:
    cfg = cfg_dt(out, steps)
    cfg["train"]["dt"].update(alpha_start=alpha, alpha_end=alpha)
    return cfg


def test_dt_constant_alpha_run_logs_flips_band_and_soft_hard_gap(tmp_path):
    s = train.train(_dt_const(tmp_path / "run", 5.0))
    d = s["deletion_tuning"]
    assert d["alpha"] == [5.0, 5.0] and d["alpha_final"] == 5.0
    recs = [r for r in rows(tmp_path / "run", "metrics.jsonl") if r.get("optimizer_stepped")]
    assert recs and all(r["dt_alpha"] == 5.0 for r in recs)
    prev = d["deletion_at_init"]["deleted"]
    for r in recs:  # the net change of the deleted count is exactly newly deleted minus restored
        assert r["dt_deleted"] - prev == r["dt_newly_deleted"] - r["dt_restored"]
        prev = r["dt_deleted"]
        assert 0 <= r["dt_band_share"] <= r["dt_live_share"] <= 1
        assert r["sh_k3"] >= 0 and r["sh_abs_logratio"] >= 0 and 0 <= r["sh_outside_frac"] <= 1
        assert 0 < r["dt_soft_hard_gap"] < 0.5
    assert prev == d["deletion_final"]["deleted"]
    assert sum(r["dt_newly_deleted"] + r["dt_restored"] for r in recs) > 0  # lr 0.01 at alpha 5 does flip logits


def test_soft_hard_gap_shrinks_as_the_mask_sharpens(tmp_path):
    train.train(_dt_const(tmp_path / "lo", 5.0, steps=2))
    train.train(_dt_const(tmp_path / "hi", 1.0e6, steps=2))
    first = lambda name: [r for r in rows(tmp_path / name, "metrics.jsonl") if r.get("optimizer_stepped")][0]  # noqa: E731
    a, b = first("lo"), first("hi")
    assert a["dt_soft_hard_gap"] > 100 * b["dt_soft_hard_gap"]
    assert a["sh_abs_logratio"] > b["sh_abs_logratio"]
    assert b["dt_band_share"] < a["dt_band_share"]


def test_non_dt_objective_v1_rows_have_no_dt_or_soft_hard_keys(tmp_path):
    cfg = cfg_dt(tmp_path / "run", 2)
    del cfg["train"]["dt"]
    train.train(cfg)
    for r in rows(tmp_path / "run", "metrics.jsonl"):
        assert not any(k.startswith(("sh_", "dt_")) for k in r)


def test_soft_hard_outside_share_equals_trust_region_mask_when_the_sampler_is_hard_masked(tmp_path):
    """With the CPU policy sampler the ratio denominator is the trainer's own hard-mask log-prob, so the tokens the
    trust region drops are exactly those whose soft/hard ratio leaves [1 - eps, 1 + eps]. A small eps makes it bite."""
    cfg = _dt_const(tmp_path / "run", 1.0, steps=3)
    cfg["train"]["tr_epsilon"] = 0.01
    train.train(cfg)
    recs = [r for r in rows(tmp_path / "run", "metrics.jsonl") if r.get("optimizer_stepped")]
    assert recs and all(r["ratio_source"] == "old_lp" for r in recs)
    assert all(r["sh_outside_frac"] == r["masked_frac"] for r in recs)
    assert any(r["masked_frac"] > 0.1 for r in recs)


def test_dt_default_alpha_matches_paper_repo_100_to_1000(tmp_path):
    cfg = cfg_dt(tmp_path / "run", 1)
    cfg["train"]["dt"] = {"targets": "attn", "eta": 0.05, "calib_prompts": 8, "alpha_steps": 4}
    s = train.train(cfg)
    assert s["deletion_tuning"]["alpha"] == [100.0, 1000.0]
    assert 0.0 <= s["deletion_tuning"]["band_at_init"]["band_share"] <= 1.0
