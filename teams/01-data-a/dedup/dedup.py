r"""Dedup v1: turn overlap.py's qualifying matches into a remove list, using source_priority_v1.md.

Reads the returned outputs of an overlap.py run (overlap_summary.json, overlap_matches.csv, overlap_docs.parquet),
checks their SHA-256 against the summary, joins the matches into duplicate clusters (union-find) and keeps one survivor
per cluster with the rules of source_priority_v1.md. It never reads or rewrites document text: IDs, scores and counts only.
TSAI filters the cleaned data with remove_list.csv (dedup_design_v1.md, "Pipeline and hand-off to TSAI").

EMPTY DOCUMENTS
===============
A document with no shingles (overlap_docs.parquet "shingles" = 0) is empty after normalisation. All such documents share
one H1 key, so overlap.py reports them as exact copies of each other, but they are not duplicates: cleaning emptied them
without dropping them. Their matches are set aside before clustering, nothing is removed for them, and they are listed
in empty_documents.csv for the cleaning team.

THE RULES (source_priority_v1.md), applied in order to each cluster
=====================================================================
  0  Held-out first   dedup never removes a held-out document. In a cluster with held-out copies, every held-out copy
                      survives and every train copy is removed. Held-out <-> held-out matches are reported, not removed.
  1  Licence          a copy whose pack has an unusable licence never survives. If no train copy is usable, every train
                      copy is removed. The pack -> usable map is in the config (from G10's licence table).
  2  Provenance       prefer a copy with a non-empty url. Needs the cleaned parts ("inputs" in the config); without them
                      the url is unknown and this rule decides nothing. It changes which copy survives, never how many.
  3  Completeness     prefer the longer copy (more words in its H1 key; overlap_docs.parquet "words").
  4  Pack order       prefer the pack ranked first in "pack_order"; then the lowest (split, part, doc_id).

HOW TO RUN IT
=============
Python 3.10 or later with pyarrow, numpy and scipy (pip install -r teams/01-data-a/dedup/requirements_overlap.txt).
Runs on Windows, macOS and Linux. The work over all documents runs in PyArrow, and the duplicate groups come from
SciPy's connected components. Paths in the config are relative to the repository root, so it can be started from any folder.

    python teams/01-data-a/dedup/dedup.py --config teams/01-data-a/dedup/dedup.json

CONFIG (JSON; keys starting with "_" are comments)
==================================================
  results          folder with overlap_summary.json, overlap_matches.csv and overlap_docs.parquet (required)
  inputs           cleaned parts, as given to overlap.py (train/ and heldout/), for rule 2's url; "" to skip rule 2
  out              output folder, inside out/                                              (default out/dedup)
  cross_pack       true applies the cross-pack pass (dedup_design_v1.md, E2)               (default true)
  pack_order       every pack ID, in source_priority_v1.md rule 4 order                    (required)
  licence_usable   {pack_id: true/false}; packs not listed use default_licence_usable
  default_licence_usable   true or false; the summary records which packs used the default (default true)
  gold_dirs        folders with <pack_id>_gold.csv files, for the harm check               (default [])

WHAT IT WRITES (in out)
=======================
  remove_list.csv          what TSAI filters out: pack_id, split, part, row_in_part, doc_id
  dedup_log.jsonl          one row per removed document: removed_* and kept_* (pack_id, split, part, row_in_part, id),
                           rule, similarity, priority_rule, stage, direct (false when the removed copy reached the
                           survivor only through other copies; similarity is then its strongest match in the cluster)
  heldout_duplicates.csv   held-out <-> held-out matches, reported to G3; nothing is removed for them
  empty_documents.csv      documents with no shingles (pack_id, split, part, row_in_part, doc_id), for the cleaning
                           team; nothing is removed for them
  dedup_groups.csv         every duplicate group, one row per member: group_id, group_size, priority_rule, role
                           (survivor or removed), pack_id, split, part, row_in_part, doc_id. A group can have several
                           survivors (every held-out copy, rule 0) or none (no usable licence, rule 1). For the F2 step
                           after dedup: it counts and lists the groups whose survivor F2 removes (TSAI, 12 Nov)
  dedup_summary.json       per pack: documents in, removed by H1 / H2 / cross-pack, documents out; totals; how often
                           each rule decided; empty documents and the matches set aside for them; the harm check; the
                           config; each output's size and sha256
"""
import argparse, csv, hashlib, json, sys, time
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[3]   # teams/01-data-a/dedup/dedup.py -> the repository root
DEFAULTS = {"results": None, "inputs": "", "out": "out/dedup", "cross_pack": True, "pack_order": None,
            "licence_usable": {}, "default_licence_usable": True, "gold_dirs": []}
NEEDED = ("overlap_summary.json", "overlap_matches.csv", "overlap_docs.parquet")


class Fatal(Exception):
    pass


# ---------------------------------------------------------------- config and inputs

def load_config(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    unknown = sorted(k for k in raw if not k.startswith("_") and k not in DEFAULTS)
    if unknown:
        raise Fatal(f"unknown keys in {path}: {unknown}")
    cfg = {**DEFAULTS, **{k: v for k, v in raw.items() if not k.startswith("_")}}
    if not cfg["results"]:
        raise Fatal("results is required: the folder with the overlap.py outputs")
    for k in ("results", "inputs", "out"):
        if cfg[k] and Path(cfg[k]).is_absolute():
            raise Fatal(f"{k} must be relative to the repository root")
    if not (REPO / cfg["out"]).resolve().is_relative_to((REPO / "out").resolve()):
        raise Fatal(f"out must be inside out/ in the repository root, not {cfg['out']}")
    order = cfg["pack_order"]
    if not isinstance(order, list) or not order or len(set(order)) != len(order):
        raise Fatal("pack_order must be a list of distinct pack IDs (source_priority_v1.md, rule 4)")
    if not isinstance(cfg["licence_usable"], dict) or any(not isinstance(v, bool) for v in cfg["licence_usable"].values()):
        raise Fatal("licence_usable must map pack IDs to true or false")
    if not isinstance(cfg["default_licence_usable"], bool) or not isinstance(cfg["cross_pack"], bool):
        raise Fatal("default_licence_usable and cross_pack must be true or false")
    if not isinstance(cfg["gold_dirs"], list):
        raise Fatal("gold_dirs must be a list of folders")
    return cfg


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_results(results):
    """The overlap run must be complete, and the two files used must match the summary's SHA-256."""
    for name in NEEDED:
        if not (results / name).is_file():
            raise Fatal(f"missing {results / name}")
    summary = json.loads((results / "overlap_summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "complete":
        raise Fatal("the overlap run did not complete (overlap_summary.json status)")
    checked = {}
    for name in ("overlap_matches.csv", "overlap_docs.parquet"):
        got, want = sha256_file(results / name), summary["outputs"][name]["sha256"]
        if got != want:
            raise Fatal(f"SHA-256 mismatch for {name}: {got} != {want} in overlap_summary.json")
        checked[name] = got
    return summary, checked


def read_matches(results, cross_pack):
    """[(row_a, row_b, rule, stage, score)]. The score is the code token Jaccard for code pairs, else the word Jaccard;
    1.0 for H1."""
    out, dropped = [], 0
    with (results / "overlap_matches.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not cross_pack and r["stage"] == "cross_pack":
                dropped += 1
                continue
            score = 1.0 if r["rule"] == "H1" else float(r["code_jaccard"] or r["word_jaccard"] or 0)
            out.append((int(r["row_a"]), int(r["row_b"]), r["rule"], r["stage"], score))
    return out, dropped


def read_docs(results, rows, gold_dirs):
    """Run-local row -> document fields for the matched rows, documents per pack, the gold IDs (read for the packs in
    the run) with how many of them are in it, and every document with no shingles (empty).

    The work over all documents runs in PyArrow: only the matched and empty rows, and rows holding a gold ID, become
    Python objects. A gold ID counts once per pack, however many rows hold it."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    cols = ["row", "doc_id", "pack", "split", "part", "row_in_part", "words", "shingles"]
    t = pq.read_table(results / "overlap_docs.parquet", columns=cols)
    is_matched = pc.is_in(t["row"], value_set=pa.array(sorted(rows), type=t.schema.field("row").type))
    is_empty = pc.equal(t["shingles"], 0)
    docs, empty = {}, []
    for d in t.filter(pc.or_(is_matched, is_empty)).to_pylist():   # file order, as before
        if d["row"] in rows:
            docs[d["row"]] = d
        if d["shingles"] == 0:
            empty.append(d)
    missing = rows - docs.keys()
    if missing:
        raise Fatal(f"{len(missing)} matched rows are not in overlap_docs.parquet, e.g. {sorted(missing)[:3]}")
    counts = pc.value_counts(t["pack"])
    per_pack = dict(zip(counts.field("values").to_pylist(), counts.field("counts").to_pylist()))
    gold = read_gold(gold_dirs, per_pack)
    present = {p: 0 for p in gold}
    all_gold = sorted({d for ids in gold.values() for d in ids})
    if all_gold:
        hits = t.filter(pc.is_in(t["doc_id"], value_set=pa.array(all_gold, type=t.schema.field("doc_id").type)))
        for p, d in {(p, d) for p, d in zip(hits["pack"].to_pylist(), hits["doc_id"].to_pylist())}:
            if d in gold.get(p, ()):
                present[p] += 1
    return docs, per_pack, gold, present, empty


def read_urls(inputs, docs):
    """url for each matched document, from the cleaned parts; None when no inputs are given."""
    if not inputs:
        return None
    import pyarrow.parquet as pq
    want = defaultdict(dict)   # (split, part) -> {row_in_part: run row}
    for row, d in docs.items():
        want[(d["split"], d["part"])][d["row_in_part"]] = row
    urls = {}
    for (split, part), rows in want.items():
        path = inputs / split / part
        if not path.is_file():
            raise Fatal(f"missing cleaned part {path} (needed for rule 2's url)")
        t = pq.read_table(path, columns=["doc_id", "url"])
        wanted = sorted(rows)                                   # only these rows become Python objects
        if wanted[-1] >= t.num_rows:
            raise Fatal(f"{path} row {wanted[-1]} is not doc_id {docs[rows[wanted[-1]]]['doc_id']}: "
                        "inputs do not match the run")
        got = t.take(wanted)
        for r_in_part, doc_id, url in zip(wanted, got["doc_id"].to_pylist(), got["url"].to_pylist()):
            row = rows[r_in_part]
            if doc_id != docs[row]["doc_id"]:
                raise Fatal(f"{path} row {r_in_part} is not doc_id {docs[row]['doc_id']}: inputs do not match the run")
            urls[row] = url or ""
    return urls


# ---------------------------------------------------------------- clusters and survivors

def clusters(matches):
    """Duplicate groups: the connected components of the match graph (SciPy), each as a sorted list of run rows."""
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    if not matches:
        return []
    a = np.fromiter((m[0] for m in matches), dtype=np.int64, count=len(matches))
    b = np.fromiter((m[1] for m in matches), dtype=np.int64, count=len(matches))
    nodes, idx = np.unique(np.concatenate([a, b]), return_inverse=True)
    n = len(nodes)
    graph = coo_matrix((np.ones(len(a), dtype=np.int8), (idx[:len(a)], idx[len(a):])), shape=(n, n))
    _, label = connected_components(graph, directed=False)
    order = np.lexsort((nodes, label))                         # by group, rows ascending inside each group
    cuts = np.flatnonzero(np.diff(label[order])) + 1
    return [g.tolist() for g in np.split(nodes[order], cuts)]


def rank_key(d, rank, urls):
    """Rules 2-4: a lower key wins."""
    has_url = 0 if urls is None or urls.get(d["row"]) else 1   # unknown url: every copy ties on rule 2
    return (has_url, -d["words"], rank[d["pack"]], d["split"], d["part"], d["doc_id"])


def pick(candidates, rank, urls):
    """Rules 2-4 in order, each breaking the ties left by the one above: (winner, the rule that left one copy)."""
    remaining = list(candidates)
    for rule, key in ((2, lambda d: rank_key(d, rank, urls)[0]),
                      (3, lambda d: rank_key(d, rank, urls)[1]),
                      (4, lambda d: rank_key(d, rank, urls)[2:])):
        best = min(key(d) for d in remaining)
        remaining = [d for d in remaining if key(d) == best]
        if len(remaining) == 1:
            return remaining[0], rule
    return remaining[0], 4   # identical on every key: cannot happen, (split, part, doc_id) differs


def decide(cluster, docs, rank, usable, urls):
    """(survivor rows, removed rows, the rule that decided, the reference survivor for the log)."""
    members = [docs[r] for r in cluster]
    held = [d for d in members if d["split"] == "heldout"]
    train = [d for d in members if d["split"] != "heldout"]
    if held:                                                  # rule 0: every held-out copy survives
        ref, _ = pick(held, rank, urls) if len(held) > 1 else (held[0], 0)
        return [d["row"] for d in held], [d["row"] for d in train], 0, ref
    ok = [d for d in train if usable(d["pack"])]
    if not ok:                                                # rule 1: no usable copy, all train copies go
        return [], [d["row"] for d in train], 1, None
    if len(ok) == 1:                                          # rule 1: licence alone leaves one copy
        best, rule = ok[0], 1
    else:
        best, rule = pick(ok, rank, urls)
    return [best["row"]], [d["row"] for d in train if d is not best], rule, best


# ---------------------------------------------------------------- harm check

def read_gold(gold_dirs, packs):
    """{pack: gold doc_ids} from <pack>_gold.csv in gold_dirs, for the packs in the run."""
    gold = defaultdict(set)
    for g in gold_dirs:
        for f in sorted((REPO / g).glob("*_gold.csv")):
            pack = f.name[: -len("_gold.csv")]
            if pack in packs:
                with f.open(newline="", encoding="utf-8") as fh:
                    gold[pack] |= {r["doc_id"] for r in csv.DictReader(fh)}
    return gold


def harm_check(gold_dirs, gold, present, removed_keys):
    """Gold documents present in the input, and gold documents removed, matched on (pack_id, doc_id)."""
    if not gold_dirs:
        return {"status": "not_run", "reason": "no gold_dirs in the config"}
    removed = sorted((p, d) for p, d in removed_keys if d in gold.get(p, ()))
    n_present = sum(present.values())
    status = "not_testable" if n_present == 0 else ("fail" if removed else "pass")
    return {"status": status, "gold_ids_in_input": n_present, "gold_ids_in_input_by_pack": present,
            "gold_removed": len(removed), "gold_removed_ids": [f"{p}:{d}" for p, d in removed],
            "note": "not_testable means no gold ID is in this input, so the check tested nothing "
                    "(dedup_design_v1.md, Validation): run it on the diagnosis packs"}


# ---------------------------------------------------------------- main

def run(cfg):
    t0 = time.time()
    results = REPO / cfg["results"]
    summary_in, checked = check_results(results)
    matches, dropped_cross = read_matches(results, cfg["cross_pack"])
    rows = {x for a, b, *_ in matches for x in (a, b)}
    docs, per_pack, gold, present, empty = read_docs(results, rows, cfg["gold_dirs"])
    empty_rows = {d["row"] for d in empty}
    n_matches = len(matches)
    matches = [m for m in matches if m[0] not in empty_rows and m[1] not in empty_rows]   # not duplicates: set aside
    empty_matches = n_matches - len(matches)
    packs = sorted(per_pack)
    missing = sorted(set(packs) - set(cfg["pack_order"]))
    if missing:
        raise Fatal(f"pack_order has no rank for {missing}")
    rank = {p: i for i, p in enumerate(cfg["pack_order"])}
    defaulted = sorted(p for p in packs if p not in cfg["licence_usable"])
    usable = lambda p: cfg["licence_usable"].get(p, cfg["default_licence_usable"])
    urls = read_urls(REPO / cfg["inputs"] if cfg["inputs"] else None, docs)

    # strongest direct match of each pair, for the log
    best_pair = {}
    for a, b, rule, stage, score in matches:
        k = (min(a, b), max(a, b))
        if k not in best_pair or score > best_pair[k][1]:
            best_pair[k] = (rule, score)
    strongest = {}
    for (a, b), (rule, score) in best_pair.items():
        for x in (a, b):
            if x not in strongest or score > strongest[x][1]:
                strongest[x] = (rule, score)

    removed, log, decided, member = [], [], Counter(), []   # member: (group_id, group_size, rule, role, row)
    no_survivor = several_survivors = 0
    for i, cl in enumerate(sorted(clusters(matches), key=lambda g: g[0]), 1):   # by lowest row: same group_id every run
        keep, drop, rule, ref = decide(cl, docs, rank, usable, urls)
        decided[rule] += 1
        no_survivor += not keep
        several_survivors += len(keep) > 1
        member += [(f"G{i:06d}", len(cl), rule, "survivor", r) for r in keep]
        member += [(f"G{i:06d}", len(cl), rule, "removed", r) for r in drop]
        for r in drop:
            d = docs[r]
            if ref is not None:
                direct = best_pair.get((min(r, ref["row"]), max(r, ref["row"])))
                m_rule, sim = direct if direct else strongest[r]
            else:
                direct, (m_rule, sim) = None, strongest[r]
            log.append({
                "removed_pack_id": d["pack"], "removed_split": d["split"], "removed_part": d["part"],
                "removed_row_in_part": d["row_in_part"], "removed_id": d["doc_id"],
                "kept_pack_id": ref["pack"] if ref else None, "kept_split": ref["split"] if ref else None,
                "kept_part": ref["part"] if ref else None, "kept_row_in_part": ref["row_in_part"] if ref else None,
                "kept_id": ref["doc_id"] if ref else None,
                "rule": m_rule, "similarity": round(sim, 6), "priority_rule": rule,
                "stage": "none" if ref is None else ("within_pack" if ref["pack"] == d["pack"] else "cross_pack"),
                "direct": direct is not None,
            })
            removed.append(r)

    held_pairs = [(a, b, rule, score) for (a, b), (rule, score) in sorted(best_pair.items())
                  if docs[a]["split"] == "heldout" and docs[b]["split"] == "heldout"]

    out = REPO / cfg["out"]
    out.mkdir(parents=True, exist_ok=True)
    log.sort(key=lambda e: (e["removed_pack_id"], e["removed_split"], e["removed_part"], e["removed_row_in_part"]))
    with (out / "remove_list.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pack_id", "split", "part", "row_in_part", "doc_id"])
        for e in log:
            w.writerow([e["removed_pack_id"], e["removed_split"], e["removed_part"], e["removed_row_in_part"], e["removed_id"]])
    with (out / "dedup_log.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for e in log:
            f.write(json.dumps(e) + "\n")
    with (out / "heldout_duplicates.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pack_a", "part_a", "doc_id_a", "pack_b", "part_b", "doc_id_b", "rule", "similarity"])
        for a, b, rule, score in held_pairs:
            w.writerow([docs[a]["pack"], docs[a]["part"], docs[a]["doc_id"],
                        docs[b]["pack"], docs[b]["part"], docs[b]["doc_id"], rule, round(score, 6)])
    with (out / "empty_documents.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pack_id", "split", "part", "row_in_part", "doc_id"])
        for d in sorted(empty, key=lambda d: (d["pack"], d["split"], d["part"], d["row_in_part"])):
            w.writerow([d["pack"], d["split"], d["part"], d["row_in_part"], d["doc_id"]])

    with (out / "dedup_groups.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["group_id", "group_size", "priority_rule", "role", "pack_id", "split", "part", "row_in_part", "doc_id"])
        place = lambda r: (docs[r]["pack"], docs[r]["split"], docs[r]["part"], docs[r]["row_in_part"])
        member.sort(key=lambda m: (m[0], m[3] != "survivor", place(m[4])))
        for g, size, rule, role, r in member:
            d = docs[r]
            w.writerow([g, size, rule, role, d["pack"], d["split"], d["part"], d["row_in_part"], d["doc_id"]])

    by_pack = {p: Counter() for p in packs}
    for e in log:
        c = by_pack[e["removed_pack_id"]]
        c["removed"] += 1
        c[f"removed_{e['rule']}"] += 1
        if e["stage"] == "cross_pack":
            c["removed_cross_pack"] += 1
    per = {p: {"documents_in": per_pack[p], "removed": by_pack[p]["removed"],
               "removed_H1": by_pack[p]["removed_H1"], "removed_H2": by_pack[p]["removed_H2"],
               "removed_cross_pack": by_pack[p]["removed_cross_pack"],
               "documents_out": per_pack[p] - by_pack[p]["removed"]} for p in packs}
    harm = harm_check(cfg["gold_dirs"], gold, present, {(e["removed_pack_id"], e["removed_id"]) for e in log})
    files = {f: {"bytes": (out / f).stat().st_size, "sha256": sha256_file(out / f)}
             for f in ("remove_list.csv", "dedup_log.jsonl", "heldout_duplicates.csv", "empty_documents.csv",
                       "dedup_groups.csv")}
    summary = {
        "status": "complete",
        "config": cfg,
        "overlap_run": {"commit_note": "see overlap_summary.json", "documents_all": summary_in.get("documents_all"),
                        "checked_sha256": checked},
        "matches_used": len(matches),
        "cross_pack_matches_dropped": dropped_cross,
        "empty_documents": len(empty),
        "empty_document_matches_set_aside": empty_matches,
        "clusters": sum(decided.values()),
        "clusters_decided_by_rule": {str(k): v for k, v in sorted(decided.items())},
        "groups_without_survivor": no_survivor,
        "groups_with_several_survivors": several_survivors,
        "documents_all": sum(per_pack.values()),
        "removed": len(log),
        "removed_share": round(len(log) / max(sum(per_pack.values()), 1), 6),
        "removed_by_rule": dict(Counter(e["rule"] for e in log)),
        "removed_by_stage": dict(Counter(e["stage"] for e in log)),
        "heldout_removed": sum(e["removed_split"] == "heldout" for e in log),
        "heldout_heldout_pairs_reported": len(held_pairs),
        "url_known": urls is not None,
        "rule_2_note": None if urls is not None else "no inputs given: url unknown, rule 2 decided nothing",
        "licence_default_used_for": defaulted,
        "harm_check": harm,
        "by_pack": per,
        "outputs": files,
        "seconds": round(time.time() - t0, 1),
    }
    (out / "dedup_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="JSON config; see CONFIG above")
    args = ap.parse_args(argv)
    try:
        s = run(load_config(args.config))
    except Fatal as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"{s['documents_all']:,} documents, {s['matches_used']:,} matches, {s['clusters']:,} clusters")
    print(f"removed {s['removed']:,} ({s['removed_share']:.4%}): by rule {s['removed_by_rule']}, by stage {s['removed_by_stage']}")
    print(f"clusters decided by priority rule: {s['clusters_decided_by_rule']}")
    print(f"held-out removed: {s['heldout_removed']} (must be 0); held-out <-> held-out pairs reported: "
          f"{s['heldout_heldout_pairs_reported']}")
    print(f"empty documents: {s['empty_documents']} listed, not removed; {s['empty_document_matches_set_aside']} "
          f"matches between them set aside")
    if s["rule_2_note"]:
        print(f"note: {s['rule_2_note']}")
    if s["licence_default_used_for"]:
        print(f"note: licence map not filled for {len(s['licence_default_used_for'])} packs; default used")
    print(f"harm check: {s['harm_check']['status']}")
    print(f"wrote remove_list.csv, dedup_log.jsonl, heldout_duplicates.csv, empty_documents.csv, dedup_groups.csv and "
          f"dedup_summary.json to "
          f"{(REPO / s['config']['out']).relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
