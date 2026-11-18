"""CLAUDE.md G10 GRPO review, once, on the Deletion-Tuned stand-in: real advantage function, real objective_v1 backward,
real AdamW, the real trainer with the deletion held (train.keep_zero).

    python capstone/dt_review.py --adapter-config adapter_b.yaml --init-state model.safetensors --keep-masks dt_keep_masks.bin \
        --out DIR

Checks (scripted rewards on four-token prompts, no text; the model is the real DT-SFT checkpoint, CPU fp32):
  1. constant, singleton and mixed groups through grpo.advantages: None, None, finite [-0.5, 0.5, -0.5, 0.5];
  2. a batch of {all-pass, all-fail, mixed}: one group kept, one optimizer step, the constant groups never reach the
     backward, the loss denominator counts only the mixed group's tokens, stored weights changed;
  3. adding a dropped (constant) group to two mixed groups leaves loss, weights and AdamW moments unchanged;
  4. an all-dropped batch (constant groups, then a singleton) never steps the optimizer, creates no state, leaves
     weights unchanged;
  5. in every run that stepped, deleted weights stay exactly 0 (the trainer's own per-step check, plus a final count).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import torch
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rl-loop"))
import grpo  # noqa: E402
import train  # noqa: E402
from test_rl_loop import ALL_FAIL, ALL_PASS, MIXED, MIXED_B, ScriptedTask, _PromptSeeded, _RecAdamW  # noqa: E402
from _pytest.monkeypatch import MonkeyPatch  # noqa: E402


def run(args, tmp: Path, name: str, scripts: dict, k=4, steps=1, ppo_epochs=1, lr=1e-4):
    mp = MonkeyPatch()
    rec = {"logprob_calls": 0, "groups": []}
    real_lp, real_make, real_bg = train.chunked_logprobs, train.rollout.make_sampler, train.backward_objective_v1

    def lp(pol, seq, plen, micro):
        rec["logprob_calls"] += 1
        return real_lp(pol, seq, plen, micro)

    def bg(pol, group, *a, **kw):
        rec["groups"].append(tuple(group[0][0, :group[5]].tolist()))
        return real_bg(pol, group, *a, **kw)

    mp.setattr(train, "chunked_logprobs", lp)
    mp.setattr(train, "backward_objective_v1", bg)
    mp.setattr(train.rollout, "make_sampler", lambda *a, **kw: _PromptSeeded(real_make(*a, **kw)))
    mp.setattr(train, "build_task", lambda tcfg, tok, seed: ScriptedTask(scripts))
    mp.setattr(torch.optim, "AdamW", _RecAdamW)
    _RecAdamW.made = []
    cfg = {"seed": 1234, "device": "cpu", "out_dir": str(tmp / name), "verbose": False,
           "model": {"kind": "team5_adapter", "adapter_config": str(args.adapter_config), "allow_fixture_smoke": True,
                     "kv_cache": True, "init_state": str(args.init_state)},
           "task": {"kind": "scripted"},
           "train": {"algo": "objective_v1", "steps": steps, "prompts_per_step": len(scripts), "k": k, "max_new": 3,
                     "temperature": 1.0, "lr": lr, "ppo_epochs": ppo_epochs, "kl_coef": 0.0, "eval_every": 100,
                     "eval_k": 2, "sampler": "policy", "keep_zero": {"path": str(args.keep_masks)}}}
    try:
        summary = train.train(cfg)
    finally:
        mp.undo()
    recs = [json.loads(x) for x in (tmp / name / "smoke_metrics.jsonl").read_text().splitlines()]
    return summary, _RecAdamW.made[0], recs, rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adapter-config", type=Path, required=True)
    ap.add_argument("--init-state", type=Path, required=True)
    ap.add_argument("--keep-masks", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    out: dict = {}
    t = torch.tensor
    out["advantages"] = {
        "constant_all_one": grpo.advantages(t([1.0] * 4), "objective_v1") is None,
        "constant_all_zero": grpo.advantages(t([0.0] * 4), "objective_v1") is None,
        "singleton": grpo.advantages(t([1.0]), "objective_v1") is None,
        "mixed": grpo.advantages(t([0.0, 1.0, 0.0, 1.0]), "objective_v1").tolist()}
    assert out["advantages"]["mixed"] == [-0.5, 0.5, -0.5, 0.5] and all(
        out["advantages"][k] for k in ("constant_all_one", "constant_all_zero", "singleton"))
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        s, opt, recs, rec = run(args, tmp, "m", {ALL_PASS: [1, 1, 1, 1], ALL_FAIL: [0, 0, 0, 0], MIXED: [0, 1, 0, 1]})
        r = recs[0]
        assert r["groups_used"] == 1 and r["groups_dropped"] == 2 and rec["groups"] == [MIXED]
        assert r["optimizer_stepped"] and opt.n_steps == 1 and r["tokens"] == 4 * 3 and r["masked_frac"] == 0.0
        assert r["deleted_nonzero"] == 0 and s["keep_zero"]["deleted_nonzero_end"] == 0
        moved = sum(int((p != p0).sum()) for p, p0 in zip(opt.params(), opt.start))
        assert moved > 0 and r["stored_update_share"] > 0 and torch.isfinite(t(r["loss"]))
        out["mixed_batch"] = {"groups_used": 1, "groups_dropped": 2, "tokens": r["tokens"], "optimizer_steps": 1,
                              "loss": r["loss"], "grad_norm": r["grad_norm"], "stored_update_share": r["stored_update_share"],
                              "grad_nonzero_share": r["grad_nonzero_share"], "weights_changed": moved,
                              "deleted_nonzero": r["deleted_nonzero"], "zero_share": r["zero_share"],
                              "deleted_at_start": s["keep_zero"]["deleted_at_start"]}
        mixed = {MIXED: [0, 1, 0, 1], MIXED_B: [1, 1, 0, 0]}
        _, o0, r0, _ = run(args, tmp, "d0", dict(mixed), ppo_epochs=2)
        _, o1, r1, rec1 = run(args, tmp, "d1", {**mixed, ALL_PASS: [1, 1, 1, 1]}, ppo_epochs=2)
        assert r1[0]["groups_dropped"] == 1 and ALL_PASS not in rec1["groups"] and r0[0]["tokens"] == r1[0]["tokens"]
        assert abs(r1[0]["loss"] - r0[0]["loss"]) <= 1e-7
        def drift(oa, ob, same_state=True):
            ww = mm = 0.0
            ns = 0
            for pa, pb in zip(oa.params(), ob.params()):
                ww = max(ww, float((pa.detach() - pb.detach()).abs().max()))
                # a parameter no routed token reached has no gradient, hence no AdamW state, in both runs or neither
                assert not same_state or (pa in oa.state) == (pb in ob.state)
                if pa in oa.state and pb in ob.state:
                    ns += 1
                    for key in ("exp_avg", "exp_avg_sq"):
                        mm = max(mm, float((oa.state[pa][key] - ob.state[pb][key]).abs().max()))
            return ww, mm, ns
        worst_w, worst_m, n_state = drift(o0, o1)
        # Group order is a random shuffle of the batch, so adding a group reorders the floating-point sums: expect
        # rounding-level differences (~1e-7), not exact equality. Sensitivity control: really removing a kept group
        # moves the weights by order of lr (1e-4); the tolerance below (1e-6) sits well between the two.
        _, o2, r2, _ = run(args, tmp, "d2", {MIXED: [0, 1, 0, 1]}, ppo_epochs=2)
        ctrl_w, ctrl_m, _ = drift(o0, o2, same_state=False)
        assert worst_w <= 1e-6 and worst_m <= 1e-7 and ctrl_w > 10 * worst_w
        out["dropped_group_invariance"] = {"loss_diff": abs(r1[0]["loss"] - r0[0]["loss"]), "max_weight_diff": worst_w,
                                           "max_moment_diff": worst_m, "params_with_state": n_state, "tokens": r0[0]["tokens"],
                                           "lr": 1e-4, "control_remove_a_kept_group_max_weight_diff": ctrl_w,
                                           "control_remove_a_kept_group_max_moment_diff": ctrl_m}
        _, opt, recs, rec = run(args, tmp, "z", {ALL_PASS: [1, 1, 1, 1], ALL_FAIL: [0, 0, 0, 0]}, steps=2)
        assert not any(x["optimizer_stepped"] for x in recs) and opt.n_steps == 0 and len(opt.state) == 0
        assert all(torch.equal(p, p0) for p, p0 in zip(opt.params(), opt.start)) and rec["logprob_calls"] == 0
        _, opt, recs, _ = run(args, tmp, "z1", {MIXED: [0, 1, 0, 1]}, k=1)
        assert recs[0]["group_kinds"]["singleton"] == 1 and opt.n_steps == 0 and len(opt.state) == 0
        out["all_dropped_batch"] = {"constant_groups_steps": 0, "singleton_steps": 0, "optimizer_state_entries": 0,
                                    "weights_unchanged": True, "logprob_calls": 0}
    out["pass"] = True
    (args.out / "dt_review.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
