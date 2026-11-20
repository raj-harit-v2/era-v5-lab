#!/usr/bin/env python3
"""zwj_counts.py - Gate 3, week 3 task 4: ZWJ (U+200D) and ZWNJ (U+200C) counts before and after cleaning.

Before: raw CAP-1 pack   <packs-dir>/<pack_id>/Part_1/part-00000.parquet   (doc_id, text)
After : p1536 shard      <shards-dir>/<pack_id>/<pack_id>-train-000000.{bin,idx.npy,docs.parquet}
        (downloaded from shard_links.tsv when missing; decoded with the frozen tokenizer by read_shard()
        from indic_audit.py)

Per pack, only the documents that are in the shard (doc_id in .docs.parquet) are counted.
Allowed change: the tokenizer folds an old Malayalam chillu (consonant + virama + ZWJ) into one character, which
removes one ZWJ per chillu. So a document is "changed" when
    zwj_shard  != zwj_raw - (old chillu in raw)      or      zwnj_shard != zwnj_raw

Output CSV: pack_id, docs_kept, zwj_raw, zwj_shard, zwnj_raw, zwnj_shard, docs_changed   (counts only, no text)

Speed: numpy for the shard, Rust batch decode for the text, pyarrow compute kernels for the counts.
No Python loop over tokens or characters.

Usage
  python zwj_counts.py --packs-dir Cap1-packs/Cap1-packs --shards-dir shards --tokenizer tokenizer.json \
      --links shard_links.tsv --out zwj_counts.csv
"""
import argparse
import csv
import hashlib
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from indic_audit import read_shard      # #523: checks header, index and EOS, then batch-decodes
from tokenizers import Tokenizer

ZWJ, ZWNJ = "\u200d", "\u200c"
# Old-style Malayalam chillu: consonant + virama + ZWJ. The tokenizer normalizer folds each into one atomic chillu.
OLD_CHILLU = "(ണ|ന|ര|ല|ള|ക)\u0d4d\u200d"
FROZEN_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"   # frozen p1536 tokenizer
SHARD_SUFFIXES = (".bin", ".idx.npy", ".docs.parquet")


def download_shards(links_tsv, shards_dir):
    """Download the .bin, .idx.npy and .docs.parquet of every ind-* shard listed in shard_links.tsv (skips files
    that are already there). Returns the sorted pack ids."""
    jobs, packs = [], set()
    for line in Path(links_tsv).read_text(encoding="utf-8").splitlines():
        name, _, url = line.partition("\t")
        if name.startswith("ind-") and name.endswith(SHARD_SUFFIXES):
            pack_id = name.split("-train-")[0]
            packs.add(pack_id)
            dest = Path(shards_dir) / pack_id / name
            if not dest.exists():
                jobs.append((url, dest))

    def fetch(job):
        url, dest = job
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(dest)                                   # a file only appears under its real name when complete

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(fetch, jobs))
    print(f"downloaded {len(jobs)} files for {len(packs)} shards")
    return sorted(packs)


def count_pack(pack_id, packs_dir, shards_dir, tok):
    """One CSV row: ZWJ and ZWNJ counts in the raw and the shard text of the documents the shard kept."""
    raw = pq.read_table(Path(packs_dir) / pack_id / "Part_1" / "part-00000.parquet", columns=["doc_id", "text"])
    doc_ids, texts = read_shard(Path(shards_dir) / pack_id / f"{pack_id}-train-000000.bin", tok)
    shard = pa.table({"doc_id": doc_ids, "shard_text": texts})
    kept = raw.join(shard, "doc_id", join_type="inner")      # only documents that are in the shard
    raw_text, shard_text = kept.column("text").combine_chunks(), kept.column("shard_text").combine_chunks()

    zwj_raw, zwj_shard = pc.count_substring(raw_text, ZWJ), pc.count_substring(shard_text, ZWJ)
    zwnj_raw, zwnj_shard = pc.count_substring(raw_text, ZWNJ), pc.count_substring(shard_text, ZWNJ)
    chillu = pc.count_substring_regex(raw_text, OLD_CHILLU)  # ZWJ the normalizer is allowed to remove
    changed = pc.or_(pc.not_equal(zwj_shard, pc.subtract(zwj_raw, chillu)), pc.not_equal(zwnj_shard, zwnj_raw))

    total = lambda a: pc.sum(a).as_py() or 0
    return {"pack_id": pack_id, "docs_kept": kept.num_rows,
            "zwj_raw": total(zwj_raw), "zwj_shard": total(zwj_shard),
            "zwnj_raw": total(zwnj_raw), "zwnj_shard": total(zwnj_shard),
            "docs_changed": total(changed.cast(pa.int64()))}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--packs-dir", required=True)
    ap.add_argument("--shards-dir", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--links", required=True, help="shard_links.tsv (file name <TAB> url)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    start = time.time()
    got = hashlib.sha256(Path(a.tokenizer).read_bytes()).hexdigest()
    if got != FROZEN_SHA256:
        raise SystemExit(f"{a.tokenizer}: sha256 {got} is not the frozen tokenizer {FROZEN_SHA256}")
    tok = Tokenizer.from_file(a.tokenizer)
    pack_ids = download_shards(a.links, a.shards_dir)
    rows = [count_pack(p, a.packs_dir, a.shards_dir, tok) for p in pack_ids]

    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(" | ".join(rows[0]))
    for r in rows:
        print(" | ".join(str(v) for v in r.values()))
    print(f"packs {len(rows)}, docs_changed {sum(r['docs_changed'] for r in rows)}, "
          f"wall time {time.time() - start:.1f} s")


if __name__ == "__main__":
    main()
