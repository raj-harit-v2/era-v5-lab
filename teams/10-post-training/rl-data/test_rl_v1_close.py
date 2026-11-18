"""Tests for rl_v1_close.py (G10): RL data v1 pool flags. Toy tasks only, no data, no network.

    pytest teams/10-post-training/rl-data/test_rl_v1_close.py -q
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rl_v1_close as rc  # noqa: E402

LONG = "Given N integers, print their sum modulo the prime given on the second line of the input.\n\nInput\n..."
SHORT = "Example\n\nInput\n\n3\n\nOutput\n\n6"


def task(i, judge, statement=LONG):
    return {"id": f"cc-{judge}-{i}", "judge": judge, "statement": statement}


CC = [task(1, "aizu"), task(2, "aizu", SHORT), task(3, "codechef"), task(4, "hackerearth"), task(5, "atcoder"),
      task(6, "atcoder")]
MATH = [{"id": "math-toy-0"}, {"id": "math-toy-1"}]
EFFORT = {"training_exclusion": {"task_ids": ["cc-atcoder-6", "math-toy-1"]}}


def test_applied_flags_shrink_the_pool_and_python2_is_sized_not_applied():
    out, private = rc.close(CC, MATH, EFFORT)
    f, p = out["flags"], out["parts"]
    assert f["statement_less"]["tasks"] == 1 and f["statement_less"]["applied"] is True
    assert (f["effort_suite"]["present_in_code"], f["effort_suite"]["present_in_math"], f["effort_suite"]["listed_not_in_v1"]) == (1, 1, 0)
    assert p["code"]["pool_tasks"] == 4 and private["code_pool_ids.txt"] == {"cc-aizu-1", "cc-codechef-3", "cc-hackerearth-4", "cc-atcoder-5"}
    assert f["python2_only"]["applied"] is False and f["python2_only"]["in_pool_after_other_flags"] == 2
    assert f["python2_only"]["outcome_keep"]["code_pool_tasks"] == 4 and f["python2_only"]["outcome_drop"]["code_pool_tasks"] == 2
    assert p["math"]["reserved_tasks"] == 1 and "reserved" in p["math"]["status"]


def test_each_flag_is_reversed_or_applied_by_its_switch():
    out, _ = rc.close(CC, MATH, EFFORT, keep_statement_less=True, drop_python2=True)
    assert out["flags"]["statement_less"]["applied"] is False and out["flags"]["python2_only"]["applied"] is True
    assert out["parts"]["code"]["pool_tasks"] == 3  # aizu-1, aizu-2 (kept), atcoder-5; codechef/hackerearth dropped
    assert out["flags"]["python2_only"]["outcome_keep"]["code_pool_tasks"] == 5


def test_ids_never_reach_the_public_body():
    out, _ = rc.close(CC, MATH, EFFORT)
    text = repr(out)
    assert not any(t["id"] in text for t in CC) and "math-toy" not in text


def test_the_evaluation_firewall_splits_the_close_pool_without_changing_it():
    base, base_private = rc.close(CC, MATH, EFFORT)
    out, private = rc.close(CC, MATH, EFFORT, rl_heldout={"cc-aizu-1", "cc-atcoder-6"}, sft_heldout_match={"cc-codechef-3", "cc-aizu-1"})
    code = out["parts"]["code"]
    assert code["pool_tasks"] == base["parts"]["code"]["pool_tasks"] and private["code_pool_ids.txt"] == base_private["code_pool_ids.txt"]
    assert private["code_train_pool_ids.txt"] == base_private["code_pool_ids.txt"] - {"cc-aizu-1", "cc-codechef-3"}
    assert code["train_pool_tasks"] == code["pool_tasks"] - 2
    h = out["flags"]["rl_heldout_v1"]
    assert (h["listed"], h["in_close_pool"], h["outside_close_pool"]) == (2, 1, 1)  # cc-atcoder-6 is an effort-suite task
    assert out["flags"]["sft_heldout"]["also_rl_heldout"] == 1 and out["parts"]["heldout"]["tasks"] == 2
    assert "cc-aizu-1" not in str(out)  # ids stay private
    import pytest
    with pytest.raises(ValueError):
        rc.close(CC, MATH, EFFORT, rl_heldout={"cc-nowhere-9"})
