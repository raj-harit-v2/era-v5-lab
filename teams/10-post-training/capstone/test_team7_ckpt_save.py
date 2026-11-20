"""Offline tests for Team 7 Checkpointer.save + export_safetensors wiring in capstone/sft_g5.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import torch
import torch.nn as nn
from safetensors.torch import load_file

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sft_g5  # noqa: E402


class TinyLM(nn.Module):
    def __init__(self, vocab: int = 32, dim: int = 16):
        super().__init__()
        self.emb = nn.Embedding(vocab, dim)
        self.proj = nn.Linear(dim, dim, bias=False)
        self.head = nn.Linear(dim, vocab, bias=False)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        return self.head(torch.tanh(self.proj(self.emb(ids))))


def _make_probe(ids: torch.Tensor):
    def probe_fn(m: nn.Module) -> torch.Tensor:
        with torch.no_grad():
            logits = m(ids).float()
            return nn.functional.cross_entropy(logits[:, :-1].reshape(-1, logits.size(-1)),
                                               ids[:, 1:].reshape(-1))
    return probe_fn


def test_save_and_export_team7_full_ft_with_live_optim(tmp_path):
    torch.manual_seed(7)
    model = TinyLM()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    ids = torch.tensor([[1, 5, 9, 2, 7, 3, 8, 4]])
    loss = nn.functional.cross_entropy(model(ids)[:, :-1].reshape(-1, 32), ids[:, 1:].reshape(-1))
    loss.backward()
    opt.step()
    model.eval()

    export_path = tmp_path / "exported" / "model.safetensors"
    info = sft_g5.save_and_export_team7(
        model,
        opt,
        model_factory=lambda: TinyLM().eval(),
        probe_fn=_make_probe(ids),
        step=12,
        tokens=96,
        run_id="g10-sft-test-full",
        local_root=tmp_path / "local",
        remote_root=tmp_path / "remote",
        export_path=export_path,
        seed=1,
        reason="sft_full",
    )

    assert info["step"] == 12
    assert info["used_live_optim"] is True
    assert len(info["export_sha256"]) == 64
    assert export_path.is_file()
    latest = json.loads((tmp_path / "remote" / "g10-sft-test-full" / "latest.json").read_text(encoding="utf-8"))
    assert latest["step"] == 12
    fresh = TinyLM().eval()
    fresh.load_state_dict(load_file(str(export_path)), strict=True)
    with torch.no_grad():
        assert float((fresh(ids) - model(ids)).abs().max()) == 0.0


def test_save_and_export_team7_handles_post_bake_mismatched_optim(tmp_path):
    torch.manual_seed(11)
    model = TinyLM().eval()
    # Simulate an optimizer that held only temporary DT/LoRA params before bake/merge replaced them.
    stale_param = nn.Parameter(torch.zeros(4, 4))
    stale_opt = torch.optim.AdamW([stale_param], lr=1e-3)
    ids = torch.tensor([[2, 4, 6, 8, 10, 12]])

    export_path = tmp_path / "exported_dt.safetensors"
    info = sft_g5.save_and_export_team7(
        model,
        stale_opt,
        model_factory=lambda: TinyLM().eval(),
        probe_fn=_make_probe(ids),
        step=5,
        tokens=40,
        run_id="g10-sft-test-dt",
        local_root=tmp_path / "local",
        remote_root=tmp_path / "remote",
        export_path=export_path,
        seed=1,
        reason="sft_dt",
    )

    assert info["step"] == 5
    assert info["used_live_optim"] is False
    fresh = TinyLM().eval()
    fresh.load_state_dict(load_file(str(export_path)), strict=True)
    with torch.no_grad():
        assert float((fresh(ids) - model(ids)).abs().max()) == 0.0


def test_parse_args_team7_flags_default_off():
    args = sft_g5.parse_args([
        "--adapter-config", "a.yaml", "--train", "tr.jsonl", "--eval", "ev.jsonl",
        "--method", "full", "--out", "out",
    ])
    assert args.team7_ckpt_remote is None
    assert args.team7_run_id is None
    assert args.team7_local_root is None
    assert args.team7_export_path is None
