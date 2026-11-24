"""Offline tests for capstone/dryrun2_dt_compare.py and KE2/KAS untied head readiness."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dryrun2_dt_compare as cmp  # noqa: E402
import keep_weights as kw  # noqa: E402
import sft_g5  # noqa: E402

BASE = ["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b",
        "--heldout", "h", "--packs", "p", "--steps", "200", "--device", "cpu"]


def test_default_dt_args_match_17_nov_paper_repo_port_check():
    a = cmp.parse_args([*BASE, "--out", "o"])
    assert a.dt_lr == pytest.approx(5e-4)
    assert a.dt_targets == "g5_gate"
    assert a.dt_alpha_start == 100.0
    assert a.dt_alpha_end == 1000.0
    assert a.dt_eta == pytest.approx(1.0 / 2048.0)
    assert a.dt_lambda == pytest.approx(1e-5)
    assert a.dt_prior_strength == 3.0
    assert a.keep_canary_state_dir is None
    assert a.keep_weights_dir is None


def test_build_arm_cmd_sets_equal_steps_and_no_before_on_lora_and_dt(tmp_path):
    a = cmp.parse_args([*BASE, "--keep-weights-dir", str(tmp_path / "kw"),
                        "--keep-weights-arms", "full,dt", "--out", str(tmp_path / "out")])
    cfg, rows, dev = Path("a.yaml"), Path("tr.jsonl"), Path("ev.jsonl")
    c_full = cmp.build_arm_cmd(a, "full", cfg, rows, dev, tmp_path / "f", 123, False)
    c_lora = cmp.build_arm_cmd(a, "lora", cfg, rows, dev, tmp_path / "l", 123, True)
    c_dt = cmp.build_arm_cmd(a, "dt", cfg, rows, dev, tmp_path / "d", 123, True)
    assert "--no-before" not in c_full and "--keep-weights-dir" in c_full
    assert "--no-before" in c_lora and "--keep-weights-dir" not in c_lora
    assert "--no-before" in c_dt and "--keep-weights-dir" in c_dt
    assert c_dt[c_dt.index("--dt-targets") + 1] == "g5_gate"
    assert float(c_dt[c_dt.index("--lr") + 1]) == pytest.approx(5e-4)
    for c in (c_full, c_lora, c_dt):
        assert c[c.index("--steps") + 1] == "123"


def test_run_matches_steps_across_all_three_arms_and_writes_compare_md(tmp_path, monkeypatch):
    import make_adapter_config
    import sft_slice_v1 as sl

    seen_cmds: dict[str, list[str]] = {}
    canary_dests: dict[str, Path | None] = {}

    def fake_build(packs, tok, tab, max_tokens, out, dev_rows, check_hashes=True):
        out.mkdir(parents=True)
        for n in ("a2_train.jsonl", "a4_train.jsonl", "dev.jsonl"):
            (out / n).write_text("row\n", encoding="utf-8")
        return {"train_rows": 1}

    def fake_run_arm(out, arm, cmd, timeout=None, canary_dest=None):
        seen_cmds[arm] = cmd
        canary_dests[arm] = canary_dest
        d = out / f"sft_{arm}"
        d.mkdir(parents=True, exist_ok=True)
        n_steps = 42 if arm == "full" else int(cmd[cmd.index("--steps") + 1])
        delta = {"full": 0.052, "lora": 0.030, "dt": 0.018}[arm]
        rep = {
            "log": [{"step": i + 1, "loss": 1.0} for i in range(n_steps)],
            "train_seconds": 1.2,
            "before": {"eval_loss": {"nll_per_target": 2.5}, "forgetting": {"val/bpb": 1.50}},
            "after": {
                "eval_loss": {"nll_per_target": 1.8},
                "forgetting": {"val/bpb": 1.50 + delta},
                "generation": {"format_validity": 0.8, "closed_im_end": 0.9, "hit_budget": 0.0, "mean_gen_tokens": 20.0},
            },
            "method_info": {"band_at_init": {"in_band_frac": 0.99}, "deletion_final": {"deleted_frac": 0.03}},
        }
        (d / "sft_report.json").write_text(json.dumps(rep), encoding="utf-8")
        return {"ok": True, "steps_completed": n_steps, "before": rep["before"]}

    monkeypatch.setattr(cmp.probe, "check_pins", lambda *a: {"checks": {}})
    monkeypatch.setattr(cmp.job, "check_run_and_inputs", lambda a: {"block_size": 2048})
    monkeypatch.setattr(cmp.job, "check_g5_sources", lambda a: {})
    monkeypatch.setattr(cmp.job, "run_arm", fake_run_arm)
    monkeypatch.setattr(sl, "build", fake_build)
    import inspect  # noqa: PLC0415
    real_sig = inspect.signature(make_adapter_config.write_config)
    configs = []

    def checked_write_config(*a, **kw):  # the real signature must accept the call (a stray kwarg used to crash every run)
        bound = real_sig.bind(*a, **kw)
        configs.append(bound.arguments)
        return bound.arguments["out"]

    monkeypatch.setattr(make_adapter_config, "write_config", checked_write_config)

    out = tmp_path / "run_out"
    canary = tmp_path / "canary_keep"
    probe_file = tmp_path / "probe.json"
    probe_file.write_text(json.dumps({"ids": [5, 6, 7], "expected_mean_nll": 2.5, "atol": 1e-4}), encoding="utf-8")
    args = cmp.parse_args([*BASE, "--keep-canary-state-dir", str(canary), "--probe-file", str(probe_file),
                           "--out", str(out)])
    rc = cmp.run(args, out)
    assert rc == 0
    assert configs[0]["probe"] == {"ids": [5, 6, 7], "expected_mean_nll": 2.5, "atol": 1e-4}
    # Full completed 42 steps; LoRA and DT must be locked to 42 steps too.
    assert seen_cmds["lora"][seen_cmds["lora"].index("--steps") + 1] == "42"
    assert seen_cmds["dt"][seen_cmds["dt"].index("--steps") + 1] == "42"
    assert canary_dests == {"full": None, "lora": None, "dt": canary / "dt"}
    comp = json.loads((out / "compare.json").read_text(encoding="utf-8"))
    assert comp["steps_matched"] is True
    assert comp["arms"]["full"]["forgetting_verdict"] == "FORGET (at limit)"
    assert comp["arms"]["dt"]["forgetting_verdict"] == "ok"
    md = (out / "compare.md").read_text(encoding="utf-8")
    assert "| dt | 42 |" in md and "| lora | 42 |" in md and "| full | 42 |" in md


class _MockKASHead(nn.Module):
    """Minimal untied KE2/KAS-like output head (no `weight`, no `out_features`; has `W_out` + `tok_u[V, r]`)."""

    def __init__(self, vocab: int = 64, d_model: int = 16, tok_rank: int = 8):
        super().__init__()
        self.vocab_size = vocab
        self.W_out = nn.Linear(d_model, tok_rank, bias=False)
        self.tok_u = nn.Parameter(torch.randn(vocab, tok_rank) * 0.02)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        return self.W_out(h) @ self.tok_u.T


class _MockKASModel(nn.Module):
    def __init__(self, vocab: int = 64, d_model: int = 16):
        super().__init__()
        self.emb = nn.Embedding(vocab, d_model)
        self.head = _MockKASHead(vocab=vocab, d_model=d_model)

    def forward(self, ids: torch.Tensor, valid: torch.Tensor | None = None) -> torch.Tensor:
        return self.head(self.emb(ids))


def test_enable_head_rows_and_team5_probe_support_untied_ke2_kas_head():
    torch.manual_seed(3)
    m = _MockKASModel(vocab=64, d_model=16)
    for p in m.parameters():
        p.requires_grad_(False)
    ids = [2, 7, 15]
    p = sft_g5.enable_head_rows(m, ids)
    assert p is m.head.tok_u
    x = torch.tensor([[1, 2, 7, 15, 3]])
    loss = m(x).sum()
    loss.backward()
    # Non-marker rows must have exact zero gradient; marker rows receive gradient.
    mask = torch.zeros(64, dtype=torch.bool)
    mask[ids] = True
    assert float(p.grad[~mask].abs().max()) == 0.0
    assert float(p.grad[mask].abs().sum()) > 0.0
    # Team 9 / keep_weights probe resolves vocab_size cleanly without `.out_features`.
    probe_val = kw.team5_probe(m)
    assert isinstance(probe_val, float) and probe_val > 0.0
