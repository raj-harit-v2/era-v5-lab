"""F2 alone, after dedup: drop the docs G9's benchmark fingerprints flag, keep the rest unchanged.

  python -I teams/01-data-a/spec_v1/run_f2.py --inputs <deduped_dir> --out <final_dir>

F2 is G9's decontamination check (teams/09-evaluation/decontam, fpset.py) with G9's fingerprint set, unchanged: a doc
is dropped when it shares one run of words (13 words, 20 tokens for code) with a benchmark item of the set, or holds a
benchmark canary string. It is the F2 of spec_v1's f2_rule.py, run alone on the deduped docs.

--inputs takes folders (every *.parquet under them, at any depth) or Parquet files, several if needed. Each file needs
doc_id and text columns; other columns pass through. For each file, <out> gets the same relative path holding only the
docs F2 keeps, with the same schema and unchanged text, and a <file>.f2.json next to it with the counts, the input's
sha256, the set_sha256, the run_f2.py sha256 and, for each dropped doc_id, up to 5 benchmark items and the character
offset. It never holds document or benchmark text. <out>/f2_summary.json totals the run.

The set is pinned: SET names its folder and SET_SHA256 its set_sha256 (fingerprints v2, as in G9's #342), and a set with
another set_sha256 is refused. F2_FINGERPRINTS can point to a copy of the same set elsewhere. A future set needs its own
harm test, then both changed here. The full set needs about 1.1 GB of memory and about 20 s to load; it is loaded and
checked once, before anything is written. It finds copies only (G9's README): a reworded, translated or very short item
is not found, nor a benchmark outside the set.

A doc whose check raises is kept out and reported by doc_id and error type, and the run exits with code 1.
kept + dropped + errors must equal the input rows, or the run stops. A file whose .f2.json already names the same input
sha256 and set_sha256 is skipped, so a stopped run resumes: the Parquet is written to a .tmp file and renamed, and the
.f2.json is written last. --out may not be inside an input folder, nor an input inside --out.
"""
import argparse, hashlib, importlib.util, json, os, sys, time
from functools import cache
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

SET = "v2"  # G9's fingerprint set: teams/09-evaluation/fingerprints/<SET>
SET_SHA256 = "2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a"
G9 = Path(__file__).resolve().parents[2] / "09-evaluation" / "decontam"
BATCH = 1000


@cache
def fingerprints(benchmarks=None):
    """G9's fingerprint set, checked against the pin and its SHA256SUMS, loaded once. benchmarks (a tuple of IDs) is for the tests only."""
    path = Path(os.environ.get("F2_FINGERPRINTS") or G9.parent / "fingerprints" / SET)
    if not (path / "SHA256SUMS").is_file():
        raise FileNotFoundError(f"no fingerprint set at {path}: SET or F2_FINGERPRINTS names a missing folder")
    got = hashlib.sha256((path / "SHA256SUMS").read_text(encoding="utf-8").encode("utf-8")).hexdigest()  # as fpset.py computes it
    if got != SET_SHA256:
        raise ValueError(f"the fingerprint set at {path} has set_sha256 {got}, not the pinned {SET_SHA256}. "
                         "A new set needs its own harm test before SET and SET_SHA256 change.")
    saved = sys.modules.pop("normalize", None)  # fpset imports G9's normalize: load it for this import only
    sys.path.insert(0, str(G9))
    try:
        spec = importlib.util.spec_from_file_location("g9_fpset", G9 / "fpset.py")
        fpset = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fpset)
    finally:
        sys.path.remove(str(G9))
        sys.modules.pop("normalize", None)
        if saved is not None:
            sys.modules["normalize"] = saved
    return fpset.Fingerprints(path, list(benchmarks) if benchmarks else None)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def inputs(paths):
    """(file, its path relative to the folder given, or its name)."""
    for p in paths:
        if p.is_file():
            yield p, Path(p.name)
        elif p.is_dir():
            yield from ((f, f.relative_to(p)) for f in sorted(p.rglob("*.parquet")))
        else:
            sys.exit(f"--inputs: {p} is not a file or folder")


def run_file(src, dst, fp, code_sha):
    """F2 on one Parquet file: writes dst and dst.f2.json, returns the report."""
    report_path = dst.with_name(dst.name + ".f2.json")
    in_sha = sha256(src)
    if report_path.exists():
        old = json.loads(report_path.read_text(encoding="utf-8"))
        if old.get("input_sha256") == in_sha and old.get("set_sha256") == fp.set_sha256 and dst.exists():
            print(f"{src}: done before, skipped", file=sys.stderr)
            return old
    pf = pq.ParquetFile(src)
    missing = {"doc_id", "text"} - set(pf.schema_arrow.names)
    if missing:
        sys.exit(f"{src}: no {', '.join(sorted(missing))} column")
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    t0, rows, kept, dropped, errors = time.time(), 0, 0, [], []
    with pq.ParquetWriter(tmp, pf.schema_arrow) as w:
        for batch in pf.iter_batches(batch_size=BATCH):
            keep = []
            for doc_id, text in zip(batch.column("doc_id").to_pylist(), batch.column("text").to_pylist()):
                try:
                    flagged, hits = fp.check(text or "")
                except Exception as e:  # kept out, reported by type, never by text
                    errors.append([doc_id, type(e).__name__])
                    keep.append(False)
                    continue
                if flagged:
                    dropped.append({"doc_id": doc_id, "items": [h["item"] for h in hits[:5]], "offset": hits[0]["offset"]})
                keep.append(not flagged)
            rows += batch.num_rows
            kept += sum(keep)
            w.write_table(pa.Table.from_batches([batch]).filter(pa.array(keep, pa.bool_())))
            print(f"{src.name}: {rows}/{pf.metadata.num_rows} dropped={len(dropped)} errors={len(errors)}", file=sys.stderr, flush=True)
    if kept + len(dropped) + len(errors) != rows or rows != pf.metadata.num_rows:
        tmp.unlink()
        sys.exit(f"{src}: counts do not add up: rows {rows}, kept {kept}, dropped {len(dropped)}, errors {len(errors)}")
    tmp.replace(dst)
    report = {"input": src.as_posix(), "input_sha256": in_sha, "output_sha256": sha256(dst), "set_sha256": fp.set_sha256,
              "run_f2_py_sha256": code_sha, "rows": rows, "kept": kept, "dropped_by_f2": len(dropped), "errors": errors,
              "seconds": round(time.time() - t0, 1), "dropped": dropped}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", type=Path, nargs="+", required=True, help="deduped Parquet folders or files")
    ap.add_argument("--out", type=Path, required=True, help="the final folder")
    args = ap.parse_args()
    out = args.out.resolve()
    for p in args.inputs:
        p = p.resolve()
        if p.is_dir() and (out == p or p in out.parents) or out in p.parents:
            sys.exit(f"--out {args.out} and --inputs {p} overlap: the output would be read as input")
    files = list(inputs(args.inputs))
    if not files:
        sys.exit("--inputs: no .parquet files")
    names = [rel for _, rel in files]
    if len(set(names)) != len(names):
        sys.exit("--inputs: two inputs map to the same output path; give them in separate runs")
    try:
        fp = fingerprints()  # load and check the pinned set before anything is written
    except (OSError, ValueError) as e:
        sys.exit(f"F2: {e}")
    code_sha = sha256(Path(__file__))
    t0, reports = time.time(), []
    for src, rel in files:
        reports.append(run_file(src, out / rel, fp, code_sha))
    total = {k: sum(r[k] for r in reports) for k in ("rows", "kept", "dropped_by_f2")}
    total["errors"] = sum(len(r["errors"]) for r in reports)
    summary = {"set_sha256": fp.set_sha256, "run_f2_py_sha256": code_sha, "files": len(reports), **total,
               "seconds": round(time.time() - t0, 1),
               "per_file": [{k: r[k] for k in ("input", "input_sha256", "output_sha256", "rows", "kept", "dropped_by_f2")} for r in reports]}
    out.mkdir(parents=True, exist_ok=True)
    (out / "f2_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print({k: v for k, v in summary.items() if k != "per_file"})
    sys.exit(1 if total["errors"] else 0)


if __name__ == "__main__":
    main()
