"""Write a shard for every part in a pipeline run's final folder: shard_writer.py once per part.

  python -I teams/01-data-a/shards/run_shards.py --input <run>/final --manifest <run>/pipeline_manifest.json \
      --tokenizer <p1536>/tokenizer.json --dataset-version corpus-v1 --out <dir> [--pack code-go ...] [--tokens N]
      [--any-tokenizer]

--input is the run's final folder: <input>/<split>/<pack>/<part>.parquet, the layout run_pipeline.py gives it. Every part
found is handed to shard_writer.py (the split comes from the folder name), except a part in a folder named in
NOT_SHARDED (heldout, validation, val): it is reported as "not_sharded", which is not an error, because what a held-out
part becomes is for G3 and G9 to say. Language, script, domain and lane come from the pack's row in pack_table.json (--pack-table
for another table, such as a job's; one that also gives "license" and "license_source" has both written into every manifest); a pack that is not in the
table, or has a null field, is not sharded (status "skipped").

Shard numbers run across the parts of a pack and split, in part order: the writer fills a shard up to --tokens and rolls
over into the next number, so a part gets one shard or several, and the next part starts at the number after its last.
Without a rollover, part-00000 gets <pack>-<split>-000000, part-00001 gets 000001, and so on.

A part with no document to write gets no shard (never a zero-token one) and an explicit status: "empty" when it has no
rows (dedup or F2 removed them all), "all_left_out" when the writer left out every row; the doc_ids it left out are in
the part's entry ("left_out_docs"), where reconcile_shards.py finds them. A part the writer stops on (a broken link in
its chain, ...) is recorded as "failed" and the run goes on. It exits 1 unless every part was written, not_sharded,
empty or all_left_out.

Restart: the writer publishes each shard's manifest last (written to .tmp and renamed), and the summary is saved before
the first shard and after every part, so a run that stops part-way can be run again with the same arguments into the
same --out. Parts the summary holds as done, whose shards are the next numbers of their pack and whose files have the sha256 their manifests give,
are kept as they are; the first part that is not is written again, after every file of its pack numbered from there on
(and any .tmp) is removed. A rerun with other settings (--tokens, --dataset-version, tokenizer) is refused, as is a
--out that holds shards of a pack but no summary.

When it is done it checks the shards that are in --out (verify_shards.py: files, hashes, format, counts, pack table, and the first
and last document of each shard against the final part), not only what it just wrote. A part whose shard fails a check becomes
"failed" with the reason; a problem that belongs to no part (cleaning_pipeline.json missing, a shard no part accounts for) goes
to "problems" in the summary; any problem makes the exit code 1. "verified" is true when the checks found nothing, false when
they did, and null when there was no shard to check, or when --no-verify was given: then nothing is checked here and no part is
marked failed for its files. run_pipeline.py gives it to this script because the pipeline runs the same checks itself, once,
after it (the shard files are then read once, and the pipeline keeps their hashes); on its own, leave the flag out.

Writes <out>/shards_summary.json: for each part its status; for a written part its shards (the part-to-shards map: each
shard_id with its docs, tokens and the rows first_row..rows_read-1 of the part it covers), the docs, tokens and rows read
summed over them, rows_in_part, "truncated" (rows_read < rows_in_part: never, now that the writer rolls over; kept as a
check) and the docs left out per reason, with the run_id and the sha256 of cleaning_pipeline.json. A second run into the same --out
with --pack adds to the summary; one made for another run_id is refused, and the writer refuses other processing part by part.
Needs what shard_writer.py needs.
"""
import sys
sys.dont_write_bytecode = True

import argparse, contextlib, hashlib, io, json, os, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pack_table  # noqa: E402
import shard_writer  # noqa: E402
import verify_shards  # noqa: E402

SUMMARY = "shards_summary.json"
NOT_SHARDED = ("heldout", "validation", "val")  # split folders that are left alone (shard_writer.py also refuses a non-train part)


def find_parts(final, packs=()):
    """[(split, pack, part file)] of <final>/<split>/<pack>/*.parquet, sorted; only `packs` if given."""
    found = []
    for path in sorted(Path(final).glob("*/*/*.parquet")):
        split, pack = path.parent.parent.name, path.parent.name
        if not packs or pack in packs:
            found.append((split, pack, path))
    return found


def shards_of(out, split, pack):
    """The manifests <pack>-<split>-<6 digits>.json already in out."""
    return sorted(p.name for p in Path(out).glob(f"{pack}-{split}-*.json")
                  if re.fullmatch(rf"{re.escape(pack)}-{re.escape(split)}-\d{{6}}\.json", p.name))


DONE = ("written", "empty", "all_left_out")  # a part with one of these needs nothing more
FILE = re.compile(r"(?P<pack>.+)-(?P<split>[^-]+)-(?P<n>\d{6})\.(bin|idx\.npy|docs\.parquet|json|quality_report\.json|dump\.md)(\.tmp)?")


def settings_of(a):
    """What every shard of one --out must share; a rerun with other settings is refused."""
    return {"tokens": a.tokens or 2 ** 26, "dataset_version": a.dataset_version or "test",
            "tokenizer_sha256": shard_writer.sha(a.tokenizer)}


def save(path, summary):
    """Write the summary to a .tmp and rename it: a run stopped while saving leaves the previous one."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def reusable(out, split, pack, entry, index):
    """True when entry (a part the summary holds) is done and its shards are <pack>-<split>-<index>, <index + 1>, ... with
    files whose sha256 is what their manifests give."""
    if not entry or entry.get("status") not in DONE:
        return False
    ids = [x["shard_id"] for x in entry.get("shards", [])]
    if ids != [f"{pack}-{split}-{k:06d}" for k in range(index, index + len(ids))]:
        return False
    for sid in ids:
        mfile = out / f"{sid}.json"
        if not mfile.is_file():
            return False
        m = json.loads(mfile.read_text(encoding="utf-8"))
        # ponytail: hashes each kept shard once more here (verify_written hashes them again); fine at 2^26-token shards
        for uri, key in (("payload_uri", "payload_sha256"), ("index_uri", "index_sha256"), ("sample_metadata_uri", "sample_metadata_sha256")):
            f = out / m.get(uri, "")
            if not f.is_file() or shard_writer.sha(f) != m.get(key):
                return False
    return True


def clear_from(out, split, pack, index):
    """Remove every file of pack's shards numbered index or more, and its .tmp files: what a stopped run left part-way."""
    for f in Path(out).glob(f"{pack}-{split}-*"):
        m = FILE.fullmatch(f.name)
        if m and m["pack"] == pack and m["split"] == split and (int(m["n"]) >= index or f.name.endswith(".tmp")):
            f.unlink()


def no_shard_entry(e):
    """The summary entry of a part the writer found nothing to write in (shard_writer.NoShard)."""
    return {"status": "empty" if e.rows == 0 else "all_left_out", "shards": [], "docs": 0, "tokens": 0, "rows_read": e.rows,
            "rows_in_part": e.rows, "truncated": False, "left_out": {k: len(v) for k, v in e.left_out.items()},
            "left_out_docs": e.left_out}


def write_one(path, a, row, index):
    """Run shard_writer on one part, its first shard numbered index. Returns ([manifest, ...], None), (NoShard, None) or
    (None, why it stopped)."""
    argv = ["--input", str(path), "--manifest", str(a.manifest), "--tokenizer", str(a.tokenizer), "--out", str(a.out),
            "--language", row["language"], "--script", row["script"], "--domain", row["domain"], "--lane", row["lane"],
            "--index", str(index)]
    if "license" in row:  # a table with licences (pack_table.LICENCE): both go into the manifest
        argv += ["--license", row["license"], "--license-source", row["license_source"]]
    if a.tokens:
        argv += ["--tokens", str(a.tokens)]
    if a.any_tokenizer:
        argv.append("--any-tokenizer")
    if a.dataset_version:
        argv += ["--dataset-version", a.dataset_version]
    try:
        with contextlib.redirect_stdout(io.StringIO()):  # the writer prints a JSON line per shard; the summary has it
            return shard_writer.main(argv), None
    except shard_writer.NoShard as e:
        return e, None
    except SystemExit as e:
        return None, str(e.code)
    except Exception as e:  # one bad part must not stop the others
        return None, f"{type(e).__name__}: {e}"


def entry_of(manifests, out):
    """The summary entry of a written part, from its shards' manifests and quality reports."""
    shards, left_out = [], {k: 0 for k in shard_writer.LEFT_OUT}
    for m in manifests:
        report = json.loads((out / f"{m['shard_id']}.quality_report.json").read_text(encoding="utf-8"))
        shards.append({"shard_id": m["shard_id"], "docs": m["doc_count"], "tokens": m["token_count"],
                       "first_row": report["first_row"], "rows_read": report["rows_read"]})
        for k, v in report["left_out"].items():
            left_out[k] += v
    rows_in_part = report["upstream"]["counts"]["final"]
    return {"status": "written", "shards": shards, "docs": sum(x["docs"] for x in shards), "tokens": sum(x["tokens"] for x in shards),
            "rows_read": shards[-1]["rows_read"], "rows_in_part": rows_in_part, "truncated": shards[-1]["rows_read"] < rows_in_part,
            "left_out": left_out}


def count(summary):
    """{status: number of parts} for every status, and how many parts are truncated."""
    entries = summary["parts"].values()
    counts = {s: sum(e["status"] == s for e in entries) for s in ("written", "empty", "all_left_out", "failed", "skipped", "not_sharded")}
    counts["truncated"] = sum(bool(e.get("truncated")) for e in entries)
    counts["shards"] = sum(len(e.get("shards", [])) for e in entries if e["status"] == "written")
    return counts


def verify_written(a, summary):
    """Check the shards in a.out against their files (verify_shards.py), for every part the summary calls written. A problem
    that names a shard fails that part; the others go to summary["problems"]. Sets summary["verified"]; returns the problems."""
    summary["verified"], summary["problems"] = None, []
    written = {x["shard_id"]: name for name, e in summary["parts"].items() if e["status"] == "written" for x in e["shards"]}
    if not written:
        return []
    problems, _ = verify_shards.verify(a.out, a.manifest, a.tokenizer, a.pack_table, summary)
    by_part = {}
    for problem in problems:
        name = next((n for sid, n in written.items() if problem.startswith(sid + ": ")), None)
        if name is None:
            summary["problems"].append(problem)
        else:
            by_part.setdefault(name, []).append(problem)
    for name, found in by_part.items():
        entry = summary["parts"][name]
        more = f" (and {len(found) - 3} more)" if len(found) > 3 else ""
        summary["parts"][name] = {"pack_id": entry["pack_id"], "shards": entry["shards"], "status": "failed",
                                  "reason": "verify_shards: " + "; ".join(found[:3]) + more}
    summary["verified"] = not problems
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, required=True, help="the run's final folder: <input>/<split>/<pack>/<part>.parquet")
    ap.add_argument("--manifest", type=Path, required=True, help="the run's pipeline_manifest.json")
    ap.add_argument("--tokenizer", type=Path, required=True, help="G3's frozen p1536 tokenizer.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pack", action="append", default=[], help="only this pack (repeatable)")
    ap.add_argument("--tokens", type=int, help="fill each shard up to this many tokens (shard_writer's default: 2^26)")
    ap.add_argument("--any-tokenizer", action="store_true", help="tests only: accept a tokenizer other than p1536")
    ap.add_argument("--dataset-version", help="every manifest's dataset_version (e.g. sample, corpus-v1); required unless --any-tokenizer")
    ap.add_argument("--pack-table", type=Path, default=pack_table.TABLE)
    ap.add_argument("--no-verify", action="store_true",
                    help="do not check the shards when done (verify_shards.py): the caller does, as run_pipeline.py does; "
                         "'verified' in the summary is then null")
    a = ap.parse_args(argv)
    problem = shard_writer.dataset_version_problem(a.dataset_version, a.any_tokenizer)
    if problem:  # before anything is read or written: every part would fail on it
        sys.exit(f"run_shards: {problem}")

    table = pack_table.load(a.pack_table)
    parts = find_parts(a.input, a.pack)
    if not parts:
        sys.exit(f"run_shards: no <split>/<pack>/<part>.parquet in {a.input}" + (f" for {a.pack}" if a.pack else ""))
    run_id = json.loads(a.manifest.read_text(encoding="utf-8")).get("run_id")
    summary_path = a.out / SUMMARY
    summary = {"parts": {}}
    settings = settings_of(a)
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary["run_id"] != run_id:
            sys.exit(f"run_shards: {summary_path} is from another pipeline run ({summary['run_id']}) than {a.manifest} ({run_id}); use a new --out")
        if summary.get("settings", settings) != settings:
            sys.exit(f"run_shards: {summary_path} was made with {summary['settings']}, this run has {settings}. Nothing was "
                     "written; use a new --out")
    else:
        taken = [n for split, pack in sorted({(s, p) for s, p, _ in parts if s not in NOT_SHARDED}) for n in shards_of(a.out, split, pack)]
        if taken:
            sys.exit(f"run_shards: already in {a.out}, with no {SUMMARY}: {', '.join(taken[:5])}{' ...' if len(taken) > 5 else ''}. "
                     "Nothing was written; use a new --out")
    summary["run_id"], summary["settings"] = run_id, settings
    a.out.mkdir(parents=True, exist_ok=True)
    save(summary_path, summary)  # before the first shard: a run stopped in its first part can be run again too

    this_run, next_index = [], {}  # the names of the parts this run handled; (split, pack) -> the number of its next shard
    for split, pack, path in parts:
        name, kept = f"{split}/{pack}/{path.name}", False
        if split in NOT_SHARDED:
            entry = {"pack_id": pack, "status": "not_sharded", "reason": f"{split} is not sharded (held-out data: G3 and G9 decide)"}
        else:
            entry = {"pack_id": pack}
            try:
                row = pack_table.row(pack, table)
            except pack_table.PackTableError as e:
                entry.update(status="skipped", reason=str(e))
            else:
                index = next_index.get((split, pack), 0)
                if reusable(a.out, split, pack, summary["parts"].get(name), index):
                    entry, kept = summary["parts"][name], True  # done by an earlier run that stopped later
                else:
                    clear_from(a.out, split, pack, index)
                    manifests, why = write_one(path, a, row, index)
                    if why:
                        entry.update(status="failed", reason=why)
                    elif isinstance(manifests, shard_writer.NoShard):
                        entry.update(no_shard_entry(manifests))
                    else:
                        entry.update(entry_of(manifests, a.out))
                next_index[(split, pack)] = index + len(entry.get("shards", []))
        summary["parts"][name] = entry
        save(summary_path, summary)  # after every part: a rerun picks up from here
        this_run.append(name)
        note = (f"{len(entry['shards'])} shard(s), {entry['docs']} docs, {entry['tokens']} tokens" + (" TRUNCATED" if entry["truncated"] else "")
                + (" (kept from an earlier run)" if entry["status"] == "written" and kept else "")
                if entry["status"] in DONE else entry["reason"])
        print(f"{entry['status']:8} {name}: {note}", file=sys.stderr if entry["status"] in ("failed", "skipped") else sys.stdout)

    pipeline = a.out / "cleaning_pipeline.json"  # written by the writer with the run's first shard
    summary = {"run_id": run_id, "settings": settings,
               "cleaning_pipeline_sha256": hashlib.sha256(pipeline.read_bytes()).hexdigest() if pipeline.is_file() else None,
               "parts": summary["parts"]}
    summary["counts"] = count(summary)
    if a.no_verify:
        summary["verified"], summary["problems"], problems = None, [], []
    else:
        problems = verify_written(a, summary)
    for name, e in summary["parts"].items():
        if e["status"] == "failed" and e["reason"].startswith("verify_shards: "):
            print(f"failed   {name}: {e['reason']}", file=sys.stderr)
    for problem in summary["problems"]:
        print(f"problem  {problem}", file=sys.stderr)
    summary["counts"] = count(summary)
    save(summary_path, summary)
    print(json.dumps(summary["counts"]))
    statuses = {summary["parts"][n]["status"] for n in this_run}  # this run's parts, not those an earlier run left in the summary
    return 0 if statuses <= {*DONE, "not_sharded"} and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
