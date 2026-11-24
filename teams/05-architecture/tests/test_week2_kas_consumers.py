"""Check downstream adapter contracts with the actual KAS model."""

import importlib.util
from pathlib import Path
import sys
import unittest

import torch
import test_week2_kas_v2 as kas_fixture


class KASConsumerTests(unittest.TestCase):
    def test_affine_export_identity_matches_public_fixture_head(self):
        helper = kas_fixture.FixtureParity()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        head = helper.head()
        position = helper.codec.positions(helper.rows, helper.lengths).reshape(-1, 2048)
        folded_weight = head.beta[helper.lengths, None] * (position @ head.W_out.t())
        folded_weight = folded_weight + head.tok_u @ head.tok_c
        hidden = torch.from_numpy(helper.z["h"].copy())
        folded = torch.nn.functional.linear(hidden, folded_weight, head.unigram)
        torch.testing.assert_close(folded, head(hidden), rtol=0, atol=1e-10)

    def test_team10_recognises_real_input_and_head_and_preserves_logits(self):
        helper = kas_fixture.ModelIntegration()
        self.addCleanup(helper.doCleanups)
        _, _, _, model = helper.model()
        path = Path(__file__).resolve().parents[2] / "10-post-training/rl-loop/team5_adapter.py"
        name = "kas_validation_team10_adapter"
        spec = importlib.util.spec_from_file_location(name, path)
        adapter = importlib.util.module_from_spec(spec)
        sys.modules[name] = adapter
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(adapter)
        head = adapter.head_access(model)
        self.assertEqual(head["kind"], "kas")
        self.assertEqual(head["vocab_size"], model.head.out_features)
        self.assertIs(head["per_token"], model.head.tok_u)
        self.assertFalse(head["tied"])
        embedding = adapter.input_access(model, 32)
        self.assertEqual(embedding["kind"], "ke2_code_2048")
        self.assertEqual(embedding["width"], 2048)
        model.eval()
        ids = torch.arange(8).reshape(1, 8)
        with torch.no_grad():
            h = model.hidden(ids, torch.ones_like(ids, dtype=torch.bool))
            torch.testing.assert_close(adapter.head_logits(model, h), model.head(h), rtol=0, atol=0)


if __name__ == "__main__":
    unittest.main()
