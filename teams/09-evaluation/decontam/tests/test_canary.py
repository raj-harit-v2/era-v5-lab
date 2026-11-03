"""Tests for the lab canary and canary_scan.py (G9, week 2 task 5).

    pytest teams/09-evaluation/decontam/tests -q

No network. The Parquet tests need pyarrow (skipped without it).
"""

import json
import pathlib

import pytest

import canary_scan
from decontam_check import DEFAULT_SET
from fpset import Fingerprints
from lab_canary import (LAB_CANARY, LAB_CANARY_ID, LAB_CANARY_LINE, MARKDOWN_LINE, find, load_canaries,
                        read_canary_file, stamp)
from test_decontam import CANARY as TOY_CANARY
from test_decontam import CLEAN, build_toy

# Named decorators: pr-guard reads a diff line that starts with a dotted decorator as an email address.
module_fixture = pytest.fixture(scope="module")
shipped = pytest.mark.skipif(not (DEFAULT_SET / "MANIFEST.json").exists(), reason="no shipped set")
G9 = pathlib.Path(__file__).resolve().parent.parent.parent  # teams/09-evaluation


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def make_set(folder, canaries_by_benchmark):
    """A minimal fingerprint set folder: MANIFEST.json and <benchmark>/canaries.txt."""
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {"benchmarks": {}}
    for bid, cs in canaries_by_benchmark.items():
        manifest["benchmarks"][bid] = {"canaries": len(cs)}
        if cs:
            (folder / bid).mkdir()
            (folder / bid / "canaries.txt").write_text("".join(c + "\n" for c in cs), encoding="utf-8")
    (folder / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def run(capsys, *argv):
    """Run canary_scan.main; return (exit code, stdout records, stderr)."""
    code = canary_scan.main([str(a) for a in argv])
    out, err = capsys.readouterr()
    return code, [json.loads(line) for line in out.splitlines() if line.strip()], err


# ---- the canary string ----

def test_lab_canary_is_plain_ascii_text():
    # Plain text, not a special token (TSAI ruling), and ASCII so JSON escaping cannot change it.
    assert LAB_CANARY.isascii() and LAB_CANARY_LINE.isascii()
    assert LAB_CANARY in LAB_CANARY_LINE and LAB_CANARY_LINE in MARKDOWN_LINE
    assert "<|" not in LAB_CANARY and " " not in LAB_CANARY
    assert json.dumps(LAB_CANARY_LINE, ensure_ascii=True) == '"' + LAB_CANARY_LINE + '"'


def test_the_repo_never_holds_the_whole_canary():
    # If the repo is crawled into training data, it must not carry the canary.
    files = [p for p in G9.rglob("*") if p.is_file() and p.suffix in {".py", ".md", ".json", ".toml", ".txt", ".ipynb"}
             and "runs" not in p.parts and "fingerprints" not in p.parts]
    assert files
    assert [p for p in files if LAB_CANARY in p.read_text(encoding="utf-8", errors="replace")] == []


def test_stamp_puts_the_canary_first_and_keeps_the_record():
    rec = {"id": "gsm8k/3", "question": "q", "canary": "old"}
    s = stamp(rec)
    assert list(s)[0] == "canary" and s["canary"] == LAB_CANARY_LINE
    assert {k: v for k, v in s.items() if k != "canary"} == {"id": "gsm8k/3", "question": "q"}
    assert rec["canary"] == "old"  # the input is not changed


def test_find_gives_every_occurrence_in_offset_order():
    text = "a " + LAB_CANARY + " b " + TOY_CANARY + " c " + LAB_CANARY
    hits = find(text, {LAB_CANARY: "lab", TOY_CANARY: "toy"})
    assert hits == [(2, LAB_CANARY), (text.index(TOY_CANARY), TOY_CANARY), (text.rindex(LAB_CANARY), LAB_CANARY)]
    assert all(text[o:o + len(c)] == c for o, c in hits)
    assert find(CLEAN[0], {LAB_CANARY: "lab"}) == []


def test_find_refuses_an_empty_canary():
    with pytest.raises(ValueError):
        find("abc", {"": "x"})


def test_read_canary_file_strips_and_skips_blank_lines(tmp_path):
    f = tmp_path / "canaries.txt"
    f.write_text(TOY_CANARY + "  \n\n   \n", encoding="utf-8")
    assert read_canary_file(f) == [TOY_CANARY]


def test_load_canaries_follows_the_manifest(tmp_path):
    s = make_set(tmp_path / "set", {"toy": [TOY_CANARY], "plain": []})
    (s / "stale").mkdir()  # a folder that is not in the MANIFEST is not read
    (s / "stale" / "canaries.txt").write_text("STALE-CANARY\n", encoding="utf-8")
    assert load_canaries(s) == {LAB_CANARY: LAB_CANARY_ID, TOY_CANARY: "toy"}
    assert load_canaries(None) == {LAB_CANARY: LAB_CANARY_ID}


def test_load_canaries_refuses_a_folder_that_is_not_a_set(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_canaries(tmp_path / "typo")
    with pytest.raises(FileNotFoundError):
        load_canaries(tmp_path)  # exists, but no MANIFEST.json


@shipped
def test_shipped_set_gives_the_gpqa_and_hle_canaries():
    sources = set(load_canaries(DEFAULT_SET).values())
    assert {LAB_CANARY_ID, "gpqa_diamond", "hle"} <= sources


# ---- canary_scan.py ----

def test_scan_prints_only_canary_doc_id_and_offset(tmp_path, capsys):
    secret = "SECRET BENCHMARK QUESTION TEXT"
    docs = write_jsonl(tmp_path / "docs.jsonl", [
        {"doc_id": "d0", "text": CLEAN[0]},
        {"doc_id": "d1", "text": secret + "\n" + LAB_CANARY_LINE + "\n" + secret},
    ])
    code, recs, err = run(capsys, docs, "--lab-only")
    assert code == 1
    assert recs == [{"canary": LAB_CANARY, "doc_id": "d1",
                     "offset": len(secret + "\n" + LAB_CANARY_LINE) - len(LAB_CANARY)}]
    assert all(set(r) == {"canary", "doc_id", "offset"} for r in recs)
    out_and_err = json.dumps(recs) + err
    assert secret not in out_and_err and "MUST NEVER" not in out_and_err  # no document text
    assert "docs 2 with_canary 1 hits 1" in err


def test_scan_reports_every_hit_in_a_document(tmp_path, capsys):
    text = LAB_CANARY + " middle " + LAB_CANARY + " end " + TOY_CANARY
    docs = write_jsonl(tmp_path / "docs.jsonl", [{"id": 7, "body": text}])
    s = make_set(tmp_path / "set", {"toy": [TOY_CANARY]})
    code, recs, err = run(capsys, docs, "--id-field", "id", "--text-field", "body", "--fingerprints", s)
    assert code == 1
    assert [(r["doc_id"], r["offset"], r["canary"]) for r in recs] == [
        ("7", 0, LAB_CANARY), ("7", text.index(" end") - len(LAB_CANARY), LAB_CANARY),
        ("7", text.index(TOY_CANARY), TOY_CANARY)]
    assert "hits 3" in err


def test_clean_documents_give_no_output_and_exit_0(tmp_path, capsys):
    docs = write_jsonl(tmp_path / "docs.jsonl", [{"doc_id": f"c{i}", "text": t} for i, t in enumerate(CLEAN)])
    code, recs, err = run(capsys, docs, "--lab-only")
    assert code == 0 and recs == []
    assert f"docs {len(CLEAN)} with_canary 0 hits 0" in err


def test_a_wrong_fingerprints_path_is_an_error_not_a_clean_scan(tmp_path, capsys):
    docs = write_jsonl(tmp_path / "docs.jsonl", [{"doc_id": "d", "text": TOY_CANARY}])
    with pytest.raises(SystemExit) as e:
        canary_scan.main([str(docs), "--fingerprints", str(tmp_path / "typo")])
    assert e.value.code == 2 and "--lab-only" in capsys.readouterr().err


def test_extra_canary_string(tmp_path, capsys):
    docs = write_jsonl(tmp_path / "docs.jsonl", [{"doc_id": "x", "text": "abc MY-MARKER def"}])
    code, recs, _ = run(capsys, docs, "--lab-only", "--canary", "MY-MARKER")
    assert code == 1 and recs == [{"canary": "MY-MARKER", "doc_id": "x", "offset": 4}]


def test_an_empty_extra_canary_is_refused(tmp_path, capsys):
    docs = write_jsonl(tmp_path / "docs.jsonl", [{"doc_id": "x", "text": "abc"}])
    with pytest.raises(SystemExit) as e:
        canary_scan.main([str(docs), "--lab-only", "--canary", " "])
    assert e.value.code == 2


def test_jsonl_lines_without_the_text_field_are_scanned_whole(tmp_path, capsys):
    # run_lm_eval.py --log-samples lines: {"canary", "task", "doc", ...}, no "text".
    samples = write_jsonl(tmp_path / "samples_5.jsonl", [
        stamp({"task": "gsm8k", "doc_id": 3, "doc": {"question": "q"}}),
        {"task": "gsm8k", "doc_id": 4, "doc": {"question": "clean"}},
    ])
    (tmp_path / "raw.jsonl").write_text("not json " + LAB_CANARY + "\n[1, 2]\n", encoding="utf-8")
    code, recs, err = run(capsys, samples, tmp_path / "raw.jsonl", "--lab-only")
    assert code == 1
    assert [(r["doc_id"], r["canary"]) for r in recs] == [("3", LAB_CANARY), (f"{tmp_path / 'raw.jsonl'}:0", LAB_CANARY)]
    assert "docs 4 with_canary 2 hits 2" in err


def test_parquet_input(tmp_path, capsys):
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq
    pq.write_table(pa.table({"doc_id": ["p0", "p1"], "text": [CLEAN[1], "x" + LAB_CANARY]}), tmp_path / "s.parquet")
    code, recs, _ = run(capsys, tmp_path / "s.parquet", "--lab-only")
    assert code == 1 and recs == [{"canary": LAB_CANARY, "doc_id": "p1", "offset": 1}]


def test_folder_input_finds_a_stamped_eval_item_file(tmp_path, capsys):
    # An item file as make_eval_mini_items.py writes it: pure ASCII JSON with the canary in the file and in each item.
    items = {"items": [stamp({"id": "milu_Hindi/4", "question": "भारत की राजधानी क्या है?", "answer": "A"})]}
    eval_dir = tmp_path / "eval"
    (eval_dir / "a").mkdir(parents=True)
    (eval_dir / "b").mkdir()
    (eval_dir / "a" / "items.json").write_text(json.dumps(stamp(items), ensure_ascii=True, indent=1), encoding="ascii")
    (eval_dir / "b" / "items.json").write_text(json.dumps(items, ensure_ascii=True), encoding="ascii")
    (eval_dir / "notes.md").write_text("# notes\n" + MARKDOWN_LINE + "\n", encoding="utf-8")
    (eval_dir / "clean.txt").write_text(CLEAN[0], encoding="utf-8")
    (eval_dir / "weights.bin").write_bytes(LAB_CANARY.encode())  # not a text suffix: not read
    code, recs, err = run(capsys, eval_dir, "--lab-only")
    assert code == 1
    # Files in a folder are named by their relative path, so the two items.json can be told apart.
    assert sorted(r["doc_id"] for r in recs) == ["a/items.json", "a/items.json", "b/items.json", "notes.md"]
    assert "docs 4 " in err


def test_an_unreadable_file_is_skipped_and_gives_exit_2(tmp_path, capsys):
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq
    d = tmp_path / "shards"
    d.mkdir()
    pq.write_table(pa.table({"doc_id": ["m"], "meta": ["no text column"]}), d / "a_meta.parquet")
    write_jsonl(d / "b_clean.jsonl", [{"doc_id": "c", "text": CLEAN[0]}])
    code, recs, err = run(capsys, d, "--lab-only")
    assert code == 2 and recs == []
    assert "skipped a_meta.parquet" in err and "docs 1 " in err and "files_skipped 1" in err
    # A leak still wins over a skipped file: exit 1.
    write_jsonl(d / "c_leak.jsonl", [{"doc_id": "l", "text": LAB_CANARY}])
    code, recs, err = run(capsys, d, "--lab-only")
    assert code == 1 and [r["doc_id"] for r in recs] == ["l"] and "files_skipped 1" in err


# ---- the full check (decontam_check.py) also flags the lab canary ----

@module_fixture
def toy_fp(tmp_path_factory):
    out, _ = build_toy(tmp_path_factory.mktemp("toy_canary"))
    return Fingerprints(out)


def test_fingerprints_flag_the_lab_canary(toy_fp):
    text = CLEAN[0] + "\n" + LAB_CANARY_LINE
    flagged, hits = toy_fp.check(text)
    assert flagged
    assert hits[0] == {"item": f"{LAB_CANARY_ID}:canary", "canary": LAB_CANARY, "offset": text.index(LAB_CANARY)}
    assert not toy_fp.check(CLEAN[0])[0]
    assert set(toy_fp.canaries.values()) == {LAB_CANARY_ID, "toy"}
