r"""Time dedup.py against an earlier commit and check that its outputs did not change. Everything stays under out/.

For each config, it runs the dedup.py of --baseline (taken from git) and the current dedup.py on the same inputs,
alternating, --runs times each. It records wall time and peak memory, and fails (exit 1) if any of the five lists or
any count in dedup_summary.json differs (config, outputs and seconds may differ by design).

HOW TO RUN IT
=============
From the repository root, with the packages in dedup/requirements_overlap.txt:

    python3 -B teams/01-data-a/dedup/benchmark_dedup.py --configs out/dedup_a.json out/dedup_b.json \
        --baseline 0011cc4 --runs 2 --out out/bench_dedup

Each config is a dedup.json whose results, inputs and gold_dirs point at an overlap run on this machine (results and
out relative to the repository root, as dedup.py requires). The out folder must not exist yet. Peak memory needs the
`resource` module (Linux and macOS); on Windows it is reported as null.

WHAT IT WRITES (in --out)
=========================
  report.json                    per config: wall time and peak memory of every run, output SHA-256, SAME/DIFF
  <config>/<version>-run<n>.txt  the console output of every run
  baseline/dedup.py              the --baseline dedup.py, with its repository root set to this checkout
"""
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEDUP = Path("teams/01-data-a/dedup/dedup.py")
FILES = ["remove_list.csv", "dedup_log.jsonl", "heldout_duplicates.csv", "empty_documents.csv", "dedup_groups.csv"]
SKIP = {"config", "outputs", "seconds"}
# Runs dedup.py's main() and prints its peak memory as the last stderr line.
WRAPPER = r'''
import json, runpy, sys
script, cfg = sys.argv[1], sys.argv[2]
sys.argv = [script, "--config", cfg]
code = 0
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as e:
    code = e.code or 0
try:
    import resource
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak = rss / 1024 / (1024 if sys.platform == "darwin" else 1)
except ImportError:
    peak = None
sys.stderr.write("\nBENCH " + json.dumps({"peak_mb": peak}) + "\n")
sys.exit(code)
'''


def snapshot_baseline(ref, out):
    """The baseline dedup.py, with REPO pointing at this checkout so that config paths resolve the same way."""
    src = subprocess.run(["git", "show", f"{ref}:{DEDUP.as_posix()}"], cwd=REPO, capture_output=True, text=True,
                         check=True).stdout
    lines = src.splitlines(keepends=True)
    hits = [i for i, l in enumerate(lines) if l.startswith("REPO = ")]
    if len(hits) != 1:
        sys.exit(f"ERROR: expected one 'REPO = ' line in {ref}:{DEDUP}")
    lines[hits[0]] = f"REPO = Path({str(REPO)!r})\n"
    path = out / "baseline" / "dedup.py"
    path.parent.mkdir(parents=True)
    path.write_text("".join(lines), encoding="utf-8")
    return path


def run_once(script, cfg, log):
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, "-B", "-c", WRAPPER, str(script), str(cfg)], cwd=REPO,
                       capture_output=True, text=True)
    wall = time.perf_counter() - t0
    log.write_text(p.stdout + p.stderr, encoding="utf-8")
    if p.returncode:
        sys.exit(f"ERROR: {script} failed on {cfg}; see {log}")
    peak = json.loads(p.stderr.rsplit("BENCH ", 1)[1])["peak_mb"]
    return round(wall, 2), (round(peak) if peak is not None else None)


def fingerprint(out_dir):
    files = {f: hashlib.sha256((out_dir / f).read_bytes()).hexdigest() for f in FILES}
    s = json.loads((out_dir / "dedup_summary.json").read_text(encoding="utf-8"))
    return files, {k: v for k, v in s.items() if k not in SKIP}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--configs", nargs="+", required=True, help="dedup.json files to run (paths from the repo root)")
    ap.add_argument("--baseline", default="0011cc4", help="git commit whose dedup.py is the baseline")
    ap.add_argument("--runs", type=int, default=2, help="runs per version and config, alternating")
    ap.add_argument("--out", required=True, help="new folder under out/")
    args = ap.parse_args()
    out = REPO / args.out
    if not out.resolve().is_relative_to((REPO / "out").resolve()):
        sys.exit("ERROR: --out must be inside out/")
    if out.exists():
        sys.exit(f"ERROR: {args.out} exists; use a new folder")
    base = snapshot_baseline(args.baseline, out)
    commit = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    report, ok = {"baseline": args.baseline, "candidate": commit + " (working tree)", "configs": {}}, True
    for cfg_path in args.configs:
        name = Path(cfg_path).stem
        cfg = json.loads((REPO / cfg_path).read_text(encoding="utf-8"))
        runs, prints = {"baseline": [], "candidate": []}, {}
        for n in range(1, args.runs + 1):
            order = ("baseline", "candidate") if n % 2 else ("candidate", "baseline")   # alternate the order
            for version in order:
                c = dict(cfg, out=f"{args.out}/{name}/{version}-out")
                cp = out / name / f"{version}.json"
                cp.parent.mkdir(parents=True, exist_ok=True)
                cp.write_text(json.dumps(c, indent=2), encoding="utf-8")
                script = base if version == "baseline" else REPO / DEDUP
                wall, peak = run_once(script, cp, out / name / f"{version}-run{n}.txt")
                runs[version].append({"wall_s": wall, "peak_mb": peak})
                prints[version] = fingerprint(REPO / c["out"])
        files_same = {f: prints["baseline"][0][f] == prints["candidate"][0][f] for f in FILES}
        summary_same = prints["baseline"][1] == prints["candidate"][1]
        ok &= all(files_same.values()) and summary_same
        report["configs"][name] = {"config": cfg_path, "runs": runs, "files_same": files_same,
                                   "summary_counts_same": summary_same,
                                   "sha256": prints["candidate"][0]}
        b = ", ".join(f"{r['wall_s']} s / {r['peak_mb']} MB" for r in runs["baseline"])
        c = ", ".join(f"{r['wall_s']} s / {r['peak_mb']} MB" for r in runs["candidate"])
        print(f"{name}: baseline {b} | candidate {c} | "
              f"{'SAME' if all(files_same.values()) and summary_same else 'DIFF'}")
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("ALL SAME" if ok else "DIFFERENCES FOUND", f"- report: {args.out}/report.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
