"""Apply dedup.py's remove list: copy the cleaned parts without the rows it names, everything else unchanged.

  python -I teams/01-data-a/pipeline/apply_dedup.py --cleaned <cleaned_dir> --remove-list <remove_list.csv> --out <dir>
         [--workers N] [--copy] [--hash-cache <file>]

This is the "filters the cleaned parts with remove_list.csv" step of dedup/dedup_design_v1.md ("Pipeline and hand-off to
TSAI"), between dedup.py and F2. It decides nothing: dedup.py chose what goes, this only carries it out, and checks it.

INPUT
=====
--cleaned is the folder overlap.py read: <cleaned>/train/**.parquet and <cleaned>/heldout/**.parquet. A "part" is a file's
path relative to its split folder (code-go/part-00000.parquet) and row_in_part is its 0-based row in file order, as
overlap.py numbers them. --remove-list is dedup.py's remove_list.csv: pack_id, split, part, row_in_part, doc_id. Parts are
compared with / as the separator, so a list written on Linux matches files on Windows and back.

doc_id alone is not a key: in the cleaned sample v0, 22,773 doc_ids sit in two parts of the same pack and split. A row is
found by (split, part, row_in_part), and its doc_id and pack_id must then match the list.

CHECKS (any failure stops the run before anything is written; exit code 1)
==========================================================================
  - the header is exactly dedup.py's, no row is listed twice, row_in_part is a whole number >= 0
  - no held-out row: dedup never removes a held-out document (source_priority_v1.md rule 0), so one in the list means
    the list is broken
  - every listed part exists, every listed row is inside it, and the doc_id and pack_id at that row are the listed ones;
    a mismatch means the list came from another cleaning run than these parts
  - --out is not inside --cleaned, nor the other way round
  - every part opens as Parquet with doc_id and pack_id columns, and no pack_id is empty (null), not just in the parts
    with removals
  - --out holds no Parquet file outside the current parts (one left by an earlier run would be read by F2)
After writing, each filtered part must hold exactly its rows minus the listed ones, and the totals must add up.

OUTPUT
======
<out>/<split>/<part> for every part, with the same schema and unchanged text. A part with nothing to remove is copied
byte for byte (hard-linked when --cleaned and --out are on the same file system, so it takes no extra disk; --copy
copies instead), so its sha256 shows it is untouched. A filtered part keeps the input's compression codec, rows and row
order; its row groups hold up to 64k rows or 32 MiB each and its pages about 1 MiB, whatever the input used (the cleaner
writes 128-row groups, and writing thousands of tiny groups cost most of the time), so its bytes differ from a part
written row group by row group. Files are written to <name>.<pid>.tmp and renamed; temp files left by a killed run are deleted first. One run at
a time may write into --out: a second one stops (runlock.py). <out>/apply_dedup_summary.json holds the remove list's
sha256 and row count, the code's sha256 (this file and the helper modules it runs on, hashing.code_sha256), and per
part: rows, removed, kept, the input and output sha256 and whether it was copied; then totals and counts per pack and
split. IDs, counts and hashes only, never text. A rerun with the same remove list and code skips each part whose input
and output still have the recorded sha256, so a stopped run resumes.

SPEED AND SCALE
===============
Whole columns at a time with pyarrow, never a Python loop over rows: the list's checks are vectorised, each part's
listed rows are checked with one take/compare, and a part is filtered with one keep-mask (built once per part) while
it is read in batches of about 16 MiB of decoded data (at most 1,024 rows), through an 8 MiB read buffer. The size of
each read comes from the decoded bytes per row seen so far, not from the footer alone: repeated text in a
dictionary-encoded column decodes far larger than it is stored (arrowtools.iter_sized). So memory stays near a batch
plus one 32 MiB output row group per worker (plus a page of the input, which the cleaner's writer sets), even for a
part written as a single huge row group, one of 200 KB documents, or one of the same long text repeated. A batch that
loses no row is passed on as it is, not copied; one bigger than an output row group is split before it is written. Parts are checked and written by --workers threads
(default 4; pyarrow and hashlib release the GIL). Every sha256 goes through hashing.HashCache: a hard-linked part takes
its input's sha256 (it is the same file), and the runner's digests reuse these hashes (--hash-cache keeps them on disk
for a resumed run). The summary is rewritten at most every few seconds, not after every part.
"""
import sys
sys.dont_write_bytecode = True

import argparse, glob, json, os, shutil, threading, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
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

HEADER = ["pack_id", "split", "part", "row_in_part", "doc_id"]
SPLITS = ("train", "heldout")
SUMMARY = "apply_dedup_summary.json"
DEFAULT_WORKERS = 4
SUMMARY_EVERY = 5.0  # seconds between progress writes of the summary
BATCH_ROWS = 1024  # at most this many rows read at a time while filtering ...
BATCH_BYTES = 16 << 20  # ... and about this many bytes of decoded data (arrowtools.iter_sized)
READ_BUFFER = 8 << 20  # column chunks are read through a buffer of this size, never whole
ROW_GROUP_ROWS = 65536  # an output row group holds at most this many rows ...
ROW_GROUP_BYTES = 32 << 20  # ... and this many bytes in memory
PAGE_BYTES = 1 << 20  # an output page holds about this many bytes (the writer's 1,024 rows of 200 KB would be 200 MB)


class Stop(Exception):
    """A check failed: the message says which and where."""


def opened(path):
    return at.opened(path)  # kept for callers that used apply_dedup.opened


# --- the remove list -------------------------------------------------------------------------------------------------
def read_remove_list(path, splits):
    """({(split, part): Table(row_in_part int64, doc_id, pack_id)}, rows) after every per-row check, done column-wise.
    The first bad line is reported, with the first check it fails, as a line-by-line reader would."""
    path = Path(path)
    t = at.posix(at.read_csv(path, HEADER, {}, Stop))  # every column as a string: row_in_part is checked here
    n = t.num_rows
    if n == 0:
        return {}, 0
    split, part, row = t["split"], t["part"], t["row_in_part"]
    digits = pc.match_substring_regex(row, r"^[0-9]{1,18}$")
    as_int = pc.cast(pc.if_else(digits, row, "0"), pa.int64())
    idx = at.arange(n)
    key = pc.binary_join_element_wise(split, part, pc.cast(as_int, pa.string()), "\x1f")
    first = pa.table({"key": key, "i": idx}).group_by("key").aggregate([("i", "min")])
    j = pa.table({"key": key, "i": idx}).join(first, "key").sort_by("i")
    repeated = pc.and_(digits, pc.not_equal(j["i"], j["i_min"]))
    checks = [
        (pc.equal(split, "heldout"),
         lambda i: f"a held-out row ({part[i]} row {row[i]}). Dedup never removes held-out documents "
                   "(source_priority_v1.md rule 0), so this remove list is broken"),
        (pc.invert(pc.is_in(split, value_set=pa.array(SPLITS))),
         lambda i: f"split {split[i].as_py()!r} is not train or heldout"),
        (pc.invert(pc.is_in(split, value_set=pa.array(list(splits), pa.string()))),
         lambda i: f"split {split[i]} is not among --splits {list(splits)}"),
        (pc.invert(digits), lambda i: f"row_in_part {row[i].as_py()!r} is not a whole number >= 0"),
        (repeated, lambda i: f"{split[i]}/{part[i]} row {as_int[i]} is listed twice"),
    ]
    bad_any = checks[0][0]
    for mask, _ in checks[1:]:
        bad_any = pc.or_(bad_any, mask)
    if at.count(bad_any):
        i = pc.index(bad_any, True).as_py()
        for mask, message in checks:
            if mask[i].as_py():
                raise Stop(f"{path} line {i + 2}: {message(i)}")
    listed = pa.table({"split": split, "part": part, "row_in_part": as_int, "doc_id": t["doc_id"], "pack_id": t["pack_id"]})
    return {k: v.select(["row_in_part", "doc_id", "pack_id"]).sort_by("row_in_part")
            for k, v in at.by_part(listed).items()}, n


# --- the parts -------------------------------------------------------------------------------------------------------
def find_parts(cleaned, splits):
    """[(split, part, path)] for every Parquet file under the selected split folders, as overlap.py finds them."""
    parts = []
    for split in splits:
        folder = cleaned / split
        if not folder.is_dir():
            raise Stop(f"--cleaned {cleaned} has no {split}/ folder")
        parts += [(split, f.relative_to(folder).as_posix(), f) for f in sorted(folder.rglob("*.parquet")) if f.is_file()]
    if not parts:
        raise Stop(f"--cleaned {cleaned}: no Parquet parts under {list(splits)}")
    return parts


def check_part(path, split, part, listed):
    """Every check of one part, before anything is written: it opens as Parquet with doc_id and pack_id, no pack_id is
    null, and every listed row is inside it with the listed doc_id and pack_id. Returns (rows, {pack: rows},
    {pack: removed})."""
    try:
        with at.opened(path) as pf:
            names = set(pf.schema_arrow.names)
            missing = {"doc_id", "pack_id"} - names
            if missing:
                raise Stop(f"{split}/{part}: no {', '.join(sorted(missing))} column")
            t = pf.read(columns=["pack_id", "doc_id"] if listed is not None else ["pack_id"])
    except Stop:
        raise
    except Exception as e:  # not Parquet, truncated, unreadable
        raise Stop(f"{split}/{part}: cannot be read as Parquet ({type(e).__name__})")
    n = t.num_rows
    packs = at.as_str(t["pack_id"])
    if packs.null_count:
        raise Stop(f"{split}/{part}: {packs.null_count} row(s) have no pack_id")
    per_pack = _value_counts(packs)
    removed = Counter()
    if listed is not None:
        rows = listed["row_in_part"]
        outside = pc.greater_equal(rows, n)
        if at.count(outside):
            raise Stop(f"{split}/{part}: row {pc.min(rows.filter(outside)).as_py()} is listed, but the part has {n} rows")
        doc, pack = at.as_str(t["doc_id"]).take(rows), packs.take(rows)
        bad_doc = pc.fill_null(pc.not_equal(doc, at.as_str(listed["doc_id"])), True)
        bad_pack = pc.fill_null(pc.not_equal(pack, at.as_str(listed["pack_id"])), True)
        bad = pc.or_(bad_doc, bad_pack)
        if at.count(bad):
            i = pc.index(bad, True).as_py()  # rows are sorted, so this is the first bad row of the part
            r = rows[i].as_py()
            if bad_doc[i].as_py():
                raise Stop(f"{split}/{part} row {r}: doc_id is {doc[i].as_py()!r}, the remove list says "
                           f"{listed['doc_id'][i].as_py()!r}. The list was made from another cleaning run than these parts")
            raise Stop(f"{split}/{part} row {r}: pack_id is {pack[i].as_py()!r}, the remove list says "
                       f"{listed['pack_id'][i].as_py()!r}")
        removed = _value_counts(pack)
    return n, per_pack, removed


def _value_counts(arr):
    """{value: count} of a string array, counted by pyarrow; the loop is over distinct values (packs), not rows."""
    return Counter({v["values"]: v["counts"] for v in pc.value_counts(arr).to_pylist()})


def stale_outputs(out, parts, splits):
    """Parquet files under <out>/<split> that are not among the current parts: left by an earlier run."""
    current = {(s, p) for s, p, _ in parts}
    found = []
    for split in splits:
        if (out / split).is_dir():
            found += [f"{split}/{f.relative_to(out / split).as_posix()}" for f in sorted((out / split).rglob("*.parquet"))
                      if (split, f.relative_to(out / split).as_posix()) not in current]
    return found


def compression(pf):
    """The input's codec, so a filtered part is written the way it was read (snappy, zstd, ...)."""
    md = pf.metadata
    if md.num_row_groups and md.num_columns:
        codec = md.row_group(0).column(0).compression.lower()
        return "none" if codec == "uncompressed" else codec
    return "snappy"


def filter_part(src, tmp, rows):
    """Write src without the rows in `rows` (an int64 array of 0-based row numbers) to tmp, with the input's codec.
    One keep-mask for the whole part (one lookup set), applied to batches of about BATCH_BYTES of decoded data (at most
    BATCH_ROWS rows) as they are read; an output row group is written before it would pass ROW_GROUP_ROWS rows or
    ROW_GROUP_BYTES bytes, and a batch bigger than that is split first. Returns the rows written."""
    kept, offset, pending, pending_rows, pending_bytes = 0, 0, [], 0, 0
    with at.opened(src, buffer_size=READ_BUFFER) as pf, \
            pq.ParquetWriter(tmp, pf.schema_arrow, compression=compression(pf),
                             write_batch_size=at.batch_rows(pf, PAGE_BYTES, 1024)) as w:
        keep = pc.invert(pc.is_in(at.arange(pf.metadata.num_rows), value_set=rows))

        def flush():
            nonlocal pending, pending_rows, pending_bytes
            if pending_rows:
                w.write_table(pa.Table.from_batches(pending, schema=pf.schema_arrow), row_group_size=pending_rows)
            pending, pending_rows, pending_bytes = [], 0, 0

        def add(b):
            nonlocal pending_rows, pending_bytes
            if pending_rows and (pending_rows + b.num_rows > ROW_GROUP_ROWS or pending_bytes + b.nbytes > ROW_GROUP_BYTES):
                flush()
            pending.append(b)
            pending_rows += b.num_rows
            pending_bytes += b.nbytes

        for batch in at.iter_sized(pf, BATCH_BYTES, BATCH_ROWS):
            mask = keep.slice(offset, batch.num_rows)
            offset += batch.num_rows
            b = batch if at.count(mask) == batch.num_rows else batch.filter(mask)  # no copy when no row goes
            del batch
            if not b.num_rows:
                continue
            kept += b.num_rows
            if b.nbytes > ROW_GROUP_BYTES and b.num_rows > 1:  # never one row group above the limit
                step = max(1, b.num_rows * ROW_GROUP_BYTES // b.nbytes)
                for start in range(0, b.num_rows, step):
                    add(b.slice(start, step))
            else:
                add(b)
        flush()
    return kept


def write_json(path, data):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


# --- the run ---------------------------------------------------------------------------------------------------------
def apply(cleaned, remove_list, out, splits=SPLITS, link=True, workers=DEFAULT_WORKERS, cache=None):
    """Run the checks, then write <out>, holding <out>'s lock. Returns the summary dict. Raises Stop on any failed check
    or when another process is writing into <out>. `cache`: a hashing.HashCache to share sha256s with the caller (the
    runner); a new in-memory one by default."""
    cleaned, remove_list, out = Path(cleaned), Path(remove_list), Path(out)
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise Stop(f"workers is {workers!r}, expected a whole number >= 1")
    rc, ro = cleaned.resolve(), out.resolve()
    if rc == ro or rc in ro.parents or ro in rc.parents:  # before the lock: no lock file inside the input
        raise Stop(f"--out {out} and --cleaned {cleaned} overlap: the output would be read as input")
    try:
        with runlock.exclusive(out):
            return _apply(cleaned, remove_list, out, splits, link, workers, cache or HashCache())
    except runlock.Busy as e:
        raise Stop(str(e)) from None


def _apply(cleaned, remove_list, out, splits, link, workers, cache):
    todo, n_listed = read_remove_list(remove_list, splits)
    parts = find_parts(cleaned, splits)
    known = {(s, p) for s, p, _ in parts}
    absent = sorted(k for k in todo if k not in known)
    if absent:
        raise Stop(f"{len(absent)} listed part(s) not found under --cleaned, e.g. {absent[0][0]}/{absent[0][1]}")

    def check(item):
        split, part, path = item
        return check_part(path, split, part, todo.get((split, part)))

    with ThreadPoolExecutor(max_workers=min(workers, len(parts))) as pool:  # every check before anything is written
        checked = list(pool.map(check, parts))
    stale = stale_outputs(out, parts, splits)
    if stale:
        raise Stop(f"--out {out} holds {len(stale)} Parquet file(s) that are not among the current parts, e.g. "
                   f"{stale[0]}: left by an earlier run. Use a new --out, or delete them")

    rl_sha, (code_sha, code_files) = cache.sha256(remove_list), code_sha256(Path(__file__), cache)
    old = {}
    if (out / SUMMARY).is_file():
        try:
            prev = json.loads((out / SUMMARY).read_text(encoding="utf-8"))
        except ValueError:
            prev = {}
        if prev.get("remove_list", {}).get("sha256") == rl_sha and prev.get("code_sha256") == code_sha:
            old = {(p["split"], p["part"]): p for p in prev.get("parts", [])}

    summary = {"tool": "apply_dedup.py", "code_sha256": code_sha, "code_files": code_files, "cleaned": cleaned.as_posix(),
               "remove_list": {"path": remove_list.as_posix(), "sha256": rl_sha, "rows": n_listed},
               "splits": list(splits), "parts": []}
    out.mkdir(parents=True, exist_ok=True)
    done, lock, last = {}, threading.Lock(), [time.monotonic()]

    def progress(force=False):
        with lock:
            if not force and time.monotonic() - last[0] < SUMMARY_EVERY:
                return
            last[0] = time.monotonic()
            summary["parts"] = [done[i] for i in sorted(done)]
            write_json(out / SUMMARY, summary)

    def write(i):
        (split, part, src), (rows, per_pack, removed) = parts[i], checked[i]
        dst = out / split / part
        listed = todo.get((split, part))
        in_sha = cache.sha256(src)
        prev = old.get((split, part))
        if prev and prev.get("input_sha256") == in_sha and dst.is_file() and cache.sha256(dst) == prev.get("output_sha256"):
            entry = {**prev, "skipped": True}
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            # a temp file left by a killed run may be a hard link to the cleaned part: delete it, never write through it
            for stale in [dst.with_name(dst.name + ".tmp"), *dst.parent.glob(glob.escape(dst.name) + ".*.tmp")]:
                stale.unlink(missing_ok=True)
            tmp = dst.with_name(f"{dst.name}.{os.getpid()}.tmp")
            linked = False
            if listed is not None:
                kept = filter_part(src, tmp, listed["row_in_part"])
                if kept != rows - listed.num_rows:
                    tmp.unlink(missing_ok=True)
                    raise Stop(f"{split}/{part}: kept {kept} rows, expected {rows} - {listed.num_rows} listed")
            else:
                if link:  # same bytes, no extra disk; nothing here edits a file in place (all writes go to .tmp + rename)
                    try:
                        os.link(src, tmp)
                        linked = True
                    except OSError:  # another file system, no permission, ...: copy instead
                        pass
                if not linked:
                    shutil.copyfile(src, tmp)
            os.replace(tmp, dst)
            if linked:  # the same file as the input, so its sha256; making the link moved its ctime, so its key is new
                cache.remember(dst, in_sha)
            n_removed = 0 if listed is None else listed.num_rows
            entry = {"split": split, "part": part, "rows": rows, "removed": n_removed, "kept": rows - n_removed,
                     "input_sha256": in_sha, "output_sha256": cache.sha256(dst), "copied": listed is None,
                     "linked": linked, "skipped": False,
                     "packs": {p: {"rows": per_pack[p], "removed": removed[p]} for p in sorted(per_pack)}}
        with lock:
            done[i] = entry
        progress()
        return entry

    with ThreadPoolExecutor(max_workers=min(workers, len(parts))) as pool:
        list(pool.map(write, range(len(parts))))
    summary["parts"] = [done[i] for i in range(len(parts))]

    by_pack = defaultdict(lambda: defaultdict(Counter))
    for p in summary["parts"]:
        for pack, c in p["packs"].items():
            by_pack[pack][p["split"]].update(rows=c["rows"], removed=c["removed"])
    summary["by_pack"] = {pack: {sp: {"rows": c["rows"], "removed": c["removed"], "kept": c["rows"] - c["removed"]}
                                 for sp, c in sorted(splits_.items())} for pack, splits_ in sorted(by_pack.items())}
    totals = Counter()
    for p in summary["parts"]:
        totals.update(rows=p["rows"], removed=p["removed"], kept=p["kept"])
    summary["totals"] = {k: totals[k] for k in ("rows", "removed", "kept")}
    if summary["totals"]["removed"] != n_listed or summary["totals"]["rows"] != summary["totals"]["kept"] + n_listed:
        raise Stop(f"removed {summary['totals']['removed']} rows in all, the list names {n_listed}")
    write_json(out / SUMMARY, summary)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cleaned", type=Path, required=True, help="folder with train/ and heldout/ cleaned parts")
    ap.add_argument("--remove-list", type=Path, required=True, help="dedup.py's remove_list.csv")
    ap.add_argument("--out", type=Path, required=True, help="output folder (gets train/, heldout/ and the summary)")
    ap.add_argument("--splits", nargs="+", default=list(SPLITS), choices=SPLITS)
    ap.add_argument("--copy", action="store_true", help="copy untouched parts instead of hard-linking them")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="parts checked and written at once (default 4)")
    ap.add_argument("--hash-cache", type=Path, help="keep sha256s in this file, so a resumed run does not hash again")
    args = ap.parse_args()
    cache = HashCache(args.hash_cache) if args.hash_cache else None
    try:
        s = apply(args.cleaned, args.remove_list, args.out, tuple(args.splits), link=not args.copy, workers=args.workers,
                  cache=cache)
    except Stop as e:
        sys.exit(f"apply_dedup: {e}")
    finally:
        if cache:
            cache.save()
    print(json.dumps({"parts": len(s["parts"]), **s["totals"]}))


if __name__ == "__main__":
    main()
