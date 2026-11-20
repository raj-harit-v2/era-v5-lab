"""Tests for audit/check_shard.py on a made-up shard of three documents (token ids only, no text).

    python -m pytest teams/01-data-a/tests/audit -q
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

TEAM = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_shard", TEAM / "audit" / "check_shard.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

SID = "code-go-train-000007"
DOCS = [[11, 12, 13, cs.EOS_ID], [21, cs.EOS_ID], [31, 32, cs.EOS_ID]]


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


PART = "train/code-go/part-00000.parquet"
DEDUP = {"remove_list_sha256": "d" * 64, "remove_list_rows": 6,
         "overlap": {"matches_sha256": "e" * 64, "docs_sha256": "f" * 64, "k": 5, "floor": 0.5, "code_sha256": "a" * 64},
         "settings": {"cross_pack": True, "pack_order": ["code-go"], "licence_usable": {"code-go": True},
                      "default_licence_usable": False}, "code_sha256": "b" * 64}


def write_shard(d, docs=DOCS, dedup=DEDUP, sid=None, first_row=0, part=PART, rows=None):
    """Write a shard in format v1 with a manifest that matches it, and return the manifest path. sid, first_row, part
    and rows (input_row of each doc; default first_row, first_row + 1, ...) place it in a part, for the map tests."""
    global SID
    sid_saved, SID = SID, sid or SID
    try:
        return _write(d, docs, dedup, first_row, part, rows)
    finally:
        SID = sid_saved


def _write(d, docs, dedup, first_row, part, rows):
    toks = np.array([t for doc in docs for t in doc], dtype="<u4")
    header = np.zeros(cs.HEADER_BYTES // 4, dtype="<i4")
    header[:3] = [cs.MAGIC, cs.VERSION, len(toks)]
    (d / f"{SID}.bin").write_bytes(header.tobytes() + toks.tobytes())
    idx = np.concatenate([[0], np.cumsum([len(x) for x in docs])]).astype(np.int64)
    np.save(d / f"{SID}.idx.npy", idx)
    rows = list(rows) if rows is not None else list(range(first_row, first_row + len(docs)))
    pq.write_table(pa.table({"doc_id": [f"{SID}_d{i}" for i in range(len(docs))], "input_part": [part] * len(docs),
                             "input_row": rows, "n_tokens": [len(x) for x in docs]}), d / f"{SID}.docs.parquet")
    qr = {"shard_id": SID, "first_row": first_row, "rows_read": first_row + len(docs), "docs_in_shard": len(docs),
          "left_out": {"secret": 0, "empty": 0, "special": 0, "roundtrip": 0, "oversize": 0},
          "left_out_docs": {"secret": [], "empty": [], "special": [], "roundtrip": [], "oversize": []},
          "upstream": {"input_part": part}}
    (d / f"{SID}.quality_report.json").write_text(json.dumps(qr))
    clean_sha = _sha(cs.CLEAN_PYS[0]) if cs.CLEAN_PYS[0].exists() else "0" * 64
    (d / "cleaning_pipeline.json").write_text(json.dumps(
        {"clean_py_sha256": clean_sha, "f2_set_sha256": cs.F2_V2_SHA256, "dedup": dedup}))
    man = json.loads(cs.TEMPLATE.read_text())
    man.update({
        "dataset_version": "test", "shard_id": SID, "tokenizer_sha256": cs.P1536_SHA256, "pack_id": "code-go", "language": "go", "domain": "code",
        "capability_lane": "code", "license": "test-licence", "license_source": "test", "split": "train",
        "payload_uri": f"{SID}.bin", "payload_sha256": _sha(d / f"{SID}.bin"),
        "payload_bytes": cs.HEADER_BYTES + 4 * len(toks),
        "index_uri": f"{SID}.idx.npy", "index_sha256": _sha(d / f"{SID}.idx.npy"),
        "doc_count": len(docs), "token_count": len(toks),
        "inputs_sha256": "1" * 64, "cleaning_pipeline_sha256": _sha(d / "cleaning_pipeline.json"),
        "sample_metadata_uri": f"{SID}.docs.parquet", "sample_metadata_sha256": _sha(d / f"{SID}.docs.parquet"),
        "quality_report_uri": f"{SID}.quality_report.json",
        "quality_report_sha256": _sha(d / f"{SID}.quality_report.json"),
        "created_by": "2" * 40})
    path = d / f"{SID}.json"
    path.write_text(json.dumps(man))
    return path


def by_status(rows, status):
    return [r["check"] for r in rows if r["status"] == status]


LOW_SPECIALS = (36, 129994)  # two of the special ids below 130,725 in p1536 and C3


def test_good_shard_passes_every_check(tmp_path):
    write_shard(tmp_path)
    rows = cs.run_checks(tmp_path, SID, special_ids=LOW_SPECIALS, expect_dataset_version="test")
    assert by_status(rows, cs.FAIL) == []
    assert by_status(rows, cs.NOT_CHECKED) == []
    assert "every document ends with EOS" in by_status(rows, cs.PASS)


def test_a_truncated_index_fails_and_folder_audit_continues(tmp_path, capsys):
    make_run(tmp_path)
    index = tmp_path / 'code-go-train-000000.idx.npy'
    index.write_bytes(index.read_bytes()[:-8])
    report = tmp_path / 'audit.json'
    assert cs.main([str(tmp_path), '--json', str(report)]) == 1
    result = json.loads(report.read_text())
    assert 'index can be read' in by_status(result['shards']['code-go-train-000000']['checks'], cs.FAIL)
    assert len(result['shards']) == 4
    assert result['shards']['code-go-train-000003']['counts'][cs.FAIL] == 0


@pytest.mark.parametrize('suffix', ['.docs.parquet', '.bin', '.idx.npy', '.quality_report.json'])
def test_missing_manifest_listed_file_fails_a_full_folder_audit(tmp_path, suffix):
    make_run(tmp_path)
    (tmp_path / ('code-go-train-000000' + suffix)).unlink()
    report = tmp_path / 'audit.json'
    assert cs.main([str(tmp_path), '--json', str(report)]) == 1
    rows = json.loads(report.read_text())['shards']['code-go-train-000000']['checks']
    assert any(r['status'] == cs.FAIL and r['observed'] == 'file not present' for r in rows)


def test_missing_files_in_a_single_shard_partial_bundle_are_not_checked(tmp_path):
    write_shard(tmp_path)
    (tmp_path / f'{SID}.docs.parquet').unlink()
    rows = cs.run_checks(tmp_path, SID)
    assert by_status(rows, cs.FAIL) == []
    assert '.docs.parquet checks' in by_status(rows, cs.NOT_CHECKED)


@pytest.mark.parametrize('index', [np.array([], dtype=np.int64), np.array([[0, 9]], dtype=np.int64),
                                  np.array([0., 9.]), np.array([0, -1, 9], dtype=np.int64)])
def test_malformed_index_reports_failures_without_crashing(tmp_path, index):
    write_shard(tmp_path)
    np.save(tmp_path / f'{SID}.idx.npy', index)
    assert by_status(cs.run_checks(tmp_path, SID), cs.FAIL)


def test_low_special_id_inside_a_document_fails(tmp_path):
    write_shard(tmp_path, docs=[[11, 36, 13, cs.EOS_ID], [21, cs.EOS_ID]])
    rows = cs.run_checks(tmp_path, SID, special_ids=LOW_SPECIALS)
    assert by_status(rows, cs.FAIL) == ["none of the 2 special ids below 130725 inside a document"]
    unchecked = cs.run_checks(tmp_path, SID)  # without the special ids it cannot tell, and says so
    assert "special ids below 130725 inside a document" in by_status(unchecked, cs.NOT_CHECKED)


@pytest.mark.parametrize("chunk", [1, 2, 3, 5, 1 << 22])
def test_results_do_not_depend_on_the_chunk_size(tmp_path, monkeypatch, chunk):
    write_shard(tmp_path, docs=[[11, 36, 13, cs.EOS_ID], [21, cs.EOS_ID], [130725, 32, cs.EOS_ID], [5, 6, 7, 99]])
    monkeypatch.setattr(cs, "CHUNK", chunk)
    rows = {r["check"]: (r["status"], r["observed"]) for r in cs.run_checks(tmp_path, SID, special_ids=LOW_SPECIALS)}
    assert rows["every document ends with EOS"] == (cs.FAIL, "3")
    assert rows["no special id >= 130725 inside a document"] == (cs.FAIL, "1")
    assert rows["none of the 2 special ids below 130725 inside a document"] == (cs.FAIL, "1")
    assert rows["every id < vocab 131072"] == (cs.PASS, str(cs.EOS_ID))


def test_expected_tokenizer(tmp_path):
    write_shard(tmp_path)  # write_shard names p1536
    assert by_status(cs.run_checks(tmp_path, SID, expect_tokenizer=cs.P1536_SHA256), cs.FAIL) == []
    assert by_status(cs.run_checks(tmp_path, SID, expect_tokenizer=cs.C3_SHA256), cs.FAIL) == ["tokenizer_sha256 is C3"]


def test_special_ids_from_tokenizer_json(tmp_path):
    p = tmp_path / "tokenizer.json"
    p.write_text(json.dumps({"added_tokens": [{"id": 36, "special": True}, {"id": 500, "special": False},
                                              {"id": 130822, "special": True}]}))
    assert cs.special_ids_from(p) == [36, 130822]


def test_missing_bin_and_docs_are_not_checked_never_pass(tmp_path):
    write_shard(tmp_path)
    (tmp_path / f"{SID}.bin").unlink()
    (tmp_path / f"{SID}.docs.parquet").unlink()
    rows = cs.run_checks(tmp_path, SID)
    assert by_status(rows, cs.FAIL) == []
    not_checked = by_status(rows, cs.NOT_CHECKED)
    assert f"payload_sha256 ({SID}.bin)" in not_checked
    assert f"sample_metadata_sha256 ({SID}.docs.parquet)" in not_checked
    assert not any(".bin" in c or "docs.parquet" in c for c in by_status(rows, cs.PASS))


def test_changed_bin_fails_its_hash(tmp_path):
    write_shard(tmp_path)
    b = tmp_path / f"{SID}.bin"
    raw = bytearray(b.read_bytes())
    raw[cs.HEADER_BYTES] ^= 1  # one bit of the first token
    b.write_bytes(bytes(raw))
    assert f"payload_sha256 ({SID}.bin)" in by_status(cs.run_checks(tmp_path, SID), cs.FAIL)


def test_wrong_token_count_fails(tmp_path):
    man_path = write_shard(tmp_path)
    man = json.loads(man_path.read_text())
    man["token_count"] += 1
    man_path.write_text(json.dumps(man))
    failed = by_status(cs.run_checks(tmp_path, SID), cs.FAIL)
    assert "payload_bytes = 1024 + 4 x token_count" in failed
    assert "index ends at token_count" in failed


def test_doc_without_eos_and_special_id_inside_fail(tmp_path):
    write_shard(tmp_path, docs=[[11, 12, 13, 99], [cs.SPECIAL_LO, cs.EOS_ID]])
    failed = by_status(cs.run_checks(tmp_path, SID), cs.FAIL)
    assert "every document ends with EOS" in failed
    assert "no special id >= 130725 inside a document" in failed


def test_id_at_vocab_fails(tmp_path):
    write_shard(tmp_path, docs=[[cs.VOCAB, cs.EOS_ID]])
    assert "every id < vocab 131072" in by_status(cs.run_checks(tmp_path, SID), cs.FAIL)


def test_missing_dedup_version_fails(tmp_path):
    write_shard(tmp_path, dedup=None)
    assert by_status(cs.run_checks(tmp_path, SID), cs.FAIL) == ["cleaning_pipeline records a dedup run"]


@pytest.mark.parametrize("field,value", [("eos_token_id", 36), ("split", "test"),
                                          ("tokenizer_sha256", "f" * 64), ("schema_version", "shard-v0"),
                                          ("created_by", "5255556"), ("created_by", "<git commit of the shard writer>")])
def test_bad_manifest_values_fail(tmp_path, field, value):
    man_path = write_shard(tmp_path)
    man = json.loads(man_path.read_text())
    man[field] = value
    man_path.write_text(json.dumps(man))
    assert by_status(cs.run_checks(tmp_path, SID), cs.FAIL)


def test_missing_field_fails(tmp_path):
    man_path = write_shard(tmp_path)
    man = json.loads(man_path.read_text())
    del man["created_by"]
    man_path.write_text(json.dumps(man))
    assert "all template fields present" in by_status(cs.run_checks(tmp_path, SID), cs.FAIL)


# --- the dedup record, clean.py, dataset_version, licence fields and row ranges (format of #56 on g1-pipeline)

def test_dedup_record_without_its_fields_fails_and_null_code_hashes_are_reported(tmp_path):
    write_shard(tmp_path, dedup={"remove_list_sha256": "d" * 64, "remove_list_rows": 1, "overlap": None, "settings": {},
                                 "code_sha256": None})
    rows = cs.run_checks(tmp_path, SID)
    assert "dedup record has remove list, overlap and settings" in by_status(rows, cs.FAIL)
    assert "dedup and overlap code_sha256 recorded" in by_status(rows, cs.NOT_CHECKED)


def test_expected_dataset_version(tmp_path):
    write_shard(tmp_path)
    assert by_status(cs.run_checks(tmp_path, SID, expect_dataset_version="test"), cs.FAIL) == []
    assert by_status(cs.run_checks(tmp_path, SID, expect_dataset_version="corpus-v1"), cs.FAIL) == ["dataset_version is corpus-v1"]
    assert "dataset_version (reported, no --expect-dataset-version)" in by_status(cs.run_checks(tmp_path, SID), cs.NOT_CHECKED)


def test_clean_py_must_be_one_of_the_checkouts(tmp_path):
    write_shard(tmp_path)
    assert by_status(cs.run_checks(tmp_path, SID, clean_pys=cs.CLEAN_PYS[1:]), cs.FAIL) == [
        "cleaning_pipeline clean.py is a clean.py in this checkout"]


def test_rows_outside_the_shards_range_or_from_two_parts_fail(tmp_path):
    write_shard(tmp_path, first_row=10, rows=[10, 11, 13])  # rows_read is 13, so row 13 is outside
    assert "docs.parquet input_row increasing, inside first_row..rows_read-1" in by_status(cs.run_checks(tmp_path, SID), cs.FAIL)
    write_shard(tmp_path)
    t = pq.read_table(tmp_path / f"{SID}.docs.parquet").to_pydict()
    t["input_part"][1] = "train/code-go/part-00001.parquet"
    pq.write_table(pa.table(t), tmp_path / f"{SID}.docs.parquet")
    man = json.loads((tmp_path / f"{SID}.json").read_text())
    man["sample_metadata_sha256"] = _sha(tmp_path / f"{SID}.docs.parquet")
    (tmp_path / f"{SID}.json").write_text(json.dumps(man))
    assert by_status(cs.run_checks(tmp_path, SID), cs.FAIL) == ["docs.parquet rows come from one input part"]


# --- folder mode: the part-to-shards map of shards_summary.json (run_shards.py, rollover)

def make_run(d, layout=((PART, (3, 2, 1)), ("train/code-go/part-00001.parquet", (2,)))):
    """Shards for a pack over several parts, numbered across them, and the summary run_shards.py would write.
    layout: (part, docs per shard) in part order; every doc has two tokens plus EOS."""
    summary, k = {"run_id": "r", "parts": {}, "verified": True, "problems": []}, 0
    for part, sizes in layout:
        shards, row = [], 0
        for n in sizes:
            sid = f"code-go-train-{k:06d}"
            write_shard(d, docs=[[11 + i, 12, cs.EOS_ID] for i in range(n)], sid=sid, first_row=row, part=part)
            shards.append({"shard_id": sid, "docs": n, "tokens": 3 * n, "first_row": row, "rows_read": row + n})
            row, k = row + n, k + 1
        summary["parts"][part] = {"pack_id": "code-go", "status": "written", "shards": shards, "docs": row,
                                  "tokens": 3 * row, "rows_read": row, "rows_in_part": row, "truncated": False,
                                  "left_out": {"secret": 0, "empty": 0, "special": 0, "roundtrip": 0, "oversize": 0}}
    summary["parts"]["heldout/code-go/part-00000.parquet"] = {"pack_id": "code-go", "status": "not_sharded", "reason": "held-out"}
    summary["counts"] = {"written": len(layout), "empty": 0, "all_left_out": 0, "failed": 0, "skipped": 0, "not_sharded": 1,
                         "truncated": 0, "shards": k}
    summary["cleaning_pipeline_sha256"] = _sha(d / "cleaning_pipeline.json")
    (d / cs.SUMMARY).write_text(json.dumps(summary))
    return summary


def test_a_good_rollover_map_passes(tmp_path):
    rows = cs.run_map_checks(tmp_path, make_run(tmp_path))
    assert by_status(rows, cs.FAIL) == [] and by_status(rows, cs.NOT_CHECKED) == []
    assert "train/code-go: shards numbered from 000000 across its parts, in part order" in by_status(rows, cs.PASS)


def broken(tmp_path, change):
    s = make_run(tmp_path)
    change(s, tmp_path)
    return by_status(cs.run_map_checks(tmp_path, s), cs.FAIL)


def test_a_gap_between_shards_fails(tmp_path):
    def gap(s, d):
        s["parts"][PART]["shards"][1]["first_row"] = 4
    assert f"{PART}: shards cover its rows with no gap or overlap" in broken(tmp_path, gap)


def test_a_truncated_part_fails(tmp_path):
    def cut(s, d):
        s["parts"][PART]["rows_in_part"], s["parts"][PART]["truncated"] = 9, True
    assert f"{PART}: last rows_read = rows_read = rows_in_part, not truncated" in broken(tmp_path, cut)


def test_numbering_out_of_part_order_fails(tmp_path):
    def swap(s, d):
        a, b = s["parts"][PART]["shards"][0], s["parts"][PART]["shards"][1]
        a["shard_id"], b["shard_id"] = b["shard_id"], a["shard_id"]
    assert "train/code-go: shards numbered from 000000 across its parts, in part order" in broken(tmp_path, swap)


def test_an_unlisted_shard_in_the_folder_fails(tmp_path):
    def extra(s, d):
        write_shard(d, sid="code-go-train-000009")
    assert "folder: every shard is listed in the summary" in broken(tmp_path, extra)


def test_summary_counts_that_are_not_the_shards_fail(tmp_path):
    def more(s, d):
        s["parts"][PART]["shards"][0]["docs"] = 4
        s["parts"][PART]["docs"] = 7
    failed = broken(tmp_path, more)
    assert f"{PART}: code-go-train-000000 docs/tokens = its manifest" in failed


def test_a_doc_in_two_shards_fails(tmp_path):
    def dup(s, d):
        t = pq.read_table(d / "code-go-train-000001.docs.parquet").to_pydict()
        t["doc_id"][0] = "code-go-train-000000_d0"
        pq.write_table(pa.table(t), d / "code-go-train-000001.docs.parquet")
    assert "train/code-go: no doc_id in two of its shards" in broken(tmp_path, dup)


def test_a_failed_part_fails_the_run(tmp_path):
    def fail(s, d):
        s["parts"]["train/code-go/part-00002.parquet"] = {"pack_id": "code-go", "status": "failed", "reason": "x"}
        s["counts"]["failed"] = 1
    assert "run: no part failed or skipped" in broken(tmp_path, fail)


def test_a_missing_shard_fails_unless_subset(tmp_path):
    s = make_run(tmp_path)
    for f in tmp_path.glob("code-go-train-000003.*"):
        f.unlink()
    name = "train/code-go/part-00001.parquet: every listed shard is in the folder"
    assert name in by_status(cs.run_map_checks(tmp_path, s), cs.FAIL)
    rows = cs.run_map_checks(tmp_path, s, subset=True)
    assert name in by_status(rows, cs.NOT_CHECKED) and by_status(rows, cs.FAIL) == []


def test_folder_mode_exit_codes(tmp_path, capsys):
    make_run(tmp_path)
    args = [str(tmp_path), "--expect-tokenizer", "p1536", "--expect-dataset-version", "test", "--specials-from"]
    tok = tmp_path / "tokenizer.json"
    tok.write_text(json.dumps({"added_tokens": [{"id": 36, "special": True}]}))
    assert cs.main(args + [str(tok)]) == 0
    assert "4 shard(s)" in capsys.readouterr().out
    assert cs.main(args + [str(tok), "--expect-dataset-version", "corpus-v1"]) == 1


def test_a_real_rollover_run_passes(tmp_path, monkeypatch):
    """The real run_shards.py with a forced rollover (as in shards/tests/test_run_shards.py): the map passes, and so does
    every shard except what a test run cannot have (G6's baseline tokenizer, a made-up clean.py, no licence)."""
    pytest.importorskip("torch")
    import sys
    sys.path.insert(0, str(TEAM / "shards" / "tests"))
    t = pytest.importorskip("test_run_shards")
    run = t.make_run(tmp_path / "pipeline", monkeypatch, {
        ("train", "pk-a/part-00000.parquet"): t.rows("pk-a", "a0_"), ("train", "pk-a/part-00001.parquet"): t.rows("pk-a", "a1_"),
        ("heldout", "pk-a/part-00000.parquet"): t.rows("pk-a", "h0_")})
    table = tmp_path / "pack_table.json"
    table.write_text(json.dumps(t.TABLE))
    code, out, summary = t.go(run, tmp_path, table, "--pack", "pk-a", "--tokens", "40")
    assert code == 0 and summary["counts"]["shards"] > 2
    rows = cs.run_map_checks(out, summary)
    assert by_status(rows, cs.FAIL) == [] and by_status(rows, cs.NOT_CHECKED) == []
    expected = {"tokenizer_sha256 is a frozen tokenizer (p1536 or C3)", "cleaning_pipeline clean.py is a clean.py in this checkout"}
    for sid in cs.shard_ids_in(out):
        assert set(by_status(cs.run_checks(out, sid, expect_dataset_version="test"), cs.FAIL)) == expected
@pytest.mark.parametrize("drop,fails", [(("license", "license_source"), False), (("license_source",), True)])
def test_the_licence_fields_are_both_or_neither(tmp_path, drop, fails):
    man_path = write_shard(tmp_path)
    man = json.loads(man_path.read_text())
    for field in drop:
        del man[field]
    man_path.write_text(json.dumps(man))
    assert ("all template fields present" in by_status(cs.run_checks(tmp_path, SID), cs.FAIL)) == fails
