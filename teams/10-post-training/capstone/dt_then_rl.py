"""Helpers for the "Deletion Tuning, then the small RL test" study (week-3 task 11): RL configs and the analysis.

    python capstone/dt_then_rl.py config --arm dt|lora|base --seed 1 --lr 1e-4 --steps 30 --sft-dir DIR --out RUN_DIR --adapter ADAPTER_YAML
    python capstone/dt_then_rl.py analyze --arm dt=DIR1,DIR2,DIR3 --arm lora=... --arm base=... [--json OUT]

The RL run itself is rl-loop/train.py (objective_v1, the toy task). `analyze` reads each run's evals.jsonl (per-prompt
held-out scores at every evaluation) and metrics.jsonl and gives, per arm: held-out reward first -> last with a paired
bootstrap over prompts (averaging each prompt's change over seeds), the arm-vs-arm paired difference, and per-step
means. Pairing requires evaluation rows with matching prompt-order fingerprints and evaluation endpoints.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rl-loop"))
import heldout  # noqa: E402


def make_config(arm: str, seed: int, lr: float, steps: int, sft_dir: Path | None, out: Path, adapter: Path,
                rule: str = "even", task_seed: int = 4242, n_heldout: int = 128, prompt_len: int = 32, max_new: int = 4,
                eval_every: int = 5, cohort_k: int = 0, trainable: str | None = None) -> dict:
    cfg = {"seed": seed, "device": "cpu", "out_dir": str(out), "verbose": False,
           "model": {"kind": "team5_adapter", "adapter_config": str(adapter), "allow_fixture_smoke": True,
                     "kv_cache": True},
           "task": {"kind": "toy", "vocab": 131072, "prompt_len": prompt_len, "rule": rule, "n_train": 64,
                    "n_heldout": n_heldout, "seed": task_seed},
           "train": {"algo": "objective_v1", "steps": steps, "prompts_per_step": 8, "k": 8, "max_new": max_new,
                     "temperature": 1.0, "lr": lr, "ppo_epochs": 1, "kl_coef": 0.0, "eval_every": eval_every,
                     "eval_k": 8, "sampler": "policy", "log_zero_share": True}}
    if arm in ("dt", "lora"):
        name = {"dt": "dt_markers", "lora": "lora_markers"}[arm]
        st = Path(sft_dir) / name
        cfg["model"]["init_state"] = str(st / "model.safetensors")
        if arm == "dt":
            cfg["train"]["keep_zero"] = {"path": str(st / "dt_keep_masks.bin")}
    elif arm != "base":
        raise ValueError(arm)
    if cohort_k:
        cfg["train"].update(cohort_eval_k=cohort_k, state_dir=str(out / "state"), state_every=eval_every)
    if trainable:
        cfg["_trainable_note"] = trainable
    return cfg


def read_evaluations(evals: list[dict], name: str, directory: Path) -> tuple[dict, str | None]:
    rows = [row for row in evals if row["name"] == name]
    if not rows:
        return {}, None
    digest = rows[0].get("prompt_order_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError(f"{directory}: {name} evaluations need a prompt_order_sha256 fingerprint")
    size = len(rows[0]["scores"])
    scores = {}
    for row in rows:
        step = row["step"]
        if row.get("prompt_order_sha256") != digest:
            raise ValueError(f"{directory}: {name} prompt order changed at step {step}")
        if not size or len(row["scores"]) != size:
            raise ValueError(f"{directory}: {name} score count is empty or changed at step {step}")
        if step in scores:
            raise ValueError(f"{directory}: duplicate {name} evaluation at step {step}")
        scores[step] = row["scores"]
    return scores, digest


def read_run(d: Path) -> dict:
    evals = [json.loads(x) for x in (d / "evals.jsonl").read_text().splitlines()]
    held, held_digest = read_evaluations(evals, "heldout", d)
    cohort, cohort_digest = read_evaluations(evals, "train_cohort", d)
    recs = [json.loads(x) for x in (d / "smoke_metrics.jsonl").read_text().splitlines()] if (
        d / "smoke_metrics.jsonl").exists() else [json.loads(x) for x in (d / "metrics.jsonl").read_text().splitlines()]
    sfile = d / "smoke_summary.json" if (d / "smoke_summary.json").exists() else d / "summary.json"
    return {"held": held, "held_digest": held_digest, "cohort": cohort, "cohort_digest": cohort_digest,
            "recs": recs, "summary": json.loads(sfile.read_text()) if sfile.exists() else {}}


def boot(delta: list[float], n: int = 10_000, seed: int = 0) -> dict:
    return heldout.paired_bootstrap([0.0] * len(delta), delta, n=n, seed=seed)


def aligned_steps(runs: list[dict], split: str) -> list[int]:
    steps = sorted(runs[0][split])
    if len(steps) < 2 or steps[0] != 0:
        raise ValueError(f"{split} needs evaluations at step 0 and a later step")
    digest_key = f"{split}_digest"
    size = len(runs[0][split][0])
    for run in runs[1:]:
        if sorted(run[split]) != steps:
            raise ValueError(f"runs of one arm have different {split} evaluation steps")
        if run[digest_key] != runs[0][digest_key] or len(run[split][0]) != size:
            raise ValueError(f"runs of one arm have different {split} prompts or prompt order")
    return steps


def arm_stats(dirs: list[Path]) -> dict:
    runs = [read_run(d) for d in dirs]
    steps = aligned_steps(runs, "held")
    first, last = steps[0], steps[-1]
    s0 = torch.tensor([r["held"][first] for r in runs], dtype=torch.float64)   # [seeds, prompts]
    s1 = torch.tensor([r["held"][last] for r in runs], dtype=torch.float64)
    per_prompt = (s1 - s0).mean(0)                                            # averaged over seeds
    per_seed = [round(float((b - a).mean()), 4) for a, b in zip(s0, s1)]
    curve = {int(s): round(float(torch.tensor([r["held"][s] for r in runs], dtype=torch.float64).mean()), 4) for s in steps}
    stepped = [[x for x in r["recs"] if x["step"] >= 1] for r in runs]

    def mean(key, only_stepped=False):
        vals = [x[key] for rr in stepped for x in rr if key in x and (not only_stepped or x.get("optimizer_stepped"))]
        return round(sum(vals) / len(vals), 4) if vals else None
    out = {"seeds": len(runs), "first_step": first, "last_step": last, "heldout_prompts": len(per_prompt),
           "prompt_order_sha256": runs[0]["held_digest"],
           "start": round(float(s0.mean()), 4), "end": round(float(s1.mean()), 4), "per_seed_change": per_seed,
           "change": boot(per_prompt.tolist()), "curve_mean_over_seeds": curve,
           "mean_groups_used_of_8": mean("groups_used"), "first3_mean_groups_used": round(sum(
               x["groups_used"] for rr in stepped for x in rr[:3]) / max(sum(len(rr[:3]) for rr in stepped), 1), 3),
           "mean_train_reward": mean("train_reward"), "mean_masked_frac": mean("masked_frac", True),
           "mean_stored_update_share": mean("stored_update_share", True),
           "mean_grad_nonzero_share": mean("grad_nonzero_share", True),
           "step1_stored_update_share": [rr[0].get("stored_update_share") for rr in stepped],
           "step1_grad_nonzero_share": [rr[0].get("grad_nonzero_share") for rr in stepped],
           "optimizer_steps": [sum(1 for x in rr if x.get("optimizer_stepped")) for rr in stepped],
           "zero_share_first_last": [[rr[0].get("zero_share"), rr[-1].get("zero_share")] for rr in stepped],
           "max_deleted_nonzero": max((x.get("deleted_nonzero", 0) for rr in stepped for x in rr), default=0)
           if any("deleted_nonzero" in x for rr in stepped for x in rr) else None,
           "run_seconds": [r["summary"].get("seconds") for r in runs],
           "mean_step_s": mean("step_s"),
           "keep_zero": runs[0]["summary"].get("keep_zero")}
    if all(r["cohort"] for r in runs):
        cohort_steps = aligned_steps(runs, "cohort")
        c0 = torch.tensor([r["cohort"][cohort_steps[0]] for r in runs], dtype=torch.float64)
        c1 = torch.tensor([r["cohort"][cohort_steps[-1]] for r in runs], dtype=torch.float64)
        out["train_cohort_change"] = boot((c1 - c0).mean(0).tolist())
    out["_per_prompt"] = per_prompt.tolist()
    return out


def analyze(arms: dict[str, list[Path]]) -> dict:
    res = {name: arm_stats(dirs) for name, dirs in arms.items()}
    names = list(res)
    res["_pairs"] = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if any(res[a][key] != res[b][key] for key in ("first_step", "last_step")):
                raise ValueError(f"{a} and {b} have different held-out evaluation endpoints")
            if any(res[a][key] != res[b][key] for key in ("heldout_prompts", "prompt_order_sha256")):
                raise ValueError(f"{a} and {b} have different held-out prompts or prompt order")
            d = [x - y for x, y in zip(res[a]["_per_prompt"], res[b]["_per_prompt"], strict=True)]
            ca, cb = res[a]["change"]["diff"], res[b]["change"]["diff"]
            res["_pairs"][f"{a}-{b}"] = {**boot(d), "change_a": ca, "change_b": cb,
                                         "ratio_a_over_b": round(ca / cb, 3) if abs(cb) > 1e-12 else None}
    for v in res.values():
        if isinstance(v, dict):
            v.pop("_per_prompt", None)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("config")
    c.add_argument("--arm", required=True, choices=("dt", "lora", "base"))
    c.add_argument("--seed", type=int, required=True)
    c.add_argument("--lr", type=float, required=True)
    c.add_argument("--steps", type=int, required=True)
    c.add_argument("--sft-dir", type=Path)
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--adapter", type=Path, required=True)
    c.add_argument("--rule", default="even")
    c.add_argument("--task-seed", type=int, default=4242)
    c.add_argument("--n-heldout", type=int, default=128)
    c.add_argument("--prompt-len", type=int, default=32)
    c.add_argument("--max-new", type=int, default=4)
    c.add_argument("--eval-every", type=int, default=5)
    c.add_argument("--cohort-k", type=int, default=0)
    c.add_argument("--write", type=Path, required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--arm", action="append", required=True, help="name=dir1,dir2,...")
    a.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "config":
        cfg = make_config(args.arm, args.seed, args.lr, args.steps, args.sft_dir, args.out, args.adapter, args.rule,
                          args.task_seed, args.n_heldout, args.prompt_len, args.max_new, args.eval_every, args.cohort_k)
        args.write.write_text(yaml.safe_dump(cfg, sort_keys=False))
        return 0
    arms = {x.split("=", 1)[0]: [Path(p) for p in x.split("=", 1)[1].split(",")] for x in args.arm}
    res = analyze(arms)
    text = json.dumps(res, indent=1)
    if args.json:
        args.json.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
