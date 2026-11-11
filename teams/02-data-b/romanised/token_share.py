#!/usr/bin/env python3
"""token_share.py - romanised Indic share in tokens, per language, for the cap in romanised_policy_v1.md.

TSAI's rules (#213, part 2): the cap is measured in tokens, and a document counts as romanised when most of its words
are romanised (doc_detector.decide, word-list classifier, chosen in eval_v2.md).
Per language it reports
  cap share      tokens of the romanised documents / all tokens          (what the cap limits)
  segment share  tokens of romanised segments in any document / all tokens (for scale only: romanised headings and
                 comments inside native documents, which the cap does not touch)

The tokenizer is a stand-in until the project tokenizer is final: BrahmicTokenizer-131K, the baseline team
03-tokenizer measures its candidates against (github.com/theschoolofai/BrahmicTokenizer-131K, commit 7dfcf398,
tokenizer.json). Pass --tokenizer to use another tokenizer.json.

Usage
  python token_share.py --packs-dir packs --tokenizer tokenizer/tokenizer.json --out romanised_token_share_v1.csv
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from tokenizers import Tokenizer

import doc_detector


def main(argv=None):
    ap = argparse.ArgumentParser(description="Romanised Indic share in tokens, per language.")
    ap.add_argument("--packs-dir", default="packs", type=Path)
    ap.add_argument("--tokenizer", default="tokenizer/tokenizer.json", type=Path)
    ap.add_argument("--out", default="romanised_token_share_v1.csv", type=Path)
    a = ap.parse_args(argv)

    tok = Tokenizer.from_file(str(a.tokenizer))
    n = lambda texts: sum(len(e.ids) for e in tok.encode_batch(texts, add_special_tokens=False)) if texts else 0
    agg = defaultdict(lambda: defaultdict(int))
    top = []
    for path in sorted(a.packs_dir.glob("ind-*.parquet")):
        lang = path.stem.split("-")[1]
        docs = pq.read_table(path, columns=["doc_id", "text"]).to_pylist()
        texts = [d["text"] or "" for d in docs]
        doc_tokens = [len(e.ids) for e in tok.encode_batch(texts, add_special_tokens=False)]
        s = agg[lang]
        s["packs"] += 1
        for d, text, t in zip(docs, texts, doc_tokens):
            segs = doc_detector.segments(text)
            flagged = [g for g in segs if doc_detector.wordlist_segment(g) and doc_detector.latin_words(g)]
            dec = doc_detector.decide(text)
            s["docs"] += 1
            s["tokens"] += t
            s["seg_tokens"] += n(flagged)
            s["contains_docs"] += bool(flagged)
            if dec["romanised"]:
                s["rom_docs"] += 1
                s["rom_tokens"] += t
            top.append((dec["share"], path.stem, d["doc_id"]))

    fields = ["lang", "packs", "docs", "tokens", "romanised_docs", "romanised_doc_tokens", "cap_share",
              "docs_with_romanised_segments", "romanised_segment_tokens", "segment_share"]
    rows = []
    for lang in sorted(agg, key=lambda l: -agg[l]["seg_tokens"] / agg[l]["tokens"]) + ["all"]:
        s = agg[lang] if lang != "all" else {k: sum(agg[l][k] for l in agg) for k in
                                             ("packs", "docs", "tokens", "rom_docs", "rom_tokens", "contains_docs",
                                              "seg_tokens")}
        rows.append({"lang": lang, "packs": s["packs"], "docs": s["docs"], "tokens": s["tokens"],
                     "romanised_docs": s["rom_docs"], "romanised_doc_tokens": s["rom_tokens"],
                     "cap_share": f"{s['rom_tokens'] / s['tokens']:.4%}",
                     "docs_with_romanised_segments": s["contains_docs"], "romanised_segment_tokens": s["seg_tokens"],
                     "segment_share": f"{s['seg_tokens'] / s['tokens']:.4%}"})
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"tokenizer: {a.tokenizer}")
    print(" | ".join(fields))
    for r in rows:
        print(" | ".join(str(r[k]) for k in fields))
    print("highest romanised word share in any document:",
          ", ".join(f"{sh:.0%} {p} {d}" for sh, p, d in sorted(top, reverse=True)[:5]))


if __name__ == "__main__":
    main()
