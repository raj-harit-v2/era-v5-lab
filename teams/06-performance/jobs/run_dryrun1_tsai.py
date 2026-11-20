"""Job wrapper: G6 dryrun1_tsai, the dry run 1 profile on the lab GPU, for the TSAI lab column of
results/profile_dryrun1.md and results/speed_dryrun1.md.

Same model, config and commands as the G6 member-GPU runs (configs/g5_t2_base.yaml: dry run 1 model, loop dispatch,
loop Muon, torch kernels; synthetic data; B=8), run from teams/06-performance:
  1. prof: perfkit.bench --modes clean,layer,trace --level 3 --repeat 2          -> out/prof/
  2. ckpt: perfkit.bench --modes clean,checkpoint --level 1                      -> out/ckpt/
  3. nsys: jobs/run_dryrun1_nsys.py, 5 untraced warmup + 3 traced steps         -> out/nsys/ (skipped if no nsys)
If B=8 runs out of GPU memory (peak about 44 GiB on an A100), prof retries at B=4, 2, 1 and ckpt and nsys use the
batch that fitted; out/result.json records it.

Writes only under --out. Deletes the large files at the end (full torch.profiler traces, checkpoint files, the nsys
SQLite export), so out/ stays under 50 MB: run JSONs and reports, part traces, the .nsys-rep, nsys stats CSVs, logs.

Usage from repo root:
  # CPU smoke (no GPU, no nsys): tiny model, a few steps, same three steps
  python -B teams/06-performance/jobs/run_dryrun1_tsai.py --smoke-cpu

  # TSAI 1-GPU command
  python -B teams/06-performance/jobs/run_dryrun1_tsai.py --out out
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

PERF_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PERF_DIR.parents[1]
CONFIG = "configs/g5_t2_base.yaml"
BATCHES = (8, 4, 2, 1)
OOM = ("out of memory", "OutOfMemoryError")
REPEAT_DONE = (0, 2)    # perfkit --repeat: 0 PASS, 2 the 5% check failed (data for the tables, not a job failure)


def _commit() -> str:
    p = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else os.environ.get("PERF_COMMIT", "unknown")


def _run(cmd: list, log: Path, env: dict) -> tuple:
    """Run cmd from teams/06-performance, tee its output to log; return (exit code, wall s, output)."""
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    lines = []
    with log.open("w") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        p = subprocess.Popen(cmd, cwd=str(PERF_DIR), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True)
        for line in p.stdout:
            sys.stdout.write(line)
            f.write(line)
            lines.append(line)
        code = p.wait()
    return code, round(time.perf_counter() - t0, 1), "".join(lines)


def _size_mb(path: Path) -> float:
    return round(sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 2**20, 1) if path.exists() else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="out")
    ap.add_argument("--smoke-cpu", action="store_true", help="CPU smoke: configs/tiny_cpu.yaml, few steps, no nsys")
    ap.add_argument("--skip-nsys", action="store_true")
    a = ap.parse_args()

    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    commit = _commit()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1", "PERF_COMMIT": commit,
           "ERA_PERF_CACHE": str(out / "cache")}
    py = [sys.executable, "-B"]
    if a.smoke_cpu:
        config, batches = "configs/tiny_cpu.yaml", (2,)
        short = ["--steps", "3", "--warmup", "1"]
    else:
        config, batches, short = CONFIG, BATCHES, []
    base = ["--config", config, "data.source=synthetic"]
    result = {"job": "dryrun1_tsai", "commit": commit, "config": config, "python": platform.python_version(),
              "steps": {}}
    smi = shutil.which("nvidia-smi")
    if smi:
        (out / "nvidia-smi.txt").write_text(subprocess.run([smi], capture_output=True, text=True).stdout)

    # 1. prof: the profile, repeated in a new process for the 5% check; first batch that fits
    batch = None
    for b in batches:
        code, wall, text = _run(py + ["-m", "perfkit.bench", *base, "--modes", "clean,layer,trace", "--level", "3",
                                      "--repeat", "2", "--tag", f"dryrun1_tsai_b{b}", f"bench.out_dir={out / 'prof'}",
                                      f"run.batch_size={b}", *short], out / "logs" / f"prof_b{b}.log", env)
        result["steps"][f"prof_b{b}"] = {"exit": code, "wall_s": wall}
        if code in REPEAT_DONE or not any(s in text for s in OOM):
            batch = b
            break
    result["batch_size"] = batch
    if batch is None or result["steps"][f"prof_b{batch}"]["exit"] not in REPEAT_DONE:
        (out / "result.json").write_text(json.dumps(result, indent=1))
        print("[dryrun1_tsai] prof failed; ckpt and nsys not run", flush=True)
        return 1

    # 2. ckpt: full-size checkpoint save (model + optimizer state) into out/cache, deleted below
    code, wall, _ = _run(py + ["-m", "perfkit.bench", *base, "--modes", "clean,checkpoint", "--level", "1",
                               "--tag", f"dryrun1_tsai_ckpt_b{batch}", f"bench.out_dir={out / 'ckpt'}",
                               f"run.batch_size={batch}", *short], out / "logs" / f"ckpt_b{batch}.log",
                         {**env, "ERA_PERF_CACHE": str(out / "cache_ckpt")})
    result["steps"]["ckpt"] = {"exit": code, "wall_s": wall}

    # 3. nsys: Nsight Systems capture, only where nsys exists
    nsys = os.environ.get("NSYS") or shutil.which("nsys")
    if a.smoke_cpu or a.skip_nsys or not nsys:
        result["steps"]["nsys"] = {"exit": None, "note": "skipped: " + ("smoke-cpu" if a.smoke_cpu else
                                   "--skip-nsys" if a.skip_nsys else "nsys not on PATH and NSYS not set")}
    else:
        code, wall, _ = _run(py + ["jobs/run_dryrun1_nsys.py", "--config", config, "--synthetic",
                                   "--tag", f"dryrun1_tsai_nsys_b{batch}", "--out", str(out / "nsys"),
                                   f"run.batch_size={batch}"], out / "logs" / f"nsys_b{batch}.log", env)
        result["steps"]["nsys"] = {"exit": code, "wall_s": wall}

    # keep out/ small: full traces, checkpoint files and the nsys SQLite are large and not needed for the tables
    for p in (out / "cache", out / "cache_ckpt"):
        shutil.rmtree(p, ignore_errors=True)
    for p in (out / "nsys").glob("*.sqlite"):
        p.unlink()
    result["out_mb"] = _size_mb(out)
    (out / "result.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
    return 0 if result["steps"]["ckpt"]["exit"] == 0 and result["steps"]["nsys"]["exit"] in (0, None) else 1


if __name__ == "__main__":
    sys.exit(main())
