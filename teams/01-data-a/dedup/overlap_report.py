"""Rebuild source overlap shares from returned TSAI artifacts, without reading document text.

python teams/01-data-a/dedup/overlap_report.py --results teams/01-data-a/jobs/results/2026-11-04-overlap

Writes only to out/. The input must contain overlap_docs.parquet and overlap_matches.csv from overlap.py.
"""
import argparse
import bisect
from collections import Counter, defaultdict
from collections.abc import Mapping
import csv
import hashlib
from itertools import chain, repeat
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]


def write_matrix(out, documents, pairs):
    """Count distinct source document rows, once per target pack, with no self-matches.

    documents maps run-local integer row IDs to pack IDs. pairs yields qualifying (row_a, row_b).
    A repeated doc_id is deliberately irrelevant: rows denote distinct input occurrences.
    """
    totals = Counter(documents.values())
    hits = defaultdict(set)
    for a, b in pairs:
        if a not in documents or b not in documents:
            raise ValueError(f"pair references unknown document rows: {a}, {b}")
        if a == b:
            continue
        pa, pb = documents[a], documents[b]
        hits[pa, pb].add(a)
        hits[pb, pa].add(b)
    packs = sorted(totals)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "overlap_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", *packs])
        for a in packs:
            writer.writerow([a, *(f"{len(hits[a, b]) / totals[a]:.10f}" for b in packs)])
    with (out / "overlap_matrix_counts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_a", "source_b", "matched_documents", "total_documents"])
        for a in packs:
            for b in packs:
                writer.writerow([a, b, len(hits[a, b]), totals[a]])


class RowRuns(Mapping):
    """Row -> value (pack or split) for rows 0..N-1, kept as one entry per run of rows with the same value."""

    def __init__(self, starts, labels, total):
        self.starts, self.labels, self.total = starts, labels, total

    def __getitem__(self, row):
        if not (isinstance(row, int) and 0 <= row < self.total):
            raise KeyError(row)
        return self.labels[bisect.bisect_right(self.starts, row) - 1]

    def __iter__(self):
        return iter(range(self.total))

    def __len__(self):
        return self.total

    def values(self):
        """Every row's value in row order, repeated per run in C (write_matrix counts them per pack)."""
        sizes = [b - a for a, b in zip(self.starts, self.starts[1:] + [self.total])]
        return chain.from_iterable(map(repeat, self.labels, sizes))


def read_docs(path, columns):
    """One RowRuns per column of overlap_docs.parquet, with the runs found by NumPy.

    None unless the rows are 0..N-1 in order (as overlap.py writes them) and every row has a value in each column.
    """
    import numpy as np
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    t = pq.read_table(path, columns=["row", *columns])
    n = t.num_rows
    if not np.array_equal(t["row"].to_numpy(), np.arange(n)) or any(t[c].null_count for c in columns):
        return None
    maps = []
    for name in columns:
        encoded = pc.dictionary_encode(t[name].combine_chunks())
        codes = encoded.indices.to_numpy(zero_copy_only=False)
        starts = np.flatnonzero(np.r_[True, codes[1:] != codes[:-1]]) if n else np.zeros(0, dtype=np.int64)
        labels = encoded.dictionary.to_pylist()
        maps.append(RowRuns(starts.tolist(), [labels[c] for c in codes[starts]], n))
    return maps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--out", default="out/overlap_returned", type=Path)
    args = parser.parse_args()
    out = (REPO / args.out).resolve()
    if not out.is_relative_to((REPO / "out").resolve()):
        parser.error("out must be inside out/ in the repository root")
    summary = json.loads((args.results / "overlap_summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "complete":
        parser.error("returned overlap job did not complete successfully")
    for name in ("overlap_docs.parquet", "overlap_matches.csv"):
        expected = summary["outputs"][name]["sha256"]
        digest = hashlib.sha256()
        with (args.results / name).open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            parser.error(f"returned artifact checksum mismatch: {name}")
    maps = read_docs(args.results / "overlap_docs.parquet", ["pack"])
    if maps is None or len(maps[0]) != summary["documents_all"]:
        parser.error("overlap_docs.parquet needs rows 0..N-1 in order, a pack on every row and documents_all rows")
    documents = maps[0]
    with (args.results / "overlap_matches.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not {"row_a", "row_b", "rule"} <= set(reader.fieldnames or []):
            parser.error("overlap_matches.csv needs row_a, row_b and rule columns")
        write_matrix(out, documents, ((int(p["row_a"]), int(p["row_b"]))
                                     for p in reader))
    print(f"Wrote overlap_matrix.csv and overlap_matrix_counts.csv to {out}")


if __name__ == "__main__":
    main()
