"""Job wrapper: G6 Week-3 dryrun1_nsys, an Nsight Systems capture of the dry run 1 training step.

Companion to dryrun1_prof (class #486, torch.profiler). Same model: G5's signed config_v1.yaml (aec75af) mapped
onto configs/base.yaml with the same key mapping as run_dryrun1_prof.py, sorted MoE dispatch, mfu_method=g6-v1.

What it does (one command, no shell pipes):
  1. Re-runs itself under `nsys profile --capture-range=cudaProfilerApi`.
  2. Inside: builds the model with perfkit.bench.build, runs --warmup steps untraced, then cudaProfilerStart,
     --steps training steps inside perfkit's trace-mode recorder (every perfkit region is an NVTX range, plus one
     "dryrun1_nsys.step<i>" range per step), cudaProfilerStop. Only those steps are in the report.
  3. `nsys stats` on the report: GPU kernels, NVTX ranges, memcpy time and size, CUDA API calls, as CSV.
  4. Writes out/dryrun1_nsys.md (tables from the CSVs, per measured step) and out/result.json (GPU, commit SHA,
     nsys and torch versions, config pin, the CSV rows).
Times under nsys include tracing overhead: they rank kernels and regions; step time comes from dryrun1_prof.

Needs the Nsight Systems CLI (`nsys`) on PATH (or NSYS=/path/to/nsys). Without it the job stops at once, exit 3.

Outputs in --out (default out/):
  dryrun1_nsys.nsys-rep            the Nsight report (open in Nsight Systems; gist it, never commit it to tip)
  dryrun1_nsys_<report>.csv        one CSV per nsys stats report
  dryrun1_nsys.md / result.json    summary for tip results/profile_dryrun1.md (Nsight notes)
  dryrun1_nsys_inner.json          what the traced process saw: GPU, dtype, steps, model sizes
The SQLite export nsys stats makes is deleted at the end (it is large and duplicates the report).

Usage from repo root:
  # CPU smoke (no GPU, no nsys): builds the model and runs the step loop with the NVTX recorder
  python -B teams/06-performance/jobs/run_dryrun1_nsys.py --smoke-cpu
  # TSAI 1-GPU command
  python -B teams/06-performance/jobs/run_dryrun1_nsys.py --config teams/05-architecture/configs/config_v1.yaml --tag dryrun1_nsys --out out --synthetic
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

PERF_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PERF_DIR.parents[1]
DEFAULT_G5_CONFIG = REPO_ROOT / "teams" / "05-architecture" / "configs" / "config_v1.yaml"
CONFIG_PIN = "aec75af"   # G5 Gate 2 signed config_v1.yaml (#447)

# Same mapping as run_dryrun1_prof.py (class #486), so both jobs profile the same model.
G5_TO_BASE_KEY = {
    "run.seed": "run.seed",
    "run.grad_clip": "run.grad_clip",
    "optim.name": "optim.name",
    "optim.lr": "optim.lr",
    "tokenizer.vocab_size": "model.vocab_size",
    "embedding.pos_dim": "model.ke_max_pos",
    "attention.impl": "model.attn_impl",
    "moe.n_expert": "model.moe.num_experts",
    "moe.n_shared": "model.moe.num_shared",
    "moe.top_k": "model.moe.top_k",
    "model.n_layer": "model.n_layer",
    "model.d_model": "model.n_embd",
    "model.n_head": "model.n_head",
    "model.d_ff": "model.moe.ffn_hidden",
    "data.seq_len": "model.block_size",
    "precision": "run.dtype",
}

# nsys stats report names. Newer nsys names the NVTX report nvtx_sum, older ones nvtx_pushpop_sum.
REPORTS = ["cuda_gpu_kern_sum", "nvtx_sum", "cuda_gpu_mem_time_sum", "cuda_gpu_mem_size_sum", "cuda_api_sum"]
REPORT_FALLBACK = {"nvtx_sum": "nvtx_pushpop_sum"}
NSYS_EXIT_MISSING = 3


def load_g5_overrides(cfg_path: Path):
    """G5 `settings: [{key, value}]` -> base.yaml overrides (null values keep base.yaml's small width).
    A plain perfkit config (with model:/run:) gives no overrides: it is loaded as it is."""
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw.get("settings"), list):
        return [], {}
    applied, overrides, has_moe = {}, [], False
    for item in raw["settings"]:
        if not isinstance(item, dict):
            continue
        key, val = item.get("key"), item.get("value")
        if not key or val is None:
            continue
        applied[key] = val
        if key == "tokenizer.name":
            continue
        if key == "embedding.type":
            overrides.append(f"model.embedding={'ke2' if str(val).lower() in ('kronecker', 'ke2') else val}")
            continue
        if key == "loss.train_on":
            overrides.append(f"model.mtp={'true' if str(val).lower() == 'mtp' else 'false'}")
            continue
        has_moe = has_moe or key.startswith("moe.")
        if key in G5_TO_BASE_KEY:
            overrides.append(f"{G5_TO_BASE_KEY[key]}={val}")
    if has_moe:
        overrides.insert(0, "model.ffn=moe")
        overrides.append("model.moe.dispatch=sorted")
    return overrides, applied


def resolve_config(arg: str) -> Path:
    p = Path(arg)
    if p.is_absolute():
        return p
    for base in (REPO_ROOT, PERF_DIR, Path.cwd()):
        if (base / p).exists():
            return (base / p).resolve()
    raise SystemExit(f"config not found: {arg}")


SMOKE_OVERRIDES = [
    "model.ffn=moe", "model.moe.num_experts=4", "model.moe.num_shared=1", "model.moe.top_k=2",
    "model.moe.dispatch=sorted", "optim.name=muon", "optim.lr=0.001", "run.seed=1234", "run.grad_clip=1.0",
    "data.source=synthetic", "run.device=cpu", "run.dtype=fp32",
]


# ------------------------------------------------------------------------------ inside nsys: the traced steps

def inner(a, base_cfg: str, overrides: list) -> int:
    """Build the model, warm up, then trace --steps steps between cudaProfilerStart and cudaProfilerStop."""
    sys.path.insert(0, str(PERF_DIR))
    import torch
    from models.config import load_config
    from perfkit import bench as B
    from perfkit import metrics as M
    from perfkit import timer as T
    from perfkit.regions import use_recorder

    cfg = load_config(base_cfg, overrides)
    device = B.pick_device(cfg["run"]["device"])
    s = B.build(cfg, device)
    cuda = device.type == "cuda"
    print(f"[dryrun1_nsys] device={M.device_name(device)} dtype={s.dtype} B={cfg['run']['batch_size']} "
          f"T={s.mcfg.block_size} layers={s.mcfg.n_layer} d={s.mcfg.n_embd} ffn={s.mcfg.ffn}", flush=True)
    for note in s.notes:
        print(f"[dryrun1_nsys] note: {note}", flush=True)

    for _ in range(a.warmup):                       # untraced: allocator, autotune and lazy init settle here
        B.train_step(s)
    T.sync(device)

    rec = T.ProfilerRecorder(max_level=a.level)     # NVTX range per perfkit region on CUDA (same names as the JSON)
    losses = []
    if cuda:
        torch.cuda.reset_peak_memory_stats(device)
        torch.cuda.profiler.start()                 # nsys --capture-range=cudaProfilerApi starts here
    t0 = time.perf_counter()
    for i in range(a.steps):
        if cuda:
            torch.cuda.nvtx.range_push(f"dryrun1_nsys.step{i}")
        with use_recorder(rec):
            _, loss = B.train_step(s)
        if cuda:
            torch.cuda.nvtx.range_pop()
        losses.append(loss)
    T.sync(device)
    wall_ms = (time.perf_counter() - t0) * 1e3
    if cuda:
        torch.cuda.profiler.stop()                  # ... and stops here
    loss_vals = [float(x) for x in losses]

    commit, dirty = M.git_state()
    info = {
        "gpu": M.device_name(device),
        "capability": list(torch.cuda.get_device_capability(device)) if cuda else None,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "dtype": s.dtype,
        "notes": s.notes,
        "commit": commit,
        "dirty": dirty,
        "batch_size": cfg["run"]["batch_size"],
        "block_size": s.mcfg.block_size,
        "n_layer": s.mcfg.n_layer,
        "n_embd": s.mcfg.n_embd,
        "n_head": s.mcfg.n_head,
        "ffn": s.mcfg.ffn,
        "moe": cfg["model"].get("moe"),
        "embedding": s.mcfg.embedding,
        "attn_impl": cfg["model"].get("attn_impl"),
        "data_source": cfg["data"]["source"],
        "params_total_active": list(s.core.param_counts()),
        "warmup_steps": a.warmup,
        "traced_steps": a.steps,
        "traced_wall_ms_total": round(wall_ms, 3),
        "traced_wall_ms_per_step": round(wall_ms / max(a.steps, 1), 3),
        "traced_wall_note": "measured under nsys tracing; for ranking only, step time comes from dryrun1_prof",
        "peak_mem_mb": round(torch.cuda.max_memory_allocated(device) / 2**20, 1) if cuda else None,
        "losses": loss_vals,
        "losses_finite": all(v == v and abs(v) != float("inf") for v in loss_vals),
    }
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.tag}_inner.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"[dryrun1_nsys] traced {a.steps} steps in {wall_ms:.1f} ms (under nsys); losses {loss_vals}", flush=True)
    return 0 if info["losses_finite"] else 1


# ------------------------------------------------------------------------------ outside: nsys, stats, summary

def find_nsys():
    cand = [os.environ.get("NSYS"), shutil.which("nsys")]
    cand += sorted(glob.glob("/opt/nvidia/nsight-systems/*/bin/nsys"), reverse=True)
    cand += sorted(glob.glob("/usr/local/cuda*/bin/nsys"), reverse=True)
    return next((c for c in cand if c and os.path.isfile(c) and os.access(c, os.X_OK)), None)


def run(cmd, **kw):
    print("[dryrun1_nsys] $ " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], text=True, **kw)


def read_csv(path: Path):
    """nsys stats CSV -> list of dict rows (some versions print a title line before the header)."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next((i for i, ln in enumerate(lines) if "Time" in ln and "," in ln), None)
    if start is None:
        return []
    return list(csv.DictReader(lines[start:]))


def col(row: dict, *names):
    """The value of the first column whose header contains one of names (headers differ across nsys versions)."""
    for n in names:
        for k, v in row.items():
            if k and n.lower() in k.lower():
                return v
    return None


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def table(rows, steps, name_cols, count_cols, top):
    """Rows sorted by total time: name, ms per traced step, % of the report's time, calls per step, avg us."""
    out = []
    for r in rows:
        total_ns = num(col(r, "Total Time"))
        if total_ns is None:
            continue
        cnt = num(col(r, *count_cols))
        avg_ns = num(col(r, "Avg"))
        out.append({
            "name": (col(r, *name_cols) or "?").strip(),
            "ms_per_step": round(total_ns / 1e6 / steps, 4),
            "pct": num(col(r, "Time (%)", "Time(%)")),
            "calls_per_step": round(cnt / steps, 2) if cnt is not None else None,
            "avg_us": round(avg_ns / 1e3, 2) if avg_ns is not None else None,
        })
    out.sort(key=lambda d: -d["ms_per_step"])
    return out[:top]


def md_table(rows, label):
    if not rows:
        return f"_No rows: the `{label}` report was empty or could not be read._\n"
    head = "| rank | name | ms / step | % | calls / step | avg µs |\n| ---: | :--- | ---: | ---: | ---: | ---: |\n"
    def cell(v, fmt="{}"):
        return "" if v is None else fmt.format(v)

    body = "".join(
        f"| {i} | `{r['name'][:110].replace('|', '/')}` | {r['ms_per_step']:.3f} | {cell(r['pct'], '{:.1f}')} | "
        f"{cell(r['calls_per_step'])} | {cell(r['avg_us'])} |\n"
        for i, r in enumerate(rows, 1))
    return head + body


def outer(a, base_cfg: str, overrides: list, g5_applied: dict, cfg_path: Path) -> int:
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    nsys = find_nsys()
    if nsys is None:
        print("[dryrun1_nsys] ERROR: Nsight Systems CLI `nsys` not found on PATH (or NSYS=...). This job needs it; "
              "nothing was run.", file=sys.stderr, flush=True)
        return NSYS_EXIT_MISSING
    ver = subprocess.run([nsys, "--version"], capture_output=True, text=True).stdout.strip()
    print(f"[dryrun1_nsys] nsys: {nsys} ({ver})", flush=True)

    rep_base = out / a.tag
    for old in glob.glob(f"{rep_base}*"):           # a clean out/ for this tag: no stale CSVs from an earlier run
        Path(old).unlink()
    child = [sys.executable, "-B", Path(__file__).resolve(), "--inner", "--config", str(cfg_path),
             "--tag", a.tag, "--out", str(out), "--warmup", str(a.warmup), "--steps", str(a.steps),
             "--level", str(a.level)] + (["--synthetic"] if a.synthetic else []) + a.extra
    t0 = time.perf_counter()
    prof = run([nsys, "profile", "--trace=cuda,nvtx", "--sample=none", "--cpuctxsw=none",
                "--capture-range=cudaProfilerApi", "--capture-range-end=stop", "--force-overwrite=true",
                "-o", rep_base] + child, cwd=str(PERF_DIR))
    prof_s = time.perf_counter() - t0
    rep = Path(f"{rep_base}.nsys-rep")
    if prof.returncode != 0 or not rep.exists():
        print(f"[dryrun1_nsys] ERROR: nsys profile exit {prof.returncode}; report exists: {rep.exists()}",
              file=sys.stderr, flush=True)
        return prof.returncode or 1

    stats, failed = {}, []
    for name in REPORTS:
        for rname in [name] + ([REPORT_FALLBACK[name]] if name in REPORT_FALLBACK else []):
            r = run([nsys, "stats", "--report", rname, "--format", "csv", "--force-export=true",
                     "--output", rep_base, rep], capture_output=True)
            hits = sorted(glob.glob(f"{rep_base}_{rname}*.csv"))
            if r.returncode == 0 and hits:
                stats[name] = {"report": rname, "csv": Path(hits[0]).name, "rows": read_csv(Path(hits[0]))}
                break
            print(f"[dryrun1_nsys] stats {rname}: exit {r.returncode} {r.stderr.strip()[-300:]}", flush=True)
        else:
            failed.append(name)
    for big in glob.glob(f"{rep_base}.sqlite"):     # nsys stats' export: large and redundant with the report
        Path(big).unlink()

    info = json.loads((out / f"{a.tag}_inner.json").read_text(encoding="utf-8"))
    steps = info["traced_steps"]
    kern = table(stats.get("cuda_gpu_kern_sum", {}).get("rows", []), steps, ("Name",), ("Instances",), 20)
    nvtx = table(stats.get("nvtx_sum", {}).get("rows", []), steps, ("Range", "Name"), ("Instances",), 30)
    mem_t = table(stats.get("cuda_gpu_mem_time_sum", {}).get("rows", []), steps, ("Operation", "Name"),
                  ("Count", "Instances"), 10)
    api = table(stats.get("cuda_api_sum", {}).get("rows", []), steps, ("Name",), ("Num Calls", "Calls", "Instances"), 12)
    kern_all = table(stats.get("cuda_gpu_kern_sum", {}).get("rows", []), steps, ("Name",), ("Instances",), 10**6)
    kern_ms = round(sum(k["ms_per_step"] for k in kern_all), 3)
    files = {p.name: p.stat().st_size for p in sorted(out.glob(f"{a.tag}*"))}

    result = {
        "job": "dryrun1_nsys",
        "tag": a.tag,
        "source_config": str(cfg_path.relative_to(REPO_ROOT)) if cfg_path.is_relative_to(REPO_ROOT) else str(cfg_path),
        "config_pin": CONFIG_PIN,
        "base_config": base_cfg,
        "g5_config_v1_applied": g5_applied,
        "overrides": overrides,
        "mfu_method": "g6-v1",
        "nsys": ver,
        "nsys_profile_s": round(prof_s, 1),
        "inner": info,
        "kernel_ms_per_step_sum": kern_ms,
        "top_kernels": kern,
        "nvtx_ranges": nvtx,
        "memcpy": mem_t,
        "cuda_api": api,
        "stats_reports": {k: {"report": v["report"], "csv": v["csv"], "rows": len(v["rows"])} for k, v in stats.items()},
        "stats_failed": failed,
        "files_bytes": files,
    }
    (out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    sha = (info.get("commit") or "unknown")[:12] + (" (dirty)" if info.get("dirty") else "")
    md = [f"# dryrun1_nsys: Nsight Systems, dry run 1\n\n",
          f"| Field | Value |\n| :--- | :--- |\n| GPU | {info['gpu']} |\n| Commit | `{sha}` |\n",
          f"| Config | `{result['source_config']}` @ `{CONFIG_PIN}` → `{base_cfg}` |\n",
          f"| Model | B={info['batch_size']} T={info['block_size']} L={info['n_layer']} d={info['n_embd']} "
          f"ffn={info['ffn']} attn={info['attn_impl']} emb={info['embedding']} |\n",
          f"| dtype | {info['dtype']} |\n| Data | {info['data_source']} |\n",
          f"| Steps | {info['warmup_steps']} warmup (untraced) + {steps} traced |\n| nsys | {ver} |\n",
          f"| torch / CUDA | {info['torch']} / {info['cuda']} |\n| `mfu_method` | g6-v1 (not computed here) |\n\n",
          "Times are per traced step, from `nsys stats` on the captured steps only. Tracing adds overhead, so "
          "use them to rank kernels and regions; step time comes from `dryrun1_prof`.\n\n",
          f"Sum of GPU kernel time: **{kern_ms:.3f} ms/step**; wall time of a traced step under nsys: "
          f"{info['traced_wall_ms_per_step']:.3f} ms (kernel sum / wall is a rough GPU-busy share; kernels on "
          "different streams can overlap).\n\n",
          "## Top GPU kernels (`cuda_gpu_kern_sum`)\n\n", md_table(kern, "cuda_gpu_kern_sum"),
          "\n## NVTX ranges: perfkit regions (`" + stats.get("nvtx_sum", {}).get("report", "nvtx_sum") + "`)\n\n",
          "CPU-side range time (the time the host spent inside each region), not GPU time.\n\n",
          md_table(nvtx, "nvtx_sum"),
          "\n## Memory copies (`cuda_gpu_mem_time_sum`)\n\n", md_table(mem_t, "cuda_gpu_mem_time_sum"),
          "\n## CUDA API calls (`cuda_api_sum`)\n\n", md_table(api, "cuda_api_sum"),
          "\n## Files\n\n" + "".join(f"- `{k}`: {v / 2**20:.2f} MB\n" for k, v in files.items()),
          ("\n**Reports empty or failed:** " + ", ".join(failed) + " (an empty report, e.g. no memcpy, is "
           "normal)\n") if failed else ""]
    (out / f"{a.tag}.md").write_text("".join(md), encoding="utf-8")

    total_mb = sum(files.values()) / 2**20
    print(f"[dryrun1_nsys] wrote {out / 'result.json'} and {out / (a.tag + '.md')}; out/ {total_mb:.1f} MB", flush=True)
    if total_mb > 50:
        print("[dryrun1_nsys] WARN: outputs exceed 50 MB; lower --steps", flush=True)
    if failed:
        print(f"[dryrun1_nsys] WARN: stats reports failed: {failed}", flush=True)
    return 0 if "cuda_gpu_kern_sum" in stats and info["losses_finite"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G6 W3 dryrun1_nsys: Nsight Systems capture of the dry run 1 step")
    ap.add_argument("--config", default=str(DEFAULT_G5_CONFIG), help="G5 config_v1.yaml or a perfkit config YAML")
    ap.add_argument("--tag", default="dryrun1_nsys")
    ap.add_argument("--out", default="out")
    ap.add_argument("--warmup", type=int, default=5, help="untraced warmup steps")
    ap.add_argument("--steps", type=int, default=3, help="traced steps (keep small: the report grows with steps)")
    ap.add_argument("--level", type=int, default=3, help="perfkit region depth recorded as NVTX ranges")
    ap.add_argument("--synthetic", action="store_true", help="data.source=synthetic (no FineWeb shard needed)")
    ap.add_argument("--smoke-cpu", action="store_true", help="CPU smoke: tiny model, no nsys, step loop only")
    ap.add_argument("--inner", action="store_true", help=argparse.SUPPRESS)
    a, extra = ap.parse_known_args(argv)
    a.extra = extra                                   # key=value overrides passed straight to load_config
    a.out = str(Path(a.out).resolve())                # before any chdir: out/ is relative to where the job starts

    if a.smoke_cpu:
        a.warmup, a.steps = min(a.warmup, 2), min(a.steps, 2)
        os.chdir(PERF_DIR)                            # perfkit configs are relative to teams/06-performance
        return inner(a, "configs/tiny_cpu.yaml", SMOKE_OVERRIDES + extra)

    cfg_path = resolve_config(a.config)
    g5, applied = load_g5_overrides(cfg_path)
    base_cfg = "configs/base.yaml" if g5 else str(cfg_path)
    overrides = g5 + (["data.source=synthetic"] if a.synthetic else []) + extra
    if a.inner:
        os.chdir(PERF_DIR)
        return inner(a, base_cfg, overrides)
    return outer(a, base_cfg, overrides, applied, cfg_path)


if __name__ == "__main__":
    raise SystemExit(main())
