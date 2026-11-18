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
  <module>:<function> a real-model scorer, imported from this folder or sys.path. The function gets the arguments
                      this script does not know (a list of strings) and returns an object with:
                        name                  harness.name of its records, unless a record sets its own `harness`
                        check(manifest)       raise SystemExit if it cannot score this checkpoint (MANIFEST.json dict)
                        factory()             a fresh model on CPU with the checkpoint's keys (export_safetensors)
                        probe(model)          the probe loss export_safetensors compares with the saved bits
                        score(model, device)  a list of record fields per task and metric (task, metric, value, ...);
                                              it may also set format, dtype, seed, harness and hardware
                      lm_eval_lab:team5 is eval-mini on a Team 5 LanguageModel (lm_eval_lab.py).

    python teams/09-evaluation/harness_lab/run_lab_ckpt.py --run-dir <remote_root>/<run_id> --step 100 \\
        --device cuda --scorer lm_eval_lab:team5 --model-config <arm.yaml> --tokenizer <tokenizer.json> \\
        --tokenizer-sha256 <sha256> --byte-table <table.npz> --tier A --hf-home <HF cache> --offline

A finished Team 5 ``train_week2.py`` run folder (dry run 1: TSAI on #475, p1536, one final checkpoint) is scored with
``--team5-run <folder>`` in place of ``--run-dir``: ``checkpoint.pt`` ``state["model"]`` is loaded strictly and its
weights hash must equal summary.json ``final_model_sha256``, which becomes ``model_revision``.

    python teams/09-evaluation/harness_lab/run_lab_ckpt.py --team5-run ./out/dryrun1-1234 --device cuda \\
        --scorer lm_eval_lab:team5 --model-config ./out/dryrun1-1234/manifest.json --tokenizer <p1536 tokenizer.json> \\
        --tokenizer-sha256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b \\
        --byte-table teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz --tier A --hf-home <HF cache> --offline

The export runs on CPU with deterministic algorithms and one thread (the settings the saved probe-loss bits were made
with); the model then moves to --device for scoring. The last line gives the wall time of each phase.
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
import time
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


def version_key(version: str) -> tuple[tuple[int, ...], int]:
    """A version string as numbers, so that "2.9.0" sorts below "2.14.1" (as plain strings it sorts above).

    The local part ("+cpu", "+cu130") is ignored, and a pre-release or dev build ("2.14.1rc1", "2.15.0a0",
    "2.15.0.dev20261101") sorts just below its release. No dependency on ``packaging``, which the job may not have.
    """
    m = re.fullmatch(r"(\d+(?:\.\d+)*)(.*)", str(version).split("+", 1)[0].strip())
    if not m:
        raise ValueError(f"not a version number: {version!r}")
    release = [int(x) for x in m.group(1).split(".")]
    while len(release) > 1 and release[-1] == 0:
        release.pop()  # "2.14" and "2.14.0" are the same version
    pre_release = re.match(r"[.-]?(a|b|rc|dev)", m.group(2)) is not None
    return tuple(release), 0 if pre_release else 1


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


TEAM5_SOURCE = "train_week2/manifest"


def team5_facts(run_dir: Path, shown: str, run_name: str | None) -> dict:
    """The same facts for a Team 5 ``train_week2.py`` run folder (dry run 1: TSAI on #475, one final checkpoint).

    It holds one checkpoint, ``checkpoint.pt``, written before ``summary.json``. Only a COMPLETED run is scored.
    ``model_revision`` is summary.json ``final_model_sha256``: Team 5's hash of the weights (train_week2.model_hash),
    which the loader recomputes, so it names the weights scored. There is no step folder, branch or epoch.
    """
    manifest_path, summary_path, ckpt = run_dir / "manifest.json", run_dir / "summary.json", run_dir / "checkpoint.pt"
    for p in (manifest_path, summary_path, ckpt):
        if not p.exists():
            raise PointerError(f"{p} not found: not a finished train_week2.py run folder")
    raw = manifest_path.read_bytes()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "COMPLETED":
        raise PointerError(f"{summary_path}: status {summary.get('status')!r}; only a COMPLETED run is scored")
    revision = summary.get("final_model_sha256")
    if not (isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{64}", revision)):
        raise PointerError(f"{summary_path}: no final_model_sha256")
    run = run_name or run_dir.name
    return {
        "model": f"lab:{run}",
        "model_revision": revision,
        "checkpoint": {"run": run, "branch": "main", "step": summary["steps"], "epoch": None, "tokens_seen": None,
                       "path": f"{shown}/checkpoint.pt"},
        "manifest_sha256": sha256_bytes(raw),
        "source": {"path": f"{shown}/manifest.json", "schema_version": TEAM5_SOURCE},
        "pointer_path": "checkpoint.pt",
        "manifest": json.loads(raw),
        "probe_classes": [],
    }


def load_team5_weights(path: Path, model, expected_sha256: str) -> None:
    """Load ``state["model"]`` of a train_week2.py checkpoint.pt into ``model`` and check Team 5's weights hash.

    mmap=True reads only the tensors used: the file also holds the optimizer state (about 2.2 GB in all for dry run 1),
    which is never copied into memory. weights_only=False because the file pickles numpy and Python RNG states; it is
    TSAI's own run output, the input of a TSAI job.
    """
    import torch
    from train_week2 import model_hash  # Team 5's own definition, so the check means what summary.json means

    state = torch.load(path, map_location="cpu", weights_only=False, mmap=True)
    model.load_state_dict(state["model"], strict=True)
    del state
    got = model_hash(model)
    if got != expected_sha256:
        raise SystemExit(f"{path}: weights hash {got[:16]} differs from summary.json final_model_sha256 "
                         f"{expected_sha256[:16]}; not scored")


def checkpoint_facts(run_dir: Path, shown: str, pointer: dict, run_name: str | None) -> dict:
    """Everything the v1 ``checkpoint`` block and ``model_revision`` need, from the pointer and MANIFEST.json."""
    folder = run_dir / pointer["path"]
    manifest_path = folder / "MANIFEST.json"
    if not manifest_path.exists():
        raise PointerError(f"{manifest_path} not found: the commit is incomplete (MANIFEST.json is written last)")
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    run = run_name or manifest["run_id"]
    probe_classes = sorted(manifest.get("probe_loss") or {})
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
        "source": {"path": f"{shown}/{pointer['path']}/MANIFEST.json", "schema_version": "v5-ckpt/2"},
        "pointer_path": pointer["path"],
        "manifest": manifest,
        "probe_classes": probe_classes,
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


class SmokeScorer:
    """``--scorer smoke``: the tiny MoE through the same contract as a real scorer (CPU only)."""

    name = "run_lab_ckpt"

    def __init__(self, a: argparse.Namespace):
        self.cfg = tiny_cfg(a.config.resolve(), a.tiny.resolve(), a.steps)
        self.factory, self.probe = tiny_pieces(self.cfg)
        self.seed = int(self.cfg["run.seed"])

    def check(self, manifest: dict) -> None:
        pass

    def score(self, model, device: str) -> list[dict]:
        return smoke_scorer(model, self.cfg, self.seed)


# ---- v1 document ----------------------------------------------------------------------------------------------------

def describe_hardware(device: str) -> str:
    return f"{platform.processor() or platform.machine()} ({device})"


LATE_FIELDS = ("seed", "harness", "hardware")   # a scorer may set these; they stay at the end of the record


def build_records(facts: dict, scored: list[dict], fmt: str, dtype: str, backend: str, seed: int | None, device: str,
                  harness_name: str, run_date: str) -> list[dict]:
    """One v1 record per scored entry. The checkpoint identity always comes from the pointer and MANIFEST.json; a
    scorer's own format, backend, dtype, seed, harness or hardware win over the defaults here."""
    records = []
    for s in scored:
        s = dict(s)
        late = {k: s.pop(k) for k in LATE_FIELDS if k in s}
        records.append({
            "model": facts["model"], "model_revision": facts["model_revision"], "checkpoint": facts["checkpoint"],
            "format": fmt, "backend": backend, "dtype": dtype,
            **s,
            "seed": late.get("seed", None if seed is None else
                             {"random": seed, "numpy": seed, "torch": seed, "fewshot": seed}),
            "harness": late.get("harness", {"name": harness_name, "version": RUN_VERSION}),
            "hardware": late.get("hardware", describe_hardware(device)), "run_date": run_date,
        })
    return records


def build_doc(facts: dict, records: list[dict], run_date: str, convert) -> tuple[dict, bytes]:
    records = sorted(records, key=lambda r: tuple(str(r[k]) for k in convert.KEY))
    doc = {
        "schema_version": SCHEMA_VERSION,
        "generated": run_date,
        "sources": [{"path": facts["source"]["path"], "sha256": facts["manifest_sha256"],
                     "schema_version": facts["source"]["schema_version"]}],
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
    t_start = time.perf_counter()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__, allow_abbrev=False)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--run-dir", type=Path, help="<remote_root>/<run_id>: the folder with latest.json and commits.jsonl")
    source.add_argument("--team5-run", type=Path,
                        help="a finished Team 5 train_week2.py run folder (manifest.json, checkpoint.pt, summary.json "
                             "with status COMPLETED), as dry run 1 left it; needs a real scorer")
    ap.add_argument("--step", type=int, help="score the commit at this step (default: the one latest.json names)")
    ap.add_argument("--run-name", help="checkpoint.run if not the manifest's run_id; in a queue job '<job_run_id>/<arm>'")
    ap.add_argument("--scorer", default="smoke", help="smoke, or <module>:<function> (see above)")
    ap.add_argument("--config", type=Path, default=CONFIGS05 / "config_v0.yaml", help="smoke: Team 5's config")
    ap.add_argument("--tiny", type=Path, default=CONFIGS05 / "small" / "tiny_moe.yaml", help="smoke: the tiny MoE")
    ap.add_argument("--steps", type=int, default=200, help="smoke: the saving run's step count (stream length)")
    ap.add_argument("--out", type=Path, default=HERE / "out" / "eval_mini_v1_lab.json")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                    help="where the scorer runs (the export is always on CPU); smoke runs on CPU only")
    a, rest = ap.parse_known_args(argv)

    import torch

    if version_key(torch.__version__) < version_key(MIN_TORCH):
        ap.error(f"needs torch {MIN_TORCH} or newer, found {torch.__version__}")
    if a.team5_run is not None and a.scorer == "smoke":
        ap.error("--team5-run needs a real scorer (--scorer lm_eval_lab:team5); smoke scores Team 7's tiny MoE")
    if a.scorer == "smoke":
        if rest:
            ap.error(f"unrecognized arguments: {' '.join(rest)}")
        if a.device != "cpu":
            ap.error("--scorer smoke runs the tiny MoE on CPU only")
    elif a.device == "cuda" and not torch.cuda.is_available():
        ap.error("--device cuda: CUDA is not available")
    threads = torch.get_num_threads()
    # the saved probe-loss bits were made with these two settings (restore_test.py); other settings change the last bit
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    scorer = SmokeScorer(a) if a.scorer == "smoke" else load_scorer(a.scorer)(rest)
    team5 = a.team5_run is not None
    given = a.team5_run if team5 else a.run_dir
    run_dir = given.resolve()
    if team5:
        if a.step is not None:
            ap.error("--step is for --run-dir; a Team 5 run folder has one checkpoint")
        facts = team5_facts(run_dir, given.as_posix().rstrip("/"), a.run_name)
        print(f"checkpoint: {facts['model']} step {facts['checkpoint']['step']} (Team 5 run folder, checkpoint.pt)")
        print(f"model_revision (summary.json final_model_sha256): {facts['model_revision']}")
    else:
        pointer = read_pointer(run_dir, a.step)
        facts = checkpoint_facts(run_dir, given.as_posix().rstrip("/"), pointer, a.run_name)
        print(f"checkpoint: {facts['model']} step {facts['checkpoint']['step']} branch {facts['checkpoint']['branch']} "
              f"epoch {facts['checkpoint']['epoch']} ({pointer['path']})")
        print(f"model_revision (sha256 of MANIFEST.json): {facts['model_revision']}")
    scorer.check(facts["manifest"])

    t_export = time.perf_counter()
    if team5:
        model = scorer.factory()
        load_team5_weights(run_dir / "checkpoint.pt", model, facts["model_revision"])
        print("load ok: checkpoint.pt state['model'] (strict), weights hash equals summary.json final_model_sha256")
    else:
        model = export_store(run_dir, facts, scorer)
    t_export = time.perf_counter() - t_export
    torch.set_num_threads(threads)
    dtype = str(next(model.parameters()).dtype)
    fmt = FORMAT_OF_DTYPE.get(dtype, dtype)

    t_score = time.perf_counter()
    scored = scorer.score(model, a.device)
    t_score = time.perf_counter() - t_score
    return finish(a, facts, scorer, scored, fmt, dtype, t_export, t_score, t_start)


def export_store(run_dir: Path, facts: dict, scorer):
    """A Team 7 store commit: weights through export_safetensors (file sha256, keys and, on the same device class, the
    saved probe-loss bits are checked), loaded strictly into a fresh model."""
    from ckpt.ckpt import export_safetensors
    from safetensors.torch import load_file

    os.environ.setdefault("V5_EVENTS_DIR", tempfile.mkdtemp(prefix="lab_events_"))
    with tempfile.TemporaryDirectory(prefix="lab_export_") as tmp:
        exported = Path(tmp) / "model.safetensors"
        info = export_safetensors(run_dir.as_posix(), scorer.factory, scorer.probe, str(exported),
                                  step=facts["checkpoint"]["step"])
        if "cpu" in facts["probe_classes"]:
            print(f"export ok: step {info['step']}, probe loss bits equal the saved ones")
        else:  # export_safetensors compares only bits made on the same device class
            print(f"export ok: step {info['step']}, file sha256 and keys checked; the saved probe loss is for "
                  f"{', '.join(facts['probe_classes']) or 'no device'}, so it is not compared on cpu")
        model = scorer.factory()
        model.load_state_dict(load_file(str(exported)), strict=True)
    return model


def finish(a, facts, scorer, scored, fmt, dtype, t_export, t_score, t_start) -> int:
    """Build, check and write the v1 document; print the results and the phase times."""
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records = build_records(facts, scored, fmt, dtype.removeprefix("torch."), "lab", getattr(scorer, "seed", None),
                            a.device, scorer.name, run_date)
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
    print(f"TIME export {t_export:.1f} s, score {t_score:.1f} s, total {time.perf_counter() - t_start:.1f} s "
          f"({a.scorer}, {a.device})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
