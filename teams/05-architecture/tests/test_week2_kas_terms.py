"""Confirmed-mechanics checks; not complete selected-head/reference parity."""

import copy
import io
from pathlib import Path
import sys
import unittest

import torch

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
from week2.kas_terms import correction_row_dropout, initialize_unigram_
from week2.unigram import UnigramCounts, load_counts
from week2.artifacts import P1536_SHA256
from week2.optim import build_optimizer
from test_week2_model import fixture
from week2.model import LanguageModel


def small_counts():
    return UnigramCounts((4, 0, 0, 2), 3, 2, (1, 2), "a" * 64,
                         P1536_SHA256, (), "a" * 64, "exact")


class PriorInitializationTests(unittest.TestCase):
    def test_centered_add_one_initialization_is_finite_float32_and_trainable(self):
        counts = small_counts()
        parameter = torch.nn.Parameter(torch.zeros(4))
        identity = initialize_unigram_(parameter, counts, add_eos_per_document=False)
        probabilities = torch.tensor([5, 1, 1, 3], dtype=torch.float64) / 10
        expected = probabilities.log()
        expected -= expected.mean()
        torch.testing.assert_close(parameter, expected.float(), rtol=0, atol=0)
        torch.testing.assert_close(parameter.softmax(0).double(), probabilities)
        self.assertLess(abs(parameter.mean().item()), 1e-6)
        self.assertTrue(parameter.requires_grad)
        self.assertFalse(identity["add_eos_per_document"])
        self.assertEqual(identity["smoothing"], 1.0)
        parameter.square().sum().backward()
        self.assertTrue(torch.isfinite(parameter.grad).all())
        self.assertEqual(counts.counts, (4, 0, 0, 2))

    def test_eos_adaptation_stays_explicit(self):
        counts = small_counts()
        parameter = torch.nn.Parameter(torch.zeros(4))
        with self.assertRaises(TypeError):
            initialize_unigram_(parameter, counts)
        identity = initialize_unigram_(parameter, counts, add_eos_per_document=True)
        expected = torch.tensor([5, 1, 4, 3], dtype=torch.float32) / 13
        torch.testing.assert_close(parameter.softmax(0), expected)
        self.assertTrue(identity["add_eos_per_document"])

    def test_parameter_contract_is_enforced(self):
        for parameter in (torch.zeros(4), torch.nn.Parameter(torch.zeros(3)),
                          torch.nn.Parameter(torch.zeros(4, dtype=torch.float64)),
                          torch.nn.Parameter(torch.zeros(4), requires_grad=False)):
            with self.subTest(parameter=parameter), self.assertRaises(ValueError):
                initialize_unigram_(parameter, small_counts(), add_eos_per_document=False)

    def test_real_p1536_all_ids_including_9702_zeros(self):
        path = TEAM.parent / "03-tokenizer/counts/p1536_counts.json"
        counts = load_counts(path, expected_sha256="0768b5982825645a796abc76ec23c737837cfacc8f6b089335e5ce5446def3a6",
                             expected_tokenizer_sha256=P1536_SHA256, expected_vocab_size=131072, checksum_mode="lf")
        parameter = torch.nn.Parameter(torch.zeros(131072))
        initialize_unigram_(parameter, counts, add_eos_per_document=False)
        self.assertTrue(torch.isfinite(parameter).all())
        zero_ids = torch.tensor([i for i, count in enumerate(counts.counts) if count == 0])
        self.assertEqual(len(zero_ids), 9702)
        self.assertTrue(torch.equal(parameter[zero_ids], parameter[zero_ids[0]].expand(len(zero_ids))))
        self.assertLess(abs(parameter.mean().item()), 1e-6)
        self.assertEqual(counts.counts[130822], 0)


class CorrectionDropoutTests(unittest.TestCase):
    def test_whole_rows_are_zero_or_inverted_scaled_at_chosen_rate(self):
        original = torch.ones(131072, 64)
        output = correction_row_dropout(original, probability=0.05, training=True,
                                        generator=torch.Generator().manual_seed(1234))
        self.assertTrue(torch.equal(output, output[:, :1].expand_as(output)))
        dropped = output[:, 0] == 0
        self.assertLess(abs(dropped.float().mean().item() - 0.05), 0.005)
        torch.testing.assert_close(output[~dropped], torch.full_like(output[~dropped], 1 / 0.95))
        self.assertTrue(torch.equal(original, torch.ones_like(original)))

    def test_eval_and_zero_dropout_do_not_consume_rng_or_change_values(self):
        tok_u = torch.randn(31, 64)
        for training, probability in ((False, 0.05), (True, 0.0)):
            state = torch.get_rng_state().clone()
            self.assertIs(correction_row_dropout(tok_u, probability=probability, training=training), tok_u)
            self.assertTrue(torch.equal(state, torch.get_rng_state()))

    def test_gradient_uses_one_mask_value_for_entire_row(self):
        tok_u = torch.ones(100, 64, requires_grad=True)
        output = correction_row_dropout(tok_u, probability=0.05, training=True,
                                        generator=torch.Generator().manual_seed(31))
        output.sum().backward()
        torch.testing.assert_close(tok_u.grad, output, rtol=0, atol=0)

    def test_restored_rng_and_optimizer_state_reproduce_next_update(self):
        tok_u = torch.nn.Parameter(torch.randn(31, 64))
        unigram = torch.nn.Parameter(torch.zeros(31))
        parameters = torch.nn.ParameterList([tok_u, unigram])
        optimizer = torch.optim.AdamW(parameters, lr=0.001)
        features = torch.linspace(0.1, 1.0, 64)
        def step(ps, opt):
            opt.zero_grad()
            correction = correction_row_dropout(ps[0], probability=0.05, training=True)
            loss = (correction @ features + ps[1]).square().mean()
            loss.backward()
            opt.step()
            return loss.detach().clone()
        torch.manual_seed(1234)
        step(parameters, optimizer)
        checkpoint = io.BytesIO()
        torch.save({"model": parameters.state_dict(), "optimizer": optimizer.state_dict(),
                    "rng": torch.get_rng_state()}, checkpoint)
        checkpoint.seek(0)
        saved = torch.load(checkpoint, weights_only=True)
        expected_loss = step(parameters, optimizer)
        expected_parameters = copy.deepcopy(parameters.state_dict())
        restored = torch.nn.ParameterList([torch.nn.Parameter(torch.zeros(31, 64)), torch.nn.Parameter(torch.zeros(31))])
        restored.load_state_dict(saved["model"])
        restored_optimizer = torch.optim.AdamW(restored, lr=0.001)
        restored_optimizer.load_state_dict(saved["optimizer"])
        torch.set_rng_state(saved["rng"])
        torch.testing.assert_close(step(restored, restored_optimizer), expected_loss, rtol=0, atol=0)
        for name, tensor in restored.state_dict().items():
            torch.testing.assert_close(tensor, expected_parameters[name], rtol=0, atol=0)

    def test_confirmed_parameter_names_are_grouped_with_the_output_head(self):
        cfg, rows, lengths = fixture()
        cfg["optim"].update(name="muon", muon_lr=0.006)
        model = LanguageModel(cfg["model"], rows, lengths)
        # Register the confirmed terms on a test host, without pretending the
        # legacy Linear head's forward implements KAS.
        model.head.unigram = torch.nn.Parameter(torch.zeros(cfg["model"]["vocab_size"]))
        model.head.tok_u = torch.nn.Parameter(torch.zeros(cfg["model"]["vocab_size"], 64))
        for sgd in (False, True):
            cfg["optim"].update(head_sgd=sgd, head_sgd_lr=0.01, head_sgd_momentum=0.99)
            optimizers = build_optimizer(model, cfg["optim"])
            owners = {id(p): name for name, opt in optimizers.named for group in opt.param_groups for p in group["params"]}
            for name, parameter in model.head.named_parameters():
                self.assertEqual(owners[id(parameter)], "sgd" if sgd else "adamw", name)

    def test_invalid_arguments_fail(self):
        for probability in (-1, 1, True, float("nan")):
            with self.subTest(probability=probability), self.assertRaises(ValueError):
                correction_row_dropout(torch.ones(3, 64), probability=probability, training=True)
        with self.assertRaises(ValueError):
            correction_row_dropout(torch.ones(64), probability=0.05, training=True)


if __name__ == "__main__":
    unittest.main()
