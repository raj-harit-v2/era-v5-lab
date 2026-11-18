"""Behavioral checks for source shares and domain-specific H1/H2 decisions."""
import csv
from pathlib import Path
import random
import sys

import pytest
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from overlap_report import write_matrix
from overlap_rules import NUMBERS, code_shingles, code_scores, gram_set
from test_overlap import make_config, make_sample, run


def matches(out):
    with (out / "overlap_matches.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def test_shares_are_directional_distinct_and_exclude_self_matches(tmp_path):
    # Three copies have the same doc_id in reality, but each is a distinct input row.
    write_matrix(tmp_path, {0: "a", 1: "a", 2: "a", 3: "b", 4: "b"},
                 [(0, 3), (1, 3), (0, 3), (0, 1), (3, 3)])
    with (tmp_path / "overlap_matrix.csv").open(newline="") as f:
        rows = {r["source"]: r for r in csv.DictReader(f)}
    assert float(rows["a"]["b"]) == pytest.approx(2 / 3)
    assert float(rows["b"]["a"]) == 0.5
    assert float(rows["a"]["a"]) == pytest.approx(2 / 3)
    assert float(rows["b"]["b"]) == 0
    with (tmp_path / "overlap_matrix_counts.csv").open(newline="") as f:
        assert next(csv.DictReader(f)) == {"source_a": "a", "source_b": "a", "matched_documents": "2", "total_documents": "3"}


def test_unknown_rows_cannot_inflate_matrix(tmp_path):
    with pytest.raises(ValueError, match="unknown document rows"):
        write_matrix(tmp_path, {0: "a"}, [(0, 1)])


PROSE = " ".join(f"word{i}" for i in range(100))
CODE = "\n".join(f"value_{i} = old_value + shared_name" for i in range(24))


def test_prose_length_guard_does_not_exclude_h1(tmp_path, monkeypatch):
    parts = {"train/en-a/a.parquet": [("a", " ".join(PROSE.split()[:20])),
                                      ("b", " ".join(PROSE.split()[:19]) + " changed"),
                                      ("c", " ".join(PROSE.split()[:20]).upper()),
                                      ("long", PROSE), ("edited", PROSE + " final")]}
    out, _, _ = run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, parts)))
    docs = pq.read_table(out / "overlap_docs.parquet").to_pylist()
    ids = {d["row"]: d["doc_id"] for d in docs}
    got = {(ids[int(p["row_a"])], ids[int(p["row_b"])]): p["rule"] for p in matches(out)}
    assert got == {("a", "c"): "H1", ("long", "edited"): "H2"}


def test_math_requires_identical_numbers_even_at_high_similarity(tmp_path, monkeypatch):
    base = " ".join(f"term{i}" for i in range(150))
    parts = {"train/math-finemath/a.parquet": [("a", base + " solve x = -2"),
                                               ("b", base + " solve x = 2"),
                                               ("c", base + " compute x = -2")]}
    out, pairs, _ = run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, parts)))
    assert all(float(p["jaccard"]) >= 0.90 for p in pairs)
    assert [(p["row_a"], p["row_b"], p["rule"]) for p in matches(out)] == [("0", "2", "H2")]


@pytest.mark.parametrize("pack, comment", [("code-python", "#"), ("code-cpp", "//"),
                                         ("code-go", "//"), ("code-java", "//"),
                                         ("code-js-ts", "//"), ("code-rust", "//")])
def test_code_comments_removed_and_strings_preserved(pack, comment):
    code = 'value = "https://host/path#fragment"\n'
    original, _ = code_shingles(code * 20, pack)
    header, lines = code_shingles(comment + " licence header\n" + (code + comment + " comment\n") * 20, pack)
    changed, _ = code_shingles(code.replace("fragment", "different") * 20, pack)
    assert original == header
    assert original != changed
    assert lines == 20


def test_code_detected_even_below_raw_word_floor(tmp_path, monkeypatch):
    # Long, unrelated comment headers destroy raw-word similarity but leave the same code.
    a = "# " + " ".join(f"leftword{i}" for i in range(1000)) + "\n" + CODE
    b = "# " + " ".join(f"rightword{i}" for i in range(1000)) + "\n" + CODE
    parts = {"train/code-python/a.parquet": [("a", a), ("b", b), ("short", "x = 1\ny = 2")]}
    out, pairs, _ = run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, parts)))
    assert not pairs
    assert [(p["row_a"], p["row_b"], p["code_jaccard"]) for p in matches(out)] == [("0", "1", "1.0")]


def test_code_minimum_cannot_be_inflated_by_comment_lines(tmp_path, monkeypatch):
    a = "# line\n" * 30 + "x = 1\ny = 2\nz = 3"
    b = "# other\n" * 30 + "x = 1\ny = 2\nz = 4"
    parts = {"train/code-python/a.parquet": [("a", a), ("b", b), ("exact", a)]}
    out, _, _ = run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, parts)))
    assert [p["rule"] for p in matches(out)] == ["H1"]


def test_mixed_domains_must_pass_both_rules(tmp_path, monkeypatch):
    # A code-looking prose document meets both the word and token thresholds and lengths.
    parts = {"train/code-python/a.parquet": [("code", CODE)],
             "train/en-a/a.parquet": [("both", CODE.replace("shared_name", "changed", 1)),
                                      ("one_line", CODE.replace("\n", " ").replace("shared_name", "other", 1))]}
    out, _, _ = run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, parts)))
    got = [p for p in matches(out) if p["stage"] == "cross_pack"]
    assert len(got) == 1 and got[0]["rule"] == "H2"
    assert float(got[0]["word_jaccard"]) >= 0.80
    assert float(got[0]["code_jaccard"]) >= 0.85


def test_mixed_math_prose_requires_prose_length(tmp_path, monkeypatch):
    parts = {"train/math-finemath/a.parquet": [("a", PROSE), ("short", "one two three four five six seven eight nine ten")],
             "train/en-a/a.parquet": [("b", PROSE + " added"), ("short", "one two three four five six seven eight nine ten more")]}
    out, _, _ = run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, parts)))
    got = matches(out)
    assert len(got) == 1 and got[0]["rule"] == "H2"


def test_inventory_mismatch_fails_before_scoring(tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="pack inventory mismatch: missing=\\['en-missing'\\]"):
        run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, {"train/en-a/p.parquet": [("a", PROSE), ("b", PROSE)]}),
                                               expected_packs=["en-a", "en-missing"]))


def test_selected_split_must_exist(tmp_path):
    (tmp_path / "train").mkdir()
    with pytest.raises(SystemExit, match="missing selected split folder"):
        __import__("overlap").find_parts(tmp_path, ["train", "heldout"])


def test_returned_artifacts_rebuild_identical_matrix(tmp_path, monkeypatch):
    out, _, _ = run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, {
        "train/en-a/a.parquet": [("same", PROSE), ("same", PROSE)],
        "heldout/en-b/a.parquet": [("same", PROSE)]})))
    import overlap_report
    monkeypatch.setattr(overlap_report, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["overlap_report.py", "--results", str(out)])
    overlap_report.main()
    for name in ("overlap_matrix.csv", "overlap_matrix_counts.csv"):
        assert (out / name).read_bytes() == (tmp_path / "out/overlap_returned" / name).read_bytes()


def test_preprocessor_directives_are_not_comments():
    a, _ = code_shingles("#include <stdio.h>\nint a = 1;", "code-cpp")
    b, _ = code_shingles("#include <stdlib.h>\nint a = 1;", "code-cpp")
    assert gram_set(a) != gram_set(b)


def test_code_sparse_scores_match_brute_force():
    rng = random.Random(83)
    code = {}
    for i in range(20):
        lines = CODE.splitlines()
        for _ in range(rng.randrange(4)):
            j = rng.randrange(len(lines))
            lines[j] = lines[j].replace("shared_name", f"edited_{i}")
        code[i] = code_shingles("\n".join(lines), "code-python")
    sets = {i: gram_set(v[0]) for i, v in code.items()}
    expected = {(a, b): len(sets[a] & sets[b]) / len(sets[a] | sets[b])
                for a in code for b in code if a < b}
    expected = {k: v for k, v in expected.items() if v >= 0.85}
    got = {(a, b): s for a, b, s in code_scores(code, block=3)}
    assert len(got) > 10
    assert got == pytest.approx(expected)


def test_corrupt_returned_artifact_is_rejected(tmp_path, monkeypatch):
    out, _, _ = run(monkeypatch, tmp_path, make_config(tmp_path, make_sample(tmp_path, {
        "train/en-a/a.parquet": [("a", PROSE), ("b", PROSE)]})))
    with (out / "overlap_matches.csv").open("a") as f:
        f.write("corrupt\n")
    import overlap_report
    monkeypatch.setattr(overlap_report, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["overlap_report.py", "--results", str(out)])
    with pytest.raises(SystemExit):
        overlap_report.main()
    assert not (tmp_path / "out/overlap_returned").exists()


@pytest.mark.parametrize("negative, positive", [("-.5", ".5"), ("−2", "2"), ("-1.2e-3", "1.2e-3")])
def test_number_guard_preserves_signs_and_decimal_exponents(negative, positive):
    assert NUMBERS.findall(negative) == [negative]
    assert NUMBERS.findall(negative) != NUMBERS.findall(positive)
