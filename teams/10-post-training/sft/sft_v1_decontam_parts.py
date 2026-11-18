"""Team 9 decontamination check of a gzipped C3 full conversion, one part at a time (G10, week-3 task 1).

    python sft_v1_decontam_parts.py --record results/sft_v1_records/<set>.full.record.json --parts-dir <dir> \
        --out-dir out/decontam [--workers 4] [--parts NAME ...]

For each part named in the full record: check that its gz bytes equal the record's, decompress it to
`<out-dir>/tmp/`, check the decompressed sha256 against the record's `plain_sha256`, run `decontam_run.run_set` on
it (Team 9's full fingerprint set, pinned set_sha256, canary scan, clean-file recheck; the clean copy is deleted
after the recheck), and delete the decompressed file. One `decontam_run` record per part goes to
`<out-dir>/<part>/<set>.record.json`. A part whose record already exists, is ok and was made from the same plain
sha256 is skipped, so a stopped run resumes. Nothing is written outside `--out-dir`; no network is used.

This measures and records which rows the fingerprint set flags. It writes no cleaned copy of the set; the
exclusion is applied later by `sft_v1_admit.py` from these records.
Exit code: 0 = every part has an ok record; 1 = a part failed a check or holds a canary; 2 = a tool or input error.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import decontam_run as dr  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def done_already(rec_path: Path, plain_sha256: str) -> bool:
    if not rec_path.is_file():
        return False
    r = json.loads(rec_path.read_text(encoding="utf-8"))
    return bool(r.get("ok")) and [i["sha256"] for i in r.get("inputs", [])] == [plain_sha256]


def one_part(set_id: str, part: dict, parts_dir: str, out_dir: str, tools: str) -> dict:
    out = Path(out_dir)
    rec_path = out / part["name"] / f"{set_id}.record.json"
    if done_already(rec_path, part["plain_sha256"]):
        return {"part": part["name"], "status": "reused"}
    gz = Path(parts_dir) / part["name"]
    if gz.stat().st_size != part["gz_bytes"] or sha256_file(gz) != part["gz_sha256"]:
        raise dr.RunError(f"{gz.name}: gz bytes differ from the record")
    tmp = out / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    plain = tmp / part["name"][: -len(".gz")]
    t0 = time.monotonic()
    try:
        with gzip.open(gz, "rb") as src, open(plain, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        if sha256_file(plain) != part["plain_sha256"]:
            raise dr.RunError(f"{gz.name}: decompressed sha256 differs from the record")
        rec = dr.run_set(set_id, [plain], out / part["name"], tools=tools, drop_clean=True)
    finally:
        plain.unlink(missing_ok=True)
    return {"part": part["name"], "status": "ok" if rec["ok"] else "failed", "rows": rec["rows_in"],
            "flagged": rec["rows_flagged"], "canary": rec["rows_canary"], "wall_s": round(time.monotonic() - t0, 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", required=True, type=Path)
    ap.add_argument("--parts-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--tools", default=str(dr.DEFAULT_TOOLS), help="Team 9's decontam folder")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--parts", nargs="*", help="only these part names (a test run)")
    a = ap.parse_args(argv)
    record = json.loads(a.record.read_text(encoding="utf-8"))
    parts = [p for p in record["parts"] if not a.parts or p["name"] in a.parts]
    if a.parts and len(parts) != len(a.parts):
        print("refused: a --parts name is not in the record", file=sys.stderr)
        return 2
    results, bad = [], 0
    try:
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            futs = [ex.submit(one_part, record["set"], p, str(a.parts_dir), str(a.out_dir), a.tools) for p in parts]
            for f in as_completed(futs):
                r = f.result()
                results.append(r)
                bad += r["status"] == "failed"
                print(json.dumps(r), flush=True)
    except (dr.RunError, OSError, json.JSONDecodeError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    new = [r for r in results if r["status"] != "reused"]
    print(f"{record['set']}: parts {len(results)} of {len(record['parts'])} in this run, new {len(new)}, "
          f"reused {len(results) - len(new)}, rows {sum(r.get('rows', 0) for r in new)}, "
          f"flagged {sum(r.get('flagged', 0) for r in new)}, canary {sum(r.get('canary', 0) for r in new)}, failed {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
