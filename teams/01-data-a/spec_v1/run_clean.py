"""Run clean.py on one pack. Reads only the pack, writes only to --out, needs no network.

  python run_clean.py --pack code-go.parquet --out out

The file must be named <pack_id>.parquet, for one of the 13 packs clean.py has rules for. Any other name stops the run with
exit code 1 before the pack is read or anything is written: clean.py would pass every doc through unchanged.
Writes out/<pack>_clean.parquet (the kept docs, with their cleaned text) and out/<pack>_summary.json (counts, dropped doc_ids
and the SHA-256 of the clean.py that ran, no text).
"""
import argparse, hashlib, json, sys, time
from collections import Counter
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean as c

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--pack", type=Path, required=True)
ap.add_argument("--out", type=Path, default=Path("out"))
args = ap.parse_args()
pack = args.pack.stem
if pack not in c._FAMILY:  # no rule applies to it, so a run would "succeed" without cleaning anything
    sys.exit(f"{args.pack.name}: {pack!r} is not one of the {len(c._FAMILY)} packs clean.py has rules for, so nothing would be cleaned. "
             f"Name the file <pack_id>.parquet, with one of: {', '.join(sorted(c._FAMILY))}")
rows = pq.read_table(args.pack).to_pylist()
for row in rows:  # clean.py picks the rules by pack_id: a pack without the column takes its file name
    if row.setdefault("pack_id", pack) != pack:
        sys.exit(f"{args.pack.name}: doc_id {row['doc_id']} has pack_id {row['pack_id']!r}")
args.out.mkdir(parents=True, exist_ok=True)
t0, actions, dropped, errors, kept = time.time(), Counter(), [], [], []
for row in rows:
    try:
        action, text = c.clean(row)
    except Exception as e:  # a rule that crashes keeps the doc out and is reported by type, never by text
        errors.append([row["doc_id"], type(e).__name__])
        continue
    actions[action] += 1
    if action == "drop": dropped.append(row["doc_id"])
    else: kept.append(dict(row, text=text))
pq.write_table(pa.Table.from_pylist(kept), args.out / f"{args.pack.stem}_clean.parquet")
summary = {"pack": args.pack.name, "pack_id": pack, "family": c._FAMILY[pack], "rows": len(rows), "actions": dict(actions), "errors": errors, "dropped": dropped, "seconds": round(time.time() - t0, 1), "docs_per_second": round(len(rows) / max(time.time() - t0, 1e-9), 1),
           "clean_py_sha256": hashlib.sha256(Path(c.__file__).read_bytes()).hexdigest()}  # which rules ran: the same hash means the same clean.py
(args.out / f"{args.pack.stem}_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
print({k: v for k, v in summary.items() if k != "dropped"}, "dropped:", len(dropped))
sys.exit(1 if errors else 0)
