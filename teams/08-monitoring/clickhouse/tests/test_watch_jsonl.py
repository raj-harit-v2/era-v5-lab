"""Tests for watch_jsonl.py (Issue #27).

The offline tests use FakeClickHouse, which keeps INSERTs in lists and answers the watcher's two SELECTs.
The last test loads the full dry run 1 log into a real ClickHouse on CLICKHOUSE_URL. It fails, never skips,
when that server is down, so a green run always means the live load was checked.
"""

import json
import os
from pathlib import Path
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from load_jsonl import REPO_ROOT, _parse_jsonl_content, ch_Exec  # noqa: E402
from watch_jsonl import Watcher, WatchError, lock_source, main, prepare_schema  # noqa: E402

DRYRUN1 = REPO_ROOT / "teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl"


class FakeClickHouse:
    def __init__(self):
        self.metrics: list[dict] = []
        self.batches: list[dict] = []
        self.fail_batch_inserts = 0

    def __call__(self, sql, data=None):
        if sql.startswith("INSERT INTO metrics_raw"):
            self.metrics.extend(json.loads(ln) for ln in data.decode().splitlines())
            return ""
        if sql.startswith("INSERT INTO ingest_batches"):
            if self.fail_batch_inserts:
                self.fail_batch_inserts -= 1
                raise ConnectionError("connection refused")
            self.batches.append(json.loads(data))
            return ""
        run_id = re.search(r"run_id = '([^']*)'", sql).group(1)
        if "FROM ingest_batches" in sql:
            source = re.search(r"source_file = '([^']*)'", sql).group(1)
            mine = [b for b in self.batches if b["run_id"] == run_id and b["source_file"] == source]
            return f"{max((b['end_offset'] for b in mine), default=0)}\t{sum(b['lines'] for b in mine)}\n"
        if "FROM metrics_raw" in sql:
            pairs = {(r["step"], r["rank"]) for r in self.metrics if r["run_id"] == run_id}
            return "".join(f"{s}\t{r}\n" for s, r in sorted(pairs))
        raise AssertionError(f"unexpected SQL: {sql}")

    def duplicate_pairs(self, run_id):
        keys = [(r["step"], r["name"], r["rank"]) for r in self.metrics if r["run_id"] == run_id]
        return len(keys) - len(set(keys))


def line(step, **extra):
    """One JSONL line with two metrics, loss and lr."""
    return json.dumps({"step": step, "loss": 3.0 - step / 100, "lr": 0.001, **extra}) + "\n"


def append(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def full_parse_rows(path, run_id):
    return _parse_jsonl_content(Path(path).read_text(encoding="utf-8"), run_id, run_id)["rows"]


def test_half_written_line_waits_for_its_newline(tmp_path):
    path = tmp_path / "metrics.jsonl"
    path.write_text(line(0) + line(1) + line(2) + '{"step": 3, "loss": 3.')
    ch = FakeClickHouse()
    w = Watcher(path, run_id="r1", exec_fn=ch)

    b1 = w.poll_once()
    assert (b1.first_step, b1.last_step, b1.lines) == (0, 2, 3)
    assert w.offset == len((line(0) + line(1) + line(2)).encode())
    assert w.poll_once() is None  # still no newline after step 3

    append(path, '14}\n')
    b2 = w.poll_once()
    assert (b2.first_step, b2.last_step, b2.lines, b2.start_offset) == (3, 3, 1, b1.end_offset)
    assert [r["value"] for r in ch.metrics if r["step"] == 3] == [3.14]
    assert ch.metrics == full_parse_rows(path, "r1")


def test_batches_chain_and_rows_match_a_full_parse(tmp_path):
    dry_lines = DRYRUN1.read_text(encoding="utf-8").splitlines(keepends=True)[:25]
    path = tmp_path / "metrics.jsonl"
    path.write_text("")
    ch = FakeClickHouse()
    w = Watcher(path, run_id="dry", exec_fn=ch)

    for chunk in (dry_lines[:1], dry_lines[1:11], dry_lines[11:21], dry_lines[21:]):  # flushes at 0, 10, 20, end
        append(path, "".join(chunk))
        assert w.poll_once() is not None
        assert w.poll_once() is None  # nothing new

    assert [b["start_offset"] for b in ch.batches[1:]] == [b["end_offset"] for b in ch.batches[:-1]]
    assert ch.batches[-1]["end_offset"] == path.stat().st_size
    assert sum(b["lines"] for b in ch.batches) == 25
    assert ch.metrics == full_parse_rows(path, "dry")  # same invented times as a one-shot load
    assert len({r["time"] for r in ch.metrics}) == 25
    assert ch.duplicate_pairs("dry") == 0


def test_restart_continues_at_the_saved_offset_and_line_number(tmp_path):
    path = tmp_path / "metrics.jsonl"
    path.write_text("".join(line(s) for s in range(12)))
    ch = FakeClickHouse()
    Watcher(path, run_id="r1", exec_fn=ch).poll_once()

    append(path, "".join(line(s) for s in range(12, 25)))
    w2 = Watcher(path, run_id="r1", exec_fn=ch)
    batch = w2.poll_once()
    assert (batch.first_step, batch.lines, batch.skipped_lines) == (12, 13, 0)
    assert w2.line_index == 25
    assert ch.metrics == full_parse_rows(path, "r1")
    assert ch.duplicate_pairs("r1") == 0


def test_resumed_segment_loads_only_steps_not_yet_stored(tmp_path):
    # Segment A flushed steps 0..7, then the job died; the checkpoint held history to step 9 (#606, #512).
    seg_a = tmp_path / "a" / "g8" / "metrics.jsonl"
    seg_b = tmp_path / "b" / "g8" / "metrics.jsonl"
    seg_a.parent.mkdir(parents=True)
    seg_b.parent.mkdir(parents=True)
    seg_a.write_text("".join(line(s, run_id="r7", time=1000 + s) for s in range(8)))
    seg_b.write_text("".join(line(s, run_id="r7", time=2000 + s) for s in range(15)))
    ch = FakeClickHouse()

    Watcher(seg_a, exec_fn=ch).poll_once()
    batch = Watcher(seg_b, exec_fn=ch).poll_once()

    assert (batch.lines, batch.skipped_lines, batch.rows) == (15, 8, 7 * 2)
    assert sorted({r["step"] for r in ch.metrics}) == list(range(15))
    assert {r["run_id"] for r in ch.metrics} == {"r7"}
    assert ch.duplicate_pairs("r7") == 0


def test_run_id_comes_from_the_rows_then_the_folder(tmp_path):
    with_id = tmp_path / "g8" / "metrics.jsonl"
    with_id.parent.mkdir()
    with_id.write_text(line(0, run_id="r9") + line(1, run_id="r9"))
    w = Watcher(with_id, exec_fn=FakeClickHouse())
    w.poll_once()
    assert w.run_id == "r9"

    no_id = tmp_path / "dryrun1-full" / "metrics.jsonl"
    no_id.parent.mkdir()
    no_id.write_text(line(0))
    w = Watcher(no_id, exec_fn=FakeClickHouse())
    w.poll_once()
    assert w.run_id == "dryrun1-full"


def test_a_second_run_id_in_the_same_file_stops_the_watcher(tmp_path):
    path = tmp_path / "metrics.jsonl"
    path.write_text(line(0, run_id="r9") + line(1, run_id="other"))
    ch = FakeClickHouse()
    with pytest.raises(WatchError, match="run_id 'other'"):
        Watcher(path, exec_fn=ch).poll_once()
    assert ch.metrics == []


def test_broken_complete_line_inserts_nothing_and_names_the_byte(tmp_path):
    path = tmp_path / "metrics.jsonl"
    good = line(0) + line(1)
    path.write_text(good + '{"step": 2, "loss": }\n')
    ch = FakeClickHouse()
    w = Watcher(path, run_id="r1", exec_fn=ch)
    with pytest.raises(WatchError, match=f"line 3 at byte {len(good.encode())}"):
        w.poll_once()
    assert ch.metrics == [] and ch.batches == [] and w.offset == 0


def test_truncated_file_stops_the_watcher(tmp_path):
    path = tmp_path / "metrics.jsonl"
    path.write_text(line(0) + line(1))
    w = Watcher(path, run_id="r1", exec_fn=FakeClickHouse())
    w.poll_once()
    path.write_text(line(0))
    with pytest.raises(WatchError, match="shorter than the resume offset"):
        w.poll_once()


def test_crash_between_the_two_inserts_does_not_double_rows(tmp_path):
    path = tmp_path / "metrics.jsonl"
    path.write_text(line(0) + line(1))
    ch = FakeClickHouse()
    ch.fail_batch_inserts = 1  # rows go in, the ingest_batches row does not
    with pytest.raises(ConnectionError):
        Watcher(path, run_id="r1", exec_fn=ch).poll_once()
    assert len(ch.metrics) == 4 and ch.batches == []

    append(path, line(2))
    batch = Watcher(path, run_id="r1", exec_fn=ch).poll_once()  # the restart
    assert (batch.first_step, batch.lines, batch.skipped_lines) == (0, 3, 2)
    assert sorted({r["step"] for r in ch.metrics}) == [0, 1, 2]
    assert ch.duplicate_pairs("r1") == 0


def test_clickhouse_down_stops_the_watcher_instead_of_polling(tmp_path):
    path = tmp_path / "metrics.jsonl"
    path.write_text(line(0))

    def down(sql, data=None):
        raise ConnectionError("connection refused")

    def no_sleep(seconds):
        raise AssertionError("the watcher kept polling a dead server")

    with pytest.raises(ConnectionError):
        Watcher(path, run_id="r1", exec_fn=down).run(poll=2, sleep=no_sleep)


def test_main_exits_1_and_says_why_when_clickhouse_is_down(tmp_path, capsys):
    path = tmp_path / "metrics.jsonl"
    path.write_text(line(0))
    assert main([str(path), "--run-id", "r1", "--url", "http://127.0.0.1:1"]) == 1
    out = capsys.readouterr()
    assert "error: ClickHouse at http://127.0.0.1:1 failed, watcher stopped" in out.err
    assert f"NOT LOADED: {len(line(0))} bytes after the offset" in out.out


def test_summary_tells_an_unfinished_line_from_unloaded_lines(tmp_path):
    path = tmp_path / "metrics.jsonl"
    path.write_text(line(0) + '{"step": 1, "lo')
    w = Watcher(path, run_id="r1", exec_fn=FakeClickHouse())
    w.poll_once()
    assert w.summary().endswith("(15 bytes of an unfinished last line not loaded)")


def test_waits_for_a_missing_file_then_exits_when_idle(tmp_path):
    path = tmp_path / "live" / "metrics.jsonl"
    ch = FakeClickHouse()
    w = Watcher(path, run_id="r1", exec_fn=ch)
    assert w.poll_once() is None

    clock = [0.0]
    writes = {2.0: line(0), 4.0: line(1)}

    def sleep(seconds):
        clock[0] += seconds
        if clock[0] in writes:
            path.parent.mkdir(exist_ok=True)
            append(path, writes[clock[0]])

    w.run(poll=2, idle_exit=6, sleep=sleep, monotonic=lambda: clock[0])
    assert [b["last_step"] for b in ch.batches] == [0, 1]
    assert clock[0] == 10.0  # last line at t=4, then idle for 6 s


def test_second_watcher_on_the_same_file_is_refused(tmp_path):
    pytest.importorskip("fcntl")
    path = tmp_path / "metrics.jsonl"
    path.write_text("")
    first = lock_source(path)
    try:
        with pytest.raises(WatchError, match="already loading"):
            lock_source(path)
    finally:
        first.close()
    lock_source(path).close()  # free again once the first watcher is gone


def test_live_dryrun1_catch_up_load():
    run_id = f"pytest_watch_{os.getpid()}"
    prepare_schema()
    try:
        Watcher(DRYRUN1, run_id=run_id).run(poll=0.2, idle_exit=0.5)
        assert Watcher(DRYRUN1, run_id=run_id).poll_once() is None  # a restart finds nothing new

        def one(sql):
            return ch_Exec(f"{sql} FORMAT TabSeparated").strip()

        where = f"run_id = '{run_id}'"
        assert one(f"SELECT uniqExact(step), count(), countIf(value IS NULL) FROM metrics_raw WHERE {where}") == (
            "1222\t19753\t0"
        )
        assert one(
            f"SELECT count() FROM (SELECT step, name, rank FROM metrics_raw WHERE {where} "
            f"GROUP BY step, name, rank HAVING count() > 1)"
        ) == "0"
        assert one(f"SELECT sum(lines), max(end_offset) FROM ingest_batches WHERE {where}") == (
            f"1222\t{DRYRUN1.stat().st_size}"
        )
    finally:
        for table in ("metrics_raw", "ingest_batches"):
            ch_Exec(f"ALTER TABLE {table} DELETE WHERE run_id = '{run_id}' SETTINGS mutations_sync = 2")
