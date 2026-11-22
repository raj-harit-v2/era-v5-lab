"""Tests of capstone/keep_weights.py on Team 5's tiny MoE (CPU, no network, synthetic data).

    python -m pytest capstone/test_keep_weights.py -q

2a export_safetensors succeeds; 2b the exported weights load strictly into a fresh model and give the same logits;
2c Team 9's run_lab_ckpt.py reads the folder (pointer, manifest, export, smoke score on a synthetic stream);
2d one flipped byte in a saved shard is refused by Team 7's integrity check.
Not covered here: scoring on benchmark data (lm_eval_lab:team5 needs tokenizer, byte table, HF cache not on disk).
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest
from pytest import fixture  # bare decorator: pr-guard reads a dotted decorator as an e-mail address

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
HERE = Path(__file__).resolve().parent
TEAMS = HERE.parents[1]
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("run_lab_ckpt", TEAMS / "09-evaluation" / "harness_lab" / "run_lab_ckpt.py")
rl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rl)  # puts Team 7 and Team 5 harness folders on sys.path
if rl.version_key(torch.__version__) < rl.version_key(rl.MIN_TORCH):
    pytest.skip(f"run_lab_ckpt.py needs torch {rl.MIN_TORCH}", allow_module_level=True)
import keep_weights as kw  # noqa: E402

STEPS = 20


@fixture
def saved(tmp_path, monkeypatch):
    # Team 5's harness/train.py (reached through run_lab_ckpt.tiny_pieces) imports the pip package kronecker_embeddings
    pytest.importorskip("kronecker_embeddings", reason="Team 5's harness/train.py needs the pip package kronecker_embeddings")
    monkeypatch.setenv("V5_EVENTS_DIR", str(tmp_path / "events"))
    sys.modules.pop("train", None)  # rl-loop/train.py may be imported by another test file: Team 5's must win here
    monkeypatch.syspath_prepend(str(rl.HARNESS05))
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    cfg = rl.tiny_cfg(rl.CONFIGS05 / "config_v0.yaml", rl.CONFIGS05 / "small" / "tiny_moe.yaml", STEPS)
    factory, probe = rl.tiny_pieces(cfg)
    model = factory()
    with torch.no_grad():  # make the saved model differ from the factory's seeded one
        for p in model.parameters():
            p.add_(0.01 * torch.randn_like(p, generator=torch.Generator().manual_seed(3)))
    info = kw.save_run_folder(model, tmp_path / "keep", "kw-tiny", step=7, probe_fn=probe, tokens=99)
    yield {"model": model, "factory": factory, "probe": probe, "cfg": cfg, "info": info, "tmp": tmp_path}
    sys.modules.pop("train", None)  # Team 5's harness/train.py must not shadow rl-loop/train.py in later test files


def test_2a_export_safetensors_succeeds_on_the_folder(saved):
    from ckpt.ckpt import export_safetensors
    out = saved["tmp"] / "m.safetensors"
    got = export_safetensors(saved["info"]["run_dir"], saved["factory"], saved["probe"], str(out), step=7)
    assert got["step"] == 7 and out.is_file()
    run = Path(saved["info"]["run_dir"])
    assert (run / "latest.json").is_file() and (run / "commits.jsonl").is_file()
    assert (run / saved["info"]["manifest_path"].split("/", 1)[1]).is_file()
    assert len(saved["info"]["manifest_sha256"]) == 64


def test_2b_exported_weights_load_strictly_and_logits_match(saved):
    from ckpt.ckpt import export_safetensors
    from safetensors.torch import load_file
    out = saved["tmp"] / "m.safetensors"
    export_safetensors(saved["info"]["run_dir"], saved["factory"], saved["probe"], str(out), step=7)
    fresh = saved["factory"]()
    fresh.load_state_dict(load_file(str(out)), strict=True)
    assert set(fresh.state_dict()) == set(saved["model"].state_dict())
    from train import stream_for
    batch = stream_for(saved["cfg"], 5)[:2]
    saved["model"].eval(); fresh.eval()
    with torch.no_grad():
        a, _ = saved["model"](batch)
        b, _ = fresh(batch)
    assert float((a - b).abs().max()) <= 1e-6
    assert float((a - saved["factory"]().eval()(batch)[0]).abs().max()) > 1e-6  # the weights are not the seeded ones


def test_2c_team9_reader_runs_on_the_folder(saved, capsys):
    out = saved["tmp"] / "o.json"
    assert rl.main(["--run-dir", saved["info"]["run_dir"], "--steps", str(STEPS), "--out", str(out)]) == 0
    (rec, *_) = json.loads(out.read_text(encoding="utf-8"))["records"]
    assert rec["model_revision"] == saved["info"]["manifest_sha256"]
    assert rec["checkpoint"]["step"] == 7 and rec["checkpoint"]["run"] == "kw-tiny"
    assert "probe loss bits equal the saved ones" in capsys.readouterr().out


def test_2d_a_flipped_byte_is_refused(saved):
    from ckpt.ckpt import IntegrityError, export_safetensors
    step_dir = next((Path(saved["info"]["run_dir"]) / "main").iterdir())
    shard = next(p for p in sorted(step_dir.iterdir()) if p.suffix == ".distcp")
    raw = bytearray(shard.read_bytes())
    raw[len(raw) // 2] ^= 0xFF
    shard.write_bytes(bytes(raw))
    with pytest.raises(IntegrityError):
        export_safetensors(saved["info"]["run_dir"], saved["factory"], saved["probe"], str(saved["tmp"] / "x.st"), step=7)


def test_adapter_keys_are_refused(saved):
    m = saved["factory"]()
    m.register_parameter("lora_A", torch.nn.Parameter(torch.zeros(1)))
    with pytest.raises(ValueError, match="not plain weights"):
        kw.save_run_folder(m, saved["tmp"] / "k2", "bad", step=1, probe_fn=saved["probe"])


def test_probe_constants_equal_team9s():
    src = (TEAMS / "09-evaluation" / "harness_lab" / "lm_eval_lab.py").read_text(encoding="utf-8")
    m = re.search(r"^PROBE_SHAPE, PROBE_SEED = (\(.*?\)), (\d+)$", src, re.M)
    assert m and (eval(m.group(1)), int(m.group(2))) == (kw.PROBE_SHAPE, kw.PROBE_SEED)


def test_only_weights_are_saved_and_grad_flags_come_back(saved):
    """No optimizer moments (they would triple the bytes) and the model's requires_grad flags are as they were."""
    step_dir = next((Path(saved["info"]["run_dir"]) / "main").iterdir())
    size = sum(p.stat().st_size for p in step_dir.glob("*.distcp"))
    weights = sum(p.numel() * p.element_size() for p in saved["model"].state_dict().values())
    assert weights <= size < 1.2 * weights
    assert all(p.requires_grad for p in saved["model"].parameters())
