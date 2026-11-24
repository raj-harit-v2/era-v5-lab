"""Tests for eval_lag.py, the eval-watcher lag alarm (week 4, Team 08 task 1).

Offline: FakeClickHouse keeps the tables in lists, answers the alarm's three SELECTs and watch_jsonl.Watcher's own
SQL, and fails on any other statement. A run is built on a timeline first (batches as watch_jsonl.py writes them,
commits as Team 07's Checkpointer makes them, Tier A rows as the eval watcher loads them); the fake hides rows from
the future, so the alarm can then be checked at any moment. No ClickHouse, no torch.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time
import urllib.error

import pytest

ALARMS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ALARMS))
sys.path.insert(0, str(ALARMS.parent / "clickhouse"))
from eval_lag import TABLE_SQL, Batch, EvalLagMonitor, active_lag_ms, main, tsv_fields  # noqa: E402
from load_jsonl import REPO_ROOT, _format_utc, _parse_jsonl_content, ch_Exec, load_source  # noqa: E402
from watch_jsonl import Watcher, prepare_schema  # noqa: E402

DRYRUN1 = REPO_ROOT / "teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/metrics.jsonl"
DASHBOARD = REPO_ROOT / "teams/08-monitoring/grafana/private_v1.json"
EVAL_TEMPLATE = REPO_ROOT / "teams/09-evaluation/results/eval_mini_v1.json"
LIVE_URL = os.environ.get("CLICKHOUSE_URL")
RUN = "dryrun2-1234"
RESUME = "dryrun2-1234-resume-a"  # the kill drill's run 2 writes to ./out/dryrun2-1234-resume-a
OTHER = "dryrun2-5678"  # a second, separate run
T0 = 1_795_000_000_000  # a fixed start time, UTC ms (Nov 2026)
INTERVAL_S = 600.0
LIMIT_MS = 1_200_000  # 2 x 600 s
BATCH_MS = 45_000  # one batch per 10-step flush: 10 x 4.4 s + 1 s until watch_jsonl.py reads it


def ms(seconds: float) -> int:
    return round(seconds * 1000)


def to_ms(text: str) -> int:
    return ms(datetime.strptime(text, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc).timestamp())


def quoted(text: str) -> set[str]:
    return set(re.findall(r"'([^']*)'", text))


class FakeClickHouse:
    def __init__(self):
        self.batches: list[dict] = []  # ingest_batches rows, plus seen_ms
        self.pairs: dict[str, set] = {}  # metrics_raw (step, rank) pairs per run
        self.evals: list[dict] = []  # eval_mini rows: run_id, checkpoint_run, checkpoint_step, loaded_ms
        self.checks: list[dict] = []  # eval_lag_checks rows
        self.ddl: list[str] = []
        self.now_ms: int | None = None  # rows after this time are not visible yet
        self.error: Exception | None = None  # raised by the next call

    def visible(self, rows, key):
        return [r for r in rows if self.now_ms is None or r[key] <= self.now_ms]

    def __call__(self, sql, data=None):
        if self.error is not None:
            raise self.error
        if sql.startswith("CREATE TABLE IF NOT EXISTS eval_lag_checks"):
            self.ddl.append(sql)
            return ""
        if sql == "INSERT INTO eval_lag_checks FORMAT JSONEachRow":
            self.checks.extend(json.loads(ln) for ln in data.decode().splitlines())
            return ""
        if sql.startswith("INSERT INTO metrics_raw"):
            for row in (json.loads(ln) for ln in data.decode().splitlines()):
                self.pairs.setdefault(row["run_id"], set()).add((row["step"], row["rank"]))
            return ""
        if sql.startswith("INSERT INTO ingest_batches"):
            row = json.loads(data)
            self.batches.append({**row, "seen_ms": to_ms(row["seen_at"])})
            return ""
        assert sql.endswith(" FORMAT TabSeparated"), sql
        if "argMax(last_step, seen_at)" in sql:
            return self._newest_batches(sql)
        if "FROM eval_mini" in sql:
            return self._newest_scores(sql)
        if "first_step, last_step FROM ingest_batches" in sql:
            return self._batches(sql)
        run_id = re.search(r"run_id = '([^']*)'", sql).group(1)  # watch_jsonl.Watcher.start()
        if "FROM ingest_batches" in sql:
            source = re.search(r"source_file = '([^']*)'", sql).group(1)
            mine = [b for b in self.batches if b["run_id"] == run_id and b["source_file"] == source]
            return f"{max((b['end_offset'] for b in mine), default=0)}\t{sum(b['lines'] for b in mine)}\n"
        if "FROM metrics_raw" in sql:
            return "".join(f"{s}\t{r}\n" for s, r in sorted(self.pairs.get(run_id, ())))
        raise AssertionError(f"unexpected SQL: {sql}")

    def _newest_batches(self, sql):
        assert "FROM ingest_batches WHERE lines > 0" in sql, sql
        m = re.search(r"AND run_id IN \(([^)]*)\)", sql)
        newest: dict[str, tuple[int, int]] = {}
        for b in self.visible(self.batches, "seen_ms"):
            if b["lines"] > 0 and (m is None or b["run_id"] in quoted(m.group(1))):
                key = (b["seen_ms"], b["last_step"])
                newest[b["run_id"]] = max(newest.get(b["run_id"], key), key)
        return "".join(f"{run}\t{seen}\t{step}\n" for run, (seen, step) in sorted(newest.items()))

    def _newest_scores(self, sql):
        needle = re.search(r"position\(run_id, '([^']*)'\) > 0", sql).group(1)
        m = re.search(r"checkpoint_run IN \(([^)]*)\)", sql)
        best: dict[str, tuple[int, int]] = {}
        for e in self.visible(self.evals, "loaded_ms"):
            if needle in e["run_id"] and (m is None or e["checkpoint_run"] in quoted(m.group(1))):
                step, loaded = best.get(e["checkpoint_run"], (-1, -1))
                best[e["checkpoint_run"]] = (max(step, e["checkpoint_step"]), max(loaded, e["loaded_ms"]))
        return "".join(f"{run}\t{step}\t{loaded}\n" for run, (step, loaded) in sorted(best.items()))

    def _batches(self, sql):
        assert " WHERE lines > 0 AND (" in sql, sql
        assert sql.endswith(" ORDER BY seen_at, source_file, start_offset FORMAT TabSeparated"), sql
        clauses = [(quoted(runs), int(low))
                   for runs, low in re.findall(r"\(run_id IN \(([^)]*)\) AND last_step >= (\d+)\)", sql)]
        assert clauses, sql
        rows = sorted((b for b in self.visible(self.batches, "seen_ms") if b["lines"] > 0
                       and any(b["run_id"] in runs and b["last_step"] >= low for runs, low in clauses)),
                      key=lambda b: (b["seen_ms"], b["source_file"], b["start_offset"]))
        return "".join(f"{b['run_id']}\t{b['seen_ms']}\t{b['first_step']}\t{b['last_step']}\n" for b in rows)


class Run:
    """A training run on a timeline. `train()` writes a batch per 10-step flush (read 1 s later) and commits as
    Team 07's Checkpointer does: the first step at least 600 s after the last commit, with the timer restarting in
    each new process. `score()` adds the eval watcher's rows: 230 s after each commit, 159 s more on every 10th
    commit (Tier B first on the shared slot)."""

    def __init__(self, ch: FakeClickHouse, step_s: float = 4.4, flush: int = 10):
        self.ch, self.step_s, self.flush = ch, step_s, flush
        self.t = T0 / 1000  # seconds
        self.commits: list[tuple[int, float]] = []  # (step, time)
        self._last_commit = self.t
        self._offsets: dict[str, int] = {}

    def train(self, first, last, train_run=RUN, *, commit_first=False, new_process=True, killed=False):
        if new_process:
            self._last_commit = self.t
        if commit_first:
            self.commits.append((first - 1, self.t))  # --checkpoint-at-start commits step 0 before step 1
        pending: list[int] = []
        for step in range(first, last + 1):
            self.t += self.step_s
            pending.append(step)
            if step % self.flush == 0 or (step == last and not killed):  # SIGKILL loses the unflushed lines
                self._batch(train_run, pending)
                pending = []
            if self.t - self._last_commit >= INTERVAL_S:
                self.commits.append((step, self.t))
                self._last_commit = self.t
        return self

    def pause(self, seconds):
        self.t += seconds
        return self

    def score(self, label="tier-a", *, eval_run=RUN, delay_s=230.0, tier_b_s=159.0, skip=lambda loaded_s: False):
        for i, (step, t) in enumerate(self.commits):
            loaded = t + delay_s + (tier_b_s if i % 10 == 9 else 0.0)
            if not skip(loaded):
                self.ch.evals.append({"run_id": f"{eval_run}:step-{step:08d}:{label}:0123456789ab",
                                      "checkpoint_run": eval_run, "checkpoint_step": step, "loaded_ms": ms(loaded)})
        return self

    def _batch(self, train_run, steps):
        offset = self._offsets.get(train_run, 0)
        self._offsets[train_run] = offset + len(steps)
        self.ch.batches.append({"run_id": train_run, "source_file": f"{train_run}/metrics.jsonl",
                                "start_offset": offset, "end_offset": offset + len(steps), "first_step": steps[0],
                                "last_step": steps[-1], "lines": len(steps), "seen_ms": ms(self.t + 1)})


def monitor(ch, **kw) -> EvalLagMonitor:
    kw.setdefault("interval_s", INTERVAL_S)
    return EvalLagMonitor(ch, **kw)


def sweep(mon, ch, start_ms, end_ms, every_ms=30_000):
    """Check (and save) every 30 s; returns the (time, check) pairs."""
    out = []
    for now in range(start_ms, end_ms + 1, every_ms):
        ch.now_ms = now
        checks = mon.check(now)
        mon.save(checks, now)
        out += [(now, c) for c in checks]
    return out


def pages(results):
    return [(now, c) for now, c in results if c.paged]


def max_lag(results):
    return max((c.lag_ms for _, c in results if c.lag_ms is not None), default=0)


def other_lag(ch, now, *, runs, restores=True, pause_ms=10**12):
    """The lag measured another way, to show a test case is a real trap: `restores=False` times each step by when
    it was first reached (as `metrics_raw` keeps the first rows), a huge `pause_ms` counts pauses in full."""
    batches = sorted((b for b in ch.batches if b["seen_ms"] <= now and b["run_id"] in runs),
                     key=lambda b: (b["seen_ms"], b["start_offset"]))
    steps = [e["checkpoint_step"] for e in ch.evals if e["loaded_ms"] <= now and ":tier-a:" in e["run_id"]]
    eval_step = max(steps, default=None)
    if not restores:
        reached = [b["seen_ms"] for b in batches if eval_step is None or b["last_step"] >= eval_step]
        return batches[-1]["seen_ms"] - min(reached) if reached and batches else 0
    return active_lag_ms([Batch(b["seen_ms"], b["first_step"], b["last_step"]) for b in batches], eval_step, pause_ms)


# --- the lag itself -------------------------------------------------------------------------------------------------

def test_lag_runs_from_the_batch_that_reached_the_scored_step():
    batches = [Batch(0, 1, 10), Batch(20_000, 11, 20), Batch(40_000, 21, 30)]
    assert active_lag_ms(batches, 15, 300_000) == 20_000
    assert active_lag_ms(batches, 30, 300_000) == 0
    assert active_lag_ms(batches, None, 300_000) == 40_000  # no Tier A row: from the start of the pass
    assert active_lag_ms(batches, 35, 300_000) == 0  # scored step ahead of training
    assert active_lag_ms([], None, 300_000) == 0


def test_a_restore_drops_the_lost_steps_and_the_downtime():
    first = [Batch(0, 1, 10), Batch(20_000, 11, 20), Batch(40_000, 21, 30)]
    redo = [Batch(400_000, 11, 20), Batch(420_000, 21, 25)]  # restored to step 10 after a 360 s stop
    assert active_lag_ms(first + redo, 15, 300_000) == 20_000  # from the redo batch, not from 20 s
    assert active_lag_ms(first + redo, 28, 300_000) == 0  # training is behind step 28 again
    assert active_lag_ms(first + redo, None, 300_000) == 20_000


def test_lag_caps_each_pause():
    batches = [Batch(0, 1, 10), Batch(20_000, 11, 20), Batch(1_000_000, 21, 30)]
    assert active_lag_ms(batches, 15, 300_000) == 300_000
    assert active_lag_ms(batches, None, 300_000) == 320_000


def test_a_restore_keeps_the_lag_built_up_before_its_restore_point():
    before = [Batch(0, 1, 10), Batch(20_000, 11, 20), Batch(40_000, 21, 30)]
    # Scored step 15; restored to step 25 after a 360 s stop: 15..25 still counts (20 s), the stop doesn't, +20 s.
    assert active_lag_ms(before + [Batch(400_000, 26, 30), Batch(420_000, 31, 40)], 15, 300_000) == 40_000
    # Restored to step 22, inside the batch 21..30: that batch is cut at 22. A scored step 25 was lost, so the lag
    # runs from the redo batch that reaches 25 again; a scored step 22 was kept, so it runs from the cut batch.
    after_22 = [Batch(400_000, 23, 30), Batch(420_000, 31, 40)]
    assert active_lag_ms(before + after_22, 25, 300_000) == 20_000
    assert active_lag_ms(before + after_22, 22, 300_000) == 20_000
    assert active_lag_ms(before + after_22, None, 300_000) == 60_000  # 0..40 s, nothing for the stop, then 20 s


def test_lag_is_the_same_on_the_batches_the_alarm_reads():
    """The alarm reads only batches with last_step >= the scored step; across restores the lag must not change."""
    rng = random.Random(24)
    for _ in range(300):
        batches, t, step = [], 0, 0
        for _ in range(rng.randint(1, 40)):
            if batches and rng.random() < 0.15:
                step = rng.randint(0, step)  # a restore goes back to an earlier step
            first, step = step + 1, step + rng.randint(1, 12)
            t += rng.choice((2_000, 20_000, 400_000))
            batches.append(Batch(t, first, step))
        for eval_step in range(0, max(b.last_step for b in batches) + 2):
            if batches[-1].last_step >= eval_step:
                kept = [b for b in batches if b.last_step >= eval_step]
                assert active_lag_ms(kept, eval_step, 300_000) == active_lag_ms(batches, eval_step, 300_000)


def test_metrics_raw_time_is_invented_for_the_trainers_rows():
    """Why the alarm reads ingest_batches: Team 05's rows have no time, so metrics_raw gets 28 Oct + 1 s per line."""
    two_lines = "".join(DRYRUN1.read_text(encoding="utf-8").splitlines(keepends=True)[:2])
    times = sorted({row["time"] for row in _parse_jsonl_content(two_lines, RUN)["rows"]})
    assert times == ["2026-10-28 00:00:00.000", "2026-10-28 00:00:01.000"]


# --- the alarm on whole runs ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("last_step, lowest_max_lag_ms", [
    (1221, 600_000),  # dry run 2: 1,221 steps, about 90 min
    (4900, 900_000),  # 6 hours: includes the 10th commits, where Tier B goes first
])
def test_a_watcher_that_keeps_up_never_pages(last_step, lowest_max_lag_ms):
    ch = FakeClickHouse()
    run = Run(ch).train(1, last_step, commit_first=True).score()
    results = sweep(monitor(ch, runs={RUN: RUN}), ch, T0, ms(run.t) + 60_000)
    assert pages(results) == []
    assert lowest_max_lag_ms < max_lag(results) < LIMIT_MS


def test_a_stopped_watcher_pages_once_per_episode():
    ch = FakeClickHouse()
    run = Run(ch).train(1, 4900, commit_first=True)
    down = [(T0 / 1000 + 3_000, T0 / 1000 + 6_000), (T0 / 1000 + 12_000, T0 / 1000 + 20_000)]
    run.score(skip=lambda s: any(a <= s < b for a, b in down))
    got = pages(sweep(monitor(ch, runs={RUN: RUN}), ch, T0, ms(run.t) + 60_000))
    assert len(got) == 2
    for (now, page), (start, end) in zip(got, down):
        assert ms(start) < now < ms(end)
        assert LIMIT_MS < page.lag_ms <= LIMIT_MS + BATCH_MS  # at the first check after the lag passed the limit
        assert page.eval_step is not None and page.train_step > page.eval_step


def test_tier_b_and_tier_c_rows_do_not_count():
    ch = FakeClickHouse()
    run = Run(ch).train(1, 1221, commit_first=True).score("tier-b", delay_s=159.0)
    ch.evals += [{"run_id": f"{RUN}:step-{s}:tier-c", "checkpoint_run": RUN, "checkpoint_step": s, "loaded_ms": T0}
                 for s, _ in run.commits]
    got = pages(sweep(monitor(ch, runs={RUN: RUN}), ch, T0, ms(run.t)))
    assert len(got) == 1 and got[0][1].eval_step is None
    assert sweep(monitor(ch), ch, T0, ms(run.t)) == []  # without --run, a run with no Tier A row is not checked


def test_a_finished_run_goes_quiet_and_its_lag_stops_growing():
    ch = FakeClickHouse()
    run = Run(ch).train(1, 1221, commit_first=True)
    end = run.t
    run.score(skip=lambda s: s > T0 / 1000 + 4_600)  # the last commit before the end is never scored
    results = sweep(monitor(ch, runs={RUN: RUN}), ch, T0, ms(end) + 3 * LIMIT_MS)
    assert pages(results) == []
    after_end = [c for now, c in results if now > ms(end + 1)]
    assert len({c.lag_ms for c in after_end if c.live}) == 1  # measured in training time, not on the clock
    assert not after_end[-1].live and "not training" in after_end[-1].status(T0 + 10**8)
    assert max(to_ms(r["checked_at"]) for r in ch.checks) <= ms(end + 1) + LIMIT_MS  # rows stop with the run


@pytest.mark.parametrize("resume_run", [RESUME, RUN])
def test_the_planned_failure_does_not_page(resume_run):
    ch = FakeClickHouse()
    run = Run(ch).train(1, 546, commit_first=True, killed=True)
    assert run.commits[-1][0] == 411  # kill (a) 135 steps (594 s) after the commit at step 411: the worst moment
    run.pause(300).train(412, 1221, resume_run).score()  # 5 minutes down, then --resume-committed from step 411
    results = sweep(monitor(ch, runs={RESUME: RUN, RUN: RUN}), ch, T0, ms(run.t) + 60_000)
    assert pages(results) == []
    assert max_lag(results) < LIMIT_MS
    assert results[-1][1].train_runs == tuple(sorted({RUN, resume_run}))  # both segments feed one eval run
    # Timing each step by when it was first reached, as metrics_raw would, pages on this restore:
    assert max(other_lag(ch, now, runs={RUN, RESUME}, restores=False) for now, _ in results) > LIMIT_MS


@pytest.mark.parametrize("dies_after_s, pages_before_kill", [(300, True), (1_500, False)])
def test_a_restore_does_not_hide_a_dead_watcher(dies_after_s, pages_before_kill):
    ch = FakeClickHouse()
    run = Run(ch).train(1, 546, commit_first=True, killed=True)  # kill (a), 594 s after the commit at step 411
    kill = run.t
    run.pause(300).train(412, 1221, RESUME)
    run.score(skip=lambda s: s > T0 / 1000 + dies_after_s)  # the Tier A watcher dies and never comes back
    got = pages(sweep(monitor(ch, runs={RUN: RUN, RESUME: RUN}), ch, T0, ms(run.t) + 60_000))
    assert len(got) == 1  # one outage, one page: the restore doesn't re-arm it
    now, page = got[0]
    assert LIMIT_MS < page.lag_ms <= LIMIT_MS + BATCH_MS
    assert (now < ms(kill)) == pages_before_kill
    assert now < ms(kill + 300) + LIMIT_MS  # a count started afresh at the restore would page only after this


def test_a_batch_of_blank_lines_changes_nothing():
    ch = FakeClickHouse()
    run = Run(ch).train(1, 1221, commit_first=True).score()
    clean = sweep(monitor(ch, runs={RUN: RUN}), ch, T0, ms(run.t))
    for b in ch.batches[::20]:  # watch_jsonl.py stores a batch of blank lines as steps 0..0
        ch.batches.append({**b, "first_step": 0, "last_step": 0, "lines": 0, "seen_ms": b["seen_ms"] + 500,
                           "start_offset": b["start_offset"] + 10**6})
    noisy = sweep(monitor(ch, runs={RUN: RUN}), ch, T0, ms(run.t))
    assert [(c.train_step, c.lag_ms) for _, c in noisy] == [(c.train_step, c.lag_ms) for _, c in clean]


def test_an_unmapped_resume_segment_looks_like_a_stopped_run():
    ch = FakeClickHouse()
    run = Run(ch).train(1, 546, commit_first=True, killed=True)
    kill = run.t
    run.pause(300).train(412, 1221, RESUME).score()
    results = sweep(monitor(ch, runs={RUN: RUN}), ch, T0, ms(run.t))
    assert pages(results) == []
    assert all(not c.live for now, c in results if now > ms(kill + 1) + LIMIT_MS)  # blind: map the segment


def test_a_trainer_pause_is_not_eval_lag():
    ch = FakeClickHouse()
    run = Run(ch).train(1, 600, commit_first=True)
    run.pause(900).train(601, 1221, new_process=False).score()  # the trainer stalls 15 minutes
    results = sweep(monitor(ch, runs={RUN: RUN}), ch, T0, ms(run.t) + 60_000)
    assert pages(results) == [] and max_lag(results) < LIMIT_MS
    assert max(other_lag(ch, now, runs={RUN}) for now, _ in results) > LIMIT_MS  # counting the pause in full would page


def test_no_tier_a_row_pages_after_the_limit():
    ch = FakeClickHouse()
    run = Run(ch).train(1, 1221, commit_first=True)  # the eval watcher never starts
    mon = monitor(ch, runs={RUN: RUN})
    ch.now_ms = T0 + 1_100_000
    assert [c.paged for c in mon.check(ch.now_ms)] == [False]
    got = pages(sweep(mon, ch, T0 + 1_100_000, ms(run.t)))
    assert len(got) == 1
    page = got[0][1]
    assert page.eval_step is None and LIMIT_MS < page.lag_ms <= LIMIT_MS + BATCH_MS
    assert "no tier-a score yet" in page.detail()


def test_training_restored_behind_the_scored_step_has_no_lag():
    ch = FakeClickHouse()
    run = Run(ch).train(1, 600, commit_first=True, killed=True)
    assert run.commits[-1][0] == 548
    run.pause(60).train(275, 900).score()  # restored further back than the scored step 548 (commit 548 lost)
    results = sweep(monitor(ch, runs={RUN: RUN}), ch, T0, ms(run.t) + 60_000)
    behind = [c for _, c in results if c.eval_step is not None and c.train_step < c.eval_step]
    assert behind and all(c.lag_ms == 0 for c in behind)
    assert pages(results) == []


def test_two_separate_runs_are_checked_on_their_own():
    ch = FakeClickHouse()
    healthy = Run(ch).train(1, 1221, commit_first=True).score()
    stopped = Run(ch).train(1, 1221, OTHER, commit_first=True).score(eval_run=OTHER, skip=lambda s: s > T0 / 1000 + 300)
    end = ms(max(healthy.t, stopped.t))
    for runs in ({RUN: RUN, OTHER: OTHER}, None):  # named with --run, and found by their Tier A rows
        ch.checks.clear()
        results = sweep(monitor(ch, runs=runs), ch, T0, end)
        assert [c.run_id for _, c in pages(results)] == [OTHER]
        assert {c.run_id for _, c in results} == {row["run_id"] for row in ch.checks} == {RUN, OTHER}
        assert max_lag([(now, c) for now, c in results if c.run_id == RUN]) < LIMIT_MS


# --- what it writes -------------------------------------------------------------------------------------------------

def test_rows_match_the_table_and_mark_the_page():
    columns = re.findall(r"^\s+([a-z_]+)\s+[A-Z]", TABLE_SQL.read_text(encoding="utf-8"), flags=re.M)
    ch = FakeClickHouse()
    run = Run(ch).train(1, 1221, commit_first=True)
    run.score(skip=lambda s: s > T0 / 1000 + 1_500)
    results = sweep(monitor(ch, runs={RUN: RUN}), ch, T0, ms(run.t))
    assert len(ch.ddl) == 1 and "ORDER BY (run_id, checked_at)" in ch.ddl[0]
    assert ch.checks and all(list(row) == columns for row in ch.checks)
    assert len(ch.checks) == sum(c.live for _, c in results)
    assert sum(row["paged"] for row in ch.checks) == len(pages(results)) == 1
    page_row = next(row for row in ch.checks if row["paged"])
    assert page_row["over_limit"] == 1 and page_row["train_runs"] == [RUN] and "behind" in page_row["detail"]
    assert all(row["detail"] == "" for row in ch.checks if not row["over_limit"])


def test_a_page_row_that_failed_to_save_is_written_next_time():
    ch = FakeClickHouse()
    Run(ch).train(1, 1221, commit_first=True).score(skip=lambda s: s > T0 / 1000 + 300)
    mon = monitor(ch, runs={RUN: RUN})
    ch.now_ms = T0 + 1_400_000
    checks = mon.check(ch.now_ms)
    assert [c.paged for c in checks] == [True]
    ch.error = TimeoutError("insert timed out")
    with pytest.raises(TimeoutError):
        mon.save(checks, ch.now_ms)
    ch.error, ch.now_ms = None, ch.now_ms + 60_000
    later = mon.check(ch.now_ms)
    assert [c.paged for c in later] == [False]  # the page fires once ...
    assert mon.save(later, ch.now_ms) == 2  # ... so its row goes with the next save, at its own time
    assert [(row["paged"], to_ms(row["checked_at"])) for row in ch.checks] == [(1, T0 + 1_400_000),
                                                                             (0, T0 + 1_460_000)]


def test_tsv_answers_are_unescaped():
    """ClickHouse's TabSeparated output escapes ' and \\ (seen on 24.8): a run id must come back as written."""
    assert tsv_fields("it\\'s\tback\\\\slash\ttab\\there\tplain") == ["it's", "back\\slash", "tab\there", "plain"]
    answer = "dryrun2-o\\'neil\t1795000000000\t7\n"
    mon = EvalLagMonitor(lambda sql, data=None: answer, interval_s=600, runs={"dryrun2-o'neil": "dryrun2-o'neil"})
    assert mon._newest_batches() == {"dryrun2-o'neil": (1_795_000_000_000, 7)}


def test_no_write_only_reads():
    ch = FakeClickHouse()
    Run(ch).train(1, 300, commit_first=True).score()
    mon = monitor(ch, runs={RUN: RUN}, write=False)
    ch.now_ms = T0 + 600_000
    assert mon.save(mon.check(ch.now_ms), ch.now_ms) == 0
    assert ch.ddl == [] and ch.checks == []


# --- the real dry run 1 log through the real watch_jsonl.py --------------------------------------------------------

def replay_dry_run_1(tmp_path, ch, tier_a_until_s=None):
    """Dry run 1's log at its real pace (perf/step_ms; 22 s for step 0, as replay_jsonl.py), flushed every 10 steps,
    killed as in drill (a) just before a commit and resumed into a fresh --out, each file loaded by a real
    watch_jsonl.Watcher. Tier A loads 230 s after each commit (until `tier_a_until_s`). The alarm checks every 60 s.
    Returns the (time, check) pairs and the kill."""
    lines = [ln for ln in DRYRUN1.read_text(encoding="utf-8").splitlines() if ln.strip()]
    step_s = [json.loads(ln).get("perf/step_ms", 22_000) / 1000 for ln in lines]
    clock_ms = [T0]
    paths = [tmp_path / RUN / "metrics.jsonl", tmp_path / RESUME / "metrics.jsonl"]
    for path in paths:
        path.parent.mkdir()
    watchers = [Watcher(path, exec_fn=ch, clock=lambda: _format_utc(
        datetime.fromtimestamp(clock_ms[0] / 1000, tz=timezone.utc))) for path in paths]

    events: list[tuple[int, int, object]] = []  # (time, order, action); writes before polls before loads at a tie
    t = last_commit = T0 / 1000
    commits, buffer, segment, kill, step = [(0, t)], [], 0, None, 0
    while step < len(lines):
        t += step_s[step]
        buffer.append(lines[step] + "\n")
        if step % 10 == 0 or step == len(lines) - 1:
            text, path, watcher = "".join(buffer), paths[segment], watchers[segment]
            events.append((ms(t), 0, lambda p=path, x=text: p.open("ab").write(x.encode("utf-8"))))
            events.append((ms(t + 1), 1, watcher.poll_once))
            buffer = []
        if step > 0 and t - last_commit >= INTERVAL_S:
            commits.append((step, t))
            last_commit = t
        nxt = step + 1
        if kill is None and len(commits) >= 3 and nxt < len(lines) and t + step_s[nxt] > commits[-1][1] + 595:
            kill = {"step": step, "ms": ms(t), "restored": commits[-1][0]}
            buffer, segment = [], 1  # SIGKILL loses the unflushed lines; run 2 writes a new file
            t += 300  # 5 minutes down
            last_commit, nxt = t, commits[-1][0] + 1  # --resume-committed restores the newest commit
        step = nxt
    for i, (s, tc) in enumerate(commits):
        loaded = tc + 230 + (159 if i % 10 == 9 else 0)
        if tier_a_until_s is None or loaded <= T0 / 1000 + tier_a_until_s:
            row = {"run_id": f"{RUN}:step-{s:08d}:tier-a:0123456789ab", "checkpoint_run": RUN, "checkpoint_step": s,
                   "loaded_ms": ms(loaded)}
            events.append((ms(loaded), 2, lambda r=row: ch.evals.append(r)))

    mon = monitor(ch, runs={RUN: RUN, RESUME: RUN})
    results = []

    def check(now):
        checks = mon.check(now)
        mon.save(checks, now)
        results.extend((now, c) for c in checks)

    for now in range(T0, ms(t) + 120_000, 60_000):
        events.append((now, 3, lambda n=now: check(n)))
    for when, _, action in sorted(events, key=lambda e: (e[0], e[1])):
        clock_ms[0] = when
        action()
    return results, kill


def test_dry_run_1_replay_with_kill_a_does_not_page(tmp_path):
    ch = FakeClickHouse()
    results, kill = replay_dry_run_1(tmp_path, ch)
    resumed = [b for b in ch.batches if b["run_id"] == RESUME]
    assert {b["run_id"] for b in ch.batches} == {RUN, RESUME}  # the resumed file arrives under its folder name
    assert resumed[0]["first_step"] == kill["restored"] + 1  # ... and starts with a step going back:
    assert resumed[0]["first_step"] <= max(b["last_step"] for b in ch.batches if b["run_id"] == RUN)
    assert resumed[-1]["last_step"] == 1221
    assert pages(results) == []
    assert 600_000 < max_lag(results) < LIMIT_MS


def test_dry_run_1_replay_pages_once_when_tier_a_stops(tmp_path):
    ch = FakeClickHouse()
    results, kill = replay_dry_run_1(tmp_path, ch, tier_a_until_s=300)  # only step 0 is ever scored
    got = pages(results)
    assert len(got) == 1
    now, page = got[0]
    assert page.eval_step == 0 and now < kill["ms"]
    assert LIMIT_MS < page.lag_ms <= LIMIT_MS + 60_000


# --- command line ---------------------------------------------------------------------------------------------------

def stopped_watcher_run():
    ch = FakeClickHouse()
    Run(ch).train(1, 1221, commit_first=True).score(skip=lambda s: s > T0 / 1000 + 300)
    ch.now_ms = T0 + 2_000_000
    return ch


def test_cli_once_prints_one_page_and_exits_1(capsys):
    ch = stopped_watcher_run()
    assert main(["--interval-s", "600", "--run", RUN, "--once"], exec_fn=ch, now_ms=lambda: ch.now_ms) == 1
    out, err = capsys.readouterr()
    event = json.loads(out)  # exactly one JSON line
    assert {"step", "metric", "rule", "severity", "detail"} <= set(event)
    assert (event["rule"], event["severity"], event["run_id"], event["eval_step"]) == ("eval_lag", "page", RUN, 0)
    assert f"eval_lag {RUN}: training step" in err and err.rstrip().endswith("PAGE")
    assert len(ch.ddl) == 1 and len(ch.checks) == 1


def test_cli_once_without_a_page_exits_0(capsys):
    ch = FakeClickHouse()
    Run(ch).train(1, 1221, commit_first=True).score()
    ch.now_ms = T0 + 2_000_000
    assert main(["--interval-s", "600", "--once", "--no-write"], exec_fn=ch, now_ms=lambda: ch.now_ms) == 0
    out, err = capsys.readouterr()
    assert out == "" and ": ok" in err and ch.checks == []


def test_cli_once_exits_2_when_clickhouse_is_down(capsys):
    ch = FakeClickHouse()
    ch.error = urllib.error.URLError("connection refused")
    assert main(["--interval-s", "600", "--once"], exec_fn=ch, now_ms=lambda: T0) == 2
    assert "URLError" in capsys.readouterr().err


def test_cli_names_a_missing_table(capsys):
    ch = FakeClickHouse()
    ch.error = RuntimeError("ClickHouse HTTP 404: Code: 60. DB::Exception: Unknown table expression identifier "
                            "'ingest_batches' in scope SELECT run_id FROM ingest_batches. (UNKNOWN_TABLE)")
    assert main(["--interval-s", "600", "--once"], exec_fn=ch, now_ms=lambda: T0) == 2
    err = capsys.readouterr().err
    assert "table ingest_batches is missing" in err and "watch_jsonl.py" in err


def test_cli_once_exits_2_not_1_on_an_unexpected_error(capsys):
    ch = FakeClickHouse()
    ch.error = KeyError("boom")  # a bug, not a ClickHouse error: exit 1 would read as a page
    assert main(["--interval-s", "600", "--once"], exec_fn=ch, now_ms=lambda: T0) == 2
    err = capsys.readouterr().err
    assert "unexpected KeyError" in err and "Traceback (most recent call last)" in err


def test_cli_poll_survives_an_unexpected_error(capsys):
    ch = FakeClickHouse()
    Run(ch).train(1, 300, commit_first=True).score()
    ch.now_ms = T0 + 600_000
    ch.error = KeyError("boom")
    naps = []

    def sleep(seconds):
        naps.append(seconds)
        if len(naps) == 2:
            raise KeyboardInterrupt
        ch.error = None

    assert main(["--interval-s", "600", "--run", RUN, "--poll", "5"], exec_fn=ch, now_ms=lambda: ch.now_ms,
                sleep=sleep) == 0
    err = capsys.readouterr().err
    assert "check failed (no complete check in the 0 s since start): unexpected KeyError" in err
    assert len(ch.checks) == 1  # the next check ran and wrote its row


def test_cli_startup_line_gives_the_settings_without_the_password(capsys):
    argv = ["--interval-s", "600", "--run", RUN, "--run", f"{RESUME}={RUN}", "--once", "--no-write",
            "--url", "http://alarm:hunter2@ch.example:8123"]
    main(argv, exec_fn=FakeClickHouse(), now_ms=lambda: T0)
    first = capsys.readouterr().err.splitlines()[0]
    assert first.startswith(_format_utc(datetime.fromtimestamp(T0 / 1000, tz=timezone.utc)) + " eval_lag: ")
    assert "eval_lag: http://ch.example:8123, limit" in first and "hunter2" not in first
    assert f"limit 1,200 s (2 x 600 s), label tier-a, runs {RUN}={RUN}, {RESUME}={RUN}," in first
    assert first.endswith("eval_lag_checks off, once")


def test_cli_poll_reports_errors_and_keeps_going(capsys):
    ch = FakeClickHouse()
    Run(ch).train(1, 300, commit_first=True).score()
    ch.now_ms = T0 + 600_000
    naps = []

    def sleep(seconds):
        naps.append(seconds)
        if len(naps) == 3:
            raise KeyboardInterrupt
        ch.error = ConnectionError("refused") if len(naps) == 1 else None

    argv = ["--interval-s", "600", "--run", RUN, "--poll", "5"]
    assert main(argv, exec_fn=ch, now_ms=lambda: ch.now_ms, sleep=sleep) == 0
    err = capsys.readouterr().err
    assert naps == [5.0, 5.0, 5.0]
    assert "ConnectionError: refused" in err and "since the last complete check" in err
    assert len(ch.checks) == 2  # the two complete checks wrote their rows


@pytest.mark.parametrize("argv", [
    [],  # --interval-s is required: the main run's interval is not dry run 2's
    ["--interval-s", "0"],
    ["--interval-s", "nan"],
    ["--interval-s", "600", "--run", "=x"],
    ["--interval-s", "600", "--run", "a="],
    ["--interval-s", "600", "--run", "a=b", "--run", "a=c"],
    ["--interval-s", "600", "--label", "tier:a"],
    ["--interval-s", "600", "--once", "--poll", "5"],
])
def test_cli_rejects_bad_arguments(argv):
    with pytest.raises(SystemExit) as exc:
        main(argv, exec_fn=FakeClickHouse())
    assert exc.value.code == 2


# --- Grafana panels 29 to 31 -----------------------------------------------------------------------------------------

def lag_panels():
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    return dashboard, {p["id"]: p for p in dashboard["panels"] if p["id"] in (29, 30, 31)}


def test_grafana_panels_read_only_eval_lag_checks_columns():
    dashboard, panels = lag_panels()
    ids = [p["id"] for p in dashboard["panels"]]
    assert len(ids) == len(set(ids)) and sorted(panels) == [29, 30, 31]
    assert [panels[i]["type"] for i in (29, 30, 31)] == ["timeseries", "table", "stat"]

    def box(p):
        g = p["gridPos"]
        return g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"]

    for new in panels.values():
        x0, y0, x1, y1 = box(new)
        assert x1 <= 24
        for other in dashboard["panels"]:
            a0, b0, a1, b1 = box(other)
            assert other is new or x1 <= a0 or a1 <= x0 or y1 <= b0 or b1 <= y0, (new["id"], other["id"])

    # Their own run list: $eval_run comes from eval_mini, so it lacks a run whose watcher never started.
    variables = {v["name"]: v for v in dashboard["templating"]["list"]}
    assert variables["lag_run"]["query"] == "SELECT DISTINCT run_id FROM eval_lag_checks ORDER BY run_id"
    assert variables["lag_run"]["multi"] and variables["lag_run"]["includeAll"]

    columns = set(re.findall(r"^\s+([a-z_]+)\s+[A-Z]", TABLE_SQL.read_text(encoding="utf-8"), flags=re.M))
    allowed = columns | {"eval_lag_checks", "lag_run", "time", "series", "value", "concat", "count", "max"}
    source = {"type": "grafana-clickhouse-datasource", "uid": "${ds}"}
    for p in panels.values():
        assert p["datasource"] == source
        for target in p["targets"]:
            sql = target["rawSql"]
            assert target["datasource"] == source
            assert re.search(r"FROM eval_lag_checks WHERE (paged = 1 AND )?run_id IN \(\$lag_run\)", sql), sql
            assert ("$__timeFilter(checked_at)" in sql) == (p["id"] != 31)  # the stat looks at the newest row only
            words = set(re.findall(r"\b[a-z][a-z_]*\b", re.sub(r"'[^']*'", "", sql)))
            assert words <= allowed, words - allowed  # a misspelt column fails here, before any Grafana sees it


# --- live ClickHouse (CI: GitHub Actions with clickhouse-server 24.8) -----------------------------------------------

def grafana_sql(sql, runs, start_ms, end_ms):
    """A panel's rawSql with Grafana's $lag_run and $__timeFilter(checked_at) filled in."""
    return (sql.replace("$lag_run", ", ".join(f"'{r}'" for r in runs))
               .replace("$__timeFilter(checked_at)", f"checked_at >= toDateTime({start_ms // 1000}) "
                                                     f"AND checked_at <= toDateTime({end_ms // 1000 + 1})"))


@pytest.mark.skipif(not LIVE_URL, reason="set CLICKHOUSE_URL to run the live ClickHouse test (it fails if that "
                                         "server is down)")
def test_live_clickhouse_end_to_end(tmp_path):
    """The real loaders, the alarm's SQL and table, the CLI and the Grafana panels' SQL on a real ClickHouse.

    Run A trains steps 0..400, is killed, and resumes from its commit at step 300 under a second run id (as the
    kill drill's fresh --out does); Tier A keeps up. Run B trains with Tier A stopped after step 0. Interval 300 s,
    so the limit is 600 s. Both runs end 29 s before now, so they count as training. Every row uses a
    `pytest_evallag_<pid>` prefix and is deleted at the end.
    """
    prefix = f"pytest_evallag_{os.getpid()}"
    run_a, resume_a, run_b = f"{prefix}_a", f"{prefix}_a-resume-a", f"{prefix}_b"

    def exec_live(sql, data=None):
        return ch_Exec(sql, data=data, url=LIVE_URL)

    def rows(sql):
        return [tsv_fields(line) for line in exec_live(f"{sql} FORMAT TabSeparated").splitlines() if line]

    lines = [ln for ln in DRYRUN1.read_text(encoding="utf-8").splitlines() if ln.strip()]
    template = json.loads(EVAL_TEMPLATE.read_text(encoding="utf-8"))["records"][0]
    now = int(time.time() * 1000)
    t0 = now - 1_530_000
    clock = [t0]

    def train(train_run, first, last, start_ms):
        """Steps first..last of the dry run 1 log, 2 s each, flushed every 10 steps, loaded by a real Watcher."""
        path = tmp_path / train_run / "metrics.jsonl"
        path.parent.mkdir()
        watcher = Watcher(path, exec_fn=exec_live,
                          clock=lambda: _format_utc(datetime.fromtimestamp(clock[0] / 1000, tz=timezone.utc)))
        for start in range(first, last + 1, 10):
            chunk = lines[start:min(start + 10, last + 1)]
            with path.open("ab") as f:
                f.write("".join(ln + "\n" for ln in chunk).encode("utf-8"))
            clock[0] = start_ms + (start - first + len(chunk)) * 2_000 + 1_000
            assert watcher.poll_once() is not None

    def tier_a(eval_run, step):
        record = dict(template, hardware="ci", checkpoint={"run": eval_run, "branch": "main", "step": step,
                                                           "epoch": None, "tokens_seen": None,
                                                           "path": f"step-{step:08d}"})
        path = tmp_path / f"{eval_run}.step-{step}.json"
        path.write_text(json.dumps({"schema_version": "eval_mini_v1", "records": [record]}), encoding="utf-8")
        load_source(str(path), run_id_override=f"{eval_run}:step-{step:08d}:tier-a:0123456789ab", url=LIVE_URL)

    prepare_schema(url=LIVE_URL)
    try:
        train(run_a, 0, 400, t0)  # commits at steps 0, 150 and 300 (every 300 s)
        train(resume_a, 301, 600, t0 + 900_000)  # killed at 400, 100 s down, restored from 300
        train(run_b, 0, 750, t0)
        for step in (0, 150, 300, 450):  # 450: the first commit after the restore, scored 60 s after it
            tier_a(run_a, step)
        tier_a(run_b, 0)
        assert rows(f"SELECT min(first_step) FROM ingest_batches WHERE run_id = '{resume_a}'") == [["301"]]

        mon = EvalLagMonitor(exec_live, interval_s=300, runs={run_a: run_a, resume_a: run_a, run_b: run_b})
        checks = {c.run_id: c for c in mon.check(now)}
        a, b = checks[run_a], checks[run_b]
        # A: from the resumed batch that reached step 450 (t0+1,201 s) to its newest (t0+1,501 s).
        assert (a.train_runs, a.train_step, a.eval_step, a.lag_ms, a.paged) == ((run_a, resume_a), 600, 450,
                                                                                  300_000, False)
        # B: from its first batch (t0+21 s) to its newest (step 750, t0+1,503 s).
        assert (b.train_step, b.eval_step, b.lag_ms, b.paged) == (750, 0, 1_482_000, True)
        assert mon.save(list(checks.values()), now) == 2
        nullable_time = "Nullable(DateTime64(3, 'UTC'))"
        assert rows(f"SELECT run_id, train_runs, train_step, eval_step, lag_s, threshold_s, over_limit, paged, "
                    f"toTypeName(eval_loaded_at) FROM eval_lag_checks WHERE startsWith(run_id, '{prefix}') "
                    f"ORDER BY run_id") == [
            [run_a, f"['{run_a}','{resume_a}']", "600", "450", "300", "600", "0", "0", nullable_time],
            [run_b, f"['{run_b}']", "750", "0", "1482", "600", "1", "1", nullable_time],
        ]

        _, panels = lag_panels()
        sql = {(i, t["refId"]): grafana_sql(t["rawSql"], (run_a, run_b), t0, now)
               for i, p in panels.items() for t in p["targets"]}
        assert sorted(r[1] for r in rows(sql[29, "A"])) == [f"{run_a} lag", f"{run_b} lag"]
        assert sorted(r[2] for r in rows(sql[29, "B"])) == ["600", "600"]
        assert [r[1:5] for r in rows(sql[30, "A"])] == [[run_b, "750", "0", "1482"]]
        assert 0 <= int(rows(sql[31, "A"])[0][0]) < 600

        cli = subprocess.run(
            [sys.executable, "-B", str(ALARMS / "eval_lag.py"), "--once", "--no-write", "--url", LIVE_URL,
             "--interval-s", "300", "--run", run_a, "--run", f"{resume_a}={run_a}", "--run", run_b],
            capture_output=True, text=True, timeout=120)
        assert cli.returncode == 1, cli.stderr
        assert [json.loads(line)["run_id"] for line in cli.stdout.splitlines()] == [run_b]
    finally:
        for table in ("metrics_raw", "ingest_batches", "eval_mini", "ingest_manifest", "eval_lag_checks"):
            with contextlib.suppress(Exception):  # a table the failed test never created
                exec_live(f"ALTER TABLE {table} DELETE WHERE startsWith(run_id, '{prefix}') "
                          "SETTINGS mutations_sync = 2")
