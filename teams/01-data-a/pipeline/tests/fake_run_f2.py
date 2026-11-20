"""Stand-in for run_f2.py in the runner's tests: same command line, same outputs, no fingerprint set.

The real F2 needs G9's full fingerprint set (about 1.1 GB) and lives in its own PR with its own tests, so the runner's
tests use this instead. Like run_f2.py it writes <out>/<rel>.parquet, <out>/<rel>.parquet.f2.json (with the input's
absolute path and the seconds taken, which differ between runs) and <out>/f2_summary.json, and exits 1 when a doc raised.
Environment switches for the tests:
  FAKE_F2_DROP      comma-separated doc_ids to drop as benchmark copies
  FAKE_F2_ERROR     comma-separated doc_ids whose check "raises": kept out and reported as errors
  FAKE_F2_BAD_SHA   any value: report a wrong input_sha256 (an F2 that read something else)
  FAKE_F2_CRASH     a text: exit 2 without writing anything when an input path contains it (a crashed process)
"""
import argparse, hashlib, json, os, sys, time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SET = "2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ids(name):
    return set(filter(None, os.environ.get(name, "").split(",")))


ap = argparse.ArgumentParser()
ap.add_argument("--inputs", type=Path, nargs="+", required=True)
ap.add_argument("--out", type=Path, required=True)
args = ap.parse_args()
drop, err = ids("FAKE_F2_DROP"), ids("FAKE_F2_ERROR")
crash = os.environ.get("FAKE_F2_CRASH")
if crash and any(crash in p.as_posix() for p in args.inputs):
    sys.exit(2)
reports, t0 = [], time.time()
for root in args.inputs:
    for src in sorted(root.rglob("*.parquet")):
        rel = src.relative_to(root)
        dst = args.out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        t = pq.read_table(src)
        doc_ids = t.column("doc_id").to_pylist()
        keep = [d not in drop and d not in err for d in doc_ids]
        pq.write_table(t.filter(pa.array(keep, pa.bool_())), dst)
        dropped = [{"doc_id": d, "items": ["fake:1"], "offset": 0} for d in doc_ids if d in drop]
        errors = [[d, "ValueError"] for d in doc_ids if d in err]
        r = {"input": src.resolve().as_posix(), "input_sha256": "0" * 64 if os.environ.get("FAKE_F2_BAD_SHA") else sha(src),
             "output_sha256": sha(dst), "set_sha256": SET, "run_f2_py_sha256": sha(__file__), "rows": len(doc_ids),
             "kept": sum(keep), "dropped_by_f2": len(dropped), "errors": errors, "seconds": round(time.time() - t0, 3),
             "dropped": dropped}
        dst.with_name(dst.name + ".f2.json").write_text(json.dumps(r), encoding="utf-8")
        reports.append(r)
args.out.mkdir(parents=True, exist_ok=True)
total = {k: sum(r[k] for r in reports) for k in ("rows", "kept", "dropped_by_f2")}
total["errors"] = sum(len(r["errors"]) for r in reports)
(args.out / "f2_summary.json").write_text(json.dumps({"set_sha256": SET, "files": len(reports), **total,
                                                      "seconds": round(time.time() - t0, 3)}), encoding="utf-8")
sys.exit(1 if total["errors"] else 0)
