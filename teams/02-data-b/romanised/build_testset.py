#!/usr/bin/env python3
"""build_testset.py - the 100 labelled documents the D2 detector is tested on.

Positives: every document that at least one reader marked D2 (about 50, most in ind-hi-hplt).
Negatives: documents that at least one reader labelled and no reader marked D2, chosen with a fixed seed. Half of them
come from documents where at least LATIN_HARD of the letters are Latin, so the detector also meets English, brand names
and URLs, not only clean Indic text; the other half are drawn from all remaining labelled documents.
The choice of negatives does not use the detector, so the test does not favour it.

Usage
  python3 build_testset.py --sheets sheets --packs-dir packs --out testset_100.csv [--size 100] [--seed 0]
  sheets/<pack_id>/<handle>.csv is one reader's labels.csv (fetch_sheets.py makes this layout),
  packs/<pack_id>.parquet is the pack.
Writes the columns doc_id, pack, lang, reader_label (1 = some reader marked D2), n_readers, n_d2_marks, latin_pct,
stratum (d2 | latin_heavy | random). Ids and counts only, never text.
"""
import argparse
import csv
import random
import re
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

LATIN_HARD = 0.10
CODE = re.compile(r"\b[A-H]\d\b")


def read_sheets(sheets):
    """{(pack, doc_id): (n_readers, n_d2_marks)} from every reader's sheet."""
    seen = defaultdict(lambda: [0, 0])
    for path in sorted(Path(sheets).glob("*/*.csv")):
        pack = path.parent.name
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            for row in csv.DictReader(f):
                doc = (row.get("doc_id") or "").strip()
                if not doc or not (row.get("verdict") or "").strip():
                    continue
                seen[(pack, doc)][0] += 1
                seen[(pack, doc)][1] += "D2" in CODE.findall(row.get("diseases") or "")
    return seen


def latin_share(text):
    letters = [c for c in text if c.isalpha()]
    return sum(c.isascii() for c in letters) / len(letters) if letters else 0.0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the D2 detector test set.")
    ap.add_argument("--sheets", default="sheets", type=Path)
    ap.add_argument("--packs-dir", default="packs", type=Path)
    ap.add_argument("--out", default="testset_100.csv", type=Path)
    ap.add_argument("--size", default=100, type=int)
    ap.add_argument("--seed", default=0, type=int)
    a = ap.parse_args(argv)

    seen = read_sheets(a.sheets)
    latin = {}
    for pack in sorted({p for p, _ in seen}):
        path = a.packs_dir / f"{pack}.parquet"
        if not path.exists():
            print(f"skip {pack}: no parquet in {a.packs_dir}")
            continue
        for r in pq.read_table(path, columns=["doc_id", "text"]).to_pylist():
            if (pack, r["doc_id"]) in seen:
                latin[(pack, r["doc_id"])] = latin_share(r["text"] or "")

    pos = sorted(k for k in latin if seen[k][1] > 0)
    neg = sorted(k for k in latin if seen[k][1] == 0)
    rng = random.Random(a.seed)
    n_neg = a.size - len(pos)
    hard = [k for k in neg if latin[k] >= LATIN_HARD]
    picked_hard = rng.sample(hard, min(len(hard), n_neg // 2))
    rest = [k for k in neg if k not in set(picked_hard)]
    picked_rest = rng.sample(rest, n_neg - len(picked_hard))

    rows = [(k, "d2") for k in pos] + [(k, "latin_heavy") for k in picked_hard] + [(k, "random") for k in picked_rest]
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["doc_id", "pack", "lang", "reader_label", "n_readers", "n_d2_marks", "latin_pct", "stratum"])
        for (pack, doc), stratum in sorted(rows, key=lambda r: (r[1] != "d2", r[0])):
            n, d2 = seen[(pack, doc)]
            w.writerow([doc, pack, pack.split("-")[1], int(d2 > 0), n, d2, round(100 * latin[(pack, doc)], 1), stratum])
    print(f"wrote {a.out}: {len(pos)} D2 + {len(picked_hard)} latin-heavy + {len(picked_rest)} random negatives "
          f"(from {len(latin)} labelled documents, {len(hard)} of the negatives latin-heavy)")


if __name__ == "__main__":
    main()
