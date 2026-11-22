#!/usr/bin/env python3
"""
count_p1536.py
==============

Token counts of the frozen p1536 tokenizer on the text it was trained on, for G5's KAS unigram log-prior
(`--init logunigram`, PR #717). Real corpus-v1 counts can replace these later; these exist now.

The text, every file checked against its pinned sha256 before it is read:
  - Indic: the files train_bpe.py read for p1536 (`train/p1536_s0_manifest.json`): corpus60/<lang>.txt for the 11
    languages, except that Hi and Mr also read corpus_s0/<lang>.txt and Gu and Or read only corpus_s0/<lang>.txt
    (the `mix` entry).
  - English and code: usage/En.txt and usage/Code.txt (`train/heldout_manifest.json`), the text prune_o200k.py
    used to decide which o200k base tokens p1536 keeps.

Each file is encoded with p1536 exactly as a trainer would (normalizer included, add_special_tokens=False).
Files are split only after a newline that is followed by a non-space character, which no pre-tokenizer piece
crosses, so the ids equal those of encoding the whole file at once.

The counts are raw: no mix factor, no smoothing. Special tokens get no counts from text; the documents per file
are listed so a caller can add one eos (130822) per document, as Data A's shard writer does. The smoothing,
zero-count and special-token policy is G5's call (see README.md).

    python teams/03-tokenizer/counts/count_p1536.py --tokenizer release/tokenizer.json \
        --corpus60 inputs/corpus60 --corpus-s0 out/corpus_s0 --usage heldout/usage --out teams/03-tokenizer/counts
"""
import argparse
import hashlib
import json
import platform
import re
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent
P1536_SHA = "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
VOCAB = 131072
LANGS = ("Hi", "Bn", "Ta", "Te", "Kn", "Ml", "Mr", "Gu", "Pa", "Or", "As")
SPLIT = re.compile(r"(?<=\n)(?=\S)")
CHUNK = 1 << 20


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sources(args):
    """[(name, lang, path, sha256, docs)] in a fixed order."""
    manifest = json.loads((TEAM / "train/p1536_s0_manifest.json").read_text(encoding="utf-8"))
    heldout = json.loads((TEAM / "train/heldout_manifest.json").read_text(encoding="utf-8"))
    dirs = {"corpus60": Path(args.corpus60), "corpus_s0": Path(args.corpus_s0)}
    s0_docs = json.loads((dirs["corpus_s0"] / "corpus_manifest.json").read_text(encoding="utf-8"))
    out = []
    for lang in LANGS:
        units = manifest["mix"].get(lang) or [{"dir": "corpus60", "file": f"{lang}.txt",
                                               "sha256": manifest["corpus"][lang]["sha256"]}]
        for u in units:
            docs = manifest["corpus"][lang]["docs"] if u["dir"] == "corpus60" else s0_docs[lang].get("docs")
            out.append((f"{u['dir']}/{u['file']}", lang, dirs[u["dir"]] / u["file"], u["sha256"], docs))
    for lang in ("En", "Code"):
        f = heldout[lang]["files"][f"usage/{lang}.txt"]
        out.append((f"usage/{lang}.txt", lang, Path(args.usage) / f"{lang}.txt", f["sha256"], f["docs"]))
    return out


def chunks(text):
    buf, size = [], 0
    for piece in SPLIT.split(text):
        buf.append(piece)
        size += len(piece)
        if size >= CHUNK:
            yield "".join(buf)
            buf, size = [], 0
    if buf:
        yield "".join(buf)


def count(tok, path):
    counts = Counter()
    text = Path(path).read_text(encoding="utf-8")
    batch = list(chunks(text))
    for enc in tok.encode_batch(batch, add_special_tokens=False):
        counts.update(enc.ids)
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tokenizer", required=True, help=f"p1536 tokenizer.json (sha256 {P1536_SHA[:8]}…)")
    ap.add_argument("--corpus60", required=True)
    ap.add_argument("--corpus-s0", required=True, help="sample_to_corpus.py output (rebuild_cand.py out/corpus_s0)")
    ap.add_argument("--usage", required=True, help="fetch_heldout.py usage/ folder (En.txt, Code.txt)")
    ap.add_argument("--out", required=True, help="folder for p1536_counts.json and p1536_counts_by_source.json")
    args = ap.parse_args()
    import tokenizers
    from tokenizers import Tokenizer

    if sha256_file(args.tokenizer) != P1536_SHA:
        sys.exit(f"{args.tokenizer} is not p1536 ({P1536_SHA})")
    tok = Tokenizer.from_file(args.tokenizer)
    raw = json.loads(Path(args.tokenizer).read_text(encoding="utf-8"))
    specials = sorted(a["id"] for a in raw["added_tokens"] if a["special"])

    total = [0] * VOCAB
    by_source = {}
    t0 = time.time()
    for name, lang, path, digest, docs in sources(args):
        got = sha256_file(path)
        if got != digest:
            sys.exit(f"{name}: sha256 {got}, pinned {digest}")
        c = count(tok, path)
        for i, n in c.items():
            total[i] += n
        by_source[name] = {"lang": lang, "sha256": digest, "bytes": path.stat().st_size, "docs": docs,
                           "tokens": sum(c.values()), "distinct_ids": len(c),
                           "counts": {str(i): c[i] for i in sorted(c)}}
        print(f"{name}: {by_source[name]['tokens']:,} tokens, {len(c):,} distinct ids ({time.time() - t0:.0f}s)",
              flush=True)

    seen = sum(1 for n in total if n)
    out = {
        "_comment": "p1536 token counts on its tokenizer-training text, for G5's KAS unigram log-prior. Made by "
                    "count_p1536.py; see README.md. `total[i]` is the raw count of id i summed over all sources "
                    "(no mix factor, no smoothing, no eos). p1536_counts_by_source.json has each file's counts "
                    "(id -> count, non-zero only) so other weightings can be built.",
        "tokenizer_sha256": P1536_SHA,
        "vocab_size": VOCAB,
        "special_ids": specials,
        "eos_id": 130822,
        "summary": {"tokens": sum(total), "ids_seen": seen, "ids_zero": VOCAB - seen,
                    "special_ids_seen": sum(1 for i in specials if total[i]),
                    "docs": sum(s["docs"] or 0 for s in by_source.values())},
        "software": {"python": platform.python_version(), "tokenizers": tokenizers.__version__,
                     "count_p1536.py": sha256_file(__file__)},
        "sources": {k: {f: v for f, v in s.items() if f != "counts"} for k, s in by_source.items()},
        "total": total,
    }
    # Two files, each under pr-guard's 5 MB limit.
    folder = Path(args.out)
    (folder / "p1536_counts.json").write_text(json.dumps(out, separators=(",", ":")) + "\n", encoding="utf-8")
    (folder / "p1536_counts_by_source.json").write_text(
        json.dumps({"tokenizer_sha256": P1536_SHA, "by_source": {k: s["counts"] for k, s in by_source.items()}},
                   separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(out["summary"]), f"-> {folder} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
