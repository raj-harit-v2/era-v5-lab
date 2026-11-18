r"""H1 exact duplicates across one pack's folders: SHA-256 of an H1 key built on normalize.match_key, compared all-to-all.

Reads every Parquet file in the Part_* and Heldout folders of one pack as one combined set (each file needs doc_id and
text columns), builds each document's H1 key, hashes its UTF-8 bytes with SHA-256 and compares every document with
every other one by that hash: two documents are duplicates exactly when their hashes are equal. Documents are never
changed, and no text is written out: IDs, hashes and counts only.

THE H1 KEY
==========
  1. normalize.match_key(text) from spec_v1/normalize.py (spec_v1/tools/ before #244), unchanged: HTML entities, control
     and invisible characters, NFC with its listed folds, casefold, spaces.
  2. Then the H1 normalisation of dedup_design_v1.md on top: NFKC, casefold, every run of whitespace to one space,
     ends stripped. NFKC is applied only here, never in normalize.py, so spec v1 and G9's fingerprints are unchanged.

HOW TO RUN IT
=============
Run from teams/01-data-a/. Python 3.9 or later with pyarrow (python3 -m pip install pyarrow).

    python3 -I dedup/h1_sha256.py --pack <packs folder>/en-dclm --out <output folder, outside the repo>

WHAT IT WRITES (in --out)
=========================
  docs.csv               one row per document: folder, file, row, doc_id, sha256, copies (documents with this hash)
  duplicate_groups.csv   one row per hash shared by 2+ documents: sha256, copies, folders, members (folder:doc_id)
  duplicate_pairs.csv    the all-to-all result: every pair of documents with the same hash; every other pair differs.
                         same_doc_id is True when the doc_ids match too. doc_id is a hash of the original text
                         (dedup_design_v1.md), so a pair with different doc_ids became equal only after normalising.
                         Not written if there are more than --max-pairs pairs (duplicate_groups.csv has them all).
  folder_matrix.csv      row folder x column folder: documents in the row folder that have a copy in the column
                         folder (the diagonal: a copy in the same folder)
  summary.json           the counts, the input files and normalize.NORMALIZE_ID
"""
import argparse, csv, hashlib, json, re, sys, time, unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

# normalize.py is spec_v1/normalize.py after #244 and spec_v1/tools/normalize.py before it; the file is the same
# (NORMALIZE_ID "g1-spec-v1"). Look in the new place first.
_SPEC = Path(__file__).resolve().parents[1] / "spec_v1"
sys.path.insert(0, str(_SPEC / "tools"))
sys.path.insert(0, str(_SPEC))
from normalize import NORMALIZE_ID, match_key  # noqa: E402


def h1_key(text):
    """normalize.match_key, then dedup_design_v1.md H1: NFKC, casefold, whitespace runs to one space."""
    return " ".join(unicodedata.normalize("NFKC", match_key(text)).casefold().split())


def pack_folders(pack):
    """Part_1, Part_2, ... in number order, then Heldout."""
    natural = lambda d: [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", d.name)]
    parts = sorted((d for d in pack.glob("Part_*") if d.is_dir()), key=natural)
    return parts + [d for d in sorted(pack.iterdir()) if d.is_dir() and d.name.lower() == "heldout"]


def read_file(path):
    """(row, doc_id, text) for every document of one Parquet file, which needs doc_id and text columns."""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    missing = {"doc_id", "text"} - set(pf.schema_arrow.names)
    if missing:
        sys.exit(f"ERROR: {path} has no {sorted(missing)} column (it has {pf.schema_arrow.names})")
    row = 0
    for batch in pf.iter_batches(batch_size=1000, columns=["doc_id", "text"]):
        for doc_id, text in zip(batch.column("doc_id").to_pylist(), batch.column("text").to_pylist()):
            yield row, doc_id, text
            row += 1


def read_docs(folder):
    """(file, row, doc_id, text) for every document of every Parquet file in the folder, in file then row order."""
    for f in sorted(folder.rglob("*.parquet")):
        for row, doc_id, text in read_file(f):
            yield f.relative_to(folder), row, doc_id, text


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", required=True, help="pack folder holding Part_* and Heldout, e.g. <packs>/en-dclm")
    ap.add_argument("--out", required=True, help="output folder; keep it outside the repo")
    ap.add_argument("--max-pairs", type=int, default=10_000_000, help="skip duplicate_pairs.csv above this many pairs")
    args = ap.parse_args()
    pack, out = Path(args.pack), Path(args.out)
    dirs = pack_folders(pack)
    if not dirs:
        sys.exit(f"ERROR: no Part_* or Heldout folder in {pack}")
    names = [d.name for d in dirs]
    out.mkdir(parents=True, exist_ok=True)

    # 1. Combine all folders and hash each document's normalised key.
    docs, by_hash, t0 = [], defaultdict(list), time.time()   # docs[i] = (folder, file, row, doc_id, sha256)
    for d in dirs:
        n = 0
        for file, row, doc_id, text in read_docs(d):
            h = hashlib.sha256(h1_key(text or "").encode("utf-8")).hexdigest()
            by_hash[h].append(len(docs))
            docs.append((d.name, str(file), row, doc_id, h))
            n += 1
        print(f"{d.name}: {n} documents hashed ({time.time() - t0:.0f}s)", flush=True)

    # 2. All-to-all: equal hashes are duplicates, so grouping by hash compares every pair at once.
    groups = {h: ix for h, ix in by_hash.items() if len(ix) > 1}
    has_copy_in = {a: Counter() for a in names}   # has_copy_in[a][b]: documents in a with a copy in b
    n_pairs = same_id_pairs = 0
    for ix in groups.values():
        n_pairs += len(ix) * (len(ix) - 1) // 2
        same_id_pairs += sum(c * (c - 1) // 2 for c in Counter(docs[i][3] for i in ix).values())
        per = Counter(docs[i][0] for i in ix)
        for a, ca in per.items():
            for b in per:
                if a != b or ca > 1:
                    has_copy_in[a][b] += ca

    write_csv(out / "docs.csv", ["folder", "file", "row", "doc_id", "sha256", "copies"],
              (d + (len(by_hash[d[4]]),) for d in docs))
    ref = lambda i: f"{docs[i][0]}:{docs[i][3]}"
    write_csv(out / "duplicate_groups.csv", ["sha256", "copies", "folders", "members"],
              ([h, len(ix), ";".join(sorted({docs[i][0] for i in ix}, key=names.index)), ";".join(map(ref, ix))]
               for h, ix in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))))
    pairs_file = out / "duplicate_pairs.csv"
    if n_pairs <= args.max_pairs:
        write_csv(pairs_file, ["sha256", "folder_a", "file_a", "row_a", "doc_id_a",
                               "folder_b", "file_b", "row_b", "doc_id_b", "same_doc_id"],
                  ([h, *docs[i][:4], *docs[j][:4], docs[i][3] == docs[j][3]]
                   for h, ix in groups.items() for i, j in combinations(ix, 2)))
    else:
        pairs_file.unlink(missing_ok=True)
        print(f"duplicate_pairs.csv not written: {n_pairs} pairs > --max-pairs {args.max_pairs}")
    write_csv(out / "folder_matrix.csv", ["documents in \\ with a copy in", *names],
              ([a, *(has_copy_in[a][b] for b in names)] for a in names))

    per_folder = Counter(d[0] for d in docs)
    in_groups = sum(len(ix) for ix in groups.values())
    summary = {
        "pack": str(pack.resolve()),
        "normalize_id": NORMALIZE_ID,
        "key": "sha256(utf-8 h1_key(text)): normalize.match_key, then NFKC, casefold, whitespace runs to one space",
        "files": {d.name: [str(f.relative_to(d)) for f in sorted(d.rglob("*.parquet"))] for d in dirs},
        "documents": {**{a: per_folder[a] for a in names}, "all": len(docs)},
        "pairs_compared": len(docs) * (len(docs) - 1) // 2,
        "unique_hashes": len(by_hash),
        "duplicate_groups": len(groups),
        "cross_folder_groups": sum(len({docs[i][0] for i in ix}) > 1 for ix in groups.values()),
        "documents_in_duplicate_groups": in_groups,
        "extra_copies": in_groups - len(groups),
        "duplicate_pairs": n_pairs,
        "duplicate_pairs_same_doc_id": same_id_pairs,
        "documents_with_a_copy_in": {a: {b: has_copy_in[a][b] for b in names} for a in names},
        "seconds": round(time.time() - t0, 1),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "files"}, indent=2))
    print(f"Wrote docs.csv, duplicate_groups.csv, {'duplicate_pairs.csv, ' if pairs_file.exists() else ''}"
          f"folder_matrix.csv and summary.json to {out}")


if __name__ == "__main__":
    sys.exit(main())
