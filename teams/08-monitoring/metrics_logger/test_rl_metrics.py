"""Unit tests for the G10-aligned Week 3 RL metrics in metric_list_v1.yaml and metrics_writer.py."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import yaml

HERE = Path(__file__).resolve().parent
MONITORING_DIR = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(MONITORING_DIR / "clickhouse") not in sys.path:
    sys.path.insert(0, str(MONITORING_DIR / "clickhouse"))

from metrics_writer import METRICS, MetricsWriter
from load_jsonl import parse_source

RL_METRICS = (
    "reward_per_env",
    "train_reward",
    "entropy",
    "mismatch_k3",
    "mismatch_abs_logratio",
)


def test_rl_metrics_present_in_catalog_and_writer_allowlist():
    catalog_path = MONITORING_DIR / "metrics" / "metric_list_v1.yaml"
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    names = {entry["name"] for entry in data["metrics"]}
    for m in RL_METRICS:
        assert m in names, f"{m} missing from metric_list_v1.yaml"
        assert m in METRICS, f"{m} missing from metrics_writer.METRICS"
    for removed in ("solved_share", "masked_tokens", "train_inference_mismatch"):
        assert removed not in names
        assert removed not in METRICS


def test_metrics_writer_logs_rl_metrics_and_clickhouse_loader_flattens_env_dict(tmp_path):
    out = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(out), flush_every=10) as w:
        w.write(
            10,
            reward_per_env={"math": 0.75, "code": 0.5, "swe": 0.25},
            train_reward=0.625,
            entropy=0.42,
            mismatch_k3=0.0012,
            mismatch_abs_logratio=0.018,
        )

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    r = rows[0]
    assert r["step"] == 10
    assert r["reward_per_env"] == {"math": 0.75, "code": 0.5, "swe": 0.25}
    assert math.isclose(r["train_reward"], 0.625)
    assert math.isclose(r["entropy"], 0.42)
    assert math.isclose(r["mismatch_k3"], 0.0012)
    assert math.isclose(r["mismatch_abs_logratio"], 0.018)

    parsed = parse_source(str(out), run_id_override="rl_smoke_v1")
    by_name = {item["name"]: item["value"] for item in parsed["rows"]}
    assert math.isclose(by_name["reward_per_env.math"], 0.75)
    assert math.isclose(by_name["reward_per_env.code"], 0.50)
    assert math.isclose(by_name["reward_per_env.swe"], 0.25)
    assert math.isclose(by_name["train_reward"], 0.625)
    assert math.isclose(by_name["entropy"], 0.42)
    assert math.isclose(by_name["mismatch_k3"], 0.0012)
    assert math.isclose(by_name["mismatch_abs_logratio"], 0.018)
