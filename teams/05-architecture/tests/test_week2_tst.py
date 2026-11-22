"""TST ("Secret Sauce", week-4 task 3, TSAI's 21 Nov recipe, unconfirmed on KE2): bags, targets, loss, phase, config."""

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
from week2 import tst
from test_week2_model import fixture


class WeightTests(unittest.TestCase):
    def test_power_weights_match_tsai(self):
        w = tst.power_weights(6)
        self.assertAlmostEqual(float(w.sum()), 1.0, places=6)
        for got, want in zip(w.tolist(), [0.408, 0.204, 0.136, 0.102, 0.082, 0.068]):
            self.assertAlmostEqual(got, want, places=3)


class PhaseTests(unittest.TestCase):
    def test_first_30_percent_only(self):
        run = {"tst": True, "tst_bag": 6, "tst_frac": 0.3}
        on = [tst.active(k, 1221, run) for k in range(1, 1222)]
        self.assertEqual(sum(on), 366)  # round(0.3 * 1221)
        self.assertTrue(all(on[:366]) and not any(on[366:]))

    def test_off_when_not_set(self):
        self.assertFalse(tst.active(1, 100, {}))
        self.assertFalse(tst.active(1, 100, {"tst": False, "tst_frac": 0.3}))


class BatchTests(unittest.TestCase):
    def setUp(self):
        # one row of 14 tokens: x[t] = t, y[t] = x[t + 1] (the next token), last target unscored
        self.x = torch.arange(14).reshape(1, 14)
        self.y = torch.cat([torch.arange(1, 14), torch.tensor([-100])]).reshape(1, 14)

    def test_inputs_and_next_bag_targets(self):
        s = 3
        inputs, valid, targets = tst.tst_batch(self.x, self.y, s)
        # bags need a complete next bag: (14 - 3 + 1) // 3 = 4 bags
        self.assertEqual(inputs.tolist(), [list(range(12))])
        self.assertEqual(targets.tolist(), [[[3, 4, 5], [6, 7, 8], [9, 10, 11], [12, 13, -100]]])
        self.assertEqual(valid.tolist(), [[True, True, True, True]])

    def test_padding_is_not_scored(self):
        y = self.y.clone()
        y[0, 6:] = -100  # the document's last scored target is token 6
        _, valid, targets = tst.tst_batch(self.x, y, 3)
        # bag 1 still scores token 6 (its first next-bag target); bags 2 and 3 have nothing left to score
        self.assertEqual(targets.tolist()[0][1], [6, -100, -100])
        self.assertEqual(valid.tolist(), [[True, True, False, False]])
        self.assertEqual(tst.scored_bags(y, 3), 2)


class LossTests(unittest.TestCase):
    def setUp(self):
        c, rows, lengths = fixture()
        c["model"]["block_size"] = 12
        torch.manual_seed(1234)
        self.m = LanguageModel(c["model"], rows, lengths)
        self.x = torch.arange(24).reshape(2, 12) % 31
        self.y = torch.cat([self.x[:, 1:], torch.full((2, 1), -100)], 1)

    def test_matches_a_slow_reference(self):
        s = 3
        got = tst.tst_loss(self.m, self.x, self.y, s)
        # reference: average each bag's embeddings by hand, run the blocks, score each target separately
        n = tst.bag_count(12, s)
        emb = self.m.embedding(self.x[:, : s * n]).float()
        h = torch.stack([emb[:, s * j : s * j + s].mean(1) for j in range(n)], 1)
        valid = torch.ones(2, n, dtype=torch.bool)
        for block in self.m.blocks:
            h = block(h, valid)
        logp = F.log_softmax(self.m.head(self.m.norm(h)).float(), -1)
        w = tst.power_weights(s)
        want = 0.0
        for b in range(2):
            for j in range(n):
                for i in range(s):
                    t = int(self.y[b, s * (j + 1) + i - 1])
                    if t != -100:
                        want += float(w[i]) * -float(logp[b, j, t].detach())
        self.assertAlmostEqual(float(got), want, places=4)

    def test_gradient_reaches_every_part(self):
        tst.tst_loss(self.m, self.x, self.y, 3).backward()
        for name in ["embedding.projection.weight", "blocks.0.attn.q.weight", "head.weight"]:
            g = dict(self.m.named_parameters())[name].grad
            self.assertIsNotNone(g, name)
            self.assertTrue(torch.isfinite(g).all() and g.abs().sum() > 0, name)

    def test_six_times_fewer_positions(self):
        """Bag positions are what the blocks see: about 1/s of the tokens."""
        seen = []
        hook = self.m.blocks[0].register_forward_hook(lambda mod, inp, out: seen.append(inp[0].shape[1]))
        tst.tst_loss(self.m, self.x, self.y, 3)
        hook.remove()
        self.assertEqual(seen, [tst.bag_count(12, 3)])


class ConfigTests(unittest.TestCase):
    def resolved(self):
        return merge(
            load_runtime(TEAM / "configs/arms/muon_screen/muon_1e-2.yaml"),
            load(TEAM / "configs/small/smoke_resolution.yaml"),
        )

    def test_off_by_default_and_valid_when_complete(self):
        c = self.resolved()
        self.assertFalse(c["run"].get("tst", False))
        c["run"].update(tst=True, tst_bag=6, tst_frac=0.3)
        self.assertFalse(any("tst" in e for e in validate(c)))

    def test_needs_explicit_settings(self):
        c = self.resolved()
        c["run"]["tst"] = True
        errs = validate(c)
        self.assertTrue(any("tst_bag" in e for e in errs))
        self.assertTrue(any("tst_frac" in e for e in errs))

    def test_bad_and_stray_settings(self):
        c = self.resolved()
        c["run"].update(tst=True, tst_bag=6, tst_frac=1.5)
        self.assertTrue(any("tst_frac" in e for e in validate(c)))
        c = self.resolved()
        c["run"]["tst_frac"] = 0.3
        self.assertTrue(any("would be ignored" in e for e in validate(c)))
        c = self.resolved()
        c["run"]["tst"] = "yes"
        self.assertTrue(any("true or false" in e for e in validate(c)))


if __name__ == "__main__":
    unittest.main()
