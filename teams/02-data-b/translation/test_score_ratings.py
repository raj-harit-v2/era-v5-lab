"""Tests for score_ratings.py.  Run:  python3 test_score_ratings.py"""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_ratings as sr  # noqa: E402


class ScoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def sheet(self, name, scores):
        rows = ["doc_id,shared,score,note"] + [f"{d},,{s}," for d, s in scores.items()]
        (self.tmp / name).write_text("\n".join(rows) + "\n", encoding="utf-8")

    def run_tool(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = sr.main([str(self.tmp)])
        return code, out.getvalue(), err.getvalue()

    def test_twenty_shared_with_80_percent_within_one_point_passes(self):
        self.sheet("te_amy.csv", {f"d{i}": 3 for i in range(20)})
        self.sheet("te_bob.csv", {f"d{i}": (4 if i < 16 else 5) for i in range(20)})  # 16 of 20 within 1 point
        code, out, _ = self.run_tool()
        self.assertEqual(code, 0)
        self.assertIn("| te | amy, bob | 20 | 16 (80%) | PASS |", out)

    def test_below_80_percent_fails_and_fewer_than_20_is_reported(self):
        self.sheet("kn_amy.csv", {f"d{i}": 1 for i in range(20)})
        self.sheet("kn_bob.csv", {f"d{i}": (5 if i < 5 else 2) for i in range(20)})  # 15 of 20 within 1 point
        self.sheet("ta_cat.csv", {f"d{i}": 4 for i in range(10)})
        self.sheet("ta_dan.csv", {f"d{i}": 4 for i in range(10)})
        out = self.run_tool()[1]
        self.assertIn("| kn | amy, bob | 20 | 15 (75%) | FAIL |", out)
        self.assertIn("too few shared documents (10 of 20)", out)

    def test_quality_counts_a_shared_document_once(self):
        self.sheet("hi_amy.csv", {"d1": 5, "d2": 3})
        self.sheet("hi_bob.csv", {"d1": 3})  # d1 averages to 4; mean of 4 and 3 is 3.50
        self.assertIn("| hi | 2 | 2 | 3.50 |", self.run_tool()[1])

    def test_blank_scores_are_skipped_and_bad_scores_stop_the_run(self):
        self.sheet("te_amy.csv", {"d1": "", "d2": 4})
        self.assertEqual(self.run_tool()[0], 0)
        self.sheet("te_bob.csv", {"d1": 7})
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("score '7' is not 1 to 5", err)


if __name__ == "__main__":
    unittest.main()
