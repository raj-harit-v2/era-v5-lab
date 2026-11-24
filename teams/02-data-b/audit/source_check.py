"""source_check.py - is a reader's damage row also in the raw text (source), or did cleaning make it?

For every G1-G4 row in the given reader or rotation files, compare the shard text (decoded with p1536 by
read_shard from indic_audit.py) with the document's raw sample-v0 text after p1536's own normalizer (NFC, plus the
folds NFC does not make, such as the Bengali nukta letters; with NFC alone, unchanged Bengali text looks changed):
  source  the document is unchanged by cleaning, or the 12 characters on each side of the row's offset are
          also in the raw text; for a cut start or end (the note says so, and the offset is within 50 characters
          of the start or the end), the raw text starts or ends the same way
  CHECK   none of these: read the row by hand
Day files have a shard column. Rotation files have none: give the shard after a colon, FILE:SHARD.
Prints counts per file, the rows to check by hand and the wall time. IDs, codes and offsets only.

  python -I source_check.py --shards DIR --raw DIR --tokenizer p1536_tokenizer.json \
      day_D4_ta.md rotation_uz9ai.md:ind-kn-sangraha-v-train-000000

--shards holds <shard>.bin (or TSAI's <pack>/train/<shard>.bin); --raw holds <pack>_part-00000.parquet, named as
in raw_parts_SHA256SUMS.
"""
import argparse
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq
from tokenizers import Tokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indic_audit import read_shard  # noqa: E402

DAY_ROW = re.compile(r"^\|\s*`?([0-9a-f]{16})`?\s*\|\s*`?([\w-]+)`?\s*\|\s*(?:ok|finding)\s*\|\s*(G[1-4])\s*\|"
                     r"\s*(\d*)\s*\|([^|]*)\|", re.M)
ROTATION_ROW = re.compile(r"^\|\s*`?([0-9a-f]{16})`?\s*\|\s*(G[1-4])\s*\|\s*(\d+)\s*\|[^|]*\|([^|]*)\|", re.M)
START = re.compile(r"start|opening|begin", re.I)
END = re.compile(r"\bend\b|ends|stops|breaks off", re.I)
EDGE = 50  # a cut start or end is reported within this many characters of the text's start or end


def rows(path, shard):
    """(doc_id, shard, code, offset, note) for each G1-G4 row of one file."""
    md = Path(path).read_text(encoding="utf-8")
    if shard:
        return [(d, shard, code, int(off), note) for d, code, off, note in ROTATION_ROW.findall(md)]
    return [(d, sh, code, int(off or 0), note) for d, sh, code, off, note in DAY_ROW.findall(md)]


def tag(shard_text, raw_text, offset, note):
    if shard_text == raw_text:
        return "source"
    if START.search(note) and offset < EDGE:
        return "source" if raw_text[:40] == shard_text[:40] else "CHECK"
    if END.search(note) and len(shard_text) - offset < EDGE:
        return "source" if raw_text.rstrip()[-40:] == shard_text.rstrip()[-40:] else "CHECK"
    window = shard_text[max(0, offset - 12): offset + 12]
    return "source" if window and window in raw_text else "CHECK"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--shards", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("files", nargs="+", help="reader files; rotation files as FILE:SHARD")
    a = ap.parse_args()
    t0 = time.time()
    tok = Tokenizer.from_file(a.tokenizer)
    normalize = tok.normalizer.normalize_str if tok.normalizer else (lambda s: unicodedata.normalize("NFC", s))
    cache = {}

    def texts(shard):  # one read per shard: {doc_id: shard text}, {doc_id: raw text}
        if shard not in cache:
            pack = shard.rsplit("-train-", 1)[0]
            path = Path(a.shards, shard + ".bin")
            if not path.exists():
                path = Path(a.shards, pack, "train", shard + ".bin")
            ids, tx = read_shard(str(path), tok)
            raw = pq.read_table(Path(a.raw, pack + "_part-00000.parquet"), columns=["doc_id", "text"])
            cache[shard] = (dict(zip(ids.to_pylist(), tx.to_pylist())),
                            dict(zip(raw["doc_id"].to_pylist(), raw["text"].to_pylist())))
        return cache[shard]

    total, check = Counter(), []
    for arg in a.files:
        path, _, shard = arg.partition(":")
        counts = Counter()
        for doc_id, sh, code, offset, note in rows(path, shard):
            shard_texts, raw_texts = texts(sh)
            t = tag(shard_texts[doc_id], normalize(raw_texts[doc_id]), offset, note)
            counts[f"{code} {t}"] += 1
            if t == "CHECK":
                check.append(f"{Path(path).name} {doc_id} {code} {offset}")
        total.update(counts)
        print(Path(path).name, dict(sorted(counts.items())))
    print("all", dict(sorted(total.items())))
    print("rows to check by hand:", len(check))
    for row in check:
        print("  " + row)
    print(f"wall {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
