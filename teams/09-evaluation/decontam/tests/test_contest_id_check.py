"""Tests for contest_id_check.py (G9, week 3).

    pytest teams/09-evaluation/decontam/tests/test_contest_id_check.py -q

No network. The parquet test needs pyarrow (skipped without it).
"""

import json

import pytest

import contest_id_check as cic

BENCH = [2000, 2001, 2010]


def test_contest_id_from_field_id_forms_and_missing():
    assert cic.contest_of({"contest_id": "1990", "id": "x"}) == 1990
    assert cic.contest_of({"contest_id": 1990}) == 1990
    assert cic.contest_of({"id": "1990/A"}) == 1990
    assert cic.contest_of({"id": "cf_1990_B2"}) == 1990
    assert cic.contest_of({"id": "1990A"}) == 1990
    assert cic.contest_of({"id": "aizu_p01160_It_Prefokery_Pio"}) is None
    assert cic.contest_of({"id": ""}) is None
    assert cic.contest_of({}) is None


def test_distance_to_the_nearest_benchmark_contest():
    assert cic.nearest(2001, BENCH) == 0
    assert cic.nearest(2002, BENCH) == 1
    assert cic.nearest(2005, BENCH) == 4
    assert cic.nearest(1500, BENCH) == 500


def test_check_counts_rows_by_distance_and_lists_the_drop():
    rows = [{"id": "2000/A"}, {"id": "2000/B"}, {"id": "2002/A"}, {"id": "2004/A"}, {"id": "2007/A"},
            {"id": "1500/A"}, {"id": "no-contest"}]
    report, drop = cic.check(BENCH, rows, window=3)
    assert report["pool_rows"] == 7 and report["rows_without_contest_id"] == 1 and report["pool_contests"] == 5
    assert report["rows_in_benchmark_contest"] == 2          # 2000/A, 2000/B
    assert report["rows_within_1"] == 3                      # + 2002/A
    assert report["rows_within_window"] == 5                 # + 2004/A (distance 3 to 2001), 2007/A (3 to 2010)
    assert report["contests_within_window"]["2002"] == {"distance": 1, "rows": 1}
    assert report["contests_within_window"]["2007"] == {"distance": 3, "rows": 1}
    assert "1500" not in report["contests_within_window"]
    assert drop == ["2000/A", "2000/B", "2002/A", "2004/A", "2007/A"]


def test_window_zero_keeps_only_benchmark_contests():
    report, drop = cic.check(BENCH, [{"id": "2000/A"}, {"id": "2002/A"}], window=0)
    assert report["rows_within_window"] == 1 and drop == ["2000/A"]


def test_report_has_no_text_and_main_writes_the_files(tmp_path, capsys):
    bench = tmp_path / "bench.json"
    bench.write_text(json.dumps(BENCH), encoding="utf-8")
    pool = tmp_path / "pool.jsonl"
    pool.write_text("".join(json.dumps(r) + "\n" for r in [
        {"id": "2002/A", "text": "SECRET PROBLEM TEXT"}, {"id": "1500/A", "text": "other"}]), encoding="utf-8")
    out, drop = tmp_path / "r.json", tmp_path / "drop.txt"
    assert cic.main(["--benchmark", str(bench), "--pool", str(pool), "--out", str(out), "--drop", str(drop)]) == 0
    shown = capsys.readouterr().out
    assert "SECRET" not in shown and "SECRET" not in out.read_text(encoding="utf-8")
    assert json.loads(out.read_text(encoding="utf-8"))["rows_within_1"] == 1
    assert drop.read_text(encoding="utf-8") == "2002/A\n"
    first = out.read_text(encoding="utf-8")
    cic.main(["--benchmark", str(bench), "--pool", str(pool), "--out", str(out)])
    assert out.read_text(encoding="utf-8") == first         # a rerun gives the same bytes


def test_empty_benchmark_is_refused(tmp_path):
    bench = tmp_path / "bench.json"
    bench.write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit):
        cic.benchmark_contests(bench)


def test_benchmark_from_parquet(tmp_path):
    pq = pytest.importorskip("pyarrow.parquet")
    pa = pytest.importorskip("pyarrow")
    path = tmp_path / "test.parquet"
    pq.write_table(pa.table({"contest_id": ["2001", "2000", "2001"], "title": ["a", "b", "c"]}), path)
    assert cic.benchmark_contests(path) == [2000, 2001]
