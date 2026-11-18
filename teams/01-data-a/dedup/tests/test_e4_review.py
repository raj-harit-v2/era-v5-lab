"""Unit tests for e4_review.py, which rebuilds E4's rejected sangraha-s pairs from the raw text for a human reader.

overlap.py runs in-process on made-up cleaned parts, as in test_overlap.py, to give TSAI-like outputs; e4_review.py then
runs on those outputs and on made-up raw parts, one of which differs from its cleaned version. Every text here is made
up; none comes from a pack. Nothing is read from or written to the real inputs/ or out/.

  python3 -B -m pytest dedup/tests/test_e4_review.py
"""
import csv
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")
pytest.importorskip("pygments")
pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import e4_review as e4  # noqa: E402
from test_overlap import make_config, make_sample, run  # noqa: E402

W = [f"w{i}" for i in range(80)]
K1 = " ".join(W[:30])                 # 30 words: 26 5-grams
K2 = " ".join(W[:29] + ["x"])         # last word changed: shares 25 of 27 5-grams with K1, but under 50 words
K2_RAW = K2 + "\nz1 z2"               # its raw text, before cleaning removed the last line: 25 of 29 with K1
K3 = " ".join(W[10:70])               # 60 words
K4 = " ".join(W[10:69] + ["y"])       # shares 55 of 57 5-grams with K3, and both have 50+ words: qualifies
K5 = "an unrelated sentence about something else entirely"
T1 = " ".join(f"t{i}" for i in range(25))   # 25 words: 21 5-grams
T2 = T1 + " t25"                            # one word added: shares 21 of 22, under 50 words

CLEANED = {"train/ind-kn-sangraha-s/part-00000.parquet": [("k1", K1), ("k3", K3), ("k4", K4), ("k5", K5)],
           "heldout/ind-kn-sangraha-s/part-00000.parquet": [("k2", K2)],
           "train/ind-ta-sangraha-s/part-00000.parquet": [("t1", T1), ("t2", T2)]}
RAW = {"ind-kn-sangraha-s/Part_1/part-00000.parquet": [("k1", K1), ("k3", K3), ("k4", K4), ("k5", K5)],
       "ind-kn-sangraha-s/Heldout/part-00000.parquet": [("k2", K2_RAW)],
       "ind-ta-sangraha-s/Part_1/part-00000.parquet": [("t1", T1), ("t2", T2)]}


@pytest.fixture
def e4_run(tmp_path, monkeypatch):
    """overlap.py on CLEANED (as TSAI's outputs, in out/t), then e4_review.py on those and on RAW."""
    run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, CLEANED)))
    for name, docs in RAW.items():
        path = tmp_path / "inputs" / "raw" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist([{"doc_id": d, "text": t} for d, t in docs]), path)
    monkeypatch.setattr(e4, "REPO", tmp_path)
    e4.main(["--tsai", "out/t", "--raw", "inputs/raw", "--out", "out/e4",
             "--packs", "ind-kn-sangraha-s", "ind-ta-sangraha-s"])
    out = tmp_path / "out" / "e4"
    with open(out / "e4_pairs.csv", newline="", encoding="utf-8") as f:
        pairs = {r["pack"]: r for r in csv.DictReader(f)}
    return out, json.loads((out / "e4_summary.json").read_text(encoding="utf-8")), pairs


def test_finds_the_rejected_pairs_and_checks_them_against_the_raw_text(e4_run):
    _, summary, pairs = e4_run
    kn, ta = summary["packs"]["ind-kn-sangraha-s"], summary["packs"]["ind-ta-sangraha-s"]
    assert (kn["pairs_at_or_above_0.80"], kn["qualify"], kn["rejected"]) == (2, 1, 1)
    assert (kn["rejected_by_50_word_minimum"], kn["rejected_other"]) == (1, 0)
    assert (ta["pairs_at_or_above_0.80"], ta["qualify"], ta["rejected"]) == (1, 0, 1)
    assert kn["documents_tsai"] == {"heldout": 1, "train": 4} == kn["documents_raw"]
    # k2's raw text still has the line cleaning removed, so it does not give TSAI's counts or score; the rest do.
    assert (kn["tsai_documents_found_in_raw"], kn["tsai_documents_with_tsai_counts_from_raw"]) == (5, 4)
    assert kn["rejected_pairs_with_tsai_score_from_raw"] == 0
    assert (ta["tsai_documents_with_tsai_counts_from_raw"], ta["rejected_pairs_with_tsai_score_from_raw"]) == (2, 1)
    k, t = pairs["ind-kn-sangraha-s"], pairs["ind-ta-sangraha-s"]
    assert (k["doc_id_a"], k["split_a"], k["doc_id_b"], k["split_b"]) == ("k1", "train", "k2", "heldout")
    assert float(k["tsai_jaccard"]) == pytest.approx(25 / 27, abs=1e-6)
    assert float(k["raw_jaccard"]) == pytest.approx(25 / 29, abs=1e-6)
    assert (k["tsai_score_from_raw"], k["tsai_counts_from_raw_a"], k["tsai_counts_from_raw_b"]) == ("False", "True", "False")
    assert (t["tsai_score_from_raw"], float(t["raw_jaccard"])) == ("True", pytest.approx(21 / 22, abs=1e-6))
    assert (t["differing_words_a"], t["differing_words_b"]) == ("0", "1")
    assert (kn["documents_in_rejected_pairs"], kn["clusters"], kn["cluster_sizes"]) == (2, 1, {"2": 1})


def test_counts_the_pairs_a_lower_word_minimum_would_keep(e4_run):
    _, summary, _ = e4_run
    kn, ta = summary["packs"]["ind-kn-sangraha-s"], summary["packs"]["ind-ta-sangraha-s"]
    assert kn["rejected_pairs_by_shorter_document_words"]["30-39"] == 1   # both kn documents have 30 words
    assert kn["rejected_pairs_qualifying_with_minimum"] == {"40": 0, "30": 1, "20": 1, "10": 1}
    assert ta["rejected_pairs_qualifying_with_minimum"] == {"40": 0, "30": 0, "20": 1, "10": 1}
    ind = summary["ind_prose_pairs_rejected_by_length"]["all"]
    assert (ind["pairs"], ind["rejected_other"], ind["documents"]) == (2, 0, 4)
    assert ind["documents_in_qualifying_pairs"] == {"40": 0, "30": 2, "20": 4, "10": 4}


def test_review_sheet_is_blind(e4_run):
    out, _, pairs = e4_run
    sheet = out / "review" / "ind-kn-sangraha-s"
    page = (sheet / "reading.html").read_text(encoding="utf-8")
    k = pairs["ind-kn-sangraha-s"]
    # The texts are there, with the words found in only one of them marked ...
    assert "kn-01" in page and "w0 w1" in page and "<mark>x</mark>" in page and "<mark>z1</mark>" in page
    # ... but no score, no doc_id and no word count.
    for hidden in (k["tsai_jaccard"], k["raw_jaccard"], "0.92", "k1", "k2", "30 words"):
        assert hidden not in page
    with open(sheet / "labels.csv", newline="", encoding="utf-8-sig") as f:
        assert list(csv.reader(f)) == [["pair_id", "label", "note"], ["kn-01", "", ""]]


def test_find_text_uses_the_part_and_row_for_a_repeated_doc_id():
    index = {("train", "d"): [("part-00000.parquet", 0, "first"), ("part-00000.parquet", 3, "second")]}
    doc = {"split": "train", "doc_id": "d", "part": "ind-kn-sangraha-s/part-00000.parquet", "row_in_part": 3}
    assert e4.find_text(index, doc) == ("second", "found")
    assert e4.find_text(index, {**doc, "row_in_part": 1}) == ("first", "ambiguous")
    assert e4.find_text(index, {**doc, "doc_id": "e"}) == (None, "missing")


def test_refuses_an_output_folder_outside_out(tmp_path, monkeypatch):
    monkeypatch.setattr(e4, "REPO", tmp_path)
    with pytest.raises(SystemExit, match="inside out/"):
        e4.main(["--out", "elsewhere"])
