"""Unit tests for h3.py, the H3 measurement job: its config checks, how it reads both input layouts, and the pairs it
finds, with a fake encoder in place of the model, so no model, torch or network is needed.

The fake encoder gives each word a fixed random vector and a text the normalised sum of its words' vectors. A made-up
Hindi word stands for a made-up English word (DICTIONARY), so a word-for-word "translation" gets exactly the vectors
of its original, and two unrelated texts get nearly orthogonal ones. Every text here is made up; none comes from a
pack. The job runs in-process with its repository root pointed at a temporary folder, as in test_overlap.py, so nothing
is read from or written to the real inputs or out/.

  python3 -B -m pytest dedup/tests/test_h3.py
"""
import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pa = pytest.importorskip("pyarrow")
torch = pytest.importorskip("torch")
import pyarrow.parquet as pq  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import h3  # noqa: E402

H3_HEADER = ["pack_id_a", "split_a", "part_a", "row_in_part_a", "doc_id_a",   # copied from h3_join.py, the reader
             "pack_id_b", "split_b", "part_b", "row_in_part_b", "doc_id_b", "lang_a", "lang_b", "coverage"]
LATIN = "bcdfghjklmnprstvz"
DEVANAGARI = "कखगघचछजझटठडढतथदधनपफबभमयरलवशसह"


def en_word(i):
    """A made-up English word; distinct for i below 17 x 17."""
    return LATIN[i % len(LATIN)] + "a" + LATIN[(i // len(LATIN)) % len(LATIN)] + "o"


def hi_word(i):
    """A made-up Hindi word (consonant, aa sign, consonant); distinct for i below 29 x 29."""
    return DEVANAGARI[i % len(DEVANAGARI)] + "ा" + DEVANAGARI[(i // len(DEVANAGARI)) % len(DEVANAGARI)]


DICTIONARY = {hi_word(i): en_word(i) for i in range(289)}


def en_doc(words):
    """Sentences of six words each, ending with a full stop."""
    return " ".join(" ".join(en_word(w) for w in words[s:s + 6]) + "." for s in range(0, len(words), 6))


def hi_doc(words):
    """The word-for-word translation of en_doc(words), each sentence ending with a danda."""
    return " ".join(" ".join(hi_word(w) for w in words[s:s + 6]) + "।" for s in range(0, len(words), 6))


def topic(words, new):
    """Each six-word sentence keeps its first two words and takes four new ones: the same topic, other sentences."""
    out = []
    for s in range(0, len(words), 6):
        out += words[s:s + 2] + new[(s // 6) * 4:(s // 6) * 4 + 4]
    return out


E1, E2, E4, H2, H4 = range(0, 24), range(24, 48), range(200, 224), range(48, 72), range(150, 174)
E3 = topic(list(E1), list(range(100, 116)))
SAMPLE = {   # path under the input folder -> [(doc_id, text, url)]
    "en-x/Part_1/part-00000.parquet": [
        ("e1", en_doc(list(E1)), "https://news.example.org/story/1"),
        ("e2", en_doc(list(E2)), ""),
        ("e3", en_doc(E3), ""),                                     # same topic as e1, not a translation
        ("e4", en_doc(list(E4)), "https://example.org/en/story/7"),
        ("e5", "babo.", "")],                                       # too short: skipped, never encoded
    "ind-hi-x/Part_1/part-00000.parquet": [
        ("h1", hi_doc(list(E1)), ""),                               # translation of e1
        ("h2", hi_doc(list(H2)), ""),                               # no English counterpart
        ("h4", hi_doc(list(H4)), "https://example.org/hi/story/7")],  # same URL key as e4, other content
    "ind-hi-x/Heldout/part-00000.parquet": [
        ("h5", hi_doc(list(E2)), "")],                              # held-out translation of e2
    "code-x/Part_1/part-00000.parquet": [
        ("c1", en_doc(list(E1)), "")],                              # a pack not in the config: never read
}


def vector(word):
    seed = int.from_bytes(hashlib.sha256(word.encode()).digest()[:8], "little")
    return np.random.default_rng(seed).standard_normal(64)


class FakeEncoder:
    id = "fake-encoder-v1"
    info = {"name": "fake", "dim": 64}

    def __init__(self):
        self.texts = 0

    def encode(self, texts):
        self.texts += len(texts)
        out = np.zeros((len(texts), 64))
        for r, text in enumerate(texts):
            for token in text.replace("।", " ").replace(".", " ").split():
                out[r] += vector(DICTIONARY.get(token, token))
        return (out / np.linalg.norm(out, axis=1, keepdims=True)).astype(np.float32)


def make_sample(root, parts=SAMPLE):
    base = root / "inputs" / "raw"
    for name, docs in parts.items():
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist([{"pack_id": name.split("/")[0], "doc_id": d, "text": t, "url": u}
                                             for d, t, u in docs]), path)
    return "inputs/raw"


BASE = {"packs": {"ind-hi-*": "hi", "en-*": "en"}, "pairs": [["hi", "en"]], "cache": "", "min_chars": 80,
        "min_sentences": 3, "sentence_min_chars": 20, "top_k": 2, "doc_floor": 0.5, "device": "cpu"}


def make_config(root, name="h3_test.json", **over):
    path = root / name
    path.write_text(json.dumps({"inputs": make_sample(root), "out": "out/t", **BASE, **over}))
    return path


def run(monkeypatch, root, cfg_path, encoder=None):
    """Run h3.main() with root as the repository root; return the output folder and the summary."""
    monkeypatch.setattr(h3, "REPO", root)
    monkeypatch.setattr(sys, "argv", ["h3.py", "--config", str(cfg_path)])
    h3.main(encoder=encoder or FakeEncoder())
    out = root / json.loads(cfg_path.read_text())["out"]
    return out, json.loads((out / "h3_summary.json").read_text())


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def by_doc_ids(out, path):
    ids = {d["row"]: d["doc_id"] for d in pq.read_table(out / "h3_docs.parquet").to_pylist()}
    return {tuple(sorted((ids[int(r["row_a"])], ids[int(r["row_b"])]))): r for r in rows(path)}


def match_ids(path):
    """h3_matches.csv by the two doc_ids of each pair."""
    return {tuple(sorted((r["doc_id_a"], r["doc_id_b"]))): r for r in rows(path)}


def test_finds_translations_and_keeps_the_rest(tmp_path, monkeypatch):
    out, summary = run(monkeypatch, tmp_path, make_config(tmp_path))
    matches = match_ids(out / "h3_matches.csv")
    assert set(matches) == {("e1", "h1"), ("e2", "h5")}
    assert all({m["lang_a"], m["lang_b"]} == {"hi", "en"} for m in matches.values())
    assert float(matches[("e1", "h1")]["coverage"]) == 1.0
    assert {matches[("e2", "h5")]["split_a"], matches[("e2", "h5")]["split_b"]} == {"train", "heldout"}
    assert summary["status"] == "complete" and summary["qualifying"] == 2
    assert summary["qualifying_heldout_train"] == 1


def test_matches_are_keyed_by_document(tmp_path, monkeypatch):
    """h3_matches.csv has exactly the columns h3_join.py reads, and each side is a document of h3_docs.parquet with the
    same pack_id, split, part, row_in_part, doc_id and language."""
    out, _ = run(monkeypatch, tmp_path, make_config(tmp_path))
    with open(out / "h3_matches.csv", newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == H3_HEADER
    docs = {(d["pack"], d["split"], d["part"], d["row_in_part"]): d
            for d in pq.read_table(out / "h3_docs.parquet").to_pylist()}
    matches = rows(out / "h3_matches.csv")
    assert len(matches) == 2
    for m in matches:
        for s in "ab":
            d = docs[(m[f"pack_id_{s}"], m[f"split_{s}"], m[f"part_{s}"], int(m[f"row_in_part_{s}"]))]
            assert d["doc_id"] == m[f"doc_id_{s}"] and d["lang"] == m[f"lang_{s}"]


def test_same_url_key_is_verified_but_needs_aligned_sentences(tmp_path, monkeypatch):
    out, summary = run(monkeypatch, tmp_path, make_config(tmp_path))
    listed = by_doc_ids(out, out / "h3_candidates.csv")
    url_pair = listed[("e4", "h4")]                           # listed because it was found by URL
    assert "url" in url_pair["found_by"] and url_pair["qualifies"] == "false"
    assert float(url_pair["coverage"]) == 0.0
    assert summary["url"]["pairs"] == 1
    assert ("e1", "e3") not in listed and ("e3", "h1") not in match_ids(out / "h3_matches.csv")


def test_sentence_threshold_per_language_pair(tmp_path, monkeypatch):
    """A {language pair: threshold} map applies to its pair, named in either order. At 0 for hi-en, the e4/h4 URL pair
    (other content, 0 aligned at the default 0.7) aligns sentences."""
    out1, s1 = run(monkeypatch, tmp_path, make_config(tmp_path))
    out2, s2 = run(monkeypatch, tmp_path, make_config(tmp_path, name="h3_map.json", out="out/map",
                                                      sentence_threshold={"en-hi": 0.0}))
    assert int(by_doc_ids(out1, out1 / "h3_candidates.csv")[("e4", "h4")]["aligned"]) == 0
    assert int(by_doc_ids(out2, out2 / "h3_candidates.csv")[("e4", "h4")]["aligned"]) > 0
    assert s1["rule"]["sentence_threshold"] == {"hi-en": 0.7} and s2["rule"]["sentence_threshold"] == {"hi-en": 0.0}


def test_sentence_threshold_map_gives_unnamed_pairs_the_default(tmp_path, monkeypatch):
    monkeypatch.setattr(h3, "REPO", tmp_path)
    cfg = h3.load_config(make_config(tmp_path, packs={"ind-hi-*": "hi", "ind-sa-*": "sa", "en-*": "en"},
                                     pairs=[["hi", "en"], ["sa", "en"], ["sa", "hi"]],
                                     sentence_threshold={"en-sa": 0.55, "sa-hi": 0.6}))
    assert h3.sentence_thresholds(cfg) == {"hi-en": 0.7, "sa-en": 0.55, "sa-hi": 0.6}


def test_imports_and_runs_without_the_resource_module(tmp_path, monkeypatch):
    """resource is Unix only. Without it (Windows), h3.py still imports, and a run reports peak_rss_mb as null."""
    spec = importlib.util.spec_from_file_location("h3_without_resource", h3.__file__)
    module = importlib.util.module_from_spec(spec)
    with monkeypatch.context() as m:
        m.setitem(sys.modules, "resource", None)                 # import resource now raises ImportError
        spec.loader.exec_module(module)
    assert module.resource is None and module.peak_rss_mb() is None
    monkeypatch.setattr(h3, "resource", None)
    _, summary = run(monkeypatch, tmp_path, make_config(tmp_path))
    assert summary["status"] == "complete" and summary["peak_rss_mb"] is None


def test_reads_only_configured_packs_and_skips_short_documents(tmp_path, monkeypatch):
    out, summary = run(monkeypatch, tmp_path, make_config(tmp_path))
    docs = pq.read_table(out / "h3_docs.parquet").to_pylist()
    assert sorted(d["doc_id"] for d in docs) == ["e1", "e2", "e3", "e4", "h1", "h2", "h4", "h5"]
    assert {d["doc_id"]: d["split"] for d in docs}["h5"] == "heldout"
    assert set(summary["documents"]) == {"en-x", "ind-hi-x"}       # code-x is not read
    assert summary["documents"]["en-x"]["too_short"] == 1
    assert summary["inputs"]["parts_selected"] == 3 and summary["inputs"]["parts_found"] == 4


def test_reads_the_train_heldout_layout_too(tmp_path, monkeypatch):
    """TSAI's cleaned output: train/<pack>/ and heldout/<pack>/ instead of <pack>/Part_N/ and <pack>/Heldout/. As in
    overlap_docs.parquet, part is the path under the split folder, so the same part name is in both splits here, and a
    Parquet file outside the two split folders is not read."""
    layout = {"train/en-x/part-00000.parquet": SAMPLE["en-x/Part_1/part-00000.parquet"],
              "train/ind-hi-x/part-00000.parquet": SAMPLE["ind-hi-x/Part_1/part-00000.parquet"],
              "heldout/ind-hi-x/part-00000.parquet": SAMPLE["ind-hi-x/Heldout/part-00000.parquet"],
              "reports/en-x/part-00000.parquet": [("r2", en_doc(list(H2)), "")]}   # would translate h2 if read
    for name, docs in layout.items():
        path = tmp_path / "inputs" / "cleaned" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist([{"pack_id": name.split("/")[1], "doc_id": d, "text": t, "url": u}
                                             for d, t, u in docs]), path)
    cfg = tmp_path / "h3_cleaned.json"
    cfg.write_text(json.dumps({"inputs": "inputs/cleaned", "out": "out/c", **BASE}))
    out, summary = run(monkeypatch, tmp_path, cfg)
    matches = match_ids(out / "h3_matches.csv")
    assert set(matches) == {("e1", "h1"), ("e2", "h5")}
    assert summary["inputs"]["parts_found"] == 3
    m = matches[("e2", "h5")]
    sides = {m[f"doc_id_{s}"]: (m[f"pack_id_{s}"], m[f"split_{s}"], m[f"part_{s}"], m[f"row_in_part_{s}"])
             for s in "ab"}
    assert sides == {"e2": ("en-x", "train", "en-x/part-00000.parquet", "1"),
                     "h5": ("ind-hi-x", "heldout", "ind-hi-x/part-00000.parquet", "0")}


def test_writes_no_text(tmp_path, monkeypatch):
    out, _ = run(monkeypatch, tmp_path, make_config(tmp_path))
    first_en, first_hi = en_doc(list(E1)).split(".")[0], hi_doc(list(E1)).split("।")[0]
    for f in out.iterdir():
        data = f.read_bytes()
        assert first_en.encode() not in data and first_hi.encode() not in data, f.name


def test_summary_has_stage_times_and_an_estimate(tmp_path, monkeypatch):
    _, summary = run(monkeypatch, tmp_path, make_config(tmp_path, max_docs_per_pack=2))
    assert {"read", "url", "encode", "retrieve", "verify_read", "verify"} <= set(summary["stages_seconds"])
    assert all(d["encoded"] <= 2 for d in summary["documents"].values())
    est = summary["estimate_all_documents"]
    assert est["documents_full"]["en"] >= est["documents_encoded"]["en"]
    assert est["suggested_max_time_minutes"] >= 1
    assert set(summary["outputs"]) == set(h3.OUTPUTS)


def test_cache_skips_encoding_on_a_rerun(tmp_path, monkeypatch):
    first = FakeEncoder()
    out1, s1 = run(monkeypatch, tmp_path, make_config(tmp_path, cache="out/cache"), first)
    second = FakeEncoder()
    cfg2 = tmp_path / "h3_rerun.json"
    cfg2.write_text(json.dumps({**json.loads((tmp_path / "h3_test.json").read_text()), "out": "out/t2"}))
    out2, s2 = run(monkeypatch, tmp_path, cfg2, second)
    assert s1["counts"]["encoded_heads"] == 8 and s2["counts"].get("encoded_heads", 0) == 0
    assert s2["counts"]["cached_parts"] == 3
    m1, m2 = match_ids(out1 / "h3_matches.csv"), match_ids(out2 / "h3_matches.csv")
    assert set(m1) == set(m2) == {("e1", "h1"), ("e2", "h5")}   # cached vectors are float16: compare pairs
    assert all(m1[k]["coverage"] == m2[k]["coverage"] for k in m1)


def test_batch_sizes_do_not_change_the_result(tmp_path, monkeypatch):
    """One row per record batch, three texts per encoder call, one row per retrieval block and one pair per alignment
    step give the same documents, candidates and matches as the defaults."""
    out1, s1 = run(monkeypatch, tmp_path, make_config(tmp_path))
    monkeypatch.setattr(h3, "BATCH_ROWS", 1)
    monkeypatch.setattr(h3, "CHUNK", 3)
    out2, s2 = run(monkeypatch, tmp_path, make_config(tmp_path, name="h3_small.json", out="out/small", block=1,
                                                      pair_batch=1))
    assert pq.read_table(out1 / "h3_docs.parquet").equals(pq.read_table(out2 / "h3_docs.parquet"))
    assert set(by_doc_ids(out1, out1 / "h3_candidates.csv")) == set(by_doc_ids(out2, out2 / "h3_candidates.csv"))
    assert (out1 / "h3_matches.csv").read_text() == (out2 / "h3_matches.csv").read_text()
    assert s1["counts"]["rows_scanned"] == s2["counts"]["rows_scanned"] == 9


def test_encode_sends_texts_longest_first_and_keeps_their_order(monkeypatch):
    """encode() gives the encoder the texts longest first, CHUNK at a time, and puts each row back in its text's
    place: the same vectors as encoding every text in order."""
    class Recording(FakeEncoder):
        def __init__(self):
            super().__init__()
            self.lengths = []

        def encode(self, texts):
            self.lengths += [len(t) for t in texts]
            return super().encode(texts)

    monkeypatch.setattr(h3, "CHUNK", 2)
    texts = pa.array([en_doc(list(range(n))) for n in (6, 30, 12, 24, 18)])
    encoder, stats = Recording(), Counter()
    V = h3.encode(encoder, texts, h3.Clock(60), stats, "texts", "cpu", torch.float32)
    assert encoder.lengths == sorted(encoder.lengths, reverse=True) and stats["texts"] == 5
    assert torch.allclose(V, h3.unit(torch.as_tensor(FakeEncoder().encode(texts.to_pylist()))), atol=1e-6)


def test_max_docs_per_pack_across_record_batches(tmp_path, monkeypatch):
    monkeypatch.setattr(h3, "BATCH_ROWS", 2)
    out, summary = run(monkeypatch, tmp_path, make_config(tmp_path, max_docs_per_pack=3))
    docs = pq.read_table(out / "h3_docs.parquet").to_pylist()
    # The first 3 long documents of each pack, parts in path order: ind-hi-x/Heldout/ (h5) before ind-hi-x/Part_1/.
    assert sorted(d["doc_id"] for d in docs) == ["e1", "e2", "e3", "h1", "h2", "h5"]
    assert summary["documents"]["en-x"]["encoded"] == 3 and summary["documents"]["ind-hi-x"]["encoded"] == 3


def test_time_limit_stops_and_writes_no_results(tmp_path, monkeypatch):
    cfg = make_config(tmp_path, max_minutes=1e-9)
    monkeypatch.setattr(h3, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["h3.py", "--config", str(cfg)])
    with pytest.raises(SystemExit, match="incomplete"):
        h3.main(encoder=FakeEncoder())
    out = tmp_path / "out" / "t"
    assert json.loads((out / "h3_summary.json").read_text())["status"] == "stopped_time_limit"
    assert not any((out / f).exists() for f in h3.OUTPUTS)


@pytest.mark.parametrize("over,message", [
    ({"colour": 1}, "unknown keys"),
    ({"pairs": [["hi", "sa"]]}, "pairs must be"),
    ({"pairs": [["hi", "en"], ["en", "hi"]]}, "pairs must be"),
    ({"out": "results/h3"}, "inside out/"),
    ({"cache": "../cache"}, "inside out/"),
    ({"packs": {}}, "packs must be"),
    ({"top_k": 0}, "top_k must be"),
    ({"head_sentences": 20, "max_sentences": 16}, "head_sentences"),
    ({"coverage_threshold": 1.5}, "coverage_threshold"),
    ({"sentence_threshold": {"hi-sa": 0.5}}, "sentence_threshold keys"),
    ({"sentence_threshold": {"hi-en": 0.5, "en-hi": 0.6}}, "sentence_threshold keys"),
    ({"sentence_threshold": {"hi-en": 1.5}}, "sentence_threshold must be"),
    ({"sentence_threshold": "0.7"}, "sentence_threshold must be"),
    ({"max_output_mb": 60}, "max_output_mb"),
    ({"device": "tpu"}, "device"),
    ({"precision": "fp8"}, "precision"),
    ({"pair_batch": 0}, "pair_batch"),
    ({"sync_debug": 1}, "sync_debug"),
])
def test_config_errors(tmp_path, monkeypatch, over, message):
    monkeypatch.setattr(h3, "REPO", tmp_path)
    with pytest.raises(SystemExit, match=message):
        h3.load_config(make_config(tmp_path, **over))


def test_no_model_folder_stops_before_reading(tmp_path, monkeypatch):
    cfg = make_config(tmp_path, model_path="models/missing")
    monkeypatch.setattr(h3, "REPO", tmp_path)
    monkeypatch.setattr(sys, "argv", ["h3.py", "--config", str(cfg)])
    with pytest.raises(SystemExit, match="never downloaded"):
        h3.main()
