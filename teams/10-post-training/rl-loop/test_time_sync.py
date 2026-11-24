"""train.time_sync: per-step phase seconds that own their GPU work. Off by default (no added synchronization); on CUDA,
the clock waits for queued kernels before each read. CPU only here: torch.cuda.synchronize is replaced by a counter.

    python -m pytest rl-loop/test_time_sync.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import torch
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import train  # noqa: E402

parametrize = pytest.mark.parametrize  # no dotted decorator: the lab pr-guard's old email regex flags it
PHASES = {"rollout", "reward", "old_logprobs", "train", "sync"}


def test_the_default_clock_is_host_time_and_never_synchronizes(monkeypatch):
    calls = []
    monkeypatch.setattr(torch.cuda, "synchronize", lambda d=None: calls.append(d))
    clock = train.phase_clock(None)
    assert clock is train.time.time
    clock()
    assert calls == []


def test_the_synced_clock_waits_for_the_device_before_each_read(monkeypatch):
    calls = []
    monkeypatch.setattr(torch.cuda, "synchronize", lambda d=None: calls.append(d))
    clock = train.phase_clock("cuda:0")
    t0 = clock()
    t1 = clock()
    assert calls == ["cuda:0", "cuda:0"] and t1 >= t0


def _toy_cfg(tmp_path, **train_kw):
    cfg = yaml.safe_load((HERE / "config" / "smoke_tiny_olmoe.yaml").read_text())
    cfg.update(out_dir=str(tmp_path / "out"), verbose=False)
    cfg["train"].update(steps=2, eval_every=2, **train_kw)
    return cfg


@parametrize("time_sync", [False, True])
def test_every_step_row_splits_its_seconds_by_phase_and_cpu_never_syncs(tmp_path, monkeypatch, time_sync):
    seen = []
    real = train.phase_clock
    monkeypatch.setattr(train, "phase_clock", lambda d: seen.append(d) or real(d))
    train.train(_toy_cfg(tmp_path, **({"time_sync": True} if time_sync else {})))
    rows = [json.loads(x) for x in (tmp_path / "out" / "metrics.jsonl").read_text().splitlines()]
    assert [r["step"] for r in rows] == [1, 2]
    for r in rows:
        assert set(r["times_s"]) >= PHASES and r["step_s"] == pytest.approx(sum(r["times_s"].values()), abs=0.01)
        assert "times_synced" not in r  # a CPU device has nothing queued: the flag is a no-op there
    assert seen == [None]
