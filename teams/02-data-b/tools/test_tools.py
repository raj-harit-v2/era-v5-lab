"""Tests for harm_test_indic.py, gold_indic.py and fetch_sheets.py (standard library only).

Run:  python3 test_tools.py        (from this folder; no network, no pack data)
"""
import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_sheets as fs  # noqa: E402
import gold_indic as gi  # noqa: E402
import harm_test_indic as ht  # noqa: E402

ZWNJ, ZWJ = chr(0x200C), chr(0x200D)
FENCE = "```"


def medicine(*sections):
    """A medicine.md with one numbered section per (code, python source) pair, laid out like the real ones."""
    out = ["# Medicine sheet: test pack (tester)", ""]
    for k, (code, src) in enumerate(sections, 1):
        out += [f"## Medicine {k}", "", f"1. **Disease:** {code} (test)", "2. **Medicine:** test", f"   {FENCE}python"]
        out += ["   " + line for line in src.strip("\n").split("\n")]
        out += [f"   {FENCE}", "3. **Action:** fix the text.", ""]
    return "\n".join(out)


class HarmTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def run_tool(self, md, docs_by_pack, gold_ids=None, extra=()):
        """docs_by_pack: {pack: {doc_id: text}}; gold_ids: {pack: [ids]} (default: all of them)."""
        (self.tmp / "medicine.md").write_text(md, encoding="utf-8")
        packs = []
        for pack, docs in docs_by_pack.items():
            p = self.tmp / f"{pack}.jsonl"
            p.write_text("".join(json.dumps({"doc_id": d, "text": t}, ensure_ascii=False) + "\n" for d, t in docs.items()), encoding="utf-8")
            packs.append(str(p))
            ids = (gold_ids or {}).get(pack, list(docs))
            with open(self.tmp / f"{pack}_gold.csv", "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["doc_id", "reader_1", "reader_2"])
                w.writerows([[i, "a", "b"] for i in ids])
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = ht.main(["--medicine", str(self.tmp / "medicine.md"), "--pack", *packs, "--gold-dir", str(self.tmp), *extra])
        return code, out.getvalue(), err.getvalue()

    def test_rule_that_touches_nothing_passes(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text.replace('()', '')"))
        code, out, _ = self.run_tool(md, {"p1": {f"d{i}": "ఒక పాఠం" for i in range(5)}})
        self.assertEqual(code, 0, out)
        self.assertIn("result: PASS", out)

    def test_limit_is_one_percent_of_the_whole_gold_set(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text.replace('()', '')"))
        docs = {f"d{i}": "ఒక పాఠం" for i in range(100)}
        docs["d0"] = "ఒక () పాఠం"
        self.assertEqual(self.run_tool(md, {"p1": docs})[0], 0)  # 1 of 100 is exactly 1%
        docs["d1"] = "ఒక () పాఠం"
        self.assertEqual(self.run_tool(md, {"p1": docs})[0], 1)  # 2 of 100 fails

    def test_small_set_rule_allows_one_document_not_two(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text.replace('()', '')"))
        docs = {f"d{i}": "ఒక పాఠం" for i in range(46)}
        docs["d0"] = "ఒక () పాఠం"
        code, out, _ = self.run_tool(md, {"p1": docs})
        self.assertEqual(code, 0, out)  # 1 of 46 is 2.2%, but TSAI allows max(1 document, 1%)
        docs["d1"] = "ఒక () పాఠం"
        self.assertEqual(self.run_tool(md, {"p1": docs})[0], 1)
        self.assertEqual(ht.allowed_docs(46, 1), 1)
        self.assertEqual(ht.allowed_docs(500, 1), 5)

    def test_detector_true_drops(self):
        md = medicine(("D4", "def medicine_d4(text):\n    return 'xx' in text"))
        docs = {f"d{i}": "ok" for i in range(100)}
        docs["d0"] = "xx"
        code, out, _ = self.run_tool(md, {"p1": docs})
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"D4\s+0\s+1\s+1\.00%")

    def test_rule_that_deletes_a_zwnj_fails_the_joiner_audit(self):
        md = medicine(("A1", f"def medicine_a1(text):\n    return text.replace(chr(0x200C), '')"))
        docs = {f"d{i}": "ok" for i in range(100)}
        docs["d0"] = f"క{ZWNJ}ష"
        code, out, _ = self.run_tool(md, {"p1": docs})
        self.assertEqual(code, 1, out)
        self.assertIn("joiner count changed", out)

    def test_rule_that_adds_a_zwj_fails_too(self):
        md = medicine(("A1", "def medicine_a1(text):\n    return text.replace('x', chr(0x200D))"))
        docs = {f"d{i}": "ok" for i in range(100)}
        docs["d0"] = "axb"
        self.assertEqual(self.run_tool(md, {"p1": docs})[0], 1)

    def test_replacing_a_compatibility_character_fails_the_form_audit(self):
        docs = {f"d{i}": "ok" for i in range(100)}
        docs["d0"] = "ｱ"  # a half-width letter: what NFKC would rewrite to the full-width one
        bad = medicine(("G4", "def medicine_g4(text):\n    return text.replace(chr(0xFF71), chr(0x30A2))"))
        code, out, _ = self.run_tool(bad, {"p1": docs})
        self.assertEqual(code, 1)
        self.assertIn("normal form broken", out)
        fine = medicine(("A5", "import unicodedata\ndef medicine_a5(text):\n    return unicodedata.normalize('NFC', text)"))
        self.assertEqual(self.run_tool(fine, {"p1": docs})[0], 0)

    def test_decomposing_an_nfc_document_fails(self):
        md = medicine(("A5", "import unicodedata\ndef medicine_a5(text):\n    return unicodedata.normalize('NFD', text)"))
        docs = {f"d{i}": "ok" for i in range(100)}
        docs["d0"] = "é"  # NFC: one code point
        self.assertEqual(self.run_tool(md, {"p1": docs})[0], 1)

    def test_each_pack_is_judged_on_its_own_gold_set(self):
        # TSAI, CAP 31 Oct: per pack, never pooled. 2 of 210 pooled would pass; 2 of pb's 10 does not.
        md = medicine(("G3", "def medicine_g3(text):\n    return text.replace('()', '')"))
        a = {f"a{i}": "ok" for i in range(200)}
        b = {f"b{i}": "ok" for i in range(10)}
        b["b0"] = b["b1"] = "x () y"
        code, out, _ = self.run_tool(md, {"pa": a, "pb": b})
        self.assertEqual(code, 1, out)
        self.assertIn("gold set: 200 documents in 1 pack(s) (pa 200)", out)
        self.assertIn("gold set: 10 documents in 1 pack(s) (pb 10)", out)

    def test_a_pack_with_an_empty_gold_set_is_not_testable_and_the_others_run(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text"))
        code, out, _ = self.run_tool(md, {"pa": {"a0": "ok"}, "pb": {"b0": "ok"}}, gold_ids={"pb": []},
                                     extra=("--md-out", str(self.tmp / "blocks.md")))
        self.assertEqual(code, 0, out)
        self.assertIn("pb: gold set empty, not testable", out)
        self.assertIn("gold set empty, not testable", (self.tmp / "blocks.md").read_text(encoding="utf-8"))

    def test_only_gold_documents_are_tested(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text.replace('()', '')"))
        docs = {f"d{i}": "ok" for i in range(10)}
        docs["d9"] = "x () y"  # not in the gold set
        self.assertEqual(self.run_tool(md, {"p1": docs}, gold_ids={"p1": [f"d{i}" for i in range(9)]})[0], 0)

    def test_gold_document_missing_from_the_pack_is_an_error(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text"))
        code, _, err = self.run_tool(md, {"p1": {"d0": "ok"}}, gold_ids={"p1": ["d0", "zzz"]})
        self.assertEqual(code, 2)
        self.assertIn("not in the pack", err)

    def test_empty_gold_set_is_an_error_not_a_pass(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text"))
        code, _, err = self.run_tool(md, {"p1": {"d0": "ok"}}, gold_ids={"p1": []})
        self.assertEqual(code, 2)
        self.assertIn("empty", err)

    def test_wrong_return_type_and_crash_fail(self):
        for body in ("return None", "return 5", "raise ValueError('x')"):
            md = medicine(("G3", f"def medicine_g3(text):\n    {body}"))
            code, out, _ = self.run_tool(md, {"p1": {f"d{i}": "ok" for i in range(5)}})
            self.assertEqual(code, 1, body)
            self.assertIn("error:", out)

    @unittest.skipUnless(ht.HAS_ALARM, "needs SIGALRM")
    def test_a_rule_that_hangs_is_stopped(self):
        md = medicine(("G3", "import time\ndef medicine_g3(text):\n    time.sleep(5)\n    return text"))
        code, out, _ = self.run_tool(md, {"p1": {"d0": "ok"}}, extra=("--timeout", "0.05"))
        self.assertEqual(code, 1)
        self.assertIn("took more than", out)

    def test_all_in_order_runs_the_rules_one_after_another(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text.replace('()', 'X')"),
                      ("B2", "def medicine_b2(text):\n    return text.replace('X', 'Y')"))
        docs = {f"d{i}": "ok" for i in range(100)}
        docs["d0"] = "a () b"
        _, out, _ = self.run_tool(md, {"p1": docs})
        self.assertRegex(out, r"G3\s+1\s+0")
        self.assertRegex(out, r"B2\s+0\s+0")  # on its own B2 finds no X
        self.assertRegex(out, r"ALL IN ORDER\s+1\s+0")

    def test_all_in_order_compares_the_final_text_with_the_original(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text.replace('()', 'X')"),
                      ("B2", "def medicine_b2(text):\n    return text.replace('X', '()')"))
        docs = {f"d{i}": "ok" for i in range(100)}
        docs["d0"] = "a () b"
        _, out, _ = self.run_tool(md, {"p1": docs})
        self.assertRegex(out, r"G3\s+1\s+0")
        self.assertRegex(out, r"ALL IN ORDER\s+0\s+0")  # the second rule restores the text

    def test_pack_row_without_doc_id_exits_2(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text"))
        (self.tmp / "medicine.md").write_text(md, encoding="utf-8")
        (self.tmp / "p1.jsonl").write_text('{"text": "ok"}\n', encoding="utf-8")
        (self.tmp / "p1_gold.csv").write_text("doc_id,reader_1,reader_2\nd0,a,b\n", encoding="utf-8")
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = ht.main(["--medicine", str(self.tmp / "medicine.md"), "--pack", str(self.tmp / "p1.jsonl"), "--gold-dir", str(self.tmp)])
        self.assertEqual(code, 2)
        self.assertIn("row 1 has no doc_id", err.getvalue())

    def test_a_section_without_code_is_reported_not_failed(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text")) + "\n1. **Disease:** D5 (no code)\n2. **Medicine:** none\n"
        code, out, _ = self.run_tool(md, {"p1": {"d0": "ok"}})
        self.assertEqual(code, 0)
        self.assertIn("D5 has no rule in code", out)

    def test_bad_medicine_files_are_refused(self):
        two = medicine(("G3", "def medicine_g3(text):\n    return text"), ("G3", "def medicine_g3(text):\n    return text"))
        self.assertEqual(self.run_tool(two, {"p1": {"d0": "ok"}})[0], 2)
        broken = medicine(("G3", "def medicine_g3(text):\n    return ("))
        self.assertEqual(self.run_tool(broken, {"p1": {"d0": "ok"}})[0], 2)
        needs_doc = medicine(("G3", "def medicine_g3(doc):\n    return doc['text']"))
        code, _, err = self.run_tool(needs_doc, {"p1": {"d0": "ok"}})
        self.assertEqual(code, 2)
        self.assertIn("G3: the function medicine_g3() takes 'doc'", err)
        self.assertEqual(self.run_tool("# no sections here", {"p1": {"d0": "ok"}})[0], 2)

    def test_a_doc_rule_does_not_block_the_other_rules_when_one_is_chosen(self):
        md = medicine(("G3", "def medicine_g3(doc):\n    return doc['text']"),
                      ("B2", "def medicine_b2(text):\n    return text"))
        code, out, _ = self.run_tool(md, {"p1": {"d0": "ok"}}, extra=("--rule", "B2"))
        self.assertEqual(code, 0, out)

    def test_helper_functions_with_underscore_are_not_the_rule(self):
        md = medicine(("G3", "def _helper(t):\n    return t.replace('()', '')\ndef cleaner(text):\n    return _helper(text)"))
        docs = {f"d{i}": "ok" for i in range(100)}
        docs["d0"] = "a () b"
        self.assertRegex(self.run_tool(md, {"p1": docs})[1], r"G3\s+1\s+0")

    def test_md_out_has_a_part_4_for_each_rule(self):
        md = medicine(("G3", "def medicine_g3(text):\n    return text"))
        self.run_tool(md, {"p1": {"d0": "ok"}}, extra=("--md-out", str(self.tmp / "blocks.md")))
        text = (self.tmp / "blocks.md").read_text(encoding="utf-8")
        self.assertIn("4. **Harm test:**", text)
        self.assertIn("ZWJ/ZWNJ audit", text)


class GoldCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def sheet(self, pack, handle, rows, header="doc_id,read,verdict,diseases,evidence,hex,note"):
        d = self.tmp / "sheets" / pack
        d.mkdir(parents=True, exist_ok=True)
        lines = [header] + [f"{doc},{read},{verdict},{codes},,," for doc, read, verdict, codes in rows]
        (d / f"{handle}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def build(self, *packs):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = gi.main(["--sheets", str(self.tmp / "sheets"), "--out", str(self.tmp / "out"), "--lang", "telugu"]
                           + (["--packs", *packs] if packs else []))

        def rows(name):
            with open(self.tmp / "out" / name, encoding="utf-8") as f:
                return list(csv.reader(f))[1:]
        return code, rows, err.getvalue()

    def test_two_clean_full_readers_make_gold(self):
        self.sheet("p1", "amy", [("d1", "full", "clean", ""), ("d2", "full", "clean", "")])
        self.sheet("p1", "bob", [("d1", "full", "clean", ""), ("d2", "full", "fix", "D4")])
        code, rows, _ = self.build()
        self.assertEqual((code, rows("p1_gold.csv")), (0, [["d1", "amy", "bob"]]))

    def test_one_dissent_removes_a_document_even_with_two_clean_votes(self):
        for h, v, c in (("amy", "clean", ""), ("bob", "clean", ""), ("cat", "fix", "D4")):
            self.sheet("p1", h, [("d1", "full", v, c)])
        self.assertEqual(self.build()[1]("p1_gold.csv"), [])

    def test_partial_read_and_clean_with_a_code_are_not_clean_votes(self):
        self.sheet("p1", "amy", [("d1", "full", "clean", ""), ("d2", "full", "clean", "")])
        self.sheet("p1", "bob", [("d1", "partial", "clean", ""), ("d2", "full", "clean", "A6")])
        self.assertEqual(self.build()[1]("p1_gold.csv"), [])

    def test_a_clean_row_whose_only_code_is_d3_is_a_clean_vote(self):
        # TSAI, G1 31 Oct: D3 is a label only. With another code, or with a fix verdict, it is still not clean.
        self.sheet("p1", "amy", [("d1", "full", "clean", "D3"), ("d2", "full", "clean", "D3;A6"), ("d3", "full", "fix", "D3")])
        self.sheet("p1", "bob", [("d1", "full", "clean", ""), ("d2", "full", "clean", ""), ("d3", "full", "clean", "")])
        self.assertEqual(self.build()[1]("p1_gold.csv"), [["d1", "amy", "bob"]])

    def test_a_sheet_with_a_bad_header_is_skipped_and_reported(self):
        self.sheet("p1", "amy", [("d1", "full", "clean", "")])
        self.sheet("p1", "bob", [("d1", "full", "clean", "")])
        self.sheet("p1", "cat", [("d1", "full", "clean", "")], header="-doc_id,read,verdict,diseases,evidence,hex,note")
        code, rows, err = self.build()
        self.assertEqual((code, rows("p1_gold.csv")), (0, [["d1", "amy", "bob"]]))
        self.assertIn("cat.csv: skipped", err)

    def test_same_document_with_two_different_rows_counts_for_nothing(self):
        self.sheet("p1", "amy", [("d1", "full", "clean", ""), ("d1", "full", "fix", "D4")])
        self.sheet("p1", "bob", [("d1", "full", "clean", "")])
        self.assertEqual(self.build()[1]("p1_gold.csv"), [])

    def test_a_fix_row_of_a_reader_who_also_has_a_clean_row_disputes_the_document(self):
        self.sheet("p1", "amy", [("d1", "full", "clean", ""), ("d1", "full", "fix", "D4")])
        self.sheet("p1", "bob", [("d1", "full", "clean", "")])
        self.sheet("p1", "cat", [("d1", "full", "clean", "")])
        code, rows, _ = self.build()
        self.assertEqual(rows("p1_gold.csv"), [])  # bob and cat are clean, amy says fix: disputed, not gold
        self.assertEqual(rows("gold_coverage.csv")[0][4], "1")  # the disputed column

    def test_language_file_joins_the_packs_and_coverage_is_written(self):
        for pack in ("p1", "p2"):
            self.sheet(pack, "amy", [(f"{pack}d", "full", "clean", "")])
            self.sheet(pack, "bob", [(f"{pack}d", "full", "clean", "")])
        code, rows, _ = self.build()
        self.assertEqual(sorted(r[0] for r in rows("telugu_gold.csv")), ["p1d", "p2d"])
        self.assertEqual([r[0] for r in rows("gold_coverage.csv")], ["p1", "p2"])

    def test_unknown_pack_is_an_error(self):
        self.sheet("p1", "amy", [("d1", "full", "clean", "")])
        self.assertEqual(self.build("nope")[0], 2)


class FetchCase(unittest.TestCase):
    def test_closed_wrong_folder_and_newest(self):
        prs = [{"number": 5, "state": "OPEN", "author": "Amy", "files": ["diagnosis/submissions/p1/amy/labels.csv"]},
               {"number": 9, "state": "MERGED", "author": "amy", "files": ["diagnosis/submissions/p1/amy/labels.csv"]},
               {"number": 7, "state": "CLOSED", "author": "bob", "files": ["diagnosis/submissions/p1/bob/labels.csv"]},
               {"number": 8, "state": "OPEN", "author": "cat", "files": ["diagnosis/submissions/p1/dan/labels.csv"]}]
        calls = []

        def fake_gh(*args):
            calls.append(args)
            return json.dumps(prs).encode() if args[0] == "pr" else b"doc_id,read,verdict,diseases,evidence,hex,note\n"
        tmp = Path(tempfile.mkdtemp())
        out = io.StringIO()
        with mock.patch.object(fs, "gh", fake_gh), redirect_stdout(out):
            code = fs.main(["--packs", "p1", "--out", str(tmp)])
        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in (tmp / "p1").iterdir()), ["amy.csv"])  # bob closed, dan not the author's folder
        self.assertIn("refs/pull/9/head", calls[-1][-1])  # the newest pull request of amy
        self.assertIn("closed without merge", out.getvalue())

    def test_jq_filter_text(self):
        jq = fs.jq_filter(["ind-te-fw2", "ind-te-sangraha-v"])
        self.assertIn("(ind-te-fw2|ind-te-sangraha-v)", jq)
        self.assertNotIn("\\-", jq)  # jq rejects an escaped hyphen
        self.assertIn("labels\\\\.csv", jq)  # one literal backslash before the dot, written as two in jq

    def test_bad_pack_id_is_refused(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(fs.main(["--packs", "p1;rm -rf", "--out", "x"]), 2)


if __name__ == "__main__":
    unittest.main()
