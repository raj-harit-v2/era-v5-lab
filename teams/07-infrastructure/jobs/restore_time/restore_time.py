"""Restore time: how long Checkpointer.restore takes, by phase and by checkpoint size.

In simple words: the restore test proves a restore is exact; this script times it. Two parts:

  tiny   runs jobs/restore_test/restore_test.py several times (Team 05's tiny MoE, 1 and 2 CPU processes, or
         1 GPU) and reads rank 0's `restore.done` event: the time of each phase of the real restore.
  sweep  saves a SYNTHETIC model (8 square linear layers + AdamW state, so the state is 3 times the weights) at
         several sizes, then times `Checkpointer.restore()` from a cold node-local folder. The sizes say how
         restore time grows with checkpoint size. They are not the size of any real model.

Both write only the JSON file named by --out. The checkpoints live in a temporary folder that is deleted
before the script exits, so the returned folder stays far below the 50 MB limit.

    python jobs/restore_time/restore_time.py                       # CPU, both parts, 9 repetitions
    python jobs/restore_time/restore_time.py --parts sweep --device cuda --note "1 GPU"

What the numbers are not: a remote store (the store is a folder on the local disk, with a warm page cache), the
time from job start to the first training step (CK-13), or a real model size.
"""
import argparse
import glob
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                                   # teams/07-infrastructure
sys.path[:0] = [str(ROOT), str(ROOT / "support" / "simulation")]

import torch  # noqa: E402
import torch.nn as nn  # noqa: E402

PHASES = ("verify_s", "download_s", "load_s", "checks_s", "restore_s")
LAYERS = 8                                               # square linear layers: params = 8 * width^2


def summ(xs):
    xs = sorted(xs)
    return {"median": round(statistics.median(xs), 4), "min": round(xs[0], 4), "max": round(xs[-1], 4), "n": len(xs)}


def folder_bytes(path) -> int:
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(path) for f in fs)


def tiny(reps: int, device: str) -> dict:
    """Run the real restore test `reps` times per process count; read rank 0's restore.done."""
    out = {}
    env = dict(os.environ)
    if device == "cpu":
        env["CUDA_VISIBLE_DEVICES"] = ""                 # hide any GPU, as the committed CPU evidence does
    for nproc in ((1, 2) if device == "cpu" else (1,)):
        phases = {k: [] for k in PHASES}
        walls, size = [], 0
        for _ in range(reps):
            with tempfile.TemporaryDirectory() as tmp:
                t = time.perf_counter()
                r = subprocess.run([sys.executable, str(ROOT / "jobs" / "restore_test" / "restore_test.py"),
                                    "--nproc", str(nproc), "--device", device, "--out", tmp],
                                   capture_output=True, text=True, env=env)
                walls.append(time.perf_counter() - t)
                if r.returncode != 0 or "PASS" not in r.stdout:
                    raise SystemExit(f"restore_test failed (nproc={nproc}): {r.stdout[-300:]} {r.stderr[-300:]}")
                ev = [json.loads(line) for f in glob.glob(f"{tmp}/events/*.jsonl") for line in open(f)]
                ev = [e for e in ev if e["event"] == "restore.done"]
                assert len(ev) == 1, f"expected one restore.done, got {len(ev)}"
                for k in PHASES:
                    phases[k].append(ev[0][k])
                size = folder_bytes(glob.glob(f"{tmp}/ckpt_store/**/step_00000100-e1", recursive=True)[0])
        out[str(nproc)] = {"script_wall_s": summ(walls), "ckpt_bytes": size, **{k: summ(v) for k, v in phases.items()}}
    return out


def sweep(widths, reps: int, device: str) -> dict:
    from ckpt.ckpt import Checkpointer
    from trainer.tiny import SyntheticLoader
    dev = torch.device(device)
    torch.set_num_threads(1)
    os.environ.update(RANK="0", WORLD_SIZE="1", LOCAL_RANK="0")
    sync = torch.cuda.synchronize if dev.type == "cuda" else (lambda: None)
    res = {}
    for width in widths:
        x = torch.randn(4, width, generator=torch.Generator().manual_seed(1)).to(dev)

        def probe(m):
            with torch.no_grad():
                return float(m(x).pow(2).mean())

        def build():
            torch.manual_seed(0)
            m = nn.Sequential(*[nn.Linear(width, width) for _ in range(LAYERS)]).to(dev)
            o = torch.optim.AdamW(m.parameters(), lr=1e-3)
            m(x).sum().backward()
            o.step()                                     # AdamW creates its moments on the first step
            return m, o

        with tempfile.TemporaryDirectory() as tmp:       # deleted on exit: only the JSON is returned
            m, o = build()
            ck = Checkpointer("sweep", f"{tmp}/local", f"{tmp}/store", seed=0)
            ck.claim()
            if not (ck.save(1, m, o, SyntheticLoader(1, 4, 0, 1), probe, reason="restore_time") and ck.wait()):
                raise SystemExit(f"width {width}: the checkpoint was not committed")
            size = folder_bytes(f"{tmp}/store")
            total, ph = [], {k: [] for k in PHASES}
            for _ in range(reps):
                m2, o2 = build()
                shutil.rmtree(f"{tmp}/local", ignore_errors=True)   # cold: no node-local copy, so it downloads
                c2 = Checkpointer("sweep", f"{tmp}/local", f"{tmp}/store", seed=0)
                sync()
                t = time.perf_counter()
                info = c2.restore(m2, o2, SyntheticLoader(1, 4, 0, 1), probe, from_step=1)   # claim included
                sync()
                total.append(time.perf_counter() - t)
                assert info["step"] == 1
                for k in PHASES:
                    ph[k].append(info[k])
        res[str(width)] = {"params": LAYERS * width * width, "ckpt_bytes": size, "restore_total_s": summ(total),
                           **{k: summ(v) for k, v in ph.items()}}
        print(f"width {width}: {size / 1e6:.0f} MB, restore {res[str(width)]['restore_total_s']['median']} s",
              flush=True)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--parts", default="tiny,sweep", help="comma list of: tiny, sweep (default both)")
    ap.add_argument("--device", default="cpu", choices=("cpu", "cuda"))
    ap.add_argument("--reps", type=int, default=9, help="repetitions per setting (default 9)")
    ap.add_argument("--widths", default="512,1024,2048,4096",
                    help="sweep: layer widths; checkpoint = 8*w*w params * 3 (weights + 2 AdamW moments) * 4 bytes")
    ap.add_argument("--note", default="", help="free text for the machine, e.g. 'Apple M5, 10 cores, 16 GB'")
    ap.add_argument("--out", default=str(HERE / "out" / "restore_time.json"), help="the only file written")
    a = ap.parse_args()
    parts = set(a.parts.split(","))
    if a.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("--device cuda, but no GPU is visible")
    r = {"schema": "restore-time/1", "device": a.device, "reps": a.reps, "note": a.note,
         "python": platform.python_version(), "torch": torch.__version__, "platform": platform.platform(),
         "gpu": torch.cuda.get_device_name(0) if a.device == "cuda" else None,
         "store": "local folder, warm page cache"}
    if "tiny" in parts:
        r["tiny_moe"] = tiny(a.reps, a.device)
    if "sweep" in parts:
        r["sweep"] = sweep([int(w) for w in a.widths.split(",")], a.reps, a.device)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(r, f, indent=1)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
