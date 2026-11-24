"""The pipeline's clean job (pipeline/clean_job.py), with made-up rows only.

  python -m pytest teams/01-data-a/pipeline/tests/test_clean_job.py -q      (from the repository root)

The real job and the real spec v1.1 clean.py run on four tiny parts. Covers the job's input checks (the cleaner's pin, the
manifest, the config), the per-part processing and its counts, and resume: a failure is injected into one part, then the
job is run again with "resume": true.
"""
import csv
import json
import zlib
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import clean_job as job
from conftest import PIPELINE

CLEAN = (PIPELINE.parent / "spec_v1_1" / "clean.py").resolve()
PIN = job.digest(CLEAN)
job.load_clean(CLEAN, PIN)
PARTS = [("train", "en-dclm", 0), ("train", "en-dclm", 1), ("heldout", "en-dclm", 0), ("train", "cadj-commits", 0)]
TEXTS = ["Area of a circle.\n", "Area​ of a circle.\n", "Subscribe to our newsletter\n"]


def write_part(root, split, pack, n, texts=TEXTS):
    """One made-up raw part under root/split/pack; returns its manifest entry."""
    rows = [dict(doc_id=f"{split}-{pack}-{n}-d{i}", text=text, pack_id=pack, lang_label="en", url="") for i, text in enumerate(texts)]
    path = root / split / pack / f"part-{n:05d}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)
    return dict(path=f"{split}/{pack}/part-{n:05d}.parquet", pack_id=pack, split=split, rows=len(rows),
                bytes=path.stat().st_size, sha256=job.digest(path))


def write_manifest(path, shards):
    path.write_text(json.dumps(dict(name="made up", total_docs=sum(s["rows"] for s in shards), shards=shards)))
    return job.digest(path)


@pytest.fixture
def sample(tmp_path, monkeypatch):
    """Four made-up parts, a manifest for them, and a config; the job runs from tmp_path (it writes below ./out)."""
    monkeypatch.chdir(tmp_path)
    shards = [write_part(tmp_path / "input", *part) for part in PARTS]
    config = dict(clean=str(CLEAN), clean_sha256=PIN, manifest=str(tmp_path / "manifest.json"),
                  manifest_sha256=write_manifest(tmp_path / "manifest.json", shards), expected_parts={"train": 3, "heldout": 1},
                  batch_size=2, unsupported_policy="passthrough_with_explicit_status", audit_samples=5, input_root="input", output_root="out/job")

    def run(out="out/job", resume=False, only=(), drop=(), **extra):
        data = {k: v for k, v in dict(config, output_root=out, **({"resume": resume} if resume is not False else {}), **extra).items()
                if k not in drop}
        path = tmp_path / f"config-{out.replace('/', '_')}.json"
        path.write_text(json.dumps(data))
        return job.main(["--config", str(path), "--input-root", str(tmp_path / "input"), *[a for p in only for a in ("--only", p)]])

    run.config = config
    return tmp_path, shards, run


def fail_on(monkeypatch, part):
    real = job.process_part

    def flaky(source, shard, output, batch_size, **more):
        if shard["path"] == part:
            raise job.JobError("injected failure: " + part)
        return real(source, shard, output, batch_size, **more)

    monkeypatch.setattr(job, "process_part", flaky)


def outputs(folder):
    """What a finished job must make the same however it got there: each part's bytes, the rule counts, the cleaned manifest."""
    manifest = json.loads((folder / "cleaned_manifest.json").read_text())
    return (manifest, (folder / "rule_counts.csv").read_text(),
            {p["part"]: job.digest(folder / p["part"]) for p in manifest["parts"]})


def interrupted(monkeypatch, run, part="train/en-dclm/part-00001.parquet"):
    """Run the job until it fails on `part`: parts before it are finished, the others are not started."""
    with monkeypatch.context() as m:
        fail_on(m, part)
        with pytest.raises(job.JobError, match="injected failure"):
            run()


# --- the cleaner: the file the config names, once its sha256 is the pin ----------------------------------------------------
def test_the_cleaner_is_the_file_the_config_names_and_the_job_reports_it(sample):
    tmp, shards, run = sample
    assert run() == 0
    assert Path(job.clean.__file__).resolve() == CLEAN
    summary = json.loads((tmp / "out/job/job_summary.json").read_text())
    assert (summary["clean_sha256"], summary["clean_path"]) == (PIN, str(CLEAN))


def test_the_cleaner_is_not_run_unless_it_has_the_pinned_sha256(tmp_path, monkeypatch):
    fake = tmp_path / "clean.py"
    fake.write_text(f"open({str(tmp_path / 'ran')!r}, 'w').close()\n")
    monkeypatch.setattr(job, "clean", job.clean)  # load_clean replaces it; put the real one back afterwards
    with pytest.raises(job.JobError, match="clean.py differs from the pin: .*, the config pins 111111111111"):
        job.load_clean(fake, "1" * 64)
    assert not (tmp_path / "ran").exists()  # the file was hashed, not run
    module = job.load_clean(fake, job.digest(fake))
    assert (tmp_path / "ran").exists() and module.__file__ == str(fake) and job.clean is module


def test_a_cleaner_that_is_not_there_is_named(tmp_path):
    with pytest.raises(job.JobError, match="the cleaner .*nowhere.py is not there"):
        job.load_clean(tmp_path / "nowhere.py", PIN)


def test_a_config_with_another_pin_stops_the_job_before_anything_is_written(sample):
    tmp, shards, run = sample
    with pytest.raises(job.JobError, match="clean.py differs from the pin"):
        run(clean_sha256="0" * 64)
    assert not (tmp / "out").exists()


# --- the input set: any manifest that matches the run config ---------------------------------------------------------------
def test_a_manifest_of_any_size_is_accepted_when_the_config_says_so(sample):
    tmp, shards, run = sample
    one = tmp / "one.json"
    pin = write_manifest(one, shards[:1])  # one part, not the 86 of sample v0
    assert run(manifest=str(one), manifest_sha256=pin, expected_parts={"train": 1}) == 0
    summary = json.loads((tmp / "out/job/job_summary.json").read_text())
    assert summary["completed_parts"] == summary["expected_parts"] == 1 and summary["scope"] == "full manifest"


def test_a_manifest_that_is_not_the_pinned_file_stops_the_job(sample):
    tmp, shards, run = sample
    with pytest.raises(job.JobError, match="manifest.json has sha256 .*, the pin is 000000000000"):
        run(manifest_sha256="0" * 64)
    assert not (tmp / "out").exists()


def test_a_manifest_that_does_not_match_expected_parts_stops_the_job(sample):
    tmp, shards, run = sample
    with pytest.raises(job.JobError, match="expected_parts says"):
        run(expected_parts={"train": 48, "heldout": 38})
    assert not (tmp / "out").exists()


def test_only_must_name_parts_of_the_manifest(sample):
    tmp, shards, run = sample
    with pytest.raises(job.JobError, match="not in the manifest: train/en-dclm/part-00009.parquet"):
        run(only=["train/en-dclm/part-00009.parquet"])
    assert not (tmp / "out").exists()


def test_only_runs_those_parts_and_says_the_run_is_partial(sample):
    tmp, shards, run = sample
    assert run(only=["train/en-dclm/part-00001.parquet"]) == 0
    summary = json.loads((tmp / "out/job/job_summary.json").read_text())
    assert summary["scope"] == "partial (--only)" and summary["completed_parts"] == 1 and summary["expected_parts"] == 4
    assert json.loads((tmp / "out/job/cleaned_manifest.json").read_text())["complete_sample"] is False


@pytest.mark.parametrize("key", ["clean", "clean_sha256", "manifest", "manifest_sha256", "expected_parts", "batch_size", "unsupported_policy", "audit_samples"])
def test_a_config_without_a_required_key_names_it(sample, key):
    tmp, shards, run = sample
    with pytest.raises(job.JobError, match=f"the config lacks .*{key}"):
        run(drop=(key,))
    assert not (tmp / "out").exists()


def test_a_config_without_folders_needs_them_on_the_command_line(sample):
    tmp, shards, run = sample
    config = tmp / "c.json"
    config.write_text(json.dumps({k: v for k, v in run.config.items() if k not in ("input_root", "output_root")}))
    with pytest.raises(job.JobError, match="lacks input_root or output_root"):
        job.main(["--config", str(config)])


@pytest.mark.parametrize("extra, why", [(dict(optional_f2=True), "F2 is its own stage"),
                                        (dict(unsupported_policy="drop"), "unsupported pack policy must be explicit"),
                                        (dict(batch_size=0), "batch_size must be a positive integer"),
                                        (dict(batch_size="2"), "batch_size must be a positive integer"),
                                        (dict(batch_size=True), "batch_size must be a positive integer"),
                                        (dict(audit_samples=-1), "audit_samples must be a whole number"),
                                        (dict(audit_samples="5"), "audit_samples must be a whole number"),
                                        (dict(audit_samples=True), "audit_samples must be a whole number")])
def test_settings_the_job_does_not_accept_are_refused(sample, extra, why):
    tmp, shards, run = sample
    with pytest.raises(job.JobError, match=why):
        run(**extra)
    assert not (tmp / "out").exists()


# --- one part -----------------------------------------------------------------------------------------------------------
def part(tmp_path, pack="en-dclm", split="train"):
    shard = write_part(tmp_path / "input", split, pack, 0)
    path = tmp_path / "input" / shard["path"]
    rows = pq.read_table(path).to_pylist()
    return path, shard, rows


@pytest.mark.parametrize("platform, rss", [("darwin", 512 * 1024 * 1024), ("linux", 512 * 1024)])
def test_peak_memory_uses_platform_units(platform, rss, monkeypatch):
    monkeypatch.setattr(job, "resource", SimpleNamespace(RUSAGE_SELF=0, RUSAGE_CHILDREN=1, getrusage=lambda _: SimpleNamespace(ru_maxrss=rss)))
    monkeypatch.setattr(job.sys, "platform", platform)
    assert job.peak_rss_mib() == 512.0


def test_peak_memory_is_the_largest_process_the_job_or_a_worker(monkeypatch):
    usage = {0: 100 * 1024, 1: 300 * 1024}  # Linux units: KiB
    monkeypatch.setattr(job, "resource", SimpleNamespace(RUSAGE_SELF=0, RUSAGE_CHILDREN=1, getrusage=lambda who: SimpleNamespace(ru_maxrss=usage[who])))
    monkeypatch.setattr(job.sys, "platform", "linux")
    assert job.peak_rss_mib() == 300.0


def test_peak_memory_is_unavailable_without_resource(monkeypatch):
    monkeypatch.setattr(job, "resource", None)
    assert job.peak_rss_mib() is None


def test_counting_runs_actual_cleaner_with_identical_results():
    rows = [dict(doc_id="d", text=t, pack_id="en-dclm", lang_label="en", url="") for t in TEXTS]
    expected = [job.clean.clean(row) for row in rows]
    original_run, original_ids = job.clean._run, dict(job.clean._ID)
    counter = job.RuleCounter()
    with counter.instrument():
        assert [job.clean.clean(row) for row in rows] == expected
    assert job.clean._run is original_run and job.clean._ID == original_ids
    assert counter.counts["DA-A1-004"]["fix"] == 1
    assert sum(counter.counts["DA-F1-005"].values()) == 2  # drop short-circuits later rules


def test_streaming_output_and_rule_counts_match_cleaner(tmp_path):
    path, shard, rows = part(tmp_path)
    out = tmp_path / "out"
    result = job.process_part(path, shard, out, batch_size=1)
    expected = [(row["doc_id"], job.clean.clean(row)) for row in rows]
    written = pq.read_table(out / shard["path"]).to_pylist()
    assert [(row["doc_id"], row["text"]) for row in written] == [(d, value[1]) for d, value in expected if value[0] != "drop"]
    assert result["actions"] == {"keep": 1, "fix": 1, "drop": 1}
    assert result["rule_counts"]["DA-F1-005"]["not_reached"] == 1
    assert result["input_rows"] == result["output_rows"] + result["actions"]["drop"]
    with pytest.raises(job.JobError, match="overwrite"):
        job.process_part(path, shard, out, 1)


def test_unknown_pack_is_explicit_passthrough(tmp_path):
    path, shard, rows = part(tmp_path, "cadj-stackexchange")
    out = tmp_path / "out"
    result = job.process_part(path, shard, out, 2)
    assert result["status"] == "unsupported_passthrough"
    assert result["rule_counts"] == {} and result["actions"] == {"keep": 3}
    assert pq.read_table(out / shard["path"]).to_pylist() == rows


def test_heldout_and_train_outputs_are_separate(tmp_path):
    out = tmp_path / "out"
    for split in ("train", "heldout"):
        path, shard, _ = part(tmp_path, split=split)
        job.process_part(path, shard, out, 2)
    assert (out / "train/en-dclm/part-00000.parquet").is_file()
    assert (out / "heldout/en-dclm/part-00000.parquet").is_file()


def test_hash_resolution_handles_browser_rename_but_rejects_wrong_bytes(tmp_path):
    path, shard, _ = part(tmp_path)
    target = tmp_path / "organized/en-dclm/train/part-00000_part2.parquet"
    target.parent.mkdir(parents=True)
    path.rename(target)
    assert job.resolve_input(tmp_path / "organized", shard, {}) == target
    target.write_bytes(b"wrong data")
    with pytest.raises(job.JobError, match="checksum"):
        job.resolve_input(tmp_path / "organized", shard, {})


def test_errors_are_counted_and_partial_output_is_not_published(tmp_path, monkeypatch):
    path, shard, _ = part(tmp_path)

    def broken(doc):
        raise ValueError("synthetic private content that must not appear in reports")

    monkeypatch.setattr(job.clean, "_PIPELINES", {"english": (lambda: broken,)})
    # Replace the registered factory consistently so the actual clean() path raises.
    failed_factory = job.clean._PIPELINES["english"][0]
    monkeypatch.setattr(job.clean, "_RULE", {"DA-A1-004": failed_factory, "f1_rule.py": job.clean._shared_f1_rule})
    monkeypatch.setattr(job.clean, "_ID", {failed_factory: "DA-A1-004", job.clean._shared_f1_rule: "f1_rule.py"})
    out = tmp_path / "out"
    with pytest.raises(job.JobError, match="ValueError"):
        job.process_part(path, shard, out, 1)
    text = (out / "failure.json").read_text()
    assert "synthetic private content" not in text
    assert json.loads(text)["rule_counts"]["DA-A1-004"]["error"] == 1
    assert not (out / shard["path"]).exists()


def test_output_and_part_paths_are_bounded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert job.output_folder("out/job") == tmp_path / "out/job"
    for bad in ("out", "../elsewhere", "/tmp/elsewhere"):
        with pytest.raises(job.JobError, match="output"):
            job.output_folder(bad)
    with pytest.raises(job.JobError, match="unexpected part path"):
        job.safe_path("../train/escape.parquet")
    with pytest.raises(job.JobError, match="unexpected part path"):
        job.safe_path("val/en-dclm/part-00000.parquet")  # only train and heldout


def test_all_dropped_part_still_has_a_valid_parquet_schema(tmp_path):
    shard = write_part(tmp_path / "input", "train", "en-dclm", 0, texts=["Subscribe to our newsletter\n"] * 3)
    path = tmp_path / "input" / shard["path"]
    out = tmp_path / "out"
    result = job.process_part(path, shard, out, 1)
    table = pq.read_table(out / shard["path"])
    assert table.num_rows == result["output_rows"] == 0
    assert table.schema == pq.read_schema(path)
    assert result["actions"] == {"drop": 3}


def test_aggregate_includes_zero_rules_and_explicit_partial_manifest(tmp_path):
    path, shard, _ = part(tmp_path, "cadj-stackexchange")
    out = tmp_path / "out"
    report = job.process_part(path, shard, out, 2)
    summary = job.write_aggregate(out, [report], {"sample": "synthetic"}, 86)
    assert summary["unsupported_parts"] == [shard["path"]]
    assert json.loads((out / "cleaned_manifest.json").read_text())["complete_sample"] is False
    counts = list(csv.DictReader((out / "rule_counts.csv").open()))
    assert len(counts) == len(job.clean._RULE)
    assert all(row["invocations"] == "0" for row in counts)


def two_parts(tmp_path, audit_samples):
    """Parts 0 and 1 of one pack, cleaned with audit_samples; (output folder, their reports)."""
    out, reports = tmp_path / "out", []
    for n in (0, 1):
        shard = write_part(tmp_path / "input", "train", "en-dclm", n)
        reports.append(job.process_part(tmp_path / "input" / shard["path"], shard, out, 2, audit_samples))
    return out, reports


def fires(counter, rid, doc_ids, action="fix"):
    for doc_id in doc_ids:
        counter.note(rid, {"doc_id": doc_id, "text": "abcdef"}, action, "abc")


def test_the_documents_a_rule_keeps_do_not_depend_on_the_order_of_the_rows():
    ids = [f"d{n}" for n in range(200)]
    forward, backward = job.RuleCounter(5), job.RuleCounter(5)
    fires(forward, "R", ids)
    fires(backward, "R", ids[::-1])
    assert forward.samples["R"] == backward.samples["R"]
    assert [s[0] for s in forward.samples["R"]] == sorted(zlib.crc32(f"R\0{d}".encode()) for d in ids)[:5]  # the 5 lowest keys


def test_a_rule_keeps_at_most_audit_samples_documents_and_all_of_them_when_it_fired_less_often():
    counter = job.RuleCounter(3)
    fires(counter, "A", ["a1", "a2"])
    fires(counter, "B", [f"b{n}" for n in range(50)])
    assert len(counter.samples["A"]) == 2 and len(counter.samples["B"]) == 3


def test_different_rules_pick_different_documents():
    ids = [f"d{n}" for n in range(200)]
    counter = job.RuleCounter(5)
    fires(counter, "R1", ids)
    fires(counter, "R2", ids)
    assert {s[1] for s in counter.samples["R1"]} != {s[1] for s in counter.samples["R2"]}


def test_only_fixes_and_drops_are_remembered_and_a_drop_has_no_length_after():
    rows = [dict(doc_id=f"d{n}", text=text, pack_id="en-dclm", lang_label="en", url="") for n, text in enumerate(TEXTS)]
    counter = job.RuleCounter(5)
    with counter.instrument():
        for row in rows:
            job.clean.clean(row)
    assert [s[1:] for s in counter.samples["DA-A1-004"]] == [("d1", "fix", 19, 18)]
    assert [s[1:] for s in counter.samples["DA-C1-006"]] == [("d2", "drop", 28, None)]
    assert all(s[1] != "d0" for picked in counter.samples.values() for s in picked)  # d0 is a keep


def test_with_audit_samples_zero_the_rules_are_counted_but_nothing_is_remembered():
    rows = [dict(doc_id=f"d{n}", text=text, pack_id="en-dclm", lang_label="en", url="") for n, text in enumerate(TEXTS)]
    counter = job.RuleCounter()
    with counter.instrument():
        for row in rows:
            job.clean.clean(row)
    assert counter.counts["DA-A1-004"]["fix"] == 1 and not counter.samples


def test_the_audit_file_of_a_part_holds_ids_and_lengths_but_no_text(tmp_path):
    path, shard, rows = part(tmp_path)
    out = tmp_path / "out"
    job.process_part(path, shard, out, 2, audit_samples=5)
    written = (out / "audit" / (shard["path"] + ".json")).read_text(encoding="utf-8")
    data = json.loads(written)
    assert data["part"] == shard["path"] and data["pack_id"] == "en-dclm" and data["samples_per_rule"] == 5
    assert set(data["rules"]) == {"DA-A1-004", "DA-C1-006"}
    assert all(set(s) == {"key", "doc_id", "action", "chars_before", "chars_after"} for docs in data["rules"].values() for s in docs)
    assert not any(text.strip() in written for text in TEXTS)


def test_rule_examples_hold_the_lowest_keys_over_all_parts_of_a_pack(tmp_path):
    out, reports = two_parts(tmp_path, audit_samples=1)
    job.write_aggregate(out, reports, {"sample": "synthetic"}, 86, audit_samples=1)
    rows = list(csv.DictReader((out / "rule_examples.csv").open()))
    assert [row["pack_id"] for row in rows] == ["en-dclm"] * len(job.applicable_rules("en-dclm"))
    assert [row["rule_id"] for row in rows] == job.applicable_rules("en-dclm")  # the cleaner's order, one row per rule
    fixed = next(row for row in rows if row["rule_id"] == "DA-A1-004")
    # the fix happened once per part: the example is the one with the lower key, the totals count both
    key = lambda part: zlib.crc32(f"DA-A1-004\0train-en-dclm-{part}-d1".encode())
    lower = min((0, 1), key=key)
    assert fixed["doc_id"] == f"train-en-dclm-{lower}-d1" and fixed["part"] == f"train/en-dclm/part-0000{lower}.parquet"
    assert (fixed["rank"], fixed["split"], fixed["action"], fixed["pack_fixes"]) == ("1", "train", "fix", "2")
    never = next(row for row in rows if row["pack_fixes"] == "0" and row["pack_drops"] == "0")  # fired in no part
    assert never["doc_id"] == never["rank"] == ""


def test_rule_examples_keep_at_most_audit_samples_per_rule(tmp_path):
    out, reports = two_parts(tmp_path, audit_samples=2)
    job.write_aggregate(out, reports, {"sample": "synthetic"}, 86, audit_samples=2)
    rows = [row for row in csv.DictReader((out / "rule_examples.csv").open()) if row["rule_id"] == "DA-A1-004"]
    assert [row["rank"] for row in rows] == ["1", "2"] and len({row["doc_id"] for row in rows}) == 2
    assert {row["pack_fixes"] for row in rows} == {"2"}


def test_without_audit_samples_there_is_no_audit_folder_and_no_examples_file(tmp_path):
    out, reports = two_parts(tmp_path, audit_samples=0)
    job.write_aggregate(out, reports, {"sample": "synthetic"}, 86)
    assert not (out / "audit").exists() and not (out / "rule_examples.csv").exists()


def test_audit_sampling_preserves_cleaned_parquet_and_rule_counts(tmp_path):
    plain, plain_reports = two_parts(tmp_path / 'plain', audit_samples=0)
    audit, audit_reports = two_parts(tmp_path / 'audit', audit_samples=5)
    for before, after in zip(plain_reports, audit_reports):
        part = before['part']
        assert (plain / part).read_bytes() == (audit / part).read_bytes()
        assert before['actions'] == after['actions']
        assert before['rule_counts'] == after['rule_counts']


def test_a_missing_audit_file_stops_the_aggregate_naming_the_part(tmp_path):
    out, reports = two_parts(tmp_path, audit_samples=1)
    (out / "audit/train/en-dclm/part-00001.parquet.json").unlink()
    with pytest.raises(job.JobError, match="audit file of train/en-dclm/part-00001.parquet is missing"):
        job.write_aggregate(out, reports, {"sample": "synthetic"}, 86, audit_samples=1)


def test_a_finished_part_without_its_audit_file_is_named_when_resuming(sample, monkeypatch):
    tmp, shards, run = sample
    interrupted(monkeypatch, run)
    out = tmp / "out/job"
    (out / "audit/train/en-dclm/part-00000.parquet.json").unlink()
    with pytest.raises(job.JobError, match=r"train/en-dclm/part-00000.parquet: its audit file audit/train/en-dclm/part-00000.parquet.json is missing"):
        run(resume=True)


def test_a_job_with_audit_samples_writes_one_audit_file_per_part_and_the_examples(sample):
    tmp, shards, run = sample
    assert run() == 0
    out = tmp / "out/job"
    assert all((out / "audit" / (s["path"] + ".json")).is_file() for s in shards)
    assert (out / "rule_examples.csv").is_file()
    assert json.loads((out / "job_summary.json").read_text())["audit_samples"] == 5


# --- resume --------------------------------------------------------------------------------------------------------------
def test_a_fresh_job_writes_its_state_and_one_attempt(sample):
    tmp, shards, run = sample
    assert run() == 0
    out = tmp / "out/job"
    state = json.loads((out / "job_state.json").read_text())
    assert [a["status"] for a in state["attempts"]] == ["complete"] and state["attempts"][0]["resumed"] is False
    assert sorted(state["fingerprint"]) == ["audit_samples", "clean_sha256", "manifest_sha256", "runner_sha256", "selected_parts"]
    summary = json.loads((out / "job_summary.json").read_text())
    assert summary["resumed_parts"] == 0 and summary["completed_parts"] == 4 and summary["attempts"] == state["attempts"]


def test_an_interrupted_job_is_not_continued_without_resume_and_nothing_changes(sample, monkeypatch):
    tmp, shards, run = sample
    interrupted(monkeypatch, run)
    out = tmp / "out/job"
    before = sorted((p.relative_to(out).as_posix(), p.stat().st_mtime_ns) for p in out.rglob("*") if p.is_file())
    with pytest.raises(job.JobError, match='"resume": true'):
        run()
    assert before == sorted((p.relative_to(out).as_posix(), p.stat().st_mtime_ns) for p in out.rglob("*") if p.is_file())


def test_resume_finishes_the_job_with_the_output_of_a_job_that_was_never_interrupted(sample, monkeypatch):
    tmp, shards, run = sample
    run(out="out/fresh")
    interrupted(monkeypatch, run)
    out = tmp / "out/job"
    assert (out / "train/en-dclm/part-00000.parquet").is_file() and not (out / "train/en-dclm/part-00001.parquet").exists()
    assert run(resume=True) == 0
    assert outputs(out) == outputs(tmp / "out/fresh")
    summary = json.loads((out / "job_summary.json").read_text())
    assert summary["resumed_parts"] == 1 and summary["completed_parts"] == 4
    statuses = [a["status"] for a in summary["attempts"]]
    assert statuses == ["failed", "complete"] and summary["attempts"][1]["resumed"] and summary["attempts"][1]["kept_parts"] == 1
    assert "injected failure" in summary["attempts"][0]["error"]
    assert not (out / "failure.json").exists()


def test_the_failure_record_of_an_earlier_attempt_is_kept_in_its_attempt(sample, monkeypatch):
    tmp, shards, run = sample
    out = tmp / "out/job"
    out.mkdir(parents=True)
    interrupted(monkeypatch, run)
    (out / "failure.json").write_text(json.dumps({"part": "x", "doc_id": "d", "error_type": "ValueError"}))  # as process_part writes it
    run(resume=True)
    state = json.loads((out / "job_state.json").read_text())
    assert state["attempts"][0]["failure"] == {"part": "x", "doc_id": "d", "error_type": "ValueError"}
    assert not (out / "failure.json").exists()


def test_a_killed_attempt_is_recorded_as_interrupted(sample, monkeypatch):
    tmp, shards, run = sample
    interrupted(monkeypatch, run)
    out = tmp / "out/job"
    state = json.loads((out / "job_state.json").read_text())
    state["attempts"][0].update(status="running")  # a process that was killed never wrote how it ended
    (out / "job_state.json").write_text(json.dumps(state))
    run(resume=True)
    assert [a["status"] for a in json.loads((out / "job_state.json").read_text())["attempts"]] == ["interrupted", "complete"]


def test_a_part_without_its_report_and_a_tmp_file_are_redone(sample, monkeypatch):
    tmp, shards, run = sample
    run(out="out/fresh")
    interrupted(monkeypatch, run, part="train/cadj-commits/part-00000.parquet")  # the first three parts are finished
    out = tmp / "out/job"
    (out / "reports/train/en-dclm/part-00001.parquet.json").unlink()  # published, but killed before its report
    (out / "heldout/en-dclm/part-00000.parquet.tmp").write_bytes(b"half a part")
    run(resume=True)
    assert not (out / "heldout/en-dclm/part-00000.parquet.tmp").exists()
    assert outputs(out) == outputs(tmp / "out/fresh")
    assert json.loads((out / "job_summary.json").read_text())["resumed_parts"] == 2


def test_a_finished_part_that_does_not_verify_stops_the_job_naming_the_part_and_the_files_to_delete(sample, monkeypatch):
    tmp, shards, run = sample
    run(out="out/fresh")
    interrupted(monkeypatch, run, part="train/cadj-commits/part-00000.parquet")
    out = tmp / "out/job"
    bad = out / "train/en-dclm/part-00001.parquet"
    bad.write_bytes(bad.read_bytes() + b"x")
    orphan = out / "heldout/en-dclm/part-00000.parquet"
    (out / "reports/heldout/en-dclm/part-00000.parquet.json").unlink()  # would be redone, but only after every check passes
    with pytest.raises(job.JobError) as stop:
        run(resume=True)
    message = str(stop.value)
    assert "train/en-dclm/part-00001.parquet" in message and "nothing was changed" in message
    assert "out/job/train/en-dclm/part-00001.parquet and out/job/reports/train/en-dclm/part-00001.parquet.json" in message
    assert orphan.exists()  # not deleted: the job stopped before changing anything
    # the two files it names are deleted, and the next run goes on from there
    bad.unlink()
    (out / "reports/train/en-dclm/part-00001.parquet.json").unlink()
    assert run(resume=True) == 0
    assert outputs(out) == outputs(tmp / "out/fresh")


@pytest.mark.parametrize("damage, why", [
    (lambda r: r.update(input_sha256="1" * 64), "input_sha256"),
    (lambda r: r.update(output_rows=r["output_rows"] + 1), "add up"),
    (lambda r: r.update(status="unsupported_passthrough"), "status"),
    (lambda r: r.update(errors=1), "errors"),
])
def test_a_report_that_disagrees_with_the_manifest_or_the_part_is_named(sample, monkeypatch, damage, why):
    tmp, shards, run = sample
    interrupted(monkeypatch, run)
    report_path = tmp / "out/job/reports/train/en-dclm/part-00000.parquet.json"
    report = json.loads(report_path.read_text())
    damage(report)
    report_path.write_text(json.dumps(report))
    with pytest.raises(job.JobError, match=f"train/en-dclm/part-00000.parquet: .*({why})"):
        run(resume=True)


def test_a_part_with_other_rows_than_its_report_is_named(sample, monkeypatch):
    tmp, shards, run = sample
    interrupted(monkeypatch, run)
    out = tmp / "out/job"
    part_file = out / "train/en-dclm/part-00000.parquet"
    pq.write_table(pq.read_table(part_file).slice(0, 1), part_file)  # a valid Parquet file, but not the part the report describes
    with pytest.raises(job.JobError, match="train/en-dclm/part-00000.parquet: the part has 1 rows, its report says 2"):
        run(resume=True)


def test_a_report_without_its_part_is_named(sample, monkeypatch):
    tmp, shards, run = sample
    interrupted(monkeypatch, run)
    (tmp / "out/job/train/en-dclm/part-00000.parquet").unlink()
    with pytest.raises(job.JobError, match="train/en-dclm/part-00000.parquet: a report without its part"):
        run(resume=True)


@pytest.mark.parametrize("key", ["clean_sha256", "runner_sha256", "manifest_sha256", "selected_parts", "audit_samples"])
def test_a_job_started_with_something_else_is_not_resumed(sample, monkeypatch, key):
    tmp, shards, run = sample
    interrupted(monkeypatch, run)
    state_path = tmp / "out/job/job_state.json"
    state = json.loads(state_path.read_text())
    state["fingerprint"][key] = "1" * 64 if key != "selected_parts" else ["train/en-dclm/part-00000.parquet"]
    state_path.write_text(json.dumps(state))
    with pytest.raises(job.JobError, match=f"cannot resume: the job was started with another {key}"):
        run(resume=True)


def test_a_different_part_selection_is_not_resumed(sample, monkeypatch):
    tmp, shards, run = sample
    interrupted(monkeypatch, run)
    with pytest.raises(job.JobError, match="another selected_parts"):
        run(resume=True, only=["train/en-dclm/part-00000.parquet"])


def test_a_finished_job_is_never_resumed_or_overwritten(sample):
    tmp, shards, run = sample
    run()
    before = (tmp / "out/job/job_summary.json").read_bytes()
    for resume in (False, True):
        with pytest.raises(job.JobError, match="finished job"):
            run(resume=resume)
    assert (tmp / "out/job/job_summary.json").read_bytes() == before


def test_a_folder_that_is_not_a_job_of_this_runner_is_not_resumed(sample):
    tmp, shards, run = sample
    (tmp / "out/job").mkdir(parents=True)
    (tmp / "out/job/something.txt").write_text("x")
    for resume in (False, True):
        with pytest.raises(job.JobError, match="not an interrupted job"):
            run(resume=resume)


def test_resume_with_no_folder_yet_is_a_fresh_job(sample):
    tmp, shards, run = sample
    assert run(resume=True) == 0
    state = json.loads((tmp / "out/job/job_state.json").read_text())
    assert state["attempts"][0]["resumed"] is False


def test_resume_must_be_true_or_false(sample):
    tmp, shards, run = sample
    with pytest.raises(job.JobError, match="resume must be true or false"):
        run(resume="yes")
    assert not (tmp / "out/job").exists()


def test_resume_skips_hashing_the_inputs_of_finished_parts(sample, monkeypatch):
    tmp, shards, run = sample
    interrupted(monkeypatch, run)
    asked = []
    real = job.resolve_input
    monkeypatch.setattr(job, "resolve_input", lambda root, shard, hashes: asked.append(shard["path"]) or real(root, shard, hashes))
    run(resume=True)
    assert asked == ["train/en-dclm/part-00001.parquet", "heldout/en-dclm/part-00000.parquet", "train/cadj-commits/part-00000.parquet"]


def test_the_rule_counts_of_a_resumed_job_are_the_sum_of_every_part(sample, monkeypatch):
    tmp, shards, run = sample
    interrupted(monkeypatch, run)
    run(resume=True)
    rows = {r["rule_id"]: r for r in csv.DictReader((tmp / "out/job/rule_counts.csv").open())}
    reports = [json.loads(p.read_text()) for p in sorted((tmp / "out/job/reports").rglob("*.json"))]
    for rid, row in rows.items():
        for kind in ("keep", "fix", "drop", "error"):
            assert int(row[kind]) == sum(r["rule_counts"].get(rid, {}).get(kind, 0) for r in reports)


# --- workers: parts cleaned by several processes at once --------------------------------------------------------------------
def summary_of(folder):
    """job_summary.json without what legitimately differs between two runs of the same job (time, attempts, workers)."""
    data = json.loads((folder / "job_summary.json").read_text())
    for key in ("wall_seconds", "peak_rss_mib", "attempts", "workers", "config_sha256", "resumed_parts"):
        data.pop(key)
    for report in data["parts"]:
        report.pop("seconds")
    return data


def same_output(a, b):
    assert outputs(a) == outputs(b)
    assert (a / "rule_examples.csv").read_text() == (b / "rule_examples.csv").read_text()
    assert summary_of(a) == summary_of(b)


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "2", None])
def test_workers_must_be_a_whole_number_of_one_or_more(sample, bad):
    tmp, shards, run = sample
    with pytest.raises(job.JobError, match="workers must be a whole number, 1 or more"):
        run(workers=bad)
    assert not (tmp / "out").exists()


def test_the_default_is_one_worker_in_this_process_and_needs_no_pool(sample, monkeypatch):
    tmp, shards, run = sample
    monkeypatch.setattr(job, "clean_in_pool", lambda *a, **k: pytest.fail("a pool was started"))
    assert run() == 0
    assert run(out="out/one", workers=1) == 0
    assert json.loads((tmp / "out/one/job_summary.json").read_text())["workers"] == 1


def test_several_workers_make_the_output_of_one(sample):
    tmp, shards, run = sample
    run(out="out/one")
    assert run(out="out/three", workers=3) == 0
    same_output(tmp / "out/three", tmp / "out/one")
    summary = json.loads((tmp / "out/three/job_summary.json").read_text())
    assert summary["workers"] == 3
    assert [p["part"] for p in summary["parts"]] == [s["path"] for s in shards]  # manifest order, not finishing order


def test_more_workers_than_parts_start_only_as_many_as_there_are_parts(sample):
    tmp, shards, run = sample
    run(out="out/one")
    assert run(out="out/many", workers=16) == 0
    same_output(tmp / "out/many", tmp / "out/one")
    assert json.loads((tmp / "out/many/job_summary.json").read_text())["workers"] == len(shards)


def test_workers_started_by_spawn_load_the_pinned_cleaner_and_make_the_same_output(sample, monkeypatch):
    tmp, shards, run = sample  # nothing is inherited from this process: each worker loads and checks the cleaner itself
    run(out="out/one")
    assert job.start_method() == "spawn"  # the default
    assert run(out="out/spawned", workers=2) == 0
    same_output(tmp / "out/spawned", tmp / "out/one")


def test_the_biggest_parts_go_first(tmp_path, monkeypatch):
    shards = [dict(path=f"train/p/part-{n}.parquet", rows=rows) for n, rows in enumerate([5, 90, 7, 90, 40])]
    submitted = []

    class Pool:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def submit(self, fn, task):
            submitted.append(task[1]["path"])
            future = job.Future()
            future.set_result({"part": task[1]["path"]})
            return future

    monkeypatch.setattr(job, "ProcessPoolExecutor", Pool)
    monkeypatch.setattr(job, "clean", SimpleNamespace(__file__="clean.py"))
    done = job.clean_in_pool(shards, {s["path"]: s["path"] for s in shards}, tmp_path, 1, 0, 2, "pin")
    assert submitted == ["train/p/part-1.parquet", "train/p/part-3.parquet", "train/p/part-4.parquet",
                         "train/p/part-2.parquet", "train/p/part-0.parquet"]  # by rows, equal sizes by path
    assert sorted(done) == sorted(s["path"] for s in shards)


def test_a_failure_with_workers_stops_the_job_and_a_resume_with_another_number_finishes_it(sample, monkeypatch):
    tmp, shards, run = sample
    run(out="out/fresh")
    with monkeypatch.context() as m:
        m.setattr(job, "start_method", lambda: "fork")  # a forked worker inherits the patch below; a spawned one would not
        fail_on(m, "train/en-dclm/part-00001.parquet")
        with pytest.raises(job.JobError, match="injected failure"):
            run(workers=2)
    out = tmp / "out/job"
    assert not (out / "job_summary.json").exists()
    assert not (out / "train/en-dclm/part-00001.parquet").exists()  # the failed part was not published
    state = json.loads((out / "job_state.json").read_text())
    assert [a["status"] for a in state["attempts"]] == ["failed"] and "injected failure" in state["attempts"][0]["error"]
    assert run(resume=True, workers=1) == 0  # not part of what a resume checks
    same_output(out, tmp / "out/fresh")
    assert json.loads((out / "job_summary.json").read_text())["completed_parts"] == 4


def test_a_cleaner_error_in_workers_leaves_the_record_of_the_failure_the_job_reports(sample, monkeypatch):
    tmp, shards, run = sample

    def broken(doc):
        raise ValueError("synthetic private content that must not appear in reports")

    broken_rule = lambda: broken
    monkeypatch.setattr(job.clean, "_RULE", {"DA-A1-004": broken_rule, "f1_rule.py": job.clean._shared_f1_rule})
    monkeypatch.setattr(job.clean, "_ID", {broken_rule: "DA-A1-004", job.clean._shared_f1_rule: "f1_rule.py"})
    monkeypatch.setattr(job.clean, "_PIPELINES", {"english": (broken_rule,)})
    monkeypatch.setattr(job, "start_method", lambda: "fork")  # the workers inherit the patched cleaner...
    monkeypatch.setattr(job, "load_clean", lambda path, pin: job.clean)  # ...and neither they nor the job load the real one over it
    with pytest.raises(job.JobError, match="cleaner error: (?P<part>\\S+) doc_id=.* type=ValueError") as caught:
        run(workers=3)  # all three en-dclm parts fail, in different workers
    named = caught.value.args[0].split()[2]
    out = tmp / "out/job"
    failure = (out / "failure.json").read_text()
    assert "synthetic private content" not in failure
    assert json.loads(failure)["part"] == named and json.loads(failure)["error_type"] == "ValueError"  # the one the job reports
    assert json.loads(failure)["rule_counts"]["DA-A1-004"]["error"] == 1
    assert sorted(p.name for p in out.glob("failure*")) == ["failure.json"]  # no temporary files


def test_a_worker_that_dies_is_named_and_the_job_can_be_resumed(sample, monkeypatch):
    tmp, shards, run = sample
    run(out="out/fresh")
    parent = job.os.getpid()
    real = job.process_part

    def dies(source, shard, output, batch_size, **more):
        if job.os.getpid() != parent and shard["path"] == "train/en-dclm/part-00001.parquet":
            job.os._exit(1)  # as if the kernel had killed it
        return real(source, shard, output, batch_size, **more)

    with monkeypatch.context() as m:
        m.setattr(job, "start_method", lambda: "fork")
        m.setattr(job, "process_part", dies)
        with pytest.raises(job.JobError, match='a worker process died .*"resume": true'):
            run(workers=2)
    state = json.loads((tmp / "out/job/job_state.json").read_text())
    assert [a["status"] for a in state["attempts"]] == ["failed"]
    assert run(resume=True, workers=2) == 0
    same_output(tmp / "out/job", tmp / "out/fresh")
