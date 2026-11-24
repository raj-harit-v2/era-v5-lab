"""``harness/save_hidden_vectors.py``: the saved rows are the head inputs at scored positions."""

from pathlib import Path
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
from save_hidden_vectors import _batches, collect
from week2.config import load, load_runtime, merge
from week2.model import LanguageModel
import save_hidden_vectors as exporter
import test_week2_kas_v2 as kas_fixture

VOCAB = 31
WIDTH = 16
PAD = 0


class Windows:
    """The two things ``collect`` reads from a dataset: ``windows`` and ``pad_id``."""

    def __init__(self, count=9, seed=5):
        rng = np.random.default_rng(seed)
        self.pad_id = PAD
        self.windows = []
        for _ in range(count):
            size = int(rng.integers(2, 9))
            inputs = rng.integers(1, VOCAB, size).tolist()
            targets = rng.integers(1, VOCAB, size).tolist()
            targets[0] = -100  # an unscored position inside the window
            self.windows.append((inputs, targets, [1] * size))


def tiny_model():
    config = merge(
        load_runtime(TEAM / "configs/arms/t1.yaml"),
        load(TEAM / "configs/small/smoke_resolution.yaml"),
    )
    model = config["model"]
    model.update(
        vocab_size=VOCAB, n_embd=WIDTH, n_layer=2, n_head=4, n_kv_head=2, block_size=8
    )
    model["moe"].update(num_experts=4, top_k=2, num_shared=1, ffn_hidden=24)
    rng = np.random.default_rng(7)
    rows = rng.integers(0, 256, (VOCAB, 4), dtype=np.uint8)
    lengths = rng.integers(1, 5, VOCAB, dtype=np.int16)
    torch.manual_seed(3)
    return LanguageModel(model, rows, lengths)


def one_by_one(model, dataset, seed):
    """Reference: each window alone, no padding, in the order ``collect`` uses."""
    vectors, ids = [], []
    model.eval()
    with torch.no_grad():
        for i in np.random.default_rng(seed).permutation(len(dataset.windows)):
            inputs, targets, _ = dataset.windows[i]
            x = torch.tensor([inputs])
            y = torch.tensor([targets])
            valid = y != -100
            vectors.append(model.hidden(x, valid)[valid])
            ids.append(y[valid])
    model.train()
    return torch.cat(vectors).numpy(), torch.cat(ids).numpy()


class SaveHiddenVectorsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = tiny_model()
        cls.data = Windows()
        cls.scored = sum(sum(t != -100 for t in w[1]) for w in cls.data.windows)

    def test_rows_are_head_inputs_at_scored_positions(self):
        expected, expected_ids = one_by_one(self.model, self.data, seed=0)
        for budget in [16, 24, 16_384]:
            vectors, ids, _ = collect(
                self.model, self.data, self.scored, 0, "cpu", max_batch_tokens=budget
            )
            self.assertEqual(vectors.shape, (self.scored, WIDTH))
            self.assertEqual(vectors.dtype, np.float32)
            self.assertEqual(ids.dtype, np.int64)
            np.testing.assert_array_equal(ids, expected_ids)
            np.testing.assert_allclose(vectors, expected, rtol=0, atol=1e-5)

    def test_no_row_comes_from_padding_or_an_unscored_position(self):
        _, ids, _ = collect(self.model, self.data, self.scored, 0, "cpu")
        self.assertTrue((ids >= 1).all() and (ids < VOCAB).all())
        self.assertEqual(len(ids), self.scored)

    def test_row_count_is_exact_and_stops_at_the_data(self):
        vectors, ids, hits = collect(self.model, self.data, 7, 0, "cpu")
        self.assertEqual((len(vectors), len(ids), len(hits)), (7, 7, 7))
        full, _, _ = collect(self.model, self.data, self.scored, 0, "cpu")
        np.testing.assert_array_equal(vectors, full[:7])
        more, _, _ = collect(self.model, self.data, 10 * self.scored, 0, "cpu")
        self.assertEqual(len(more), self.scored)
        with self.assertRaisesRegex(ValueError, "positive"):
            collect(self.model, self.data, 0, 0, "cpu")

    def test_seed_fixes_the_rows(self):
        a = collect(self.model, self.data, 12, 4, "cpu")
        b = collect(self.model, self.data, 12, 4, "cpu")
        c = collect(self.model, self.data, 12, 5, "cpu")
        np.testing.assert_array_equal(a[0], b[0])
        np.testing.assert_array_equal(a[1], b[1])
        self.assertFalse(np.array_equal(a[1], c[1]))

    def test_dense_head_on_the_saved_rows_gives_the_recorded_hits(self):
        vectors, ids, hits = collect(self.model, self.data, self.scored, 0, "cpu")
        with torch.no_grad():
            top1 = self.model.head(torch.from_numpy(vectors)).argmax(-1).numpy()
        np.testing.assert_array_equal(top1 == ids, hits)

    def test_training_mode_is_restored(self):
        self.model.train()
        collect(self.model, self.data, 5, 0, "cpu")
        self.assertTrue(self.model.training)

    def test_batches_cover_every_window_once_inside_the_budget(self):
        order = np.random.default_rng(1).permutation(len(self.data.windows))
        batches = list(_batches(self.data.windows, order, 16))
        self.assertEqual(sorted(i for b in batches for i in b), sorted(order.tolist()))
        for batch in batches:
            width = max(len(self.data.windows[i][1]) for i in batch)
            self.assertLessEqual(len(batch) * width, 16)
        with self.assertRaisesRegex(ValueError, "budget"):
            list(_batches(self.data.windows, order, 1))

    def test_cli_uses_saved_tokenizer_identity_and_kas_metadata(self):
        helper = kas_fixture.ModelIntegration()
        self.addCleanup(helper.doCleanups)
        cfg, byte_rows, lengths, model = helper.model()
        # Artifacts and DocumentWindows are mocked below; p1536.json is never opened.
        # The real release hash is only a saved-manifest identity to forward to the
        # loader. The synthetic 31-token model does not validate the p1536 tokenizer.
        recorded = {"tokenizer_sha256": "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"}
        artifacts = SimpleNamespace(bytes=byte_rows, lengths=lengths, pos_dim=32,
                                    tokenizer_sha=recorded["tokenizer_sha256"], table_content_sha="b" * 64,
                                    identity=lambda: recorded)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "manifest.json").write_text(json.dumps({
                "config": cfg, "artifacts": recorded,
                "identity_sha256": "test-run-identity", "status": "SMOKE_NOT_A_QUALITY_RESULT",
                "heldout_sha256": "c" * 64,
            }), encoding="utf8")
            torch.save({"model": model.state_dict(), "identity_sha256": "test-run-identity", "step": 1},
                       root / "checkpoint.pt")
            heldout = root / "heldout.jsonl"
            heldout.write_text('{"text":"heldout"}\n', encoding="utf8")
            output = root / "hidden.npz"
            args = ["save_hidden_vectors", "--run", str(root), "--tokenizer", "p1536.json",
                    "--byte-table", "raw.npz", "--heldout-data", str(heldout), "--out", str(output),
                    "--rows", "7"]
            with patch.object(sys, "argv", args), patch.object(exporter, "Artifacts", return_value=artifacts) as loader, \
                    patch.object(exporter, "DocumentWindows", return_value=Windows()):
                exporter.main()
            loader.assert_called_once_with(Path("p1536.json"), Path("raw.npz"),
                                           expected_tokenizer_sha=recorded["tokenizer_sha256"], expected_vocab=31)
            with np.load(output, allow_pickle=False) as z:
                self.assertEqual(str(z["kind"]), "hidden_before_kas_head")
                self.assertEqual(str(z["head_mode"]), "kas_v2")
                self.assertEqual(int(z["ke2_code_dim"]), 2048)
                self.assertEqual(z["vectors"].shape, (7, 16))
                self.assertEqual(float(z["head_top1"]), float(z["dense_head_top1"]))


if __name__ == "__main__":
    unittest.main()
