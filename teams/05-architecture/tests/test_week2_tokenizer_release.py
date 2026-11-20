"""Tokenizer releases in the week-2 harness: v0, frozen C3 and frozen p1536.

`--tokenizer-release` selects the pinned tokenizer.json sha256. C3 and p1536 normalize text inside
the tokenizer, so the table bytes reconstruct the normalized text and BPB divides by the original
UTF-8 bytes (test_week2_scoring.py covers the scoring side).

The p1536 checks use the released tokenizer (teams/03-tokenizer/release/tokenizer.json, not in git;
see that folder's README) and Team 4's committed p1536 table. They are skipped when the tokenizer
file is absent. Set ERA_P1536_TOKENIZER to use a copy elsewhere.
"""

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
from tokenizers import Tokenizer, models, normalizers

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
from week2 import artifacts as artifacts_module
from week2.artifacts import (
    Artifacts,
    C3_SHA256,
    NORMALIZING_TOKENIZER_SHAS,
    P1536_SHA256,
    TOKENIZER_RELEASES,
    V0_SHA256,
    sha256,
)

P1536_TOKENIZER = Path(
    os.environ.get("ERA_P1536_TOKENIZER", TEAM.parent / "03-tokenizer/release/tokenizer.json")
)
P1536_TABLE = TEAM.parent / "04-ke2/results/tables/p1536-s0/raw_table_P32.npz"
# Content sha256 of Team 4's p1536 raw P = 32 table (teams/04-ke2/results/tables/p1536-s0/manifest.json).
P1536_TABLE_CONTENT_SHA256 = "21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a"
# Bengali YA + NUKTA, which both normalizing releases compose to U+09DF; Malayalam NA + VIRAMA + ZWJ,
# which both compose to the chillu U+0D7B.
DECOMPOSED = "\u09af\u09bc \u0d28\u0d4d\u200d"


class ReleasePins(unittest.TestCase):
    def test_release_names_map_to_the_published_hashes(self):
        self.assertEqual(
            TOKENIZER_RELEASES,
            {"v0": V0_SHA256, "frozen-c3": C3_SHA256, "frozen-p1536": P1536_SHA256},
        )
        self.assertEqual(
            P1536_SHA256, "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
        )

    def test_only_c3_and_p1536_normalize(self):
        self.assertEqual(NORMALIZING_TOKENIZER_SHAS, {C3_SHA256, P1536_SHA256})
        self.assertNotIn(V0_SHA256, NORMALIZING_TOKENIZER_SHAS)


class NormalizingArtifacts(unittest.TestCase):
    """A small normalizing tokenizer: the table must reconstruct the normalized text, not the raw text."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.tokpath = root / "tokenizer.json"
        self.tablepath = root / "raw.npz"
        pieces = ["a", "b", "c", "<|begin_of_text|>", "<|pad|>"]
        tok = Tokenizer(models.WordLevel(dict(zip(pieces, range(5))), unk_token="c"))
        tok.normalizer = normalizers.Replace("x", "a")
        tok.add_special_tokens(pieces[3:])
        tok.save(str(self.tokpath))
        rows = np.zeros((5, 32), dtype=np.uint8)
        lengths = np.zeros(5, dtype=np.int16)
        for i, piece in enumerate(pieces):
            raw = piece.encode()
            rows[i, : len(raw)] = list(raw)
            lengths[i] = len(raw)
        h = hashlib.sha256(b"ke2-table-v2|raw|32|")
        h.update(rows.tobytes())
        h.update(lengths.tobytes())
        np.savez_compressed(
            self.tablepath,
            bytes=rows,
            lengths=lengths,
            pos_dim=32,
            kind="raw",
            format_version=2,
            tokenizer_sha256=sha256(self.tokpath),
            table_sha256=h.hexdigest(),
            n_truncated=0,
            n_empty_rows=0,
        )
        self.sha = sha256(self.tokpath)

    def tearDown(self):
        self.tmp.cleanup()

    def load(self):
        return Artifacts(self.tokpath, self.tablepath, expected_tokenizer_sha=self.sha, expected_vocab=5)

    def test_a_normalizing_release_checks_the_normalized_text(self):
        with mock.patch.object(
            artifacts_module, "NORMALIZING_TOKENIZER_SHAS", frozenset({self.sha})
        ):
            a = self.load()
        self.assertTrue(a.normalize_input)
        self.assertEqual(a.encode("x"), [0])

    def test_a_non_normalizing_release_rejects_text_the_tokenizer_changes(self):
        a = self.load()
        self.assertFalse(a.normalize_input)
        self.assertEqual(a.encode("a"), [0])
        with self.assertRaisesRegex(ValueError, "does not reconstruct"):
            a.encode("x")


class FrozenP1536(unittest.TestCase):
    def setUp(self):
        if not P1536_TOKENIZER.is_file():
            self.skipTest(f"{P1536_TOKENIZER} is absent (see teams/03-tokenizer/release/README.md)")
        if sha256(P1536_TOKENIZER) != P1536_SHA256:
            self.fail(f"{P1536_TOKENIZER} is not the frozen p1536 tokenizer")

    def test_the_committed_table_passes_every_artifact_check(self):
        a = Artifacts(P1536_TOKENIZER, P1536_TABLE, expected_tokenizer_sha=TOKENIZER_RELEASES["frozen-p1536"])
        self.assertEqual(a.table_content_sha, P1536_TABLE_CONTENT_SHA256)
        self.assertTrue(a.normalize_input)
        self.assertEqual((len(a.lengths), a.pos_dim, a.bos_id, a.pad_id), (131072, 32, 130725, 130726))

    def test_the_v0_pin_rejects_the_p1536_file(self):
        with self.assertRaisesRegex(ValueError, "Tokenizer identity mismatch"):
            Artifacts(P1536_TOKENIZER, P1536_TABLE)

    def test_encode_reconstructs_the_normalized_bytes(self):
        a = Artifacts(P1536_TOKENIZER, P1536_TABLE, expected_tokenizer_sha=P1536_SHA256)
        ids = a.encode(DECOMPOSED)
        normalized = a.tokenizer.normalizer.normalize_str(DECOMPOSED).encode("utf8")
        rebuilt = b"".join(a.bytes[i, : int(a.lengths[i])].tobytes() for i in ids)
        self.assertEqual(rebuilt, normalized)
        self.assertLess(len(normalized), len(DECOMPOSED.encode("utf8")))


if __name__ == "__main__":
    unittest.main()
