"""Stand-in for shards/run_shards.py in the runner's tests: same command line, a summary like the real one, no tokenizer.

The real run_shards.py needs torch and a tokenizer and has its own tests (shards/tests), so the runner's tests use this.
It needs <manifest folder>/cleaning_pipeline.json (written by the runner's shard stage before it starts), "shards" every
train part (of the --pack packs, if given) with a dummy .bin, counts the other splits as not_sharded, and refuses an --out
that already holds a .bin, like the real one (exit 1, summary untouched). Environment switches for the tests:
  FAKE_SHARDS_FAIL     any value: mark the first train part failed (exit 1)
  FAKE_SHARDS_TRUNCATE any value: mark the first written part truncated (cut short; exit 0, like the real one)
  FAKE_SHARDS_NONE     any value: write nothing and exit 2 (a crashed process)
  FAKE_SHARDS_BAD_RUN  any value: write another run_id in the summary
"""
import argparse, hashlib, json, os, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--input", type=Path, required=True)
ap.add_argument("--manifest", type=Path, required=True)
ap.add_argument("--tokenizer", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--pack", action="append", default=[])
ap.add_argument("--tokens", type=int)
ap.add_argument("--pack-table", type=Path)
ap.add_argument("--any-tokenizer", action="store_true")
ap.add_argument("--dataset-version")
a = ap.parse_args()
if os.environ.get("FAKE_SHARDS_NONE"):
    sys.exit(2)
record = a.manifest.parent / "cleaning_pipeline.json"
if not record.is_file():
    sys.exit(f"no {record}")
if a.out.is_dir() and list(a.out.glob("*.bin")):
    sys.exit("already in the out folder")
a.out.mkdir(parents=True, exist_ok=True)
parts, counts = {}, {"written": 0, "failed": 0, "skipped": 0, "not_sharded": 0, "truncated": 0, "shards": 0}
for f in sorted(a.input.glob("*/*/*.parquet")):
    split, pack = f.parent.parent.name, f.parent.name
    if a.pack and pack not in a.pack:
        continue
    name = f"{split}/{pack}/{f.name}"
    if split != "train":
        parts[name] = {"pack_id": pack, "status": "not_sharded"}
        counts["not_sharded"] += 1
    elif os.environ.get("FAKE_SHARDS_FAIL") and not counts["failed"]:
        parts[name] = {"pack_id": pack, "status": "failed", "reason": "made up"}
        counts["failed"] += 1
    else:
        sid = f"{pack}-{split}-{int(f.stem.split('-')[1]):06d}"
        (a.out / f"{sid}.bin").write_bytes(b"shard")
        cut = bool(os.environ.get("FAKE_SHARDS_TRUNCATE")) and not counts["truncated"]
        parts[name] = {"pack_id": pack, "status": "written", "shards": [{"shard_id": sid}], "truncated": cut}
        counts["written"] += 1
        counts["shards"] += 1
        counts["truncated"] += cut
manifest = json.loads(a.manifest.read_text(encoding="utf-8"))
(a.out / "args.json").write_text(json.dumps({"tokens": a.tokens, "packs": a.pack, "any_tokenizer": a.any_tokenizer, "dataset_version": a.dataset_version,
                                             "pack_table": str(a.pack_table)}), encoding="utf-8")
(a.out / "shards_summary.json").write_text(json.dumps({
    "run_id": "another-run" if os.environ.get("FAKE_SHARDS_BAD_RUN") else manifest["run_id"],
    "cleaning_pipeline_sha256": hashlib.sha256(record.read_bytes()).hexdigest(), "parts": parts, "counts": counts}), encoding="utf-8")
sys.exit(1 if counts["failed"] else 0)
