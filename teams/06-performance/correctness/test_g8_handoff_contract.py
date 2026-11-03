"""Focused G6 Task 6 -> G8 producer-side handoff regression tests.

Place in teams/06-performance/correctness/test_g8_handoff_contract.py.
These tests cover only NEW boundary cases beyond correctness/test_events.py:
shared run IDs across nodes, strict JSON numbers, G6/G8 timing units,
and compatibility between interleaved GPU/step JSONL records.

They do NOT test G8 ClickHouse ingestion, Grafana, or review/sign-off.
"""

import json
import math

import pytest

from perfkit.events import JsonlWriter, gpu_sample_record, step_timing_record


TIMESTAMP = "2026-10-30T12:00:00.000Z"


def _step(*, node_id="node-a", rank=0, local_rank=0, step=17, data_ms=12.5):
    return step_timing_record(
        run_id="shared-run", node_id=node_id, rank=rank,
        local_rank=local_rank, step=step, data_ms=data_ms,
        raw_step_ms=32.25, timestamp=TIMESTAMP,
    )


def _gpu(*, node_id="node-a", uuid="GPU-A", step=17, pci_bus_id="0000:01:00.0"):
    return gpu_sample_record(
        run_id="shared-run", node_id=node_id,
        gpu={"name": "Example GPU", "index": 0, "uuid": uuid,
             "pci_bus_id": pci_bus_id},
        metrics={"mem_used_mib": 1024, "gpu_util_pct": 97.5},
        slowdown_flags=[], step=step, timestamp=TIMESTAMP,
    )


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_shared_run_id_preserves_distinct_nodes_ranks_steps_and_gpu_uuids(tmp_path):
    """Simulate independent collectors with the same run_id, not G8 ingestion."""
    a_path, b_path = tmp_path / "node-a.jsonl", tmp_path / "node-b.jsonl"
    with JsonlWriter(a_path) as writer:
        writer.write(_gpu(node_id="node-a", uuid="GPU-A", step=17))
        writer.write(_step(node_id="node-a", rank=0, local_rank=0, step=17))
    with JsonlWriter(b_path) as writer:
        writer.write(_gpu(node_id="node-b", uuid="GPU-B", step=18))
        writer.write(_step(node_id="node-b", rank=8, local_rank=0, step=18))

    rows = _read_jsonl(a_path) + _read_jsonl(b_path)
    assert len(rows) == 4
    assert {r["run_id"] for r in rows} == {"shared-run"}
    gpu_keys = {(r["run_id"], r["node_id"], r["gpu"]["uuid"], r["step"])
                for r in rows if r["event"] == "gpu_sample"}
    step_keys = {(r["run_id"], r["node_id"], r["rank"], r["local_rank"], r["step"])
                 for r in rows if r["event"] == "step_timing"}
    assert gpu_keys == {("shared-run", "node-a", "GPU-A", 17),
                        ("shared-run", "node-b", "GPU-B", 18)}
    assert step_keys == {("shared-run", "node-a", 0, 0, 17),
                         ("shared-run", "node-b", 8, 0, 18)}


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")], ids=["nan", "posinf", "neginf"])
def test_nonfinite_numbers_cannot_enter_jsonl_and_writer_recovers(tmp_path, bad):
    """A rejected metric must not write a corrupt or partial JSONL line."""
    path = tmp_path / "safe.jsonl"
    with JsonlWriter(path) as writer:
        with pytest.raises(ValueError):
            writer.write(_step(data_ms=bad))
        with pytest.raises(ValueError):
            writer.write(gpu_sample_record(
                run_id="shared-run", node_id="node-a",
                gpu={"uuid": "GPU-A", "index": 0},
                metrics={"mem_used_mib": bad}, slowdown_flags=[],
                step=17, timestamp=TIMESTAMP,
            ))
        writer.write(_step(data_ms=1.25))
    rows = _read_jsonl(path)
    assert len(rows) == 1
    assert math.isfinite(rows[0]["data_ms"])
    assert "NaN" not in path.read_text(encoding="utf-8")
    assert "Infinity" not in path.read_text(encoding="utf-8")


def test_g6_data_ms_remains_milliseconds_for_g8_to_convert(tmp_path):
    """G6 writes host-side ms; G8 (not G6) owns loader_wait_time seconds."""
    path = tmp_path / "units.jsonl"
    with JsonlWriter(path) as writer:
        writer.write(_step(data_ms=12.5))
    row = _read_jsonl(path)[0]
    assert row["data_ms"] == pytest.approx(12.5)
    assert row["raw_step_ms"] == pytest.approx(32.25)
    assert row["data_ms"] / 1000.0 == pytest.approx(0.0125)
    assert "loader_wait_time" not in row
    assert "loader_wait_time_ms" not in row


def test_interleaved_gpu_and_step_records_retain_g8_join_context(tmp_path):
    """Interleaving + unknown PCI should not break identity or event parsing."""
    path = tmp_path / "mixed.jsonl"
    with JsonlWriter(path) as writer:
        writer.write(_gpu(pci_bus_id="[Unknown Error]", step=17))
        writer.write(_step(step=17, rank=0))
        writer.write(_gpu(step=None))  # sampler may not have a current step
        writer.write(_step(step=18, rank=0))
    rows = _read_jsonl(path)
    assert [r["event"] for r in rows] == [
        "gpu_sample", "step_timing", "gpu_sample", "step_timing"]
    assert {r["schema_version"] for r in rows} == {1}
    assert {(r["run_id"], r["node_id"]) for r in rows} == {("shared-run", "node-a")}
    assert rows[0]["gpu"]["uuid"] == "GPU-A"
    assert rows[0]["gpu"]["pci_bus_id"] == "[Unknown Error]"
    assert rows[0]["metrics"]["mem_used_mib"] == 1024  # raw MiB
    assert rows[1]["rank"] == 0 and rows[1]["step"] == 17
    assert rows[2]["step"] is None
    assert rows[3]["rank"] == 0 and rows[3]["step"] == 18
    # A missing/unreliable PCI ID is NOT a substitute for GPU UUID.
    assert rows[0]["gpu"]["uuid"] == rows[2]["gpu"]["uuid"]
