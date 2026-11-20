"""Tests for verify_shards.py: a good set of shards passes, and each way a shard on disk can be wrong is caught and named.

The shards are made by the real run_shards.py / shard_writer.py (G6's baseline tokenizer with --any-tokenizer, as in
test_run_shards.py) over a synthetic pipeline run (synthetic_run.py). Each test breaks one thing after the shards were written.

  python -m pytest teams/01-data-a/shards/tests/test_verify_shards.py
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from synthetic_run import make_run, sha  # noqa: E402  (also puts shards/ and pipeline/ on the path)
import run_shards as rs  # noqa: E402  (imports shard_writer, which puts G6's folder on the path)
import verify_shards as vs  # noqa: E402
from dataio.tokenizer import BrahmicTokenizer  # noqa: E402

BASE = BrahmicTokenizer().path
TEXTS = ["The water cycle moves water between the sea, the air and the land.\n",
         "package main\n\nfunc area(r float64) float64 {\n\treturn 3.14159 * r * r\n}\n",
         "पानी समुद्र, हवा और ज़मीन के बीच घूमता है।\n"]
TABLE = {"packs": {"pk-a": {"language": "go", "script": "Latn", "domain": "code", "lane": "code"},
                   "pk-b": {"language": "en", "script": "Latn", "domain": "english", "lane": "english"}}}
SID = "pk-a-train-000000"


def rows(pack, tag):
    return [{"doc_id": f"{tag}{k}", "text": t, "url": "", "lang_label": "en", "pack_id": pack} for k, t in enumerate(TEXTS)]


@pytest.fixture
def made(tmp_path, monkeypatch):
    """Shards of pk-a (two parts) and pk-b, written by run_shards.py; verify() is called through made.check()."""
    parts = {("train", "pk-a/part-00000.parquet"): rows("pk-a", "a0_"), ("train", "pk-a/part-00001.parquet"): rows("pk-a", "a1_"),
             ("train", "pk-b/part-00000.parquet"): rows("pk-b", "b0_"), ("heldout", "pk-a/part-00000.parquet"): rows("pk-a", "h0_")}
    run = make_run(tmp_path / "pipeline", monkeypatch, parts)
    table, out = tmp_path / "pack_table.json", tmp_path / "shards"
    table.write_text(json.dumps(TABLE), encoding="utf-8")
    assert rs.main(["--input", str(run / "final"), "--manifest", str(run / "pipeline_manifest.json"), "--tokenizer", str(BASE),
                    "--any-tokenizer", "--pack-table", str(table), "--out", str(out)]) == 0
    m = SimpleNamespace(run=run, out=out, table=table, tokenizer=BASE)

    def check(summary=True, tokenizer=None):
        s = json.loads((out / "shards_summary.json").read_text(encoding="utf-8")) if summary is True else summary
        return vs.verify(out, run / "pipeline_manifest.json", tokenizer or BASE, table, s)
    m.check = check
    return m


def edit_manifest(made, sid=SID, **changes):
    p = made.out / f"{sid}.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    m.update(changes)
    p.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")


def rehash(made, sid=SID):
    """Make the manifest agree with the files as they are now, so that only the content checks can catch the change."""
    m = json.loads((made.out / f"{sid}.json").read_text(encoding="utf-8"))
    edit_manifest(made, sid, payload_sha256=sha(made.out / m["payload_uri"]), payload_bytes=(made.out / m["payload_uri"]).stat().st_size,
                  index_sha256=sha(made.out / m["index_uri"]), sample_metadata_sha256=sha(made.out / m["sample_metadata_uri"]))


def test_good_shards_pass_and_their_hashes_are_returned(made):
    problems, hashes = made.check()
    assert problems == []
    assert sorted(hashes) == sorted(f"pk-{p}-train-00000{i}.{x}" for p, i in (("a", 0), ("a", 1), ("b", 0))
                                    for x in ("bin", "docs.parquet", "idx.npy"))
    assert hashes["pk-a-train-000000.bin"] == sha(made.out / "pk-a-train-000000.bin")


def test_without_a_summary_the_shards_alone_are_checked(made):
    assert made.check(summary=None)[0] == []


def test_a_missing_index_is_named(made):
    (made.out / f"{SID}.idx.npy").unlink()
    problems, _ = made.check()
    assert any(SID in p and "idx.npy is missing" in p for p in problems)


def test_a_missing_dump_or_quality_report_is_named(made):
    (made.out / f"{SID}.dump.md").unlink()
    (made.out / "pk-b-train-000000.quality_report.json").unlink()
    problems = made.check()[0]
    assert any("dump.md is missing" in p for p in problems) and any("quality_report.json is missing" in p for p in problems)


def test_a_changed_byte_in_the_payload_is_caught_by_its_hash(made):
    p = made.out / f"{SID}.bin"
    data = bytearray(p.read_bytes())
    data[vs.HEADER_BYTES + 8] ^= 1
    p.write_bytes(bytes(data))
    assert any(f"{SID}.bin: sha256" in x for x in made.check()[0])


def test_a_changed_token_with_the_hash_fixed_is_caught_by_the_content_check(made):
    p = made.out / f"{SID}.bin"
    data = np.fromfile(p, dtype="<u4")
    data[vs.HEADER_BYTES // 4] = (data[vs.HEADER_BYTES // 4] + 1) % 1000  # first token of the first document
    data.tofile(p)
    rehash(made)
    problems = made.check()[0]
    assert problems == [f"{SID}: document 0 (a0_0) is not the tokens of its text in train/pk-a/part-00000.parquet"]


def test_a_changed_token_in_the_last_document_is_caught_too(made):
    p = made.out / f"{SID}.bin"
    data = np.fromfile(p, dtype="<u4")
    data[-2] = (data[-2] + 1) % 1000  # the token before the final EOS
    data.tofile(p)
    rehash(made)
    assert [x for x in made.check()[0] if "document 2" in x and "not the tokens of its text" in x]


def test_a_truncated_payload_is_caught_by_size(made):
    p = made.out / f"{SID}.bin"
    p.write_bytes(p.read_bytes()[:-4])
    problems = made.check()[0]
    assert any("bytes, token_count" in x for x in problems)


def test_a_wrong_header_count_is_caught(made):
    p = made.out / f"{SID}.bin"
    data = bytearray(p.read_bytes())
    data[8:12] = (5).to_bytes(4, "little")
    p.write_bytes(bytes(data))
    rehash(made)
    assert any("the header says 5 tokens" in x for x in made.check()[0])


def test_a_wrong_hash_in_the_manifest_is_caught(made):
    edit_manifest(made, index_sha256="0" * 64)
    assert any(f"{SID}.idx.npy: sha256" in x for x in made.check()[0])


def test_a_manifest_without_a_template_field_is_named(made):
    p = made.out / f"{SID}.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    del m["inputs_sha256"]
    p.write_text(json.dumps(m), encoding="utf-8")
    assert made.check()[0][0] == f"{SID}: the manifest lacks inputs_sha256"


def test_an_index_that_does_not_end_at_the_token_count_is_caught(made):
    p = made.out / f"{SID}.idx.npy"
    idx = np.load(p)
    idx[-1] -= 1
    np.save(p, idx)
    rehash(made)
    assert any("idx.npy: not an int64 index" in x for x in made.check()[0])


def test_metadata_with_a_missing_row_is_caught(made):
    p = made.out / f"{SID}.docs.parquet"
    pq.write_table(pq.read_table(p).slice(0, 2), p)
    rehash(made)
    assert any("2 rows, doc_count is 3" in x for x in made.check()[0])


def test_metadata_naming_another_doc_id_is_caught(made):
    p = made.out / f"{SID}.docs.parquet"
    t = pq.read_table(p)
    ids = t.column("doc_id").to_pylist()
    ids[0] = "somebody_else"
    pq.write_table(t.set_column(t.schema.get_field_index("doc_id"), "doc_id", pa.array(ids)), p)
    rehash(made)
    assert any("document 0: row 0 of train/pk-a/part-00000.parquet is a0_0, the metadata says somebody_else" in x for x in made.check()[0])


def test_a_special_id_inside_a_document_is_caught(made):
    p = made.out / f"{SID}.bin"
    data = np.fromfile(p, dtype="<u4")
    data[vs.HEADER_BYTES // 4 + 1] = 130_800  # inside G3's block of specials
    data.tofile(p)
    rehash(made)
    assert any("a special id other than the EOS" in x for x in made.check()[0])


def test_an_id_above_the_vocabulary_is_caught(made):
    p = made.out / f"{SID}.bin"
    data = np.fromfile(p, dtype="<u4")
    data[vs.HEADER_BYTES // 4 + 1] = 200_000
    data.tofile(p)
    rehash(made)
    assert any("a token id of 131072 or more" in x for x in made.check()[0])


def test_a_stray_shard_manifest_is_caught(made):
    (made.out / "pk-z-train-000000.json").write_text((made.out / f"{SID}.json").read_text(encoding="utf-8"), encoding="utf-8")
    problems = made.check()[0]
    assert any("pk-z-train-000000: there is a shard manifest for it, but the summary does not list it" in x for x in problems)
    assert any("pk-z-train-000000: shard_id is" in x for x in problems)


def test_a_summary_that_lists_a_shard_that_is_not_there_is_caught(made):
    s = json.loads((made.out / "shards_summary.json").read_text(encoding="utf-8"))
    s["parts"]["train/pk-a/part-00000.parquet"]["shards"][0]["shard_id"] = "pk-a-train-000009"
    problems = made.check(summary=s)[0]
    assert any("pk-a-train-000009: the summary lists it as written, but there is no shard manifest" in x for x in problems)
    assert any(f"{SID}: there is a shard manifest for it, but the summary does not list it" in x for x in problems)


def test_a_summary_with_other_counts_is_caught(made):
    s = json.loads((made.out / "shards_summary.json").read_text(encoding="utf-8"))
    s["parts"]["train/pk-b/part-00000.parquet"]["shards"][0]["tokens"] += 1
    s["counts"]["written"] += 1
    problems = made.check(summary=s)[0]
    assert any("the summary says tokens" in x for x in problems) and any("counts 4 written parts, and lists 3" in x for x in problems)


def test_a_changed_cleaning_pipeline_file_is_caught(made):
    p = made.out / "cleaning_pipeline.json"
    p.write_text(p.read_text(encoding="utf-8") + " ", encoding="utf-8")
    problems = made.check()[0]
    assert any("is not the run's own" in x for x in problems) and any("cleaning_pipeline_sha256" in x for x in problems)


def test_shards_from_other_processing_are_not_compared_with_this_runs_final_data(made):
    p = made.out / "cleaning_pipeline.json"
    p.write_text(p.read_text(encoding="utf-8") + " ", encoding="utf-8")
    problems = made.check()[0]
    assert any("other processing" in x for x in problems) and not any("not the tokens of its text" in x or "document 0" in x for x in problems)


def test_a_missing_cleaning_pipeline_file_is_caught(made):
    (made.out / "cleaning_pipeline.json").unlink()
    assert any("cleaning_pipeline.json is missing" in x for x in made.check()[0])


def test_a_manifest_that_disagrees_with_the_pack_table_is_caught(made):
    TABLE_B = json.loads(made.table.read_text(encoding="utf-8"))
    TABLE_B["packs"]["pk-a"]["language"] = "rust"
    TABLE_B["packs"]["pk-b"]["lane"] = "math"
    made.table.write_text(json.dumps(TABLE_B), encoding="utf-8")
    problems = made.check()[0]
    assert any("language is 'go', pack_table.json says 'rust' for pk-a" in x for x in problems)
    assert any("capability_lane is 'english', pack_table.json says 'math' for pk-b" in x for x in problems)


def test_a_licence_the_table_does_not_give_is_caught_in_the_manifest(made):
    edit_manifest(made, license="made up", license_source="nowhere")
    assert any("pk-a-train-000000: license is 'made up', the pack table says None for pk-a" in x for x in made.check()[0])


def test_a_licence_the_table_gives_must_be_in_the_manifest(made):
    table = json.loads(made.table.read_text(encoding="utf-8"))
    table["packs"]["pk-a"].update(license="a licence", license_source="a table")
    made.table.write_text(json.dumps(table), encoding="utf-8")
    problems = made.check()[0]
    assert any("pk-a-train-000000: license is None, the pack table says 'a licence' for pk-a" in x for x in problems)
    assert any("pk-a-train-000001: license_source is None, the pack table says 'a table' for pk-a" in x for x in problems)
    assert not any("pk-b" in x for x in problems)  # a pack the table gives no licence stays valid without one


def test_a_licence_other_than_the_tables_is_caught(made):
    table = json.loads(made.table.read_text(encoding="utf-8"))
    table["packs"]["pk-a"].update(license="a licence", license_source="a table")
    made.table.write_text(json.dumps(table), encoding="utf-8")
    edit_manifest(made, license="a licence", license_source="a table")
    assert not [x for x in made.check()[0] if x.startswith(SID + ": licen")]
    edit_manifest(made, license="another licence")
    assert any(f"{SID}: license is 'another licence', the pack table says 'a licence' for pk-a" in x for x in made.check()[0])
    edit_manifest(made, license="a licence", license_source=None)
    assert any(f"{SID}: license_source is None, the pack table says 'a table' for pk-a" in x for x in made.check()[0])


def test_a_pack_that_is_not_in_the_table_is_caught(made):
    made.table.write_text(json.dumps({"packs": {"pk-b": TABLE["packs"]["pk-b"]}}), encoding="utf-8")
    assert any("pk-a is not in pack_table.json" in x for x in made.check()[0])


def test_another_tokenizer_is_caught(made, tmp_path):
    other = tmp_path / "other_tokenizer.json"
    other.write_text(json.dumps(json.loads(Path(BASE).read_text(encoding="utf-8")), indent=1), encoding="utf-8")  # same tokenizer, other bytes
    assert any("tokenizer_sha256" in x for x in made.check(tokenizer=other)[0])


def test_another_f2_set_is_caught(made):
    edit_manifest(made, decontam_set_sha256="f" * 64)
    assert any("decontam_set_sha256" in x for x in made.check()[0])


def test_a_final_part_that_lost_the_row_is_caught(made):
    p = made.run / "final" / "train" / "pk-a" / "part-00000.parquet"
    pq.write_table(pq.read_table(p).slice(0, 1), p)
    assert any("document 2: row 2 of train/pk-a/part-00000.parquet is not there" in x for x in made.check()[0])


def test_the_command_line_reports_problems_and_exits_1(made, monkeypatch, capsys):
    argv = ["verify_shards.py", "--out", str(made.out), "--manifest", str(made.run / "pipeline_manifest.json"),
            "--tokenizer", str(BASE), "--pack-table", str(made.table)]
    monkeypatch.setattr(sys, "argv", argv)
    assert vs.main() == 0 and "0 problem(s)" in capsys.readouterr().out
    (made.out / f"{SID}.bin").unlink()
    assert vs.main() == 1
    out = capsys.readouterr()
    assert "problem(s)" in out.out and "0 problem(s)" not in out.out
    assert f"{SID}.bin is missing" in out.err


def test_an_empty_folder_is_a_problem(tmp_path, made):
    empty = tmp_path / "empty"
    empty.mkdir()
    problems, _ = vs.verify(empty, made.run / "pipeline_manifest.json", BASE, made.table, None)
    assert any("no shard manifest" in x for x in problems) and any("cleaning_pipeline.json is missing" in x for x in problems)
