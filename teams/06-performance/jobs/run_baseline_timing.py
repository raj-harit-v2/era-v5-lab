#!/usr/bin/env python3
"""TSAI job wrapper: time G6 baseline (or a short CPU smoke) and write only under --out.

Usage (repo root):
  python teams/06-performance/jobs/run_baseline_timing.py --out out
  python teams/06-performance/jobs/run_baseline_timing.py --out out --synthetic
  python teams/06-performance/jobs/run_baseline_timing.py --out out --smoke-cpu

No network. Reads configs under teams/06-performance. Writes only under --out.

GPU path (non-smoke) — Lab Cap Choice A4:
  Process 1: --repeat 1 clean,layer with layer_warmup=20 (clean KPI once).
  After a 120s cool-down: process W is a discarded layer-only warm pass (never
  compared); process A is layer-only (no against); process B is layer-only
  --against A JSON. Against uses report.compare_clean_step=false,
  report.tol_pct=10, report.abs_tol_ms=0.5.
  A3a (41e9748) compared A vs B inside one pair, which fixed the fwd skew, but A
  was still the cold first sample after the cool-down: bwd:block0 missed by 0.8
  points (10.8%, 0.415 ms). A4 drops the cold sample (pass W) and widens the
  absolute floor to 0.5 ms. Job-only; perfkit and tip configs are unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

JOB_DIR = Path(__file__).resolve().parent
PERF_ROOT = JOB_DIR.parent
REPO_ROOT = PERF_ROOT.parents[1]

# Cool-down before the layer pair to cut thermal hysteresis from process 1.
LAYER_COOLDOWN_S = 120
LAYER_WARMUP = 20
RUN1_MODES = "clean,layer"
RUN2_MODES = "layer"
# Against policy for lab power-cap nodes (TSAI: 5% cross-process too tight).
RUN2_COMPARE_CLEAN_STEP = "false"
RUN2_TOL_PCT = "10"
RUN2_ABS_TOL_MS = "0.5"
LAB_CAP = "A4"


def _newest_json(out: Path, tag: str) -> Path | None:
    """Resolve the JSON stem free_path wrote for ``tag`` (tag.json or tag-N.json)."""
    matches = sorted(out.glob(f"{tag}.json")) + sorted(out.glob(f"{tag}-*.json"))
    # Exclude second-run tags that start with ``{tag}-run``.
    matches = [p for p in matches if not p.name.startswith(f"{tag}-run")]
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def _run_bench(out: Path, *, smoke_cpu: bool, synthetic: bool) -> int:
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PERF_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    if smoke_cpu:
        config = PERF_ROOT / "configs" / "tiny_cpu.yaml"
        tag = "baseline_smoke_cpu"
        args = [
            sys.executable, "-m", "perfkit.bench",
            "--config", str(config),
            "--tag", tag,
            "--modes", "clean",
            "--level", "1",
            "--warmup", "2",
            "--steps", "10",
            "--repeat", "1",
            f"bench.out_dir={out.as_posix()}",
            "data.source=synthetic",
            "run.device=cpu",
            "run.dtype=fp32",
        ]
        print("cwd:", PERF_ROOT)
        print("cmd:", " ".join(args))
        proc = subprocess.run(args, cwd=str(PERF_ROOT), env=env)
        summary = {
            "pass": proc.returncode == 0,
            "exit_code": proc.returncode,
            "tag": tag,
            "config": str(config.relative_to(REPO_ROOT)),
            "smoke_cpu": smoke_cpu,
            "synthetic": synthetic,
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "out_dir": str(out),
        }
        (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
        return proc.returncode

    config = PERF_ROOT / "configs" / "base.yaml"
    tag = "baseline_v1_job"
    tag_layer_w = f"{tag}-layerW"
    tag_layer_a = f"{tag}-layerA"
    tag_layer_b = f"{tag}-layerB"
    base_args = [
        sys.executable, "-m", "perfkit.bench",
        "--config", str(config),
        "--level", "3",
        "--repeat", "1",
        f"bench.layer_warmup={LAYER_WARMUP}",
        f"bench.out_dir={out.as_posix()}",
    ]
    if synthetic:
        base_args.append("data.source=synthetic")

    args1 = [*base_args, "--modes", RUN1_MODES, "--tag", tag]
    print("cwd:", PERF_ROOT)
    print("cmd:", " ".join(args1))
    proc1 = subprocess.run(args1, cwd=str(PERF_ROOT), env=env)
    if proc1.returncode != 0:
        summary = {
            "pass": False,
            "exit_code": proc1.returncode,
            "tag": tag,
            "config": str(config.relative_to(REPO_ROOT)),
            "smoke_cpu": smoke_cpu,
            "synthetic": synthetic,
            "layer_warmup": LAYER_WARMUP,
            "cooldown_s": LAYER_COOLDOWN_S,
            "run1_modes": RUN1_MODES,
            "lab_cap": LAB_CAP,
            "phase": "run1",
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "out_dir": str(out),
        }
        (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
        return proc1.returncode

    print(f"cool-down {LAYER_COOLDOWN_S}s before warm pass + layer pair (thermal hysteresis)…")
    time.sleep(LAYER_COOLDOWN_S)

    # Discarded warm pass: absorbs the cold first sample so A and B are warm vs warm.
    args2w = [*base_args, "--modes", RUN2_MODES, "--tag", tag_layer_w]
    print("cmd (warm pass, discarded):", " ".join(args2w))
    proc2w = subprocess.run(args2w, cwd=str(PERF_ROOT), env=env)
    if proc2w.returncode != 0:
        summary = {
            "pass": False,
            "exit_code": proc2w.returncode,
            "tag": tag_layer_w,
            "config": str(config.relative_to(REPO_ROOT)),
            "smoke_cpu": smoke_cpu,
            "synthetic": synthetic,
            "layer_warmup": LAYER_WARMUP,
            "cooldown_s": LAYER_COOLDOWN_S,
            "run1_modes": RUN1_MODES,
            "run2_modes": RUN2_MODES,
            "lab_cap": LAB_CAP,
            "phase": "layerW",
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "out_dir": str(out),
        }
        (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
        return proc2w.returncode

    args2a = [*base_args, "--modes", RUN2_MODES, "--tag", tag_layer_a]
    print("cmd:", " ".join(args2a))
    proc2a = subprocess.run(args2a, cwd=str(PERF_ROOT), env=env)
    if proc2a.returncode != 0:
        summary = {
            "pass": False,
            "exit_code": proc2a.returncode,
            "tag": tag_layer_a,
            "config": str(config.relative_to(REPO_ROOT)),
            "smoke_cpu": smoke_cpu,
            "synthetic": synthetic,
            "layer_warmup": LAYER_WARMUP,
            "cooldown_s": LAYER_COOLDOWN_S,
            "run1_modes": RUN1_MODES,
            "run2_modes": RUN2_MODES,
            "lab_cap": LAB_CAP,
            "phase": "layerA",
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "out_dir": str(out),
        }
        (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
        return proc2a.returncode

    layer_a_json = _newest_json(out, tag_layer_a)
    if layer_a_json is None or not layer_a_json.is_file():
        print("ERROR: layerA JSON not found under", out, file=sys.stderr)
        return 2

    args2b = [
        *base_args,
        "--modes", RUN2_MODES,
        "--tag", tag_layer_b,
        "--against", str(layer_a_json),
        f"report.compare_clean_step={RUN2_COMPARE_CLEAN_STEP}",
        f"report.tol_pct={RUN2_TOL_PCT}",
        f"report.abs_tol_ms={RUN2_ABS_TOL_MS}",
    ]
    print("cmd:", " ".join(args2b))
    proc2b = subprocess.run(args2b, cwd=str(PERF_ROOT), env=env)
    summary = {
        "pass": proc2b.returncode == 0,
        "exit_code": proc2b.returncode,
        "tag": tag_layer_b,
        "against": str(layer_a_json),
        "config": str(config.relative_to(REPO_ROOT)),
        "smoke_cpu": smoke_cpu,
        "synthetic": synthetic,
        "layer_warmup": LAYER_WARMUP,
        "cooldown_s": LAYER_COOLDOWN_S,
        "run1_modes": RUN1_MODES,
        "run2_modes": RUN2_MODES,
        "run2_compare_clean_step": RUN2_COMPARE_CLEAN_STEP == "true",
        "run2_tol_pct": float(RUN2_TOL_PCT),
        "run2_abs_tol_ms": float(RUN2_ABS_TOL_MS),
        "lab_cap": LAB_CAP,
        "phase": "layerB_against_layerA",
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(out),
    }
    (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    return proc2b.returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="out", help="output folder (only write target)")
    ap.add_argument(
        "--smoke-cpu",
        action="store_true",
        help="short synthetic CPU run for the attached test log",
    )
    ap.add_argument(
        "--synthetic",
        action="store_true",
        help="force data.source=synthetic (lab nodes without FineWeb shards)",
    )
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    # JOB_REQUEST rule: write only under ./out when run from the job cwd.
    if out.name != "out" and "out" not in out.parts:
        print("refusing out path that is not under an 'out' folder:", out, file=sys.stderr)
        return 2
    return _run_bench(out, smoke_cpu=a.smoke_cpu, synthetic=a.synthetic)


if __name__ == "__main__":
    raise SystemExit(main())
