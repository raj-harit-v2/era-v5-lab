"""CPU-only regression tests for G6's opt-in full-model compile mode."""
from pathlib import Path
from unittest.mock import patch

import pytest
import torch

from models.config import load_config
from perfkit.bench import select_compile_model

BASE = Path(__file__).resolve().parents[1] / "configs" / "base.yaml"


def test_compile_config_is_explicit_and_default_is_eager():
    cfg = load_config(BASE)
    assert cfg["run"]["compile"] is False
    assert cfg["run"]["compile_mode"] == "default"
    mode_cfg = load_config(BASE, ["run.compile=true", "run.compile_mode=max-autotune-no-cudagraphs"])
    assert mode_cfg["run"]["compile_mode"] == "max-autotune-no-cudagraphs"


def test_eager_model_is_unchanged():
    core = torch.nn.Linear(4, 4)
    with patch("perfkit.bench.torch.compile") as compiler:
        assert select_compile_model(core, {"compile": False, "compile_mode": "default"}) is core
        compiler.assert_not_called()


def test_default_matches_preexisting_torch_compile_call():
    core = torch.nn.Linear(4, 4)
    with patch("perfkit.bench.torch.compile") as compiler:
        assert select_compile_model(core, {"compile": True, "compile_mode": "default"}) is compiler.return_value
        compiler.assert_called_once_with(core)


def test_max_autotune_no_cudagraphs_selects_requested_mode():
    core = torch.nn.Linear(4, 4)
    with patch("perfkit.bench.torch.compile") as compiler:
        assert select_compile_model(core, {"compile": True, "compile_mode": "max-autotune-no-cudagraphs"}) is compiler.return_value
        compiler.assert_called_once_with(core, mode="max-autotune-no-cudagraphs")


@pytest.mark.parametrize("enabled", [True, False])
def test_unknown_mode_is_rejected(enabled):
    with pytest.raises(ValueError, match="run.compile_mode"):
        select_compile_model(torch.nn.Linear(2, 2), {"compile": enabled, "compile_mode": "bad-mode"})
