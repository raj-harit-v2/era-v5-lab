#!/usr/bin/env python3
"""indic_audit.py - Gate 3 check of the Indic shards: drop rate per language, ZWJ/ZWNJ and visarga before and after.

Week 3, tasks 4 and 6 of the Data B work order. For each Indic pack it compares the raw pack (before cleaning) with the
token shards TSAI returns (after cleaning and tokenizing; `teams/01-data-a/shards/shard_format_v1.md`):

  dropped     raw documents with no row in any shard of the pack (cleaning or dedup removed them)
  joiners     for every kept document, the ZWJ (U+200D) and ZWNJ (U+200C) counts of the raw text and of the shard
              text (decoded with the frozen tokenizer). They must match. The one allowed change is the tokenizer's own
              normalizer, which folds Malayalam old-style chillu (consonant + virama + ZWJ) into the atomic chillu.
  where       for each flagged document: "cut text" when the shard text is one unbroken piece of the raw text, so the
              joiners went out with text that cleaning removed; "kept text" when the text that stayed was changed.
              Gate 3 needs 0 documents in kept text.
  visarga     the visarga counts of the raw and shard text, and the visargas that cleaning turned into ':' or deleted
              inside a word it kept (Data A found visarga -> ':' in the v0-clean sample, #566). Gate 3 needs 0.

Only IDs and counts are written, never document text.

Usage
  python indic_audit.py --packs-dir packs --shards-dir shards --tokenizer tokenizer/tokenizer.json \
      --tokenizer-sha256 <frozen sha256> --out audit_v1.csv --flagged-out audit_v1_flagged.csv

  packs/<pack_id>_part-NNNNN.parquet              the raw sample parts the shards were made from (doc_id, text);
                                                  <pack_id>.parquet also works
  shards/<pack_id>/<split>/<shard_id>.bin         with .idx.npy and .docs.parquet next to it

Speed: shards are read with numpy, decoded with the tokenizer's batch decode (Rust) and counted with pyarrow compute
kernels. There is no Python loop over tokens.
"""
import argparse
import csv
import hashlib
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from tokenizers import Tokenizer

ZWJ, ZWNJ = "\u200d", "\u200c"
# The tokenizer normalizer replaces each of these with one atomic chillu (U+0D7A to U+0D7F), so one ZWJ goes away.
OLD_CHILLU = ["ണ്\u200d", "ന്\u200d", "ര്\u200d",
              "ല്\u200d", "ള്\u200d", "ക്\u200d"]
OLD_CHILLU_RE = "|".join(OLD_CHILLU)                   # one regex pass instead of six substring passes
# The visarga of each script; for Tamil the aytham U+0B83 (Unicode calls it TAMIL SIGN VISARGA).
VISARGA = {"hi": "\u0903", "mr": "\u0903", "sa": "\u0903", "bn": "\u0983", "gu": "\u0a83", "or": "\u0b03",
           "ta": "\u0b83", "te": "\u0c03", "kn": "\u0c83", "ml": "\u0d03"}
MAGIC, VERSION, HEADER_BYTES, EOS_ID = 20261025, 2, 1024, 130822


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count(texts, s):
    """How many times s occurs in each text (pyarrow kernel, one int per document)."""
    return pc.count_substring(texts, s)


def joiners_changed(raw, shard):
    """True for each document whose ZWJ or ZWNJ count changed between the raw text and the shard text.

    raw, shard: pyarrow string arrays of the same length, one row per kept document, in the same order.
    Allowed: the normalizer folds each OLD_CHILLU sequence into one atomic chillu, so the shard has one ZWJ fewer for
    each OLD_CHILLU found in the raw text. Any other difference in ZWJ or ZWNJ counts is a change.
    Returns the mask and the four counts, so each text is scanned once per character (five passes in all).
    Uses pc kernels only: no Python loop over documents or characters.
    """
    n = {"zwj_raw": count(raw, ZWJ), "zwj_shard": count(shard, ZWJ),
         "zwnj_raw": count(raw, ZWNJ), "zwnj_shard": count(shard, ZWNJ)}
    chillu = pc.count_substring_regex(raw, OLD_CHILLU_RE)
    zwj_expected = pc.subtract(n["zwj_raw"], chillu)       # the normalizer removes one ZWJ per old chillu
    zwj_changed = pc.not_equal(n["zwj_shard"], zwj_expected)
    zwnj_changed = pc.not_equal(n["zwnj_shard"], n["zwnj_raw"])
    return pc.or_(zwj_changed, zwnj_changed), n


def where_changed(raw, shard, tok):
    """For one flagged document: 'cut text' when the shard text is one unbroken piece of the raw text (after the
    tokenizer normalizer), so every missing joiner was in text that cleaning removed with it; otherwise 'kept text',
    and the document needs a reader. Called only for flagged documents."""
    normalized = tok.normalizer.normalize_str(raw) if tok.normalizer else raw
    return "cut text" if shard in normalized else "kept text"


def visarga_edited(raw, shard, v, normalize=lambda t: t):
    """Visargas that cleaning turned into ':' or deleted inside a word that it kept.

    Only documents whose shard text has fewer visargas than the raw text are read. In each, a word with a visarga
    counts as edited when the shard has more copies of that word written with ':' or with no visarga than the raw text
    has. A visarga that went out with text cleaning removed (a line, a sentence, markup) leaves no such word, so it is
    not counted. Returns (documents that lost visargas, words edited). The loop runs over these documents only.
    """
    lost = pc.greater(count(raw, v), count(shard, v))
    edited = 0
    for r, s in zip(pc.filter(raw, lost).to_pylist(), pc.filter(shard, lost).to_pylist()):
        raw_words, shard_words = Counter(normalize(r).split()), Counter(s.split())
        variants = {w.replace(v, alt) for w in raw_words if v in w for alt in (":", "")}
        edited += sum(max(0, shard_words[w] - raw_words[w]) for w in variants)
    return int(pc.sum(lost.cast(pa.int64())).as_py() or 0), edited


def read_shard(bin_path, tok, eos_id=EOS_ID):
    """doc_ids and decoded texts of one shard, in shard order. Checks the header, the index and the EOS ids."""
    head = np.fromfile(bin_path, dtype="<i4", count=HEADER_BYTES // 4)
    if head[0] != MAGIC or head[1] != VERSION:
        raise SystemExit(f"{bin_path}: not a shard-v1 file (magic {head[0]}, version {head[1]})")
    tokens = np.fromfile(bin_path, dtype="<u4", offset=HEADER_BYTES)
    if len(tokens) != head[2]:
        raise SystemExit(f"{bin_path}: header says {head[2]} tokens, file has {len(tokens)}")
    stem = str(bin_path)[: -len(".bin")]
    idx = np.load(stem + ".idx.npy")
    doc_ids = pq.read_table(stem + ".docs.parquet", columns=["doc_id"]).column("doc_id").combine_chunks()
    if len(idx) != len(doc_ids) + 1 or idx[-1] != len(tokens):
        raise SystemExit(f"{bin_path}: index does not match the documents or the token count")
    if len(doc_ids) and not (tokens[idx[1:] - 1] == eos_id).all():
        raise SystemExit(f"{bin_path}: a document does not end with EOS id {eos_id}")
    docs = np.split(tokens, idx[1:-1])                      # views, one per document, each ending in EOS
    texts = tok.decode_batch([d[:-1].tolist() for d in docs], skip_special_tokens=False)
    return doc_ids, pa.array(texts, pa.string())


def pack_of(path):
    """ind-bn-fw2_part-00000.parquet -> ind-bn-fw2 (a raw sample part); ind-bn-fw2.parquet -> ind-bn-fw2."""
    return Path(path).stem.split("_part")[0]


def audit_pack(raw_paths, shard_paths, tok, eos_id=EOS_ID):
    """One summary row for the pack (all its raw parts), and the flagged documents: (pack_id, doc_id, where)."""
    raw = pa.concat_tables([pq.read_table(p, columns=["doc_id", "text"]) for p in raw_paths])
    if shard_paths:
        parts = [read_shard(p, tok, eos_id) for p in shard_paths]
        shard = pa.table({"doc_id": pa.concat_arrays([p[0] for p in parts]),
                          "shard_text": pa.concat_arrays([p[1] for p in parts])})
    else:
        shard = pa.table({"doc_id": pa.array([], pa.string()), "shard_text": pa.array([], pa.string())})
    kept = raw.join(shard, "doc_id", join_type="inner")
    raw_text, shard_text = kept.column("text").combine_chunks(), kept.column("shard_text").combine_chunks()
    changed, n = joiners_changed(raw_text, shard_text)
    total = lambda a: int(pc.sum(a).as_py() or 0)
    pack_id = pack_of(raw_paths[0])
    visarga = VISARGA[pack_id.split("-")[1]]
    docs_visarga_lost, visarga_edits = visarga_edited(
        raw_text, shard_text, visarga, tok.normalizer.normalize_str if tok.normalizer else (lambda t: t))
    flagged = sorted((pack_id, d, where_changed(r, s, tok)) for d, r, s in zip(   # sorted: join order varies
        pc.filter(kept.column("doc_id"), changed).to_pylist(),
        pc.filter(raw_text, changed).to_pylist(), pc.filter(shard_text, changed).to_pylist()))
    row = {
        "pack_id": pack_id, "lang": pack_id.split("-")[1], "shards": len(shard_paths),
        "docs_raw": raw.num_rows, "docs_kept": kept.num_rows, "docs_dropped": raw.num_rows - kept.num_rows,
        **{k: total(v) for k, v in n.items()},
        "docs_joiners_changed": len(flagged),
        "docs_joiners_changed_in_kept_text": sum(f[2] == "kept text" for f in flagged),
        "visarga_raw": total(count(raw_text, visarga)), "visarga_shard": total(count(shard_text, visarga)),
        "docs_visarga_lost": docs_visarga_lost, "visarga_words_edited_in_kept_text": visarga_edits,
    }
    return row, flagged


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--packs-dir", required=True)
    ap.add_argument("--shards-dir", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--tokenizer-sha256", required=True, help="the frozen sha256; the script stops on a mismatch")
    ap.add_argument("--out", required=True)
    ap.add_argument("--flagged-out", required=True)
    a = ap.parse_args()
    got = sha256(a.tokenizer)
    if got != a.tokenizer_sha256:
        raise SystemExit(f"tokenizer sha256 {got} is not {a.tokenizer_sha256}")
    tok = Tokenizer.from_file(a.tokenizer)
    start = time.time()
    rows, flagged = [], []
    packs = {}
    for part in sorted(Path(a.packs_dir).glob("ind-*.parquet")):
        packs.setdefault(pack_of(part), []).append(part)
    for pack_id, parts in sorted(packs.items()):
        shards = sorted((Path(a.shards_dir) / pack_id).glob("*/*.bin"))
        row, f = audit_pack(parts, shards, tok)
        rows.append(row)
        flagged += f
    for r in rows:
        r["drop_rate"] = f"{r['docs_dropped'] / r['docs_raw']:.2%}" if r["shards"] else "no shard"
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(a.flagged_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pack_id", "doc_id", "where"])
        w.writerows(flagged)
    print(f"tokenizer sha256 {got}")
    print(" | ".join(rows[0]))
    for r in rows:
        print(" | ".join(str(v) for v in r.values()))
    in_kept = sum(f[2] == "kept text" for f in flagged)
    print(f"documents with a ZWJ/ZWNJ change: {len(flagged)} ({len(flagged) - in_kept} in cut text, {in_kept} in kept "
          f"text); documents that lost visargas: {sum(r['docs_visarga_lost'] for r in rows)}, visarga words edited in "
          f"kept text: {sum(r['visarga_words_edited_in_kept_text'] for r in rows)}; wall time {time.time() - start:.1f} s")


if __name__ == "__main__":
    main()
