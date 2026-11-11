"""Tests for g5_adapter.py (train_week2.py --logger-factory -> MetricsWriter).

    cd teams/08-monitoring/metrics_logger && python -m pytest test_g5_adapter.py -q
"""
import importlib
import json
import math
from pathlib import Path

import pytest

from g5_adapter import G5_ONLY, make_writer


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def g5_train_row(step, norm_clipped=False):
    """The row train_week2.py builds for one optimizer step (same keys)."""
    return {"step": step, "train/ce_loss": 3.2, "loss_total": 3.5, "loss_ntp": 3.2, "loss_mtp": 3.0,
            "gradient_clipping_applied": norm_clipped, "train/scored_tokens": 1200, "train/input_positions": 1536,
            "train/utf8_bytes": 4800, "perf/step_ms": 250.0, "tokens_per_second": 6144.0, "gpu_alloc_gb": 12.5}


def g5_eval(nll=3000.0, tokens=1000):
    """The keys G5's week2.evaluation.evaluate() returns."""
    return {"val/nll_nats": nll, "val/scored_tokens": tokens, "val/bpb": 1.1, "val/perplexity": math.exp(nll / tokens)}


def test_factory_as_train_week2_calls_it(tmp_path):
    # train_week2.py: module,name=args.logger_factory.split(":",1); getattr(import_module(module),name)(args.out)
    module, name = "g5_adapter:make_writer".split(":", 1)
    writer = getattr(importlib.import_module(module), name)(tmp_path)
    writer.write(g5_train_row(1))
    writer.flush()
    writer.close()
    assert (tmp_path / "g8" / "metrics.jsonl").is_file()
    assert not (tmp_path / "metrics.jsonl").exists()  # G5's own file is not touched


def test_train_row_mapped(tmp_path, capsys):
    writer = make_writer(tmp_path)
    writer.write(g5_train_row(1, norm_clipped=True))
    writer.write(g5_train_row(2, norm_clipped=False))
    writer.close()
    r1, r2 = rows(tmp_path / "g8" / "metrics.jsonl")
    assert r1["step"] == 1 and r2["step"] == 2
    assert r1["loss_ntp"] == 3.2 and r1["loss_mtp"] == 3.0 and r1["tokens_per_second"] == 6144.0
    assert r1["gpu_alloc_gib"] == 12.5 and "gpu_alloc_gb" not in r1
    assert r1["gradient_clipping_applied"] == 1 and r2["gradient_clipping_applied"] == 0
    assert r1["tokens_per_byte"] == pytest.approx(1200 / 4800)
    assert not set(r1) & G5_ONLY
    assert "skipping unknown metric" not in capsys.readouterr().err  # G5-only names dropped quietly


def test_validation_step(tmp_path):
    writer = make_writer(tmp_path)
    writer.write(dict(step=0, **g5_eval()))                       # train_week2's step-0 eval row
    writer.write({**g5_train_row(10), **g5_eval(2500.0, 1000)})   # eval_every_steps row
    writer.close()
    r0, r10 = rows(tmp_path / "g8" / "metrics.jsonl")
    assert r0 == {"step": 0, "time": r0["time"], "validation_loss": pytest.approx(3.0)}
    assert r10["validation_loss"] == pytest.approx(2.5)
    assert r10["validation_loss"] == pytest.approx(math.log(g5_eval(2500.0, 1000)["val/perplexity"]))
    assert not any(k.startswith("val/") for k in r10)


def test_unknown_g5_field_still_warns(tmp_path, capsys):
    writer = make_writer(tmp_path)
    writer.write({**g5_train_row(1), "train/new_field": 1.0})
    writer.close()
    assert "train/new_field" in capsys.readouterr().err
    assert "train/new_field" not in rows(tmp_path / "g8" / "metrics.jsonl")[0]


def test_tokens_per_byte_edge_cases(tmp_path):
    writer = make_writer(tmp_path)
    writer.write({**g5_train_row(1), "train/utf8_bytes": 0})       # no bytes: not written
    writer.write({**g5_train_row(2), "tokens_per_byte": 0.5})      # a value already there wins
    writer.close()
    r1, r2 = rows(tmp_path / "g8" / "metrics.jsonl")
    assert "tokens_per_byte" not in r1
    assert r2["tokens_per_byte"] == 0.5


def test_flush_cadence_and_nonfinite(tmp_path):
    writer = make_writer(tmp_path)
    path = tmp_path / "g8" / "metrics.jsonl"
    writer.write(g5_train_row(1))
    assert path.read_text() == ""                                  # buffered until step % 10 == 0
    writer.write({**g5_train_row(2), "loss_ntp": float("nan")})     # non-finite: flushed at once, stored "nan"
    assert [r["loss_ntp"] for r in rows(path)] == [3.2, "nan"]
    writer.close()


def test_row_without_step_rejected(tmp_path):
    writer = make_writer(tmp_path)
    with pytest.raises(ValueError):
        writer.write({"loss_ntp": 1.0})
    writer.close()
