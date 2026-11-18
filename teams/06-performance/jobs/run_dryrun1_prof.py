"""Job wrapper: G6 Week-3 dryrun1_prof — full-width / Gate-2 config_v1 step profile.

Authority: G6 Week 3 Full-width profile in dry run (work order) + RAJ_G6_week3_Plan_V001.md
Owner: Varshith Chennuru (varshith2000)

Runs perfkit.bench with --modes clean,layer,trace --level 3 --tag dryrun1_prof
using G5's signed Gate-2 config (teams/05-architecture/configs/config_v1.yaml)
mapped onto teams/06-performance/configs/base.yaml, keeping mfu_method=g6-v1.

All outputs land in --out (default: out/):
  - out/result.json          summary JSON with meta, metrics (mfu_method=g6-v1), clean, layer, trace
  - out/dryrun1_prof.json    full perfkit bench record
  - out/dryrun1_prof.md      markdown step + layer + trace report
  - out/dryrun1_prof.jsonl   live event stream record
  - out/dryrun1_prof_parts/  cut Chrome trace parts (<50 MB total) for Perfetto / chrome://tracing

Usage from repo root:
  # Local CPU smoke test (exit 0 required before filing PR):
  python -B teams/06-performance/jobs/run_dryrun1_prof.py --smoke-cpu

  # TSAI 1-GPU runner command:
  python -B teams/06-performance/jobs/run_dryrun1_prof.py \
      --config teams/05-architecture/configs/config_v1.yaml \
      --modes clean,layer,trace --level 3 --tag dryrun1_prof --out out --synthetic
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

PERF_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PERF_DIR.parents[1]
DEFAULT_G5_CONFIG = REPO_ROOT / "teams" / "05-architecture" / "configs" / "config_v1.yaml"

# Explicit mapping from G5 config_v1.yaml `settings:` keys to G6 configs/base.yaml keys
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


def _load_g5_overrides(cfg_path: Path) -> Tuple[List[str], Dict[str, object]]:
    """Translate G5's `settings: [{key, value, ...}]` YAML into valid configs/base.yaml CLI overrides.

    If `cfg_path` is already a standard perfkit config dict (with `model:`/`run:`),
    returns an empty override list so perfkit can load `cfg_path` directly.
    """
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if "settings" not in raw or not isinstance(raw["settings"], list):
        return [], {}

    applied: Dict[str, object] = {}
    overrides: List[str] = []
    unmapped: List[str] = []
    has_moe = False

    for item in raw["settings"]:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        val = item.get("value")
        if not key or val is None:
            # Open full-width dimensions (null in Gate-2 config_v1.yaml) fall back
            # to base.yaml small-width defaults until G5/G7 lock full-width dims.
            continue
        applied[key] = val

        if key == "tokenizer.name":
            # Verified by dataio.loader against BrahmicTokenizer-131K; not a base.yaml key
            continue
        if key == "embedding.type":
            mapped_val = "ke2" if str(val).lower() in ("kronecker", "ke2") else val
            overrides.append(f"model.embedding={mapped_val}")
            continue
        if key == "loss.train_on":
            if str(val).lower() == "ntp":
                overrides.append("model.mtp=false")
            elif str(val).lower() == "mtp":
                overrides.append("model.mtp=true")
            else:
                unmapped.append(f"{key}={val}")
            continue

        if key.startswith("moe."):
            has_moe = True

        target_key = G5_TO_BASE_KEY.get(key)
        if target_key:
            overrides.append(f"{target_key}={val}")
        else:
            unmapped.append(f"{key}={val}")

    if unmapped:
        # A filled-in G5 value must reach the model or stop the job; never time a different model silently.
        raise ValueError(f"{cfg_path}: G5 settings with no base.yaml mapping (add them to G5_TO_BASE_KEY): "
                         + ", ".join(unmapped))

    if has_moe:
        overrides.insert(0, "model.ffn=moe")
        overrides.append("model.moe.dispatch=sorted")

    return overrides, applied


def _run_bench(cmd: List[str]) -> Tuple[int, str, float]:
    t0 = time.perf_counter()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        cmd,
        cwd=str(PERF_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    wall = time.perf_counter() - t0
    out = (proc.stdout or "") + (("\n--- stderr ---\n" + proc.stderr) if proc.stderr else "")
    return proc.returncode, out, wall


def main() -> int:
    ap = argparse.ArgumentParser(description="G6 W3 dryrun1_prof torch.profiler job wrapper")
    ap.add_argument(
        "--config",
        default=str(DEFAULT_G5_CONFIG),
        help="Path to G5 config_v1.yaml or a perfkit config YAML",
    )
    ap.add_argument("--modes", default="clean,layer,trace", help="Comma-separated perfkit modes")
    ap.add_argument("--level", type=int, default=3, help="Profiler level (3 = clean + layer + trace)")
    ap.add_argument("--tag", default="dryrun1_prof", help="Run tag for output artifacts")
    ap.add_argument("--out", default="out", help="Output directory for JSON/MD/trace parts")
    ap.add_argument(
        "--synthetic",
        action="store_true",
        help="Use synthetic token stream (fallback when FineWeb shard is absent)",
    )
    ap.add_argument(
        "--smoke-cpu",
        action="store_true",
        help="Run tiny_cpu smoke check on CPU to verify exit 0 before PR",
    )
    args, extra_overrides = ap.parse_known_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        candidate = (REPO_ROOT / cfg_path).resolve()
        cfg_path = candidate if candidate.exists() else (PERF_DIR / cfg_path).resolve()

    g5_overrides, g5_applied = _load_g5_overrides(cfg_path)

    if args.smoke_cpu:
        base_cfg = "configs/tiny_cpu.yaml"
        warmup, steps = 2, 10
        # Apply Gate-2 MoE + Muon choices from config_v1.yaml while keeping tiny CPU dims
        mode_overrides = [
            "model.ffn=moe",
            "model.moe.num_experts=4",
            "model.moe.num_shared=1",
            "model.moe.top_k=2",
            "model.moe.dispatch=sorted",
            "optim.name=muon",
            "optim.lr=0.001",
            "run.seed=1234",
            "run.grad_clip=1.0",
            "data.source=synthetic",
            "run.device=cpu",
            "run.dtype=fp32",
        ]
    else:
        base_cfg = "configs/base.yaml" if g5_overrides else str(cfg_path)
        warmup, steps = 5, 20
        mode_overrides = list(g5_overrides)
        if args.synthetic:
            mode_overrides.append("data.source=synthetic")

    out_override = [f"bench.out_dir={out_dir}"]

    # Remove existing files for the same tag in out_dir so free_path writes <tag>.json directly
    for ext in (".json", ".md", ".jsonl"):
        p = out_dir / f"{args.tag}{ext}"
        if p.exists():
            p.unlink()

    # On GPU, run one discarded warm clean pass so CUDA/Triton caches are hot before timed run
    if not args.smoke_cpu:
        warm_cmd = [
            sys.executable,
            "-B",
            "-m",
            "perfkit.bench",
            "--config",
            base_cfg,
            "--modes",
            "clean",
            "--level",
            "1",
            "--tag",
            f"{args.tag}-warm",
            "--warmup",
            str(warmup),
            "--steps",
            str(steps),
            *mode_overrides,
            *out_override,
            *extra_overrides,
        ]
        print(f"[dryrun1_prof] running discarded warmup pass: {' '.join(warm_cmd)}", flush=True)
        rc, log, wall = _run_bench(warm_cmd)
        print(log, flush=True)
        if rc != 0:
            print(f"[dryrun1_prof] warmup pass failed (exit={rc})", file=sys.stderr)
            return rc
        for ext in (".json", ".md", ".jsonl"):
            p = out_dir / f"{args.tag}-warm{ext}"
            if p.exists():
                p.unlink()

    cmd = [
        sys.executable,
        "-B",
        "-m",
        "perfkit.bench",
        "--config",
        base_cfg,
        "--modes",
        args.modes,
        "--level",
        str(args.level),
        "--tag",
        args.tag,
        "--warmup",
        str(warmup),
        "--steps",
        str(steps),
        *mode_overrides,
        *out_override,
        *extra_overrides,
    ]
    print(f"[dryrun1_prof] running timed profile: {' '.join(cmd)}", flush=True)
    rc, log, wall = _run_bench(cmd)
    print(log, flush=True)
    if rc != 0:
        print(f"[dryrun1_prof] timed profile failed (exit={rc})", file=sys.stderr)
        return rc

    rec_path = out_dir / f"{args.tag}.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
    meta = rec.get("meta", {})
    metrics = rec.get("metrics", {})

    summary = {
        "job": "dryrun1_prof",
        "owner": "Varshith Chennuru (varshith2000)",
        "tag": args.tag,
        "modes": args.modes.split(","),
        "level": args.level,
        "smoke_cpu": args.smoke_cpu,
        "source_config": str(cfg_path.relative_to(REPO_ROOT)) if cfg_path.is_relative_to(REPO_ROOT) else str(cfg_path),
        "base_config": base_cfg,
        "g5_config_v1_applied": g5_applied,
        "g5_mapped_overrides": g5_overrides,
        "mfu_method": metrics.get("mfu_method", "g6-v1"),
        "git_sha": meta.get("commit"),
        "gpu": meta.get("gpu"),
        "dtype": meta.get("dtype"),
        "wall_s": round(wall, 3),
        "metrics": metrics,
        "clean": rec.get("clean", {}),
        "layer": rec.get("layer", {}),
        "trace": rec.get("trace", {}),
    }
    result_path = out_dir / "result.json"
    result_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[dryrun1_prof] wrote summary -> {result_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
