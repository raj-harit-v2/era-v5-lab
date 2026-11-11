#!/usr/bin/env python3
"""make_review_pack.py - pick the translated documents our readers rate, and write one blank sheet per language.

For each of the four sangraha-s packs (Hindi, Kannada, Tamil, Telugu) it picks N documents (default 50) and marks
the first S of them (default 25) as shared: two readers rate the shared documents separately (agreement, task 7).
25 shared leaves room above the minimum of 20 that the agreement check needs.

The pick is a hash ranking: each doc_id gets sha256("<seed>:<doc_id>"), and the N lowest hashes win. A rerun with
the same seed and pack gives the same documents on any machine and any Python version, whatever the row order.
Documents with empty text, or longer than --max-chars (default 10000 characters), are never picked.

The sheets hold IDs only: review_pack/<lang>.csv with doc_id, shared (yes/no), score (blank) and note (blank).
Each reader copies the sheet to ratings/<lang>_<handle>.csv and fills in score (1 to 5) and note (codes and
offsets only), which is the layout score_ratings.py reads.

Usage:  python3 make_review_pack.py PACK_DIR [--out DIR] [--seed 212] [--n 50] [--shared 25] [--max-chars 10000]
        The defaults give the committed sheets.
        PACK_DIR holds ind-hi-sangraha-s.parquet, ind-kn-sangraha-s.parquet, ind-ta-sangraha-s.parquet and
        ind-te-sangraha-s.parquet. Document text is never printed or written.
Exit codes: 0 done, 2 could not run (a pack is missing, has duplicate doc_ids, or has too few documents).
"""
import argparse
import csv
import hashlib
import sys
from pathlib import Path

import pyarrow.parquet as pq

LANGS = ("hi", "kn", "ta", "te")
COLUMNS = ["doc_id", "shared", "score", "note"]


def rank_key(seed, doc_id):
    return hashlib.sha256(f"{seed}:{doc_id}".encode("utf-8")).hexdigest()


def pick(docs, seed, n, shared, max_chars=None):
    """[(doc_id, is_shared)] for N documents of {doc_id: text}, in rank order; the first S are shared."""
    eligible = [d for d, text in docs.items() if text and text.strip() and (max_chars is None or len(text) <= max_chars)]
    if len(eligible) < n:
        raise ValueError(f"only {len(eligible)} eligible documents, {n} needed")
    chosen = sorted(eligible, key=lambda d: rank_key(seed, d))[:n]
    return [(d, k < shared) for k, d in enumerate(chosen)]


def read_pack(path):
    """{doc_id: text} from one pack; refuses duplicate doc_ids."""
    table = pq.read_table(path, columns=["doc_id", "text"])
    ids, texts = table.column("doc_id").to_pylist(), table.column("text").to_pylist()
    if len(set(ids)) != len(ids):
        raise ValueError(f"{path.name}: duplicate doc_ids")
    return dict(zip(ids, texts))


def write_sheet(path, picked):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(COLUMNS)
        for doc_id, is_shared in picked:
            w.writerow([doc_id, "yes" if is_shared else "no", "", ""])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pack_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "review_pack")
    ap.add_argument("--seed", default="212")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--shared", type=int, default=25)
    ap.add_argument("--max-chars", type=int, default=10000, help="leave out documents longer than this (default: 10000)")
    a = ap.parse_args(argv)
    if not 0 <= a.shared <= a.n:
        print(f"--shared {a.shared} must be between 0 and --n {a.n}", file=sys.stderr)
        return 2
    results = []
    for lang in LANGS:
        path = a.pack_dir / f"ind-{lang}-sangraha-s.parquet"
        try:
            docs = read_pack(path)
            picked = pick(docs, a.seed, a.n, a.shared, a.max_chars)
        except (OSError, ValueError) as e:
            print(f"{lang}: {e}", file=sys.stderr)
            return 2
        sha = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        results.append((lang, picked, len(docs), sha))
    for lang, picked, _, _ in results:
        write_sheet(a.out / f"{lang}.csv", picked)
    print(f"seed {a.seed}: {a.n} documents per language, {a.shared} shared -> {a.out}")
    print("| Language | Pack rows | Picked | Shared | Pack sha256 |\n|---|---|---|---|---|")
    for lang, picked, rows, sha in results:
        print(f"| {lang} | {rows} | {len(picked)} | {sum(s for _, s in picked)} | {sha} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
