"""Tests for local_trial/: the example configs agree with each other and with the tracked sample manifest, and show.py prints a run.
Nothing here runs the pipeline.

  python -m pytest teams/01-data-a/pipeline/tests/test_local_trial.py
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

TRIAL = Path(__file__).resolve().parents[1] / "local_trial"
REPO = Path(__file__).resolve().parents[4]
MANIFEST = REPO / "teams/01-data-a/jobs/2026-11-02-tokenizer-sample-v0-clean/tokenizer_sample_v0_manifest.json"
spec = importlib.util.spec_from_file_location("show", TRIAL / "show.py")
show = importlib.util.module_from_spec(spec)
spec.loader.exec_module(show)


def configs():
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted((TRIAL / "configs").glob("*.json"))}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_the_trial_has_the_configs_the_readme_names():
    readme = (TRIAL / "README.md").read_text(encoding="utf-8")
    files = set(configs())
    assert files == {"1-full.json", "2-stop-at-clean.json", "3a-steps-to-dedup.json", "3b-steps-apply-to-f2.json",
                     "3c-steps-survivor-loss-and-shards.json", "4-adopt-clean.json", "5-error-from-without-record.json",
                     "6-error-changed-folder.json"}
    for name in files:
        assert f"local_trial/configs/{name}" in readme, name  # every config has its command in the README


def test_every_config_explains_itself_and_stays_below_the_trial_names():
    for name, c in configs().items():
        assert c["_comment"] and c["run_id"].startswith("trial-") and c["out"] == "out/pipeline", name


def test_the_clean_stage_reads_the_trial_parts_that_are_in_the_tracked_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    parts = {s["path"]: s for s in manifest["shards"]}
    full = configs()["1-full.json"]["stages"]["clean"]["only"]
    assert len(full) == 6 and sum(p.startswith("train/") for p in full) == 1 and set(full) <= set(parts)
    for name, c in configs().items():
        clean = c["stages"]["clean"]
        if clean.get("mode") == "adopt":
            continue
        assert clean["manifest_sha256"] == sha(MANIFEST), name  # the pin is the tracked manifest's sha256
        assert clean["expected_parts"] == {"train": 48, "heldout": 38} and len(parts) == 86
        assert clean["input"] == "inputs/local_trial" and clean["only"] == full


def test_paths_in_the_configs_are_relative_to_the_repository():
    for name, c in configs().items():
        for spec_ in c["stages"].values():
            for key in ("input", "tokenizer", "output", "settings", "script"):
                if key in spec_:
                    assert not Path(spec_[key]).is_absolute(), (name, key)


def test_the_steps_share_one_run_and_follow_each_other():
    c = configs()
    a, b, d = c["3a-steps-to-dedup.json"], c["3b-steps-apply-to-f2.json"], c["3c-steps-survivor-loss-and-shards.json"]
    assert a["run_id"] == b["run_id"] == d["run_id"] == "trial-steps"
    assert (a.get("from"), a["to"]) == (None, "dedup") and (b["from"], b["to"]) == ("apply", "f2") and (d["from"], d.get("to")) == ("survivor_loss", None)


def test_the_adopt_config_takes_the_clean_folder_of_the_steps_run():
    c = configs()["4-adopt-clean.json"]
    assert c["stages"]["clean"] == {"mode": "adopt", "output": "out/pipeline/trial-steps/clean"} and c["to"] == "dedup"


def test_the_error_configs_match_what_they_test():
    c = configs()
    assert c["5-error-from-without-record.json"]["from"] == "f2" and c["5-error-from-without-record.json"]["run_id"] not in ("trial-full", "trial-steps")
    assert c["6-error-changed-folder.json"]["run_id"] == c["1-full.json"]["run_id"] == "trial-full" and c["6-error-changed-folder.json"]["from"] == "apply"


def test_the_cleanup_command_removes_every_run_the_configs_make():
    readme = (TRIAL / "README.md").read_text(encoding="utf-8")
    for c in configs().values():
        assert f"out/pipeline/{c['run_id']}" in readme


def fake_manifest(folder, run_id, ok=True):
    d = folder / run_id
    d.mkdir(parents=True)
    path = d / "pipeline_manifest.json"
    path.write_text(json.dumps({
        "run_id": run_id, "totals": {"cleaned": 5}, "checks": [{"check": "a check", "ok": ok}],
        "stages": [{"stage": "clean", "mode": "run", "seconds": 1.5, "counts": {"rows": 5, "by_split": {"train": 5}}}]}), encoding="utf-8")
    return path


def test_show_prints_the_totals_a_line_per_stage_and_flags_a_failed_check(tmp_path):
    lines, failed = show.show_lines(fake_manifest(tmp_path, "r1"))
    assert lines[0] == "r1: {'cleaned': 5}" and "clean" in lines[1] and "{'rows': 5}" in lines[1] and lines[-1].endswith("none") and not failed
    assert show.show_lines(fake_manifest(tmp_path, "r2", ok=False))[1] is True


def test_show_reads_a_run_from_the_out_folder_and_names_a_missing_one(tmp_path, capsys):
    fake_manifest(tmp_path, "r3")
    assert show.main(["r3", str(tmp_path)]) == 0 and "r3:" in capsys.readouterr().out
    fake_manifest(tmp_path, "r4", ok=False)
    assert show.main(["r4", str(tmp_path)]) == 1
    with pytest.raises(SystemExit, match="not found"):
        show.main(["nope", str(tmp_path)])
