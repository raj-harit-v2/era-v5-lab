"""Tests for ledger.py: the runner takes the synthetic chain through F2 (fake_run_f2.py), then the ledger is built from
what each stage wrote, and changed inputs must stop it.

  python -m pytest teams/01-data-a/pipeline/tests -q
"""
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from conftest import HEADER, PIPELINE
import ledger
import run_pipeline as rp
from test_run_pipeline import GROUP_HEADER, config, tsai_outputs, write_csv  # noqa: F401  (fixtures)


@pytest.fixture
def chain(tmp_path, config, tsai_outputs):
    """The runner's outputs up to F2, and the arguments ledger.build takes."""
    rp.run(config, to="f2")
    run = tmp_path / "runs" / "test-run"
    d = tsai_outputs["dedup"]
    return {"cleaned": tsai_outputs["cleaned"], "remove_list": d / "remove_list.csv", "groups_csv": d / "dedup_groups.csv",
            "f2": run / "final", "out": tmp_path / "ledger", "log": d / "dedup_log.jsonl"}


def rows(out):
    """{(split, part, doc_id): ledger row} over every ledger file."""
    got = {}
    for f in sorted(Path(out).rglob("*.parquet")):
        for r in pq.read_table(f).to_pylist():
            got[(r["split"], r["part"], r["doc_id"])] = r
    return got


def test_mode_c_decisions_per_document(chain):
    s = ledger.build(**chain)
    assert s["clean_mode"] == "C"
    assert s["totals"] == {"rows": 13, "rows_cleaned": 13, "kept": 9, "dropped_by_clean": 0, "removed_by_dedup": 2,
                           "dropped_by_f2": 2, "f2_error": 0, "clean_fix_by_text": None}
    assert s["by_pack"]["code-go"]["heldout"] == {"rows": 2, "rows_cleaned": 2, "kept": 1, "dropped_by_clean": 0,
                                                  "removed_by_dedup": 0, "dropped_by_f2": 1, "f2_error": 0}
    r = rows(chain["out"])
    assert len(r) == 13
    copy = r[("train", "code-go/part-00001.parquet", "g0")]  # removed by dedup: the copy of g0 in part 1
    assert (copy["final"], copy["dedup_role"], copy["dedup_group"], copy["dedup_list"]) == (
        "removed_by_dedup", "removed", "G000001", "dedup")
    assert (copy["dedup_match_rule"], copy["dedup_similarity"], copy["dedup_kept_doc"], copy["dedup_stage"]) == (
        "H1", 1.0, "g0", "within_pack")
    assert copy["f2_action"] is None and copy["final_part"] is None and copy["final_row"] is None
    surv = r[("train", "code-go/part-00000.parquet", "g0")]  # its survivor, then dropped by F2
    assert (surv["final"], surv["dedup_role"], surv["f2_action"], surv["f2_items"], surv["f2_offset"]) == (
        "dropped_by_f2", "survivor", "dropped", "fake:1", 0)
    g1 = r[("train", "code-go/part-00000.parquet", "g1")]
    assert (g1["final"], g1["dedup_role"], g1["f2_action"], g1["final_part"], g1["final_row"], g1["row_in_part"]) == (
        "kept", "none", "kept", "code-go/part-00000.parquet", 0, 1)
    assert r[("train", "en-dclm/part-00000.parquet", "e2")]["dedup_stage"] == "cross_pack"
    assert {x["clean_action"] for x in r.values()} == {"unknown"} and all(x["raw_row"] is None for x in r.values())


def test_final_rows_point_into_the_final_parts(chain):
    ledger.build(**chain)
    for (split, part, doc_id), r in rows(chain["out"]).items():
        if r["final"] == "kept":
            ids = pq.read_table(chain["f2"] / split / r["final_part"]).column("doc_id").to_pylist()
            assert ids[r["final_row"]] == doc_id


def test_sample_and_summary_hold_no_text(chain):
    s = ledger.build(**chain)
    sample = (chain["out"] / "ledger_sample.csv").read_text(encoding="utf-8")
    summary = (chain["out"] / "ledger_summary.json").read_text(encoding="utf-8")
    assert "synthetic text" not in sample + summary
    with (chain["out"] / "ledger_sample.csv").open(encoding="utf-8", newline="") as f:
        got = list(csv.DictReader(f))
    assert {r["final"] for r in got} == {"kept", "removed_by_dedup", "dropped_by_f2"}
    assert [f["file"] for f in s["files"]] == ["heldout/code-go.parquet", "train/code-go.parquet", "train/en-dclm.parquet"]


def test_same_inputs_same_bytes(chain, tmp_path):
    ledger.build(**chain)
    ledger.build(**{**chain, "out": tmp_path / "ledger2"})
    for f in sorted(chain["out"].rglob("*")):
        if f.is_file():
            assert f.read_bytes() == (tmp_path / "ledger2" / f.relative_to(chain["out"])).read_bytes(), f.name


def test_without_the_log_the_match_columns_are_empty(chain):
    ledger.build(**{**chain, "log": None})
    copy = rows(chain["out"])[("train", "code-go/part-00001.parquet", "g0")]
    assert copy["final"] == "removed_by_dedup" and copy["dedup_match_rule"] is None and copy["dedup_group"] == "G000001"


def make_raw(cleaned, raw, layout="split"):
    """Raw parts: each cleaned part plus one doc the cleaner 'dropped' (at row 1); e0's text 'fixed' by the cleaner."""
    for f in cleaned.rglob("*.parquet"):
        rel = f.relative_to(cleaned)
        split, pack, name = rel.parts
        t = pq.read_table(f).to_pylist()
        t.insert(1, dict(t[0], doc_id="x-" + t[0]["doc_id"]))
        for r in t:
            if r["doc_id"] == "e0":
                r["text"] = "synthetic text of e0, before the fix"
        dst = raw / rel if layout == "split" else raw / pack / split / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(t), dst)
    return write_reports(cleaned, raw)


def write_reports(cleaned, raw):
    """The cleaning job's report for every cleaned part, as run_tokenizer_sample.py writes it, from the raw part as it is
    now: input_sha256, input_rows, and keep / fix / drop. Mode B needs them; call again after changing a raw part."""
    for f in cleaned.glob("*/*/*.parquet"):
        split, pack, name = f.relative_to(cleaned).parts
        src = next((p for p in (raw / split / pack / name, raw / pack / split / name) if p.is_file()), None)
        if src is None:
            continue
        r, c = pq.read_table(src), {d["doc_id"]: d.get("text") for d in pq.read_table(f).to_pylist()}
        texts = r.column("text").to_pylist() if "text" in r.column_names else [None] * r.num_rows
        ids = r.column("doc_id").to_pylist()
        drop = sum(d not in c for d in ids)
        fix = sum(d in c and t is not None and c[d] != t for d, t in zip(ids, texts))
        rep = cleaned / "reports" / split / pack / f"{name}.json"
        rep.parent.mkdir(parents=True, exist_ok=True)
        rep.write_text(json.dumps({"input_sha256": sha(src), "input_rows": r.num_rows, "output_rows": r.num_rows - drop,
                                   "actions": {"keep": r.num_rows - drop - fix, "fix": fix, "drop": drop}}), encoding="utf-8")
    return raw


@pytest.mark.parametrize("layout", ["split", "pack"])
def test_mode_b_keep_fix_drop(chain, tmp_path, layout):
    raw = make_raw(chain["cleaned"], tmp_path / "raw", layout)
    s = ledger.build(**chain, raw=raw)
    assert s["clean_mode"] == "B"
    assert (s["totals"]["rows"], s["totals"]["dropped_by_clean"], s["totals"]["kept"], s["totals"]["clean_fix_by_text"]) == (
        17, 4, 9, 1)
    r = rows(chain["out"])
    drop = r[("train", "code-go/part-00000.parquet", "x-g0")]
    assert (drop["final"], drop["clean_action"], drop["raw_row"], drop["row_in_part"], drop["dedup_role"]) == (
        "dropped_by_clean", "drop", 1, None, None)
    g1 = r[("train", "code-go/part-00000.parquet", "g1")]
    assert (g1["clean_action"], g1["raw_row"], g1["row_in_part"], g1["final_row"]) == ("keep", 2, 1, 0)
    assert r[("train", "en-dclm/part-00000.parquet", "e0")]["clean_action"] == "fix"


def test_mode_b_checks_the_cleaning_reports(chain, tmp_path):
    raw = make_raw(chain["cleaned"], tmp_path / "raw")
    rep = chain["cleaned"] / "reports" / "train" / "en-dclm" / "part-00000.parquet.json"
    s = ledger.build(**chain, raw=raw)
    assert s["clean_reports"] == {"parts": 4, "input_rows": 17, "drop": 4, "fix": 1, "keep": 12}
    good = json.loads(rep.read_text(encoding="utf-8"))
    assert (good["input_rows"], good["actions"]) == (4, {"keep": 2, "fix": 1, "drop": 1})
    rep.write_text(json.dumps({**good, "output_rows": 2, "actions": {"keep": 2, "drop": 2}}), encoding="utf-8")
    with pytest.raises(ledger.Stop, match="cleaning report"):
        ledger.build(**{**chain, "out": tmp_path / "l2"}, raw=raw)


def test_mode_b_raw_from_another_run_stops(chain, tmp_path):
    raw = make_raw(chain["cleaned"], tmp_path / "raw")
    f = raw / "train" / "en-dclm" / "part-00000.parquet"
    t = pq.read_table(f).to_pylist()
    pq.write_table(pa.Table.from_pylist([r for r in t if r["doc_id"] != "e1"]), f)
    write_reports(chain["cleaned"], raw)
    with pytest.raises(ledger.Stop, match="not in the raw part"):
        ledger.build(**chain, raw=raw)


def test_mode_b_missing_raw_part_stops(chain, tmp_path):
    raw = make_raw(chain["cleaned"], tmp_path / "raw")
    (raw / "heldout" / "code-go" / "part-00000.parquet").unlink()
    with pytest.raises(ledger.Stop, match="no raw part has the sha256 the cleaning report names for heldout/code-go"):
        ledger.build(**chain, raw=raw)


def test_remove_list_with_another_doc_id_stops(chain, tmp_path):
    bad = tmp_path / "bad_remove.csv"
    write_csv(bad, HEADER, [["code-go", "train", "code-go/part-00001.parquet", 0, "g5"],
                            ["en-dclm", "train", "en-dclm/part-00000.parquet", 2, "e2"]])
    with pytest.raises(ledger.Stop, match="another doc_id"):
        ledger.build(**{**chain, "remove_list": bad})


def test_row_past_the_end_stops(chain, tmp_path):
    bad = tmp_path / "bad_remove.csv"
    write_csv(bad, HEADER, [["code-go", "train", "code-go/part-00001.parquet", 9, "g0"],
                            ["en-dclm", "train", "en-dclm/part-00000.parquet", 2, "e2"]])
    with pytest.raises(ledger.Stop, match="not rows of this cleaned part"):
        ledger.build(**{**chain, "remove_list": bad})


def test_groups_disagreeing_with_the_remove_list_stop(chain, tmp_path):
    rows_ = list(csv.reader(chain["groups_csv"].open(encoding="utf-8")))[1:]
    rows_[4][3] = "survivor"  # e2 removed in the list, a survivor in the groups
    bad = tmp_path / "bad_groups.csv"
    write_csv(bad, GROUP_HEADER, rows_)
    with pytest.raises(ledger.Stop, match="not the other"):
        ledger.build(**{**chain, "groups_csv": bad})


def test_unknown_part_stops(chain, tmp_path):
    bad = tmp_path / "bad_remove.csv"
    write_csv(bad, HEADER, [["code-go", "train", "code-go/part-00009.parquet", 0, "g0"]])
    with pytest.raises(ledger.Stop, match="not among the cleaned parts"):
        ledger.build(**{**chain, "remove_list": bad})


def test_final_part_out_of_order_stops(chain):
    f = chain["f2"] / "train" / "code-go" / "part-00000.parquet"
    t = pq.read_table(f)
    pq.write_table(t.take(list(reversed(range(t.num_rows)))), f)
    with pytest.raises(ledger.Stop, match="does not hold the ledger's"):
        ledger.build(**chain)


def test_missing_f2_report_stops(chain):
    (chain["f2"] / "train" / "en-dclm" / "part-00000.parquet.f2.json").unlink()
    with pytest.raises(ledger.Stop, match="no F2 report"):
        ledger.build(**chain)


def test_f2_report_naming_a_removed_doc_stops(chain):
    rep = chain["f2"] / "train" / "en-dclm" / "part-00000.parquet.f2.json"
    r = json.loads(rep.read_text(encoding="utf-8"))
    r["dropped"].append({"doc_id": "e2", "items": ["fake:1"], "offset": 0})  # e2 was removed by dedup: F2 never saw it
    rep.write_text(json.dumps(r), encoding="utf-8")
    with pytest.raises(ledger.Stop, match="not among the rows apply kept"):
        ledger.build(**chain)


def test_f2_errors_are_their_own_status(chain):
    rep = chain["f2"] / "train" / "en-dclm" / "part-00000.parquet.f2.json"
    r = json.loads(rep.read_text(encoding="utf-8"))
    r["errors"] = [["e1", "ValueError"]]
    rep.write_text(json.dumps(r), encoding="utf-8")
    f = chain["f2"] / "train" / "en-dclm" / "part-00000.parquet"
    t = pq.read_table(f)
    pq.write_table(t.filter(pa.array([d != "e1" for d in t.column("doc_id").to_pylist()])), f)
    s = ledger.build(**chain)
    e1 = rows(chain["out"])[("train", "en-dclm/part-00000.parquet", "e1")]
    assert (e1["final"], e1["f2_action"], e1["f2_items"]) == ("f2_error", "error", "error:ValueError")
    assert (s["totals"]["f2_error"], s["totals"]["kept"]) == (1, 8)


def test_survivors_dropped_by_f2_are_counted(chain):
    """F2 drops g0 (G000001's survivor) and h1 (one of G000002's held-out survivors); the removed copy of g0 never
    reaches F2. An F2 error on a survivor (h0 here) counts too, as survivor_loss.py counts it."""
    s = ledger.build(**chain)
    assert s["survivors_dropped_by_f2"] == {"total": 2, "by_pack": {"code-go": 2}}
    rep = chain["f2"] / "heldout" / "code-go" / "part-00000.parquet.f2.json"
    r = json.loads(rep.read_text(encoding="utf-8"))
    r["errors"] = [["h0", "ValueError"]]
    rep.write_text(json.dumps(r), encoding="utf-8")
    f = chain["f2"] / "heldout" / "code-go" / "part-00000.parquet"
    t = pq.read_table(f)
    pq.write_table(t.filter(pa.array([d != "h0" for d in t.column("doc_id").to_pylist()])), f)
    s = ledger.build(**chain)  # into the same --out: a rebuild replaces the ledger whole
    assert s["survivors_dropped_by_f2"] == {"total": 3, "by_pack": {"code-go": 3}}


def test_an_out_that_is_not_a_ledger_folder_stops_untouched(chain):
    other = chain["out"] / "notes.txt"
    other.parent.mkdir(parents=True)
    other.write_text("someone else's file", encoding="utf-8")
    with pytest.raises(ledger.Stop, match="not a ledger folder"):
        ledger.build(**chain)
    assert other.read_text(encoding="utf-8") == "someone else's file" and [p.name for p in chain["out"].iterdir()] == ["notes.txt"]


def test_a_rerun_replaces_an_earlier_ledger_whole(chain):
    ledger.build(**chain)
    stale = chain["out"] / "train" / "old-pack.parquet"
    stale.write_bytes(b"left by an earlier run")
    ledger.build(**chain)
    assert not stale.exists() and not list(chain["out"].parent.glob("ledger.partial"))
    assert not list(chain["out"].parent.glob("ledger.old"))


def test_cli(chain):
    args = [sys.executable, "-I", str(PIPELINE / "ledger.py"), "--cleaned", chain["cleaned"], "--remove-list",
            chain["remove_list"], "--groups", chain["groups_csv"], "--log", chain["log"], "--f2", chain["f2"],
            "--out", chain["out"]]
    p = subprocess.run(list(map(str, args)), capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout.strip().splitlines()[-1]) == {"clean_mode": "C", "rows": 13, "rows_cleaned": 13, "kept": 9,
                                                             "dropped_by_clean": 0, "removed_by_dedup": 2,
                                                             "dropped_by_f2": 2, "f2_error": 0}


def test_log_naming_a_survivor_stops(chain, tmp_path):
    entries = [json.loads(line) for line in chain["log"].read_text(encoding="utf-8").splitlines()]
    entries[1].update(removed_part="code-go/part-00000.parquet", removed_row_in_part=0, removed_id="g0")  # a survivor
    bad = tmp_path / "bad_log.jsonl"
    bad.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    with pytest.raises(ledger.Stop, match="dedup_log.jsonl but not the other"):
        ledger.build(**{**chain, "log": bad})


def test_row_in_two_groups_stops(chain, tmp_path):
    rows_ = list(csv.reader(chain["groups_csv"].open(encoding="utf-8")))[1:]
    rows_.append(["G000003", 2, 4, "survivor", "en-dclm", "train", "en-dclm/part-00000.parquet", 2, "e2"])
    bad = tmp_path / "bad_groups.csv"
    write_csv(bad, GROUP_HEADER, rows_)
    with pytest.raises(ledger.Stop, match="more than once"):
        ledger.build(**{**chain, "groups_csv": bad})


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_mode_b_finds_the_raw_part_by_sha256_under_any_name(chain, tmp_path):
    raw = make_raw(chain["cleaned"], tmp_path / "raw")
    src = raw / "train" / "en-dclm" / "part-00000.parquet"
    renamed = src.with_name("part-00000 (7).parquet")
    src.rename(renamed)
    rep = chain["cleaned"] / "reports" / "train" / "en-dclm" / "part-00000.parquet.json"
    rep.write_text(json.dumps({"input_sha256": sha(renamed), "input_rows": 4, "actions": {"keep": 2, "fix": 1, "drop": 1}}),
                   encoding="utf-8")
    s = ledger.build(**chain, raw=raw)
    files = {f["part"]: f for f in s["inputs"]["raw"]["files"]}
    assert files["train/en-dclm/part-00000.parquet"] == {"part": "train/en-dclm/part-00000.parquet",
                                                         "file": "train/en-dclm/part-00000 (7).parquet", "sha256": sha(renamed)}
    assert len(files) == 4


def test_mode_b_same_name_but_another_raw_file_stops(chain, tmp_path):
    raw = make_raw(chain["cleaned"], tmp_path / "raw")
    rep = chain["cleaned"] / "reports" / "train" / "en-dclm" / "part-00000.parquet.json"
    rep.write_text(json.dumps({"input_sha256": "0" * 64, "input_rows": 4, "actions": {"keep": 2, "fix": 1, "drop": 1}}),
                   encoding="utf-8")
    with pytest.raises(ledger.Stop, match="no raw part has the sha256"):
        ledger.build(**chain, raw=raw)


def test_a_stopped_rebuild_leaves_the_previous_ledger_whole(chain):
    ledger.build(**chain)
    before = {f.relative_to(chain["out"]).as_posix(): f.read_bytes() for f in chain["out"].rglob("*") if f.is_file()}
    f = chain["f2"] / "train" / "en-dclm" / "part-00000.parquet"
    t = pq.read_table(f)
    pq.write_table(t.take(list(reversed(range(t.num_rows)))), f)
    with pytest.raises(ledger.Stop):
        ledger.build(**chain)
    after = {f.relative_to(chain["out"]).as_posix(): f.read_bytes() for f in chain["out"].rglob("*") if f.is_file()}
    assert after == before and not list(chain["out"].parent.glob("ledger.partial"))




# --- scale and robustness (the scale audit, 14 Nov) -----------------------------------------------------------------
def test_two_builds_into_one_folder_are_refused(chain):
    import runlock
    with runlock.exclusive(chain["out"]):
        with pytest.raises(ledger.Stop, match="another process is writing"):
            ledger.build(**chain)


def write_texts(path, ids, texts):
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({"doc_id": ids, "text": texts, "pack_id": ["p"] * len(ids)}), path)
    return path


@pytest.mark.parametrize("batch", [1, 2, 3, 1000])
def test_streamed_text_compare_matches_the_in_memory_one(tmp_path, monkeypatch, batch):
    import pyarrow.compute as pc
    monkeypatch.setattr(ledger, "TEXT_BATCH", batch)
    raw_ids = [f"d{i}" for i in range(11)]
    raw_text = [f"text {i}" for i in range(11)]
    kept = [0, 1, 3, 4, 5, 8, 10]  # the cleaner dropped 2, 6, 7, 9 and fixed 4 and 10
    clean_text = [("FIXED " if i in (4, 10) else "") + raw_text[i] for i in kept]
    raw = write_texts(tmp_path / "raw.parquet", raw_ids, raw_text)
    cleaned = write_texts(tmp_path / "clean.parquet", [raw_ids[i] for i in kept], clean_text)
    matched = pa.array([i in kept for i in range(11)])
    rip = pa.array([kept.index(i) if i in kept else None for i in range(11)], pa.int64())
    streamed = ledger.same_text_streamed(raw, cleaned, matched)
    in_memory = ledger.same_text_in_memory(raw, cleaned, rip)
    want = [i in kept and i not in (4, 10) for i in range(11)]
    assert streamed.to_pylist() == want and in_memory.to_pylist() == want


def test_mode_b_with_a_cleaned_part_out_of_raw_order(chain, tmp_path):
    raw = make_raw(chain["cleaned"], tmp_path / "raw")
    f = chain["cleaned"] / "train" / "code-go" / "part-00000.parquet"
    rf = raw / "train" / "code-go" / "part-00000.parquet"
    t = pq.read_table(rf)
    pq.write_table(t.take(list(reversed(range(t.num_rows)))), rf)  # raw order reversed: the cleaned part is out of order
    write_reports(chain["cleaned"], raw)
    s = ledger.build(**chain, raw=raw)
    assert s["totals"]["dropped_by_clean"] == 4 and s["totals"]["kept"] == 9
    r = rows(chain["out"])
    assert r[("train", "code-go/part-00000.parquet", "g1")]["clean_action"] == "keep"
    assert r[("train", "code-go/part-00000.parquet", "x-g0")]["final"] == "dropped_by_clean"


def test_a_pack_folder_named_unlike_its_pack_id_can_be_rebuilt(chain):
    import shutil
    for root in (chain["cleaned"], chain["f2"]):
        for split in ("train",):
            shutil.move(str(root / split / "en-dclm"), str(root / split / "english-folder"))
    for name in ("remove_list", "groups_csv"):
        path = chain[name]
        path.write_text(path.read_text(encoding="utf-8").replace("en-dclm/part", "english-folder/part"), encoding="utf-8")
    log = chain["log"]
    log.write_text(log.read_text(encoding="utf-8").replace("en-dclm/part", "english-folder/part"), encoding="utf-8")
    ledger.build(**chain)
    s = ledger.build(**chain)  # the rerun used to stop: its files are named by pack_id, not by folder
    assert (chain["out"] / "train" / "en-dclm.parquet").is_file() and s["totals"]["kept"] == 9


def test_many_parts_keep_their_own_dedup_rows(tmp_path):
    """60 parts in 30 packs: each part's remove-list rows, groups and log land on that part (the by_part ordering bug)."""
    import csv
    cleaned, f2 = tmp_path / "cleaned", tmp_path / "final"
    removes, groups, logs = [], [], []
    for k in range(60):
        pack, part = f"p{k // 2:02d}", f"p{k // 2:02d}/part-{k % 2:05d}.parquet"
        ids = [f"{k}-{i}" for i in range(4)]
        for root, keep in ((cleaned, [0, 1, 2, 3]), (f2, [0, 2, 3])):
            path = root / "train" / part
            path.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(pa.table({"doc_id": [ids[i] for i in keep], "text": ["x"] * len(keep),
                                     "pack_id": [pack] * len(keep)}), path)
        (f2 / "train" / (part + ".f2.json")).write_text(json.dumps({"rows": 3, "set_sha256": "s", "dropped": [],
                                                                     "errors": []}), encoding="utf-8")
        removes.append([pack, "train", part, 1, ids[1]])
        groups += [[f"G{k:06d}", 2, 4, "survivor", pack, "train", part, 0, ids[0]],
                   [f"G{k:06d}", 2, 4, "removed", pack, "train", part, 1, ids[1]]]
        logs.append({"removed_split": "train", "removed_part": part, "removed_row_in_part": 1, "removed_id": ids[1],
                     "rule": "H1", "similarity": 1.0, "kept_id": ids[0], "stage": "within_pack"})
    write_csv(tmp_path / "remove_list.csv", HEADER, removes)
    write_csv(tmp_path / "groups.csv", GROUP_HEADER, groups)
    (tmp_path / "log.jsonl").write_text("".join(json.dumps(e) + "\n" for e in logs), encoding="utf-8")
    s = ledger.build(cleaned, tmp_path / "remove_list.csv", tmp_path / "groups.csv", f2, tmp_path / "ledger",
                     log=tmp_path / "log.jsonl")
    assert s["totals"]["removed_by_dedup"] == 60 and s["totals"]["kept"] == 180
    r = rows(tmp_path / "ledger")
    for k in range(60):
        part = f"p{k // 2:02d}/part-{k % 2:05d}.parquet"
        assert r[("train", part, f"{k}-1")]["final"] == "removed_by_dedup"
        assert r[("train", part, f"{k}-1")]["dedup_kept_doc"] == f"{k}-0"
        assert r[("train", part, f"{k}-0")]["dedup_role"] == "survivor"


# --- the review of the scale pass (14 Nov) ---------------------------------------------------------------------------
def files_of(folder):
    return {f.relative_to(folder).as_posix(): f.read_bytes() for f in folder.rglob("*") if f.is_file()}


def test_mode_b_without_a_text_column_stops(chain, tmp_path):
    raw = make_raw(chain["cleaned"], tmp_path / "raw")
    f = raw / "train" / "en-dclm" / "part-00000.parquet"
    pq.write_table(pq.read_table(f).drop_columns(["text"]), f)
    write_reports(chain["cleaned"], raw)
    with pytest.raises(ledger.Stop, match="no text column"):
        ledger.build(**chain, raw=raw)


def test_mode_b_reads_large_documents_in_small_batches(tmp_path, monkeypatch):
    """Batches are sized in bytes: 2 KB documents with a 5 KB budget are compared a few rows at a time, same result."""
    import arrowtools as at
    seen, real = [], at.iter_sized

    def spy(*a, **k):
        for b in real(*a, **k):
            seen.append(b.num_rows)
            yield b
    monkeypatch.setattr(at, "iter_sized", spy)
    monkeypatch.setattr(ledger, "TEXT_BYTES", 5000)
    ids = [f"d{i}" for i in range(9)]
    raw_text = [f"{i}" * 2000 for i in range(9)]
    kept = [0, 2, 3, 5, 8]
    raw = write_texts(tmp_path / "raw.parquet", ids, raw_text)
    cleaned = write_texts(tmp_path / "clean.parquet", [ids[i] for i in kept], ["fixed" if i == 3 else raw_text[i] for i in kept])
    got = ledger.same_text_streamed(raw, cleaned, pa.array([i in kept for i in range(9)]))
    assert got.to_pylist() == [i in kept and i != 3 for i in range(9)]
    assert seen and all(1 <= n <= 3 for n in seen)  # 2 or 3 rows of 2 KB a read, from both files


def test_a_failed_swap_keeps_the_previous_ledger_and_the_new_one(chain, monkeypatch):
    """Windows will not rename a folder while a file in it is open: the swap is retried, then undone; nothing is lost."""
    ledger.build(**chain)
    out = chain["out"]
    before, real = files_of(out), os.replace

    def replace(a, b):
        if Path(a).name == "ledger.partial":
            raise PermissionError(13, "a file in it is open")
        return real(a, b)
    monkeypatch.setattr(ledger.os, "replace", replace)
    monkeypatch.setattr(ledger, "RENAME_WAIT", 0)
    with pytest.raises(ledger.Stop, match="Nothing was lost: the previous ledger is still in"):
        ledger.build(**chain)
    assert files_of(out) == before and not out.with_name("ledger.old").exists()
    assert (out.with_name("ledger.partial") / "ledger_summary.json").is_file()  # the new one, whole, to look at


def test_a_rename_refused_for_a_moment_is_retried(chain, monkeypatch):
    real, refused = os.replace, []

    def replace(a, b):
        if Path(a).name == "ledger.partial" and len(refused) < 3:
            refused.append(a)
            raise PermissionError(13, "a virus scan has a file open")
        return real(a, b)
    monkeypatch.setattr(ledger.os, "replace", replace)
    monkeypatch.setattr(ledger, "RENAME_WAIT", 0)
    s = ledger.build(**chain)
    assert len(refused) == 3 and s["totals"]["kept"] == 9 and (chain["out"] / "ledger_summary.json").is_file()
    assert not chain["out"].with_name("ledger.partial").exists() and not chain["out"].with_name("ledger.old").exists()


def test_a_run_killed_between_the_two_renames_gets_the_previous_ledger_back(chain):
    ledger.build(**chain)
    out = chain["out"]
    before = files_of(out)
    os.replace(out, out.with_name("ledger.old"))  # killed after the first rename: no --out, the previous ledger in .old
    f = chain["f2"] / "train" / "en-dclm" / "part-00000.parquet"  # and the next run stops on a check
    t = pq.read_table(f)
    pq.write_table(t.take(list(reversed(range(t.num_rows)))), f)
    with pytest.raises(ledger.Stop):
        ledger.build(**chain)
    assert files_of(out) == before and not out.with_name("ledger.old").exists()


# --- review of PR #46 (patilvijay23, 15 Nov) -------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["ledger.partial", "ledger.old"])
def test_an_input_in_a_folder_the_ledger_deletes_is_never_touched(chain, name):
    """The cleaned parts at <out>.partial or <out>.old: the ledger deleted them. It now stops before touching anything."""
    moved = chain["out"].with_name(name)
    shutil.copytree(chain["cleaned"], moved)
    before = files_of(moved)
    with pytest.raises(ledger.Stop, match="overlap"):
        ledger.build(**{**chain, "cleaned": moved})
    assert files_of(moved) == before and not chain["out"].exists()


def test_an_out_inside_an_input_stops(chain):
    with pytest.raises(ledger.Stop, match="overlap"):
        ledger.build(**{**chain, "out": chain["f2"] / "ledger"})
    assert not (chain["f2"] / "ledger").exists()


@pytest.mark.parametrize("name", ["ledger.partial", "ledger.old"])
def test_a_folder_by_those_names_the_ledger_did_not_make_is_never_deleted(chain, name):
    other = chain["out"].with_name(name)
    other.mkdir(parents=True)
    (other / "notes.txt").write_text("someone else's", encoding="utf-8")
    with pytest.raises(ledger.Stop, match="not a folder the ledger made"):
        ledger.build(**chain)
    assert (other / "notes.txt").read_text(encoding="utf-8") == "someone else's" and not chain["out"].exists()


def test_a_staging_folder_a_killed_run_left_is_cleared(chain):
    stage = chain["out"].with_name("ledger.partial")
    stage.mkdir(parents=True)
    (stage / ledger.STAGING_MARK).write_text("x", encoding="utf-8")
    (stage / "half.parquet").write_bytes(b"half a ledger")
    s = ledger.build(**chain)
    assert s["totals"]["kept"] == 9 and not stage.exists()
    assert not (chain["out"] / ledger.STAGING_MARK).exists() and not list(chain["out"].rglob("half.parquet"))


def test_an_old_ledger_that_could_only_be_partly_deleted_is_cleared_next_time(chain):
    ledger.build(**chain)
    old = chain["out"].with_name("ledger.old")
    old.mkdir()
    (old / ledger.OLD_MARK).write_text("x", encoding="utf-8")
    (old / "train").mkdir()
    (old / "train" / "left.parquet").write_bytes(b"left over")
    ledger.build(**chain)
    assert not old.exists()


def test_mode_b_with_the_same_long_text_repeated_reads_small_batches(tmp_path, monkeypatch):
    """Dictionary-encoded repeated text is stored in a few bytes a row but decodes to the whole text: batches are sized
    from what was decoded, not from the footer."""
    import arrowtools as at
    seen = []
    real = at.iter_sized

    def spy(*a, **k):
        for b in real(*a, **k):
            seen.append(b.nbytes)
            yield b
    monkeypatch.setattr(at, "iter_sized", spy)
    monkeypatch.setattr(ledger, "TEXT_BYTES", 1 << 20)
    text = "abcdefgh" * 25_000  # 200 KB
    ids = [f"d{i}" for i in range(300)]
    for name in ("raw", "clean"):
        pq.write_table(pa.table({"doc_id": ids, "text": [text] * 300, "pack_id": ["p"] * 300}), tmp_path / f"{name}.parquet",
                       row_group_size=128)
    got = ledger.same_text_streamed(tmp_path / "raw.parquet", tmp_path / "clean.parquet", pa.array([True] * 300))
    assert got.to_pylist() == [True] * 300
    probes = [n for n in seen if n > 2 * (1 << 20)]
    assert len(probes) <= 2 and max(seen) <= 16 * 200_016  # one 16-row first read per file, then sized from it


# --- review of PR #46 (patilvijay23, 17 Nov) -------------------------------------------------------------------------
@pytest.mark.parametrize("fails", ["folder", "file"])
def test_a_backup_that_could_not_be_deleted_keeps_its_marker_and_is_cleared_next_time(chain, monkeypatch, fails):
    """Deleting a child of <out>.old fails for a moment (Windows: a file still open). The marker stays with what is
    left, so the next run knows the folder is the ledger's and deletes it, instead of refusing to touch it."""
    ledger.build(**chain)
    out = chain["out"]
    old = out.with_name("ledger.old")
    (out / "notes.txt").write_text("a file of the ledger folder", encoding="utf-8")  # a file child as well as folders
    failed = []
    real_rmtree, real_unlink = ledger.shutil.rmtree, Path.unlink

    def rmtree(path, *a, **k):
        if fails == "folder" and Path(path).parent == old and not failed:
            failed.append(Path(path).name)
            raise PermissionError(13, "in use", str(path))
        return real_rmtree(path, *a, **k)

    def unlink(self, *a, **k):
        if fails == "file" and self.parent == old and self.name == "notes.txt" and not failed:
            failed.append(self.name)
            raise PermissionError(13, "in use", str(self))
        return real_unlink(self, *a, **k)
    monkeypatch.setattr(ledger.shutil, "rmtree", rmtree)
    monkeypatch.setattr(Path, "unlink", unlink)
    ledger.build(**chain)  # the new ledger is published; the previous one could only be partly deleted
    assert failed and old.is_dir() and (old / ledger.OLD_MARK).is_file()
    assert any(child.name != ledger.OLD_MARK for child in old.iterdir())
    assert (out / "ledger_summary.json").is_file()
    s = ledger.build(**chain)  # the delete works again: the leftover is the ledger's, so it goes
    assert s["totals"]["kept"] == 9 and not old.exists() and (out / "ledger_summary.json").is_file()


def test_remove_marked_reports_what_it_could_not_delete(tmp_path, monkeypatch):
    folder = tmp_path / "x.old"
    (folder / "sub").mkdir(parents=True)
    (folder / ledger.OLD_MARK).write_text("x", encoding="utf-8")
    (folder / "sub" / "a.parquet").write_bytes(b"a")
    monkeypatch.setattr(ledger.shutil, "rmtree", lambda p, *a, **k: (_ for _ in ()).throw(PermissionError(13, "in use")))
    assert ledger.remove_marked(folder, ledger.OLD_MARK) is False and (folder / ledger.OLD_MARK).is_file()
    monkeypatch.undo()
    assert ledger.remove_marked(folder, ledger.OLD_MARK) is True and not folder.exists()
    assert ledger.remove_marked(folder, ledger.OLD_MARK) is True  # nothing there: nothing to do


# --- review of PR #46 (TEJASKUMAR-REDDY-J, 18 Nov) ------------------------------------------------------------------
@pytest.mark.parametrize("report", ["none", "no input_sha256", "no input_rows"])
def test_mode_b_stops_on_a_part_without_a_cleaning_report(chain, tmp_path, report):
    """Mode B needs every cleaned part's report: without one (a clean step that writes none, such as a bare
    run_clean.py) it would match a raw file by name and skip the check of the cleaner's drops, silently. It stops."""
    raw = make_raw(chain["cleaned"], tmp_path / "raw")
    rep = chain["cleaned"] / "reports" / "train" / "en-dclm" / "part-00000.parquet.json"
    if report == "none":
        rep.unlink()
    else:
        r = json.loads(rep.read_text(encoding="utf-8"))
        r.pop(report.split()[-1])
        rep.write_text(json.dumps(r), encoding="utf-8")
    with pytest.raises(ledger.Stop, match=r"--raw: train/en-dclm/part-00000.parquet has no cleaning report with input_rows, "
                                          r"actions and input_sha256.*leave out --raw \(mode C\)"):
        ledger.build(**chain, raw=raw)
    assert not chain["out"].exists()
    ledger.build(**chain)  # mode C needs no report
