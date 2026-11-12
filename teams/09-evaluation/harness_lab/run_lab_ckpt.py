#!/usr/bin/env python3
"""Score one lab checkpoint and write the result as eval-mini v1 (results/eval_mini_v1_schema.md, section 6).

In simple words: give it the folder of a run in the checkpoint store; it reads the checkpoint that the run's pointer
names, checks and exports the weights through Team 7's ``export_safetensors()``, scores them, and writes one v1 JSON
file whose records say exactly which checkpoint was scored.

    # CPU test on Team 7's tiny MoE (make the store first with jobs/restore_test/restore_test.py):
    python teams/07-infrastructure/jobs/restore_test/restore_test.py
    python teams/09-evaluation/harness_lab/run_lab_ckpt.py \\
        --run-dir teams/07-infrastructure/jobs/restore_test/out/ckpt_store/restore-b

    # a given step instead of the newest commit:
    python teams/09-evaluation/harness_lab/run_lab_ckpt.py --run-dir <remote_root>/<run_id> --step 100

What it reads (schema section 6): only the folder named by ``latest.json`` (or by the ``commits.jsonl`` line of
``--step``), never a folder found by listing. ``model_revision`` is the sha256 of the bytes of ``MANIFEST.json``.

Scorers (``--scorer``):
  smoke               top-1 next-token accuracy of the tiny MoE on a held-out slice of Team 5's seeded token stream.
                      It exercises the whole path (pointer -> manifest -> export -> score -> v1 -> check) on CPU.
                      It is NOT an eval-mini task and its numbers say nothing about model quality.
  <module>:<function> reserved for a real-model scorer (not wired yet): it needs an lm-eval wrapper that loads
                      the Team 5 model and tokenizer, which do not exist yet.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAMS = HERE.parents[1]
TEAM07 = TEAMS / "07-infrastructure"
HARNESS05 = TEAMS / "05-architecture" / "harness"
CONFIGS05 = TEAMS / "05-architecture" / "configs"
RESULTS09 = TEAMS / "09-evaluation" / "results"
sys.path[:0] = [str(TEAM07), str(TEAM07 / "support" / "simulation"), str(HARNESS05)]

SCHEMA_VERSION = "eval_mini_v1"
RUN_VERSION = "0.1"
MIN_TORCH = "2.14.1"
SMOKE_TASK = "lab_smoke_next_token"
SMOKE_SEQUENCES = 64
FORMAT_OF_DTYPE = {"torch.bfloat16": "bf16", "torch.float16": "fp16", "torch.float32": "fp32"}


class PointerError(SystemExit):
    pass


def load_converter():
    """results/convert_v0_to_v1.py, for check(); it has no package, so load it by path."""
    spec = importlib.util.spec_from_file_location("convert_v0_to_v1", RESULTS09 / "convert_v0_to_v1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_pointer(run_dir: Path, step: int | None) -> dict:
    """The one pointer to read: ``latest.json``, or the ``commits.jsonl`` line of ``step``. Never a directory listing."""
    if step is None:
        latest = run_dir / "latest.json"
        if not latest.exists():
            raise PointerError(f"{latest} not found: no committed checkpoint for this run")
        pointer = json.loads(latest.read_text(encoding="utf-8"))
        if not pointer.get("path"):
            raise PointerError(f"{latest} has no path: the run was claimed but nothing is committed yet")
        return pointer
    commits = run_dir / "commits.jsonl"
    if not commits.exists():
        raise PointerError(f"{commits} not found")
    lines = [json.loads(x) for x in commits.read_text(encoding="utf-8").splitlines() if x.strip()]
    found = [x for x in lines if x["step"] == step]
    if not found:
        raise PointerError(f"no commit at step {step} in {commits}; steps committed: {[x['step'] for x in lines]}")
    return found[-1]


def checkpoint_facts(run_dir: Path, shown: str, pointer: dict, run_name: str | None) -> dict:
    """Everything the v1 ``checkpoint`` block and ``model_revision`` need, from the pointer and MANIFEST.json."""
    folder = run_dir / pointer["path"]
    manifest_path = folder / "MANIFEST.json"
    if not manifest_path.exists():
        raise PointerError(f"{manifest_path} not found: the commit is incomplete (MANIFEST.json is written last)")
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    run = run_name or manifest["run_id"]
    # schema: the epoch is the <E> in the folder name. latest.json can hold a later epoch than the folder (a restore
    # claims epoch + 1 before it commits anything), so the folder name is the one that matches.
    named = re.search(r"-e(\d+)$", pointer["path"])
    epoch = int(named.group(1)) if named else pointer.get("epoch")
    return {
        "model": f"lab:{run}",
        "model_revision": sha256_bytes(raw),
        "checkpoint": {
            "run": run,
            "branch": manifest["branch"],
            "step": manifest["step"],
            "epoch": epoch,
            "tokens_seen": manifest.get("tokens"),
            "path": f"{shown}/{pointer['path']}",  # as the caller wrote --run-dir, not this machine's absolute path
        },
        "manifest_sha256": sha256_bytes(raw),
        "pointer_path": pointer["path"],
    }


# ---- the tiny MoE (Team 5) behind Team 7's loader, for the CPU test -------------------------------------------------

def tiny_cfg(config: Path, tiny: Path, steps: int) -> dict:
    from check_config import errors_for, load_settings, merge
    from train import as_map

    settings = merge(load_settings(config), tiny)
    found = errors_for(settings)
    if found:
        raise SystemExit("\n".join(found))
    cfg = as_map(settings)
    cfg["tiny.steps"] = steps  # the probe batch comes from a stream of this length, so it must equal the saving run's
    return cfg


def tiny_pieces(cfg: dict):
    """(model_factory, probe_fn) as ``export_safetensors`` wants them: the same probe as restore_test.py."""
    import torch
    import torch.nn.functional as F
    from train import TinyMoE, stream_for

    seed = int(cfg["run.seed"])
    probe_batch = stream_for(cfg, seed + 1)[: int(cfg["tiny.batch"])]

    def factory():
        torch.manual_seed(seed)
        return TinyMoE(cfg)

    def probe(model) -> float:
        model.eval()
        with torch.no_grad():
            logits, _ = model(probe_batch.to(next(model.parameters()).device))
            return F.cross_entropy(logits[:, :-1].reshape(-1, logits.shape[-1]), probe_batch[:, 1:].reshape(-1)).item()

    return factory, probe


def smoke_scorer(model, cfg: dict, seed: int) -> list[dict]:
    """Top-1 next-token accuracy on SMOKE_SEQUENCES sequences of a seeded stream no training step used."""
    import torch
    from train import stream_for

    held_out = dict(cfg)
    held_out["tiny.steps"] = SMOKE_SEQUENCES  # stream_for makes steps * batch sequences; batch is 1 below
    held_out["tiny.batch"] = 1
    tokens = stream_for(held_out, seed + 1000)
    model.eval()
    with torch.no_grad():
        logits, _ = model(tokens)
    correct = (logits[:, :-1].argmax(-1) == tokens[:, 1:]).sum().item()
    total = tokens[:, 1:].numel()
    return [{
        "task": SMOKE_TASK, "metric": "acc", "filter": "none", "primary": True,
        "value": round(100 * correct / total, 2), "stderr": None, "n_items": total,
        "item_set": f"limit:{SMOKE_SEQUENCES}", "num_fewshot": 0, "decoding": "loglikelihood",
        "notes": [f"smoke test of the pipeline on Team 5's synthetic stream (seed {seed + 1000}); not an eval-mini task, "
                  "says nothing about model quality"],
    }]


# ---- v1 document ----------------------------------------------------------------------------------------------------

def describe_hardware(device: str) -> str:
    return f"{platform.processor() or platform.machine()} ({device})"


def build_records(facts: dict, scored: list[dict], fmt: str, dtype: str, backend: str, seed: int, device: str,
                  harness_name: str, run_date: str) -> list[dict]:
    records = []
    for s in scored:
        records.append({
            "model": facts["model"], "model_revision": facts["model_revision"], "checkpoint": facts["checkpoint"],
            "format": fmt, "backend": backend, "dtype": dtype,
            **s,
            "seed": {"random": seed, "numpy": seed, "torch": seed, "fewshot": seed},
            "harness": {"name": harness_name, "version": RUN_VERSION},
            "hardware": describe_hardware(device), "run_date": run_date,
        })
    return records


def build_doc(facts: dict, records: list[dict], run_date: str, convert) -> tuple[dict, bytes]:
    records = sorted(records, key=lambda r: tuple(str(r[k]) for k in convert.KEY))
    doc = {
        "schema_version": SCHEMA_VERSION,
        "generated": run_date,
        "sources": [{"path": f"{facts['checkpoint']['path']}/MANIFEST.json", "sha256": facts["manifest_sha256"],
                     "schema_version": "v5-ckpt/2"}],
        "notes": ["Lab checkpoint scored by teams/09-evaluation/harness_lab/run_lab_ckpt.py; the record's checkpoint block "
                  "and model_revision follow results/eval_mini_v1_schema.md section 6."],
        "records": records,
    }
    return doc, (json.dumps(doc, indent=1, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def load_scorer(name: str):
    module, _, function = name.partition(":")
    if not function:
        raise SystemExit(f"--scorer must be 'smoke' or '<module>:<function>', got {name!r}")
    return getattr(importlib.import_module(module), function)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--run-dir", type=Path, required=True,
                    help="<remote_root>/<run_id>: the folder with latest.json and commits.jsonl")
    ap.add_argument("--step", type=int, help="score the commit at this step (default: the one latest.json names)")
    ap.add_argument("--run-name", help="checkpoint.run if not the manifest's run_id; in a queue job '<job_run_id>/<arm>'")
    ap.add_argument("--scorer", default="smoke")
    ap.add_argument("--config", type=Path, default=CONFIGS05 / "config_v0.yaml")
    ap.add_argument("--tiny", type=Path, default=CONFIGS05 / "small" / "tiny_moe.yaml")
    ap.add_argument("--steps", type=int, default=200, help="tiny MoE: the saving run's step count (stream length)")
    ap.add_argument("--out", type=Path, default=HERE / "out" / "eval_mini_v1_lab.json")
    ap.add_argument("--device", default="cpu", choices=["cpu"], help="the tiny MoE test runs on CPU")
    a = ap.parse_args(argv)

    import torch

    if torch.__version__ < MIN_TORCH:
        ap.error(f"needs torch {MIN_TORCH} or newer, found {torch.__version__}")
    if a.scorer != "smoke":
        raise SystemExit("--scorer <module>:<function> is not wired yet: it needs an lm-eval wrapper that loads the "
                         "Team 5 model and tokenizer. Use --scorer smoke for the CPU test.")
    run_dir = a.run_dir.resolve()
    pointer = read_pointer(run_dir, a.step)
    facts = checkpoint_facts(run_dir, a.run_dir.as_posix().rstrip("/"), pointer, a.run_name)
    print(f"checkpoint: {facts['model']} step {facts['checkpoint']['step']} branch {facts['checkpoint']['branch']} "
          f"epoch {facts['checkpoint']['epoch']} ({pointer['path']})")
    print(f"model_revision (sha256 of MANIFEST.json): {facts['model_revision']}")

    from ckpt.ckpt import export_safetensors
    from safetensors.torch import load_file

    # the saved probe-loss bits were made with these two settings (restore_test.py); other settings change the last bit
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    cfg = tiny_cfg(a.config.resolve(), a.tiny.resolve(), a.steps)
    factory, probe = tiny_pieces(cfg)
    seed = int(cfg["run.seed"])
    os.environ.setdefault("V5_EVENTS_DIR", tempfile.mkdtemp(prefix="lab_events_"))
    with tempfile.TemporaryDirectory(prefix="lab_export_") as tmp:
        exported = Path(tmp) / "model.safetensors"
        info = export_safetensors(run_dir.as_posix(), factory, probe, str(exported), step=facts["checkpoint"]["step"])
        print(f"export ok: step {info['step']}, probe loss bits equal the saved ones")
        model = factory()
        model.load_state_dict(load_file(str(exported)), strict=True)
    dtype = str(next(model.parameters()).dtype)
    fmt = FORMAT_OF_DTYPE.get(dtype, dtype)

    scored = smoke_scorer(model, cfg, seed)
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records = build_records(facts, scored, fmt, dtype.removeprefix("torch."), "lab", seed, a.device, "run_lab_ckpt", run_date)
    convert = load_converter()
    doc, data = build_doc(facts, records, run_date, convert)
    print(f"{len(records)} record(s)")
    ok = convert.check(doc, 0)
    if not ok:
        raise SystemExit("check(doc, 0) failed; nothing written")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(data)
    for r in records:
        print(f"RESULT {r['task']} {r['metric']}/{r['filter']} = {r['value']} (n={r['n_items']}) -> {a.out}")
    print(f"wrote {a.out} ({len(data):,} bytes, sha256 {sha256_bytes(data)[:16]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
