"""Tests for compare_rotation.py (attn-3 at seed 1240).

Run from the repo root:
    python -m pytest teams/05-architecture/jobs/evidence/2026-11-17-rotation-attn3-seed1240/test_compare_rotation.py -q
"""
import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from compare_rotation import check_run, main, not_worse, seed_stats  # noqa: E402

PR462_REFERENCE = [1.7673, 1.7796, 1.7792, 1.7542]


def test_seed_stats_reproduces_pr462_reference():
    s = seed_stats(PR462_REFERENCE)
    assert s["n"] == 4
    assert round(s["mean"], 4) == 1.7701
    assert round(s["range"], 4) == 0.0254
    assert round(s["sd"], 4) == 0.0120


def test_seed_stats_single_value():
    s = seed_stats([1.7650])
    assert s["n"] == 1 and s["range"] == 0.0 and s["sd"] is None


def test_not_worse_single_candidate_seed():
    r = not_worse([1.7650], PR462_REFERENCE)
    assert r["allowance"] == pytest.approx(0.0254)
    assert r["passes"] is True and r["formal"] is False


def test_not_worse_fails_beyond_allowance():
    assert not_worse([1.80], PR462_REFERENCE)["passes"] is False


def test_check_run_rejects_short_run():
    c = check_run({"steps": 1044, "timed_out": True}, [{"step": 1, "loss": 7.0}])
    assert c["C1_complete"] is False
    assert c["status"] == "INCOMPLETE_NOT_A_RESULT"


def test_check_run_rejects_nan():
    c = check_run({"steps": 1221, "timed_out": False}, [{"step": 1, "loss": float("nan")}])
    assert c["C2_finite"] is False
    assert c["status"] == "VOID_NONFINITE"


def test_check_run_ok():
    c = check_run({"steps": 1221, "timed_out": False}, [{"step": 1221, "val/bpb": 1.76}])
    assert c == {"C1_complete": True, "C2_finite": True, "status": "OK"}


COMPLETE_RUN = {"steps": 1221, "timed_out": False, "source": "test fixture comment"}


def _write_table(tmp_path, **overrides):
    table = {
        "source": "test fixture",
        "reference": {
            "bpb": {str(s): v for s, v in zip(range(1234, 1238), PR462_REFERENCE)},
            "three_group": {"1234": 1.93, "1235": 1.94, "1236": 1.935},
        },
        "attn3": {},
        "attn3_1240": {"bpb": 1.7650, "three_group": 1.932, "code": None, "indic": None},
        "attn3_1240_run": COMPLETE_RUN,
    }
    table.update(overrides)
    tpath = tmp_path / "t2_table.json"
    tpath.write_text(json.dumps(table))
    return tpath


def _rows(out):
    return {(r["reading"], r["metric"]): r for r in csv.DictReader(out.open())}


def test_compare_without_run_dir(tmp_path):
    out = tmp_path / "rotation-comparison.csv"
    assert main(["--table", str(_write_table(tmp_path)), "--out", str(out)]) == 0
    rows = list(csv.DictReader(out.open()))
    assert [(r["reading"], r["metric"]) for r in rows] == [
        (reading, m)
        for reading in ("seed_1240_alone", "all_seeds")
        for m in ("three_group", "code", "indic", "bpb")
    ]
    tg = _rows(out)[("seed_1240_alone", "three_group")]
    assert tg["passes"] == "True" and tg["formal"] == "False"
    assert float(tg["diff"]) == pytest.approx(1.932 - 1.935, abs=1e-6)


def test_bpb_row_has_no_verdict(tmp_path):
    # The not-worse rule covers three-group, code and Indic only; bpb gets the gap and spread, no verdict.
    out = tmp_path / "rotation-comparison.csv"
    assert main(["--table", str(_write_table(tmp_path)), "--out", str(out)]) == 0
    bpb = _rows(out)[("seed_1240_alone", "bpb")]
    assert float(bpb["diff"]) == pytest.approx(1.7650 - 1.7701, abs=1e-4)
    assert bpb["passes"] == "" and bpb["formal"] == ""


def test_two_readings_and_1240_not_double_counted(tmp_path):
    tpath = _write_table(tmp_path, attn3={"three_group": {"1234": 1.931, "1235": 1.933, "1240": 1.932}})
    out = tmp_path / "rotation-comparison.csv"
    assert main(["--table", str(tpath), "--out", str(out)]) == 0
    rows = _rows(out)
    assert rows[("seed_1240_alone", "three_group")]["attn3_n"] == "1"
    pooled = rows[("all_seeds", "three_group")]
    assert pooled["attn3_n"] == "3"
    assert float(pooled["attn3_mean"]) == pytest.approx((1.931 + 1.933 + 1.932) / 3)


def test_table_value_without_complete_run_block_refused(tmp_path):
    out = tmp_path / "rotation-comparison.csv"
    for run in (None, {"steps": 1044, "timed_out": True, "source": "comment"}):
        assert main(["--table", str(_write_table(tmp_path, attn3_1240_run=run)), "--out", str(out)]) == 2
        assert not out.exists()


def test_run_dir_missing_summary_is_incomplete(tmp_path):
    # At 71bc0fb a non-finite value raises inside the loop, so summary.json is never written.
    run = tmp_path / "run"
    run.mkdir()
    (run / "metrics.jsonl").write_text(json.dumps({"step": 10, "loss": 7.0}) + "\n")
    tpath = _write_table(tmp_path, attn3_1240=None, attn3_1240_run=None)
    out = tmp_path / "rotation-comparison.csv"
    assert main(["--table", str(tpath), "--run-dir", str(run), "--out", str(out)]) == 2
    assert not out.exists()


def test_run_dir_without_final_eval_refused(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "summary.json").write_text(json.dumps({"steps": 1221, "timed_out": False}))
    (run / "metrics.jsonl").write_text(json.dumps({"step": 1221, "loss": 6.2}) + "\n")
    tpath = _write_table(tmp_path)
    out = tmp_path / "rotation-comparison.csv"
    assert main(["--table", str(tpath), "--run-dir", str(run), "--out", str(out)]) == 2
    assert not out.exists()


def test_compare_refuses_verdict_for_incomplete_run(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "summary.json").write_text(json.dumps({"steps": 900, "timed_out": True}))
    (run / "metrics.jsonl").write_text(json.dumps({"step": 900, "val/bpb": 1.8}) + "\n")
    tpath = tmp_path / "t2_table.json"
    tpath.write_text(json.dumps({"source": "x", "reference": {}, "attn3": {}, "attn3_1240": None}))
    out = tmp_path / "rotation-comparison.csv"
    assert main(["--table", str(tpath), "--run-dir", str(run), "--out", str(out)]) == 2
    assert not out.exists()
