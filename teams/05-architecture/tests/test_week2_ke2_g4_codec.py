"""KE2 input path of the week-2 harness against Team 4's float64 codec on the committed table.

Team 4 asked Team 5 for this check for Gate 3, and TSAI supports it.

Reference: ``encode_f64`` in ``teams/04-ke2/src/ke2/codec.py``, on the committed
``teams/04-ke2/results/tables/raw_table_P32.npz`` (131,072 tokens, P = 32, D = 8,192).
Under test: ``week2.model.KE2`` and the dense ``week2.model.codec``. The reference shares no code
with either. Every token ID is checked, not a sample.

To run the same check on another Team 4 format-v2 raw table, for example the table built for
the frozen tokenizer, set ``ERA_KE2_TABLE`` to its path.

This file tests the input path only. The output head stays dense and untied.
"""

import json
import os
from pathlib import Path
import sys
import unittest

import numpy as np
import torch

TEAM = Path(__file__).resolve().parents[1]
G4 = TEAM.parent / "04-ke2"
COMMITTED = G4 / "results/tables/raw_table_P32.npz"
TABLE = Path(os.environ.get("ERA_KE2_TABLE", COMMITTED)).resolve()
sys.path.insert(0, str(TEAM / "harness"))
sys.path.insert(0, str(G4 / "src"))
from week2.model import KE2, codec
from ke2.codec import encode_f64
from ke2.tables import table_content_sha256

WIDTH = 64
CHUNK = 2048
# FP32 sparse path against an FP64 dense reference. Measured on CPU over all 131,072 IDs of the
# committed P32 table: largest absolute difference 1.4e-6, on outputs with mean size 0.82 and
# largest size 5.5. The bound leaves a factor of 7.
ATOL = 1e-5
RTOL = 1e-5
# The projection gradient sums many FP32 terms and reaches about 1,200 in size.
# It is compared after dividing by the largest reference entry. Measured: 3.1e-7.
GRAD_ATOL = 2e-6


def load_table(path):
    with np.load(path, allow_pickle=False) as z:
        meta = {
            "format_version": int(z["format_version"]),
            "kind": str(z["kind"]),
            "pos_dim": int(z["pos_dim"]),
            "n_truncated": int(z["n_truncated"]),
            "table_sha256": str(z["table_sha256"]),
        }
        return z["bytes"].copy(), z["lengths"].copy(), meta


def sample_ids(lengths, count=256, seed=2):
    """Random IDs, both ends of the vocabulary, and the shortest and longest tokens."""
    rng = np.random.default_rng(seed)
    longest = np.flatnonzero(lengths == lengths.max())[:4]
    shortest = np.flatnonzero(lengths == lengths.min())[:4]
    edge = np.concatenate([[0, len(lengths) - 1], longest, shortest])
    edge = np.resize(edge, 10)
    picked = np.concatenate([rng.integers(0, len(lengths), count - 10), edge])
    return picked.astype(np.int64)


class G4CodecOnCommittedTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.lengths, cls.meta = load_table(TABLE)
        cls.vocab = len(cls.rows)
        cls.p = cls.meta["pos_dim"]
        torch.manual_seed(1234)
        cls.layer = KE2(cls.rows, cls.lengths, WIDTH)
        cls.weight64 = cls.layer.projection.weight.detach().double().numpy()

    def test_table_passes_the_g4_integrity_contract(self):
        self.assertEqual(self.meta["format_version"], 2)
        self.assertEqual(self.meta["kind"], "raw")
        self.assertEqual(self.meta["n_truncated"], 0)
        self.assertEqual(self.rows.shape, (self.vocab, self.p))
        self.assertEqual(self.lengths.shape, (self.vocab,))
        self.assertEqual(self.rows.dtype, np.uint8)
        self.assertEqual(self.lengths.dtype, np.int16)
        self.assertTrue(np.all(self.lengths > 0) and np.all(self.lengths <= self.p))
        content = table_content_sha256("raw", self.p, self.rows, self.lengths)
        self.assertEqual(content, self.meta["table_sha256"])
        if TABLE == COMMITTED.resolve():
            self.assertEqual((self.vocab, self.p), (131072, 32))
            manifest = json.loads((TABLE.parent / "manifest.json").read_text())
            self.assertEqual(content, manifest["tables"][TABLE.name]["sha256"])

    def test_projection_matches_g4_f64_codec_for_every_token_id(self):
        worst = 0.0
        checked = 0
        with torch.no_grad():
            for start in range(0, self.vocab, CHUNK):
                stop = min(start + CHUNK, self.vocab)
                codes = encode_f64(self.rows[start:stop], self.lengths[start:stop], self.p)
                expected = torch.from_numpy(codes @ self.weight64.T)
                actual = self.layer(torch.arange(start, stop)).double()
                worst = max(worst, float((actual - expected).abs().max()))
                torch.testing.assert_close(
                    actual, expected, rtol=RTOL, atol=ATOL, msg=f"ids {start}..{stop - 1}"
                )
                checked += stop - start
        self.assertEqual(checked, self.vocab)
        self.assertLess(worst, ATOL)

    def test_dense_reference_codec_matches_g4_f64_codec(self):
        ids = sample_ids(self.lengths)
        reference = torch.from_numpy(encode_f64(self.rows[ids], self.lengths[ids], self.p))
        dense = codec(torch.from_numpy(self.rows[ids]), torch.from_numpy(self.lengths[ids]))
        self.assertEqual(tuple(dense.shape), (len(ids), 256 * self.p))
        torch.testing.assert_close(dense.double(), reference, rtol=1e-5, atol=1e-6)

    def test_projection_gradient_matches_g4_f64_codec(self):
        ids = sample_ids(self.lengths)
        layer = KE2(self.rows, self.lengths, WIDTH)
        layer.projection.weight.data.copy_(self.layer.projection.weight.data)
        upstream = torch.randn(len(ids), WIDTH, generator=torch.Generator().manual_seed(3))
        (layer(torch.from_numpy(ids)) * upstream).sum().backward()
        codes = encode_f64(self.rows[ids], self.lengths[ids], self.p)
        expected = torch.from_numpy(upstream.double().numpy().T.dot(codes))
        scale = expected.abs().max()
        torch.testing.assert_close(
            layer.projection.weight.grad.double() / scale,
            expected / scale,
            rtol=0.0,
            atol=GRAD_ATOL,
        )

    def test_leading_dimensions_are_kept(self):
        ids = sample_ids(self.lengths)
        with torch.no_grad():
            flat = self.layer(torch.from_numpy(ids))
            batched = self.layer(torch.from_numpy(ids).view(2, 4, -1))
        self.assertEqual(tuple(batched.shape), (2, 4, len(ids) // 8, WIDTH))
        self.assertTrue(torch.equal(batched.reshape(len(ids), WIDTH), flat))


if __name__ == "__main__":
    unittest.main()
