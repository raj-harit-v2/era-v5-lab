"""Decode training shards (Data A shard format v1) back to text for the decontamination check (G9).

    python decode_shard.py <shard.bin | folder> --tokenizer <p1536>/tokenizer.json --out <dir>
    python decontam_check.py <dir>/<shard_id>.text.parquet          # full set: no --benchmarks, --tags or --exclude

A shard (teams/01-data-a/shards/shard_format_v1.md) holds token IDs, not text:
  <shard_id>.bin           1,024-byte header (256 little-endian int32: magic 20261025, version 2, token count),
                           then the uint32 ids
  <shard_id>.idx.npy       int64 start of each document, then the token count
  <shard_id>.docs.parquet  doc_id and n_tokens per document, in shard order (IDs and counts only)
  <shard_id>.json          the manifest (shard_id, file names, sha256 of each file, counts, EOS id, tokenizer sha256)

This script checks a shard against its manifest and against the rules shard_writer.py asserts, then writes
<out>/<shard_id>.text.parquet with the columns doc_id, text, shard_id, n_tokens, payload_sha256, dataset_version and
split. decontam_check.py and canary_scan.py read that file as it is (doc_id and text columns).

Each document is its tokens minus the final EOS (<|endoftext|> id 130822), decoded with a frozen tokenizer:
  - p1536: frozen at Gate 3 (sha256 P1536_SHA256); the first training shards use it;
  - C3: the earlier freeze (sha256 C3_SHA256); Data A's sample shard and earlier work use it.
Any other tokenizer is refused, and the shard's manifest must name the same tokenizer sha256. The two have the same
vocab (131,072), EOS and special ids. The text is the tokenizer-normalized text the model trains on.

Checks. A shard that fails one is reported and skipped: any old output for it is removed and nothing new is written. The
other shards still run, and the exit code is 1 if any shard failed.
  - header magic and version; file size = 1,024 + 4 x token count = the manifest's payload_bytes;
  - .idx.npy is int64, starts at 0, rises, and ends at the token count;
  - docs.parquet: one row per document, doc_id unique and not null, n_tokens = the document's length in the index;
  - manifest: schema_version shard-v1, token_dtype uint32, shard_id and the three file names (the last part of each
    *_uri, which may be a full store path) match the files; payload,
    index and docs sha256, doc_count, token_count, eos_token_id and tokenizer_sha256 match;
  - every token id is below the vocab size (131,072 for p1536 and C3);
  - every document ends with EOS, and no special id occurs inside a document, EOS included. Special ids are the
    tokenizer's added tokens marked special (p1536 and C3 have 9 below 130,725, e.g. 36 <|end_of_text|> and 129994
    <|im_start|>)
    plus 130,725 to the end of the vocab: the same set shard_writer.py refuses.
With --check-text <clean.parquet> (the run_clean.py output one shard was written from; one shard per run), each decoded
document must equal the tokenizer-normalized source text of the same doc_id: a round-trip test of the decoder.

In a folder, a .bin counts as a shard when any of its .idx.npy, .docs.parquet or .json is next to it; a shard with a
file missing (e.g. an incomplete download) fails. A .bin with none of them (e.g. a model file) is listed and ignored.
The printed summary and the output's columns name the shard's payload_sha256, dataset_version and split, so the result
can be tied to the exact shard bytes. Memory: about 20 bytes per token at peak (measured 1.8 GB for a 67M-token shard),
fine for the 2^26-token shards of the format; a single oversized document in its own shard needs memory in proportion.

The output holds document text. Do not commit it or paste it anywhere (pr-guard refuses .parquet anyway); the report
gives only IDs, items, coverage and offsets. Needs numpy, pyarrow and tokenizers (no torch).
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path, PurePosixPath

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from tokenizers import Tokenizer

# p1536: Gate 3 freeze (TSAI notice, 15 Nov; #414). C3: earlier freeze (G3, #340); Data A's sample shard #373 uses it.
P1536_SHA256 = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
C3_SHA256 = "15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3"
FROZEN_TOKENIZERS = {P1536_SHA256: "p1536", C3_SHA256: "C3"}
VOCAB = 131_072  # both frozen tokenizers
MAGIC, VERSION, HEADER_BYTES = 20261025, 2, 1024
EOS_ID, EOS = 130_822, "<|endoftext|>"
SPECIAL_FROM = 130_725  # G3: named specials and reserved slots run from here to the end of the vocab
BATCH = 256


class ShardError(ValueError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def vocab_end(tok):
    """Highest token id + 1 (a vocab may have gaps)."""
    return max(tok.get_vocab(with_added_tokens=True).values()) + 1


def load_tokenizer(path, any_tokenizer=False):
    """(tokenizer, sha256). Only a frozen tokenizer (FROZEN_TOKENIZERS: p1536 or C3), unless any_tokenizer (tests)."""
    got = sha256(path)
    tok = Tokenizer.from_file(str(path))
    if not any_tokenizer:
        if got not in FROZEN_TOKENIZERS:
            frozen = ", ".join(f"{name} {sha[:12]}…" for sha, name in FROZEN_TOKENIZERS.items())
            raise ShardError(f"{path}: sha256 {got} is not a frozen tokenizer ({frozen})")
        if vocab_end(tok) != VOCAB or tok.id_to_token(EOS_ID) != EOS:
            raise ShardError(f"{path}: frozen {FROZEN_TOKENIZERS[got]} sha256 but vocab {vocab_end(tok)} or EOS "
                             f"{tok.id_to_token(EOS_ID)!r} is wrong")
    return tok, got


def special_ids(tok, special_from=None):
    """Sorted int array: added tokens marked special, plus special_from to the end of the vocab (as shard_writer.py)."""
    special_from = SPECIAL_FROM if special_from is None else special_from
    ids = {i for i, t in tok.get_added_tokens_decoder().items() if t.special} | set(range(special_from, vocab_end(tok)))
    return np.array(sorted(ids), dtype=np.int64)


def shard_files(bin_path):
    bin_path = Path(bin_path)
    stem = bin_path.name[: -len(".bin")]
    base = bin_path.with_name(stem)
    return {"bin": bin_path, "idx": Path(f"{base}.idx.npy"), "docs": Path(f"{base}.docs.parquet"),
            "manifest": Path(f"{base}.json"), "shard_id": stem}


def read_shard(bin_path, tokenizer_sha, specials, vocab, eos_id=None):
    """Check one shard (see the module docstring). specials: special_ids(tok), EOS included; vocab: vocab_end(tok).
    Return (shard_id, tokens, starts, doc_ids)."""
    eos_id = EOS_ID if eos_id is None else eos_id
    f = shard_files(bin_path)
    for key in ("bin", "idx", "docs", "manifest"):
        if not f[key].exists():
            raise ShardError(f"{f['shard_id']}: missing {f[key].name}")
    m = json.loads(f["manifest"].read_text(encoding="utf-8"))
    if not isinstance(m, dict):
        raise ShardError(f"{f['manifest'].name}: the manifest is not a JSON object")

    header = np.fromfile(f["bin"], dtype="<i4", count=256)
    if len(header) != 256 or header[0] != MAGIC or header[1] != VERSION or header[2] <= 0:
        raise ShardError(f"{f['bin'].name}: bad header (want magic {MAGIC}, version {VERSION})")
    n_tok = int(header[2])
    size = f["bin"].stat().st_size
    if size != HEADER_BYTES + 4 * n_tok:
        raise ShardError(f"{f['bin'].name}: size {size}, header says {HEADER_BYTES + 4 * n_tok}")
    tokens = np.fromfile(f["bin"], dtype="<u4", offset=HEADER_BYTES)

    starts = np.load(f["idx"], allow_pickle=False)
    if starts.dtype != np.int64 or starts.ndim != 1 or len(starts) < 2:
        raise ShardError(f"{f['idx'].name}: want a 1-D int64 array of doc starts plus the token count")
    if starts[0] != 0 or starts[-1] != n_tok or np.any(np.diff(starts) <= 0):
        raise ShardError(f"{f['idx'].name}: starts must begin at 0, rise, and end at the token count {n_tok}")
    n_docs = len(starts) - 1

    docs = pq.read_table(f["docs"])
    for col in ("doc_id", "n_tokens"):
        if col not in docs.column_names:
            raise ShardError(f"{f['docs'].name}: no {col} column")
    doc_ids = docs.column("doc_id").to_pylist()
    if len(doc_ids) != n_docs:
        raise ShardError(f"{f['docs'].name}: {len(doc_ids)} rows, index has {n_docs} documents")
    if any(d is None or str(d) == "" for d in doc_ids):
        raise ShardError(f"{f['docs'].name}: a doc_id is null or empty")
    doc_ids = [str(d) for d in doc_ids]
    if len(set(doc_ids)) != n_docs:
        raise ShardError(f"{f['docs'].name}: doc_ids are not unique")
    lengths = [int(x) for x in np.diff(starts)]
    n_tokens = docs.column("n_tokens").to_pylist()
    for i, (a, b) in enumerate(zip(n_tokens, lengths)):
        if a != b:
            raise ShardError(f"{f['docs'].name}: row {i} ({doc_ids[i]}) n_tokens {a}, the index gives {b}")

    if m.get("shard_id") != f["shard_id"]:
        raise ShardError(f"{f['manifest'].name}: shard_id is {m.get('shard_id')!r}, the shard gives {f['shard_id']!r}")
    uris = (("payload_uri", f["bin"].name), ("index_uri", f["idx"].name), ("sample_metadata_uri", f["docs"].name))
    for key, name in uris:
        uri = m.get(key)
        if not isinstance(uri, str) or PurePosixPath(uri).name != name:  # a *_uri may be a full store path
            raise ShardError(f"{f['manifest'].name}: {key} is {uri!r}, the file is {name!r}")
    want = {"schema_version": "shard-v1", "token_dtype": "uint32", "shard_id": f["shard_id"], "payload_bytes": size,
            "payload_sha256": sha256(f["bin"]), "index_sha256": sha256(f["idx"]),
            "sample_metadata_sha256": sha256(f["docs"]), "doc_count": n_docs, "token_count": n_tok,
            "eos_token_id": eos_id, "tokenizer_sha256": tokenizer_sha}
    for key, value in want.items():
        if m.get(key) != value:
            raise ShardError(f"{f['manifest'].name}: {key} is {m.get(key)!r}, the shard gives {value!r}")

    if int(tokens.max()) >= vocab:
        pos = int(np.flatnonzero(tokens >= vocab)[0])
        raise ShardError(f"{f['shard_id']}: token id {int(tokens[pos])} at position {pos} "
                         f"is not below the vocab size {vocab}")
    ends = starts[1:] - 1
    if np.any(tokens[ends] != eos_id):
        bad = int(np.flatnonzero(tokens[ends] != eos_id)[0])
        raise ShardError(f"{f['shard_id']}: document {doc_ids[bad]} does not end with EOS {eos_id}")
    inner = np.ones(n_tok, dtype=bool)
    inner[ends] = False
    hit = inner & np.isin(tokens, specials)
    if np.any(hit):
        pos = int(np.flatnonzero(hit)[0])
        doc = int(np.searchsorted(starts, pos, side="right") - 1)
        raise ShardError(f"{f['shard_id']}: special id {int(tokens[pos])} inside document {doc_ids[doc]}")
    return f["shard_id"], tokens, starts, doc_ids, m


def decode_shard(bin_path, tok, tokenizer_sha, eos_id=None, special_from=None):
    """Return a pyarrow table: doc_id, text, shard_id, n_tokens (with the final EOS), payload_sha256,
    dataset_version, split."""
    eos_id = EOS_ID if eos_id is None else eos_id
    shard_id, tokens, starts, doc_ids, m = read_shard(bin_path, tokenizer_sha, special_ids(tok, special_from),
                                                      vocab_end(tok), eos_id)
    texts = []
    for i in range(0, len(doc_ids), BATCH):
        seqs = [tokens[starts[j]:starts[j + 1] - 1].tolist() for j in range(i, min(i + BATCH, len(doc_ids)))]
        texts.extend(tok.decode_batch(seqs, skip_special_tokens=False))
    n = len(doc_ids)
    return pa.table({"doc_id": doc_ids, "text": texts, "shard_id": [shard_id] * n,
                     "n_tokens": np.diff(starts).astype(np.int64),
                     "payload_sha256": [m["payload_sha256"]] * n,
                     "dataset_version": [str(m.get("dataset_version"))] * n, "split": [str(m.get("split"))] * n})


def check_text(table, clean_parquet, tok):
    """Round trip: each decoded doc equals the tokenizer-normalized source text. Return (checked, mismatches)."""
    src = pq.read_table(clean_parquet, columns=["doc_id", "text"])
    ids = [str(d) for d in src.column("doc_id").to_pylist()]
    if len(set(ids)) != len(ids):
        raise ShardError(f"{clean_parquet}: doc_ids are not unique")
    source = dict(zip(ids, src.column("text").to_pylist()))
    norm = tok.normalizer.normalize_str if tok.normalizer is not None else (lambda s: s)
    bad = []
    for doc_id, text in zip(table.column("doc_id").to_pylist(), table.column("text").to_pylist()):
        if doc_id not in source:
            bad.append((doc_id, "not in source"))
        elif text != norm(source[doc_id] or ""):
            bad.append((doc_id, "text differs"))
    return table.num_rows, bad


def find_shards(path):
    """(shards, ignored): in a folder, a .bin is a shard when its .idx.npy, .docs.parquet or .json is next to it."""
    path = Path(path)
    if path.is_dir():
        bins = sorted(path.rglob("*.bin"))
        is_shard = [any(shard_files(b)[k].exists() for k in ("idx", "docs", "manifest")) for b in bins]
        return [b for b, ok in zip(bins, is_shard) if ok], [b for b, ok in zip(bins, is_shard) if not ok]
    if path.suffix == ".bin":
        return [path], []
    raise ShardError(f"{path}: give a .bin file or a folder of shards")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("shards", help="a <shard_id>.bin file or a folder searched for *.bin")
    ap.add_argument("--tokenizer", type=Path, required=True,
                    help="a frozen tokenizer.json: p1536 (the first training shards) or C3 (the sample shard)")
    ap.add_argument("--out", type=Path, required=True,
                    help="folder for <shard_id>.text.parquet (holds text: never commit)")
    ap.add_argument("--check-text", type=Path, help="run_clean.py *_clean.parquet one shard came from: round-trip test")
    ap.add_argument("--any-tokenizer", action="store_true", help="tests only: accept a tokenizer that is not frozen")
    a = ap.parse_args(argv)

    try:
        tok, tok_sha = load_tokenizer(a.tokenizer, a.any_tokenizer)
        shards, ignored = find_shards(a.shards)
        a.out.mkdir(parents=True, exist_ok=True)
    except ShardError as e:
        print(f"decode_shard: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # missing or invalid tokenizer file, --out is a file, ...
        print(f"decode_shard: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    for b in ignored:
        print(f"decode_shard: ignoring {b} (no shard files next to it, so not a shard)", file=sys.stderr)
    if not shards:
        print(f"decode_shard: no shards under {a.shards}", file=sys.stderr)
        return 1
    if a.check_text and len(shards) > 1:
        print("decode_shard: --check-text takes one shard (the one the clean parquet was written into)",
              file=sys.stderr)
        return 1
    failed, seen = 0, set()
    for path in shards:
        shard_id = shard_files(path)["shard_id"]
        out = a.out / f"{shard_id}.text.parquet"
        try:
            if shard_id in seen:
                raise ShardError(f"{path}: shard_id {shard_id} appears twice under {a.shards}")
            seen.add(shard_id)
            out.unlink(missing_ok=True)  # never leave an old output next to a shard that now fails
            table = decode_shard(path, tok, tok_sha)
            summary = {"shard_id": shard_id, "payload_sha256": table.column("payload_sha256")[0].as_py(),
                       "dataset_version": table.column("dataset_version")[0].as_py(),
                       "split": table.column("split")[0].as_py(), "docs": table.num_rows,
                       "tokens": int(sum(table.column("n_tokens").to_pylist())),
                       "tokenizer": f"{FROZEN_TOKENIZERS.get(tok_sha, 'not frozen')} {tok_sha[:12]}"}
            if a.check_text:
                checked, bad = check_text(table, a.check_text, tok)
                summary["round_trip"] = f"{checked - len(bad)}/{checked} match"
                if bad:
                    raise ShardError(f"{path.name}: {len(bad)} of {checked} documents do not round-trip "
                                     f"(first: {', '.join(d for d, _ in bad[:5])})")
            tmp = out.with_name(out.name + ".tmp")
            pq.write_table(table, tmp)
            os.replace(tmp, out)
            summary["out"] = str(out)
            print(json.dumps(summary))
        except Exception as e:  # one bad shard (bad JSON, bad Parquet, failed check) must not stop the others
            failed += 1
            msg = str(e) if isinstance(e, ShardError) else f"{path}: {type(e).__name__}: {e}"
            print(f"decode_shard: {msg}", file=sys.stderr)
    print(f"decoded {len(shards) - failed} of {len(shards)} shard(s)", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
