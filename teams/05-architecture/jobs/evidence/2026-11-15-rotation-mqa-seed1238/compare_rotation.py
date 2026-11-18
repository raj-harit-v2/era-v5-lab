"""Checks and tables for the Team 5 rotation run: the MQA arm (attn1_mqa.yaml) at seed 1238.

Puts the run beside the 10 Nov 2026 attention screen (seed 1235: attn-0 reference, attn-1 MQA).
Reads only the files in this folder and the screen's evidence folder; standard library only.
Writes rotation-comparison.csv and rotation-slice-scores.csv next to this script, prints checks C1-C7,
and exits 1 if any check fails.

usage: python compare_rotation.py [--screen DIR]    (default: ../2026-11-10-attention-screen)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = 1221
SCREEN_LIMIT_MIN = 90  # T2 max_time_min in runtime.yaml (sha256 cee02cca...)
GROUPS = [
    ("three-group BPB", "val/three_group_bpb"),
    ("code BPB", "val/groups/code_bpb"),
    ("Indic BPB", "val/groups/indic_mean_bpb"),
    ("English BPB", "val/groups/english_bpb"),
    ("all-text BPB", "val/bpb"),
]
SLICES = ["as", "bn", "gu", "hi", "kn", "ml", "mr", "or", "pa", "ta", "te", "en", "code", "math", "sci"]
# The only manifest fields allowed to differ from the screen's attn-1 run, and why.
EXPECTED_DIFF = {
    "config.run.seed": "assigned seed 1238 (screen: 1235)",
    "config.run.max_time_min": "T2 wall-clock stop raised from 90 to 150 for a slower GPU",
    "config.provenance.runtime_sha256": "runtime_t2_150min.yaml: runtime.yaml with only that line changed",
    "identity_sha256": "a hash over the config, so it follows the two lines above",
    "gpu": "own GPU",
    "artifacts.table_file_sha256": "same table content (table_content_sha256 equal); different .npz container bytes",
    "heldout_provenance.source_commit": "label only: inputs rebuilt by the notebook at c1849c1b; held-out bytes equal",
}
T2_150 = "  T2:\n    steps: 1221\n    max_time_min: 150\n"
T2_90 = "  T2:\n    steps: 1221\n    max_time_min: 90\n"


def rows_of(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def final_row(rows: list[dict]) -> dict | None:
    hits = [r for r in rows if r.get("step") == STEPS and "val/bpb" in r]
    return hits[-1] if hits else None


def flat(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flat(v, f"{prefix}{k}."))
    else:
        out[prefix[:-1]] = json.dumps(d, sort_keys=True)
    return out


def run_info(folder: Path) -> dict:
    rows = rows_of(folder / "metrics.jsonl")
    train = [r for r in rows if "perf/step_ms" in r]
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    return {
        "rows": rows,
        "final": final_row(rows),
        "summary": summary,
        "manifest": manifest,
        "wall_min": summary["wall_seconds"] / 60,
        "median_step_s": statistics.median(r["perf/step_ms"] for r in train) / 1000,
        "train_scored": sum(r["train/scored_tokens"] for r in train),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", type=Path, default=HERE.parent / "2026-11-10-attention-screen")
    args = ap.parse_args()

    ref, mqa = run_info(args.screen / "attn-0"), run_info(args.screen / "attn-1")
    run = run_info(HERE)
    att1 = HERE / "attempt1"
    results: list[tuple[str, bool, str]] = []

    # C1: the run reached every step and was not stopped by the time limit.
    s = run["summary"]
    results.append(("C1 run complete", s["steps"] == STEPS and not s["timed_out"] and run["final"] is not None,
                     f"steps {s['steps']}, timed_out {s['timed_out']}"))

    # C2: every logged number is finite.
    bad = sum(1 for r in run["rows"] for v in r.values() if isinstance(v, float) and not math.isfinite(v))
    results.append(("C2 all metrics finite", bad == 0, f"{len(run['rows'])} rows, {bad} non-finite values"))

    # C3: all three runs are scored on the same held-out tokens and bytes, overall and per slice.
    keys = ["val/scored_tokens"] + [f"val/slices/{x}/{m}" for x in SLICES for m in ("scored_tokens", "utf8_bytes")]
    same = all(ref["final"][k] == mqa["final"][k] == run["final"][k] for k in keys)
    results.append(("C3 same held-out scoring", same, f"{run['final']['val/scored_tokens']} scored tokens in each run"))

    # C4: the manifest differs from the screen's MQA run only in the expected fields.
    fa, fb = flat(mqa["manifest"]), flat(run["manifest"])
    diff = {k for k in fa.keys() | fb.keys() if fa.get(k) != fb.get(k)}
    results.append(("C4 manifest differs only where expected", diff == set(EXPECTED_DIFF),
                    f"{len(fa) - len(diff)} of {len(fa)} fields equal; differ: {sorted(diff)}"))

    # C5: the run finished inside the screen's original 90-minute limit, so the raised limit never acted.
    results.append(("C5 original time limit not reached", run["wall_min"] < SCREEN_LIMIT_MIN,
                    f"wall {run['wall_min']:.1f} min < {SCREEN_LIMIT_MIN} min"))

    # C6: the runtime file differs from the screen's runtime.yaml only in T2 max_time_min.
    # The run hashed the LF file; a Windows checkout with core.autocrlf=true has CRLF, so normalise first.
    text = (HERE / "runtime_t2_150min.yaml").read_bytes().decode("utf-8").replace("\r\n", "\n")
    ok6 = (hashlib.sha256(text.encode()).hexdigest() == run["manifest"]["config"]["provenance"]["runtime_sha256"]
           and text.count(T2_150) == 1
           and hashlib.sha256(text.replace(T2_150, T2_90).encode()).hexdigest()
           == mqa["manifest"]["config"]["provenance"]["runtime_sha256"])
    results.append(("C6 runtime file = screen runtime.yaml except T2 limit", ok6,
                    "setting 150 back to 90 reproduces the screen's runtime_sha256"))

    # C7: attempt 1 (screen runtime.yaml unchanged; stopped at step 1044 after the laptop slept)
    #     logged bit-identical losses on every step it shares with this run.
    a_manifest = json.loads((att1 / "manifest.json").read_text(encoding="utf-8"))
    a_loss = (att1 / "losses.txt").read_text(encoding="utf-8").splitlines()
    r_loss = (HERE / "losses.txt").read_text(encoding="utf-8").splitlines()
    ok7 = (a_manifest["config"]["provenance"]["runtime_sha256"] == mqa["manifest"]["config"]["provenance"]["runtime_sha256"]
           and len(a_loss) > 0 and a_loss == r_loss[: len(a_loss)])
    results.append(("C7 attempt-1 losses bit-identical", ok7, f"{len(a_loss)} shared steps"))

    with open(HERE / "rotation-comparison.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["description", "design", "seed", "steps", *[g for g, _ in GROUPS], "wall minutes",
                    "median step seconds", "gpu", "scored training tokens", "three-group BPB difference from reference"])
        base = ref["final"]["val/three_group_bpb"]
        for name, design, seed, r in [("Reference", "attn-0", 1235, ref), ("More key/value sharing", "attn-1", 1235, mqa),
                                      ("More key/value sharing (rotation)", "attn-1", 1238, run)]:
            w.writerow([name, design, seed, r["summary"]["steps"], *[repr(r["final"][k]) for _, k in GROUPS],
                        repr(r["wall_min"]), repr(r["median_step_s"]), r["manifest"]["gpu"], r["train_scored"],
                        repr(r["final"]["val/three_group_bpb"] - base)])
    with open(HERE / "rotation-slice-scores.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["slice", "scored tokens", "reference seed 1235", "MQA seed 1235", "MQA seed 1238",
                    "MQA seed 1238 minus seed 1235"])
        for x in SLICES:
            k = f"val/slices/{x}/bpb"
            w.writerow([x, run["final"][f"val/slices/{x}/scored_tokens"], repr(ref["final"][k]), repr(mqa["final"][k]),
                        repr(run["final"][k]), repr(run["final"][k] - mqa["final"][k])])

    print(f"{'':16s}{'ref 1235':>10s}{'MQA 1235':>10s}{'MQA 1238':>10s}{'1238-1235':>11s}{'1238-ref':>10s}")
    for g, k in GROUPS:
        a, b, c = ref["final"][k], mqa["final"][k], run["final"][k]
        print(f"{g:16s}{a:10.4f}{b:10.4f}{c:10.4f}{c - b:+11.4f}{c - a:+10.4f}")
    # attn-1's not-worse rule (docs/attention_harness.md): mean(MQA) - mean(reference) <= larger seed range.
    print("\nnot-worse inputs   two-seed MQA mean - reference   MQA seed range")
    for g, k in GROUPS[:3]:
        a, b, c = ref["final"][k], mqa["final"][k], run["final"][k]
        print(f"{g:16s}{(b + c) / 2 - a:+20.4f}{abs(c - b):24.4f}")
    print()
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
