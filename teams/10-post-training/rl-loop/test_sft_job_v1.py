"""Contracts of the first real SFT job: slice rules (length, same rows in both forms, split by statement, pinned packs)
and the driver (A4 gets A2's completed steps and skips the base evaluation; rows never leave the job; decision rule).
The fixture rows below are synthetic test fixtures, not training data."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "capstone"))
import sft_g5
import sft_job_v1 as job
import sft_rows
import sft_slice_v1 as sl

parametrize = pytest.mark.parametrize
T = sft_rows._load("g10_convert_for_capstone", sl.TEAM10 / "sft" / "convert.py").render.T


def fixture_text(statement: str, effort: str, think: str | None, answer: str) -> str:
    body = (f"{T['think']}{think}{T['think_end']}\n" if think is not None else "") + answer
    return (f"{T['im_start']}system\nReasoning effort: {effort}{T['im_end']}\n{T['im_start']}user\n{statement}"
            f"{T['im_end']}\n{T['im_start']}assistant\n{body}{T['im_end']}\n")


class CharRetok:
    """Stand-in for sft_rows.Retok: one id per character (ids = code points), same mask rule as the converter."""

    def __init__(self, tokenizer, table):
        self.convert = sft_rows._load("g10_convert_for_capstone", sl.TEAM10 / "sft" / "convert.py")

    def row(self, r):
        ids = [ord(c) for c in r["text"]]
        mask = self.convert.token_mask([tuple(s) for s in r["train_spans"]], [(i, i + 1) for i in range(len(ids))])
        if not any(mask):
            return None, "empty_mask"
        return {"id": r["id"], "input_ids": ids, "loss_mask": mask, "prompt_len": mask.index(1),
                "n_tokens": len(ids), "n_trained": sum(mask)}, "ok"


def pack_row(i: int, text: str, corrupt: bool = False) -> str:
    convert = sft_rows._load("g10_convert_for_capstone", sl.TEAM10 / "sft" / "convert.py")
    spans = convert.train_spans(text)
    r, _ = CharRetok(None, None).row({"id": f"sft-code-opencodereasoning-2/{i}", "text": text, "train_spans": spans})
    ids = r["input_ids"][:-1] + [0] if corrupt else r["input_ids"]
    return json.dumps({"id": r["id"], "set": "sft-code-opencodereasoning-2", "source_id": "x", "effort": "1k",
                       "text": text, "train_spans": spans, "input_ids": ids, "loss_mask": r["loss_mask"]})


@parametrize("ids", [[], [7], [1, 2, 3], list(range(500))])
def test_raw_id_count_equals_parsed_length(ids):
    line = json.dumps({"id": "a", "text": "t, with, commas", "input_ids": ids, "loss_mask": [0] * len(ids)})
    assert sl.n_ids_raw(line) == len(ids)


def test_strip_reasoning_deletes_only_the_block_and_needs_code_after():
    t = fixture_text("Add two numbers.", "1k", "reason here", "```python\nprint(1)\n```")
    s = sl.strip_reasoning(t, T)
    assert T["think"] not in s and "reason here" not in s
    assert s == t.replace(f"{T['think']}reason here{T['think_end']}\n", "")
    assert sl.strip_reasoning(fixture_text("q", "1k", None, "```python\n```"), T) is None
    assert sl.strip_reasoning(fixture_text("q", "1k", "r", "no code"), T) is None


def test_split_follows_the_statement_not_the_effort_label():
    a = fixture_text("Same problem.", "1k", "r1", "```python\nA\n```")
    b = fixture_text("Same problem.", "16k", "a much longer r2", "```python\nB\n```")
    assert sl.user_turn(a, T) == sl.user_turn(b, T) == "Same problem."
    assert sl.dev_digest(sl.user_turn(a, T)) == sl.dev_digest(sl.user_turn(b, T))


def make_pack(tmp_path: Path, n: int = 120) -> tuple[Path, dict]:
    lines, kinds = [], {}
    for i in range(n):
        if i % 10 == 0:  # too long
            text, kinds[i] = fixture_text(f"Problem {i}.", "4k", "x" * 400, "```python\npass\n```"), "long"
        elif i % 10 == 1:  # no reasoning block
            text, kinds[i] = fixture_text(f"Problem {i}.", "1k", None, "```python\npass\n```"), "nothink"
        elif i % 10 == 2:  # ids differ from the tokenizer's
            text, kinds[i] = fixture_text(f"Problem {i}.", "1k", "r", "```python\npass\n```"), "corrupt"
        else:
            text, kinds[i] = fixture_text(f"Problem {i % 40}.", "1k", "r" * (i % 7), "```python\nprint(%d)\n```" % i), "ok"
        lines.append(pack_row(i, text, corrupt=kinds[i] == "corrupt"))
    p = tmp_path / "pack.firewalled.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return p, kinds


def test_slice_keeps_the_same_rows_in_both_forms_and_drops_what_it_must(tmp_path, monkeypatch):
    monkeypatch.setattr(sft_rows, "Retok", CharRetok)
    pack, kinds = make_pack(tmp_path)
    (tmp_path / "tok").write_text("{}")
    s = sl.build([pack], tmp_path / "tok", Path("tab"), 300, tmp_path / "out", dev_rows=1000, check_hashes=False)
    assert s["stats"]["over_max_tokens"] == sum(k == "long" for k in kinds.values())
    assert s["stats"]["no_reasoning_block_or_code"] == sum(k == "nothink" for k in kinds.values())
    assert s["stats"]["retok_mismatch"] == sum(k == "corrupt" for k in kinds.values())
    read = lambda n: [json.loads(x) for x in (tmp_path / "out" / n).read_text().splitlines()]
    a2, a4, dev = read("a2_train.jsonl"), read("a4_train.jsonl"), read("dev.jsonl")
    assert [r["id"] for r in a2] == [r["id"] for r in a4]
    assert len(a2) + len(dev) == sum(k == "ok" for k in kinds.values())
    assert all(r["split"] == "train" for r in a2 + a4) and all(r["split"] == "eval" for r in dev)
    assert all(len(x["input_ids"]) < len(y["input_ids"]) for x, y in zip(a4, a2))
    # every completion of one statement is on one side
    stmt = lambda r: sl.user_turn("".join(map(chr, r["input_ids"])), T)
    assert not {stmt(r) for r in a2} & {stmt(r) for r in dev}
    assert sum(s["train_buckets"].values()) == len(a2)
    assert s["files"]["a2_train.jsonl"]["sha256"] == hashlib.sha256((tmp_path / "out" / "a2_train.jsonl").read_bytes()).hexdigest()


def test_unmeasured_pack_is_refused_before_it_is_read(tmp_path, monkeypatch):
    monkeypatch.setattr(sft_rows, "Retok", lambda *a: pytest.fail("rows read from an unpinned pack"))
    pack, _ = make_pack(tmp_path, 3)
    with pytest.raises(ValueError, match="not a measured firewalled shard"):
        sl.build([pack], Path("tok"), Path("tab"), 2048, tmp_path / "out")


def test_committed_firewall_record_names_shards_0_to_3():
    assert sorted(sl.expected_pack_hashes().values()) == ["0", "1", "2", "3"]


def metrics(delta, mixed, runs):
    return {"forgetting_delta_bpb": delta, "rl_mixed_groups": mixed, "rl_runs_share": runs}


def test_decision_rule():
    assert job.decide(metrics(0.01, 3, 0.2), metrics(0.02, 1, 0.5))["default_shape"] == "A2"
    assert job.decide(metrics(0.01, 0, 0.1), metrics(0.02, 0, 0.4)) == {
        "verdict": "no RL signal at this size", "default_shape": "A4", "rule": job.decide(metrics(0, 0, 0), metrics(0, 0, 0))["rule"]}
    assert job.decide(metrics(0.09, 9, 0.9), metrics(0.03, 2, 0.1))["default_shape"] == "A4"
    assert job.decide(metrics(0.09, 9, 0.9), metrics(None, 2, 0.1))["default_shape"] is None


def test_arm_metrics_reads_forgetting_and_rl_reasons():
    before = {"forgetting": {"val/bpb": 2.0, "val/groups/code_bpb": 3.0}}
    rep = {"log": [{}] * 5, "after": {"forgetting": {"val/bpb": 2.04, "val/groups/code_bpb": 2.5},
                                      "generation": {"format_validity": 0.5},
                                      "rl_screen": {"prompts": 2, "k": 4, "pass_rate": 0.125, "groups": {"mixed": 1},
                                                    "samples_with_code_fence": 6, "skipped_too_long": 0,
                                                    "reasons": {"pass": 1, "wrong answer on a test": 3, "x": 4}}}}
    m = job.arm_metrics(rep, before)
    assert m["steps"] == 5 and abs(m["forgetting_delta_bpb"] - 0.04) < 1e-12
    assert m["forgetting_delta_by_group"] == {"code_bpb": -0.5}
    assert m["rl_runs_share"] == 0.5 and m["rl_code_fence_share"] == 0.75 and m["rl_mixed_groups"] == 1


def test_a4_runs_a2s_completed_steps_without_base_eval_and_rows_are_removed(tmp_path, monkeypatch):
    calls = []

    def fake_build(packs, tok, tab, max_tokens, out, dev_rows, check_hashes=True):
        out.mkdir(parents=True)
        for n in ("a2_train.jsonl", "a4_train.jsonl", "dev.jsonl"):
            (out / n).write_text("rows")
        return {"train_rows": 1}

    def fake_arm(out, arm, cmd, timeout=None):
        calls.append((arm, cmd))
        (out / f"sft_{arm}").mkdir(exist_ok=True)
        rep = {"log": [{}] * (7 if arm == "a2" else int(cmd[cmd.index("--steps") + 1])),
               "before": None if "--no-before" in cmd else {"forgetting": {"val/bpb": 2.0}},
               "after": {"forgetting": {"val/bpb": 2.01}}}
        (out / f"sft_{arm}" / "sft_report.json").write_text(json.dumps(rep))
        return {"before": rep["before"], "after": rep["after"]}

    monkeypatch.setattr(job.probe, "check_pins", lambda *a: {"checks": {}})
    monkeypatch.setattr(job, "check_run_and_inputs", lambda a: {"block_size": 2048})
    monkeypatch.setattr(job.probe, "run_sft_arm", fake_arm)
    monkeypatch.setattr(sl, "build", fake_build)
    import make_adapter_config
    monkeypatch.setattr(make_adapter_config, "write_config", lambda out, *a: out)
    args = ["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b", "--heldout", "h",
            "--packs", "p", "--steps", "300", "--device", "cpu", "--out", str(tmp_path)]
    assert job.main(args) == 0
    (a2, c2), (a4, c4) = calls
    assert (a2, a4) == ("a2", "a4")
    assert "--no-before" not in c2 and "--no-before" in c4
    assert c2[c2.index("--steps") + 1] == "300" and c4[c4.index("--steps") + 1] == "7"
    assert not (tmp_path / "_inputs").exists()
    cmp = json.loads((tmp_path / "compare.json").read_text())
    assert cmp["steps_matched"] and abs(cmp["arms"]["A4"]["forgetting_delta_bpb"] - 0.01) < 1e-12


def test_pin_mismatch_builds_no_rows(tmp_path, monkeypatch):
    def bad(*a):
        raise ValueError("run folder was trained with different tokenizer_sha256")
    monkeypatch.setattr(job.probe, "check_pins", bad)
    monkeypatch.setattr(sl, "build", lambda *a, **k: pytest.fail("rows built after a pin mismatch"))
    args = ["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b", "--heldout", "h",
            "--packs", "p", "--out", str(tmp_path)]
    assert job.main(args) == 1
    assert json.loads((tmp_path / "summary.json").read_text())["failed_steps"] == ["pins"]


def _run_folder(tmp_path, block=2048):
    run = tmp_path / "run"
    run.mkdir()
    (run / "checkpoint.pt").write_bytes(b"x")
    (run / "manifest.json").write_text(json.dumps({"config": {"model": {"block_size": block}}}))
    return run


def test_missing_or_mismatched_input_stops_before_rows(tmp_path, monkeypatch):
    for case in ("missing_pack", "missing_pool", "block_size", "pool_sha"):
        d = tmp_path / case
        d.mkdir()
        _check_input_case(d, monkeypatch, case)


def _check_input_case(tmp_path, monkeypatch, case):
    run = _run_folder(tmp_path, block=1024 if case == "block_size" else 2048)
    pack, pool, ids = tmp_path / "pack.jsonl", tmp_path / "cc.jsonl", tmp_path / "ids.txt"
    for f in (pack, pool, ids):
        f.write_text("x")
    {"missing_pack": pack, "missing_pool": pool}.get(case, tmp_path / "none").unlink(missing_ok=True)
    monkeypatch.setattr(job.probe, "check_pins", lambda *a: {"checks": {}})
    monkeypatch.setattr(sl, "build", lambda *a, **k: pytest.fail("rows built after a failed input check"))
    out = tmp_path / "out"
    args = ["--g5-root", "g", "--run-folder", str(run), "--tokenizer", "t", "--byte-table", "b", "--heldout", "h",
            "--packs", str(pack), "--rl-tasks", str(pool), "--rl-ids", str(ids), "--out", str(out)]
    assert job.main(args) == 1
    err = json.loads((out / "pins.json").read_text())["error"]
    want = {"missing_pack": "#565", "missing_pool": "#564", "block_size": "block_size 1024", "pool_sha": "not the pinned"}
    assert want[case] in err


def test_inputs_present_and_pinned_pass(tmp_path, monkeypatch):
    run = _run_folder(tmp_path)
    pack, pool = tmp_path / "pack.jsonl", tmp_path / "cc.jsonl"
    pack.write_text("x")
    pool.write_text("x")
    monkeypatch.setattr(job, "RL_POOL_SHA256", job.probe.sha256_file(pool))
    a = job.parse_args(["--g5-root", "g", "--run-folder", str(run), "--tokenizer", "t", "--byte-table", "b",
                        "--heldout", "h", "--packs", str(pack), "--rl-tasks", str(pool), "--out", "o"])
    r = job.check_run_and_inputs(a)
    assert r["block_size"] == 2048 and r["rl_pool_sha256"] == job.RL_POOL_SHA256


def test_sft_g5_accepts_no_before():
    a = sft_g5.parse_args(["--adapter-config", "c", "--train", "t", "--eval", "e", "--method", "full", "--out", "o",
                           "--no-before"])
    assert a.no_before


def test_arms_compared_on_prompts_both_screens_reached():
    k = 8
    a2 = {"k": k, "prompts": 3, "skipped_too_long": 0, "per_prompt": [["t1", 0, 0, 0], ["t2", 3, 4, 8], ["t3", 0, 1, 8]]}
    a4 = {"k": k, "prompts": 5, "skipped_too_long": 0,
          "per_prompt": [["t1", 2, 8, 8], ["t2", 8, 8, 8], ["t3", 1, 2, 8], ["t4", 4, 8, 8], ["t5", 5, 8, 8]]}
    ids = job.common_prefix([a2, a4], "per_prompt")
    assert ids == ["t1", "t2", "t3"]
    m4 = job.screen_metrics(None, a4, None, ids)
    assert m4["rl_prompts"] == 3 and m4["rl_mixed_groups"] == 2 and m4["rl_screened_before_budget"] == 5
    assert abs(m4["rl_runs_share"] - 18 / 24) < 1e-12
    m2 = job.screen_metrics(None, a2, None, ids)
    assert m2["rl_mixed_groups"] == 1 and abs(m2["rl_pass_rate"] - 3 / 24) < 1e-12
    g2 = {"per_row": [["r1", 1, 1, 0, 300], ["r2", 0, 0, 1, 1536]]}
    g4 = {"per_row": [["r1", 1, 1, 0, 200], ["r2", 1, 1, 0, 250], ["r3", 1, 1, 0, 100]]}
    gids = job.common_prefix([g2, g4], "per_row")
    assert gids == ["r1", "r2"] and job.screen_metrics(g4, None, gids, None)["format_prompts"] == 2


def test_common_prefix_refuses_different_orders():
    with pytest.raises(RuntimeError):
        job.common_prefix([{"per_prompt": [["a", 0, 0, 0]]}, {"per_prompt": [["b", 0, 0, 0]]}], "per_prompt")
    assert job.common_prefix([{"prompts": 1}, {"per_prompt": []}], "per_prompt") is None


def test_rl_screen_stops_at_budget(tmp_path):
    import time as _t
    import torch

    class Codec:
        def encode_prompt(self, s):
            return [1, 2, 3]

        def decode_completion(self, ids):
            return "no code here"

    class Bundle:
        kv_cache = False
        spec = {"block_size": 64}

        def codec(self):
            return Codec()

        def sample(self, prompt, k, mn, temp, gen):
            _t.sleep(0.05)
            return torch.zeros(k, len(prompt) + 4, dtype=torch.long), torch.ones(k, 4, dtype=torch.bool), None

    tasks = tmp_path / "t.jsonl"
    tasks.write_text("".join(json.dumps({"id": f"x{i}", "statement": "s", "tests": []}) + "\n" for i in range(10)))
    ids = tmp_path / "ids.txt"
    ids.write_text("\n".join(f"x{i}" for i in range(10)))
    r = job.probe.rl_screen_bundle(Bundle(), tasks, ids, 2, 32, "cpu", 0, seconds=0.12)
    assert r["stopped_at_budget"] and 1 <= r["prompts"] < 10
    assert [x[0] for x in r["per_prompt"]] == [f"x{i}" for i in range(r["prompts"])]
    full = job.probe.rl_screen_bundle(Bundle(), tasks, ids, 2, 32, "cpu", 3)
    assert full["prompts"] == 3 and not full["stopped_at_budget"]


def test_arm_killed_at_deadline_and_weights_removed(tmp_path):
    arm_out = tmp_path / "sft_a2"
    arm_out.mkdir()
    (arm_out / "model.safetensors").write_bytes(b"w")
    cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
    with pytest.raises(RuntimeError, match="deadline"):
        job.probe.run_sft_arm(tmp_path, "a2", cmd, timeout=0.5)
    assert not (arm_out / "model.safetensors").exists()
    with pytest.raises(RuntimeError, match="not started"):
        job.run_arm(tmp_path, "a4", cmd, timeout=0)
