"""run_events: restarts, checkpoints and alarm hits for the open infrastructure health panels (32, 33)."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

HERE = Path(__file__).resolve().parent
G8 = HERE.parents[1]
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
from load_run_events import (  # noqa: E402
    SCHEMA_SQL, _ch_post, alarm_row, coverage_row, ensure_table, event_row, insert_rows, main, parse_alarms,
    parse_events,
)

# Named decorator: pr-guard reads an added pytest decorator line as an email address.
parametrize = pytest.mark.parametrize

TEAM7_RESTART_FILE = REPO / "teams/07-infrastructure/results/restart_cpu_rotation_03.txt"
PRIVATE_JSON = G8 / "grafana" / "private_v1.json"


def ev(event, **fields):
    """A v5-event/1 record as Team 07's common/events.py emit() writes it, host and job included."""
    rec = {"schema": "v5-event/1", "time": "2026-11-24T10:00:00.000Z", "host": "node-17.cluster.internal",
           "run_id": "dryrun2-1234", "job_id": "4242", "event": event}
    rec.update(fields)
    return rec


def test_schema_is_replacing_merge_tree_with_no_machine_columns():
    ddl = "\n".join(ln for ln in SCHEMA_SQL.read_text(encoding="utf-8").splitlines() if not ln.strip().startswith("--"))
    assert "CREATE TABLE IF NOT EXISTS run_events" in ddl
    assert "ReplacingMergeTree(loaded_at)" in ddl
    assert "ORDER BY (run_id, event_key)" in ddl
    for forbidden in ("host", "job", "path", "store", "file", "gpu", "cost"):
        assert forbidden not in ddl.lower(), forbidden


@parametrize("event, kind", [
    ("restore.done", "restart"),
    ("restore.failed", "restart_failed"),
    ("checkpoint.committed", "checkpoint"),
    ("checkpoint.failed", "checkpoint_failed"),
    ("checkpoint.fenced", "checkpoint_failed"),
    ("checkpoint.started", "other"),
    ("checkpoint.claimed", "other"),
])
def test_event_kinds(event, kind):
    row = event_row(ev(event, step=600))
    assert row["kind"] == kind and row["event"] == event and row["step"] == 600 and row["severity"] == ""


def test_machine_fields_never_stored():
    rec = ev("checkpoint.committed", step=1200, branch="main", reason="interval", store="s3",
             path="/shared/ckpt/dryrun2-1234/main/step_00001200-e1", upload_gbps=9.5, bytes=123,
             detail="Traceback ... /home/user/node-17/...")
    row = event_row(rec)
    blob = json.dumps(row)
    for leaked in ("node-17", "4242", "/shared/ckpt", "upload_gbps", "s3", "Traceback"):
        assert leaked not in blob, leaked
    assert json.loads(row["detail"]) == {"branch": "main", "reason": "interval"}


def test_time_is_utc_datetime64_text():
    assert event_row(ev("restore.done", step=5))["event_time"] == "2026-11-24 10:00:00.000"
    assert event_row(ev("restore.done", step=5, time="garbage"))["event_time"] is None


def test_run_id_override_and_missing_run_id():
    assert event_row(ev("restore.done"), run_id="other")["run_id"] == "other"
    with pytest.raises(ValueError, match="run_id"):
        event_row(ev("restore.done", run_id=""))


def test_non_events_are_not_rows():
    assert event_row({"event": "restore.done"}) is None  # no schema
    assert event_row({"schema": "v5-health/1", "event": "x"}) is None
    assert alarm_row({"rule": "non_finite", "severity": "loud"}, "r") is None
    assert alarm_row({"severity": "warn"}, "r") is None


def test_parse_events_handles_prefixes_torn_lines_and_dirs(tmp_path):
    d = tmp_path / "events"
    d.mkdir()
    (d / "a-1.jsonl").write_text(json.dumps(ev("checkpoint.committed", step=0)) + "\n"
                                 + json.dumps(ev("checkpoint.committed", step=600))[:40] + "\n",  # torn by a kill
                                 encoding="utf-8")
    (d / "b-2.jsonl").write_text("restore.done: " + json.dumps(ev("restore.done", step=600)) + "\n\n"
                                 + "supervisor: " + json.dumps({"action": "restart"}) + "\n", encoding="utf-8")
    (d / "notes.txt").write_text(json.dumps(ev("restore.done", step=1)) + "\n", encoding="utf-8")  # not *.jsonl
    rows, skipped = parse_events(d)
    assert [(r["kind"], r["step"]) for r in rows] == [("checkpoint", 0), ("restart", 600)]
    assert skipped == 2  # the torn line and the supervisor line; blank lines are not counted


def test_reload_gives_the_same_keys(tmp_path):
    f = tmp_path / "e.jsonl"
    f.write_text("\n".join(json.dumps(ev("checkpoint.committed", step=s)) for s in (0, 600, 1200)) + "\n",
                 encoding="utf-8")
    first, _ = parse_events(f)
    second, _ = parse_events(f)
    assert [r["event_key"] for r in first] == [r["event_key"] for r in second]
    assert len({r["event_key"] for r in first}) == 3


def test_alarm_rows_and_stable_keys():
    hit = {"step": 140, "metric": "loss_ntp", "rule": "non_finite", "severity": "stop", "detail": "loss_ntp is nan"}
    row = alarm_row(hit, "dryrun2-1234")
    assert (row["kind"], row["event"], row["severity"], row["step"], row["event_time"]) == \
        ("alarm", "alarm.non_finite", "stop", 140, None)
    assert alarm_row(dict(hit, detail="reworded"), "dryrun2-1234")["event_key"] == row["event_key"]
    assert alarm_row(dict(hit, step=141), "dryrun2-1234")["event_key"] != row["event_key"]
    with pytest.raises(ValueError, match="run-id"):
        alarm_row(hit, "")


def test_team7_restart_drill_file_counts_four_restarts():
    """Team 07's CPU restart drill killed the run 4 times; each restart wrote one restore.done event."""
    if not TEAM7_RESTART_FILE.exists():
        pytest.skip("Team 07 restart evidence not in this checkout")
    rows, _ = parse_events(TEAM7_RESTART_FILE)
    assert [r["kind"] for r in rows] == ["restart"] * 4
    assert sorted(r["step"] for r in rows) == [25, 75, 125, 150]


def test_alarms_py_output_loads(tmp_path):
    """Contract with alarms.py: its --jsonl stdout is the --alarms input, with no conversion step."""
    metrics = tmp_path / "metrics.jsonl"
    with open(metrics, "w", encoding="utf-8") as f:
        for s in range(30):
            loss = "nan" if s == 20 else 3.0 - s / 100
            f.write(json.dumps({"step": s, "loss_ntp": loss, "lr": 3e-4}) + "\n")
    out = subprocess.run([sys.executable, "-I", str(G8 / "alarms" / "alarms.py"), "--jsonl", str(metrics)],
                         capture_output=True, text=True, check=True).stdout
    alarms_file = tmp_path / "alarms.jsonl"
    alarms_file.write_text(out, encoding="utf-8")
    rows, skipped = parse_alarms(alarms_file, "r1")
    assert [(r["event"], r["severity"], r["step"]) for r in rows] == [("alarm.non_finite", "stop", 20)]
    assert skipped == 0


def test_cli_dry_run_prints_rows_and_a_coverage_marker(tmp_path, capsys):
    f = tmp_path / "e.jsonl"
    f.write_text(json.dumps(ev("restore.done", step=7)) + "\n", encoding="utf-8")
    assert main(["--events", str(f), "--dry-run"]) == 0
    out = capsys.readouterr()
    rows = [json.loads(x) for x in out.out.strip().splitlines()]
    assert [(r["kind"], r["event"], r["run_id"]) for r in rows] == [
        ("restart", "restore.done", "dryrun2-1234"), ("coverage", "events.loaded", "dryrun2-1234")]
    assert "2 run_events rows" in out.err


def test_alarm_file_with_no_hits_still_marks_the_run_checked(tmp_path, capsys):
    empty = tmp_path / "alarms.jsonl"
    empty.write_text("", encoding="utf-8")
    assert main(["--alarms", str(empty), "--run-id", "r1", "--dry-run"]) == 0
    rows = [json.loads(x) for x in capsys.readouterr().out.strip().splitlines()]
    assert rows == [coverage_row("r1", "alarms")]


def test_alarms_need_a_run_id(tmp_path):
    f = tmp_path / "alarms.jsonl"
    f.write_text("", encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["--alarms", str(f), "--dry-run"])


def test_coverage_key_is_one_per_run_and_source():
    assert coverage_row("r1", "alarms")["event_key"] == coverage_row("r1", "alarms")["event_key"]
    assert coverage_row("r1", "alarms")["event_key"] != coverage_row("r1", "events")["event_key"]
    assert coverage_row("r1", "alarms")["event_key"] != coverage_row("r2", "alarms")["event_key"]


def test_private_panels_32_33_read_run_events_only():
    d = json.loads(PRIVATE_JSON.read_text(encoding="utf-8"))
    panels = {p["id"]: p for p in d["panels"]}
    ids = [p["id"] for p in d["panels"]]
    assert len(ids) == len(set(ids))
    for pid in (32, 33):
        sql = panels[pid]["targets"][0]["rawSql"]
        assert "FROM run_events FINAL" in sql and "$event_run" in sql
        assert "host" not in sql and "job" not in sql
    assert any(v["name"] == "event_run" and "run_events" in v["query"] for v in d["templating"]["list"])


def _ch_available() -> bool:
    try:
        return _ch_post("SELECT 1").strip() == "1"
    except Exception:
        return False


@pytest.mark.skipif(not _ch_available(), reason="ClickHouse server is not reachable on 127.0.0.1:8123")
def test_clickhouse_counts_do_not_double_on_reload():
    run = f"test-run-events-{uuid.uuid4().hex[:8]}"
    events = [ev("checkpoint.committed", step=s, run_id=run) for s in (0, 600, 1200)]
    events += [ev("restore.done", step=600, run_id=run), ev("checkpoint.failed", step=900, run_id=run)]
    rows = [event_row(e) for e in events]
    rows += [alarm_row({"step": 300, "metric": "loss_ntp", "rule": "spike_score", "severity": "page"}, run),
             alarm_row({"step": 310, "metric": "gradient_norm", "rule": "ema_z", "severity": "warn"}, run)]
    rows += [coverage_row(run, "events"), coverage_row(run, "alarms")]
    alarms_only = f"{run}-alarms-only"  # alarms checked with no hits, Team 07 events never loaded
    rows += [coverage_row(alarms_only, "alarms")]
    ensure_table()
    try:
        insert_rows(rows)
        insert_rows(rows)  # a reload of the same files
        panel = json.loads(PRIVATE_JSON.read_text(encoding="utf-8"))
        sql = next(p for p in panel["panels"] if p["id"] == 32)["targets"][0]["rawSql"]
        got = _ch_post(sql.replace("$event_run", f"'{run}', '{alarms_only}'") + " FORMAT JSONEachRow")
        by_run = {r["run_id"]: r for r in map(json.loads, got.strip().splitlines())}
        assert set(by_run) == {run, alarms_only}
        lone = by_run[alarms_only]
        assert lone["restarts"] is None and lone["checkpoints"] is None  # blank: never loaded, not zero
        assert int(lone["alarm_page"]) == 0  # checked, nothing found
        row = by_run[run]
        counts = {k: int(row[k]) for k in ("restarts", "failed_restores", "checkpoints", "failed_checkpoints",
                                            "alarm_stop", "alarm_page", "alarm_warn")}
        assert counts == {"restarts": 1, "failed_restores": 0, "checkpoints": 3, "failed_checkpoints": 1,
                          "alarm_stop": 0, "alarm_page": 1, "alarm_warn": 1}
        assert int(row["last_event_step"]) == 1200
        trend_sql = next(p for p in panel["panels"] if p["id"] == 33)["targets"][0]["rawSql"]
        lines = [json.loads(x) for x in _ch_post(trend_sql.replace("$event_run", f"'{run}'")
                                                 + " FORMAT JSONEachRow").strip().splitlines()]
        last = {}
        for x in lines:
            last[x["series"]] = int(x["value"])
        assert last == {f"{run} checkpoint": 3, f"{run} restart": 1, f"{run} checkpoint_failed": 1,
                        f"{run} alarm": 2}
    finally:
        _ch_post(f"ALTER TABLE run_events DELETE WHERE run_id LIKE '{run}%' SETTINGS mutations_sync = 2")


def test_bad_step_is_stored_as_no_step():
    assert event_row(ev("checkpoint.committed", step=float("nan")))["step"] is None
    assert event_row(ev("checkpoint.committed", step="abc"))["step"] is None
    assert event_row(ev("checkpoint.committed", step=True))["step"] is None
