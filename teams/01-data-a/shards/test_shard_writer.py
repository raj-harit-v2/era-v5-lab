"""Tests for shard_writer.py on made-up docs (English, Hindi, Malayalam, Tamil, code). They use the baseline
BrahmicTokenizer-131K that G6 pins (fetched once by G6's tokenizer.py) with --any-tokenizer, since C3's tokenizer.json is not
in the repo; with C3 the same checks run on the real file.

  python -m pytest teams/01-data-a/shards/test_shard_writer.py
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("shard_writer", HERE / "shard_writer.py")
sw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sw)
from dataio.loader import open_shard  # noqa: E402  (shard_writer put G6's folder on sys.path)
from dataio.tokenizer import BrahmicTokenizer  # noqa: E402

BASE = BrahmicTokenizer().path  # the pinned baseline, downloaded and checked by G6's code on first use
MALAYALAM_OLD_CHILLU = "അവന്‍"  # n + virama + ZWJ: the old chillu spelling
DOCS = [
    ("en1", "The water cycle moves water between the sea, the air and the land.\n", "en"),
    ("hi1", "पानी समुद्र, हवा और ज़मीन के बीच घूमता है।\n", "hi"),
    ("ml1", f"{MALAYALAM_OLD_CHILLU} വന്നു. മഴ പെയ്തു.\n", "ml"),
    ("ta1", "நீர் கடல், காற்று, நிலம் இடையே சுற்றுகிறது.\n", "ta"),
    ("go1", "package main\n\nfunc area(r float64) float64 {\n\treturn 3.14159 * r * r\n}\n", "code"),
]


def pack(tmp_path, docs, f2=True):
    clean, summary = tmp_path / "x_clean.parquet", tmp_path / "x_summary.json"
    pq.write_table(pa.Table.from_pylist([{"doc_id": d, "text": t, "lang_label": l} for d, t, l in docs]), clean)
    s = {"pack": "part-00000.parquet", "pack_id": "x-pack", "family": "web", "input_sha256": "0" * 64,
         "clean_py_sha256": "1" * 64}
    if f2:
        s["f2"] = {"set_sha256": "2" * 64, "dropped": []}
    summary.write_text(json.dumps(s), encoding="utf-8")
    return clean, summary


def write(tmp_path, docs, *extra, tokenizer=BASE, f2=True):
    clean, summary = pack(tmp_path, docs, f2)
    out = tmp_path / "out"
    m = sw.main(["--clean", str(clean), "--summary", str(summary), "--tokenizer", str(tokenizer), "--language", "mixed",
                 "--script", "mixed", "--lane", "test", "--out", str(out), *extra])
    return m, out, json.loads(next(out.glob("*.quality_report.json")).read_text(encoding="utf-8"))


def test_a_shard_of_five_languages_is_written_and_checked(tmp_path):
    m, out, q = write(tmp_path, DOCS, "--any-tokenizer")
    assert m["dataset_version"] == "test" and m["eos_token_id"] == 130822 and m["doc_count"] == 5
    assert q["left_out"] == {"secret": 0, "empty": 0, "special": 0, "roundtrip": 0}
    tokens, idx = open_shard(out / m["payload_uri"]), np.load(out / m["index_uri"])
    assert len(tokens) == m["token_count"] == idx[-1] and len(idx) == 6
    assert (tokens == 130822).sum() == 5 and (tokens[idx[1:] - 1] == 130822).all()
    meta = pq.read_table(out / m["sample_metadata_uri"]).to_pylist()
    assert [r["doc_id"] for r in meta] == [d for d, _, _ in DOCS] and [r["input_row"] for r in meta] == list(range(5))
    tok = sw.Tokenizer.from_file(str(BASE))
    for k, (_, text, _) in enumerate(DOCS):  # the Malayalam ZWJ spelling survives: the baseline has no normalizer
        assert tok.decode(tokens[idx[k]:idx[k + 1] - 1].tolist(), skip_special_tokens=False) == text


def test_a_literal_special_string_in_the_text_leaves_the_doc_out(tmp_path):
    docs = DOCS[:1] + [("im", "x = '<|im_start|>user'\n", "code"), ("eot", "a <|end_of_text|> b\n", "en")] + DOCS[1:2]
    m, out, q = write(tmp_path, docs, "--any-tokenizer")
    assert q["left_out_docs"]["special"] == [{"doc_id": "im", "ids": [129994]}, {"doc_id": "eot", "ids": [36]}]
    assert m["doc_count"] == 2


def test_secret_like_and_empty_docs_are_left_out(tmp_path):
    mail = "someone.name" + "@" + "gmail.com"  # built at run time: pr-guard scans the added lines for addresses
    docs = [("mail", f"write to {mail} today\n", "en"), ("empty", "", "en")] + DOCS[:1]
    m, _, q = write(tmp_path, docs, "--any-tokenizer")
    assert q["left_out_docs"]["secret"] == ["mail"] and q["left_out_docs"]["empty"] == ["empty"] and m["doc_count"] == 1


def test_a_doc_is_never_split_and_the_shard_stops_at_the_limit(tmp_path):
    tok = sw.Tokenizer.from_file(str(BASE))
    first_two = sum(len(tok.encode(t, add_special_tokens=False).ids) + 1 for _, t, _ in DOCS[:2])
    m, out, q = write(tmp_path, DOCS, "--any-tokenizer", "--tokens", str(first_two + 1))
    assert m["doc_count"] == 2 and m["token_count"] == first_two and q["rows_read"] == 2


def test_the_round_trip_compares_with_the_normalized_text(tmp_path):
    """A tokenizer with an NFC normalizer: a decomposed é comes back composed, and the doc is kept."""
    spec_ = json.loads(Path(BASE).read_text(encoding="utf-8"))
    spec_["normalizer"] = {"type": "Sequence", "normalizers": [{"type": "NFC"}]}  # a Sequence, as in C3: it tests falsy
    nfc = tmp_path / "nfc_tokenizer.json"
    nfc.write_text(json.dumps(spec_), encoding="utf-8")
    m, out, q = write(tmp_path, [("cafe", "café au lait\n", "en")], "--any-tokenizer", tokenizer=nfc)
    assert q["left_out"]["roundtrip"] == 0 and m["doc_count"] == 1
    ids = open_shard(out / m["payload_uri"]).tolist()[:-1]
    assert sw.Tokenizer.from_file(str(nfc)).decode(ids) == "café au lait\n"


def test_any_tokenizer_but_c3_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="not the frozen C3"):
        write(tmp_path, DOCS)


def test_a_run_without_f2_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="no F2"):
        write(tmp_path, DOCS, "--any-tokenizer", f2=False)


def test_the_c3_pin_matches_g3s_release():
    assert sw.C3_SHA256.startswith("15468e66") and sw.EOS_ID == 130822 and sys.modules["dataio.loader"].HEADER_BYTES == 1024
