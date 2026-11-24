"""run_lab_ckpt.py --team5-run on a real Team 5 LanguageModel (CPU, no network, a few seconds).

test_run_lab_ckpt_scorer.py checks the --team5-run path with a stub model. Here the model is Team 5's own
week2.model.LanguageModel (KE2 embedding, MoE blocks, dense head), built from the small fixture of Team 5's tests,
trained for a few steps with Team 5's optimizers, and saved in train_week2.py's checkpoint.pt layout. The scorer loads
it strictly, checks Team 5's weights hash and reads ``model.head.out_features``, as lm_eval_lab.py does. If Team 5 changes
the head (the KE2/KAS head, #691), this is the test to run on their branch.

    python -m pytest teams/09-evaluation/harness_lab/tests/test_run_lab_ckpt_team5_model.py -q

Needs torch >= 2.14.1, safetensors and tokenizers, as Team 5's harness does; skipped otherwise.
"""
import importlib.util
import json
import sys
import textwrap
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
pytest.importorskip("tokenizers")
HERE = Path(__file__).resolve().parent
TEAM05_TESTS = HERE.parents[2] / "05-architecture" / "tests"
_spec = importlib.util.spec_from_file_location("run_lab_ckpt", HERE.parent / "run_lab_ckpt.py")
rl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rl)   # puts Team 5's harness and Team 7's folders on sys.path
if rl.version_key(torch.__version__) < rl.version_key(rl.MIN_TORCH):
    pytest.skip(f"run_lab_ckpt.py needs torch {rl.MIN_TORCH}", allow_module_level=True)

SCORER = textwrap.dedent('''
    """A scorer for the small Team 5 model: the contract of run_lab_ckpt.py, a probe batch instead of lm-eval."""
    import torch
    from test_week2_model import fixture
    from week2.model import LanguageModel

    LAYERS = {"n_layer": None}   # a test sets this to build the model with another depth

    def config():
        c, rows, lengths = fixture()
        if LAYERS["n_layer"]:
            c["model"]["n_layer"] = LAYERS["n_layer"]
        return c["model"], rows, lengths

    class Scorer:
        name = "team5_small"

        def __init__(self, argv):
            self.argv = argv

        def check(self, manifest):
            pass

        def factory(self):
            m, rows, lengths = config()
            torch.manual_seed(0)
            return LanguageModel(m, rows, lengths)

        def probe(self, model):
            return 0.0

        def score(self, model, device):
            vocab = model.head.out_features   # what lm_eval_lab.py reads from the head
            ids = torch.arange(16).reshape(2, 8) % vocab
            model.eval()
            with torch.no_grad():
                logits = model(ids, torch.ones_like(ids, dtype=torch.bool))
            loss = torch.nn.functional.cross_entropy(logits[:, :-1].reshape(-1, vocab), ids[:, 1:].reshape(-1)).item()
            return [{"task": "probe_batch", "metric": "loss", "filter": "none", "primary": True,
                     "value": round(loss, 6), "stderr": None, "n_items": 16, "item_set": "probe",
                     "num_fewshot": 0, "decoding": "loglikelihood", "notes": [],
                     "seed": {"random": 0, "numpy": 0, "torch": 0, "fewshot": 0},
                     "harness": {"name": "team5_small", "version": "1"}, "dtype": "float32"}]

    def make(argv):
        return Scorer(argv)
''')


def probe_loss(model, vocab):
    ids = torch.arange(16).reshape(2, 8) % vocab
    model.eval()
    with torch.no_grad():
        logits = model(ids, torch.ones_like(ids, dtype=torch.bool))
    return round(torch.nn.functional.cross_entropy(logits[:, :-1].reshape(-1, vocab), ids[:, 1:].reshape(-1)).item(), 6)


@pytest.fixture
def small(tmp_path, monkeypatch):
    """(scorer module, trained model, run folder) for a few real optimizer steps on the small Team 5 model."""
    import numpy as np

    (tmp_path / "team5_small.py").write_text(SCORER, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.syspath_prepend(str(TEAM05_TESTS))
    import team5_small
    from train_week2 import model_hash
    from week2.optim import build_optimizer

    from test_week2_model import fixture

    c, _, _ = fixture()
    model = team5_small.Scorer([]).factory()
    fresh = probe_loss(model, 31)
    opt = build_optimizer(model, c["optim"])
    ids = torch.arange(16).reshape(2, 8) % 31
    for _ in range(3):
        opt.zero_grad(set_to_none=True)
        logits = model(ids, torch.ones_like(ids, dtype=torch.bool))
        torch.nn.functional.cross_entropy(logits[:, :-1].reshape(-1, 31), ids[:, 1:].reshape(-1)).backward()
        opt.step()
    run = tmp_path / "dryrun-small-3"
    run.mkdir()
    torch.save({"model": model.state_dict(), "optimizer": opt.state_dict(),
                "numpy_rng": np.random.get_state(), "step": 3}, run / "checkpoint.pt")
    (run / "manifest.json").write_text(json.dumps({"artifacts": {"tokenizer_sha256": "e6b9"},
                                                   "config": {"model": c["model"]}}), encoding="utf-8")
    (run / "summary.json").write_text(json.dumps({"status": "COMPLETED", "steps": 3,
                                                  "final_model_sha256": model_hash(model)}), encoding="utf-8")
    yield team5_small, model, run, fresh
    sys.modules.pop("team5_small", None)


def test_the_trained_real_model_is_loaded_and_scored(small, tmp_path, capsys):
    team5_small, trained, run, fresh = small
    out = tmp_path / "out.json"
    assert rl.main(["--team5-run", str(run), "--scorer", "team5_small:make", "--out", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    (rec,) = doc["records"]
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    assert rec["model_revision"] == summary["final_model_sha256"] and rec["checkpoint"]["step"] == 3
    # the number comes from the loaded weights: the trained model's own loss, and not a fresh model's
    assert rec["value"] == probe_loss(trained, trained.head.out_features)
    assert rec["value"] != fresh
    assert "weights hash equals summary.json final_model_sha256" in capsys.readouterr().out


def test_a_checkpoint_of_another_shape_is_refused_and_nothing_is_written(small, tmp_path):
    team5_small, _, run, _ = small
    team5_small.LAYERS["n_layer"] = 3   # the scorer now builds a 3-layer model for a 2-layer checkpoint
    out = tmp_path / "o.json"
    with pytest.raises(RuntimeError, match="Missing key|Unexpected key|size mismatch"):
        rl.main(["--team5-run", str(run), "--scorer", "team5_small:make", "--out", str(out)])
    assert not out.exists()


def test_the_head_the_scorer_reads_is_the_models_output_layer(small):
    """lm_eval_lab.py reads model.head.out_features (the vocabulary). A head without that attribute fails here first."""
    team5_small, trained, _, _ = small
    m, _, _ = team5_small.config()
    assert trained.head.out_features == m["vocab_size"] == 31
