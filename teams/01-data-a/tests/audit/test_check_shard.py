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


def write_shard(d, docs=DOCS, dedup="dedup-v1"):
    """Write a shard in format v1 with a manifest that matches it, and return the manifest path."""
    toks = np.array([t for doc in docs for t in doc], dtype="<u4")
    header = np.zeros(cs.HEADER_BYTES // 4, dtype="<i4")
    header[:3] = [cs.MAGIC, cs.VERSION, len(toks)]
    (d / f"{SID}.bin").write_bytes(header.tobytes() + toks.tobytes())
    idx = np.concatenate([[0], np.cumsum([len(x) for x in docs])]).astype(np.int64)
    np.save(d / f"{SID}.idx.npy", idx)
    pq.write_table(pa.table({"doc_id": [f"d{i}" for i in range(len(docs))], "n_tokens": [len(x) for x in docs]}),
                   d / f"{SID}.docs.parquet")
    qr = {"shard_id": SID, "rows_read": len(docs), "docs_in_shard": len(docs),
          "left_out": {"secret": 0, "empty": 0, "special": 0, "roundtrip": 0},
          "left_out_docs": {"secret": [], "empty": [], "special": [], "roundtrip": []}}
    (d / f"{SID}.quality_report.json").write_text(json.dumps(qr))
    clean_sha = _sha(cs.CLEAN_PY) if cs.CLEAN_PY.exists() else "0" * 64
    (d / "cleaning_pipeline.json").write_text(json.dumps(
        {"clean_py_sha256": clean_sha, "f2_set_sha256": cs.F2_V2_SHA256, "dedup": dedup}))
    man = json.loads(cs.TEMPLATE.read_text())
    man.update({
        "dataset_version": "test", "shard_id": SID, "tokenizer_sha256": cs.P1536_SHA256, "pack_id": "code-go", "language": "go", "domain": "code",
        "capability_lane": "code", "split": "train",
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
    rows = cs.run_checks(tmp_path, SID, special_ids=LOW_SPECIALS)
    assert by_status(rows, cs.FAIL) == []
    assert by_status(rows, cs.NOT_CHECKED) == []
    assert "every document ends with EOS" in by_status(rows, cs.PASS)


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
    assert by_status(cs.run_checks(tmp_path, SID), cs.FAIL) == ["cleaning_pipeline records a dedup version"]


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
