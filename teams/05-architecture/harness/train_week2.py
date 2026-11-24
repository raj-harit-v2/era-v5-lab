"""G5 Week-2 trainer. Accepted Week-1 train.py is deliberately unchanged."""

from __future__ import annotations
import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import argparse
import copy
from contextlib import nullcontext
import hashlib
import importlib
import json
import math
from pathlib import Path
import random
import re
import signal
import sys
import time
from time import monotonic as checkpoint_clock
from uuid import uuid4
import numpy as np
import torch
from week2.artifacts import Artifacts, TOKENIZER_RELEASES, sha256
from week2.config import load, load_runtime, merge, validate
from week2.data import DocumentWindows, BatchStream
from week2.model import LanguageModel
from week2.evaluation import EVAL_BATCH_TOKENS, evaluate, token_nll
from week2.optim import Optimizers, build_optimizer, describe, lr_scale, set_lr_scale
from week2 import tst as tst_mod
from week2.team7_checkpoints import CheckpointProgress, write_native_checkpoint


class JsonWriter:
    def __init__(self, out, cadence=10):
        self.file = (out / "metrics.jsonl").open("w", encoding="utf8")
        self.cadence = cadence

    def write(self, row):
        self.file.write(json.dumps(row, allow_nan=False) + "\n")
        if row.get("step", 0) % self.cadence == 0:
            self.flush()

    def flush(self):
        self.file.flush()

    def close(self):
        self.file.close()


def scored_ntp_loss(model, ids, targets):
    """Sum next-token NLL without materializing logits for ignored positions."""
    scored = targets != -100
    hidden = model.hidden(ids, scored)
    return token_nll(model.head(hidden[scored]), targets[scored]).sum()


# G7 exit-note detail is capped at 500 characters. Keep the complete G5 error
# below that boundary, with 100 characters of headroom; no G7 contract change.
NONFINITE_MESSAGE_LIMIT = 400
NONFINITE_NAME_LIMIT = 64


def nonfinite_tensor_detail(model, *, gradients=False, limit=3):
    """Bounded, best-effort tensor names; called only after a numerical failure."""
    try:
        names = []
        for name, parameter in model.named_parameters():
            value = parameter.grad if gradients else parameter
            if value is not None and not bool(torch.isfinite(value.detach()).all()):
                if len(name) > NONFINITE_NAME_LIMIT:
                    name = name[:30] + "..." + name[-31:]
                names.append(name)
                if len(names) > limit:
                    break
        if not names:
            return "; no nonfinite tensors found in the inspected state"
        suffix = ", ... further tensors not listed" if len(names) > limit else ""
        return "; tensors: " + ", ".join(names[:limit]) + suffix
    except Exception as error:
        # A diagnostic (including a CUDA failure) must not replace the original cause.
        return "; tensor inspection unavailable (" + type(error).__name__[:NONFINITE_NAME_LIMIT] + ")"


def nonfinite_error_message(prefix, model, *, gradients=False):
    """Cap the complete diagnostic, including prefix and the post-clip caveat."""
    caveat = " (gradients inspected after clipping; nonfinites may have propagated)" if gradients else ""
    message = prefix + caveat + nonfinite_tensor_detail(model, gradients=gradients)
    if len(message) > NONFINITE_MESSAGE_LIMIT:
        suffix = "... [truncated]"
        return message[:NONFINITE_MESSAGE_LIMIT - len(suffix)] + suffix
    return message


def checked_step_losses(micro_losses, grad_norm, model=None):
    """Read microbatch losses and the pre-clip norm together before updating."""
    values = torch.cat((torch.stack(micro_losses).flatten(), grad_norm.reshape(1)))
    *losses, norm = values.tolist()
    if not all(map(math.isfinite, losses)):
        raise NonfiniteTrainingError("Nonfinite training objective or MTP component")
    if not math.isfinite(norm):
        message = "Nonfinite gradient norm"
        if model is not None:
            message = nonfinite_error_message(message, model, gradients=True)
        raise NonfiniteTrainingError(message)
    return tuple(sum(losses[i::3]) for i in range(3))


def model_hash(model):
    h = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(str(value.dtype).encode())
        h.update(str(tuple(value.shape)).encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def apply_resolution(cfg, resolution):
    allowed = {
        "approval.status",
        "approval.reference",
        "model.rope_theta",
        "model.norm_eps",
        "model.mtp_weight",
        "model.moe.bias",
        "evaluation.approved",
        "run.micro_batch_size",
    }

    def paths(obj, prefix=""):
        out = []
        for k, v in obj.items():
            key = prefix + k
            out.extend(paths(v, key + ".")) if isinstance(v, dict) else out.append(key)
        return out

    unknown = set(paths(resolution)) - allowed
    if unknown:
        raise ValueError(
            "Resolution cannot change fixed sizes/arms: " + str(sorted(unknown))
        )
    for key, value in (
        cfg.get("provenance", {}).get("lead_explicit_choices", {}).items()
    ):
        node = resolution
        for component in key.split("."):
            if not isinstance(node, dict) or component not in node:
                break
            node = node[component]
        else:
            if node != value:
                raise ValueError(
                    "Resolution conflicts with explicit lead choice: " + key
                )
    return merge(cfg, resolution)


def resolve_run_config(cfg, resolution_path, smoke):
    """Only an explicitly supplied resolution may override the runtime baseline."""
    if resolution_path is None:
        if not smoke:
            raise ValueError(
                "Baseline choices pending: supply an agreed resolution file"
            )
        return merge(cfg, {})
    return apply_resolution(cfg, load(resolution_path))


_evaluate_orig = evaluate


def evaluate(*a, **k):  # execution-only (TSAI): release cached GPU memory before each evaluation
    torch.cuda.empty_cache()
    return _evaluate_orig(*a, **k)


class NonfiniteTrainingError(ValueError):
    pass


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in [
        "config",
        "tokenizer",
        "byte-table",
        "train-data",
        "heldout-data",
        "out",
    ]:
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument(
        "--runtime",
        type=Path,
        help="Harness-only runtime contract; dimensions remain lead-owned",
    )
    p.add_argument(
        "--resolution",
        type=Path,
        help="Explicit baseline overrides; smoke without this option preserves runtime settings",
    )
    p.add_argument(
        "--heldout-sources", type=Path, help="PR191 per-document source/slice sidecar"
    )
    p.add_argument(
        "--heldout-sha256", type=Path, help="Official results/heldout_v1.sha256 file"
    )
    p.add_argument(
        "--heldout-report",
        type=Path,
        help="Data-owner JSON provenance; see HARNESS_WEEK2.md",
    )
    p.add_argument(
        "--lr",
        type=float,
        help="Explicit LR override, recorded in manifest; no optimizer default",
    )
    p.add_argument(
        "--tokenizer-release", choices=sorted(TOKENIZER_RELEASES), default="v0",
        help="Select the pinned tokenizer hash and byte-reconstruction policy",
    )
    p.add_argument("--seed", type=int)
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    p.add_argument(
        "--consolidate-step-checks",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Check microbatch losses and pre-clip norm together; disable for baseline A/B",
    )
    p.add_argument(
        "--smoke",
        action="store_true",
        help="Marks output NOT a quality result and permits provisional choices",
    )
    p.add_argument("--smoke-steps", type=int, default=3)
    p.add_argument("--smoke-seq-len", type=int)
    p.add_argument("--smoke-batch-size", type=int)
    p.add_argument(
        "--logger-factory",
        help="module:function returning writer(out_dir) with write/flush/close",
    )
    p.add_argument(
        "--expert-load-every", type=int, default=0, metavar="STEPS",
        help="Record MoE routing picks every STEPS training steps (0 disables collection)",
    )
    p.add_argument(
        "--run-id", help="Shared job run ID (letters, digits, dots, dashes, underscores)"
    )
    p.add_argument(
        "--watchdog-s", type=float, default=os.environ.get("WATCHDOG_S", "0"),
        help="Step progress timeout in seconds (defaults to WATCHDOG_S or 0, which disables)",
    )
    p.add_argument("--stop-after", type=int)
    p.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="Smoke checks only: omit large checkpoint output",
    )
    p.add_argument("--checkpoint-store", help="Team 7 shared checkpoint root (directory or s3:// URI)")
    p.add_argument(
        "--checkpoint-interval-s", type=float,
        help="Wall-clock interval between saves (defaults to INTERVAL_S or 600)",
    )
    p.add_argument(
        "--checkpoint-at-start", action="store_true",
        help="Commit resumable step-0 state on a fresh run before training",
    )
    resume = p.add_mutually_exclusive_group()
    resume.add_argument(
        "--resume", type=Path, help="Only load your own trusted harness checkpoint"
    )
    resume.add_argument(
        "--resume-committed", action="store_true", help="Restore from the trusted Team 7 checkpoint store"
    )
    args = p.parse_args()
    if args.expert_load_every < 0:
        p.error("--expert-load-every must be nonnegative")
    if not args.smoke:
        if not args.checkpoint_store:
            p.error("Quality runs require --checkpoint-store and --run-id for Team 7 commits")
        if args.resume is not None:
            p.error("Quality runs resume through --resume-committed")
    if args.checkpoint_store is not None:
        if not args.checkpoint_store or not args.run_id or args.no_checkpoint:
            p.error("Team 7 checkpoints require a nonempty store and --run-id, and cannot use --no-checkpoint")
        if args.checkpoint_interval_s is None:
            try:
                args.checkpoint_interval_s = float(os.environ.get("INTERVAL_S", "600"))
            except ValueError:
                p.error("INTERVAL_S must be a finite positive number")
        if not math.isfinite(args.checkpoint_interval_s) or args.checkpoint_interval_s <= 0:
            p.error("Checkpoint interval must be a finite positive number")
    elif args.resume_committed or args.checkpoint_interval_s is not None or args.checkpoint_at_start:
        p.error("Committed resume, interval and start checkpoint options require --checkpoint-store")
    if not math.isfinite(args.watchdog_s) or args.watchdog_s < 0:
        p.error("--watchdog-s must be a finite nonnegative number")
    if args.watchdog_s:
        try:
            from week2.watchdog import StepWatchdog
        except ModuleNotFoundError as error:
            if error.name not in ("common", "common.events", "common.reasons"):
                raise
            p.error("Add teams/07-infrastructure to PYTHONPATH to use --watchdog-s")
    started = time.perf_counter()
    if args.out.exists() and any(args.out.iterdir()):
        p.error("Use a fresh output directory")
    cfg = load_runtime(args.config, args.runtime)
    try:
        cfg = resolve_run_config(cfg, args.resolution, args.smoke)
    except ValueError as error:
        p.error(str(error))
    if args.lr is not None:
        cfg["optim"]["lr"] = args.lr
    if args.seed is not None:
        cfg["run"]["seed"] = args.seed
    if args.smoke:
        cfg["run"]["steps"] = args.smoke_steps
        cfg["run"]["dtype"] = "fp32" if args.device == "cpu" else cfg["run"]["dtype"]
        if args.smoke_seq_len:
            cfg["model"]["block_size"] = args.smoke_seq_len
        if args.smoke_batch_size:
            cfg["run"]["batch_size"] = args.smoke_batch_size
            cfg["run"]["micro_batch_size"] = args.smoke_batch_size
    else:
        if args.device != "cuda" or cfg["run"]["dtype"] != "bf16":
            p.error("Lead plan requires GPU BF16 for quality runs")
        if (
            cfg["approval"]["status"] != "agreed"
            or not cfg["approval"]["reference"]
            or not cfg["evaluation"]["approved"]
        ):
            p.error(
                "Baseline/head/scoring agreements are pending; use smoke mode for development"
            )
        if not args.heldout_sources or not args.heldout_sha256:
            p.error("Quality scoring requires official heldout hash and slice sources")
        if not args.heldout_report:
            p.error("Data-owner heldout zero-match provenance required")
        if args.no_checkpoint:
            p.error("Quality runs must save checkpoint state")
        if args.smoke_seq_len or args.smoke_batch_size:
            p.error("Smoke shape overrides forbidden in quality runs")
    errors = validate(cfg)
    if errors:
        p.error("; ".join(errors))
    if args.smoke_steps <= 0 or (args.stop_after is not None and args.stop_after <= 0):
        p.error("Step counts must be positive")
    device = torch.device(args.device)
    if device.type == "cuda" and (not torch.cuda.is_available()):
        p.error("CUDA unavailable")
    if (
        device.type == "cuda"
        and cfg["run"]["dtype"] == "bf16"
        and torch.cuda.get_device_capability()[0] < 8
    ):
        p.error("Native BF16 hardware required; no silent FP16 substitution")
    seed = cfg["run"]["seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    artifacts = Artifacts(
        args.tokenizer, args.byte_table,
        expected_tokenizer_sha=TOKENIZER_RELEASES[args.tokenizer_release],
    )
    if len(artifacts.lengths) != cfg["model"]["vocab_size"]:
        p.error("Model/tokenizer vocabulary mismatch")
    if artifacts.pos_dim != cfg["model"]["ke_max_pos"]:
        p.error("Byte-table P differs from model config")
    train_hash = sha256(args.train_data)
    heldout_hash = sha256(args.heldout_data)
    if train_hash == heldout_hash:
        p.error("Training and holdout files are identical")
    data_load_started = time.perf_counter() if artifacts.normalize_input else None
    train = DocumentWindows(args.train_data, artifacts, cfg["model"]["block_size"])
    val = DocumentWindows(
        args.heldout_data,
        artifacts,
        cfg["model"]["block_size"],
        require_ids=not args.smoke,
        sources_path=args.heldout_sources,
    )
    if data_load_started is not None:
        data_load_seconds = time.perf_counter() - data_load_started
    if train.document_hashes & val.document_hashes:
        p.error("Exact document overlap between train and holdout")
    if args.heldout_sha256:
        lines = [
            line.split()
            for line in args.heldout_sha256.read_text(encoding='utf8').splitlines()
            if line.strip()
        ]
        if len(lines) != 1 or len(lines[0]) != 2 or lines[0][0] != heldout_hash:
            p.error('Official heldout checksum mismatch')
        if Path(lines[0][1].lstrip('*')).name != args.heldout_data.name:
            p.error('Official checksum names a different heldout file')
    if not args.smoke and set(val.slice_raw_bytes) != {
        'en',
        'code',
        'math',
        'sci',
        'hi',
        'bn',
        'ta',
        'te',
        'kn',
        'ml',
        'mr',
        'gu',
        'pa',
        'or',
        'as',
    }:
        p.error('Official holdout must provide all 15 slices')
    report = None
    if args.heldout_report:
        report = json.loads(args.heldout_report.read_text(encoding="utf8"))
        if (
            report.get("heldout_sha256") != heldout_hash
            or type(report.get("matches")) is not int
            or report["matches"] != 0
            or not report.get("fingerprint_set_id")
            or report.get("scope") != "full"
            or report.get("docs_checked") != val.document_count
        ):
            p.error(
                "Heldout report must bind this file/document count to full-set zero matches"
            )
    model = LanguageModel(cfg["model"], artifacts.bytes, artifacts.lengths).to(device)
    # Use the optimizer selected by the resolved arm configuration.
    optimizer = build_optimizer(model, cfg["optim"])
    stream = BatchStream(train, cfg["run"]["batch_size"], seed)

    def amp():
        return (
            torch.autocast(device_type="cuda", dtype=torch.bfloat16)
            if device.type == "cuda" and cfg["run"]["dtype"] == "bf16"
            else nullcontext()
        )

    source_files = [Path(__file__), *Path(__file__).with_name("week2").glob("*.py")]
    sources = {f.name: sha256(f) for f in source_files}
    identity = {
        "config": cfg,
        "artifacts": artifacts.identity(),
        "train_sha256": train_hash,
        "heldout_sha256": heldout_hash,
        "heldout_sources_sha256": (
            sha256(args.heldout_sources) if args.heldout_sources else None
        ),
        "heldout_checksum_sha256": (
            sha256(args.heldout_sha256) if args.heldout_sha256 else None
        ),
        "sources": sources,
        "device": str(device),
        "torch": torch.__version__,
        "smoke": args.smoke,
        "consolidate_step_checks": args.consolidate_step_checks,
    }
    if artifacts.normalize_input:
        identity["bpb_policy"] = (
            f"original UTF-8 bytes, with {args.tokenizer_release} tokenizer normalization"
        )
    if hasattr(model, "prior_identity"):
        from week2.kas_v2 import FIXTURE_SHA
        identity["kas_v2"] = {"codec_fixture_sha256": FIXTURE_SHA, "prior": model.prior_identity}
    # Resume checks bind the checkpoint to the resolved inputs and source hashes.
    identity_hash = hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode()
    ).hexdigest()
    checkpoint = None
    run_id = args.run_id
    if args.resume:
        checkpoint = torch.load(args.resume, map_location=device, weights_only=False)
        if checkpoint["identity_sha256"] != identity_hash:
            p.error("Resume code/config/artifact/data/device/software identity changed")
        saved_run_id = checkpoint.get("run_id")
        if saved_run_id is None:
            saved_run_id = sha256(args.resume)
        if run_id is not None and run_id != saved_run_id:
            p.error("--run-id does not match the checkpoint run ID")
        run_id = saved_run_id
    if run_id is None:
        run_id = uuid4().hex
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
        p.error("Run ID must begin with a letter or digit and use only letters, digits, dots, dashes and underscores")

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {
        **identity,
        "run_id": run_id,
        "identity_sha256": identity_hash,
        "baseline_commit": cfg["provenance"]["lead_snapshot"],
        "parameters": model.parameter_count(),
        "optimizer": describe(model, cfg["optim"]),
        "gpu": torch.cuda.get_device_name() if device.type == "cuda" else None,
        "status": "SMOKE_NOT_A_QUALITY_RESULT" if args.smoke else "AGREED_BASELINE_RUN",
        "heldout_provenance": report,
        "g8_external_writer": bool(args.logger_factory),
        "expert_load_every": args.expert_load_every,
        "token_budget_note": "Input positions include right padding; scored tokens/bytes reported separately",
        "train_documents": train.document_count,
        "heldout_documents": val.document_count,
    }
    if data_load_started is not None:
        manifest["data_load_seconds"] = data_load_seconds
    checkpointer = None
    checkpoint_errors = (NonfiniteTrainingError,)
    if args.checkpoint_store:
        try:
            from ckpt.ckpt import CheckpointError, Checkpointer
            from common.reasons import EXIT_FATAL, EXIT_RETRY, write_exit_note
        except ModuleNotFoundError as error:
            if error.name not in ("ckpt", "ckpt.ckpt"):
                raise
            p.error("Add teams/07-infrastructure to PYTHONPATH to use Team 7 checkpoints")

        checkpoint_errors += (CheckpointError,)
        probe_x, probe_y, _ = val.batch([0], device)

        @torch.no_grad()
        def probe(probe_model):
            training = probe_model.training
            try:
                probe_model.eval()
                with amp():
                    if cfg["model"].get("head_mode") == "kas_v2":
                        from week2.kas_v2 import checkpoint_probe
                        return checkpoint_probe(probe_model)
                    return float(scored_ntp_loss(probe_model, probe_x, probe_y))
            finally:
                probe_model.train(training)

        checkpointer = Checkpointer(
            run_id, str(args.out / "checkpoint-cache"), args.checkpoint_store,
            config_path=str(args.config), seed=seed,
            frozen_keys=("embedding.rows", "embedding.lengths") + (("codec.G", "codec.Phi") if hasattr(model, "codec") else ()), code_paths=source_files,
        )
        if not args.resume_committed and checkpointer.store.exists("latest.json"):
            p.error("Team 7 run ID already exists. Use --resume-committed or a fresh run ID")
        optimizers = tuple(o for _, o in optimizer.named) if isinstance(optimizer, Optimizers) else optimizer
        progress = CheckpointProgress(stream, identity_hash, run_id)
        manifest["team7_checkpoint"] = {
            "store": args.checkpoint_store,
            "run_id": run_id,
            "interval_s": args.checkpoint_interval_s,
        }
    if args.watchdog_s:
        manifest["watchdog_s"] = args.watchdog_s
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf8"
    )
    external = None
    rows = []
    trace = []
    ntp_trace = []
    completed = 0
    resumed_seconds = 0.0
    committed_path = None
    restored_step = None
    last_requested_step = None
    tokens = 0

    def checkpoint_exit(code, cause, detail):
        print(detail, file=sys.stderr)
        write_exit_note(code, cause, completed, detail)
        raise SystemExit(code)

    if checkpoint is not None:
        model.load_state_dict(checkpoint["model"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        stream.load_state_dict(checkpoint["stream"])
        torch.set_rng_state(checkpoint["torch_rng"].cpu())
        if checkpoint["cuda_rng"] is not None:
            torch.cuda.set_rng_state_all([v.cpu() for v in checkpoint["cuda_rng"]])
        random.setstate(checkpoint["python_rng"])
        np.random.set_state(checkpoint["numpy_rng"])
        completed = checkpoint["step"]
        trace = checkpoint["trace"]
        ntp_trace = checkpoint["ntp_trace"]
        rows = checkpoint["rows"]
        resumed_seconds = checkpoint["wall_seconds"]
    elif args.resume_committed:
        inactive_mtp = model.mtp_head is not None and cfg["model"]["mtp_weight"] == 0
        if inactive_mtp:
            # DCP initializes state for trainable parameters when preparing a restore.
            # This head did not contribute to the objective and has no optimizer state.
            model.mtp_head.requires_grad_(False)
        try:
            info = checkpointer.restore(model, optimizers, progress, probe)
            if info is None:
                checkpoint_exit(EXIT_FATAL, "CheckpointError", "No committed Team 7 checkpoint for this run ID")
        except CheckpointError as error:
            checkpoint_exit(EXIT_FATAL, type(error).__name__, str(error))
        finally:
            if inactive_mtp:
                model.mtp_head.requires_grad_(True)
        completed = info["step"]
        restored_step = completed
        tokens = info["tokens"]
        committed_path = info["from_path"]
        history = progress.history
        if completed == 0:
            optimizer.load_state_dict(history["initial_optimizer"])
        trace = history["trace"]
        ntp_trace = history["ntp_trace"]
        rows = history["rows"]
        resumed_seconds = history["wall_seconds"]

    if checkpoint is not None:
        tokens = sum(row.get("train/scored_tokens", 0) for row in rows)

    def save_committed(reason):
        nonlocal last_requested_step
        writer.flush()
        if external is not None:
            external.flush()
        progress.history = {
            "trace": trace, "ntp_trace": ntp_trace, "rows": rows,
            "wall_seconds": resumed_seconds + time.perf_counter() - started,
        }
        initial_optimizer = copy.deepcopy(optimizer.state_dict()) if reason == "start" else None
        inactive_mtp = reason == "start" and model.mtp_head is not None and cfg["model"]["mtp_weight"] == 0
        if initial_optimizer is not None:
            # DCP materializes lazy optimizer state when taking the initial snapshot.
            # Retain the original state for the first real update, also after restore.
            progress.history["initial_optimizer"] = initial_optimizer
        if inactive_mtp:
            model.mtp_head.requires_grad_(False)
        try:
            saved = checkpointer.save(
                completed, model, optimizers, progress, probe, tokens=tokens, reason=reason
            )
        finally:
            if inactive_mtp:
                model.mtp_head.requires_grad_(True)
            if initial_optimizer is not None:
                optimizer.load_state_dict(initial_optimizer)
        if saved:
            last_requested_step = completed
        return saved

    def log(row):
        for key in [
            "tokens_per_second",
            "loss_ntp",
            "loss_mtp",
            "loss",
            "lr",
            "gpu_alloc_gb",
            "gradient_norm",
        ]:
            row.setdefault(key, float(cfg["optim"]["lr"]) if key == "lr" else 0.0)
        writer.write(row)
        if external is not None:
            external.write(row)

    writer = JsonWriter(args.out, cfg["run"]["flush_every_steps"])
    stop_signal = None
    signal_handlers = {}

    def request_stop(signum, _frame):
        nonlocal stop_signal
        stop_signal = signal.Signals(signum).name

    watchdog = StepWatchdog(args.watchdog_s) if args.watchdog_s else None
    try:
        if checkpointer is not None:
            for signum in (signal.SIGTERM, getattr(signal, "SIGUSR1", None)):
                if signum is not None:
                    signal_handlers[signum] = signal.signal(signum, request_stop)
        if args.logger_factory:
            module, name = args.logger_factory.split(":", 1)
            external = getattr(importlib.import_module(module), name)(args.out)
        for row in rows:
            log(row)
        if watchdog is not None:
            watchdog.arm(completed)
        if not rows:
            row = dict(
                step=0,
                **evaluate(
                    model, val, 1, device, amp, max_batch_tokens=EVAL_BATCH_TOKENS
                ),
            )
            rows.append(row)
            log(row)
            if device.type == "cuda":
                torch.cuda.empty_cache()  # execution-only (TSAI)
        if args.checkpoint_at_start and not args.resume and not args.resume_committed:
            if not save_committed("start"):
                checkpoint_exit(EXIT_RETRY, "crash", "Step-0 Team 7 checkpoint was skipped")
        steps = cfg["run"]["steps"]
        if args.stop_after is not None:
            steps = min(steps, args.stop_after)
        timed_out = False
        checkpoint_deadline = (
            checkpoint_clock() + args.checkpoint_interval_s if checkpointer is not None else None
        )
        for step in range(completed + 1, steps + 1):
            if stop_signal is not None:
                break
            if checkpointer is not None and checkpointer.fenced:
                checkpoint_exit(EXIT_FATAL, "FencedError", "A newer attempt owns the checkpoint run")
            if (
                resumed_seconds + time.perf_counter() - started
                >= cfg["run"]["max_time_min"] * 60
            ):
                timed_out = True
                break
            if watchdog is not None:
                watchdog.arm(completed)
            if device.type == "cuda":
                torch.cuda.synchronize()
            tick = time.perf_counter()
            x, y, lengths = stream.next(device)
            optimizer.zero_grad(set_to_none=True)
            # TSAI recipe (21 Nov), unconfirmed on KE2: bag training (TST) for the first tst_frac of the steps.
            tst_on = tst_mod.active(step, cfg["run"]["steps"], cfg["run"])
            count = int((y != -100).sum())  # real scored tokens: logged, and the normal-training normaliser
            # TST normalises by scored bags instead; the logged token count stays the real one (Team 8's tokens per byte).
            bag_count = tst_mod.scored_bags(y, cfg["run"]["tst_bag"]) if tst_on else 0
            mtp_count = int((y[:, 1:] != -100).sum())
            total = 0.0
            ntp_value = 0.0
            mtp_value = 0.0
            micro_losses = []
            sample_expert_load = args.expert_load_every and step % args.expert_load_every == 0
            if sample_expert_load:
                model.start_expert_load()
            micro = cfg["run"]["micro_batch_size"]
            model.clear_router_bias_load()
            for start in range(0, len(x), micro):
                tx, ty = x[start : start + micro], y[start : start + micro]
                # Normalize each microbatch by the full batch target count.
                with amp():
                    mtp = None
                    if tst_on:
                        ntp = tst_mod.tst_loss(model, tx, ty, cfg["run"]["tst_bag"]) / max(bag_count, 1)
                    elif model.mtp_head is None:
                        ntp = scored_ntp_loss(model, tx, ty) / count
                    else:
                        logits, mtp_logits = model(tx, ty != -100, return_mtp=True)
                        ntp = token_nll(logits, ty).sum() / count
                        targets = torch.full_like(ty, -100)
                        targets[:, :-1] = ty[:, 1:]
                        mtp = token_nll(mtp_logits, targets).sum() / max(mtp_count, 1)
                    loss = (
                        ntp
                        if mtp is None or cfg["model"]["mtp_weight"] == 0
                        else ntp + cfg["model"]["mtp_weight"] * mtp
                    )
                if args.consolidate_step_checks:
                    mtp_log = mtp.detach() if mtp is not None else ntp.new_zeros(())
                    micro_losses.append(
                        torch.stack((loss.detach(), ntp.detach(), mtp_log))
                    )
                    loss.backward()
                else:
                    if not torch.isfinite(loss):
                        raise NonfiniteTrainingError("Nonfinite training objective")
                    if mtp is not None and not torch.isfinite(mtp):
                        raise NonfiniteTrainingError("Nonfinite MTP component")
                    loss.backward()
                    total += float(loss.detach())
                    ntp_value += float(ntp.detach())
                    if mtp is not None:
                        mtp_value += float(mtp.detach())
            model.update_router_bias()
            if not args.consolidate_step_checks:
                grads = [q.grad for q in model.parameters() if q.grad is not None]
                if grads and not bool(torch.isfinite(torch.stack(torch._foreach_norm(grads))).all()):
                    for name, param in model.named_parameters():
                        if param.grad is not None and not torch.isfinite(param.grad).all():
                            raise NonfiniteTrainingError("Nonfinite gradient: " + name)
                    raise NonfiniteTrainingError("Nonfinite gradient")
            norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), cfg["run"]["grad_clip"],
                error_if_nonfinite=not args.consolidate_step_checks,
            )
            if args.consolidate_step_checks:
                total, ntp_value, mtp_value = checked_step_losses(micro_losses, norm, model)
            # TSAI recipe (21 Nov): WSD scales both optimizers' peak rates; constant leaves them unchanged.
            scale = lr_scale(step, cfg["run"]["steps"], cfg["optim"])
            set_lr_scale(optimizer, scale)
            optimizer.step()
            if not bool(torch.isfinite(torch.stack(torch._foreach_norm([q.detach() for q in model.parameters()]))).all()):
                raise NonfiniteTrainingError(nonfinite_error_message("Nonfinite parameter after optimizer step", model))
            if device.type == "cuda":
                torch.cuda.synchronize()
            ms = (time.perf_counter() - tick) * 1000
            trace.append(total)
            ntp_trace.append(ntp_value)
            completed = step
            tokens += count
            if watchdog is not None:
                watchdog.arm(completed)
            row = {
                "step": step,
                "train/ce_loss": ntp_value,
                "loss_total": total,
                "loss_ntp": ntp_value,
                "loss_mtp": mtp_value if cfg["model"]["mtp"] else 0.0,
                "mtp_weight": cfg["model"]["mtp_weight"],
                "loss": ntp_value,
                "lr": cfg["optim"]["lr"] * scale,
                "gradient_norm": float(norm),
                "gradient_clipping_applied": float(norm) > cfg["run"]["grad_clip"],
                "train/scored_tokens": count,
                "train/input_positions": x.numel(),
                "train/utf8_bytes": int(lengths.sum()),
                "perf/step_ms": ms,
                "tokens_per_second": x.numel() / (ms / 1000),
                "gpu_alloc_gb": (
                    torch.cuda.memory_allocated() / 1024**3
                    if device.type == "cuda"
                    else 0.0
                ),
            }
            if sample_expert_load:
                row["expert_load"] = model.finish_expert_load()
            if (
                step % cfg["run"]["eval_every_steps"] == 0
                or step == cfg["run"]["steps"]
            ):
                row.update(
                    evaluate(
                        model, val, 1, device, amp, max_batch_tokens=EVAL_BATCH_TOKENS
                    )
                )
                if device.type == "cuda":
                    torch.cuda.empty_cache()  # execution-only (TSAI): free the eval cache so training does not thrash
            if cfg["optim"]["name"] == "muon":
                row["muon_lr"] = cfg["optim"]["muon_lr"] * scale
            rows.append(row)
            log(row)
            if stop_signal is not None:
                break
            if checkpoint_deadline is not None and step < steps and checkpoint_clock() >= checkpoint_deadline:
                save_committed("interval")
                checkpoint_deadline = checkpoint_clock() + args.checkpoint_interval_s
        if watchdog is not None:
            watchdog.disarm()
        # Interrupted segments must not introduce extra validation events into resume history.
        writer.flush()
        if external is not None:
            external.flush()
        if checkpointer is not None:
            if completed and completed not in (last_requested_step, restored_step):
                requested = save_committed("signal" if stop_signal else "final")
            else:
                requested = True
            committed = checkpointer.wait()
            if checkpointer.any_fenced():
                checkpoint_exit(EXIT_FATAL, "FencedError", "A newer attempt owns the checkpoint run")
            if stop_signal is not None:
                cause = "saved_and_stopped" if requested and committed else "crash"
                checkpoint_exit(EXIT_RETRY, cause, f"Stopped on {stop_signal} after step {completed}")
            if not requested or not committed or (
                completed == 0 and last_requested_step != 0 and restored_step != 0
            ):
                checkpoint_exit(EXIT_RETRY, "crash", "Final Team 7 checkpoint did not commit")
            if last_requested_step == completed:
                if checkpointer.last_commit_step != completed:
                    checkpoint_exit(EXIT_RETRY, "crash", "Final Team 7 checkpoint did not commit")
                committed_path = checkpointer.step_rel(checkpointer.branch, completed)
        wall = resumed_seconds + time.perf_counter() - started
        if not args.no_checkpoint:
            write_native_checkpoint(
                {
                    "model": model.state_dict(),
                    "optimizer": optimizer.state_dict(),
                    "stream": stream.state_dict(),
                    "torch_rng": torch.get_rng_state(),
                    "cuda_rng": (
                        torch.cuda.get_rng_state_all()
                        if torch.cuda.is_available()
                        else None
                    ),
                    "python_rng": random.getstate(),
                    "numpy_rng": np.random.get_state(),
                    "step": completed,
                    "identity_sha256": identity_hash,
                    "run_id": run_id,
                    "trace": trace,
                    "ntp_trace": ntp_trace,
                    "rows": rows,
                    "wall_seconds": wall,
                },
                args.out / "checkpoint.pt",
            )
        (args.out / "losses.txt").write_text(
            "\n".join(v.hex() for v in ntp_trace) + "\n", encoding="utf8"
        )
        (args.out / "total_losses.txt").write_text(
            "\n".join(v.hex() for v in trace) + "\n", encoding="utf8"
        )
        full = completed == cfg["run"]["steps"] and not timed_out
        (args.out / "summary.json").write_text(
            json.dumps(
                {
                    "status": (
                        "SMOKE"
                        if args.smoke
                        else ("COMPLETED" if full else "INCOMPLETE_NOT_A_RESULT")
                    ),
                    "run_id": run_id,
                    "steps": completed,
                    "wall_seconds": wall,
                    "timed_out": timed_out,
                    **({"team7_checkpoint_path": committed_path} if committed_path else {}),
                    "first_ce": ntp_trace[0] if ntp_trace else None,
                    "last_ce": ntp_trace[-1] if ntp_trace else None,
                    "final_model_sha256": model_hash(model),
                    "eligible_for_quality_comparison": full and not args.smoke,
                },
                indent=2,
            ),
            encoding="utf8",
        )
    except checkpoint_errors as error:
        if checkpointer is None:
            raise
        checkpoint_exit(EXIT_FATAL, type(error).__name__, str(error))
    finally:
        if watchdog is not None:
            watchdog.close()
        for signum, handler in signal_handlers.items():
            signal.signal(signum, handler)
        try:
            writer.close()
        finally:
            if external is not None:
                external.close()


if __name__ == "__main__":
    main()
