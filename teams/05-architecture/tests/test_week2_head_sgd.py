"""Optional SGD-momentum on the output head group (week-4 task 3, TSAI's 21 Nov recipe): off by default."""

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
from week2.optim import Optimizers, build_optimizer, describe, set_lr_scale
from test_week2_model import fixture

SGD = {"head_sgd": True, "head_sgd_lr": 0.01, "head_sgd_momentum": 0.99}


def build(name="muon", **extra):
    c, rows, lengths = fixture()
    c["optim"].update(name=name, **({"muon_lr": 0.003} if name == "muon" else {}), **extra)
    torch.manual_seed(1234)
    m = LanguageModel(c["model"], rows, lengths)
    return c, m, build_optimizer(m, c["optim"])


def names_in(opt, key, m):
    ids = {id(p) for g in dict(opt.named)[key].param_groups for p in g["params"]}
    return {n for n, p in m.named_parameters() if id(p) in ids}


def one_step(m, opt):
    ids = torch.arange(16).reshape(2, 8) % 31
    opt.zero_grad(set_to_none=True)
    F.cross_entropy(m(ids, torch.ones_like(ids, dtype=torch.bool)).reshape(-1, 31), (ids + 1).reshape(-1) % 31).backward()
    opt.step()


class GroupTests(unittest.TestCase):
    def test_off_by_default(self):
        c, m, opt = build()
        self.assertEqual([k for k, _ in opt.named], ["muon", "adamw"])
        self.assertFalse(describe(m, c["optim"])["head_sgd"])

    def test_whole_head_on_sgd_nothing_else(self):
        c, m, opt = build(**SGD)
        self.assertEqual([k for k, _ in opt.named], ["muon", "adamw", "sgd"])
        sgd = names_in(opt, "sgd", m)
        self.assertEqual(sgd, {n for n, _ in m.named_parameters() if n.startswith("head.")})
        self.assertFalse(sgd & names_in(opt, "adamw", m))
        self.assertFalse(sgd & names_in(opt, "muon", m))
        ids = [id(p) for _, o in opt.named for g in o.param_groups for p in g["params"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), {id(p) for p in m.parameters()})
        g = dict(opt.named)["sgd"].param_groups[0]
        self.assertEqual((g["lr"], g["momentum"]), (0.01, 0.99))
        d = describe(m, c["optim"])
        self.assertEqual(d["muon_parameters"] + d["adamw_parameters"] + d["head_sgd_parameters"], m.parameter_count())

    def test_adamw_arm_with_head_sgd(self):
        c, m, opt = build("adamw", **SGD)
        self.assertIsInstance(opt, Optimizers)
        self.assertEqual([k for k, _ in opt.named], ["adamw", "sgd"])
        d = describe(m, c["optim"])
        self.assertTrue(d["head_sgd"])

    def test_one_step_moves_head(self):
        c, m, opt = build(**SGD)
        before = m.head.weight.detach().clone()
        one_step(m, opt)
        self.assertFalse(torch.equal(before, m.head.weight.detach()))

    def test_schedule_scales_sgd_too(self):
        c, m, opt = build(**SGD)
        set_lr_scale(opt, 0.5)
        self.assertEqual(dict(opt.named)["sgd"].param_groups[0]["lr"], 0.005)


class ResumeTests(unittest.TestCase):
    def test_resume_with_same_setting(self):
        c, m, opt = build(**SGD)
        one_step(m, opt)
        state = opt.state_dict()
        fresh = build_optimizer(m, c["optim"])
        fresh.load_state_dict(state)
        buf = dict(opt.named)["sgd"].state_dict()["state"]
        self.assertTrue(buf)
        self.assertEqual(dict(fresh.named)["sgd"].state_dict()["state"].keys(), buf.keys())

    def test_switch_cannot_flip_on_resume(self):
        """A checkpoint saved without head SGD does not load into a run with it, and back (#608 resume guard)."""
        c, m, off = build()
        one_step(m, off)
        c2, m2, on = build(**SGD)
        with self.assertRaises(ValueError):
            on.load_state_dict(off.state_dict())
        with self.assertRaises(ValueError):
            off.load_state_dict(on.state_dict())


class ConfigTests(unittest.TestCase):
    def resolved(self, path):
        return merge(
            load_runtime(TEAM / "configs/arms" / path),
            load(TEAM / "configs/small/smoke_resolution.yaml"),
        )

    def test_valid_when_complete(self):
        c = self.resolved("muon_screen/muon_1e-2.yaml")
        c["optim"].update(SGD)
        self.assertFalse(any("head_sgd" in e for e in validate(c)))

    def test_needs_rate_and_momentum(self):
        c = self.resolved("muon_screen/muon_1e-2.yaml")
        c["optim"]["head_sgd"] = True
        errs = validate(c)
        self.assertTrue(any("head_sgd_lr" in e for e in errs))
        self.assertTrue(any("head_sgd_momentum" in e for e in errs))

    def test_bad_values_and_stray_settings(self):
        c = self.resolved("muon_screen/muon_1e-2.yaml")
        c["optim"]["head_sgd"] = "yes"
        self.assertTrue(any("true or false" in e for e in validate(c)))
        c = self.resolved("muon_screen/muon_1e-2.yaml")
        c["optim"].update(dict(SGD, head_sgd_momentum=1.0))
        self.assertTrue(any("head_sgd_momentum" in e for e in validate(c)))
        c = self.resolved("muon_screen/muon_1e-2.yaml")
        c["optim"]["head_sgd_lr"] = 0.01
        self.assertTrue(any("would be ignored" in e for e in validate(c)))


if __name__ == "__main__":
    unittest.main()
