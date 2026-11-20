"""Tests for run_pipeline.py: the whole chain on synthetic data, with clean, overlap and dedup adopted (as when TSAI ran
them) and apply, F2 (a stand-in, fake_run_f2.py), survivor_loss and the ledger run by the runner.

  python -m pytest teams/01-data-a/pipeline/tests -q
"""
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from conftest import HEADER, PARTS, PIPELINE, made_up_manifest
import run_pipeline as rp

FAKE_F2 = Path(__file__).resolve().parent / "fake_run_f2.py"
FAKE_SHARDS = Path(__file__).resolve().parent / "fake_run_shards.py"
FAKE_STAGE = Path(__file__).resolve().parent / "fake_stage.py"
GROUP_HEADER = ["group_id", "group_size", "priority_rule", "role", "pack_id", "split", "part", "row_in_part", "doc_id"]


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def overlap_folder(folder, cleaned_parts=PARTS, docs_all=13):
    """What overlap.py returns, shaped like its real summary (status, documents_all, inputs.parts, outputs)."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "overlap_matches.csv").write_text("row_a,row_b\n0,1\n", encoding="utf-8")
    (folder / "overlap_docs.parquet").write_bytes(b"stand-in for overlap_docs.parquet")
    summary = {"status": "complete", "documents_all": docs_all, "config": {"k": 5, "floor": 0.5, "inputs": "made up"},
               "inputs": {"parts": [{"part": f"{s}/{p}", "documents": len(rows),
                                      "sha256": sha(folder.parent / "cleaned" / s / p)
                                      if (folder.parent / "cleaned" / s / p).is_file() else "0" * 64}
                                     for (s, p), rows in cleaned_parts.items()]},
               "outputs": {n: {"sha256": sha(folder / n)} for n in ("overlap_matches.csv", "overlap_docs.parquet")}}
    (folder / "overlap_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return folder


def dedup_folder(folder, overlap, removed=2, heldout_removed=0):
    """What dedup.py returns: G-numbered groups, integer rules, and the overlap files it checked."""
    write_csv(folder / "remove_list.csv", HEADER, [["code-go", "train", "code-go/part-00001.parquet", 0, "g0"],
                                                   ["en-dclm", "train", "en-dclm/part-00000.parquet", 2, "e2"]])
    write_csv(folder / "dedup_groups.csv", GROUP_HEADER, [
        ["G000001", 2, 4, "survivor", "code-go", "train", "code-go/part-00000.parquet", 0, "g0"],
        ["G000001", 2, 4, "removed", "code-go", "train", "code-go/part-00001.parquet", 0, "g0"],
        ["G000002", 3, 0, "survivor", "code-go", "heldout", "code-go/part-00000.parquet", 0, "h0"],
        ["G000002", 3, 0, "survivor", "code-go", "heldout", "code-go/part-00000.parquet", 1, "h1"],
        ["G000002", 3, 0, "removed", "en-dclm", "train", "en-dclm/part-00000.parquet", 2, "e2"]])
    log = [{"removed_pack_id": "code-go", "removed_split": "train", "removed_part": "code-go/part-00001.parquet",
            "removed_row_in_part": 0, "removed_id": "g0", "kept_pack_id": "code-go", "kept_split": "train",
            "kept_part": "code-go/part-00000.parquet", "kept_row_in_part": 0, "kept_id": "g0", "rule": "H1",
            "similarity": 1.0, "priority_rule": 4, "stage": "within_pack", "direct": True},
           {"removed_pack_id": "en-dclm", "removed_split": "train", "removed_part": "en-dclm/part-00000.parquet",
            "removed_row_in_part": 2, "removed_id": "e2", "kept_pack_id": "code-go", "kept_split": "heldout",
            "kept_part": "code-go/part-00000.parquet", "kept_row_in_part": 0, "kept_id": "h0", "rule": "H2",
            "similarity": 0.91, "priority_rule": 0, "stage": "cross_pack", "direct": True}]
    (folder / "dedup_log.jsonl").write_text("".join(json.dumps(e) + "\n" for e in log), encoding="utf-8")
    checked = {n: sha(overlap / n) for n in ("overlap_matches.csv", "overlap_docs.parquet")}
    (folder / "dedup_summary.json").write_text(json.dumps({
        "status": "complete", "overlap_run": {"documents_all": 13, "checked_sha256": checked}, "documents_all": 13,
        "removed": removed, "heldout_removed": heldout_removed,
        "clusters": 2, "groups_without_survivor": 0, "groups_with_several_survivors": 1,
        "config": {"cross_pack": True, "pack_order": ["code-go", "en-dclm"], "licence_usable": {}, "default_licence_usable": True,
                   "gold_dirs": []}}), encoding="utf-8")
    return folder


@pytest.fixture
def tsai_outputs(tmp_path, cleaned):
    overlap = overlap_folder(tmp_path / "overlap")
    return {"cleaned": cleaned, "overlap": overlap, "dedup": dedup_folder(tmp_path / "dedup", overlap)}


def write_config(path, outs, run_id="test-run", **extra):
    cfg = {"run_id": run_id, "out": str(path.parent / "runs"),
           "stages": {"clean": {"mode": "adopt", "output": str(outs["cleaned"])},
                      "overlap": {"mode": "adopt", "output": str(outs["overlap"])},
                      "dedup": {"mode": "adopt", "output": str(outs["dedup"])},
                      "f2": {"script": str(FAKE_F2)}}}
    cfg["stages"].update(extra)
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


@pytest.fixture
def config(tmp_path, tsai_outputs, monkeypatch):
    for k in ("FAKE_F2_ERROR", "FAKE_F2_BAD_SHA", "FAKE_F2_CRASH"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("FAKE_F2_DROP", "g0,h1")
    return write_config(tmp_path / "pipeline.json", tsai_outputs)


def final_ids(run):
    return sorted(d for f in (run / "final").rglob("*.parquet") for d in pq.read_table(f).column("doc_id").to_pylist())


def test_full_chain(tmp_path, config):
    m = rp.run(config)
    run = tmp_path / "runs" / "test-run"
    assert [s["stage"] for s in m["stages"]] == [s for s in rp.STAGES if s not in rp.OPTIONAL]
    c = {s["stage"]: s["counts"] for s in m["stages"]}
    assert c["clean"]["rows"] == 13 and c["overlap"]["documents_all"] == 13 and c["dedup"]["remove_list_rows"] == 2
    assert (c["apply"]["rows"], c["apply"]["removed"], c["apply"]["kept"]) == (13, 2, 11)
    assert (c["f2"]["rows"], c["f2"]["dropped_by_f2"], c["f2"]["kept"]) == (11, 2, 9)
    assert c["f2"]["by_split"]["heldout"] == {"rows": 2, "kept": 1, "dropped_by_f2": 1, "errors": 0}
    assert c["survivor_loss"]["lost"] == 1 and c["survivor_loss"]["partly_hit"] == 1
    assert m["totals"] == {"cleaned": 13, "removed_by_dedup": 2, "dropped_by_f2": 2, "final": 9}
    assert c["ledger"] == {"rows": 13, "rows_cleaned": 13, "kept": 9, "dropped_by_clean": 0, "removed_by_dedup": 2,
                           "dropped_by_f2": 2, "f2_error": 0}
    assert m["by_pack"] == {
        "code-go": {"train": {"cleaned": 8, "removed_by_dedup": 1, "dropped_by_f2": 1, "final": 6},
                    "heldout": {"cleaned": 2, "removed_by_dedup": 0, "dropped_by_f2": 1, "final": 1}},
        "en-dclm": {"train": {"cleaned": 3, "removed_by_dedup": 1, "dropped_by_f2": 0, "final": 2}}}
    assert {"ledger per pack = apply per pack", "every per-pack row adds up",
            "per-pack table adds up to the stages' counts"} <= {ch["check"] for ch in m["checks"]}
    assert rp.pack_table({}) == "" and rp.pack_table({"p": {}}) == ""
    assert sorted(p.relative_to(run / "ledger").as_posix() for p in (run / "ledger").rglob("*.parquet")) == [
        "heldout/code-go.parquet", "train/code-go.parquet", "train/en-dclm.parquet"]
    names = {ch["check"] for ch in m["checks"]}
    assert {"overlap read these cleaned parts", "dedup used this overlap run", "F2 read what apply wrote in train",
            "survivor loss saw every dedup group", "survivor loss's groups without a survivor = dedup's",
            "survivor loss's groups with several survivors = dedup's", "ledger kept = F2's kept",
            "ledger's survivors dropped by F2 = survivor loss's",
            "ledger's survivors dropped by F2 per pack = survivor loss's"} <= names and all(ch["ok"] for ch in m["checks"])
    assert final_ids(run) == sorted(["g1", "g2", "g3", "g4", "g5", "g6", "e0", "e1", "h0"])
    assert (run / "logs" / "f2_train.log").is_file()
    on_disk = json.loads((run / "pipeline_manifest.json").read_text(encoding="utf-8"))
    assert on_disk["totals"] == m["totals"] and "synthetic text" not in json.dumps(on_disk)


def test_h3_match_file_is_linked_to_this_run_and_dedup(tmp_path, config, tsai_outputs, monkeypatch):
    out = tmp_path / "h3"
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["stages"]["h3"] = {"mode": "run", "command": [str(FAKE_STAGE)], "output": str(out)}
    config.write_text(json.dumps(cfg), encoding="utf-8")
    original = rp.run_script

    def h3_stage(script, args, stage, log, **kwargs):
        if stage != "h3":
            return original(script, args, stage, log, **kwargs)
        out.mkdir()
        write_csv(out / "h3_matches.csv", ["pack_id_a", "split_a", "part_a", "row_in_part_a", "doc_id_a",
                                            "pack_id_b", "split_b", "part_b", "row_in_part_b", "doc_id_b",
                                            "lang_a", "lang_b", "coverage"], [])
        (out / "h3_summary.json").write_text(json.dumps({
            "status": "complete", "inputs": {"root": str(tsai_outputs["cleaned"])}, "qualifying": 0,
            "outputs": {"h3_matches.csv": {"sha256": sha(out / "h3_matches.csv")}}}), encoding="utf-8")
        return 0

    monkeypatch.setattr(rp, "run_script", h3_stage)
    summary = tsai_outputs["dedup"] / "dedup_summary.json"
    d = json.loads(summary.read_text(encoding="utf-8"))
    # The fake H3 command writes an empty match file, whose digest is fixed by its header.
    header = "pack_id_a,split_a,part_a,row_in_part_a,doc_id_a,pack_id_b,split_b,part_b,row_in_part_b,doc_id_b,lang_a,lang_b,coverage\r\n"
    d["h3"] = {"matches": {"sha256": hashlib.sha256(header.encode()).hexdigest(), "pairs": 0}, "remove": False}
    summary.write_text(json.dumps(d), encoding="utf-8")
    m = rp.run(config, to="dedup")
    assert [s["stage"] for s in m["stages"]] == ["clean", "overlap", "h3", "dedup"]
    assert any(c["check"] == "dedup used this run's H3 matches" and c["ok"] for c in m["checks"])
    d["h3"]["matches"]["sha256"] = "0" * 64
    summary.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(rp.Stop, match="dedup used this run's H3 matches"):
        rp.run(config, start="dedup", to="dedup")


def test_h3_cannot_be_selected_without_a_stage(config):
    with pytest.raises(rp.Stop, match="needs stages.h3"):
        rp.plan(config, to="h3")
    with pytest.raises(rp.Stop, match="needs stages.h3"):
        rp.run(config, to="h3")


def test_digests_repeat_across_identical_runs(tmp_path, config, tsai_outputs):
    a = rp.run(config)
    b = rp.run(write_config(tmp_path / "again.json", tsai_outputs, run_id="test-run-2"))
    assert [s["digest"] for s in a["stages"]] == [s["digest"] for s in b["stages"]]


def test_from_keeps_earlier_checks(config):
    full = len(rp.run(config, to="apply")["checks"])
    m = rp.run(config, start="f2")
    assert [s["stage"] for s in m["stages"]] == [s for s in rp.STAGES if s not in rp.OPTIONAL] and m["totals"]["final"] == 9
    assert len(m["checks"]) > full and {ch["stage"] for ch in m["checks"]} >= {"overlap", "dedup", "apply", "f2"}


def test_adopted_output_changed_after_recording_stops(config, tsai_outputs):
    rp.run(config, to="apply")
    with (tsai_outputs["dedup"] / "remove_list.csv").open("a", encoding="utf-8") as f:
        f.write("en-dclm,train,en-dclm/part-00000.parquet,1,e1\n")
    with pytest.raises(rp.Stop, match="changed"):
        rp.run(config, start="f2")


def test_from_a_stage_whose_input_was_never_run_stops(config):
    with pytest.raises(rp.Stop, match="no record .* run it first"):
        rp.run(config, start="f2")


def test_dedup_from_another_overlap_run_stops(tmp_path, config, tsai_outputs):
    other = overlap_folder(tmp_path / "other_overlap")
    (other / "overlap_matches.csv").write_text("row_a,row_b\n0,2\n", encoding="utf-8")
    dedup_folder(tsai_outputs["dedup"], other)
    with pytest.raises(rp.Stop, match="dedup used this overlap run"):
        rp.run(config)


def test_overlap_of_other_parts_stops(tmp_path, config, tsai_outputs):
    parts = dict(PARTS)
    parts[("train", "en-dclm/part-00009.parquet")] = parts.pop(("train", "en-dclm/part-00000.parquet"))
    overlap_folder(tsai_outputs["overlap"], parts)
    dedup_folder(tsai_outputs["dedup"], tsai_outputs["overlap"])
    with pytest.raises(rp.Stop, match="overlap read these cleaned parts"):
        rp.run(config)


def test_overlap_of_changed_cleaned_bytes_stops(config, tsai_outputs):
    part = next((tsai_outputs["cleaned"] / "train").rglob("*.parquet"))
    table = pq.read_table(part)
    rows = table.to_pylist()
    rows[0]["text"] += " changed after overlap"
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), part)
    with pytest.raises(rp.Stop, match="overlap read these cleaned bytes"):
        rp.run(config)


def test_count_mismatch_stops(tmp_path, config, tsai_outputs):
    overlap_folder(tsai_outputs["overlap"], docs_all=12)
    with pytest.raises(rp.Stop, match="overlap read every cleaned row"):
        rp.run(config)


def test_dedup_removing_heldout_stops(config, tsai_outputs):
    dedup_folder(tsai_outputs["dedup"], tsai_outputs["overlap"], heldout_removed=1)
    with pytest.raises(rp.Stop, match="held-out"):
        rp.run(config)


def test_f2_errors_stop(config, monkeypatch):
    monkeypatch.setenv("FAKE_F2_ERROR", "g3")
    with pytest.raises(rp.Stop, match="F2 reported no errors on train"):
        rp.run(config)


def test_f2_that_read_something_else_stops(config, monkeypatch):
    monkeypatch.setenv("FAKE_F2_BAD_SHA", "1")
    with pytest.raises(rp.Stop, match="F2 read what apply wrote"):
        rp.run(config)


def test_stale_final_output_stops(tmp_path, config):
    stale = tmp_path / "runs" / "test-run" / "final" / "train" / "old-pack" / "part-00000.parquet"
    stale.parent.mkdir(parents=True)
    shutil.copyfile(next((tmp_path / "cleaned" / "train").rglob("*.parquet")), stale)
    with pytest.raises(rp.Stop, match="stale F2 output"):
        rp.run(config)


def test_train_only_run(tmp_path, cleaned, monkeypatch):
    shutil.rmtree(cleaned / "heldout")
    train = {k: v for k, v in PARTS.items() if k[0] == "train"}
    overlap = overlap_folder(tmp_path / "overlap1", train, docs_all=11)
    dedup = dedup_folder(tmp_path / "dedup1", overlap)
    rows = list(csv.reader((dedup / "dedup_groups.csv").open(encoding="utf-8")))
    write_csv(dedup / "dedup_groups.csv", rows[0], [r for r in rows[1:] if r[5] == "train"])
    s = json.loads((dedup / "dedup_summary.json").read_text(encoding="utf-8"))
    s.update(documents_all=11, groups_without_survivor=1, groups_with_several_survivors=0)  # G000002 kept only held-out copies
    (dedup / "dedup_summary.json").write_text(json.dumps(s), encoding="utf-8")
    monkeypatch.setenv("FAKE_F2_DROP", "g0")
    cfg = write_config(tmp_path / "p1.json", {"cleaned": cleaned, "overlap": overlap, "dedup": dedup}, run_id="train-only")
    m = rp.run(cfg)
    assert m["totals"] == {"cleaned": 11, "removed_by_dedup": 2, "dropped_by_f2": 1, "final": 8}


def test_run_mode_calls_the_script(tmp_path, config, tsai_outputs):
    maker = tmp_path / "make_overlap.py"
    src = tsai_outputs["overlap"]
    maker.write_text(f"import shutil, sys\nshutil.copytree({str(src)!r}, sys.argv[1], dirs_exist_ok=True)\n", encoding="utf-8")
    out = tmp_path / "overlap_run"
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["stages"]["overlap"] = {"mode": "run", "output": str(out), "command": [str(maker), str(out)]}
    config.write_text(json.dumps(cfg), encoding="utf-8")
    m = rp.run(config)
    rec = next(s for s in m["stages"] if s["stage"] == "overlap")
    assert rec["mode"] == "run" and rec["code_sha256"] == sha(maker)
    assert (tmp_path / "runs" / "test-run" / "logs" / "overlap.log").is_file()


def test_run_mode_failure_stops(tmp_path, config):
    bad = tmp_path / "bad_overlap.py"
    bad.write_text("import sys; print('boom'); sys.exit(3)\n", encoding="utf-8")
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["stages"]["overlap"] = {"mode": "run", "output": cfg["stages"]["overlap"]["output"], "command": [str(bad)]}
    config.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match="exit code 3.*boom"):
        rp.run(config)


def test_bad_config_stops_before_anything_runs(tmp_path, config):
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["stages"]["f2"] = {"script": str(tmp_path / "missing_run_f2.py")}
    config.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match="f2 script .* not found"):
        rp.run(config)
    assert not (tmp_path / "runs").exists()


def set_f2(config, **kw):
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["stages"]["f2"].update(kw)
    config.write_text(json.dumps(cfg), encoding="utf-8")


def test_parallel_f2_matches_one_process(tmp_path, config, tsai_outputs):
    one = rp.run(config)
    par_cfg = write_config(tmp_path / "par.json", tsai_outputs, run_id="parallel")
    set_f2(par_cfg, workers=3)
    par = rp.run(par_cfg)
    run = tmp_path / "runs" / "parallel"
    f2 = next(s for s in par["stages"] if s["stage"] == "f2")
    assert (f2["workers"], f2["units"]) == (3, 3)  # train/code-go, train/en-dclm, heldout/code-go
    assert par["totals"] == one["totals"] and final_ids(run) == final_ids(tmp_path / "runs" / "test-run")
    assert {p.name for p in (run / "logs").glob("f2_*.log")} == {"f2_train_code-go.log", "f2_train_en-dclm.log",
                                                                  "f2_heldout_code-go.log"}
    c = {s["stage"]: s["counts"] for s in par["stages"]}
    assert (c["survivor_loss"]["lost"], c["survivor_loss"]["partly_hit"]) == (1, 1)
    assert c["ledger"] == {s["stage"]: s["counts"] for s in one["stages"]}["ledger"]


def test_parallel_f2_crash_names_the_pack_and_rerun_recovers(config, monkeypatch):
    set_f2(config, workers=2)
    monkeypatch.setenv("FAKE_F2_CRASH", "en-dclm")
    with pytest.raises(rp.Stop, match=r"1 of 3 unit\(s\) failed.*train/en-dclm"):
        rp.run(config)
    monkeypatch.delenv("FAKE_F2_CRASH")
    assert rp.run(config, start="f2")["totals"]["final"] == 9


@pytest.mark.parametrize("workers", [0, "4", 1.5, True])
def test_bad_workers_stop(config, workers):
    set_f2(config, workers=workers)
    with pytest.raises(rp.Stop, match="workers"):
        rp.run(config)


# --- survivor loss against dedup's summary and the ledger (step 17) --------------------------------------------------
def edit_dedup_summary(tsai_outputs, **changes):
    path = tsai_outputs["dedup"] / "dedup_summary.json"
    s = json.loads(path.read_text(encoding="utf-8"))
    for k, v in changes.items():
        if v is None:
            s.pop(k, None)
        else:
            s[k] = v
    path.write_text(json.dumps(s), encoding="utf-8")


@pytest.mark.parametrize("key, value, message", [
    ("clusters", 3, "survivor loss saw every dedup group"),
    ("groups_without_survivor", 1, "groups without a survivor"),
    ("groups_with_several_survivors", 0, "groups with several survivors"),
    ("clusters", None, "dedup's summary counts its groups")])
def test_survivor_loss_disagreeing_with_dedups_summary_stops(config, tsai_outputs, key, value, message):
    """dedup_groups.csv is checked against what dedup.py decided, not against itself."""
    edit_dedup_summary(tsai_outputs, **{key: value})
    with pytest.raises(rp.Stop, match=message):
        rp.run(config)


@pytest.mark.parametrize("h3, stops", [(None, True), ({"groups_survivor_removed": 1}, False)])
def test_h3_may_leave_a_group_without_survivor(config, tsai_outputs, h3, stops):
    """H3 turns survivors into removed copies after dedup.py counted groups_without_survivor: with h3 in the summary, up
    to h3.groups_survivor_removed more groups may have none."""
    path = tsai_outputs["dedup"] / "dedup_groups.csv"
    rows = list(csv.reader(path.open(encoding="utf-8")))
    write_csv(path, rows[0], [r[:3] + ["removed"] + r[4:] if r[0] == "G000001" else r for r in rows[1:]])
    edit_dedup_summary(tsai_outputs, h3=h3)
    if stops:
        with pytest.raises(rp.Stop, match="groups without a survivor"):
            rp.run(config, to="survivor_loss")
    else:
        c = {s["stage"]: s["counts"] for s in rp.run(config, to="survivor_loss")["stages"]}
        assert (c["survivor_loss"]["without_survivor"], c["survivor_loss"]["lost"]) == (1, 0)


@pytest.mark.parametrize("shift, message", [
    ({"code-go": 1}, "ledger's survivors dropped by F2 = survivor loss's"),
    ({"code-go": -1, "en-dclm": 1}, "ledger's survivors dropped by F2 per pack = survivor loss's")])
def test_ledger_disagreeing_with_survivor_loss_stops(config, monkeypatch, shift, message):
    """The ledger counts the survivors F2 dropped from every document's row; survivor_loss.py from the groups and F2's
    reports. A difference in total or per pack stops the run."""
    import ledger
    real = ledger.build

    def build(*args, **kwargs):
        s = real(*args, **kwargs)
        by_pack = s["survivors_dropped_by_f2"]["by_pack"]
        for pack, n in shift.items():
            by_pack[pack] = by_pack.get(pack, 0) + n
        s["survivors_dropped_by_f2"]["total"] += sum(shift.values())
        return s
    monkeypatch.setattr(ledger, "build", build)
    with pytest.raises(rp.Stop, match=message):
        rp.run(config)


def test_cli(tmp_path, config):
    env = {**os.environ, "FAKE_F2_DROP": "g0,h1"}
    p = subprocess.run([sys.executable, "-I", str(PIPELINE / "run_pipeline.py"), "--config", str(config)],
                       capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout.strip().splitlines()[-1])["final"] == 9
    table = p.stderr.strip().splitlines()[-5:]
    assert table[0].split() == ["pack", "split", "cleaned", "-dedup", "-f2", "final"]
    assert table[-1].split() == ["total", "13", "2", "2", "9"]
    assert table[1].split() == ["code-go", "train", "8", "1", "1", "6"]


# --- the shard stage (stand-in run_shards.py; the real one is tested in shards/tests) -----------------------------------
@pytest.fixture
def shard_config(tmp_path, tsai_outputs, config, monkeypatch):
    """A config with stages.shards, and the clean job's job_summary.json the shard stage needs. Returns the config path."""
    for k in ("FAKE_SHARDS_FAIL", "FAKE_SHARDS_NONE", "FAKE_SHARDS_BAD_RUN", "FAKE_SHARDS_TRUNCATE"):
        monkeypatch.delenv(k, raising=False)
    sys.path.insert(0, str(FAKE_SHARDS.parents[2] / "shards"))
    import verify_shards  # the stand-in writes dummy .bin files: the real verification is tested in shards/tests
    monkeypatch.setattr(verify_shards, "verify", lambda *args, **kwargs: ([], {}))
    (tsai_outputs["cleaned"] / "job_summary.json").write_text(json.dumps({"clean_sha256": "c" * 64, "parts": []}), encoding="utf-8")
    tokenizer = tmp_path / "tokenizer.json"
    tokenizer.write_text("{}", encoding="utf-8")
    return write_config(tmp_path / "pipeline.json", tsai_outputs,
                        shards={"script": str(FAKE_SHARDS), "tokenizer": str(tokenizer), "packs": ["code-go"], "tokens": 100,
                                "dataset_version": "sample"})


def test_shards_run_after_f2_and_are_recorded(tmp_path, shard_config):
    m = rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert [s["stage"] for s in m["stages"]] == [s for s in rp.STAGES[: rp.STAGES.index("shards") + 1] if s != "h3"]
    s = m["stages"][-1]
    assert s["counts"] == {"written": 2, "failed": 0, "skipped": 0, "not_sharded": 1, "truncated": 0, "shards": 2, "parts": 3}
    assert m["totals"]["shards_written"] == 2 and all(ch["ok"] for ch in m["checks"])
    record = json.loads((run / "cleaning_pipeline.json").read_text(encoding="utf-8"))
    assert sorted(record) == ["clean_py_sha256", "dedup", "f2_set_sha256"] and record["clean_py_sha256"] == "c" * 64
    assert s["cleaning_pipeline_sha256"] == rp.sha256(run / "cleaning_pipeline.json")
    assert json.loads((run / "pipeline_manifest.json").read_text(encoding="utf-8"))["stages"][-1]["stage"] == "shards"
    assert json.loads((run / "shards" / "args.json").read_text(encoding="utf-8"))["packs"] == ["code-go"]
    assert json.loads((run / "shards" / "args.json").read_text(encoding="utf-8"))["tokens"] == 100
    assert json.loads((run / "shards" / "args.json").read_text(encoding="utf-8"))["dataset_version"] == "sample"
    assert (run / "logs" / "shards.log").is_file() and s["digest"] and s["code_sha256"]


def test_without_stages_shards_the_run_stops_after_the_ledger(tmp_path, config):
    m = rp.run(config)
    assert [s["stage"] for s in m["stages"]][-1] == "ledger" and "shards_written" not in m["totals"]
    assert not (tmp_path / "runs" / "test-run" / "cleaning_pipeline.json").exists()
    with pytest.raises(rp.Stop, match="stages.shards is not configured"):
        rp.run(config, to="shards")


def test_from_shards_adds_the_stage_to_a_finished_run(tmp_path, shard_config):
    rp.run(shard_config, to="ledger")
    m = rp.run(shard_config, start="shards")
    assert [s["stage"] for s in m["stages"]] == [s for s in rp.STAGES[: rp.STAGES.index("shards") + 1] if s != "h3"] and m["totals"]["final"] == 9 and m["totals"]["shards_written"] == 2


def test_a_second_shard_run_into_the_same_out_stops(shard_config):
    rp.run(shard_config)
    with pytest.raises(rp.Stop, match="run_shards.py exited 0"):  # the stand-in refuses, as the real one does
        rp.run(shard_config, start="shards")


def test_a_failed_part_stops_the_run_before_the_stage_is_recorded(tmp_path, shard_config, monkeypatch):
    monkeypatch.setenv("FAKE_SHARDS_FAIL", "1")
    with pytest.raises(rp.Stop, match="no part failed or was skipped"):
        rp.run(shard_config)
    stages = [s["stage"] for s in json.loads((tmp_path / "runs" / "test-run" / "pipeline_manifest.json").read_text(encoding="utf-8"))["stages"]]
    assert stages[-1] == "ledger"


def test_a_shard_process_that_wrote_no_summary_stops_the_run(shard_config, monkeypatch):
    monkeypatch.setenv("FAKE_SHARDS_NONE", "1")
    with pytest.raises(rp.Stop, match="wrote no shards_summary.json"):
        rp.run(shard_config)


def test_a_summary_of_another_run_stops_the_run(shard_config, monkeypatch):
    monkeypatch.setenv("FAKE_SHARDS_BAD_RUN", "1")
    with pytest.raises(rp.Stop, match="the summary is this run's"):
        rp.run(shard_config)


def test_no_clean_job_summary_means_no_shard_stage(tmp_path, shard_config, tsai_outputs):
    (tsai_outputs["cleaned"] / "job_summary.json").unlink()
    with pytest.raises(rp.Stop, match="shards: .*no job_summary.json"):
        rp.run(shard_config)


@pytest.mark.parametrize("change, message", [({"tokenizer": "/no/such/tokenizer.json"}, "stages.shards.tokenizer"),
                                             ({"tokens": 0}, "stages.shards.tokens"), ({"packs": "code-go"}, "stages.shards.packs"),
                                             ({"script": "/no/such/run_shards.py"}, "shards script"),
                                             ({"dataset_version": None}, "dataset_version is None: name the corpus release"),
                                             ({"dataset_version": ""}, "dataset_version is '': name the corpus release"),
                                             ({"dataset_version": "test"}, '"test" is only for any_tokenizer'),
                                             ({"any_tokenizer": True, "dataset_version": "corpus-v1"},
                                              'any_tokenizer shards are "test"')])
def test_the_shards_config_is_checked_before_anything_runs(tmp_path, shard_config, change, message):
    cfg = json.loads(shard_config.read_text(encoding="utf-8"))
    cfg["stages"]["shards"].update(change)
    shard_config.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match=message):
        rp.run(shard_config)
    assert not (tmp_path / "runs").exists()


# --- stages run from settings files: default folders in the run folder, generated configs, --plan -----------------------
@pytest.fixture
def staged(tmp_path, tsai_outputs, monkeypatch):
    """A run config whose clean, overlap and dedup stages run the stand-in fake_stage.py from settings files, in a made-up
    repository (rp.REPO), with every folder left to the default. Returns (config path, repo)."""
    repo = tmp_path / "repo"
    (repo / "out").mkdir(parents=True)
    monkeypatch.setattr(rp, "REPO", repo)
    for k in ("FAKE_F2_ERROR", "FAKE_F2_BAD_SHA", "FAKE_F2_CRASH"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("FAKE_F2_DROP", "g0,h1")

    manifest = tmp_path / "sample_manifest.json"
    manifest.write_text(made_up_manifest({"train": 3, "heldout": 1}), encoding="utf-8")

    def settings(name, fixture, **extra):
        p = tmp_path / f"{name}_settings.json"
        p.write_text(json.dumps({"fixture": str(fixture), **extra}), encoding="utf-8")
        return str(p)

    cfg = {"run_id": "test-run", "out": str(repo / "out" / "runs"), "stages": {
        "clean": {"mode": "run", "script": str(FAKE_STAGE), "settings": settings("clean", tsai_outputs["cleaned"]), "input": "raw/sample",
                  "manifest": str(manifest), "manifest_sha256": sha(manifest), "expected_parts": {"train": 3, "heldout": 1}, "sample": "made up"},
        "overlap": {"mode": "run", "script": str(FAKE_STAGE), "settings": settings("overlap", tsai_outputs["overlap"], k=5, floor=0.5, inputs="x", out="y")},
        "dedup": {"mode": "run", "script": str(FAKE_STAGE), "settings": settings("dedup", tsai_outputs["dedup"], cross_pack=True, results="x", inputs="x", out="y")},
        "f2": {"script": str(FAKE_F2)}}}
    path = tmp_path / "run_config.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path, repo


def edit_stage(path, stage, **changes):
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["stages"][stage].update(changes)
    path.write_text(json.dumps(cfg), encoding="utf-8")


def test_stages_run_from_settings_into_the_run_folder(tmp_path, staged):
    path, repo = staged
    m = rp.run(path)
    run = repo / "out" / "runs" / "test-run"
    recs = {s["stage"]: s for s in m["stages"]}
    assert m["totals"] == {"cleaned": 13, "removed_by_dedup": 2, "dropped_by_f2": 2, "final": 9} and all(c["ok"] for c in m["checks"])
    assert [recs[s]["output"] for s in ("clean", "overlap", "dedup")] == [f"out/runs/test-run/{s}" for s in ("clean", "overlap", "dedup")]
    assert (run / "clean" / "train").is_dir() and (run / "overlap" / "overlap_summary.json").is_file() and (run / "dedup" / "remove_list.csv").is_file()
    # every stage gets the settings with the path keys filled in, repo-relative; every other setting is kept
    cl = json.loads((run / "cfg" / "clean.json").read_text(encoding="utf-8"))
    assert (cl["input_root"], cl["output_root"]) == ("raw/sample", "out/runs/test-run/clean") and recs["clean"]["command"][-2:] == ["--config", (run / "cfg" / "clean.json").as_posix()]
    assert (cl["manifest_sha256"], cl["expected_parts"], cl["sample"]) == (sha(cl["manifest"]), {"train": 3, "heldout": 1}, "made up")
    ov = json.loads((run / "cfg" / "overlap.json").read_text(encoding="utf-8"))
    dd = json.loads((run / "cfg" / "dedup.json").read_text(encoding="utf-8"))
    assert (ov["inputs"], ov["out"], ov["k"], ov["floor"]) == ("out/runs/test-run/clean", "out/runs/test-run/overlap", 5, 0.5)
    assert (dd["results"], dd["inputs"], dd["out"], dd["cross_pack"]) == ("out/runs/test-run/overlap", "out/runs/test-run/clean", "out/runs/test-run/dedup", True)
    for stage in ("clean", "overlap", "dedup"):
        assert recs[stage]["config"] == f"cfg/{stage}.json" and recs[stage]["config_sha256"] == sha(run / "cfg" / f"{stage}.json")
    assert recs["overlap"]["settings_sha256"] == sha(json.loads(path.read_text(encoding="utf-8"))["stages"]["overlap"]["settings"])
    assert json.loads((run / "logs" / "clean.log").read_text(encoding="utf-8").splitlines()[-1])["input_root"] == "raw/sample"
    assert json.loads((run / "logs" / "dedup.log").read_text(encoding="utf-8").splitlines()[-1])["keys"]["results"] == "out/runs/test-run/overlap"


def test_clean_resume_reaches_the_job_the_record_and_the_plan(staged):
    path, repo = staged
    edit_stage(path, "clean", resume=True)
    assert "resume = True" in rp.plan(path)
    m = rp.run(path, to="clean")
    run = repo / "out" / "runs" / "test-run"
    assert json.loads((run / "cfg" / "clean.json").read_text(encoding="utf-8"))["resume"] is True
    assert m["stages"][0]["stage"] == "clean" and m["stages"][0]["resume"] is True
    edit_stage(path, "clean", resume=False)
    assert "resume = True" not in rp.plan(path)


def test_a_run_without_resume_does_not_tell_the_job_so(staged):
    path, repo = staged
    m = rp.run(path, to="clean")
    assert "resume" not in m["stages"][0]
    assert "resume" not in json.loads((repo / "out" / "runs" / "test-run" / "cfg" / "clean.json").read_text(encoding="utf-8"))


def test_a_resumed_clean_stage_adds_to_its_log_and_a_stage_without_resume_starts_it_again(staged):
    path, repo = staged
    log = repo / "out" / "runs" / "test-run" / "logs" / "clean.log"
    rp.run(path, to="clean")
    first = log.read_text(encoding="utf-8")
    assert first.count("$ ") == 1
    with pytest.raises(rp.Stop, match="clean: .*failed"):  # the stand-in refuses a folder that is there, as the job does without resume
        rp.run(path, to="clean")
    assert log.read_text(encoding="utf-8").count("$ ") == 1 and log.read_text(encoding="utf-8") != first  # rewritten: the failed attempt's
    edit_stage(path, "clean", resume=True)
    with pytest.raises(rp.Stop, match="clean: .*failed"):
        rp.run(path, to="clean")
    after = log.read_text(encoding="utf-8")
    assert after.count("$ ") == 2 and "\n\n$ " in after  # the attempt before it is kept, a blank line between


def test_resume_is_refused_for_a_stage_that_is_not_clean(staged):
    path, repo = staged
    edit_stage(path, "overlap", resume=True)
    for go in (rp.plan, rp.run):
        with pytest.raises(rp.Stop, match="overlap.resume: only the clean job can be resumed"):
            go(path)
    assert not (repo / "out" / "runs").exists()


def clean_checks(m):
    return [c for c in m["checks"] if c["check"].startswith("clean: ")]


def test_the_clean_summary_is_checked_against_the_folder_and_the_record_says_so(staged):
    path, repo = staged
    m = rp.run(path, to="clean")
    assert m["stages"][0]["job_summary_checked"] is True
    assert [c["check"].removeprefix("clean: ") for c in clean_checks(m)] == [
        "the job reported no errors", "the job cleaned the parts the run expects, each with a report",
        "the job read this run's input manifest", "input rows = output rows + dropped, and the output rows are those on disk",
        "the parts on disk are the parts the job reports, with their rows", "each part's sha256 is the one the job recorded"]
    assert all(c["ok"] for c in clean_checks(m))


@pytest.mark.parametrize("damage, message", [
    ("errors", "the job reported no errors.*2 error"),
    ("parts", "the run expects.*completed_parts 3, expected_parts 4, 4 part report.*the run expects 4"),
    ("manifest", "the job read this run's input manifest.*ffffffffffff"),
    ("rows", r"input rows = output rows \+ dropped.*input_rows 13, output_rows 14"),
    ("renamed", "the parts on disk are the parts the job reports.*1 reported but not on disk.*1 on disk but not reported"),
    ("sha", "each part's sha256 is the one the job recorded.*1 of 4 part"),
    ("none", "job_summary.json is missing or is not a clean job's summary")])
def test_a_clean_job_whose_summary_disagrees_with_its_folder_stops_the_run(staged, monkeypatch, damage, message):
    path, repo = staged
    monkeypatch.setenv("FAKE_CLEAN_DAMAGE", damage)
    with pytest.raises(rp.Stop, match=message):
        rp.run(path, to="clean")


def write_clean_summary(folder, **change):
    """The job_summary.json of a clean job that made `folder`, as clean_job.py writes it (the keys the runner reads)."""
    parts = [{"part": f.relative_to(folder).as_posix(), "output_rows": pq.read_metadata(f).num_rows, "output_sha256": sha(f)}
             for f in sorted(folder.rglob("*.parquet"))]
    rows = sum(p["output_rows"] for p in parts)
    summary = {"completed_parts": len(parts), "expected_parts": len(parts), "input_rows": rows, "output_rows": rows,
               "actions": {"keep": rows}, "errors": 0, "scope": "full manifest", "parts": parts, **change}
    (folder / "job_summary.json").write_text(json.dumps(summary), encoding="utf-8")


def test_an_adopted_folder_without_a_clean_job_summary_is_not_checked_and_the_record_says_so(config):
    m = rp.run(config, to="clean")
    assert m["stages"][0]["job_summary_checked"] is False and clean_checks(m) == []


def test_an_adopted_folder_with_a_clean_job_summary_is_checked_without_the_run_config(config, tsai_outputs):
    write_clean_summary(tsai_outputs["cleaned"])
    m = rp.run(config, to="clean")
    assert m["stages"][0]["job_summary_checked"] is True
    assert "the job read this run's input manifest" not in [c["check"].removeprefix("clean: ") for c in clean_checks(m)]  # needs stages.clean's pin
    assert len(clean_checks(m)) == 5 and all(c["ok"] for c in clean_checks(m))


@pytest.mark.parametrize("change, message", [({"errors": 1}, "the job reported no errors"),
                                             ({"output_rows": 99}, "input rows = output rows"),
                                             ({"completed_parts": 3}, "the job cleaned the parts the run expects")])
def test_an_adopted_clean_summary_that_disagrees_with_its_folder_stops_the_run(config, tsai_outputs, change, message):
    write_clean_summary(tsai_outputs["cleaned"], **change)
    with pytest.raises(rp.Stop, match=message):
        rp.run(config, to="clean")


def test_a_summary_in_another_format_is_not_a_clean_job_summary_even_when_adopted(config, tsai_outputs):
    (tsai_outputs["cleaned"] / "job_summary.json").write_text(json.dumps({"clean_sha256": "c" * 64, "parts": []}), encoding="utf-8")
    assert rp.run(config, to="clean")["stages"][0]["job_summary_checked"] is False


def test_the_default_shard_script_is_told_not_to_verify_and_another_script_is_not(shard_config, monkeypatch):
    seen, real = [], rp.run_script
    monkeypatch.setattr(rp, "run_script", lambda script, args, stage, log, append=False:
                        (seen.append(list(map(str, args))) or 0) if stage == "shards" else real(script, args, stage, log, append))
    for script in (rp.DEFAULT_SHARDS, str(FAKE_SHARDS)):  # no summary is written: the stage stops, after the command was built
        edit_stage(shard_config, "shards", script=script)
        with pytest.raises(rp.Stop, match="wrote no shards_summary.json"):
            rp.run(shard_config)
    assert "--no-verify" in seen[0] and "--no-verify" not in seen[1]


def test_a_stage_script_given_as_a_list_runs_the_tool_through_its_wrapper(tmp_path, staged):
    """A cleaner that is run through a wrapper (spec v1.1: use_clean.py <tool> --config ...): "script" as a list names
    the wrapper and the tool, the tool goes before --config, and the stage record keeps the sha256 of both."""
    path, repo = staged
    wrapper = tmp_path / "wrapper.py"
    wrapper.write_text("import runpy, sys\nsys.argv = sys.argv[1:]\nrunpy.run_path(sys.argv[0], run_name='__main__')\n", encoding="utf-8")
    edit_stage(path, "clean", script=[str(wrapper), str(FAKE_STAGE)])
    assert f"{wrapper} {FAKE_STAGE} --config" in rp.plan(path)
    m = rp.run(path)
    recs = {s["stage"]: s for s in m["stages"]}
    assert recs["clean"]["command"][:3] == [str(wrapper), str(FAKE_STAGE), "--config"] and all(c["ok"] for c in m["checks"])
    assert recs["clean"]["code_sha256"] == sha(wrapper) and recs["clean"]["tools_sha256"] == {str(FAKE_STAGE): sha(FAKE_STAGE)}
    assert "tools_sha256" not in recs["overlap"] and m["totals"]["cleaned"] == 13


def test_the_clean_record_keeps_the_sha256_of_the_cleaner_the_settings_name(tmp_path, staged):
    """clean_job.py loads the cleaner named by "clean" in the settings file and checks its pin; the stage record keeps that
    file's sha256 (and clean_manifest.py's, which the job shares with --plan) next to the job script's."""
    path, repo = staged
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cleaner = tmp_path / "some_clean.py"
    cleaner.write_text("# a cleaner\n", encoding="utf-8")
    named = tmp_path / "clean_names_cleaner.json"
    named.write_text(json.dumps({**json.loads(Path(cfg["stages"]["clean"]["settings"]).read_text(encoding="utf-8")), "clean": str(cleaner)}),
                     encoding="utf-8")
    edit_stage(path, "clean", settings=str(named))
    recs = {s["stage"]: s for s in rp.run(path)["stages"]}
    assert recs["clean"]["tools_sha256"] == {str(cleaner): sha(cleaner),
                                             str(PIPELINE / "clean_manifest.py"): sha(PIPELINE / "clean_manifest.py")}
    assert recs["clean"]["code_sha256"] == sha(FAKE_STAGE)  # the job script itself, as before
    assert "tools_sha256" not in recs["overlap"]


@pytest.mark.parametrize("script, message", [
    (["{wrapper}", "{missing}"], "config: stages.clean script .*no_such_tool.py not found"),
    (["{missing}", "{tool}"], "config: stages.clean script .*no_such_tool.py not found"),
    ([], "stages.clean.script must be a script's path, or a list")])
def test_a_script_list_that_names_a_missing_script_stops_before_anything_runs(tmp_path, staged, script, message):
    path, repo = staged
    names = {"wrapper": str(FAKE_STAGE), "tool": str(FAKE_STAGE), "missing": str(tmp_path / "no_such_tool.py")}
    edit_stage(path, "clean", script=[s.format(**names) for s in script])
    for go in (rp.plan, rp.run):
        with pytest.raises(rp.Stop, match=message):
            go(path)
    assert not (repo / "out" / "runs").exists()


def test_a_settings_pin_that_does_not_match_stops_before_anything_runs(staged):
    path, repo = staged
    edit_stage(path, "overlap", settings_sha256="0" * 64)
    with pytest.raises(rp.Stop, match="overlap: .*pins"):
        rp.run(path)
    assert not (repo / "out" / "runs").exists()


def test_a_run_stage_needs_settings_or_a_command(staged):
    path, _ = staged
    cfg = json.loads(path.read_text(encoding="utf-8"))
    del cfg["stages"]["dedup"]["settings"]
    path.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match="dedup: .*settings .* is missing"):
        rp.run(path)


def test_a_command_must_say_where_it_writes_and_an_adopted_stage_needs_its_folder(staged):
    path, _ = staged
    edit_stage(path, "overlap", command=[str(FAKE_STAGE)])
    with pytest.raises(rp.Stop, match="overlap.output is missing: with a command, say where it writes"):
        rp.run(path)
    edit_stage(path, "overlap", mode="adopt")
    with pytest.raises(rp.Stop, match="overlap.output is missing \\(an adopted stage needs"):
        rp.run(path)


def test_an_output_may_not_take_a_folder_name_of_the_run_or_overlap_another_stage(staged):
    path, repo = staged
    run = repo / "out" / "runs" / "test-run"
    edit_stage(path, "overlap", output=str(run / "final"))
    with pytest.raises(rp.Stop, match="folder of the run itself"):
        rp.run(path)
    edit_stage(path, "overlap", output=str(run / "clean" / "inner"))
    with pytest.raises(rp.Stop, match="stages.clean.output and stages.overlap.output overlap"):
        rp.run(path)


def test_a_settings_stage_cannot_write_outside_out(staged, tmp_path):
    path, repo = staged
    edit_stage(path, "overlap", output=str(tmp_path / "elsewhere"))
    with pytest.raises(rp.Stop, match="named subfolder"):
        rp.run(path)


def test_the_plan_shows_every_folder_and_command_and_runs_nothing(staged, capsys, monkeypatch):
    path, repo = staged
    text = rp.plan(path)
    for line in ("run folder: out/runs/test-run", "01 clean", "02 overlap", "03 dedup", "04 apply", "05 f2", "06 survivor_loss",
                 "inputs = out/runs/test-run/clean, out = out/runs/test-run/overlap", "generated config out/runs/test-run/cfg/overlap.json",
                 "input_root = raw/sample, manifest = ", "output_root = out/runs/test-run/clean", "settings "):
        assert line in text
    assert "shards" not in text.split("\n", 1)[1] and "07 shards" not in text
    assert not (repo / "out" / "runs").exists()  # nothing written, not even cfg/
    assert "05 f2" not in rp.plan(path, to="apply")
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--config", str(path), "--plan"])
    rp.main()
    assert "01 clean" in capsys.readouterr().out and not (repo / "out" / "runs").exists()


def test_the_plan_of_an_adopted_run_says_adopt(config):
    text = rp.plan(config)
    assert sum(" adopt  " in line for line in text.splitlines()) == 3 and "$ python" not in text


def test_the_plan_checks_the_config_like_a_run(staged):
    path, _ = staged
    edit_stage(path, "dedup", settings_sha256="0" * 64)
    with pytest.raises(rp.Stop, match="pins"):
        rp.plan(path)
    with pytest.raises(rp.Stop, match="unknown stage"):
        rp.Run(path).plan("nope")


# --- run parameters live in the config file: run_id, adopted stages, stages.clean.only, to, from ----------------------------
def edit_config(path, **top):
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg.update(top)
    path.write_text(json.dumps(cfg), encoding="utf-8")


def set_stage(path, stage, spec):
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["stages"][stage] = spec
    path.write_text(json.dumps(cfg), encoding="utf-8")


def test_run_id_in_the_config_names_the_run(staged):
    path, repo = staged
    edit_config(path, run_id="job-1")
    m = rp.run(path)
    assert m["run_id"] == "job-1" and "overrides" not in m
    assert (repo / "out" / "runs" / "job-1" / "pipeline_manifest.json").is_file() and not (repo / "out" / "runs" / "test-run").exists()
    assert m["config"]["run_id"] == "job-1"  # the manifest embeds the config that ran


def test_a_run_needs_a_run_id(staged):
    path, _ = staged
    cfg = json.loads(path.read_text(encoding="utf-8"))
    del cfg["run_id"]
    path.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match="run_id is missing"):
        rp.run(path)


def test_an_adopted_stage_in_the_config_uses_the_folder_instead_of_running(tmp_path, staged, tsai_outputs):
    path, repo = staged
    prev = repo / "out" / "earlier" / "clean"
    shutil.copytree(tsai_outputs["cleaned"], prev)
    set_stage(path, "clean", {"mode": "adopt", "output": str(prev)})
    m = rp.run(path)
    run = repo / "out" / "runs" / "test-run"
    clean = next(s for s in m["stages"] if s["stage"] == "clean")
    assert (clean["mode"], clean["command"], clean["output"]) == ("adopt", None, "out/earlier/clean")
    assert not (run / "clean").exists() and not (run / "logs" / "clean.log").exists() and not (run / "cfg" / "clean.json").exists()
    assert json.loads((run / "cfg" / "overlap.json").read_text(encoding="utf-8"))["inputs"] == "out/earlier/clean"
    assert m["totals"]["final"] == 9


def test_clean_only_in_the_config_limits_the_clean_job_and_lets_overlap_expect_fewer_packs(staged, monkeypatch):
    path, repo = staged
    monkeypatch.setattr(rp.Run, "check_clean_summary", lambda self, out, counts: False)  # the stand-in copies every part whatever --only says
    part = "train/code-go/part-00000.parquet"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["stages"]["clean"]["only"] = [part]
    cfg["to"] = "overlap"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    m = rp.run(path)
    run = repo / "out" / "runs" / "test-run"
    clean = next(s for s in m["stages"] if s["stage"] == "clean")
    assert [s["stage"] for s in m["stages"]] == ["clean", "overlap"]
    assert clean["only"] == [part] and clean["command"][-2:] == ["--only", part]
    assert json.loads((run / "logs" / "clean.log").read_text(encoding="utf-8").splitlines()[-1])["only"] == [part]
    assert json.loads((run / "cfg" / "overlap.json").read_text(encoding="utf-8"))["expected_packs"] == []


def test_without_only_overlaps_settings_are_not_changed(staged):
    path, repo = staged
    edit_config(path, to="overlap")
    rp.run(path)
    assert "expected_packs" not in json.loads((repo / "out/runs/test-run/cfg/overlap.json").read_text(encoding="utf-8"))


def test_only_needs_a_clean_stage_that_runs_from_settings(staged, tsai_outputs):
    path, repo = staged
    prev = repo / "out" / "earlier" / "clean"
    shutil.copytree(tsai_outputs["cleaned"], prev)
    set_stage(path, "clean", {"mode": "adopt", "output": str(prev), "only": ["train/code-go/part-00000.parquet"]})
    with pytest.raises(rp.Stop, match="stages.clean.only limits the clean job"):
        rp.run(path)


def test_only_must_be_a_list_of_parts(staged):
    path, _ = staged
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["stages"]["clean"]["only"] = "train/code-go/part-00000.parquet"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match="stages.clean.only must be a list"):
        rp.run(path)


def test_to_in_the_config_stops_after_that_stage_and_checks_only_the_stages_up_to_it(staged):
    path, repo = staged
    cfg = json.loads(path.read_text(encoding="utf-8"))
    del cfg["stages"]["overlap"], cfg["stages"]["dedup"]
    cfg["to"] = "clean"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    assert "02 overlap" not in rp.plan(path)
    m = rp.run(path)
    assert [s["stage"] for s in m["stages"]] == ["clean"] and m["totals"] == {"cleaned": 13}
    edit_config(path, to="dedup", run_id="second")
    with pytest.raises(rp.Stop, match="stages.overlap is missing"):
        rp.run(path)


def test_from_in_the_config_resumes_a_recorded_run(staged):
    path, repo = staged
    edit_config(path, to="apply")
    first = rp.run(path)
    assert [s["stage"] for s in first["stages"]][-1] == "apply"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    del cfg["to"]
    cfg["from"] = "f2"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    m = rp.run(path)
    assert [s["stage"] for s in m["stages"]] == ["clean", "overlap", "dedup", "apply", "f2", "survivor_loss", "ledger"] and m["totals"]["final"] == 9


def test_from_must_not_come_after_to(staged):
    path, _ = staged
    edit_config(path, to="clean")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["from"] = "dedup"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match='"from": dedup comes after "to": clean'):
        rp.run(path)


def test_the_plan_follows_the_config(staged, tsai_outputs):
    path, repo = staged
    prev = repo / "out" / "earlier" / "clean"
    shutil.copytree(tsai_outputs["cleaned"], prev)
    set_stage(path, "clean", {"mode": "adopt", "output": str(prev)})
    edit_config(path, run_id="job-2", to="overlap")
    text = rp.plan(path)
    assert "run folder: out/runs/job-2" in text and "01 clean         adopt  out/earlier/clean" in text
    assert "02 overlap" in text and "03 dedup" not in text


def test_the_command_line_takes_only_config_and_plan(staged, capsys, monkeypatch):
    path, repo = staged
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--config", str(path), "--plan"])
    rp.main()
    assert "01 clean" in capsys.readouterr().out and not (repo / "out" / "runs").exists()
    for flag in (["--run-id", "x"], ["--adopt", "clean=y"], ["--only", "z"], ["--to", "dedup"], ["--from", "f2"]):
        monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--config", str(path), *flag])
        with pytest.raises(SystemExit) as e:
            rp.main()
        assert e.value.code == 2  # argparse: unrecognized arguments


def test_ledger_mode_b_adds_the_cleaners_drops(tmp_path, config, cleaned):
    raw = tmp_path / "raw"
    for f in cleaned.rglob("*.parquet"):
        t = pq.read_table(f)
        dst = raw / f.relative_to(cleaned)
        dst.parent.mkdir(parents=True, exist_ok=True)
        extra = t.slice(0, 1).to_pylist()
        extra[0]["doc_id"] = "x-" + extra[0]["doc_id"]
        pq.write_table(pa_concat(t, extra), dst)
    write_reports(cleaned, raw)  # mode B needs the cleaning job's report of every part
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["stages"]["ledger"] = {"raw": str(raw)}
    config.write_text(json.dumps(cfg), encoding="utf-8")
    m = rp.run(config)
    assert m["totals"] == {"raw": 17, "dropped_by_clean": 4, "cleaned": 13, "removed_by_dedup": 2, "dropped_by_f2": 2,
                           "final": 9}
    rec = next(s for s in m["stages"] if s["stage"] == "ledger")
    assert rec["clean_mode"] == "B" and rec["counts"]["clean_fix_by_text"] == 0
    assert m["by_pack"]["en-dclm"]["train"] == {"raw": 4, "dropped_by_clean": 1, "cleaned": 3, "removed_by_dedup": 1,
                                                "dropped_by_f2": 0, "final": 2}


def test_ledger_mode_b_with_a_pack_the_cleaner_emptied(tmp_path, config, cleaned):
    """A raw pack whose every document the cleaner dropped: in the ledger with 0 cleaned rows, absent from apply."""
    import pyarrow as pa
    raw = tmp_path / "raw"
    for f in cleaned.rglob("*.parquet"):
        dst = raw / f.relative_to(cleaned)
        dst.parent.mkdir(parents=True, exist_ok=True)
        t = pq.read_table(f)
        if f.relative_to(cleaned).as_posix() == "train/en-dclm/part-00000.parquet":
            ghost = dict(t.slice(0, 1).to_pylist()[0], doc_id="ghost-1", pack_id="ghost-pack")
            t = pa.concat_tables([t, pa.Table.from_pylist([ghost], schema=t.schema)])
        pq.write_table(t, dst)
    write_reports(cleaned, raw)
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["stages"]["ledger"] = {"raw": str(raw)}
    config.write_text(json.dumps(cfg), encoding="utf-8")
    m = rp.run(config)
    assert m["by_pack"]["ghost-pack"] == {"train": {"raw": 1, "dropped_by_clean": 1, "cleaned": 0, "removed_by_dedup": 0,
                                                    "dropped_by_f2": 0, "final": 0}}
    assert m["totals"]["dropped_by_clean"] == 1 and all(ch["ok"] for ch in m["checks"])


def pa_concat(t, rows):
    import pyarrow as pa
    return pa.concat_tables([t, pa.Table.from_pylist(rows, schema=t.schema)])


def test_ledger_raw_must_be_a_folder(tmp_path, config):
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["stages"]["ledger"] = {"raw": str(tmp_path / "no-such-raw")}
    config.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match="stages.ledger.raw"):
        rp.run(config)
    assert not (tmp_path / "runs").exists()


def test_from_ledger_reuses_earlier_stages(config):
    first = rp.run(config)
    again = rp.run(config, start="ledger")
    assert again["totals"] == first["totals"]
    assert [s["digest"] for s in again["stages"]] == [s["digest"] for s in first["stages"]]


def test_ledger_disagreeing_with_apply_per_pack_stops(config, monkeypatch):
    import ledger
    real = ledger.build

    def shifted(*a, **kw):
        s = real(*a, **kw)
        bp = s["by_pack"]
        bp["code-go"]["train"]["removed_by_dedup"] += 1
        bp["en-dclm"]["train"]["removed_by_dedup"] -= 1  # same totals, wrong packs
        return s
    monkeypatch.setattr(ledger, "build", shifted)
    with pytest.raises(rp.Stop, match="ledger per pack = apply per pack.*code-go/train"):
        rp.run(config)


def test_from_ledger_keeps_the_per_pack_table(config):
    first = rp.run(config)
    assert rp.run(config, start="ledger")["by_pack"] == first["by_pack"]
    assert rp.run(config, to="f2").get("by_pack") is None


# --- f2_pool.py as the F2 stage, and the reconcile stage ------------------------------------------------------------
FAKE_F2_MODULE = Path(__file__).resolve().parent / "fake_f2_module.py"


def test_f2_pool_gives_the_same_run_as_run_f2(tmp_path, config, tsai_outputs):
    one = rp.run(config)
    cfg = write_config(tmp_path / "pool.json", tsai_outputs, run_id="pooled")
    set_f2(cfg, script=str(FAKE_F2_MODULE), pool=True, workers=2)
    m = rp.run(cfg)
    f2 = next(s for s in m["stages"] if s["stage"] == "f2")
    assert f2["pool"] is True and f2["units"] == 2 and f2["pool_code_sha256"] == rp.sha256(rp.path(rp.POOL))
    assert m["totals"] == one["totals"] and m["by_pack"] == one["by_pack"] and all(ch["ok"] for ch in m["checks"])
    assert final_ids(tmp_path / "runs" / "pooled") == final_ids(tmp_path / "runs" / "test-run")
    assert "f2_pool.py" in rp.Run(cfg).plan()


def test_f2_pool_must_be_true_or_false(config):
    set_f2(config, pool="yes")
    with pytest.raises(rp.Stop, match="pool must be true or false"):
        rp.run(config)


def test_reconcile_needs_shards(config):
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["stages"]["reconcile"] = {}
    config.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match="reconcile needs stages.shards"):
        rp.run(config)  # whatever "to" says


def test_to_reconcile_needs_it_configured(shard_config):
    with pytest.raises(rp.Stop, match="needs stages.reconcile"):
        rp.run(shard_config, to="reconcile")


def test_reconcile_runs_after_the_shards(tmp_path, shard_config, monkeypatch):
    from test_reconcile_shards import write_shards

    def fake_shards(self):  # shard files in the writer's format, made from this run's final parts
        write_shards(self.dir, self.output("shards"), packs={"code-go"})
        return {"mode": "run", "command": ["fake"], "code_sha256": None, "output": "shards",
                "counts": {"written": 2, "failed": 0, "skipped": 0, "not_sharded": 1, "truncated": 0, "parts": 3}}
    monkeypatch.setattr(rp.Run, "stage_shards", fake_shards)
    cfg = json.loads(shard_config.read_text(encoding="utf-8"))
    cfg["stages"]["reconcile"] = {}
    shard_config.write_text(json.dumps(cfg), encoding="utf-8")
    m = rp.run(shard_config)
    rec = m["stages"][-1]
    assert rec["stage"] == "reconcile" and [s["stage"] for s in m["stages"]] == [s for s in rp.STAGES if s != "h3"]
    assert rec["counts"] == {"kept": 9, "in_shards": 6, "in_shard": 6, "not_selected": 2, "not_sharded": 1}
    assert "reconcile: no document is in two shards" in {c["check"] for c in m["checks"]}


def test_a_failed_reconciliation_stops_the_run(tmp_path, shard_config, monkeypatch):
    from test_reconcile_shards import write_shards

    def fake_shards(self):
        write_shards(self.dir, self.output("shards"), packs={"code-go"}, rows_read={"train/code-go/part-00000.parquet": 2})
        return {"mode": "run", "command": ["fake"], "code_sha256": None, "output": "shards",
                "counts": {"written": 2, "failed": 0, "skipped": 0, "not_sharded": 1, "truncated": 1, "parts": 3}}
    monkeypatch.setattr(rp.Run, "stage_shards", fake_shards)
    cfg = json.loads(shard_config.read_text(encoding="utf-8"))
    cfg["stages"]["reconcile"] = {}
    shard_config.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match="reconcile: .*not_reached"):
        rp.run(shard_config)


def test_the_shards_on_disk_are_verified_and_the_check_is_in_the_manifest(shard_config):
    m = rp.run(shard_config)
    assert [c for c in m["checks"] if c["check"].startswith("shards: the shard files on disk verify") and c["ok"]]


def test_shards_that_do_not_verify_stop_the_run_before_the_stage_is_recorded(tmp_path, shard_config, monkeypatch):
    import verify_shards
    monkeypatch.setattr(verify_shards, "verify", lambda *args, **kwargs: (["pk-a-train-000000: pk-a-train-000000.bin: sha256 1234abcd…, the manifest says 0000…"], {}))
    with pytest.raises(rp.Stop, match="the shard files on disk verify.*1 problem.*the first 1: pk-a-train-000000"):
        rp.run(shard_config)
    stages = [s["stage"] for s in json.loads((tmp_path / "runs" / "test-run" / "pipeline_manifest.json").read_text(encoding="utf-8"))["stages"]]
    assert stages[-1] == "ledger"


def test_a_verification_that_cannot_run_is_a_stop_not_a_traceback(shard_config, monkeypatch):
    import verify_shards

    def broken(*args, **kwargs):
        raise ValueError("expected value at line 1")
    monkeypatch.setattr(verify_shards, "verify", broken)
    with pytest.raises(rp.Stop, match="could not be verified: ValueError"):
        rp.run(shard_config)


def test_a_stage_digest_may_reuse_hashes_a_stage_computed(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 100)
    (tmp_path / "b.json").write_text(
        json.dumps({"seconds": 1, "k": 2}),
        encoding="utf-8",
    )

    plain = rp.digest(tmp_path)

    for given, same in (
        (rp.sha256(tmp_path / "a.bin"), True),
        ("0" * 64, False),
    ):
        cache = rp.HashCache()
        cache.remember(tmp_path / "a.bin", given)
        assert (rp.digest(tmp_path, cache)[0] == plain[0]) is same

    cache = rp.HashCache()
    cache.remember(tmp_path / "a.bin", rp.sha256(tmp_path / "a.bin"))
    assert rp.digest(tmp_path, cache) == plain

    other = rp.HashCache()
    other.remember(tmp_path / "a.bin", "0" * 64)
    assert rp.digest(tmp_path, other)[0] != plain[0]


def test_the_hashes_verification_read_go_to_the_hash_cache_not_a_second_read(shard_config, monkeypatch):
    import verify_shards
    monkeypatch.setattr(verify_shards, "verify", lambda *args, **kwargs: ([], {"pk-a-train-000000.bin": "ab" * 32}))
    remembered = []
    monkeypatch.setattr(rp.HashCache, "remember", lambda self, path, digest: remembered.append((Path(path).name, digest)))
    rp.run(shard_config)
    assert [r for r in remembered if r[0].endswith(".bin")] == [("pk-a-train-000000.bin", "ab" * 32)]  # apply also remembers its hard links


def test_a_failed_part_stops_the_run_and_names_the_reason(tmp_path, shard_config, monkeypatch):
    monkeypatch.setenv("FAKE_SHARDS_FAIL", "1")
    with pytest.raises(rp.Stop, match="no part failed or was skipped.*first: train/code-go/part-00000.parquet: made up"):
        rp.run(shard_config)


# --- scale and robustness (the scale audit, 14 Nov) -----------------------------------------------------------------
def test_records_are_counted_not_lines(tmp_path):
    f = tmp_path / "list.csv"
    write_csv(f, HEADER, [["p", "train", "p/part-00000.parquet", 0, "two\nlines"], ["p", "train", "p/part-00000.parquet", 1, "b"]])
    assert rp.csv_rows(f) == 2 and len(f.read_text(encoding="utf-8").splitlines()) == 4


def test_records_of_a_csv_whose_header_names_are_quoted(tmp_path):
    """h3.py writes h3_matches.csv with pyarrow's write_csv, which quotes every header name ("pack_id_a"). Before this,
    csv_rows asked pyarrow for a column named with the quotes, and every run with stages.h3 stopped after H3."""
    import pyarrow.csv as pacsv
    f = tmp_path / "h3_matches.csv"
    pacsv.write_csv(pa.table({"pack_id_a": ["a", "b"], "coverage": [0.7, 0.9]}), f,
                    write_options=pacsv.WriteOptions(quoting_style="needed"))
    assert f.read_text(encoding="utf-8").startswith('"pack_id_a"') and rp.csv_rows(f) == 2
    empty = tmp_path / "no_matches.csv"  # h3.py's output when nothing qualifies: the header alone
    pacsv.write_csv(pa.table({"pack_id_a": pa.array([], pa.string())}), empty)
    assert rp.csv_rows(empty) == 0


@pytest.mark.parametrize("key, value, message", [("hash_cache", "yes", "hash_cache"), ("apply_workers", 0, "stages.apply.workers")])
def test_new_config_keys_are_checked(tmp_path, config, key, value, message):
    cfg = json.loads(config.read_text(encoding="utf-8"))
    if key == "hash_cache":
        cfg["hash_cache"] = value
    else:
        cfg["stages"]["apply"] = {"workers": value}
    config.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(rp.Stop, match=message):
        rp.run(config)


def test_a_resumed_run_reuses_the_hash_cache(tmp_path, config):
    first = rp.run(config)
    store = tmp_path / "runs" / "test-run" / "cache" / "sha256.json"
    assert store.is_file() and json.loads(store.read_text(encoding="utf-8"))["sha256"]
    run = rp.Run(config)
    m = run.execute(start="ledger")
    assert [s["digest"] for s in m["stages"]] == [s["digest"] for s in first["stages"]]
    new_files = [f for f in (tmp_path / "runs" / "test-run" / "ledger").rglob("*") if f.is_file() and f.suffix != ".json"]
    assert run.cache.misses == len(new_files) and run.cache.hits > 0  # only the rewritten ledger is read; the rest is cached


def test_without_the_hash_cache_the_digests_are_the_same(tmp_path, config, tsai_outputs):
    a = rp.run(config)
    cfg = write_config(tmp_path / "nocache.json", tsai_outputs, run_id="nocache")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    data["hash_cache"] = False
    cfg.write_text(json.dumps(data), encoding="utf-8")
    b = rp.run(cfg)
    assert [s["digest"] for s in a["stages"]] == [s["digest"] for s in b["stages"]]
    assert not (tmp_path / "runs" / "nocache" / "cache").exists()


# --- patilvijay23's review of PR #46 (15 Nov) -------------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["ledger.partial", "ledger.old", "deduped.lock", "ledger"])
def test_an_input_in_a_folder_the_run_writes_is_refused(tmp_path, tsai_outputs, name):
    """stages.clean.output at <run>/ledger.partial passed validation, and the ledger then deleted the cleaned parts. The
    config now stops before any stage runs, and the parts are untouched."""
    import shutil
    target = tmp_path / "runs" / "test-run" / name
    shutil.copytree(tsai_outputs["cleaned"], target)
    before = sorted(p.relative_to(target).as_posix() for p in target.rglob("*.parquet"))
    cfg = write_config(tmp_path / "c.json", {**tsai_outputs, "cleaned": target})
    with pytest.raises(rp.Stop, match="folder of the run itself"):
        rp.run(cfg)
    assert sorted(p.relative_to(target).as_posix() for p in target.rglob("*.parquet")) == before


def test_a_raw_folder_the_run_writes_is_refused(tmp_path, tsai_outputs):
    raw = tmp_path / "runs" / "test-run" / "ledger.old"
    raw.mkdir(parents=True)
    cfg = write_config(tmp_path / "c.json", tsai_outputs, ledger={"raw": str(raw)})
    with pytest.raises(rp.Stop, match="stages.ledger.raw .* is a folder of the run itself"):
        rp.run(cfg)
    assert raw.is_dir()


def test_run_varying_fields_of_overlap_and_dedup_summaries_do_not_change_a_digest(tmp_path):
    """When the runner runs overlap.py and dedup.py, their summaries record wall time, peak memory and the run's own output
    folders; two identical runs must still get the same stage digest."""
    a, b = tmp_path / "a", tmp_path / "b"
    for d, wall, rss, out in ((a, 71.2, 812.0, "out/pipeline/run-1/overlap"), (b, 61.8, 790.5, "out/pipeline/run-2/overlap")):
        d.mkdir()
        (d / "overlap_summary.json").write_text(json.dumps({
            "documents_all": 13, "wall_seconds": wall, "peak_rss_mb": rss,
            "config": {"out": out, "results": out, "inputs": "out/cleaned", "k": 5}}), encoding="utf-8")
    assert rp.digest(a)[0] == rp.digest(b)[0]
    (b / "overlap_summary.json").write_text(json.dumps({
        "documents_all": 14, "wall_seconds": 1.0, "peak_rss_mb": 1.0,
        "config": {"out": "x", "results": "x", "inputs": "out/cleaned", "k": 5}}), encoding="utf-8")
    assert rp.digest(a)[0] != rp.digest(b)[0]  # a real difference still shows


# --- task 4.8: the run's own intermediate Parquet, kept (default) or dropped once reconcile has passed (16 Nov) --------
# The chain's kept documents: train code-go/part-00000 (g1-g4) and part-00001 (g5, g6), which the stand-in shard stage
# puts in shards; train en-dclm/part-00000 (e0, e1), a pack the shard stage is not asked for (not_selected); heldout
# code-go/part-00000 (h0), not_sharded. So a drop takes the two code-go train parts and leaves the other two.
SHARD_COUNTS = {"written": 2, "failed": 0, "skipped": 0, "not_sharded": 1, "truncated": 0, "parts": 3}
THROUGH_LEDGER = tuple(s for s in rp.STAGES[: rp.STAGES.index("ledger") + 1] if s != "h3")
SHARDED = ["train/code-go/part-00000.parquet", "train/code-go/part-00001.parquet"]
NOT_IN_SHARDS = ["heldout/code-go/part-00000.parquet", "train/en-dclm/part-00000.parquet"]


def with_reconcile(path, monkeypatch, intermediates=None, after_shards=None, **shard_kw):
    """Give the config at `path` a reconcile stage, and the run a shard stage that writes shards in the writer's format
    from the run's final parts (as test_reconcile_runs_after_the_shards does). Sets "intermediates" when given;
    after_shards(run) is called once the shards are written."""
    from test_reconcile_shards import write_shards

    def fake_shards(self):
        write_shards(self.dir, self.output("shards"), packs={"code-go"}, **shard_kw)
        if after_shards:
            after_shards(self)
        return {"mode": "run", "command": ["fake"], "code_sha256": None, "output": "shards", "counts": dict(SHARD_COUNTS)}
    monkeypatch.setattr(rp.Run, "stage_shards", fake_shards)
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["stages"]["reconcile"] = {}
    if intermediates is not None:
        cfg["intermediates"] = intermediates
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


def parquet_under(folder):
    return sorted(p.relative_to(folder).as_posix() for p in Path(folder).rglob("*.parquet"))


def snapshot(folder):
    """{relative path: sha256} of every file in a folder, to show that a run left it alone."""
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(Path(folder).rglob("*")) if p.is_file()}


def write_reports(cleaned, raw):
    """The cleaning job's per-part reports for mode B (test_ledger.write_reports)."""
    from test_ledger import write_reports as w
    return w(cleaned, raw)


def manifest_of(run):
    return json.loads((run / "pipeline_manifest.json").read_text(encoding="utf-8"))


def link_dir(target, link):
    """A directory link: a symlink, or a junction on Windows, where a symlink needs a privilege."""
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        if sys.platform != "win32":
            pytest.skip("cannot make a directory link here")
        import _winapi
        _winapi.CreateJunction(str(target), str(link))


def test_intermediates_are_kept_unless_the_config_says_drop(tmp_path, shard_config, monkeypatch):
    m = rp.run(with_reconcile(shard_config, monkeypatch))
    run = tmp_path / "runs" / "test-run"
    assert m["intermediates"] == {"mode": "keep"} and m["stages"][-1]["stage"] == "reconcile"
    assert len(parquet_under(run / "deduped")) == 4 and len(parquet_under(run / "final")) == 4
    assert "intermediates: keep" in rp.plan(shard_config)


def test_drop_deletes_only_the_parts_whose_kept_documents_are_all_in_shards(tmp_path, shard_config, tsai_outputs, monkeypatch, capsys):
    adopted = snapshot(tsai_outputs["cleaned"])
    kept = rp.run(with_reconcile(shard_config, monkeypatch))  # the same chain with everything kept, to compare with
    run = tmp_path / "runs" / "test-run"
    linked = sum((run / "deduped" / p).stat().st_nlink > 1 for p in SHARDED)  # parts apply hard-linked from the adopted folder
    left = {f: {p: sha(run / f / p) for p in NOT_IN_SHARDS} for f in ("deduped", "final")}
    shutil.rmtree(run)
    plan = rp.plan(with_reconcile(shard_config, monkeypatch, intermediates="drop"))
    assert "intermediates: drop" in plan and "runs/test-run/deduped and " in plan and "runs/test-run/final;" in plan
    m = rp.run(shard_config)
    # the two code-go train parts are in shards: their Parquet is gone from both folders. The held-out part and the
    # part of the pack the shard stage was not asked for are in no shard: they stay, byte for byte
    assert parquet_under(run / "deduped") == NOT_IN_SHARDS and parquet_under(run / "final") == NOT_IN_SHARDS
    assert {f: {p: sha(run / f / p) for p in NOT_IN_SHARDS} for f in ("deduped", "final")} == left
    assert final_ids(run) == ["e0", "e1", "h0"]
    # what the stages reported stays, and so do the ledger, the shards and the reconciliation
    assert (run / "deduped" / "apply_dedup_summary.json").is_file() and (run / "final" / "train" / "f2_summary.json").is_file()
    assert len(list((run / "final").rglob("*.f2.json"))) == 4
    assert len(parquet_under(run / "ledger")) == 3 and len(parquet_under(run / "shards")) == 2
    assert (run / "reconcile" / "reconcile_docs.parquet").is_file() and (run / "report" / "survivor_loss.csv").is_file()
    # the adopted folder is an input: every file is still there, the ones the run hard-linked too
    assert snapshot(tsai_outputs["cleaned"]) == adopted
    d = m["intermediates"]
    assert (d["mode"], d["state"], d["parts"]) == ("drop", "done", {"dropped": 2, "left": 2})
    assert sorted(d["folders"]) == ["deduped", "final"]
    assert d["folders"]["deduped"] == {"stage": "apply", "parquet_files": 2, "bytes": d["folders"]["deduped"]["bytes"], "hard_links": linked}
    assert d["folders"]["final"] == {"stage": "f2", "parquet_files": 2, "bytes": d["folders"]["final"]["bytes"], "hard_links": 0}
    assert d["folders"]["deduped"]["bytes"] > 0 and d["folders"]["final"]["bytes"] > 0
    assert manifest_of(run)["intermediates"] == d
    # the manifest still describes the folders as they were checked, before the drop
    digests = lambda man: {s["stage"]: s["digest"] for s in man["stages"] if s["stage"] in THROUGH_LEDGER}
    assert digests(m) == digests(kept) and m["totals"] == kept["totals"] and all(ch["ok"] for ch in m["checks"])
    assert "intermediates: dropped 2 part(s), left 2: deduped 2 Parquet file(s)" in capsys.readouterr().err


def test_a_part_with_a_document_the_shards_do_not_hold_is_left(tmp_path, shard_config, monkeypatch):
    """A written part goes only when reconcile_docs.parquet shows all its kept documents in a shard or left out for a
    stated reason: one row with any other status keeps the whole part. (reconcile itself stops a run on a missing
    document; this is the drop's own reading of the statuses.)"""
    import pyarrow as pa
    rp.run(with_reconcile(shard_config, monkeypatch))
    run = tmp_path / "runs" / "test-run"
    r = rp.Run(shard_config)
    assert r.droppable_parts() == (SHARDED, 2)
    docs = run / "reconcile" / "reconcile_docs.parquet"
    schema = pq.read_schema(docs)
    rows = pq.read_table(docs).to_pylist()
    for status in ("not_selected", "not_sharded", "missing", "not_reached", "part_failed", None):
        for row in rows:
            if row["doc_id"] == "g5":
                row["shard_status"] = status
            if row["doc_id"] == "g1":
                row["shard_status"] = "left_out:empty"
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), docs)
        # part-00001 holds g5, so it stays whatever that status is; part-00000's g1 was left out for a stated reason
        assert r.droppable_parts() == (SHARDED[:1], 3), status
    summary = run / "shards" / "shards_summary.json"
    s = json.loads(summary.read_text(encoding="utf-8"))
    s["parts"][SHARDED[0]]["status"] = "failed"
    summary.write_text(json.dumps(s), encoding="utf-8")
    assert r.droppable_parts() == ([], 4)  # and a part the shard stage does not report as written stays too


def test_drop_never_touches_the_cleaned_folder_not_even_one_this_run_wrote(tmp_path, staged, tsai_outputs, monkeypatch):
    path, repo = staged
    tokenizer = tmp_path / "tokenizer.json"
    tokenizer.write_text("{}", encoding="utf-8")
    set_stage(path, "shards", {"script": str(FAKE_SHARDS), "tokenizer": str(tokenizer), "packs": ["code-go"], "dataset_version": "sample"})
    with_reconcile(path, monkeypatch, intermediates="drop")
    m = rp.run(path)
    run = repo / "out" / "runs" / "test-run"
    assert m["stages"][0]["mode"] == "run" and sorted(m["intermediates"]["folders"]) == ["deduped", "final"]
    assert parquet_under(run / "deduped") == NOT_IN_SHARDS and parquet_under(run / "final") == NOT_IN_SHARDS
    # another run may have adopted <run>/clean, so it stays whole: the same files the clean job wrote (the stand-in adds its job_summary.json)
    kept = snapshot(run / "clean")
    assert kept.pop("job_summary.json") and kept == snapshot(tsai_outputs["cleaned"]) and len(parquet_under(run / "clean")) == 4


@pytest.mark.parametrize("reconcile, to", [(False, None), (True, "ledger"), (True, "shards")])
def test_drop_needs_a_run_that_ends_at_reconcile(tmp_path, shard_config, reconcile, to):
    cfg = json.loads(shard_config.read_text(encoding="utf-8"))
    cfg["intermediates"] = "drop"
    if reconcile:
        cfg["stages"]["reconcile"] = {}
    if to:
        cfg["to"] = to
    shard_config.write_text(json.dumps(cfg), encoding="utf-8")
    for call in (rp.run, rp.plan):
        with pytest.raises(rp.Stop, match="needs a run that ends at reconcile"):
            call(shard_config)
    assert not (tmp_path / "runs").exists()


def test_intermediates_must_be_keep_or_drop(tmp_path, config):
    edit_config(config, intermediates=True)
    with pytest.raises(rp.Stop, match="intermediates is True, expected keep or drop"):
        rp.run(config)
    assert not (tmp_path / "runs").exists()


def test_a_failed_reconciliation_drops_nothing(tmp_path, shard_config, monkeypatch):
    with pytest.raises(rp.Stop, match="reconcile: .*not_reached"):
        rp.run(with_reconcile(shard_config, monkeypatch, intermediates="drop",
                              rows_read={"train/code-go/part-00000.parquet": 2}))
    run = tmp_path / "runs" / "test-run"
    assert len(parquet_under(run / "deduped")) == 4 and len(parquet_under(run / "final")) == 4
    on_disk = manifest_of(run)
    assert on_disk["intermediates"] == {"mode": "drop"} and on_disk["stages"][-1]["stage"] == "shards"


def test_a_finished_run_can_be_resumed_at_reconcile_to_drop(tmp_path, shard_config, monkeypatch):
    rp.run(with_reconcile(shard_config, monkeypatch))
    run = tmp_path / "runs" / "test-run"
    edit_config(shard_config, intermediates="drop")
    m = rp.run(shard_config, start="reconcile")
    assert m["intermediates"]["state"] == "done" and parquet_under(run / "final") == NOT_IN_SHARDS
    assert [s["stage"] for s in m["stages"]] == [s for s in rp.STAGES if s != "h3"]


@pytest.mark.parametrize("state", ["done", "started"])
def test_a_run_that_dropped_its_parquet_cannot_be_resumed_or_rerun_in_place(tmp_path, shard_config, monkeypatch, state):
    """"started" is what a drop that was interrupted leaves in the manifest: refused like a finished one."""
    run = tmp_path / "runs" / "test-run"
    if state == "done":
        rp.run(with_reconcile(shard_config, monkeypatch, intermediates="drop"))
    else:
        rp.run(with_reconcile(shard_config, monkeypatch))
        m = manifest_of(run)
        m["intermediates"] = {"mode": "drop", "state": "started"}
        (run / "pipeline_manifest.json").write_text(json.dumps(m), encoding="utf-8")
    assert manifest_of(run)["intermediates"]["state"] == state
    for start in (None, "f2", "reconcile"):
        with pytest.raises(rp.Stop, match=f"dropped its intermediate Parquet .*{state}.*new run_id"):
            rp.run(shard_config, start=start)
    edit_config(shard_config, intermediates="keep")  # nor with the switch turned back
    with pytest.raises(rp.Stop, match="new run_id"):
        rp.run(shard_config, start="ledger")


def test_the_manifest_says_started_before_the_first_file_goes(tmp_path, shard_config, monkeypatch):
    run, seen = tmp_path / "runs" / "test-run", []
    unlink = Path.unlink

    def watched(self, *a, **kw):
        if self.suffix == ".parquet" and run in self.parents and self.parent.parent.parent.name in ("deduped", "final"):
            seen.append((manifest_of(run)["intermediates"], len(parquet_under(run / "deduped")) + len(parquet_under(run / "final"))))
        return unlink(self, *a, **kw)
    with_reconcile(shard_config, monkeypatch, intermediates="drop")
    monkeypatch.setattr(Path, "unlink", watched)
    rp.run(shard_config)
    assert seen[0] == ({"mode": "drop", "state": "started"}, 8) and len(seen) == 4


def failing_unlink(monkeypatch, run, fail_at):
    """Path.unlink fails on the fail_at-th Parquet part deleted from the run's deduped/ or final/ (1 = the first)."""
    unlink, calls = Path.unlink, []

    def flaky(self, *a, **kw):
        if self.suffix == ".parquet" and run in self.parents and self.parent.parent.parent.name in ("deduped", "final"):
            calls.append(self)
            if len(calls) == fail_at:
                raise PermissionError(13, "made up: access denied")
        return unlink(self, *a, **kw)
    monkeypatch.setattr(Path, "unlink", flaky)


def test_a_drop_that_cannot_delete_its_first_file_leaves_the_run_whole_and_resumable(tmp_path, shard_config, monkeypatch):
    run = tmp_path / "runs" / "test-run"
    with_reconcile(shard_config, monkeypatch, intermediates="drop")
    with monkeypatch.context() as mp:
        failing_unlink(mp, run, fail_at=1)
        with pytest.raises(rp.Stop, match="could not delete .*nothing was deleted"):
            rp.run(shard_config)
    assert len(parquet_under(run / "deduped")) == 4 and len(parquet_under(run / "final")) == 4
    assert manifest_of(run)["intermediates"] == {"mode": "drop"}  # the "started" mark was taken back
    m = rp.run(shard_config, start="reconcile")  # so the run can be picked up again, and then drops
    assert m["intermediates"]["state"] == "done" and parquet_under(run / "final") == NOT_IN_SHARDS


def test_a_drop_that_fails_halfway_stays_marked_started(tmp_path, shard_config, monkeypatch):
    run = tmp_path / "runs" / "test-run"
    with_reconcile(shard_config, monkeypatch, intermediates="drop")
    with monkeypatch.context() as mp:
        failing_unlink(mp, run, fail_at=2)
        with pytest.raises(rp.Stop, match="after 1 file.s. were deleted; the manifest records the drop as started"):
            rp.run(shard_config)
    assert len(parquet_under(run / "deduped")) + len(parquet_under(run / "final")) == 7
    assert manifest_of(run)["intermediates"] == {"mode": "drop", "state": "started"}
    with pytest.raises(rp.Stop, match="new run_id"):
        rp.run(shard_config, start="reconcile")


def test_a_read_only_part_stops_the_drop_before_anything_is_deleted(tmp_path, shard_config, monkeypatch):
    """On Windows a read-only file cannot be deleted, and the attribute belongs to the adopted file too when the part is
    a hard link, so it is not changed: the drop stops first, with every file in place."""
    if os.name != "nt":
        pytest.skip("deleting a read-only file needs no change of the file on this system")
    import stat
    run = tmp_path / "runs" / "test-run"

    def lock_one(r):
        os.chmod(r.dir / "final" / SHARDED[1], stat.S_IREAD)
    with_reconcile(shard_config, monkeypatch, intermediates="drop", after_shards=lock_one)
    try:
        with pytest.raises(rp.Stop, match="cannot be deleted .read-only.; nothing was deleted"):
            rp.run(shard_config)
        assert len(parquet_under(run / "deduped")) == 4 and len(parquet_under(run / "final")) == 4
        assert manifest_of(run)["intermediates"] == {"mode": "drop"}
    finally:
        os.chmod(run / "final" / SHARDED[1], stat.S_IWRITE | stat.S_IREAD)


def test_drop_refuses_the_shards_or_an_input_inside_a_folder_it_deletes_from(tmp_path, staged, monkeypatch):
    path, repo = staged
    run = repo / "out" / "runs" / "test-run"
    tokenizer = tmp_path / "tokenizer.json"
    tokenizer.write_text("{}", encoding="utf-8")
    shards = {"script": str(FAKE_SHARDS), "tokenizer": str(tokenizer), "packs": ["code-go"], "dataset_version": "sample"}
    set_stage(path, "shards", {**shards, "out": str(run / "final" / "train" / "shards")})
    with_reconcile(path, monkeypatch, intermediates="drop")
    with pytest.raises(rp.Stop, match="stages.shards.out .* lies in it"):
        rp.run(path)
    set_stage(path, "shards", shards)
    edit_stage(path, "clean", input=str(run / "deduped" / "raw"))
    with pytest.raises(rp.Stop, match="stages.clean.input .* lies in it"):
        rp.run(path)
    assert not run.exists()  # stopped in validation, before any stage


@pytest.mark.parametrize("link", ["final/train/code-go", "final/train", "final", "deduped/train/code-go"])
def test_drop_never_follows_a_folder_link_out_of_its_place(tmp_path, shard_config, monkeypatch, link):
    """A pack, split or stage folder that has become a link to somewhere else (here: after the shards were written):
    the drop stops before the first file goes, in the folder with the link and in the other one."""
    run, elsewhere, before = tmp_path / "runs" / "test-run", tmp_path / "elsewhere", {}

    def swap(r):
        shutil.move(str(r.dir / link), str(elsewhere))
        link_dir(elsewhere, r.dir / link)
        before.update(snapshot(elsewhere))
    with_reconcile(shard_config, monkeypatch, intermediates="drop", after_shards=swap)
    with pytest.raises(rp.Stop, match="is a link to somewhere else; nothing was deleted"):
        rp.run(shard_config)
    other = "deduped" if link.startswith("final") else "final"
    assert before and snapshot(elsewhere) == before and len(parquet_under(run / other)) == 4
    assert manifest_of(run)["intermediates"] == {"mode": "drop"}


def test_a_link_to_another_folder_of_the_same_run_is_not_followed_either(tmp_path, shard_config, monkeypatch):
    """final/train/code-go as a link to another folder of the same run: inside the run folder, but not the part's own
    place, so nothing there is deleted either."""
    run = tmp_path / "runs" / "test-run"

    def swap(r):
        decoy = r.dir / "report" / "decoy"
        shutil.move(str(r.dir / "final" / "train" / "code-go"), str(decoy))
        link_dir(decoy, r.dir / "final" / "train" / "code-go")
    with_reconcile(shard_config, monkeypatch, intermediates="drop", after_shards=swap)
    with pytest.raises(rp.Stop, match="is a link to somewhere else; nothing was deleted"):
        rp.run(shard_config)
    assert len(parquet_under(run / "report" / "decoy")) == 2 and len(parquet_under(run / "deduped")) == 4


def test_with_nothing_to_drop_the_run_is_not_marked_and_stays_resumable(tmp_path, shard_config, monkeypatch):
    run = tmp_path / "runs" / "test-run"
    with_reconcile(shard_config, monkeypatch, intermediates="drop")
    monkeypatch.setattr(rp.Run, "droppable_parts", lambda self: ([], 4))
    m = rp.run(shard_config)
    assert m["intermediates"]["parts"] == {"dropped": 0, "left": 4} and "state" not in m["intermediates"]
    assert manifest_of(run)["intermediates"] == m["intermediates"]
    assert len(parquet_under(run / "deduped")) == 4 and len(parquet_under(run / "final")) == 4
    edit_config(shard_config, intermediates="keep")
    assert rp.run(shard_config, start="reconcile")["intermediates"] == {"mode": "keep"}  # not refused: nothing was dropped


@pytest.mark.parametrize("name", ["train/code-go/../part-00000.parquet", "train/../code-go/part-00000.parquet", "train/code-go/part-00000.txt",
                                  "train/code-go/sub/part-00000.parquet", "train/part-00000.parquet", "test/code-go/part-00000.parquet",
                                  "train//part-00000.parquet", "/train/code-go/part-00000.parquet", "train/code-go/a\\part-00000.parquet",
                                  "train/../part-00000.parquet", "train/./part-00000.parquet"])
def test_only_a_part_name_is_ever_deleted(tmp_path, shard_config, monkeypatch, name):
    if name.endswith("a\\part-00000.parquet") and os.name != "nt":
        pytest.skip("a backslash is an ordinary character in a file name here")
    rp.run(with_reconcile(shard_config, monkeypatch))
    with pytest.raises(rp.Stop, match="is not a part name .*nothing was deleted"):
        rp.Run(shard_config).drop_files([name])


def test_a_part_that_is_already_missing_is_skipped_and_a_folder_that_cannot_be_written_stops_the_drop(tmp_path, shard_config, monkeypatch):
    rp.run(with_reconcile(shard_config, monkeypatch))
    run, r = tmp_path / "runs" / "test-run", rp.Run(shard_config)
    assert [(n, f.relative_to(run / n).as_posix()) for n, f in r.drop_files(SHARDED)] == [(n, p) for n in ("deduped", "final") for p in SHARDED]
    (run / "deduped" / SHARDED[0]).unlink()
    assert [(n, f.relative_to(run / n).as_posix()) for n, f in r.drop_files(SHARDED)] == [("deduped", SHARDED[1]), ("final", SHARDED[0]), ("final", SHARDED[1])]
    access = os.access
    monkeypatch.setattr(rp.os, "access", lambda p, mode: False if Path(p).is_dir() else access(p, mode))
    with pytest.raises(rp.Stop, match="cannot be deleted .read-only.; nothing was deleted"):
        r.drop_files(SHARDED)


# --- gate 12 of the shard job request: the expected inventory, "inventory" in the config (16 Nov) -------------------------
# A run with an inventory is the production run: stages.ledger.raw (mode B), a shard stage for every pack, reconcile, and
# no earlier "to". The raw parts here are the cleaned parts plus one document each that the cleaner "dropped", so a part's
# raw rows are not its cleaned rows. The inventory is made from the raw parts alone, as the real one is made from the input
# manifest, and the adopted clean job's job_summary.json names that manifest.
ALL_PACKS = ["code-go", "en-dclm"]
INPUT_MANIFEST = "ab" * 32
PACKS_CHECK = "inventory: every listed pack is in the ledger, and no other pack has kept documents"
ON_LEDGER = ["inventory: made from the input manifest the clean job read", "inventory: the ledger accounts for every raw document (mode B)",
             "inventory: the ledger holds exactly the listed parts", PACKS_CHECK,
             "inventory: each part's raw file is the listed one (sha256)", "inventory: each part's raw rows are the listed ones"]
ON_SHARDS = ["inventory: the shard summary holds exactly the listed parts", "inventory: every part ended in a listed status",
             "inventory: every part is of its listed pack"]
INVENTORY_SHARD_COUNTS = {"written": 3, "failed": 0, "skipped": 0, "not_sharded": 1, "truncated": 0, "shards": 3, "parts": 4}


def write_inventory(tmp_path, change=None):
    """expected_inventory.json from the raw parts under tmp_path/raw; change(inventory) edits it before it is written."""
    raw, parts = tmp_path / "raw", []
    for f in sorted(raw.rglob("*.parquet")):
        rel = f.relative_to(raw).as_posix()
        split, pack, _ = rel.split("/")
        parts.append({"split": split, "pack_id": pack, "part": rel, "raw_sha256": sha(f), "raw_rows": pq.read_metadata(f).num_rows,
                      "expected": "written" if split == "train" else "not_sharded"})
    inv = {"_comment": "made up", "input_manifest_sha256": INPUT_MANIFEST, "packs": list(ALL_PACKS), "parts": parts}
    if change:
        change(inv)
    path = tmp_path / "expected_inventory.json"
    path.write_text(json.dumps(inv), encoding="utf-8")
    return path


def clean_job_names(cleaned, manifest_sha256):
    """Set (or with None remove) the input manifest the adopted clean job's job_summary.json names."""
    f = cleaned / "job_summary.json"
    s = json.loads(f.read_text(encoding="utf-8"))
    s.pop("manifest_sha256", None)
    if manifest_sha256 is not None:
        s["manifest_sha256"] = manifest_sha256
    f.write_text(json.dumps(s), encoding="utf-8")


def with_inventory(path, tmp_path, monkeypatch, change=None, after_shards=None, raw_extra=None, script=False):
    """Give the config at `path` (shard_config) what a run with an inventory needs: a clean job summary that names its
    input manifest, the raw parts for the ledger, a shard stage for every pack, reconcile, and the inventory.
    The shard stage writes shards in the writer's format from the run's final parts (after_shards(run) is called once
    they are written); with script=True it is the runner's own stage_shards with the stand-in run_shards.py, and
    reconcile is replaced, since the stand-in writes no documents to reconcile. raw_extra: {part: [document]} added to
    a raw part only (documents the cleaner dropped). Returns the config path."""
    from test_reconcile_shards import write_shards
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cleaned, raw = Path(cfg["stages"]["clean"]["output"]), tmp_path / "raw"
    clean_job_names(cleaned, INPUT_MANIFEST)
    for f in sorted(cleaned.rglob("*.parquet")):
        dst = raw / f.relative_to(cleaned)
        dst.parent.mkdir(parents=True, exist_ok=True)
        t = pq.read_table(f)
        gone = t.slice(0, 1).to_pylist()
        gone[0]["doc_id"] = "x-" + gone[0]["doc_id"]
        gone += (raw_extra or {}).get(f.relative_to(cleaned).as_posix(), [])
        pq.write_table(pa_concat(t, gone), dst)
    write_reports(cleaned, raw)

    def fake_shards(self):
        write_shards(self.dir, self.output("shards"))
        if after_shards:
            after_shards(self)
        return {"mode": "run", "command": ["fake"], "code_sha256": None, "output": "shards", "counts": dict(INVENTORY_SHARD_COUNTS)}

    def fake_reconcile(ledger, shards, out, packs):
        out.mkdir(parents=True, exist_ok=True)
        (out / "reconcile_summary.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        return {"checks": [{"check": "made up", "ok": True, "detail": ""}], "code_sha256": None, "kept": 9, "in_shards": 8, "totals": {}}
    if script:
        import reconcile_shards
        monkeypatch.setattr(reconcile_shards, "reconcile", fake_reconcile)
    else:
        monkeypatch.setattr(rp.Run, "stage_shards", fake_shards)
    cfg["stages"]["ledger"] = {"raw": str(raw)}
    cfg["stages"]["shards"]["packs"] = list(ALL_PACKS)
    cfg["stages"]["reconcile"] = {}
    cfg["inventory"] = str(write_inventory(tmp_path, change))
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


def edit_stages(path, change):
    cfg = json.loads(path.read_text(encoding="utf-8"))
    change(cfg["stages"])
    path.write_text(json.dumps(cfg), encoding="utf-8")


def inventory_report(run):
    return json.loads((run / "inventory_check.json").read_text(encoding="utf-8"))


def inventory_checks(m, stage):
    return [c["check"] for s in m["stages"] if s["stage"] == stage for c in s["checks"] if c["check"].startswith("inventory: ")]


def stage_record(m, stage):
    return next(s for s in m["stages"] if s["stage"] == stage)


def part_of(inv, name):
    return next(p for p in inv["parts"] if p["part"] == name)


def test_a_run_that_matches_its_inventory_passes_and_says_which_inventory(tmp_path, shard_config, monkeypatch):
    m = rp.run(with_inventory(shard_config, tmp_path, monkeypatch))
    run, file = tmp_path / "runs" / "test-run", tmp_path / "expected_inventory.json"
    assert m["stages"][-1]["stage"] == "reconcile" and all(c["ok"] for c in m["checks"])
    assert m["stages"][-1]["counts"] == {"kept": 9, "in_shards": 8, "in_shard": 8, "not_sharded": 1}
    assert m["totals"]["raw"] == 17 and m["totals"]["dropped_by_clean"] == 4
    assert m["inventory"] == {"file": file.resolve().as_posix(), "sha256": sha(file), "input_manifest_sha256": INPUT_MANIFEST,
                              "packs": 2, "parts": 4, "expected": {"not_sharded": 1, "written": 3},
                              "checked": {"ledger": sha(file), "reconcile": sha(file)}, "report": "inventory_check.json"}
    # the ledger side is checked on entry to the shard stage (the ledger stage is recorded by then), and again at the end
    assert inventory_checks(m, "ledger") == [] and inventory_checks(m, "shards") == ON_LEDGER
    assert inventory_checks(m, "reconcile") == ON_LEDGER + ON_SHARDS
    assert [s["stage"] for s in m["stages"] if "inventory_sha256" in s] == ["shards", "reconcile"]
    assert stage_record(m, "shards")["inventory_sha256"] == stage_record(m, "reconcile")["inventory_sha256"] == sha(file)
    report = inventory_report(run)
    assert report["ok"] is True and report["checked_after"] == "reconcile" and report["run_id"] == "test-run"
    assert [c["check"] for c in report["checks"]] == ON_LEDGER + ON_SHARDS and report["inventory"]["sha256"] == sha(file)
    assert report["ledger"]["rows"] == 17 and report["shards"]["statuses"] == {"not_sharded": 1, "written": 3}
    assert manifest_of(run)["inventory"] == m["inventory"] and "synthetic text" not in (run / "inventory_check.json").read_text(encoding="utf-8")


def test_the_report_names_paths_as_the_manifest_does(tmp_path, shard_config, monkeypatch):
    """Inside the repository a path is shown relative to it, in the report as in the manifest: no absolute path, no user name."""
    with_inventory(shard_config, tmp_path, monkeypatch)
    monkeypatch.setattr(rp, "REPO", tmp_path)
    m = rp.run(shard_config)
    text = (tmp_path / "runs" / "test-run" / "inventory_check.json").read_text(encoding="utf-8")
    report = json.loads(text)
    assert report["inventory"]["file"] == m["inventory"]["file"] == "expected_inventory.json"
    assert report["ledger"]["folder"] == "runs/test-run/ledger" and report["shards"]["folder"] == "runs/test-run/shards"
    assert tmp_path.name not in text and tmp_path.resolve().as_posix() not in text


def test_without_an_inventory_the_run_says_so_and_checks_nothing(tmp_path, shard_config, monkeypatch):
    with_inventory(shard_config, tmp_path, monkeypatch)
    cfg = json.loads(shard_config.read_text(encoding="utf-8"))
    del cfg["inventory"], cfg["stages"]["ledger"]  # and without the raw parts: nothing asks for them
    shard_config.write_text(json.dumps(cfg), encoding="utf-8")
    line = next(ln for ln in rp.plan(shard_config).splitlines() if ln.startswith("inventory: "))
    assert line.startswith("inventory: none   the run's parts and packs are not checked against an input manifest") and "not a production run" in line
    m = rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert m["inventory"] is None and manifest_of(run)["inventory"] is None and "inventory" in manifest_of(run)
    assert not (run / "inventory_check.json").exists() and not any("inventory_sha256" in s for s in m["stages"])
    assert not [c for c in m["checks"] if c["check"].startswith("inventory")] and m["stages"][-1]["stage"] == "reconcile"
    edit_config(shard_config, inventory=None)  # null is "none" too
    assert "\ninventory: none " in rp.plan(shard_config)


def test_the_plan_names_the_inventory_and_where_it_is_checked(tmp_path, shard_config, monkeypatch):
    with_inventory(shard_config, tmp_path, monkeypatch)
    file = tmp_path / "expected_inventory.json"
    line = next(ln for ln in rp.plan(shard_config).splitlines() if ln.startswith("inventory: "))
    assert line == (f"inventory: {file.resolve().as_posix()} (sha256 {sha(file)[:12]}…)   2 pack(s), 4 part(s), expected "
                    f"not_sharded 1, written 3; checked before the shard stage and after reconcile; report "
                    f"{(tmp_path / 'runs' / 'test-run' / 'inventory_check.json').resolve().as_posix()}")
    write_inventory(tmp_path, lambda inv: inv["parts"][-1].update(expected="writen"))  # a mistyped status shows in the counts
    assert "expected not_sharded 1, writen 1, written 2;" in rp.plan(shard_config)
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("key", ["Inventory", "inventory_file", "production", "intermediate", "From"])
def test_an_unknown_key_in_the_config_is_refused(tmp_path, config, key):
    """A mistyped run parameter would otherwise be ignored: "Inventory" would give a run without any inventory check."""
    edit_config(config, **{key: "x"})
    for go in (rp.run, rp.plan):
        with pytest.raises(rp.Stop, match=f"config: unknown key '{key}'; the run parameters are run_id, out, stages, from, to, "
                                          "hash_cache, intermediates, inventory"):
            go(config)
    assert not (tmp_path / "runs").exists()


def test_a_comment_key_is_not_a_run_parameter_and_a_key_under_stages_must_be_a_stage(tmp_path, config):
    edit_config(config, _note="a comment", _inventory="how to set it")
    assert "\ninventory: none " in rp.plan(config)
    cfg = json.loads(config.read_text(encoding="utf-8"))
    cfg["stages"]["_shards_example"] = {"tokenizer": "x"}
    config.write_text(json.dumps(cfg), encoding="utf-8")
    assert rp.plan(config)
    cfg["stages"]["inventory"] = "expected_inventory.json"  # the right key in the wrong place
    config.write_text(json.dumps(cfg), encoding="utf-8")
    for go in (rp.run, rp.plan):
        with pytest.raises(rp.Stop, match="config: stages.inventory is not a stage; the stages are clean, overlap, h3, dedup"):
            go(config)
    del cfg["stages"]["inventory"]
    for stage, key in (("ledger", "inventory"), ("f2", "intermediates")):  # and one level deeper, inside a stage's settings
        nested = json.loads(json.dumps(cfg))
        nested["stages"].setdefault(stage, {})[key] = "x"
        config.write_text(json.dumps(nested), encoding="utf-8")
        for go in (rp.run, rp.plan):
            with pytest.raises(rp.Stop, match=f"config: stages.{stage}.{key}: \"{key}\" is a run parameter, not a stage setting"):
                go(config)
    config.write_text(json.dumps(dict(cfg, stages=["clean"])), encoding="utf-8")
    with pytest.raises(rp.Stop, match="config: stages must be an object"):
        rp.plan(config)
    config.write_text(json.dumps([cfg]), encoding="utf-8")
    with pytest.raises(rp.Stop, match="expected a JSON object"):
        rp.plan(config)
    assert not (tmp_path / "runs").exists()


def no_raw(stages):
    stages["ledger"] = {}


def no_ledger(stages):
    del stages["ledger"]


def no_reconcile(stages):
    del stages["reconcile"]


def no_shards(stages):
    del stages["reconcile"], stages["shards"]


def fewer_packs(stages):
    stages["shards"]["packs"] = ["code-go"]


def other_packs(stages):
    stages["shards"]["packs"] = ["code-go", "en-dclm", "sci-x"]


@pytest.mark.parametrize("change, message", [
    (no_raw, "\"inventory\" needs stages.ledger.raw"), (no_ledger, "\"inventory\" needs stages.ledger.raw"),
    (no_reconcile, "\"inventory\" needs stages.shards and stages.reconcile"), (no_shards, "\"inventory\" needs stages.shards and stages.reconcile"),
    (fewer_packs, r"stages.shards.packs and the inventory's packs differ: 1 inventory pack\(s\) not in stages.shards.packs, e.g. en-dclm; 0 of"),
    (other_packs, r"0 inventory pack\(s\) not in stages.shards.packs; 1 of stages.shards.packs not in the inventory, e.g. sci-x")])
def test_a_run_with_an_inventory_is_the_production_run(tmp_path, shard_config, monkeypatch, change, message):
    """It is refused, before anything runs, without the raw parts for the ledger, without the shard and reconcile stages,
    or with a shard stage asked for other packs than the inventory lists."""
    edit_stages(with_inventory(shard_config, tmp_path, monkeypatch), change)
    for go in (rp.run, rp.plan):
        with pytest.raises(rp.Stop, match=message):
            go(shard_config)
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("to", ["clean", "apply", "ledger", "shards"])
def test_a_run_with_an_inventory_must_end_at_reconcile(tmp_path, shard_config, monkeypatch, to):
    """An earlier "to" would let the run finish without one or both check points: the config's "to", the argument and
    --plan are all refused, before anything runs."""
    with_inventory(shard_config, tmp_path, monkeypatch)
    message = f"\"inventory\" needs a run that ends at reconcile, and \"to\" is {to}"
    for go in (lambda c: rp.run(c, to=to), lambda c: rp.plan(c, to=to), lambda c: rp.run(c, start="clean", to=to)):
        with pytest.raises(rp.Stop, match=message):
            go(shard_config)
    edit_config(shard_config, to=to)
    for go in (rp.run, rp.plan):
        with pytest.raises(rp.Stop, match=message):
            go(shard_config)
    assert not (tmp_path / "runs").exists()
    edit_config(shard_config, to="reconcile")  # said outright, it is the same run
    assert "\ninventory: " in rp.plan(shard_config)


def test_without_stages_shards_packs_the_shard_stage_takes_every_pack(tmp_path, shard_config, monkeypatch):
    """The stand-in run_shards.py runs here through the runner's own shard stage: it gets no --pack, shards every pack,
    and its shards_summary.json is what the inventory is checked against."""
    edit_stages(with_inventory(shard_config, tmp_path, monkeypatch, script=True), lambda stages: stages["shards"].pop("packs"))
    m = rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert json.loads((run / "shards" / "args.json").read_text(encoding="utf-8"))["packs"] == []
    assert stage_record(m, "shards")["counts"] == INVENTORY_SHARD_COUNTS and inventory_checks(m, "reconcile") == ON_LEDGER + ON_SHARDS
    assert inventory_report(run)["shards"] == {"folder": (run / "shards").resolve().as_posix(), "parts": 4,
                                               "statuses": {"not_sharded": 1, "written": 3}}


def test_the_inventory_is_checked_against_the_summary_the_shard_script_writes(tmp_path, shard_config, monkeypatch):
    """Through the runner's own shard stage (not a replaced one): a part the script wrote and the inventory lists as
    not_sharded stops the run after reconcile; with the inventory corrected, "from": "reconcile" finishes it."""
    name = "train/en-dclm/part-00000.parquet"
    with_inventory(shard_config, tmp_path, monkeypatch, script=True, change=lambda inv: part_of(inv, name).update(expected="not_sharded"))
    with pytest.raises(rp.Stop, match=f"inventory: every part ended in a listed status: 1 of 4 .*{name}: status 'written', listed not_sharded"):
        rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert json.loads((run / "shards" / "shards_summary.json").read_text(encoding="utf-8"))["parts"][name]["shards"][0]["shard_id"] == "en-dclm-train-000000"
    write_inventory(tmp_path)
    m = rp.run(shard_config, start="reconcile")
    assert all(c["ok"] for c in m["checks"]) and inventory_report(run)["ok"] is True


def twice(inv):
    inv["parts"].append(dict(inv["parts"][0]))


def expects_failed(inv):
    inv["parts"][0]["expected"] = "failed"


def pack_without_part(inv):
    inv["packs"].append("sci-x")


def no_raw_rows(inv):
    del part_of(inv, SHARDED[1])["raw_rows"]


def hash_under_another_name(inv):
    for p in inv["parts"]:
        p["sha256"] = p.pop("raw_sha256")


def no_input_manifest(inv):
    del inv["input_manifest_sha256"]


def manifest_under_another_name(inv):
    inv["manifest_sha256"] = inv["input_manifest_sha256"]


@pytest.mark.parametrize("value, message", [(7, "inventory must be the path"), ("", "inventory must be the path"),
                                            ("{tmp}/no-such-inventory.json", "config: inventory: .*no-such-inventory.json is not a file"),
                                            ("{tmp}/runs/test-run/ledger/expected_inventory.json", "is in a folder of the run itself"),
                                            (twice, "config: inventory: .* is listed twice"),
                                            (expects_failed, "config: inventory: .*no run may expect"),
                                            (pack_without_part, "config: inventory: .*pack 'sci-x' is in \"packs\" but no part is of it"),
                                            (no_raw_rows, "config: inventory: .*part-00001.parquet: raw_rows is missing"),
                                            (hash_under_another_name, "config: inventory: .*unknown key 'sha256'; a part has part, expected, raw_sha256"),
                                            (no_input_manifest, "config: inventory: .*input_manifest_sha256 is missing"),
                                            (manifest_under_another_name, "config: inventory: .*unknown key 'manifest_sha256'; an inventory has")])
def test_a_missing_or_malformed_inventory_stops_before_anything_runs(tmp_path, shard_config, monkeypatch, value, message):
    """Also an inventory that would compare nothing: a part without its raw rows, or with its hash under another name."""
    with_inventory(shard_config, tmp_path, monkeypatch, change=value if callable(value) else None)
    if not callable(value):
        edit_config(shard_config, inventory=value.replace("{tmp}", tmp_path.as_posix()) if isinstance(value, str) else value)
    for go in (rp.run, rp.plan):
        with pytest.raises(rp.Stop, match=message):
            go(shard_config)
    assert not (tmp_path / "runs").exists()


def test_the_inventory_must_be_of_the_input_manifest_the_clean_stage_pins(tmp_path, staged):
    path, repo = staged
    cfg = json.loads(path.read_text(encoding="utf-8"))
    tokenizer, raw, file = tmp_path / "tokenizer.json", tmp_path / "raw", tmp_path / "expected_inventory.json"
    tokenizer.write_text("{}", encoding="utf-8")
    raw.mkdir()
    cfg["stages"].update(shards={"script": str(FAKE_SHARDS), "tokenizer": str(tokenizer), "dataset_version": "sample"}, reconcile={},
                         ledger={"raw": str(raw)})
    cfg["inventory"] = str(file)
    path.write_text(json.dumps(cfg), encoding="utf-8")
    inv = {"input_manifest_sha256": INPUT_MANIFEST, "packs": ["code-go"],
           "parts": [{"part": "train/code-go/part-00000.parquet", "expected": "written", "raw_sha256": "0" * 64, "raw_rows": 5}]}
    file.write_text(json.dumps(inv), encoding="utf-8")
    pinned = cfg["stages"]["clean"]["manifest_sha256"]
    for go in (rp.plan, rp.run):
        with pytest.raises(rp.Stop, match=f"the inventory was made from input manifest abababababab…, and stages.clean.manifest_sha256 is {pinned[:12]}…"):
            go(path)
    assert not (repo / "out" / "runs").exists()  # the clean stage did not start
    file.write_text(json.dumps(dict(inv, input_manifest_sha256=pinned)), encoding="utf-8")
    assert "\ninventory: " in rp.plan(path)


def test_the_inventory_must_be_of_the_input_manifest_the_adopted_clean_job_read(tmp_path, shard_config, tsai_outputs, monkeypatch):
    """The adopted folder is there before the run, so this is known, and refused, before anything runs."""
    with_inventory(shard_config, tmp_path, monkeypatch)
    clean_job_names(tsai_outputs["cleaned"], "cd" * 32)
    for go in (rp.run, rp.plan):
        with pytest.raises(rp.Stop, match="config: the inventory was made from input manifest abababababab…, and the adopted clean job read cdcdcdcdcdcd…"):
            go(shard_config)
    clean_job_names(tsai_outputs["cleaned"], None)
    for go in (rp.run, rp.plan):
        with pytest.raises(rp.Stop, match="job_summary.json of the adopted clean job records no manifest_sha256"):
            go(shard_config)
    assert not (tmp_path / "runs").exists()
    clean_job_names(tsai_outputs["cleaned"], "cd" * 32)
    write_inventory(tmp_path, lambda inv: inv.update(input_manifest_sha256="cd" * 32))
    m = rp.run(shard_config)
    assert inventory_checks(m, "shards") == ON_LEDGER and all(c["ok"] for c in m["checks"])


@pytest.mark.parametrize("damage, message", [
    (lambda f: f.unlink(), r"job_summary.json of the adopted clean job cannot be read \(FileNotFoundError\)"),
    (lambda f: f.write_text("{not json", encoding="utf-8"), r"job_summary.json of the adopted clean job cannot be read \(JSONDecodeError\)"),
    (lambda f: f.write_bytes(b"\xff\xfe\xff"), r"job_summary.json of the adopted clean job cannot be read \(UnicodeDecodeError\)"),
    (lambda f: f.write_text("[]", encoding="utf-8"), "job_summary.json of the adopted clean job is not a JSON object")])
def test_an_adopted_clean_job_without_a_readable_summary_is_refused_before_anything_runs(tmp_path, shard_config, tsai_outputs, monkeypatch,
                                                                                         damage, message):
    """The adopted folder is there, so its summary can be read now: the run does not go through seven stages to find
    out that nothing says which input manifest the clean job read."""
    with_inventory(shard_config, tmp_path, monkeypatch)
    damage(tsai_outputs["cleaned"] / "job_summary.json")
    for go in (rp.run, rp.plan):
        with pytest.raises(rp.Stop, match="config: .*" + message + ", so the inventory cannot be tied to the input manifest"):
            go(shard_config)
    assert not (tmp_path / "runs").exists()


def test_a_clean_job_whose_summary_is_gone_fails_the_input_manifest_check(tmp_path, shard_config, tsai_outputs, monkeypatch):
    """The summary goes while the run is under way: nothing says which input manifest the clean job read, and the check
    is not left out, it fails."""
    with_inventory(shard_config, tmp_path, monkeypatch, after_shards=lambda self: (tsai_outputs["cleaned"] / "job_summary.json").unlink())
    with pytest.raises(rp.Stop, match="check failed: inventory: made from the input manifest the clean job read: the cleaned folder has no job_summary.json"):
        rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert [s["stage"] for s in manifest_of(run)["stages"]] == [s for s in rp.STAGES[:-1] if s != "h3"] and inventory_report(run)["checked_after"] == "reconcile"
    assert inventory_report(run)["differences"]["input_manifest_sha256"] == [{"clean_job": None, "listed": INPUT_MANIFEST}]


def extra_part(inv):
    inv["parts"].append({"part": "train/code-go/part-00007.parquet", "raw_sha256": "0" * 64, "raw_rows": 3, "expected": "written"})


def one_part_less(inv):
    inv["parts"] = [p for p in inv["parts"] if p["part"] != SHARDED[1]]


def other_rows(inv):
    part_of(inv, SHARDED[0])["raw_rows"] += 1


def other_file(inv):
    part_of(inv, "heldout/code-go/part-00000.parquet")["raw_sha256"] = "0" * 64


@pytest.mark.parametrize("change, message, difference", [
    (extra_part, r"the ledger holds exactly the listed parts: 1 listed part\(s\) not in the ledger, e.g. train/code-go/part-00007.parquet; 0 ledger",
     ("ledger_parts_missing", ["train/code-go/part-00007.parquet"])),
    (one_part_less, r"the ledger holds exactly the listed parts: 0 listed part\(s\) not in the ledger; 1 ledger part\(s\) not listed, e.g. train/code-go/part-00001.parquet",
     ("ledger_parts_unlisted", [SHARDED[1]])),
    (other_rows, r"each part's raw rows are the listed ones: 1 of 4 part\(s\) differ, e.g. train/code-go/part-00000.parquet: ledger 6, listed 7",
     ("raw_rows", [{"part": SHARDED[0], "ledger": 6, "listed": 7}])),
    (other_file, r"each part's raw file is the listed one \(sha256\): 1 of 4 part\(s\) differ, e.g. heldout/code-go/part-00000.parquet: ledger read .*, listed 000000000000…",
     None)])
def test_a_ledger_that_differs_from_the_inventory_stops_the_run_before_the_shard_stage(tmp_path, shard_config, monkeypatch, change, message, difference):
    """With the ledger stage recorded: the ledger is whole, it is the inventory (or the input) that has to be put right."""
    ran = []
    with_inventory(shard_config, tmp_path, monkeypatch, change=change, after_shards=ran.append)
    with pytest.raises(rp.Stop, match="check failed: inventory: " + message + ".*; see inventory_check.json in the run folder"):
        rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert not ran and not (run / "shards").exists()
    m = manifest_of(run)
    assert [s["stage"] for s in m["stages"]] == list(THROUGH_LEDGER) and not any("inventory_sha256" in s for s in m["stages"])
    assert m["inventory"]["checked"] == {"ledger": None, "reconcile": None} and m["inventory"]["report"] == "inventory_check.json"
    report = inventory_report(run)
    assert report["ok"] is False and report["checked_after"] == "ledger" and [c["check"] for c in report["checks"]] == ON_LEDGER
    assert sum(not c["ok"] for c in report["checks"]) == 1
    if difference:
        assert report["differences"][difference[0]] == difference[1]


def test_a_corrected_inventory_resumes_at_the_shard_stage(tmp_path, shard_config, monkeypatch):
    """The ledger is not built again for a mistake in the inventory file: "from": "shards" picks the run up."""
    ran = []
    with_inventory(shard_config, tmp_path, monkeypatch, change=other_rows, after_shards=ran.append)
    with pytest.raises(rp.Stop, match="each part's raw rows are the listed ones"):
        rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    ledger = stage_record(manifest_of(run), "ledger")
    monkeypatch.setattr(rp.Run, "stage_ledger", lambda self: pytest.fail("the ledger stage ran again"))
    write_inventory(tmp_path)
    m = rp.run(shard_config, start="shards")
    assert len(ran) == 1 and stage_record(m, "ledger") == ledger and m["stages"][-1]["stage"] == "reconcile"
    assert all(c["ok"] for c in m["checks"]) and m["inventory"]["checked"]["ledger"] == sha(tmp_path / "expected_inventory.json")


def test_a_run_resumed_at_the_shard_stage_is_checked_before_anything_is_sharded(tmp_path, shard_config, monkeypatch):
    """"from": "shards" skips the ledger stage, not the check of the ledger: a listed part the ledger lacks stops the
    resumed run before the shard stage, as it stops a run from the start."""
    ran = []
    rp.run(with_inventory(shard_config, tmp_path, monkeypatch, after_shards=ran.append))
    run = tmp_path / "runs" / "test-run"
    write_inventory(tmp_path, extra_part)
    with pytest.raises(rp.Stop, match=r"inventory: the ledger holds exactly the listed parts: 1 listed part\(s\) not in the ledger"):
        rp.run(shard_config, start="shards")
    assert len(ran) == 1 and inventory_report(run)["checked_after"] == "ledger"  # the shard stage did not run a second time
    # The check point writes its report, not the manifest: the records of the stages it stopped before are still the
    # finished run's, so with the inventory put right the run resumes at reconcile without sharding again.
    assert [s["stage"] for s in manifest_of(run)["stages"]] == [s for s in rp.STAGES if s != "h3"]
    write_inventory(tmp_path)
    m = rp.run(shard_config, start="reconcile")
    assert len(ran) == 1 and m["stages"][-1]["stage"] == "reconcile" and inventory_report(run)["ok"] is True


def test_a_ledger_built_without_the_raw_parts_stops_a_resumed_run_before_the_shard_stage(tmp_path, shard_config, monkeypatch):
    """A run to the ledger without an inventory and without stages.ledger.raw (mode C), then resumed at the shard stage
    with both: the inventory is not passed on the config's word, the ledger on disk is checked."""
    ran = []
    with_inventory(shard_config, tmp_path, monkeypatch, after_shards=ran.append)
    full = json.loads(shard_config.read_text(encoding="utf-8"))
    early = json.loads(json.dumps(full))
    del early["inventory"], early["stages"]["ledger"]
    shard_config.write_text(json.dumps(dict(early, to="ledger")), encoding="utf-8")
    assert stage_record(rp.run(shard_config), "ledger")["clean_mode"] == "C"
    shard_config.write_text(json.dumps(full), encoding="utf-8")
    with pytest.raises(rp.Stop, match=r"inventory: the ledger accounts for every raw document \(mode B\): ledger clean_mode 'C'"):
        rp.run(shard_config, start="shards")
    assert not ran and not (tmp_path / "runs" / "test-run" / "shards").exists()


def ghost(doc_id):
    return {"doc_id": doc_id, "text": f"synthetic text of {doc_id}", "url": "", "lang_label": "en", "pack_id": "ghost-pack"}


def test_a_document_of_an_unlisted_pack_that_the_cleaner_dropped_does_not_stop_the_run(tmp_path, shard_config, monkeypatch):
    """A raw part of a listed pack may hold a document with another pack_id. Dropped by the cleaner, nothing of that
    pack goes on, and the inventory cannot list a pack that has no part: the run passes and the check says what it saw."""
    with_inventory(shard_config, tmp_path, monkeypatch, raw_extra={"train/en-dclm/part-00000.parquet": [ghost("ghost-1")]})
    m = rp.run(shard_config)
    assert m["by_pack"]["ghost-pack"]["train"]["raw"] == 1 and m["by_pack"]["ghost-pack"]["train"]["final"] == 0
    detail = next(c["detail"] for c in m["checks"] if c["check"] == PACKS_CHECK)
    assert detail == "all 2 listed packs; 1 other pack id(s) among the documents, none kept, e.g. ghost-pack"


def test_a_kept_document_of_an_unlisted_pack_stops_the_run_before_the_shard_stage(tmp_path, shard_config, tsai_outputs, monkeypatch):
    """The same document kept by the cleaner (it is in the cleaned part, and neither dedup nor F2 takes it out) would
    reach the shards under a pack the input manifest does not list."""
    f = tsai_outputs["cleaned"] / "train" / "en-dclm" / "part-00000.parquet"
    t = pq.read_table(f)
    rows = t.to_pylist()
    rows[1]["pack_id"] = "ghost-pack"  # e1: not on the remove list, not dropped by F2
    pq.write_table(pa_concat(t.slice(0, 0), rows), f)
    overlap_folder(tsai_outputs["overlap"])  # model a fresh overlap run on the changed cleaned bytes
    ran = []
    with_inventory(shard_config, tmp_path, monkeypatch, after_shards=ran.append)
    with pytest.raises(rp.Stop, match=r"no other pack has kept documents: 0 listed pack\(s\) not in the ledger; 1 pack\(s\) that are "
                                      r"not listed have kept documents, e.g. ghost-pack \(1 kept\)"):
        rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert not ran and inventory_report(run)["differences"]["ledger_packs_unlisted"] == [{"pack": "ghost-pack", "kept": 1}]


def test_a_part_that_ends_in_another_status_than_listed_stops_the_run_after_reconcile(tmp_path, shard_config, monkeypatch):
    name = "train/en-dclm/part-00000.parquet"
    with_inventory(shard_config, tmp_path, monkeypatch, change=lambda inv: part_of(inv, name).update(expected="not_sharded"))
    with pytest.raises(rp.Stop, match=r"inventory: every part ended in a listed status: 1 of 4 part\(s\) differ, e.g. "
                                      f"{name}: status 'written', listed not_sharded; see inventory_check.json"):
        rp.run(shard_config)
    run, file = tmp_path / "runs" / "test-run", tmp_path / "expected_inventory.json"
    m = manifest_of(run)
    assert [s["stage"] for s in m["stages"]] == [s for s in rp.STAGES[:-1] if s != "h3"] and inventory_checks(m, "shards") == ON_LEDGER
    assert m["inventory"]["checked"] == {"ledger": sha(file), "reconcile": None} and m["inventory"]["report"] == "inventory_check.json"
    report = inventory_report(run)
    assert report["checked_after"] == "reconcile" and report["differences"]["status"] == [
        {"part": name, "status": "written", "listed": ["not_sharded"]}]
    assert (run / "reconcile" / "reconcile_summary.json").is_file()  # reconcile itself passed and wrote its outputs


def test_a_part_in_the_shard_summary_that_is_not_listed_stops_the_run(tmp_path, shard_config, monkeypatch):
    other = "train/code-go/part-00009.parquet"

    def one_more(self):
        f = self.output("shards") / "shards_summary.json"
        s = json.loads(f.read_text(encoding="utf-8"))
        s["parts"][other] = {"pack_id": "code-go", "status": "not_sharded"}
        f.write_text(json.dumps(s), encoding="utf-8")
    with_inventory(shard_config, tmp_path, monkeypatch, after_shards=one_more)
    with pytest.raises(rp.Stop, match=r"inventory: the shard summary holds exactly the listed parts: 0 listed part\(s\) not in "
                                      rf"shards_summary.json; 1 part\(s\) in it not listed, e.g. {other}"):
        rp.run(shard_config)
    assert inventory_report(tmp_path / "runs" / "test-run")["differences"]["shard_parts_unlisted"] == [other]


def test_a_shard_summary_entry_without_its_pack_stops_the_run(tmp_path, shard_config, monkeypatch):
    def no_pack(self):
        f = self.output("shards") / "shards_summary.json"
        s = json.loads(f.read_text(encoding="utf-8"))
        del s["parts"][SHARDED[0]]["pack_id"]
        f.write_text(json.dumps(s), encoding="utf-8")
    with_inventory(shard_config, tmp_path, monkeypatch, after_shards=no_pack)
    with pytest.raises(rp.Stop, match=f"inventory: every part is of its listed pack: 1 of 4 .*{SHARDED[0]}: pack_id None, listed 'code-go'"):
        rp.run(shard_config)


def test_a_status_the_inventory_lists_as_acceptable_passes(tmp_path, shard_config, monkeypatch):
    name = "train/en-dclm/part-00000.parquet"
    with_inventory(shard_config, tmp_path, monkeypatch, change=lambda inv: part_of(inv, name).update(expected=["empty", "written"]))
    m = rp.run(shard_config)
    assert m["inventory"]["expected"] == {"empty|written": 1, "not_sharded": 1, "written": 2} and all(c["ok"] for c in m["checks"])


def test_a_resumed_run_is_checked_against_the_inventory_as_it_is_now(tmp_path, shard_config, monkeypatch):
    """"from": "reconcile" skips the shard stage and its check point, so the reconcile stage checks the ledger side
    again: an inventory that changed since is not passed on the earlier check's word, and the manifest says which
    inventory each check point passed with."""
    rp.run(with_inventory(shard_config, tmp_path, monkeypatch))
    run, first = tmp_path / "runs" / "test-run", sha(tmp_path / "expected_inventory.json")
    write_inventory(tmp_path, other_rows)
    changed = sha(tmp_path / "expected_inventory.json")
    with pytest.raises(rp.Stop, match="inventory: each part's raw rows are the listed ones: 1 of 4"):
        rp.run(shard_config, start="reconcile")
    assert inventory_report(run)["ok"] is False and inventory_report(run)["inventory"]["sha256"] == changed
    m = manifest_of(run)  # still the finished run's: a stage that did not finish again changes no record
    assert [s["stage"] for s in m["stages"]] == [s for s in rp.STAGES if s != "h3"] and m["inventory"]["sha256"] == first
    assert m["inventory"]["checked"] == {"ledger": first, "reconcile": first}
    write_inventory(tmp_path, lambda inv: inv.update(_comment="the same parts, written again"))
    second = sha(tmp_path / "expected_inventory.json")
    m = rp.run(shard_config, start="reconcile")
    assert second != first and m["inventory"]["sha256"] == second and inventory_report(run)["ok"] is True
    assert m["inventory"]["checked"] == {"ledger": first, "reconcile": second}  # the first check point saw another file
    assert inventory_checks(m, "shards") == ON_LEDGER and inventory_checks(m, "reconcile") == ON_LEDGER + ON_SHARDS


def test_a_check_point_that_cannot_make_its_checks_says_so_in_its_report(tmp_path, shard_config, tsai_outputs, monkeypatch):
    """The first check point passes and writes its report. Then the clean job's summary stops being a JSON object, so
    the second cannot make its checks: the run stops with a message, and the report is the second's, saying why, not
    the passing one of the first."""
    seen = []

    def break_summary(self):
        seen.append(inventory_report(self.dir)["ok"])
        (tsai_outputs["cleaned"] / "job_summary.json").write_text("[]", encoding="utf-8")
    with_inventory(shard_config, tmp_path, monkeypatch, after_shards=break_summary)
    with pytest.raises(rp.Stop, match="^inventory: the clean job's summary .*job_summary.json is not a JSON object"):
        rp.run(shard_config)
    run, file = tmp_path / "runs" / "test-run", tmp_path / "expected_inventory.json"
    report = inventory_report(run)
    assert seen == [True] and report["ok"] is False and report["checked_after"] == "reconcile" and "checks" not in report
    assert "is not a JSON object" in report["error"] and report["inventory"]["sha256"] == sha(file)
    m = manifest_of(run)
    assert [s["stage"] for s in m["stages"]] == [s for s in rp.STAGES[:-1] if s != "h3"] and m["inventory"]["checked"] == {"ledger": sha(file), "reconcile": None}


def test_a_report_that_cannot_be_written_stops_the_run_and_leaves_no_earlier_one(tmp_path, shard_config, monkeypatch):
    """The first check point writes its report; at the second the disk is full. The run stops with a message, not a
    traceback, and the first report is not left to be read as the second's."""
    def no_space(report, out):
        raise OSError(28, "No space left on device")
    with_inventory(shard_config, tmp_path, monkeypatch,
                   after_shards=lambda self: monkeypatch.setattr(rp.inventory_check, "write_report", no_space))
    with pytest.raises(rp.Stop, match=r"^inventory: the report .*inventory_check.json could not be written \(OSError\)"):
        rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert not (run / "inventory_check.json").exists() and [s["stage"] for s in manifest_of(run)["stages"]] == [s for s in rp.STAGES[:-1] if s != "h3"]


def test_a_report_of_an_earlier_invocation_does_not_stay(tmp_path, shard_config, monkeypatch):
    """A run that passed its inventory, then reconciled again without one: the passing report is not left in the run
    folder as if it were of the run as it is now."""
    rp.run(with_inventory(shard_config, tmp_path, monkeypatch))
    run = tmp_path / "runs" / "test-run"
    assert inventory_report(run)["ok"] is True
    cfg = json.loads(shard_config.read_text(encoding="utf-8"))
    del cfg["inventory"]
    shard_config.write_text(json.dumps(cfg), encoding="utf-8")
    m = rp.run(shard_config, start="reconcile")
    assert m["inventory"] is None and not (run / "inventory_check.json").exists()


def test_a_failed_inventory_check_drops_nothing(tmp_path, shard_config, monkeypatch):
    """"intermediates": "drop" deletes only after every check of the run has passed, the inventory's among them."""
    name = "train/en-dclm/part-00000.parquet"
    with_inventory(shard_config, tmp_path, monkeypatch, change=lambda inv: part_of(inv, name).update(expected="not_sharded"))
    edit_config(shard_config, intermediates="drop")
    with pytest.raises(rp.Stop, match="inventory: every part ended in a listed status"):
        rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert len(parquet_under(run / "final")) == len(parquet_under(run / "deduped")) == 4
    assert manifest_of(run)["intermediates"] == {"mode": "drop"}
    write_inventory(tmp_path)
    m = rp.run(shard_config, start="reconcile")  # nothing was dropped, so the run can be resumed, and now it drops
    assert m["intermediates"]["state"] == "done" and parquet_under(run / "final") == ["heldout/code-go/part-00000.parquet"]


def test_an_inventory_and_a_drop_go_together(tmp_path, shard_config, monkeypatch):
    with_inventory(shard_config, tmp_path, monkeypatch)
    edit_config(shard_config, intermediates="drop")
    m = rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert m["intermediates"]["state"] == "done" and m["intermediates"]["parts"] == {"dropped": 3, "left": 1}
    assert inventory_report(run)["ok"] is True and parquet_under(run / "final") == ["heldout/code-go/part-00000.parquet"]



# --- patilvijay23's review of PR #46 (17 Nov): a drop checks the shards on disk first -------------------------------------
def remove_payload_and_index(out):
    for f in list(out.glob("*.bin")) + list(out.glob("*.idx.npy")):
        f.unlink()


def flip_a_payload_byte(out):
    f = sorted(out.glob("*.bin"))[0]
    b = bytearray(f.read_bytes())
    b[-1] ^= 0xFF
    f.write_bytes(bytes(b))


def cut_the_payload(out):
    f = sorted(out.glob("*.bin"))[0]
    f.write_bytes(f.read_bytes()[:-4])


def remove_the_index(out):  # (a docs.parquet that lost a row is already stopped by reconcile)
    sorted(out.glob("*.idx.npy"))[0].unlink()


def bad_header(out):
    f = sorted(out.glob("*.bin"))[0]
    b = bytearray(f.read_bytes())
    b[0:4] = (12345).to_bytes(4, "little")
    f.write_bytes(bytes(b))


@pytest.mark.parametrize("damage, message", [
    (remove_payload_and_index, r"\.bin: missing"),  # patilvijay23's reproduction: metadata fine, .bin and .idx.npy gone
    (flip_a_payload_byte, r"\.bin: sha256 .*, the manifest has"),
    (cut_the_payload, r"\.bin: sha256"),
    (remove_the_index, r"\.idx\.npy: missing"),
    (bad_header, r"\.bin: sha256")])
def test_a_drop_checks_the_shards_on_disk_and_deletes_nothing_when_one_is_not_as_its_manifest_says(
        tmp_path, shard_config, monkeypatch, damage, message):
    """The summary and reconcile say the parts are in shards, but the shard files are not what the manifests say: the
    drop stops before the first file goes, leaves no mark, and the run stays whole and resumable."""
    with_reconcile(shard_config, monkeypatch, intermediates="drop", after_shards=lambda self: damage(self.output("shards")))
    with pytest.raises(rp.Stop, match="intermediates: a shard is not on disk as its manifest says, so its Parquet stays: "
                                      + ".*" + message + ".*Nothing was deleted"):
        rp.run(shard_config)
    run = tmp_path / "runs" / "test-run"
    assert len(parquet_under(run / "deduped")) == 4 and len(parquet_under(run / "final")) == 4  # every part still there
    m = manifest_of(run)
    assert m["intermediates"] == {"mode": "drop"} and m["stages"][-1]["stage"] == "reconcile"  # no mark: resumable


def shard_on_disk(out, n=3):
    """One whole shard "s" of n documents (2 tokens each) in `out`, as the writer leaves it. Returns its manifest."""
    from test_reconcile_shards import write_payload, files_of_shard
    out.mkdir(exist_ok=True)
    pq.write_table(pa.table({"doc_id": [f"d{i}" for i in range(n)]}), out / "s.docs.parquet")
    (out / "s.quality_report.json").write_text("{}", encoding="utf-8")
    m = {"shard_id": "s", "doc_count": n, **files_of_shard(out, "s", write_payload(out, "s", n))}
    (out / "s.json").write_text(json.dumps(m), encoding="utf-8")
    return m


def rewritten(out, name, data, **manifest):
    """Replace a shard file and record its new sha256 in the manifest (so only the check under test can see it)."""
    import hashing
    (out / name).write_bytes(data)
    m = json.loads((out / "s.json").read_text(encoding="utf-8"))
    key = {"bin": "payload", "npy": "index", "parquet": "sample_metadata", "json": "quality_report"}[name.rsplit(".", 1)[1]]
    (out / "s.json").write_text(json.dumps({**m, f"{key}_sha256": hashing.file_sha256(out / name), **manifest}),
                                encoding="utf-8")


def npy_bytes(arr):
    import io
    import numpy as np
    b = io.BytesIO()
    np.save(b, arr)
    return b.getvalue()


def test_shard_problems_names_each_defect(tmp_path):
    """shard_problems on its own: a whole shard passes, and each defect is named by the check that finds it, the sha256
    written to the manifest after the damage so that only that check can see it (header, size, index, rows, counts)."""
    import io
    import numpy as np
    out = tmp_path / "shards"

    def problems(entry=None):
        return rp.shard_problems(out, "s", entry or {}, rp.HashCache())
    m = shard_on_disk(out)
    assert problems({"docs": 3, "tokens": 6}) == []
    assert problems({"tokens": 7}) == ["shards_summary.json: tokens 7 for s, the manifest has 6"]
    payload = (out / "s.bin").read_bytes()
    rewritten(out, "s.bin", (12345).to_bytes(4, "little") + payload[4:])  # magic
    assert problems() == ["s.bin: header [12345, 2, 6], expected [20261025, 2, 6]"]
    shard_on_disk(out)
    rewritten(out, "s.bin", payload + bytes(4), payload_bytes=len(payload) + 4)  # a token more than the header says
    assert problems() == [f"s.bin: {len(payload) + 4:,} bytes, expected {len(payload):,} (manifest payload_bytes {len(payload) + 4})"]
    shard_on_disk(out)
    rewritten(out, "s.bin", payload, payload_bytes=len(payload) - 4)  # the manifest's size is not the file's
    assert problems() == [f"s.bin: {len(payload):,} bytes, expected {len(payload):,} (manifest payload_bytes {len(payload) - 4})"]
    i8 = np.int64  # pinned: NumPy < 2 on Windows makes a plain np.array of ints int32
    for arr, why in ((np.array([0, 4, 2, 6], dtype=i8), ""), (np.array([0, 4, 2, 6], dtype=np.uint64), " (uint64)"),
                     (np.array([0, 2, 4, 6], dtype=np.int32), " (int32)"), (np.array([0, 2, 4], dtype=i8), ""),
                     (np.array([1, 2, 4, 6], dtype=i8), "")):
        shard_on_disk(out)
        rewritten(out, "s.idx.npy", npy_bytes(arr))  # falling, wraps in uint64, not int64, a document short, not from 0
        assert problems() == [f"s.idx.npy: not 4 rising int64 offsets from 0 to 6{why}"], arr
    for data, error in ((b"", "EOFError"), (b"PK\x03\x04" + bytes(40), "BadZipFile")):  # a copy cut to nothing, another format
        shard_on_disk(out)
        rewritten(out, "s.idx.npy", data)
        assert problems() == [f"s.idx.npy: not 4 rising int64 offsets from 0 to 6 (cannot be read: {error})"]
    shard_on_disk(out)
    z = io.BytesIO()
    np.savez(z, idx=np.array([0, 2, 4, 6], dtype=np.int64))
    rewritten(out, "s.idx.npy", z.getvalue())
    assert problems() == ["s.idx.npy: not 4 rising int64 offsets from 0 to 6 (NpzFile)"]
    shard_on_disk(out)
    b = io.BytesIO()
    pq.write_table(pa.table({"doc_id": ["d0", "d1"]}), b)
    rewritten(out, "s.docs.parquet", b.getvalue())  # a document short
    assert problems() == ["s.docs.parquet: 2 rows, the manifest has 3 documents"]
    rewritten(out, "s.docs.parquet", b"not parquet")
    assert problems() == ["s.docs.parquet: cannot be read (ArrowInvalid)"]
    # the files the manifest names: the writer's names in the folder, and nothing else
    m = shard_on_disk(out)
    for name in ("../s.bin", "t.bin", "s.bin.old", None):
        (out / "s.json").write_text(json.dumps({**m, "payload_uri": name}), encoding="utf-8")
        assert problems() == [f"s.json: payload_uri is {name!r}, expected 's.bin'"]
    (out / "s.json").write_text("{not json", encoding="utf-8")
    assert problems() == ["s.json: cannot be read (JSONDecodeError)"]
    (out / "s.json").write_text(json.dumps({**m, "shard_id": "other"}), encoding="utf-8")
    assert problems() == ["s.json: not the manifest of s"]


def test_shard_problems_refuses_a_shard_file_that_is_a_link(tmp_path):
    """A .bin that is a link to a file elsewhere (with the right bytes) is not in the shard folder: after a drop it would
    be the only copy of those documents, outside the run."""
    out = tmp_path / "shards"
    shard_on_disk(out)
    elsewhere = tmp_path / "elsewhere.bin"
    (out / "s.bin").replace(elsewhere)
    try:
        (out / "s.bin").symlink_to(elsewhere)
    except OSError:
        pytest.skip("this system does not let the tests make a symbolic link")
    assert rp.shard_problems(out, "s", {}, rp.HashCache()) == ["s.bin: a link, not the file"]


# --- TEJASKUMAR-REDDY-J's review of PR #46 (18 Nov): dataset_version, truncated parts ----------------------------------------
def test_the_shard_stage_passes_the_dataset_version_and_any_tokenizer_runs_stay_test(tmp_path, shard_config):
    """stages.shards.dataset_version goes to run_shards.py as --dataset-version (shard_writer writes it into every
    manifest); an any_tokenizer run passes none, so its shards are "test". --plan names the version."""
    assert 'dataset_version sample' in rp.plan(shard_config)
    rp.run(shard_config)
    args = json.loads((tmp_path / "runs" / "test-run" / "shards" / "args.json").read_text(encoding="utf-8"))
    assert args["dataset_version"] == "sample" and args["any_tokenizer"] is False
    cfg = json.loads(shard_config.read_text(encoding="utf-8"))
    cfg["run_id"] = "test-run-2"
    cfg["stages"]["shards"] = {**{k: v for k, v in cfg["stages"]["shards"].items() if k != "dataset_version"}, "any_tokenizer": True}
    shard_config.write_text(json.dumps(cfg), encoding="utf-8")
    assert 'dataset_version test' in rp.plan(shard_config)
    rp.run(shard_config)
    args = json.loads((tmp_path / "runs" / "test-run-2" / "shards" / "args.json").read_text(encoding="utf-8"))
    assert args["dataset_version"] is None and args["any_tokenizer"] is True


def test_a_part_cut_short_by_the_shard_writer_stops_the_shard_stage(tmp_path, shard_config, monkeypatch):
    """A part whose kept documents did not all fit in stages.shards.tokens stops the run at the shard stage, with the
    parts named, instead of later in reconcile as not_reached."""
    monkeypatch.setenv("FAKE_SHARDS_TRUNCATE", "1")
    with pytest.raises(rp.Stop, match=r"no part was cut short.*1 part\(s\) cut short, e.g. "
                                      r"\['train/code-go/part-00000.parquet'\]"):
        rp.run(shard_config)
