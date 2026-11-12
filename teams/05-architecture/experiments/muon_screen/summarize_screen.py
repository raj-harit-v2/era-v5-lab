"""Summarise the Muon screen (plan_v1): three T1 runs, muon_lr 1e-3, 1e-2, 1e-1, seed 1234.

Reads the run folders written by harness/train_week2.py (manifest.json, summary.json,
metrics.jsonl, and losses.txt if present). Checks each run, then prints the final held-out
bits per byte per rate (three-group, whole file, English, code, Indic mean), the NaN check,
and which Indic slices were scored. Writes the same numbers to a JSON file.
Standard library only. It does not change any run file.

The screen is one seed, so it never names a winner: can_win is always false. It reports the
rate with the lowest three-group bpb only when all three runs pass every check and have the
three-group, code and Indic values. plan_v1 uses that rate for the exp2-muon arm.

Usage (from the repository root):
    python teams/05-architecture/experiments/muon_screen/summarize_screen.py RUN_1e-3 RUN_1e-2 RUN_1e-1 \
        --heldout-sha256 <sha256 of the held-out file the job used> \
        --json teams/05-architecture/experiments/muon_screen/screen_summary.json

--smoke-ok accepts CPU smoke folders, only to test this script. Its output is marked NOT A RESULT.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

RATES = (0.001, 0.01, 0.1)
ADAMW_LR = 0.001  # AdamW rate for the embedding projection, head and norm gains (t1.yaml)
SEED = 1234
STEPS = 245
MAX_TIME_MIN = 30
INDIC = ("hi", "bn", "ta", "te", "kn", "ml", "mr", "gu", "pa", "or", "as")
SLICES = ("en", "code", "math", "sci", *INDIC)
KEYS = {
    "three_group_bpb": "val/three_group_bpb",
    "bpb_whole_file": "val/bpb",
    "english_bpb": "val/groups/english_bpb",
    "code_bpb": "val/groups/code_bpb",
    "indic_mean_bpb": "val/groups/indic_mean_bpb",
}
NEEDED = ("three_group_bpb", "code_bpb", "indic_mean_bpb")


def numbers(obj, prefix=""):
    """Yield (path, value) for every number inside a parsed JSON object."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from numbers(v, f"{prefix}{k}.")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from numbers(v, f"{prefix}[{i}].")
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield prefix.rstrip("."), obj


def check_run(run: Path, smoke_ok: bool, expected_heldout: str | None):
    errors, notes = [], []
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf8"))
    summary = json.loads((run / "summary.json").read_text(encoding="utf8"))
    rows = [json.loads(line) for line in (run / "metrics.jsonl").read_text(encoding="utf8").splitlines() if line.strip()]
    losses_file = run / "losses.txt"
    if losses_file.exists():
        losses = [float.fromhex(v) for v in losses_file.read_text(encoding="utf8").split()]
    else:
        losses = [r["loss_ntp"] for r in rows if r.get("step", 0) >= 1 and "loss_ntp" in r]
    cfg = manifest["config"]
    opt = cfg["optim"]
    rate = opt.get("muon_lr")
    smoke = bool(manifest.get("smoke"))

    # 1. Run identity: a Muon screen arm, seed 1234, a GPU bf16 run, the expected held-out file.
    if opt.get("name") != "muon":
        errors.append(f"optimizer is {opt.get('name')}, not muon")
    if rate not in RATES:
        errors.append(f"optim.muon_lr is {rate}, not one of {RATES}")
    if opt.get("lr") != ADAMW_LR:
        errors.append(f"optim.lr (AdamW part) is {opt.get('lr')}, not {ADAMW_LR}")
    if cfg["run"]["seed"] != SEED:
        errors.append(f"seed is {cfg['run']['seed']}, not {SEED}")
    if expected_heldout and manifest.get("heldout_sha256") != expected_heldout:
        errors.append(f"held-out sha256 is {manifest.get('heldout_sha256')}, not {expected_heldout} (given on the command line)")
    if not manifest.get("heldout_sources_sha256"):
        errors.append("no held-out slice sources: slice and three-group scores missing")
    if smoke:
        (notes if smoke_ok else errors).append("smoke run: NOT A RESULT")
    else:
        if manifest.get("device") != "cuda" or cfg["run"]["dtype"] != "bf16":
            errors.append(f"device {manifest.get('device')} dtype {cfg['run']['dtype']}: plan needs GPU bf16")
        if cfg["run"]["steps"] != STEPS or cfg["run"]["max_time_min"] != MAX_TIME_MIN:
            errors.append(f"budget {cfg['run']['steps']} steps / {cfg['run']['max_time_min']} min, plan is {STEPS} / {MAX_TIME_MIN}")
        if summary.get("status") != "COMPLETED" or summary.get("timed_out") or not summary.get("eligible_for_quality_comparison"):
            errors.append(f"status {summary.get('status')}, timed_out {summary.get('timed_out')}: not a result")

    # 2. Completion and NaN / inf: every number in metrics.jsonl and summary.json, and every training loss.
    if summary.get("steps") != cfg["run"]["steps"]:
        errors.append(f"reached step {summary.get('steps')} of {cfg['run']['steps']}")
    bad = [f"metrics step {r.get('step')}: {p}" for r in rows for p, x in numbers(r) if not math.isfinite(x)]
    bad += [f"summary: {p}" for p, x in numbers(summary) if not math.isfinite(x)]
    bad += [f"training loss at step {i + 1}" for i, x in enumerate(losses) if not math.isfinite(x)]
    if len(losses) != summary.get("steps"):
        errors.append(f"{len(losses)} logged training losses, run reached {summary.get('steps')} steps")
    if bad:
        errors.append("non-finite values: " + "; ".join(bad[:5]))

    # 3. Final held-out score: the eval row at the last step. Recompute bpb from nats and bytes.
    final = [r for r in rows if r.get("step") == summary.get("steps") and "val/bpb" in r]
    if len(final) != 1:
        errors.append(f"expected one held-out eval at step {summary.get('steps')}, found {len(final)}")
        return rate, None, errors, notes, manifest
    f = final[0]
    recomputed = f["val/nll_nats"] / math.log(2) / f["val/utf8_bytes"]
    if not math.isclose(recomputed, f["val/bpb"], rel_tol=1e-12):
        errors.append(f"val/bpb {f['val/bpb']} != nats/ln2/bytes {recomputed}")
    result = {
        "muon_lr": rate,
        "steps": summary.get("steps"),
        "wall_min": round(summary.get("wall_seconds", 0) / 60, 2),
        "first_train_ce": summary.get("first_ce"),
        "last_train_ce": summary.get("last_ce"),
        "train_scored_tokens": sum(r.get("train/scored_tokens", 0) for r in rows),
        "val_scored_tokens": f.get("val/scored_tokens"),
        "utf8_bytes": f.get("val/utf8_bytes"),
        "nll_nats": f.get("val/nll_nats"),
        "nan_or_inf": bool(bad),
        "heldout_sha256": manifest.get("heldout_sha256"),
        "heldout_documents": manifest.get("heldout_documents"),
        "final_model_sha256": summary.get("final_model_sha256"),
        "gpu": manifest.get("gpu"),
        "torch": manifest.get("torch"),
    }
    for name, key in KEYS.items():
        result[name] = f.get(key)
    result["slices_bpb"] = {s: f[f"val/slices/{s}/bpb"] for s in SLICES if f"val/slices/{s}/bpb" in f}
    result["indic_slices_scored"] = [s for s in INDIC if s in result["slices_bpb"]]
    result["indic_slices_missing"] = [s for s in INDIC if s not in result["slices_bpb"]]
    for name in NEEDED:
        if result[name] is None:
            errors.append(f"{KEYS[name]} missing from the final eval row")
    return rate, result, errors, notes, manifest


def same_setup(manifests):
    """The three runs must differ only in optim.muon_lr, the arm name and the arm's own file."""
    errors = []

    def strip(m):
        c = json.loads(json.dumps(m["config"]))
        c["optim"].pop("muon_lr", None)
        c.get("intended", {}).pop("arm", None)
        c.get("intended", {}).get("lead_intent", {}).pop("arm", None)
        prov = c.get("provenance", {})
        if "arm_sources" in prov:  # keep the shared parent (t1.yaml) in the comparison
            prov["arm_sources"] = [s for s in prov["arm_sources"] if "muon_screen/" not in s.get("path", "")]
        return {"config": c, "sources": m.get("sources"), "artifacts": m.get("artifacts"),
                "train_sha256": m.get("train_sha256"), "heldout_sha256": m.get("heldout_sha256"),
                "torch": m.get("torch")}

    base = strip(manifests[0])
    for m in manifests[1:]:
        other = strip(m)
        for k in base:
            if base[k] != other[k]:
                errors.append(f"muon_lr {m['config']['optim'].get('muon_lr')} differs from "
                              f"muon_lr {manifests[0]['config']['optim'].get('muon_lr')} in {k}")
    return errors


def fmt(x, d=4):
    return "n/a" if x is None else f"{x:.{d}f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path, help="one train_week2.py output folder per Muon rate")
    ap.add_argument("--json", type=Path, help="write the summary here")
    ap.add_argument("--heldout-sha256", help="expected sha256 of the held-out file the job scored on")
    ap.add_argument("--heldout-sha256-file", type=Path, help="or a sha256 file whose first field is the expected hash")
    ap.add_argument("--smoke-ok", action="store_true", help="test this script on CPU smoke folders; output is NOT A RESULT")
    a = ap.parse_args()

    expected = a.heldout_sha256
    if a.heldout_sha256_file:
        expected = a.heldout_sha256_file.read_text(encoding="utf8").split()[0]
    if expected is None:
        print("NOTE: no expected held-out sha256 given; the held-out file is not checked against a hash.\n")

    per_rate, problems, manifests, smoke = {}, {}, [], False
    for run in a.runs:
        rate, result, errors, notes, manifest = check_run(run, a.smoke_ok, expected)
        smoke |= bool(manifest.get("smoke"))
        if rate in per_rate:
            errors = errors + [f"second folder for muon_lr {rate}: {run}"]
        manifests.append(manifest)
        if errors:
            problems.setdefault(str(rate), []).extend(errors)
        if result is not None and rate not in per_rate:
            result.update(run_dir=str(run), counted=not errors, notes=notes)
            per_rate[rate] = result
    setup_errors = same_setup(manifests) if len(manifests) > 1 else []
    if setup_errors:
        for r in per_rate.values():
            r["counted"] = False

    missing = [r for r in RATES if r not in per_rate]
    counted = [per_rate[r] for r in RATES if r in per_rate and per_rate[r]["counted"]]
    complete = len(counted) == len(RATES) and all(r[n] is not None for r in counted for n in NEEDED)
    lowest = min(counted, key=lambda r: r["three_group_bpb"])["muon_lr"] if complete and not smoke else None
    agg = {
        "rates_counted": [r["muon_lr"] for r in counted],
        "lowest_three_group_muon_lr": lowest,
        "can_win": False,  # one seed: a screen, never a winner (plan_v1)
        "any_nan_or_inf": any(r["nan_or_inf"] for r in per_rate.values()),
        "indic_slices_missing": sorted({s for r in per_rate.values() for s in r["indic_slices_missing"]}),
    }

    clean = not problems and not setup_errors
    if smoke and a.smoke_ok:
        status = "SMOKE TEST OF THIS SCRIPT - NOT A RESULT" + ("" if clean else " - CHECK FAILED")
    else:
        status = "OK" if clean and not missing else "CHECK FAILED"
    out = {"arm": "muon-screen", "seed": SEED, "status": status,
           "per_rate": {str(k): v for k, v in per_rate.items()}, "aggregate": agg,
           "problems": problems, "setup_errors": setup_errors, "missing_rates": missing}

    print(f"Muon screen (seed {SEED}, T1) - {status}\n")
    print("| muon_lr | steps | wall min | three-group bpb | whole-file bpb | English | code | Indic mean | last train CE | NaN/inf | counted |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for rate in RATES:
        if rate not in per_rate:
            continue
        r = per_rate[rate]
        print(f"| {rate:g} | {r['steps']} | {r['wall_min']} | {fmt(r['three_group_bpb'])} | {fmt(r['bpb_whole_file'])} | "
              f"{fmt(r['english_bpb'])} | {fmt(r['code_bpb'])} | {fmt(r['indic_mean_bpb'])} | {fmt(r['last_train_ce'], 3)} | "
              f"{'yes' if r['nan_or_inf'] else 'no'} | {'yes' if r['counted'] else 'no'} |")
    print()
    print(f"Rates counted: {[f'{x:g}' for x in agg['rates_counted']]}  (missing: {[f'{x:g}' for x in missing] or 'none'})")
    if agg["indic_slices_missing"]:
        print(f"Indic slices not in the held-out file: {agg['indic_slices_missing']} (the Indic mean covers the rest)")
    if lowest is not None:
        print(f"Lowest three-group bpb: muon_lr {lowest:g}. One seed, so a screen choice for exp2-muon, not a winner.")
    elif smoke:
        print("Lowest three-group bpb: not reported for smoke runs.")
    else:
        print("Lowest three-group bpb: not reported (needs all three runs to pass with three-group, code and Indic values).")
    print(f"Any NaN/inf: {'yes' if agg['any_nan_or_inf'] else 'no'}.  Can win: no (one seed).")
    for k, errs in problems.items():
        for e in errs:
            print(f"PROBLEM muon_lr {k}: {e}")
    for e in setup_errors:
        print(f"PROBLEM setup: {e}")
    if a.json:
        a.json.write_text(json.dumps(out, indent=2) + "\n", encoding="utf8")
        print(f"\nwrote {a.json}")
    return 0 if not status.endswith("CHECK FAILED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
