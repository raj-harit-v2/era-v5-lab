"""The default-off --keep-weights-dir option of sft_job_v1.py, sft_g5.py and rl_job_v1.py (CPU, stand-ins, no model run).

    python -m pytest capstone/test_keep_weights_wiring.py -q
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import day_one_probe as probe  # noqa: E402
import keep_weights as kw  # noqa: E402
import rl_job_v1 as rl_job  # noqa: E402
import sft_g5  # noqa: E402
import sft_job_v1 as job  # noqa: E402

BASE = ["--g5-root", "g", "--run-folder", "r", "--tokenizer", "t", "--byte-table", "b", "--heldout", "h", "--packs", "p",
        "--steps", "300", "--device", "cpu"]


def test_flag_needs_its_arm_and_the_arm_needs_the_flag(tmp_path):
    for extra in (["--keep-weights-dir", str(tmp_path)], ["--keep-arm", "a2"]):
        with pytest.raises(SystemExit) as e:
            job.parse_args([*BASE, *extra, "--out", str(tmp_path)])
        assert e.value.code == 2
    a = job.parse_args([*BASE, "--keep-weights-dir", str(tmp_path), "--keep-arm", "a4", "--out", str(tmp_path)])
    assert a.keep_arm == "a4"
    assert job.parse_args([*BASE, "--out", str(tmp_path)]).keep_weights_dir is None
    assert sft_g5.parse_args(["--adapter-config", "c", "--train", "t", "--eval", "e", "--method", "full", "--out", "o"]
                             ).keep_weights_dir is None


def _fake_job(tmp_path, monkeypatch, extra):
    import sft_slice_v1 as sl
    import make_adapter_config
    calls = []

    def fake_build(packs, tok, tab, max_tokens, out, dev_rows, check_hashes=True):
        out.mkdir(parents=True)
        for n in ("a2_train.jsonl", "a4_train.jsonl", "dev.jsonl"):
            (out / n).write_text("rows")
        return {"train_rows": 1}

    def fake_arm(out, arm, cmd, timeout=None):
        calls.append((arm, cmd))
        (out / f"sft_{arm}").mkdir(exist_ok=True)
        rep = {"log": [{}] * 7, "before": None if "--no-before" in cmd else {"forgetting": {"val/bpb": 2.0}},
               "after": {"forgetting": {"val/bpb": 2.01}}}
        (out / f"sft_{arm}" / "sft_report.json").write_text(json.dumps(rep))
        kept = {"kept_weights": {"run_dir": "K/g10-sft-a2", "step": 7, "manifest_sha256": "ab" * 32}} if "--keep-weights-dir" in cmd else {}
        return {"before": rep["before"], "after": rep["after"], **kept}

    monkeypatch.setattr(job.probe, "check_pins", lambda *a: {"checks": {}})
    monkeypatch.setattr(job, "check_run_and_inputs", lambda a: {"block_size": 2048})
    monkeypatch.setattr(job, "check_g5_sources", lambda a: {})
    monkeypatch.setattr(job.probe, "run_sft_arm", fake_arm)
    monkeypatch.setattr(sl, "build", fake_build)
    monkeypatch.setattr(make_adapter_config, "write_config", lambda out, *a: out)
    assert job.main([*BASE, *extra, "--out", str(tmp_path)]) == 0
    return calls


def test_only_the_kept_arm_gets_the_flag_and_summary_records_it(tmp_path, monkeypatch):
    calls = _fake_job(tmp_path, monkeypatch, ["--keep-weights-dir", str(tmp_path / "K"), "--keep-arm", "a2"])
    (a2, c2), (a4, c4) = calls
    assert c2[c2.index("--keep-run-id") + 1] == "g10-sft-a2" and c2[c2.index("--keep-weights-dir") + 1] == str(tmp_path / "K")
    assert "--keep-weights-dir" not in c4
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["kept_weights"] == {"sft_a2": {"run_dir": "K/g10-sft-a2", "step": 7, "manifest_sha256": "ab" * 32}}


def test_without_the_flag_nothing_is_added(tmp_path, monkeypatch):
    calls = _fake_job(tmp_path, monkeypatch, [])
    assert all("--keep-weights-dir" not in c for _, c in calls)
    assert json.loads((tmp_path / "summary.json").read_text()) == {"ok": True, "steps": 5, "failed_steps": []}


def test_run_sft_arm_keeps_the_record_but_still_deletes_weights_and_generations(tmp_path):
    arm = tmp_path / "sft_a2"
    arm.mkdir()
    prog = ("import json,pathlib;p=pathlib.Path(%r);(p/'model.safetensors').write_bytes(b'w');(p/'generations.jsonl').write_text('g');"
            "(p/'sft_report.json').write_text(json.dumps({'before':{},'after':{},'kept_weights':{'step':3}}))" % str(arm))
    res = probe.run_sft_arm(tmp_path, "a2", [sys.executable, "-c", prog])
    assert res["kept_weights"] == {"step": 3}
    assert not (arm / "model.safetensors").exists() and not (arm / "generations.jsonl").exists()


class StandInLM(torch.nn.Module):
    """Has what Team 5's LanguageModel has that keep_weights uses: .head and forward(ids, valid)."""

    def __init__(self):
        super().__init__()
        torch.manual_seed(0)
        self.emb = torch.nn.Embedding(11, 8)
        self.body = torch.nn.Linear(8, 8)
        self.head = torch.nn.Linear(8, 11)

    def forward(self, ids, valid):
        return self.head(torch.relu(self.body(self.emb(ids))))


def test_rl_final_weights_lay_the_trainable_tensors_over_the_start_weights(tmp_path, monkeypatch):
    monkeypatch.setenv("V5_EVENTS_DIR", str(tmp_path / "ev"))
    (tmp_path / "_work").mkdir()
    m = StandInLM()
    new = {"body.weight": torch.full((8, 8), 0.25).to(torch.bfloat16)}
    torch.save(new, tmp_path / "_work" / "rl_trainable.pt")
    a = argparse.Namespace(keep_weights_dir=tmp_path / "K")
    info = rl_job.keep_final_weights(a, tmp_path, None, 12, model=m)
    assert info["step"] == 12 and info["trainable_tensors"] == 1 and Path(info["run_dir"]).name == "g10-rl-final"
    from ckpt.ckpt import export_safetensors
    from safetensors.torch import load_file
    out = tmp_path / "m.safetensors"
    export_safetensors(info["run_dir"], StandInLM, kw.team5_probe, str(out), step=12)
    got = load_file(str(out))
    assert torch.equal(got["body.weight"], torch.full((8, 8), 0.25)) and set(got) == set(StandInLM().state_dict())
    assert torch.equal(got["head.weight"], StandInLM().head.weight)  # untouched tensors keep the start weights
    torch.save({"nope.weight": torch.zeros(1)}, tmp_path / "_work" / "rl_trainable.pt")
    with pytest.raises(RuntimeError, match="without a place"):
        rl_job.keep_final_weights(a, tmp_path, None, 12, model=StandInLM())


def test_train_config_asks_for_trainable_weights_only_with_the_flag(tmp_path):
    ns = dict(seed=1, device="cpu", allow_fixture_smoke=False, rl_tasks=tmp_path / "t", updates=3, prompts_per_step=2, k=2,
              max_new=8, lr=1e-5, tr_epsilon=0.2, eval_k=1, reward_pool=1, min_mixed=1, state_every=1, max_steps_this_call=0)
    import yaml
    plain = yaml.safe_load(rl_job.write_train_config(argparse.Namespace(**ns), tmp_path, None, None, 0.0, 4).read_text())
    kept = yaml.safe_load(rl_job.write_train_config(argparse.Namespace(**ns, keep_weights_dir=tmp_path / "K"), tmp_path, None,
                                                    None, 0.0, 4).read_text())
    assert "save_trainable" not in plain["train"]
    assert kept["train"]["save_trainable"] == str(tmp_path / "_work" / "rl_trainable.pt")
    assert {k: v for k, v in kept["train"].items() if k != "save_trainable"} == plain["train"]
