"""Subgroup observer: per-step counts of sampled and kept groups and tokens per input subgroup must agree with the
trainer's own step record. Toy task, tiny random OLMoE, CPU. Fixtures, not training data."""
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import train  # noqa: E402


def test_subgroup_counts_match_the_step_record(tmp_path, monkeypatch):
    real_build_task = train.build_task

    def build_task(tcfg, tokenizer, seed, pool=None):
        task = real_build_task(tcfg, tokenizer, seed)
        task.subgroup_of = lambda prompt: "odd" if int(prompt[0]) % 2 else "even"  # stand-in for the judge field
        return task
    monkeypatch.setattr(train, "build_task", build_task)
    cfg = yaml.safe_load((HERE / "config" / "smoke_objective_v1.yaml").read_text())
    cfg.update(out_dir=str(tmp_path / "out"), verbose=False)
    cfg["train"].update(steps=4, eval_every=100, ppo_epochs=1)
    s = train.train(cfg)
    recs = [json.loads(line) for line in (tmp_path / "out" / "metrics.jsonl").read_text().splitlines()]
    assert len(recs) == 4
    for r in recs:
        sg = r["subgroups"]
        assert set(sg) <= {"odd", "even"}
        assert sum(v["groups"] for v in sg.values()) == r["groups_used"] + r["groups_dropped"] == 16
        assert sum(v["kept"] for v in sg.values()) == r["groups_used"]
        assert sum(v["tokens"] for v in sg.values()) == r["sampled_tokens"]  # one host sync per step, same total
        assert all(0 <= v["kept_tokens"] <= v["tokens"] and v["rollouts"] == 8 * v["groups"] for v in sg.values())
    tot = s["subgroups"]
    assert sum(v["groups"] for v in tot.values()) == 64
    assert abs(sum(v["sampled_group_share"] for v in tot.values()) - 1) < 1e-3
