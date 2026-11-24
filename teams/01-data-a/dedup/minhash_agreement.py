r"""Agreement check: minhash_overlap.py against an exact overlap.py run on the same documents.

Maps the exact run's qualifying matches onto the MinHash run's document table by (pack, split, part, row_in_part,
doc_id), keeping only pairs whose two documents are both in the MinHash run, writes them as an overlap run folder with
the MinHash run's overlap_docs.parquet (so both runs have the same row numbers), and reports:
  - qualifying pairs: exact H2 pairs found / missed by MinHash, H2 pairs MinHash adds; H1 groups;
  - duplicate groups (dedup.py's connected components, empty documents set aside): identical or not;
  - if --dedup is given, dedup.py's remove_list.csv for both runs, and whether the two are byte-identical.
IDs and counts only; no text.

    python teams/01-data-a/dedup/minhash_agreement.py --exact out/overlap_tsai --minhash out/mh_full \
        --dedup teams/01-data-a/dedup/dedup.json --out out/mh_agreement
"""
import sys
sys.dont_write_bytecode = True

import argparse, csv, hashlib, json, shutil, subprocess  # noqa: E402
from collections import Counter  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def components(n, edges, empty):
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = [(a, b) for a, b in edges if a not in empty]
    a = np.array([x for x, _ in e] + [0]); b = np.array([y for _, y in e] + [0])
    _, lab = connected_components(coo_matrix((np.ones(len(a)), (a, b)), shape=(n, n)), directed=False)
    groups = {}
    for i, l in enumerate(lab.tolist()):
        groups.setdefault(l, []).append(i)
    return {tuple(g) for g in groups.values() if len(g) > 1}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exact", required=True); ap.add_argument("--minhash", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--dedup")
    a = ap.parse_args()
    import pyarrow.parquet as pq
    ex, mh, out = REPO / a.exact, REPO / a.minhash, REPO / a.out
    key = lambda d: list(zip(d["pack"], d["split"], [p.replace("\\", "/") for p in d["part"]], d["row_in_part"], d["doc_id"]))
    dx = pq.read_table(ex / "overlap_docs.parquet").to_pydict()
    dm = pq.read_table(mh / "overlap_docs.parquet").to_pydict()
    pos = {k: i for i, k in enumerate(key(dm))}
    xmap = [pos.get(k) for k in key(dx)]
    n = len(dm["row"])
    # shingle counts must agree for the shared documents, else the inputs differ
    shared = [(i, j) for i, j in enumerate(xmap) if j is not None]
    diff = sum(dx["shingles"][i] != dm["shingles"][j] for i, j in shared)
    with open(ex / "overlap_matches.csv", newline="", encoding="utf-8") as f:
        xm = list(csv.DictReader(f))
    with open(mh / "overlap_matches.csv", newline="", encoding="utf-8") as f:
        mm = list(csv.DictReader(f))
    kept = []
    for r in xm:
        x, y = xmap[int(r["row_a"])], xmap[int(r["row_b"])]
        if x is not None and y is not None:
            kept.append({**r, "row_a": min(x, y), "row_b": max(x, y)})
    empty = {i for i, s in enumerate(dm["shingles"]) if s == 0}
    h2x = {(r["row_a"], r["row_b"]) for r in kept if r["rule"] == "H2"}
    h2m = {(int(r["row_a"]), int(r["row_b"])) for r in mm if r["rule"] == "H2"}
    gx = components(n, [(r["row_a"], r["row_b"]) for r in kept], empty)
    gm = components(n, [(int(r["row_a"]), int(r["row_b"])) for r in mm], empty)
    report = {"documents_minhash": n, "documents_exact": len(dx["row"]), "documents_shared": len(shared),
              "shingle_count_differences": diff,
              "exact_matches_within_shared": len(kept), "exact_rules": dict(Counter(r["rule"] for r in kept)),
              "minhash_rules": dict(Counter(r["rule"] for r in mm)),
              "h2_exact": len(h2x), "h2_found": len(h2x & h2m), "h2_missed": len(h2x - h2m), "h2_added": len(h2m - h2x),
              "missed_examples": [[dm["pack"][x], dm["doc_id"][x], dm["pack"][y], dm["doc_id"][y]]
                                  for x, y in sorted(h2x - h2m)[:10]],
              "groups_exact": len(gx), "groups_minhash": len(gm), "groups_identical": gx == gm,
              "documents_in_groups_exact": sum(map(len, gx)), "documents_in_groups_minhash": sum(map(len, gm))}
    # an overlap folder for the exact matches on the MinHash row numbers, so dedup.py can run on both
    xo = out / "exact_on_minhash_rows"
    xo.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mh / "overlap_docs.parquet", xo / "overlap_docs.parquet")
    with open(xo / "overlap_matches.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["row_a", "row_b", "rule", "stage", "pack_a", "pack_b", "word_jaccard", "code_jaccard"])
        w.writeheader()
        for r in sorted(kept, key=lambda r: (r["row_a"], r["row_b"])):
            w.writerow({k: r[k] for k in w.fieldnames} | {"pack_a": dm["pack"][r["row_a"]], "pack_b": dm["pack"][r["row_b"]]})
    s = json.loads((mh / "overlap_summary.json").read_text(encoding="utf-8"))
    s["outputs"] = {nm: {"sha256": sha(xo / nm)} for nm in ("overlap_matches.csv", "overlap_docs.parquet")}
    s["method"] = "exact (5 Nov run) mapped onto the MinHash run's rows"
    (xo / "overlap_summary.json").write_text(json.dumps(s), encoding="utf-8")
    if a.dedup:
        base = json.loads((REPO / a.dedup).read_text(encoding="utf-8"))
        for name, res in (("exact", xo), ("minhash", mh)):
            cfg = {k: v for k, v in base.items() if not k.startswith("_")}
            cfg.update({"results": res.relative_to(REPO).as_posix(), "out": (out / f"dedup_{name}").relative_to(REPO).as_posix(),
                        "gold_dirs": []})
            cfg.pop("inputs", None)
            p = out / f"dedup_{name}.json"; p.write_text(json.dumps(cfg), encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "dedup.py"), "--config", str(p)], cwd=REPO,
                               capture_output=True, text=True)
            report[f"dedup_{name}_exit"] = r.returncode
            if r.returncode:
                report[f"dedup_{name}_error"] = r.stdout[-500:] + r.stderr[-500:]
        rx, rm = out / "dedup_exact/remove_list.csv", out / "dedup_minhash/remove_list.csv"
        if rx.exists() and rm.exists():
            report.update({"remove_list_rows_exact": sum(1 for _ in open(rx)) - 1,
                           "remove_list_rows_minhash": sum(1 for _ in open(rm)) - 1,
                           "remove_list_sha256_exact": sha(rx), "remove_list_sha256_minhash": sha(rm),
                           "remove_list_identical": sha(rx) == sha(rm)})
    (out / "agreement.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
