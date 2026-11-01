"""MFU, HFU, memory, GPU telemetry, run metadata.  [implemented; time and token goodput still to write]

The one place these numbers are computed: perfkit.bench calls it, and G8 gets the same formulas (docs/METRICS.md).

    gpu_peak(device_name)          {"spec": "A100", "bf16": 312, "fp16": 312, "fp32": 19.5}, {} when unknown
    peak_tflops(device_name, dtype)  (dense peak TFLOPS for this dtype or None, spec or None)
    run_metadata(device)           the device, version and git fields of the run JSON "meta" (perfkit/schema.py)
    flops_per_token(model, T, opt_flops_per_step=0, tokens_per_step=None)
                                   model_flops_per_token, hw_flops_per_token, params_total, params_active
    mfu(flops, tokens_per_s, peak_tflops)   MFU/HFU and explicit unavailable-reason fields
    memory(device)                 peak allocated / reserved GB (None off CUDA)
    gpu_telemetry(device)          SM clock, temperature, power, throttle reasons from nvidia-smi (None off CUDA)
    telemetry_during(device, work) the same, sampled while work() keeps the GPU busy
    throttle_flags(tel)            slowdown reasons in a sample (power cap, thermal, ...), None if not reported
    GpuSampler(device, on_sample=...) streams per-GPU node samples during clean steps; run["system"] summarizes
                                   only the GPU used by the benchmark process

FLOPs per token (T = sequence length, L = layers, d = width, N_active from GPT.param_counts):
    model_flops_per_token = 6 * N_active + 12 * L * d * T      (PaLM; attention scores counted non-causal)
                            N_active counts each FFN's matrices: 2 * d * h for GELU, 3 * d * h for SwiGLU
                            (gate, up, down), times (top_k + shared) for an MoE layer; the elementwise
                            SiLU * up, like GELU, is not counted
    hw_flops_per_token    = model + 2 forwards of the stack when reversible (invert + recompute)
                            + 2 * head again when ce_impl=chunked (it recomputes the head)
                            + optimizer FLOPs per step (Muon Newton-Schulz) / tokens per step
MFU uses model FLOPs, HFU hardware FLOPs; both against the dense vendor peak for the dtype the run used.

Extra, still to write: goodput (time and tokens, badput buckets).
"""
from __future__ import annotations

import math
import os
import platform
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]

# Dense (no sparsity) vendor peak TFLOPS per dtype. First substring match wins, so specific names come
# first. An empty table = known GPU, unknown peak: MFU is left empty and the run says so (or pass --peak-tflops).
PEAKS = [
    ("B200", {"bf16": 2250, "fp16": 2250}),
    # H200 NVL has lower dense throughput than H200 SXM; keep this specific match before H200.
    ("H200 NVL", {"bf16": 835.5, "fp16": 835.5, "fp32": 60}),
    ("H200", {"bf16": 989, "fp16": 989, "fp32": 67}),
    ("H100 PCIe", {"bf16": 756, "fp16": 756, "fp32": 51}),
    ("H100 NVL", {}),
    ("H100", {"bf16": 989, "fp16": 989, "fp32": 67}),
    ("A100", {"bf16": 312, "fp16": 312, "fp32": 19.5}),
    ("L40S", {"bf16": 362, "fp16": 362, "fp32": 91.6}),
    ("L40", {"bf16": 181, "fp16": 181, "fp32": 90.5}),
    ("L4", {"bf16": 121, "fp16": 121, "fp32": 30.3}),
    ("A10G", {}),
    ("A10", {"bf16": 125, "fp16": 125, "fp32": 31.2}),
    # RTX 3060: 101 Tensor TFLOPS includes 2:4 sparsity; this table records dense peak.
    ("RTX 3060", {"bf16": 50.5, "fp16": 50.5, "fp32": 13}),
    ("RTX 4090", {"bf16": 165, "fp16": 165, "fp32": 82.6}),
    ("RTX 3090", {"bf16": 71, "fp16": 71, "fp32": 35.6}),
    ("V100", {"fp16": 125, "fp32": 15.7}),
    ("T4", {"fp16": 65, "fp32": 8.1}),
    ("P100", {"fp16": 18.7, "fp32": 9.3}),
]


# ------------------------------------------------------------------------------ device and peak

def gpu_peak(device_name: str) -> dict:
    for key, table in PEAKS:
        if key.lower() in device_name.lower():
            return {"spec": key, **table}
    return {}


def peak_tflops(device_name: str, dtype: str):
    """(peak TFLOPS for this dtype or None, gpu_spec or None)."""
    p = gpu_peak(device_name)
    return p.get(dtype), p.get("spec")


def peak_unavailable_reason(device_name: str, dtype: str, peak: float | None = None) -> str | None:
    """Stable reason code when no positive peak is available for an MFU/HFU denominator."""
    if peak is not None:
        return None if math.isfinite(peak) and peak > 0 else "invalid_peak_tflops"
    p = gpu_peak(device_name)
    if not p:
        return "unknown_gpu"
    if dtype not in p:
        return "unsupported_dtype"
    return "peak_tflops_unavailable"


def device_name(device) -> str:
    if device.type == "cuda":
        return torch.cuda.get_device_name(device)
    if device.type == "mps":
        return "Apple MPS"
    return platform.processor() or platform.machine() or "cpu"


def _sh(args, cwd=None):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10, check=True, cwd=cwd).stdout.strip()
    except Exception:
        return None


def git_state():
    """(commit, dirty). Dirty = any change in teams/06-performance outside results/, new files included
    (a new module the bench imports is code the commit ID does not name). Not counted: __pycache__,
    .pytest_cache, .ipynb_checkpoints, .DS_Store (they appear without anyone editing code).
    dirty is None when git status cannot run; commit is then PERF_COMMIT when there is no .git."""
    commit = _sh(["git", "rev-parse", "HEAD"], cwd=ROOT)
    if commit is None:                    # e.g. a Colab upload without .git
        return os.environ.get("PERF_COMMIT"), None
    # Python and pytest caches, notebook checkpoints (Colab) and Finder files (macOS) are not code: they appear
    # without anyone editing a file (no .gitignore covers them, and pr-guard allows none in the team folder).
    status = _sh(["git", "status", "--porcelain", "--untracked-files=all", "--", ".", ":(exclude)results",
                  ":(exclude,glob)**/__pycache__/**", ":(exclude,glob)**/.pytest_cache/**",
                  ":(exclude,glob)**/.ipynb_checkpoints/**", ":(exclude,glob)**/.DS_Store"], cwd=ROOT)
    return commit, bool(status) if status is not None else None


_SMI = "name,uuid,pci.bus_id,driver_version,pstate,clocks.sm,clocks.max.sm,clocks.mem,temperature.gpu,power.draw,power.limit"


def _smi_select(device) -> str:
    """The nvidia-smi --id for this device, by PCI bus ID: nvidia-smi and CUDA may number GPUs differently."""
    try:
        props = torch.cuda.get_device_properties(device)
        dom, bus, dv = (getattr(props, f"pci_{k}_id", None) for k in ("domain", "bus", "device"))
    except (AssertionError, RuntimeError):
        dom = bus = dv = None
    if all(isinstance(v, int) for v in (dom, bus, dv)):
        return f"--id={dom:08X}:{bus:02X}:{dv:02X}.0"
    return f"--id={device.index or 0}"


def gpu_telemetry(device) -> dict | None:
    """SM clock, temperature and power now: explains a 5% miss on a shared or hot GPU."""
    if device.type != "cuda":
        return None
    sel = _smi_select(device)
    out = _sh(["nvidia-smi", sel, f"--query-gpu={_SMI}", "--format=csv,noheader,nounits"])
    if not out:
        return None
    vals = [v.strip() for v in out.splitlines()[0].split(",")]
    res = {}
    for k, v in zip(_SMI.split(","), vals):
        try:
            res[k] = v if k in ("name", "uuid", "pci.bus_id", "driver_version", "pstate") else float(v)
        except ValueError:
            res[k] = v
    for field in REASON_FIELDS:
        r = _sh(["nvidia-smi", sel, f"--query-gpu={field}", "--format=csv,noheader"])
        if r:
            try:
                res["throttle_reasons"] = int(r.splitlines()[0].strip(), 16)
                break
            except ValueError:
                pass
    return res


REASON_FIELDS = ("clocks_event_reasons.active", "clocks_throttle_reasons.active")   # new name, old name


# nvidia-smi clock event reasons that mean the GPU was slowed down. GpuIdle (0x1), application clocks (0x2),
# sync boost (0x10) and display clocks (0x100) are not slowdowns: a GPU sampled between steps reports GpuIdle.
SLOWDOWN = {0x4: "SwPowerCap", 0x8: "HwSlowdown", 0x20: "SwThermalSlowdown", 0x40: "HwThermalSlowdown",
            0x80: "HwPowerBrakeSlowdown"}


def throttle_flags(tel: dict | None) -> list | None:
    """The slowdown reasons active in a telemetry sample; None when the driver did not report them."""
    if not tel or "throttle_reasons" not in tel:
        return None
    return [name for bit, name in SLOWDOWN.items() if tel["throttle_reasons"] & bit]


def telemetry_during(device, work, delay_s: float = 0.2) -> dict | None:
    """gpu_telemetry sampled from a thread while work() runs (a few untimed steps), so the clock and the
    reasons describe a busy GPU. Sampling after the steps sees an idle GPU at a lowered clock."""
    if device.type != "cuda":
        work()
        return None
    import threading
    box = {}

    def sample():
        time.sleep(delay_s)
        box["tel"] = gpu_telemetry(device)
    t = threading.Thread(target=sample, daemon=True)
    t.start()
    work()
    t.join(timeout=30)
    return box.get("tel")


# nvidia-smi query field -> key in run["system"]["metrics"] (docs/METRICS.md says what each one means)
SAMPLE_FIELDS = {"utilization.gpu": "gpu_util_pct", "utilization.memory": "mem_util_pct",
                 "memory.used": "mem_used_mib", "clocks.sm": "sm_clock_mhz", "clocks.mem": "mem_clock_mhz",
                 "power.draw": "power_w", "temperature.gpu": "temp_c"}


class GpuSampler:
    """System metrics while the measured steps run, for G8 (docs/METRICS.md).

        with GpuSampler(device) as s:
            run_clean(...)
        run["system"] = s.summary()        # None off CUDA or without nvidia-smi

    One nvidia-smi child process queries all visible GPUs on this node and writes samples to a reader thread.
    Optional on_sample callbacks can stream each GPU sample to JSONL while training continues; no CUDA
    synchronization is introduced. summary() returns aggregates for the benchmark's selected device only.
    """

    def __init__(self, device, interval_ms: int = 1000, on_sample=None):
        self.device, self.interval_ms = device, interval_ms
        self.on_sample = on_sample
        self.identity_fields = ["index", "name", "uuid", "pci.bus_id"]
        self.fields = list(SAMPLE_FIELDS)
        self.target_index = None
        self.target_pci_bus_id = None
        if device.type == "cuda":
            self.target_index = device.index if device.index is not None else torch.cuda.current_device()
            try:
                p = torch.cuda.get_device_properties(device)
                dom, bus, dv = (getattr(p, f"pci_{k}_id", None) for k in ("domain", "bus", "device"))
                if all(isinstance(v, int) for v in (dom, bus, dv)):
                    self.target_pci_bus_id = f"{dom:08X}:{bus:02X}:{dv:02X}.0"
            except (AssertionError, RuntimeError):
                pass
        self.reason = None
        self.started = False
        self.rows = []
        self.current_step = None
        self._proc = self._reader = None
        self.callback_error = None

    def set_step(self, step: int) -> None:
        """Publish the current clean-step index to the asynchronous sampler, without device synchronization."""
        self.current_step = int(step)

    def _read_samples(self):
        """Consume samples as they arrive; optional JSONL callbacks run off the timed training thread."""
        if self._proc is None or self._proc.stdout is None:
            return
        for line in self._proc.stdout:
            row = self.parse_line(line)
            if row is None:
                continue
            self.rows.append(row)
            if self.on_sample is not None:
                try:
                    self.on_sample(row, self.current_step)
                except Exception as exc:  # telemetry output must not abort model timing
                    self.callback_error = str(exc)

    def __enter__(self):
        if self.device.type != "cuda" or shutil.which("nvidia-smi") is None:
            return self
        self.reason = next((f for f in REASON_FIELDS
                            if _sh(["nvidia-smi", f"--query-gpu={f}", "--format=csv,noheader"])), None)
        query = self.identity_fields + self.fields + ([self.reason] if self.reason else [])
        # Query all GPUs once per node. A single collector process can then provide distinct device samples
        # without one nvidia-smi child per GPU or duplicate rows from every distributed rank.
        self._proc = subprocess.Popen(["nvidia-smi", f"--query-gpu={','.join(query)}",
                                       "--format=csv,noheader,nounits", f"--loop-ms={self.interval_ms}"],
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self._reader = threading.Thread(target=self._read_samples, name="perfkit-gpu-sampler", daemon=True)
        self._reader.start()
        self.started = True
        return self

    def __exit__(self, *exc):
        if self._proc is None:
            return False
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait()
        if self._reader is not None:
            self._reader.join(timeout=5)
        if self._proc.stdout is not None:
            self._proc.stdout.close()
        self._proc = None
        self._reader = None
        return False

    def parse_line(self, line: str) -> dict | None:
        """One GPU CSV row -> identity and numeric fields; None for the wrong number of values."""
        query = self.identity_fields + self.fields + ([self.reason] if self.reason else [])
        vals = [v.strip() for v in line.split(",")]
        if len(vals) != len(query):
            return None
        row = {}
        for f, v in zip(query, vals):
            if f in ("name", "uuid", "pci.bus_id"):
                row[f] = None if v in ("[N/A]", "[Not Supported]") else v
            else:
                try:
                    row[f] = int(v, 16) if f == self.reason else float(v)
                except ValueError:                    # [N/A], [Not Supported]
                    row[f] = None
        return row

    def _selected_rows(self):
        """Rows for the benchmark's CUDA device, preserving the original per-run summary scope."""
        if self.target_pci_bus_id:
            matched = [r for r in self.rows if r.get("pci.bus_id", "").upper() == self.target_pci_bus_id.upper()]
            if matched:
                return matched
        return [r for r in self.rows if r.get("index") == self.target_index]

    def summary(self) -> dict | None:
        if not self.started:
            return None
        from perfkit.timer import stats
        selected = self._selected_rows()
        out = {"source": f"nvidia-smi --loop-ms={self.interval_ms}", "interval_ms": self.interval_ms,
               "during": "clean steps", "samples": len(selected), "metrics": {},
               "gpu": {"index": self.target_index, "pci_bus_id": self.target_pci_bus_id}}
        for f, key in SAMPLE_FIELDS.items():
            vals = [r[f] for r in selected if r.get(f) is not None]
            if vals:
                st = stats(vals)
                out["metrics"][key] = {k: st[k] for k in ("min", "median", "max", "mean")}
        if self.reason:
            flagged = [f for r in selected if r.get(self.reason) is not None
                       and (f := throttle_flags({"throttle_reasons": r[self.reason]}))]
            out["slowdown_samples"] = len(flagged)
            out["slowdown_reasons"] = sorted({n for names in flagged for n in names})
        return out


def run_metadata(device) -> dict:
    """gpu, gpu_spec, torch, cuda, driver, device, commit, dirty, python (+ compute capability, SM count,
    memory, GPU count and telemetry_start on CUDA). The bench adds the run fields (config, tag, dtype, ...)."""
    commit, dirty = git_state()
    name = device_name(device)
    tel = gpu_telemetry(device)
    meta = {
        "gpu": name, "gpu_spec": gpu_peak(name).get("spec"),
        "torch": torch.__version__,
        "cuda": torch.version.cuda if device.type == "cuda" else None,
        "driver": (tel or {}).get("driver_version") if device.type == "cuda" else None,
        "device": device.type, "commit": commit, "dirty": dirty,
        "python": platform.python_version(),
    }
    if device.type == "cuda":
        p = torch.cuda.get_device_properties(device)
        gpu_index = device.index if device.index is not None else torch.cuda.current_device()
        dom, bus, dv = (getattr(p, f"pci_{key}_id", None) for key in ("domain", "bus", "device"))
        pci_bus_id = (tel or {}).get("pci.bus_id")
        if pci_bus_id is None and all(isinstance(v, int) for v in (dom, bus, dv)):
            pci_bus_id = f"{dom:08X}:{bus:02X}:{dv:02X}.0"
        gpu_uuid = (tel or {}).get("uuid") or getattr(p, "uuid", None)
        meta.update(compute_capability=f"{p.major}.{p.minor}", sm_count=p.multi_processor_count,
                    gpu_mem_gb=round(p.total_memory / 2**30, 1), gpu_count=torch.cuda.device_count(),
                    gpu_index=gpu_index, gpu_uuid=str(gpu_uuid) if gpu_uuid is not None else None,
                    gpu_pci_bus_id=pci_bus_id,
                    telemetry_start=tel)
    return meta


# ------------------------------------------------------------------------------ FLOPs, MFU, memory

def flops_per_token(model, T: int, opt_flops_per_step: float = 0.0, tokens_per_step: int | None = None) -> dict:
    """model: a models.gpt.GPT. See the module docstring for the formulas."""
    m = model.cfg
    total, active = model.param_counts()
    L, d = m.n_layer, m.n_embd
    model_fpt = 6 * active + 12 * L * d * T
    head = model.head.weight.numel() + (model.mtp_head.weight.numel() if m.mtp else 0)
    ke = model.tok.proj.weight.numel() if m.embedding in ("ke1", "ke2") else 0
    stack_fwd = 2 * (active - head - ke) + 4 * L * d * T
    hw = model_fpt + (2 * stack_fwd if m.reversible else 0) + (2 * head if m.ce_impl == "chunked" else 0)
    if opt_flops_per_step and tokens_per_step:
        hw += opt_flops_per_step / tokens_per_step
    return {"model_flops_per_token": model_fpt, "hw_flops_per_token": hw,
            "params_total": total, "params_active": active}


def mfu(flops: dict, tokens_per_s: float, peak_tflops: float | None,
        peak_reason: str | None = None) -> dict:
    """Return MFU/HFU plus separate null reasons; flops come from flops_per_token()."""
    out = {"model_tflops_per_s": flops["model_flops_per_token"] * tokens_per_s / 1e12,
           "mfu": None, "hfu": None,
           "mfu_unavailable_reason": None, "hfu_unavailable_reason": None}
    if peak_tflops is None or not math.isfinite(peak_tflops) or peak_tflops <= 0:
        reason = peak_reason or "peak_tflops_unavailable"
        out["mfu_unavailable_reason"] = reason
        out["hfu_unavailable_reason"] = reason
        return out
    out["mfu"] = flops["model_flops_per_token"] * tokens_per_s / (peak_tflops * 1e12)
    if flops.get("hw_flops_per_token") is not None:
        out["hfu"] = flops["hw_flops_per_token"] * tokens_per_s / (peak_tflops * 1e12)
    else:
        out["hfu_unavailable_reason"] = "hw_flops_unavailable"
    return out


def memory(device) -> dict | None:
    if device.type != "cuda":
        return None
    return {"peak_allocated_gb": torch.cuda.max_memory_allocated(device) / 2**30,
            "peak_reserved_gb": torch.cuda.max_memory_reserved(device) / 2**30}
