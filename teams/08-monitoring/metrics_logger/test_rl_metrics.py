"""Unit tests for the five Week 3 RL alignment metrics in metric_list_v1.yaml and metrics_writer.py."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import pytest
import yaml

HERE = Path(__file__).resolve().parent
MONITORING_DIR = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(MONITORING_DIR / "clickhouse") not in sys.path:
    sys.path.insert(0, str(MONITORING_DIR / "clickhouse"))

from metrics_writer import METRICS, MetricsWriter, train_inference_mismatch
from load_jsonl import parse_source

RL_METRICS = (
    "reward_per_env",
    "solved_share",
    "entropy",
    "masked_tokens",
    "train_inference_mismatch",
)


def test_rl_metrics_present_in_catalog_and_writer_allowlist():
    catalog_path = MONITORING_DIR / "metrics" / "metric_list_v1.yaml"
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    names = {entry["name"] for entry in data["metrics"]}
    for m in RL_METRICS:
        assert m in names, f"{m} missing from metric_list_v1.yaml"
        assert m in METRICS, f"{m} missing from metrics_writer.METRICS"


def test_train_inference_mismatch_helper():
    assert train_inference_mismatch(None, [0.5]) is None
    assert train_inference_mismatch([], []) is None
    assert math.isclose(
        train_inference_mismatch([0.20, 0.80, 0.05], [0.21, 0.76, 0.05]),
        0.04,
        rel_tol=1e-9,
    )
    assert math.isnan(train_inference_mismatch([0.2, 0.8], [0.2]))
    assert math.isnan(train_inference_mismatch([0.2, float("nan")], [0.2, 0.5]))


def test_metrics_writer_logs_rl_metrics_and_clickhouse_loader_flattens_env_dict(tmp_path):
    out = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(out), flush_every=10) as w:
        w.write(
            10,
            reward_per_env={"math": 0.75, "code": 0.5, "swe": 0.25},
            rl_solved_share=0.625,
            rl_entropy=0.42,
            rl_masked_tokens=128,
            p_train=[0.30, 0.55, 0.15],
            p_infer=[0.31, 0.52, 0.15],
        )

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    r = rows[0]
    assert r["step"] == 10
    assert r["reward_per_env"] == {"math": 0.75, "code": 0.5, "swe": 0.25}
    assert math.isclose(r["solved_share"], 0.625)
    assert math.isclose(r["entropy"], 0.42)
    assert r["masked_tokens"] == 128
    assert math.isclose(r["train_inference_mismatch"], 0.03, rel_tol=1e-9)

    parsed = parse_source(str(out), run_id_override="rl_smoke_v1")
    by_name = {item["name"]: item["value"] for item in parsed["rows"]}
    assert math.isclose(by_name["reward_per_env.math"], 0.75)
    assert math.isclose(by_name["reward_per_env.code"], 0.50)
    assert math.isclose(by_name["reward_per_env.swe"], 0.25)
    assert math.isclose(by_name["solved_share"], 0.625)
    assert math.isclose(by_name["entropy"], 0.42)
    assert math.isclose(by_name["masked_tokens"], 128.0)
    assert math.isclose(by_name["train_inference_mismatch"], 0.03, rel_tol=1e-9)


def test_nonfinite_mismatch_flushes_immediately(tmp_path):
    out = tmp_path / "metrics.jsonl"
    w = MetricsWriter(str(out), flush_every=10)
    try:
        # Step 3 is not a flush_every multiple, but mismatched lengths yield NaN -> immediate flush
        w.write(3, p_train=[0.5, 0.5], p_infer=[0.5])
        lines = out.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["train_inference_mismatch"] == "nan"
    finally:
        w.close()
