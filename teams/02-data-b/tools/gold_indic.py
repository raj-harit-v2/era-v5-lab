#!/usr/bin/env python3
"""gold_indic.py - the Data B gold set: the documents that two readers marked clean.

The rule is the one in Data A's build_gold.py (DISEASES.md section 5). A document is gold when at least two
different readers marked it read=full, verdict=clean with no disease code, and no reader marked it fix or drop.
D3 (mixed language) is a label only: a clean row whose only code is D3 is a clean vote (TSAI, G1, 31 Oct).
What differs: it needs no GitHub token (you give it the sheets), a bad sheet is skipped and reported instead of
stopping the run, and it also writes one file for the whole language.

Usage
  python3 gold_indic.py --sheets SHEETS_DIR --out OUT_DIR --lang telugu [--packs ind-te-fw2 ind-te-sangraha-v]
  SHEETS_DIR/<pack_id>/<handle>.csv is one reader's labels.csv (fetch_sheets.py makes this layout).
  --packs defaults to every folder in SHEETS_DIR.
Writes in OUT_DIR: <pack_id>_gold.csv for each pack, <lang>_gold.csv for all of them (columns doc_id,reader_1,
reader_2: ids and GitHub handles only, never text) and gold_coverage.csv.
Exit codes: 0 done, 2 could not run.
"""
import argparse
import csv
import sys
from pathlib import Path

NEED = ("doc_id", "read", "verdict", "diseases")


def read_votes(path, warnings):
    """{doc_id: 'clean' | 'negative' | 'seen'} for one reader's sheet. A row that cannot be trusted counts for nothing."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        names = [(n or "").strip().lower() for n in (reader.fieldnames or [])]
        if not set(NEED) <= set(names):
            raise ValueError(f"the header has no {', '.join(sorted(set(NEED) - set(names)))} column")
        votes, conflict, every = {}, set(), {}
        for row in reader:
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items() if k is not None}
            doc, read, verdict = r.get("doc_id"), r.get("read", "").lower(), r.get("verdict", "").lower()
            if not doc or read not in ("full", "partial") or verdict not in ("clean", "fix", "drop"):
                continue
            codes = {c.strip().upper() for c in r.get("diseases", "").replace(",", ";").split(";") if c.strip()} - {"D3"}
            if verdict == "clean" and read == "full" and not codes:
                vote = "clean"
            elif verdict in ("fix", "drop") or codes:
                vote = "negative"
            else:
                vote = "seen"  # clean but only partly read, or clean with a code: not a clean vote, not a dispute
            if doc in votes and votes[doc] != vote:
                conflict.add(doc)
            votes[doc] = vote
            every.setdefault(doc, set()).add(vote)
    if conflict:
        warnings.append(f"{path.parent.name}/{path.name}: {len(conflict)} documents with two different rows (disputed if one row is fix or drop)")
        for doc in conflict:
            if "negative" in every[doc]:
                votes[doc] = "negative"  # one row says fix or drop: the document is disputed, never gold
            else:
                del votes[doc]
    return votes


def build_pack(pack_dir, warnings):
    """(gold rows [(doc_id, reader_1, reader_2)], coverage dict) for one pack."""
    sheets = {}
    for path in sorted(pack_dir.glob("*.csv")):
        try:
            sheets[path.stem] = read_votes(path, warnings)
        except (ValueError, OSError, UnicodeDecodeError, csv.Error) as e:
            warnings.append(f"{pack_dir.name}/{path.name}: skipped, {e}")
            continue
        if "clean" not in sheets[path.stem].values() and sheets[path.stem]:
            warnings.append(f"{pack_dir.name}/{path.name}: no clean vote counts (every clean row is a partial read, or has a code)")
    docs = sorted({d for v in sheets.values() for d in v})
    gold, two_clean, disputed = [], 0, 0
    for d in docs:
        clean = sorted((h for h, v in sheets.items() if v.get(d) == "clean"), key=str.casefold)
        if len(clean) < 2:
            continue
        two_clean += 1
        if any(v.get(d) == "negative" for v in sheets.values()):
            disputed += 1
            continue
        gold.append((d, clean[0], clean[1]))
    cover = {"pack_id": pack_dir.name, "readers": len(sheets), "docs_labelled": len(docs),
             "docs_with_2_clean_votes": two_clean, "disputed": disputed, "gold_docs": len(gold)}
    return gold, cover


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gold set from readers' label sheets (Data B).")
    ap.add_argument("--sheets", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--lang", required=True, help="name of the language file, e.g. telugu")
    ap.add_argument("--packs", nargs="+")
    a = ap.parse_args(argv)
    if not a.sheets.is_dir():
        print(f"error: {a.sheets} is not a folder", file=sys.stderr)
        return 2
    packs = a.packs or sorted(p.name for p in a.sheets.iterdir() if p.is_dir())
    missing = [p for p in packs if not (a.sheets / p).is_dir()]
    if missing or not packs:
        print(f"error: no sheet folder for {', '.join(missing) or 'any pack'} in {a.sheets}", file=sys.stderr)
        return 2
    a.out.mkdir(parents=True, exist_ok=True)
    warnings, all_rows, coverage = [], [], []
    for pack in packs:
        gold, cover = build_pack(a.sheets / pack, warnings)
        write_csv(a.out / f"{pack}_gold.csv", ("doc_id", "reader_1", "reader_2"), gold)
        all_rows += gold
        coverage.append(cover)
    write_csv(a.out / f"{a.lang}_gold.csv", ("doc_id", "reader_1", "reader_2"), all_rows)
    write_csv(a.out / "gold_coverage.csv", list(coverage[0]), [list(c.values()) for c in coverage])
    print(f"{'pack_id':<22}{'readers':>8}{'labelled':>9}{'2 clean':>8}{'disputed':>9}{'gold':>6}")
    for c in coverage:
        print(f"{c['pack_id']:<22}{c['readers']:>8}{c['docs_labelled']:>9}{c['docs_with_2_clean_votes']:>8}{c['disputed']:>9}{c['gold_docs']:>6}")
    print(f"{a.lang}: {len(all_rows)} gold documents in {len(packs)} pack(s) -> {a.out}")
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
