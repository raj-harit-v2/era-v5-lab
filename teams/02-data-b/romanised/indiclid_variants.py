#!/usr/bin/env python3
"""indiclid_variants.py - can IndicLID be tuned to beat the word list on the gold check?

eval_v2.py runs IndicLID as published. This script tries the two obvious fixes, at the contains level (the document
has at least one romanised segment, which is what readers marked as D2):
  minimum length   a segment counts only when it has at least N Latin-letter words (short names and datelines out)
  minimum score    a segment counts only when IndicLID's score for its label is at least S
  Latin words only IndicLID gets only the Latin-letter words of the segment, so a Hinglish line mixed with Devanagari
                   goes to its roman-script models instead of its native-script model
Each variant is scored like eval_v2.py: precision and recall on testset_100.csv (readers' and checked labels),
documents flagged in gold (every one is a false positive), and documents flagged in all pack documents.

IndicLID labels and scores are cached in indiclid/cache_scores.json ("S\t<segment>" and "L\t<Latin words>" -> [label,
score, model]); the first run labels about 29,000 inputs (a few minutes on CPU). Setup as in indiclid_segments.py.

Usage
  python indiclid_variants.py --testset testset_100.csv --checked checked_labels.csv --gold-dir ../gold \
                              --packs-dir packs --out eval_v2_indiclid_variants.md
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

import pyarrow.parquet as pq

import doc_detector as dd
from indiclid_segments import BATCH, LID_DIR, is_romanised

CACHE = LID_DIR / "cache_scores.json"


def fill_cache(inputs):
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = sorted(t for t in inputs if t not in cache)
    if todo:
        sys.path.insert(0, str(LID_DIR))
        here = os.getcwd()
        os.chdir(LID_DIR)  # IndicLID.py opens its models with paths relative to its own folder
        try:
            from IndicLID import IndicLID
            lid = IndicLID(input_threshold=0.5, roman_lid_threshold=0.6)
            for i in range(0, len(todo), 2000):
                chunk = todo[i:i + 2000]
                for key, (_, label, score, model) in zip(chunk, lid.batch_predict([k[2:] for k in chunk], BATCH)):
                    cache[key] = [label, float(score), model]
                print(f"  IndicLID: {min(i + 2000, len(todo))} of {len(todo)} inputs", flush=True)
        finally:
            os.chdir(here)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return cache


def main(argv=None):
    ap = argparse.ArgumentParser(description="IndicLID with length and score thresholds, against the word list.")
    ap.add_argument("--testset", default="testset_100.csv", type=Path)
    ap.add_argument("--checked", default="checked_labels.csv", type=Path)
    ap.add_argument("--gold-dir", default=Path(__file__).resolve().parent.parent / "gold", type=Path)
    ap.add_argument("--packs-dir", default="packs", type=Path)
    ap.add_argument("--out", default="eval_v2_indiclid_variants.md", type=Path)
    a = ap.parse_args(argv)

    docs = {}
    for path in sorted(a.packs_dir.glob("ind-*.parquet")):
        for d in pq.read_table(path, columns=["doc_id", "text"]).to_pylist():
            docs[(path.stem, d["doc_id"])] = [s for s in dd.segments(d["text"] or "") if dd.latin_words(s)]
    inputs = set()
    for segs in docs.values():
        for s in segs:
            inputs |= {"S\t" + s, "L\t" + " ".join(dd.latin_words(s))}
    cache = fill_cache(inputs)

    rows = list(csv.DictReader(open(a.testset, encoding="utf-8")))
    reader = {(r["pack"], r["doc_id"]): r["reader_label"] == "1" for r in rows}
    chk = {(r["pack"], r["doc_id"]): r["checked_label"] == "1"
           for r in csv.DictReader(open(a.checked, encoding="utf-8"))}
    checked = {k: chk.get(k, y) for k, y in reader.items()}
    gold = set()
    for path in a.gold_dir.glob("ind-*_gold.csv"):
        pack = path.name[:-len("_gold.csv")]
        gold |= {(pack, r["doc_id"]) for r in csv.DictReader(open(path, encoding="utf-8-sig"))}
    gold &= set(docs)

    def indiclid(latin_only, min_words, min_score):
        def clf(s):
            lw = dd.latin_words(s)
            if len(lw) < min_words:
                return False
            label, score, _ = cache[("L\t" + " ".join(lw)) if latin_only else ("S\t" + s)]
            return is_romanised(label) and score >= min_score
        return clf

    variants = [("word list", None, None, None, dd.wordlist_segment)]
    for latin_only in (False, True):
        for mw in (1, 3, 4):
            for ms in (0.0, 0.8, 0.9):
                variants.append(("IndicLID", "Latin words only" if latin_only else "whole segment", mw, ms,
                                 indiclid(latin_only, mw, ms)))

    def pr(flag, lab):
        tp = sum(flag[k] and y for k, y in lab.items())
        fp = sum(flag[k] and not y for k, y in lab.items())
        fn = sum(lab.values()) - tp
        return f"{tp / (tp + fp):.0%} / {tp / (tp + fn):.0%}" if tp + fp else "- / 0%"

    out = ["# IndicLID with length and score thresholds, against the word list", "",
           "Contains level (at least one romanised segment). Precision / recall on `testset_100.csv`; gold flagged = "
           f"false positives among the {len(gold)} gold documents; packs flagged = documents flagged among all "
           f"{len(docs)} pack documents (readers marked about 52 as D2).", "",
           "| tool | IndicLID input | min Latin words | min score | readers P / R | checked P / R | gold flagged "
           "| packs flagged |", "|---|---|---|---|---|---|---|---|"]
    for tool, mode, mw, ms, clf in variants:
        flag = {k: any(clf(s) for s in segs) for k, segs in docs.items()}
        out.append(f"| {tool} | {mode or '-'} | {mw or '-'} | {'-' if ms is None else ms} | {pr(flag, reader)} "
                   f"| {pr(flag, checked)} | {sum(flag[k] for k in gold)} | {sum(flag.values())} |")
    a.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
