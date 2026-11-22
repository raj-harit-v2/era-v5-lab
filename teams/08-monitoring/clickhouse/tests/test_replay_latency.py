"""Tests for replay_latency.py (Issue #27): the join of a replay log to loader batches, without ClickHouse."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from replay_latency import epoch, measure, percentile  # noqa: E402

T0 = "2026-11-21 01:00:00.000"


def row(step, produced, written, start, end):
    return {"step": str(step), "produced_at": produced, "written_at": written,
            "start_offset": str(start), "end_offset": str(end)}


def test_delays_come_from_the_batch_that_holds_each_line():
    log = [
        row(0, "2026-11-21 01:00:00.000", "2026-11-21 01:00:00.000", 0, 100),
        row(1, "2026-11-21 01:00:02.000", "2026-11-21 01:00:04.000", 100, 200),
        row(2, "2026-11-21 01:00:04.000", "2026-11-21 01:00:04.000", 200, 300),
    ]
    batches = [(0, 100, epoch("2026-11-21 01:00:01.000")), (100, 300, epoch("2026-11-21 01:00:05.500"))]
    result = measure(log, batches, [2.0, 2.0, 2.0])
    assert result["unmatched"] == 0
    assert result["pauses"] == []
    assert result["from_write"] == [1.0, 1.5, 1.5]
    assert result["from_produce"] == [1.0, 3.5, 1.5]


def test_unloaded_or_double_loaded_lines_are_unmatched():
    log = [row(0, T0, T0, 0, 100), row(1, "2026-11-21 01:00:02.000", "2026-11-21 01:00:02.000", 100, 200)]
    ins = epoch("2026-11-21 01:00:03.000")
    assert measure(log, [], [2.0, 2.0])["unmatched"] == 2
    assert measure(log, [(0, 200, ins), (0, 100, ins)], [2.0, 2.0])["unmatched"] == 1


def test_a_gap_longer_than_the_step_counts_as_a_pause():
    log = [row(0, T0, T0, 0, 100), row(1, "2026-11-21 01:00:10.000", "2026-11-21 01:00:10.000", 100, 200)]
    result = measure(log, [(0, 200, epoch("2026-11-21 01:00:11.000"))], [2.0, 2.0])
    assert result["pauses"] == [8.0]


def test_percentile_is_nearest_rank():
    values = [float(v) for v in range(1, 101)]
    assert percentile(values, 50) == 51.0
    assert percentile(values, 95) == 95.0
    assert percentile([3.0], 95) == 3.0
