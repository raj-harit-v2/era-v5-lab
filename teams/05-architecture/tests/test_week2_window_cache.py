"""Prove the optional numeric cache preserves the native data/scoring contract."""

from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import torch

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
from week2.data import BatchStream, DocumentWindows, build_window_cache
from week2.evaluation import evaluate


class ByteFixture:
    # Independent fixture IDs are literal UTF-8 bytes, not course tokenizer IDs.
    bos_id, pad_id = 256, 257
    lengths = [1] * 256 + [0, 0]

    def encode(self, text):
        return list(text.encode("utf8"))

    def identity(self):
        return dict(kind="test-byte-fixture", bos_id=self.bos_id, pad_id=self.pad_id)


class UniformModel(torch.nn.Module):
    def forward(self, x, valid):
        return torch.zeros(*x.shape, 258, device=x.device)


class WindowCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / "input.jsonl"
        self.cache = self.root / "cache"
        self.artifacts = ByteFixture()
        self.texts = ["Hello world!", "नमस्ते\n", "", "ଓଡ଼ିଆ", "a", "0123456789" * 3]
        self.input.write_text("".join(
            json.dumps({"id": str(i), "text": text}, ensure_ascii=False) + "\n"
            for i, text in enumerate(self.texts)), encoding="utf8")
        self.environment = patch.dict(os.environ)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        os.environ.pop("G5_DOCUMENT_CACHE_DIR", None)

    def native(self, **kwargs):
        return DocumentWindows(self.input, self.artifacts, 7, **kwargs)

    def cached(self, **kwargs):
        destination = build_window_cache(self.input, self.artifacts, 7, self.cache, **kwargs)
        with patch.dict(os.environ, G5_DOCUMENT_CACHE_DIR=str(self.cache)):
            return self.native(**kwargs), destination

    def assert_batches_equal(self, a, b):
        for left, right in zip(a, b):
            self.assertTrue(torch.equal(left, right))

    def test_all_windows_padding_and_metadata_match_native(self):
        native = self.native()
        cached, directory = self.cached()
        self.assertEqual(list(native.windows), list(cached.windows))
        self.assertEqual(native.windows[-1], cached.windows[-1])
        self.assertEqual(native.windows[1:4], cached.windows[1:4])
        for name in ("raw_bytes", "tokens", "document_count", "document_hashes",
                     "slice_raw_bytes", "pad_id", "seq_len"):
            self.assertEqual(getattr(native, name), getattr(cached, name))
        self.assertEqual(native.window_slices, list(cached.window_slices))
        self.assert_batches_equal(native.batch(range(len(native.windows)), "cpu"),
                                  cached.batch(range(len(cached.windows)), "cpu"))
        self.assertFalse(cached.windows.tokens.flags.writeable)
        self.assertEqual(set(p.name for p in directory.iterdir()),
                         {"metadata.json", "tokens.bin", "windows.bin", "document_hashes.bin"})

    def test_sampler_order_epoch_rollover_and_resume_match(self):
        cached, _ = self.cached()
        original = BatchStream(self.native(), 5, 1235)
        mapped = BatchStream(cached, 5, 1235)
        for _ in range(9):
            self.assert_batches_equal(original.next("cpu"), mapped.next("cpu"))
        resumed = BatchStream(cached, 5, 0)
        resumed.load_state_dict(mapped.state_dict())
        for _ in range(9):
            expected = original.next("cpu")
            self.assert_batches_equal(expected, mapped.next("cpu"))
            self.assert_batches_equal(expected, resumed.next("cpu"))

    def test_bpb_and_byte_denominator_match_exactly(self):
        cached, _ = self.cached()
        model = UniformModel()
        for batch in (1, 4):
            expected = evaluate(model, self.native(), batch, "cpu", nullcontext)
            actual = evaluate(model, cached, batch, "cpu", nullcontext)
            self.assertEqual(expected, actual)

    def test_source_sidecar_binding_and_window_slices_match(self):
        sources = self.root / "sources.jsonl"
        sources.write_text("".join(json.dumps({
            "id": str(i), "slice": "en" if i % 2 else "code",
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        }) + "\n" for i, text in enumerate(self.texts)))
        native = self.native(require_ids=True, sources_path=sources)
        cached, _ = self.cached(require_ids=True, sources_path=sources)
        self.assertEqual(native.window_slices, list(cached.window_slices))
        self.assertEqual(native.slice_raw_bytes, cached.slice_raw_bytes)
        with patch.dict(os.environ, G5_DOCUMENT_CACHE_DIR=str(self.cache)):
            with self.assertRaises(FileNotFoundError):
                self.native(sources_path=sources)  # require_ids is part of identity.
        sources.write_text(sources.read_text().replace('"slice": "code"', '"slice": "en"', 1))
        with patch.dict(os.environ, G5_DOCUMENT_CACHE_DIR=str(self.cache)):
            with self.assertRaises(FileNotFoundError):
                self.native(require_ids=True, sources_path=sources)

    def test_missing_cache_never_silently_falls_back(self):
        with patch.dict(os.environ, G5_DOCUMENT_CACHE_DIR=str(self.cache)):
            with self.assertRaises(FileNotFoundError):
                self.native()
        with patch.dict(os.environ, G5_DOCUMENT_CACHE_DIR=""):
            with self.assertRaises(ValueError):
                self.native()

    def test_input_artifact_and_sequence_changes_cannot_reuse_cache(self):
        self.cached()
        with patch.dict(os.environ, G5_DOCUMENT_CACHE_DIR=str(self.cache)):
            with self.assertRaises(FileNotFoundError):
                DocumentWindows(self.input, self.artifacts, 8)
            with patch.object(ByteFixture, "pad_id", 258):
                with self.assertRaises(FileNotFoundError):
                    self.native()
            self.input.write_text(
                self.input.read_text(encoding="utf8") + '{"id":"extra","text":"z"}\n',
                encoding="utf8",
            )
            with self.assertRaises(FileNotFoundError):
                self.native()

    def test_corruption_and_truncation_fail_closed(self):
        # Build without opening memory maps so Windows permits overwriting files.
        directory = build_window_cache(self.input, self.artifacts, 7, self.cache)
        token_file = directory / "tokens.bin"
        content = token_file.read_bytes()
        token_file.write_bytes(bytes([content[0] ^ 1]) + content[1:])
        with patch.dict(os.environ, G5_DOCUMENT_CACHE_DIR=str(self.cache)):
            with self.assertRaisesRegex(ValueError, "checksum"):
                self.native()
            token_file.write_bytes(content[:-1])
            with self.assertRaisesRegex(ValueError, "size"):
                self.native()

    def test_metadata_identity_tampering_is_rejected(self):
        _, directory = self.cached()
        metadata_path = directory / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["identity"]["seq_len"] = 999
        metadata_path.write_text(json.dumps(metadata))
        with patch.dict(os.environ, G5_DOCUMENT_CACHE_DIR=str(self.cache)):
            with self.assertRaisesRegex(ValueError, "identity"):
                self.native()

    def test_bad_ids_and_source_binding_are_rejected_before_finalize(self):
        self.input.write_text('{"id":"a","text":"one"}\n{"id":"a","text":"two"}\n')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            build_window_cache(self.input, self.artifacts, 7, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])
        self.input.write_text('{"text":"missing id"}\n')
        with self.assertRaisesRegex(ValueError, "missing document id"):
            build_window_cache(self.input, self.artifacts, 7, self.cache, require_ids=True)

    def test_encoder_failure_and_empty_data_never_publish_partial_cache(self):
        def fail_after_one(records):
            doc = next(records)
            yield doc, self.artifacts.encode(doc["text"])
            raise ValueError("encoding failed")
        with self.assertRaisesRegex(ValueError, "encoding failed"):
            build_window_cache(self.input, self.artifacts, 7, self.cache,
                               encode_records=fail_after_one)
        self.assertEqual(list(self.cache.iterdir()), [])
        self.input.write_text("")
        with self.assertRaisesRegex(ValueError, "Empty"):
            build_window_cache(self.input, self.artifacts, 7, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
