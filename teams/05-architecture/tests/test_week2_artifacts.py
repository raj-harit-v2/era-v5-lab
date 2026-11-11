import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from tokenizers import Tokenizer, models

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
from week2.artifacts import Artifacts, sha256
from week2.data import DocumentWindows


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.tokpath = self.root / "tokenizer.json"
        self.tablepath = self.root / "raw.npz"
        pieces = ["a", "b", "c", "<|begin_of_text|>", "<|pad|>"]
        tok = Tokenizer(models.WordLevel(dict(zip(pieces, range(5))), unk_token="c"))
        tok.add_special_tokens(pieces[3:])
        tok.save(str(self.tokpath))
        self.rows = np.zeros((5, 32), dtype=np.uint8)
        self.lengths = np.zeros(5, dtype=np.int16)
        for i, piece in enumerate(pieces):
            raw = piece.encode()
            self.rows[i, : len(raw)] = list(raw)
            self.lengths[i] = len(raw)
        self.save()

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, kind="raw", bad_hash=False):
        h = hashlib.sha256(f"ke2-table-v2|{kind}|32|".encode())
        h.update(self.rows.tobytes())
        h.update(self.lengths.tobytes())
        np.savez_compressed(
            self.tablepath,
            bytes=self.rows,
            lengths=self.lengths,
            pos_dim=32,
            kind=kind,
            format_version=2,
            tokenizer_sha256=sha256(self.tokpath),
            table_sha256="bad" if bad_hash else h.hexdigest(),
            n_truncated=0,
            n_empty_rows=0,
        )

    def load(self):
        return Artifacts(
            self.tokpath,
            self.tablepath,
            expected_tokenizer_sha=sha256(self.tokpath),
            expected_vocab=5,
        )

    def test_valid_artifacts_and_text(self):
        self.assertEqual(self.load().encode("a"), [0])

    def test_wrong_tokenizer_hash(self):
        with self.assertRaisesRegex(ValueError, "Tokenizer identity"):
            Artifacts(
                self.tokpath,
                self.tablepath,
                expected_tokenizer_sha="0" * 64,
                expected_vocab=5,
            )

    def test_wrong_table_tokenizer_binding(self):
        self.tokpath.write_text(self.tokpath.read_text() + " ", encoding="utf8")
        with self.assertRaisesRegex(ValueError, "different tokenizer"):
            self.load()

    def test_decoded_table_rejected(self):
        self.save(kind="decode")
        with self.assertRaisesRegex(ValueError, "RAW table"):
            self.load()

    def test_corrupt_content_rejected(self):
        self.save(bad_hash=True)
        with self.assertRaisesRegex(ValueError, "content hash"):
            self.load()

    def test_semantically_wrong_row_rejected_even_with_valid_hash(self):
        self.rows[0, 0] = ord("b")
        self.save()
        with self.assertRaisesRegex(ValueError, "row mismatch"):
            self.load()

    def test_lossy_text_roundtrip_rejected(self):
        with self.assertRaisesRegex(ValueError, "reconstruct"):
            self.load().encode("A")

    def test_duplicate_heldout_ids_rejected(self):
        path = self.root / "heldout.jsonl"
        path.write_text(
            '{"id":"same","text":"a"}\n{"id":"same","text":"b"}\n', encoding="utf8"
        )
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            DocumentWindows(path, self.load(), 8, require_ids=True)

    def test_missing_heldout_id_rejected(self):
        path = self.root / "heldout.jsonl"
        path.write_text('{"text":"a"}\n', encoding="utf8")
        with self.assertRaisesRegex(ValueError, "missing document id"):
            DocumentWindows(path, self.load(), 8, require_ids=True)


if __name__ == "__main__":
    unittest.main()
