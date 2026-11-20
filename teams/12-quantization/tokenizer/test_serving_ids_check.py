"""Tests for serving_ids_check.py with stand-ins for the tokenizer and llama.cpp (no model, no download).

Run from teams/12-quantization:  python -m unittest tokenizer/test_serving_ids_check.py -v
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import serving_ids_check as sic  # noqa: E402


class Enc:
    def __init__(self, ids):
        self.ids = ids


class FakeHF:
    """tokenizer.json stand-in: one id per character; its normalizer folds 'ẞ' to 'SS' (any change will do)."""
    class normalizer:
        @staticmethod
        def normalize_str(t):
            return t.replace("ẞ", "SS")

    def encode(self, t, add_special_tokens=False):
        return Enc([ord(c) for c in self.normalizer.normalize_str(t)])

    def encode_batch(self, ts, add_special_tokens=False):
        return [self.encode(t) for t in ts]

    def decode_batch(self, idss, skip_special_tokens=False):
        return ["".join(map(chr, ids)) for ids in idss]


class FakeLlama:
    """llama.cpp stand-in: detokenize is exact except for id `broken`; tokenize skips the normalizer."""
    def __init__(self, broken=None):
        self.broken = broken

    def detokenize(self, ids, special=True):
        return "".join("?" if i == self.broken else chr(i) for i in ids).encode("utf-8")

    def tokenize(self, b, add_bos=False, special=True):
        return [ord(c) for c in b.decode("utf-8")]

    def reset(self):
        pass

    def create_completion(self, prompt, max_tokens, temperature):
        return {"usage": {"prompt_tokens": len(prompt)}}


SETS = {"tel_Telu": {"lines": ["తెలుగు", "రెండు"]}, "deu_Latn": {"lines": ["GROẞ"]}}


class IdsPathTest(unittest.TestCase):
    def test_exact_detokenize_passes(self):
        r = sic.ids_path(FakeHF(), FakeLlama(), FakeLlama(), SETS)
        self.assertEqual({n: s["text_differs"] for n, s in r.items()}, {"tel_Telu": [], "deu_Latn": []})
        self.assertTrue(all(s["model_ran_on_ids"] for s in r.values()))

    def test_a_wrong_piece_is_caught_on_its_line(self):
        r = sic.ids_path(FakeHF(), FakeLlama(broken=ord("ర")), FakeLlama(), SETS)
        self.assertEqual(r["tel_Telu"]["text_differs"], [1])


class VocabTest(unittest.TestCase):
    def test_bad_piece_is_listed(self):
        bm = {v: k for k, v in sic.byte_map().items()}
        tok = {"model": {"vocab": {bm[65]: 65, bm[66]: 66}}, "added_tokens": []}
        self.assertEqual(sic.vocab_pieces(FakeLlama(), tok)["bad"], [])
        self.assertEqual(sic.vocab_pieces(FakeLlama(broken=66), tok)["bad"], [66])


class PlainTextTest(unittest.TestCase):
    def test_counts_per_pack(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        d = Path(tempfile.mkdtemp()) / "ind-te-test"
        d.mkdir()
        docs = ["తెలుగు వాక్యం", "GROẞE Straße", "École de Paris"]   # É + lower case: the case change cuts
        pq.write_table(pa.table({"text": docs}), d / "part-00000.parquet")
        unicode_case = r"\p{Lu}+|\p{Ll}+|\s+|[^\s\p{L}]+|\p{L}+"    # stand-in for tokenizer.json's pattern
        ascii_case = r"[A-Z]+|[a-z]+|\s+|[^\s\p{L}]+|\p{L}+"        # stand-in for llama.cpp's ASCII-only one
        r = sic.plain_text_cost(d.parent, FakeHF(), FakeLlama(), unicode_case, ascii_case)["ind-te-test"]
        self.assertEqual((r["docs"], r["normalizer_changes"], r["sample_ids_differ"]), (3, 1, 1))
        self.assertEqual(r["docs_with_non_ascii_capital"], 2)        # Telugu has no case: never run
        self.assertEqual(r["split_differs"], 2)                      # ẞ and É cut differently


if __name__ == "__main__":
    unittest.main()
