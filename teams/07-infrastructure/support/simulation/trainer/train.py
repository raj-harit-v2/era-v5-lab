"""Test trainer: trains TinyLM with the V5 checkpoint, signal and watchdog rules.

In simple words: this is a stand-in for the real training script. It shows exactly what the real one
must do so that no paid GPU time is wasted:
- save on a timer, and also when told to stop (Slurm preemption, a spot notice, a sick node);
- after a stop signal, save first, then exit with 75 ("saved, run me again");
- never save a NaN; exit with 78 ("do not retry, a person must look");
- if no step finishes for too long (a hang), dump the stacks and exit 75 so the job restarts.

Runs as one process per rank: under Slurm (srun) or torchrun, or alone.
"""
import argparse
import collections
import faulthandler
import json
import math
import os
import signal
import statistics
import sys
import threading
import time

import torch
import torch.distributed as dist
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
CODE_PATHS = (os.path.abspath(__file__), os.path.join(HERE, "tiny.py"))   # code_sha256: trainer, model, loader
# support/simulation/ holds the trainer package; the team folder holds ckpt/ and common/.
sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "..", "..", "..")]
from ckpt.ckpt import (EXIT_DONE, EXIT_FATAL, EXIT_RETRY, Checkpointer, CheckpointError,  # noqa: E402
                       EnvMismatchError, FrozenChangedError, NonFiniteError, StrictLoadError, float_bits)
from common.events import emit  # noqa: E402
from common.reasons import write_exit_note  # noqa: E402
from ckpt.ds_ckpt import DSCheckpointer  # noqa: E402
from trainer.tiny import FROZEN_KEYS, SyntheticLoader, TinyLM, lm_loss, make_probe_fn  # noqa: E402

DEFAULT_CONFIG = os.path.join(HERE, "..", "config_v0.yaml")


def load_config(path: str) -> dict:
    with open(path) as f:
        doc = yaml.safe_load(f)
    return {s["key"]: s.get("value") for s in doc["settings"]}


def pick_device(name: str) -> torch.device:
    """cpu (Docker test, laptop) or cuda (Kaggle, the cloud). One GPU per rank: cuda:<LOCAL_RANK>."""
    if name == "cuda":
        dev = torch.device("cuda", int(os.environ.get("LOCAL_RANK", os.environ.get("SLURM_LOCALID", "0"))))
        torch.cuda.set_device(dev)
        return dev
    return torch.device("cpu")


def init_dist(device: torch.device):
    """Rank and world size from Slurm (srun) or torchrun. One process alone is world size 1."""
    if "SLURM_PROCID" in os.environ and "RANK" not in os.environ:
        os.environ["RANK"] = os.environ["SLURM_PROCID"]
        os.environ["WORLD_SIZE"] = os.environ["SLURM_NTASKS"]
        os.environ["LOCAL_RANK"] = os.environ.get("SLURM_LOCALID", "0")
    ws = int(os.environ.get("WORLD_SIZE", "1"))
    if ws > 1 and not dist.is_initialized():
        backend = "nccl" if device.type == "cuda" else "gloo"
        dist.init_process_group(backend=backend)
    return (dist.get_rank() if dist.is_initialized() else 0), ws


class LossSpikeError(Exception):
    pass


class Watchdog(threading.Thread):
    """Exit 75 with stack dumps if no step completes within `limit_s` (ADR 0003 §2)."""

    def __init__(self, limit_s: float):
        super().__init__(daemon=True)
        self.limit_s = limit_s
        self.last = time.monotonic()
        self.step = 0

    def beat(self, step: int):
        self.last, self.step = time.monotonic(), step

    def run(self):
        while True:
            time.sleep(min(1.0, self.limit_s / 4))
            idle = time.monotonic() - self.last
            if idle > self.limit_s:
                emit("train.watchdog", step=self.step, idle_s=round(idle, 2), limit_s=self.limit_s)
                faulthandler.dump_traceback(all_threads=True)
                write_exit_note(EXIT_RETRY, "hang_watchdog", self.step, f"no step for {idle:.0f} s",
                                rank=int(os.environ.get("RANK", os.environ.get("SLURM_PROCID", "0"))))
                os._exit(EXIT_RETRY)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=os.environ.get("RUN_ID", "local"))
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--global-batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=1e-3, help="smoke-test step size; optim.lr is still open")
    ap.add_argument("--interval-s", type=float, default=10.0, help="checkpoint interval (wall clock)")
    ap.add_argument("--step-sleep", type=float, default=0.0, help="test only: pretend each step takes longer")
    ap.add_argument("--watchdog-s", type=float, default=600.0)
    ap.add_argument("--local-root", default="/nvme/ckpt")
    ap.add_argument("--remote-root", default="/shared/ckpt")
    ap.add_argument("--from-step", type=int, help="rollback: restore this step, not latest")
    ap.add_argument("--skip", type=int, default=0, help="rollback: skip this many batches after the restore")
    ap.add_argument("--branch", help="rollback: name of the new branch")
    ap.add_argument("--allow-env-change", action="store_true")
    ap.add_argument("--inject-nan-at", type=int, default=int(os.environ.get("INJECT_NAN_AT", "-1")))
    ap.add_argument("--hang-at", type=int, default=int(os.environ.get("HANG_AT", "-1")),
                    help="test only: stop making progress at this step")
    ap.add_argument("--loss-log", help="append per-step loss bits (rank 0) to this JSONL file")
    ap.add_argument("--drill-dir", help="test only: a file <dir>/nan_at_step makes that step's loss NaN")
    ap.add_argument("--spike-ratio", type=float, default=float(os.environ.get("V5_SPIKE_RATIO", "1.5")),
                    help="loss above ratio x the median of the last --spike-window steps is a spike")
    ap.add_argument("--spike-steps", type=int, default=3, help="this many spike steps in a row -> hold (exit 78)")
    ap.add_argument("--spike-window", type=int, default=100)
    ap.add_argument("--spike-at", type=int, default=int(os.environ.get("SPIKE_AT", "-1")),
                    help="test only: multiply the loss by 10 for 5 steps from this step")
    ap.add_argument("--device", default=os.environ.get("V5_DEVICE", "cpu"), choices=["cpu", "cuda"])
    ap.add_argument("--fsdp", action="store_true", default=os.environ.get("V5_FSDP") == "1",
                    help="shard weights and optimizer with FSDP2 (fully_shard) instead of DDP, like the real run")
    ap.add_argument("--deepspeed", action="store_true", default=os.environ.get("V5_DEEPSPEED") == "1",
                    help="train and checkpoint with a DeepSpeed ZeRO engine (support/docs/deepspeed_impact.md)")
    ap.add_argument("--zero-stage", type=int, default=int(os.environ.get("V5_ZERO_STAGE", "1")), choices=[0, 1, 2, 3])
    ap.add_argument("--ds-precision", default=os.environ.get("V5_DS_PRECISION", "fp32"), choices=["fp32", "fp16", "bf16"],
                    help="DeepSpeed weights dtype: fp32 (CPU tests), fp16 (older GPUs: no bf16), bf16 (the real run)")
    ap.add_argument("--crash-at", type=int, default=int(os.environ.get("CRASH_AT", "-1")),
                    help="test only: raise an unhandled error at this step (exit 1)")
    a = ap.parse_args(argv)

    os.environ["RUN_ID"] = a.run_id
    cfg = load_config(a.config)
    seed, clip = int(cfg["run.seed"]), float(cfg["run.grad_clip"])
    assert cfg["optim.name"] == "adamw", "the harness optimiser is AdamW"
    # Determinism: two runs with the same seed must match (config run.seed, attention.impl=eager).
    # cuBLAS needs a fixed workspace to give the same bits every run (PyTorch reproducibility notes).
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    torch.manual_seed(seed)

    if a.device == "cuda":
        os.environ.setdefault("LOCAL_RANK", os.environ.get("SLURM_LOCALID", "0"))
    dev = pick_device(a.device)       # set the GPU before NCCL starts
    rank, ws = init_dist(dev)
    stop = {"sig": None}

    def on_signal(signum, _frame):
        stop["sig"] = signal.Signals(signum).name

    signal.signal(signal.SIGUSR1, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    model = TinyLM(seed).to(dev)
    ddp = model
    optim = None
    if a.deepspeed:
        # DeepSpeed owns the optimizer and the gradient sync. fp32 on CPU; fp16 on older GPUs (dynamic loss scale, its
        # state is in the checkpoint); bf16 on the GPU node, the real run. srun or torchrun has already started the process group (DS-3: no deepspeed launcher).
        import platform

        import deepspeed
        if dev.type == "cpu" and platform.machine() not in ("x86_64", "AMD64"):
            # DeepSpeed's CPU mode compiles a shared-memory all-reduce at start; its kernels are x86 only (AVX),
            # so on ARM (Apple-silicon Docker) the compile fails. Plain gloo does the same job. GPU runs never use it.
            deepspeed.ops.__compatible_ops__["deepspeed_shm_comm"] = False
        if not dist.is_initialized():      # one process alone: start a group of 1, or DeepSpeed looks for MPI
            for k, v in (("RANK", "0"), ("WORLD_SIZE", "1"), ("LOCAL_RANK", "0"), ("MASTER_ADDR", "127.0.0.1"),
                         ("MASTER_PORT", "29500")):
                os.environ.setdefault(k, v)
            dist.init_process_group(backend="nccl" if dev.type == "cuda" else "gloo")
        ds_cfg = {
            "train_batch_size": a.global_batch, "train_micro_batch_size_per_gpu": a.global_batch // ws,
            "gradient_accumulation_steps": 1, "gradient_clipping": clip,
            "optimizer": {"type": "AdamW", "params": {"lr": a.lr, "torch_adam": True}},
            # Bucket sizes are memory: DeepSpeed's default buckets hold 5e8 values (2 GB fp32) whatever the model
            # size, and 4 such trainers OOM the Docker VM. Size them to the model (impact doc §1.12); on the real
            # run they are a tuned, pinned part of ds_config (DS-7).
            "zero_optimization": {"stage": a.zero_stage, "reduce_scatter": False, "reduce_bucket_size": 2 ** 20,
                                  "allgather_bucket_size": 2 ** 20, "stage3_prefetch_bucket_size": 2 ** 20,
                                  "stage3_param_persistence_threshold": 0, "stage3_max_live_parameters": 2 ** 22},
            "checkpoint": {"tag_validation": "Fail", "use_node_local_storage": True},
            "steps_per_print": 10 ** 9, "wall_clock_breakdown": False,
        }
        if a.ds_precision == "fp16":
            ds_cfg["fp16"] = {"enabled": True, "loss_scale": 0, "initial_scale_power": 12}
        elif a.ds_precision == "bf16":
            ds_cfg["bf16"] = {"enabled": True}
        ddp, optim, _, _ = deepspeed.initialize(model=model, model_parameters=model.parameters(), config=ds_cfg)
    elif a.fsdp and ws > 1:
        # Every rank holds only its slice of each weight (DTensor). Checkpoint fingerprints, the probe forward
        # and DCP must then run on every rank together: this mode proves they do (test T16).
        try:
            from torch.distributed.fsdp import fully_shard
        except ImportError:  # torch < 2.6
            from torch.distributed._composable.fsdp import fully_shard
        for m in (model.ff1, model.ff2, model.head, model.head_mtp):
            fully_shard(m)
        ddp = fully_shard(model)
    elif ws > 1:
        ddp = torch.nn.parallel.DistributedDataParallel(model, device_ids=[dev.index] if dev.type == "cuda" else None)
    if optim is None:
        optim = torch.optim.AdamW(model.parameters(), lr=a.lr)
    loader = SyntheticLoader(seed, a.global_batch, rank, ws)
    probe = make_probe_fn(seed)
    ck = (DSCheckpointer if a.deepspeed else Checkpointer)(a.run_id, a.local_root, a.remote_root, config_path=a.config, seed=seed,
                                                       frozen_keys=FROZEN_KEYS, code_paths=CODE_PATHS)

    try:
        info = ck.restore(ddp, optim, loader, probe, from_step=a.from_step, skip=a.skip,
                          new_branch=a.branch, allow_env_change=a.allow_env_change)
    except (StrictLoadError, EnvMismatchError, CheckpointError) as e:
        if rank == 0:
            emit("restore.fatal", cause=type(e).__name__, detail=str(e)[:800])
            write_exit_note(EXIT_FATAL, type(e).__name__, None, str(e))
        print(f"FATAL restore: {e}", file=sys.stderr)
        return EXIT_FATAL
    step = info["step"] if info else 0
    tokens = info["tokens"] if info else 0
    if rank == 0:
        emit("train.started", step=step, world=ws, fresh=info is None, branch=ck.branch)

    def fenced_exit(at):
        """A newer attempt owns the run (FencedError): stop, and never retry this attempt."""
        if rank == 0:
            emit("train.exit", step=at, code=EXIT_FATAL, cause="FencedError")
            write_exit_note(EXIT_FATAL, "FencedError", at, "a newer attempt claimed the run; this one stopped")
        return EXIT_FATAL

    wd = Watchdog(a.watchdog_s)
    wd.start()
    last_save = time.monotonic()
    first = True
    window = collections.deque(maxlen=a.spike_window)   # recent losses, for the spike guard
    spike_run = 0
    loss_log = open(a.loss_log, "a") if (a.loss_log and rank == 0) else None

    try:
        while step < a.steps:
            t0 = time.monotonic()
            if step == a.hang_at:
                while True:          # a hang with no NCCL error: only the watchdog catches it
                    time.sleep(1)
            if step == a.crash_at:
                raise RuntimeError(f"injected crash at step {step}")
            if a.drill_dir and os.path.exists(os.path.join(a.drill_dir, "nan_at_step")):
                a.inject_nan_at = int(open(os.path.join(a.drill_dir, "nan_at_step")).read())
            if a.drill_dir and os.path.exists(os.path.join(a.drill_dir, "spike_at_step")):
                a.spike_at = int(open(os.path.join(a.drill_dir, "spike_at_step")).read())
            batch = loader.next().to(dev)
            ntp, mtp = lm_loss(ddp, batch)
            if step == a.inject_nan_at:
                ntp = ntp * float("nan")
            if 0 <= a.spike_at <= step < a.spike_at + 5:
                ntp = ntp * 10.0
            if not math.isfinite(ntp.item()):
                emit("train.nonfinite", step=step, loss=str(ntp.item()))
                raise NonFiniteError(f"loss is {ntp.item()} at step {step}")
            # Loss-spike guard (ADR 0001 §6): a loss far above its recent median, several steps in a row,
            # is a divergence that a NaN check does not see. Same answer as NaN: no save, hold for a rollback.
            lv = ntp.item()
            if len(window) >= a.spike_window // 2 and lv > a.spike_ratio * statistics.median(window):
                spike_run += 1
                if rank == 0:
                    emit("train.loss_spike", step=step, loss=round(lv, 6), median=round(statistics.median(window), 6),
                         run=spike_run)
                if spike_run >= a.spike_steps:
                    raise LossSpikeError(f"loss {lv:.4f} > {a.spike_ratio} x median for {spike_run} steps at {step}")
            else:
                spike_run = 0
                window.append(lv)
            if a.deepspeed:
                ddp.backward(ntp + 0.0 * mtp)   # the engine syncs grads, clips (gradient_clipping) and steps
                ddp.step()
            else:
                optim.zero_grad(set_to_none=True)
                (ntp + 0.0 * mtp).backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
                optim.step()
            step += 1
            tokens += a.global_batch * 32
            if a.step_sleep:
                time.sleep(a.step_sleep)
            step_s = time.monotonic() - t0
            wd.beat(step)
            if loss_log:
                loss_log.write(json.dumps({"step": step, "loss_bits": float_bits(ntp.item()),
                                           "branch": ck.branch}) + "\n")
                loss_log.flush()
            if first or step % 10 == 0:
                emit("train.step", step=step, loss=round(ntp.item(), 6), loss_mtp=round(mtp.item(), 6),
                     step_s=round(step_s, 4), rank=rank, first_after_start=first)
                first = False

            # Rank 0 owns the timer; any rank may have received a stop signal. All ranks agree.
            # Never save in the middle of a loss spike: the state may already be damaged.
            due = rank == 0 and step < a.steps and spike_run == 0 and time.monotonic() - last_save >= a.interval_s
            flags = torch.tensor([1 if due else 0,
                                  1 if stop["sig"] else 0,
                                  1 if ck.fenced else 0], dtype=torch.int32, device=dev)
            if dist.is_initialized():
                dist.all_reduce(flags, op=dist.ReduceOp.MAX)
            if flags[2]:
                return fenced_exit(step)
            if flags[1]:
                if rank == 0:
                    emit("train.stop_requested", step=step, signal=stop["sig"] or "peer")
                ck.save(step, ddp, optim, loader, probe, tokens, reason="signal")
                ok = ck.wait()
                if ck.any_fenced():
                    return fenced_exit(step)
                if rank == 0:
                    emit("train.exit", step=step, code=EXIT_RETRY, committed=ok)
                    write_exit_note(EXIT_RETRY, "saved_and_stopped", step,
                                    f"signal {stop['sig'] or 'from a peer rank'}; checkpoint committed: {ok}")
                return EXIT_RETRY
            if flags[0]:
                ck.save(step, ddp, optim, loader, probe, tokens, reason="interval")
                last_save = time.monotonic()

        ck.save(step, ddp, optim, loader, probe, tokens, reason="final")
        ok = ck.wait()
        if ck.any_fenced():
            return fenced_exit(step)
        if rank == 0:
            emit("train.exit", step=step, code=EXIT_DONE if ok else EXIT_RETRY, committed=ok)
            write_exit_note(EXIT_DONE if ok else EXIT_RETRY, "done" if ok else "crash", step,
                            "" if ok else "final checkpoint not committed")
        return EXIT_DONE if ok else EXIT_RETRY
    except (NonFiniteError, LossSpikeError, FrozenChangedError) as e:
        print(f"FATAL: {e}", file=sys.stderr)
        cause = {LossSpikeError: "loss_spike", FrozenChangedError: "FrozenChangedError"}.get(type(e), "nonfinite")
        if rank == 0:
            emit("train.exit", step=step, code=EXIT_FATAL, cause=cause,
                 hint=f"rollback: TRAIN_EXTRA='--from-step <last good> --skip <N> --branch <new>'")
            write_exit_note(EXIT_FATAL, cause, step, str(e))
        return EXIT_FATAL
    finally:
        if loss_log:
            loss_log.close()


if __name__ == "__main__":
    code = main()
    # Skip interpreter teardown: a peer that already left must not turn a clean exit into a hang.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
