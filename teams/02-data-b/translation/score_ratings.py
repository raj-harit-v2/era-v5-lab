#!/usr/bin/env python3
"""score_ratings.py - the two Gate 2 translation tables from the readers' rating sheets (standard library only).

Each reader rates alone in ratings/<lang>_<handle>.csv (doc_id, score 1-5; a blank score is not rated yet).
  Agreement (agreement_v1.md): for each language, the documents that two readers both rated. A language passes
  when there are at least 20 of them and the two scores are within 1 point on 80% or more (TSAI, G2 31 Oct).
  Quality (quality_v1.md): for each language, the mean score; a document rated by two readers counts once, with
  the mean of its two scores.

Usage:  python3 score_ratings.py RATINGS_DIR [--id-col doc_id] [--score-col score] [--md-out FILE]
Exit codes: 0 done, 2 could not run (no sheets, or a score that is not 1 to 5).
"""
import argparse
import csv
import sys
from itertools import combinations
from pathlib import Path

MIN_SHARED, PASS_SHARE = 20, 0.8


def read_sheets(folder, id_col, score_col):
    """{lang: {handle: {doc_id: score}}} from every <lang>_<handle>.csv in folder."""
    sheets, bad = {}, []
    for path in sorted(Path(folder).glob("*_*.csv")):
        lang, handle = path.stem.split("_", 1)
        scores = {}
        with open(path, encoding="utf-8-sig", newline="") as f:
            for k, row in enumerate(csv.DictReader(f), 2):
                doc, score = (row.get(id_col) or "").strip(), (row.get(score_col) or "").strip()
                if not doc or not score:
                    continue
                if score not in {"1", "2", "3", "4", "5"}:
                    bad.append(f"{path.name} line {k}: score {score!r} is not 1 to 5")
                    continue
                scores[doc] = int(score)
        sheets.setdefault(lang, {})[handle] = scores
    return sheets, bad


def agreement(sheets):
    rows = []
    for lang, readers in sorted(sheets.items()):
        for a, b in combinations(sorted(readers, key=str.casefold), 2):
            both = sorted(set(readers[a]) & set(readers[b]))
            if not both:
                continue
            within = sum(abs(readers[a][d] - readers[b][d]) <= 1 for d in both)
            share = within / len(both)
            result = "PASS" if len(both) >= MIN_SHARED and share >= PASS_SHARE else (
                f"too few shared documents ({len(both)} of {MIN_SHARED})" if len(both) < MIN_SHARED else "FAIL")
            rows.append((lang, a, b, len(both), within, share, result))
    return rows


def quality(sheets):
    rows = []
    for lang, readers in sorted(sheets.items()):
        per_doc = {}
        for scores in readers.values():
            for d, s in scores.items():
                per_doc.setdefault(d, []).append(s)
        if per_doc:
            means = [sum(v) / len(v) for v in per_doc.values()]
            rows.append((lang, len(readers), len(per_doc), sum(means) / len(means)))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ratings_dir", type=Path)
    ap.add_argument("--id-col", default="doc_id")
    ap.add_argument("--score-col", default="score")
    ap.add_argument("--md-out", type=Path, help="also write both tables to this markdown file")
    a = ap.parse_args(argv)
    sheets, bad = read_sheets(a.ratings_dir, a.id_col, a.score_col)
    if bad or not sheets:
        print("\n".join(bad) or f"no <lang>_<handle>.csv sheets in {a.ratings_dir}", file=sys.stderr)
        return 2
    lines = ["## Agreement (two readers, the same documents)", "",
             "| Language | Readers | Shared documents | Within 1 point | Result |", "|---|---|---|---|---|"]
    lines += [f"| {lang} | {x}, {y} | {n} | {w} ({share:.0%}) | {res} |" for lang, x, y, n, w, share, res in agreement(sheets)]
    lines += ["", "## Quality (mean score, 1 to 5)", "", "| Language | Readers | Documents rated | Mean score |", "|---|---|---|---|"]
    lines += [f"| {lang} | {r} | {n} | {m:.2f} |" for lang, r, n, m in quality(sheets)]
    text = "\n".join(lines) + "\n"
    print(text, end="")
    if a.md_out:
        a.md_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
