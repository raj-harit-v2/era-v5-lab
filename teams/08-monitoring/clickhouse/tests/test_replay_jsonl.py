"""Tests for replay_jsonl.py (Issue #27). A fake clock makes the replay schedule instant and exact."""

import csv
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from load_jsonl import REPO_ROOT  # noqa: E402
from replay_jsonl import main, read_lines, replay, utc_text  # noqa: E402

DRYRUN1 = REPO_ROOT / "teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl"
EPOCH = 1_763_500_000.0


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def sleep(self, seconds):
        assert seconds > 0
        self.now += seconds

    def monotonic(self):
        return self.now

    def wall(self):
        return EPOCH + self.now


def run(lines, tmp_path, **kwargs):
    clock = FakeClock()
    out, log = tmp_path / "live" / "metrics.jsonl", tmp_path / "live" / "written.csv"
    info = replay(lines, out, log, sleep=clock.sleep, monotonic=clock.monotonic, wall=clock.wall,
                  report=lambda msg: None, **kwargs)
    with open(log, newline="") as f:
        return info, out, list(csv.DictReader(f))


def write_source(path, records):
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    return path


def test_dryrun1_lines_are_copied_byte_for_byte_in_writer_flushes(tmp_path):
    lines = read_lines(DRYRUN1, limit=25)
    info, out, rows = run(lines, tmp_path)

    source_head = b"".join(DRYRUN1.read_bytes().splitlines(keepends=True)[:25])
    assert out.read_bytes() == source_head
    groups = {}
    for r in rows:
        groups.setdefault(r["written_at"], []).append(int(r["step"]))
    assert list(groups.values()) == [[0], list(range(1, 11)), list(range(11, 21)), list(range(21, 25))]
    assert info["flushes"] == 4
    assert [int(r["start_offset"]) for r in rows[1:]] == [int(r["end_offset"]) for r in rows[:-1]]
    assert int(rows[-1]["end_offset"]) == len(source_head)
    assert (rows[1]["start_offset"], rows[11]["start_offset"]) == ("2927", "7716")


def test_each_line_is_produced_after_its_own_step_ms_divided_by_speed(tmp_path):
    lines = read_lines(DRYRUN1, limit=12)
    _, _, rows = run(lines, tmp_path, speed=2.0)

    elapsed = 0.0
    for line, row in zip(lines, rows):
        elapsed += line.seconds / 2.0
        assert row["produced_at"] == utc_text(EPOCH + elapsed)
    assert lines[0].seconds == 1.9  # step 0 has no perf/step_ms
    assert lines[1].seconds == pytest.approx(4.430346715991618)  # step 1's recorded warm-up


def test_a_line_holding_null_is_flushed_at_once(tmp_path):
    src = write_source(tmp_path / "src.jsonl", [
        {"step": 0, "loss": 3.0}, {"step": 1, "loss": 2.9}, {"step": 2, "loss": None}, {"step": 3, "loss": 2.8},
    ])
    _, _, rows = run(read_lines(src), tmp_path)
    assert [r["written_at"] == rows[2]["written_at"] for r in rows] == [False, True, True, False]


def test_limit_and_step_seconds(tmp_path):
    src = write_source(tmp_path / "src.jsonl", [{"step": s, "loss": 1.0} for s in range(5)])
    lines = read_lines(src, step_seconds=0.5, limit=3)
    assert [(line.step, line.seconds) for line in lines] == [(0, 0.5), (1, 0.5), (2, 0.5)]


def test_bad_source_fails_before_anything_is_written(tmp_path):
    src = tmp_path / "src.jsonl"
    src.write_text('{"step": 0, "loss": 1.0}\n{"loss": 2.0}\n')
    out = tmp_path / "out" / "metrics.jsonl"
    assert main([str(src), "--out", str(out), "--log", str(tmp_path / "out" / "w.csv")]) == 1
    assert not out.exists()


def test_existing_output_is_refused_unless_overwrite(tmp_path, capsys):
    src = write_source(tmp_path / "src.jsonl", [{"step": 0, "loss": 1.0}])
    out, log = tmp_path / "metrics.jsonl", tmp_path / "w.csv"
    out.write_text("old\n")
    args = [str(src), "--out", str(out), "--log", str(log), "--step-seconds", "0.01"]

    assert main(args) == 1
    assert "pass --overwrite" in capsys.readouterr().err
    assert out.read_text() == "old\n"

    assert main(args + ["--overwrite"]) == 0
    assert out.read_text() == '{"step": 0, "loss": 1.0}\n'
