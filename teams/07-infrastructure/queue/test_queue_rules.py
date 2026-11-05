"""Queue rules v1 (docs/queue_rules_v1.md) and their checker, queue/queue_rules.py. CPU only, no network.

    cd teams/07-infrastructure && python -m pytest queue/test_queue_rules.py -q
"""
import datetime as dt
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import queue_rules as qr  # noqa: E402

RID = "g7-restore-test-20261104-01"
REQUEST = f"""# Restore test, 1 device

```
Team:            07-infrastructure
Owner:           G7 Member B (example-handle)
Lead approval:   example-lead
Question:        Does run B, restored from step 100, give bit-equal loss at steps 101 to 200?
Script:          teams/07-infrastructure/jobs/restore_test/restore_test.py
Command:         python jobs/restore_test/restore_test.py --config jobs/restore_test/config.yaml --run-id {RID} --device cuda
Config:          teams/07-infrastructure/jobs/restore_test/config.yaml
Inputs:          synthetic
Hardware:        1 GPU
Max time:        30                                    (TSAI stops the job at this limit)
Precision:       fp32
Measures:        steps with equal loss bits
Expected result: 100 of 100 steps equal
Outputs:         out/*.json, out/*.csv (50 MB or less in total)
Test log:        https://github.com/example/era-v5-lab/actions/runs/1
Run ID:          {RID}
Devices:         1
Log path:        ./out/{RID}/logs/
Checkpoint path: ./out/{RID}/ckpt/
```
"""


def write_request(tmp_path, text=REQUEST, name="2026-11-04-restore-test.md"):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def good_result(**over):
    r = {"schema": qr.RESULT_SCHEMA, "run_id": RID, "status": "pass", "exit_code": 0, "device_kind": "cpu",
         "device_count": 0, "max_time_min": 15, "elapsed_s": 41.5, "started_utc": "2026-11-04T10:00:00Z",
         "ended_utc": "2026-11-04T10:00:41Z", "numbers": {"bit_equal_steps": 100}}
    r.update(over)
    return r


STEP = "main/step_00000100-e1"                       # ckpt.py's step_rel(): <branch>/step_<08d>-e<epoch>


def make_out(tmp_path, result=None, committed=True, manifest=True):
    """./out as a job leaves it: one checkpoint of arm a, committed the way ckpt.py commits (MANIFEST.json,
    then latest.json and a commits.jsonl line naming the folder)."""
    p = qr.job_paths(RID, str(tmp_path / "out"), arm="a")
    os.makedirs(p["logs"])
    open(p["job_log"], "w").write("2026-11-04T10:00:00Z r0 start\n")
    step = os.path.join(p["ckpt_arm"], *STEP.split("/"))
    os.makedirs(step)
    if manifest:
        open(os.path.join(step, "MANIFEST.json"), "w").write("{}")
    if committed:
        ptr = {"step": 100, "branch": "main", "path": STEP, "epoch": 1}
        json.dump(ptr, open(os.path.join(p["ckpt_arm"], "latest.json"), "w"))
        open(os.path.join(p["ckpt_arm"], "commits.jsonl"), "w").write(json.dumps(ptr) + "\n")
    json.dump(result if result is not None else good_result(), open(p["result"], "w"))
    return str(tmp_path / "out")


# ---- R5: run ID
def test_run_id_is_made_from_the_request_name_and_date():
    assert qr.make_run_id("restore-test", dt.date(2026, 11, 4)) == RID
    assert qr.make_run_id("health-baseline", dt.date(2026, 11, 2), 2) == "g7-health-baseline-20261102-02"


@pytest.mark.parametrize("bad", ["G7-restore-20261104-01", "g7-restore--test-20261104-01", "g7-restore-20261304-01",
                                 "g7-restore-20261104-00", "g7-restore-20261104-1", "restore-20261104-01", ""])
def test_bad_run_ids_are_refused(bad):
    assert qr.run_id_problems(bad)


# ---- R3, R4: paths
def test_paths_put_everything_under_out_run_id():
    p = qr.job_paths(RID, "./out", arm="b")
    assert all(v.startswith(f"./out/{RID}") for v in p.values())
    assert p["ckpt_root"] == f"./out/{RID}/ckpt" and p["ckpt_arm"] == f"./out/{RID}/ckpt/b"
    assert p["job_log"] == f"./out/{RID}/logs/job.log"
    with pytest.raises(ValueError):
        qr.job_paths(RID, arm="Run-B")


# ---- the request
def test_a_filled_request_passes(tmp_path):
    assert qr.check_request(write_request(tmp_path)) == []


def test_the_raw_template_is_refused(tmp_path):
    raw = REQUEST.replace("Max time:        30", "Max time:        <minutes>").replace("Hardware:        1 GPU",
                                                                                     "Hardware:        CPU | 1 GPU")
    problems = qr.check_request(write_request(tmp_path, raw))
    assert any("Max time" in p for p in problems) and any("Hardware" in p for p in problems)


@pytest.mark.parametrize("old,new,word", [
    ("Max time:        30", "Max time:        90", "cap"),                    # R1
    ("Devices:         1", "Devices:         2", "does not match"),           # R2
    ("Devices:         1", "Devices:         4", "Devices"),                  # R2
    (f"Log path:        ./out/{RID}/logs/", "Log path:        /tmp/logs/", "Log path"),            # R3
    (f"Checkpoint path: ./out/{RID}/ckpt/", "Checkpoint path: ./ckpt/", "Checkpoint path"),       # R4
    ("--device cuda", "--device cuda | tee log.txt", "one command"),          # R6
    (f"--run-id {RID} ", "", "--run-id"),                                     # R5
    ("Run ID:          " + RID, "Run ID:          g7-restore-test-20261105-01", "request date"),  # R5
    ("Run ID:          " + RID, "Run ID:          g7-other-20261104-01", "short name"),           # R5
])
def test_each_rule_is_checked(tmp_path, old, new, word):
    assert old in REQUEST
    problems = qr.check_request(write_request(tmp_path, REQUEST.replace(old, new, 1)))
    assert any(word in p for p in problems), problems


def test_missing_g7_lines_are_reported(tmp_path):
    text = "\n".join(l for l in REQUEST.splitlines() if not l.startswith(("Run ID", "Devices")))
    problems = qr.check_request(write_request(tmp_path, text))
    assert any("`Run ID:`" in p for p in problems) and any("`Devices:`" in p for p in problems)


def test_request_file_name_follows_job_request_md(tmp_path):
    problems = qr.check_request(write_request(tmp_path, name="restore.md"))
    assert any("file name" in p for p in problems)


# ---- the ./out/ folder after a run
def test_a_good_out_folder_passes(tmp_path):
    assert qr.check_out(make_out(tmp_path), RID) == []


def test_a_pointer_to_a_folder_without_manifest_is_an_error(tmp_path):
    problems = qr.check_out(make_out(tmp_path, manifest=False), RID)
    assert any("has no MANIFEST.json" in p for p in problems)


def test_manifest_no_pointer_names_is_a_cut_save_not_a_checkpoint(tmp_path):
    out = make_out(tmp_path, committed=False)
    assert qr.check_out(out, RID) == []
    assert qr.check_checkpoints(os.path.join(out, RID, "ckpt")) == ([], [])


def test_complete_folders_are_the_committed_ones(tmp_path):
    out = make_out(tmp_path)
    assert qr.check_checkpoints(os.path.join(out, RID, "ckpt"))[1] == [os.path.join("a", STEP)]


def test_an_older_commit_in_commits_jsonl_is_complete_too(tmp_path):
    """restore() falls back through commits.jsonl, so every commit there is COMPLETE, not only latest.json's."""
    out = make_out(tmp_path)
    arm = os.path.join(out, RID, "ckpt", "a")
    os.makedirs(os.path.join(arm, "main", "step_00000050-e1"))
    open(os.path.join(arm, "main", "step_00000050-e1", "MANIFEST.json"), "w").write("{}")
    older = {"step": 50, "branch": "main", "path": "main/step_00000050-e1", "epoch": 1}
    lines = open(os.path.join(arm, "commits.jsonl")).read()
    open(os.path.join(arm, "commits.jsonl"), "w").write(json.dumps(older) + "\n" + lines)
    got = qr.check_checkpoints(os.path.join(out, RID, "ckpt"))
    assert got == ([], [os.path.join("a", STEP), os.path.join("a", "main", "step_00000050-e1")])


def test_a_claim_before_the_first_save_is_not_a_checkpoint(tmp_path):
    """ckpt.py's claim() writes latest.json with path null before anything is saved."""
    out = make_out(tmp_path, committed=False, manifest=False)
    arm = os.path.join(out, RID, "ckpt", "a")
    json.dump({"step": None, "branch": None, "path": None, "epoch": 1}, open(os.path.join(arm, "latest.json"), "w"))
    assert qr.check_out(out, RID) == []


@pytest.mark.parametrize("latest,word", [("{not json", "not a JSON object"),
                                         ('{"path": "main/latest"}', "is not <branch>/step_")])
def test_a_bad_pointer_is_reported(tmp_path, latest, word):
    out = make_out(tmp_path)
    open(os.path.join(out, RID, "ckpt", "a", "latest.json"), "w").write(latest)
    assert any(word in p for p in qr.check_out(out, RID))


def test_a_bad_commits_line_is_reported(tmp_path):
    out = make_out(tmp_path)
    open(os.path.join(out, RID, "ckpt", "a", "commits.jsonl"), "a").write("{\"step\": 3}\n")
    assert any("commits.jsonl line 2" in p for p in qr.check_out(out, RID))


@pytest.mark.parametrize("over,word", [
    ({"run_id": "g7-other-20261104-01"}, "run_id"),
    ({"status": "ok"}, "status"),
    ({"status": "pass", "exit_code": 75}, "exit_code 0"),
    ({"status": "stopped_at_limit", "exit_code": 0}, "exit_code 75"),
    ({"device_kind": "cpu", "device_count": 1}, "devices"),
    ({"device_kind": "gpu", "device_count": 3}, "devices"),
    ({"max_time_min": 15, "elapsed_s": 901}, "elapsed_s"),
    ({"max_time_min": 120}, "max_time_min"),
    ({"ended_utc": "2026-11-04 10:00"}, "ended_utc"),
])
def test_result_json_rules(tmp_path, over, word):
    problems = qr.check_out(make_out(tmp_path, good_result(**over)), RID)
    assert any(word in p for p in problems), problems


def test_missing_result_and_log_are_reported(tmp_path):
    out = make_out(tmp_path)
    os.remove(os.path.join(out, RID, "result.json"))
    os.remove(os.path.join(out, RID, "logs", "job.log"))
    problems = qr.check_out(out, RID)
    assert any("result.json" in p for p in problems) and any("job.log" in p for p in problems)


def test_a_second_run_folder_in_out_is_refused(tmp_path):
    out = make_out(tmp_path)
    os.makedirs(os.path.join(out, "g7-restore-test-20261104-02"))
    assert any("only ./out/" in p for p in qr.check_out(out, RID))


def test_out_over_50_mb_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(qr, "MAX_OUT_BYTES", 10)
    assert any("50 MB" in p for p in qr.check_out(make_out(tmp_path), RID))


# ---- command line
def test_command_line(tmp_path, capsys):
    assert qr.main(["run-id", "restore-test", "--date", "2026-11-04"]) == 0
    assert capsys.readouterr().out.strip() == RID
    assert qr.main(["check-request", write_request(tmp_path)]) == 0
    assert qr.main(["check-out", make_out(tmp_path), "--run-id", RID]) == 0
    assert qr.main(["run-id", "Bad_Name", "--date", "2026-11-04"]) == 1


def test_the_example_in_the_doc_passes(tmp_path):
    """Section 4 of docs/queue_rules_v1.md, with its placeholders filled, must pass the checker."""
    doc = open(os.path.join(os.path.dirname(__file__), "..", "docs", "queue_rules_v1.md"), encoding="utf-8").read()
    block = doc.split("## 4. A filled example", 1)[1].split("```", 2)[1]
    block = (block.replace("<name as on Axiom> (<github handle>)", "G7 Member B (example-handle)")
             .replace("<lead github handle>", "example-lead").replace("<link to the CPU log>", "https://example.org/log"))
    assert qr.check_request(write_request(tmp_path, "```" + block + "```\n")) == []
