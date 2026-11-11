import json
from pathlib import Path
import sys
import tempfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from load_node_logs import (  # noqa: E402
    extract_telemetry_metrics,
    parse_node_log_text,
    run_selftest,
    to_clickhouse_node_health_row,
)


def test_load_node_logs_selftest():
    assert run_selftest() is True


def test_parse_real_health_sample_v5():
    sample_path = (
        Path(__file__).resolve().parents[3]
        / "07-infrastructure"
        / "health"
        / "results"
        / "health_sample_v5.json"
    )
    assert sample_path.exists(), f"Missing {sample_path}"

    text = sample_path.read_text(encoding="utf-8")
    parsed = parse_node_log_text(text, "health_sample_v5")
    assert parsed["jsonl_lines"] == 1
    assert len(parsed["node_health_rows"]) == 1

    row = parsed["node_health_rows"][0]
    assert row["host"] == "pop-os"
    assert row["mode"] == "prolog"
    assert row["expected_gpus"] == 8
    assert row["gpus_seen"] == 8
    assert row["verdict"] == "fail"
    assert row["admit_training"] == 0
    assert "ecc_uncorrectable" in row["drain_reason"]
    assert "xid" in row["drain_reason"]
    assert row["ecc_uncorrectable_total"] == 2
    assert row["xid_codes"] == [13, 79, 94, 157]
    assert row["checks_fail"] == 2
    assert row["checks_warn"] == 3
    assert row["checks_pass"] >= 10
    assert row["runtime_seconds"] == 0.002

    # Verify extracted metrics for metrics_raw
    assert len(parsed["metrics_raw_rows"]) >= 9
    metric_names = {r["name"] for r in parsed["metrics_raw_rows"]}
    assert "temp_c" in metric_names
    assert "host_mem_available_gb" in metric_names
    assert "gpus_seen" in metric_names

    # Check GPU temperatures
    gpu_temps = [r["value"] for r in parsed["metrics_raw_rows"] if r["name"] == "temp_c"]
    assert 87.0 in gpu_temps  # The hot GPU 2


def test_parse_multi_node_jsonl_stream():
    sample_reports = [
        {
            "schema": "v5-health/1",
            "timestamp_utc": "2026-11-04T00:00:00Z",
            "host": "node-1",
            "mode": "periodic",
            "expected_gpus": 8,
            "verdict": "pass",
            "admit_training": True,
            "checks": [
                {"name": "gpu_inventory", "status": "pass", "required": True, "metrics": {"count": 8}},
                {"name": "gpu_temperature", "status": "pass", "required": True, "gpu": 0, "metrics": {"temp_c": 35.0}},
            ],
        },
        {
            "schema": "v5-health/1",
            "timestamp_utc": "2026-11-04T00:00:30Z",
            "host": "node-2",
            "mode": "periodic",
            "expected_gpus": 8,
            "verdict": "warn",
            "admit_training": False,
            "drain_reason": "gpu_temperature",
            "checks": [
                {"name": "gpu_inventory", "status": "pass", "required": True, "metrics": {"count": 8}},
                {"name": "gpu_temperature", "status": "warn", "required": True, "gpu": 1, "metrics": {"temp_c": 89.0}},
            ],
        },
    ]

    jsonl_text = "\n".join(json.dumps(r) for r in sample_reports)
    parsed = parse_node_log_text(jsonl_text, "multi_node_test")

    assert parsed["jsonl_lines"] == 2
    assert len(parsed["node_health_rows"]) == 2
    assert parsed["node_health_rows"][0]["host"] == "node-1"
    assert parsed["node_health_rows"][0]["verdict"] == "pass"
    assert parsed["node_health_rows"][1]["host"] == "node-2"
    assert parsed["node_health_rows"][1]["verdict"] == "warn"
    assert len(parsed["metrics_raw_rows"]) == 4


def test_extract_telemetry_metrics_null_handling():
    doc_with_nans = {
        "timestamp_utc": "2026-11-04T00:00:00Z",
        "checks": [
            {"name": "gpu_temperature", "status": "fail", "gpu": 0, "metrics": {"temp_c": "nan"}},
            {"name": "host_mem", "status": "skipped", "metrics": {"available_gb": None}},
        ],
    }
    m = extract_telemetry_metrics(doc_with_nans, "nan_test")
    assert len(m) == 2
    assert m[0]["value"] is None
    assert m[1]["value"] is None
