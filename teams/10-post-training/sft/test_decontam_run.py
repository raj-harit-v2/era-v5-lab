"""Tests for decontam_run.py and decontam_report.py (G10).

    pytest teams/10-post-training/sft/test_decontam_run.py -q

They need Team 9's decontam folder (teams/09-evaluation/decontam, or G10_DECONTAM_TOOLS) and no network.
A toy fingerprint set is built from made-up items, so no real benchmark text is used anywhere.
"""

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import decontam_report as rep  # noqa: E402
import decontam_run as run  # noqa: E402

TOOLS = run.DEFAULT_TOOLS


def _tools_are_v2() -> bool:
    """Team 9's folder must be the fingerprints v2 version (fpset.DEFAULT_NORM); an older copy lacks it."""
    fpset = TOOLS / "fpset.py"
    return (TOOLS / "decontam_check.py").is_file() and fpset.is_file() and "DEFAULT_NORM" in fpset.read_text(encoding="utf-8")


pytestmark = pytest.mark.skipif(not _tools_are_v2(), reason="Team 9's decontam folder here is missing or older than "
                                "fingerprints v2 (no fpset.DEFAULT_NORM): set G10_DECONTAM_TOOLS to lab main c6b0ce0")

# Made-up items, as in Team 9's own tests.
TOY = [
    {"qid": "q0", "question": "A farmer has 23 lemon trees and each tree gives 41 lemons every week. "
                              "How many lemons does the farmer collect in 6 weeks?",
     "answer": "", "choices": [], "canary": "TOY DATA MUST NEVER BE TRAINED ON. canary GUID toy:ab12:0f8fad5b-d9cb-469f-a165-70867728950e"},
    {"qid": "q1", "question": "Which gas do the green leaves of most land plants take in from the "
                              "air to make sugar during the day?",
     "answer": "", "choices": [], "canary": ""},
]
CANARY = "toy:ab12:0f8fad5b-d9cb-469f-a165-70867728950e"
COPY = TOY[0]["question"]
CLEAN = ["The monsoon reached Kerala two days early this year, and farmers in the south began to plant rice.",
         "To install the package, open a terminal and run the install command. Then restart the editor.",
         "Count with me: 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20."]


# A named decorator: pr-guard takes a dotted decorator line of a diff for an email address.
module_fixture = pytest.fixture(scope="module")


@module_fixture
def toy_set(tmp_path_factory):
    sys.path.insert(0, str(TOOLS))
    try:
        import fpset
        import registry
    finally:
        sys.path.remove(str(TOOLS))
    tmp = tmp_path_factory.mktemp("toy")
    data = tmp / "toy.jsonl"
    data.write_text("".join(json.dumps(r) + "\n" for r in TOY), encoding="utf-8")
    reg_file = tmp / "benchmarks.toml"
    reg_file.write_text(f'''
[toy]
name = "Toy"
status = "active"
tags = ["english"]
licence = "test only"
source = "local"
files = [{{ path = "{data.as_posix()}" }}]
id = "{{qid}}"
dedupe = true
texts = ["{{question}}"]
canaries = ["{{canary|guid}}"]
''', encoding="utf-8")
    reg = registry.load(reg_file)
    out = tmp / "set"
    canaries = set()
    norm = fpset.DEFAULT_NORM
    fpset.write_benchmark(out, "toy", registry.items("toy", reg["toy"], tmp, canaries),
                          registry.run_lengths(reg["toy"]), {"name": "Toy", "tags": reg["toy"]["tags"]},
                          canaries=canaries, boilerplate=fpset.Boilerplate(norm=norm), norm=norm)
    fpset.write_index(out, {}, norm)
    return out


def write_rows(path, rows):
    path.write_text("".join(json.dumps({"id": i, "text": t}) + "\n" for i, t in rows), encoding="utf-8")
    return path


def go(tmp_path, toy_set, rows, name="toyset"):
    src = write_rows(tmp_path / f"{name}.jsonl", rows)
    return run.run_set(name, [src], tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None)


def test_flagged_row_is_removed_and_reconciled(tmp_path, toy_set):
    rows = [(f"s/{i}", t) for i, t in enumerate(CLEAN)] + [("s/9", "Solve this. " + COPY + " Show work.")]
    rec = go(tmp_path, toy_set, rows)
    assert rec["ok"]
    assert (rec["rows_in"], rec["rows_flagged"], rec["rows_removed"], rec["rows_kept"]) == (4, 1, 1, 3)
    assert list(rec["flagged"]) == ["s/9"]
    assert rec["flagged"]["s/9"]["benchmarks"] == ["toy"]
    assert all(rec["checks"].values()) and rec["recheck_on_clean"]["flagged"] == 0
    kept = [json.loads(line)["id"] for line in (tmp_path / "out" / "toyset.clean.jsonl").read_text().splitlines()]
    assert kept == ["s/0", "s/1", "s/2"]


def test_no_hit_keeps_everything(tmp_path, toy_set):
    rec = go(tmp_path, toy_set, [(f"s/{i}", t) for i, t in enumerate(CLEAN)])
    assert rec["ok"] and rec["rows_removed"] == 0 and rec["rows_kept"] == 3


def test_canary_is_a_leak_and_the_string_is_not_kept(tmp_path, toy_set):
    rows = [("s/0", CLEAN[0]), ("s/1", "notes " + CANARY + " end")]
    rec = go(tmp_path, toy_set, rows)
    assert not rec["ok"] and rec["rows_canary"] == 1 and rec["rows_kept"] == 1
    assert CANARY not in json.dumps(rec)  # only a short label of the canary is stored
    assert rec["canary"]["hits"][0]["doc_id"] == "s/1"


def test_duplicate_ids_fail_the_reconciliation(tmp_path, toy_set):
    rec = go(tmp_path, toy_set, [("s/0", CLEAN[0]), ("s/0", CLEAN[1])])
    assert not rec["ok"] and rec["checks"]["ids_unique"] is False and rec["duplicate_ids"] == 1


def test_record_holds_no_document_text(tmp_path, toy_set):
    rec = go(tmp_path, toy_set, [("s/0", "Solve this. " + COPY), ("s/1", CLEAN[0])])
    blob = json.dumps(rec)
    assert COPY[:40] not in blob and CLEAN[0][:30] not in blob


def test_wrong_set_sha256_is_refused(tmp_path, toy_set):
    src = write_rows(tmp_path / "x.jsonl", [("a", CLEAN[0])])
    with pytest.raises(run.RunError, match="not the expected"):
        run.run_set("x", [src], tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha="0" * 64)


def test_missing_id_field_is_an_error(tmp_path, toy_set):
    src = tmp_path / "bad.jsonl"
    src.write_text(json.dumps({"text": "a"}) + "\n", encoding="utf-8")
    with pytest.raises(run.RunError, match="no 'id' field"):
        run.run_set("bad", [src], tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None)


def test_parquet_input(tmp_path, toy_set):
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq
    ids, texts = ["p/0", "p/1", "p/2"], [CLEAN[0], "Quick: " + COPY, CLEAN[1]]
    src = tmp_path / "p.parquet"
    pq.write_table(pa.table({"id": ids, "text": texts}), src)
    rec = run.run_set("p", [src], tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None)
    assert rec["ok"] and rec["rows_kept"] == 2 and list(rec["flagged"]) == ["p/1"]
    assert pq.read_table(tmp_path / "out" / "p.clean.parquet").column("id").to_pylist() == ["p/0", "p/2"]


def test_relative_paths_work(tmp_path, toy_set, monkeypatch):
    write_rows(tmp_path / "rel.jsonl", [("r/0", CLEAN[0]), ("r/1", COPY)])
    monkeypatch.chdir(tmp_path)  # the tools run in their own folder, so paths must be made absolute
    rec = run.run_set("rel", ["rel.jsonl"], "out", TOOLS, fingerprints=str(toy_set), expect_sha=None)
    assert rec["ok"] and rec["rows_kept"] == 1 and (tmp_path / "out" / "rel.clean.jsonl").is_file()


def test_clean_jsonl_keeps_the_bytes_of_kept_rows(tmp_path, toy_set):
    src = tmp_path / "b.jsonl"
    keep = '{"text":"' + CLEAN[0] + '","id":"b/0","extra":[1, 2]}\r\n'  # odd spacing, key order and CRLF
    drop = json.dumps({"id": "b/1", "text": COPY}) + "\n"
    src.write_bytes((keep + drop).encode("utf-8"))
    rec = run.run_set("b", [src], tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None)
    assert rec["ok"] and (tmp_path / "out" / "b.clean.jsonl").read_bytes() == keep.encode("utf-8")


def test_input_is_never_overwritten(tmp_path, toy_set):
    out = tmp_path / "out"
    out.mkdir()
    src = write_rows(out / "same.clean.jsonl", [("a", CLEAN[0])])
    with pytest.raises(run.RunError, match="overwritten"):
        run.run_set("same", [src], out, TOOLS, fingerprints=str(toy_set), expect_sha=None)


def test_two_input_files_are_one_set(tmp_path, toy_set):
    a = write_rows(tmp_path / "a.jsonl", [("m/0", CLEAN[0]), ("m/1", COPY)])
    b = write_rows(tmp_path / "b.jsonl", [("m/2", CLEAN[1])])
    rec = run.run_set("multi", [a, b], tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None)
    assert rec["ok"] and (rec["rows_in"], rec["rows_kept"]) == (3, 2) and len(rec["clean"]) == 2


def test_record_names_the_tools_and_the_benchmarks(tmp_path, toy_set):
    rec = go(tmp_path, toy_set, [("s/0", CLEAN[0])])
    assert rec["benchmarks"] == ["toy"]
    assert set(rec["tools"]["files"]) >= {"decontam_check.py", "canary_scan.py", "fpset.py"}
    assert all(len(h) == 64 for h in rec["tools"]["files"].values())


def test_main_exit_codes(tmp_path, toy_set, capsys):
    good = write_rows(tmp_path / "good.jsonl", [("g/0", CLEAN[0])])
    leak = write_rows(tmp_path / "leak.jsonl", [("l/0", "x " + CANARY)])
    args = ["--out-dir", str(tmp_path / "out"), "--tools", str(TOOLS), "--fingerprints", str(toy_set),
            "--expect-sha", ""]
    assert run.main(["--set", "good", "--input", str(good), *args]) == 0
    assert run.main(["--set", "leak", "--input", str(leak), *args]) == 1
    assert run.main(["--set", "none", "--input", str(tmp_path / "missing.jsonl"), *args]) == 2
    with pytest.raises(SystemExit):
        run.main(["--set", "../bad", "--input", str(good), *args])
    assert CANARY not in capsys.readouterr().out


def test_report_lists_sets_and_refuses_mixed_hashes(tmp_path, toy_set):
    go(tmp_path, toy_set, [("a/0", CLEAN[0]), ("a/1", COPY)], "seta")
    recs = rep.load_records(tmp_path / "out")
    md = rep.build_report(recs, pending={"setz": "no adapter yet"}, expect_sha=recs[0]["set_sha256"])
    assert "seta" in md and recs[0]["set_sha256"] in md and COPY[:30] not in md and "setz" in md
    assert "no entry for" in md and "`toy`" in md  # the coverage gap is derived from the manifest
    assert "Flagged documents by coverage" in md and "| `seta` | 1 | 1 | 0 | 0 |" in md
    assert "| `toy:" in md and "| 1 | 1.000 |" in md  # one item, one document, full coverage
    recs2 = json.loads(json.dumps(recs))
    recs2[0]["set"] = "setb"
    recs2[0]["set_sha256"] = "1" * 64
    with pytest.raises(rep.ReportError, match="set_sha256"):
        rep.build_report(recs + recs2, pending={}, expect_sha=recs[0]["set_sha256"])


def test_report_title_and_output_path_for_another_stage(tmp_path, toy_set):
    go(tmp_path, toy_set, [("a/0", CLEAN[0])], "seta")
    recs = rep.load_records(tmp_path / "out")
    sft = rep.build_report(recs, pending={}, expect_sha=recs[0]["set_sha256"])
    assert sft.startswith("# SFT decontamination report")
    assert "--out teams/10-post-training/sft/decontam_report.md --sets <set-id> ...\n" in sft  # default unchanged
    rl = rep.build_report(recs, pending={}, expect_sha=recs[0]["set_sha256"], title="RL decontamination report",
                          out_rel="teams/10-post-training/rl/decontam_report.md")
    assert rl.startswith("# RL decontamination report")
    assert '--out teams/10-post-training/rl/decontam_report.md --sets <set-id> ... --title "RL decontamination report"' in rl


def test_report_refuses_different_tools(tmp_path, toy_set):
    go(tmp_path, toy_set, [("a/0", CLEAN[0])], "seta")
    recs = rep.load_records(tmp_path / "out")
    other = json.loads(json.dumps(recs[0]))
    other["set"] = "setb"
    other["tools"]["files"]["fpset.py"] = "0" * 64
    with pytest.raises(rep.ReportError, match="Team 9 tool files"):
        rep.build_report(recs + [other], pending={}, expect_sha=recs[0]["set_sha256"])


def test_report_refuses_a_failed_record(tmp_path, toy_set):
    go(tmp_path, toy_set, [("a/0", CLEAN[0]), ("a/0", CLEAN[1])], "dup")
    recs = rep.load_records(tmp_path / "out")
    with pytest.raises(rep.ReportError, match="failed"):
        rep.build_report(recs, pending={}, expect_sha=recs[0]["set_sha256"])


def test_report_refuses_a_record_without_the_second_pass(tmp_path, toy_set):
    src = write_rows(tmp_path / "n.jsonl", [("n/0", CLEAN[0])])
    run.run_set("n", [src], tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None, recheck=False)
    with pytest.raises(rep.ReportError, match="second pass"):
        rep.build_report(rep.load_records(tmp_path / "out"), pending={}, expect_sha=None)


def test_report_sets_filter_skips_old_records(tmp_path, toy_set):
    go(tmp_path, toy_set, [("a/0", CLEAN[0])], "seta")
    go(tmp_path, toy_set, [("b/0", CLEAN[1])], "setb")
    assert [r["set"] for r in rep.load_records(tmp_path / "out", ["setb"])] == ["setb"]
    with pytest.raises(rep.ReportError, match="no record for"):
        rep.load_records(tmp_path / "out", ["setc"])


def _stopped_run(tmp_path, toy_set, rows):
    """A finished run whose record is then deleted, as if the process had been stopped before writing it."""
    src = write_rows(tmp_path / "rs.jsonl", rows)
    full = run.run_set("rs", [src], tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None)
    (tmp_path / "out" / "rs.record.json").unlink()
    return src, full


def test_reuse_clean_gives_the_same_record_as_a_full_run(tmp_path, toy_set):
    rows = [(f"s/{i}", t) for i, t in enumerate(CLEAN * 3)] + [("s/90", "Solve. " + COPY), ("s/91", "x " + COPY)]
    src, full = _stopped_run(tmp_path, toy_set, rows)
    rec = run.run_set_reuse("rs", src, tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None, workers=3)
    assert rec["ok"] and all(rec["checks"].values()) and rec["reused_clean"]
    for k in ("rows_in", "rows_flagged", "rows_canary", "rows_removed", "rows_kept", "by_benchmark", "set_sha256"):
        assert rec[k] == full[k]
    assert rec["flagged"] == full["flagged"] and rec["clean"] == full["clean"]
    assert rec["recheck_on_clean"]["shards"] == 3 and rec["recheck_on_clean"]["flagged"] == 0
    assert not (tmp_path / "out" / ".work-rs").exists()


def test_reuse_clean_rejects_a_clean_file_that_is_not_from_the_input(tmp_path, toy_set):
    src, _ = _stopped_run(tmp_path, toy_set, [("s/0", CLEAN[0]), ("s/1", COPY)])
    clean = tmp_path / "out" / "rs.clean.jsonl"
    clean.write_bytes(clean.read_bytes() + (json.dumps({"id": "z", "text": CLEAN[1]}) + "\n").encode())
    with pytest.raises(run.RunError, match="subsequence"):
        run.run_set_reuse("rs", src, tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None, workers=2)


def test_reuse_clean_fails_when_a_kept_row_is_flagged(tmp_path, toy_set):
    src = write_rows(tmp_path / "rs.jsonl", [("s/0", CLEAN[0]), ("s/1", "Solve. " + COPY)])
    out = tmp_path / "out"
    out.mkdir()
    shutil_copy = (tmp_path / "rs.jsonl").read_bytes()
    (out / "rs.clean.jsonl").write_bytes(shutil_copy)  # a "clean" file that still holds the flagged row
    rec = run.run_set_reuse("rs", src, out, TOOLS, fingerprints=str(toy_set), expect_sha=None, workers=2)
    assert not rec["ok"] and rec["checks"]["clean_file_flags_0"] is False


def test_reuse_clean_when_the_run_removed_a_canary_row(tmp_path, toy_set):
    src, full = _stopped_run(tmp_path, toy_set, [("s/0", CLEAN[0]), ("s/1", "notes " + CANARY + " end"), ("s/2", CLEAN[1])])
    rec = run.run_set_reuse("rs", src, tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None, workers=2)
    assert rec["rows_canary"] == 1 and rec["rows_kept"] == 2 and rec["checks"]["every_removed_row_is_hit"]
    assert CANARY not in json.dumps(rec)


def test_report_marks_full_and_sampled_sets(tmp_path, toy_set):
    go(tmp_path, toy_set, [("s/0", CLEAN[0])], name="aaa")
    go(tmp_path, toy_set, [("s/0", CLEAN[1])], name="bbb")
    recs = rep.load_records(tmp_path / "out")
    md = rep.build_report(recs, {}, expect_sha=None, full={"aaa"})
    assert "| `aaa` | full set |" in md and "| `bbb` | sample |" in md and "not cleared as a whole" in md
    assert "Run on" not in rep.build_report(recs, {}, expect_sha=None)


def test_drop_clean_deletes_the_file_but_keeps_its_hash(tmp_path, toy_set):
    src = write_rows(tmp_path / "d.jsonl", [("s/0", CLEAN[0]), ("s/1", "x " + COPY)])
    rec = run.run_set("d", [src], tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None, drop_clean=True)
    assert rec["ok"] and rec["clean_files_deleted"] and rec["clean"][0]["sha256"]
    assert not (tmp_path / "out" / "d.clean.jsonl").exists()
    assert rec["recheck_on_clean"]["flagged"] == 0  # the second pass ran before the file was deleted


def test_merged_parts_equal_one_run(tmp_path, toy_set):
    rows = [(f"s/{i}", t) for i, t in enumerate(CLEAN * 2)] + [("s/90", "Solve. " + COPY), ("s/91", "x " + COPY)]
    whole = write_rows(tmp_path / "w.jsonl", rows)
    full = run.run_set("w", [whole], tmp_path / "out", TOOLS, fingerprints=str(toy_set), expect_sha=None)
    parts = []
    for n, chunk in enumerate((rows[:3], rows[3:7], rows[7:])):
        f = write_rows(tmp_path / f"p{n}.jsonl", chunk)
        parts.append(run.run_set(f"w.p{n}", [f], tmp_path / "parts", TOOLS, fingerprints=str(toy_set), expect_sha=None))
    merged = run.merge_records("w", parts, {"parts_cover_source": True}, tmp_path / "merged")
    for k in ("rows_in", "rows_flagged", "rows_canary", "rows_removed", "rows_kept", "by_benchmark", "flagged"):
        assert merged[k] == full[k]
    assert merged["ok"] and merged["parts"] == 3 and merged["checks"]["parts_cover_source"]
    assert merged["recheck_on_clean"]["docs"] == full["recheck_on_clean"]["docs"]
    assert (tmp_path / "merged" / "w.record.json").is_file()
    assert rep.build_report([merged], {}, expect_sha=None)  # the report accepts a merged record


def test_merge_refuses_parts_from_different_tools_or_with_a_failure(tmp_path, toy_set):
    a = write_rows(tmp_path / "a.jsonl", [("a/0", CLEAN[0])])
    b = write_rows(tmp_path / "b.jsonl", [("b/0", "notes " + CANARY + " end")])
    ra = run.run_set("a", [a], tmp_path / "o", TOOLS, fingerprints=str(toy_set), expect_sha=None)
    rb = run.run_set("b", [b], tmp_path / "o", TOOLS, fingerprints=str(toy_set), expect_sha=None)
    assert not run.merge_records("ab", [ra, rb])["ok"]  # a canary in one part makes the whole set fail
    rc = dict(ra, tools={"files": {}, "git_commit": "other"})
    with pytest.raises(run.RunError, match="different tools"):
        run.merge_records("ac", [ra, rc])


def test_pipeline_starts_only_files_the_downloader_marked_complete(tmp_path, monkeypatch):
    import decontam_pipeline as dp

    monkeypatch.setenv("G10_LOCAL_ROOT", str(tmp_path))
    f = tmp_path / "org" / "repo" / "data" / "a.jsonl"
    f.parent.mkdir(parents=True)
    f.write_text("{}\n")
    unit = {"dataset": "org/repo", "file": "data/a.jsonl"}
    assert not dp.local_ready(unit)  # still downloading: no marker
    Path(str(f) + ".ok").write_text("")
    assert dp.local_ready(unit)
    dp.delete_local_source(unit)
    assert not f.exists() and not Path(str(f) + ".ok").exists()
