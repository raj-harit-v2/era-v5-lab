#!/usr/bin/env python3
"""Turn the N health reports of one job into the baseline numbers, and check them against expected_results.json.

In simple words: run.sh runs the full health check five times (ADR 0003: "at least 5 --mode full runs on known-good
nodes"). This script then
  1. joins the five reports into out/node_health.jsonl (one compact line each: the format Team 08 loads),
  2. checks every report against the profile in expected_results.json that matches the GPU count,
  3. takes, for each collective and message size, the min / median / max bus bandwidth over the runs and the
     0.9 x median floor that ADR 0003 proposes,
  4. says whether Xid was actually visible on this runner (a skipped Xid check is "could not look", not "clean").

Only the standard library is used, so it also runs on a laptop to re-check an out/ folder copied back from the node.

    python summarize_baseline.py --out out            exit 0 = all expectations met, 1 = not met, 2 = no reports
"""
import argparse
import glob
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OPS = ("nccl_all_reduce", "nccl_reduce_scatter", "nccl_all_gather", "nccl_all_to_all")


def load_reports(out):
    paths = sorted(glob.glob(os.path.join(out, "health_run[0-9]*.json")),
                   key=lambda p: int(re.search(r"health_run(\d+)\.json$", p).group(1)))
    return [(p, json.load(open(p))) for p in paths]


def pick_profile(expected, gpus):
    name = "cpu" if gpus == 0 else "gpu1" if gpus == 1 else "gpu"
    return name, expected["profiles"][name]


def check_report(i, rep, name, prof):
    """Return a list of problems for one report (empty when it meets the profile)."""
    p, tag = [], f"run {i}"
    if rep.get("verdict") not in prof["verdict"]:
        bad = [f"{c['name']}{'' if c.get('gpu') is None else '[gpu ' + str(c['gpu']) + ']'}={c['status']}"
               for c in rep["checks"] if c["status"] in ("fail", "warn")]
        p.append(f"{tag}: verdict {rep.get('verdict')!r}, expected one of {prof['verdict']} ({', '.join(bad) or 'see report'})")
    if rep.get("admit_training") is not prof["admit_training"]:
        p.append(f"{tag}: admit_training is {rep.get('admit_training')}, expected {prof['admit_training']}")
    if rep.get("mode") != prof["mode"]:
        p.append(f"{tag}: mode {rep.get('mode')!r}, expected {prof['mode']!r} for profile {name}")
    by = {}
    for c in rep["checks"]:
        by.setdefault(c["name"], []).append(c)
    for cname, rule in prof["checks"].items():
        inst = by.get(cname, [])
        if not inst:
            if not rule.get("optional"):
                p.append(f"{tag}: check {cname!r} is missing")
            continue
        for c in inst:
            if c["status"] not in rule["status"]:
                where = "" if c.get("gpu") is None else f" on GPU {c['gpu']}"
                p.append(f"{tag}: {cname}{where} is {c['status']!r}, expected one of {rule['status']} ({c.get('detail', '')})")
    if rep.get("expected_gpus", 0) > 0:
        inv = next((c for c in rep["checks"] if c["name"] == "gpu_inventory"), None)
        if inv and inv["metrics"].get("count") is not None and inv["metrics"]["count"] != rep["expected_gpus"]:
            p.append(f"{tag}: gpu_inventory saw {inv['metrics'].get('count')} GPUs, expected {rep['expected_gpus']}")
    for cname in OPS:
        if cname not in prof["checks"]:
            continue
        for c in by.get(cname, []):
            m = c["metrics"]
            if m.get("backend") != prof.get("backend"):
                p.append(f"{tag}: {cname} backend {m.get('backend')!r}, expected {prof.get('backend')!r}")
            if not isinstance(m.get("world_size"), int) or m["world_size"] < prof["min_world_size"]:
                p.append(f"{tag}: {cname} world_size {m.get('world_size')!r} < {prof['min_world_size']}")
            if prof.get("bandwidth_is_meaningful") and any(s.get("busbw_gbps", 0) <= 0 for s in m.get("sizes", [])):
                p.append(f"{tag}: {cname} has a size with busbw <= 0")
    return p


def bandwidth(reports, expected):
    """{op: {bytes: {min, median, max, spread_pct, floor_0p9, n}}} over the runs."""
    table = {}
    for _, rep in reports:
        for c in rep["checks"]:
            if c["name"] in OPS and c["status"] == "pass":
                for s in c["metrics"].get("sizes", []):
                    table.setdefault(c["name"], {}).setdefault(s["bytes"], []).append(s.get("busbw_gbps", 0.0))
    out, warn = {}, []
    min_bytes = expected["run_to_run"]["min_bytes"]
    limit = expected["run_to_run"]["max_busbw_spread_pct"]
    for op, sizes in sorted(table.items()):
        out[op] = {}
        for b, v in sorted(sizes.items()):
            med = statistics.median(v)
            spread = round((max(v) - min(v)) / med * 100, 1) if med else None
            out[op][str(b)] = {"n": len(v), "min": round(min(v), 3), "median": round(med, 3), "max": round(max(v), 3),
                               "spread_pct": spread, "floor_0p9": round(0.9 * med, 3)}
            if spread is not None and b >= min_bytes and spread > limit:
                warn.append(f"{op} at {b} bytes: busbw spread {spread}% over {len(v)} runs (> {limit}%), "
                            f"0.9 x median is not a safe floor yet")
    return out, warn


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="out", help="the job's output folder (default ./out)")
    ap.add_argument("--expected", default=os.path.join(HERE, "expected_results.json"))
    a = ap.parse_args()
    expected = json.load(open(a.expected))
    reports = load_reports(a.out)
    if not reports:
        print(f"no health_run*.json in {a.out}", file=sys.stderr)
        return 2

    with open(os.path.join(a.out, "node_health.jsonl"), "w") as f:
        for _, rep in reports:
            f.write(json.dumps(rep, sort_keys=True) + "\n")

    gpus = {rep.get("expected_gpus") for _, rep in reports}
    errors, warnings, notes = [], [], []
    if len(gpus) != 1:
        errors.append(f"runs disagree on expected_gpus: {sorted(gpus, key=str)}")
    g = reports[0][1].get("expected_gpus", 0)
    name, prof = pick_profile(expected, g)
    if len(reports) < expected["runs"]:
        errors.append(f"{len(reports)} runs found, ADR 0003 needs {expected['runs']}")
    for i, (_, rep) in enumerate(reports, 1):
        errors += check_report(i, rep, name, prof)

    bw, bw_warn = ({}, [])
    if any(c in prof["checks"] for c in OPS):
        bw, bw_warn = bandwidth(reports, expected)
        if not prof.get("bandwidth_is_meaningful"):
            notes.append(f"backend is {prof['backend']} on a CPU host: the bandwidth numbers prove the pipeline "
                         f"works but are NOT a baseline for GPU nodes")
        else:
            warnings += bw_warn
    else:
        notes.append("1 GPU cannot run a collective (it needs 2 or more ranks): there is no bandwidth baseline "
                     "from this run. Ask TSAI for 2 GPUs to get one.")

    xid_status = [next((c["status"] for c in rep["checks"] if c["name"] == "xid"), None) for _, rep in reports]
    xid_visible = bool(xid_status) and all(s in ("pass", "warn", "fail") for s in xid_status)
    if not xid_visible:
        notes.append("Xid was NOT visible: the kernel log was not readable here (xid check 'skipped'). This is "
                     "'could not look', not 'no errors'. Re-run as root, or add the user to the adm / "
                     "systemd-journal group, if the Xid result matters.")
    standalone = os.path.join(a.out, "xid_scan.json")
    if os.path.exists(standalone):
        sx = json.load(open(standalone))
        if (sx.get("status") == "skipped") != (not xid_visible):
            notes.append("standalone xid_scan.py and health_check.py disagree on whether the kernel log is readable")

    summary = {
        "schema": "v5-health-baseline/1", "host": reports[0][1].get("host"), "runs": len(reports),
        "profile": name, "expected_gpus": g, "mode": prof["mode"],
        "backend": prof.get("backend"), "ok": not errors,
        "verdicts": [rep.get("verdict") for _, rep in reports],
        "runtime_seconds": [rep.get("runtime_seconds") for _, rep in reports],
        "xid_visible": xid_visible, "errors": errors, "warnings": warnings, "notes": notes,
        "busbw_gbps": bw,
        "thresholds_hint": ("ADR 0003: busbw floor = 0.9 x the median per message size. health/thresholds.yaml "
                            "baseline_busbw_gbps holds one number per size, but the four collectives differ, so "
                            "decide the mapping when filling it in. No code reads that key yet."),
    }
    with open(os.path.join(a.out, "baseline_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)

    lines = [f"baseline summary: host={summary['host']} profile={name} (expected_gpus={g}) runs={len(reports)}",
             f"verdicts: {', '.join(summary['verdicts'])}"]
    for op, sizes in bw.items():
        big = max(sizes, key=int)
        s = sizes[big]
        lines.append(f"  {op:<22} largest size {int(big) >> 20} MiB: busbw median {s['median']} GB/s "
                     f"(min {s['min']}, max {s['max']}, spread {s['spread_pct']}%, floor {s['floor_0p9']})")
    for w in warnings:
        lines.append(f"WARNING: {w}")
    for n in notes:
        lines.append(f"NOTE: {n}")
    for e in errors:
        lines.append(f"FAIL: {e}")
    lines.append("RESULT: " + ("all expectations met" if not errors else f"{len(errors)} expectation(s) NOT met"))
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(a.out, "results_check.txt"), "w") as f:
        f.write(text + "\n")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
