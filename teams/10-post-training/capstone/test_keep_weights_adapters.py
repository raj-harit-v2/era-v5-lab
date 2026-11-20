"""keep_weights.py on adapter arms: what is saved is the plain, merged model (CPU, a tiny stand-in module with Team 5's
child names; the merge and bake functions are the ones sft_g5.py calls, no new merge math).

    python -m pytest capstone/test_keep_weights_adapters.py -q

The real Team 5 LanguageModel class is covered in test_keep_weights_real_model.py. Full fine-tuning merges nothing and is the same code
path as the tiny-MoE test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest import fixture  # bare decorator: pr-guard reads a dotted decorator as an e-mail address

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
nn = torch.nn
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import keep_weights as kw  # noqa: E402
import sft_g5  # noqa: E402,F401  (loads sft/bench/train.py and dt/mask.py as sft_g5 does)

bench, dtmask = sft_g5.bench, sft_g5.dtmask


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.q = nn.Linear(8, 8)
        self.gate = nn.Linear(8, 8)
        self.down = nn.Linear(8, 8)

    def forward(self, x):
        return x + self.down(torch.relu(self.gate(self.q(x))))


class Tiny(nn.Module):
    def __init__(self):
        super().__init__()
        torch.manual_seed(0)
        self.blocks = nn.ModuleList([Block() for _ in range(2)])
        self.head = nn.Linear(8, 5)

    def forward(self, x):
        for b in self.blocks:
            x = b(x)
        return self.head(x)


def probe(m) -> float:
    with torch.no_grad():
        return float(m.eval()(torch.ones(2, 8)).square().mean())


def _reload(tmp_path, model):
    from ckpt.ckpt import export_safetensors
    from safetensors.torch import load_file
    info = kw.save_run_folder(model, tmp_path / "keep", "arm", step=3, probe_fn=probe)
    out = tmp_path / "m.safetensors"
    export_safetensors(info["run_dir"], Tiny, probe, str(out), step=3)
    plain = Tiny()
    plain.load_state_dict(load_file(str(out)), strict=True)
    assert set(plain.state_dict()) == set(Tiny().state_dict())  # keys identical to the base model
    return plain.eval()


@fixture(autouse=True)
def _events(tmp_path, monkeypatch):
    monkeypatch.setenv("V5_EVENTS_DIR", str(tmp_path / "ev"))
    torch.use_deterministic_algorithms(True)


def test_lora_arm_is_saved_merged_and_plain(tmp_path):
    m = Tiny()
    gen = torch.Generator().manual_seed(1)
    for b in m.blocks:
        b.q = bench.LoRALinear(b.q, 4, 8.0, gen)
        b.gate = bench.LoRALinear(b.gate, 4, 8.0, gen)
        torch.nn.init.normal_(b.q.lora_B, std=0.1)
        torch.nn.init.normal_(b.gate.lora_B, std=0.1)
    m.eval()
    x = torch.randn(3, 8, generator=torch.Generator().manual_seed(2))
    with torch.no_grad():
        want = m(x)
    with pytest.raises(ValueError, match="not plain weights"):
        kw.save_run_folder(m, tmp_path / "k0", "unmerged", step=1, probe_fn=probe)
    bench.merge_lora(m)
    plain = _reload(tmp_path, m)
    with torch.no_grad():
        assert float((plain(x) - want).abs().max()) <= 1e-5


def test_dt_arm_is_saved_baked_and_plain(tmp_path):
    m = Tiny()
    dtmask.convert(m, ("gate", "down"), 100.0, 1000.0, 10, seed=0)
    m.eval()
    x = torch.randn(3, 8, generator=torch.Generator().manual_seed(2))
    with pytest.raises(ValueError, match="not plain weights"):  # an unbaked DT model has no mask-named key: the class check catches it
        kw.save_run_folder(m, tmp_path / "k0", "unbaked", step=1, probe_fn=probe)
    with torch.no_grad():
        dtmask.bake(m)
        want = m(x)
    plain = _reload(tmp_path, m)
    with torch.no_grad():
        assert float((plain(x) - want).abs().max()) <= 1e-5
