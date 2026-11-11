"""Health-check JSON contract (v5-health/1), validator, and ClickHouse row builder.

Team 7's node health scripts (gpu_health.sh, xid_scan.py, nccl_probe.py, launch.sh) emit JSON
reports before a job starts (prolog), every 30 s during a run (periodic), and before dry runs
or after a repair (full). Team 8 validates those JSONL node logs and loads them into ClickHouse
in week 2 (one ClickHouse row per JSONL line).

Usage:
  python -I health_check.py --selftest
  python -I health_check.py --validate <report.json|node_health.jsonl|->
  python -I health_check.py --clickhouse-jsonl <node_health.jsonl>
  python -I health_check.py --example [prolog|full|xid-fail]
"""
import argparse, json, sys

SCHEMA = "v5-health/1"
COLLECTIVE_SCHEMA = "g7-collective/1"
COLLECTIVE_CHECKS = ("nccl_all_reduce", "nccl_reduce_scatter", "nccl_all_gather", "nccl_all_to_all")
MODES = ("prolog", "periodic", "full")
STATUSES = ("pass", "warn", "fail", "skipped")
VERDICTS = ("pass", "warn", "fail")
XID_SOURCES = ("journalctl", "dmesg", "file")

# Uncontained GPU/NVLink/memory faults: always fail and drain the node.
FATAL_XIDS = {
    48: "double-bit ECC error (DBE)",
    61: "internal micro-controller breakpoint",
    62: "internal micro-controller halt",
    64: "row-remapping failure",
    74: "NVLink error",
    79: "GPU fell off the bus",
    92: "high single-bit ECC error rate",
    95: "uncontained memory error",
    119: "GSP RPC timeout",
    120: "GSP error",
    140: "unrecovered ECC error",
}
# Contained or row-remap events: first Xid 94 warns (restart job), a second on the same GPU
# within 24 h fails and drains; 63 is a row-remap event. Either warn or fail is accepted, never pass.
CONTAINED_XIDS = {
    63: "row-remapping event",
    94: "contained memory error",
}
WARN_XIDS = {
    13: "graphics engine exception",
    31: "MMU page fault",
    43: "stopped processing (application)",
    45: "preemptive channel cleanup",
}


def expected_verdict(checks):
    """Derive the node verdict from the check list.

    Rule:
      - Any check with status 'fail' -> 'fail'.
      - Otherwise any check with status 'warn', or a required check with status 'skipped', -> 'warn'.
        A missing tool on a required check never silently passes.
      - Otherwise -> 'pass'.
    """
    if any(c.get("status") == "fail" for c in checks):
        return "fail"
    if any(c.get("status") == "warn" or (c.get("status") == "skipped" and c.get("required")) for c in checks):
        return "warn"
    return "pass"


def validate_xid_scan(d):
    """Validate a standalone xid_scan.py JSON object or the metrics dict of an 'xid' check."""
    problems = []
    events = d.get("events")
    counts = d.get("counts")
    if not isinstance(events, list):
        problems.append("xid.events must be a list")
        events = []
    if not isinstance(counts, dict):
        problems.append("xid.counts must be a dict")
        counts = {}
    tally = {}
    for i, e in enumerate(events):
        if not isinstance(e, dict):
            problems.append(f"xid.events[{i}] must be a dict")
            continue
        code = e.get("code")
        sev = e.get("severity")
        if not isinstance(code, int):
            problems.append(f"xid.events[{i}].code must be int")
            continue
        tally[str(code)] = tally.get(str(code), 0) + 1
        if not isinstance(e.get("pci_bdf"), str) or not e["pci_bdf"].strip():
            problems.append(f"xid.events[{i}].pci_bdf must be a non-empty string")
        if sev not in ("warn", "fail"):
            problems.append(f"xid.events[{i}].severity must be 'warn' or 'fail', got {sev!r}")
        elif code in FATAL_XIDS and sev != "fail":
            problems.append(f"fatal Xid {code} ({FATAL_XIDS[code]}) must have severity 'fail', got {sev!r}")
    if isinstance(counts, dict) and counts != tally:
        problems.append(f"xid.counts {counts} does not match event counts {tally}")
    return problems, events


def validate_collective(d):
    """Validate a standalone nccl_probe.py JSON object (g7-collective/1) or nccl_all_reduce metrics."""
    problems = []
    if d.get("schema") not in (None, COLLECTIVE_SCHEMA):
        problems.append(f"collective schema must be {COLLECTIVE_SCHEMA!r}")
    if d.get("backend") not in ("nccl", "gloo"):
        problems.append(f"collective backend must be 'nccl' or 'gloo', got {d.get('backend')!r}")
    if not isinstance(d.get("world_size"), int) or d.get("world_size", 0) < 1:
        problems.append("collective world_size must be an int >= 1")
    if d.get("status") not in ("pass", "fail"):
        problems.append(f"collective status must be 'pass' or 'fail', got {d.get('status')!r}")
    sizes = d.get("sizes")
    if not isinstance(sizes, list) or not sizes:
        problems.append("collective sizes must be a non-empty list")
        return problems
    for i, s in enumerate(sizes):
        if not isinstance(s, dict):
            problems.append(f"collective sizes[{i}] must be a dict")
            continue
        for k in ("bytes", "seconds", "max_error", "all_ranks_correct"):
            if k not in s:
                problems.append(f"collective sizes[{i}] missing {k!r}")
        if s.get("all_ranks_correct") is True and s.get("max_error", 0) != 0:
            problems.append(f"collective sizes[{i}] all_ranks_correct is True but max_error={s.get('max_error')}")
    if d.get("status") == "pass" and not all(isinstance(s, dict) and s.get("all_ranks_correct") is True for s in sizes):
        problems.append("collective status is 'pass' but not all sizes have all_ranks_correct=True")
    return problems


def validate_check(c, idx, expected_gpus=0):
    problems = []
    tag = f"checks[{idx}]"
    if not isinstance(c, dict):
        return [f"{tag} must be a dict"]
    name = c.get("name")
    if not isinstance(name, str) or not name.strip():
        problems.append(f"{tag}.name must be a non-empty string")
    else:
        tag = f"check[{name}]"
    status = c.get("status")
    if status not in STATUSES:
        problems.append(f"{tag}.status must be one of {STATUSES}, got {status!r}")
    if not isinstance(c.get("required"), bool):
        problems.append(f"{tag}.required must be bool")
    reason = c.get("reason") if "reason" in c else c.get("detail")
    if not isinstance(reason, str):
        problems.append(f"{tag}.reason must be a string")
    elif status == "skipped" and not reason.strip():
        problems.append(f"{tag} is 'skipped' without a reason")
    metrics = c.get("metrics")
    if not isinstance(metrics, dict):
        problems.append(f"{tag}.metrics must be a dict")
        return problems

    if name == "gpu_inventory" and status in ("pass", "fail"):
        cnt = metrics.get("count")
        if status == "pass":
            if not isinstance(cnt, int) or cnt < 0:
                problems.append(f"{tag}.metrics.count must be int >= 0 when status is 'pass'")
            elif expected_gpus > 0 and cnt != expected_gpus:
                problems.append(f"{tag} passed with count={cnt}, but expected_gpus={expected_gpus}")
    elif name == "xid" and status != "skipped":
        p, events = validate_xid_scan(metrics)
        problems.extend(p)
        want = "fail" if any(e.get("severity") == "fail" for e in events if isinstance(e, dict)) else ("warn" if events else "pass")
        if status != want:
            problems.append(f"{tag}.status is {status!r}, expected {want!r} from {len(events)} Xid event(s)")
    elif name == "ecc_uncorrectable" and status != "skipped":
        vals = metrics.get("values")
        if isinstance(vals, list):
            if status == "pass" and any(isinstance(v, (int, float)) and v > 0 for v in vals):
                problems.append(f"{tag} passed with non-zero uncorrectable ECC values {vals}")
            if status == "fail" and vals and all(v == 0 for v in vals):
                problems.append(f"{tag} failed with all-zero uncorrectable ECC values")
    elif name in COLLECTIVE_CHECKS and status == "pass":
        problems.extend(validate_collective(metrics))
        if expected_gpus > 0 and metrics.get("backend") != "nccl":
            problems.append(f"{tag} cannot pass with backend={metrics.get('backend')!r} when expected_gpus > 0; CPU gloo is not GPU NCCL proof")
        ws = metrics.get("world_size")
        if isinstance(ws, int) and ws < 2:
            problems.append(f"{tag} requires world_size >= 2 for collective proof")
    return problems


def validate_report(d):
    """Return a list of contract violations ([] when valid). Accepts v5-health/1, standalone xid, or g7-collective/1."""
    if not isinstance(d, dict):
        return ["report must be a JSON object"]
    if d.get("schema") == COLLECTIVE_SCHEMA:
        return validate_collective(d)
    if d.get("name") == "xid" and "schema" not in d:
        problems = []
        status = d.get("status")
        if status not in STATUSES:
            problems.append(f"xid.status must be one of {STATUSES}")
        src = d.get("source")
        if status == "skipped":
            if src is not None and src not in XID_SOURCES:
                problems.append(f"xid.source must be one of {XID_SOURCES} or null when skipped")
        elif src not in XID_SOURCES:
            problems.append(f"xid.source must be one of {XID_SOURCES}")
        if status != "skipped":
            p, events = validate_xid_scan(d)
            problems.extend(p)
            want = "fail" if any(e.get("severity") == "fail" for e in events if isinstance(e, dict)) else ("warn" if events else "pass")
            if status != want:
                problems.append(f"xid.status is {status!r}, expected {want!r}")
        return problems

    problems = []
    if d.get("schema") != SCHEMA:
        problems.append(f"schema must be {SCHEMA!r}, got {d.get('schema')!r}")
    if not isinstance(d.get("host"), str) or not d["host"].strip():
        problems.append("host must be a non-empty string")
    ts = d.get("timestamp_utc") if "timestamp_utc" in d else d.get("time")
    if not isinstance(ts, str) or not ts.strip():
        problems.append("timestamp_utc must be a non-empty ISO-8601 string")
    if d.get("mode") not in MODES:
        problems.append(f"mode must be one of {MODES}, got {d.get('mode')!r}")
    expected_gpus = d.get("expected_gpus", 0)
    if not isinstance(expected_gpus, int) or expected_gpus < 0:
        problems.append(f"expected_gpus must be int >= 0, got {expected_gpus!r}")
        expected_gpus = 0
    verdict = d.get("verdict")
    if verdict not in VERDICTS:
        problems.append(f"verdict must be one of {VERDICTS}, got {verdict!r}")
    checks = d.get("checks")
    if not isinstance(checks, list) or not checks:
        problems.append("checks must be a non-empty list")
        return problems

    for i, c in enumerate(checks):
        problems.extend(validate_check(c, i, expected_gpus))

    inv_checks = [c for c in checks if isinstance(c, dict) and c.get("name") == "gpu_inventory"]
    if expected_gpus > 0 and not inv_checks:
        problems.append("checks must include 'gpu_inventory' when expected_gpus > 0")

    want_verdict = expected_verdict([c for c in checks if isinstance(c, dict)])
    if verdict in VERDICTS and verdict != want_verdict:
        problems.append(f"verdict is {verdict!r}, but checks require {want_verdict!r}")

    if "admit_training" in d:
        if not isinstance(d["admit_training"], bool):
            problems.append("admit_training must be bool")
        elif d["admit_training"]:
            if want_verdict == "fail":
                problems.append("admit_training cannot be True when verdict is 'fail'")
            elif expected_gpus > 0 and (not inv_checks or inv_checks[0].get("status") != "pass"):
                problems.append("admit_training cannot be True when expected_gpus > 0 unless 'gpu_inventory' passed")
            elif expected_gpus == 0 and want_verdict != "pass":
                problems.append(f"admit_training cannot be True when expected_gpus == 0 and verdict is {want_verdict!r}")

    drain = d.get("drain_reason")
    if drain is not None and not isinstance(drain, str):
        problems.append("drain_reason must be str or null")
    if want_verdict == "fail" and (not isinstance(drain, str) or not drain.strip()):
        problems.append("drain_reason must be a non-empty string when verdict is 'fail'")
    return problems


def to_clickhouse_row(d):
    """Flatten one v5-health/1 JSON object into one row for Week 2's ClickHouse node_health table."""
    by_name = {c["name"]: c for c in d.get("checks", []) if isinstance(c, dict) and "name" in c}
    inv = by_name.get("gpu_inventory", {}).get("metrics", {})
    xid = by_name.get("xid", {}).get("metrics", {})
    ecc = by_name.get("ecc_uncorrectable", {}).get("metrics", {}).get("values", [])
    nccl = by_name.get("nccl_all_reduce", {})
    counts = {s: sum(1 for c in d.get("checks", []) if isinstance(c, dict) and c.get("status") == s) for s in STATUSES}
    return {
        "timestamp_utc": d.get("timestamp_utc") or d.get("time") or "",
        "host": d.get("host", ""),
        "mode": d.get("mode", ""),
        "expected_gpus": d.get("expected_gpus", 0),
        "gpus_seen": inv.get("count", 0) if isinstance(inv, dict) else 0,
        "verdict": d.get("verdict", ""),
        "admit_training": bool(d.get("admit_training", d.get("verdict") == "pass")),
        "drain_reason": d.get("drain_reason") or "",
        "checks_pass": counts["pass"],
        "checks_warn": counts["warn"],
        "checks_fail": counts["fail"],
        "checks_skipped": counts["skipped"],
        "xid_codes": sorted(int(k) for k in (xid.get("counts") or {}) if str(k).isdigit()),
        "ecc_uncorrectable_total": sum(v for v in ecc if isinstance(v, int)),
        "nccl_status": nccl.get("status", "not_run"),
        "runtime_seconds": float(d.get("runtime_seconds") or 0.0),
        "raw_json": json.dumps(d, sort_keys=True),
    }


def example_report(kind="prolog"):
    """Return a well-formed v5-health/1 report for testing or documentation."""
    if kind == "xid-fail":
        # Exact structure produced by Team 7's gpu_health.py on the injected Xid fixture.
        return {
            "schema": SCHEMA,
            "host": "7fb2e774ad54",
            "timestamp_utc": "2026-10-27T00:24:40.296773+00:00",
            "mode": "prolog",
            "expected_gpus": 0,
            "verdict": "fail",
            "admit_training": False,
            "checks": [
                {"name": "gpu_inventory", "status": "skipped", "required": True,
                 "reason": "nvidia-smi not installed", "metrics": {}},
                {"name": "xid", "status": "fail", "required": False, "reason": "",
                 "metrics": {
                     "counts": {"31": 1, "79": 1, "94": 1},
                     "events": [
                         {"code": 31, "pci_bdf": "0000:4b:00", "reason": "MMU page fault (often application)", "severity": "warn"},
                         {"code": 79, "pci_bdf": "0000:3a:00", "reason": "fallen off bus", "severity": "fail"},
                         {"code": 94, "pci_bdf": "0000:50:00", "reason": "contained memory error: restart affected app", "severity": "warn"},
                     ],
                 }},
                {"name": "ecc_uncorrectable", "status": "skipped", "required": False,
                 "reason": "GPU inventory unavailable", "metrics": {}},
            ],
            "drain_reason": "xid: 79",
        }
    checks = [
        {"name": "gpu_inventory", "status": "pass", "required": True, "reason": "",
         "metrics": {"count": 8, "gpus": [f"{i}, GPU-{i:04d}, GPU-80GB, 81559, 81000, 38" for i in range(8)]}},
        {"name": "xid", "status": "pass", "required": True, "reason": "", "metrics": {"counts": {}, "events": []}},
        {"name": "ecc_uncorrectable", "status": "pass", "required": False, "reason": "", "metrics": {"values": [0] * 8}},
    ]
    if kind == "full":
        checks += [
            {"name": "dcgm_quick", "status": "pass", "required": False, "reason": "Quick DCGM diagnostic exit code 0",
             "metrics": {"exit_code": 0, "output_tail": "Deployment: Pass"}},
            {"name": "nvlink", "status": "pass", "required": False, "reason": "", "metrics": {"links": 18, "inactive": 0, "down": 0}},
            {"name": "nccl_all_reduce", "status": "pass", "required": True, "reason": "",
             "metrics": {
                 "schema": COLLECTIVE_SCHEMA, "backend": "nccl", "world_size": 8, "status": "pass",
                 "sizes": [
                     {"bytes": 1024, "seconds": 0.00018, "max_error": 0.0, "all_ranks_correct": True},
                     {"bytes": 1048576, "seconds": 0.00042, "max_error": 0.0, "all_ranks_correct": True},
                     {"bytes": 8388608, "seconds": 0.00195, "max_error": 0.0, "all_ranks_correct": True},
                 ],
             }},
        ]
    return {
        "schema": SCHEMA,
        "host": "gpu-node-01",
        "timestamp_utc": "2026-10-28T12:00:00+00:00",
        "mode": "full" if kind == "full" else "prolog",
        "expected_gpus": 8,
        "verdict": "pass",
        "admit_training": True,
        "checks": checks,
        "drain_reason": None,
        "runtime_seconds": 1.4,
    }


def selftest():
    """Run synthetic verification cases for v5-health/1, standalone xid, and g7-collective/1."""
    cases = []

    # 1. Healthy 8-GPU prolog report passes.
    r1 = example_report("prolog")
    cases.append(("healthy 8-GPU prolog", validate_report(r1) == []))

    # 2. Healthy 8-GPU full report (with DCGM, NVLink, NCCL all-reduce) passes.
    r2 = example_report("full")
    cases.append(("healthy 8-GPU full", validate_report(r2) == []))

    # 3. Team 7's injected Xid fixture (Xids 31, 79, 94) passes contract validation.
    r3 = example_report("xid-fail")
    cases.append(("Team 7 injected Xid fixture", validate_report(r3) == []))

    # 4. Missing nvidia-smi on a GPU node: required check is 'skipped' -> verdict must be 'warn', never 'pass'.
    r4 = example_report("prolog")
    r4["checks"][0] = {"name": "gpu_inventory", "status": "skipped", "required": True,
                      "reason": "nvidia-smi not installed", "metrics": {}}
    cases.append(("skipped required check rejected as pass", any("verdict" in p for p in validate_report(r4))))
    r4["verdict"] = "warn"
    r4["admit_training"] = False
    cases.append(("skipped required check accepted as warn", validate_report(r4) == []))

    # 5. Fatal Xid 79 misclassified as 'warn' is rejected.
    r5 = example_report("xid-fail")
    r5["checks"][1]["metrics"]["events"][1]["severity"] = "warn"
    cases.append(("fatal Xid 79 as warn rejected", any("fatal Xid 79" in p for p in validate_report(r5))))

    # 6. Non-zero uncorrectable ECC marked 'pass' is rejected.
    r6 = example_report("prolog")
    r6["checks"][2]["metrics"]["values"] = [0, 0, 2, 0, 0, 0, 0, 0]
    cases.append(("non-zero ECC as pass rejected", any("ECC" in p for p in validate_report(r6))))

    # 7. CPU gloo collective mislabelled as passing GPU nccl_all_reduce is rejected.
    r7 = example_report("full")
    r7["checks"][-1]["metrics"]["backend"] = "gloo"
    cases.append(("CPU gloo in nccl_all_reduce rejected", any("gloo" in p for p in validate_report(r7))))

    # 8. Wrong GPU count (6 seen, 8 expected) marked 'pass' is rejected.
    r8 = example_report("prolog")
    r8["checks"][0]["metrics"]["count"] = 6
    cases.append(("GPU count mismatch as pass rejected", any("expected_gpus=8" in p for p in validate_report(r8))))

    # 9. Standalone xid_scan.py output passes.
    xid_out = {
        "name": "xid", "status": "fail", "source": "journalctl", "since_minutes": 30, "reason": "",
        "events": [
            {"code": 79, "pci_bdf": "0000:4b:00", "reason": "fallen off bus", "severity": "fail"},
            {"code": 43, "pci_bdf": "0000:2a:00", "reason": "application stopped", "severity": "warn"},
        ],
        "counts": {"43": 1, "79": 1}, "timestamp_utc": "2026-10-27T00:24:40+00:00",
    }
    cases.append(("standalone xid_scan.py output", validate_report(xid_out) == []))

    # 10. Standalone nccl_probe.py (g7-collective/1) output passes.
    nccl_out = {
        "schema": COLLECTIVE_SCHEMA, "backend": "gloo", "world_size": 2, "status": "pass",
        "sizes": [{"bytes": 1024, "seconds": 0.001, "max_error": 0.0, "all_ranks_correct": True}],
    }
    cases.append(("standalone nccl_probe.py output", validate_report(nccl_out) == []))

    # 11. ClickHouse row flattener preserves 1-to-1 fields on both pass and fail reports.
    ch_pass = to_clickhouse_row(r2)
    ch_fail = to_clickhouse_row(r3)
    cases.append(("ClickHouse row mapping (1 row per JSONL line)",
                  ch_pass["gpus_seen"] == 8 and ch_pass["nccl_status"] == "pass" and ch_fail["xid_codes"] == [31, 79, 94]))

    # 12. Non-int world_size in nccl_all_reduce reports a violation without raising TypeError.
    r12 = example_report("full")
    r12["checks"][-1]["metrics"]["world_size"] = "8"
    r12_null = example_report("full")
    r12_null["checks"][-1]["metrics"]["world_size"] = None
    cases.append(("non-int world_size in nccl_all_reduce rejected cleanly",
                  any("world_size" in p for p in validate_report(r12))
                  and any("world_size" in p for p in validate_report(r12_null))))

    # 13. Non-empty xid.counts with empty xid.events is rejected.
    r13 = example_report("prolog")
    r13["checks"][1]["metrics"] = {"counts": {"79": 1}, "events": []}
    cases.append(("xid.counts without matching xid.events rejected",
                  any("xid.counts" in p for p in validate_report(r13))))

    # 14. Missing gpu_inventory check when expected_gpus > 0 is rejected.
    r14 = example_report("prolog")
    r14["checks"] = [c for c in r14["checks"] if c["name"] != "gpu_inventory"]
    cases.append(("missing gpu_inventory with expected_gpus > 0 rejected",
                  any("gpu_inventory" in p for p in validate_report(r14))))

    # 15. CPU host (expected_gpus == 0) allows gloo collectives with world_size >= 2.
    r15 = example_report("full")
    r15["expected_gpus"] = 0
    r15["checks"][0]["metrics"] = {"count": 0, "gpus": []}
    r15["checks"][-1]["metrics"]["backend"] = "gloo"
    r15["checks"][-1]["metrics"]["world_size"] = 2
    cases.append(("CPU host (expected_gpus=0) allows gloo collective", validate_report(r15) == []))

    # 16. Prolog warn with passing gpu_inventory allows admit_training=True, but skipped gpu_inventory rejects it.
    r16 = example_report("prolog")
    r16["checks"].append({"name": "gpu_temperature", "status": "warn", "required": False, "reason": "86 C", "metrics": {}})
    r16["verdict"] = "warn"
    r16["admit_training"] = True
    r16_no_inv = example_report("prolog")
    r16_no_inv["checks"][0] = {"name": "gpu_inventory", "status": "skipped", "required": True, "reason": "no nvidia-smi", "metrics": {}}
    r16_no_inv["verdict"] = "warn"
    r16_no_inv["admit_training"] = True
    cases.append(("warn admission allowed only when gpu_inventory passed",
                  validate_report(r16) == [] and any("gpu_inventory" in p for p in validate_report(r16_no_inv))))

    # 17. Skipped standalone xid_scan output allows source=None.
    xid_skip = {"name": "xid", "status": "skipped", "source": None, "reason": "kernel log unreadable", "events": [], "counts": {}}
    cases.append(("skipped standalone xid_scan allows source=None", validate_report(xid_skip) == []))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"selftest: {len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="run built-in contract tests")
    ap.add_argument("--validate", help="validate a JSON or JSONL health file (use - for stdin)")
    ap.add_argument("--clickhouse-jsonl", help="convert v5-health/1 JSONL into ClickHouse node_health rows")
    ap.add_argument("--example", choices=("prolog", "full", "xid-fail"), help="print an example report")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if a.example:
        print(json.dumps(example_report(a.example), indent=2, sort_keys=True))
        return 0
    if a.clickhouse_jsonl:
        fh = sys.stdin if a.clickhouse_jsonl == "-" else open(a.clickhouse_jsonl, encoding="utf-8")
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            d = json.loads(line)
            probs = validate_report(d)
            if probs:
                sys.exit(f"line {i}: invalid report: {'; '.join(probs)}")
            print(json.dumps(to_clickhouse_row(d), sort_keys=True))
        return 0
    if a.validate:
        fh = sys.stdin if a.validate == "-" else open(a.validate, encoding="utf-8")
        raw = fh.read().strip()
        items = [json.loads(raw)] if raw.startswith("{") and "\n{" not in raw else [json.loads(l) for l in raw.splitlines() if l.strip()]
        bad = 0
        for i, d in enumerate(items, 1):
            probs = validate_report(d)
            if probs:
                bad += 1
                print(f"record {i}: FAIL — {'; '.join(probs)}")
            else:
                print(f"record {i}: PASS ({d.get('schema') or d.get('name')}, verdict={d.get('verdict') or d.get('status')})")
        return 1 if bad else 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
