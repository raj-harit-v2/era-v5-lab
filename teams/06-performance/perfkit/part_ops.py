"""The slowest operations inside one part of the step.  [implemented]

The rotation task profiles one part (embedding, attention, ...) and reports its three slowest operations, each with
GPU time, calls and kernels, and whether it is compute-, memory- or launch-bound. perfkit.parts only cuts a trace for
the five slowest parts of the whole step; a small part such as `embed` is not among them, and `trace.top_ops` in the
run JSON ranks the kernels of the whole step. This file answers the question for any region of the trace.

    python -m perfkit.part_ops fwd:embed.ke bwd:embed --run results/runs/<tag>.json
    python -m perfkit.part_ops fwd:block3.attn.sdpa --trace ~/.cache/era-perf/traces/<tag>.json --top 5 --json out.json

An operation is what the model code called: the outermost CPU op that starts inside the region (`aten::embedding_bag`,
`aten::index_select`, or for a backward segment `autograd::engine::evaluate_function: EmbeddingBagBackward0`). The GPU
work it launched is found through the correlation ID of its CUDA runtime calls, as in perfkit.parts, so a kernel that
runs after the CPU range ends still counts.

    ops_in(cut)                the region summary and its operations, from a trace cut by parts.cut_trace
    analyse(trace, region)     cut one region of the last profiled step and run ops_in; None if it is not in the trace
    render(result, top)        the report lines for one region
    gpu_name(trace)            the GPU named in the trace header

Per operation: calls (instances that launched GPU work), kernels (compute kernels; copies and memsets are counted
apart), gpu_ms (all of its GPU work), cpu_ms (the time its CPU ops took, the launch cost) and its biggest kernels.
Per region: the GPU span (first kernel start to last kernel end), the time the GPU was busy in it and the share.
Reading them: kernels of a few microseconds, a GPU busy share far below 100% and cpu_ms close to or above gpu_ms
mean launch-bound; a long elementwise, reduction or gather kernel whose bytes / time is near the GPU's bandwidth
means memory-bound; a long gemm or attention kernel near the dtype's peak TFLOPS means compute-bound
(perfkit.roofline gives the bytes and FLOPs to compare with). The profiler slows the CPU side, so cpu_ms is an
upper bound; gpu_ms is not affected.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from perfkit.parts import GPU_CATS, RUNTIME_CATS, cut_trace

NO_CAP = 1 << 40                      # a region of one part is small: keep every call, never sample
UNOWNED = "(no op)"                   # GPU work launched outside any CPU op that starts inside the region
BACKWARD_NODE = "autograd::engine::evaluate_function: "
KERNELS_SHOWN = 3


# ------------------------------------------------------------------------------ operations

def _inside(windows: list, t: float) -> bool:
    return any(a <= t <= b for a, b in windows)


def _launching_ops(events: list, windows: list) -> dict:
    """{correlation ID: the outermost CPU op that launched it and starts inside a window, or None}.

    One sweep per thread over its ops and runtime calls in time order, with a stack of the ops that are still open.
    An op that started before the region (a backward node that contains it) is skipped, so work is credited to what
    the region itself called."""
    threads = defaultdict(list)
    for e in events:
        if e.get("ph") != "X":
            continue
        if e.get("cat") == "cpu_op" or (e.get("cat") in RUNTIME_CATS and "correlation" in (e.get("args") or {})):
            threads[(e.get("pid"), e.get("tid"))].append(e)
    owner = {}
    for evs in threads.values():
        evs.sort(key=lambda e: (e["ts"], -e.get("dur", 0)))        # a parent before the children that start with it
        stack = []
        for e in evs:
            while stack and stack[-1]["ts"] + stack[-1].get("dur", 0) <= e["ts"]:
                stack.pop()
            if e["cat"] == "cpu_op":
                stack.append(e)
            else:
                owner[e["args"]["correlation"]] = next((o for o in stack if _inside(windows, o["ts"])), None)
    return owner


def _busy_us(events: list) -> float:
    """Time at least one of the GPU events runs."""
    busy, end = 0.0, None
    for s, e in sorted((g["ts"], g["ts"] + g.get("dur", 0)) for g in events):
        if end is None or s > end:
            busy += e - s
            end = e
        elif e > end:
            busy += e - end
            end = e
    return busy


def ops_in(cut: dict) -> dict:
    """cut: a trace from parts.cut_trace. Returns the region summary and its operations, slowest GPU time first:
    {"windows_ms", "gpu_ms", "gpu_span_ms", "gpu_busy_pct", "kernels", "copies",
     "ops": [{"op", "calls", "kernels", "copies", "gpu_ms", "gpu_pct", "cpu_ms", "kernel_names"}]}."""
    events, windows = cut["traceEvents"], cut["era_part"]["windows_us"]
    owner = _launching_ops(events, windows)
    gpu = [e for e in events if e.get("cat") in GPU_CATS and e.get("ph") == "X"]
    rows, instances = {}, defaultdict(dict)
    for g in gpu:
        op = owner.get((g.get("args") or {}).get("correlation"))
        name = op["name"] if op is not None else UNOWNED
        row = rows.setdefault(name, {"op": name, "kernels": 0, "copies": 0, "gpu_us": 0.0, "names": Counter()})
        row["gpu_us"] += g.get("dur", 0)
        row["kernels" if g["cat"] == "kernel" else "copies"] += 1
        row["names"][g["name"]] += g.get("dur", 0)
        if op is not None:
            instances[name][id(op)] = op
    total = sum(r["gpu_us"] for r in rows.values())
    ops = []
    for name, r in sorted(rows.items(), key=lambda kv: kv[1]["gpu_us"], reverse=True):
        calls = instances[name].values()
        ops.append({"op": name, "calls": len(calls), "kernels": r["kernels"], "copies": r["copies"],
                    "gpu_ms": r["gpu_us"] / 1e3, "gpu_pct": 100.0 * r["gpu_us"] / total if total else None,
                    "cpu_ms": sum(o.get("dur", 0) for o in calls) / 1e3 if calls else None,
                    "kernel_names": [{"name": k, "gpu_ms": us / 1e3}
                                     for k, us in r["names"].most_common(KERNELS_SHOWN)]})
    span = max((g["ts"] + g.get("dur", 0) for g in gpu), default=0) - min((g["ts"] for g in gpu), default=0)
    busy = _busy_us(gpu)
    return {"windows_ms": sum(b - a for a, b in windows) / 1e3, "gpu_ms": total / 1e3, "gpu_span_ms": span / 1e3,
            "gpu_busy_pct": 100.0 * busy / span if span > 0 else None,
            "kernels": sum(r["kernels"] for r in rows.values()), "copies": sum(r["copies"] for r in rows.values()),
            "ops": ops}


def analyse(trace: dict, region: str) -> dict | None:
    """Region `region` of the last profiled step in a full trace, as ops_in; None if the region is not in it."""
    cut = cut_trace(trace, region, NO_CAP)
    if cut is None:
        return None
    return {"region": region, "calls_in_step": cut["era_part"]["calls_in_step"], **ops_in(cut)}


def gpu_name(trace: dict) -> str | None:
    return next((d["name"] for d in trace.get("deviceProperties", []) if d.get("name")), None)


# ------------------------------------------------------------------------------ output

def _f(x, nd=3):
    return "-" if x is None else f"{x:.{nd}f}"


def _label(op: str) -> str:
    """A backward node is shown as `bwd EmbeddingBagBackward0`, not `autograd::engine::evaluate_function: ...`."""
    return f"bwd {op.removeprefix(BACKWARD_NODE)}" if op.startswith(BACKWARD_NODE) else op


def render(result: dict, top: int = 3) -> list:
    """The report lines of one analyse() result: a summary line, then the `top` slowest operations."""
    lines = [f"{result['region']}: {result['calls_in_step']} call(s) per step, "
             f"CPU window {_f(result['windows_ms'])} ms; "
             f"GPU {_f(result['gpu_ms'])} ms in {result['kernels']} kernels + {result['copies']} copies, "
             f"span {_f(result['gpu_span_ms'])} ms, busy {_f(result['gpu_busy_pct'], 0)}%"]
    if not result["ops"]:
        return lines + ["  no GPU work in this region (a CPU run, or the region launches nothing)"]
    lines.append(f"  {'#':>2} {'operation':44s} {'calls':>5s} {'kernels':>7s} {'copies':>6s} "
                 f"{'gpu ms':>8s} {'% gpu':>6s} {'cpu ms':>8s}")
    for i, o in enumerate(result["ops"][:top], 1):
        lines.append(f"  {i:>2} {_label(o['op'])[:44]:44s} {o['calls']:>5d} {o['kernels']:>7d} {o['copies']:>6d} "
                     f"{o['gpu_ms']:8.4f} {_f(o['gpu_pct'], 1):>6s} {_f(o['cpu_ms'], 4):>8s}")
        for k in o["kernel_names"]:
            lines.append(f"       {k['gpu_ms']:8.4f} ms  {k['name'][:90]}")
    rest = result["ops"][top:]
    if rest:
        lines.append(f"      (+{len(rest)} more operations, {sum(o['gpu_ms'] for o in rest):.4f} ms in all; "
                     f"--top N lists them)")
    return lines


# ------------------------------------------------------------------------------ main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The slowest operations inside regions of a profiled trace.")
    ap.add_argument("regions", nargs="+", help="region names as in the run JSON, e.g. fwd:embed.ke bwd:embed")
    ap.add_argument("--run", help="run JSON from perfkit.bench: the trace file, GPU name, commit and batch")
    ap.add_argument("--trace", help="the full Chrome trace (default: trace.trace_file of --run)")
    ap.add_argument("--top", type=int, default=3, help="operations listed per region (default 3)")
    ap.add_argument("--json", help="also write every operation of every region to this JSON file")
    a = ap.parse_args(argv)

    run = json.loads(Path(a.run).read_text(encoding="utf-8")) if a.run else {}
    trace_file = a.trace or (run.get("trace") or {}).get("trace_file")
    if not trace_file:
        ap.error("give --trace, or a --run whose trace mode ran")
    trace_file = Path(trace_file).expanduser()
    trace = json.loads(trace_file.read_text(encoding="utf-8"))

    meta, cfg = run.get("meta") or {}, (run.get("config") or {}).get("run") or {}
    print(f"trace:  {trace_file}")
    print(f"GPU:    {meta.get('gpu') or gpu_name(trace)}")
    if meta:
        dirty = "  (dirty tree: these numbers do not count)" if meta.get("dirty") else ""
        print(f"commit: {meta.get('commit')}{dirty}")
        print(f"run:    {meta.get('tag')}  {meta.get('dtype')}  B={meta.get('batch_size')}  T={meta.get('seq_len')}"
              f"  device={cfg.get('device')}")
    print("last profiled step; GPU times are not slowed by the profiler, CPU times are\n")

    results, missing = [], []
    for region in a.regions:
        res = analyse(trace, region)
        if res is None:
            missing.append(region)
            print(f"{region}: not in the last profiled step (names are listed in results/runs/<tag>.md)\n")
            continue
        results.append(res)
        print("\n".join(render(res, a.top)) + "\n")
    if a.json:
        out = {"trace": str(trace_file), "gpu": meta.get("gpu") or gpu_name(trace), "commit": meta.get("commit"),
               "regions": results}
        Path(a.json).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"[part_ops] wrote {a.json}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
