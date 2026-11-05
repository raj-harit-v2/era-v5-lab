"""Issue #8: host data_ms must be stored as loader_wait_time in seconds."""
import json
import pytest
from metrics_writer import MetricsWriter


def get_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.mark.parametrize("data_ms,seconds", [(0, 0.0), (12.5, 0.0125), (1000, 1.0)])
def test_data_ms_alias_converts_once(tmp_path, data_ms, seconds):
    path = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(path)) as w:
        w.write(1, data_ms=data_ms)
    row, = get_rows(path)
    assert row["loader_wait_time"] == pytest.approx(seconds)
    assert "data_ms" not in row


def test_seconds_passthrough(tmp_path):
    path = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(path)) as w:
        w.write(1, loader_wait_time=0.0125)
    assert get_rows(path)[0]["loader_wait_time"] == 0.0125


def test_canonical_value_wins_if_both_present(tmp_path):
    path = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(path)) as w:
        w.write(1, data_ms=900, loader_wait_time=0.25)
    row, = get_rows(path)
    assert row["loader_wait_time"] == 0.25
    assert "data_ms" not in row


def test_missing_measurement_does_not_emit_loader_wait(tmp_path):
    path = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(path)) as w:
        w.write(1, loss_ntp=1.2)
    assert "loader_wait_time" not in get_rows(path)[0]


def test_none_data_ms_does_not_emit_loader_wait(tmp_path):
    path = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(path)) as w:
        w.write(1, data_ms=None)
    assert "loader_wait_time" not in get_rows(path)[0]
