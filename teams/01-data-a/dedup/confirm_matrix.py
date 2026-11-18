r"""Confirm the source-by-source overlap matrix returned by TSAI's overlap job, without reading any document text.

It rebuilds overlap_matrix.csv and overlap_matrix_counts.csv from the returned overlap_matches.csv with
overlap_report.write_matrix (the function overlap.py itself uses), compares them byte for byte with the returned files,
and checks every returned output's SHA-256 and size against overlap_summary.json.

ROW -> PACK MAP
===============
With --docs, the map is read from overlap_docs.parquet after its SHA-256 is checked (the route of
overlap_report.py --results). Without it, the map is rebuilt from the part list in overlap_summary.json: overlap.py
numbers documents 0..N-1 in the order it reads the parts, and that order is summary["inputs"]["parts"]. The derived map
is used only if its per-pack train/held-out counts equal the summary's (which come from each row's pack_id) and every
matched row falls in the pack that overlap_matches.csv names for it.

HOW TO RUN IT (from the repository root; paths are relative to it)
===================================================================
    python3 teams/01-data-a/dedup/confirm_matrix.py --results out/overlap_tsai
    python3 teams/01-data-a/dedup/confirm_matrix.py --results out/overlap_tsai --docs out/overlap_tsai/overlap_docs.parquet

--results needs overlap_summary.json, overlap_matches.csv, overlap_matrix.csv and overlap_matrix_counts.csv.

WHAT IT WRITES (in --out, default out/matrix_confirmation, inside out/)
=======================================================================
  rebuilt/overlap_matrix.csv, rebuilt/overlap_matrix_counts.csv     the rebuilt matrix
  without_empty_documents/overlap_matrix*.csv                       the same, without the pairs inside the group of
                                                                    empty documents (for review; not a replacement)
  confirmation.json                                                 every check and number
Exit 0 when every check passes, 1 when one fails, 2 on unusable input.
"""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from overlap_report import RowRuns, read_docs, write_matrix  # noqa: E402

REPO = Path(__file__).resolve().parents[3]   # teams/01-data-a/dedup/confirm_matrix.py -> the repository root
NEEDED = ("overlap_summary.json", "overlap_matches.csv", "overlap_matrix.csv", "overlap_matrix_counts.csv")
MATRIX_FILES = ("overlap_matrix.csv", "overlap_matrix_counts.csv")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def groups(edges):
    """Union-find: the connected groups of rows joined by edges."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    out = defaultdict(list)
    for x in list(parent):
        out[find(x)].append(x)
    return [sorted(g) for g in out.values()]


def counts_table(path):
    return {(r["source_a"], r["source_b"]): (int(r["matched_documents"]), int(r["total_documents"]))
            for r in read_csv(path)}


class Checks:
    def __init__(self):
        self.items = []

    def add(self, name, ok, detail=""):
        self.items.append({"check": name, "ok": bool(ok), "detail": detail})

    def all_ok(self):
        return all(c["ok"] for c in self.items)


def row_map_from_docs(path, summary, checks):
    """(row -> pack, row -> split) from overlap_docs.parquet, or (None, None) when its rows are not 0..N-1 in order."""
    want = summary["outputs"]["overlap_docs.parquet"]["sha256"]
    got = sha256(path)
    checks.add("overlap_docs.parquet SHA-256 equals the summary", got == want, f"{got} (summary {want})")
    maps = read_docs(path, ["pack", "split"])
    if maps is None:
        return None, None
    row_pack, row_split = maps
    checks.add("overlap_docs.parquet has one entry per document", len(row_pack) == summary["documents_all"],
               f"{len(row_pack):,} rows")
    return row_pack, row_split.get


def row_map_from_parts(summary, checks):
    starts, splits, packs, per = [], [], [], Counter()
    r = 0
    for p in summary["inputs"]["parts"]:
        split, pack = p["part"].split("/")[:2]
        starts.append(r)
        splits.append(split)
        packs.append(pack)
        per[pack, split] += p["documents"]
        r += p["documents"]
    checks.add("the parts add up to documents_all", r == summary["documents_all"],
               f"{len(summary['inputs']['parts'])} parts, {r:,} documents (summary {summary['documents_all']:,})")
    bad = [(pk, sp, per[pk, sp], d[sp]) for pk, d in summary["documents"].items() for sp in ("train", "heldout")
           if per[pk, sp] != d[sp]]
    checks.add("per-pack train / held-out counts from the parts equal the summary (pack_id based)", not bad,
               f"{len(bad)} differ: {bad[:3]}" if bad else "38 packs x 2 splits agree")
    return RowRuns(starts, packs, r), RowRuns(starts, splits, r).get


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True, type=Path, help="folder with the returned overlap outputs")
    ap.add_argument("--docs", type=Path, help="overlap_docs.parquet of the same run (optional)")
    ap.add_argument("--out", default="out/matrix_confirmation", help="output folder, inside out/")
    args = ap.parse_args(argv)
    res = args.results if args.results.is_absolute() else REPO / args.results
    docs = None if args.docs is None else (args.docs if args.docs.is_absolute() else REPO / args.docs)
    out = (REPO / args.out).resolve()
    if not out.is_relative_to((REPO / "out").resolve()):
        ap.error("--out must be inside out/ in the repository root")
    missing = [n for n in NEEDED if not (res / n).is_file()]
    if missing or (docs is not None and not docs.is_file()):
        print(f"ERROR: missing {missing or [str(docs)]} in {res}", file=sys.stderr)
        return 2

    checks, report = Checks(), {}
    summary = json.loads((res / "overlap_summary.json").read_text(encoding="utf-8"))
    packs = sorted(summary["documents"])
    expected = summary.get("config", {}).get("expected_packs") or []
    report["inputs"] = {
        "results": str(res.relative_to(REPO)) if res.is_relative_to(REPO) else str(res),
        "row_map": "overlap_docs.parquet" if docs else "part order in overlap_summary.json (overlap_docs.parquet not given)",
        "summary_sha256": sha256(res / "overlap_summary.json"),
        "documents_all": summary["documents_all"], "packs": len(packs), "empty_documents": summary.get("empty_documents"),
    }

    # Step 1: the run
    checks.add("overlap run status is complete", summary.get("status") == "complete", str(summary.get("status")))
    checks.add("the packs equal the config's expected_packs", not expected or set(expected) == set(packs),
               f"{len(packs)} packs" + ("" if expected else "; the config has no expected_packs"))

    # Step 2: returned files against the summary
    files = {}
    for name, meta in summary["outputs"].items():
        p = res / name
        if not p.is_file():
            files[name] = {"returned": False, "bytes_in_run": meta["bytes"]}
            continue
        got, size = sha256(p), p.stat().st_size
        ok = got == meta["sha256"] and size == meta["bytes"]
        files[name] = {"returned": True, "bytes": size, "sha256": got, "equals_summary": ok}
        checks.add(f"{name}: SHA-256 and size equal the summary", ok, f"{size:,} bytes, sha256 {got}")
    report["files"] = files

    # Step 3: row -> pack map, checked against the matches
    row_pack, split_of = row_map_from_docs(docs, summary, checks) if docs else row_map_from_parts(summary, checks)
    if row_pack is None:
        print("ERROR: overlap_docs.parquet needs rows 0..N-1 in order and a pack and split on every row", file=sys.stderr)
        return 2
    matches = read_csv(res / "overlap_matches.csv")
    pairs = [(int(m["row_a"]), int(m["row_b"])) for m in matches]
    mis = sum(1 for (a, b), m in zip(pairs, matches) if (row_pack.get(a), row_pack.get(b)) != (m["pack_a"], m["pack_b"]))
    checks.add("every matched row is in the pack that overlap_matches.csv names", mis == 0,
               f"{len(matches):,} matches, {len({x for p in pairs for x in p}):,} distinct rows, {mis} mismatches")
    stage_bad = sum(1 for m in matches if (m["stage"] == "within_pack") != (m["pack_a"] == m["pack_b"]))
    checks.add("every stage label agrees with its packs", stage_bad == 0, f"{stage_bad} disagree")
    checks.add("no document is matched with itself", all(a != b for a, b in pairs))
    rules = Counter(m["rule"] for m in matches)
    checks.add("rule counts equal qualifying_pairs_by_rule", dict(rules) == summary["qualifying_pairs_by_rule"],
               f"{dict(rules)}")
    stages = Counter(m["stage"] for m in matches)
    report["matches"] = {"pairs": len(matches), "by_rule": dict(rules), "by_stage": dict(stages)}

    # Step 4: rebuild and compare byte for byte
    write_matrix(out / "rebuilt", row_pack, pairs)
    report["rebuilt"] = {}
    for name in MATRIX_FILES:
        mine, theirs = (out / "rebuilt" / name), (res / name)
        same = mine.read_bytes() == theirs.read_bytes()
        report["rebuilt"][name] = {"sha256": sha256(mine), "returned_sha256": sha256(theirs), "byte_identical": same}
        checks.add(f"rebuilt {name} is byte-identical to the returned file", same, f"sha256 {sha256(mine)}")

    # Step 5: what the matrix says
    cnt = counts_table(res / "overlap_matrix_counts.csv")
    mat_rows = read_csv(res / "overlap_matrix.csv")
    header = list(mat_rows[0].keys())[1:] if mat_rows else []
    checks.add("overlap_matrix.csv is packs x packs, in sorted order",
               header == packs and [r["source"] for r in mat_rows] == packs, f"{len(mat_rows)} rows x {len(header)} columns")
    checks.add("overlap_matrix_counts.csv has one cell per pair of packs", len(cnt) == len(packs) ** 2,
               f"{len(cnt):,} cells ({len(packs)} x {len(packs)})")
    den_bad = [a for (a, b), (k, t) in cnt.items() if t != summary["documents"][a]["all"]]
    checks.add("every denominator equals its pack's document count", not den_bad, f"{len(den_bad)} differ")
    share_bad = [(r["source"], b) for r in mat_rows for b in packs if r[b] != f"{cnt[r['source'], b][0] / cnt[r['source'], b][1]:.10f}"]
    checks.add("every share equals matched / total (10 decimals)", not share_bad, f"{len(share_bad)} differ")

    cross_docs, any_docs = defaultdict(set), set()
    for (a, b), m in zip(pairs, matches):
        any_docs.update((a, b))
        if m["pack_a"] != m["pack_b"]:
            cross_docs[m["pack_a"]].add(a)
            cross_docs[m["pack_b"]].add(b)
    per_pack = []
    for p in packs:
        k, t = cnt[p, p]
        per_pack.append({"pack": p, "documents": t, "own_pack_matched": k, "own_pack_share": k / t,
                         "other_pack_matched": len(cross_docs[p]),
                         "other_packs_with_a_match": sum(1 for q in packs if q != p and cnt[p, q][0])})
    off = sorted(((a, b, k, t) for (a, b), (k, t) in cnt.items() if a != b and k), key=lambda x: (-x[2], x[0], x[1]))
    asym = sorted({tuple(sorted((a, b))) for a, b, k, t in off if cnt[b, a][0] != k})
    report["matrix"] = {
        "cells": len(cnt), "nonzero_cells": sum(1 for v in cnt.values() if v[0]),
        "nonzero_diagonal": sum(1 for p in packs if cnt[p, p][0]), "nonzero_off_diagonal": len(off),
        "packs_with_no_match": [p for p in packs if not cnt[p, p][0] and not cross_docs[p]],
        "documents_with_any_match": len(any_docs),
        "documents_with_a_cross_pack_match": sum(len(s) for s in cross_docs.values()),
        "own_pack_matched_total": sum(cnt[p, p][0] for p in packs),
        "per_pack": per_pack,
        "off_diagonal_cells": [{"from": a, "to": b, "matched": k, "total": t, "share": k / t} for a, b, k, t in off],
        "pack_pairs_with_different_counts_each_way": [list(x) for x in asym],
        "train_heldout_pairs": sum(1 for a, b in pairs if {split_of(a), split_of(b)} == {"train", "heldout"}),
    }

    # Step 6: the group of empty documents
    E = summary.get("empty_documents", 0)
    h1 = groups(p for p, m in zip(pairs, matches) if m["rule"] == "H1")
    cand = [g for g in h1 if len(g) == E] if E >= 2 else []
    empty = {"empty_documents": E, "h1_groups": len(h1), "h1_group_sizes": dict(sorted(Counter(map(len, h1)).items()))}
    if len(cand) == 1:
        eg = set(cand[0])
        kept = [p for p in pairs if not (p[0] in eg and p[1] in eg)]
        write_matrix(out / "without_empty_documents", row_pack, kept)
        after = counts_table(out / "without_empty_documents" / "overlap_matrix_counts.csv")
        empty.update({
            "rows": [{"row": r, "pack": row_pack[r], "split": split_of(r)} for r in cand[0]],
            "pairs_inside_group": len(pairs) - len(kept),
            "cross_pack_pairs_inside_group": sum(1 for (a, b), m in zip(pairs, matches)
                                                 if a in eg and b in eg and m["stage"] == "cross_pack"),
            "changed_cells": [{"from": a, "to": b, "before": cnt[a, b][0], "after": after[a, b][0], "total": cnt[a, b][1]}
                              for a, b in sorted(cnt) if cnt[a, b][0] != after[a, b][0]],
        })
    checks.add("the empty documents form exactly one H1 group", E < 2 or len(cand) == 1,
               f"{E} empty documents; H1 groups of that size: {len(cand)}")
    report["empty_document_group"] = empty

    report["checks"] = checks.items
    report["all_checks_passed"] = checks.all_ok()
    (out / "confirmation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    w = max(len(c["check"]) for c in checks.items)
    for c in checks.items:
        print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['check']:{w}}  {c['detail']}")
    print(f"\n{sum(c['ok'] for c in checks.items)} of {len(checks.items)} checks passed; "
          f"wrote {out.relative_to(REPO)}/confirmation.json and the rebuilt matrices")
    return 0 if checks.all_ok() else 1


if __name__ == "__main__":
    sys.exit(main())
