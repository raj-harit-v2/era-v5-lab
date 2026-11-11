import json
import math
from pathlib import Path
import sys
import tempfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_rows import run_selftest, verify_source  # noqa: E402
from load_jsonl import ch_Exec, ensure_schema, load_source, parse_source, resolve_source_text  # noqa: E402


def _ch_available() -> bool:
    try:
        return "1" in ch_Exec("SELECT 1")
    except Exception:
        return False


def test_parse_team5_and_team6_sources_offline():
    p_a = parse_source("teams/05-architecture/experiments/evidence/run_a/metrics.jsonl")
    assert p_a["run_id"] == "run_a"
    assert p_a["jsonl_lines"] == 40
    assert p_a["metric_rows"] == 240
    assert p_a["null_rows"] == 0

    p_b = parse_source("teams/05-architecture/experiments/evidence/run_b/")
    assert p_b["run_id"] == "run_b"
    assert p_b["jsonl_lines"] == 40
    assert p_b["metric_rows"] == 240

    p_g6 = parse_source("teams/06-performance/results/modal_gpu/h200_v1.json")
    assert p_g6["run_id"] == "h200_v1"
    assert p_g6["jsonl_lines"] == 150
    assert p_g6["metric_rows"] > 150
    names = {r["name"] for r in p_g6["rows"]}
    assert {"step_ms", "mfu", "model_flops_utilization", "gpu_utilization", "gpu_memory_used"} <= names

    # Verify Team 06 additive MFU fields (mfu_method, mfu_scope, participants, global_tokens_per_s, run-scope reason codes)
    g6_v2_doc = json.loads(resolve_source_text("teams/06-performance/results/modal_gpu/h200_v1.json")[2])
    g6_v2_doc["metrics"].update({
        "mfu_method": "g6-v2",
        "mfu_scope": "run",
        "global_tokens_per_s": 190918.0,
        "participants": {
            "world_size": 2,
            "peak_tflops_sum": 624.0,
            "devices": [{"name": "NVIDIA A100-SXM4-80GB", "peak_tflops": 312.0}] * 2,
        },
    })
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp_g6:
        json.dump(g6_v2_doc, tmp_g6)
        g6_path = Path(tmp_g6.name)
    try:
        p_g6_v2 = parse_source(str(g6_path))
        by_n = {r["name"]: r["value"] for r in p_g6_v2["rows"]}
        assert p_g6_v2["null_rows"] == 0
        assert math.isclose(by_n["global_tokens_per_s"], 190918.0)
        assert math.isclose(by_n["participants.world_size"], 2.0)
        assert math.isclose(by_n["participants.peak_tflops_sum"], 624.0)
    finally:
        g6_path.unlink(missing_ok=True)


def test_parse_eval_mini_v1_json_and_jsonl():
    sample_doc = {
        "schema_version": "eval_mini_v1",
        "generated": "2026-11-03",
        "sources": [],
        "notes": [],
        "records": [
            {
                "model": "HuggingFaceTB/SmolLM2-1.7B",
                "model_revision": "effd688a12921b4cc83e3312b6feb579f70f9c71",
                "checkpoint": None,
                "format": "bf16",
                "backend": "hf",
                "dtype": "bfloat16",
                "task": "arc_average",
                "metric": "acc_norm",
                "filter": "none",
                "primary": True,
                "value": 60.34,
                "stderr": 0.86,
                "n_items": 3548,
                "n_items_total": 3548,
                "item_set": "full",
                "profile": "check",
                "num_fewshot": 0,
                "decoding": "loglikelihood",
                "seed": {"random": 42, "numpy": 42, "torch": 42, "fewshot": 42},
                "harness": {"name": "lm_eval", "version": "0.4.13"},
                "hardware": "Apple M2 Pro",
                "run_date": "2026-10-24",
                "derived_from": ["arc_easy", "arc_challenge"],
                "notes": [],
            },
            {
                "model": "Qwen/Qwen2.5-1.5B",
                "model_revision": "e5dfabbcffd9b0c7b31d89b82c5a6b72e663f32c",
                "checkpoint": None,
                "format": "bf16",
                "backend": "hf",
                "dtype": "bfloat16",
                "task": "humaneval",
                "metric": "pass@1",
                "filter": "none",
                "primary": True,
                "value": 37.20,
                "stderr": None,
                "n_items": 164,
                "n_items_total": 164,
                "item_set": "full",
                "profile": "code_indic",
                "num_fewshot": 0,
                "decoding": "greedy",
                "seed": None,
                "harness": {"name": "evalplus", "version": "0.3.1"},
                "hardware": "RTX 3070",
                "run_date": "2026-10-27",
                "derived_from": None,
                "notes": [],
            },
        ],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp_json:
        json.dump(sample_doc, tmp_json)
        json_path = Path(tmp_json.name)
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp_jsonl:
        for r in sample_doc["records"]:
            tmp_jsonl.write(json.dumps(r) + "\n")
        jsonl_path = Path(tmp_jsonl.name)

    try:
        for path in (json_path, jsonl_path):
            parsed = parse_source(str(path), run_id_override="eval_mini_v1")
            assert parsed["target_table"] == "eval_mini"
            assert parsed["jsonl_lines"] == 2
            assert parsed["metric_rows"] == 2
            assert parsed["null_rows"] == 1
            assert parsed["nulls_by_col"] == {
                "checkpoint": 2,
                "derived_from": 1,
                "seed": 1,
                "stderr": 1,
                "dtype": 0,
                "n_items_total": 0,
                "profile": 0,
            }
            r0, r1 = parsed["rows"]
            assert r0["checkpoint"] is None and r0["derived_from"] == '["arc_easy","arc_challenge"]'
            assert r0["seed_random"] == 42 and math.isclose(r0["stderr"], 0.86)
            assert r1["seed"] is None and r1["seed_random"] is None and r1["stderr"] is None
            assert r1["derived_from"] is None and r1["harness_name"] == "evalplus"
    finally:
        json_path.unlink(missing_ok=True)
        jsonl_path.unlink(missing_ok=True)


def test_parse_live_g6_events_and_null_handling():
    sample = "\n".join([
        json.dumps({
            "schema_version": 1,
            "event": "step_timing",
            "timestamp": "2026-10-30T12:09:59.413Z",
            "run_id": "g6_live_test",
            "node_id": "modal",
            "rank": 0,
            "local_rank": 0,
            "step": 1,
            "data_ms": 0.95,
            "raw_step_ms": 82.93,
        }),
        json.dumps({
            "schema_version": 1,
            "event": "gpu_sample",
            "timestamp": "2026-10-30T12:10:00.189Z",
            "run_id": "g6_live_test",
            "node_id": "modal",
            "gpu": {"name": "NVIDIA A100", "index": 0, "uuid": "GPU-1234", "pci_bus_id": "[Unknown Error]"},
            "step": 2,
            "metrics": {"gpu_util_pct": 64.0, "mem_used_mib": 8105.0, "power_w": 133.35, "temp_c": 41.0},
            "slowdown_flags": [],
        }),
        json.dumps({
            "step": 3,
            "time": "2026-10-30T12:10:01.000Z",
            "loss_ntp": None,
            "mfu": None,
            "mfu_unavailable_reason": "unknown_gpu",
            "gradient_norm": "nan",
        }),
    ])
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        tmp.write(sample + "\n")
        tmp_path = Path(tmp.name)

    try:
        parsed = parse_source(str(tmp_path))
        assert parsed["run_id"] == "g6_live_test"
        assert parsed["jsonl_lines"] == 3
        assert parsed["null_rows"] == 3
        by_name = {(r["step"], r["name"]): r["value"] for r in parsed["rows"]}
        assert math.isclose(by_name[(1, "loader_wait_time")], 0.00095)
        assert math.isclose(by_name[(2, "gpu_utilization")], 64.0)
        assert math.isclose(by_name[(2, "gpu_memory_used")], 8105.0 * 1048576.0)
        assert by_name[(3, "loss_ntp")] is None
        assert by_name[(3, "mfu")] is None
        assert by_name[(3, "gradient_norm")] is None
    finally:
        tmp_path.unlink(missing_ok=True)


@pytest.mark.skipif(not _ch_available(), reason="ClickHouse server is not reachable on CLICKHOUSE_URL")
def test_clickhouse_end_to_end_load_check_and_rollups():
    ensure_schema()
    assert run_selftest() is True

    for src in (
        "teams/05-architecture/experiments/evidence/run_a/metrics.jsonl",
        "teams/05-architecture/experiments/evidence/run_b/metrics.jsonl",
        "teams/06-performance/results/modal_gpu/h200_v1.json",
    ):
        load_source(src)
        res = verify_source(src)
        assert res["ok"], f"Verification failed for {src}: {res}"

    # Verify 10-step and 100-step rollups on `run_a` (40 steps -> 4 buckets in rollup_10, 1 bucket in rollup_100)
    r10 = ch_Exec(
        "SELECT step_bucket, min, max, mean, last, count "
        "FROM metrics_rollup_10 WHERE run_id = 'run_a' AND name = 'loss_ntp' "
        "ORDER BY step_bucket FORMAT JSONEachRow"
    ).strip().splitlines()
    assert len(r10) == 4
    b0 = json.loads(r10[0])
    assert int(b0["step_bucket"]) == 0
    assert int(b0["count"]) == 10
    assert b0["min"] <= b0["mean"] <= b0["max"]

    r100 = ch_Exec(
        "SELECT step_bucket, count FROM metrics_rollup_100 "
        "WHERE run_id = 'run_a' AND name = 'loss_ntp' FORMAT JSONEachRow"
    ).strip().splitlines()
    assert len(r100) == 1
    assert int(json.loads(r100[0])["count"]) == 40

    # Verify 1s GPU telemetry rollup has h200_v1 telemetry metrics
    g1s = ch_Exec(
        "SELECT name, count FROM gpu_telemetry_1s "
        "WHERE run_id = 'h200_v1' ORDER BY name FORMAT JSONEachRow"
    ).strip().splitlines()
    g_names = {json.loads(line)["name"] for line in g1s}
    assert {"gpu_utilization", "gpu_memory_used", "power_w", "temp_c"} <= g_names

    # Verify Team 09 eval_mini_v1.json loads into `eval_mini` and populates `v_eval_mini_pivot`
    try:
        load_source("teams/09-evaluation/results/eval_mini_v1.json")
        res_ev = verify_source("teams/09-evaluation/results/eval_mini_v1.json")
        assert res_ev["ok"], f"eval_mini_v1.json verification failed: {res_ev}"
        assert res_ev["ch_lines"] == 98
        assert res_ev["ch_nulls_by_col"] == {
            "checkpoint": 98,
            "derived_from": 92,
            "seed": 12,
            "stderr": 12,
            "dtype": 0,
            "n_items_total": 0,
            "profile": 0,
        }
        pivot_rows = ch_Exec(
            "SELECT model, model_revision, item_set, primary_tasks_scored "
            "FROM v_eval_mini_pivot WHERE run_id = 'eval_mini_v1' FORMAT JSONEachRow"
        ).strip().splitlines()
        assert len(pivot_rows) >= 5
    except FileNotFoundError:
        pass
