"""G6 Week-3 single-process checkpoint timing job.

Run from teams/06-performance/:
    python3 jobs/dryrun1_ckpt.py --device cpu --repeats 2 --run-id dryrun1_ckpt_smoke
    python3 jobs/dryrun1_ckpt.py --device cuda --repeats 10 --run-id dryrun1_ckpt

G5 config_v1 specifies signed choices but not executable model dimensions.
This job explicitly uses a SMALL test model. Results are NOT full-width Dry Run 1.
No dataset download or tokenizer download is performed. All generated files stay under ./out/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT.parents[1]
G5_CONFIG = LAB / "teams/05-architecture/configs/config_v1.yaml"
OUT = (ROOT / "out").resolve()
OUT.mkdir(parents=True, exist_ok=True)
# Must be set before import: perfkit.bench.CACHE is evaluated at import time.
os.environ["ERA_PERF_CACHE"] = str(OUT / "cache")
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
import yaml  # noqa: E402
from models.config import load_config, model_config  # noqa: E402
from models.gpt import GPT  # noqa: E402
from models.optim import build_optimizer  # noqa: E402
from perfkit.bench import run_checkpoint  # noqa: E402


REQUIRED = {
    "optim.name": "muon",
    "attention.impl": "eager",
    "moe.n_expert": 16,
    "moe.n_shared": 1,
    "moe.top_k": 2,
}


def signed_g5_values() -> dict:
    rows = yaml.safe_load(G5_CONFIG.read_text())["settings"]
    values = {r["key"]: r["value"] for r in rows}
    for key, expected in REQUIRED.items():
        if values.get(key) != expected:
            raise ValueError(f"G5 signed setting {key}: expected {expected!r}, got {values.get(key)!r}")
    return values


def choose_device(value: str) -> torch.device:
    if value == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested but no CUDA GPU is visible")
    if value not in ("cpu", "cuda"):
        raise ValueError("device must be cpu or cuda")
    return torch.device("cuda:0" if value == "cuda" else "cpu")


def build_config(device: str, g5: dict) -> dict:
    # The model size is provisional because G5 config_v1 leaves dimensions and precision unset.
    # Map the signed fields to the actual G6 base.yaml key names.
    overrides = [
        f"run.device={device}", "run.dtype=fp32", "run.batch_size=1",
        f"run.seed={g5['run.seed']}",
        "data.source=synthetic", "data.prefetch=false",
        "model.n_layer=2", "model.n_embd=64", "model.n_head=4",
        "model.block_size=32", "model.ffn=moe", "model.attn_impl=eager",
        "model.moe.num_experts=16", "model.moe.top_k=2", "model.moe.num_shared=1",
        "model.moe.dispatch=sorted",
        "model.embedding=ke2", "model.ce_impl=chunked",
        "optim.name=muon", f"optim.lr={g5['optim.lr']}",
        "optim.muon_lr=0.01",  # Separate instructor Dry Run 1 instruction.
    ]
    cfg = load_config(ROOT / "configs/base.yaml", overrides)
    model_config(cfg)  # fail early if invalid
    return cfg


def optimizer_state_coverage(core, optimizer) -> dict:
    """Require initialized state for every trainable parameter in each optimizer group.

    Do not use len(optimizer.state): Muon's loop implementation may create
    empty dict entries for parameters whose gradient was None.
    """
    param_names = {id(p): name for name, p in core.named_parameters() if p.requires_grad}
    assigned_ids = set()
    report = {}
    for opt_name, opt in optimizer.named:
        expected_keys = {
            "opt.muon": ("buf",),
            "opt.adamw": ("step", "exp_avg", "exp_avg_sq"),
        }.get(opt_name)
        if expected_keys is None:
            raise RuntimeError(f"Unexpected optimizer for Muon job: {opt_name}")
        missing = []
        total = 0
        for group in opt.param_groups:
            for param in group["params"]:
                pid = id(param)
                if pid in assigned_ids:
                    raise RuntimeError(f"Duplicate optimizer parameter: {param_names.get(pid, pid)}")
                assigned_ids.add(pid)
                total += 1
                state = opt.state.get(param, {})
                missing_keys = [key for key in expected_keys if key not in state]
                for key in expected_keys:
                    value = state.get(key)
                    if key != "step" and isinstance(value, torch.Tensor) and value.shape != param.shape:
                        missing_keys.append(f"{key}:shape")
                if missing_keys:
                    missing.append({"parameter": param_names.get(pid, f"unknown:{pid}"),
                                    "missing": sorted(set(missing_keys))})
        report[opt_name] = {
            "expected_parameters": total,
            "complete_parameters": total - len(missing),
            "missing_count": len(missing),
            "missing": missing,
        }
    not_assigned = sorted(name for name, param in core.named_parameters()
                          if param.requires_grad and id(param) not in assigned_ids)
    if not_assigned:
        raise RuntimeError(f"Trainable parameters absent from optimizer groups: {not_assigned}")
    return report


def git_provenance() -> dict:
    sha_cmd = subprocess.run(["git", "rev-parse", "HEAD"], cwd=LAB, text=True,
                             capture_output=True, check=False)
    status_cmd = subprocess.run(["git", "status", "--porcelain", "--untracked-files=normal"],
                                cwd=LAB, text=True, capture_output=True, check=False)
    if sha_cmd.returncode or status_cmd.returncode:
        raise RuntimeError(f"Could not capture git provenance: {sha_cmd.stderr} {status_cmd.stderr}")
    changed = [line for line in status_cmd.stdout.splitlines()
               if not line[3:].startswith("teams/06-performance/out/")]
    return {"sha": sha_cmd.stdout.strip(), "dirty": bool(changed), "dirty_paths": changed}


def main() -> int:
    job_start = time.perf_counter()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    ap.add_argument("--repeats", type=int, default=10)
    ap.add_argument("--run-id", default="dryrun1_ckpt")
    ap.add_argument("--max-warmup-steps", type=int, default=16,
                    help="Maximum actual synthetic optimizer steps to initialize all state")
    args = ap.parse_args()
    if not 1 <= args.max_warmup_steps <= 64:
        ap.error("--max-warmup-steps must be from 1 to 64")
    if args.repeats < 1 or args.repeats > 20:
        ap.error("--repeats must be from 1 to 20")
    if not args.run_id or not all(c.isalnum() or c in "_-" for c in args.run_id):
        ap.error("--run-id must contain only letters, numbers, underscores or dashes")

    g5 = signed_g5_values()
    cfg = build_config(args.device, g5)
    device = choose_device(args.device)
    torch.manual_seed(int(cfg["run"]["seed"]))
    if device.type == "cuda":
        torch.cuda.manual_seed_all(int(cfg["run"]["seed"]))
    core = GPT(model_config(cfg)).to(device).train()
    optimizer = build_optimizer(core, cfg["optim"])

    # Sparse experts can be unused on a single step. Repeated genuine synthetic
    # optimizer steps must establish *full* per-parameter state before timing.
    batch_size = cfg["run"]["batch_size"]
    seq_len = cfg["model"]["block_size"]
    start = time.perf_counter()
    coverage = {}
    last_loss = None
    warm_steps = 0
    for warm_steps in range(1, args.max_warmup_steps + 1):
        ids = torch.randint(cfg["model"]["vocab_size"],
                            (batch_size, seq_len + 1), device=device)
        _, last_loss = core(ids[:, :-1].contiguous(), ids[:, 1:].contiguous())
        last_loss.backward()
        optimizer.step()
        optimizer.zero_grad()
        coverage = optimizer_state_coverage(core, optimizer)
        if all(stats["missing_count"] == 0 for stats in coverage.values()):
            break
    else:
        incomplete = {name: stats["missing"] for name, stats in coverage.items()
                      if stats["missing_count"]}
        raise RuntimeError(
            f"Optimizer state still incomplete after {args.max_warmup_steps} real steps: {incomplete}"
        )
    if device.type == "cuda":
        torch.cuda.synchronize()
    warm_step_s = time.perf_counter() - start
    opt_state_counts = {name: len(opt.state) for name, opt in optimizer.named}
    provenance = git_provenance()

    setup = SimpleNamespace(core=core, opt=optimizer, scaler=None, device=device)
    result = run_checkpoint(setup, args.repeats, args.run_id)
    payload = {
        "evidence_status": "SMALL-WIDTH TEST ONLY - NOT TSAI FULL-WIDTH DRY RUN 1",
        "run_id": args.run_id,
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_sha": provenance["sha"],
        "git": provenance,
        "resolved_config": cfg,
        "g5_config": str(G5_CONFIG.relative_to(LAB)),
        "g5_signed": REQUIRED,
        "small_model": {"layers": 2, "width": 64, "heads": 4, "sequence": 32,
                        "batch_size": 1, "experts": 16, "shared": 1, "top_k": 2},
        "optimizer": {"name": "muon", "lr": cfg["optim"]["lr"],
                       "muon_lr": cfg["optim"]["muon_lr"], "state_counts": opt_state_counts,
                       "coverage": coverage, "warmup_steps": warm_steps},
        "python": sys.version.split()[0], "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else "CPU",
        "device": str(device), "params": sum(p.numel() for p in core.parameters()),
        "warm_step_s": warm_step_s, "warm_loss": float(last_loss.detach()),
        "wall_s": time.perf_counter() - job_start,
        "checkpoint": result,
    }
    output = OUT / f"{args.run_id}.json"
    output.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(json.dumps({"run_id": args.run_id, "device": str(device),
                      "save_ms": result["save_ms"]["median"],
                      "to_cpu_ms": result["to_cpu_ms"]["median"],
                      "write_ms": result["write_ms"]["median"],
                      "size_mb": result["size_mb"],
                      "warmup_steps": warm_steps,
                      "state_coverage_complete": True,
                      "wall_s": payload["wall_s"],
                      "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
