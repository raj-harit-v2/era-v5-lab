"""The recipe can supply embeddings without changing normal model semantics."""

import copy
import unittest
from unittest.mock import patch

import torch

from test_week2_model import fixture
from week2.model import LanguageModel


class EmbeddingInputTests(unittest.TestCase):
    def models_and_inputs(self):
        cfg, rows, lengths = fixture()
        torch.manual_seed(1234)
        model = LanguageModel(cfg["model"], rows, lengths)
        ids = torch.tensor([[0, 2, 3, 1], [2, 3, 1, 0]])
        valid = torch.tensor([[True, True, True, False], [True, True, False, False]])
        return model, ids, valid

    def test_precomputed_embeddings_match_hidden_and_logits_exactly(self):
        model, ids, valid = self.models_and_inputs()
        model.eval()
        with torch.no_grad():
            hidden = model.hidden_from_embeddings(model.embedding(ids), valid)
            torch.testing.assert_close(hidden, model.hidden(ids, valid), rtol=0, atol=0)
            torch.testing.assert_close(model.head(hidden), model(ids, valid), rtol=0, atol=0)

    def test_gradients_match_including_the_input_projection(self):
        normal, ids, valid = self.models_and_inputs()
        supplied = copy.deepcopy(normal)
        normal(ids, valid).square().sum().backward()
        supplied.head(supplied.hidden_from_embeddings(supplied.embedding(ids), valid)).square().sum().backward()
        for (name, parameter), (other_name, other) in zip(normal.named_parameters(), supplied.named_parameters()):
            self.assertEqual(name, other_name)
            if parameter.grad is None:
                self.assertIsNone(other.grad)
            else:
                torch.testing.assert_close(parameter.grad, other.grad, rtol=0, atol=0)

    def test_supplied_sequence_uses_its_own_length_without_an_embedding_lookup(self):
        model, ids, valid = self.models_and_inputs()
        embedded = model.embedding(ids).detach()[:, :2].requires_grad_()
        keys = tuple(model.state_dict())
        with patch.object(model.embedding, "forward", side_effect=AssertionError("unexpected lookup")):
            hidden = model.hidden_from_embeddings(embedded, valid[:, :2])
            self.assertEqual(hidden.shape, embedded.shape)
            model.head(hidden).square().sum().backward()
        self.assertTrue(torch.isfinite(embedded.grad).all())
        self.assertEqual(tuple(model.state_dict()), keys)


if __name__ == "__main__":
    unittest.main()
