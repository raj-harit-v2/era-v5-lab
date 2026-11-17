#!/usr/bin/env python3
"""TSAI job wrapper: time G6 dry-run-1 MoE all-to-all (comm) with config_v1 settings.

Usage (from teams/06-performance or repo root):
  cd teams/06-performance
  # smoke-cpu (1 process, tiny model, comm payload recorded, timing marked not measured):
  python jobs/run_dryrun1_a2a.py --smoke-cpu --out ../../out
  # TSAI real run (2 GPUs via torchrun):
  python jobs/run_dryrun1_a2a.py --nproc 2 --out out

Config_v1 settings (#447 @ aec75af) applied as overrides on top of base.yaml.
Null/open model-size values (n_layer, d_model, n_head, d_ff, seq_len, precision) use base.yaml defaults.
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

# Config_v1 (#447 @ aec75af) non-null settings mapped to bench overrides.
# attention.impl=eager and moe.top_k=2 / moe.num_shared=1 already match base.yaml defaults.
CONFIG_V1_OVERRIDES = [
    "run.seed=1234",
    "optim.name=muon",
    "optim.lr=0.001",
    "model.moe.num_experts=16",
]

# Job-specific: MoE a2a shape per the template + instructions.
JOB_OVERRIDES = [
    "model.ffn=moe",
    "model.moe.dispatch=sorted",
]

TAG = "dryrun1_a2a"
TAG_SMOKE = "dryrun1_a2a_smoke_cpu"


def _run(args: list, cwd: str, env: dict) -> subprocess.CompletedProcess:
    print("cwd:", cwd)
    print("cmd:", " ".join(str(a) for a in args))
    return subprocess.run(args, cwd=cwd, env=env)


def _summary(*, passed: bool, exit_code: int, tag: str, smoke_cpu: bool, out: Path, **extra) -> dict:
    return {
        "pass": passed,
        "exit_code": exit_code,
        "tag": tag,
        "smoke_cpu": smoke_cpu,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(out),
        **extra,
    }


def run_job(out: Path, *, smoke_cpu: bool, nproc: int) -> int:
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PERF_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    if smoke_cpu:
        # Use tiny_cpu.yaml for fast smoke test.
        # WORLD_SIZE=1 → bench records payload + marks timing "not measured" → exit 0.
        config = PERF_ROOT / "configs" / "tiny_cpu.yaml"
        args = [
            sys.executable, "-m", "perfkit.bench",
            "--config", str(config),
            "--tag", TAG_SMOKE,
            "--modes", "comm",
            f"bench.out_dir={out.as_posix()}",
            "data.source=synthetic",
            "run.device=cpu",
            "run.dtype=fp32",
            "run.seed=1234",
            "optim.name=muon",
            "optim.lr=0.001",
            "model.ffn=moe",
            "model.moe.dispatch=sorted",
        ]
        proc = _run(args, cwd=str(PERF_ROOT), env=env)
        s = _summary(
            passed=proc.returncode == 0,
            exit_code=proc.returncode,
            tag=TAG_SMOKE,
            smoke_cpu=True,
            out=out,
            config=str(config.relative_to(REPO_ROOT)),
        )
        (out / "result.json").write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(s))
        return proc.returncode

    # TSAI GPU run: torchrun with nproc GPUs, base.yaml + config_v1 overrides.
    config = PERF_ROOT / "configs" / "base.yaml"
    args = [
        "torchrun", f"--nproc_per_node={nproc}",
        "-m", "perfkit.bench",
        "--config", str(config),
        "--tag", TAG,
        "--modes", "comm",
        f"bench.out_dir={out.as_posix()}",
        "data.source=synthetic",
        *CONFIG_V1_OVERRIDES,
        *JOB_OVERRIDES,
    ]
    proc = _run(args, cwd=str(PERF_ROOT), env=env)
    s = _summary(
        passed=proc.returncode == 0,
        exit_code=proc.returncode,
        tag=TAG,
        smoke_cpu=False,
        out=out,
        nproc=nproc,
        config=str(config.relative_to(REPO_ROOT)),
        config_v1_overrides=CONFIG_V1_OVERRIDES,
        job_overrides=JOB_OVERRIDES,
    )
    (out / "result.json").write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(s))
    return proc.returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="out", help="output folder (writes only here)")
    ap.add_argument("--smoke-cpu", action="store_true",
                    help="short CPU run for the attached test log (single process, tiny model)")
    ap.add_argument("--nproc", type=int, default=2,
                    help="--nproc_per_node for torchrun GPU run (default 2)")
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    if out.name != "out" and "out" not in out.parts:
        print("refusing out path not under 'out':", out, file=sys.stderr)
        return 2
    return run_job(out, smoke_cpu=a.smoke_cpu, nproc=a.nproc)


if __name__ == "__main__":
    raise SystemExit(main())
