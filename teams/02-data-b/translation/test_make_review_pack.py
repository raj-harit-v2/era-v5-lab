"""Tests for make_review_pack.py.  Run:  python3 test_make_review_pack.py"""
import csv
import io
import random
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_review_pack as mrp  # noqa: E402


class ReviewPackCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.packs, self.out = self.tmp / "packs", self.tmp / "out"
        self.packs.mkdir()
        for lang in mrp.LANGS:
            self.pack(lang, {f"{lang}{i:03d}": f"text {i}" for i in range(120)})

    def pack(self, lang, docs, shuffle_seed=None):
        items = list(docs.items())
        if shuffle_seed is not None:
            random.Random(shuffle_seed).shuffle(items)
        table = pa.table({"doc_id": [d for d, _ in items], "text": [t for _, t in items]})
        pq.write_table(table, self.packs / f"ind-{lang}-sangraha-s.parquet")

    def run_tool(self, *args, out=None):
        o, e = io.StringIO(), io.StringIO()
        with redirect_stdout(o), redirect_stderr(e):
            code = mrp.main([str(self.packs), "--out", str(out or self.out), *args])
        return code, o.getvalue(), e.getvalue()

    def sheet(self, lang, out=None):
        with open((out or self.out) / f"{lang}.csv", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def test_fifty_per_language_twenty_five_shared_ids_only(self):
        self.assertEqual(self.run_tool()[0], 0)
        for lang in mrp.LANGS:
            rows = self.sheet(lang)
            self.assertEqual(list(rows[0].keys()), ["doc_id", "shared", "score", "note"])
            self.assertEqual(len(rows), 50)
            self.assertEqual(len({r["doc_id"] for r in rows}), 50)
            self.assertEqual(sum(r["shared"] == "yes" for r in rows), 25)
            self.assertTrue(all(r["shared"] in {"yes", "no"} and r["score"] == r["note"] == "" for r in rows))
            self.assertTrue(all(r["doc_id"].startswith(lang) for r in rows))

    def test_same_seed_same_sample_and_another_seed_differs(self):
        self.run_tool()
        again = self.tmp / "again"
        self.run_tool(out=again)
        other = self.tmp / "other"
        self.run_tool("--seed", "7", out=other)
        for lang in mrp.LANGS:
            self.assertEqual(self.sheet(lang), self.sheet(lang, again))
            self.assertNotEqual({r["doc_id"] for r in self.sheet(lang)}, {r["doc_id"] for r in self.sheet(lang, other)})

    def test_row_order_of_the_pack_does_not_change_the_sample(self):
        self.run_tool()
        first = {lang: self.sheet(lang) for lang in mrp.LANGS}
        for lang in mrp.LANGS:
            self.pack(lang, {f"{lang}{i:03d}": f"text {i}" for i in range(120)}, shuffle_seed=99)
        self.run_tool()
        for lang in mrp.LANGS:
            self.assertEqual(first[lang], self.sheet(lang))

    def test_documents_over_the_default_10000_characters_are_never_picked(self):
        docs = {f"te{i:03d}": "y" * (10001 if i % 2 else 10000) for i in range(200)}
        self.pack("te", docs)
        self.assertEqual(self.run_tool()[0], 0)
        self.assertTrue(all(len(docs[r["doc_id"]]) == 10000 for r in self.sheet("te")))

    def test_empty_and_too_long_documents_are_never_picked(self):
        docs = {f"hi{i:03d}": ("" if i % 2 else "x" * (10 if i % 3 else 5000)) for i in range(400)}
        self.pack("hi", docs)
        self.assertEqual(self.run_tool("--max-chars", "100")[0], 0)
        self.assertTrue(all(docs[r["doc_id"]] == "x" * 10 for r in self.sheet("hi")))

    def test_problems_stop_the_run_without_writing_sheets(self):
        self.pack("kn", {f"kn{i}": "t" for i in range(30)})                       # too few documents
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("only 30 eligible documents, 50 needed", err)
        self.assertFalse(self.out.exists())
        (self.packs / "ind-kn-sangraha-s.parquet").unlink()                        # missing pack
        self.assertEqual(self.run_tool()[0], 2)
        self.assertEqual(self.run_tool("--shared", "60")[0], 2)                     # more shared than picked

    def test_duplicate_doc_ids_are_refused(self):
        table = pa.table({"doc_id": ["ta1"] * 60, "text": ["t"] * 60})
        pq.write_table(table, self.packs / "ind-ta-sangraha-s.parquet")
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("duplicate doc_ids", err)


if __name__ == "__main__":
    unittest.main()
