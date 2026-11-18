"""Durable state: a run that is stopped and continued must equal the run that was never stopped.

Toy task, tiny random OLMoE, CPU, real train.train with objective_v1 and AdamW. Fixtures, not training data.
"""
import copy
import json
import sys
from pathlib import Path

import pytest
import torch
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import train  # noqa: E402

TIMING = {"times_s", "step_s", "seconds", "rollout_tokens_per_s", "peak_torch_gb", "gpu_used_gb", "gpu_total_gb"}


def base_cfg(out: Path, steps: int) -> dict:
    cfg = yaml.safe_load((HERE / "config" / "smoke_objective_v1.yaml").read_text())
    cfg["out_dir"] = str(out)
    cfg["verbose"] = False
    cfg["train"].update(steps=steps, eval_every=4, state_every=2, state_dir=str(out / "state"), ppo_epochs=2)
    return cfg


def rows(out: Path, name: str) -> list[dict]:
    return [{k: v for k, v in json.loads(line).items() if k not in TIMING}
            for line in (out / name).read_text().splitlines()]


def final_state(out: Path) -> dict:
    latest = json.loads((out / "state" / "LATEST.json").read_text())
    return torch.load(out / "state" / latest["file"], map_location="cpu", weights_only=False)


def same_state(a: dict, b: dict) -> None:
    assert a["step"] == b["step"] and a["order"] == b["order"]
    for n in a["trainable"]:
        assert torch.equal(a["trainable"][n], b["trainable"][n]), n
    for sa, sb in zip(a["opt"]["state"].values(), b["opt"]["state"].values()):
        for key in sa:
            assert torch.equal(torch.as_tensor(sa[key]), torch.as_tensor(sb[key])), key
    for g in a["gens"]:
        assert torch.equal(a["gens"][g], b["gens"][g]), g


def test_stop_and_continue_equals_uninterrupted(tmp_path):
    whole = train.train(base_cfg(tmp_path / "whole", 8))
    cfg = base_cfg(tmp_path / "split", 8)
    cfg["train"]["max_steps_this_call"] = 3  # pauses after step 3: not a state_every or eval_every multiple
    first = train.train(copy.deepcopy(cfg))
    assert first == {"status": "PAUSED_AT_DEADLINE", "steps_done": 3, "steps_planned": 8, "seconds": first["seconds"]}
    cfg["train"]["max_steps_this_call"] = 2  # second pause lands on a state_every multiple (step 5 is not: 3+2)
    second = train.train(copy.deepcopy(cfg))
    assert second["status"] == "PAUSED_AT_DEADLINE" and second["steps_done"] == 5
    del cfg["train"]["max_steps_this_call"]
    done = train.train(copy.deepcopy(cfg))
    assert done["status"] == "COMPLETE" and done["resumed_from_step"] == 5 and whole["resumed_from_step"] is None
    assert rows(tmp_path / "whole", "metrics.jsonl") == rows(tmp_path / "split", "metrics.jsonl")
    assert rows(tmp_path / "whole", "evals.jsonl") == rows(tmp_path / "split", "evals.jsonl")
    assert [r["step"] for r in rows(tmp_path / "split", "metrics.jsonl")] == list(range(1, 9))
    same_state(final_state(tmp_path / "whole"), final_state(tmp_path / "split"))
    for key in ("heldout_reward_start", "heldout_reward_end", "heldout_change", "trainable_weight_change"):
        assert whole[key] == done[key], key


def test_kill_during_final_evaluation_loses_nothing(tmp_path, monkeypatch):
    whole = train.train(base_cfg(tmp_path / "whole", 4))
    real = train.evaluate
    calls = {"n": 0}

    def dying(*a, **kw):
        calls["n"] += 1
        if calls["n"] == 2:  # 1 = step 0, 2 = the evaluation after the last step
            raise KeyboardInterrupt("killed during the final evaluation")
        return real(*a, **kw)

    monkeypatch.setattr(train, "evaluate", dying)
    with pytest.raises(KeyboardInterrupt):
        train.train(base_cfg(tmp_path / "killed", 4))
    monkeypatch.setattr(train, "evaluate", real)
    assert final_state(tmp_path / "killed")["step"] == 4  # the four updates are on disk
    assert len(rows(tmp_path / "killed", "metrics.jsonl")) == 4
    done = train.train(base_cfg(tmp_path / "killed", 4))  # finalize-only: no training step is repeated
    assert done["status"] == "COMPLETE" and done["resumed_from_step"] == 4
    assert rows(tmp_path / "whole", "evals.jsonl") == rows(tmp_path / "killed", "evals.jsonl")
    same_state(final_state(tmp_path / "whole"), final_state(tmp_path / "killed"))
    assert whole["heldout_change"] == done["heldout_change"]


def test_stale_rows_after_the_restored_step_are_dropped(tmp_path):
    cfg = base_cfg(tmp_path / "run", 8)
    cfg["train"]["max_steps_this_call"] = 4
    train.train(copy.deepcopy(cfg))
    with open(tmp_path / "run" / "metrics.jsonl", "a") as f:  # a step that ran after the last saved state
        f.write(json.dumps({"step": 5, "train_reward": -1.0}) + "\n")
    del cfg["train"]["max_steps_this_call"]
    train.train(copy.deepcopy(cfg))
    got = rows(tmp_path / "run", "metrics.jsonl")
    assert [r["step"] for r in got] == list(range(1, 9)) and all(r["train_reward"] >= 0 for r in got)


def test_state_of_another_run_is_refused(tmp_path):
    cfg = base_cfg(tmp_path / "run", 2)
    train.train(copy.deepcopy(cfg))
    cfg["train"]["lr"] = cfg["train"]["lr"] * 2
    cfg["train"]["steps"] = 4
    with pytest.raises(RuntimeError, match="different run"):
        train.train(cfg)


def test_torn_latest_file_falls_back_to_previous_state(tmp_path):
    cfg = base_cfg(tmp_path / "run", 8)
    cfg["train"]["max_steps_this_call"] = 4
    train.train(copy.deepcopy(cfg))
    state = tmp_path / "run" / "state"
    files = sorted(state.glob("state.step*.pt"))
    assert [f.name for f in files] == ["state.step000002.pt", "state.step000004.pt"]
    files[-1].write_bytes(files[-1].read_bytes()[:1000])  # torn write of the newest file
    del cfg["train"]["max_steps_this_call"]
    done = train.train(copy.deepcopy(cfg))
    assert done["resumed_from_step"] == 2 and done["status"] == "COMPLETE"
    assert [r["step"] for r in rows(tmp_path / "run", "metrics.jsonl")] == list(range(1, 9))


def test_vllm_objective_v1_needs_temperature_one(tmp_path):
    cfg = base_cfg(tmp_path / "run", 1)
    cfg["train"].update(sampler="vllm", temperature=0.7)
    with pytest.raises(ValueError, match="temperature 1.0"):
        train.train(cfg)


def test_unset_autocast_preserves_pre_option_identity(tmp_path):
    cfg = base_cfg(tmp_path, 4)
    identity = train.state_identity(cfg, [])
    assert "autocast" not in identity["train"]
    cfg["train"]["autocast"] = None
    assert train.state_identity(cfg, []) == identity
    cfg["train"]["autocast"] = "bf16"
    active = train.state_identity(cfg, [])
    assert active["train"].pop("autocast") == "bf16"
    assert active == identity
