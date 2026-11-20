"""Stand-in for run_f2.py as a module, for f2_pool.py in the runner's tests: the same names f2_pool.py uses (G9, SET,
SET_SHA256, sha256, fingerprints, run_file), the same outputs as fake_run_f2.py, and no fingerprint set to load.

G9, SET and SET_SHA256 are run_f2.py's, so f2_pool.py's pin check runs against the real set's SHA256SUMS (it is in the
repository); fingerprints() returns a stand-in with that set_sha256. run_file() drops the doc_ids in FAKE_F2_DROP and
reports those in FAKE_F2_ERROR as errors, like fake_run_f2.py, and skips a file done before, like run_f2.py.
"""
import hashlib, json, os, time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

TEAMS = Path(__file__).resolve().parents[3]
G9 = TEAMS / "09-evaluation" / "decontam"
SET = "v2"
SET_SHA256 = "2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class _Set:
    set_sha256 = SET_SHA256


def fingerprints(benchmarks=None):
    return _Set()


def _ids(name):
    return set(filter(None, os.environ.get(name, "").split(",")))


def run_file(src, dst, fp, code_sha):
    report_path = dst.with_name(dst.name + ".f2.json")
    in_sha = sha256(src)
    if report_path.exists():
        old = json.loads(report_path.read_text(encoding="utf-8"))
        if old.get("input_sha256") == in_sha and old.get("set_sha256") == fp.set_sha256 and dst.exists():
            return old
    t0 = time.time()
    drop, err = _ids("FAKE_F2_DROP"), _ids("FAKE_F2_ERROR")
    dst.parent.mkdir(parents=True, exist_ok=True)
    t = pq.read_table(src)
    doc_ids = t.column("doc_id").to_pylist()
    keep = [d not in drop and d not in err for d in doc_ids]
    pq.write_table(t.filter(pa.array(keep, pa.bool_())), dst)
    report = {"input": Path(src).as_posix(), "input_sha256": in_sha, "output_sha256": sha256(dst), "set_sha256": fp.set_sha256,
              "run_f2_py_sha256": code_sha, "rows": len(doc_ids), "kept": sum(keep),
              "dropped_by_f2": sum(d in drop for d in doc_ids), "errors": [[d, "ValueError"] for d in doc_ids if d in err],
              "seconds": round(time.time() - t0, 3),
              "dropped": [{"doc_id": d, "items": ["fake:1"], "offset": 0} for d in doc_ids if d in drop]}
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report
