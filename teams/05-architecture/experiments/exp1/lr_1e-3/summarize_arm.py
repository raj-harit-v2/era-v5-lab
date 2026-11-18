"""Summarise the exp1-lr-1e-3 seeds from the EXP-1 job output.

Reads the run folders written by harness/train_week2.py (manifest.json, summary.json,
metrics.jsonl, and losses.txt if present). Checks each run, then prints per-seed bits per byte,
the mean, the seed spread and the NaN check, and writes the same numbers to a JSON file.
Standard library only. It does not change any run file.

Usage (from the repository root):
    python teams/05-architecture/experiments/exp1/lr_1e-3/summarize_arm.py RUN_DIR [RUN_DIR ...] \
        --heldout-sha256 <TSAI published held-out sha256> \
        --json teams/05-architecture/experiments/exp1/lr_1e-3/arm_summary.json

--smoke-ok accepts CPU smoke folders, only to test this script. Its output is marked NOT A RESULT.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ARM_LR = 0.001
SEEDS = (1234, 1235, 1236)
STEPS = 245
MAX_TIME_MIN = 30
INDIC = ("hi", "bn", "ta", "te", "kn", "ml", "mr", "gu", "pa", "or", "as")
SLICES = ("en", "code", "math", "sci", *INDIC)
# Winner-rule metrics (plan_v1, TSAI 2 Nov): three-group mean decides; code and Indic mean are guards.
KEYS = {
    "three_group_bpb": "val/three_group_bpb",
    "bpb_whole_file": "val/bpb",
    "english_bpb": "val/groups/english_bpb",
    "code_bpb": "val/groups/code_bpb",
    "indic_mean_bpb": "val/groups/indic_mean_bpb",
}
SPREAD_KEYS = ("three_group_bpb", "code_bpb", "indic_mean_bpb", "bpb_whole_file")


def finite_numbers(obj):
    """Yield (path, value) for every number inside a parsed JSON object."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            for p, x in finite_numbers(v):
                yield f"{k}.{p}" if p else k, x
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for p, x in finite_numbers(v):
                yield f"[{i}].{p}" if p else f"[{i}]", x
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield "", obj


def check_run(run: Path, smoke_ok: bool, expected_heldout: str | None):
    errors, notes = [], []
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf8"))
    summary = json.loads((run / "summary.json").read_text(encoding="utf8"))
    rows = [json.loads(line) for line in (run / "metrics.jsonl").read_text(encoding="utf8").splitlines() if line.strip()]
    # The EXP-1 job returns only manifest, summary and metrics; then the losses come from metrics.jsonl.
    losses_file = run / "losses.txt"
    if losses_file.exists():
        losses = [float.fromhex(v) for v in losses_file.read_text(encoding="utf8").split()]
    else:
        losses = [r["loss_ntp"] for r in rows if r.get("step", 0) >= 1 and "loss_ntp" in r]
    cfg = manifest["config"]
    seed = cfg["run"]["seed"]

    # 1. Run identity: this arm, a real GPU bf16 run, the official held-out file.
    if cfg["optim"]["lr"] != ARM_LR:
        errors.append(f"optim.lr is {cfg['optim']['lr']}, not {ARM_LR}")
    if cfg["optim"].get("name") != "adamw":
        errors.append(f"optimizer is {cfg['optim'].get('name')}, not adamw")
    if manifest.get("smoke"):
        (notes if smoke_ok else errors).append("smoke run: NOT A RESULT")
    else:
        if manifest.get("device") != "cuda" or cfg["run"]["dtype"] != "bf16":
            errors.append(f"device {manifest.get('device')} dtype {cfg['run']['dtype']}: plan needs GPU bf16")
        if cfg["run"]["steps"] != STEPS or cfg["run"]["max_time_min"] != MAX_TIME_MIN:
            errors.append(f"budget {cfg['run']['steps']} steps / {cfg['run']['max_time_min']} min, plan is {STEPS} / {MAX_TIME_MIN}")
        if expected_heldout and manifest.get("heldout_sha256") != expected_heldout:
            errors.append(f"held-out sha256 {manifest.get('heldout_sha256')} does not match the expected {expected_heldout} given on the command line")
        if not manifest.get("heldout_sources_sha256"):
            errors.append("no held-out slice sources: slice and three-group scores missing")

    # 2. Completion: all steps inside the time cap.
    if not smoke_ok or not manifest.get("smoke"):
        if summary.get("status") != "COMPLETED" or summary.get("timed_out") or not summary.get("eligible_for_quality_comparison"):
            errors.append(f"status {summary.get('status')}, timed_out {summary.get('timed_out')}: not a result")
    if summary.get("steps") != cfg["run"]["steps"]:
        errors.append(f"reached step {summary.get('steps')} of {cfg['run']['steps']}")

    # 3. NaN / inf: every number in metrics.jsonl and summary.json, and every logged loss.
    bad = [f"metrics step {r.get('step')}: {p}" for r in rows for p, x in finite_numbers(r) if not math.isfinite(x)]
    bad += [f"summary: {p}" for p, x in finite_numbers(summary) if not math.isfinite(x)]
    bad += [f"training loss at step {i + 1}" for i, x in enumerate(losses) if not math.isfinite(x)]
    if len(losses) != summary.get("steps"):
        errors.append(f"{len(losses)} logged training losses, run reached {summary.get('steps')} steps")
    if bad:
        errors.append("non-finite values: " + "; ".join(bad[:5]))

    # 4. Final held-out score: the eval row at the last step. Recompute bpb from nats and bytes.
    final = [r for r in rows if r.get("step") == summary.get("steps") and "val/bpb" in r]
    if len(final) != 1:
        errors.append(f"expected one held-out eval at step {summary.get('steps')}, found {len(final)}")
        return seed, None, errors, notes, manifest
    f = final[0]
    recomputed = f["val/nll_nats"] / math.log(2) / f["val/utf8_bytes"]
    if not math.isclose(recomputed, f["val/bpb"], rel_tol=1e-12):
        errors.append(f"val/bpb {f['val/bpb']} != nats/ln2/bytes {recomputed}")
    result = {
        "seed": seed,
        "steps": summary["steps"],
        "wall_min": round(summary["wall_seconds"] / 60, 2),
        "first_train_ce": summary.get("first_ce"),
        "last_train_ce": summary.get("last_ce"),
        "scored_tokens": f["val/scored_tokens"],
        "utf8_bytes": f["val/utf8_bytes"],
        "nll_nats": f["val/nll_nats"],
        "nan_or_inf": bool(bad),
        "final_model_sha256": summary.get("final_model_sha256"),
        "gpu": manifest.get("gpu"),
        "torch": manifest.get("torch"),
    }
    for name, key in KEYS.items():
        result[name] = f.get(key)
    result["slices_bpb"] = {s: f[f"val/slices/{s}/bpb"] for s in SLICES if f"val/slices/{s}/bpb" in f}
    return seed, result, errors, notes, manifest


def same_setup(manifests):
    """Seeds must differ only in run.seed: same config, code, data and artifacts."""
    errors = []
    def strip(m):
        c = json.loads(json.dumps(m["config"]))
        c["run"].pop("seed", None)
        return {"config": c, "sources": m.get("sources"), "artifacts": m.get("artifacts"),
                "train_sha256": m.get("train_sha256"), "heldout_sha256": m.get("heldout_sha256"),
                "torch": m.get("torch")}
    base = strip(manifests[0])
    for m in manifests[1:]:
        other = strip(m)
        for k in base:
            if base[k] != other[k]:
                errors.append(f"seed {m['config']['run']['seed']} differs from seed {manifests[0]['config']['run']['seed']} in {k}")
    return errors


def fmt(x, d=4):
    return "n/a" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path, help="one train_week2.py output folder per seed")
    ap.add_argument("--json", type=Path, help="write the summary here")
    ap.add_argument("--heldout-sha256", help="expected held-out sha256 (the EXP-1 job uses TSAI's published v0-clean held-out)")
    ap.add_argument("--heldout-sha256-file", type=Path, help="or a sha256 file whose first field is the expected hash")
    ap.add_argument("--smoke-ok", action="store_true", help="test this script on CPU smoke folders; output is NOT A RESULT")
    a = ap.parse_args()

    expected = a.heldout_sha256
    if a.heldout_sha256_file:
        expected = a.heldout_sha256_file.read_text(encoding="utf8").split()[0]
    if expected is None:
        print("NOTE: no expected held-out sha256 given; the held-out file is not checked against a published hash.\n")

    per_seed, problems, manifests, smoke, repeats = {}, {}, [], False, []
    for run in a.runs:
        seed, result, errors, notes, manifest = check_run(run, a.smoke_ok, expected)
        smoke |= bool(manifest.get("smoke"))
        if seed in per_seed and a.smoke_ok and manifest.get("smoke"):
            # Smoke repeatability pair: same seed twice must give identical losses and weights.
            first = Path(per_seed[seed]["run_dir"])
            same = ((first / "losses.txt").read_bytes() == (run / "losses.txt").read_bytes()
                    and per_seed[seed]["final_model_sha256"] == (result or {}).get("final_model_sha256"))
            repeats.append(f"seed {seed}: {first.name} vs {run.name} identical losses and model sha: {'yes' if same else 'NO'}")
            if not same:
                problems.setdefault(seed, []).append(f"repeat run {run} differs from {first}")
            continue
        if seed in per_seed or seed in problems:
            problems.setdefault(seed, []).append(f"duplicate seed folder {run}")
        manifests.append(manifest)
        if errors:
            problems.setdefault(seed, []).extend(errors)
        if result is not None:
            result["run_dir"] = str(run)
            result["counted"] = not errors
            result["notes"] = notes
            per_seed[seed] = result
    setup_errors = same_setup(manifests) if len(manifests) > 1 else []
    if setup_errors:
        for r in per_seed.values():
            r["counted"] = False

    counted = [per_seed[s] for s in sorted(per_seed) if per_seed[s]["counted"] and not setup_errors]
    missing = [s for s in SEEDS if s not in per_seed] if not smoke else []
    agg = {"finished_seeds": [r["seed"] for r in counted]}
    for name in SPREAD_KEYS:
        vals = [r[name] for r in counted if r[name] is not None]
        agg[f"mean_{name}"] = math.fsum(vals) / len(vals) if vals else None
        agg[f"spread_{name}"] = (max(vals) - min(vals)) if len(vals) >= 2 else None
    # plan_v1: the winner rule needs the three-group mean and the code and Indic-mean guards on every counted seed.
    rule_keys = ("three_group_bpb", "code_bpb", "indic_mean_bpb")
    agg["rule_values_present"] = bool(counted) and all(r[k] is not None for r in counted for k in rule_keys)
    agg["can_win"] = len(counted) >= 2 and not smoke and agg["rule_values_present"]
    agg["any_nan_or_inf"] = any(r["nan_or_inf"] for r in per_seed.values())

    clean = not problems and not setup_errors
    if smoke and a.smoke_ok:
        status = "SMOKE TEST OF THIS SCRIPT - NOT A RESULT" + ("" if clean else " - CHECK FAILED")
    else:
        status = "OK" if clean and not missing else "CHECK FAILED"
    out = {"arm": "exp1-lr-1e-3", "optim_lr": ARM_LR, "status": status, "per_seed": per_seed,
           "aggregate": agg, "problems": {str(k): v for k, v in problems.items()},
           "setup_errors": setup_errors, "missing_seeds": missing, "smoke_repeats": repeats}

    print(f"exp1-lr-1e-3 (optim.lr {ARM_LR}) - {status}\n")
    print("| seed | steps | wall min | three-group bpb | whole-file bpb | English | code | Indic mean | NaN/inf | counted |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for s in sorted(per_seed):
        r = per_seed[s]
        print(f"| {s} | {r['steps']} | {r['wall_min']} | {fmt(r['three_group_bpb'])} | {fmt(r['bpb_whole_file'])} | "
              f"{fmt(r['english_bpb'])} | {fmt(r['code_bpb'])} | {fmt(r['indic_mean_bpb'])} | "
              f"{'yes' if r['nan_or_inf'] else 'no'} | {'yes' if r['counted'] else 'no'} |")
    print()
    print(f"Finished seeds: {agg['finished_seeds']}  (missing: {missing or 'none'})")
    for name in SPREAD_KEYS:
        print(f"{name}: mean {fmt(agg['mean_' + name])}, spread {fmt(agg['spread_' + name])}")
    print(f"Any NaN/inf: {'yes' if agg['any_nan_or_inf'] else 'no'}.  "
          f"Three-group, code and Indic-mean present on every counted seed: {'yes' if agg['rule_values_present'] else 'no'}.  "
          f"Can win (>= 2 finished seeds and those values): {'yes' if agg['can_win'] else 'no'}")
    for line in repeats:
        print(f"Repeat check {line}")
    for s, errs in problems.items():
        for e in errs:
            print(f"PROBLEM seed {s}: {e}")
    for e in setup_errors:
        print(f"PROBLEM setup: {e}")
    if a.json:
        a.json.write_text(json.dumps(out, indent=2) + "\n", encoding="utf8")
        print(f"\nwrote {a.json}")
    return 0 if not status.endswith("CHECK FAILED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
