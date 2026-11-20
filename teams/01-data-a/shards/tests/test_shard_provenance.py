"""Tests for provenance.py: a synthetic pipeline run (clean, overlap and dedup adopted; apply, a stand-in F2 and survivor
loss run by run_pipeline.py), then the chain of one final part checked, and broken one link at a time.

The made-up inputs and the stand-in F2 are the pipeline tests' (pipeline/tests): dedup's real file formats, no real data.

  python -m pytest teams/01-data-a/shards/tests/test_shard_provenance.py
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from synthetic_run import CLEAN_SHA, raw_sha, sha, write_cleaned  # noqa: E402  (also puts shards/ and pipeline/ on the path)
from conftest import PARTS  # noqa: E402  (pipeline/tests/conftest.py)
from test_run_pipeline import dedup_folder, overlap_folder, write_config  # noqa: E402
import provenance  # noqa: E402
import run_pipeline as rp  # noqa: E402


@pytest.fixture
def run(tmp_path, monkeypatch):
    """A finished synthetic run; F2 drops g0 (code-go part-00000) and h1 (held-out). Returns its folder."""
    for k in ("FAKE_F2_ERROR", "FAKE_F2_BAD_SHA", "FAKE_F2_CRASH"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("FAKE_F2_DROP", "g0,h1")
    cleaned = tmp_path / "cleaned"
    write_cleaned(cleaned, PARTS)
    overlap = overlap_folder(tmp_path / "overlap")
    dedup = dedup_folder(tmp_path / "dedup", overlap)
    config = write_config(tmp_path / "pipeline.json", {"cleaned": cleaned, "overlap": overlap, "dedup": dedup})
    rp.run(config)
    return tmp_path / "runs" / "test-run"


def load(run, split, part):
    return provenance.load(run / "final" / split / part, run / "pipeline_manifest.json")


def edit_json(path, **changes):
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(changes)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_a_part_with_a_dedup_removal(run):
    p = load(run, "train", "code-go/part-00001.parquet")  # g0 is removed here by dedup (group G000001, rule 4)
    assert p["part"] == {"split": "train", "part": "code-go/part-00001.parquet", "pack_id": "code-go",
                         "path": (run / "final/train/code-go/part-00001.parquet").as_posix()}
    assert p["counts"] == {"cleaned": 3, "removed_by_dedup": 1, "dropped_by_f2": 0, "final": 2}
    assert p["dedup"]["removed"] == [{"doc_id": "g0", "row_in_part": 0, "group_id": "G000001", "priority_rule": 4}]
    assert p["dedup"]["remove_list_rows"] == 2 and p["f2"]["dropped"] == []
    assert p["raw_input"] == {"sha256": raw_sha("train", "code-go/part-00001.parquet"),
                              "part": "train/code-go/part-00001.parquet"}
    assert p["clean"] == {"clean_py_sha256": CLEAN_SHA, "status": "cleaned"}
    assert p["final"]["sha256"] == sha(run / "final/train/code-go/part-00001.parquet")
    assert p["pipeline"]["manifest_sha256"] == sha(run / "pipeline_manifest.json") and p["pipeline"]["run_id"] == "test-run"


def test_a_part_with_an_f2_drop(run):
    p = load(run, "train", "code-go/part-00000.parquet")
    assert p["counts"] == {"cleaned": 5, "removed_by_dedup": 0, "dropped_by_f2": 1, "final": 4}
    assert p["dedup"]["removed"] == [] and p["f2"]["dropped"] == [{"doc_id": "g0", "items": ["fake:1"], "offset": 0}]
    assert p["f2"]["set_sha256"] == "2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a"


def test_a_heldout_part_is_described_not_refused(run):
    p = load(run, "heldout", "code-go/part-00000.parquet")  # what to do with held-out is the shard writer's decision
    assert p["part"]["split"] == "heldout" and p["counts"] == {"cleaned": 2, "removed_by_dedup": 0, "dropped_by_f2": 1, "final": 1}


def test_the_result_has_ids_counts_and_hashes_only(run):
    for (split, part) in PARTS:
        assert "synthetic text" not in json.dumps(load(run, split, part))


def test_the_command_line_prints_the_result(run, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["provenance.py", "--input", str(run / "final/train/en-dclm/part-00000.parquet"),
                                      "--manifest", str(run / "pipeline_manifest.json")])
    provenance.main()
    assert json.loads(capsys.readouterr().out)["dedup"]["removed"][0]["doc_id"] == "e2"


def test_a_part_changed_after_f2_stops(run):
    part = run / "final/train/en-dclm/part-00000.parquet"
    pq.write_table(pq.read_table(part).slice(0, 1), part)
    with pytest.raises(provenance.Stop, match="changed after F2"):
        load(run, "train", "en-dclm/part-00000.parquet")


def test_another_fingerprint_set_than_the_manifests_stops(run):
    edit_json(run / "final/train/code-go/part-00000.parquet.f2.json", set_sha256="f" * 64)
    with pytest.raises(provenance.Stop, match="fingerprint set"):
        load(run, "train", "code-go/part-00000.parquet")


def test_f2_errors_on_the_part_stop(run):
    edit_json(run / "final/train/code-go/part-00000.parquet.f2.json", errors=[["g1", "ValueError"]])
    with pytest.raises(provenance.Stop, match="error"):
        load(run, "train", "code-go/part-00000.parquet")


def test_f2_that_read_another_file_than_apply_wrote_stops(run):
    edit_json(run / "final/train/code-go/part-00000.parquet.f2.json", input_sha256="0" * 64)
    with pytest.raises(provenance.Stop, match="F2 read a part with sha256"):
        load(run, "train", "code-go/part-00000.parquet")


def test_a_remove_list_changed_after_apply_stops(run, tmp_path):
    with (tmp_path / "dedup" / "remove_list.csv").open("a", encoding="utf-8") as f:
        f.write("en-dclm,train,en-dclm/part-00000.parquet,1,e1\n")
    with pytest.raises(provenance.Stop, match="changed after apply used it"):
        load(run, "train", "code-go/part-00001.parquet")


def test_a_removed_doc_without_a_group_stops(run, tmp_path):
    groups = tmp_path / "dedup" / "dedup_groups.csv"
    groups.write_text("".join(l for l in groups.read_text(encoding="utf-8").splitlines(True) if ",removed,code-go" not in l),
                      encoding="utf-8")
    with pytest.raises(provenance.Stop, match="no removed member"):
        load(run, "train", "code-go/part-00001.parquet")


def test_a_clean_folder_without_job_summary_stops(run, tmp_path):
    (tmp_path / "cleaned" / "job_summary.json").unlink()
    with pytest.raises(provenance.Stop, match="no job_summary.json"):
        load(run, "train", "code-go/part-00000.parquet")


def test_a_cleaned_part_that_is_not_what_clean_wrote_stops(run, tmp_path):
    job = tmp_path / "cleaned" / "job_summary.json"
    data = json.loads(job.read_text(encoding="utf-8"))
    data["parts"][0]["output_sha256"] = "0" * 64
    job.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(provenance.Stop, match="the clean job wrote"):
        load(run, "train", "code-go/part-00000.parquet")


def test_a_pack_id_column_that_is_not_the_packs_stops(run):
    part = run / "final/train/en-dclm/part-00000.parquet"
    t = pq.read_table(part)
    t = t.set_column(t.schema.get_field_index("pack_id"), "pack_id", pa.array(["code-go"] * t.num_rows))
    pq.write_table(t, part)
    edit_json(part.with_name(part.name + ".f2.json"), output_sha256=sha(part))  # so only the pack_id is wrong
    with pytest.raises(provenance.Stop, match="pack_id column"):
        load(run, "train", "en-dclm/part-00000.parquet")


def test_a_file_outside_the_runs_final_folder_stops(run, tmp_path):
    elsewhere = tmp_path / "elsewhere" / "train" / "code-go" / "part-00000.parquet"
    elsewhere.parent.mkdir(parents=True)
    shutil.copy(run / "final/train/code-go/part-00000.parquet", elsewhere)
    with pytest.raises(provenance.Stop, match="not under"):
        provenance.load(elsewhere, run / "pipeline_manifest.json")


def test_a_folder_that_is_not_train_or_heldout_stops(run):
    odd = run / "final" / "test" / "code-go" / "part-00000.parquet"
    odd.parent.mkdir(parents=True)
    shutil.copy(run / "final/train/code-go/part-00000.parquet", odd)
    with pytest.raises(provenance.Stop, match="train or heldout"):
        provenance.load(odd, run / "pipeline_manifest.json")


def test_a_manifest_without_f2_stops(run):
    m = run / "pipeline_manifest.json"
    data = json.loads(m.read_text(encoding="utf-8"))
    data["stages"] = [s for s in data["stages"] if s["stage"] != "f2"]
    m.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(provenance.Stop, match="no record of stage.*f2"):
        load(run, "train", "code-go/part-00000.parquet")


def test_a_manifest_with_a_failed_check_stops(run):
    m = run / "pipeline_manifest.json"
    data = json.loads(m.read_text(encoding="utf-8"))
    data["checks"][0]["ok"] = False
    m.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(provenance.Stop, match="failed check"):
        load(run, "train", "code-go/part-00000.parquet")


def f2_set(run):
    return next(s for s in json.loads((run / "pipeline_manifest.json").read_text(encoding="utf-8"))["stages"] if s["stage"] == "f2")["set_sha256"]


def test_the_processing_record_names_clean_f2_and_the_dedup_run(run):
    m = run / "pipeline_manifest.json"
    root = run.parent.parent
    record = provenance.processing_record(m)
    assert record == {"clean_py_sha256": CLEAN_SHA, "f2_set_sha256": f2_set(run), "dedup": {
        "remove_list_sha256": sha(root / "dedup" / "remove_list.csv"), "remove_list_rows": 2,
        "overlap": {"matches_sha256": sha(root / "overlap" / "overlap_matches.csv"), "docs_sha256": sha(root / "overlap" / "overlap_docs.parquet"),
                    "k": 5, "floor": 0.5, "code_sha256": None},
        "settings": {"cross_pack": True, "pack_order": ["code-go", "en-dclm"], "licence_usable": {}, "default_licence_usable": True},
        "code_sha256": None}}
    assert "gold_dirs" not in json.dumps(record) and "made up" not in json.dumps(record)  # no paths
    assert load(run, "train", "code-go/part-00001.parquet")["record"] == record


def test_the_code_sha256_of_overlap_and_dedup_come_from_the_manifest_when_they_ran(run):
    m = run / "pipeline_manifest.json"
    data = json.loads(m.read_text(encoding="utf-8"))
    for s in data["stages"]:
        if s["stage"] in ("overlap", "dedup"):
            s["code_sha256"] = ("o" if s["stage"] == "overlap" else "d") * 64
    m.write_text(json.dumps(data), encoding="utf-8")
    record = provenance.processing_record(m)
    assert record["dedup"]["code_sha256"] == "d" * 64 and record["dedup"]["overlap"]["code_sha256"] == "o" * 64


@pytest.mark.parametrize("where, change, message", [
    ("dedup", lambda d: d.pop("config"), "dedup_summary.json config has no cross_pack, pack_order"),
    ("dedup", lambda d: d["config"].pop("pack_order"), "has no pack_order"),
    ("dedup", lambda d: d["overlap_run"].pop("checked_sha256"), "checked_sha256 has no overlap_matches.csv"),
    ("overlap", lambda d: d.pop("config"), "overlap_summary.json config has no k, floor"),
    ("overlap", lambda d: d["config"].pop("floor"), "has no floor"),
])
def test_no_record_when_a_summary_lacks_what_the_shard_records(run, where, change, message):
    f = run.parent.parent / where / f"{where}_summary.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    change(data)
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(provenance.Stop, match=message):
        provenance.processing_record(run / "pipeline_manifest.json")


def test_write_record_writes_the_file_next_to_the_manifest(run):
    path, record = provenance.write_record(run / "pipeline_manifest.json")
    assert path == run / "cleaning_pipeline.json" and json.loads(path.read_text(encoding="utf-8")) == record
    assert path.read_bytes().endswith(b"}\n") and b"\r" not in path.read_bytes()
    assert "manifest" not in path.read_text(encoding="utf-8")  # no link to the run log


def test_the_command_line_writes_the_record(run, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["provenance.py", "--manifest", str(run / "pipeline_manifest.json"), "--write-record"])
    provenance.main()
    assert (run / "cleaning_pipeline.json").is_file() and "wrote" in capsys.readouterr().out


def test_no_record_without_the_clean_jobs_summary(run):
    (run.parent.parent / "cleaned" / "job_summary.json").unlink()
    with pytest.raises(provenance.Stop, match="no job_summary.json"):
        provenance.processing_record(run / "pipeline_manifest.json")


def test_no_record_when_the_remove_list_changed_after_apply(run):
    with open(run.parent.parent / "dedup" / "remove_list.csv", "a", encoding="utf-8") as f:
        f.write("code-go,train,code-go/part-00000.parquet,1,x\n")
    with pytest.raises(provenance.Stop, match="changed after apply used it"):
        provenance.processing_record(run / "pipeline_manifest.json")


def test_the_record_follows_the_output_the_manifest_recorded_for_a_stage(run):
    """A config may leave a stage's output to the default, so the config has no `output`: the stage's record names it."""
    m = run / "pipeline_manifest.json"
    data = json.loads(m.read_text(encoding="utf-8"))
    expected = provenance.processing_record(m)
    for stage in ("clean", "overlap", "dedup"):
        del data["config"]["stages"][stage]["output"]
    m.write_text(json.dumps(data), encoding="utf-8")
    assert provenance.processing_record(m) == expected
