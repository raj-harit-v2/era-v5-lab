"""Count integrity and explicit prior policy, independent of KAS head internals."""

import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

TEAM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEAM / "harness"))
from week2.artifacts import P1536_SHA256
from week2.unigram import additive_log_prior, load_counts

COUNTS_SHA = "0768b5982825645a796abc76ec23c737837cfacc8f6b089335e5ce5446def3a6"
BY_SOURCE_SHA = "241f161bdcd46b252540f9abf49b1b26a0c13d023349edb0cc7307bea0704b82"


class UnigramTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "counts.json"
        self.spec = {
            "tokenizer_sha256": P1536_SHA256, "vocab_size": 4,
            "special_ids": [1, 2], "eos_id": 2, "total": [4, 0, 0, 2],
            "summary": {"tokens": 6, "ids_seen": 2, "ids_zero": 2, "special_ids_seen": 0, "docs": 3},
            "sources": {"training.txt": {"sha256": "a" * 64, "bytes": 10, "docs": 3, "tokens": 6}},
        }

    def load(self, spec=None, **overrides):
        self.path.write_text(json.dumps(self.spec if spec is None else spec), encoding="utf8")
        options = dict(expected_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),
                       expected_tokenizer_sha256=P1536_SHA256, expected_vocab_size=4)
        options.update(overrides)
        return load_counts(self.path, **options)

    def test_hash_tokenizer_and_vocabulary_binding(self):
        for options, error in (({"expected_sha256": "0" * 64}, "file hash"),
                               ({"expected_tokenizer_sha256": "0" * 64}, "tokenizer mismatch"),
                               ({"expected_vocab_size": 5}, "vocabulary mismatch")):
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, error):
                self.load(**options)

    def test_invalid_count_values_and_length_are_rejected(self):
        for value in (-1, True, 1.5):
            spec = copy.deepcopy(self.spec)
            spec["total"][0] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Token count"):
                self.load(spec)
        spec["total"] = [1]
        with self.assertRaisesRegex(ValueError, "one entry per token"):
            self.load(spec)

    def test_summary_and_source_receipts_are_verified(self):
        for key in ("tokens", "ids_seen", "ids_zero", "special_ids_seen"):
            spec = copy.deepcopy(self.spec)
            spec["summary"][key] += 1
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "summary mismatch"):
                self.load(spec)
        for key in ("docs", "tokens"):
            spec = copy.deepcopy(self.spec)
            spec["sources"]["training.txt"][key] += 1
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "source totals"):
                self.load(spec)
        spec = copy.deepcopy(self.spec)
        spec["sources"]["training.txt"]["sha256"] = "unverified"
        with self.assertRaisesRegex(ValueError, "Source hash"):
            self.load(spec)

    def test_invalid_specials_and_eos_are_rejected(self):
        for specials in ([1, 1, 2], [-1, 2], [True, 2]):
            spec = copy.deepcopy(self.spec)
            spec["special_ids"] = specials
            with self.subTest(specials=specials), self.assertRaises(ValueError):
                self.load(spec)
        spec["special_ids"] = [1]
        with self.assertRaisesRegex(ValueError, "EOS"):
            self.load(spec)

    def test_explicit_smoothing_and_document_eos_match_known_probabilities(self):
        counts = self.load()
        original = counts.counts
        values, identity = additive_log_prior(counts, smoothing=1.0, add_eos_per_document=True)
        for logp, numerator in zip(values, (5, 1, 4, 3)):
            self.assertAlmostEqual(math.exp(logp), numerator / 13)
        self.assertAlmostEqual(math.fsum(map(math.exp, values)), 1.0)
        self.assertEqual(counts.counts, original)
        self.assertTrue(identity["add_eos_per_document"])
        self.assertEqual(identity["source_weighting"], "raw_total")
        plain, plain_identity = additive_log_prior(counts, smoothing=1.0, add_eos_per_document=False)
        self.assertAlmostEqual(math.exp(plain[2]), 1 / 10)
        self.assertNotEqual(identity, plain_identity)

    def test_policy_arguments_are_required_and_invalid_smoothing_fails(self):
        counts = self.load()
        with self.assertRaises(TypeError):
            additive_log_prior(counts)
        for alpha in (-1, True, float("nan"), float("inf")):
            with self.subTest(alpha=alpha), self.assertRaisesRegex(ValueError, "Smoothing"):
                additive_log_prior(counts, smoothing=alpha, add_eos_per_document=False)
        with self.assertRaisesRegex(ValueError, "positive finite mass"):
            additive_log_prior(counts, smoothing=0, add_eos_per_document=False)
        with self.assertRaisesRegex(ValueError, "EOS policy"):
            additive_log_prior(counts, smoothing=1, add_eos_per_document=1)

    def test_eos_correction_cannot_be_applied_twice(self):
        spec = copy.deepcopy(self.spec)
        spec["total"] = [4, 0, 3, 2]
        spec["summary"].update(tokens=9, ids_seen=3, ids_zero=1, special_ids_seen=1)
        spec["sources"]["training.txt"]["tokens"] = 9
        counts = self.load(spec)
        with self.assertRaisesRegex(ValueError, "already contains EOS"):
            additive_log_prior(counts, smoothing=1, add_eos_per_document=True)

    def test_crlf_normalization_is_explicit_and_preserves_both_hashes(self):
        raw = (json.dumps(self.spec) + "\n").encode()
        self.path.write_bytes(raw.replace(b"\n", b"\r\n"))
        options = dict(expected_sha256=hashlib.sha256(raw).hexdigest(),
                       expected_tokenizer_sha256=P1536_SHA256, expected_vocab_size=4)
        with self.assertRaisesRegex(ValueError, "file hash"):
            load_counts(self.path, **options)
        counts = load_counts(self.path, **options, checksum_mode="lf")
        self.assertEqual(counts.identity()["counts_verified_sha256"], options["expected_sha256"])
        self.assertEqual(counts.identity()["counts_file_sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertNotEqual(counts.file_sha256, counts.verified_sha256)
        with self.assertRaisesRegex(ValueError, "checksum mode"):
            load_counts(self.path, **options, checksum_mode="unverified")

    def test_committed_g3_artifacts_match_receipts_and_all_per_id_totals(self):
        root = TEAM.parent / "03-tokenizer/counts"
        counts = load_counts(root / "p1536_counts.json", expected_sha256=COUNTS_SHA,
                             expected_tokenizer_sha256=P1536_SHA256, expected_vocab_size=131072,
                             checksum_mode="lf")
        self.assertEqual((sum(counts.counts), counts.documents, counts.eos_id), (144239593, 288350, 130822))
        self.assertEqual(sum(n == 0 for n in counts.counts), 9702)
        self.assertEqual(len(counts.special_ids), 356)
        self.assertTrue(all(counts.counts[i] == 0 for i in counts.special_ids))
        raw = (root / "p1536_counts_by_source.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(), BY_SOURCE_SHA)
        by_source = json.loads(raw)
        self.assertEqual(by_source["tokenizer_sha256"], P1536_SHA256)
        self.assertEqual(set(by_source["by_source"]), {s[0] for s in counts.sources})
        totals = [0] * 131072
        for name, _, _, _, tokens in counts.sources:
            source = by_source["by_source"][name]
            self.assertEqual(sum(source.values()), tokens)
            for tid, value in source.items():
                totals[int(tid)] += value
        self.assertEqual(tuple(totals), counts.counts)
        values, identity = additive_log_prior(counts, smoothing=1.0, add_eos_per_document=True)
        self.assertTrue(all(map(math.isfinite, values)))
        self.assertAlmostEqual(math.fsum(map(math.exp, values)), 1.0)
        self.assertEqual(identity["counts_verified_sha256"], COUNTS_SHA)
        script = (root / "count_p1536.py").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(script).hexdigest(), "cf86d54c2ce7eeb81f870f0a604185ef276b479d121a6dee86dc7e9d0149a19b")
        # This is a tested explicit example, not an approved training default.


if __name__ == "__main__":
    unittest.main()
