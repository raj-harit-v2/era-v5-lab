"""Tests for source_index.py and prepare_ocr2.py (G10).

    G10_DECONTAM_TOOLS=<lab main>/teams/09-evaluation/decontam pytest teams/10-post-training/sft/test_prepare_ocr2.py -q

No network. Every row is a synthetic placeholder from ocr2_fixtures.py: tests only, never training data.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import convert as g10  # noqa: E402
import prepare_ocr2 as join  # noqa: E402
import source_index as si  # noqa: E402
from ocr2_fixtures import SET_ID, SHARED, World, allow_everything, ocr_row, read_jsonl, statement, write_jsonl  # noqa: E402

# Named decorators: pr-guard takes a dotted decorator line of a diff for an email address.
parametrize = pytest.mark.parametrize


def joined(out):
    return read_jsonl(out / "joined.jsonl")


def outcomes(out):
    return [row["outcome"] for row in read_jsonl(out / "exclusions.jsonl")]


def allow_in_table(monkeypatch):
    row = dict(g10.licence_row(SET_ID), decision="allowed")
    monkeypatch.setattr(g10, "licence_row", lambda set_id, table=None: row)


# --- the ordinal -------------------------------------------------------------------------------

@parametrize("value,expected", [("0", 0), ("17", 17), (5, 5), (str(2**63 - 1), 2**63 - 1)])
def test_parse_ordinal_accepts_canonical_non_negative_values(value, expected):
    assert si.parse_ordinal(value) == expected


@parametrize("value", ["-1", "-0", "+1", "01", " 1", "1 ", "1\n", "1.0", "1e3", "", "0x10", "١٢", "１２", "1_000",
                       str(2**63), "9" * 5000, True, False, 1.0, 1.5, None, -1, 2**63, b"1", ["1"]])
def test_parse_ordinal_refuses_everything_else(value):
    with pytest.raises(si.BadOrdinal):
        si.parse_ordinal(value)


def test_codeforces_question_follows_the_publisher_recipe():
    row = {"description": "D", "input_format": "I", "output_format": "O", "note": "N",
           "examples": [{"input": "1", "output": "2"}, {"input": "3"}]}
    assert si.assemble_question("codeforces", row) == (
        "D\n\nInput\n\nI\n\nOutput\n\nO\n\nExamples\n\nInput\n\n1\n\nOutput\n\n2\n\nInput\n\n3\n\nNote\n\nN")
    assert si.assemble_question("codeforces", {"description": "D", "examples": None, "note": ""}) == "D"
    assert si.assemble_question("codeforces", {"description": ""}) is None
    assert si.assemble_question("codeforces", {"description": "D", "examples": [{"input": None}]}) is None  # no guessed repair
    assert si.assemble_question("description", {"description": ""}) is None
    assert si.assemble_question("question", {"question": "Q"}) == "Q"


# --- ordinals, files, sources, splits ----------------------------------------------------------

def test_first_last_ordinal_and_the_file_boundary(tmp_path):
    rows = [ocr_row(n, "taco", "train", i) for n, i in enumerate(["0", "2", "3", "4", "5"])]
    world = World(tmp_path / "w", {0: rows})
    result = world.prepare(tmp_path / "out")
    assert [r["question"] for r in joined(tmp_path / "out")] == [statement(t) for t in ("T0", "T2", "T3", "T4")]
    side = read_jsonl(tmp_path / "out" / "joined.sidecar.jsonl")
    assert [(s["source_file"], s["source_local_ordinal"]) for s in side] == [
        ("taco-train-a", 0), ("taco-train-a", 2), ("taco-train-b", 0), ("taco-train-b", 1)]
    assert [s["source_row_key"][-1] for s in side] == [0, 2, 3, 4]  # the global ordinal, not a per-file one
    assert [s["source_problem_id"] for s in side] == ["taco-train-a/0", "taco-train-a/2", "taco-train-b/0", "taco-train-b/1"]
    assert outcomes(tmp_path / "out") == ["index_out_of_bounds"] and result["outcomes"]["index_out_of_bounds"] == 1


def test_same_index_in_two_sources_and_two_splits(tmp_path):
    rows = [ocr_row(0, "taco", "train", "1"), ocr_row(1, "apps", "train", "1"), ocr_row(2, "taco", "test", "1"),
            ocr_row(3, "apps", "test", "0")]
    world = World(tmp_path / "w", {0: rows})
    world.prepare(tmp_path / "out")
    assert [r["question"] for r in joined(tmp_path / "out")] == [statement("T1"), statement("A1")]
    assert outcomes(tmp_path / "out") == ["policy_protected_split", "policy_protected_split"]


def test_bad_indexes_never_resolve_and_minus_one_is_not_the_last_row(tmp_path):
    bad = ["-1", "1.0", "01", " 1", "+1", "", True, 1.5, None, "9" * 30, "١"]
    rows = [ocr_row(n, "taco", "train", value) for n, value in enumerate(bad)] + [ocr_row(90, "taco", "train", "99")]
    world = World(tmp_path / "w", {0: rows})
    result = world.prepare(tmp_path / "out")
    assert joined(tmp_path / "out") == []
    assert result["outcomes"] == {"invalid_index": len(bad), "index_out_of_bounds": 1}
    assert statement("T4") not in (tmp_path / "out" / "joined.jsonl").read_text()


def test_a_reordered_or_other_revision_source_file_stops_the_build(tmp_path):
    world = World(tmp_path / "w", {0: [ocr_row(0, "taco", "train", "0")]})
    world.prepare(tmp_path / "ok")
    # Same file name, same row count, rows in another order: every ordinal is in bounds and names another problem.
    path = world.root / "taco-train-a.jsonl"
    write_jsonl(path, list(reversed(read_jsonl(path))))
    with pytest.raises(si.SourceIndexError, match="not the pinned"):
        si.build(world.manifest_path, tmp_path / "other.sqlite")
    assert not (tmp_path / "other.sqlite").exists() and not (tmp_path / "other.sqlite.tmp").exists()


def test_an_index_built_from_another_manifest_is_not_reused(tmp_path):
    world = World(tmp_path / "w", {0: [ocr_row(0, "taco", "train", "0")]})
    old_index = world.index_path()
    world.prepare(tmp_path / "ok")
    world.source_specs["taco/train"]["revision"] = "e" * 40  # the manifest now names another snapshot
    world.write()
    with pytest.raises(si.SourceIndexError, match="another source manifest"):
        join.prepare(world.manifest_path, world.policy_path, world.shard_input(0), 0, tmp_path / "out", "diagnostic", old_index)
    assert not (tmp_path / "out" / "joined.jsonl").exists()


def test_identity_cross_check_must_hold(tmp_path):
    good = [{"kind": "question_sha256", "ordinal": 3, "sha256": si.text_sha256(statement("T3"))}]
    World(tmp_path / "a", {0: [ocr_row(0, "taco", "train", "3")]}, cross_checks={"taco/train": good}).prepare(tmp_path / "out")
    wrong = [{"kind": "question_sha256", "ordinal": 3, "sha256": si.text_sha256(statement("T2"))}]
    world = World(tmp_path / "b", {0: [ocr_row(0, "taco", "train", "3")]}, cross_checks={"taco/train": wrong})
    with pytest.raises(si.SourceIndexError, match="cross-check failed"):
        world.prepare(tmp_path / "out2")


def test_upstream_test_rows_never_join_and_their_text_is_not_stored(tmp_path):
    rows = [ocr_row(0, "apps", "test", "0"), ocr_row(1, "taco", "test", "0"), ocr_row(2, "taco", "valid", "0"),
            ocr_row(3, "taco", "train", "0")]
    world = World(tmp_path / "w", {0: rows})  # the shard path says train/python: it authorises nothing
    result = world.prepare(tmp_path / "out")
    assert result["outcomes"] == {"policy_protected_split": 2, "policy_split_not_allowed": 1, "eligible_joined": 1}
    assert result["by_source"]["apps/test"] == {"policy_protected_split": 1}
    con = sqlite3.connect(world.index_path())
    stored = con.execute("SELECT s.split, count(r.question), count(r.question_sha256) FROM rows r JOIN sources s"
                         " ON s.source_key = r.source_key GROUP BY s.split ORDER BY s.split").fetchall()
    assert stored == [("test", 0, 3), ("train", 10, 10)]  # test rows: a hash each, no text
    for name in ("joined.jsonl", "joined.sidecar.jsonl", "exclusions.jsonl"):
        text = (tmp_path / "out" / name).read_text()
        assert statement("X0") not in text and statement("Y0") not in text
    assert statement("X0").encode() not in world.index_path().read_bytes()


def test_a_question_already_in_the_row_must_agree(tmp_path):
    rows = [ocr_row(0, "taco", "train", "1", question="  " + statement("T1").replace(": ", ":\r\n") + "\r\n"),
            ocr_row(1, "taco", "train", "1", question=statement("T1") + "\r\n"),
            ocr_row(2, "taco", "train", "1", question=statement("T2")),
            ocr_row(3, "taco", "train", "1", question=statement("T1").upper())]
    world = World(tmp_path / "w", {0: rows})
    result = world.prepare(tmp_path / "out")
    # Row 0 differs inside the text (a line break where the source has a space): that is a mismatch too.
    assert result["outcomes"] == {"question_mismatch": 3, "eligible_joined": 1}
    assert [r["id"] for r in joined(tmp_path / "out")] == ["fx0001"] and joined(tmp_path / "out")[0]["question"] == statement("T1")
    assert result["tags"]["question_verified_against_row"] == 1
    assert statement("T2") not in (tmp_path / "out" / "joined.jsonl").read_text()  # never overwritten, never emitted


def test_families_are_tracked_and_a_test_problem_is_held_out_of_train(tmp_path):
    rows = [ocr_row(0, "taco", "train", "0"), ocr_row(1, "taco", "train", "0"), ocr_row(2, "taco", "train", "1"),
            ocr_row(3, "apps", "train", "2")]  # apps/train[2] is the statement of taco/test[1]
    world = World(tmp_path / "w", {0: rows})
    result = world.prepare(tmp_path / "out")
    side = read_jsonl(tmp_path / "out" / "joined.sidecar.jsonl")
    assert side[0]["problem_family_key"] == side[1]["problem_family_key"] != side[2]["problem_family_key"]
    assert result["families"] == {"unique": 2, "with_several_solutions": 1, "max_solutions": 2, "also_in_another_source": 0}
    assert result["outcomes"]["policy_protected_family"] == 1 and SHARED not in (tmp_path / "out" / "joined.jsonl").read_text()


def test_an_explicit_protected_family_key_is_held_out(tmp_path):
    key = "sha256:" + si.family_sha256(statement("T0"))
    world = World(tmp_path / "w", {0: [ocr_row(0, "taco", "train", "0"), ocr_row(1, "taco", "train", "1")]},
                  policy={"protected_family_keys": [key]})
    assert world.prepare(tmp_path / "out")["outcomes"] == {"policy_protected_family": 1, "eligible_joined": 1}


# --- policy ------------------------------------------------------------------------------------

def test_quality_licence_dataset_and_shape_outcomes(tmp_path):
    rows = [ocr_row(0, "taco", "train", "0", judgement="wrong"),
            ocr_row(1, "taco", "train", "0", judgement="unsure"),
            ocr_row(2, "taco", "train", "0", pass_rate="0.94"),
            ocr_row(3, "taco", "train", "0", pass_rate="-1"),
            ocr_row(4, "taco", "train", "0", license="gpl-3.0"),
            ocr_row(5, "taco", "train", "0", license=""),
            ocr_row(6, "leetcode", "train", "0"),
            ocr_row(7, "taco", "train", "0", pass_rate="many"),
            {k: v for k, v in ocr_row(8, "taco", "train", "0").items() if k != "r1_generation"},
            ocr_row(3, "taco", "train", "1"),  # the id of row 3 again
            ocr_row(9, "taco", "train", "0")]
    world = World(tmp_path / "w", {0: rows})
    result = world.prepare(tmp_path / "out")
    assert result["outcomes"] == {
        "policy_row_licence": 2, "quality_critique_wrong": 1, "quality_judgement_unknown": 1, "quality_execution_failed": 1,
        "malformed_row": 2, "duplicate_row_id": 1, "unknown_dataset": 1, "eligible_joined": 2}
    assert result["tags"] == {"exec_missing": 1, "exec_pass": 1, "question_verified_against_row": 0}
    assert result["groups"] == {"policy_excluded": 5, "malformed_or_unresolved": 4, "eligible_joined": 2}
    assert sum(result["groups"].values()) == result["raw_rows"] == len(rows)
    world.policy["target_quality"]["missing_execution_evidence"] = "exclude"
    world.write()
    assert world.prepare(tmp_path / "out2")["outcomes"]["quality_execution_missing"] == 1


def test_a_source_with_no_pinned_snapshot_is_held_not_guessed(tmp_path):
    sources = {"taco/train": [("taco-train-a", [statement("T0")])]}
    world = World(tmp_path / "w", {0: [ocr_row(0, "taco", "train", "0"), ocr_row(1, "apps", "train", "0")]}, sources=sources)
    result = world.prepare(tmp_path / "out")
    assert result["outcomes"] == {"held_source_unavailable": 1, "eligible_joined": 1}
    assert result["by_source"]["apps/train"] == {"held_source_unavailable": 1}


def test_admission_mode_is_refused_under_a_reserve_ruling(tmp_path):
    world = World(tmp_path / "w", {0: [ocr_row(0, "taco", "train", "0")]})
    with pytest.raises(join.Refusal, match="not allowed"):
        world.prepare(tmp_path / "out", mode="admission")
    assert not (tmp_path / "out").exists()
    code = join.main(["--source-manifest", str(world.manifest_path), "--policy", str(world.policy_path), "--input",
                      str(world.shard_input(0)), "--shard-id", "0", "--out-dir", str(tmp_path / "out"), "--mode", "admission"])
    assert code == 3 and not (tmp_path / "out").exists()


def test_a_policy_cannot_overrule_the_licence_table(tmp_path):
    world = World(tmp_path / "w", {0: [ocr_row(0, "taco", "train", "0")]})
    allow_everything(world)  # the policy file now says allowed; licences/licence_table.md still says TSAI reserves
    for mode in ("diagnostic", "admission"):
        with pytest.raises(join.Refusal, match="the table decides"):
            world.prepare(tmp_path / mode, mode=mode)


@parametrize("change,reason", [
    (lambda p: p["teacher"].update(model=""), "teacher"),
    (lambda p: p["teacher"].update(licence=""), "teacher"),
    (lambda p: p["teacher"].update(approved=False), "teacher"),
    (lambda p: p["ocr2"].update(distribution_licence=""), "distribution licence"),
])
def test_admission_mode_needs_a_known_approved_teacher_and_licence(tmp_path, monkeypatch, change, reason):
    allow_in_table(monkeypatch)
    world = World(tmp_path / "w", {0: [ocr_row(0, "taco", "train", "0")]})
    allow_everything(world)
    change(world.policy)
    world.write()
    with pytest.raises(join.Refusal, match=reason):
        world.prepare(tmp_path / "out", mode="admission")
    assert world.prepare(tmp_path / "diag")["outcomes"] == {"eligible_joined": 1}  # still a valid diagnostic run


def test_admission_mode_holds_unapproved_and_unverified_sources(tmp_path, monkeypatch):
    allow_in_table(monkeypatch)
    rows = [ocr_row(0, "taco", "train", "0"), ocr_row(1, "apps", "train", "0"), ocr_row(2, "code_contests", "train", "1")]
    world = World(tmp_path / "w", {0: rows}, verified=("taco/train", "apps/train"))
    allow_everything(world)
    world.policy["sources"]["apps"]["training_approved"] = False
    world.write()
    result = world.prepare(tmp_path / "out", mode="admission")
    assert result["mode"] == "admission"
    assert result["outcomes"] == {"held_source_not_approved": 1, "held_identity_unverified": 1, "eligible_joined": 1}
    assert [r["dataset"] for r in joined(tmp_path / "out")] == ["taco"]


# --- binding and accounting --------------------------------------------------------------------

def test_sidecar_binds_every_joined_row_to_its_original_rows(tmp_path):
    rows = [ocr_row(0, "apps", "test", "0"), ocr_row(1, "taco", "train", "4"), ocr_row(2, "taco", "train", "x"),
            ocr_row(3, "code_contests", "train", "1"), ocr_row(4, "apps", "train", "0")]
    world = World(tmp_path / "w", {1: rows}, shard_rows={0: 1000})  # shard 0 has 1000 original rows, whatever is kept of it
    result = world.prepare(tmp_path / "out", shard_id=1)
    side = read_jsonl(tmp_path / "out" / "joined.sidecar.jsonl")
    assert result["index_base"] == 1000 and result["id_range"] == [1000, 1005]
    assert [s["rendered_id"] for s in side] == [f"{SET_ID}/{n}" for n in (1000, 1001, 1002)]
    assert [s["ocr_row_key"] for s in side] == [[world.manifest()["ocr2"]["revision"], "train/python/train-00001-of-00002.parquet", n]
                                                for n in (1, 3, 4)]
    assert [s["ocr_id"] for s in side] == ["fx0001", "fx0003", "fx0004"] == [r["id"] for r in joined(tmp_path / "out")]
    assert [s["source_row_key"][2:] for s in side] == [["taco", "train", 4], ["code_contests", "train", 1], ["apps", "train", 0]]
    assert side[1]["licence"] == {"ocr2_distribution": "cc-by-4.0", "row_tag": "apache-2.0", "source_statement": "cc-by-4.0",
                                  "attribution": world.policy["sources"]["code_contests"]["attribution"]}
    assert side[0]["teacher"] == {"model": "DeepSeek-R1", "licence": "MIT"}
    excluded = read_jsonl(tmp_path / "out" / "exclusions.jsonl")
    assert [(e["ocr_row_key"][2], e["outcome"]) for e in excluded] == [(0, "policy_protected_split"), (2, "invalid_index")]
    manifest = json.loads((tmp_path / "out" / "join_manifest.json").read_text())
    assert manifest == result
    for name, sha in result["outputs"].items():
        assert si.sha256_file(tmp_path / "out" / name) == sha
    assert result["policy_sha256"] == si.sha256_file(world.policy_path) and result["mode"] == "diagnostic"
    again = world.prepare(tmp_path / "again", shard_id=1)
    assert again == result  # same input, same bytes: no timestamp, no path


def test_the_id_range_needs_the_original_row_count_of_earlier_shards(tmp_path):
    world = World(tmp_path / "w", {1: [ocr_row(0, "taco", "train", "0")]})  # shard 0 has no known row count
    with pytest.raises(si.SourceIndexError, match="original row count of shard 0"):
        world.prepare(tmp_path / "out", shard_id=1)


def test_the_input_must_be_the_pinned_file_with_the_pinned_row_count(tmp_path):
    world = World(tmp_path / "w", {0: [ocr_row(0, "taco", "train", "0")]})
    write_jsonl(world.shard_input(0), [ocr_row(0, "taco", "train", "1")])
    with pytest.raises(si.SourceIndexError, match="the manifest pins"):
        world.prepare(tmp_path / "out")
    with pytest.raises(si.SourceIndexError, match="no pinned local input"):
        world.prepare(tmp_path / "out", shard_id=1)
    assert not (tmp_path / "out" / "joined.jsonl").exists()


def test_joined_file_is_what_convert_reads(tmp_path):
    rows = [ocr_row(0, "taco", "train", "3"), ocr_row(1, "taco", "train", "4", r1_generation="no think block here")]
    world = World(tmp_path / "w", {0: rows})
    world.prepare(tmp_path / "out")
    lines, manifest = g10.convert(SET_ID, g10.read_rows(tmp_path / "out" / "joined.jsonl"), None, None, first_index=40)
    sample = json.loads(lines[0])
    assert sample["id"] == f"{SET_ID}/40" and sample["source_id"] == "fx0000" and statement("T3") in sample["text"]
    assert manifest["rows_in"] == 2 and manifest["rows"] == 1
    assert manifest["skipped"] == {"generation does not start with one <think>...</think> block": 1}


# --- the four publisher sources, each in the file format its own repository ships -----------------

def card_question(ds_name, benchmark):
    """Test oracle: get_question() of the OCR-2 dataset card ("How to use it"), applied to one loaded row.

    Kept apart from si.assemble_question on purpose, so a slip in one of the two shows up as a difference.
    """
    if ds_name == "code_contests":
        return benchmark["description"] or None
    if ds_name in ("taco", "apps"):
        return benchmark["question"]
    if ds_name == "open-r1/codeforces":
        if not benchmark["description"]:
            return None
        question = benchmark["description"]
        if benchmark["input_format"]:
            question += "\n\nInput\n\n" + benchmark["input_format"]
        if benchmark["output_format"]:
            question += "\n\nOutput\n\n" + benchmark["output_format"]
        if benchmark["examples"]:
            question += "\n\nExamples"
            for example in benchmark["examples"]:
                if "input" in example:
                    question += "\n\nInput\n\n" + example["input"]
                if "output" in example:
                    question += "\n\nOutput\n\n" + example["output"]
        if benchmark["note"]:
            question += "\n\nNote\n\n" + benchmark["note"]
        return question
    return None


def write_arrow_stream(path, batches, file_format=False):
    """TACO ships Arrow IPC streams (what datasets.Dataset.from_file reads). One record batch per list."""
    import pyarrow as pa

    schema = pa.schema([("question", pa.string()), ("solutions", pa.string()), ("url", pa.string())])
    with pa.OSFile(str(path), "wb") as sink:
        writer = (pa.ipc.new_file if file_format else pa.ipc.new_stream)(sink, schema)
        for rows in batches:
            writer.write_batch(pa.RecordBatch.from_pylist(rows, schema=schema))
        writer.close()
    return si.sha256_file(path)


def taco_row(tag):
    return {"question": statement(tag), "solutions": "[]", "url": f"https://fixture.invalid/{tag}"}


def arrow_taco(world, batches_per_file):
    """Swap the fixture's taco/train for Arrow stream files, the way BAAI/TACO stores the split."""
    files = []
    for n, batches in enumerate(batches_per_file):
        name = f"data-{n:05d}-of-{len(batches_per_file):05d}.arrow"
        sha = write_arrow_stream(world.root / name, batches)
        files.append({"name": name, "path": name, "sha256": sha, "rows": sum(len(b) for b in batches)})
    world.source_specs["taco/train"].update(kind="arrow", problem_id_field="url", files=files,
                                            total_rows=sum(f["rows"] for f in files))
    world.write()


def test_arrow_stream_files_resolve_in_stream_order_across_batches_and_files(tmp_path):
    rows = [ocr_row(n, "taco", "train", i) for n, i in enumerate(["0", "2", "3", "4", "5"])]
    world = World(tmp_path / "w", {0: rows})
    arrow_taco(world, [[[taco_row("R0"), taco_row("R1")], [taco_row("R2")]], [[taco_row("R3")], [taco_row("R4")]]])
    result = world.prepare(tmp_path / "out")
    assert [r["question"] for r in joined(tmp_path / "out")] == [statement(t) for t in ("R0", "R2", "R3", "R4")]
    side = read_jsonl(tmp_path / "out" / "joined.sidecar.jsonl")
    assert [(s["source_file"], s["source_local_ordinal"]) for s in side] == [
        ("data-00000-of-00002.arrow", 0), ("data-00000-of-00002.arrow", 2),  # local ordinal 2 sits in the second batch
        ("data-00001-of-00002.arrow", 0), ("data-00001-of-00002.arrow", 1)]
    assert [s["source_row_key"][-1] for s in side] == [0, 2, 3, 4]
    assert side[1]["source_problem_id"] == "https://fixture.invalid/R2"
    assert result["outcomes"] == {"eligible_joined": 4, "index_out_of_bounds": 1}


def test_an_arrow_file_that_is_not_the_pinned_stream_stops_the_build(tmp_path):
    world = World(tmp_path / "w", {0: [ocr_row(0, "taco", "train", "0")]})
    arrow_taco(world, [[[taco_row("R0"), taco_row("R1")]]])
    spec = world.source_specs["taco/train"]["files"][0]
    # Same rows in the IPC *file* format: the TACO loader could not read it, so neither does the index.
    spec["sha256"] = write_arrow_stream(world.root / spec["name"], [[taco_row("R0"), taco_row("R1")]], file_format=True)
    world.write()
    with pytest.raises(si.SourceIndexError, match="not an Arrow IPC stream"):
        si.build(world.manifest_path, tmp_path / "a.sqlite")
    # A stream with the rows in another order has another sha256: refused before a single row is read.
    write_arrow_stream(world.root / spec["name"], [[taco_row("R1"), taco_row("R0")]])
    with pytest.raises(si.SourceIndexError, match="not the pinned"):
        si.build(world.manifest_path, tmp_path / "b.sqlite")
    assert not list(tmp_path.glob("*.sqlite*"))


def test_all_four_publisher_sources_resolve_at_the_card_recipe(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    apps = [{"id": n, "question": statement(f"P{n}"), "solutions": "[]", "difficulty": "interview", "url": ""} for n in range(3)]
    contests = [{"description": statement("K0")}, {"description": ""}, {"description": statement("K2")}]
    forces = [
        {"id": "1/A", "description": statement("F0"), "input_format": "FIXTURE in", "output_format": "FIXTURE out",
         "examples": [{"input": "1 2", "output": "3"}, {"input": "4 5", "output": "9"}], "note": "FIXTURE note"},
        {"id": "1/B", "description": statement("F1"), "input_format": None, "output_format": "", "examples": [], "note": None},
        {"id": "1/C", "description": None, "input_format": "FIXTURE in", "output_format": None, "examples": None, "note": None},
        {"id": "1/D", "description": statement("F3"), "input_format": None, "output_format": None,
         "examples": [{"input": "7", "output": None}], "note": None},
    ]
    rows = [ocr_row(0, "taco", "train", "1"), ocr_row(1, "apps", "train", "2"), ocr_row(2, "code_contests", "train", "2"),
            ocr_row(3, "open-r1/codeforces", "train", "0"), ocr_row(4, "open-r1/codeforces", "train", "1"),
            ocr_row(5, "open-r1/codeforces", "train", "2"), ocr_row(6, "code_contests", "train", "1"),
            ocr_row(7, "open-r1/codeforces", "train", "3"), ocr_row(8, "open-r1/codeforces", "test", "0"),
            ocr_row(9, "open-r1/codeforces", "train", "4")]
    world = World(tmp_path / "w", {0: rows})
    arrow_taco(world, [[[taco_row("R0")], [taco_row("R1")]]])
    apps_sha = write_jsonl(world.root / "train.jsonl", apps)
    world.source_specs["apps/train"].update(problem_id_field="id", total_rows=3, files=[
        {"name": "train.jsonl", "path": "train.jsonl", "sha256": apps_sha, "rows": 3}])
    cc_sha = write_jsonl(world.root / "cc.jsonl", contests)
    world.source_specs["code_contests/train"].update(total_rows=3, files=[
        {"name": "cc.jsonl", "path": "cc.jsonl", "sha256": cc_sha, "rows": 3}])
    example = pa.struct([("input", pa.string()), ("output", pa.string())])
    schema = pa.schema([("id", pa.string()), ("description", pa.string()), ("input_format", pa.string()),
                        ("output_format", pa.string()), ("examples", pa.list_(example)), ("note", pa.string())])
    pq.write_table(pa.Table.from_pylist(forces, schema=schema), world.root / "train-00000-of-00001.parquet")
    world.source_specs["open-r1/codeforces/train"] = {
        "dataset": "open-r1/codeforces", "split": "train", "repo": "fixture/open-r1-codeforces", "revision": "f" * 40,
        "kind": "parquet", "assembly": "codeforces", "protected": False, "problem_id_field": "id", "total_rows": 4,
        "files": [{"name": "train-00000-of-00001.parquet", "path": "train-00000-of-00001.parquet", "rows": 4,
                   "sha256": si.sha256_file(world.root / "train-00000-of-00001.parquet")}],
        "identity": {"level": "diagnostic"}}
    world.write()
    result = world.prepare(tmp_path / "out")

    expected = [card_question("taco", taco_row("R1")), card_question("apps", apps[2]), card_question("code_contests", contests[2]),
                card_question("open-r1/codeforces", forces[0]), card_question("open-r1/codeforces", forces[1])]
    assert all(isinstance(q, str) and q for q in expected)
    assert [r["question"] for r in joined(tmp_path / "out")] == expected
    assert expected[3].endswith("FIXTURE in\n\nOutput\n\nFIXTURE out\n\nExamples\n\nInput\n\n1 2\n\nOutput\n\n3"
                                "\n\nInput\n\n4 5\n\nOutput\n\n9\n\nNote\n\nFIXTURE note")
    side = read_jsonl(tmp_path / "out" / "joined.sidecar.jsonl")
    assert [s["source_row_key"][2:] for s in side] == [["taco", "train", 1], ["apps", "train", 2], ["code_contests", "train", 2],
                                                       ["open-r1/codeforces", "train", 0], ["open-r1/codeforces", "train", 1]]
    assert [s["source_problem_id"] for s in side][1::2] == ["2", "1/A"]
    # The card asserts `question is not None` (rows 5, 6) and would raise on a null example part (row 7): none is repaired.
    assert card_question("open-r1/codeforces", forces[2]) is None and card_question("code_contests", contests[1]) is None
    with pytest.raises(TypeError):
        card_question("open-r1/codeforces", forces[3])
    assert outcomes(tmp_path / "out") == ["source_question_unusable"] * 3 + ["policy_protected_split", "index_out_of_bounds"]
    assert result["by_source"]["open-r1/codeforces/train"] == {
        "eligible_joined": 2, "index_out_of_bounds": 1, "source_question_unusable": 2}
    assert result["by_source"]["open-r1/codeforces/test"] == {"policy_protected_split": 1}
