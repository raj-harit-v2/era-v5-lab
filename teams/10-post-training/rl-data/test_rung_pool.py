"""Tests for rung_pool.py: selection rule, tercile cut, unfiltered rest sample, determinism, input checks."""
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g10_rung_pool", HERE / "rung_pool.py")
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)


def _tasks():
    judges = ["codechef", "hackerearth", "aizu", "atcoder"]
    return [{"id": f"t{i:02d}", "judge": judges[i % 4], "statement": "x " * (i + 1)} for i in range(24)]


def test_tercile_cut_matches_screen_ladder_rule():
    assert rp.tercile_cut([5, 1, 3, 9, 7, 2]) == sorted([5, 1, 3, 9, 7, 2])[6 // 3]


def test_rule_selects_judge_and_short_only():
    tasks = _tasks()
    pool = [t["id"] for t in tasks]
    lengths = {t["id"]: i for i, t in enumerate(tasks)}
    res = rp.build(tasks, pool, lengths, rest_sample=0)
    assert res["cut"] == 8
    by = {t["id"]: t for t in tasks}
    for i in res["rung1"]:
        assert by[i]["judge"] in ("codechef", "hackerearth") and lengths[i] <= 8
    expected = {t["id"] for i, t in enumerate(tasks) if t["judge"] in ("codechef", "hackerearth") and i <= 8}
    assert set(res["rung1"]) == expected
    assert set(res["rung1"]).isdisjoint(res["rest"]) and set(res["rung1"]) | set(res["rest"]) == set(pool)


def test_rest_sample_is_unfiltered_and_deterministic():
    tasks = _tasks()
    pool = [t["id"] for t in tasks]
    lengths = {t["id"]: i for i, t in enumerate(tasks)}
    a = rp.build(tasks, pool, lengths, rest_sample=6, seed=7)
    b = rp.build(tasks, pool, lengths, rest_sample=6, seed=7)
    assert a["rest_sample"] == b["rest_sample"] and len(a["rest_sample"]) == 6
    assert set(a["rest_sample"]) <= set(a["rest"])


def test_pool_outside_task_file_and_duplicates_are_errors():
    tasks = _tasks()
    lengths = {t["id"]: 1 for t in tasks}
    with pytest.raises(ValueError):
        rp.build(tasks, ["nope"], lengths)
    with pytest.raises(ValueError):
        rp.build(tasks, ["t00", "t00"], lengths)


def test_cli_writes_ids_and_manifest_without_ids(tmp_path):
    from tokenizers import Tokenizer, models, pre_tokenizers  # noqa: PLC0415
    tasks = _tasks()
    (tmp_path / "cc.jsonl").write_text("".join(json.dumps(t) + "\n" for t in tasks))
    (tmp_path / "pool.txt").write_text("\n".join(t["id"] for t in tasks[:20]))
    tok = Tokenizer(models.WordLevel({"x": 0, "[UNK]": 1}, unk_token="[UNK]"))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    tok.save(str(tmp_path / "tok.json"))
    out = tmp_path / "out"
    assert rp.main(["--tasks", str(tmp_path / "cc.jsonl"), "--pool", str(tmp_path / "pool.txt"), "--tokenizer",
                    str(tmp_path / "tok.json"), "--out-dir", str(out), "--rest-sample", "4"]) == 0
    man = json.loads((out / "rung_pool_manifest.json").read_text())
    rung = (out / "rung1_ids.txt").read_text().split()
    assert man["counts"]["rung1"] == len(rung) and man["counts"]["pool"] == 20
    assert not any(i in json.dumps(man) for i in rung)  # the publishable manifest carries no ids


def test_unused_tests_follow_the_kept_prefix_in_builder_order():
    spec2 = importlib.util.spec_from_file_location("g10_fetch_unused", HERE / "fetch_unused_tests.py")
    fu = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(fu)
    row = {"public_tests": {"input": ["1"], "output": ["a"]}, "private_tests": {"input": ["2", "3"], "output": ["b", "c"]},
           "generated_tests": {"input": ["4"], "output": ["d"]}}
    kept = [{"input": "1", "output": "a"}, {"input": "2", "output": "b"}]
    assert fu.unused_tests(row, kept, 5) == [{"input": "3", "output": "c"}, {"input": "4", "output": "d"}]
    assert fu.unused_tests(row, kept, 1) == [{"input": "3", "output": "c"}]
    assert fu.unused_tests(row, [{"input": "9", "output": "z"}], 5) is None
