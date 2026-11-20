"""The ledger: every document's decision at every stage (cleaner, dedup, F2) and where it ended up, one row per document.

  python -I teams/01-data-a/pipeline/ledger.py --cleaned <cleaned_dir> --remove-list <remove_list.csv>
         --groups <dedup_groups.csv> --f2 <final_dir> --out <dir> [--log <dedup_log.jsonl>] [--raw <raw_dir>]

It decides nothing. It reads what each stage wrote (the cleaned parts, dedup's remove list, groups and log, F2's reports
and final parts) and puts the decisions side by side, so anyone can ask "what happened to doc X, and why?" or count the
outcomes per pack. It is built part by part with pyarrow joins and compute functions: no Python loop over documents.

INPUT
=====
--cleaned   the cleaned parts: <cleaned>/<split>/<part>, as overlap.py and apply_dedup.py read them
--raw       (optional) the raw parts the cleaner read. With the cleaning job's report for a part, the raw file is the one
            whose sha256 is the report's input_sha256, under <raw>/<split>/<pack>/ or <raw>/<pack>/<split>/ (any file
            name, as run_tokenizer_sample.py finds it). Every cleaned part needs that report in mode B: without it
            the ledger stops rather than match a raw file by name and skip the check of the cleaner's drops
--remove-list, --groups, --log   dedup.py's remove_list.csv, dedup_groups.csv and dedup_log.jsonl (the log is optional)
--f2        F2's output folder: <final>/<split>/<part> and <final>/<split>/<part>.f2.json

THE CLEANER'S DECISION (clean_action), by what is available
==========================================================
  mode B  --raw given: each raw part is joined to its cleaned part on doc_id (unique within a part: the cleaner refuses
          duplicates). Not in the cleaned part: drop. In it with other text: fix. Same text: keep. No rule ids.
  mode C  no --raw: the ledger starts at the cleaned documents and clean_action is "unknown".
  (mode A, a per-document decisions file from the cleaning job with rule ids, is not available yet: clean_rules stays empty.)
The cleaning job's per-part reports (<cleaned>/reports/<split>/<part>.json with "input_rows", "actions" and
"input_sha256") are required in mode B, which checks its drops and rows against them; mode C records their counts
when they are there.

COLUMNS (IDs, codes and counts only, never text)
================================================
  pack_id, split, part        the document's pack, split and part (the cleaned part's path within its split folder)
  raw_row                     its row in the raw part (mode B; empty in mode C)
  row_in_part                 its row in the cleaned part, as dedup numbers it (empty when the cleaner dropped it)
  doc_id
  clean_action, clean_rules   keep, fix, drop or unknown; rule ids (mode A only)
  dedup_role                  none, survivor or removed (dedup_groups.csv)
  dedup_group, dedup_priority_rule        e.g. G000123 and 0-4 (source_priority_v1.md)
  dedup_match_rule, dedup_similarity, dedup_kept_doc, dedup_stage   from dedup_log.jsonl, for removed documents
  dedup_list                  which remove list removed it ("dedup": dedup.py's remove_list.csv)
  f2_action                   kept, dropped or error (empty when F2 never saw it)
  f2_items, f2_offset         benchmark item ids (space-separated; "error:<type>" for an error) and the char offset
  final                       kept, dropped_by_clean, removed_by_dedup, dropped_by_f2 or f2_error: exactly one per document
  final_part, final_row       where a kept document is in the final parts (<final>/<split>/<final_part>, 0-based row)

CHECKS (any failure stops the run; exit code 1)
==============================================
  - every row the remove list, the groups or the log names is a row of its cleaned part, with the same doc_id, and
    none of them names a row twice (so no cleaned row is in two groups)
  - the groups' removed rows, and the log's rows when there is a log, are exactly the remove list's rows
  - doc_id is unique within each cleaned (and raw) part; mode B: every cleaned doc is in its raw part
  - every F2 report covers its part: its rows = the rows apply kept there, and every doc_id it drops or errors on is
    one of them; all reports name one set_sha256
  - each final part holds exactly the ledger's kept documents of that part, in the same order
  - mode B with cleaning reports: the ledger's drops per part = the report's drops, and its rows = the report's input rows

OUTPUT (in --out)
=================
  <split>/<pack>.parquet   the ledger, one file per pack and split (zstd)
  ledger_summary.json      clean mode, inputs (sha256), totals and counts per pack and split by final status, files,
                           and survivors_dropped_by_f2: the dedup survivors whose final is dropped_by_f2 or f2_error,
                           in total and per pack (the runner checks them against survivor_loss.py's report)
  ledger_sample.csv        to read by eye: per pack and split, up to 5 rows of each final status
The ledger is built in <out>.partial and swapped in for <out> only when it is complete, so --out never mixes two runs
and a run that stops leaves the previous ledger whole. The swap renames --out to <out>.old, <out>.partial to --out, and
deletes <out>.old. Windows will not rename a folder while a file in it is open (a notebook reading the ledger, a virus
scan), so each rename is retried for a while; if the swap still fails, --out is renamed back (the previous ledger), the
new one stays in <out>.partial, and the run stops saying so. A run killed between the two renames leaves the previous
ledger in <out>.old; the next run puts it back first. --out must be missing, empty or an earlier ledger (it holds
ledger_summary.json); anything else stops the run before anything is touched. The ledger only ever deletes folders it
made: <out>.partial holds a marker file (.ledger_partial) from the moment it is made, and <out>.old is an earlier
ledger; any other folder by those names stops the run untouched. No input (--cleaned, --remove-list, --groups, --f2,
--log, --raw) may be or hold --out, <out>.partial, <out>.old or <out>.lock, nor lie inside them. One run at a time may write --out
(runlock.py). In mode B the summary lists every raw file used with its sha256.

SPEED AND SCALE
===============
Part by part, with pyarrow joins and compute functions. Mode B compares texts in batches of about 32 MiB of decoded
text (at most 8,192 rows; arrowtools.iter_sized sizes each read from the text seen so far) while it reads both parts (the cleaner keeps raw order, so the k-th kept raw row is
the k-th cleaned row); only a cleaned part that is not in raw order falls back to holding both texts at once. The sample is taken by index, so it holds a few rows, not
the tables they came from. The dedup inputs are read once and cut by part.
"""
import sys
sys.dont_write_bytecode = True

import argparse, hashlib, json, os, shutil, time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import arrowtools as at  # noqa: E402
import runlock  # noqa: E402
from hashing import code_sha256  # noqa: E402

SPLITS = ("train", "heldout")
FINAL = ("kept", "dropped_by_clean", "removed_by_dedup", "dropped_by_f2", "f2_error")
SUFFIX = ".f2.json"
REMOVE_HEADER = ["pack_id", "split", "part", "row_in_part", "doc_id"]
GROUP_HEADER = ["group_id", "group_size", "priority_rule", "role", "pack_id", "split", "part", "row_in_part", "doc_id"]
SAMPLE_PER_STATUS = 5
LIST_LABEL = "dedup"
TEXT_BATCH = 8192  # at most this many rows of text held at a time in mode B ...
TEXT_BYTES = 32 << 20  # ... and about this many bytes of decoded text (arrowtools.iter_sized)
READ_BUFFER = 8 << 20  # column chunks are read through a buffer of this size, never whole
RENAME_TRIES = 20  # each rename of the swap is tried this often ...
RENAME_WAIT = 0.5  # ... this many seconds apart, while Windows says a file in the folder is open


class Stop(Exception):
    """A check failed: the message says which and where."""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def schema():
    import pyarrow as pa
    s, i, f = pa.string(), pa.int64(), pa.float64()
    return pa.schema([
        ("pack_id", s), ("split", s), ("part", s), ("raw_row", i), ("row_in_part", i), ("doc_id", s),
        ("clean_action", s), ("clean_rules", s),
        ("dedup_role", s), ("dedup_group", s), ("dedup_priority_rule", i),
        ("dedup_match_rule", s), ("dedup_similarity", f), ("dedup_kept_doc", s), ("dedup_stage", s), ("dedup_list", s),
        ("f2_action", s), ("f2_items", s), ("f2_offset", i),
        ("final", s), ("final_part", s), ("final_row", i)])


opened, as_str, const, count = at.opened, at.as_str, at.const, at.count


def read_columns(path, columns):
    return at.read_columns(path, columns, Stop)


def arange(n):
    return at.arange(n)


# --- the dedup and F2 inputs ----------------------------------------------------------------------------------------
def read_csv(path, header, ints=("row_in_part",)):
    """A CSV as a pyarrow Table with every column a string except the ints, and part written with /. A quoted value may
    hold a newline."""
    import pyarrow as pa
    return at.posix(at.read_csv(Path(path), header, {c: pa.int64() for c in ints}, Stop))


def read_log(path):
    """dedup_log.jsonl as a Table: split, part, row_in_part, doc_id, match rule, similarity, kept doc, stage."""
    import pyarrow as pa, pyarrow.compute as pc, pyarrow.json as pj
    cols = {"removed_split": ("split", pa.string()), "removed_part": ("part", pa.string()),
            "removed_row_in_part": ("row_in_part", pa.int64()), "removed_id": ("log_doc", pa.string()),
            "rule": ("dedup_match_rule", pa.string()), "similarity": ("dedup_similarity", pa.float64()),
            "kept_id": ("dedup_kept_doc", pa.string()), "stage": ("dedup_stage", pa.string())}
    if Path(path).stat().st_size == 0:
        return pa.table({new: pa.array([], t) for new, t in cols.values()})
    t = pj.read_json(path, parse_options=pj.ParseOptions(explicit_schema=pa.schema([(k, t) for k, (_, t) in cols.items()]),
                                                          unexpected_field_behavior="ignore"))
    t = t.select(list(cols)).rename_columns([new for new, _ in cols.values()])
    return t.set_column(t.schema.get_field_index("part"), "part", pc.replace_substring(t.column("part"), "\\", "/"))


def by_part(table):
    """{(split, part): the table's rows for that part}. Loops over parts, not rows (arrowtools.by_part)."""
    return at.by_part(table)


def read_f2_report(path):
    """(F2 table: doc_id, f2_action, f2_items, f2_offset; the report)."""
    import pyarrow as pa, pyarrow.compute as pc
    rep = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = rep.get("errors") if isinstance(rep.get("errors"), list) else []
    d = pa.array(rep.get("dropped") or [], pa.struct([("doc_id", pa.string()), ("items", pa.list_(pa.string())),
                                                      ("offset", pa.int64())]))
    e = pa.array(errors, pa.list_(pa.string()))
    nd, ne = len(d), len(e)
    dropped = pa.table({"doc_id": pc.struct_field(d, "doc_id"), "f2_action": const("dropped", nd, pa.string()),
                        "f2_items": pc.binary_join(pc.struct_field(d, "items"), " "),
                        "f2_offset": pc.struct_field(d, "offset")})
    errs = pa.table({"doc_id": pc.list_element(e, 0) if ne else pa.array([], pa.string()),
                     "f2_action": const("error", ne, pa.string()),
                     "f2_items": pc.binary_join_element_wise("error:", pc.list_element(e, 1), "") if ne
                     else pa.array([], pa.string()),
                     "f2_offset": pa.nulls(ne, pa.int64())})
    return pa.concat_tables([dropped, errs]), rep


# --- the cleaner's decision -----------------------------------------------------------------------------------------
def find_raw(raw, split, part, rep, hashes):
    """(raw file, its sha256) for a cleaned part. With the cleaning report's input_sha256: the file with that sha256 under
    <raw>/<split>/<pack>/ or <raw>/<pack>/<split>/, any name (as run_tokenizer_sample.py's resolve_input). Without it:
    the file of the same name. hashes caches sha256 per file, so a folder is hashed once."""
    pack, _, rest = part.partition("/")
    named = [raw / split / part] + ([raw / pack / split / rest] if rest else [])

    def digest_of(f):
        if f not in hashes:
            hashes[f] = sha256(f)
        return hashes[f]

    want = (rep or {}).get("input_sha256")
    if not want:
        for cand in named:
            if cand.is_file():
                return cand, digest_of(cand)
        raise Stop(f"--raw {raw}: no raw part for {split}/{part} (looked for {split}/{part}"
                   + (f" and {pack}/{split}/{rest}" if rest else "") + ", and there is no cleaning report to match by sha256)")
    folders = [raw / split / pack, raw / pack / split] if rest else [raw / split]
    for cand in dict.fromkeys(named + [f for d in folders if d.is_dir() for f in sorted(d.glob("*.parquet"))]):
        if cand.is_file() and digest_of(cand) == want:
            return cand, want
    raise Stop(f"--raw {raw}: no raw part has the sha256 the cleaning report names for {split}/{part} ({want[:12]}…): "
               "these are not the raw parts this cleaning run read")


def clean_report(cleaned, split, part):
    """The cleaning job's report for a part ({"input_rows", "actions"}), or None if there is none in that shape."""
    p = cleaned / "reports" / split / (part + ".json")
    if not p.is_file():
        return None
    try:
        r = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return r if isinstance(r.get("actions"), dict) and "input_rows" in r else None


def col_or_null(t, name, typ=None):
    import pyarrow as pa
    return t.column(name) if name in t.column_names else pa.nulls(t.num_rows, typ or pa.string())


def base_table(cleaned_path, raw_file, split, part):
    """One row per document of the part: pack_id, raw_row, row_in_part, doc_id, clean_action. Mode B with raw_file."""
    import pyarrow as pa, pyarrow.compute as pc
    if raw_file is None:
        c = read_columns(cleaned_path, ["doc_id", "pack_id"])
        n = c.num_rows
        unique(c.column("doc_id"), f"{split}/{part}")
        no_pack(c.column("pack_id"), f"{split}/{part}")
        return pa.table({"pack_id": as_str(c.column("pack_id")), "raw_row": pa.nulls(n, pa.int64()),
                         "row_in_part": arange(n), "doc_id": as_str(c.column("doc_id")),
                         "clean_action": const("unknown", n, pa.string())})
    c = read_columns(cleaned_path, ["doc_id"])  # ids first: the texts are compared in batches below
    r = read_columns(raw_file, ["doc_id", "pack_id"])
    unique(c.column("doc_id"), f"{split}/{part}")
    unique(r.column("doc_id"), f"raw {split}/{part}")
    no_pack(r.column("pack_id"), f"raw {split}/{part}")
    rix = pa.table({"doc_id": as_str(r.column("doc_id")), "raw_row": arange(r.num_rows)})
    cix = pa.table({"doc_id": as_str(c.column("doc_id")), "row_in_part": arange(c.num_rows)})
    j = rix.join(cix, "doc_id", join_type="left outer").sort_by("raw_row")
    rip, matched = j.column("row_in_part"), pc.is_valid(j.column("row_in_part"))
    if count(matched) != c.num_rows:
        raise Stop(f"{split}/{part}: {c.num_rows - count(matched)} cleaned doc(s) are not in the raw part {raw_file}: "
                   "the raw and cleaned parts are from different runs")
    in_order = c.num_rows == 0 or pc.all(pc.equal(rip.filter(matched), arange(c.num_rows))).as_py()
    same = (same_text_streamed(raw_file, cleaned_path, matched) if in_order
            else same_text_in_memory(raw_file, cleaned_path, rip))
    action = pc.if_else(matched, pc.if_else(same, "keep", "fix"), "drop")
    return pa.table({"pack_id": as_str(r.column("pack_id")), "raw_row": j.column("raw_row"), "row_in_part": rip,
                     "doc_id": j.column("doc_id"), "clean_action": action})


def same_text_streamed(raw_file, cleaned_file, matched):
    """Per raw row: does its text equal its cleaned text? For a cleaned part in raw order: the k-th matched raw row is
    cleaned row k, so both files are read in batches of TEXT_BATCH rows and compared as they come. False where the
    cleaner dropped the row."""
    import pyarrow as pa, pyarrow.compute as pc
    matched = at.flat(matched)
    out, offset, buf, pos = [], 0, None, 0
    with opened(raw_file, READ_BUFFER) as rf, opened(cleaned_file, READ_BUFFER) as cf:
        for f, pf in ((raw_file, rf), (cleaned_file, cf)):
            if "text" not in pf.schema_arrow.names:
                raise Stop(f"{f}: no text column (mode B compares the raw and cleaned texts)")
        cleaned_batches = at.iter_sized(cf, TEXT_BYTES, TEXT_BATCH, ["text"])
        for rb in at.iter_sized(rf, TEXT_BYTES, TEXT_BATCH, ["text"]):
            n = rb.num_rows
            m = matched.slice(offset, n)
            offset += n
            rt = rb.column(0).filter(m)
            need, pieces = len(rt), []
            while need:
                if buf is None or pos >= len(buf):
                    buf, pos = next(cleaned_batches).column(0), 0
                take = min(need, len(buf) - pos)
                pieces.append(buf.slice(pos, take))
                pos, need = pos + take, need - take
            ct = pa.concat_arrays(pieces) if pieces else pa.array([], rt.type)
            if ct.type != rt.type:
                rt, ct = rt.cast(pa.large_string()), ct.cast(pa.large_string())
            eq = pc.fill_null(pc.equal(rt, ct), False)
            out.append(pc.replace_with_mask(const(False, n, pa.bool_()), pc.fill_null(m, False), eq) if n else eq)
    return pa.chunked_array(out, pa.bool_()) if out else pa.chunked_array([], pa.bool_())


def same_text_in_memory(raw_file, cleaned_file, rip):
    """The same comparison when the cleaned part is not in raw order: both text columns at once."""
    import pyarrow as pa, pyarrow.compute as pc
    rt = read_columns(raw_file, ["text"]).column("text")
    ct = read_columns(cleaned_file, ["text"]).column("text").take(rip)  # null where the cleaner dropped the doc
    if ct.type != rt.type:
        rt, ct = rt.cast(pa.large_string()), ct.cast(pa.large_string())
    return pc.fill_null(pc.equal(rt, ct), False)


def unique(arr, where):
    import pyarrow.compute as pc
    if pc.count_distinct(as_str(arr), mode="all").as_py() != len(arr):
        raise Stop(f"{where}: a doc_id appears twice in the part, so documents cannot be matched by doc_id")


def no_pack(arr, where):
    import pyarrow.compute as pc
    if arr.null_count:
        raise Stop(f"{where}: {arr.null_count} row(s) have no pack_id")


# --- one part -------------------------------------------------------------------------------------------------------
def attach(base, right, name, key_doc, where):
    """Left-join the part's rows of a dedup input on row_in_part; every one of them must land on a row with its doc_id."""
    import pyarrow.compute as pc
    if right is None or right.num_rows == 0:
        return base
    twice = right.num_rows - pc.count_distinct(right.column("row_in_part"), mode="all").as_py()
    if twice:
        raise Stop(f"{where}: {name} names {twice} row(s) of this part more than once (a row in two groups, or listed twice)")
    j = base.join(right, "row_in_part", join_type="left outer")
    hit = pc.is_valid(j.column(key_doc))
    if (pc.sum(hit).as_py() or 0) != right.num_rows:
        raise Stop(f"{where}: {right.num_rows - (pc.sum(hit).as_py() or 0)} row(s) of {name} are not rows of this "
                   "cleaned part (row_in_part past the end)")
    bad = pc.sum(pc.and_(hit, pc.not_equal(j.column(key_doc), j.column("doc_id")))).as_py() or 0
    if bad:
        raise Stop(f"{where}: {bad} row(s) of {name} name another doc_id than the cleaned part holds at that row. "
                   "It was made from another cleaning run than these parts")
    return j.drop_columns([key_doc])


def part_ledger(cleaned_path, raw_file, split, part, removes, groups, log, f2_dir):
    """The ledger rows of one part (in raw_row / row_in_part order) and the F2 report's set_sha256."""
    import pyarrow as pa, pyarrow.compute as pc
    where = f"{split}/{part}"
    base = base_table(cleaned_path, raw_file, split, part)
    order = "raw_row" if raw_file is not None else "row_in_part"

    rem = removes.get((split, part))
    if rem is not None:
        rem = pa.table({"row_in_part": rem.column("row_in_part"), "rem_doc": rem.column("doc_id"),
                        "dedup_list": const(LIST_LABEL, rem.num_rows, pa.string())})
    base = attach(base, rem, "the remove list", "rem_doc", where)
    grp = groups.get((split, part))
    if grp is not None:
        grp = pa.table({"row_in_part": grp.column("row_in_part"), "grp_doc": grp.column("doc_id"),
                        "dedup_role": grp.column("role"), "dedup_group": grp.column("group_id"),
                        "dedup_priority_rule": pc.cast(grp.column("priority_rule"), pa.int64())})
    base = attach(base, grp, "dedup_groups.csv", "grp_doc", where)
    lg = log.get((split, part)) if log is not None else None
    if lg is not None:
        lg = lg.select(["row_in_part", "log_doc", "dedup_match_rule", "dedup_similarity", "dedup_kept_doc", "dedup_stage"])
        lg = lg.append_column("_log", const(True, lg.num_rows, pa.bool_()))
    base = attach(base, lg, "dedup_log.jsonl", "log_doc", where)
    base = base.sort_by(order)

    n = base.num_rows
    clean_drop = pc.equal(base.column("clean_action"), "drop")
    role = base.column("dedup_role") if "dedup_role" in base.column_names else pa.nulls(n, pa.string())
    in_rem = pc.is_valid(col_or_null(base, "dedup_list"))
    k = count(pc.xor(in_rem, pc.fill_null(pc.equal(role, "removed"), False)))
    if k:
        raise Stop(f"{where}: {k} row(s) are removed in one of remove_list.csv and dedup_groups.csv but not the other")
    if log is not None:
        k = count(pc.xor(in_rem, pc.is_valid(col_or_null(base, "_log", pa.bool_()))))
        if k:
            raise Stop(f"{where}: {k} row(s) are in one of remove_list.csv and dedup_log.jsonl but not the other "
                       "(the log has one row per removed document)")
        if "_log" in base.column_names:
            base = base.drop_columns(["_log"])

    # F2: what apply kept of this part went through F2 as <f2>/<split>/<part>
    rep_path = f2_dir / split / (part + SUFFIX)
    after_dedup = pc.and_(pc.invert(clean_drop), pc.invert(in_rem))
    if not rep_path.is_file():
        raise Stop(f"{where}: no F2 report ({rep_path}): F2 did not cover this part")
    f2t, rep = read_f2_report(rep_path)
    if rep.get("rows") != count(after_dedup):
        raise Stop(f"{where}: F2's report has {rep.get('rows')} rows, apply kept {count(after_dedup)} of this part")
    if f2t.num_rows:
        unique(f2t.column("doc_id"), f"F2 report {where}")
        base = base.append_column("_seen", after_dedup)
        j = base.join(f2t, "doc_id", join_type="left outer")
        ok = count(pc.and_(pc.is_valid(j.column("f2_action")), j.column("_seen")))
        if ok != f2t.num_rows:
            raise Stop(f"{where}: {f2t.num_rows - ok} doc_id(s) in F2's report are not among the rows apply kept here")
        base = j.sort_by(order)
        after_dedup = base.column("_seen")
        base = base.drop_columns(["_seen"])
        clean_drop, in_rem = pc.equal(base.column("clean_action"), "drop"), pc.is_valid(col_or_null(base, "dedup_list"))
        role = col_or_null(base, "dedup_role")

    def col(name, typ):
        return base.column(name) if name in base.column_names else pa.nulls(n, typ)

    f2a = col("f2_action", pa.string())
    nul = pa.nulls(n, pa.string())
    f2_action = pc.if_else(after_dedup, pc.fill_null(f2a, "kept"), nul)
    f2_final = pc.if_else(pc.equal(f2a, "dropped"), "dropped_by_f2", pc.if_else(pc.equal(f2a, "error"), "f2_error", "kept"))
    final = pc.if_else(clean_drop, "dropped_by_clean",
                       pc.if_else(in_rem, "removed_by_dedup", pc.fill_null(f2_final, "kept")))
    kept = pc.equal(final, "kept")
    # apply and F2 keep the cleaned order, so a kept document's row in the final part is its rank by row_in_part among
    # the kept rows (in mode C the rows are already in that order; in mode B they are in raw order)
    kept_rip = base.column("row_in_part").filter(kept)
    by_cleaned = pc.sort_indices(kept_rip)
    if order == "row_in_part" or count(kept) == 0:
        final_row = pc.if_else(kept, pc.subtract(pc.cumulative_sum(pc.cast(kept, pa.int64())), 1), pa.nulls(n, pa.int64()))
    else:
        ranks = pc.cast(pc.subtract(pc.rank(kept_rip, sort_keys="ascending", tiebreaker="first"), 1), pa.int64())
        final_row = pc.replace_with_mask(pa.nulls(n, pa.int64()), at.flat(pc.fill_null(kept, False)), at.flat(ranks))

    out_part = f2_dir / split / part
    if count(kept) or out_part.is_file():
        got = read_columns(out_part, ["doc_id"]).column("doc_id") if out_part.is_file() else None
        want = base.column("doc_id").filter(kept).take(by_cleaned)  # in final-part order
        same = got is not None and len(got) == len(want) and (len(want) == 0 or pc.all(pc.equal(as_str(got), want)).as_py())
        if not same:
            raise Stop(f"{where}: the final part {out_part} does not hold the ledger's {len(want)} kept documents in order")

    table = pa.table({
        "pack_id": base.column("pack_id"), "split": const(split, n, pa.string()),
        "part": const(part, n, pa.string()), "raw_row": base.column("raw_row"),
        "row_in_part": base.column("row_in_part"), "doc_id": base.column("doc_id"),
        "clean_action": base.column("clean_action"), "clean_rules": pa.nulls(n, pa.string()),
        "dedup_role": pc.if_else(clean_drop, pa.nulls(n, pa.string()), pc.fill_null(role, "none")),
        "dedup_group": col("dedup_group", pa.string()), "dedup_priority_rule": col("dedup_priority_rule", pa.int64()),
        "dedup_match_rule": col("dedup_match_rule", pa.string()), "dedup_similarity": col("dedup_similarity", pa.float64()),
        "dedup_kept_doc": col("dedup_kept_doc", pa.string()), "dedup_stage": col("dedup_stage", pa.string()),
        "dedup_list": col("dedup_list", pa.string()),
        "f2_action": f2_action, "f2_items": col("f2_items", pa.string()), "f2_offset": col("f2_offset", pa.int64()),
        "final": final, "final_part": pc.if_else(kept, part, nul), "final_row": final_row}, schema=schema())
    return table, rep.get("set_sha256")


# --- the whole ledger -----------------------------------------------------------------------------------------------
def find_parts(cleaned):
    parts = [(split, f.relative_to(cleaned / split).as_posix(), f) for split in SPLITS if (cleaned / split).is_dir()
             for f in sorted((cleaned / split).rglob("*.parquet")) if f.is_file()]
    if not parts:
        raise Stop(f"--cleaned {cleaned}: no Parquet parts under train/ or heldout/")
    return parts


STAGING_MARK = ".ledger_partial"  # in <out>.partial from the moment build() makes it: the folder is ours to delete
OLD_MARK = ".ledger_old"  # in an <out>.old that publish() could only partly delete


def is_ledger(folder):
    """A folder build() may replace: missing, empty, or holding ledger_summary.json."""
    return not folder.exists() or (folder.is_dir() and (not any(folder.iterdir()) or (folder / "ledger_summary.json").is_file()))


def is_ours(folder, mark):
    """A folder build() made: it holds ledger_summary.json or the marker file, or it is empty."""
    return folder.is_dir() and (not any(folder.iterdir()) or (folder / mark).is_file()
                                or (folder / "ledger_summary.json").is_file())


def overlap(a, b):
    a, b = Path(a).resolve(), Path(b).resolve()
    return a == b or a in b.parents or b in a.parents


def check_paths(out, inputs):
    """Stop, before anything is touched, when an input is or holds --out or a folder or file the ledger makes or
    deletes next to it, or lies inside one; and when <out>.partial or <out>.old is a folder the ledger did not make."""
    stage, old = out.with_name(out.name + ".partial"), out.with_name(out.name + ".old")
    ours = {"--out": out, "the staging folder": stage, "the backup folder": old, "the lock file": runlock.lock_path(out)}
    for name, p in inputs.items():
        if p is None:
            continue
        for what, q in ours.items():
            if overlap(p, q):
                raise Stop(f"{name} {p} and {what} {q} overlap: the ledger writes, swaps and deletes there, so it would "
                           "change its own input. Use another --out")
    if not is_ledger(out):
        raise Stop(f"--out {out} exists and is not a ledger folder (it has no ledger_summary.json): use a new --out")
    for folder, mark in ((stage, STAGING_MARK), (old, OLD_MARK)):
        if folder.exists() and not is_ours(folder, mark):
            raise Stop(f"{folder} exists and is not a folder the ledger made (no {mark} or ledger_summary.json): the "
                       "ledger deletes that folder, so move it away or use another --out")


def build(cleaned, remove_list, groups_csv, f2, out, log=None, raw=None):
    """Write the ledger to out: built in <out>.partial under out's lock, then swapped in whole. Returns the summary.
    Raises Stop on any failed check (out is then left as it was)."""
    out = Path(out)
    inputs = {"--cleaned": cleaned, "--remove-list": remove_list, "--groups": groups_csv, "--f2": f2, "--log": log,
              "--raw": raw}
    check_paths(out, inputs)
    try:
        with runlock.exclusive(out):
            check_paths(out, inputs)  # again under the lock: nothing changed it in between
            stage, old = out.with_name(out.name + ".partial"), out.with_name(out.name + ".old")
            if not out.exists() and old.is_dir() and (old / "ledger_summary.json").is_file():
                retry(os.replace, old, out)  # a run killed between the two renames of publish(): the previous ledger
            if stage.exists():  # left by a killed run, and ours (check_paths)
                retry(shutil.rmtree, stage)
            stage.mkdir(parents=True)
            (stage / STAGING_MARK).write_text("made by ledger.py; deleted with the folder\n", encoding="utf-8")
            built = False
            try:
                summary = _build(cleaned, remove_list, groups_csv, f2, stage, log, raw)
                built = True
                publish(stage, out)
                return summary
            finally:
                if not built:  # half a ledger: nothing to keep (a complete one that could not be swapped in stays)
                    remove_marked(stage, STAGING_MARK)
    except runlock.Busy as e:
        raise Stop(str(e)) from None


def retry(fn, *args):
    """fn(*args), tried RENAME_TRIES times while it raises PermissionError: Windows refuses to rename or delete a folder
    while a file in it is open, and a reader or a virus scan lets go after a moment."""
    for i in range(RENAME_TRIES):
        try:
            return fn(*args)
        except PermissionError:
            if i == RENAME_TRIES - 1:
                raise
            time.sleep(RENAME_WAIT)


def publish(stage, out):
    """Replace out by stage: out moves aside to <out>.old, stage takes its name, <out>.old is deleted. If stage cannot
    take its name, out is renamed back, stage stays as it is, and Stop says so: --out always holds a whole ledger, the
    previous one or the new one. (A crash between the renames leaves the previous ledger in <out>.old, which build()
    puts back first.)"""
    old = out.with_name(out.name + ".old")
    try:
        if old.exists():
            retry(shutil.rmtree, old)
        moved = False
        if out.exists():
            retry(os.replace, out, old)
            moved = True
        try:
            (stage / STAGING_MARK).unlink(missing_ok=True)  # the published ledger holds only the ledger
            retry(os.replace, stage, out)
        except OSError:
            if moved:
                retry(os.replace, old, out)
            raise
    except OSError as e:
        where = f"the previous ledger is in {old}; rename it to {out}" if old.exists() and not out.exists() else \
            f"the previous ledger is still in {out}"
        raise Stop(f"could not swap the new ledger in for {out} ({type(e).__name__}: {e}). Is a file in it open? "
                   f"Nothing was lost: {where}, and the new one is in {stage}") from None
    try:  # first the summary, so a .old that could only be partly deleted is never taken for a whole ledger ...
        (old / OLD_MARK).write_text("made by ledger.py; an earlier ledger being deleted\n", encoding="utf-8")
        (old / "ledger_summary.json").unlink(missing_ok=True)
    except OSError:
        pass
    remove_marked(old, OLD_MARK)  # ... and the marker, deleted last, says it is ours if anything is left


def remove_marked(folder, mark):
    """Delete a folder the ledger made, its marker file last, and only once nothing else is left in it: whatever a failed
    delete leaves (Windows: a file still open) still carries the marker, so the next run knows the folder is the
    ledger's and deletes it instead of stopping. Returns True when the folder is gone."""
    if not folder.is_dir():
        return True
    for child in folder.iterdir():
        if child.name == mark:
            continue
        try:
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
        except OSError:
            pass
    try:
        if any(child.name != mark for child in folder.iterdir()):
            return False  # something could not be deleted: the marker stays with it
        (folder / mark).unlink(missing_ok=True)
        folder.rmdir()
        return True
    except OSError:
        return False


def _build(cleaned, remove_list, groups_csv, f2, out, log=None, raw=None):
    import pyarrow as pa, pyarrow.compute as pc, pyarrow.csv as pcsv, pyarrow.parquet as pq
    cleaned, remove_list, groups_csv, f2, out = map(Path, (cleaned, remove_list, groups_csv, f2, out))
    raw = Path(raw) if raw else None
    log = Path(log) if log else None
    if raw is not None and not raw.is_dir():
        raise Stop(f"--raw {raw} is not a folder")
    parts = find_parts(cleaned)
    known = {(s, p) for s, p, _ in parts}
    removes = by_part(read_csv(remove_list, REMOVE_HEADER))
    groups_t = read_csv(groups_csv, GROUP_HEADER, ints=("row_in_part", "group_size", "priority_rule"))
    groups_rows, removed_role = groups_t.num_rows, count(pc.equal(groups_t.column("role"), "removed"))
    groups = by_part(groups_t)
    del groups_t  # by_part holds a sorted copy; the unsorted table is not needed again
    log_t = read_log(log) if log is not None else None
    log_rows = log_t.num_rows if log_t is not None else 0
    logs = by_part(log_t) if log_t is not None else None
    del log_t
    for name, d in (("remove_list.csv", removes), ("dedup_groups.csv", groups), ("dedup_log.jsonl", logs or {})):
        absent = sorted(k for k in d if k not in known)
        if absent:
            raise Stop(f"{name}: {len(absent)} part(s) not among the cleaned parts, e.g. {absent[0][0]}/{absent[0][1]}")

    out.mkdir(parents=True, exist_ok=True)  # the staging folder: empty, ours
    writers, written, sets, hashes, raw_files = {}, {}, set(), {}, []
    counts = defaultdict(lambda: defaultdict(Counter))  # pack -> split -> status / rows
    survivors = Counter()  # pack -> dedup survivors F2 dropped (or errored on)
    gone_by_f2 = pa.array(["dropped_by_f2", "f2_error"])
    sample = defaultdict(list)
    need = defaultdict(lambda: SAMPLE_PER_STATUS)
    reports = {"parts": 0, "input_rows": 0, "drop": 0, "fix": 0, "keep": 0}
    fix_by_text = 0
    ok = False
    try:
        for split, part, path in parts:
            rep = clean_report(cleaned, split, part)
            raw_file = None
            if raw is not None:
                if rep is None or not rep.get("input_sha256"):  # mode B needs it: the raw file by sha256, the drops to check
                    raise Stop(f"--raw: {split}/{part} has no cleaning report with input_rows, actions and input_sha256 "
                               f"(<cleaned>/reports/{split}/{part}.json), so the ledger can neither be sure which raw file "
                               "the cleaner read nor check the cleaner's drops. A clean step must write these reports for "
                               "mode B (run_tokenizer_sample.py does); without them leave out --raw (mode C)")
                raw_file, raw_sha = find_raw(raw, split, part, rep, hashes)
                raw_files.append({"part": f"{split}/{part}", "file": raw_file.relative_to(raw).as_posix(), "sha256": raw_sha})
            t, set_sha = part_ledger(path, raw_file, split, part, removes, groups, logs, f2)
            sets.add(set_sha)
            n_drop = pc.sum(pc.equal(t.column("clean_action"), "drop")).as_py() or 0
            if rep is not None:
                reports["parts"] += 1
                reports["input_rows"] += rep["input_rows"]
                for k in ("drop", "fix", "keep"):
                    reports[k] += rep["actions"].get(k, 0)
                if raw is not None and (n_drop != rep["actions"].get("drop", 0) or t.num_rows != rep["input_rows"]):
                    raise Stop(f"{split}/{part}: the ledger has {t.num_rows} raw rows and {n_drop} cleaner drops, the "
                               f"cleaning report {rep['input_rows']} and {rep['actions'].get('drop', 0)}")
            fix_by_text += pc.sum(pc.equal(t.column("clean_action"), "fix")).as_py() or 0
            for g in t.group_by(["pack_id", "final"]).aggregate([("doc_id", "count")]).to_pylist():
                counts[g["pack_id"]][split][g["final"]] += g["doc_id_count"]
            for g in t.group_by(["pack_id"]).aggregate([("row_in_part", "count"), ("doc_id", "count")]).to_pylist():
                counts[g["pack_id"]][split]["rows"] += g["doc_id_count"]
                counts[g["pack_id"]][split]["rows_cleaned"] += g["row_in_part_count"]
            hit = t.filter(pc.and_(pc.equal(t.column("dedup_role"), "survivor"), pc.is_in(t.column("final"), value_set=gone_by_f2)))
            for g in hit.group_by(["pack_id"]).aggregate([("doc_id", "count")]).to_pylist():  # one row per pack
                survivors[g["pack_id"]] += g["doc_id_count"]
            packs = pc.unique(t.column("pack_id")).to_pylist()
            for pack in packs:
                tp = t if len(packs) == 1 else t.filter(pc.equal(t.column("pack_id"), pack))
                key = (split, pack)
                if key not in writers:
                    dst = out / split / f"{pack}.parquet"
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    writers[key] = pq.ParquetWriter(dst.with_name(dst.name + ".tmp"), schema(), compression="zstd")
                    written[key] = dst
                writers[key].write_table(tp)
                for status in FINAL:
                    k = (split, pack, status)
                    if need[k] > 0:  # by index: the sample holds its few rows, not the table they came from
                        idx = pc.indices_nonzero(pc.equal(tp.column("final"), status))
                        s = tp.take(idx.slice(0, need[k]))
                        need[k] -= s.num_rows
                        if s.num_rows:
                            sample[(split, pack)].append(s)
        if len(sets) != 1 or None in sets:
            raise Stop(f"the F2 reports name {len(sets)} different set_sha256 values: {sorted(map(str, sets))}")
        ok = True
    finally:
        for w in writers.values():
            w.close()
        if not ok:
            for dst in written.values():
                dst.with_name(dst.name + ".tmp").unlink(missing_ok=True)

    files = []
    for key in sorted(written):
        dst = written[key]
        dst.with_name(dst.name + ".tmp").replace(dst)
        files.append({"file": dst.relative_to(out).as_posix(), "rows": sum(counts[key[1]][key[0]][s] for s in FINAL),
                      "sha256": sha256(dst)})
    keys = sorted(sample, key=lambda k: (SPLITS.index(k[0]), k[1]))
    rows = [t for k in keys for t in sample[k]]
    sample_t = pa.concat_tables(rows) if rows else schema().empty_table()
    tmp = out / "ledger_sample.csv.tmp"
    pcsv.write_csv(sample_t, tmp)
    tmp.replace(out / "ledger_sample.csv")

    totals = Counter()
    for pack in counts:
        for split in counts[pack]:
            totals.update(counts[pack][split])
    summary = {
        "tool": "ledger.py", "code_sha256": code_sha256(Path(__file__))[0], "clean_mode": "B" if raw is not None else "C",
        "inputs": {"raw": {"path": raw.as_posix(), "files": raw_files} if raw is not None else None,
                   "remove_list": {"path": remove_list.as_posix(), "sha256": sha256(remove_list),
                                   "rows": sum(t.num_rows for t in removes.values())},
                   "groups": {"path": groups_csv.as_posix(), "sha256": sha256(groups_csv), "rows": groups_rows,
                              "removed_rows": removed_role},
                   "log": {"path": log.as_posix(), "sha256": sha256(log), "rows": log_rows} if log is not None else None,
                   "set_sha256": sets.pop()},
        "parts": len(parts),
        "totals": {"rows": totals["rows"], "rows_cleaned": totals["rows_cleaned"], **{s: totals[s] for s in FINAL},
                   "clean_fix_by_text": fix_by_text if raw is not None else None},
        "survivors_dropped_by_f2": {"total": sum(survivors.values()), "by_pack": {p: survivors[p] for p in sorted(survivors)}},
        "clean_reports": reports if reports["parts"] else None,
        "by_pack": {pack: {split: {"rows": c["rows"], "rows_cleaned": c["rows_cleaned"], **{s: c[s] for s in FINAL}}
                           for split, c in sorted(counts[pack].items(), key=lambda kv: SPLITS.index(kv[0]))}
                    for pack in sorted(counts)},
        "files": files}
    if summary["inputs"]["remove_list"]["rows"] != removed_role:
        raise Stop(f"dedup_groups.csv has {removed_role} removed rows, remove_list.csv {summary['inputs']['remove_list']['rows']}")
    if sum(totals[s] for s in FINAL) != totals["rows"]:
        raise Stop(f"the final statuses add up to {sum(totals[s] for s in FINAL)}, the ledger has {totals['rows']} rows")
    tmp = out / "ledger_summary.json.tmp"
    tmp.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(out / "ledger_summary.json")
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cleaned", type=Path, required=True, help="the cleaned parts: train/ and heldout/")
    ap.add_argument("--remove-list", type=Path, required=True, help="dedup.py's remove_list.csv")
    ap.add_argument("--groups", type=Path, required=True, help="dedup.py's dedup_groups.csv")
    ap.add_argument("--log", type=Path, help="dedup.py's dedup_log.jsonl (optional: match rule, similarity, kept doc)")
    ap.add_argument("--f2", type=Path, required=True, help="F2's output folder: <split>/<part> and .f2.json reports")
    ap.add_argument("--raw", type=Path, help="the raw parts the cleaner read (mode B); without it, mode C")
    ap.add_argument("--out", type=Path, required=True, help="where the ledger goes")
    args = ap.parse_args()
    try:
        s = build(args.cleaned, args.remove_list, args.groups, args.f2, args.out, log=args.log, raw=args.raw)
    except Stop as e:
        sys.exit(f"ledger: {e}")
    print(json.dumps({"clean_mode": s["clean_mode"], **{k: v for k, v in s["totals"].items() if v is not None}}))


if __name__ == "__main__":
    main()
