"""Reconcile the shards with the ledger: every kept document is in exactly one shard, or left out for a stated reason.

  python -I teams/01-data-a/pipeline/reconcile_shards.py --ledger <run>/ledger --shards <run>/shards --out <dir>
         [--pack code-go ...]

The ledger (ledger.py) says what happened to every document and where each kept one is: final/<split>/<final_part>, row
<final_row>. The shard writer (shards/shard_writer.py, via run_shards.py) records, for every document in a shard, its
input_part (<split>/<pack>/<part>.parquet of the final folder) and input_row in <shard_id>.docs.parquet, and in
<shard_id>.quality_report.json the documents it left out and why. So the two meet on (input_part, input_row): one join.
It decides nothing and changes nothing. Built with pyarrow joins: no Python loop over documents.

INPUT
=====
--ledger   ledger.py's folder: <split>/<pack>.parquet (and ledger_summary.json)
--shards   run_shards.py's --out: shards_summary.json, <shard_id>.docs.parquet, <shard_id>.json, <shard_id>.quality_report.json
--pack     the packs the shard stage was asked for (stages.shards.packs). Kept documents of other packs are
           "not_selected", which is not an error, and a listed pack the ledger does not hold fails. Default: every pack
           the ledger holds kept documents of. Never the packs in shards_summary.json: a pack the shard stage left out
           entirely would then pass as not_selected; with the ledger's packs its documents are "missing", which fails

EVERY KEPT DOCUMENT GETS ONE STATUS (column shard_status)
========================================================
  in_shard          in <shard_id>.docs.parquet at its ledger position (input_part, input_row), with its doc_id
  left_out:<why>    the writer left it out and says why in the quality report: secret (it matches pr-guard's email or
                    secret patterns), empty (no tokens), special (it holds a special token), roundtrip (decode(encode(text))
                    differs from the text), oversize (alone it is more than a shard's --tokens; a doc is never split)
  not_sharded      its part's status is not_sharded: a held-out part (the shard format has train and validation only)
  not_selected      its pack is not among --pack (only when --pack is given)
  not_reached       its part was written but cut short ("truncated": rows at or after the part's rows_read are in no
                    shard). The writer rolls over into more shards, so this should not happen; it is data loss, so it
                    fails (patilvijay23 on #39, point 1)
  part_<status>     its part failed or was skipped by run_shards.py: fails (a part the writer left every row of out is
                    "all_left_out": its documents are left_out:<why> from the summary entry, not part_<status>)
  missing           none of the above: its part was written and reached its row, but it is in no shard: fails

CHECKS (any failure: exit code 1, after writing the outputs, so they show what failed)
=====================================================================================
  - every document in a shard is a kept document of the ledger, at the same (input_part, input_row), with the same doc_id:
    no dropped, removed or unknown document reached a shard
  - no (input_part, input_row) is in two shards
  - every document the writer left out is a kept document of that part, and none is also in a shard
  - each shard manifest's doc_count = its docs.parquet rows
  - no kept document of a selected pack is not_reached, part_failed, part_skipped or missing
  - every pack of --pack holds kept documents in the ledger

OUTPUT (in --out)
=================
  reconcile_docs.parquet    one row per kept document: pack_id, split, input_part, input_row, doc_id, shard_id, shard_status,
                            in (input_part, input_row) order when each pack has its own part folders, as the cleaner
                            writes them (otherwise in that order within each group of ledger files, see below)
  reconcile_summary.json    per pack and split: kept, and the count of each status; the checks; the sha256 of every input
IDs and counts only, never text. Both files are written to .tmp and renamed; one run at a time may write --out
(runlock.py).

SPEED AND SCALE
===============
One ledger file (one pack and split) at a time: its kept documents, the shards of its parts and their quality reports
are read, joined and checked, and its statuses are appended to reconcile_docs.parquet, so memory is bounded by the
largest pack, not the run. A part can hold documents of two packs, which are then in two ledger files, and its shard
holds both: ledger files that share a part are read and checked together (a first pass reads only their split, final
and final_part columns to find them; usually every file is a group of its own). Groups go in the order of their first
part. Written shards that no ledger file claims are checked at the end (all their rows are then at no kept ledger
position). Inputs are hashed in parallel threads (hashing.py).
"""
import sys
sys.dont_write_bytecode = True

import argparse, json, os
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import arrowtools as at  # noqa: E402
import runlock  # noqa: E402
from hashing import HashCache, code_sha256  # noqa: E402

import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

SUMMARY = "shards_summary.json"
REASONS = ("secret", "empty", "special", "roundtrip", "oversize")  # shard_writer.py's left_out keys (LEFT_OUT)
FAILING = ("not_reached", "part_failed", "part_skipped", "missing")
STATUS_SCHEMA = pa.schema([("pack_id", pa.string()), ("split", pa.string()), ("input_part", pa.string()),
                           ("input_row", pa.int64()), ("doc_id", pa.string()), ("shard_id", pa.string()),
                           ("shard_status", pa.string())])
DOCS_SCHEMA = pa.schema([("doc_id", pa.string()), ("input_part", pa.string()), ("input_row", pa.int64()),
                         ("shard_id", pa.string())])
LEFT_SCHEMA = pa.schema([("input_part", pa.string()), ("doc_id", pa.string()), ("reason", pa.string())])


class Stop(Exception):
    """The inputs cannot be read, or the reconciliation failed: the message says why."""


def const(value, n, typ):
    return at.const(value, n, typ)


def kept_rows(path):
    """One ledger file's kept documents: pack_id, split, input_part, input_row, doc_id (and the file's row count)."""
    t = pq.read_table(path, columns=["pack_id", "split", "doc_id", "final", "final_part", "final_row"])
    kept = t.filter(pc.equal(t["final"], "kept"))
    return pa.table({"pack_id": at.as_str(kept["pack_id"]), "split": at.as_str(kept["split"]),
                     "input_part": pc.binary_join_element_wise(kept["split"], kept["final_part"], "/"),
                     "input_row": pc.cast(kept["final_row"], pa.int64()), "doc_id": at.as_str(kept["doc_id"])}), t.num_rows


def kept_parts(path):
    """(the final parts <split>/<final_part> that hold kept documents of one ledger file, the packs of those documents);
    four columns are read."""
    t = pq.read_table(path, columns=["split", "final", "final_part", "pack_id"])
    t = t.filter(pc.equal(t["final"], "kept"))
    if not t.num_rows:
        return set(), set()
    u = t.group_by(["split", "final_part"]).aggregate([])
    parts = set(pc.binary_join_element_wise(at.as_str(u["split"]), at.as_str(u["final_part"]), "/").to_pylist())
    return parts, set(pc.unique(at.as_str(t["pack_id"])).to_pylist())


def file_groups(ledger, files):
    """The ledger files in groups that share no part: the files of the packs whose documents share a part go together,
    since that part's shard holds all of them; every other file is a group of its own. Groups are in the order of their
    first part (then of their file names), so the statuses come out in (input_part, input_row) order whenever no two
    groups' parts interleave. Returns (groups, the packs of all kept documents)."""
    found = {f: kept_parts(f) for f in files}
    parts = {f: found[f][0] for f in files}
    packs = set().union(*(found[f][1] for f in files)) if files else set()
    head = {f: f for f in files}

    def find(f):  # union-find over files that share a part
        while head[f] != f:
            head[f] = head[head[f]]
            f = head[f]
        return f

    owner = {}
    for f in files:
        for part in parts[f]:
            if part in owner:
                a, b = find(owner[part]), find(f)
                if a != b:
                    head[b] = a
            else:
                owner[part] = f
    groups = defaultdict(list)
    for f in files:
        groups[find(f)].append(f)

    def order(g):
        first = min((min(parts[f]) for f in g if parts[f]), default=None)
        return (first is None, first or "", [f.relative_to(ledger).as_posix() for f in g])
    return sorted(groups.values(), key=order), packs


def shard_ids(entry):
    """The shard_ids of a part's summary entry: its "shards" map (run_shards.py, one or more a part), or the single
    "shard_id" of a summary written before rollover."""
    if "shards" in entry:
        return [s["shard_id"] for s in entry["shards"]]
    return [entry["shard_id"]] if entry.get("shard_id") else []


def shard_inputs(folder, names, parts):
    """For these written (or all_left_out) parts: their shard rows (doc_id, input_part, input_row, shard_id), their left-out
    documents (input_part, doc_id, reason), {shard_id: (manifest doc_count, docs.parquet rows)} and the files read. The
    left-out lists come from each shard's quality report, or, for a part with no shard (all_left_out), its summary entry."""
    docs, left, counts, files = [], [], {}, []

    def add_left(part, lists):
        for why in REASONS:  # the left-out lists are short (documents the writer refused)
            ids = [d["doc_id"] if isinstance(d, dict) else d for d in lists.get(why, [])]
            if ids:
                left.append(pa.table({"input_part": const(part, len(ids), pa.string()), "doc_id": pa.array(ids, pa.string()),
                                      "reason": const(why, len(ids), pa.string())}))

    for name in names:
        if parts[name].get("status") == "all_left_out":
            add_left(name, parts[name].get("left_out_docs", {}))
    names = [n for n in names if parts[n].get("status") != "all_left_out"]
    for name, sid in ((n, s) for n in names for s in shard_ids(parts[n]) or [None]):
        if sid is None:
            raise Stop(f"{name}: written, but shards_summary.json names no shard for it")
        meta, man, rep = (folder / f"{sid}{x}" for x in (".docs.parquet", ".json", ".quality_report.json"))
        for f in (meta, man, rep):
            if not f.is_file():
                raise Stop(f"{name}: written as {sid}, but {f.name} is not in --shards")
        files += [meta, man, rep]
        t = pq.read_table(meta, columns=["doc_id", "input_part", "input_row"])
        docs.append(pa.table({"doc_id": at.as_str(t["doc_id"]), "input_part": at.as_str(t["input_part"]),
                              "input_row": pc.cast(t["input_row"], pa.int64()),
                              "shard_id": const(sid, t.num_rows, pa.string())}))
        counts[sid] = (json.loads(man.read_text(encoding="utf-8")).get("doc_count"), t.num_rows)
        r = json.loads(rep.read_text(encoding="utf-8"))
        add_left(r.get("upstream", {}).get("input_part", name), r.get("left_out_docs", {}))
    docs_t = pa.concat_tables(docs) if docs else DOCS_SCHEMA.empty_table()
    left_t = pa.concat_tables(left) if left else LEFT_SCHEMA.empty_table()
    return docs_t, left_t, counts, files


class Tally:
    """The checks, summed over the ledger files; each keeps its first example."""

    def __init__(self):
        self.n = Counter()
        self.example = {}

    def add(self, key, k, example=None):
        if k:
            self.n[key] += k
            if example is not None and key not in self.example:
                self.example[key] = example


def statuses(kept, docs, left, parts, scope):
    """The status of each kept document of one ledger file, and that file's check results (as Tally inputs)."""
    found = {}
    j = docs.join(kept.select(["input_part", "input_row", "doc_id"]).rename_columns(["input_part", "input_row", "ledger_doc"]),
                  ["input_part", "input_row"], join_type="left outer")
    unknown = j.filter(pc.is_null(j["ledger_doc"]))
    other = j.filter(pc.and_(pc.is_valid(j["ledger_doc"]), pc.not_equal(j["ledger_doc"], j["doc_id"])))
    found["unknown"] = (unknown.num_rows, f"{unknown['shard_id'][0]} {unknown['input_part'][0]} row {unknown['input_row'][0]}"
                        if unknown.num_rows else None)
    found["other"] = (other.num_rows, None)
    dup = docs.group_by(["input_part", "input_row"]).aggregate([("shard_id", "count")])
    found["dup"] = (dup.filter(pc.greater(dup["shard_id_count"], 1)).num_rows, None)
    left = left.group_by(["input_part", "doc_id"]).aggregate([("reason", "min")]).rename_columns(
        ["input_part", "doc_id", "reason"])  # one row per document, even if a report lists it twice
    lj = left.join(kept.select(["input_part", "doc_id", "input_row"]), ["input_part", "doc_id"], join_type="left outer")
    found["stray"] = (lj.filter(pc.is_null(lj["input_row"])).num_rows, None)
    found["both"] = (left.join(docs.select(["input_part", "doc_id", "shard_id"]), ["input_part", "doc_id"],
                               join_type="inner").num_rows, None)

    placed = docs.group_by(["input_part", "input_row"]).aggregate([("shard_id", "min")]).rename_columns(
        ["input_part", "input_row", "shard_id"])  # one row per position, even when it is in two shards
    k = kept.join(placed, ["input_part", "input_row"], join_type="left outer")
    k = k.join(lj.select(["input_part", "doc_id", "reason"]), ["input_part", "doc_id"], join_type="left outer")
    names = pc.unique(kept["input_part"]).to_pylist()  # one entry per part, not per document
    pt = pa.table({"input_part": pa.array(names, pa.string()),
                   "part_status": pa.array([parts.get(n, {}).get("status") for n in names], pa.string()),
                   "rows_read": pa.array([parts.get(n, {}).get("rows_read") for n in names], pa.int64())})
    k = k.join(pt, "input_part", join_type="left outer").sort_by([("input_part", "ascending"), ("input_row", "ascending")])
    in_scope = pc.is_in(k["pack_id"], value_set=pa.array(sorted(scope), pa.string()))
    ps = k["part_status"]
    beyond = pc.fill_null(pc.greater_equal(k["input_row"], k["rows_read"]), False)
    status = pc.if_else(pc.is_valid(k["shard_id"]), "in_shard",
             pc.if_else(pc.is_valid(k["reason"]), pc.binary_join_element_wise("left_out", k["reason"], ":"),
             pc.if_else(pc.invert(in_scope), "not_selected",
             pc.if_else(pc.fill_null(pc.equal(ps, "not_sharded"), False), "not_sharded",
             pc.if_else(pc.fill_null(pc.equal(ps, "failed"), False), "part_failed",
             pc.if_else(pc.fill_null(pc.equal(ps, "skipped"), False), "part_skipped",
             pc.if_else(pc.and_(pc.fill_null(pc.equal(ps, "written"), False), beyond), "not_reached", "missing")))))))
    rows = pa.table({"pack_id": k["pack_id"], "split": k["split"], "input_part": k["input_part"], "input_row": k["input_row"],
                     "doc_id": k["doc_id"], "shard_id": k["shard_id"], "shard_status": status}, schema=STATUS_SCHEMA)
    if rows.num_rows != kept.num_rows:  # the ledger refuses a doc_id twice in a part, so these are not the ledger's files
        raise Stop(f"{rows.num_rows} statuses for {kept.num_rows} kept documents: a doc_id appears twice in a part of --ledger")
    return rows, found


def reconcile(ledger, shards, out, packs=None, cache=None):
    """Write the outputs (under out's lock, each file atomically); return the summary. Raises Stop when a check fails
    (after writing) or an input is unreadable."""
    out = Path(out)
    for name, p in (("--ledger", ledger), ("--shards", shards)):
        for what, q in (("--out", out), ("the lock file", runlock.lock_path(out))):
            a, b = Path(p).resolve(), Path(q).resolve()
            if a == b or a in b.parents or b in a.parents:
                raise Stop(f"{name} {p} and {what} {q} overlap: use another --out")
    try:
        with runlock.exclusive(out):
            return _reconcile(Path(ledger), Path(shards), out, packs, cache or HashCache())
    except runlock.Busy as e:
        raise Stop(str(e)) from None


def _reconcile(ledger, shards, out, packs, cache):
    ledger_files = sorted(ledger.glob("*/*.parquet"), key=lambda f: f.relative_to(ledger).as_posix())  # case-sensitive
    if not ledger_files:
        raise Stop(f"--ledger {ledger}: no <split>/<pack>.parquet files")
    if not (shards / SUMMARY).is_file():
        raise Stop(f"--shards {shards}: no {SUMMARY}")
    summary = json.loads((shards / SUMMARY).read_text(encoding="utf-8"))
    parts = summary.get("parts", {})
    written = {name for name, e in parts.items() if e.get("status") in ("written", "all_left_out")}  # parts with documents placed
    groups, ledger_packs = file_groups(ledger, ledger_files)
    scope = set(packs) if packs else set(ledger_packs)  # never the shards' own summary: see --pack
    absent = sorted(set(packs or ()) - set(ledger_packs))
    tally, counts, visited, shard_files = Tally(), {}, set(), [shards / SUMMARY]
    by = defaultdict(lambda: defaultdict(Counter))
    n_kept = n_rows = n_in_shards = 0
    out.mkdir(parents=True, exist_ok=True)
    tmp_docs = out / f"reconcile_docs.parquet.{os.getpid()}.tmp"
    try:
        with pq.ParquetWriter(tmp_docs, STATUS_SCHEMA, compression="zstd") as w:
            for group in groups:  # one pack and split at a time, unless packs share a part
                tables = []
                for f in group:
                    kept, rows_in_file = kept_rows(f)
                    tables.append(kept)
                    n_rows += rows_in_file
                kept = pa.concat_tables(tables) if len(tables) > 1 else tables[0]
                del tables
                names = sorted(n for n in pc.unique(kept["input_part"]).to_pylist() if n in written)
                docs, left, shard_counts, files = shard_inputs(shards, names, parts)
                visited.update(names)
                counts.update(shard_counts)
                shard_files += files
                rows, found = statuses(kept, docs, left, parts, scope)
                for key, (k, example) in found.items():
                    tally.add(key, k, example)
                w.write_table(rows)
                n_kept += kept.num_rows
                n_in_shards += docs.num_rows
                for g in rows.group_by(["pack_id", "split", "shard_status"]).aggregate([([], "count_all")]).to_pylist():
                    by[g["pack_id"]][g["split"]][g["shard_status"]] += g["count_all"]
            # written shards that no ledger file claims: every row in them is at no kept ledger position
            orphans = sorted(written - visited)
            if orphans:
                docs, left, shard_counts, files = shard_inputs(shards, orphans, parts)
                counts.update(shard_counts)
                shard_files += files
                n_in_shards += docs.num_rows
                tally.add("unknown", docs.num_rows, f"{docs['shard_id'][0]} {docs['input_part'][0]} row "
                                                     f"{docs['input_row'][0]}" if docs.num_rows else None)
                tally.add("stray", left.num_rows)
        os.replace(tmp_docs, out / "reconcile_docs.parquet")
    finally:
        tmp_docs.unlink(missing_ok=True)

    totals = Counter()
    for pack in by:
        for split in by[pack]:
            totals.update(by[pack][split])
    bad = sorted(sid for sid, (want, got) in counts.items() if want != got)
    failing = {s: totals[s] for s in FAILING if totals[s]}
    n = tally.n
    checks = [
        {"check": "every document in a shard is a kept document at its ledger position",
         "ok": not n["unknown"] and not n["other"],
         "detail": f"{n['unknown']} shard row(s) at no kept ledger position, {n['other']} with another doc_id"
                   + (f", e.g. {tally.example['unknown']}" if "unknown" in tally.example else "")},
        {"check": "no document is in two shards", "ok": not n["dup"], "detail": f"{n['dup']} position(s) in more than one shard"},
        {"check": "every document the writer left out is a kept document of that part, and none is also in a shard",
         "ok": not n["stray"] and not n["both"],
         "detail": f"{n['stray']} left-out doc_id(s) not kept there, {n['both']} both left out and in a shard"},
        {"check": "each shard manifest's doc_count = its docs.parquet rows", "ok": not bad,
         "detail": f"{len(bad)} shard(s) differ, e.g. {bad[0] if bad else ''}"},
        {"check": "every kept document of a selected pack is in a shard or left out for a stated reason", "ok": not failing,
         "detail": f"{failing}" if failing else "all accounted"},
        {"check": "every selected pack holds kept documents in the ledger", "ok": not absent,
         "detail": f"{len(absent)} pack(s) not in the ledger, e.g. {absent[0]}" if absent else "all present"},
    ]
    hashes = cache.sha256_many([*ledger_files, *shard_files])
    result = {"tool": "reconcile_shards.py", "code_sha256": code_sha256(Path(__file__), cache)[0],
              "inputs": {"ledger_files": {f.relative_to(ledger).as_posix(): hashes[f] for f in ledger_files},
                         "shard_files": {f.name: hashes[f] for f in shard_files}},
              "packs": sorted(p for p in scope if p is not None), "ledger_rows": n_rows, "kept": n_kept,
              "in_shards": n_in_shards, "totals": dict(sorted(totals.items())),
              "by_pack": {p: {s: dict(sorted(c.items())) for s, c in sorted(by[p].items())} for p in sorted(by)},
              "checks": checks, "ok": all(c["ok"] for c in checks)}
    tmp = out / f"reconcile_summary.json.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, out / "reconcile_summary.json")
    if not result["ok"]:
        failed = [c for c in checks if not c["ok"]]
        raise Stop(f"{len(failed)} check(s) failed, e.g. {failed[0]['check']}: {failed[0]['detail']}")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", type=Path, required=True, help="ledger.py's folder")
    ap.add_argument("--shards", type=Path, required=True, help="run_shards.py's --out folder")
    ap.add_argument("--out", type=Path, required=True, help="where reconcile_docs.parquet and reconcile_summary.json go")
    ap.add_argument("--pack", action="append", default=[], help="a pack the shard stage was asked for (repeatable)")
    args = ap.parse_args()
    try:
        r = reconcile(args.ledger, args.shards, args.out, args.pack or None)
    except Stop as e:
        sys.exit(f"reconcile_shards: {e}")
    print(json.dumps({"kept": r["kept"], "in_shards": r["in_shards"], **r["totals"]}))


if __name__ == "__main__":
    main()
