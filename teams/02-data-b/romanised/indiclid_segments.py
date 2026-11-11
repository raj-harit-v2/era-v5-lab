#!/usr/bin/env python3
"""indiclid_segments.py - IndicLID (AI4Bharat, MIT licence) as a segment classifier for doc_detector.decide.

A segment is romanised Indic when IndicLID labels it as an Indian language in Latin letters (hin_Latn, tel_Latn, ...;
not eng_Latn, not other). Segments without a single Latin-letter word cannot add romanised words, so they are not sent
to IndicLID at all. IndicLID's own pipeline is used unchanged: a fastText model for native script, a fastText model for
Latin script, and its IndicBERT model for the Latin-script segments where the fastText score is below 0.6.

Labels are cached in indiclid/cache.json (segment text -> label), so the slow part runs once for the packs and gold.

Setup (not committed; see .gitignore)
  indiclid/IndicLID.py          from github.com/AI4Bharat/IndicLID, Inference/ai4bharat/IndicLID.py
  indiclid/models/indiclid-{ftn,ftr,bert}/   unzipped from the v1.0 release
  a Python 3.11 environment with torch 2.2.2, transformers 4.40.2, fasttext-wheel, numpy<2, pandas, pyarrow
Usage
  python indiclid_segments.py --packs-dir packs      fills the cache for every pack document (gold documents included)
  from indiclid_segments import classifier; doc_detector.decide(text, classifier())
"""
import argparse
import json
import os
import sys
from pathlib import Path

import pyarrow.parquet as pq

from doc_detector import latin_words, segments

HERE = Path(__file__).resolve().parent
LID_DIR = HERE / "indiclid"
CACHE = LID_DIR / "cache.json"
BATCH = 32


def is_romanised(label):
    return label.endswith("_Latn") and label != "eng_Latn"


def load_cache():
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def label_all(texts, cache):
    """Label the segments that are not in the cache yet, with IndicLID, and save the cache."""
    todo = sorted({t for t in texts if t not in cache})
    if not todo:
        return cache
    sys.path.insert(0, str(LID_DIR))
    here = os.getcwd()
    os.chdir(LID_DIR)  # IndicLID.py opens its models with paths relative to its own folder
    try:
        from IndicLID import IndicLID
        lid = IndicLID(input_threshold=0.5, roman_lid_threshold=0.6)
        for i in range(0, len(todo), 2000):
            chunk = todo[i:i + 2000]
            for text, (_, label, _, _) in zip(chunk, lid.batch_predict(chunk, BATCH)):
                cache[text] = label
            print(f"  IndicLID: {min(i + 2000, len(todo))} of {len(todo)} segments", flush=True)
    finally:
        os.chdir(here)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return cache


def classifier(cache=None):
    """A classify(segments) -> [bool] function for doc_detector.decide, reading labels from the cache."""
    cache = load_cache() if cache is None else cache

    def classify(segs):
        return [bool(latin_words(s)) and is_romanised(cache.get(s, "")) for s in segs]
    return classify


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fill the IndicLID label cache for every pack document.")
    ap.add_argument("--packs-dir", default="packs", type=Path)
    a = ap.parse_args(argv)
    texts = []
    for path in sorted(a.packs_dir.glob("ind-*.parquet")):
        for t in pq.read_table(path, columns=["text"]).column("text").to_pylist():
            texts += [s for s in segments(t or "") if latin_words(s)]
    print(f"{len(texts)} segments with Latin words, {len(set(texts))} different")
    cache = label_all(texts, load_cache())
    rom = sum(is_romanised(cache[t]) for t in set(texts))
    print(f"cache: {len(cache)} segments, {rom} of the pack segments labelled romanised Indic")


if __name__ == "__main__":
    main()
