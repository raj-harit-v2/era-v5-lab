#!/usr/bin/env python3
"""Unit tests for rotation_uz9ai.py using synthetic text only."""

import unittest

import pyarrow as pa

import rotation_uz9ai as audit


class CodePointChecksTest(unittest.TestCase):
    def codes(self, text):
        return [finding.code for finding in audit.inspect_text("synthetic", text)]

    def test_g1_flags_vowel_sign_after_space(self):
        findings = audit.inspect_text("synthetic", "ಅ \u0cbfಕ")
        self.assertEqual([(f.code, f.offset) for f in findings], [("G1", 2)])
        self.assertEqual(findings[0].hex_dump, "U+0C85 U+0020 U+0CBF U+0C95")

    def test_g1_flags_virama_after_latin_letter(self):
        findings = audit.inspect_text("synthetic", "a\u0ccdಕ")
        self.assertEqual(
            [(f.code, f.offset) for f in findings if f.code == "G1"], [("G1", 1)]
        )

    def test_valid_kannada_conjunct_is_not_g1_or_g2(self):
        self.assertEqual(self.codes("ಕ್\u200dಷ"), [])

    def test_g2_flags_boundary_and_adjacent_joiners_once(self):
        findings = audit.inspect_text("synthetic", "\u200d\u200cಕ")
        self.assertEqual([(f.code, f.offset) for f in findings], [("G2", 0)])
        self.assertIn("adjacent or doubled joiners", findings[0].note)
        self.assertIn("word start", findings[0].note)

    def test_g2_flags_joiner_at_word_end(self):
        findings = audit.inspect_text("synthetic", "ಕ\u200c ")
        self.assertEqual([(f.code, f.offset) for f in findings], [("G2", 1)])
        self.assertIn("word end", findings[0].note)

    def test_a1_and_a4(self):
        findings = audit.inspect_text("synthetic", "ಕ\u200b\ufffd")
        self.assertEqual([(f.code, f.offset) for f in findings], [("A1", 1), ("A4", 2)])

    def test_a6_flags_foreign_run_inside_kannada_word(self):
        findings = audit.inspect_text("synthetic", "ಕabcಗ")
        self.assertEqual([(f.code, f.offset) for f in findings], [("A6", 1)])
        self.assertEqual(findings[0].hex_dump, "U+0C95 U+0061 U+0062 U+0063 U+0C97")

    def test_separate_latin_word_is_not_a6(self):
        self.assertEqual(self.codes("ಕನ್ನಡ abc"), [])

    def test_common_script_modifier_is_not_a6(self):
        self.assertEqual(self.codes("ಕ\u02bcಗ"), [])

    def test_joiner_counts_use_arrow_kernels(self):
        texts = pa.array(["a\u200db", "\u200c", "\u200d\u200d"])
        self.assertEqual(audit.count_joiners(texts), (3, 1))

    def test_hex_context_is_limited_to_three_each_side(self):
        text = "abcdef\ufffdghijkl"
        self.assertEqual(
            audit.hex_context(text, 6, 7),
            "U+0064 U+0065 U+0066 U+FFFD U+0067 U+0068 U+0069",
        )


if __name__ == "__main__":
    unittest.main()
