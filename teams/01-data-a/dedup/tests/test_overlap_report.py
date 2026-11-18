"""Tests for overlap_report.py's row maps (RowRuns, read_docs) on small made-up overlap_docs.parquet files.

Run: python3 -B -m pytest teams/01-data-a/dedup/tests/test_overlap_report.py -q -p no:cacheprovider
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import overlap_report  # noqa: E402
from overlap_report import RowRuns, read_docs, write_matrix  # noqa: E402

# Parts in the order overlap.py reads them: (split, pack, documents). en-a appears in two runs; en-c is empty.
PARTS = [("train", "en-a", 4), ("train", "en-c", 0), ("train", "en-b", 3), ("heldout", "en-a", 1), ("heldout", "en-b", 1)]
PAIRS = [(0, 1), (2, 5), (3, 7), (4, 8)]


def per_document(parts, field):
    """The reference: one dict entry per document, built with a loop (as the old code did)."""
    rows = [(split, pack) for split, pack, n in parts for _ in range(n)]
    return {i: (pack if field == "pack" else split) for i, (split, pack) in enumerate(rows)}


def write_docs(path, parts, row_group_size=2):
    packs, splits = per_document(parts, "pack"), per_document(parts, "split")
    pq.write_table(pa.table({"row": list(packs), "pack": list(packs.values()), "split": list(splits.values())}),
                   path, row_group_size=row_group_size)


def test_row_runs_equal_a_per_document_map(tmp_path):
    reference = per_document(PARTS, "pack")
    starts = [sum(n for _, _, n in PARTS[:i]) for i in range(len(PARTS))]
    rows = RowRuns(starts, [p for _, p, _ in PARTS], len(reference))
    assert len(rows) == len(reference) and list(rows) == list(reference)
    assert [rows[r] for r in rows] == list(reference.values()) == list(rows.values())
    assert -1 not in rows and len(reference) not in rows and rows.get(len(reference)) is None
    write_matrix(tmp_path / "runs", rows, PAIRS)
    write_matrix(tmp_path / "dict", reference, PAIRS)
    for name in ("overlap_matrix.csv", "overlap_matrix_counts.csv"):
        assert (tmp_path / "runs" / name).read_bytes() == (tmp_path / "dict" / name).read_bytes()


def test_read_docs_equals_a_per_document_dict(tmp_path):
    """Several row groups, and a pack in two runs: each map holds one entry per run and agrees on every row."""
    path = tmp_path / "overlap_docs.parquet"
    write_docs(path, PARTS)
    packs, splits = read_docs(path, ["pack", "split"])
    assert dict(packs) == per_document(PARTS, "pack") and dict(splits) == per_document(PARTS, "split")
    assert packs.labels == ["en-a", "en-b", "en-a", "en-b"] and splits.labels == ["train", "heldout"]
    write_matrix(tmp_path / "runs", packs, PAIRS)
    write_matrix(tmp_path / "dict", per_document(PARTS, "pack"), PAIRS)
    for name in ("overlap_matrix.csv", "overlap_matrix_counts.csv"):
        assert (tmp_path / "runs" / name).read_bytes() == (tmp_path / "dict" / name).read_bytes()


@pytest.mark.parametrize("rows", [[1, 0, 2], [0, 0, 1], [0, 1, 3]])
def test_read_docs_refuses_rows_that_are_not_0_to_n_minus_1(tmp_path, rows):
    path = tmp_path / "overlap_docs.parquet"
    pq.write_table(pa.table({"row": rows, "pack": ["en-a"] * 3}), path)
    assert read_docs(path, ["pack"]) is None


def test_read_docs_refuses_a_missing_pack(tmp_path):
    path = tmp_path / "overlap_docs.parquet"
    pq.write_table(pa.table({"row": [0, 1], "pack": ["en-a", None]}), path)
    assert read_docs(path, ["pack"]) is None


def test_read_docs_of_no_documents(tmp_path):
    path = tmp_path / "overlap_docs.parquet"
    pq.write_table(pa.table({"row": pa.array([], pa.int64()), "pack": pa.array([], pa.string())}), path)
    (packs,) = read_docs(path, ["pack"])
    assert len(packs) == 0 and list(packs.values()) == []


def make_results(root, rows=None):
    """A returned overlap run with overlap_docs.parquet, overlap_matches.csv and a summary recording their SHA-256."""
    res = root / "res"
    res.mkdir()
    write_docs(res / "overlap_docs.parquet", PARTS)
    if rows is not None:
        t = pq.read_table(res / "overlap_docs.parquet")
        pq.write_table(t.set_column(0, "row", pa.array(rows)), res / "overlap_docs.parquet")
    with (res / "overlap_matches.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["row_a", "row_b", "rule"])
        w.writerows((a, b, "H2") for a, b in PAIRS)
    outputs = {n: {"sha256": hashlib.sha256((res / n).read_bytes()).hexdigest()}
               for n in ("overlap_docs.parquet", "overlap_matches.csv")}
    summary = {"status": "complete", "documents_all": len(per_document(PARTS, "pack")), "outputs": outputs}
    (res / "overlap_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return res


def test_main_rebuilds_the_matrix_from_the_runs(tmp_path, monkeypatch):
    res = make_results(tmp_path)
    monkeypatch.setattr(overlap_report, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["overlap_report.py", "--results", str(res)])
    overlap_report.main()
    write_matrix(tmp_path / "dict", per_document(PARTS, "pack"), PAIRS)
    for name in ("overlap_matrix.csv", "overlap_matrix_counts.csv"):
        assert (tmp_path / "out/overlap_returned" / name).read_bytes() == (tmp_path / "dict" / name).read_bytes()


def test_main_refuses_rows_out_of_order(tmp_path, monkeypatch):
    n = len(per_document(PARTS, "pack"))
    res = make_results(tmp_path, rows=[1, 0, *range(2, n)])
    monkeypatch.setattr(overlap_report, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["overlap_report.py", "--results", str(res)])
    with pytest.raises(SystemExit):
        overlap_report.main()
    assert not (tmp_path / "out/overlap_returned").exists()
