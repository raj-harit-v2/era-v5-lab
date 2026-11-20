"""Shared fixtures for the pipeline tests: tiny synthetic cleaned parts, laid out the way overlap.py reads them.

No real data: every document is made up here. The layout is <cleaned>/<split>/<pack>/part-NNNNN.parquet with the
cleaned-part columns (doc_id, text, url, lang_label, pack_id). One doc_id ("g0") appears in two parts of the same pack
and split on purpose: the real cleaned sample has 22,773 such doc_ids, so nothing may match on doc_id alone.
"""
import csv
import json
import sys
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq

PIPELINE = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True  # no __pycache__ in the pipeline folder
sys.path.insert(0, str(PIPELINE))

HEADER = ["pack_id", "split", "part", "row_in_part", "doc_id"]


def made_up_manifest(expected_parts, **change):
    """The text of a sample manifest that clean_manifest.validate accepts: {split: count} parts of one made-up pack, two
    rows each, a different sha256 each. change: top-level keys to replace (e.g. total_docs=1)."""
    shards = []
    for split, count in expected_parts.items():
        for i in range(count):
            shards.append({"path": f"{split}/code-go/part-{i:05d}.parquet", "split": split, "pack_id": "code-go", "rows": 2,
                           "text_bytes": 20, "bytes": 100, "sha256": f"{len(shards):064x}"})
    return json.dumps({"name": "made up", "total_docs": 2 * len(shards), "shards": shards, **change})


def doc(doc_id, pack, text=None, url="", lang="en"):
    return {"doc_id": doc_id, "text": text if text is not None else f"synthetic text of {doc_id}",
            "url": url, "lang_label": lang, "pack_id": pack}


PARTS = {
    ("train", "code-go/part-00000.parquet"): [doc(f"g{i}", "code-go", lang="code") for i in range(5)],
    ("train", "code-go/part-00001.parquet"): [doc(d, "code-go", lang="code") for d in ("g0", "g5", "g6")],
    ("train", "en-dclm/part-00000.parquet"): [doc(f"e{i}", "en-dclm") for i in range(3)],
    ("heldout", "code-go/part-00000.parquet"): [doc(f"h{i}", "code-go", lang="code") for i in range(2)],
}


@pytest.fixture
def cleaned(tmp_path):
    """A cleaned-parts folder with train/ and heldout/."""
    root = tmp_path / "cleaned"
    for (split, part), rows in PARTS.items():
        path = root / split / part
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows), path)
    return root


@pytest.fixture
def write_remove_list(tmp_path):
    """write_remove_list(rows, header=HEADER) -> path of a remove_list.csv as dedup.py writes it."""
    def write(rows, header=HEADER, name="remove_list.csv"):
        path = tmp_path / name
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        return path
    return write
