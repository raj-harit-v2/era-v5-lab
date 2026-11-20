"""LoRA and DT kept arms on Team 5's real LanguageModel class (week2/model.py, the t2 arm shrunk to width 64, CPU, stand-in byte table).

    python -m pytest capstone/test_keep_weights_real_model.py -q

The arm is wrapped by sft_g5.apply_method (the job's own code), nudged, merged or baked with the job's own functions, saved with
keep_weights and exported with Team 7's export_safetensors; the export loads strictly into a fresh LanguageModel and gives the same logits.
Only loop dispatch exists in Team 5's model (week2/config.py rejects anything else), so that is what is covered.
"""
from __future__ import annotations

import copy
import sys
import types
from pathlib import Path

import pytest
from pytest import fixture  # bare decorator: pr-guard reads a dotted decorator as an e-mail address

parametrize = pytest.mark.parametrize
torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
HERE = Path(__file__).resolve().parent
TEAMS = HERE.parents[1]
H5 = TEAMS / "05-architecture" / "harness"
sys.path[:0] = [str(HERE), str(H5)]
import keep_weights as kw  # noqa: E402
from week2 import config as C  # noqa: E402
from week2.model import LanguageModel  # noqa: E402
import sft_g5  # noqa: E402


@fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("V5_EVENTS_DIR", str(tmp_path / "ev"))
    torch.use_deterministic_algorithms(True)
    m = copy.deepcopy(C.load_runtime(str(TEAMS / "05-architecture" / "configs" / "arms" / "t2.yaml"))["model"])
    m.update(vocab_size=256, block_size=32, n_layer=2, n_head=2, n_kv_head=1, n_embd=64)
    m["moe"] = dict(m["moe"], num_experts=4, top_k=2, num_shared=1, ffn_hidden=32)
    rows = torch.randint(0, 255, (256, 32), generator=torch.Generator().manual_seed(1)).to(torch.uint8)
    lengths = torch.randint(1, 5, (256,), generator=torch.Generator().manual_seed(2))

    def make():
        torch.manual_seed(0)
        return LanguageModel(m, rows, lengths)
    return make


@parametrize("method", ["lora", "dt"])
def test_adapter_arm_is_saved_plain_and_reloads_strictly(method, factory, tmp_path):
    from ckpt.ckpt import export_safetensors
    from safetensors.torch import load_file
    ids = torch.randint(0, 256, (2, 16), generator=torch.Generator().manual_seed(5))
    valid = torch.ones_like(ids, dtype=torch.bool)

    def logits(x):
        x.eval()
        with torch.no_grad():
            return x(ids, valid)
    model = factory()
    base_keys = set(model.state_dict())
    args = types.SimpleNamespace(seed=1, lora_r=4, lora_alpha=8.0, dt_targets="g5_mlp", dt_alpha_start=100.0, dt_alpha_end=1000.0,
                                 steps=20, dt_lambda=0.0, dt_eta=0.0)
    info = sft_g5.apply_method(model, method, args)
    assert (info.get("wrapped_modules") or info.get("masked_layers")) > 0
    gen = torch.Generator().manual_seed(9)
    with torch.no_grad():
        for p in model.parameters():
            if p.requires_grad:
                p.add_(0.05 * torch.randn(p.shape, generator=gen))
    wrapped = logits(model).clone()
    with pytest.raises(ValueError, match="not plain weights"):
        kw.save_run_folder(model, tmp_path / "unmerged", "x", step=1, probe_fn=kw.team5_probe)
    sft_g5.bench.merge_lora(model) if method == "lora" else sft_g5.dtmask.bake(model)
    assert float((wrapped - logits(model)).abs().max()) <= 1e-5
    assert set(model.state_dict()) == base_keys
    info = kw.save_run_folder(model, tmp_path / "keep", f"g10-{method}", step=3, probe_fn=kw.team5_probe)
    out = tmp_path / "m.safetensors"
    export_safetensors(info["run_dir"], factory, kw.team5_probe, str(out), step=3)
    fresh = factory()
    fresh.load_state_dict(load_file(str(out)), strict=True)
    assert float((logits(fresh) - logits(model)).abs().max()) == 0.0
