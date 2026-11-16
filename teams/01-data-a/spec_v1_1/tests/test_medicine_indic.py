"""Tests for the rule in sheets/medicine_indic.md (Data B's DB-C6-001), loaded the way harmtest/harm_test.py loads it.
All text is made up.

  python3 -m unittest discover -s spec_v1_1/tests      (from teams/01-data-a)
"""
import sys
import unittest
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPEC.parent / "harmtest"))  # harm_test.py moved here from tools/ (theschoolofai/era-v5-lab#244)
import harm_test  # noqa: E402  (only its loader is used; the file is not changed)

SHEET = SPEC / "sheets" / "medicine_indic.md"
RULES, _ = harm_test.load_rules(SHEET)
RULES = RULES["RULES_BY_ID"]
R = "DB-C6-001"
TE = "తెలుగు వాక్యం"  # made-up Telugu words, to show the text around the dots is untouched


def run(text, pack="ind-te-sangraha-v"):
    return RULES[R]({"doc_id": "0" * 16, "text": text, "url": "", "lang_label": "te", "pack_id": pack})


class Sheet(unittest.TestCase):
    def test_one_indic_rule(self):
        self.assertEqual(sorted(RULES), [R])

    def test_off_on_other_packs(self):
        text = TE + " . . " + TE
        for pack in ("ind-te-sangraha-s", "ind-hi-sangraha-s", "en-dclm", None):
            self.assertEqual(run(text, pack), ("keep", text), pack)


class C6Dots(unittest.TestCase):
    def test_runs_of_dots_become_an_ellipsis(self):
        for dots in (". .", "..", ". . .", " .\t.", ".  .  ."):
            text = TE + dots + " " + TE
            self.assertEqual(run(text), ("fix", TE + ("" if dots[0] == "." else dots[0]) + "..." + " " + TE), repr(dots))

    def test_four_dots_become_three(self):
        self.assertEqual(run(TE + "...."), ("fix", TE + "..."))  # the documented side effect

    def test_single_dots_ellipses_and_line_breaks_stay(self):
        for text in (TE + ". " + TE, TE + "…", TE + "...", TE + ".\n." + TE, "3.67", TE + ".\r\n."):
            self.assertEqual(run(text), ("keep", text), repr(text))

    def test_joiners_are_untouched(self):
        zwj, zwnj = chr(0x200D), chr(0x200C)
        text = "క" + zwj + "్ష" + zwnj + " . . " + TE
        new = run(text)[1]
        self.assertEqual((new.count(zwj), new.count(zwnj)), (1, 1))

    def test_idempotent(self):
        once = run(TE + " . . " + TE + ".." + TE)[1]
        self.assertEqual(run(once), ("keep", once))


if __name__ == "__main__":
    unittest.main()
