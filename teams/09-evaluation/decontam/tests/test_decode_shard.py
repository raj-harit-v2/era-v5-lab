"""Tests for decode_shard.py (G9, week 3 task 2).

    pytest teams/09-evaluation/decontam/tests/test_decode_shard.py -q

The unit tests build tiny shards in shard format v1 with a small word-level tokenizer, so they need numpy, pyarrow and
tokenizers but not a frozen tokenizer.json (8 MB, not in the repo). They are skipped without those packages.

One more test runs on a real shard when ERA_SHARD (a <shard_id>.bin with its .idx.npy, .docs.parquet and .json next to
it) and ERA_TOKENIZER (the frozen tokenizer.json the shard was written with: p1536, or C3 for Data A's sample shard;
the old name ERA_C3_TOKENIZER also works) are set; ERA_SHARD_CLEAN (the run_clean.py *_clean.parquet it
came from) adds the round-trip check. Data A's sample shard (teams/01-data-a/shards/sample/README.md) can be rebuilt
for this with the two commands in its README.
"""

import hashlib
import json
import os
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")
tokenizers = pytest.importorskip("tokenizers")

import canary_scan  # noqa: E402
import decode_shard as ds  # noqa: E402
from decontam_check import read_docs  # noqa: E402

EOS, SPECIAL = 9, 9  # toy vocab: id 9 is the EOS and the first special id
# ids 0-9 with no gaps, so tokens a test adds get fresh ids (10, 11, ...), as in p1536 and C3
VOCAB = {"[UNK]": 0, "hello": 1, "world": 2, "foo": 3, "bar": 4, "baz": 5, "qux": 6, "quux": 7, "<x>": 8, "<eos>": 9}
DOCS = {"d1": "hello world", "d2": "foo bar baz", "d3": "world"}  # d1: 0-2, d2: 3-6, d3: 7-8 (EOS last)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _toy(tmp_path, specials=()):
    from tokenizers import Tokenizer, models, pre_tokenizers
    tok = Tokenizer(models.WordLevel(VOCAB, unk_token="[UNK]"))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    if specials:
        tok.add_special_tokens(list(specials))
    path = tmp_path / f"toy_tokenizer{len(specials)}.json"
    tok.save(str(path))
    return path


@pytest.fixture
def toy_tokenizer(tmp_path):
    return _toy(tmp_path)


def write_shard(folder, tok_path, docs=DOCS, shard_id="toy-train-000000", eos=EOS, tamper=None):
    """Write <shard_id>.{bin,idx.npy,docs.parquet,json} like shard_writer.py, with a full manifest.
    tamper(files) may edit the files before the manifest is written, so the sha256 checks still pass."""
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(tok_path))
    seqs = [tok.encode(text).ids + [eos] for text in docs.values()]
    tokens = np.array([t for s in seqs for t in s], dtype="<u4")
    starts = np.concatenate([[0], np.cumsum([len(s) for s in seqs])]).astype(np.int64)
    folder = Path(folder)
    files = {"bin": folder / f"{shard_id}.bin", "idx": folder / f"{shard_id}.idx.npy",
             "docs": folder / f"{shard_id}.docs.parquet", "manifest": folder / f"{shard_id}.json"}
    header = np.zeros(256, dtype="<i4")
    header[:3] = [ds.MAGIC, ds.VERSION, len(tokens)]
    files["bin"].write_bytes(header.tobytes() + tokens.tobytes())
    np.save(files["idx"], starts)
    pq.write_table(pa.table({"doc_id": list(docs), "n_tokens": np.diff(starts)}), files["docs"])
    if tamper:
        tamper(files)
    idx_now = np.load(files["idx"])
    manifest = {"schema_version": "shard-v1", "token_dtype": "uint32", "shard_id": shard_id,
                "payload_uri": files["bin"].name, "index_uri": files["idx"].name,
                "sample_metadata_uri": files["docs"].name, "payload_bytes": files["bin"].stat().st_size,
                "payload_sha256": _sha(files["bin"]), "index_sha256": _sha(files["idx"]),
                "sample_metadata_sha256": _sha(files["docs"]), "doc_count": len(idx_now) - 1,
                "token_count": int(idx_now[-1]), "eos_token_id": eos, "tokenizer_sha256": _sha(tok_path)}
    files["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
    return files


def _decode(files, tok_path, special_from=SPECIAL):
    tok, sha = ds.load_tokenizer(tok_path, any_tokenizer=True)
    return ds.decode_shard(files["bin"], tok, sha, eos_id=EOS, special_from=special_from)


def _run_cli(argv):
    old = (ds.EOS_ID, ds.SPECIAL_FROM)
    ds.EOS_ID, ds.SPECIAL_FROM = EOS, SPECIAL
    try:
        return ds.main(argv)
    finally:
        ds.EOS_ID, ds.SPECIAL_FROM = old


def _set_token(pos, value):
    def tamper(files):
        raw = bytearray(files["bin"].read_bytes())
        at = ds.HEADER_BYTES + 4 * pos
        raw[at:at + 4] = int(value).to_bytes(4, "little")
        files["bin"].write_bytes(bytes(raw))
    return tamper


def _set_header(index, value):
    def tamper(files):
        raw = bytearray(files["bin"].read_bytes())
        raw[4 * index:4 * index + 4] = int(value).to_bytes(4, "little", signed=True)
        files["bin"].write_bytes(bytes(raw))
    return tamper


def _docs(**cols):
    return lambda f: pq.write_table(pa.table(cols), f["docs"])


# --- correct shards -----------------------------------------------------------------------------------------------

def test_decode_round_trip(tmp_path, toy_tokenizer):
    files = write_shard(tmp_path, toy_tokenizer)
    table = _decode(files, toy_tokenizer)
    assert table.column("doc_id").to_pylist() == list(DOCS)
    assert table.column("text").to_pylist() == list(DOCS.values())
    assert table.column("n_tokens").to_pylist() == [3, 4, 2]  # tokens plus the final EOS
    assert set(table.column("shard_id").to_pylist()) == {"toy-train-000000"}


def test_one_document_shard(tmp_path, toy_tokenizer):
    files = write_shard(tmp_path, toy_tokenizer, docs={"only": "foo"})
    assert _decode(files, toy_tokenizer).column("text").to_pylist() == ["foo"]


def test_output_reads_in_decontam_check(tmp_path, toy_tokenizer):
    files = write_shard(tmp_path, toy_tokenizer)
    out = tmp_path / "toy.text.parquet"
    pq.write_table(_decode(files, toy_tokenizer), out)
    assert list(read_docs([out], "doc_id", "text")) == list(DOCS.items())


def test_output_reads_in_canary_scan(tmp_path, toy_tokenizer):
    files = write_shard(tmp_path, toy_tokenizer)
    out = tmp_path / "toy.text.parquet"
    pq.write_table(_decode(files, toy_tokenizer), out)
    assert list(canary_scan.read_file(out, out.name, "doc_id", "text")) == list(DOCS.items())


def test_output_names_the_exact_shard(tmp_path, toy_tokenizer):
    files = write_shard(tmp_path, toy_tokenizer)
    table = _decode(files, toy_tokenizer)
    m = json.loads(files["manifest"].read_text())
    assert set(table.column("payload_sha256").to_pylist()) == {m["payload_sha256"]}
    assert set(table.column("dataset_version").to_pylist()) == {"None"}  # the toy manifest has none
    assert set(table.column("split").to_pylist()) == {"None"}


def test_int_doc_ids_are_accepted_as_strings(tmp_path, toy_tokenizer):
    def int_ids(files):
        pq.write_table(pa.table({"doc_id": [11, 12, 13], "n_tokens": [3, 4, 2]}), files["docs"])
    files = write_shard(tmp_path, toy_tokenizer, tamper=int_ids)
    assert _decode(files, toy_tokenizer).column("doc_id").to_pylist() == ["11", "12", "13"]


def test_uri_may_be_a_full_store_path(tmp_path, toy_tokenizer):
    """The manifest template puts a store path in *_uri; only the file name has to match."""
    files = write_shard(tmp_path, toy_tokenizer)
    m = json.loads(files["manifest"].read_text())
    for key, f in (("payload_uri", "bin"), ("index_uri", "idx"), ("sample_metadata_uri", "docs")):
        m[key] = f"<store>/corpus-v1/toy/train/{files[f].name}"
    files["manifest"].write_text(json.dumps(m))
    assert _decode(files, toy_tokenizer).num_rows == 3


def test_check_text_finds_a_changed_document(tmp_path, toy_tokenizer):
    files = write_shard(tmp_path, toy_tokenizer)
    table = _decode(files, toy_tokenizer)
    clean = tmp_path / "clean.parquet"
    pq.write_table(pa.table({"doc_id": list(DOCS), "text": list(DOCS.values())}), clean)
    tok, _ = ds.load_tokenizer(toy_tokenizer, any_tokenizer=True)
    assert ds.check_text(table, clean, tok) == (3, [])
    pq.write_table(pa.table({"doc_id": ["d1", "d2"], "text": ["hello world", "foo baz"]}), clean)
    checked, bad = ds.check_text(table, clean, tok)
    assert checked == 3 and dict(bad) == {"d2": "text differs", "d3": "not in source"}


def test_cli_writes_one_file_per_shard(tmp_path, toy_tokenizer, capsys):
    shards = tmp_path / "shards"
    shards.mkdir()
    write_shard(shards, toy_tokenizer, shard_id="toy-train-000000")
    write_shard(shards, toy_tokenizer, docs={"e1": "baz foo"}, shard_id="toy-train-000001")
    rc = _run_cli([str(shards), "--tokenizer", str(toy_tokenizer), "--out", str(tmp_path / "out"), "--any-tokenizer"])
    assert rc == 0
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["toy-train-000000.text.parquet",
                                                                    "toy-train-000001.text.parquet"]
    assert "decoded 2 of 2 shard(s)" in capsys.readouterr().err


def test_refuses_a_tokenizer_that_is_not_frozen(toy_tokenizer):
    with pytest.raises(ds.ShardError, match="is not a frozen tokenizer"):
        ds.load_tokenizer(toy_tokenizer)


def test_frozen_set_is_p1536_and_c3():
    """The two sha256 from TSAI's Gate 3 notice (p1536, 15 Nov) and the G3 freeze (C3, #340)."""
    assert ds.FROZEN_TOKENIZERS == {
        "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b": "p1536",
        "15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3": "C3"}


def test_both_frozen_tokenizers_load_and_others_are_refused(tmp_path, monkeypatch):
    """Two toy tokenizers stand in for p1536 and C3 (same vocab, EOS and specials, different sha256)."""
    p1536, c3, other = _toy(tmp_path, ["<a>"]), _toy(tmp_path, ["<a>", "<b>"]), _toy(tmp_path, ["<a>", "<b>", "<c>"])
    monkeypatch.setattr(ds, "FROZEN_TOKENIZERS", {_sha(p1536): "p1536", _sha(c3): "C3"})
    for path in (p1536, c3, other):
        assert ds.Tokenizer.from_file(str(path)).id_to_token(EOS) == "<eos>"  # added tokens did not take id 9
    monkeypatch.setattr(ds, "EOS_ID", EOS)
    monkeypatch.setattr(ds, "EOS", "<eos>")
    for path in (p1536, c3):
        monkeypatch.setattr(ds, "VOCAB", ds.vocab_end(ds.Tokenizer.from_file(str(path))))
        assert ds.load_tokenizer(path)[1] == _sha(path)
    with pytest.raises(ds.ShardError, match=r"is not a frozen tokenizer \(p1536 .*, C3 .*\)"):
        ds.load_tokenizer(other)


def test_shard_from_one_frozen_tokenizer_is_refused_with_the_other(tmp_path, toy_tokenizer):
    """The manifest names the tokenizer the shard was written with; decoding with another one is refused."""
    files = write_shard(tmp_path, toy_tokenizer)
    other = _toy(tmp_path, ["<a>"])
    tok, sha = ds.load_tokenizer(other, any_tokenizer=True)
    with pytest.raises(ds.ShardError, match="tokenizer_sha256"):
        ds.decode_shard(files["bin"], tok, sha, eos_id=EOS, special_from=SPECIAL)


# --- shards that must be refused ----------------------------------------------------------------------------------

@pytest.mark.parametrize("tamper, message", [
    (_set_header(0, 1234), "bad header"),
    (_set_header(1, 1), "bad header"),
    (lambda f: f["bin"].write_bytes(f["bin"].read_bytes()[:-4]), "size"),
    (lambda f: np.save(f["idx"], np.array([0, 3, 7], dtype=np.int64)), "end at the token count"),
    (lambda f: np.save(f["idx"], np.array([0, 3, 3, 9], dtype=np.int64)), "rise"),
    (_docs(doc_id=["d1", "d2"], n_tokens=[3, 4]), "rows"),
    (_docs(doc_id=["d1", "d2", "d3"]), "no n_tokens column"),
    (_docs(doc_id=["d1", "d1", "d3"], n_tokens=[3, 4, 2]), "not unique"),
    (_docs(doc_id=["d1", None, "d3"], n_tokens=[3, 4, 2]), "null or empty"),
    # rows shifted by one: every doc_id would point at another document's text
    (_docs(doc_id=["d3", "d1", "d2"], n_tokens=[2, 3, 4]), r"row 0 \(d3\) n_tokens 2, the index gives 3"),
    (_set_token(1, EOS), "special id 9 inside document d1"),            # an EOS inside a document
    (_set_token(4, 8), "special id 8 inside document d2"),              # a reserved special id inside a document
    (_set_token(4, 200_000), "token id 200000 at position 4 is not below the vocab size 10"),
    (_set_token(8, 2), "does not end with EOS"),
])
def test_bad_shard_is_refused(tmp_path, toy_tokenizer, tamper, message):
    files = write_shard(tmp_path, toy_tokenizer, tamper=tamper)
    with pytest.raises(ds.ShardError, match=message):
        _decode(files, toy_tokenizer, special_from=8)


def test_merged_documents_are_refused(tmp_path, toy_tokenizer):
    """Drop one index boundary and its docs row: two documents would come out as one, joined by an EOS."""
    def merge_d1_d2(files):
        np.save(files["idx"], np.array([0, 7, 9], dtype=np.int64))
        pq.write_table(pa.table({"doc_id": ["d1", "d3"], "n_tokens": [7, 2]}), files["docs"])
    files = write_shard(tmp_path, toy_tokenizer, tamper=merge_d1_d2)
    with pytest.raises(ds.ShardError, match="special id 9 inside document d1"):
        _decode(files, toy_tokenizer)


def test_added_special_token_below_the_reserved_block_is_refused(tmp_path):
    """p1536 and C3 have added special tokens below 130,725 (e.g. 36, 129994); they count as special too."""
    path = _toy(tmp_path, specials=["<sp>"])
    from tokenizers import Tokenizer
    sp_id = Tokenizer.from_file(str(path)).token_to_id("<sp>")
    files = write_shard(tmp_path, path, tamper=_set_token(4, sp_id))
    tok, sha = ds.load_tokenizer(path, any_tokenizer=True)
    assert sp_id in ds.special_ids(tok).tolist()
    with pytest.raises(ds.ShardError, match=f"special id {sp_id} inside document d2"):
        ds.decode_shard(files["bin"], tok, sha, eos_id=EOS)  # default block (130,725+) is above this toy vocab


@pytest.mark.parametrize("key, value", [
    ("schema_version", "shard-v0"), ("token_dtype", "uint16"), ("shard_id", "hindi-web-train-000123"),
    ("payload_uri", "other.bin"), ("index_uri", "other.idx.npy"), ("sample_metadata_uri", "other.docs.parquet"),
    ("payload_bytes", 1), ("payload_sha256", "0" * 64), ("index_sha256", "0" * 64),
    ("sample_metadata_sha256", "0" * 64), ("doc_count", 2), ("token_count", 8), ("eos_token_id", 7),
    ("tokenizer_sha256", "0" * 64),
])
def test_manifest_mismatch_is_refused(tmp_path, toy_tokenizer, key, value):
    files = write_shard(tmp_path, toy_tokenizer)
    m = json.loads(files["manifest"].read_text())
    m[key] = value
    files["manifest"].write_text(json.dumps(m))
    with pytest.raises(ds.ShardError, match=key):
        _decode(files, toy_tokenizer)


def test_renamed_shard_is_refused(tmp_path, toy_tokenizer):
    """The shard_id comes from the manifest, not just the file name."""
    files = write_shard(tmp_path, toy_tokenizer)
    for f in files.values():
        f.rename(f.with_name(f.name.replace("toy-train-000000", "hindi-web-train-000123")))
    with pytest.raises(ds.ShardError, match="shard_id"):
        _decode(ds.shard_files(tmp_path / "hindi-web-train-000123.bin"), toy_tokenizer)


def test_missing_file_is_refused(tmp_path, toy_tokenizer):
    files = write_shard(tmp_path, toy_tokenizer)
    files["docs"].unlink()
    with pytest.raises(ds.ShardError, match="missing"):
        _decode(files, toy_tokenizer)


# --- the command line on bad input --------------------------------------------------------------------------------

@pytest.mark.parametrize("manifest", ["{not json", "[]"])
def test_bad_manifest_skips_that_shard_only(tmp_path, toy_tokenizer, capsys, manifest):
    shards = tmp_path / "shards"
    shards.mkdir()
    write_shard(shards, toy_tokenizer, shard_id="toy-train-000000")
    bad = write_shard(shards, toy_tokenizer, docs={"e1": "baz"}, shard_id="toy-train-000001")
    bad["manifest"].write_text(manifest, encoding="utf-8")
    rc = _run_cli([str(shards), "--tokenizer", str(toy_tokenizer), "--out", str(tmp_path / "out"), "--any-tokenizer"])
    assert rc == 1
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["toy-train-000000.text.parquet"]
    assert "decoded 1 of 2 shard(s)" in capsys.readouterr().err


def test_duplicate_shard_id_is_refused(tmp_path, toy_tokenizer, capsys):
    for sub in ("a", "b"):
        (tmp_path / "shards" / sub).mkdir(parents=True)
        write_shard(tmp_path / "shards" / sub, toy_tokenizer, shard_id="toy-train-000000")
    rc = _run_cli([str(tmp_path / "shards"), "--tokenizer", str(toy_tokenizer), "--out", str(tmp_path / "out"),
                   "--any-tokenizer"])
    err = capsys.readouterr().err
    assert rc == 1 and "appears twice" in err and "decoded 1 of 2 shard(s)" in err


def test_stray_bin_without_manifest_is_ignored(tmp_path, toy_tokenizer, capsys):
    shards = tmp_path / "shards"
    shards.mkdir()
    write_shard(shards, toy_tokenizer)
    (shards / "pytorch_model.bin").write_bytes(b"\0" * 64)
    rc = _run_cli([str(shards), "--tokenizer", str(toy_tokenizer), "--out", str(tmp_path / "out"), "--any-tokenizer"])
    err = capsys.readouterr().err
    assert rc == 0 and "ignoring" in err and "pytorch_model.bin" in err and "decoded 1 of 1 shard(s)" in err


def test_shard_missing_its_manifest_fails_and_old_output_is_removed(tmp_path, toy_tokenizer, capsys):
    """An incomplete download (.bin, .idx.npy, .docs.parquet, no .json) is a failed shard, not an ignored file."""
    shards, out = tmp_path / "shards", tmp_path / "out"
    shards.mkdir()
    write_shard(shards, toy_tokenizer, shard_id="toy-train-000000")
    files = write_shard(shards, toy_tokenizer, shard_id="toy-train-000001")
    argv = [str(shards), "--tokenizer", str(toy_tokenizer), "--out", str(out), "--any-tokenizer"]
    assert _run_cli(argv) == 0 and (out / "toy-train-000001.text.parquet").exists()
    files["manifest"].unlink()
    assert _run_cli(argv) == 1
    assert not (out / "toy-train-000001.text.parquet").exists()
    assert "missing toy-train-000001.json" in capsys.readouterr().err


@pytest.mark.parametrize("bad", ["missing_tokenizer", "out_is_a_file"])
def test_bad_arguments_give_a_message_not_a_traceback(tmp_path, toy_tokenizer, capsys, bad):
    shards = tmp_path / "shards"
    shards.mkdir()
    write_shard(shards, toy_tokenizer)
    tok, out = toy_tokenizer, tmp_path / "out"
    if bad == "missing_tokenizer":
        tok = tmp_path / "nope.json"
    else:
        out.write_text("a file")
    assert _run_cli([str(shards), "--tokenizer", str(tok), "--out", str(out), "--any-tokenizer"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("decode_shard: ") and "Traceback" not in err


def test_failed_rerun_removes_the_old_output(tmp_path, toy_tokenizer):
    shards, out = tmp_path / "shards", tmp_path / "out"
    shards.mkdir()
    files = write_shard(shards, toy_tokenizer)
    argv = [str(shards), "--tokenizer", str(toy_tokenizer), "--out", str(out), "--any-tokenizer"]
    assert _run_cli(argv) == 0 and (out / "toy-train-000000.text.parquet").exists()
    _set_token(0, 2)(files)  # corrupt the .bin; the manifest sha256 no longer matches
    assert _run_cli(argv) == 1
    assert not (out / "toy-train-000000.text.parquet").exists()


def test_cli_check_text_mismatch_writes_nothing(tmp_path, toy_tokenizer, capsys):
    shards = tmp_path / "shards"
    shards.mkdir()
    write_shard(shards, toy_tokenizer)
    clean = tmp_path / "clean.parquet"
    pq.write_table(pa.table({"doc_id": list(DOCS), "text": ["hello world", "foo baz", "world"]}), clean)
    rc = _run_cli([str(shards), "--tokenizer", str(toy_tokenizer), "--out", str(tmp_path / "out"), "--any-tokenizer",
                   "--check-text", str(clean)])
    assert rc == 1 and not list((tmp_path / "out").iterdir())
    assert "1 of 3 documents do not round-trip (first: d2)" in capsys.readouterr().err


def test_check_text_with_several_shards_is_refused(tmp_path, toy_tokenizer, capsys):
    shards = tmp_path / "shards"
    shards.mkdir()
    write_shard(shards, toy_tokenizer, shard_id="toy-train-000000")
    write_shard(shards, toy_tokenizer, shard_id="toy-train-000001")
    clean = tmp_path / "clean.parquet"
    pq.write_table(pa.table({"doc_id": list(DOCS), "text": list(DOCS.values())}), clean)
    rc = _run_cli([str(shards), "--tokenizer", str(toy_tokenizer), "--out", str(tmp_path / "out"), "--any-tokenizer",
                   "--check-text", str(clean)])
    assert rc == 1 and "takes one shard" in capsys.readouterr().err


# --- a real shard (optional) --------------------------------------------------------------------------------------

REAL_TOKENIZER = os.environ.get("ERA_TOKENIZER") or os.environ.get("ERA_C3_TOKENIZER")
real = pytest.mark.skipif(not (os.environ.get("ERA_SHARD") and REAL_TOKENIZER),
                          reason="set ERA_SHARD and ERA_TOKENIZER to test a real shard")


@real
def test_real_shard_decodes():
    tok, sha = ds.load_tokenizer(REAL_TOKENIZER)
    table = ds.decode_shard(os.environ["ERA_SHARD"], tok, sha)
    docs = pq.read_table(ds.shard_files(os.environ["ERA_SHARD"])["docs"])
    assert table.column("doc_id").to_pylist() == [str(d) for d in docs.column("doc_id").to_pylist()]
    assert all(isinstance(t, str) and t for t in table.column("text").to_pylist())
    assert "<|endoftext|>" not in "".join(table.column("text").to_pylist())
    if os.environ.get("ERA_SHARD_CLEAN"):
        checked, bad = ds.check_text(table, os.environ["ERA_SHARD_CLEAN"], tok)
        assert bad == [], f"{len(bad)} of {checked} documents do not round-trip"
