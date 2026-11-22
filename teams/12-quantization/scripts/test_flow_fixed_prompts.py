#!/usr/bin/env python3
"""flow_fixed_prompts.py: tokenizer sha256 from scores.json, public rows, agreement per source:  python test_flow_fixed_prompts.py"""
import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_fixed_prompts as f  # noqa: E402

SHA = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"


class TokenizerShaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def scores(self, name, **kw):
        (self.d / name).write_text(json.dumps(kw), encoding="utf-8"); return self.d / name

    def test_default_file_in_the_gguf_dir(self):
        self.scores("m-scores.json", tokenizer_sha256=SHA)
        self.assertEqual(f.tokenizer_sha_from_scores(self.d, None), (SHA, None))

    def test_explicit_path_wins(self):
        other = self.scores("elsewhere.json", tokenizer_sha256=SHA)
        self.scores("m-scores.json", tokenizer_sha256="0" * 64)
        self.assertEqual(f.tokenizer_sha_from_scores(self.d, other), (SHA, None))

    def test_not_found_or_ambiguous_or_empty_is_noted_not_guessed(self):
        sha, why = f.tokenizer_sha_from_scores(self.d, None)
        self.assertIsNone(sha); self.assertIn("no *-scores.json", why)
        self.scores("a-scores.json", tokenizer_sha256=SHA); self.scores("b-scores.json", tokenizer_sha256=SHA)
        sha, why = f.tokenizer_sha_from_scores(self.d, None)
        self.assertIsNone(sha); self.assertIn("2 *-scores.json", why)
        sha, why = f.tokenizer_sha_from_scores(self.d, self.scores("c.json", tokenizer_sha256=""))
        self.assertIsNone(sha); self.assertIn("no tokenizer_sha256", why)


class PublicRowTests(unittest.TestCase):
    def row(self, private):
        return {"id": "s", "private": private, "output_ids": [5, 6, 7], "text_sha256": "x"}

    def test_team10_row_keeps_only_a_sha256_of_its_ids(self):
        out = f.public_row(self.row(True))
        self.assertNotIn("output_ids", out); self.assertNotIn("private", out)
        self.assertEqual(len(out["output_ids_sha256"]), 64)

    def test_our_row_keeps_its_ids_and_the_input_is_not_changed(self):
        r = self.row(False)
        self.assertEqual(f.public_row(r)["output_ids"], [5, 6, 7])
        f.public_row(self.row(True)); self.assertIn("private", r)


class AgreementBySourceTests(unittest.TestCase):
    def rows(self, outs, srcs):
        return [{"id": i, "output_ids": o, **({"source": s} if s else {})} for i, (o, s) in enumerate(zip(outs, srcs))]

    def test_manifest_run_reports_the_two_sources_apart_and_no_pooled_number(self):
        srcs = ["g10", "g10", "g10", "g12", "g12"]
        base = self.rows([[1, 2], [1, 2], [1, 2], [3, 4], [3, 4]], srcs)
        other = self.rows([[1, 2], [1, 9], [7, 7], [3, 4], [3, 4]], srcs)
        a = f.agreement_by_source(base, other)
        self.assertEqual(list(a), ["g10_3", "g12_fill_2"])
        self.assertEqual(a["g10_3"], {"identical_outputs": 1, "of": 3, "mean_shared_prefix_fraction": 0.5})
        self.assertEqual(a["g12_fill_2"], {"identical_outputs": 2, "of": 2, "mean_shared_prefix_fraction": 1.0})

    def test_a_source_with_no_rows_is_left_out(self):
        base = self.rows([[1]], ["g12"])
        self.assertEqual(list(f.agreement_by_source(base, base)), ["g12_fill_1"])

    def test_plain_run_is_unchanged(self):
        base, other = self.rows([[1, 2], [3]], [None, None]), self.rows([[1, 2], [4]], [None, None])
        self.assertEqual(f.agreement_by_source(base, other), f.agreement(base, other))


if __name__ == "__main__":
    unittest.main()
