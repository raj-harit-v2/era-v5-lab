"""Tests for eval_watcher.py: no torch, no GPU, no ClickHouse server, no network.

The scorer process is replaced by a function that writes the same kind of eval-mini v1 file as run_lab_ckpt.py;
the rows go through Team 8's real load_jsonl.parse_source.

    python -m pytest teams/09-evaluation/harness_lab/tests/test_eval_watcher.py -q
"""
import hashlib
import importlib.util
import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("eval_watcher", HERE.parent / "eval_watcher.py")
ew = importlib.util.module_from_spec(_spec)
sys.modules["eval_watcher"] = ew
_spec.loader.exec_module(ew)


def make_run(root: Path, commits, name="run-x", newline_last=True, committed_at=0.0, final=False) -> Path:
    """A run folder in Team 7's layout. commits: (step, epoch, has_manifest). final: the last commit ends the run."""
    run = root / name
    run.mkdir(parents=True)
    lines = []
    for n, (step, epoch, has_manifest) in enumerate(commits, 1):
        rel = f"main/step_{step:08d}-e{epoch}"
        if has_manifest:
            (run / rel).mkdir(parents=True)
            (run / rel / "MANIFEST.json").write_text(json.dumps({"run_id": name, "branch": "main", "step": step,
                                                                 "committed_at": committed_at}))
        reason = "final" if final and n == len(commits) else "interval"
        lines.append(json.dumps({"step": step, "branch": "main", "path": rel, "time": committed_at,
                                 "reason": reason, "epoch": epoch}))
    text = "\n".join(lines) + ("\n" if newline_last and lines else "")
    (run / "commits.jsonl").write_text(text, encoding="utf-8")
    return run


def revision_of(run_dir: Path, path: str) -> str:
    """model_revision as run_lab_ckpt.py writes it: the sha256 of the bytes of MANIFEST.json."""
    return hashlib.sha256((run_dir / path / "MANIFEST.json").read_bytes()).hexdigest()


def doc_for(run_dir_arg: str, step: int, path: str, revision: str, value=50.0) -> dict:
    """The shape run_lab_ckpt.py writes (one smoke record)."""
    rec = {
        "model": "lab:run-x", "model_revision": revision,
        "checkpoint": {"run": "run-x", "branch": "main", "step": step, "epoch": 1, "tokens_seen": None,
                       "path": f"{Path(run_dir_arg).as_posix().rstrip('/')}/{path}"},
        "format": "fp32", "backend": "lab", "dtype": "float32",
        "task": "lab_smoke_next_token", "metric": "acc", "filter": "none", "primary": True, "value": value,
        "stderr": None, "n_items": 960, "item_set": "limit:64", "num_fewshot": 0, "decoding": "loglikelihood",
        "notes": ["test"], "seed": {"random": 1234, "numpy": 1234, "torch": 1234, "fewshot": 1234},
        "harness": {"name": "run_lab_ckpt", "version": "0.1"}, "hardware": "test (cpu)", "run_date": "2026-11-14",
    }
    return {"schema_version": "eval_mini_v1", "generated": "2026-11-14", "sources": [], "notes": [], "records": [rec]}


class FakeScorer:
    """Stands in for run_scorer: reads the argv the watcher built and writes the file run_lab_ckpt.py would."""

    def __init__(self, codes=None, wrong_step=False, on_call=None):
        self.calls, self.codes, self.wrong_step, self.on_call = [], list(codes or []), wrong_step, on_call

    def __call__(self, argv, log_path, timeout, stop):
        args = dict(zip(argv[2::2], argv[3::2]))
        self.calls.append(argv)
        log_path.write_text("fake scorer\n")
        if "--team5-run" in args:  # as run_lab_ckpt.team5_facts does
            given = args["--team5-run"]
            run_dir = Path(given)
            summary = json.loads((run_dir / "summary.json").read_text())
            step, path, revision = summary["steps"], "checkpoint.pt", summary["final_model_sha256"]
        else:
            given = args["--run-dir"]
            run_dir, step = Path(given), int(args["--step"])
            lines = [json.loads(x) for x in (run_dir / "commits.jsonl").read_text().splitlines() if x.strip()]
            path = [c for c in lines if c["step"] == step][-1]["path"]  # as run_lab_ckpt.read_pointer does
            revision = revision_of(run_dir, path)
        if self.on_call:
            self.on_call(run_dir, path)
        code = self.codes.pop(0) if self.codes else 0
        if code == 0:
            doc = doc_for(given, step + self.wrong_step, path, revision)
            Path(args["--out"]).write_text(json.dumps(doc))
        return code

    @property
    def steps(self):
        out = []
        for a in self.calls:
            args = dict(zip(a[2::2], a[3::2]))
            out.append(int(args["--step"]) if "--step" in args else "team5")
        return out


def run(tmp_path, run_dir, *extra, out="out"):
    return ew.main(["--run-dir", str(run_dir), "--out-dir", str(tmp_path / out), "--once", *extra])


def state(tmp_path, out="out") -> dict:
    return json.loads((tmp_path / out / "state.json").read_text())["checkpoints"]


@pytest.fixture
def scorer(monkeypatch):
    fake = FakeScorer()
    monkeypatch.setattr(ew, "run_scorer", fake)
    return fake


class RecordingLoader:
    """Team 8's real parser behind load_source, recording each run_id (no ClickHouse server)."""

    def __init__(self, fail_first=0):
        self.real, self.seen, self.fail_first = ew.loader(), [], fail_first

    def load_source(self, source, run_id_override=None, url=None):
        self.seen.append(run_id_override)
        if len(self.seen) <= self.fail_first:
            raise RuntimeError("ClickHouse HTTP 503: down")
        return self.real.parse_source(source, run_id_override=run_id_override)

    def parse_source(self, source, run_id_override=None):
        return self.real.parse_source(source, run_id_override=run_id_override)


# ---- which commits, in which order ----------------------------------------------------------------------------------

def test_scores_each_commit_once_in_order(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True), (200, 1, True), (300, 1, True)])
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_OK
    assert scorer.steps == [100, 200, 300]
    assert {r["status"] for r in state(tmp_path).values()} == {"scored"}
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_OK  # second pass: nothing new
    assert scorer.steps == [100, 200, 300]


def test_argv_passes_run_dir_as_given_and_extra_args(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True)])
    run(tmp_path, run_dir, "--no-load", "--scorer", "smoke", "--run-name", "job7/arm", "--", "--steps", "200")
    argv = scorer.calls[0]
    assert argv[1].endswith("run_lab_ckpt.py")
    assert argv[argv.index("--run-dir") + 1] == str(run_dir)
    assert argv[argv.index("--run-name") + 1] == "job7/arm"
    assert argv[-2:] == ["--steps", "200"]


def test_every_n_uses_the_retention_count(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(s, 1, True) for s in (100, 200, 300, 400, 500)])
    assert run(tmp_path, run_dir, "--no-load", "--every", "2") == ew.EXIT_OK
    assert scorer.steps == [200, 400]  # commit 2 and 4, as (i + 1) % 2 == 0 in run_retention


def test_from_step(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True), (200, 1, True)])
    run(tmp_path, run_dir, "--no-load", "--from-step", "150")
    assert scorer.steps == [200]


def test_superseded_and_gone_are_not_scored(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True), (100, 2, True), (200, 2, False)])
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_OK
    assert scorer.steps == [100]
    s = state(tmp_path)
    assert s["main/step_00000100-e1"]["status"] == "superseded"
    assert s["main/step_00000100-e2"]["status"] == "scored"
    assert s["main/step_00000200-e2"]["status"] == "gone"


def test_torn_last_line_waits_for_its_newline(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True), (200, 1, True)], newline_last=False)
    run(tmp_path, run_dir, "--no-load")
    assert scorer.steps == [100]
    with open(run_dir / "commits.jsonl", "a", encoding="utf-8") as f:
        f.write("\n")
    run(tmp_path, run_dir, "--no-load")
    assert scorer.steps == [100, 200]


@pytest.mark.parametrize("bad", ['{"step": 100, "branch": "main"', '{"branch": "main", "path": "main/x"}', '[1, 2]'])
def test_a_bad_complete_line_is_fatal(tmp_path, scorer, bad):
    run_dir = make_run(tmp_path, [(100, 1, True)])
    with open(run_dir / "commits.jsonl", "a", encoding="utf-8") as f:
        f.write(bad + "\n")
    with pytest.raises(SystemExit) as e:
        run(tmp_path, run_dir, "--no-load")
    assert e.value.code == ew.EXIT_FATAL
    assert scorer.calls == []  # nothing is scored from a commit log that cannot be trusted


# ---- failures, retries, the store going away ------------------------------------------------------------------------

def test_failure_is_retried_then_given_up(tmp_path, monkeypatch):
    fake = FakeScorer(codes=[1, 1])
    monkeypatch.setattr(ew, "run_scorer", fake)
    run_dir = make_run(tmp_path, [(100, 1, True)])
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_RETRY
    assert state(tmp_path)["main/step_00000100-e1"]["status"] == "error"
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_FAILED
    rec = state(tmp_path)["main/step_00000100-e1"]
    assert (rec["status"], rec["attempts"]) == ("failed", 2)
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_FAILED  # no third attempt
    assert len(fake.calls) == 2


def test_a_file_for_the_wrong_checkpoint_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(ew, "run_scorer", FakeScorer(wrong_step=True))
    run_dir = make_run(tmp_path, [(100, 1, True)])
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_RETRY
    assert "expected main/step_00000100-e1 step 100" in state(tmp_path)["main/step_00000100-e1"]["detail"]


def test_deleted_while_scored_is_gone_not_failed(tmp_path, monkeypatch):
    """Retention deletes an unprotected checkpoint about 90 min after its commit; a scorer that then fails is not a
    failure of the checkpoint."""
    fake = FakeScorer(codes=[1], on_call=lambda run_dir, path: (run_dir / path / "MANIFEST.json").unlink())
    monkeypatch.setattr(ew, "run_scorer", fake)
    run_dir = make_run(tmp_path, [(100, 1, True)])
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_OK
    rec = state(tmp_path)["main/step_00000100-e1"]
    assert rec["status"] == "gone" and "while it was scored" in rec["detail"]


def test_store_gone_after_a_read_marks_nothing(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True), (200, 1, False)])
    log = ew.CommitLog(run_dir)
    assert len(log.read()) == 2
    (run_dir / "commits.jsonl").unlink()
    with pytest.raises(ew.StoreUnavailable):
        log.read()


def test_store_missing_with_state_is_a_retry_not_done(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True)])
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_OK
    before = state(tmp_path)
    (run_dir / "commits.jsonl").rename(run_dir / "commits.jsonl.away")  # a mount that dropped out
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_RETRY
    assert state(tmp_path) == before


def test_manifest_check_while_store_is_down_marks_nothing(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, False)])
    a = ew.parse_args(["--run-dir", str(run_dir), "--out-dir", str(tmp_path / "out"), "--once"])
    w = ew.Watcher(a, threading.Event())
    w.read_commits()
    (run_dir / "commits.jsonl").unlink()
    with pytest.raises(ew.StoreUnavailable):
        w.manifest_gone("main/step_00000100-e1")


def test_load_failure_keeps_the_score_and_retries_only_the_load(tmp_path, scorer, monkeypatch):
    flaky = RecordingLoader(fail_first=1)
    monkeypatch.setattr(ew, "loader", lambda: flaky)
    run_dir = make_run(tmp_path, [(100, 1, True)])
    assert run(tmp_path, run_dir) == ew.EXIT_RETRY
    rec = state(tmp_path)["main/step_00000100-e1"]
    assert (rec["status"], rec["loaded"]) == ("scored", False) and "503" in rec["load_error"]
    assert run(tmp_path, run_dir) == ew.EXIT_OK
    assert state(tmp_path)["main/step_00000100-e1"]["loaded"] is True
    assert scorer.steps == [100]  # scored once, loaded twice


# ---- ClickHouse run_id, labels, state ownership ---------------------------------------------------------------------

def test_each_checkpoint_loads_under_its_own_run_id(tmp_path, scorer, monkeypatch):
    """load_jsonl.load_source deletes all rows of a run_id first, so a shared run_id would drop earlier scores."""
    rec = RecordingLoader()
    monkeypatch.setattr(ew, "loader", lambda: rec)
    run_dir = make_run(tmp_path, [(100, 1, True), (200, 1, True), (300, 1, True)])
    assert run(tmp_path, run_dir) == ew.EXIT_OK
    assert len(rec.seen) == len(set(rec.seen)) == 3
    assert rec.seen[0] == f"run-x:main/step_00000100-e1:smoke:{revision_of(run_dir, 'main/step_00000100-e1')[:12]}"


def test_run_ids_differ_across_labels_and_across_runs_with_one_name(tmp_path, scorer, monkeypatch):
    """Tier A and Tier B of one checkpoint, and two runs that share a run name (dry run 1 and dry run 2), must not
    delete each other's rows."""
    rec = RecordingLoader()
    monkeypatch.setattr(ew, "loader", lambda: rec)
    first = make_run(tmp_path / "dry1", [(100, 1, True)], committed_at=1.0)
    second = make_run(tmp_path / "dry2", [(100, 1, True)], committed_at=2.0)
    assert run(tmp_path, first, "--label", "tier-a", out="a1") == ew.EXIT_OK
    assert run(tmp_path, first, "--label", "tier-b", out="b1") == ew.EXIT_OK
    assert run(tmp_path, second, "--label", "tier-a", out="a2") == ew.EXIT_OK
    assert len(set(rec.seen)) == 3


def test_default_label_and_out_folder_follow_the_scorer_arguments(tmp_path):
    run_dir = make_run(tmp_path, [(100, 1, True)])
    a = ew.parse_args(["--run-dir", str(run_dir), "--scorer", "lm_eval_lab:team5", "--", "--tier", "A"])
    b = ew.parse_args(["--run-dir", str(run_dir), "--scorer", "lm_eval_lab:team5", "--", "--tier", "B"])
    assert a.label.startswith("lm_eval_lab_team5-") and a.label != b.label and a.out_dir != b.out_dir
    assert a.slot_lock == b.slot_lock  # one GPU slot for both tiers
    with pytest.raises(SystemExit):
        ew.parse_args(["--run-dir", str(run_dir), "--label", "tier a"])


def test_state_of_another_label_is_refused(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True)])
    run(tmp_path, run_dir, "--no-load", "--label", "tier-a")
    with pytest.raises(SystemExit) as e:
        run(tmp_path, run_dir, "--no-load", "--label", "tier-b")  # same --out-dir
    assert e.value.code == ew.EXIT_FATAL


def test_output_parses_with_team8_loader(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True)])
    run(tmp_path, run_dir, "--no-load")
    rec = state(tmp_path)["main/step_00000100-e1"]
    parsed = ew.loader().parse_source(rec["out"], run_id_override=rec["run_id"])
    assert parsed["target_table"] == "eval_mini" and parsed["metric_rows"] == 1
    row = parsed["rows"][0]
    assert (row["checkpoint_step"], row["run_id"]) == (100, rec["run_id"])


def test_state_of_another_run_is_refused(tmp_path, scorer):
    run(tmp_path, make_run(tmp_path, [(100, 1, True)], name="run-a"), "--no-load")
    with pytest.raises(SystemExit) as e:
        run(tmp_path, make_run(tmp_path, [(100, 1, True)], name="run-b"), "--no-load")
    assert e.value.code == ew.EXIT_FATAL


def test_second_watcher_on_the_same_state_is_refused(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True)])
    (tmp_path / "out").mkdir()
    with ew.StateLock(tmp_path / "out" / "state.json"):
        with pytest.raises(SystemExit) as e:
            run(tmp_path, run_dir, "--no-load")
    assert e.value.code == ew.EXIT_FATAL


def test_no_commits_yet_is_not_an_error(tmp_path, scorer):
    run_dir = tmp_path / "empty-run"
    run_dir.mkdir()
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_OK
    assert scorer.calls == []


def test_missing_run_dir_is_fatal(tmp_path):
    with pytest.raises(SystemExit) as e:
        run(tmp_path, tmp_path / "nope")
    assert e.value.code == ew.EXIT_FATAL


# ---- time per checkpoint, the GPU slot, the scorer process ----------------------------------------------------------

def test_time_per_checkpoint_and_lag_are_kept(tmp_path, scorer, capsys):
    run_dir = make_run(tmp_path, [(100, 1, True)], committed_at=time.time() - 100)
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_OK
    rec = state(tmp_path)["main/step_00000100-e1"]
    assert rec["seconds"] >= 0 and rec["lag_s"] >= 100 and rec["slot_wait_s"] >= 0
    assert "time: 1 checkpoint(s) scored" in capsys.readouterr().out


def test_slot_is_released_after_each_checkpoint(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True), (200, 1, True)])
    assert run(tmp_path, run_dir, "--no-load") == ew.EXIT_OK
    lock = ew.FileLock(tmp_path / "gpu_slot.lock")  # the default: next to the out folder
    assert lock.try_acquire()
    lock.release()


def test_a_held_slot_waits_and_a_stop_ends_the_wait(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True)])
    a = ew.parse_args(["--run-dir", str(run_dir), "--out-dir", str(tmp_path / "out"), "--once"])
    stop = threading.Event()
    w = ew.Watcher(a, stop)
    other = ew.FileLock(a.slot_lock)  # the other tier's watcher is scoring
    assert other.try_acquire()
    threading.Timer(0.3, stop.set).start()
    with pytest.raises(ew.Stopped):
        w.poll()
    other.release()
    assert scorer.calls == []
    assert not (tmp_path / "out" / "state.json").exists()  # nothing was decided, so nothing was saved


def test_until_final_ends_the_watch_after_the_last_commit(tmp_path, scorer):
    run_dir = make_run(tmp_path, [(100, 1, True), (200, 1, True), (300, 1, True)], final=True)
    code = ew.main(["--run-dir", str(run_dir), "--out-dir", str(tmp_path / "out"), "--no-load", "--until-final",
                    "--interval", "0.01"])
    assert code == ew.EXIT_OK and scorer.steps == [100, 200, 300]


def test_until_final_waits_while_the_run_goes_on_or_work_is_left(tmp_path, scorer):
    a = ew.parse_args(["--run-dir", str(make_run(tmp_path, [(100, 1, True)])), "--out-dir", str(tmp_path / "o1")])
    w = ew.Watcher(a, threading.Event())
    w.poll()
    assert not w.run_ended()                    # no final commit yet: keep watching
    b = ew.parse_args(["--run-dir", str(make_run(tmp_path / "r2", [(100, 1, True)], final=True)),
                       "--out-dir", str(tmp_path / "o2"), "--no-load"])
    w = ew.Watcher(b, threading.Event())
    w.read_commits()
    assert not w.run_ended()                    # final commit seen, but not scored yet
    w.poll()
    assert w.run_ended()


def test_real_subprocess_timeout_and_log(tmp_path):
    """run_scorer itself: output goes to the log, a scorer past --timeout is stopped, and a retry keeps the first
    attempt's output in the same log."""
    log = tmp_path / "x.log"
    code = ew.run_scorer([sys.executable, "-c", "print('hello from scorer')"], log, 30, threading.Event())
    assert code == 0 and "hello from scorer" in log.read_text()
    code = ew.run_scorer([sys.executable, "-c", "import time; time.sleep(30)"], log, 1.5, threading.Event())
    text = log.read_text()
    assert code == ew.TIMEOUT_CODE and "--timeout" in text and "hello from scorer" in text
    assert text.count("=== ") == 2


@pytest.mark.skipif(os.name == "nt", reason="process groups are POSIX; Windows ends the scorer process only")
def test_timeout_ends_the_scorers_children_too(tmp_path):
    log = tmp_path / "x.log"
    child = ("import subprocess, sys, time; "
             "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
             "print('child', p.pid, flush=True); time.sleep(60)")
    assert ew.run_scorer([sys.executable, "-c", child], log, 2.0, threading.Event()) == ew.TIMEOUT_CODE
    pid = int(next(line.split()[1] for line in log.read_text().splitlines() if line.startswith("child ")))
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        stat = Path(f"/proc/{pid}/stat")
        if stat.exists() and stat.read_text().rsplit(")", 1)[-1].split()[0] == "Z":
            break  # dead, waiting for a container's init to reap it
        time.sleep(0.1)
    else:
        pytest.fail(f"child {pid} of the stopped scorer is still alive")


# ---- --team5-run: dry run 1, a Team 5 train_week2.py run folder with one checkpoint ---------------------------------

REV5 = "ab" * 32


def make_team5_run(root: Path, status="COMPLETED", steps=1221, checkpoint=True, summary=True, name="dryrun1-1234"):
    run = root / name
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"artifacts": {"tokenizer_sha256": "e6b9"}}))
    if checkpoint:
        (run / "checkpoint.pt").write_bytes(b"weights")
    if summary:
        (run / "summary.json").write_text(json.dumps({"status": status, "steps": steps,
                                                      "final_model_sha256": REV5}))
    return run


def run5(tmp_path, run_dir, *extra, out="out"):
    return ew.main(["--team5-run", str(run_dir), "--out-dir", str(tmp_path / out), "--once", *extra])


def test_team5_run_scores_its_one_checkpoint_and_loads_it(tmp_path, scorer, monkeypatch):
    rec = RecordingLoader()
    monkeypatch.setattr(ew, "loader", lambda: rec)
    run_dir = make_team5_run(tmp_path)
    assert run5(tmp_path, run_dir, "--label", "tier-a") == ew.EXIT_OK
    argv = scorer.calls[0]
    assert argv[argv.index("--team5-run") + 1] == str(run_dir) and "--step" not in argv and "--run-dir" not in argv
    (r,) = state(tmp_path).values()
    assert (r["status"], r["loaded"], r["step"]) == ("scored", True, 1221)
    assert rec.seen == [f"dryrun1-1234:checkpoint.pt:tier-a:{REV5[:12]}"]
    assert run5(tmp_path, run_dir, "--label", "tier-a") == ew.EXIT_OK and len(scorer.calls) == 1  # done once


def test_team5_run_waits_until_summary_is_written(tmp_path, scorer):
    run_dir = make_team5_run(tmp_path, summary=False)
    assert run5(tmp_path, run_dir, "--no-load") == ew.EXIT_OK  # nothing owned yet: --once has nothing to do
    assert scorer.calls == []


def test_team5_run_ends_by_itself_without_once(tmp_path, scorer):
    run_dir = make_team5_run(tmp_path)
    code = ew.main(["--team5-run", str(run_dir), "--out-dir", str(tmp_path / "out"), "--no-load", "--interval", "0.05"])
    assert code == ew.EXIT_OK and scorer.steps == ["team5"]  # --team5-run implies --until-final


@pytest.mark.parametrize("status", ["INCOMPLETE_NOT_A_RESULT", "SMOKE"])
def test_team5_run_that_did_not_complete_is_fatal(tmp_path, scorer, status):
    run_dir = make_team5_run(tmp_path, status=status)
    with pytest.raises(SystemExit) as e:
        run5(tmp_path, run_dir, "--no-load")
    assert e.value.code == ew.EXIT_FATAL and scorer.calls == []


def test_team5_run_without_checkpoint_is_gone(tmp_path, scorer):
    run_dir = make_team5_run(tmp_path, checkpoint=False)
    assert run5(tmp_path, run_dir, "--no-load") == ew.EXIT_OK
    (r,) = state(tmp_path).values()
    assert r["status"] == "gone" and scorer.calls == []


def test_team5_run_needs_every_1_and_excludes_run_dir(tmp_path):
    run_dir = make_team5_run(tmp_path)
    for extra in (["--every", "10"], ["--run-dir", str(run_dir)]):
        with pytest.raises(SystemExit) as e:
            run5(tmp_path, run_dir, *extra)
        assert e.value.code == 2


def test_load_over_http_sends_rows_with_the_eval_mini_columns(tmp_path, scorer):
    """Without --no-load: Team 8's real load_source over HTTP to a local stand-in for ClickHouse. Each eval_mini row
    must have exactly the columns of schema_v1.sql (JSONEachRow refuses unknown fields), null only where Nullable."""
    import http.server
    import re

    schema = (ew.LOAD_JSONL.parent / "schema_v1.sql").read_text(encoding="utf-8")
    block = re.search(r"CREATE TABLE IF NOT EXISTS eval_mini\s*\((.*?)\n\)", schema, re.S).group(1)
    cols = dict(re.findall(r"^\s*(\w+)\s+(.+?),?\s*$", block, re.M))
    cols.pop("loaded_at")  # DEFAULT now64
    seen = []

    class FakeClickHouse(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            sql, _, data = self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8").partition("\n")
            seen.append((sql.strip(), data))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeClickHouse)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        run_dir = make_team5_run(tmp_path)
        url = f"http://127.0.0.1:{server.server_address[1]}"
        assert run5(tmp_path, run_dir, "--label", "tier-a", "--clickhouse-url", url) == ew.EXIT_OK
    finally:
        server.shutdown()
    (r,) = state(tmp_path).values()
    assert r["loaded"] is True
    data = [(q, d) for q, d in seen if q.startswith(("ALTER", "INSERT"))]
    assert [q.split(" WHERE")[0].split(" (")[0] for q, _ in data] == [
        "ALTER TABLE eval_mini DELETE", "ALTER TABLE ingest_manifest DELETE",
        "INSERT INTO eval_mini FORMAT JSONEachRow", "INSERT INTO ingest_manifest"]
    assert f"run_id = '{r['run_id']}'" in data[0][0]
    rows = [json.loads(x) for x in data[2][1].splitlines() if x.strip()]
    assert len(rows) == 1 and set(rows[0]) == set(cols)
    assert all(rows[0][k] is not None or t.startswith("Nullable") for k, t in cols.items())
    assert rows[0]["checkpoint_step"] == 1221 and rows[0]["model_revision"] == REV5
