"""Tests for run_ocr2.py (G10): row identity through every stage, completion markers, resume, worker order.

    G10_DECONTAM_TOOLS=<lab main>/teams/09-evaluation/decontam pytest teams/10-post-training/sft/test_ocr2_resume.py -q

No network. Rows are synthetic placeholders from ocr2_fixtures.py and a toy fingerprint set: tests only.
The real convert.py and decontam_run.py run as subprocesses, exactly as in a shard run.
"""

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import convert as g10  # noqa: E402
import run_ocr2  # noqa: E402
import source_index as si  # noqa: E402
from ocr2_fixtures import (CANARY, DEFAULT_SOURCES, SET_ID, World, allow_everything, ocr_row, read_jsonl, statement,  # noqa: E402
                           toy_fingerprints, toy_tokenizer)

# Named decorators: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize
module_fixture = pytest.fixture(scope="module")

LONG_TRACE = "<think>" + "z9 " * 60000 + "</think>\n\nfixture reply"  # far over the 64k trace budget of the toy tokenizer
SHARD = [ocr_row(0, "apps", "test", "0"),                                   # join exclusion
         ocr_row(1, "taco", "train", "0", r1_generation="no think block"),  # converter skip (broken trace)
         ocr_row(2, "code_contests", "train", "0"),                         # removed by the scan
         ocr_row(3, "taco", "train", "3"),                                  # kept
         ocr_row(4, "taco", "train", "1", r1_generation=LONG_TRACE),        # converter skip (oversized trace)
         ocr_row(5, "taco", "train", "4")]                                  # kept
OTHER = [ocr_row(10, "apps", "train", "0"), ocr_row(11, "taco", "test", "0"), ocr_row(12, "apps", "train", "1")]


@module_fixture
def kit(tmp_path_factory):
    root = tmp_path_factory.mktemp("kit")
    return {"tokenizer": (root / "tokenizer.json", toy_tokenizer(root / "tokenizer.json")), "toy": toy_fingerprints(root / "fp")}


def make_world(root, kit, shards=None, **kwargs):
    kwargs.setdefault("n_shards", 2)
    return World(root, shards or {0: OTHER, 1: SHARD}, **kit, **kwargs)


def run(world, out, shards="0:2", workers=1, **kwargs):
    return run_ocr2.run(world.manifest_path, world.policy_path, shards, workers, out, **kwargs)


def shard_info(coverage, shard_id):
    return next(s for s in coverage["shards"] if s["shard_id"] == shard_id)


@module_fixture
def reference(tmp_path_factory, kit):
    root = tmp_path_factory.mktemp("reference")
    world = make_world(root / "w", kit)
    return world, run(world, root / "run"), root / "run"


def test_exclusion_then_converter_skip_then_scan_removal_keeps_row_identity(reference):
    world, coverage, out = reference
    info = shard_info(coverage, 1)
    counts = info["counts"]
    assert info["state"] == "complete" and info["not_reconciled"] == []
    assert (counts["joined"]["raw_rows"], counts["joined"]["policy_excluded"], counts["joined"]["eligible_joined"]) == (6, 1, 5)
    assert counts["rendered"]["skipped"] == {"generation does not start with one <think>...</think> block": 1,
                                             "trace over the 64k effort budget": 1}
    assert (counts["rendered"]["converter_rejected"], counts["rendered"]["rendered"]) == (2, 3)
    scan = counts["screened"]
    assert (scan["rows_in"], scan["rows_flagged"], scan["rows_canary"], scan["rows_kept"]) == (3, 1, 0, 2)
    assert scan["scan"] == "full_set" and scan["set_sha256"] == world.toy_sha and scan["by_benchmark"] == {"toy": 1}
    assert counts["rechecked"]["recheck"] == "second_full_pass_zero_hits" and counts["rechecked"]["retained"] == 2
    shard = out / "shards" / "shard-00001"
    base = 3  # shard 0 has 3 original rows; ids of shard 1 start there whatever shard 0 kept
    assert [r["id"] for r in read_jsonl(shard / "rendered" / "rendered.jsonl")] == [f"{SET_ID}/{base + n}" for n in (1, 2, 4)]
    kept = read_jsonl(shard / "screen" / f"{SET_ID}.clean.jsonl")
    side = read_jsonl(shard / "recheck" / "retained.sidecar.jsonl")
    assert [r["id"] for r in kept] == [s["rendered_id"] for s in side] == [f"{SET_ID}/{base + 2}", f"{SET_ID}/{base + 4}"]
    # Two holes before them (one join exclusion, converter skips, one scan removal): still the right original rows.
    assert [s["ocr_row_key"][2] for s in side] == [3, 5] and [s["ocr_id"] for s in side] == ["fx0003", "fx0005"]
    assert [s["source_row_key"][2:] for s in side] == [["taco", "train", 3], ["taco", "train", 4]]
    assert [r["source_id"] for r in kept] == ["fx0003", "fx0005"]
    assert statement("T3") in kept[0]["text"] and statement("T4") in kept[1]["text"] and "fixture reply 5" in kept[1]["text"]
    removed = json.loads((shard / "screen" / f"{SET_ID}.record.json").read_text())["flagged"]
    assert list(removed) == [f"{SET_ID}/{base + 1}"]  # the code_contests row, OCR row 2


def test_coverage_accounts_for_every_shard_and_claims_nothing_more(reference, tmp_path, kit):
    _, coverage, out = reference
    assert coverage["accounting"] == {"expected_shards": 2, "requested": 2, "not_requested": 0, "complete_full_shard": 2,
                                      "complete_row_prefix_only": 0, "not_available_locally": 0, "stopped_canary": 0, "failed": 0}
    assert coverage["full_dataset"] is True and coverage["test_fixture"] is True
    totals = coverage["totals_over_complete_shards"]
    assert totals["joined.raw_rows"] == 9 == totals["joined.policy_excluded"] + totals["joined.malformed_or_unresolved"] + totals["joined.eligible_joined"]
    assert totals["joined.eligible_joined"] == totals["rendered.converter_rejected"] + totals["rendered.rendered"]
    assert totals["rendered.rendered"] == totals["screened.rows_removed"] + totals["screened.rows_kept"]
    assert totals["screened.rows_kept"] == totals["pack.attempted"] == totals["pack.pack_rejected"] + totals["pack.row_checks_passed"]
    assert totals["pack.admitted"] == 0 == totals["pack.emitted"]  # a diagnostic run admits nothing
    assert json.loads((out / "coverage.json").read_text()) == coverage
    world = make_world(tmp_path / "w", kit, shards={0: OTHER}, n_shards=4)
    partial = run(world, tmp_path / "run", shards="0:3")
    assert partial["accounting"] == {"expected_shards": 4, "requested": 3, "not_requested": 1, "complete_full_shard": 1,
                                     "complete_row_prefix_only": 0, "not_available_locally": 2, "stopped_canary": 0, "failed": 0}
    assert partial["full_dataset"] is False
    assert [s["state"] for s in partial["shards"]] == ["complete", "not_available_locally", "not_available_locally"]
    assert not (tmp_path / "run" / "shards" / "shard-00001").exists()


def test_a_second_run_reuses_every_verified_stage(reference):
    world, coverage, out = reference
    again = run(world, out, resume=True)
    assert again == coverage
    execs = json.loads((out / "coverage.exec.json").read_text())
    assert execs["indexed"]["resumed"] is True
    assert all(stage["resumed"] for shard in execs["shards"].values() for stage in shard.values())
    assert not (out / "shards" / "shard-00001" / "quarantine").exists()
    with pytest.raises(run_ocr2.RunError, match="pass --resume"):
        run(world, out)


def test_shards_with_nothing_to_join_or_render_get_no_scan_credit_and_are_not_retried(tmp_path, kit):
    only_test_rows = [ocr_row(0, "apps", "test", "0"), ocr_row(1, "taco", "test", "1")]
    only_broken = [ocr_row(2, "taco", "train", "0", r1_generation="no think block"),
                   ocr_row(3, "taco", "train", "1", r1_generation=LONG_TRACE)]
    world = make_world(tmp_path / "w", kit, shards={0: only_test_rows, 1: only_broken})
    coverage = run(world, tmp_path / "run")
    for shard_id, eligible in ((0, 0), (1, 2)):
        info = shard_info(coverage, shard_id)
        counts = info["counts"]
        assert info["state"] == "complete" and info["final_state"] == "pack_report"
        assert counts["joined"]["eligible_joined"] == eligible and counts["rendered"]["rendered"] == 0
        assert counts["screened"]["scan"] == "not_run" and counts["screened"]["scan_credit"] is False
        assert counts["rechecked"]["recheck"] == "not_run" and counts["pack"]["attempted"] == 0
        assert "scan_record_missing" in counts["pack"]["blockers"]
        screen = tmp_path / "run" / "shards" / f"shard-{shard_id:05d}" / "screen"
        assert [p.name for p in screen.iterdir()] == ["scan.json"]  # no record: an absent scan is not "zero canaries"
    assert shard_info(coverage, 0)["counts"]["joined"]["policy_excluded"] == 2
    assert shard_info(coverage, 1)["counts"]["rendered"]["converter_rejected"] == 2
    assert run(world, tmp_path / "run", resume=True) == coverage
    execs = json.loads((tmp_path / "run" / "coverage.exec.json").read_text())
    assert all(stage["resumed"] for shard in execs["shards"].values() for stage in shard.values())


@parametrize("stage", run_ocr2.STAGES)
@parametrize("point", run_ocr2.FAULT_POINTS)
def test_killed_at_any_stage_then_rerun_twice_gives_the_same_result(reference, tmp_path, stage, point):
    world, coverage, _ = reference
    out = tmp_path / "run"
    with pytest.raises(run_ocr2.Fault):
        run(world, out, fault=(stage, point))
    shard = out / "shards" / "shard-00000"  # the first shard is the one that was stopped
    folder = run_ocr2.STAGE_DIR[stage]
    assert not (shard / "state" / f"{stage}.complete.json").exists()  # no marker: the stage does not count
    assert (shard / (folder + ".tmp")).is_dir() if point == "before_publish" else (shard / folder).is_dir()
    assert not (out / "coverage.json").exists()
    first = run(world, out, resume=True)
    second = run(world, out, resume=True)
    assert first == second == coverage  # same counts and the same deterministic hashes as a run that was never stopped
    pen = sorted(p.name for p in (shard / "quarantine").iterdir())
    assert pen == [f"{folder}.tmp.0" if point == "before_publish" else f"{folder}.0"]  # the partial unit is set aside, once
    done_before = run_ocr2.STAGES[:run_ocr2.STAGES.index(stage)]
    execs = json.loads((out / "coverage.exec.json").read_text())
    assert all(execs["shards"]["0"][s]["resumed"] for s in run_ocr2.STAGES)  # second rerun: nothing ran again
    for done in done_before:  # stages finished before the stop were never redone
        marker = json.loads((shard / "state" / f"{done}.complete.json").read_text())
        assert marker["exec"]["quarantined"] == []
    ids = [r["id"] for s in ("shard-00000", "shard-00001") for r in read_jsonl(out / "shards" / s / "screen" / f"{SET_ID}.clean.jsonl")]
    assert len(ids) == len(set(ids)) == coverage["totals_over_complete_shards"]["screened.rows_kept"]


def test_worker_count_and_order_do_not_change_ids_or_hashes(reference, tmp_path):
    world, coverage, _ = reference
    parallel = run(world, tmp_path / "run", workers=2)
    assert parallel == coverage and parallel["deterministic_sha256"] == coverage["deterministic_sha256"]
    for shard_id in (0, 1):
        assert shard_info(parallel, shard_id)["stage_sha256"] == shard_info(coverage, shard_id)["stage_sha256"]


def test_a_damaged_output_is_quarantined_and_only_that_stage_reruns(tmp_path, kit):
    world = make_world(tmp_path / "w", kit)
    out = tmp_path / "run"
    coverage = run(world, out)
    shard = out / "shards" / "shard-00001"
    rendered = shard / "rendered" / "rendered.jsonl"
    rendered.write_bytes(rendered.read_bytes()[:-20])  # a truncated file under a completed marker
    assert run(world, out, resume=True) == coverage
    execs = json.loads((out / "coverage.exec.json").read_text())["shards"]["1"]
    assert {stage: info["resumed"] for stage, info in execs.items()} == {
        "joined": True, "rendered": False, "screened": True, "rechecked": True, "pack": True}  # same bytes again: descendants stand
    assert sorted(p.name for p in (shard / "quarantine").iterdir()) == ["rendered.0", "rendered.complete.json.0"]


def test_a_changed_policy_invalidates_every_stage(tmp_path, kit):
    world = make_world(tmp_path / "w", kit)
    out = tmp_path / "run"
    before = run(world, out)
    world.policy["target_quality"]["missing_execution_evidence"] = "exclude"
    world.write()
    after = run(world, out, resume=True)
    assert after["run_id"] != before["run_id"] and after["config_sha256"] != before["config_sha256"]
    assert json.loads((out / "run.json").read_text())["history"] == [before["run_id"]]
    execs = json.loads((out / "coverage.exec.json").read_text())["shards"]
    assert not any(stage["resumed"] for shard in execs.values() for stage in shard.values())
    assert shard_info(after, 1)["counts"]["screened"]["rows_kept"] == 2  # same rows: only the tuple changed


def test_a_changed_shard_input_invalidates_the_run_of_that_shard(tmp_path, kit):
    world = make_world(tmp_path / "w", kit)
    out = tmp_path / "run"
    run(world, out)
    world2 = make_world(tmp_path / "w", kit, shards={0: OTHER, 1: SHARD[:4]})  # same folder: shard 1 has other bytes now
    after = run(world2, out, resume=True)
    assert shard_info(after, 1)["counts"]["joined"]["raw_rows"] == 4 and shard_info(after, 1)["counts"]["screened"]["rows_kept"] == 1
    execs = json.loads((out / "coverage.exec.json").read_text())["shards"]
    assert not any(stage["resumed"] for shard in execs.values() for stage in shard.values())  # the manifest pins the input


def test_a_diagnostic_folder_never_resumes_into_admission(tmp_path, kit, monkeypatch):
    world = make_world(tmp_path / "w", kit)
    run(world, tmp_path / "run")
    row = dict(g10.licence_row(SET_ID), decision="allowed")
    monkeypatch.setattr(g10, "licence_row", lambda set_id, table=None: row)
    allow_everything(world)
    with pytest.raises(run_ocr2.RunError, match="never resumes into admission"):
        run(world, tmp_path / "run", resume=True, mode="admission")
    monkeypatch.undo()
    with pytest.raises(run_ocr2.join.Refusal):  # and with the real table an admission run does not start at all
        run(world, tmp_path / "other", mode="admission")
    assert not (tmp_path / "other").exists()


def test_a_canary_stops_the_shard_and_leaves_an_incident_without_text(tmp_path, kit):
    sources = dict(DEFAULT_SOURCES)
    sources["apps/train"] = [("apps-train-a", ["FIXTURE statement with a leaked marker " + CANARY + " inside.", statement("A1")])]
    world = make_world(tmp_path / "w", kit, sources=sources)
    coverage = run(world, tmp_path / "run")
    info = shard_info(coverage, 0)
    assert info["state"] == "stopped_canary" and info["stages_complete"] == ["joined", "rendered"]
    assert coverage["accounting"]["stopped_canary"] == 1 and shard_info(coverage, 1)["state"] == "complete"
    incident = Path(info["incident"])
    text = incident.read_text()
    assert CANARY not in text and json.loads(text)["hits"][0]["doc_id"] == f"{SET_ID}/0"
    assert not (tmp_path / "run" / "shards" / "shard-00000" / "state" / "screened.complete.json").exists()
    assert run_ocr2.main(["--manifest", str(world.manifest_path), "--policy", str(world.policy_path), "--shards", "0:2",
                          "--out-dir", str(tmp_path / "run"), "--resume"]) == 1


def test_unset_paths_and_hashes_stop_the_run(tmp_path, kit):
    world = make_world(tmp_path / "w", kit)

    def broken(change, match):
        manifest = world.manifest()
        change(manifest)
        world.manifest_path.write_text(json.dumps(manifest))
        with pytest.raises(run_ocr2.RunError, match=match):
            run(world, tmp_path / "run")
        assert not (tmp_path / "run").exists()

    broken(lambda m: m["conversion"].pop("tokenizer"), "tokenizer")
    broken(lambda m: m["conversion"]["tokenizer"].update(sha256="0" * 64), "pinned tokenizer")
    broken(lambda m: m["screening"].pop("set_sha256"), "empty expected hash is never used")
    broken(lambda m: m["screening"].pop("tools_dir"), "tools_dir")
    broken(lambda m: m.pop("test_fixture"), "for test fixtures")  # a real run may not point at another fingerprint set
    broken(lambda m: (m.pop("test_fixture"), m["screening"].pop("fingerprints_test_only"),
                      m["screening"].update(set_sha256="1" * 64)), "not an approved fingerprint set")
    with pytest.raises(run_ocr2.RunError, match="outside the 2 shards"):
        world.write()
        run(world, tmp_path / "run", shards="0:3")


def test_a_real_run_cannot_use_fault_injection(tmp_path, kit):
    world = make_world(tmp_path / "w", kit)
    manifest = world.manifest()
    manifest.pop("test_fixture")
    manifest["screening"].pop("fingerprints_test_only")
    world.policy["pack"]["approved_fingerprint_set_sha256"] = [world.toy_sha]
    world.policy_path.write_text(json.dumps(world.policy))
    world.manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(run_ocr2.RunError, match="test fixtures only"):
        run(world, tmp_path / "run", fault=("joined", "before_marker"))


def test_markers_record_the_tuple_and_keep_run_times_out_of_the_hash(reference):
    world, coverage, out = reference
    marker = json.loads((out / "shards" / "shard-00001" / "state" / "screened.complete.json").read_text())
    assert marker["state"] == "screened" and marker["mode"] == "diagnostic" and marker["test_fixture"] is True
    assert marker["config_sha256"] == coverage["config_sha256"] and marker["run_id"] == coverage["run_id"]
    assert set(marker["outputs"]) == {"scan.json", f"{SET_ID}.clean.jsonl", f"{SET_ID}.record.json"}
    stable = {k: v for k, v in marker["outputs"].items() if k != f"{SET_ID}.record.json"}  # the record carries run_at
    assert marker["deterministic_sha256"] == si.sha256_json({
        "stage": "screened", "shard_id": 1, "mode": "diagnostic", "config_sha256": marker["config_sha256"],
        "outputs": stable, "counts": marker["counts"]})
    config = json.loads((out / "run.json").read_text())["config"]
    assert config["tokenizer_sha256"] == world.tokenizer_sha and config["fingerprint_set_sha256"] == world.toy_sha
    assert set(config["code_sha256"]) == set(run_ocr2.CODE_FILES) and config["policy_sha256"] == si.sha256_file(world.policy_path)
