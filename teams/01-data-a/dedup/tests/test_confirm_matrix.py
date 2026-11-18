"""Tests for confirm_matrix.py on small made-up overlap runs (no real data).

Run: python3 -B -m pytest teams/01-data-a/dedup/tests/test_confirm_matrix.py -q -p no:cacheprovider
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import confirm_matrix  # noqa: E402
from overlap_report import write_matrix  # noqa: E402

HEADER = ["row_a", "row_b", "rule", "stage", "pack_a", "pack_b", "word_jaccard", "code_jaccard"]
# Parts in the order overlap.py reads them: (split, pack, documents). Rows 0-3 en-a, 4-6 en-b, 7 en-a held-out, 8 en-b.
PARTS = [("train", "en-a", 4), ("train", "en-b", 3), ("heldout", "en-a", 1), ("heldout", "en-b", 1)]
# Within en-a (0~1), cross-pack H1 (2~5), and two train ~ held-out pairs inside a pack (3~7 in en-a, 4~8 in en-b).
MATCHES = [(0, 1, "H2", 0.9), (2, 5, "H1", 1.0), (3, 7, "H2", 0.85), (4, 8, "H2", 0.82)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_packs(parts):
    return [pack for _, pack, n in parts for _ in range(n)]


def make_run(root, parts=PARTS, matches=MATCHES, empty=0, list_parts=None, docs=False):
    """A returned overlap run in root/res. list_parts: the part order written to the summary (default: parts)."""
    res = root / "res"
    res.mkdir(parents=True, exist_ok=True)
    packs = row_packs(parts)
    with (res / "overlap_matches.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for a, b, rule, score in matches:
            stage = "within_pack" if packs[a] == packs[b] else "cross_pack"
            w.writerow([a, b, rule, stage, packs[a], packs[b], score, ""])
    write_matrix(res, dict(enumerate(packs)), [(a, b) for a, b, *_ in matches])
    documents = {}
    for split, pack, n in parts:
        d = documents.setdefault(pack, {"train": 0, "heldout": 0, "all": 0})
        d[split] += n
        d["all"] += n
    names = ["overlap_matches.csv", "overlap_matrix.csv", "overlap_matrix_counts.csv"]
    if docs:
        pa = pytest.importorskip("pyarrow")
        import pyarrow.parquet as pq
        splits = [split for split, _, n in parts for _ in range(n)]
        pq.write_table(pa.table({"row": list(range(len(packs))), "pack": packs, "split": splits}),
                       res / "overlap_docs.parquet")
        names.append("overlap_docs.parquet")
    summary = {
        "status": "complete",
        "config": {"expected_packs": sorted(documents)},
        "documents": documents,
        "documents_all": len(packs),
        "empty_documents": empty,
        "inputs": {"parts": [{"part": f"{s}/{p}/part-00000.parquet", "documents": n} for s, p, n in (list_parts or parts)]},
        "qualifying_pairs_by_rule": {r: sum(1 for m in matches if m[2] == r) for r in sorted({m[2] for m in matches})},
        "outputs": {n: {"bytes": (res / n).stat().st_size, "sha256": sha(res / n)} for n in names},
    }
    (res / "overlap_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return res


def refresh_hash(res, name):
    """Record a file's current SHA-256 and size in the summary, as if the run had written it that way."""
    s = json.loads((res / "overlap_summary.json").read_text(encoding="utf-8"))
    s["outputs"][name] = {"bytes": (res / name).stat().st_size, "sha256": sha(res / name)}
    (res / "overlap_summary.json").write_text(json.dumps(s), encoding="utf-8")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(confirm_matrix, "REPO", tmp_path)
    return tmp_path


def run(repo, res, *extra):
    code = confirm_matrix.main(["--results", str(res), *extra])
    report = json.loads((repo / "out/matrix_confirmation/confirmation.json").read_text(encoding="utf-8"))
    return code, report, {c["check"] for c in report["checks"] if not c["ok"]}


def test_matching_run_is_confirmed(repo):
    res = make_run(repo)
    code, report, failed = run(repo, res)
    assert code == 0 and not failed and report["all_checks_passed"]
    for name in ("overlap_matrix.csv", "overlap_matrix_counts.csv"):
        assert (repo / "out/matrix_confirmation/rebuilt" / name).read_bytes() == (res / name).read_bytes()
    m = report["matrix"]
    assert m["documents_with_any_match"] == 8 and m["documents_with_a_cross_pack_match"] == 2
    assert m["train_heldout_pairs"] == 2 and m["nonzero_off_diagonal"] == 2


def test_changed_matrix_is_not_byte_identical(repo):
    res = make_run(repo)
    path = res / "overlap_matrix.csv"                   # en-b -> en-b is 2 of 4 documents: 0.5000000000
    path.write_bytes(path.read_bytes().replace(b"0.5000000000", b"0.5000000001", 1))
    refresh_hash(res, "overlap_matrix.csv")          # the summary agrees, but the matrix no longer follows the matches
    code, _, failed = run(repo, res)
    assert code == 1
    assert failed == {"rebuilt overlap_matrix.csv is byte-identical to the returned file",
                      "every share equals matched / total (10 decimals)"}


def test_file_that_differs_from_the_summary_fails(repo):
    res = make_run(repo)
    with (res / "overlap_matches.csv").open("a", encoding="utf-8") as f:
        f.write("0,1,H2,within_pack,en-a,en-a,0.9,\n")
    code, _, failed = run(repo, res)
    assert code == 1 and "overlap_matches.csv: SHA-256 and size equal the summary" in failed


def test_wrong_part_order_is_caught_by_the_matches(repo):
    # Same parts, listed in another order: the per-pack counts still agree, but rows land in the wrong packs.
    swapped = [PARTS[1], PARTS[0], PARTS[2], PARTS[3]]
    res = make_run(repo, list_parts=swapped)
    code, _, failed = run(repo, res)
    assert code == 1
    assert "every matched row is in the pack that overlap_matches.csv names" in failed
    assert "per-pack train / held-out counts from the parts equal the summary (pack_id based)" not in failed


def test_part_counts_that_disagree_with_the_summary_fail(repo):
    res = make_run(repo, list_parts=[("train", "en-a", 5), ("train", "en-b", 2), PARTS[2], PARTS[3]])
    code, _, failed = run(repo, res)
    assert code == 1 and "per-pack train / held-out counts from the parts equal the summary (pack_id based)" in failed


def test_empty_document_group_is_reported_and_removed_for_review(repo):
    # Rows 0, 1 (en-a) and 4 (en-b) are empty: one complete H1 group of 3, plus one real H2 pair.
    matches = [(0, 1, "H1", 1.0), (0, 4, "H1", 1.0), (1, 4, "H1", 1.0), (2, 3, "H2", 0.9)]
    res = make_run(repo, matches=matches, empty=3)
    code, report, failed = run(repo, res)
    assert code == 0 and not failed
    e = report["empty_document_group"]
    assert [r["row"] for r in e["rows"]] == [0, 1, 4]
    assert e["pairs_inside_group"] == 3 and e["cross_pack_pairs_inside_group"] == 2
    changed = {(c["from"], c["to"]): (c["before"], c["after"]) for c in e["changed_cells"]}
    assert changed == {("en-a", "en-a"): (4, 2), ("en-a", "en-b"): (2, 0), ("en-b", "en-a"): (1, 0)}
    assert (repo / "out/matrix_confirmation/without_empty_documents/overlap_matrix_counts.csv").is_file()


def test_empty_documents_without_one_group_fail(repo):
    res = make_run(repo, empty=3)                       # 3 empty documents reported, but no H1 group of 3
    code, _, failed = run(repo, res)
    assert code == 1 and "the empty documents form exactly one H1 group" in failed


def test_docs_parquet_route(repo):
    res = make_run(repo, docs=True)
    code, report, failed = run(repo, res, "--docs", str(res / "overlap_docs.parquet"))
    assert code == 0 and not failed and report["inputs"]["row_map"] == "overlap_docs.parquet"
    assert "overlap_docs.parquet SHA-256 equals the summary" in {c["check"] for c in report["checks"]}


def test_docs_parquet_with_another_hash_fails(repo):
    res = make_run(repo, docs=True)
    s = json.loads((res / "overlap_summary.json").read_text(encoding="utf-8"))
    s["outputs"]["overlap_docs.parquet"]["sha256"] = "0" * 64
    (res / "overlap_summary.json").write_text(json.dumps(s), encoding="utf-8")
    code, _, failed = run(repo, res, "--docs", str(res / "overlap_docs.parquet"))
    assert code == 1 and "overlap_docs.parquet SHA-256 equals the summary" in failed


def test_docs_parquet_with_rows_out_of_order_returns_2(repo):
    res = make_run(repo, docs=True)
    import pyarrow as pa
    import pyarrow.parquet as pq
    path = res / "overlap_docs.parquet"
    t = pq.read_table(path)
    pq.write_table(t.set_column(0, "row", pa.array([1, 0, *range(2, t.num_rows)])), path)
    refresh_hash(res, "overlap_docs.parquet")
    assert confirm_matrix.main(["--results", str(res), "--docs", str(path)]) == 2


def test_missing_input_returns_2(repo):
    res = make_run(repo)
    (res / "overlap_matrix_counts.csv").unlink()
    assert confirm_matrix.main(["--results", str(res)]) == 2


def test_out_must_be_inside_out(repo):
    res = make_run(repo)
    with pytest.raises(SystemExit) as e:
        confirm_matrix.main(["--results", str(res), "--out", "elsewhere"])
    assert e.value.code == 2
