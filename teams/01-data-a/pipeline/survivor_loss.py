"""Count and list the dedup groups whose survivor F2 dropped (TSAI, 12 Nov: accept the loss, count and list the groups).

  python -I teams/01-data-a/pipeline/survivor_loss.py --groups <dedup_groups.csv> --f2 <final_dir> --out <dir>

Dedup keeps one copy of each duplicate group (several when the group has held-out copies) and F2 runs after it. When F2
drops a survivor, that copy is gone and the removed copies are not brought back (dedup_design_v1.md, the F2 step).

INPUT
=====
--groups is dedup.py's dedup_groups.csv: group_id, group_size, priority_rule, role (survivor or removed), pack_id, split,
part, row_in_part, doc_id. --f2 is the folder F2 wrote, one run per split: <final>/<split>/<part>.f2.json, each with
run_f2.py's "dropped" list ({doc_id, items, offset}), "errors" ([doc_id, error type]; such a doc is kept out of the
output too, so it counts as gone, with f2_items "error:<type>") and "set_sha256". A survivor is matched on (split, part, doc_id):
doc_id alone is not a key (in sample v0, 22,773 doc_ids sit in two parts of the same pack and split).

A GROUP IS
==========
  lost          it had at least one survivor and F2 dropped all of them: no copy is left in the final data
  partly_hit    F2 dropped some of its survivors, not all (a group with several held-out survivors)
  untouched     F2 dropped none of its survivors
  (without_survivor: dedup kept no copy, as with no usable licence; F2 cannot change it)
  (with_several_survivors: dedup kept more than one copy, every held-out copy by rule 0; counted for the runner, which
  checks it, with total and without_survivor, against dedup_summary.json)

CHECKS (exit code 1 on failure)
===============================
dedup_groups.csv has dedup.py's header; every part that holds a survivor has an F2 report (else F2 did not cover it);
every F2 report names the same set_sha256.

OUTPUT
======
<out>/survivor_loss.csv: one row per survivor F2 dropped (status, group_id, group_size, priority_rule, pack_id, split,
part, row_in_part, doc_id, f2_items, offset), groups ordered by group_id's length then group_id (G9 before G10), and a
group's rows in the CSV's order. <out>/survivor_loss_summary.json: group counts, survivor rows per pack and status
(survivor_rows_by_pack: dropped survivors, not groups), the set_sha256, the sha256 of dedup_groups.csv and of the code
(this file and its helper modules, hashing.code_sha256). IDs, benchmark item IDs and offsets only, never text.

SPEED AND SCALE
===============
dedup_groups.csv can hold millions of rows: it is read by pyarrow, survivors are matched to F2's drops with one join on
(split, part, doc_id), and each group's status comes from one group_by. The only Python loop is over the F2 reports
(one per part), whose dropped lists are turned into columns at once.
"""
import sys
sys.dont_write_bytecode = True

import argparse, csv, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import arrowtools as at  # noqa: E402
from hashing import code_sha256, file_sha256 as sha256  # noqa: E402

import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402

GROUP_HEADER = ["group_id", "group_size", "priority_rule", "role", "pack_id", "split", "part", "row_in_part", "doc_id"]
OUT_COLUMNS = ["status", "group_id", "group_size", "priority_rule", "pack_id", "split", "part", "row_in_part", "doc_id",
               "f2_items", "offset"]
SUFFIX = ".f2.json"


class Stop(Exception):
    """A check failed: the message says which and where."""


def read_groups(path):
    """dedup_groups.csv as a Table (part written with /)."""
    return at.posix(at.read_csv(path, GROUP_HEADER, {"group_size": pa.int64(), "priority_rule": pa.int64(),
                                                     "row_in_part": pa.int64()}, Stop))


def read_f2(final):
    """(Table of what F2 kept out: split, part, doc_id, f2_items, offset; the set_sha256 all reports share; reports)."""
    final = Path(final)
    reports = sorted(final.rglob("*" + SUFFIX))
    if not reports:
        raise Stop(f"--f2 {final}: no *{SUFFIX} reports")
    tables, sets, covered = [], set(), []
    dropped_type = pa.struct([("doc_id", pa.string()), ("items", pa.list_(pa.string())), ("offset", pa.int64())])
    for path in reports:  # one per part
        rel = path.relative_to(final).as_posix()
        split, _, part = rel.partition("/")
        part = part[: -len(SUFFIX)]
        data = json.loads(path.read_text(encoding="utf-8"))
        sets.add(data.get("set_sha256"))
        covered.append((split, part))
        d = pa.array(data.get("dropped") or [], dropped_type)
        e = pa.array(data.get("errors") if isinstance(data.get("errors"), list) else [], pa.list_(pa.string()))
        nd, ne = len(d), len(e)
        if nd + ne == 0:
            continue
        doc = pa.concat_arrays([pc.struct_field(d, "doc_id"), pc.list_element(e, 0) if ne else pa.array([], pa.string())])
        items = pa.concat_arrays([pc.binary_join(pc.struct_field(d, "items"), " "),
                                  pc.binary_join_element_wise("error:", pc.list_element(e, 1), "") if ne
                                  else pa.array([], pa.string())])
        offset = pa.concat_arrays([pc.cast(pc.struct_field(d, "offset"), pa.string()),
                                   at.const("", ne, pa.string())])  # an error has no offset
        n = nd + ne
        tables.append(pa.table({"split": at.const(split, n, pa.string()), "part": at.const(part, n, pa.string()),
                                "doc_id": doc, "f2_items": pc.fill_null(items, ""), "offset": pc.fill_null(offset, "")}))
    if len(sets) != 1 or None in sets:
        raise Stop(f"the F2 reports name {len(sets)} different set_sha256 values: {sorted(map(str, sets))}")
    empty = pa.table({c: pa.array([], pa.string()) for c in ("split", "part", "doc_id", "f2_items", "offset")})
    gone = pa.concat_tables(tables) if tables else empty
    # a doc_id listed twice in a report (dropped twice, or dropped and an error) would double a survivor: keep one, the
    # last (errors come after drops), as a dict keyed on doc_id did
    gone = gone.group_by(["split", "part", "doc_id"], use_threads=False).aggregate(
        [("f2_items", "last"), ("offset", "last")]).rename_columns(["split", "part", "doc_id", "f2_items", "offset"])
    return gone, sets.pop(), covered


def report(groups_csv, final, out):
    groups_csv, out = Path(groups_csv), Path(out)
    groups = read_groups(groups_csv)
    groups = groups.append_column("_row", at.arange(groups.num_rows))  # the CSV's order, kept within a group
    gone, set_sha, covered = read_f2(final)
    survivors = groups.filter(pc.equal(groups["role"], "survivor"))
    need = survivors.group_by(["split", "part"]).aggregate([]) if survivors.num_rows else None
    if need is not None:
        have = pa.table({"split": pa.array([c[0] for c in covered], pa.string()),
                         "part": pa.array([c[1] for c in covered], pa.string()), "_r": at.const(True, len(covered), pa.bool_())})
        miss = need.join(have, ["split", "part"], join_type="left outer").filter(pc.is_null(pc.field("_r")))
        if miss.num_rows:
            miss = miss.sort_by([("split", "ascending"), ("part", "ascending")])
            raise Stop(f"{miss.num_rows} part(s) hold a dedup survivor but have no F2 report, e.g. "
                       f"{miss['split'][0]}/{miss['part'][0]}: F2 did not cover them")

    hit = survivors.join(gone, ["split", "part", "doc_id"], join_type="left outer")
    hit = hit.append_column("_hit", pc.is_valid(hit["f2_items"]))
    per_group = hit.group_by("group_id").aggregate([([], "count_all"), ("_hit", "sum")]) if hit.num_rows else None
    all_groups = pc.count_distinct(groups["group_id"]).as_py() if groups.num_rows else 0
    counts = {"total": all_groups, "with_survivor": 0, "without_survivor": all_groups, "with_several_survivors": 0,
              "lost": 0, "partly_hit": 0, "untouched": 0}
    rows = pa.table({c: pa.array([], pa.string()) for c in OUT_COLUMNS})
    by_pack = {}
    if per_group is not None:
        n_surv, n_hit = per_group["count_all"], pc.fill_null(per_group["_hit_sum"], 0)
        status = pc.if_else(pc.equal(n_hit, 0), "untouched", pc.if_else(pc.equal(n_hit, n_surv), "lost", "partly_hit"))
        per_group = per_group.append_column("status", status)
        counts["with_survivor"] = per_group.num_rows
        counts["without_survivor"] = all_groups - per_group.num_rows
        counts["with_several_survivors"] = at.count(pc.greater(n_surv, 1))
        for s in ("lost", "partly_hit", "untouched"):
            counts[s] = at.count(pc.equal(status, s))
        dropped = hit.filter(hit["_hit"]).join(per_group.select(["group_id", "status"]), "group_id")
        # groups by (length of group_id, group_id), so G9 comes before G10, and within a group in the CSV's order
        dropped = dropped.append_column("_len", pc.utf8_length(dropped["group_id"]))
        dropped = dropped.sort_by([("_len", "ascending"), ("group_id", "ascending"), ("_row", "ascending")])
        rows = pa.table({c: (pc.cast(dropped[c], pa.string()) if c in ("group_size", "priority_rule", "row_in_part")
                             else dropped[c]) for c in OUT_COLUMNS})
        for g in dropped.group_by(["pack_id", "status"]).aggregate([([], "count_all")]).to_pylist():  # per pack
            by_pack.setdefault(g["pack_id"], {"lost": 0, "partly_hit": 0})[g["status"]] += g["count_all"]

    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "survivor_loss.csv.tmp"
    with tmp.open("w", newline="", encoding="utf-8") as f:  # csv quoting, as before; the rows are only the dropped survivors
        w = csv.writer(f)
        w.writerow(OUT_COLUMNS)
        w.writerows(zip(*(rows[c].to_pylist() for c in OUT_COLUMNS)))
    tmp.replace(out / "survivor_loss.csv")
    summary = {"tool": "survivor_loss.py", "code_sha256": code_sha256(Path(__file__))[0], "groups_sha256": sha256(groups_csv),
               "set_sha256": set_sha, "f2_reports": len(covered), "groups": counts,
               "survivors_dropped_by_f2": rows.num_rows,
               "survivor_rows_by_pack": {p: by_pack[p] for p in sorted(by_pack)}}
    tmp = out / "survivor_loss_summary.json.tmp"
    tmp.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(out / "survivor_loss_summary.json")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--groups", type=Path, required=True, help="dedup.py's dedup_groups.csv")
    ap.add_argument("--f2", type=Path, required=True, help="F2's output folder: <split>/<part>.f2.json")
    ap.add_argument("--out", type=Path, required=True, help="where survivor_loss.csv and the summary go")
    args = ap.parse_args()
    try:
        s = report(args.groups, args.f2, args.out)
    except Stop as e:
        sys.exit(f"survivor_loss: {e}")
    print(json.dumps({**s["groups"], "survivors_dropped_by_f2": s["survivors_dropped_by_f2"]}))


if __name__ == "__main__":
    main()
