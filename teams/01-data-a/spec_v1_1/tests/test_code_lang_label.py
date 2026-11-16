"""Harm test: a spec v1 code rule fires on a code doc whose lang_label is "code" (TSAI, Gate 2 decision).

The Week 2 sample labels every code doc lang_label = "code", which is in no rule's LANGS. The code rules in
spec_v1/sheets/specv1.md also check pack_id (Smita's fix, theschoolofai/era-v5-lab#244), and this test shows that this is
what lets them run. It uses DA-A1-001 (delete U+FEFF, the BOM), loaded and run with harmtest/harm_test.py's own
load_rules and run_rule, as the harm test runs it. The doc is made up.

  python3 -m unittest discover -s spec_v1_1/tests      (from teams/01-data-a)
"""
import ast
import re
import sys
import unittest
from pathlib import Path

DATA_A = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DATA_A / "harmtest"))
import harm_test  # noqa: E402  (only its loader and run_rule are used; the file is not changed)

SHEET = DATA_A / "spec_v1" / "sheets" / "specv1.md"
NS, _ = harm_test.load_rules(SHEET)
RULE_ID = "DA-A1-001"
RULE = NS["RULES_BY_ID"][RULE_ID]
CODE_PACKS = ("code-cpp", "code-go", "code-java", "code-js-ts", "code-python", "code-rust")
TEXT = "﻿import os\nprint(os.getcwd())\n"  # a made-up Python file that starts with a BOM
FIXED = "import os\nprint(os.getcwd())\n"


def doc(pack, lang="code", doc_id="0" * 16):
    return {"doc_id": doc_id, "text": TEXT, "url": "", "lang_label": lang, "pack_id": pack}


class CodeLangLabel(unittest.TestCase):
    def test_lang_label_code_is_not_in_the_rules_languages(self):
        # the premise: on lang_label alone, the rule would skip these docs
        block = SHEET.read_text(encoding="utf-8").split(f'RULE_ID = "{RULE_ID}"', 1)[1].split("```", 1)[0]
        langs = ast.literal_eval(re.search(r"^LANGS = (\{.*\})$", block, re.M).group(1))
        self.assertIn("python", langs)
        self.assertNotIn("code", langs)

    def test_the_rule_fires_on_a_code_doc_labelled_code(self):
        for pack in CODE_PACKS:
            with self.subTest(pack=pack):
                self.assertEqual(RULE(doc(pack)), ("fix", FIXED))

    def test_the_harm_test_counts_it_as_a_change(self):
        docs = {f"{i:016x}": doc(p, doc_id=f"{i:016x}") for i, p in enumerate(CODE_PACKS)}
        changed, dropped, errors = harm_test.run_rule(RULE, docs, timeout=5.0)
        self.assertEqual((sorted(changed), dropped, errors), (sorted(docs), [], []))

    def test_it_is_the_pack_check_that_lets_it_run(self):
        # the same doc and label, outside a code pack or with no pack, is kept
        for pack in ("en-dclm", "math-finemath", None):
            with self.subTest(pack=pack):
                self.assertEqual(RULE(doc(pack)), ("keep", TEXT))

    def test_a_doc_without_the_disease_is_kept(self):
        clean = doc("code-python")
        clean["text"] = FIXED
        self.assertEqual(RULE(clean), ("keep", FIXED))


if __name__ == "__main__":
    unittest.main()
