"""Shared output-head contracts for the trainer, optimizer and Team 9.

These checks exercise the actual LanguageModel head, including every parameter
it registers. Main still has the legacy dense head: these are compatibility
groundwork, not evidence of selected KAS-arm correctness or reference parity.
"""

import copy
import io
import unittest

import numpy as np
import torch

from test_week2_model import fixture
from week2.model import LanguageModel
from week2.optim import Optimizers, build_optimizer


class HeadInterfaceTests(unittest.TestCase):
    def test_every_actual_head_and_input_parameter_is_only_on_adamw(self):
        cfg, rows, lengths = fixture()
        cfg["optim"].update(name="muon", muon_lr=0.006)
        model = LanguageModel(cfg["model"], rows, lengths)
        optimizer = build_optimizer(model, cfg["optim"])
        self.assertIsInstance(optimizer, Optimizers)
        owners = {}
        for name, item in optimizer.named:
            for group in item.param_groups:
                for parameter in group["params"]:
                    owners.setdefault(id(parameter), []).append(name)
        self.assertEqual(set(owners), {id(p) for p in model.parameters()})
        self.assertTrue(all(len(groups) == 1 for groups in owners.values()))
        self.assertTrue(list(model.head.parameters()))
        self.assertTrue(list(model.embedding.parameters()))
        for name, parameter in model.named_parameters():
            if name.startswith(("head.", "embedding.")):
                self.assertEqual(owners[id(parameter)], ["adamw"], name)
        head = {id(p) for p in model.head.parameters()}
        inputs = {id(p) for p in model.embedding.parameters()}
        self.assertTrue(head.isdisjoint(inputs), "input and output parameters must be untied")
        head_storage = {p.untyped_storage().data_ptr() for p in model.head.parameters()}
        input_storage = {p.untyped_storage().data_ptr() for p in model.embedding.parameters()}
        self.assertTrue(head_storage.isdisjoint(input_storage), "independent parameters must not alias storage")

    def test_merged_recipe_optional_sgd_owns_every_actual_head_parameter(self):
        cfg, rows, lengths = fixture()
        cfg["optim"].update(name="muon", muon_lr=0.006, head_sgd=True,
                            head_sgd_lr=0.01, head_sgd_momentum=0.99)
        model = LanguageModel(cfg["model"], rows, lengths)
        optimizer = build_optimizer(model, cfg["optim"])
        owners = {}
        for name, item in optimizer.named:
            for group in item.param_groups:
                for parameter in group["params"]:
                    owners.setdefault(id(parameter), []).append(name)
        self.assertEqual(set(owners), {id(p) for p in model.parameters()})
        self.assertTrue(all(len(groups) == 1 for groups in owners.values()))
        for name, parameter in model.named_parameters():
            if name.startswith("head."):
                self.assertEqual(owners[id(parameter)], ["sgd"], name)
            elif name.startswith("embedding."):
                self.assertEqual(owners[id(parameter)], ["adamw"], name)

    def test_merged_tst_backpropagates_through_input_and_head(self):
        from week2.tst import tst_loss

        cfg, rows, lengths = fixture()
        model = LanguageModel(cfg["model"], rows, lengths)
        ids = torch.arange(24).reshape(1, 24) % cfg["model"]["vocab_size"]
        targets = torch.roll(ids, shifts=-1, dims=1)
        targets[:, -1] = -100
        loss = tst_loss(model, ids, targets, 6)
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        for name, parameter in model.named_parameters():
            if name.startswith(("head.", "embedding.")):
                self.assertIsNotNone(parameter.grad, name)
                self.assertTrue(torch.isfinite(parameter.grad).all(), name)
                self.assertTrue(torch.any(parameter.grad != 0), name)

    def test_p1536_sized_constructor_and_strict_weight_reload_preserve_scoring(self):
        cfg, _, _ = fixture()
        spec = copy.deepcopy(cfg["model"])
        spec["vocab_size"] = 131072
        ids_np = np.arange(spec["vocab_size"], dtype=np.uint32)
        rows = np.zeros((len(ids_np), 32), dtype=np.uint8)
        for column in range(3):
            rows[:, column] = (ids_np >> (8 * column)) & 255
        lengths = np.full(len(ids_np), 3, dtype=np.int16)
        spec["ke_max_pos"] = 32
        torch.manual_seed(12)
        model = LanguageModel(spec, rows, lengths).eval()
        self.assertEqual(model.head.out_features, 131072)
        ids = torch.tensor([[130725, 130822]])
        valid = torch.ones_like(ids, dtype=torch.bool)
        with torch.no_grad():
            hidden = model.hidden(ids, valid)
            logits = model.head(hidden)
            self.assertEqual(logits.shape, (1, 2, 131072))
            self.assertTrue(torch.isfinite(logits).all())
            # Team 9 selects hidden rows before invoking the head.
            selected = model.head(hidden.reshape(-1, spec["n_embd"]))
            self.assertEqual(selected.shape, (2, 131072))
            torch.testing.assert_close(selected, logits.reshape(2, -1), rtol=0, atol=0)
        checkpoint = io.BytesIO()
        torch.save(model.state_dict(), checkpoint)
        checkpoint.seek(0)
        restored = LanguageModel(spec, rows, lengths).eval()
        restored.load_state_dict(torch.load(checkpoint, weights_only=True), strict=True)
        with torch.no_grad():
            torch.testing.assert_close(restored(ids, valid), logits, rtol=0, atol=0)


if __name__ == "__main__":
    unittest.main()
