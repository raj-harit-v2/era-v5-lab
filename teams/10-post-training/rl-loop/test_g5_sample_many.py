"""g5_decode.sample_many and sampler g5_batch on a real Team 5 run folder (the CPU stand-in of COMMON: set
G10_STANDIN_RUN_FOLDER and G10_STANDIN_ARTIFACTS, as for capstone/test_rl_job_v1.py).

What must hold for the batched sampler to replace one decode per prompt:
  - every row's logits equal Team 5's full forward of that row alone (prompts of different lengths, left padding)
  - greedy decoding gives the same tokens, masks and stop reasons as g5_decode.sample per prompt
  - the trainer accepts sampler g5_batch for the G5 model and runs an objective_v1 step with it
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import torch
import yaml
from pytest import fixture  # bare decorator: pr-guard reads '+@a.b' as an email

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "capstone"))

_WORK = HERE.parents[5] / "work"
STANDIN_RUN = Path(os.environ.get("G10_STANDIN_RUN_FOLDER", _WORK / "pr587-main-check-2026-11-18/private/runs/post521"))
STANDIN_ART = Path(os.environ.get("G10_STANDIN_ARTIFACTS", _WORK / "capstone-rehearsal-2026-11-16/artifacts"))
needs_standin = pytest.mark.skipif(not (STANDIN_RUN / "checkpoint.pt").is_file()
                                   or not (STANDIN_ART / "tokenizer_p1536.json").is_file(),
                                   reason="set G10_STANDIN_RUN_FOLDER and G10_STANDIN_ARTIFACTS")


@fixture(scope="module")
def adapter_yaml(tmp_path_factory):
    import make_adapter_config as mac  # noqa: PLC0415
    d = tmp_path_factory.mktemp("g5many")
    repo = HERE.parents[2]
    return mac.write_config(d / "adapter.yaml", repo, STANDIN_RUN, STANDIN_ART / "tokenizer_p1536.json",
                            STANDIN_ART / "ke2_p1536" / "raw_table_P32.npz", HERE.parent, "g10_rehearsal", False,
                            probe={"ids": [5, 6, 7, 8]})


@fixture(scope="module")
def bundle(adapter_yaml):
    import team5_adapter as ta  # noqa: PLC0415
    return ta.build(yaml.safe_load(Path(adapter_yaml).read_text())).bundle


def _prompts(seed: int, lens) -> list[list[int]]:
    g = torch.Generator().manual_seed(seed)
    return [torch.randint(16, 30000, (n,), generator=g).tolist() for n in lens]


@needs_standin
def test_parity_many_matches_team5_forward_per_row(bundle):
    import g5_decode  # noqa: PLC0415
    rows = _prompts(1, (19, 9, 24, 4))
    assert g5_decode.parity_many(bundle.model, rows, 3) < 1e-4  # the module's stated tolerance (parity())


@needs_standin
def test_sample_many_greedy_equals_one_decode_per_prompt(bundle):
    prompts = _prompts(2, (6, 2, 11))
    bundle.kv_cache = True
    try:
        ref = [bundle.sample(p, 2, 8, 0.0, None, stop_ids=[-1]) for p in prompts]
        got = bundle.sample_many(prompts, 2, 8, 0.0, None, stop_ids=[-1])
        assert len(got) == 3
        for p, a, b in zip(prompts, ref, got):
            assert b[0].shape == (2, len(p) + 8) and b[1].shape == (2, 8)
            assert torch.equal(a[0], b[0]) and torch.equal(a[1], b[1]) and a[2] == b[2]
        stop = [int(ref[0][0][0, len(prompts[0]) + 2])]  # a token greedy decoding emits at step 2
        ref = [bundle.sample(p, 2, 8, 0.0, None, stop_ids=stop) for p in prompts]
        got = bundle.sample_many(prompts, 2, 8, 0.0, None, stop_ids=stop)
        assert any(r.startswith("stop:") for _, _, rs in ref for r in rs)
        assert all(torch.equal(a[0], b[0]) and torch.equal(a[1], b[1]) and a[2] == b[2] for a, b in zip(ref, got))
    finally:
        bundle.kv_cache = False


@needs_standin
def test_sample_many_checks_and_sampling_contract(bundle):
    prompts = _prompts(3, (5, 3))
    out = bundle.sample_many(prompts, 3, 4, 1.0, torch.Generator().manual_seed(0))
    for p, (s, m, r) in zip(prompts, out):
        assert s.shape == (3, len(p) + 4) and bool(m[:, 0].all()) and len(r) == 3
        assert torch.equal(s[:, :len(p)], torch.tensor([p] * 3))
    with pytest.raises(ValueError, match="block_size"):
        bundle.sample_many([[5] * bundle.spec["block_size"]], 1, 1, 0.0, None)
    with pytest.raises(ValueError, match="generator"):
        bundle.sample_many(prompts, 1, 1, 1.0, None)
    with pytest.raises(ValueError, match="non-empty"):
        bundle.sample_many([[5], []], 1, 1, 0.0, None)


@needs_standin
def test_g5_batch_sampler_chunks_rows_without_changing_greedy_tokens(bundle):
    import rollout  # noqa: PLC0415
    pol = bundle.policy()
    prompts = _prompts(4, (7, 3, 9, 5, 2))
    one = rollout.make_sampler("g5_batch", pol, max_rows=128).sample(prompts, 2, 6, 0.0)
    chunked = rollout.make_sampler("g5_batch", pol, max_rows=4).sample(prompts, 2, 6, 0.0)  # 2 prompts per chunk
    assert len(one) == len(chunked) == 5
    assert all(torch.equal(a.seq, b.seq) and torch.equal(a.cmask, b.cmask) for a, b in zip(one, chunked))
    with pytest.raises(ValueError, match="sample_many"):
        rollout.make_sampler("g5_batch", object())
    with pytest.raises(ValueError, match="at least 1"):
        rollout.make_sampler("g5_batch", pol, max_rows=0)


@needs_standin
def test_trainer_runs_an_objective_v1_step_with_sampler_g5_batch(adapter_yaml, tmp_path, monkeypatch):
    import train  # noqa: PLC0415
    from test_objective_v1_trainer import ScriptedTask  # noqa: PLC0415
    from test_rl_loop import MIXED, MIXED_B  # noqa: PLC0415
    monkeypatch.setattr(train, "build_task", lambda tcfg, tok, seed: ScriptedTask({MIXED: [0, 1, 0, 1], MIXED_B: [1, 0, 1, 0]}))
    calls = []
    real = train.rollout.G5BatchSampler.sample

    def spy(self, prompts, *a, **kw):
        calls.append(len(prompts))
        return real(self, prompts, *a, **kw)

    monkeypatch.setattr(train.rollout.G5BatchSampler, "sample", spy)
    cfg = {"seed": 7, "device": "cpu", "out_dir": str(tmp_path / "run"), "verbose": False,
           "model": {"kind": "team5_adapter", "adapter_config": str(adapter_yaml), "allow_fixture_smoke": True,
                     "kv_cache": True},
           "task": {"kind": "scripted"},
           "train": {"algo": "objective_v1", "steps": 1, "prompts_per_step": 2, "k": 4, "max_new": 3, "temperature": 1.0,
                     "lr": 1e-3, "ppo_epochs": 1, "kl_coef": 0.0, "eval_every": 100, "eval_k": 2, "sampler": "g5_batch",
                     "sampler_max_rows": 8, "fp32_master": False}}
    summary = train.train(cfg)
    assert summary["sampler"] == "g5_batch" and 2 in calls  # the step's two prompts in one sample call (evals: 1 prompt)
    with pytest.raises(ValueError, match="g5_batch is for the G5"):
        train.train({**cfg, "model": {"kind": "tiny_olmoe"}, "out_dir": str(tmp_path / "bad")})
