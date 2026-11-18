"""run_lab_ckpt.py --scorer <module>:<function>, on a checkpoint saved through Team 7's Checkpointer (CPU, no network).

Needs torch >= 2.14.1 and safetensors, as run_lab_ckpt.py does; skipped otherwise.

    python -m pytest teams/09-evaluation/harness_lab/tests/test_run_lab_ckpt_scorer.py -q
"""
import hashlib
import importlib.util
import json
import sys
import textwrap
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("run_lab_ckpt", HERE.parent / "run_lab_ckpt.py")
rl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rl)   # puts Team 7's folders on sys.path
if rl.version_key(torch.__version__) < rl.version_key(rl.MIN_TORCH):  # as numbers: "2.9.0" < "2.14.1" (#444)
    pytest.skip(f"run_lab_ckpt.py needs torch {rl.MIN_TORCH}", allow_module_level=True)

STUB = textwrap.dedent('''
    import torch

    class Tiny(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.lin = torch.nn.Linear(4, 4)

        def forward(self, x):
            return self.lin(x)

    def probe(model):
        with torch.no_grad():
            return float(model(torch.ones(2, 4)).square().mean())

    class Scorer:
        name = "stub"

        def __init__(self, argv):
            self.argv = argv

        def check(self, manifest):
            if "--refuse" in self.argv:
                raise SystemExit(f"refused step {manifest['step']}")

        def factory(self):
            torch.manual_seed(0)
            return Tiny()

        def probe(self, model):
            return probe(model)

        def score(self, model, device):
            return [{"task": "stub_task", "metric": "acc", "filter": "none", "primary": True,
                     "value": round(100 * probe(model), 2) % 100, "stderr": None, "n_items": 2,
                     "item_set": "limit:2", "num_fewshot": 0, "decoding": "loglikelihood", "notes": self.argv,
                     "seed": {"random": 7, "numpy": 7, "torch": 7, "fewshot": 7},
                     "harness": {"name": "stub", "version": "1"}, "dtype": "float32"}]

    def make(argv):
        return Scorer(argv)
''')


@pytest.fixture
def store(tmp_path, monkeypatch):
    """One commit at step 10 in Team 7's layout, and the stub scorer module on sys.path."""
    (tmp_path / "stub_scorer.py").write_text(STUB, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("V5_EVENTS_DIR", str(tmp_path / "events"))
    import stub_scorer
    from ckpt.ckpt import Checkpointer
    from trainer.tiny import SyntheticLoader

    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    model = stub_scorer.Scorer([]).factory()
    optim = torch.optim.AdamW(model.parameters(), lr=1e-3)
    ck = Checkpointer("run-s", str(tmp_path / "local"), str(tmp_path / "store"), seed=0)
    assert ck.save(10, model, optim, SyntheticLoader(0, 2, 0, 1), stub_scorer.probe, tokens=40) and ck.wait()
    yield tmp_path / "store" / "run-s"
    sys.modules.pop("stub_scorer", None)


def test_a_module_scorer_gets_the_unknown_arguments_and_sets_its_fields(store, tmp_path, capsys):
    out = tmp_path / "out.json"
    assert rl.main(["--run-dir", str(store), "--step", "10", "--scorer", "stub_scorer:make", "--out", str(out),
                    "--tier", "A", "--flag", "x"]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    (rec,) = doc["records"]
    manifest = store / "main" / "step_00000010-e1" / "MANIFEST.json"
    assert rec["model_revision"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert rec["checkpoint"] == {"run": "run-s", "branch": "main", "step": 10, "epoch": 1, "tokens_seen": 40,
                                 "path": f"{store.as_posix()}/main/step_00000010-e1"}
    assert rec["notes"] == ["--tier", "A", "--flag", "x"]
    assert (rec["harness"]["name"], rec["seed"]["random"], rec["backend"]) == ("stub", 7, "lab")
    assert list(rec)[-4:] == ["seed", "harness", "hardware", "run_date"]
    printed = capsys.readouterr().out
    assert "probe loss bits equal the saved ones" in printed and "TIME export" in printed


def test_a_scorer_can_refuse_a_checkpoint(store, tmp_path):
    with pytest.raises(SystemExit, match="refused step 10"):
        rl.main(["--run-dir", str(store), "--scorer", "stub_scorer:make", "--out", str(tmp_path / "o.json"),
                 "--refuse"])
    assert not (tmp_path / "o.json").exists()


def test_smoke_refuses_unknown_arguments_and_cuda(store, tmp_path):
    for extra in (["--tier", "A"], ["--device", "cuda"]):
        with pytest.raises(SystemExit) as e:
            rl.main(["--run-dir", str(store), "--out", str(tmp_path / "o.json"), *extra])
        assert e.value.code == 2


# ---- --team5-run: a finished Team 5 train_week2.py run folder (dry run 1) -------------------------------------------

@pytest.fixture
def team5_run(tmp_path, monkeypatch):
    """A run folder as train_week2.py leaves it: checkpoint.pt (model, optimizer and RNG state), manifest.json with
    artifacts.tokenizer_sha256, and summary.json with status COMPLETED and final_model_sha256."""
    import numpy as np

    (tmp_path / "stub_scorer.py").write_text(STUB, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    import stub_scorer
    from train_week2 import model_hash

    model = stub_scorer.Scorer([]).factory()
    optim = torch.optim.AdamW(model.parameters(), lr=1e-3)
    model(torch.ones(2, 4)).sum().backward()
    optim.step()
    run = tmp_path / "dryrun1-7"
    run.mkdir()
    torch.save({"model": model.state_dict(), "optimizer": optim.state_dict(), "numpy_rng": np.random.get_state(),
                "step": 7}, run / "checkpoint.pt")
    (run / "manifest.json").write_text(json.dumps({"artifacts": {"tokenizer_sha256": "e6b9"}, "config": {"model": {}}}),
                                       encoding="utf-8")
    (run / "summary.json").write_text(json.dumps({"status": "COMPLETED", "steps": 7,
                                                  "final_model_sha256": model_hash(model)}), encoding="utf-8")
    yield run
    sys.modules.pop("stub_scorer", None)


def test_team5_run_is_scored_with_its_weights_hash_as_revision(team5_run, tmp_path, capsys):
    out = tmp_path / "out.json"
    assert rl.main(["--team5-run", str(team5_run), "--scorer", "stub_scorer:make", "--out", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    (rec,) = doc["records"]
    summary = json.loads((team5_run / "summary.json").read_text(encoding="utf-8"))
    assert rec["model_revision"] == summary["final_model_sha256"]
    assert rec["model"] == "lab:dryrun1-7"
    assert rec["checkpoint"] == {"run": "dryrun1-7", "branch": "main", "step": 7, "epoch": None, "tokens_seen": None,
                                 "path": f"{team5_run.as_posix()}/checkpoint.pt"}
    (src,) = doc["sources"]
    assert src["path"] == f"{team5_run.as_posix()}/manifest.json" and src["schema_version"] == rl.TEAM5_SOURCE
    assert src["sha256"] == hashlib.sha256((team5_run / "manifest.json").read_bytes()).hexdigest()
    printed = capsys.readouterr().out
    assert "weights hash equals summary.json final_model_sha256" in printed and "TIME export" in printed


def test_team5_run_with_other_weights_is_refused(team5_run, tmp_path):
    summary = json.loads((team5_run / "summary.json").read_text(encoding="utf-8"))
    summary["final_model_sha256"] = "0" * 64
    (team5_run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(SystemExit, match="differs from summary.json final_model_sha256"):
        rl.main(["--team5-run", str(team5_run), "--scorer", "stub_scorer:make", "--out", str(tmp_path / "o.json")])
    assert not (tmp_path / "o.json").exists()


@pytest.mark.parametrize("status", ["INCOMPLETE_NOT_A_RESULT", "SMOKE"])
def test_team5_run_that_did_not_complete_is_refused(team5_run, tmp_path, status):
    summary = json.loads((team5_run / "summary.json").read_text(encoding="utf-8"))
    summary["status"] = status
    (team5_run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(SystemExit, match="only a COMPLETED run is scored"):
        rl.main(["--team5-run", str(team5_run), "--scorer", "stub_scorer:make", "--out", str(tmp_path / "o.json")])


def test_team5_run_refuses_smoke_and_step(team5_run, tmp_path):
    for extra in (["--scorer", "smoke"], ["--scorer", "stub_scorer:make", "--step", "7"]):
        with pytest.raises(SystemExit) as e:
            rl.main(["--team5-run", str(team5_run), "--out", str(tmp_path / "o.json"), *extra])
        assert e.value.code == 2


def test_run_dir_and_team5_run_are_exclusive(team5_run, tmp_path):
    with pytest.raises(SystemExit) as e:
        rl.main(["--team5-run", str(team5_run), "--run-dir", str(team5_run), "--scorer", "stub_scorer:make"])
    assert e.value.code == 2
