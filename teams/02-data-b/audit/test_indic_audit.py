"""Tests for indic_audit.py. Run: python -m unittest test_indic_audit -v (from this folder).

The tests write small shards in the shard-v1 format with a byte-level tokenizer built here. It has the same
normalizer as the frozen tokenizer (NFC, then the Malayalam old-style chillu folded into the atomic chillu), so no
tokenizer file is needed. The texts are made up.
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from tokenizers import Tokenizer, decoders, models, normalizers, pre_tokenizers

import indic_audit as ia

ATOMIC = ["ൺ", "ൻ", "ർ", "ൽ", "ൾ", "ൿ"]


def toy_tokenizer():
    alphabet = sorted(pre_tokenizers.ByteLevel.alphabet())
    tok = Tokenizer(models.BPE(vocab={c: i for i, c in enumerate(alphabet)}, merges=[]))
    tok.normalizer = normalizers.Sequence(
        [normalizers.NFC()] + [normalizers.Replace(o, n) for o, n in zip(ia.OLD_CHILLU, ATOMIC)])
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False)
    tok.decoder = decoders.ByteLevel()
    tok.add_special_tokens(["<|endoftext|>"])
    return tok, tok.token_to_id("<|endoftext|>")


def write_pack(folder, pack_id, docs):
    pq.write_table(pa.table({"doc_id": [d for d, _ in docs], "text": [t for _, t in docs]}),
                   Path(folder) / f"{pack_id}.parquet")


def write_shard(folder, pack_id, docs, tok, eos, magic=ia.MAGIC):
    """docs: (doc_id, cleaned text). Writes <folder>/<pack_id>/train/<pack_id>-train-000000 .bin, .idx.npy and
    .docs.parquet."""
    out = Path(folder) / pack_id / "train"
    out.mkdir(parents=True, exist_ok=True)
    ids = [e.ids + [eos] for e in tok.encode_batch([t for _, t in docs], add_special_tokens=False)]
    tokens = np.array([i for d in ids for i in d], dtype="<u4")
    idx = np.concatenate([[0], np.cumsum([len(d) for d in ids])]).astype(np.int64)
    head = np.zeros(256, dtype="<i4")
    head[:3] = [magic, ia.VERSION, len(tokens)]
    stem = out / f"{pack_id}-train-000000"
    with open(f"{stem}.bin", "wb") as f:
        f.write(head.tobytes())
        f.write(tokens.tobytes())
    np.save(f"{stem}.idx.npy", idx)
    pq.write_table(pa.table({"doc_id": [d for d, _ in docs]}), f"{stem}.docs.parquet")
    return Path(f"{stem}.bin")


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.tok, self.eos = toy_tokenizer()

    def tearDown(self):
        self.tmp.cleanup()

    def run_pack(self, raw_docs, shard_docs, pack_id="ind-hi-test"):
        write_pack(self.dir, pack_id, raw_docs)
        bins = [write_shard(self.dir + "/shards", pack_id, shard_docs, self.tok, self.eos)] if shard_docs else []
        return ia.audit_pack([Path(self.dir) / f"{pack_id}.parquet"], bins, self.tok, self.eos)

    def test_raw_parts_of_one_pack_are_joined(self):
        write_pack(self.dir, "ind-hi-test_part-00000", [("p1", "one")])
        write_pack(self.dir, "ind-hi-test_part-00001", [("p2", "two")])
        b = write_shard(self.dir + "/shards", "ind-hi-test", [("p1", "one"), ("p2", "two")], self.tok, self.eos)
        parts = [Path(self.dir) / "ind-hi-test_part-00000.parquet", Path(self.dir) / "ind-hi-test_part-00001.parquet"]
        row, flagged = ia.audit_pack(parts, [b], self.tok, self.eos)
        self.assertEqual((row["pack_id"], row["docs_raw"], row["docs_dropped"]), ("ind-hi-test", 2, 0))

    def test_joiners_kept_are_not_flagged(self):
        docs = [("a1", "क्\u200dष और र\u200cय"), ("a2", "no joiners here")]
        row, flagged = self.run_pack(docs, docs)
        self.assertEqual((row["zwj_raw"], row["zwj_shard"], row["zwnj_raw"], row["zwnj_shard"]), (1, 1, 1, 1))
        self.assertEqual(flagged, [])

    def test_zwj_lost_in_cleaning_is_flagged(self):
        raw = [("b1", "क्\u200dष"), ("b2", "ok")]
        row, flagged = self.run_pack(raw, [("b1", "क्ष"), ("b2", "ok")])
        self.assertEqual((row["docs_joiners_changed"], row["docs_joiners_changed_in_kept_text"]), (1, 1))
        self.assertEqual(flagged, [("ind-hi-test", "b1", "kept text")])

    def test_zwnj_lost_in_cleaning_is_flagged(self):
        row, flagged = self.run_pack([("c1", "र\u200cय")], [("c1", "रय")])
        self.assertEqual(flagged, [("ind-hi-test", "c1", "kept text")])

    def test_zwj_added_is_flagged(self):
        row, flagged = self.run_pack([("c2", "कष")], [("c2", "क\u200dष")])
        self.assertEqual(flagged, [("ind-hi-test", "c2", "kept text")])

    def test_zwj_in_text_cut_by_cleaning_is_marked_cut(self):
        row, flagged = self.run_pack([("c3", "पहला वाक्य। Also Read - क्\u200dष")], [("c3", "पहला वाक्य।")])
        self.assertEqual((row["docs_joiners_changed"], row["docs_joiners_changed_in_kept_text"]), (1, 0))
        self.assertEqual(flagged, [("ind-hi-test", "c3", "cut text")])

    def test_old_chillu_folded_by_the_tokenizer_is_allowed(self):
        text = "അവന്\u200d വന്നു"                   # old-style chillu n: the normalizer folds it into U+0D7B
        row, flagged = self.run_pack([("d1", text)], [("d1", text)], pack_id="ind-ml-test")
        self.assertEqual((row["zwj_raw"], row["zwj_shard"]), (1, 0))
        self.assertEqual(flagged, [])

    def test_dropped_documents_are_counted(self):
        raw = [("e1", "one"), ("e2", "two"), ("e3", "three")]
        row, flagged = self.run_pack(raw, [("e1", "one"), ("e3", "three")])
        self.assertEqual((row["docs_raw"], row["docs_kept"], row["docs_dropped"]), (3, 2, 1))

    def test_pack_with_no_shard_drops_everything(self):
        row, flagged = self.run_pack([("f1", "one")], [])
        self.assertEqual((row["shards"], row["docs_kept"], row["docs_dropped"]), (0, 0, 1))

    def visarga(self, row):
        return (row["visarga_raw"], row["visarga_shard"], row["docs_visarga_lost"],
                row["visarga_words_edited_in_kept_text"])

    def test_visarga_kept_is_not_counted(self):
        docs = [("v1", "पुन\u0903 आया"), ("v2", "no visarga")]
        row, _ = self.run_pack(docs, docs)
        self.assertEqual(self.visarga(row), (1, 1, 0, 0))

    def test_visarga_turned_into_colon_is_counted(self):            # the #566 pattern
        row, _ = self.run_pack([("v3", "దు\u0c03ఖం వచ్చింది")], [("v3", "దు:ఖం వచ్చింది")], pack_id="ind-te-test")
        self.assertEqual(self.visarga(row), (1, 0, 1, 1))

    def test_visarga_deleted_in_a_kept_word_is_counted(self):
        row, _ = self.run_pack([("v4", "अत\u0903 आगे")], [("v4", "अत आगे")])
        self.assertEqual(self.visarga(row), (1, 0, 1, 1))

    def test_visarga_in_text_cut_by_cleaning_is_not_an_edit(self):
        row, _ = self.run_pack([("v5", "पहला वाक्य। हे ही वाचा\u0903 दूसरा")], [("v5", "पहला वाक्य।")])
        self.assertEqual(self.visarga(row), (1, 0, 1, 0))

    def test_tamil_aytham_turned_into_colon_is_counted(self):
        row, _ = self.run_pack([("v6", "அ\u0b83து நல்லது")], [("v6", "அ:து நல்லது")], pack_id="ind-ta-test")
        self.assertEqual(self.visarga(row), (1, 0, 1, 1))

    def test_bad_header_is_refused(self):
        write_pack(self.dir, "ind-hi-test", [("g1", "x")])
        b = write_shard(self.dir + "/shards", "ind-hi-test", [("g1", "x")], self.tok, self.eos, magic=1)
        with self.assertRaises(SystemExit):
            ia.audit_pack([Path(self.dir) / "ind-hi-test.parquet"], [b], self.tok, self.eos)

    def test_missing_eos_is_refused(self):
        write_pack(self.dir, "ind-hi-test", [("h1", "x")])
        b = write_shard(self.dir + "/shards", "ind-hi-test", [("h1", "x")], self.tok, self.eos)
        with self.assertRaises(SystemExit):
            ia.audit_pack([Path(self.dir) / "ind-hi-test.parquet"], [b], self.tok, self.eos + 1)


if __name__ == "__main__":
    unittest.main()
