"""The dry run 2 arm carries TSAI's 22 Nov values: Muon 0.006, WSD on, TST and head SGD off, router on Muon (23 Nov default)."""

from pathlib import Path
import sys
import unittest

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
from week2.config import load, load_runtime, merge, validate
from week2.optim import lr_scale
from week2 import tst


class DryRun2ArmTests(unittest.TestCase):
    def setUp(self):
        self.c = merge(
            load_runtime(TEAM / "configs/arms/dryrun2.yaml"),
            load(TEAM / "configs/small/smoke_resolution.yaml"),
        )

    def test_valid(self):
        self.assertEqual(validate(self.c), [])

    def test_recipe_values(self):
        o, r = self.c["optim"], self.c["run"]
        self.assertEqual(o["name"], "muon")
        self.assertEqual((o["muon_lr"], o["lr"]), (0.006, 0.001))
        self.assertEqual(
            (o["schedule"], o["warmup_frac"], o["decay_frac"], o["final_lr_frac"]), ("wsd", 0.05, 0.1, 0.0)
        )
        self.assertFalse(o.get("head_sgd", False))
        self.assertTrue(o.get("router_on_muon", True))
        self.assertFalse(r.get("tst", False))
        self.assertFalse(self.c["model"]["moe"]["bias"])
        self.assertEqual(self.c["model"]["moe"]["bias_gamma"], 0.001)

    def test_schedule_at_dry_run_1_length(self):
        """At 1,221 steps: 61 warmup steps, flat, 122 decay steps ending at 0."""
        o, n = self.c["optim"], 1221
        s = [lr_scale(k, n, o) for k in range(1, n + 1)]
        self.assertAlmostEqual(s[0], 1 / 61)
        self.assertEqual(s[60], 1.0)
        self.assertTrue(all(v == 1.0 for v in s[60 : n - 122]))
        self.assertLess(s[n - 122], 1.0)
        self.assertEqual(s[-1], 0.0)

    def test_tst_never_active(self):
        self.assertFalse(any(tst.active(k, 1221, self.c["run"]) for k in range(1, 1222)))


if __name__ == "__main__":
    unittest.main()
