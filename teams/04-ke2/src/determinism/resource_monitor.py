#!/usr/bin/env python3
"""Sample CPU, RAM and NVIDIA GPU use to a CSV while a long run goes on.

Every ``--interval`` seconds it records CPU use (all cores), RAM in use, the number and memory of Python processes,
and from ``nvidia-smi``: GPU and memory-controller utilization, VRAM in use, power, temperature, SM and memory
clocks and the active clock-limit reasons. It stops when ``--watch-pid`` exits or after ``--max-minutes``.

Usage:

    python resource_monitor.py --out results/decode_gpu/resources_raw_P32.csv --watch-pid <pid of decode_gpu.py>
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

GPU_FIELDS = (
    "utilization.gpu",
    "utilization.memory",
    "memory.used",
    "power.draw",
    "temperature.gpu",
    "clocks.sm",
    "clocks.mem",
    "clocks_event_reasons.active",
)
COLUMNS = (
    "elapsed_s",
    "utc",
    "cpu_percent",
    "ram_used_gib",
    "python_processes",
    "python_rss_gib",
    "gpu_util_percent",
    "gpu_memory_controller_percent",
    "vram_used_gib",
    "power_w",
    "temperature_c",
    "sm_clock_mhz",
    "memory_clock_mhz",
    "clock_limit_reasons",
)


def gpu_sample() -> list[str]:
    try:
        out = subprocess.run(
            ["nvidia-smi", f"--query-gpu={','.join(GPU_FIELDS)}", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return [""] * len(GPU_FIELDS)
    values = [v.strip() for v in out.splitlines()[0].split(",")]
    values[2] = f"{float(values[2]) / 1024:.2f}"  # MiB -> GiB
    return values


def python_processes() -> tuple[int, float]:
    count, rss = 0, 0
    for p in psutil.process_iter(["name", "memory_info"]):
        info = p.info
        mem = info["memory_info"]
        if (info["name"] or "").lower().startswith("python") and mem is not None and mem.rss > 100 * 1024**2:
            count += 1  # processes under 100 MiB are launcher shims
            rss += mem.rss
    return count, rss / 1024**3


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--watch-pid", type=int, help="stop when this process exits")
    ap.add_argument("--max-minutes", type=float, default=240.0)
    args = ap.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    psutil.cpu_percent(interval=None)  # prime the counter
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        while time.monotonic() - start < args.max_minutes * 60:
            if args.watch_pid is not None and not psutil.pid_exists(args.watch_pid):
                break
            time.sleep(args.interval)
            count, rss = python_processes()
            writer.writerow(
                [
                    round(time.monotonic() - start, 1),
                    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    psutil.cpu_percent(interval=None),
                    f"{psutil.virtual_memory().used / 1024**3:.2f}",
                    count,
                    f"{rss:.2f}",
                    *gpu_sample(),
                ]
            )
            f.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
