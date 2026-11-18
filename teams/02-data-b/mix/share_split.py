#!/usr/bin/env python3
"""share_split.py - split the native Indic share of every batch across languages (mix/indic_share_v1.md).

Reads the manifests (<shard_id>.json) of the Indic token shards TSAI returned and adds up token_count per language.
Translated packs (sangraha-s, #212) are left out: translated text is 0% until TSAI decides it at Gate 3.
Split: each language with a shard gets --floor points of --total; the rest is shared in proportion to native tokens.
A language with no shard gets 0 and is listed, so its floor is added when its shard exists (rerun this script).
Only the manifests are read: no document text.

Usage
  python share_split.py --shards-dir shards --tokenizer-sha256 <frozen sha256> --total 8 --floor 0.3 \
      --out indic_share_v1.csv
  shards/<pack_id>/<split>/<shard_id>.json        one manifest per shard (shard_format_v1.md)
"""
import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path

LANGS = ["hi", "bn", "te", "kn", "ta", "mr", "gu", "sa", "ml", "or"]
TRANSLATED = "-sangraha-s"                     # pack_id ending of the translated packs (#212)


def split(tokens, total, floor):
    """Percent of every batch per language: floor for each language with tokens, the rest in proportion."""
    present = {lang: n for lang, n in tokens.items() if n}
    rest = total - floor * len(present)
    if rest < 0:
        raise SystemExit(f"floor {floor} x {len(present)} languages is more than the total {total}")
    all_tokens = sum(present.values())
    return {lang: (floor + rest * present[lang] / all_tokens if lang in present else 0.0) for lang in tokens}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shards-dir", required=True)
    ap.add_argument("--tokenizer-sha256", required=True, help="the frozen sha256; the script stops on a mismatch")
    ap.add_argument("--total", type=float, required=True, help="native Indic share of every batch, in percent")
    ap.add_argument("--floor", type=float, required=True, help="points of the total for each language with a shard")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    start = time.time()
    tokens, packs, left_out = dict.fromkeys(LANGS, 0), defaultdict(list), []
    for path in sorted(Path(a.shards_dir).glob("ind-*/*/*.json")):
        if path.name.endswith(".quality_report.json"):
            continue
        m = json.loads(path.read_text(encoding="utf-8"))
        if m["tokenizer_sha256"] != a.tokenizer_sha256:
            raise SystemExit(f"{path}: tokenizer {m['tokenizer_sha256']} is not {a.tokenizer_sha256}")
        if m["pack_id"].endswith(TRANSLATED):
            left_out.append((m["pack_id"], m["token_count"]))
            continue
        tokens[m["language"]] += m["token_count"]
        packs[m["language"]].append(m["pack_id"])
    shares = split(tokens, a.total, a.floor)
    native = sum(tokens.values())
    rows = [{"lang": lang, "packs": " ".join(sorted(packs[lang])) or "no shard", "native_tokens": tokens[lang],
             "share_of_native_tokens": f"{tokens[lang] / native:.2%}", "share_of_batch_pct": f"{shares[lang]:.2f}"}
            for lang in LANGS]
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(" | ".join(rows[0]))
    for r in rows:
        print(" | ".join(str(v) for v in r.values()))
    print(f"native tokens {native:,}; left out (translated): "
          + ", ".join(f"{p} {n:,}" for p, n in left_out) + f"; sum of shares {sum(shares.values()):.2f}")
    print(f"wall time {time.time() - start:.2f} s")


if __name__ == "__main__":
    main()
