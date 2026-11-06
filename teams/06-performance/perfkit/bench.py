"""Time each part of the training step; write the run JSON, its Markdown and the live JSONL events.

    python -m perfkit.bench --config configs/tiny_cpu.yaml                    # laptop: proves it runs (~30 s)
    python -m perfkit.bench --level 3 --modes clean,layer,trace,checkpoint
    python -m perfkit.bench --level 3 --against results/runs/<first>.json     # 5% check against an earlier run
    python -m perfkit.bench --level 3 --repeat 2                              # two runs, each in a new process
    torchrun --nproc_per_node 2 -m perfkit.bench --modes comm model.ffn=moe   # MoE all-to-all, 2+ GPUs

--modes, --level, --steps, --warmup, --peak-tflops are shortcuts for bench.<key>; any key of configs/base.yaml
can be given as key=value. Modes (clean always runs):
  clean       step time, tokens/s, MFU / HFU, memory, GPU samples
  layer       every region up to bench.level, recorder overhead from alternating steps
  trace       torch.profiler trace (~/.cache/era-perf/traces/), top ops, host syncs; with layer, one small trace
              per slowest part
  checkpoint  model + optimizer save time and size
  comm        MoE all-to-all with the real payload (timed on 2+ GPUs under torchrun; one GPU records the payload)

Exit codes: 0 ok, 1 run JSON incomplete, 2 --against / --repeat found a part outside the 5% rule (report.gate),
3 out of memory, 4 no data. With --repeat, the first run that ends with another code stops the repeat with that code.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import random
import re
import socket
import subprocess
import sys
import time
import uuid
import warnings
from collections import deque
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataio.loader import Loader  # noqa: E402
from dataio.tokenizer import REVISION as TOKENIZER_REVISION, SHA256 as TOKENIZER_SHA256, VOCAB_SIZE as BRAHMIC_VOCAB  # noqa: E402
from models.config import load_config, model_config  # noqa: E402
from models.gpt import GPT  # noqa: E402
from models.optim import build_optimizer  # noqa: E402
from perfkit import metrics as M  # noqa: E402
from perfkit.events import JsonlWriter, StepTimingStreamer, gpu_sample_record  # noqa: E402
from perfkit import parts as P  # noqa: E402
from perfkit import timer as T  # noqa: E402
from perfkit.regions import phase, point, region, use_recorder  # noqa: E402
from perfkit.report import PASSED, ab_note, compare_config_value, compare_lines, gate  # noqa: E402
from perfkit.schema import validate_run  # noqa: E402

BENCH_VERSION = 1
CACHE = Path(os.environ.get("ERA_PERF_CACHE", "~/.cache/era-perf")).expanduser()
AMP = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": None}
MODES = ("clean", "layer", "trace", "checkpoint", "comm")
# Config that changes the work a step does: two runs that differ here are not compared (quick_compare),
# except in report.IMPL_SWITCHES (an A/B of one implementation switch, labelled by report.ab_note).
# (section, key); key None = the whole section.
COMPARE_CONFIG = [("model", None), ("optim", None), ("run", "compile"), ("run", "grad_clip"), ("data", "source")]


# ------------------------------------------------------------------------------ build

@dataclass
class Setup:
    """Everything one run needs, made once by build()."""

    cfg: dict
    mcfg: object
    device: torch.device
    dtype: str                    # the dtype actually used: bf16 | fp16 | fp32
    loader: Loader
    core: torch.nn.Module         # the GPT module (param_counts, moe_layers, state_dict)
    model: torch.nn.Module        # core, or torch.compile(core)
    opt: object                   # models.optim.Optimizers
    scaler: object = None
    grad_clip: float | None = None
    notes: list = field(default_factory=list)
    sample_step_callback: object = None
    step_timing_callback: object = None

    def autocast(self):
        amp = AMP[self.dtype]
        return torch.autocast(self.device.type, dtype=amp) if amp is not None else nullcontext()


def pick_device(name: str) -> torch.device:
    """run.device: auto picks cuda, then mps, then cpu; cuda without an index uses the current device."""
    if name == "auto":
        if torch.cuda.is_available():
            name = "cuda"
        elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            name = "mps"
        else:
            name = "cpu"
    d = torch.device(name)
    if d.type == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit("run.device=cuda but no CUDA GPU is visible")
        if d.index is None:
            d = torch.device("cuda", torch.cuda.current_device())
        torch.cuda.set_device(d)
    return d


def native_bf16() -> bool:
    """True when the GPU has native (not emulated) bf16."""
    try:
        return torch.cuda.is_bf16_supported(including_emulation=False)
    except TypeError:  # torch < 2.4
        return torch.cuda.get_device_capability()[0] >= 8


def choose_dtype(want: str, device: torch.device, notes: list) -> str:
    """The dtype the run can use, with a note for every fallback (bf16 -> fp16 without native bf16, ...)."""
    want = want or "fp32"
    if want not in AMP:
        raise ValueError(f"run.dtype={want!r}: bf16 | fp16 | fp32")
    if device.type == "cuda" and want == "bf16" and not native_bf16():
        notes.append("run.dtype=bf16 but this GPU has no native bf16: using fp16 + GradScaler")
        return "fp16"
    if device.type == "cpu" and want == "fp16":
        notes.append("run.dtype=fp16 on CPU: using bf16 autocast instead")
        return "bf16"
    if device.type == "mps" and want != "fp32":
        try:
            with torch.autocast("mps", dtype=AMP[want]):
                pass
        except Exception:
            notes.append(f"run.dtype={want} autocast is not supported on this MPS build: using fp32")
            return "fp32"
    return want


def resolve_batch(want) -> int:
    """run.batch_size: a positive number from the config. Nothing is picked from the device: set it in the
    YAML (B=32 does not fit a T4: at T=256 the fp32 logits of the 131K vocabulary and their gradient are 8 GiB)."""
    if isinstance(want, bool) or not isinstance(want, int) or want < 1:
        raise SystemExit(f"run.batch_size={want!r}: set a positive number in the config (e.g. 32, or 8 on a T4)")
    return want


def seed_everything(seed: int):
    """Seed Python, NumPy (when installed) and torch on every GPU."""
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def select_compile_model(core: torch.nn.Module, run: dict):
    """Keep eager/default behavior unchanged; allow opt-in compiler autotuning.

    The model configuration, optimizer, batch, dtype and LR schedule are untouched.
    """
    compile_mode = run.get("compile_mode", "default")
    allowed = ("default", "max-autotune-no-cudagraphs")
    if compile_mode not in allowed:
        raise ValueError(f"run.compile_mode={compile_mode!r} not in {allowed}")
    if not run["compile"]:
        return core
    if compile_mode == "default":
        return torch.compile(core)  # preserve the original compilation call
    return torch.compile(core, mode=compile_mode)


def build(cfg: dict, device: torch.device) -> Setup:
    """Config -> Setup: the loader, model, optimizer, scaler and dtype of one run."""
    mcfg = model_config(cfg)
    run, data = cfg["run"], cfg["data"]
    notes = []
    run["batch_size"] = resolve_batch(run["batch_size"])
    seed_everything(run["seed"])
    dtype = choose_dtype(run["dtype"], device, notes)
    loader = Loader(data["source"], run["batch_size"], mcfg.block_size, device, data_dir=data["dir"],
                    vocab_size=mcfg.vocab_size, seed=run["seed"], tokenizer_path=data["tokenizer_path"],
                    prefetch=data["prefetch"])
    schedule = cfg["optim"]["schedule"]
    if schedule != "constant":
        notes.append(f"optim.schedule={schedule} is ignored: bench times every step at the base learning rate")
    core = GPT(mcfg, loader.token_bytes(mcfg.ke_max_pos) if mcfg.embedding == "ke1" else None).to(device)
    core.train()
    model = select_compile_model(core, run)
    opt = build_optimizer(core, cfg["optim"])
    scaler = torch.amp.GradScaler("cuda") if (device.type == "cuda" and dtype == "fp16") else None
    if scaler is not None:
        notes.append("fp16 + GradScaler: scaler.step reads found_inf on the host, one sync per step inside opt "
                     "(docs/PARTS.md timing rule cannot hold for fp16)")
    clip = run["grad_clip"] or None
    return Setup(cfg, mcfg, device, dtype, loader, core, model, opt, scaler, clip, notes)


# ------------------------------------------------------------------------------ one step

def train_step(s: Setup):
    """One training step. Returns (host ms of the data fetch, loss tensor). Nothing here waits for the GPU; the step
    itself may (the fp16 GradScaler, the MoE loop dispatch).
    With data.prefetch the next batch is prepared after backward is queued; its host time is in the data ms."""
    t0 = time.perf_counter()
    with region("data", 1):
        x, y = s.loader.next_batch()
    data_ms = (time.perf_counter() - t0) * 1e3
    with region("fwd", 1), phase("fwd"), s.autocast():
        loss = s.model(x, y)[1]          # a memory-bounded ce_impl returns logits=None: use only [1]
    with region("bwd", 1), phase("bwd"):
        point("__bwd_start__")
        (s.scaler.scale(loss) if s.scaler is not None else loss).backward()
        point("__bwd_end__")
    if s.loader.prefetch_enabled:
        t0 = time.perf_counter()
        with phase("data"), region("prefetch", 3):
            s.loader.prefetch()
        data_ms += (time.perf_counter() - t0) * 1e3
    with region("opt", 1), phase("opt"):
        if s.scaler is not None:
            with region("opt.unscale", 2):
                s.opt.unscale(s.scaler)
        if s.grad_clip:
            with region("opt.clip", 2):
                torch.nn.utils.clip_grad_norm_(s.core.parameters(), s.grad_clip)
        s.opt.step(s.scaler)
        if s.scaler is not None:
            s.scaler.update()
        with region("opt.moe_bias", 3):
            for m in s.core.moe_layers():
                m.update_bias()
        s.opt.zero_grad()
    return data_ms, loss.detach()


def reversible_check(s: Setup) -> float:
    """Reconstruction error of the reversible stack on one batch, in the run dtype."""
    from models.reversible import reconstruction_error
    x, _ = s.loader.next_batch()
    s.core.eval()                         # do not count these tokens for the MoE bias update
    try:
        with torch.no_grad(), s.autocast():
            emb = s.core.embed(x)
            return reconstruction_error(emb, s.core.blocks)
    finally:
        s.core.train()


# ------------------------------------------------------------------------------ modes

def run_clean(s: Setup, n: int):
    """clean mode: n steps, one timer pair each (CUDA events on a GPU).
    Returns (clean section, last loss, peak memory)."""
    st = T.StepTimer(s.device, expected_steps=n)
    data, loss = [], None
    if s.device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(s.device)
    for step in range(n):
        if s.sample_step_callback is not None:
            s.sample_step_callback(step + 1)
        st.start()
        d, loss = train_step(s)
        pair = st.stop()
        data.append(d)
        if s.step_timing_callback is not None:
            s.step_timing_callback(step + 1, d, st.kind, pair)
    times = st.times_ms()
    clean = {"step_ms": T.stats(times), "data_ms": T.stats(data),
             "raw_step_ms": [round(t, 4) for t in times],
             "events_created_during_steps": st.events_created_during_steps}
    return clean, loss, M.memory(s.device)


def layer_pass(s: Setup, n: int, max_level: int, warm: int) -> dict:
    """warm recorded steps, then n steps with the recorder and n without, alternating. Returns the layer section
    for this max_level."""
    pool = T.EventPool() if s.device.type == "cuda" else None
    n_ev = 0
    for _ in range(warm):                 # the first recorded steps touch every region once
        rec = T.EventRecorder(s.device, max_level, pool)
        with use_recorder(rec):
            train_step(s)
        n_ev = rec.n_events()
        rec.collect()
    if pool is not None:
        pool.reserve(4 * n_ev + 64)       # room for a few steps in flight: no event is created while measuring
        created = pool.created
    on_t, off_t = (T.StepTimer(s.device, expected_steps=n),
                   T.StepTimer(s.device, expected_steps=n))
    order, pending, parts, data_host = [], deque(), [], []
    for i in range(2 * n):
        on = i % 2 == 1                   # recorder on every other step: overhead from neighbouring steps
        if on:
            rec = T.EventRecorder(s.device, max_level, pool)
            on_t.start()
            with use_recorder(rec):
                d, _ = train_step(s)
            on_t.stop()
            data_host.append(d)
            pending.append(rec)
        else:
            off_t.start()
            train_step(s)
            off_t.stop()
        order.append(on)
        while pending and pending[0].ready():          # never waits: only finished steps
            parts.append(T.step_parts(pending.popleft().collect(), max_level))
    while pending:
        parts.append(T.step_parts(pending.popleft().collect(), max_level))
    on_ms, off_ms = iter(on_t.times_ms()), iter(off_t.times_ms())
    seq = [(o, next(on_ms) if o else next(off_ms)) for o in order]
    out = {
        "level": max_level,
        "events_created_during_steps": (on_t.events_created_during_steps
                                        + off_t.events_created_during_steps),
        "overhead_pct": T.paired_overhead(seq),
        "step_ms": T.stats([ms for o, ms in seq if o]),
        "step_ms_recorder_off": T.stats([ms for o, ms in seq if not o]),
        "regions": T.aggregate(parts),
        "data_host_ms": T.stats(data_host),
        "events_per_step": n_ev,
        "steps": n,
    }
    if s.device.type == "cuda":
        out["data_note"] = ("regions['data'] is GPU-stream time between two events around the host fetch: the "
                            "host-to-device copy, or ~0 when the GPU is still busy with the previous step. "
                            "The host time of the fetch is data_host_ms.")
    if pool is not None and pool.created > created:
        out["events_created_while_measuring"] = pool.created - created
    return out


def run_layer(s: Setup, n: int, level: int, warm: int) -> dict:
    """layer mode: gated parts from a level <= 2 pass; at level 3, the parts inside a block from a second pass."""
    gated = min(level, 2)
    main = layer_pass(s, n, gated, warm)
    for r in main["regions"].values():
        r["pass"] = gated
    if level < 3:
        return main
    inner = layer_pass(s, n, level, warm)
    regions = {}
    for name, r in inner["regions"].items():          # inner order puts each part under its parent
        if r["level"] <= gated:
            if name in main["regions"]:
                regions[name] = main["regions"][name]
        else:
            r["pass"] = level
            regions[name] = r
    for name, r in main["regions"].items():
        regions.setdefault(name, r)
    out = {**main, "level": level, "regions": regions}
    out["inner_pass"] = {k: inner[k] for k in ("level", "overhead_pct", "step_ms", "step_ms_recorder_off",
                                               "events_per_step", "events_created_during_steps")}
    if "events_created_while_measuring" in inner:
        out["inner_pass"]["events_created_while_measuring"] = inner["events_created_while_measuring"]
    return out


def run_trace(s: Setup, steps: int, tag: str) -> dict:
    """trace mode: torch.profiler over `steps` steps after one warmup step; the kernel summary, the trace file and,
    on CUDA, the host syncs per step."""
    from torch.profiler import ProfilerActivity, profile, schedule

    tdir = CACHE / "traces"
    tdir.mkdir(parents=True, exist_ok=True)
    path = tdir / f"{tag}.json"
    cuda = s.device.type == "cuda"
    acts = [ProfilerActivity.CPU] + ([ProfilerActivity.CUDA] if cuda else [])
    rec = T.ProfilerRecorder(max_level=3)

    def export(p):
        try:
            p.export_chrome_trace(str(path))
        except Exception as e:  # a full disk must not lose the rest of the run
            print(f"[bench] could not write the trace: {e}")

    # One profiler cycle on purpose: its "clears events at the end of each cycle" warning is noise here.
    warnings.filterwarnings("ignore", message="Profiler clears events")
    with profile(activities=acts, schedule=schedule(wait=0, warmup=1, active=steps, repeat=1),
                 on_trace_ready=export) as prof:
        for _ in range(steps + 1):
            with use_recorder(rec):
                train_step(s)
            prof.step()
    T.sync(s.device)
    if cuda:
        out = T.kernel_summary(T.profiler_device_events(prof), steps)
    else:                                 # no CUDA (CPU or MPS): rank ops by their own CPU time instead
        ka = sorted(prof.key_averages(), key=lambda e: e.self_cpu_time_total, reverse=True)[:15]
        tot = sum(e.self_cpu_time_total for e in prof.key_averages()) or 1
        out = {"top_ops": [{"name": e.key[:160], "ms_per_step": e.self_cpu_time_total / 1e3 / steps,
                            "calls_per_step": e.count / steps, "pct": 100 * e.self_cpu_time_total / tot}
                           for e in ka],
               "gpu_busy_pct": None, "kernels_per_step": 0}
    out["trace_file"] = str(path)
    out["steps"] = steps
    if cuda:
        n, sites = T.count_syncs(lambda: train_step(s), root=ROOT)     # one extra step in sync debug mode
        out["host_syncs_per_step"] = n
        out["sync_sites"] = dict(list(sites.items())[:12])
    return out


def _to_cpu(obj, memo, pinned=None):
    """CPU copy of a (nested) state dict. pinned: {key: pinned CPU tensor} reused across saves; GPU tensors
    are copied into those buffers without blocking (one sync after the whole copy), as a real
    checkpointer that keeps its staging buffers does. None: plain .to("cpu")."""
    if isinstance(obj, torch.Tensor):
        # Keyed by what the tensor views, not by id(): state_dict() returns a new detach() per key, so a
        # tied weight comes back as two objects over one storage. Same key = one CPU copy, saved once.
        key = (obj.device, obj.untyped_storage().data_ptr(), obj.storage_offset(), tuple(obj.shape),
               obj.stride(), obj.dtype)
        if key not in memo:
            src = obj.detach()
            if pinned is not None and src.is_cuda:
                if key not in pinned:
                    pinned[key] = torch.empty_like(src, device="cpu", pin_memory=True)
                memo[key] = pinned[key].copy_(src, non_blocking=True)
            else:
                memo[key] = src.to("cpu")
        return memo[key]
    if isinstance(obj, dict):
        return {k: _to_cpu(v, memo, pinned) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(_to_cpu(v, memo, pinned) for v in obj)
    return obj


def run_checkpoint(s: Setup, repeats: int, tag: str) -> dict:
    """What a training checkpoint holds: model, every optimizer's state, the scaler. Timed in two parts:
    GPU -> CPU copy (into pinned buffers kept across saves), then serialise + write + fsync (so the page
    cache does not hide the disk). One extra save first, not counted: it allocates the pinned buffers
    and touches the file system, which made the first Colab A100 copy 557 ms against 343 ms in the next run."""
    cdir = CACHE / "ckpt"
    cdir.mkdir(parents=True, exist_ok=True)
    path = cdir / f"{tag}.pt"
    to_cpu, write, total, size = [], [], [], 0
    pinned = {} if s.device.type == "cuda" else None
    try:
        for i in range(repeats + 1):
            T.sync(s.device)
            t0 = time.perf_counter()
            state = {"model": s.core.state_dict(),
                     "optim": {name: o.state_dict() for name, o in s.opt.named},
                     "scaler": s.scaler.state_dict() if s.scaler is not None else None}
            cpu = _to_cpu(state, {}, pinned)
            T.sync(s.device)
            t1 = time.perf_counter()
            with open(path, "wb") as f:
                torch.save(cpu, f)
                f.flush()
                os.fsync(f.fileno())
            t2 = time.perf_counter()
            size = path.stat().st_size
            del state, cpu
            if i == 0:                            # the warm save
                continue
            to_cpu.append((t1 - t0) * 1e3)
            write.append((t2 - t1) * 1e3)
            total.append((t2 - t0) * 1e3)
    finally:
        path.unlink(missing_ok=True)
    save = T.stats(total)
    return {"save_ms": save, "to_cpu_ms": T.stats(to_cpu), "write_ms": T.stats(write),
            "size_mb": size / 2**20, "write_mb_per_s": size / 2**20 / (T.stats(write)["median"] / 1e3),
            "level": 2, "repeats": repeats, "discarded_first": True, "pinned": pinned is not None,
            "where": "local disk, ~/.cache/era-perf/ckpt (deleted after)"}


def a2a_plan(cfg: dict, mcfg, dtype: str) -> dict | None:
    """The expert-parallel all-to-all this config would do: B * T * top_k * d fp32 values per call (an upper bound),
    4 calls per MoE layer and step, 8 with the reversible stack."""
    if mcfg.ffn != "moe":
        return None
    B, Tn = cfg["run"]["batch_size"], mcfg.block_size
    k, d = mcfg.moe["top_k"], mcfg.n_embd
    nbytes = 4
    per_layer = 8 if mcfg.reversible else 4
    return {"bytes_per_call": B * Tn * k * d * nbytes, "payload_mb_per_call": B * Tn * k * d * nbytes / 2**20,
            "calls_per_layer": per_layer, "calls_per_step": per_layer * mcfg.n_layer, "dtype": dtype,
            "payload_dtype": "fp32", "level": 2}


def run_comm(plan: dict, device: torch.device, reps: int) -> dict:
    """Time all_to_all_single with the plan's payload on every rank; reports the slowest rank."""
    import torch.distributed as dist
    W = dist.get_world_size()
    dt = {"fp32": torch.float32, "fp16": torch.float16, "bf16": torch.bfloat16}[plan["payload_dtype"]]
    n = plan["bytes_per_call"] // torch.tensor([], dtype=dt).element_size()
    n -= n % W                            # all_to_all_single splits the buffer evenly across ranks
    inp = torch.randn(n, device=device).to(dt)
    out = torch.empty_like(inp)
    for _ in range(5):                    # warm the communicator before timing
        dist.all_to_all_single(out, inp)
    T.sync(device)
    dist.barrier()
    st = T.StepTimer(device, expected_steps=reps)
    for _ in range(reps):
        st.start()
        dist.all_to_all_single(out, inp)
        st.stop()
    per_call = T.stats(st.times_ms())
    worst = torch.tensor([per_call["median"]], device=device, dtype=torch.float64)
    dist.all_reduce(worst, op=dist.ReduceOp.MAX)
    worst = worst.item()
    # MAX across ranks, outside the measured communication loop.
    count = torch.tensor([st.events_created_during_steps], device=device, dtype=torch.int64)
    dist.all_reduce(count, op=dist.ReduceOp.MAX)
    max_rank_events = int(count.item())
    return {**plan, "measured": True, "world_size": W, "backend": dist.get_backend(),
            "events_created_during_steps": max_rank_events,
            "per_call_ms": per_call, "per_call_ms_slowest_rank": worst,
            "per_step_ms": worst * plan["calls_per_step"],
            "note": "isolated all-to-all, no overlap with compute; per_step_ms = slowest rank x calls_per_step"}


# ------------------------------------------------------------------------------ metadata and metrics

def run_metadata(s: Setup, config_file: str, overrides: list, tag: str,
                 run_id: str | None = None, node_id: str | None = None) -> dict:
    """perfkit.metrics.run_metadata (device, versions, git) plus what this run was."""
    meta = M.run_metadata(s.device)
    meta.update({
        "config_file": config_file, "overrides": overrides, "tag": tag,
        "run_id": run_id or uuid.uuid4().hex,
        "node_id": node_id or os.environ.get("G8_NODE_ID") or socket.gethostname(),
        "time": _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "dtype": s.dtype, "dtype_requested": s.cfg["run"]["dtype"], "notes": list(s.notes),
        "batch_size": s.loader.B, "seq_len": s.loader.T, "tokens_per_step": s.loader.B * s.loader.T,
        "vocab_size": s.mcfg.vocab_size, "data_source": s.cfg["data"]["source"],
        "tokenizer": {"name": "BrahmicTokenizer-131K", "revision": TOKENIZER_REVISION, "sha256": TOKENIZER_SHA256,
                      "vocab_size": s.loader.vocab_size},
        "lr_schedule": s.cfg["optim"]["schedule"],
        "bench_version": BENCH_VERSION,
        "timing": {"cuda": "cuda_events", "mps": "sync_per_boundary", "cpu": "perf_counter"}.get(s.device.type),
    })
    return meta


def process_ranks(device) -> tuple[int, int]:
    """Global and local process rank for live step events; standalone runs are rank zero."""
    def read(name, default):
        try:
            return int(os.environ.get(name, default))
        except (TypeError, ValueError):
            return int(default)

    local_default = device.index if device.type == "cuda" and device.index is not None else 0
    return read("RANK", 0), read("LOCAL_RANK", local_default)


def memory_with_identity(memory: dict | None, meta: dict) -> dict | None:
    """Attach the measured CUDA device and make the binary GiB unit explicit."""
    if memory is None:
        return None
    return {
        **memory,
        "unit": "GiB",
        "gpu": {"name": meta.get("gpu"), "index": meta.get("gpu_index"),
                "uuid": meta.get("gpu_uuid"), "pci_bus_id": meta.get("gpu_pci_bus_id")},
    }


def compute_metrics(s: Setup, step_ms: float, peak, peak_reason: str | None = None) -> dict:
    """Tokens/s from the clean step time; MFU and HFU from perfkit.metrics (method: docs/METRICS.md)."""
    tokens = s.loader.B * s.loader.T
    f = M.flops_per_token(s.core, s.loader.T, s.opt.flops(), tokens)
    tps = tokens / (step_ms / 1e3)
    return {"tokens_per_step": tokens, "tokens_per_s": tps, **f, "peak_tflops": peak,
            "mfu_method": M.DEFAULT_METHOD, "mfu_scope": "selected_gpu",   # local tokens/s over this GPU's peak
            **M.mfu(f, tps, peak, peak_reason)}


# ------------------------------------------------------------------------------ output

def _f(x, nd=2):
    """x with nd decimals, or '-' for None / NaN."""
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def summary(run: dict, gate_level: int) -> str:
    """The console summary printed after a run."""
    m, c, me = run["metrics"], run["clean"], run["meta"]
    st = c["step_ms"]
    lines = [
        "",
        f"{me['gpu']} | {me['dtype']} | B={me['batch_size']} T={me['seq_len']} V={me['vocab_size']} | "
        f"commit {str(me['commit'])[:10]}{' (DIRTY)' if me.get('dirty') else ''} | tag {me['tag']}",
        f"step  median {_f(st['median'])} ms  p10 {_f(st['p10'])}  p90 {_f(st['p90'])}  spread {_f(st['spread_pct'], 1)}%"
        f"   data {_f(c['data_ms']['median'], 3)} ms",
        f"      {m['tokens_per_s']:,.0f} tokens/s   MFU {_f(100 * m['mfu'], 1) + '%' if m['mfu'] else 'n/a'}"
        f"   HFU {_f(100 * m['hfu'], 1) + '%' if m['hfu'] else 'n/a'}"
        + (f"   peak mem {run['memory']['peak_allocated_gb']:.2f} GB" if run.get("memory") else ""),
    ]
    lay = run.get("layer")
    if lay:
        base = lay["step_ms"]["median"] or 1
        lines += ["", f"parts under the 5% rule (level <= {gate_level}), recorder overhead {_f(lay['overhead_pct'], 2)}%",
                  f"  {'part':<34}{'median ms':>11}{'p10..p90':>19}{'% step':>8}{'spread%':>9}{'lvl':>4}{'calls':>6}"]
        for name, r in lay["regions"].items():
            if r["level"] <= gate_level:
                # phase, then its parts, then the blocks of the stack: indented so the tree reads top-down
                indent = "" if ":" not in name else "    " if re.search(r":block\d+$", name) else "  "
                lines.append(f"  {indent + name:<34}{_f(r['median'], 3):>11}{_f(r['p10'], 2) + '..' + _f(r['p90'], 2):>19}"
                             f"{_f(100 * r['median'] / base, 1):>8}{_f(r['spread_pct'], 1):>9}{r['level']:>4}"
                             f"{r['calls_per_step']:>6}")
        inner = {}
        for name, r in lay["regions"].items():
            if r["level"] > gate_level:
                key = re.sub(r"expert\d+", "expert*", re.sub(r"block\d+", "block*", name))   # one row per part type
                inner[key] = inner.get(key, 0.0) + r["median"]
        if inner:
            lines += ["", "inside the blocks (information only, not gated; summed over layers), top 15:"]
            for k in sorted(inner, key=inner.get, reverse=True)[:15]:
                lines.append(f"  {k:<44}{_f(inner[k], 3):>10} ms{_f(100 * inner[k] / base, 1):>7}%")
    if run.get("checkpoint"):
        ck = run["checkpoint"]
        lines.append(f"\ncheckpoint save {_f(ck['save_ms']['median'], 1)} ms (to CPU {_f(ck['to_cpu_ms']['median'], 1)}, "
                     f"write {_f(ck['write_ms']['median'], 1)}), {ck['size_mb']:.1f} MB, {ck['write_mb_per_s']:.0f} MB/s")
    a2a = (run.get("comm") or {}).get("moe_a2a")
    if a2a:
        if a2a.get("measured"):
            lines.append(f"MoE all-to-all {_f(a2a['per_call_ms_slowest_rank'], 3)} ms/call x {a2a['calls_per_step']} "
                         f"= {_f(a2a['per_step_ms'], 1)} ms/step on {a2a['world_size']} GPUs ({a2a['backend']})")
        else:
            lines.append(f"MoE all-to-all not measured ({a2a['reason']}); {a2a['payload_mb_per_call']:.1f} MB/call, "
                         f"{a2a['calls_per_step']} calls/step")
    tr = run.get("trace")
    if tr and tr.get("parts"):
        lines.append("\nslowest parts (summed over layers):")
        pw = max(40, *(len(p["part"]) + 2 for p in tr["parts"]))
        for i, p in enumerate(tr["parts"], 1):
            lines.append(f"  {i}. {p['part']:<{pw}}{_f(p['ms'], 2):>10} ms{_f(p['pct'], 1):>7}%  trace {p['file'] or '-'}")
    sy = run.get("system")
    if sy:
        mt = sy["metrics"]
        get = lambda k: _f((mt.get(k) or {}).get("median"), 0)
        lines.append(f"GPU during clean ({sy['samples']} samples): util {get('gpu_util_pct')}%  mem {get('mem_used_mib')} MiB  "
                     f"SM {get('sm_clock_mhz')} MHz  {get('power_w')} W  {get('temp_c')} C")
    if tr and tr.get("gpu_busy_pct") is None:
        lines.append(f"trace (CPU run: no GPU numbers) -> {tr['trace_file']}")
    elif tr:
        lines.append(f"trace: GPU busy {_f(tr.get('gpu_busy_pct'), 1)}%, {tr['kernels_per_step']:.0f} kernels/step"
                     + (f", {tr['host_syncs_per_step']} host syncs/step" if "host_syncs_per_step" in tr else "")
                     + f"  ->  {tr['trace_file']}")
    return "\n".join(lines)


def quick_compare(a: dict, b: dict, tol_pct: float, gate_level: int, abs_tol_ms: float) -> tuple:
    """Console comparison of this run (a) with an earlier one (b), by the perfkit.report.gate rule.
    The official check is perfkit.report.compare."""
    problems = []
    for k in ("gpu", "dtype", "batch_size", "seq_len", "vocab_size"):
        if a["meta"].get(k) != b["meta"].get(k):
            problems.append(f"different {k}: {a['meta'].get(k)} vs {b['meta'].get(k)}")
    for section, key in COMPARE_CONFIG:                  # what changes the work a step does
        va = compare_config_value(a["config"], section, key)
        vb = compare_config_value(b["config"], section, key)
        if va != vb:
            problems.append(f"different {section} config" if key is None else
                            f"different {section}.{key}: {va} vs {vb}")
    pairs = [("step (clean)", a["clean"]["step_ms"]["median"], b["clean"]["step_ms"]["median"])]
    ra, rb = (a.get("layer") or {}).get("regions", {}), (b.get("layer") or {}).get("regions", {})
    gated = [n for n, r in ra.items() if r["level"] <= gate_level]
    gated += [n for n, r in rb.items() if r["level"] <= gate_level and n not in ra]     # a part only b has
    for name in gated:
        pairs.append((name, ra[name]["median"] if name in ra else None, rb[name]["median"] if name in rb else None))
    if a.get("checkpoint") and b.get("checkpoint"):
        pairs.append(("checkpoint save", a["checkpoint"]["save_ms"]["median"], b["checkpoint"]["save_ms"]["median"]))
    ca, cb = (a.get("comm") or {}).get("moe_a2a") or {}, (b.get("comm") or {}).get("moe_a2a") or {}
    if ca.get("measured") and cb.get("measured"):
        pairs.append(("moe all-to-all", ca["per_step_ms"], cb["per_step_ms"]))
    rows, ok = [], not problems
    for name, x, y in pairs:
        if x is None or y is None:
            rows.append((name, x, y, None, "MISSING"))
            ok = False
            continue
        diff, verdict = gate(x, y, tol_pct, abs_tol_ms)
        ok &= verdict in PASSED
        rows.append((name, x, y, diff, verdict))
    return rows, ok, problems


def free_path(out_dir: Path, tag: str) -> Path:
    """Choose a shared JSON/JSONL stem without overwriting either file from an earlier run."""
    path = out_dir / f"{tag}.json"
    i = 2
    while path.exists() or path.with_suffix(".jsonl").exists():
        path = out_dir / f"{tag}-{i}.json"
        i += 1
    return path


def write_run(run: dict, out_dir: Path, tag: str, path: Path | None = None) -> Path:
    """Write the run JSON (NaN / inf as null) to path or a free path; returns the path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = path or free_path(out_dir, tag)
    path.write_text(json.dumps(_finite(run), indent=1, default=str, allow_nan=False) + "\n")
    return path


def _finite(o):
    """NaN / inf -> None: the run JSON must stay valid JSON for report.py and G8."""
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, dict):
        return {k: _finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_finite(v) for v in o]
    return o


def _show(p: Path) -> str:
    """A path relative to teams/06-performance when it is inside it, else absolute."""
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def _slug(s: str) -> str:
    """A GPU name as a tag fragment: 'NVIDIA A100-SXM4-40GB' -> 'a100-sxm4-40gb'."""
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("nvidia", "")).strip("-") or "cpu"


# ------------------------------------------------------------------------------ main

def parse(argv):
    """(args, overrides): the shortcut flags become bench.<key>=value overrides."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "configs" / "base.yaml"),
                    help="default: configs/base.yaml")
    ap.add_argument("--tag", default=None, help="run name; default <config>_<gpu>_<time>")
    ap.add_argument("--run-id", default=None, help="shared experiment ID; defaults to a unique ID per benchmark run")
    ap.add_argument("--node-id", default=None, help="node identity for G8 (default: G8_NODE_ID or hostname)")
    ap.add_argument("--modes", default=None, help=f"comma list from {','.join(MODES)} (= bench.modes)")
    ap.add_argument("--level", type=int, default=None, help="1 phases, 2 layers, 3 inside layers (= bench.level)")
    ap.add_argument("--steps", type=int, default=None, help="measured steps per mode (= bench.steps)")
    ap.add_argument("--warmup", type=int, default=None, help="warmup steps (= bench.warmup)")
    ap.add_argument("--peak-tflops", type=float, default=None, help="(= bench.peak_tflops) for a GPU not in the peak table")
    ap.add_argument("--against", default=None, help="an earlier run JSON: check every gated part within tol_pct")
    ap.add_argument("--repeat", type=int, default=1,
                    help="run the benchmark N times and compare each run with the first (exit 2 above tol_pct)")
    ap.add_argument("overrides", nargs="*", help="key=value, e.g. run.batch_size=16 model.vocab_size=131072")
    a = ap.parse_intermixed_args(argv)        # key=value overrides may come before or after the flags
    ov = list(a.overrides)
    if a.modes:
        ov.append(f"bench.modes=[{a.modes}]")
    for key, val in (("level", a.level), ("steps", a.steps), ("warmup", a.warmup), ("peak_tflops", a.peak_tflops)):
        if val is not None:
            ov.append(f"bench.{key}={val}")
    return a, ov


def warn_timing_allocations(warns: list, count: int, mode: str) -> None:
    """Record a warning for CUDA event allocations inside timed iterations."""
    if count > 0:
        warns.append(f"{count} CUDA timing events were created during {mode} measured steps")


def run_once(a, overrides):
    """One complete benchmark run. Returns (exit code, path of the run JSON or None).
    Each --repeat run calls it in its own process (repeat_run)."""
    cfg = load_config(a.config, overrides)
    mcfg = model_config(cfg)              # fail early on a bad config
    b = cfg["bench"]
    modes = list(b["modes"])
    unknown = sorted(set(modes) - set(MODES))
    if unknown:
        raise SystemExit(f"unknown bench.modes {unknown}: {', '.join(MODES)}")
    warns = []

    # Distributed only for the all-to-all: every rank joins, then rank 0 carries on alone.
    world = int(os.environ.get("WORLD_SIZE", "1"))
    comm = None
    if world > 1:
        import torch.distributed as dist
        lr = int(os.environ.get("LOCAL_RANK", "0"))
        if torch.cuda.is_available():
            torch.cuda.set_device(lr)
            cfg["run"]["device"] = f"cuda:{lr}"
        dist.init_process_group("nccl" if torch.cuda.is_available() else "gloo",
                                timeout=_dt.timedelta(minutes=60))
        device = pick_device(cfg["run"]["device"])
        cfg["run"]["batch_size"] = resolve_batch(cfg["run"]["batch_size"])
        dtype = choose_dtype(cfg["run"]["dtype"], device, [])
        plan = a2a_plan(cfg, mcfg, dtype)
        if plan is not None and device.type == "cuda":
            comm = {"moe_a2a": run_comm(plan, device, b["comm_reps"])}
        rank = dist.get_rank()
        dist.destroy_process_group()
        if rank != 0:
            return 0, None
        if "comm" not in modes:
            modes.append("comm")

    device = pick_device(cfg["run"]["device"])
    config_file = os.path.relpath(Path(a.config).resolve(), ROOT)
    buckets = T.Buckets(device)
    try:
        with buckets("startup"):
            s = build(cfg, device)
    except FileNotFoundError as e:
        print(f"[bench] {e}\n[bench] or time without the shards: add data.source=synthetic")
        return 4, None
    tag = a.tag or f"{Path(a.config).stem}_{_slug(M.device_name(device))}_{_dt.datetime.now():%Y%m%d-%H%M%S}"
    meta = run_metadata(s, config_file, overrides, tag, run_id=a.run_id, node_id=a.node_id)
    out_dir = ROOT / Path(b["out_dir"]).expanduser()
    path = free_path(out_dir, tag)
    events_path = path.with_suffix(".jsonl")
    meta["events_jsonl"] = _show(events_path)
    print(f"[bench] {meta['gpu']} | {s.dtype} | B={s.loader.B} T={s.loader.T} V={s.mcfg.vocab_size} | "
          f"modes {','.join(modes)} | level {b['level']} | {b['steps']} steps after {b['warmup']} warmup")
    for n in s.notes:
        print(f"[bench] note: {n}")

    run = {"meta": meta, "config": cfg}
    try:
        if s.mcfg.reversible:
            err = reversible_check(s)
            meta["reconstruction_err"] = err
            if err > 1e-3:
                warns.append(f"reversible reconstruction error {err:.1e} > 1e-3: the backward rebuilds wrong inputs")
        with buckets("first_step"):          # compile / autotune happen here, timed apart from warmup
            _, loss0 = train_step(s)
        with buckets("warmup"):
            for _ in range(max(0, b["warmup"] - 1)):
                train_step(s)
        meta["loss_after_first_step"] = float(loss0)
        tel0 = M.gpu_telemetry(device)

        print("[bench] clean ...", flush=True)
        def emit_gpu_sample(row, step):           # one live gpu_sample JSONL event per nvidia-smi row
            reason_field = next((field for field in M.REASON_FIELDS if field in row), None)
            reason = row.get(reason_field) if reason_field else None
            gpu_index = row.get("index")
            gpu = {"name": row.get("name"), "index": int(gpu_index) if gpu_index is not None else None,
                   "uuid": row.get("uuid"), "pci_bus_id": row.get("pci.bus_id")}
            record = gpu_sample_record(
                run_id=meta["run_id"], node_id=meta["node_id"], gpu=gpu,
                metrics={key: row.get(field) for field, key in M.SAMPLE_FIELDS.items()},
                slowdown_flags=M.throttle_flags({"throttle_reasons": reason}) if reason_field else None,
                step=step,
                timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            )
            event_writer.write(record)

        print(f"[bench] live JSONL -> {_show(events_path)} (run_id={meta['run_id']}, node_id={meta['node_id']})",
              flush=True)
        rank, local_rank = process_ranks(device)
        with JsonlWriter(events_path) as event_writer:
            with StepTimingStreamer(event_writer, run_id=meta["run_id"], node_id=meta["node_id"],
                                    rank=rank, local_rank=local_rank) as step_streamer:
                with M.GpuSampler(device, on_sample=emit_gpu_sample) as sampler:
                    s.sample_step_callback = sampler.set_step
                    s.step_timing_callback = step_streamer.submit
                    try:
                        run["clean"], loss, mem = run_clean(s, b["steps"])
                    finally:
                        s.sample_step_callback = None
                        s.step_timing_callback = None
        system = sampler.summary()
        if sampler.callback_error:
            warns.append(f"could not write a live GPU sample: {sampler.callback_error}")
        if step_streamer.error:
            warns.append(f"could not write a live step timing event: {step_streamer.error}")
        if system:
            run["system"] = system
            if system.get("slowdown_samples"):
                warns.append(f"{system['slowdown_samples']} of {system['samples']} samples during the clean steps had "
                             f"a slowdown reason ({', '.join(system['slowdown_reasons'])}): may miss the 5% check")
        warn_timing_allocations(warns, run["clean"]["events_created_during_steps"], "clean")
        meta["loss_end"] = float(loss)
        if mem:
            run["memory"] = memory_with_identity(mem, meta)
        if not math.isfinite(meta["loss_end"]):
            warns.append(f"loss is {meta['loss_end']}: the numbers time a broken run")
        tel_busy = M.telemetry_during(device, lambda: [train_step(s) for _ in range(3)])   # untimed steps

        if "layer" in modes:
            print(f"[bench] layer (level {b['level']}) ...", flush=True)
            run["layer"] = run_layer(s, b["steps"], b["level"], b["layer_warmup"])
            lay = run["layer"]
            if lay["overhead_pct"] is not None and lay["overhead_pct"] > b["max_overhead_pct"]:
                warns.append(f"recorder overhead {lay['overhead_pct']:.1f}% > {b['max_overhead_pct']}%: "
                             "layer numbers are flagged")
            for pass_name, pass_data in (("layer", lay), ("layer.inner_pass", lay.get("inner_pass") or {})):
                pool_events = pass_data.get("events_created_while_measuring", 0)
                if pool_events > 0:
                    warns.append(f"{pool_events} recorder-pool CUDA events were created during {pass_name} measured steps")
            layer_events = (lay.get("events_created_during_steps", 0)
                            + lay.get("inner_pass", {}).get("events_created_during_steps", 0))
            warn_timing_allocations(warns, layer_events, "layer")
        if "trace" in modes:
            print("[bench] trace ...", flush=True)
            run["trace"] = run_trace(s, b["trace_steps"], tag)
        if "checkpoint" in modes:
            print("[bench] checkpoint ...", flush=True)
            run["checkpoint"] = run_checkpoint(s, b["ckpt_repeats"], tag)
        if "comm" in modes:
            if comm is None:
                plan = a2a_plan(cfg, s.mcfg, s.dtype)
                if plan is not None:
                    comm = {"moe_a2a": {**plan, "measured": False,
                                        "reason": "one GPU; run: torchrun --nproc_per_node 2 -m perfkit.bench ... --modes comm"}}
            run["comm"] = comm or {"moe_a2a": None}
            a2a = run["comm"].get("moe_a2a")
            if a2a:
                warn_timing_allocations(warns, a2a.get("events_created_during_steps", 0), "communication")
        tel1 = M.gpu_telemetry(device)
    except torch.cuda.OutOfMemoryError:
        Bn, Tn, V = s.loader.B, s.loader.T, s.mcfg.vocab_size
        print(f"[bench] out of GPU memory. The fp32 logits alone are {Bn * Tn * V * 4 / 2**30:.1f} GB "
              f"(B={Bn} x T={Tn} x V={V} x 4 bytes), twice that with their gradient.\n"
              f"[bench] try model.ce_impl=chunked, or run.batch_size={max(1, Bn // 2)}")
        return 3, None

    peak, _ = M.peak_tflops(meta["gpu"], s.dtype)
    peak = b["peak_tflops"] if b["peak_tflops"] is not None else peak     # bench.peak_tflops overrides the table
    peak_reason = M.peak_unavailable_reason(meta["gpu"], s.dtype, peak)
    if peak_reason == "invalid_peak_tflops":
        peak = None
    run["metrics"] = compute_metrics(s, run["clean"]["step_ms"]["median"], peak, peak_reason)
    if peak_reason and device.type == "cuda":
        warns.append(f"MFU/HFU unavailable for {meta['gpu']} / {s.dtype} ({peak_reason}); "
                     "set bench.peak_tflops to provide a positive peak")
    # PARTS.md section 2: startup = imports done, model + optimizer built; first_step includes torch.compile /
    # autotune when they run; warmup = the remaining warmup steps. Time and token goodput are still to write.
    run["goodput"] = {"badput_s": buckets.as_dict()}
    if device.type == "cuda":
        meta["telemetry"] = {"after_warmup": tel0, "during_steps": tel_busy, "end": tel1}
        warns += throttle_warnings(tel_busy, tel1)

    warns += rule_checks(run, modes, cfg)
    run["warnings"] = warns
    problems = validate_run(run)

    gate_level = cfg["report"]["gate_level"]
    if run.get("trace"):
        part_traces(run, path.parent / f"{path.stem}_parts", warns)
    print(summary(run, gate_level))
    path = write_run(run, out_dir, tag, path)
    print(f"\n[bench] run JSON -> {_show(path)}")
    print(f"[bench] event log complete -> {_show(events_path)}")
    try:
        from perfkit import report
        md = path.with_suffix(".md")
        md.write_text(report.render(run))
        print(f"[bench] report   -> {_show(md)}")
    except NotImplementedError:
        print("[bench] perfkit.report.render is still a stub: no .md written")
    for w in warns:
        print(f"[warn] {w}")
    for p in problems:
        print(f"[schema] {p}")
    code = 1 if problems else 0

    if a.against:
        other = json.loads(Path(a.against).read_text())
        rep = cfg["report"]
        tol, abs_tol, min_steps = rep["tol_pct"], rep["abs_tol_ms"], rep["min_compare_steps"]
        rows, ok, why = quick_compare(run, other, tol, gate_level, abs_tol)
        print(f"\nagainst {_show(Path(a.against))} (ms)")
        for line in compare_lines(rows, ok, why, ab_note(run, other), tol, gate_level, abs_tol):
            print(line)
        if b["steps"] < min_steps:
            print(f"[warn] bench.steps={b['steps']} < report.min_compare_steps={min_steps}: each part is the median "
                  f"of only {b['steps']} calls, too few for a stable comparison of very small parts")
        if not ok:
            code = code or 2
    return code, path


def part_traces(run: dict, out_dir: Path, warns: list):
    """The five slowest parts (from layer mode) and one small trace each, cut from the full trace (perfkit.parts)."""
    tr = run["trace"]
    if not run.get("layer"):
        tr["parts_note"] = "no layer mode in this run: the slowest parts and their traces need --modes layer,trace"
        return
    ranked = P.slowest_parts(run["layer"]["regions"], run["clean"]["step_ms"]["median"])
    try:
        cut = P.write_part_traces(tr["trace_file"], ranked, out_dir)
    except (OSError, ValueError) as e:                 # no trace file (export failed) or a broken one
        warns.append(f"could not cut the part traces from {tr['trace_file']}: {e}")
        cut = None
    for p, c in zip(ranked, cut or [{"region": P.instance(p), "file": None} for p in ranked]):
        p.pop("names")
        p.update(c)
        if p["file"]:
            p["file"] = _show(Path(p["file"]))
    tr["parts"] = ranked
    missing = [p["region"] for p in ranked if not p["file"]]
    if missing and cut is not None:                    # the file failed: already said above, not per region
        warns.append(f"no trace cut for {', '.join(missing)}: the region is not in the trace")


def _hard(code: int) -> bool:
    """A --repeat child that cannot be compared: 1 incomplete JSON (or a crash), 3 out of memory, 4 no data, or a
    kill by a signal (negative code, e.g. -9 from the out-of-memory killer). Only 0 (ok) and 2 (outside tol_pct)
    are verdicts."""
    return code not in (0, 2)


def repeat_cmd(argv, tag: str, against=None) -> list:
    """The command line of one --repeat run: the same arguments, one run, its own tag, --against when given.
    argparse keeps the last value of a repeated flag, so appending overrides the user's --tag / --repeat."""
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = [sys.executable, "-m", "perfkit.bench", *argv, "--repeat", "1", "--tag", tag]
    return cmd + (["--against", str(against)] if against else [])


def repeat_run(argv, tag: str, against=None) -> int:
    """One --repeat run in a new Python process. Returns its exit code.

    A second run in the same process after trace mode was 26% slower on host-bound parts (A100), and a second
    process started while the first held its GPU memory ran out of memory; separate processes agree within 2.5%."""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [str(ROOT), os.environ.get("PYTHONPATH")]))}
    print(f"\n[bench] repeat: {tag} in a new process", flush=True)
    return subprocess.run(repeat_cmd(argv, tag, against), env=env).returncode


def main(argv=None):
    """One run, or --repeat N runs compared with the first. Returns the exit code (module docstring)."""
    a, overrides = parse(argv)
    if a.repeat > 1 and a.run_id:
        raise SystemExit("--run-id is for one benchmark invocation; omit it with --repeat so each run gets a unique ID")
    if a.repeat <= 1 or int(os.environ.get("WORLD_SIZE", "1")) > 1:     # torchrun is for --modes comm only
        return run_once(a, overrides)[0]
    # The parent only starts the runs and never touches the GPU, so every run has the whole GPU to itself. (A parent
    # that ran run 1 itself kept ~30 GB reserved on a 40 GB A100, and run 2 ran out of memory.)
    out_dir = ROOT / Path(load_config(a.config, overrides)["bench"]["out_dir"]).expanduser()
    first = free_path(out_dir, a.tag or f"{Path(a.config).stem}_repeat_{_dt.datetime.now():%Y%m%d-%H%M%S}")
    code = repeat_run(argv, first.stem, a.against)
    if _hard(code) or not first.exists():
        return code if code > 0 else 1
    codes = [code]
    for k in range(2, a.repeat + 1):
        # <tag>-run2, <tag>-run3 ... next to the first JSON; every later run is checked against the first
        code = repeat_run(argv, f"{first.stem}-run{k}", first)
        codes.append(code)
        if _hard(code):
            return code if code > 0 else 1
    verdict = 2 if 2 in codes else 0
    # The same word the single run prints for --against, so a log reader finds one verdict per kind of check.
    print(f"\n[bench] repeat: {a.repeat} runs against {first.name}: {'FAIL' if verdict else 'PASS'}")
    return verdict


def throttle_warnings(busy: dict | None, end: dict | None) -> list:
    """From the samples taken while steps ran and at the end: a GPU at 83 C or more, then the driver's slowdown
    reasons; the SM clock alone only when the driver does not report them (an idle GPU drops its clock: A100
    1095 of 1410 MHz at 60 W)."""
    out = []
    try:
        hot = max((float(t["temperature.gpu"]) for t in (busy, end) if t), default=0.0)
        if hot >= 83:
            out.append(f"GPU at {hot:.0f} C: likely thermal throttling")
        flags = M.throttle_flags(busy)
        if flags:
            out.append(f"GPU slowed down while the steps ran ({', '.join(flags)}): a shared or throttled GPU "
                       "misses the 5% check")
        elif flags is None and busy and float(busy["clocks.sm"]) < 0.85 * float(busy["clocks.max.sm"]):
            out.append(f"SM clock {busy['clocks.sm']:.0f} MHz while the steps ran vs max "
                       f"{busy['clocks.max.sm']:.0f} (the driver gave no throttle reasons): may miss the 5% check")
    except (TypeError, ValueError, KeyError):
        pass
    return out


def rule_checks(run: dict, modes: list, cfg: dict) -> list:
    """Checks a run can make about itself: committed code, vocabulary, level, modes, spread, MPS, compile."""
    out = []
    me = run["meta"]
    if me.get("dirty"):
        out.append("uncommitted changes: Gate 1 numbers must come from committed code")
    if me.get("commit") is None:
        out.append("no commit ID (no .git): Gate 1 numbers need a git checkout of committed code; for other runs, "
                   "set PERF_COMMIT=<sha> so the run at least names its code")
    elif me.get("dirty") is None:
        out.append("could not tell whether the code is committed (no .git, or git status failed): Gate 1 numbers "
                   "must come from a git checkout of committed code")
    if me["vocab_size"] != BRAHMIC_VOCAB or (me.get("tokenizer") or {}).get("vocab_size") != BRAHMIC_VOCAB:
        out.append(f"rule 1a: timings must use the BrahmicTokenizer-131K vocabulary ({BRAHMIC_VOCAB}); "
                   f"this run used model.vocab_size={me['vocab_size']}")
    if "layer" in modes and cfg["bench"]["level"] < 3:
        out.append("rule 3a: parts inside a block were not timed; add --level 3 (reported, not gated)")
    wanted = ("checkpoint", "comm") if cfg.get("model", {}).get("ffn") == "moe" else ("checkpoint",)
    missing = [m for m in wanted if m not in modes]          # comm = the MoE all-to-all: dense models have none
    if missing:
        out.append(f"rule 3b: {' and '.join(missing)} not measured; add {','.join(missing)} to --modes")
    if run.get("layer"):
        noisy = [n for n, r in run["layer"]["regions"].items()
                 if r["level"] <= cfg["report"]["gate_level"] and (r["spread_pct"] or 0) > 10]
        if noisy:
            out.append(f"{len(noisy)} gated part(s) have p10..p90 spread > 10%, so may miss the 5% check: "
                       + ", ".join(noisy[:6]) + (f" (+{len(noisy) - 6} more)" if len(noisy) > 6 else ""))
    if me["device"] == "mps":
        out.append("MPS has no reliable timing events: parts were timed with a sync at every boundary")
    if cfg["run"]["compile"] and run.get("layer"):
        out.append("run.compile=true: regions inside compiled code are not timed reliably; trust clean and trace")
    return out


if __name__ == "__main__":
    sys.exit(main())
