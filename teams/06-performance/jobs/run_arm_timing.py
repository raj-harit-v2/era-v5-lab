#!/usr/bin/env python3
"""TSAI job wrapper: time one G5 Architecture arm config (clean x2) or a short CPU smoke.

Usage (repo root):
  python teams/06-performance/jobs/run_arm_timing.py --out out --synthetic \\
      --config teams/05-architecture/configs/arms/t1.yaml
  python teams/06-performance/jobs/run_arm_timing.py --out out --smoke-cpu \\
      --config teams/05-architecture/configs/arms/t1.yaml

No network. Reads the given --config (and G6 configs for smoke). Writes only under --out.

GPU path (non-smoke): one discarded warm clean, then clean mode level 3 --repeat 2.
No Lab Cap layer pair. --config is required on the GPU path.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

JOB_DIR = Path(__file__).resolve().parent
PERF_ROOT = JOB_DIR.parent
REPO_ROOT = PERF_ROOT.parents[1]

GPU_MODES = "clean"
GPU_LEVEL = "3"
GPU_REPEAT = "2"
GPU_TAG = "arm_v1_job"
GPU_WARM_TAG = "arm_v1_job-warm"


def _resolve_config(raw: str) -> Path:
    p = Path(raw)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    return p


def _run_bench(out: Path, *, smoke_cpu: bool, synthetic: bool, config_arg: str | None) -> int:
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PERF_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    if smoke_cpu:
        config = PERF_ROOT / "configs" / "tiny_cpu.yaml"
        tag = "arm_smoke_cpu"
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
        if config_arg:
            print("note: --config ignored for --smoke-cpu; using tiny_cpu.yaml")
        proc = subprocess.run(args, cwd=str(PERF_ROOT), env=env)
        summary = {
            "pass": proc.returncode == 0,
            "exit_code": proc.returncode,
            "tag": tag,
            "config": str(config.relative_to(REPO_ROOT)),
            "requested_config": config_arg,
            "smoke_cpu": True,
            "synthetic": True,
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "out_dir": str(out),
        }
        (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
        return proc.returncode

    if not config_arg:
        print("ERROR: --config is required for the GPU path (arms/tN.yaml).", file=sys.stderr)
        return 2

    config = _resolve_config(config_arg)
    if not config.is_file():
        print("ERROR: config not found:", config, file=sys.stderr)
        return 2

    try:
        config_rel = str(config.relative_to(REPO_ROOT))
    except ValueError:
        config_rel = str(config)

    base_args = [
        sys.executable, "-m", "perfkit.bench",
        "--config", str(config),
        "--modes", GPU_MODES,
        "--level", GPU_LEVEL,
        f"bench.out_dir={out.as_posix()}",
    ]
    if synthetic:
        base_args.append("data.source=synthetic")

    # Discarded warm clean: absorbs cold first sample after a prior job (t1 8.6% gap).
    args_warm = [*base_args, "--tag", GPU_WARM_TAG, "--repeat", "1"]
    print("cwd:", PERF_ROOT)
    print("cmd (warm, discarded):", " ".join(args_warm))
    proc_w = subprocess.run(args_warm, cwd=str(PERF_ROOT), env=env)
    if proc_w.returncode != 0:
        summary = {
            "pass": False,
            "exit_code": proc_w.returncode,
            "tag": GPU_WARM_TAG,
            "config": config_rel,
            "smoke_cpu": False,
            "synthetic": synthetic,
            "modes": GPU_MODES,
            "level": int(GPU_LEVEL),
            "phase": "warm",
            "lab_cap": None,
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "out_dir": str(out),
        }
        (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
        return proc_w.returncode

    args = [*base_args, "--tag", GPU_TAG, "--repeat", GPU_REPEAT]
    print("cmd:", " ".join(args))
    proc = subprocess.run(args, cwd=str(PERF_ROOT), env=env)
    summary = {
        "pass": proc.returncode == 0,
        "exit_code": proc.returncode,
        "tag": GPU_TAG,
        "warm_tag": GPU_WARM_TAG,
        "config": config_rel,
        "smoke_cpu": False,
        "synthetic": synthetic,
        "modes": GPU_MODES,
        "level": int(GPU_LEVEL),
        "repeat": int(GPU_REPEAT),
        "lab_cap": None,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(out),
    }
    (out / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    return proc.returncode


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
    ap.add_argument(
        "--config",
        default=None,
        help="path to arms/tN.yaml (required unless --smoke-cpu)",
    )
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    if out.name != "out" and "out" not in out.parts:
        print("refusing out path that is not under an 'out' folder:", out, file=sys.stderr)
        return 2
    return _run_bench(out, smoke_cpu=a.smoke_cpu, synthetic=a.synthetic, config_arg=a.config)


if __name__ == "__main__":
    raise SystemExit(main())
