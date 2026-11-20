"""Build H3 known translation pairs from raw ind-sa-fw2 documents (dedup v2 proposal, H3-e).

  python build_known_pairs.py --parts <raw part.parquet> [<part> ...] --out <dir> [--review 30] [--seed 1]

WHY
===
H3 (translations across languages, h3_design_v1.md) needs pairs that are known to be translations, so that an
encoder and its thresholds can be checked on real text before any hand review. ind-sa-fw2 pages often carry a Sanskrit
text with its Hindi or English rendering in the same document. Data B's cleaning rule DB-H3-001 (medicine_indic.md,
section 238; author dattatreyamanjunath, PR #45) finds those translation lines and deletes them. Run on the RAW text
(before cleaning), the same test splits a document into its Sanskrit lines and its translation lines: two halves that
are, mostly, the same content in two languages.

HOW
===
- Each line of a raw document is classed with DB-H3-001's own test (`_translation`, copied unchanged below):
  translation (Hindi by function words, or Latin script without IAST marks) or not.
- Sanskrit half: the lines that are not translations, are at least 25 characters, and are mostly Devanagari.
- Translation half: the translation lines; its language is `en` when most letters are Latin, else `hi`.
- A document becomes a pair when both halves have at least MIN_LINES lines and MIN_CHARS characters (the minimums
  h3_design_v1.md uses for a document: 200 characters, 3 sentences).

These pairs are "same document, two languages", and on inspection many are NOT translations: a Sanskrit news article
with an embedded English tweet, a story with an English blurb, Hindi commentary. So each pair gets a kind:
  interleaved   at least half of the translation lines directly follow a Sanskrit line (verse, then its rendering):
                the candidate translations. Their (Sanskrit block, translation line) pairs are counted as line pairs.
  block         the translation lines form a block of their own: same-topic pairs, the hard negatives H3 must keep.
  not_sanskrit  the "Sanskrit" half has Hindi function words: it is Hindi, so the pair is not Sanskrit-to-X. The review
sheet (random pairs, side by side) is for a human to check how many are real translations before the pairs are trusted.

OUTPUT (all under --out, which must not be inside the repo: it holds document text)
======
  known_pairs.parquet   doc_id, split, part, row_in_part, url, tr_lang, n_sa, n_tr, sa_chars, tr_chars, sa_text, tr_text
  review.md             --review random pairs, both halves side by side, for a human reader
  summary.json          counts only (no text): documents read, pairs by tr_lang, line and character quantiles
"""
import sys
sys.dont_write_bytecode = True

import argparse, json, random, re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# ---- DB-H3-001, unchanged (teams/02-data-b/indic_rules/medicine_indic.md, section 238) --------------------------------
_HIN = set("है हैं था थे थी में और नहीं लिए गया गई हुआ होता होती करने किया करें ने को से का की के भी यह वह कि जो आप हम साथ वाले रहे रही".split())
_ANCHOR = set("है हैं था थे थी में और नहीं लिए गया गई हुआ होता होती करने किया करें ने साथ वाले रहे रही".split())


def _translation(line):
    letters = [c for c in line if c.isalpha()]
    if len(line.strip()) < 25 or len(letters) < 10:
        return False
    lat = sum(1 for c in letters if c.isascii() or 0xC0 <= ord(c) <= 0x24F or 0x1E00 <= ord(c) <= 0x1EFF)
    if lat / len(letters) > 0.6:
        return not re.search(r"[āīūṛṝḷṃḥṅñṭḍṇśṣ]", line)
    w = re.findall("[ऀ-ॿ]+", line)
    h = sum(1 for x in w if x in _HIN)
    a = sum(1 for x in w if x in _ANCHOR)
    return a >= 1 and h >= 2 and h / max(1, len(w)) >= 0.15
# ---- end of DB-H3-001 -------------------------------------------------------------------------------------------------

MIN_LINES = 3
INTERLEAVED = 0.5        # at least half of the translation lines directly follow a Sanskrit line
SANSKRIT_HINDI_MAX = 0.05  # above this share of Hindi function words, the "Sanskrit" half is really Hindi
MIN_CHARS = 200
MIN_SA_LINE = 25          # same floor DB-H3-001 uses for a translation line
DEVANAGARI_SHARE = 0.6    # a Sanskrit line is mostly Devanagari letters


def _is_deva(c):
    return 0x0900 <= ord(c) <= 0x097F


def _latin_share(text):
    letters = [c for c in text if c.isalpha()]
    return sum(1 for c in letters if c.isascii()) / max(1, len(letters))


def split_doc(text):
    """(sanskrit_lines, translation_lines, labels): labels is the line sequence as 'S' (Sanskrit) / 'T' (translation),
    other lines left out."""
    sa, tr, labels = [], [], []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if _translation(line):
            tr.append(s); labels.append("T")
            continue
        letters = [c for c in s if c.isalpha()]
        if len(s) >= MIN_SA_LINE and letters and sum(map(_is_deva, letters)) / len(letters) >= DEVANAGARI_SHARE:
            sa.append(s); labels.append("S")
    return sa, tr, labels


def interleave_share(labels):
    """Share of translation lines that directly follow a Sanskrit line: high when every verse is followed by its
    rendering (Gita, stotra pages), low when the translation lines form one block (an embedded tweet, a blurb)."""
    t = labels.count("T")
    return sum(1 for a, b in zip(labels, labels[1:]) if a == "S" and b == "T") / t if t else 0.0


def hindi_share(lines):
    """Share of Devanagari words that are Hindi function words (DB-H3-001's _HIN list): near 0 for Sanskrit."""
    w = [x for l in lines for x in re.findall("[ऀ-ॿ]+", l)]
    return sum(1 for x in w if x in _HIN) / max(1, len(w))


def line_pairs(text):
    """(sanskrit block, translation line) for each translation line that directly follows Sanskrit lines."""
    out, block = [], []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if _translation(line):
            if block:
                out.append((" ".join(block), s))
            block = []
            continue
        letters = [c for c in s if c.isalpha()]
        if len(s) >= MIN_SA_LINE and letters and sum(map(_is_deva, letters)) / len(letters) >= DEVANAGARI_SHARE:
            block.append(s)
    return out


def quantiles(xs):
    if not xs:
        return {}
    xs = sorted(xs)
    q = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]
    return {"min": xs[0], "p25": q(0.25), "median": q(0.5), "p75": q(0.75), "max": xs[-1]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parts", nargs="+", type=Path, required=True, help="raw ind-sa-fw2 Parquet parts")
    ap.add_argument("--out", type=Path, required=True, help="output folder (holds text: keep it out of the repo)")
    ap.add_argument("--review", type=int, default=30, help="pairs on the review sheet (default 30)")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    rows, read, with_tr = [], 0, 0
    for part in a.parts:
        t = pq.read_table(part, columns=["doc_id", "text", "url", "pack_id"])
        split = "heldout" if "heldout" in part.as_posix().lower() else "train"
        for i, (doc_id, text, url, pack) in enumerate(zip(*(t[c].to_pylist() for c in ("doc_id", "text", "url", "pack_id")))):
            if pack != "ind-sa-fw2":
                continue
            read += 1
            sa, tr, labels = split_doc(text or "")
            with_tr += bool(tr)
            sa_text, tr_text = "\n".join(sa), "\n".join(tr)
            if len(sa) < MIN_LINES or len(tr) < MIN_LINES or len(sa_text) < MIN_CHARS or len(tr_text) < MIN_CHARS:
                continue
            share, hs = interleave_share(labels), hindi_share(sa)
            kind = ("not_sanskrit" if hs > SANSKRIT_HINDI_MAX else "interleaved" if share >= INTERLEAVED else "block")
            rows.append({"doc_id": doc_id, "split": split, "part": part.name, "row_in_part": i, "url": url or "",
                         "kind": kind, "interleave": round(share, 3), "sa_hindi_share": round(hs, 4),
                         "line_pairs": len(line_pairs(text)) if kind == "interleaved" else 0,
                         "tr_lang": "en" if _latin_share(tr_text) > 0.6 else "hi",
                         "n_sa": len(sa), "n_tr": len(tr), "sa_chars": len(sa_text), "tr_chars": len(tr_text),
                         "sa_text": sa_text, "tr_text": tr_text})

    pq.write_table(pa.Table.from_pylist(rows) if rows else pa.table({"doc_id": pa.array([], pa.string())}),
                   a.out / "known_pairs.parquet")

    rnd = random.Random(a.seed)
    inter = [r for r in rows if r["kind"] == "interleaved"]
    sample = rnd.sample(inter, min(a.review, len(inter)))
    with open(a.out / "review.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("# H3 known pairs: review sheet (interleaved pairs)\n\nFor each pair: is the second half a translation of the first? "
                "Write yes, partly (commentary, summary, only some lines), or no.\n\n")
        for n, r in enumerate(sample, 1):
            f.write(f"## {n}. `{r['doc_id']}` ({r['tr_lang']}, {r['n_sa']} / {r['n_tr']} lines)\n\nAnswer: \n\n"
                    f"**Sanskrit lines**\n\n```\n{r['sa_text'][:1500]}\n```\n\n**Translation lines**\n\n```\n{r['tr_text'][:1500]}\n```\n\n")

    summary = {"documents_read": read, "documents_with_any_translation_line": with_tr, "pairs": len(rows),
               "pairs_by_tr_lang": {k: sum(r["tr_lang"] == k for r in rows) for k in ("hi", "en")},
               "pairs_by_kind": {k: {lang: sum(r["kind"] == k and r["tr_lang"] == lang for r in rows) for lang in ("hi", "en")}
                                 for k in ("interleaved", "block", "not_sanskrit")},
               "interleaved_line_pairs": sum(r["line_pairs"] for r in rows),
               "pairs_by_split": {k: sum(r["split"] == k for r in rows) for k in ("train", "heldout")},
               "sanskrit_lines": quantiles([r["n_sa"] for r in rows]), "translation_lines": quantiles([r["n_tr"] for r in rows]),
               "sanskrit_chars": quantiles([r["sa_chars"] for r in rows]), "translation_chars": quantiles([r["tr_chars"] for r in rows]),
               "settings": {"interleaved": INTERLEAVED, "sanskrit_hindi_max": SANSKRIT_HINDI_MAX, "min_lines": MIN_LINES, "min_chars": MIN_CHARS, "min_sa_line": MIN_SA_LINE,
                            "devanagari_share": DEVANAGARI_SHARE, "review": len(sample), "seed": a.seed},
               "inputs": [p.as_posix() for p in a.parts]}
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("documents_read", "pairs", "pairs_by_kind", "interleaved_line_pairs")}))


if __name__ == "__main__":
    main()
