"""Tests for scripts/combine_spec.py. The small sheets are made up; the last class combines the real sheets.

  python3 -m unittest discover -s spec_v1_1/tests      (from teams/01-data-a)
"""
import re
import sys
import unittest
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
DATA_A = SPEC.parent
sys.path.insert(0, str(SPEC / "scripts"))
import combine_spec as cs  # noqa: E402


def card(n, family, code, rid, block, text="1. **Disease:** made up.\n"):
    return f"## Medicine {n} — {family} / {code} / `{rid}`\n\n{text}\n```python\n{block}```\n\n"


def v1_block(rid, code, packs):
    return (f'RULE_ID = "{rid}"\nCODE = "{code}"\nSTAGE = "10"\ndef medicine(doc):\n    return ("keep", doc["text"])\n\n'
            f"_spec_source_medicine = medicine\n\nSPEC_PACKS = {packs!r}\n")


def v11_block(rid, code, origin):
    return (f'RULE_ID = "{rid}"\nCODE = "{code}"  # proposed new code\nSTAGE = "10"\nORIGIN = "{origin}"  # packs it runs on\n'
            'PACKS = set(ORIGIN.split(", "))\ndef medicine(doc):\n    if doc.get("pack_id") not in PACKS:\n'
            '        return ("keep", doc["text"])\n    return ("fix", doc["text"])\n')


V1 = ("# Medicine sheet: spec v1\n\nStatus: made up. See [the template](../../../../diagnosis/t.md) and [code](medicine_code.md).\n\n"
      "## Identity mapping\n\n| Medicine | Family | Disease | Source identity | Consolidated identity |\n|---|---|---|---|---|\n"
      "| 1 | code | A1 | `DA-A1-901` | `DA-A1-001` |\n| 2 | english | A1 | `DA-A1-004` | `DA-A1-004` |\n"
      "| 3 | english | F1 | `DA-F1-005` | `DA-F1-005` |\n| 4 | math | A1 | `DA-A1-005` | `DA-A1-005` |\n\n"
      + card(1, "code", "A1", "DA-A1-001", v1_block("DA-A1-001", "A1", {"code-go"}), "Source [medicine_code.md](medicine_code.md).\n")
      + card(2, "english", "A1", "DA-A1-004", v1_block("DA-A1-004", "A1", {"en-dclm"}))
      + card(3, "english", "F1", "DA-F1-005", v1_block("DA-F1-005", "F1", {"en-dclm"}))
      + card(4, "math", "A1", "DA-A1-005", v1_block("DA-A1-005", "A1", {"math-finemath"})))

ADD = ("# Medicine sheet: spec v1.1\n\nStatus: made up.\n\n## Identity mapping\n\n"
       "| Medicine | Family | Disease | Source | Source identity | Consolidated identity |\n|---|---|---|---|---|---|\n"
       "| 1 | english | A8 | [medicine_english.md](medicine_english.md) section 1 | `DA-A8-003` | `DA-A8-003` |\n"
       "| 2 | math | C9 | [medicine_math.md](medicine_math.md) section 2 | `DA-C9-003` | `DA-C9-003` |\n\n"
       + card(1, "english", "A8", "DA-A8-003", v11_block("DA-A8-003", "A8", "en-nemotroncc"))
       + card(2, "math", "C9", "DA-C9-003", v11_block("DA-C9-003", "C9", "math-finemath, math-megamath")))


class Order(unittest.TestCase):
    def setUp(self):
        self.text, self.cards = cs.combine(V1, ADD)

    def test_each_family_has_v1_then_v11(self):
        self.assertEqual([c["id"] for c in self.cards],
                         ["DA-A1-001", "DA-A1-004", "DA-A8-003", "DA-F1-005", "DA-A1-005", "DA-C9-003"])

    def test_english_f1_stays_last(self):
        english = [c["id"] for c in self.cards if c["family"] == "english"]
        self.assertEqual(english[-1], "DA-F1-005")

    def test_cards_are_numbered_in_run_order(self):
        nums = [int(n) for n in re.findall(r"^## Medicine (\d+) — ", self.text, re.M)]
        self.assertEqual(nums, [1, 2, 3, 4, 5, 6])
        self.assertIn("## Medicine 3 — english / A8 / `DA-A8-003`", self.text)

    def test_identity_table_keeps_the_source_identity(self):
        self.assertIn("| 1 | code | A1 | v1 | [specv1.md](../../spec_v1/sheets/specv1.md) | `DA-A1-901` | `DA-A1-001` |", self.text)
        self.assertIn("| 3 | english | A8 | v1.1 | [medicine_english.md](medicine_english.md) section 1 | `DA-A8-003` | `DA-A8-003` |",
                      self.text)
        self.assertEqual(self.text.count("## Identity mapping"), 1)


class Blocks(unittest.TestCase):
    def setUp(self):
        self.text, self.cards = cs.combine(V1, ADD)
        self.blocks = {c["id"]: cs.FENCE.search(c["body"]).group(1) for c in self.cards}

    def test_v1_blocks_are_unchanged(self):
        self.assertEqual(self.blocks["DA-A1-004"], v1_block("DA-A1-004", "A1", {"en-dclm"}))

    def test_v11_blocks_get_the_spec_packs_wrapper(self):
        b = self.blocks["DA-C9-003"]
        self.assertIn("SPEC_PACKS = {'math-finemath', 'math-megamath'}", b)
        self.assertIn("_spec_source_medicine = medicine", b)
        ns = {}
        exec(compile(b, "DA-C9-003", "exec"), ns)
        self.assertEqual(ns["medicine"]({"text": "x", "pack_id": "math-megamath"}), ("fix", "x"))
        self.assertEqual(ns["medicine"]({"text": "x", "pack_id": "en-dclm"}), ("keep", "x"))

    def test_code_line_is_bare_for_build_clean(self):
        b = self.blocks["DA-A8-003"]
        self.assertRegex(b, r'(?m)^CODE = "A8"$')
        self.assertRegex(b, r"(?m)^# proposed new code\nCODE")


class Links(unittest.TestCase):
    def test_relative_links_still_reach_the_same_file(self):
        self.assertEqual(cs.moved_link("medicine_code.md"), "../../spec_v1/sheets/medicine_code.md")
        self.assertEqual(cs.moved_link("../build/build_clean.py"), "../../spec_v1/build/build_clean.py")
        self.assertEqual(cs.moved_link("../../../../diagnosis/t.md"), "../../../../diagnosis/t.md")
        self.assertEqual(cs.moved_link("medicine_code.md#a1"), "../../spec_v1/sheets/medicine_code.md#a1")

    def test_absolute_and_anchor_links_stay(self):
        for t in ("https://github.com/x", "#scope", "mailto:x@example.com"):
            self.assertEqual(cs.moved_link(t), t)

    def test_links_in_code_stay(self):
        text = "see [a](a.md)\n```python\nX = '[b](b.md)'\n```\n"
        self.assertEqual(cs.move_links(text), "see [a](../../spec_v1/sheets/a.md)\n```python\nX = '[b](b.md)'\n```\n")

    def test_v1_card_links_are_moved_in_the_combined_sheet(self):
        text, _ = cs.combine(V1, ADD)
        self.assertIn("Source [medicine_code.md](../../spec_v1/sheets/medicine_code.md)", text)
        self.assertIn("[the template](../../../../diagnosis/t.md)", text)


class Refusals(unittest.TestCase):
    def test_an_id_in_both_specs(self):
        add = ADD.replace("DA-A8-003", "DA-A1-004")
        with self.assertRaises(ValueError):
            cs.combine(V1, add)

    def test_a_v11_family_spec_v1_lacks(self):
        add = ADD.replace("— english / A8", "— dutch / A8")
        with self.assertRaises(ValueError):
            cs.combine(V1, add)

    def test_f1_that_is_not_last(self):
        a1 = card(2, "english", "A1", "DA-A1-004", v1_block("DA-A1-004", "A1", {"en-dclm"}))
        f1 = card(3, "english", "F1", "DA-F1-005", v1_block("DA-F1-005", "F1", {"en-dclm"}))
        v1 = V1.replace(a1 + f1, f1.replace("Medicine 3", "Medicine 2") + a1.replace("Medicine 2", "Medicine 3"))
        self.assertNotEqual(v1, V1)
        with self.assertRaises(ValueError):
            cs.combine(v1, ADD)

    def test_a_family_split_in_two(self):
        code, en_a1, en_f1, math = cs.split(V1)[1]
        with self.assertRaisesRegex(ValueError, "not together"):
            cs.order([code, en_a1, math, en_f1], [])


ADDITIONS = SPEC / "sheets" / "specv1_1_additions.md"


@unittest.skipUnless(ADDITIONS.exists(), "sheets/specv1_1_additions.md is not there")
class RealSheets(unittest.TestCase):
    def test_build_clean_reads_the_combined_sheet(self):
        import importlib.util
        import tempfile
        text, cards = cs.combine((DATA_A / "spec_v1/sheets/specv1.md").read_text(encoding="utf-8"),
                                 ADDITIONS.read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("build_clean", DATA_A / "spec_v1/build/build_clean.py")
        bc = importlib.util.module_from_spec(spec)
        argv, sys.argv = sys.argv, ["build_clean.py"]
        try:
            spec.loader.exec_module(bc)
        finally:
            sys.argv = argv
        with tempfile.TemporaryDirectory() as tmp:
            sheet = Path(tmp) / "specv1_1.md"
            sheet.write_text(text, encoding="utf-8")
            active = bc.rules(sheet)
        self.assertEqual(len(cards), len(re.findall(r"^## Medicine ", text, re.M)))
        added = {r["id"] for r in active} - {r["id"] for r in bc.rules(DATA_A / "spec_v1/sheets/specv1.md")}
        self.assertEqual(len(added), len(cs.split(ADDITIONS.read_text(encoding="utf-8"))[1]))

    def test_the_committed_sheet_is_up_to_date(self):
        text, _ = cs.combine((DATA_A / "spec_v1/sheets/specv1.md").read_text(encoding="utf-8"),
                             ADDITIONS.read_text(encoding="utf-8"),
                             _validation())
        self.assertEqual(text, (SPEC / "sheets" / "specv1_1.md").read_text(encoding="utf-8"),
                         "sheets/specv1_1.md is out of date: rerun scripts/combine_spec.py")


def _validation():
    path = SPEC / "results" / "combined" / "validation.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    unittest.main()
