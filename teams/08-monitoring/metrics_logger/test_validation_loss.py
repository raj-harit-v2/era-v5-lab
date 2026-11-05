"""Tests for validation_loss in metrics_writer.py.

    cd teams/08-monitoring/metrics_logger && python -m pytest test_validation_loss.py -q
"""
import json
import math
import sys
from contextlib import nullcontext
from pathlib import Path

import pytest
import torch

from metrics_writer import MetricsWriter, validation_loss

G5_HARNESS = Path(__file__).resolve().parents[2] / "05-architecture" / "harness"


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("nats, tokens, loss", [
    (1200.0, 400, 3.0),
    (torch.tensor(50.0, dtype=torch.float64), torch.tensor(20), 2.5),
    (0.0, 10, 0.0),
])
def test_mean_nats_per_token(nats, tokens, loss):
    assert validation_loss(nats, tokens) == pytest.approx(loss)


@pytest.mark.parametrize("nats, tokens", [
    (None, 10), (10.0, None),                      # missing
    (10.0, 0), (10.0, -3), (10.0, 2.5), (10.0, True),   # not a positive whole token count
    (math.nan, 10), (math.inf, 10), (-1.0, 10), ("x", 10),
])
def test_cannot_be_told(nats, tokens):
    assert validation_loss(nats, tokens) is None


def test_writer_only_rows_with_validation_get_it(tmp_path):
    path = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(path), flush_every=1) as w:
        w.write(99, loss_ntp=3.1)
        w.write(100, loss_ntp=3.0, **{"val/nll_nats": 1160.0, "val/scored_tokens": 400, "val/bpb": 1.2})
        w.write(101, loss_ntp=2.9, validation_loss=2.75)               # passed by the trainer: kept
        w.write(102, validation_loss=2.6, **{"val/nll_nats": 1.0, "val/scored_tokens": 1})
    r = rows(path)
    assert "validation_loss" not in r[0]
    assert r[1]["validation_loss"] == pytest.approx(2.9)
    assert [x.get("validation_loss") for x in r[2:]] == [2.75, 2.6]
    assert all(not k.startswith("val/") for x in r for k in x)        # the inputs are used up, not stored


def test_inputs_are_not_reported_as_unknown(tmp_path, capsys):
    with MetricsWriter(str(tmp_path / "m.jsonl")) as w:
        w.write(1, **{"val/nll_nats": 10.0, "val/scored_tokens": 5})
    assert "val/nll_nats" not in capsys.readouterr().err


class _Windows:
    """The part of G5's DocumentWindows that evaluate() uses: windows of tokens, -100 where nothing is scored."""
    def __init__(self, seqs):
        self.windows = seqs
        self.window_slices = [None] * len(seqs)
        self.raw_bytes = sum(len(s) for s in seqs)        # 1 byte per token here

    def batch(self, idx, device):
        idx = list(idx)
        x = torch.tensor([self.windows[i] for i in idx], device=device)
        y = torch.roll(x, -1, dims=1)
        y[:, -1] = -100
        lengths = torch.tensor([[1] * len(self.windows[i]) for i in idx])
        return x, y, lengths


class _Model(torch.nn.Module):
    def __init__(self, vocab=11):
        super().__init__()
        torch.manual_seed(0)
        self.emb = torch.nn.Embedding(vocab, vocab)

    def forward(self, x, mask):
        return self.emb(x)


def test_matches_g5_evaluate():
    """validation_loss from the real G5 evaluate() result equals ln(val/perplexity), its own per-token mean."""
    if not (G5_HARNESS / "week2" / "evaluation.py").is_file():
        pytest.skip("G5 week2 harness not in this checkout")
    sys.path.insert(0, str(G5_HARNESS))
    try:
        from week2.evaluation import evaluate
    finally:
        sys.path.remove(str(G5_HARNESS))
    val = _Windows([[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 1, 2], [3, 3, 3, 3, 3, 3]])
    result = evaluate(_Model(), val, 2, "cpu", nullcontext)
    loss = validation_loss(result["val/nll_nats"], result["val/scored_tokens"])
    assert result["val/scored_tokens"] == 15
    assert loss == pytest.approx(math.log(result["val/perplexity"]), rel=1e-12)
