"""Check a run against its expected inventory: the parts and packs the input manifest lists, and nothing else.

  python -I teams/01-data-a/pipeline/inventory_check.py --inventory <expected_inventory.json>
         [--ledger <run>/ledger] [--shards <run>/shards] [--cleaned <cleaned>] [--out <report.json>]

The ledger and the shard summary both describe what a run made, so neither can say that a pack or a part never reached
the run at all. The expected inventory can: it is written from the approved input manifest, before the run and without
reading anything the run writes. This script compares the two sides part by part. It decides nothing and changes
nothing. run_pipeline.py calls the same functions ("inventory" in the run config); the command line is for checking
returned files after a job.

THE INVENTORY (JSON)
====================
  input_manifest_sha256   the sha256 of the input manifest the inventory was made from
  packs                   the pack ids, each at least once among the parts
  parts                   one entry per part of the input manifest:
      part          "<split>/<pack>/<file>.parquet", split train or heldout
      expected      the status the part's shards must end in: "written" or "not_sharded", or a list of the statuses
                    that are acceptable (a status the shard writer gets later can be listed without a change here; a
                    status is any text, so a mistyped one fails only when the statuses are compared).
                    "failed" and "skipped" are refused: no run may expect them
      raw_sha256    the sha256 of the raw part
      raw_rows      the rows of the raw part
      split         optional: must be the split in "part"
      pack_id       optional: must be the pack in "part"
Keys starting with "_" are comments; any other key that is not named here is refused, at the top and in a part, so a
field under another name (say "sha256" for "raw_sha256") cannot go uncompared. A part listed twice, a part of a pack
that "packs" does not list, a pack without a part and an entry with a missing or malformed field are refused before
anything is compared.

CHECKS
======
With --ledger (ledger.py's folder; it must have run with --raw, mode B, where one ledger row is one raw document):
  - the ledger accounts for every raw document (mode B)
  - the ledger holds exactly the listed parts: a listed part it does not hold fails, and so does a part it holds that
    is not listed
  - every listed pack is in the ledger, and no other pack has kept documents. Packs are the documents' pack_id: a
    listed pack must be among them unless all its parts list 0 raw rows; a pack that is not listed (a document with
    another pack_id inside a listed part) fails only when one of its documents was kept
  - each part's raw file is the listed one: the sha256 ledger.py recorded for the raw file it read = raw_sha256
  - each part's raw rows are the listed ones: the part's rows in the ledger's Parquet = raw_rows
With --shards (run_shards.py's --out, for shards_summary.json):
  - the shard summary holds exactly the listed parts
  - every part ended in a listed status
  - every part is of its listed pack (the entry's pack_id; an entry without one fails). The documents' own pack_id is
    not compared part by part: a raw file in another pack's folder fails the raw sha256 check above, and a kept
    document of a pack that is not listed fails the ledger's pack check
With --cleaned (the cleaned folder, for the clean job's job_summary.json):
  - the inventory was made from the input manifest the clean job read (input_manifest_sha256 = manifest_sha256); a
    folder without job_summary.json, or a summary without manifest_sha256, fails the check
Every check runs, so the report shows all the differences; exit code 1 when any failed. Without --cleaned the input
manifest is not compared, and without --ledger or --shards that side is not: the report holds only the checks made.

REPORT
======
--out (and the function's return value): the inventory's sha256 and counts, what each side holds, every check with its
detail, and under "differences" the full lists (parts, packs, hashes, rows, statuses) behind the checks.
IDs, counts and hashes, and the paths as they were given; no document text.

WHAT IT READS
=============
The inventory; <ledger>/ledger_summary.json and two columns (split, part) of the ledger's Parquet, a batch at a time;
<shards>/shards_summary.json ("parts": {"<split>/<pack>/<file>.parquet": {"status", "pack_id", ...}}); and
<cleaned>/job_summary.json. No raw or final part is opened and nothing is hashed again.
"""
import sys
sys.dont_write_bytecode = True

import argparse, hashlib, json, os, re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from hashing import code_sha256  # noqa: E402

SPLITS = ("train", "heldout")
NEVER = ("failed", "skipped")  # statuses no inventory may expect: the shard stage stops the run on either
SHOWN = 3  # examples named in a check's detail (the report's "differences" has them all)
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TOP_KEYS = ("input_manifest_sha256", "packs", "parts")  # every key of the inventory, besides "_..." comments
PART_KEYS = ("part", "expected", "raw_sha256", "raw_rows", "split", "pack_id")  # and of a part


class Stop(Exception):
    """The inventory or an input cannot be read as what it should be: the message says why."""


def read_object(p, what):
    """The JSON object in file p. Raises Stop when it cannot be read, is not JSON, or is not an object."""
    try:
        data = json.loads(Path(p).read_bytes().decode("utf-8"))
    except OSError as e:
        raise Stop(f"{what} {p} cannot be read ({type(e).__name__})")
    except (ValueError, UnicodeDecodeError) as e:
        raise Stop(f"{what} {p} is not valid JSON ({e})")
    if not isinstance(data, dict):
        raise Stop(f"{what} {p} is not a JSON object")
    return data


def unknown_key(obj, known):
    """The first key of obj that is neither known nor a "_..." comment (None when there is none)."""
    return next((k for k in sorted(obj) if not k.startswith("_") and k not in known), None)


def load(file):
    """The expected inventory, checked and in one shape:
    {"path", "sha256", "input_manifest_sha256", "packs": [pack], "parts": {name: {"split", "pack_id", "expected":
    [status], "raw_sha256", "raw_rows"}}}. Raises Stop when it is not a well-formed inventory. The file is read once:
    the sha256 is of the bytes that were parsed."""
    file = Path(file)
    if not file.is_file():
        raise Stop(f"{file} is not a file")
    try:
        content = file.read_bytes()
    except OSError as e:
        raise Stop(f"the inventory {file} cannot be read ({type(e).__name__})")
    try:
        data = json.loads(content.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise Stop(f"the inventory {file} is not valid JSON ({e})")
    if not isinstance(data, dict):
        raise Stop(f"{file}: expected a JSON object with \"packs\" and \"parts\"")
    key = unknown_key(data, TOP_KEYS)
    if key is not None:
        raise Stop(f"{file}: unknown key {key!r}; an inventory has {', '.join(TOP_KEYS)} (a key starting with \"_\" is a comment)")
    packs, entries = data.get("packs"), data.get("parts")
    if not isinstance(packs, list) or not packs or not all(isinstance(p, str) and p for p in packs):
        raise Stop(f"{file}: \"packs\" must be a list of pack ids, with at least one")
    twice = sorted(p for p, n in Counter(packs).items() if n > 1)
    if twice:
        raise Stop(f"{file}: pack {twice[0]!r} is listed twice in \"packs\"")
    if not isinstance(entries, list) or not entries:
        raise Stop(f"{file}: \"parts\" must be a list of parts, with at least one")
    manifest = data.get("input_manifest_sha256")
    if manifest is None:
        raise Stop(f"{file}: input_manifest_sha256 is missing (the sha256 of the input manifest the inventory was made from)")
    if not (isinstance(manifest, str) and HEX64.match(manifest)):
        raise Stop(f"{file}: input_manifest_sha256 must be 64 lowercase hex characters")
    parts = {}
    for n, e in enumerate(entries):
        where = f"{file}: parts[{n}]"
        if not isinstance(e, dict):
            raise Stop(f"{where} is not an object")
        name = e.get("part")
        bits = name.split("/") if isinstance(name, str) else []
        if (len(bits) != 3 or bits[0] not in SPLITS or not bits[2].endswith(".parquet")
                or any(b in ("", ".", "..") for b in bits) or "\\" in name):
            raise Stop(f"{where}: \"part\" is {name!r}, expected <split>/<pack>/<file>.parquet with split train or heldout")
        where = f"{file}: part {name}"
        key = unknown_key(e, PART_KEYS)
        if key is not None:
            raise Stop(f"{where}: unknown key {key!r}; a part has {', '.join(PART_KEYS)} (a key starting with \"_\" is a comment)")
        if name in parts:
            raise Stop(f"{where} is listed twice")
        if "split" in e and e["split"] != bits[0]:
            raise Stop(f"{where}: \"split\" is {e['split']!r}, the part is under {bits[0]}/")
        if "pack_id" in e and e["pack_id"] != bits[1]:
            raise Stop(f"{where}: \"pack_id\" is {e['pack_id']!r}, the part is under {bits[0]}/{bits[1]}/")
        if bits[1] not in packs:
            raise Stop(f"{where}: its pack {bits[1]!r} is not in \"packs\"")
        want = e.get("expected")
        want = [want] if isinstance(want, str) else want
        if not isinstance(want, list) or not want or not all(isinstance(s, str) and s for s in want):
            raise Stop(f"{where}: \"expected\" must be a status (\"written\", \"not_sharded\") or a list of statuses")
        never = sorted(set(want) & set(NEVER))
        if never:
            raise Stop(f"{where}: \"expected\" names {never[0]!r}: no run may expect a part to be {' or '.join(NEVER)}")
        for field, what in (("raw_sha256", "the sha256 of the raw part"), ("raw_rows", "the rows of the raw part")):
            if e.get(field) is None:
                raise Stop(f"{where}: {field} is missing ({what})")
        sha, rows = e["raw_sha256"], e["raw_rows"]
        if not (isinstance(sha, str) and HEX64.match(sha)):
            raise Stop(f"{where}: raw_sha256 must be 64 lowercase hex characters")
        if not isinstance(rows, int) or isinstance(rows, bool) or rows < 0:
            raise Stop(f"{where}: raw_rows is {rows!r}, expected a whole number >= 0")
        parts[name] = {"split": bits[0], "pack_id": bits[1], "expected": sorted(set(want)), "raw_sha256": sha, "raw_rows": rows}
    empty = sorted(set(packs) - {p["pack_id"] for p in parts.values()})
    if empty:
        raise Stop(f"{file}: pack {empty[0]!r} is in \"packs\" but no part is of it")
    return {"path": file, "sha256": hashlib.sha256(content).hexdigest(), "input_manifest_sha256": manifest,
            "packs": sorted(packs), "parts": parts}


def described(inv):
    """The inventory as the report and the run manifest name it: its sha256 and counts, never its entries."""
    return {"file": Path(inv["path"]).as_posix(), "sha256": inv["sha256"], "input_manifest_sha256": inv["input_manifest_sha256"],
            "packs": len(inv["packs"]), "parts": len(inv["parts"]),
            "expected": dict(sorted(Counter("|".join(p["expected"]) for p in inv["parts"].values()).items()))}


def eg(names):
    """", e.g. a, b, c" for the first few of a sorted list ("" when it is empty)."""
    return f", e.g. {', '.join(map(str, names[:SHOWN]))}" if names else ""


def short(h):
    return f"{h[:12]}…" if isinstance(h, str) else "none"


def ledger_rows(ledger):
    """{"<split>/<part>": rows} over the ledger's Parquet (<split>/<pack>.parquet): in mode B, a part's raw rows. Two
    columns are read, a batch at a time."""
    import pyarrow as pa, pyarrow.parquet as pq
    rows = Counter()
    files = sorted(Path(ledger).glob("*/*.parquet"))
    if not files:
        raise Stop(f"--ledger {ledger}: no <split>/<pack>.parquet files")
    for f in files:
        try:
            with pq.ParquetFile(f) as pf:
                for batch in pf.iter_batches(columns=["split", "part"]):
                    t = pa.Table.from_batches([batch]).group_by(["split", "part"]).aggregate([([], "count_all")])
                    for g in t.to_pylist():
                        rows[f"{g['split']}/{g['part']}".replace("\\", "/")] += g["count_all"]
        except Exception as e:  # not Parquet, truncated, or without the two columns
            raise Stop(f"--ledger {ledger}: {f.name} cannot be read as a ledger file ({type(e).__name__})")
    return rows


def check_manifest(inv, cleaned):
    """([check], the difference): the inventory names the input manifest the clean job read. A cleaned folder without
    job_summary.json, or a summary that records no manifest_sha256, fails the check: it is never left out."""
    summary, want = Path(cleaned) / "job_summary.json", inv["input_manifest_sha256"]
    got = read_object(summary, "the clean job's summary").get("manifest_sha256") if summary.is_file() else None
    if not summary.is_file():
        detail = f"the cleaned folder has no job_summary.json, so the input manifest the clean job read is not known; inventory input_manifest_sha256 {short(want)}"
    elif not got:
        detail = f"the clean job's job_summary.json records no manifest_sha256; inventory input_manifest_sha256 {short(want)}"
    else:
        detail = f"clean job manifest_sha256 {str(got)[:12]}…, inventory input_manifest_sha256 {short(want)}"
    ok = bool(got) and got == want
    return ([{"check": "inventory: made from the input manifest the clean job read", "ok": ok, "detail": detail}],
            {"input_manifest_sha256": [] if ok else [{"clean_job": got or None, "listed": want}]})


def check_ledger(inv, ledger):
    """([checks], what the ledger holds, the differences) for the ledger side."""
    ledger = Path(ledger)
    if not (ledger / "ledger_summary.json").is_file():
        raise Stop(f"--ledger {ledger}: no ledger_summary.json")
    s = read_object(ledger / "ledger_summary.json", "the ledger's summary")
    mode = s.get("clean_mode")
    inputs = s.get("inputs")
    raw = inputs.get("raw") if isinstance(inputs, dict) else None
    raw_files = (raw.get("files") if isinstance(raw, dict) else None) or []
    if not isinstance(raw_files, list) or not all(isinstance(f, dict) and isinstance(f.get("part"), str) for f in raw_files):
        raise Stop(f"--ledger {ledger}: ledger_summary.json inputs.raw.files is not a list of {{part, sha256}} entries")
    by_pack = s.get("by_pack") or {}
    if not isinstance(by_pack, dict) or not all(isinstance(splits, dict) and all(isinstance(c, dict) for c in splits.values())
                                                for splits in by_pack.values()):
        raise Stop(f"--ledger {ledger}: ledger_summary.json by_pack is not {{pack: {{split: counts}}}}")
    kept = {}
    for pack, splits in by_pack.items():
        counts = [c.get("kept") for c in splits.values()]  # ledger.py always writes it: a missing one is not read as 0
        if not all(isinstance(n, int) and not isinstance(n, bool) and n >= 0 for n in counts):
            raise Stop(f"--ledger {ledger}: ledger_summary.json by_pack {pack!r} has a kept count that is not a whole number >= 0")
        kept[pack] = sum(counts)
    recorded = {f["part"].replace("\\", "/"): f.get("sha256") for f in raw_files}
    rows = ledger_rows(ledger)
    held = set(rows) | set(recorded)  # a raw part without a row is still a part the ledger read
    listed = inv["parts"]
    missing, unlisted = sorted(set(listed) - held), sorted(held - set(listed))
    need = {p["pack_id"] for p in listed.values() if p["raw_rows"] != 0}  # a pack of parts without rows has none in the ledger
    packs_missing = sorted(need - set(kept))
    other = sorted(set(kept) - set(inv["packs"]))  # pack ids of documents inside the listed parts that are no listed pack
    packs_unlisted = [{"pack": p, "kept": kept[p]} for p in other if kept[p] > 0]
    with_kept = [f"{p['pack']} ({p['kept']} kept)" for p in packs_unlisted]
    both = sorted(set(listed) & held)
    sha_diff = [{"part": p, "ledger": recorded.get(p), "listed": listed[p]["raw_sha256"]} for p in both
                if recorded.get(p) != listed[p]["raw_sha256"]]
    row_diff = [{"part": p, "ledger": rows.get(p, 0), "listed": listed[p]["raw_rows"]} for p in both
                if rows.get(p, 0) != listed[p]["raw_rows"]]
    b = mode == "B"
    checks = [
        {"check": "inventory: the ledger accounts for every raw document (mode B)", "ok": b,
         "detail": f"ledger clean_mode {mode!r}" + ("" if b else ": it ran without the raw parts, so raw rows and raw sha256 cannot be checked")},
        {"check": "inventory: the ledger holds exactly the listed parts", "ok": not missing and not unlisted,
         "detail": f"{len(missing)} listed part(s) not in the ledger{eg(missing)}; {len(unlisted)} ledger part(s) not listed{eg(unlisted)}"
                   if missing or unlisted else f"all {len(listed)} listed parts, and no other"},
        {"check": "inventory: every listed pack is in the ledger, and no other pack has kept documents",
         "ok": not packs_missing and not packs_unlisted,
         "detail": f"{len(packs_missing)} listed pack(s) not in the ledger{eg(packs_missing)}; {len(packs_unlisted)} pack(s) "
                   f"that are not listed have kept documents{eg(with_kept)}"
                   if packs_missing or packs_unlisted else
                   f"all {len(inv['packs'])} listed packs"
                   + (f"; {len(other)} other pack id(s) among the documents, none kept{eg(other)}" if other else ", and no other")},
        {"check": "inventory: each part's raw file is the listed one (sha256)", "ok": b and not sha_diff,
         "detail": "not checked: the ledger recorded no raw files (mode C)" if not b else
                   f"{len(sha_diff)} of {len(both)} part(s) differ"
                   + (f", e.g. {sha_diff[0]['part']}: ledger read {short(sha_diff[0]['ledger'])}, listed {short(sha_diff[0]['listed'])}"
                      if sha_diff else "")},
        {"check": "inventory: each part's raw rows are the listed ones", "ok": b and not row_diff,
         "detail": "not checked: the ledger's rows are cleaned rows, not raw rows (mode C)" if not b else
                   f"{len(row_diff)} of {len(both)} part(s) differ"
                   + (f", e.g. {row_diff[0]['part']}: ledger {row_diff[0]['ledger']}, listed {row_diff[0]['listed']}" if row_diff else "")},
    ]
    holds = {"folder": ledger.as_posix(), "clean_mode": mode, "parts": len(held), "packs": len(kept), "rows": sum(rows.values())}
    return checks, holds, {"ledger_parts_missing": missing, "ledger_parts_unlisted": unlisted, "ledger_packs_missing": packs_missing,
                           "ledger_packs_unlisted": packs_unlisted, "raw_sha256": sha_diff, "raw_rows": row_diff}


def check_shards(inv, shards):
    """([checks], what the shard summary holds, the differences) for the shard side."""
    shards = Path(shards)
    if not (shards / "shards_summary.json").is_file():
        raise Stop(f"--shards {shards}: no shards_summary.json")
    entries = read_object(shards / "shards_summary.json", "the shard summary").get("parts")
    if not isinstance(entries, dict) or not all(isinstance(e, dict) for e in entries.values()):
        raise Stop(f"--shards {shards}: shards_summary.json has no \"parts\" object of <part>: {{status, pack_id, ...}}")
    entries = {name.replace("\\", "/"): e for name, e in entries.items()}
    listed = inv["parts"]
    missing, unlisted = sorted(set(listed) - set(entries)), sorted(set(entries) - set(listed))
    both = sorted(set(listed) & set(entries))
    status_diff = [{"part": p, "status": entries[p].get("status"), "listed": listed[p]["expected"]} for p in both
                   if entries[p].get("status") not in listed[p]["expected"]]
    pack_diff = [{"part": p, "pack_id": entries[p].get("pack_id"), "listed": listed[p]["pack_id"]} for p in both
                 if entries[p].get("pack_id") != listed[p]["pack_id"]]  # an entry without pack_id differs too
    checks = [
        {"check": "inventory: the shard summary holds exactly the listed parts", "ok": not missing and not unlisted,
         "detail": f"{len(missing)} listed part(s) not in shards_summary.json{eg(missing)}; "
                   f"{len(unlisted)} part(s) in it not listed{eg(unlisted)}"
                   if missing or unlisted else f"all {len(listed)} listed parts, and no other"},
        {"check": "inventory: every part ended in a listed status", "ok": not status_diff,
         "detail": f"{len(status_diff)} of {len(both)} part(s) differ"
                   + (f", e.g. {status_diff[0]['part']}: status {status_diff[0]['status']!r}, listed "
                      f"{' or '.join(status_diff[0]['listed'])}" if status_diff else "")},
        {"check": "inventory: every part is of its listed pack", "ok": not pack_diff,
         "detail": f"{len(pack_diff)} of {len(both)} part(s) differ"
                   + (f", e.g. {pack_diff[0]['part']}: pack_id {pack_diff[0]['pack_id']!r}, listed {pack_diff[0]['listed']!r}"
                      if pack_diff else "")},
    ]
    holds = {"folder": shards.as_posix(), "parts": len(entries),
             "statuses": dict(sorted(Counter(str(e.get("status")) for e in entries.values()).items()))}
    return checks, holds, {"shard_parts_missing": missing, "shard_parts_unlisted": unlisted, "status": status_diff, "pack": pack_diff}


def check(inv, ledger=None, shards=None, cleaned=None):
    """The report of every check the given folders allow (see the docstring). Raises Stop only when an input cannot be
    read; a failed check is in the report ("ok": false)."""
    report = {"tool": "inventory_check.py", "code_sha256": code_sha256(Path(__file__))[0], "inventory": described(inv)}
    checks, differences = [], {}
    for side, folder, fn in (("cleaned", cleaned, check_manifest), ("ledger", ledger, check_ledger), ("shards", shards, check_shards)):
        if folder is None:
            continue
        got = fn(inv, folder)
        checks += got[0]
        if side != "cleaned":
            report[side] = got[1]
        differences.update(got[-1])
    report.update(differences=differences, checks=checks, ok=all(c["ok"] for c in checks))
    return report


def write_report(report, out):
    """The report as JSON, written to .tmp and renamed."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f"{out.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", type=Path, required=True, help="the expected inventory (JSON)")
    ap.add_argument("--ledger", type=Path, help="ledger.py's folder (run with --raw)")
    ap.add_argument("--shards", type=Path, help="run_shards.py's --out folder (shards_summary.json)")
    ap.add_argument("--cleaned", type=Path, help="the cleaned folder (job_summary.json), to check the input manifest")
    ap.add_argument("--out", type=Path, help="where the report goes (JSON)")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):  # a detail may hold "…": a console that cannot encode it must not stop the report
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    if args.ledger is None and args.shards is None:
        ap.error("give --ledger, --shards or both: there is nothing to check the inventory against")
    try:
        report = check(load(args.inventory), args.ledger, args.shards, args.cleaned)
        if args.out:
            write_report(report, args.out)
    except Stop as e:
        sys.exit(f"inventory_check: {e}")
    failed = [c for c in report["checks"] if not c["ok"]]
    print(json.dumps({"ok": report["ok"], "checks": len(report["checks"]), "failed": len(failed),
                      "parts": report["inventory"]["parts"], "packs": report["inventory"]["packs"]}))
    if failed:
        sys.exit("inventory_check: " + "; ".join(f"{c['check']}: {c['detail']}" for c in failed))


if __name__ == "__main__":
    main()
