"""Tests for stage_args.py: the command and generated config the runner gives each stage script. Made-up settings files and
a made-up repository folder; nothing is run.

  python -m pytest teams/01-data-a/pipeline/tests/test_stage_args.py
"""
import json

import pytest

import stage_args as sa
from conftest import made_up_manifest

OVERLAP = {"_comment": "settings only", "inputs": "old/clean", "splits": ["train", "heldout"], "out": "old/overlap", "floor": 0.5, "k": 5,
           "expected_packs": ["code-go"]}
DEDUP = {"results": "old/overlap", "inputs": "old/clean", "out": "old/dedup", "cross_pack": True, "pack_order": ["code-go", "en-dclm"],
         "licence_usable": {}, "default_licence_usable": True, "gold_dirs": []}


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "repo" / "out" / "run1").mkdir(parents=True)
    return tmp_path / "repo"


@pytest.fixture
def folders(repo):
    return {s: repo / "out" / "run1" / s for s in ("clean", "overlap", "dedup")}


def clean_spec(repo, **over):
    """A clean stage entry with its input set described: a made-up manifest in the repository and its pin."""
    (repo / "manifest.json").write_text(made_up_manifest({"train": 1, "heldout": 1}), encoding="utf-8")
    spec = {"settings": "job.json", "input": "inputs/sample", "manifest": "manifest.json", "manifest_sha256": sa.sha256(repo / "manifest.json"),
            "expected_parts": {"train": 1, "heldout": 1}, "sample": "made up"}
    return {**spec, **over}


def settings(repo, name, data):
    p = repo / f"{name}.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_clean_gets_a_generated_config_with_the_input_and_its_description(repo, folders):
    s = settings(repo, "job", {"clean_sha256": "c" * 64, "batch_size": 128})
    cfg = repo / "out/run1/cfg"
    spec = clean_spec(repo)
    r = sa.build("clean", spec, folders, cfg, repo)
    made = json.loads((cfg / "clean.json").read_text(encoding="utf-8"))
    assert (made["input_root"], made["output_root"], made["manifest"]) == ("inputs/sample", "out/run1/clean", "manifest.json")
    assert (made["manifest_sha256"], made["expected_parts"], made["sample"]) == (spec["manifest_sha256"], {"train": 1, "heldout": 1}, "made up")
    assert made["batch_size"] == 128 and made["clean_sha256"] == "c" * 64  # the settings are kept
    assert r["command"] == [sa.DEFAULT_SCRIPT["clean"], "--config", (cfg / "clean.json").as_posix()]
    assert r["settings_sha256"] == sa.sha256(s) and r["config_sha256"] == sa.sha256(cfg / "clean.json")


def test_the_default_clean_script_is_the_spec_v1_1_runner():
    assert sa.DEFAULT_SCRIPT["clean"] == "teams/01-data-a/pipeline/clean_job.py"


def test_resume_goes_into_the_generated_clean_config_only_when_it_is_true(repo, folders):
    settings(repo, "job", {"clean_sha256": "c" * 64})
    for spec, written in ((clean_spec(repo, resume=True), True), (clean_spec(repo, resume=False), False), (clean_spec(repo), False)):
        sa.build("clean", spec, folders, repo / "cfg", repo)
        made = json.loads((repo / "cfg" / "clean.json").read_text(encoding="utf-8"))
        assert ("resume" in made) is written and (made.get("resume") is True) is written
    assert sa.generated_values("clean", folders, repo, clean_spec(repo, resume=True))["resume"] is True


def test_workers_of_the_run_config_replace_the_one_in_the_settings(repo, folders):
    settings(repo, "job", {"workers": 4, "batch_size": 128})
    for spec, workers in ((clean_spec(repo, workers=2), 2), (clean_spec(repo), 4)):
        sa.build("clean", spec, folders, repo / "cfg", repo)
        made = json.loads((repo / "cfg" / "clean.json").read_text(encoding="utf-8"))
        assert (made["workers"], made["batch_size"]) == (workers, 128)  # the other settings are kept
    settings(repo, "job", {})
    sa.build("clean", clean_spec(repo), folders, repo / "cfg", repo)
    assert "workers" not in json.loads((repo / "cfg" / "clean.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("value", ["yes", 1, None, "true"])
def test_resume_must_be_true_or_false(repo, folders, value):
    settings(repo, "job", {})
    with pytest.raises(sa.ConfigError, match="stages.clean.resume is .*, expected true or false"):
        sa.build("clean", clean_spec(repo, resume=value), folders, repo / "cfg", repo)


@pytest.mark.parametrize("stage", ["overlap", "dedup"])
def test_only_the_clean_job_can_be_resumed(repo, folders, stage):
    settings(repo, stage, OVERLAP)
    with pytest.raises(sa.ConfigError, match=f"stages.{stage}.resume: only the clean job can be resumed"):
        sa.build(stage, {"settings": f"{stage}.json", "resume": True}, folders, repo / "cfg", repo)


@pytest.mark.parametrize("missing", ["input", "manifest_sha256", "expected_parts"])
def test_clean_needs_its_input_and_the_description_of_it(repo, folders, missing):
    settings(repo, "job", {})
    spec = clean_spec(repo)
    del spec[missing]
    with pytest.raises(sa.ConfigError, match=f"stages.clean.{missing} .* is missing"):
        sa.build("clean", spec, folders, repo / "cfg", repo)


def test_the_manifest_defaults_to_the_one_in_the_input_folder(repo, folders):
    settings(repo, "job", {})
    spec = clean_spec(repo)
    del spec["manifest"]
    (repo / "inputs" / "sample").mkdir(parents=True)
    (repo / "inputs" / "sample" / "sample_manifest.json").write_bytes((repo / "manifest.json").read_bytes())
    sa.build("clean", spec, folders, repo / "cfg", repo)
    assert json.loads((repo / "cfg" / "clean.json").read_text(encoding="utf-8"))["manifest"] == "inputs/sample/sample_manifest.json"


@pytest.mark.parametrize("write", [True, False])  # a run and a plan
def test_a_missing_or_changed_manifest_stops_a_run_and_a_plan(repo, folders, write):
    settings(repo, "job", {})
    spec = clean_spec(repo, manifest="nowhere.json")
    with pytest.raises(sa.ConfigError, match="sample manifest .*nowhere.json is not there"):
        sa.build("clean", spec, folders, repo / "cfg", repo, write=write)
    (repo / "manifest.json").write_text('{"shards": [1]}', encoding="utf-8")  # changed after it was pinned
    with pytest.raises(sa.ConfigError, match="stages.clean: .*manifest.json has sha256 .*, the pin is"):
        sa.build("clean", {**spec, "manifest": "manifest.json"}, folders, repo / "cfg", repo, write=write)


def test_a_manifest_that_does_not_match_expected_parts_stops_a_plan_too(repo, folders):
    settings(repo, "job", {})
    spec = clean_spec(repo, expected_parts={"train": 2, "heldout": 1})  # the manifest has one train part
    with pytest.raises(sa.ConfigError, match=r"stages.clean: the manifest has parts \{'train': 1, 'heldout': 1\}, stages.clean.expected_parts says"):
        sa.build("clean", spec, folders, repo / "cfg", repo, write=False)


def test_a_missing_default_manifest_says_where_it_looked(repo, folders):
    settings(repo, "job", {})
    spec = clean_spec(repo)
    del spec["manifest"]
    with pytest.raises(sa.ConfigError, match="not there .without stages.clean.manifest it is sample_manifest.json in the input folder"):
        sa.build("clean", spec, folders, repo / "cfg", repo, write=False)


def test_only_adds_one_flag_per_part_to_clean_and_clears_overlaps_expected_packs(repo, folders):
    settings(repo, "job", {})
    settings(repo, "overlap", OVERLAP)
    clean = clean_spec(repo)
    parts = ["train/code-go/part-00000.parquet", "heldout/code-go/part-00000.parquet"]
    command = sa.build("clean", clean, folders, repo / "cfg", repo, only=parts)["command"]
    assert command[-4:] == ["--only", parts[0], "--only", parts[1]]
    sa.build("overlap", {"settings": "overlap.json"}, folders, repo / "cfg", repo, only=parts)
    assert json.loads((repo / "cfg" / "overlap.json").read_text(encoding="utf-8"))["expected_packs"] == []
    sa.build("overlap", {"settings": "overlap.json"}, folders, repo / "cfg2", repo)
    assert json.loads((repo / "cfg2" / "overlap.json").read_text(encoding="utf-8"))["expected_packs"] == ["code-go"]


def test_overlap_config_gets_the_paths_and_keeps_every_setting(repo, folders):
    settings(repo, "overlap", OVERLAP)
    cfg = repo / "out/run1/cfg"
    r = sa.build("overlap", {"settings": "overlap.json"}, folders, cfg, repo)
    made = json.loads((cfg / "overlap.json").read_text(encoding="utf-8"))
    assert made["inputs"] == "out/run1/clean" and made["out"] == "out/run1/overlap"
    assert {k: v for k, v in made.items() if k not in ("inputs", "out")} == {k: v for k, v in OVERLAP.items() if k not in ("inputs", "out")}
    assert r["command"] == [sa.DEFAULT_SCRIPT["overlap"], "--config", (cfg / "overlap.json").as_posix()]
    assert r["config_sha256"] == sa.sha256(cfg / "overlap.json") and r["config"] == (cfg / "overlap.json").as_posix()


def test_dedup_config_names_the_overlap_folder_as_results(repo, folders):
    settings(repo, "dedup", {**DEDUP, "h3": {"matches": "old/h3_matches.csv", "remove": True}})
    r = sa.build("dedup", {"settings": "dedup.json"}, folders, repo / "cfg", repo)
    made = json.loads((repo / "cfg" / "dedup.json").read_text(encoding="utf-8"))
    assert (made["results"], made["inputs"], made["out"]) == ("out/run1/overlap", "out/run1/clean", "out/run1/dedup")
    assert made["pack_order"] == DEDUP["pack_order"] and made["gold_dirs"] == [] and made["h3"] is None
    assert r["command"][1] == "--config"


def test_h3_reads_cleaned_parts_and_dedup_uses_its_matches_report_only(repo, folders):
    folders["h3"] = repo / "out/run1/h3"
    settings(repo, "h3", {"packs": {"ind-hi-fw2": "hi", "en-fineweb-edu": "en"},
                           "pairs": [["hi", "en"]], "model_path": "../models/LaBSE"})
    settings(repo, "dedup", DEDUP)
    sa.build("h3", {"settings": "h3.json"}, folders, repo / "out/run1/cfg", repo)
    sa.build("dedup", {"settings": "dedup.json"}, folders, repo / "out/run1/cfg", repo)
    h3 = json.loads((repo / "out/run1/cfg/h3.json").read_text())
    dedup = json.loads((repo / "out/run1/cfg/dedup.json").read_text())
    assert (h3["inputs"], h3["out"], h3["cache"]) == (
        "out/run1/clean", "out/run1/h3", "out/run1/h3_cache")
    assert dedup["h3"] == {"matches": "out/run1/h3/h3_matches.csv",
                           "remove": False, "parallel_packs": []}


def test_the_settings_file_is_not_touched_and_the_result_repeats(repo, folders):
    s = settings(repo, "dedup", DEDUP)
    before = s.read_bytes()
    a = sa.build("dedup", {"settings": "dedup.json"}, folders, repo / "cfg", repo)
    b = sa.build("dedup", {"settings": "dedup.json"}, folders, repo / "cfg", repo)
    assert s.read_bytes() == before and a == b


def test_generated_config_has_no_absolute_path(repo, folders):
    settings(repo, "overlap", OVERLAP)
    sa.build("overlap", {"settings": "overlap.json"}, folders, repo / "cfg", repo)
    text = (repo / "cfg" / "overlap.json").read_text(encoding="utf-8")
    assert str(repo) not in text and "\\" not in text and text.endswith("}\n")


def test_a_pinned_settings_file_that_changed_is_refused(repo, folders):
    s = settings(repo, "overlap", OVERLAP)
    spec = {"settings": "overlap.json", "settings_sha256": sa.sha256(s)}
    sa.build("overlap", spec, folders, repo / "cfg", repo)  # the right pin is fine
    s.write_text(json.dumps({**OVERLAP, "k": 6}), encoding="utf-8")
    with pytest.raises(sa.ConfigError, match="pins"):
        sa.build("overlap", spec, folders, repo / "cfg", repo)


def test_a_missing_or_absent_settings_file_is_refused(repo, folders):
    with pytest.raises(sa.ConfigError, match="settings .* not found"):
        sa.build("overlap", {"settings": "nope.json"}, folders, repo / "cfg", repo)
    with pytest.raises(sa.ConfigError, match="settings .* is missing"):
        sa.build("overlap", {}, folders, repo / "cfg", repo)


@pytest.mark.parametrize("stage", ["clean", "overlap", "dedup"])
def test_an_output_outside_out_is_refused(repo, folders, stage, tmp_path):
    settings(repo, "s", {})
    for bad in (repo / "elsewhere" / stage, repo / "out"):
        with pytest.raises(sa.ConfigError, match="named subfolder"):
            sa.build(stage, {"settings": "s.json"}, {**folders, stage: bad}, repo / "cfg", repo)


def test_a_folder_outside_the_repo_is_refused_for_a_generated_config(repo, folders, tmp_path):
    settings(repo, "overlap", OVERLAP)
    with pytest.raises(sa.ConfigError, match="outside the repository"):
        sa.build("overlap", {"settings": "overlap.json"}, {**folders, "clean": tmp_path / "elsewhere"}, repo / "cfg", repo)


def test_a_stage_without_this_style_asks_for_a_command(repo, folders):
    with pytest.raises(sa.ConfigError, match="explicit stages.apply.command"):
        sa.build("apply", {"settings": "x"}, folders, repo / "cfg", repo)


def test_a_script_override_is_used(repo, folders):
    settings(repo, "overlap", OVERLAP)
    command = sa.build("overlap", {"settings": "overlap.json", "script": "other/overlap.py"}, folders, repo / "cfg", repo)["command"]
    assert command[0] == "other/overlap.py"


def test_a_script_given_as_a_list_puts_its_arguments_before_the_config(repo, folders):
    """A cleaner run through a wrapper: the wrapper is the script, the tool it runs is its first argument."""
    settings(repo, "overlap", OVERLAP)
    wrapped = ["spec_v1_1/use_clean.py", "spec_v1/run_tokenizer_sample.py"]
    built = sa.build("overlap", {"settings": "overlap.json", "script": wrapped}, folders, repo / "cfg", repo)
    assert built["command"][:3] == [*wrapped, "--config"] and built["command"][3] == built["config"] and len(built["command"]) == 4


@pytest.mark.parametrize("script", [[], [""], ["a.py", 3], {"a": 1}, 7, ""])
def test_a_script_that_is_neither_a_path_nor_a_list_of_strings_is_refused(repo, folders, script):
    settings(repo, "overlap", OVERLAP)
    with pytest.raises(sa.ConfigError, match="stages.overlap.script must be a script's path, or a list"):
        sa.build("overlap", {"settings": "overlap.json", "script": script}, folders, repo / "cfg", repo)
