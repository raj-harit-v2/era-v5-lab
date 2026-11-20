"""Tests for audit/audit_replay.py: a made-up clean job (audit_samples 5), then the replay of its sampled documents.

    python -m pytest teams/01-data-a/tests/audit/test_audit_replay.py -q      (from the repository root)

The real clean_job.py and the real spec v1.1 clean.py run on three tiny parts of two packs; the replay is checked against
what the job wrote. Made-up text only.
"""
import csv
import importlib.util
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

TEAM = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("audit_replay", TEAM / "audit" / "audit_replay.py")
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)
job = ar.job

CLEAN = (TEAM / "spec_v1_1" / "clean.py").resolve()
# name -> text; what the cleaner does with each is in the comment
DOCS = {
    "keep": "Area of a circle.\n",                              # nothing
    "one": "Area​ of a circle.\n",                         # DA-A1-004 fixes
    "two": "Area​ of a circle.\r\nSecond line.\r\n",       # DA-A1-004, then DA-A2-008 fix it
    "drop": "Subscribe to our newsletter\n",                    # DA-C1-006 drops
    "fix_drop": "Subscribe​ to our newsletter\n",          # DA-A1-004 fixes, then DA-C1-006 drops
}
PARTS = [("train", "en-dclm", 0), ("train", "en-dclm", 1), ("train", "en-fineweb-edu", 0)]


def write_part(root, split, pack, n):
    rows = [dict(doc_id=f"{split}-{pack}-{n}-{name}", text=text, pack_id=pack, lang_label="en", url="") for name, text in DOCS.items()]
    path = root / split / pack / f"part-{n:05d}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)
    return dict(path=f"{split}/{pack}/part-{n:05d}.parquet", pack_id=pack, split=split, rows=len(rows),
                bytes=path.stat().st_size, sha256=job.digest(path))


@pytest.fixture
def finished(tmp_path, monkeypatch, capsys):
    """The job has run on PARTS with audit_samples 5; the folder is tmp_path (the job writes below ./out)."""
    monkeypatch.chdir(tmp_path)
    shards = [write_part(tmp_path / "input", *p) for p in PARTS]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(dict(name="made up", total_docs=sum(s["rows"] for s in shards), shards=shards)))
    config = dict(clean=str(CLEAN), clean_sha256=job.digest(CLEAN), manifest=str(manifest), manifest_sha256=job.digest(manifest),
                  expected_parts={"train": 3}, batch_size=2, unsupported_policy="passthrough_with_explicit_status",
                  audit_samples=5, input_root="input", output_root="out/job")
    (tmp_path / "config.json").write_text(json.dumps(config))
    assert job.main(["--config", str(tmp_path / "config.json"), "--input-root", str(tmp_path / "input")]) == 0
    capsys.readouterr()
    return tmp_path


def replay(*extra, out="replay"):
    return ar.main(["--job", "out/job", "--input-root", "input", "--out", out, *extra])


def docs_of(root, pack="en-dclm", out="replay"):
    with (root / out / pack / "docs.csv").open(encoding="utf-8", newline="") as stream:
        return {row["doc_id"]: row for row in csv.DictReader(stream)}


def steps_of(root, doc_id, pack="en-dclm", out="replay"):
    lines = (root / out / pack / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    return [step for step in map(json.loads, lines) if step["doc_id"] == doc_id]


def test_every_sampled_document_replays_as_the_job_cleaned_it(finished):
    assert replay() == 0
    docs = docs_of(finished)
    assert sorted(d.split("-")[-1] for d in docs) == sorted(["one", "two", "drop", "fix_drop"] * 2)  # two parts; no keeps
    assert {row["replay_ok"] for row in docs.values()} == {"True"}


def test_a_document_that_several_rules_acted_on_shows_every_step_in_order(finished):
    replay()
    row = docs_of(finished)["train-en-dclm-0-two"]
    assert row["rules"] == "DA-A1-004|DA-A2-008" and row["sampled_for"] == "DA-A1-004|DA-A2-008" and row["final_action"] == "fix"
    first, second = steps_of(finished, "train-en-dclm-0-two")
    assert (first["step"], first["rule_id"], first["action"]) == (1, "DA-A1-004", "fix")
    assert (second["step"], second["rule_id"], second["action"]) == (2, "DA-A2-008", "fix")
    assert first["text_before"] == DOCS["two"] and second["text_before"] == first["text_after"]  # each rule gets the previous one's text
    cleaned = {r["doc_id"]: r["text"] for r in pq.read_table(finished / "replay/en-dclm/cleaned.parquet").to_pylist()}
    assert second["text_after"] == cleaned["train-en-dclm-0-two"]
    assert row["chars_raw"] == str(len(DOCS["two"])) and row["chars_cleaned"] == str(len(cleaned["train-en-dclm-0-two"]))


def test_a_document_that_is_fixed_and_then_dropped_has_both_steps_and_no_cleaned_row(finished):
    replay()
    doc_id = "train-en-dclm-1-fix_drop"
    row = docs_of(finished)[doc_id]
    assert row["rules"] == "DA-A1-004|DA-C1-006" and row["final_action"] == "drop" and row["chars_cleaned"] == ""
    fix, drop = steps_of(finished, doc_id)
    assert (fix["action"], drop["action"], drop["text_after"]) == ("fix", "drop", None)
    assert drop["text_before"] == fix["text_after"]
    raw = {r["doc_id"] for r in pq.read_table(finished / "replay/en-dclm/raw.parquet").to_pylist()}
    cleaned = {r["doc_id"] for r in pq.read_table(finished / "replay/en-dclm/cleaned.parquet").to_pylist()}
    assert doc_id in raw and doc_id not in cleaned


def test_a_document_no_rule_acted_on_is_not_replayed(finished):
    replay()
    assert not [d for d in docs_of(finished) if d.endswith("-keep")]
    ids = (finished / "replay/en-dclm/ids.txt").read_text().split()
    assert ids == list(docs_of(finished))


def test_only_the_named_packs_are_replayed(finished):
    assert replay("--pack", "en-fineweb-edu") == 0
    assert sorted(p.name for p in (finished / "replay").iterdir()) == ["en-fineweb-edu"]
    assert all(d.startswith("train-en-fineweb-edu-0-") for d in docs_of(finished, "en-fineweb-edu"))


def test_a_pack_without_examples_is_named(finished):
    with pytest.raises(job.JobError, match="no examples for pack.*not-a-pack"):
        replay("--pack", "not-a-pack")


def damage(root, part, doc_id, how):
    path = root / "out/job" / part
    rows = pq.read_table(path).to_pylist()
    if how == "text":
        next(r for r in rows if r["doc_id"] == doc_id)["text"] += "X"
    else:
        rows = [r for r in rows if r["doc_id"] != doc_id]
    pq.write_table(pa.Table.from_pylist(rows, schema=pq.read_schema(path)), path)


@pytest.mark.parametrize("how", ["text", "row"])
def test_a_document_that_does_not_replay_as_the_job_wrote_it_is_named_and_fails_the_run(finished, capsys, how):
    part, doc_id = "train/en-dclm/part-00000.parquet", "train-en-dclm-0-one"
    damage(finished, part, doc_id, how)  # a changed text, or a fixed document the job's part does not hold
    assert replay() == 1
    assert doc_id in capsys.readouterr().err
    docs = docs_of(finished)
    assert [d for d, row in docs.items() if row["replay_ok"] == "False"] == [doc_id]


def test_a_dropped_document_that_the_job_part_holds_does_not_replay(finished):
    part, doc_id = "train/en-dclm/part-00000.parquet", "train-en-dclm-0-drop"
    path = finished / "out/job" / part
    rows = pq.read_table(path).to_pylist() + [dict(pq.read_table(finished / "input" / part).to_pylist()[3])]
    assert rows[-1]["doc_id"] == doc_id
    pq.write_table(pa.Table.from_pylist(rows, schema=pq.read_schema(path)), path)
    assert replay() == 1
    assert [d for d, row in docs_of(finished).items() if row["replay_ok"] == "False"] == [doc_id]


def test_the_replay_will_not_write_into_the_job_folder(finished):
    with pytest.raises(job.JobError, match="outside the job folder"):
        replay(out="out/job/replay")
    assert not (finished / "out/job/replay").exists()


def test_a_job_without_examples_is_refused(finished):
    (finished / "out/job/rule_examples.csv").unlink()
    with pytest.raises(job.JobError, match="rule_examples.csv is not there"):
        replay()
    summary = json.loads((finished / "out/job/job_summary.json").read_text())
    summary["audit_samples"] = 0
    (finished / "out/job/job_summary.json").write_text(json.dumps(summary))
    with pytest.raises(job.JobError, match="audit_samples 0"):
        replay()


def test_the_cleaner_the_job_used_must_still_be_the_pinned_file(finished):
    summary = json.loads((finished / "out/job/job_summary.json").read_text())
    summary["clean_sha256"] = "1" * 64
    (finished / "out/job/job_summary.json").write_text(json.dumps(summary))
    with pytest.raises(job.JobError, match="differs from the pin"):
        replay()
    assert not (finished / "replay").exists()


def test_a_sampled_document_missing_from_the_raw_part_is_named(finished):
    part = "train/en-dclm/part-00000.parquet"
    path = finished / "input" / part
    rows = [r for r in pq.read_table(path).to_pylist() if not r["doc_id"].endswith("-one")]
    pq.write_table(pa.Table.from_pylist(rows, schema=pq.read_schema(path)), path)
    with pytest.raises(job.JobError, match="train-en-dclm-0-one is not in the raw part"):
        replay()
