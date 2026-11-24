"""Tests of capstone/rl_job_v1.py: pools and exclusions, guard, screen size and time rules, literal-sample detector,
the config written for rl-loop/train.py, and the detector's hook into train.evaluate (a stand-in module, no model).

    python -m pytest capstone/test_rl_job_v1.py
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rl_job_v1 as job  # noqa: E402


# ---------------------------------------------------------------- pools

def test_read_ids_splits_on_tab_and_skips_comments(tmp_path):
    f = tmp_path / "ids.txt"
    f.write_text("# c\ncc-a\tsample-hardcode\n\ncc-b\n")
    assert job.read_ids(f) == ["cc-a", "cc-b"]


def test_committed_exclusion_lists_are_the_pinned_ones():
    free, eff = job.read_ids(job.FREE_IDS), job.effort_ids()
    assert len(free) == 66 and len(set(free)) == 66   # 23 (18 Nov audit) + 43 constant-output / per-case-constant
    lines = [x for x in job.FREE_IDS.read_text(encoding="utf-8").splitlines() if x.strip()]
    import hashlib  # noqa: PLC0415
    old23 = "".join(x + "\n" for x in lines[:23]).encode()
    assert hashlib.sha256(old23).hexdigest() == "3709f52b460a361b33f97da03e9a4bb8895d61df752ef4c5c14224e9aa5664c7"  # 18 Nov list unchanged
    assert {x.split("\t")[1] for x in lines[23:]} <= {"constant-output", "per-case-constant"}
    assert len(eff) == 55 and len(set(eff)) == 55
    assert job.probe.sha256_file(job.FREE_IDS) == job.FREE_IDS_SHA256
    assert job.probe.sha256_file(job.EASY_IDS) == job.EASY_IDS_SHA256


def test_pool_removes_both_exclusion_lists_orders_easy_first_and_keeps_heldout_unfiltered():
    train = ["t1", "t2", "t3", "t4", "t5", "t6"]
    held = ["h1", "h2", "h3", "h4"]
    p = job.build_pools(train, held, free=["t2", "h2"], effort=["t5", "h3"], easy=["t6", "h1", "t3", "t2"], heldout_n=3)
    assert p["train_ids"] == ["t6", "t3", "t1", "t4"]          # easy ids that are trainable first, in the probe's order
    assert p["heldout_ids"] == ["h1", "h2", "h3"]               # file order, NOT filtered
    c = p["counts"]
    assert (c["trained_pool"], c["removed_free"], c["removed_effort"]) == (4, 1, 1)
    assert c["overlap_trained_free"] == c["overlap_trained_effort"] == c["overlap_trained_heldout"] == 0
    assert (c["heldout_subset_free"], c["heldout_subset_effort"]) == (1, 1)
    assert (c["easy_in_trained_pool"], c["easy_not_in_trained_pool"], c["easy_in_heldout_pool_file"]) == (2, 2, 1)


def test_pool_refuses_a_train_heldout_overlap_and_duplicates():
    with pytest.raises(ValueError, match="share 1 ids"):
        job.build_pools(["a", "b"], ["b", "c"], [], [], [])
    with pytest.raises(ValueError, match="duplicate"):
        job.build_pools(["a", "a"], ["c"], [], [], [])


# ---------------------------------------------------------------- guard

def _args(tmp_path):
    f = tmp_path / "cc.jsonl"
    f.write_text(json.dumps({"id": "x", "tests": [{"input": "1\n", "output": "2\n"}, {"input": "2\n", "output": "4\n"}]}) + "\n")
    return argparse.Namespace(rl_tasks=f), f


def test_guard_refuses_a_wrong_secret_path_before_anything_runs(tmp_path, monkeypatch):
    a, f = _args(tmp_path)
    t0 = time.perf_counter()
    for env, msg in ((None, "not set"), (str(tmp_path / "nope.jsonl"), "does not exist"), (str(tmp_path), "does not name the task file")):
        if env is None:
            monkeypatch.delenv("G10_STDIO_SECRET_PATHS", raising=False)
        else:
            monkeypatch.setenv("G10_STDIO_SECRET_PATHS", env)
        with pytest.raises(RuntimeError, match=msg):
            job.guard(a, tmp_path)
    assert time.perf_counter() - t0 < 2.0  # a refusal is fast: no model, no container


def test_attack_program_really_reads_the_expected_output_when_the_file_is_readable(tmp_path):
    """The probe is a real attack: run unsandboxed it prints the expected output, so a 0 score inside the runner means the
    runner hid the file, not that the probe was broken."""
    a, f = _args(tmp_path)
    r = subprocess.run([sys.executable, "-c", job.attack_program(f)], input="2\n", capture_output=True, text=True)
    assert r.stdout.strip() == "4"


# ---------------------------------------------------------------- screen size, time rules

def test_screen_size_is_the_largest_that_fits_ten_minutes():
    assert job.pick_screen_n(2.0)["n"] == 256          # 512 s
    assert job.pick_screen_n(4.0)["n"] == 128          # 512 s; 256 would take 1,024 s
    assert job.pick_screen_n(8.0)["n"] == 64           # 512 s
    s = job.pick_screen_n(20.0)
    assert s["n"] == 64 and s["fits"] is False         # nothing fits: the smallest, and it says so
    assert job.pick_screen_n(None)["fits"] is None


def test_not_enough_time_when_screen_three_updates_and_last_eval_do_not_fit():
    kw = dict(screen_n=64, pps=16, heldout_n=64, eval_k=4, k=8, update_s=16.0, score_s=0.5)
    need = job.enough_time(1e9, 3.0, **kw)["needed_s"]
    assert need == pytest.approx(64 * 3.5 + 3 * (16 * 3.5 + 16) + 64 * 3.5 * 0.5)
    assert job.enough_time(need + 1, 3.0, **kw)["ok"] is True
    assert job.enough_time(need - 1, 3.0, **kw)["ok"] is False


def test_time_table_totals_its_rows():
    t = job.time_table(3.0, screen_n=64, pps=16, updates=10, heldout_n=64, eval_k=4, k=8, update_s=16.0, score_s=0.5,
                       fixed_s=100.0, sft_s=900.0)
    assert t["total_s"] == pytest.approx(sum(s for _, s in t["rows"]), abs=0.5) and len(t["rows"]) == 5


# ---------------------------------------------------------------- literal-sample detector and statistics

def test_literal_sample_flags_constant_printers_and_lookups_not_real_solutions():
    tests = [{"input": "3 4 5\n", "output": "7\n"}, {"input": "10 20 30\n", "output": "30\n"}]
    assert job.literal_sample("print(7)", tests) == "no_stdin"                                   # 'prints a sample answer'
    assert job.literal_sample("print('YES')", tests) == "no_stdin"
    assert job.literal_sample("d = {'3 4 5': 7}\nprint(d[input().strip()])", tests) == "embeds_input"  # table lookup
    assert job.literal_sample("a, b, c = map(int, input().split())\nprint(a + b)", tests) is None   # a real solution
    assert job.literal_sample(None, tests) is None


def test_boot_ci_and_screen_survey():
    ci = job.boot_ci([0.0] * 30 + [1.0] * 10, seed=1)
    assert ci["mean"] == 0.25 and ci["ci_low"] < 0.25 < ci["ci_high"] and ci["n"] == 40
    s = job.screen_survey({"k": 8, "per_task": [{"id": "a", "passes": 0}, {"id": "b", "passes": 8}, {"id": "c", "passes": 3}],
                           "mixed": 1, "histogram": {"0": 1, "3": 1, "8": 1}, "min_mixed": 4,
                           "reasons": {"no_code": 12, "pass": 11, "wrong_answer": 1}, "truncated": 0.5, "mean_tokens": 90.0,
                           "rollout_s": 1.0, "score_s": 2.0})
    assert s["problems"] == 3 and s["mixed"] == 1 and s["failure_mix_share"]["no_code"] == 0.5 and s["cut_off_share"] == 0.5


def test_decision_rule_needs_all_three_clauses():
    good = {"ci_low": 0.02}
    assert job.decide_rl(good, 10, 8, 0.1, 0.1)["rl_helps"] is True
    assert job.decide_rl({"ci_low": -0.01}, 10, 8, 0.1, 0.1)["rl_helps"] is False
    assert job.decide_rl(good, 10, 11, 0.1, 0.1)["rl_helps"] is False          # more wrong answers: a format gain
    assert job.decide_rl(good, 10, 8, 0.1, 0.3)["rl_helps"] is False           # more literal prints
    assert job.decide_rl(good, 10, 8, None, None)["rl_helps"] is False         # an unmeasured clause is not a pass


# ---------------------------------------------------------------- config for train.py, detector hook

def _full_args(tmp_path, **kw):
    argv = ["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b", "--rl-tasks", "cc.jsonl",
            "--train-pool", "tp", "--heldout-pool", "hp", "--device", "cpu", "--out", str(tmp_path)]
    for k, v in kw.items():
        argv += [f"--{k.replace('_', '-')}", str(v)]
    return job.parse_args(argv)


def test_config_names_every_setting_and_caps_updates(tmp_path):
    a = _full_args(tmp_path)
    cfg = yaml.safe_load(job.write_train_config(a, tmp_path, None, None, 1234.0, 64).read_text())
    t = cfg["train"]
    assert (t["algo"], t["steps"], t["lr"], t["k"], t["prompts_per_step"], t["kl_coef"], t["tr_epsilon"]) == ("objective_v1", 10, 1e-5, 8, 16, 0.0, 0.2)
    assert t["screen"] == {"n": 64, "k": 8, "min_mixed": 4} and t["reward_pool"] > 0 and t["deadline_unix"] == 1234.0
    assert t["max_new"] == 1536 and t["sampler"] == "policy" and cfg["model"]["kv_cache"] is True and "init_state" not in cfg["model"]
    with pytest.raises(SystemExit):
        _full_args(tmp_path, updates=11)
    with pytest.raises(SystemExit):
        _full_args(tmp_path, reward_pool=0)


def test_logprob_gate_on_by_default_and_update_mode_switch(tmp_path):
    t = yaml.safe_load(job.write_train_config(_full_args(tmp_path), tmp_path, None, None, 1234.0, 64).read_text())["train"]
    assert t["logprob_gate"] is True and "update_mode" not in t  # default: gate on, trainer mode unchanged
    a = job.parse_args(["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b", "--rl-tasks", "cc.jsonl",
                        "--train-pool", "tp", "--heldout-pool", "hp", "--device", "cpu", "--out", str(tmp_path),
                        "--no-logprob-gate", "--update-mode", "eval"])
    t = yaml.safe_load(job.write_train_config(a, tmp_path, None, None, 1234.0, 64).read_text())["train"]
    assert "logprob_gate" not in t and t["update_mode"] == "eval"
    with pytest.raises(SystemExit):
        _full_args(tmp_path, update_mode="inference")


def test_sampler_stays_policy_by_default_and_g5_batch_and_time_sync_are_opt_in(tmp_path):
    t = yaml.safe_load(job.write_train_config(_full_args(tmp_path), tmp_path, None, None, 1234.0, 64).read_text())["train"]
    assert t["sampler"] == "policy" and "sampler_max_rows" not in t and "time_sync" not in t  # default config unchanged
    a = job.parse_args(["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b", "--rl-tasks", "cc.jsonl",
                        "--train-pool", "tp", "--heldout-pool", "hp", "--device", "cpu", "--out", str(tmp_path),
                        "--sampler", "g5_batch", "--sampler-max-rows", "64", "--time-sync"])
    t = yaml.safe_load(job.write_train_config(a, tmp_path, None, None, 1234.0, 64).read_text())["train"]
    assert (t["sampler"], t["sampler_max_rows"], t["time_sync"]) == ("g5_batch", 64, True)
    with pytest.raises(SystemExit):
        _full_args(tmp_path, sampler="vllm")


def test_rate_probe_under_g5_batch_times_one_batched_decode_of_the_probe_prompts(tmp_path):
    torch = pytest.importorskip("torch")
    tasks = tmp_path / "cc.jsonl"
    tasks.write_text("".join(json.dumps({"id": i, "statement": s}) + "\n"
                             for i, s in (("a", "xx"), ("b", "xxxx"), ("long", "x" * 60))))

    class Codec:
        def encode_prompt(self, text):
            return list(range(len(text)))

    class Bundle:
        spec = {"block_size": 64}
        calls = []

        def codec(self):
            return Codec()

        def sample_many(self, prompts, k, max_new, temperature, gen):
            self.calls.append((prompts, k, max_new, temperature))

    b = Bundle()
    a = _full_args(tmp_path, sampler="g5_batch", k=2, max_new=100)
    a.rl_tasks = tasks
    rep = job.batched_rate(a, b, ["a", "b", "long", "missing"])
    # one decode over every prompt that leaves 16 tokens of room ("long" does not, "missing" is not in the file);
    # max_new is cut to the room the longest kept prompt leaves (64 - 4)
    assert len(b.calls) == 1 and [len(p) for p in b.calls[0][0]] == [2, 4] and b.calls[0][1:] == (2, 60, 1.0)
    assert rep["prompts"] == 2 and rep["sampler"] == "g5_batch" and rep["max_new"] == 60
    assert rep["decode_seconds_per_prompt"] == pytest.approx(rep["seconds"] / 2, abs=0.01)


def test_detector_counts_literal_prints_only_in_heldout_evaluations(tmp_path):
    """train.evaluate / train.score_completions are patched in place; train.py is unchanged. Stand-in module, no model."""
    class Task:
        heldout = [[1], [2]]
        _items = {(1,): "a", (2,): "b", (9,): "a"}
        decode = staticmethod(lambda c, env_id=None: c)         # completions here are already text

    task = Task()
    mod = argparse.Namespace()
    mod.score_completions = lambda t, pairs, workers=1: [1.0, 1.0, 1.0, 0.0][:len(pairs)]

    def evaluate(sampler, t, prompts, *args, **kw):
        mod.score_completions(t, [([1], "```python\nprint(7)\n```"), ([2], "```python\nx=input()\nprint(x)\n```"),
                                  ([1], "```python\nprint(1+1)\n```"), ([2], "```python\nprint(0)\n```")][:4])
        return [0.5, 0.5], None
    mod.evaluate = evaluate
    tasks = {"a": {"tests": [{"input": "3 4\n", "output": "7\n"}]}, "b": {"tests": [{"input": "5\n", "output": "5\n"}]}}
    log: list = []
    ev, per = tmp_path / "evals.jsonl", tmp_path / "lit.jsonl"
    ev.write_text(json.dumps({"name": "heldout", "step": 0}) + "\n")   # step 0 already measured before a restart
    job.install_detector(mod, tasks, log, None, 1, ev, per)
    mod.score_completions(task, [([9], "```python\nprint(7)\n```")])    # a training call: not counted, log still empty
    assert log == []
    mod.evaluate(None, task, task.heldout)
    assert len(log) == 1 and log[0]["samples"] == 4 and log[0]["pass"] == 3
    assert log[0]["eval_index"] == 1 and json.loads(per.read_text())["eval_index"] == 1   # persisted, keyed to evals.jsonl
    assert log[0]["literal"] == 2 and log[0]["literal_by"] == {"no_stdin": 2}   # print(7) and print(1+1); input() reader is fine
    mod.evaluate(None, task, [[1]])                                     # not the held-out list: not counted
    assert len(log) == 1


def test_a_rehearsal_origin_is_refused_before_any_work_unless_it_is_a_dry_run(tmp_path):
    base = ["--g5-root", "g", "--run-folder", str(tmp_path), "--tokenizer", "t", "--byte-table", "b", "--rl-tasks", "c",
            "--train-pool", "tp", "--heldout-pool", "hp", "--out", str(tmp_path)]
    (tmp_path / "checkpoint.pt").write_text("x")
    (tmp_path / "manifest.json").write_text("{}")
    for n in ("c", "tp", "hp"):
        (tmp_path / n).write_text("x")
    a = job.parse_args(base + ["--origin", "g10_rehearsal"])
    a.rl_tasks, a.train_pool, a.heldout_pool = tmp_path / "c", tmp_path / "tp", tmp_path / "hp"
    with pytest.raises(ValueError, match="rehearsal adapter"):
        job.check_inputs(a)


# ---------------------------------------------------------------- origin g5_delivery (the real command's branch)

def _probe_file(tmp_path, **kw):
    p = tmp_path / "probe.json"
    p.write_text(json.dumps({"ids": [5, 6, 7, 8], "expected_mean_nll": 2.5, **kw}))
    return p


def test_a_delivered_run_folder_needs_teams_probe_and_the_probe_file_is_validated(tmp_path):
    """team5_adapter refuses origin g5_delivery without probe.ids and probe.expected_mean_nll; the job must carry them
    into adapter.yaml (before this was added the config had no probe block and the real command died in the adapter)."""
    import make_adapter_config as mac  # noqa: PLC0415
    base = ["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b", "--rl-tasks", "c",
            "--train-pool", "tp", "--heldout-pool", "hp", "--out", str(tmp_path)]
    with pytest.raises(ValueError, match="needs --probe-file"):
        job.adapter_probe(job.parse_args(base + ["--origin", "g5_delivery"]))
    assert job.adapter_probe(job.parse_args(base + ["--origin", "g10_rehearsal"])) is None
    a = job.parse_args(base + ["--origin", "g5_delivery", "--probe-file", str(_probe_file(tmp_path, atol=1e-5))])
    assert job.adapter_probe(a) == {"ids": [5, 6, 7, 8], "expected_mean_nll": 2.5, "atol": 1e-5}
    for bad in ({"expected_mean_nll": None}, {"expected_mean_nll": float("nan")}, {"ids": [1]}, {"ids": [1, "x"]}):
        with pytest.raises(ValueError, match="probe file"):
            mac.load_probe(_probe_file(tmp_path, **bad))


_STANDIN = Path(__file__).resolve().parents[6] / "work"
STANDIN_RUN = Path(os.environ.get("G10_STANDIN_RUN_FOLDER", _STANDIN / "pr587-main-check-2026-11-18/private/runs/post521"))
STANDIN_ART = Path(os.environ.get("G10_STANDIN_ARTIFACTS", _STANDIN / "capstone-rehearsal-2026-11-16/artifacts"))
needs_standin = pytest.mark.skipif(not (STANDIN_RUN / "checkpoint.pt").is_file() or not (STANDIN_ART / "tokenizer_p1536.json").is_file(),
                                   reason="set G10_STANDIN_RUN_FOLDER (a CPU run folder trained with this tree's Team 5 code) and G10_STANDIN_ARTIFACTS")


def _delivery(tmp_path):
    """A tmp copy of a tiny real G5 run folder (random-init, 20 CPU steps) whose manifest is relabelled the way Team 5's
    non-smoke delivery is labelled (status AGREED_BASELINE_RUN, smoke false). The weights, tokenizer and KE2 table are real
    files; only the label differs, which is exactly what origin g5_delivery checks."""
    import shutil  # noqa: PLC0415
    rf = tmp_path / "delivery"
    shutil.copytree(STANDIN_RUN, rf)
    m = json.loads((rf / "manifest.json").read_text())
    m["status"], m["smoke"] = "AGREED_BASELINE_RUN", False
    (rf / "manifest.json").write_text(json.dumps(m, indent=2))
    return rf


@needs_standin
def test_g5_delivery_origin_runs_pins_and_the_trainers_adapter_load_on_cpu(tmp_path):
    import make_adapter_config as mac  # noqa: PLC0415
    rl = Path(__file__).resolve().parents[1] / "rl-loop"
    sys.path.insert(0, str(rl))
    import team5_adapter as ta  # noqa: PLC0415
    repo = Path(__file__).resolve().parents[3]
    rf, tok, tab = _delivery(tmp_path), STANDIN_ART / "tokenizer_p1536.json", STANDIN_ART / "ke2_p1536" / "raw_table_P32.npz"
    stub = {n: tmp_path / n for n in ("cc.jsonl", "tp", "hp")}
    for p in stub.values():
        p.write_text("x")
    argv = ["--g5-root", str(repo), "--run-folder", str(rf), "--tokenizer", str(tok), "--byte-table", str(tab),
            "--rl-tasks", str(stub["cc.jsonl"]), "--train-pool", str(stub["tp"]), "--heldout-pool", str(stub["hp"]),
            "--device", "cpu", "--out", str(tmp_path / "out"), "--no-pack-check", "--no-git"]
    (tmp_path / "out").mkdir()
    # Team 5 would ship the expected NLL; the stand-in takes it from the rehearsal-origin build of the same weights.
    ids = [5, 6, 7, 8, 9, 10]
    cfg0 = mac.write_config(tmp_path / "rehearsal.yaml", repo, rf, tok, tab, Path(job.TEAM10), "g10_rehearsal", False,
                            probe={"ids": ids})
    nll = ta.build(yaml.safe_load(cfg0.read_text())).manifest["probe"]["mean_nll"]
    probe = _probe_file(tmp_path, ids=ids, expected_mean_nll=nll, atol=1e-4)

    # 1. without the probe file the job stops in pins, before pool or scorer
    a = job.parse_args(argv + ["--origin", "g5_delivery"])
    with pytest.raises(ValueError, match="needs --probe-file"):
        job.pins(a, tmp_path / "out")
    # 2. pins step passes on a non-smoke manifest and does not need --allow-fixture-smoke
    a = job.parse_args(argv + ["--origin", "g5_delivery", "--probe-file", str(probe)])
    res = job.pins(a, tmp_path / "out")
    assert res["block_size"] == a.max_tokens and "g5_sources" in res
    # 3. the trainer's adapter load (allow_fixture False): READY, learning report allowed, probe verified
    cfg = mac.write_config(tmp_path / "out" / "adapter.yaml", repo, rf, tok, tab, Path(job.TEAM10), a.origin, False,
                           probe=job.adapter_probe(a))
    policy, codec = ta.build_policy_and_codec(cfg, device="cpu", allow_fixture=False)
    man = codec.adapter_result.manifest
    assert codec.adapter_result.status == ta.READY and man["origin"] == "g5_delivery" and man["learning_report_allowed"] is True
    assert man["probe"]["verified_against"] == nll
    # 4. corrupted on purpose: a rehearsal label with a delivery origin, a wrong probe value, a smoke manifest
    m = json.loads((rf / "manifest.json").read_text())
    m["status"], m["smoke"] = "SMOKE_NOT_A_QUALITY_RESULT", True
    (rf / "manifest.json").write_text(json.dumps(m))
    bad = mac.write_config(tmp_path / "bad.yaml", repo, rf, tok, tab, Path(job.TEAM10), "g5_delivery", False, probe=job.adapter_probe(a))
    with pytest.raises(ta.ArtifactError, match="non-smoke AGREED_BASELINE_RUN"):
        ta.build_policy_and_codec(bad, device="cpu")
    m["status"], m["smoke"] = "AGREED_BASELINE_RUN", False
    (rf / "manifest.json").write_text(json.dumps(m))
    wrong = mac.write_config(tmp_path / "wrong.yaml", repo, rf, tok, tab, Path(job.TEAM10), "g5_delivery", False,
                             probe={"ids": ids, "expected_mean_nll": nll + 0.5})
    with pytest.raises(ta.ArtifactError, match="probe mean NLL"):
        ta.build_policy_and_codec(wrong, device="cpu")


def test_sampler_flag_defaults_to_policy_and_writes_g5_batch_config(tmp_path):
    import yaml

    base_argv = ["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b",
                 "--rl-tasks", "tasks.jsonl", "--train-pool", "tp.jsonl", "--heldout-pool", "hp.jsonl",
                 "--sft-arm", "none", "--device", "cpu", "--out", str(tmp_path / "out")]
    a_default = job.parse_args(base_argv)
    assert a_default.sampler == "policy"
    out_def = tmp_path / "def"
    out_def.mkdir()
    cfg_def = yaml.safe_load(job.write_train_config(a_default, out_def, None, None, 1000.0, 64).read_text())
    assert cfg_def["train"]["sampler"] == "policy"
    assert "sampler_max_rows" not in cfg_def["train"]

    a_batch = job.parse_args(base_argv + ["--sampler", "g5_batch", "--sampler-max-rows", "64"])
    out_b = tmp_path / "batch"
    out_b.mkdir()
    cfg_b = yaml.safe_load(job.write_train_config(a_batch, out_b, None, None, 1000.0, 64).read_text())
    assert cfg_b["train"]["sampler"] == "g5_batch"
    assert cfg_b["train"]["sampler_max_rows"] == 64



def test_micro_rows_defaults_to_1_and_0_means_the_whole_group(tmp_path):
    """Job RLG: the update of a whole group of 8 x 2,048 tokens does not fit (10.2 GiB for one row on a T4), so the
    config carries micro_rows 1 unless the job says otherwise; 0 leaves the key out (train.py: the whole group)."""
    t = yaml.safe_load(job.write_train_config(_full_args(tmp_path), tmp_path, None, None, 1234.0, 64).read_text())["train"]
    assert t["micro_rows"] == 1
    t = yaml.safe_load(job.write_train_config(_full_args(tmp_path, micro_rows=2), tmp_path, None, None, 1234.0, 64).read_text())["train"]
    assert t["micro_rows"] == 2
    t = yaml.safe_load(job.write_train_config(_full_args(tmp_path, micro_rows=0), tmp_path, None, None, 1234.0, 64).read_text())["train"]
    assert "micro_rows" not in t
