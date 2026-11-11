"""The five slowest parts of a step, and one small Chrome trace for each (docs/PARTS.md).

    slowest_parts(regions, step_ms, top=5)          [{"part", "ms", "pct", "instances", "level", "names"}]
    cut_trace(trace, name)                          one region of the last profiled step, as a trace dict, or None
    write_part_traces(trace_file, parts, out_dir)   writes <rank>_<region>.json files, returns what it wrote

A part is a leaf region with block<i> folded into block* and <x>.expert<E> into <x>, summed over the layers.
A cut keeps the CPU events in the region's time range and the GPU work they launched (by correlation ID). Each file
stays under MAX_BYTES, as pr-guard refuses files over 5 MB.
"""
from __future__ import annotations

import bisect
import json
import re
from pathlib import Path

MAX_BYTES = 4_500_000                 # pr-guard refuses files over 5 MB
PHASES = {"data", "fwd", "bwd", "opt"}
CONTAINERS = {"fwd:stack", "bwd:stack"}
GPU_CATS = {"kernel", "gpu_memcpy", "gpu_memset"}
RUNTIME_CATS = {"cuda_runtime", "cuda_driver"}
_EXPERT = re.compile(r"\.expert\d+$")
_BLOCK = re.compile(r"block(\d+)")


# ------------------------------------------------------------------------------ ranking

def slowest_parts(regions: dict, step_ms: float | None = None, top: int = 5) -> list:
    """regions: run["layer"]["regions"]. Parts summed over layers, slowest first."""
    names = [n for n in regions if not _EXPERT.search(n)]
    parts = {}
    for n in names:
        if n in PHASES or n in CONTAINERS:      # a part is a leaf: not a phase, a stack, or a region with parts in it
            continue
        if any(o != n and o.startswith(n + ".") for o in names):
            continue
        key = _BLOCK.sub("block*", n)
        p = parts.setdefault(key, {"part": key, "ms": 0.0, "instances": 0, "level": regions[n]["level"], "names": []})
        p["ms"] += regions[n]["median"] or 0.0
        p["instances"] += 1
        p["level"] = min(p["level"], regions[n]["level"])
        p["names"].append(n)
    out = sorted(parts.values(), key=lambda p: p["ms"], reverse=True)[:top]
    for p in out:
        p["pct"] = 100.0 * p["ms"] / step_ms if step_ms else None
    return out


def instance(part: dict) -> str:
    """The region to cut for a part: the middle layer's block for a block part, else the region itself."""
    names = sorted(part["names"], key=lambda n: int(m.group(1)) if (m := _BLOCK.search(n)) else -1)
    return names[len(names) // 2]


# ------------------------------------------------------------------------------ cutting

def _end(e) -> float:
    return e["ts"] + e.get("dur", 0)


def _windows(events: list, name: str) -> list:
    """The time ranges of region `name` in the last profiled step: [(start_us, end_us)]."""
    ann = [e for e in events if e.get("cat") == "user_annotation" and e.get("ph") == "X"]
    steps = [e for e in ann if str(e.get("name", "")).startswith("ProfilerStep#")]
    if steps:
        last = max(steps, key=lambda e: e["ts"])
        lo, hi = last["ts"], _end(last)
        ann = [e for e in ann if lo <= e["ts"] <= hi]
    else:
        lo = min((e["ts"] for e in ann), default=0.0)
    found = [(e["ts"], _end(e)) for e in ann if e.get("name") == name]
    if found or not name.startswith("bwd:"):    # a backward segment has no range: previous point to its own point
        return sorted(found)
    target = "__bwd_end__" if name == "bwd:embed" else name[4:]
    points = sorted((e for e in ann if str(e.get("name", "")).startswith("__point__:")), key=lambda e: e["ts"])
    out = []
    for i, p in enumerate(points):
        if p["name"] == f"__point__:{target}":
            start = points[i - 1]["ts"] if i > 0 else lo
            out.append((start, p["ts"]))
    return out


class _Windows:
    """Time ranges merged and sorted, so one overlap test is a binary search, not a scan of every range
    (opt.muon.ns has one range per matrix, ~190, tested against every event of the trace)."""

    def __init__(self, windows):
        merged = []
        for a, b in sorted(windows):
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        self.starts = [a for a, _ in merged]
        self.ends = [b for _, b in merged]

    def overlaps(self, e) -> bool:
        """A range event overlaps a window; a zero-length one lies inside one (ends included)."""
        s, t = e["ts"], _end(e)
        if t > s:
            i = bisect.bisect_left(self.starts, t)        # windows starting before the event ends
            return i > 0 and self.ends[i - 1] > s
        i = bisect.bisect_right(self.starts, s)
        return i > 0 and self.ends[i - 1] >= s


def _cut(trace: dict, windows: list, cpu_detail: bool) -> dict:
    """One pass over the trace: the CPU events in the windows, the GPU work they launched (by correlation ID),
    the GPU annotations around that work, the launch arrows, and the process / thread names."""
    events = trace["traceEvents"]
    win = _Windows(windows)
    cpu = [e for e in events if e.get("ph") in ("X", "i") and "ts" in e and e.get("cat") not in GPU_CATS
           and e.get("cat") != "gpu_user_annotation" and win.overlaps(e)]
    corr = {e["args"]["correlation"] for e in cpu
            if e.get("cat") in RUNTIME_CATS and "correlation" in (e.get("args") or {})}
    gpu = [e for e in events if e.get("cat") in GPU_CATS and (e.get("args") or {}).get("correlation") in corr]
    gpu_ann = []
    if gpu:
        span = _Windows([(min(e["ts"] for e in gpu), max(_end(e) for e in gpu))])
        gpu_ann = [e for e in events if e.get("cat") == "gpu_user_annotation" and span.overlaps(e)]
    flows = [e for e in events if e.get("cat") == "ac2g" and e.get("id") in corr]
    if not cpu_detail:
        cpu = [e for e in cpu if e.get("cat") in ("user_annotation", *RUNTIME_CATS)]
    meta = [e for e in events if e.get("ph") == "M"]
    out = {k: v for k, v in trace.items() if k != "traceEvents"}
    out["traceEvents"] = meta + cpu + gpu + gpu_ann + flows
    out["era_part"] = {"windows_us": [[a, b] for a, b in windows], "cpu_events": len(cpu), "gpu_events": len(gpu),
                       "cpu_detail": cpu_detail}
    return out


def _dump(trace: dict) -> str:
    return json.dumps(trace, separators=(",", ":"))


def cut_trace(trace: dict, name: str, max_bytes: int = MAX_BYTES) -> dict | None:
    """Region `name` of the last profiled step, as a Chrome trace dict under max_bytes; None if not in the trace.
    era_part in the result says what was kept: calls_in_step / calls_kept / stride (every stride-th call, from
    the first), gpu_events (the kernels in the file), cpu_detail, and gpu_events_truncated when even one call
    did not fit."""
    windows = _windows(trace["traceEvents"], name)
    if not windows:
        return None
    calls = len(windows)
    for cpu_detail in (True, False):             # keep every 2nd, 4th, ... call until it fits; then drop CPU detail
        stride = 1
        while True:
            w = windows[::stride]
            out = _cut(trace, w, cpu_detail)
            if len(_dump(out)) <= max_bytes:
                out["era_part"].update(region=name, calls_in_step=calls, calls_kept=len(w), stride=stride)
                return out
            if len(w) == 1:
                break
            stride *= 2
    out = _cut(trace, windows[:1], False)                 # one call, CPU skeleton: keep the first GPU events that fit
    keep = [e for e in out["traceEvents"] if e.get("cat") not in GPU_CATS]
    gpu = [e for e in out["traceEvents"] if e.get("cat") in GPU_CATS]
    while gpu and len(_dump({**out, "traceEvents": keep + gpu})) > max_bytes:
        gpu = gpu[:len(gpu) // 2]
    out["traceEvents"] = keep + gpu
    out["era_part"].update(region=name, calls_in_step=calls, calls_kept=1, stride=calls, gpu_events=len(gpu),
                           gpu_events_truncated=True)
    return out


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9.+-]+", "_", name).strip("_")


def write_part_traces(trace_file, parts: list, out_dir, max_bytes: int = MAX_BYTES) -> list:
    """Cut one trace per part from trace_file into out_dir. Returns one entry per part:
    {"part", "region", "file" (None when the region is not in the trace), "bytes", "calls_in_step", "calls_kept",
    "stride", "gpu_events"}."""
    trace = json.loads(Path(trace_file).read_text())
    out_dir = Path(out_dir)
    written = []
    for rank, p in enumerate(parts, 1):
        name = instance(p)
        cut = cut_trace(trace, name, max_bytes)
        entry = {"part": p["part"], "region": name, "file": None}
        if cut is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"{rank}_{_slug(name)}.json"
            text = _dump(cut)
            path.write_text(text)
            info = cut["era_part"]
            entry.update(file=str(path), bytes=len(text), calls_in_step=info["calls_in_step"],
                         calls_kept=info["calls_kept"], stride=info["stride"], gpu_events=info["gpu_events"])
        written.append(entry)
    return written
