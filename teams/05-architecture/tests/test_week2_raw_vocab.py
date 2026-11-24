"""Raw-byte ingestion contract; independent of the private KAS implementation."""

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
sys.path.insert(0, str(TEAM.parent / "04-ke2/src"))
from week2.raw_vocab import VocabHoleError, raw_token_bytes
from ke2.tokenizer import BYTE_TO_UNI, raw_bytes_for_id


class RawVocabularyTests(unittest.TestCase):
    def test_all_byte_values_match_team4_including_invalid_utf8(self):
        pieces = {BYTE_TO_UNI[i]: i for i in range(256)}
        spec = {"model": {"vocab": pieces}}
        bundle = SimpleNamespace(added={}, id_to_piece={i: p for p, i in pieces.items()})
        actual = raw_token_bytes(spec, 256)
        self.assertEqual(actual, tuple(raw_bytes_for_id(bundle, i) for i in range(256)))
        self.assertEqual(actual, tuple(bytes([i]) for i in range(256)))
        self.assertEqual(actual[0], b"\x00")
        self.assertEqual(actual[255], b"\xff")
        self.assertEqual(len(set(actual)), 256)

    def test_added_tokens_override_model_pieces_and_keep_literal_utf8(self):
        spec = {
            "model": {"vocab": {"x": 0, "y": 1}},
            "added_tokens": [{"id": 0, "content": "<|pad|>"}, {"id": 1, "content": "नमस्ते"}],
        }
        self.assertEqual(raw_token_bytes(spec, 2), (b"<|pad|>", "नमस्ते".encode("utf8")))

    def test_added_token_can_fill_a_model_vocab_gap(self):
        spec = {"model": {"vocab": {"a": 0}}, "added_tokens": [{"id": 1, "content": "<s>"}]}
        self.assertEqual(raw_token_bytes(spec, 2), (b"a", b"<s>"))

    def test_missing_ids_raise_vocab_hole_error(self):
        for pieces in ({"a": 1}, {"a": 0, "b": 2}):
            with self.subTest(pieces=pieces), self.assertRaisesRegex(VocabHoleError, "hole in id space"):
                raw_token_bytes({"model": {"vocab": pieces}}, 3)

    def test_empty_model_and_added_tokens_raise_vocab_hole_error(self):
        for spec in (
            {"model": {"vocab": {"": 0}}},
            {"model": {"vocab": {"a": 0}}, "added_tokens": [{"id": 0, "content": ""}]},
        ):
            with self.subTest(spec=spec), self.assertRaisesRegex(VocabHoleError, "empty byte string"):
                raw_token_bytes(spec, 1)

    def test_32_byte_limit_counts_bytes_and_never_truncates(self):
        self.assertEqual(raw_token_bytes({"model": {"vocab": {"a" * 32: 0}}}, 1), (b"a" * 32,))
        for spec in (
            {"model": {"vocab": {"a" * 33: 0}}},
            {"model": {"vocab": {}}, "added_tokens": [{"id": 0, "content": "न" * 11}]},
        ):
            with self.subTest(spec=spec), self.assertRaisesRegex(ValueError, "33 bytes.*limit 32"):
                raw_token_bytes(spec, 1)

    def test_non_bytelevel_piece_is_rejected_instead_of_reencoded(self):
        with self.assertRaisesRegex(ValueError, "non-ByteLevel"):
            raw_token_bytes({"model": {"vocab": {"न": 0}}}, 1)

    def test_p1536_size_keeps_every_id_including_high_added_ids(self):
        size = 131072
        def piece(tid):
            return "".join(BYTE_TO_UNI[b] for b in tid.to_bytes(3, "little"))
        spec = {
            "model": {"vocab": {piece(i): i for i in range(size - 1)}},
            "added_tokens": [{"id": size - 1, "content": "<last>"}],
        }
        rows = raw_token_bytes(spec, size)
        self.assertEqual(len(rows), size)
        self.assertEqual(len(set(rows)), size)
        self.assertEqual(rows[130822], (130822).to_bytes(3, "little"))
        self.assertEqual(rows[-1], b"<last>")


if __name__ == "__main__":
    unittest.main()
