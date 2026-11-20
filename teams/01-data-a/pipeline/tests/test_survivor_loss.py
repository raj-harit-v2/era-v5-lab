"""Tests for survivor_loss.py: dedup groups whose survivor F2 dropped. Synthetic dedup_groups.csv and F2 reports only.

  python -m pytest teams/01-data-a/pipeline/tests -q
"""
import csv
import json
import subprocess
import sys

import pytest

from conftest import PIPELINE
import survivor_loss as sl

SET = "2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a"
GROUP_HEADER = ["group_id", "group_size", "priority_rule", "role", "pack_id", "split", "part", "row_in_part", "doc_id"]

GROUPS = [
    # g1: one survivor, F2 drops it -> lost
    ["G000001", 2, 4, "survivor", "code-go", "train", "code-go/part-00000.parquet", 0, "a"],
    ["G000001", 2, 4, "removed", "code-go", "train", "code-go/part-00001.parquet", 3, "a2"],
    # g2: two held-out survivors, F2 drops one -> partly hit
    ["G000002", 3, 0, "survivor", "code-go", "heldout", "code-go/part-00000.parquet", 0, "h0"],
    ["G000002", 3, 0, "survivor", "code-go", "heldout", "code-go/part-00000.parquet", 1, "h1"],
    ["G000002", 3, 0, "removed", "code-go", "train", "code-go/part-00000.parquet", 1, "b"],
    # g3: survivor untouched by F2
    ["G000003", 2, 3, "survivor", "en-dclm", "train", "en-dclm/part-00000.parquet", 0, "e0"],
    ["G000003", 2, 3, "removed", "en-dclm", "train", "en-dclm/part-00000.parquet", 1, "e1"],
    # g4: no usable licence, no survivor at all
    ["G000004", 2, 1, "removed", "code-go", "train", "code-go/part-00000.parquet", 2, "c"],
    ["G000004", 2, 1, "removed", "en-dclm", "train", "en-dclm/part-00000.parquet", 2, "c2"],
]

# F2 reports as run_f2.py writes them, one per part, at <final>/<split>/<part>.f2.json
F2 = {
    ("train", "code-go/part-00000.parquet"): [{"doc_id": "a", "items": ["gsm8k:12"], "offset": 40}],
    ("train", "code-go/part-00001.parquet"): [{"doc_id": "x9", "items": ["mmlu:3"], "offset": 0}],
    ("train", "en-dclm/part-00000.parquet"): [],
    ("heldout", "code-go/part-00000.parquet"): [{"doc_id": "h1", "items": ["era-v5-lab:canary"], "offset": 5}],
}


@pytest.fixture
def groups(tmp_path):
    def write(rows=GROUPS):
        path = tmp_path / "dedup_groups.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(GROUP_HEADER)
            w.writerows(rows)
        return path
    return write


@pytest.fixture
def final(tmp_path):
    def write(reports=F2, set_sha=SET):
        root = tmp_path / "final"
        for (split, part), dropped in reports.items():
            path = root / split / (part + ".f2.json")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"input": f"somewhere/{part}", "set_sha256": set_sha, "rows": 10,
                                        "kept": 10 - len(dropped), "dropped_by_f2": len(dropped), "errors": [],
                                        "dropped": dropped}), encoding="utf-8")
        return root
    return write


def test_lost_partly_hit_and_untouched(tmp_path, groups, final):
    s = sl.report(groups(), final(), tmp_path / "report")
    assert s["groups"] == {"total": 4, "with_survivor": 3, "without_survivor": 1, "with_several_survivors": 1,
                           "lost": 1, "partly_hit": 1, "untouched": 1}
    assert s["survivors_dropped_by_f2"] == 2
    assert s["set_sha256"] == SET
    with (tmp_path / "report" / "survivor_loss.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [(r["status"], r["group_id"], r["doc_id"], r["f2_items"]) for r in rows] == [
        ("lost", "G000001", "a", "gsm8k:12"), ("partly_hit", "G000002", "h1", "era-v5-lab:canary")]
    assert s["survivor_rows_by_pack"] == {"code-go": {"lost": 1, "partly_hit": 1}}


def test_matches_on_split_part_and_doc_id(tmp_path, groups, final):
    # F2 dropped a doc_id "a" in another part; the survivor "a" in part-00000 was kept
    reports = dict(F2)
    reports[("train", "code-go/part-00000.parquet")] = []
    reports[("train", "code-go/part-00001.parquet")] = [{"doc_id": "a", "items": ["gsm8k:1"], "offset": 0}]
    s = sl.report(groups(), final(reports), tmp_path / "report")
    assert s["groups"]["lost"] == 0


def test_f2_errors_count_as_gone(tmp_path, groups, final):
    reports = dict(F2)
    reports[("train", "code-go/part-00000.parquet")] = []
    root = final(reports)
    rep = root / "train" / "code-go" / "part-00000.parquet.f2.json"
    data = json.loads(rep.read_text(encoding="utf-8"))
    data["errors"] = [["a", "UnicodeDecodeError"]]
    rep.write_text(json.dumps(data), encoding="utf-8")
    s = sl.report(groups(), root, tmp_path / "report")
    assert s["groups"]["lost"] == 1
    with (tmp_path / "report" / "survivor_loss.csv").open(encoding="utf-8") as f:
        assert next(csv.DictReader(f))["f2_items"] == "error:UnicodeDecodeError"


def test_no_f2_drops(tmp_path, groups, final):
    s = sl.report(groups(), final({k: [] for k in F2}), tmp_path / "report")
    assert (s["groups"]["lost"], s["groups"]["partly_hit"], s["survivors_dropped_by_f2"]) == (0, 0, 0)


def test_stops_when_f2_did_not_cover_a_survivor_part(tmp_path, groups, final):
    reports = {k: v for k, v in F2.items() if k != ("train", "en-dclm/part-00000.parquet")}
    with pytest.raises(sl.Stop, match="no F2 report"):
        sl.report(groups(), final(reports), tmp_path / "report")


def test_stops_on_mixed_fingerprint_sets(tmp_path, groups, final):
    root = final()
    other = root / "train" / "en-dclm" / "part-00000.parquet.f2.json"
    data = json.loads(other.read_text(encoding="utf-8"))
    data["set_sha256"] = "0" * 64
    other.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(sl.Stop, match="set_sha256"):
        sl.report(groups(), root, tmp_path / "report")


def test_stops_on_wrong_groups_header(tmp_path, final):
    path = tmp_path / "dedup_groups.csv"
    path.write_text("group_id,doc_id\n1,a\n", encoding="utf-8")
    with pytest.raises(sl.Stop, match="header"):
        sl.report(path, final(), tmp_path / "report")


def test_outputs_hold_ids_only(tmp_path, groups, final):
    sl.report(groups(), final(), tmp_path / "report")
    s = json.loads((tmp_path / "report" / "survivor_loss_summary.json").read_text(encoding="utf-8"))
    assert len(s["groups_sha256"]) == 64 and len(s["code_sha256"]) == 64 and s["f2_reports"] == 4


def test_cli(tmp_path, groups, final):
    p = subprocess.run([sys.executable, "-I", str(PIPELINE / "survivor_loss.py"), "--groups", str(groups()),
                        "--f2", str(final()), "--out", str(tmp_path / "report")], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout)["lost"] == 1


def test_cli_exits_1_on_a_failed_check(tmp_path, final):
    bad = tmp_path / "dedup_groups.csv"
    bad.write_text("group_id,doc_id\nG000001,a\n", encoding="utf-8")
    p = subprocess.run([sys.executable, "-I", str(PIPELINE / "survivor_loss.py"), "--groups", str(bad),
                        "--f2", str(final()), "--out", str(tmp_path / "report")], capture_output=True, text=True)
    assert p.returncode == 1 and p.stderr.startswith("survivor_loss: ") and "header" in p.stderr
    assert not (tmp_path / "report" / "survivor_loss_summary.json").exists()


def test_no_groups(tmp_path, groups, final):
    """Dedup found no duplicates: every count is 0 and the CSV holds only its header."""
    s = sl.report(groups([]), final(), tmp_path / "report")
    assert s["groups"] == {"total": 0, "with_survivor": 0, "without_survivor": 0, "with_several_survivors": 0,
                           "lost": 0, "partly_hit": 0, "untouched": 0}
    assert s["survivors_dropped_by_f2"] == 0 and s["survivor_rows_by_pack"] == {}
    assert loss_rows(tmp_path / "report") == []


# --- the review of the scale pass (14 Nov) ---------------------------------------------------------------------------
def loss_rows(out):
    with (out / "survivor_loss.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_rows_follow_the_length_of_group_id_then_the_csv_order(tmp_path, groups, final):
    """The order before the scale pass: groups by (len(group_id), group_id), so G9 comes before G10, and a group's rows
    in the order of dedup_groups.csv."""
    part = "code-go/part-00000.parquet"
    rows = [["G10", 2, 4, "survivor", "code-go", "train", part, 2, "c"],
            ["G10", 2, 4, "survivor", "code-go", "train", part, 0, "a"],
            ["G9", 2, 4, "survivor", "code-go", "train", part, 1, "b"],
            ["G2", 2, 4, "survivor", "code-go", "train", part, 3, "d"]]
    reports = {("train", part): [{"doc_id": d, "items": ["x:1"], "offset": 0} for d in "abcd"]}
    sl.report(groups(rows), final(reports), tmp_path / "report")
    assert [(r["group_id"], r["doc_id"]) for r in loss_rows(tmp_path / "report")] == [
        ("G2", "d"), ("G9", "b"), ("G10", "c"), ("G10", "a")]


def test_a_doc_both_dropped_and_an_error_counts_once_as_the_error(tmp_path, groups):
    path = tmp_path / "final" / "train" / "code-go" / "part-00000.parquet.f2.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"set_sha256": SET, "rows": 3, "errors": [["a", "timeout"]],
                                "dropped": [{"doc_id": "a", "items": ["gsm8k:12"], "offset": 40}]}), encoding="utf-8")
    s = sl.report(groups(GROUPS[:2]), tmp_path / "final", tmp_path / "report")
    assert s["survivors_dropped_by_f2"] == 1
    assert [(r["doc_id"], r["f2_items"], r["offset"]) for r in loss_rows(tmp_path / "report")] == [("a", "error:timeout", "")]
