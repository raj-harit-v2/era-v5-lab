"""Reproduce overlap speed/equivalence checks offline; all generated files stay under out/.

Default inputs are synthetic, not the unavailable cleaned sample used in the original PR timing.
Use --inputs <cleaned-root> to select the first --per-pack rows of each benchmark pack instead.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
PACKS = ("code-rust", "en-dclm", "math-finemath")
FILES = ("overlap.py", "h1_sha256.py", "jaccard_matrix.py", "overlap_rules.py", "overlap_report.py")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root, inputs, count):
    import pyarrow as pa
    import pyarrow.parquet as pq
    rows = {p: [] for p in PACKS}
    sources = []
    if inputs:
        for path in sorted((REPO / inputs / "train").rglob("*.parquet")):
            table = pq.read_table(path, columns=["pack_id", "doc_id", "text"])
            used = False
            for row in table.to_pylist():
                pack = row["pack_id"]
                if pack in rows and len(rows[pack]) < count:
                    rows[pack].append(row)
                    used = True
            if used:
                sources.append({"path": str(path.relative_to(REPO)), "sha256": digest(path)})
            if all(len(v) == count for v in rows.values()):
                break
    else:
        for pack in PACKS:
            for i in range(count):
                group, variant = divmod(i, 4)
                rng = random.Random(group)
                words = [f"word{rng.randrange(1000000)}" for _ in range(150)]
                if pack == "code-rust":
                    text = "// " + " ".join(words) + "\n" + "\n".join(
                        f"let value_{group}_{j} = input_{group} + {j};" for j in range(24))
                    if variant == 1:
                        text += "\n// extra comment"
                    elif variant >= 2:
                        text = text.replace(f"value_{group}_0", f"changed_{variant}", 1)
                else:
                    words[-1] = f"variant{min(variant, 2)}"
                    text = " ".join(words)
                    if pack == "math-finemath":
                        text += f" solve x = {group}"
                rows[pack].append({"pack_id": pack, "doc_id": f"{pack}-{i:06d}", "text": text})
    if any(len(v) != count for v in rows.values()):
        raise ValueError(f"need {count} rows per pack: { {p: len(v) for p, v in rows.items()} }")
    manifest = {"kind": "cleaned subset" if inputs else "synthetic", "per_pack": count,
                "sources": sources, "parts": []}
    for pack, values in rows.items():
        path = root / "inputs/train" / pack / "part-00000.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(values), path)
        manifest["parts"].append({"path": str(path.relative_to(root)), "sha256": digest(path), "rows": len(values)})
    (root / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def snapshot(root, label, ref):
    dest = root / label
    dedup = dest / "teams/01-data-a/dedup"
    dedup.mkdir(parents=True)
    for name in FILES:
        source = Path("teams/01-data-a/dedup") / name
        content = (REPO / source).read_bytes() if ref is None else subprocess.check_output(
            ["git", "show", f"{ref}:{source}"], cwd=REPO)
        (dedup / name).write_bytes(content)
    for name in ("teams/01-data-a/spec_v1/normalize.py", "teams/01-data-a/spec_v1/tools/normalize.py"):
        if ref is None:
            if not (REPO / name).exists():
                continue
            content = (REPO / name).read_bytes()
        else:
            result = subprocess.run(["git", "show", f"{ref}:{name}"], cwd=REPO, capture_output=True)
            if result.returncode:
                continue
            content = result.stdout
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (dest / "out").mkdir()
    (dest / "out/inputs").symlink_to(root / "inputs", target_is_directory=True)
    return dest


def compare(before, after):
    from scipy import sparse
    byte_files = ("overlap_pairs.csv", "overlap_docs.parquet", "overlap_by_pack.csv", "overlap_histogram.csv",
                  "overlap_matrix.csv", "overlap_matrix_counts.csv")
    for name in byte_files:
        if (before / name).read_bytes() != (after / name).read_bytes():
            raise AssertionError(f"changed artifact: {name}")
    def matches(folder):
        with (folder / "overlap_matches.csv").open(newline="") as f:
            return sorted(tuple(row) for row in csv.reader(f))
    assert matches(before) == matches(after), "changed qualifying pairs"
    a, b = (sparse.load_npz(p / "overlap_matrix.npz") for p in (before, after))
    assert a.shape == b.shape and (a != b).nnz == 0, "changed sparse scores"
    a, b = (json.loads((p / "overlap_summary.json").read_text()) for p in (before, after))
    for name in ("shingles", "wall_seconds", "peak_rss_mb", "versions", "outputs"):
        a.pop(name, None)
        b.pop(name, None)
    assert a == b, "changed summary counts/config/rules"
    return {"byte_identical": list(byte_files), "matches": "same rows", "sparse_matrix": "same values",
            "summary": "same counts/config/rules; timing, versions, hashes and hashing description excluded"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="out/bench_speed_review")
    ap.add_argument("--inputs", help="cleaned root relative to repo; omit for deterministic synthetic inputs")
    ap.add_argument("--per-pack", type=int, default=4000)
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--baseline", default="43fa750014b3f6deec6347ece82439e7beeefebb")
    ap.add_argument("--candidate-ref", help="benchmark this commit instead of current working files")
    args = ap.parse_args()
    root = (REPO / args.out).resolve()
    if not root.is_relative_to(REPO / "out") or root == REPO / "out":
        ap.error("--out must be a new directory inside repository out/")
    if args.per_pack < 1 or args.runs < 1:
        ap.error("--per-pack and --runs must be positive")
    if args.inputs and (Path(args.inputs).is_absolute() or not (REPO / args.inputs).resolve().is_relative_to(REPO)):
        ap.error("--inputs must be relative to the repository root")
    root.mkdir(parents=True, exist_ok=False)
    manifest = prepare(root, args.inputs, args.per_pack)
    config = {"inputs": "out/inputs", "splits": ["train"], "out": "out/overlap", "expected_packs": list(PACKS)}
    report = {"inputs": manifest, "baseline": args.baseline, "candidate": args.candidate_ref or "working files", "runs": []}
    snapshots = {label: snapshot(root, label, ref) for label, ref in
                 (("baseline", args.baseline), ("candidate", args.candidate_ref))}
    report["source_sha256"] = {label: {str(p.relative_to(dest)): digest(p)
                                      for p in sorted((dest / "teams").rglob("*.py"))}
                               for label, dest in snapshots.items()}
    for run in range(1, args.runs + 1):
        # Alternate order to reduce filesystem/cache order bias.
        for label in (("baseline", "candidate") if run % 2 else ("candidate", "baseline")):
            dest = snapshots[label]
            (dest / "config.json").write_text(json.dumps(config, indent=2) + "\n")
            command = [sys.executable, "-I", str(dest / "teams/01-data-a/dedup/overlap.py"),
                       "--config", str(dest / "config.json")]
            started = time.perf_counter()
            with (root / f"{label}-{run}.txt").open("w") as log:
                subprocess.run(command, cwd=dest, stdout=log, stderr=subprocess.STDOUT, check=True)
            seconds = time.perf_counter() - started
            result = dest / "out/overlap"
            summary = json.loads((result / "overlap_summary.json").read_text())
            report["runs"].append({"label": label, "run": run, "wall_seconds": round(seconds, 3),
                                   "scoring_seconds": summary["wall_seconds"], "peak_rss_mb": summary["peak_rss_mb"],
                                   "versions": summary["versions"]})
            shutil.move(result, root / f"{label}-{run}")
            print(json.dumps(report["runs"][-1]), flush=True)
        report["equivalence"] = compare(root / f"baseline-{run}", root / f"candidate-{run}")
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: all artifact comparisons; report and full console logs in {root.relative_to(REPO)}", flush=True)


if __name__ == "__main__":
    main()
