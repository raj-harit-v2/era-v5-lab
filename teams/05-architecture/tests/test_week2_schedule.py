"""WSD learning-rate schedule (week-4 task 3, TSAI's 21 Nov recipe): shape, both optimizers, resume, validation."""

from pathlib import Path
import sys
import unittest
import torch
from torch.nn import functional as F

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
sys.path.insert(0, str(TEAM / "tests"))
from week2.config import load, load_runtime, merge, validate
from week2.model import LanguageModel
from week2.optim import build_optimizer, lr_scale, set_lr_scale
from test_week2_model import fixture

WSD = {"schedule": "wsd", "warmup_frac": 0.1, "decay_frac": 0.2, "final_lr_frac": 0.0}


def muon_fixture():
    c, rows, lengths = fixture()
    c["optim"].update(name="muon", muon_lr=0.003)
    return c, rows, lengths


def group_rates(opt):
    return {name: [g["lr"] for g in o.param_groups] for name, o in opt.named}


class ShapeTests(unittest.TestCase):
    def test_constant_is_one_everywhere(self):
        for step in [1, 50, 100]:
            self.assertEqual(lr_scale(step, 100, {"schedule": "constant"}), 1.0)
        self.assertEqual(lr_scale(7, 100, {}), 1.0)

    def test_wsd_warmup_stable_decay(self):
        s = [lr_scale(k, 100, WSD) for k in range(1, 101)]
        # warmup: 10 steps, rising linearly to 1.0
        self.assertAlmostEqual(s[0], 0.1)
        self.assertEqual(s[9], 1.0)
        self.assertTrue(all(a < b for a, b in zip(s[:9], s[1:10])))
        # stable: steps 11 to 80 flat at 1.0
        self.assertTrue(all(v == 1.0 for v in s[10:80]))
        # decay: last 20 steps, falling linearly to final_lr_frac on the last step
        self.assertTrue(all(a > b for a, b in zip(s[80:], s[81:])))
        self.assertAlmostEqual(s[-1], 0.0)
        self.assertAlmostEqual(s[89], 0.5)

    def test_final_fraction_and_no_warmup(self):
        o = dict(WSD, warmup_frac=0.0, final_lr_frac=0.1)
        self.assertEqual(lr_scale(1, 100, o), 1.0)
        self.assertAlmostEqual(lr_scale(100, 100, o), 0.1)

    def test_depends_only_on_step(self):
        """A resumed run continues the same curve: no hidden state."""
        first = [lr_scale(k, 1221, WSD) for k in range(1, 1222)]
        again = [lr_scale(k, 1221, WSD) for k in range(600, 1222)]
        self.assertEqual(first[599:], again)


class OptimizerTests(unittest.TestCase):
    def test_scales_both_muon_and_adamw_from_their_own_peaks(self):
        c, rows, lengths = muon_fixture()
        m = LanguageModel(c["model"], rows, lengths)
        opt = build_optimizer(m, c["optim"])
        set_lr_scale(opt, 0.5)
        r = group_rates(opt)
        self.assertEqual(r["muon"], [0.0015])
        self.assertEqual(r["adamw"], [5e-4])
        set_lr_scale(opt, 1.0)  # peaks are kept, not compounded
        r = group_rates(opt)
        self.assertEqual(r["muon"], [0.003])
        self.assertEqual(r["adamw"], [1e-3])

    def test_adamw_only_arm(self):
        c, rows, lengths = fixture()
        m = LanguageModel(c["model"], rows, lengths)
        opt = build_optimizer(m, c["optim"])
        set_lr_scale(opt, 0.25)
        self.assertEqual([g["lr"] for g in opt.param_groups], [2.5e-4])

    def test_peak_survives_checkpoint_round_trip(self):
        c, rows, lengths = muon_fixture()
        torch.manual_seed(1234)
        m = LanguageModel(c["model"], rows, lengths)
        opt = build_optimizer(m, c["optim"])
        ids = torch.arange(16).reshape(2, 8) % 31
        set_lr_scale(opt, 0.2)
        opt.zero_grad(set_to_none=True)
        F.cross_entropy(m(ids, torch.ones_like(ids, dtype=torch.bool)).reshape(-1, 31), (ids + 1).reshape(-1) % 31).backward()
        opt.step()
        state = opt.state_dict()
        fresh = build_optimizer(m, c["optim"])
        fresh.load_state_dict(state)
        set_lr_scale(fresh, 1.0)
        r = group_rates(fresh)
        self.assertEqual(r["muon"], [0.003])
        self.assertEqual(r["adamw"], [1e-3])


class ConfigTests(unittest.TestCase):
    def resolved(self, path):
        return merge(
            load_runtime(TEAM / "configs/arms" / path),
            load(TEAM / "configs/small/smoke_resolution.yaml"),
        )

    def test_constant_still_valid(self):
        c = self.resolved("muon_screen/muon_1e-2.yaml")
        self.assertEqual(c["optim"]["schedule"], "constant")
        self.assertFalse(any("schedule" in e or "wsd" in e for e in validate(c)))

    def test_wsd_valid_when_complete(self):
        c = self.resolved("muon_screen/muon_1e-2.yaml")
        c["optim"].update(WSD)
        self.assertFalse(any("wsd" in e or "schedule" in e for e in validate(c)))

    def test_wsd_needs_every_setting(self):
        c = self.resolved("muon_screen/muon_1e-2.yaml")
        c["optim"].update(schedule="wsd", warmup_frac=0.1)
        self.assertTrue(any("decay_frac" in e and "final_lr_frac" in e for e in validate(c)))

    def test_wsd_ranges(self):
        for bad in [{"warmup_frac": 0.6, "decay_frac": 0.5}, {"decay_frac": 0.0}, {"final_lr_frac": 1.5}]:
            c = self.resolved("muon_screen/muon_1e-2.yaml")
            c["optim"].update(dict(WSD, **bad))
            self.assertTrue(any("wsd needs" in e for e in validate(c)), bad)

    def test_unknown_schedule_and_stray_settings(self):
        c = self.resolved("muon_screen/muon_1e-2.yaml")
        c["optim"]["schedule"] = "cosine"
        self.assertTrue(any("constant or wsd" in e for e in validate(c)))
        c = self.resolved("muon_screen/muon_1e-2.yaml")
        c["optim"]["warmup_frac"] = 0.1
        self.assertTrue(any("would be ignored" in e for e in validate(c)))


if __name__ == "__main__":
    unittest.main()
