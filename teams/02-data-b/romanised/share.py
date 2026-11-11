#!/usr/bin/env python3
"""share.py - the share of documents that detector.py flags as romanised Indic, per language, on the full ind-* packs.

The share is measured on the full packs, not on the gold set: gold documents are clean by definition, so they would hide
exactly what is being counted. A pack's language is the second part of its id (ind-hi-hplt -> hi).

Usage
  python3 share.py --packs-dir packs --out romanised_share_v1.csv [--by-pack romanised_share_by_pack_v1.csv]
Writes one row per language: lang, packs, docs, flagged, share_pct, and (with --by-pack) one row per pack.
Ids and counts only, never text.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

import detector


def write(path, head, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Share of romanised Indic documents per language.")
    ap.add_argument("--packs-dir", default="packs", type=Path)
    ap.add_argument("--out", default="romanised_share_v1.csv", type=Path)
    ap.add_argument("--by-pack", default="romanised_share_by_pack_v1.csv", type=Path)
    a = ap.parse_args(argv)

    per_pack = {}
    for path in sorted(a.packs_dir.glob("ind-*.parquet")):
        docs = pq.read_table(path, columns=["text"]).column("text").to_pylist()
        per_pack[path.stem] = (len(docs), sum(detector.detect(t or "")["romanised"] for t in docs))
    if not per_pack:
        raise SystemExit(f"error: no ind-*.parquet in {a.packs_dir}")

    lang = defaultdict(lambda: [[], 0, 0])
    for pack, (n, k) in per_pack.items():
        g = lang[pack.split("-")[1]]
        g[0].append(pack)
        g[1] += n
        g[2] += k
    rows = [(l, " ".join(p), n, k, round(100 * k / n, 2)) for l, (p, n, k) in sorted(lang.items())]
    write(a.out, ["lang", "packs", "docs", "flagged", "share_pct"], rows)
    if a.by_pack:
        write(a.by_pack, ["pack", "lang", "docs", "flagged", "share_pct"],
              [(p, p.split("-")[1], n, k, round(100 * k / n, 2)) for p, (n, k) in sorted(per_pack.items())])
    total_n = sum(n for n, _ in per_pack.values())
    total_k = sum(k for _, k in per_pack.values())
    for r in rows:
        print(f"{r[0]:3} {r[3]:4} of {r[2]:5}  {r[4]:5.2f}%   {r[1]}")
    print(f"all {total_k:4} of {total_n:5}  {100 * total_k / total_n:5.2f}%")


if __name__ == "__main__":
    main()
