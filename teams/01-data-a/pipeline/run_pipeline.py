"""One command for Data A's pipeline: clean -> overlap -> optional H3 -> dedup -> apply -> F2 -> survivor loss -> ledger -> shards.

  python -I teams/01-data-a/pipeline/run_pipeline.py --config teams/01-data-a/pipeline/pipeline.json [--plan]

It runs or adopts each stage in order, checks that each stage follows from the one before (counts and sha256 links), and
writes <out>/<run_id>/pipeline_manifest.json. It never reimplements a stage: clean (#244), overlap and dedup (#255) and F2
(run_f2.py, #35) are the team's scripts, called as they are; apply_dedup.py, survivor_loss.py and ledger.py are in this
folder.

STAGES
======
  clean          cleaned parts: <output>/train/**.parquet and/or <output>/heldout/**.parquet              (TSAI job, #244)
  overlap        overlap_summary.json, overlap_matches.csv, overlap_docs.parquet                          (TSAI job, #255)
  h3             optional, report-only translation matches from the same cleaned parts; requires stages.h3 (TSAI job)
  dedup          remove_list.csv, dedup_groups.csv, dedup_summary.json                                    (TSAI job, #255)
  apply          apply_dedup.py on clean's output with dedup's remove list  -> <run>/deduped
  f2             run_f2.py on <run>/deduped/<split>                           -> <run>/final/<split>
                 (one process per split; with "workers": N, up to N processes at once, one per pack folder)
  survivor_loss  survivor_loss.py on dedup_groups.csv and F2's reports        -> <run>/report
  ledger         ledger.py: one row per document with each stage's decision  -> <run>/ledger
  shards         optional, only with stages.shards: writes <run>/cleaning_pipeline.json (clean.py sha256, F2 set, dedup remove
                 list, overlap run and dedup settings: the processing behind the shards), then shards/run_shards.py on <run>/final   -> <run>/shards (or "out")
                 It runs after the manifest holds every earlier stage, which is what the shard writer reads; its own record is
                 added to the manifest afterwards. The stage stops the run if a part failed or was skipped, if no shard was
                 written, if the summary is not this run's, or if the shards on disk do not verify (verify_shards.py). "from": "shards" runs only this stage, into an out folder without shards.

clean, overlap and dedup take "mode": "adopt" (TSAI ran the job; "output" names the folder it returned) or "mode": "run".
H3 runs only when stages.h3 is configured, and must use "mode": "run" on this job's cleaned parts. Its matches are
passed to dedup with remove: false; the runner verifies H3's summary, match-file hash and dedup's recorded hash.
A run stage names a "settings" file (settings only, no paths) and the runner works out the rest: its folder is <run>/<stage>
(or "output", below ./out), it reads the previous stage's folder, and stage_args.py turns that into the script's command. clean
gets a copy of its settings with the path keys filled in (clean: input_root from "input", output_root, and the input set's
description from the stage: manifest, manifest_sha256, expected_parts, sample; overlap/H3: inputs, out; dedup: results, inputs,
out), written to <run>/cfg/<stage>.json and passed with --config. The clean stage's manifest defaults to sample_manifest.json in
its input folder, and its sha256 must equal manifest_sha256; its parts must match expected_parts and add up to its total_docs (clean_manifest.py: --plan checks it, and the job again when it starts). "script" replaces the default script (for clean: pipeline/clean_job.py, which loads the cleaner its settings file names and pins), and may be a list (the script, then the arguments that go before --config: a script run through a wrapper; the manifest then records the sha256 of both); clean also takes "resume": true, to continue an interrupted clean job in its folder (the job verifies the parts it finished; logs/clean.log is appended to); "settings_sha256" pins the settings file
(checked, and the manifest records the file's sha256 either way). Escape hatch: "command" (the script and its arguments, run
with this Python from the repository root) with "output" (where that script writes) skips all of this.
--plan checks the config and prints each stage's folder and command, without running or writing anything. It is the only
option besides --config: every run parameter is in the config file, so a run is reproduced from that file alone.

RUN PARAMETERS (all in the config file; the manifest embeds the whole config)
  run_id                 names the run: its folders are <out>/<run_id>/ (the clean job refuses an existing folder, so a new run
                         needs a new run_id)
  "mode": "adopt"        on clean, overlap or dedup, with "output": the folder to use instead of running the stage
  to                     stop after this stage; only the stages up to it are checked
  from                   resume at this stage: the earlier stages must be recorded in the manifest with unchanged digests
  stages.clean.only      run the clean job on these sample parts only (a list, for trials); overlap then expects no packs
  intermediates          "keep" (default): every stage's Parquet stays on disk, e.g. for the audit of the cleaner, which
                         reads the parts before and after clean.py. "drop": once reconcile has passed, the run deletes,
                         from <run>/deduped and <run>/final, the Parquet of every part whose kept documents are all in
                         shards (or left out by the shard writer for a stated reason), after checking every one of those
                         shards on disk against its manifest (files, sha256, header, size, index, rows: shard_problems;
                         one that fails stops the drop before anything is deleted). A held-out part, a part of a pack
                         the shard stage was not asked for and a part without kept documents stay, in both folders. The
                         cleaned folder is never touched (other runs adopt it), nor the raw input, the reports, summaries,
                         ledger, manifest and shards. It needs a run that ends at reconcile, and such a run cannot be
                         resumed or rerun in place afterwards (new run_id)
  inventory              optional: the expected inventory of the run (inventory_check.py): every part of the approved
                         input manifest with its pack, raw sha256, raw rows and the status its shards must end in. It is
                         written before the run, from the manifest, so it can say what the run's own outputs cannot:
                         that a pack or part never reached the run. A run with an inventory is the production run: it
                         needs stages.ledger.raw (every raw document accounted for, mode B), stages.shards and
                         stages.reconcile, it must end at reconcile (no earlier "to"), and stages.shards.packs, if
                         given, must be the inventory's packs. Without the key nothing of this is checked or required:
                         --plan and the manifest then say "inventory: none"
A top-level key that is none of these and does not start with "_" (a comment) is refused; so are a key under "stages"
that is not a stage, and "inventory" or "intermediates" inside a stage's settings. A mistyped or misplaced one of the
two is therefore not silently ignored.
apply, f2, survivor_loss and ledger always run. f2 takes "script" (default teams/01-data-a/spec_v1/run_f2.py) and "workers"
(default 1; each run_f2.py process loads G9's full set, about 1.1 GB of memory, so N workers need about N × 1.1 GB plus the
documents in flight). shards takes "tokenizer" (required: G3's frozen tokenizer.json, p1536), "dataset_version" (required: the
corpus release written into every shard manifest, e.g. "corpus-v1" for the first training shards or "sample"; with
"any_tokenizer" it is "test" and may be left out), and optionally "script" (default
teams/01-data-a/shards/run_shards.py), "out" (default <run>/shards), "tokens", "packs" (only these packs), "pack_table" and
"any_tokenizer" (tests only). apply takes "link" (default true: untouched parts are hard-linked, not copied) and "workers"
(default 4: parts checked and written at once, one row group in memory each). ledger takes "raw"
(optional: the raw parts the cleaner read; with it the ledger says keep / fix / drop per document, mode B, else the
cleaner's decision is "unknown", mode C); it reads dedup_log.jsonl when the dedup folder has one. Scripts run with
python -I, which ignores user site-packages and PYTHONPATH: install pyarrow and the rest into the environment itself.
Each script's output streams to <run>/logs/<stage>.log (F2: logs/f2_<split>[_<pack>].log).
Without stages.shards the run stops after the ledger, and "to": "shards" is an error.

CONFIG (JSON; keys starting with "_" are comments; paths relative to the repository root, or absolute)
=====================================================================================================
  run_id   name of this run;   out   folder for runs (default out/pipeline);   stages   as above
  hash_cache   true (default): every sha256 is computed once and kept in <run>/cache/sha256.json, keyed on each file's
               (device, inode, size, mtime, change time), so the digests reuse apply's hashes and a resumed run hashes
               nothing it has already hashed (hashing.py). false: hash everything again, for an audit
The whole config is checked before the first stage runs.

CHECKS (any failure stops the run; exit code 1)
==============================================
  clean     (a stage run from settings; an adopted folder only when it has a job_summary.json in the clean job's format, else
            the record says "job_summary_checked": false) the job's job_summary.json against the folder: no errors; the parts
            it did = the parts the run expects (stages.clean.expected_parts, or the --only parts), each with a report; it read
            this run's manifest_sha256; input rows = output rows + dropped, and the output rows = the Parquet footers'; the
            parts on disk are the parts it lists, with their rows; each part's sha256 is the one it recorded
  overlap   status complete; documents_all = the cleaned rows; for every part it lists, its documents = that cleaned part's rows
  dedup     status complete; the overlap_matches.csv and overlap_docs.parquet it checked (overlap_run.checked_sha256) are
            the adopted overlap's files; documents_all = overlap's; removed = remove_list.csv rows; heldout_removed = 0
  apply     rows = the cleaned rows; removed = the remove list (apply_dedup.py also checks every listed row)
  f2        per split: its rows = apply's kept rows; every part's report names, as input_sha256, the sha256 apply wrote;
            one fingerprint set; kept + dropped + errors = rows; no errors; no stale Parquet under final/<split>
  survivor  the groups in dedup_groups.csv = dedup_summary.json's clusters; groups without a survivor and groups with
            several = its groups_without_survivor and groups_with_several_survivors (with H3, up to
            h3.groups_survivor_removed more groups without one, and no more with several)
  ledger    its cleaned rows = the cleaned rows; removed_by_dedup = apply's removed; dropped_by_f2, f2_error and kept =
            F2's; one fingerprint set, F2's (ledger.py also checks every final part holds the ledger's kept docs in order);
            per pack and split, its cleaned rows and removed_by_dedup = apply_dedup_summary.json's by_pack; the dedup
            survivors F2 dropped, in total and per pack = survivor_loss_summary.json's
  shards    no part failed or was skipped; run_shards.py exited 0; at least one shard written; the summary is this run's;
            the shards on disk verify (verify_shards.py, independent of the summary and of the shard script): files and
            sha256, .bin header and size, index, special ids, metadata, pack table row, tokenizer, F2 set, and the first and
            last document of every shard against the final part. This is the one verification of a pipeline run: the default
            run_shards.py is told --no-verify, so a shard is read once (its hashes go to the hash cache for the digest)
  from      every earlier stage's output still has the digest the manifest recorded for it
  inventory (only with "inventory") before the shard stage does anything, also when the run resumes there: the
            ledger is mode B and holds exactly the listed parts, each with its listed raw sha256 and raw rows; every
            listed pack is in it and no other pack has kept documents; the clean job's job_summary.json names the
            inventory's input manifest (a summary that names none fails). After reconcile: the same again, and
            shards_summary.json holds exactly the listed parts, each with a listed status and its listed pack. Every
            difference is written to <run>/inventory_check.json before the run stops. The ledger stage is already
            recorded when the first check point stops the run, so a corrected inventory resumes with "from": "shards".
            A check point writes its report and never the manifest: a resumed run it stops leaves the manifest as it was

MANIFEST
========
<out>/<run_id>/pipeline_manifest.json: the git commit, Python and pyarrow versions; per stage its mode, command, the script's
sha256, its output folder's digest and file count, its counts, its checks and its seconds; all checks; totals (raw and dropped
by clean when the ledger ran in mode B, cleaned, removed by dedup, dropped by F2, final, and shards_written when the shard
stage ran), and by_pack: the same chain for every pack and split, from the ledger. At the end of a run the per-pack
table is also printed to stderr. A digest is the sha256 over the sorted relative path and sha256 of every file in the folder;
JSON summaries are hashed without the fields that change between identical runs (timings, absolute paths, skip flags), so two
runs on the same inputs give the same digests. The files are hashed in parallel threads, through the run's hash cache.
"intermediates" holds the mode and, after a drop, how many parts went and how many were left, how many shards were checked
on disk (shards_verified), and per folder the Parquet
files and bytes deleted; the stage digests stay those of the folders as they were checked, before the drop.
"inventory" is null without one. With one it names the inventory file, its sha256 and its counts of packs and parts,
under "checked" the sha256 of the inventory each check point passed with (ledger: before the shard stage; reconcile:
after it), and under "report" where the check points write. "checked" is read from the shards and reconcile stage
records, which carry that sha256 as inventory_sha256: it is null until the stage is recorded.
IDs, counts and hashes only.
"""
import sys
sys.dont_write_bytecode = True

import argparse, csv, hashlib, json, os, platform, subprocess, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import inventory_check  # noqa: E402  (the expected inventory: "inventory" in the config)
import stage_args  # noqa: E402  (how clean, overlap and dedup get their paths)
from hashing import HashCache, code_sha256  # noqa: E402  (every sha256 once, in parallel)
STAGES = ("clean", "overlap", "h3", "dedup", "apply", "f2", "survivor_loss", "ledger", "shards", "reconcile")
OPTIONAL = ("h3", "shards", "reconcile")  # run only when configured
EXTERNAL = ("clean", "overlap", "h3", "dedup")
CLEAN_SUMMARY = ("completed_parts", "expected_parts", "input_rows", "output_rows", "actions", "errors", "parts")  # a clean job's job_summary.json
NEEDED = {"overlap":("overlap_summary.json", "overlap_matches.csv", "overlap_docs.parquet"),
          "h3": ("h3_summary.json", "h3_matches.csv"),
          "dedup": ("remove_list.csv", "dedup_groups.csv", "dedup_summary.json")}
DEFAULT_F2 = "teams/01-data-a/spec_v1/run_f2.py"
DEFAULT_SHARDS = "teams/01-data-a/shards/run_shards.py"
POOL = "teams/01-data-a/pipeline/f2_pool.py"
SPLITS = ("train", "heldout")
RESERVED = ("deduped", "final", "report", "ledger", "shards", "reconcile", "cfg", "logs", "cache", "h3_cache")  # folders of the run that no stage output may take
BESIDE = (".partial", ".old", ".lock")  # what the scripts make next to a folder they write: <x>.partial, <x>.old, <x>.lock
INTERMEDIATES = ("keep", "drop")  # the run's own Parquet between the input and the shards: left on disk, or deleted at the end
KEYS = ("run_id", "out", "stages", "from", "to", "hash_cache", "intermediates", "inventory")  # every top-level key of a run config
# JSON fields that differ between identical runs: timings, absolute or run-named paths, skip flags (and overlap.py's and
# dedup.py's wall time, peak memory and the output folders they record when the runner runs them)
VOLATILE = {"seconds", "input", "path", "cleaned", "skipped", "wall_seconds", "peak_rss_mb", "out", "results"}


class Stop(Exception):
    """A check failed: the message says which and where."""


_CACHE = HashCache()  # in memory, for digest() called without the run's cache
FOOTER_WORKERS = 16  # threads reading Parquet footers


def sha256(path):
    return _CACHE.sha256(path)


def stable(obj):
    if isinstance(obj, dict):
        return {k: stable(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [stable(v) for v in obj]
    return obj


def json_hash(p):
    """sha256 of a JSON file's content without the volatile fields, or None when it is not valid JSON."""
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return hashlib.sha256(json.dumps(stable(data), sort_keys=True).encode("utf-8")).hexdigest()


def file_hash(p, cache=None):
    """sha256 of a file; for JSON, of its content without the volatile fields."""
    if p.suffix == ".json":
        h = json_hash(p)
        if h is not None:
            return h
    return (cache or _CACHE).sha256(p)


def digest(folder, cache=None):
    """(digest over every file's relative path and hash, file count). The data files are hashed through `cache`, in
    parallel threads, so a file another stage already hashed (or a hard link to it) is not read again."""
    folder, cache = Path(folder), cache or _CACHE
    files = sorted(p for p in folder.rglob("*") if p.is_file() and not p.name.endswith(".tmp"))
    hashes = {p: json_hash(p) for p in files if p.suffix == ".json"}
    hashes.update(cache.sha256_many([p for p in files if hashes.get(p) is None]))
    h = hashlib.sha256()
    for p in files:
        h.update(f"{p.relative_to(folder).as_posix()}\t{hashes[p]}\n".encode("utf-8"))
    return h.hexdigest(), len(files)


def path(p):
    p = Path(p)
    return p if p.is_absolute() else REPO / p


def run_script(script, args, stage, log, append=False):
    """Run a script with this Python from the repository root, its output streamed to log. Returns the exit code.
    append: add to the log (a resumed stage keeps the log of the attempt before it), with a blank line between."""
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-I", str(path(script)), *map(str, args)]
    with open(log, "a" if append else "w", encoding="utf-8", errors="replace") as f:
        if append and f.tell():
            f.write("\n")
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        return subprocess.run(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT).returncode


def tail(log, n=5):
    try:
        return " | ".join(Path(log).read_text(encoding="utf-8", errors="replace").strip().splitlines()[-n:])
    except OSError:
        return ""


def parquet_rows(folder):
    """{"rows", "by_split", "by_part" ({"<split>/<part>": rows})} from the Parquet footers."""
    import pyarrow.parquet as pq
    files = [(split, f) for split in SPLITS if (folder / split).is_dir() for f in sorted((folder / split).rglob("*.parquet"))]

    def rows(item):
        split, f = item
        try:
            return pq.read_metadata(f).num_rows
        except Exception as e:  # not Parquet, truncated, unreadable
            raise Stop(f"clean: {split}/{f.relative_to(folder / split).as_posix()} cannot be read as Parquet ({type(e).__name__})")

    with ThreadPoolExecutor(max_workers=max(1, min(FOOTER_WORKERS, len(files)))) as pool:  # thousands of footers
        counts = list(pool.map(rows, files))
    by_split, by_part = {}, {}
    for (split, f), n in zip(files, counts):
        by_part[f"{split}/{f.relative_to(folder / split).as_posix()}"] = n
        by_split[split] = by_split.get(split, 0) + n
    if not by_split:
        raise Stop(f"clean: {folder} has no Parquet parts under train/ or heldout/")
    return {"rows": sum(by_split.values()), "by_split": by_split, "by_part": by_part}


def csv_column(file, column):
    """One column of a CSV, every value a string, read by pyarrow (a remove list can hold millions of rows)."""
    import pyarrow as pa, pyarrow.csv as pcsv
    try:
        return pcsv.read_csv(file, parse_options=pcsv.ParseOptions(newlines_in_values=True),
                             convert_options=pcsv.ConvertOptions(include_columns=[column], column_types={column: pa.string()},
                                                                 strings_can_be_null=False)).column(column)
    except (pa.ArrowInvalid, KeyError) as e:
        raise Stop(f"{file}: cannot be read as CSV with a {column} column ({e})")


def csv_rows(file):
    """Records of a CSV, without the header (a quoted value may hold a newline, so lines are not records). The header is
    read as CSV, so a quoted column name ("pack_id_a", as pyarrow's write_csv in h3.py writes it) is the name pyarrow
    reads back."""
    with open(file, encoding="utf-8", newline="") as f:
        row = next(csv.reader([f.readline()]), [])
    first = row[0] if row else ""
    return len(csv_column(file, first)) if first else 0


def load_json(file):
    return json.loads(Path(file).read_text(encoding="utf-8"))


SHARD_MAGIC, SHARD_VERSION, SHARD_HEADER_BYTES = 20261025, 2, 1024  # shard format v1 (shards/shard_format_v1.md, G9's decoder)
SHARD_FILES = (("payload_uri", "payload_sha256"), ("index_uri", "index_sha256"),
               ("sample_metadata_uri", "sample_metadata_sha256"), ("quality_report_uri", "quality_report_sha256"))
SHARD_SUFFIXES = (".bin", ".idx.npy", ".docs.parquet", ".quality_report.json")  # <shard_id><suffix>, as shard_writer.py names them


def shard_problems(folder, shard_id, entry, cache):
    """What is wrong with one written shard on disk, checked against its own manifest (<folder>/<shard_id>.json) and its
    entry in shards_summary.json: [] when nothing is. Every file the manifest names has the writer's name
    (<shard_id>.bin, .idx.npy, .docs.parquet, .quality_report.json), is a file in the folder (not a link) and has the
    sha256 the manifest gives (a file that does not is not read further); the .bin has the format's header (magic, version, token count) and is exactly header +
    4 bytes a token; the index is int64, starts at 0, rises, and ends at the token count, one entry more than documents; the
    .docs.parquet has one row a document; and the summary's docs and tokens are the manifest's. A shard that passes
    holds what reconcile counted, so the Parquet it came from may go."""
    import numpy as np
    import pyarrow.parquet as pq
    mfile = folder / f"{shard_id}.json"
    try:
        m = load_json(mfile)
    except (OSError, ValueError) as e:
        return [f"{mfile.name}: cannot be read ({type(e).__name__})"]
    if not isinstance(m, dict) or m.get("shard_id") != shard_id:
        return [f"{mfile.name}: not the manifest of {shard_id}"]
    files, problems = {}, []
    for (uri, _), suffix in zip(SHARD_FILES, SHARD_SUFFIXES):
        name, want = m.get(uri), f"{shard_id}{suffix}"
        if name != want:  # the writer's names (shard_writer.py): never another shard's file, nor one elsewhere
            problems.append(f"{mfile.name}: {uri} is {name!r}, expected {want!r}")
        elif (folder / name).is_symlink() or not (folder / name).is_file():
            problems.append(f"{name}: missing" if not (folder / name).is_symlink() else f"{name}: a link, not the file")
        else:
            files[uri] = folder / name
    if problems:
        return problems
    shas = cache.sha256_many(files.values())
    problems = [f"{files[uri].name}: sha256 {shas[files[uri]][:12]}…, the manifest has {str(m.get(key))[:12]}…"
                for uri, key in SHARD_FILES if shas[files[uri]] != m.get(key)]
    if problems:  # a file that is not the one the writer recorded: what it holds no longer matters
        return problems
    tokens, docs = m.get("token_count"), m.get("doc_count")
    if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in (tokens, docs)):
        return [f"{mfile.name}: token_count {tokens!r}, doc_count {docs!r}"]
    payload = files["payload_uri"]
    size = payload.stat().st_size
    head = np.fromfile(payload, dtype="<i4", count=3) if size >= 12 else np.zeros(0, dtype="<i4")
    if len(head) != 3 or (int(head[0]), int(head[1]), int(head[2])) != (SHARD_MAGIC, SHARD_VERSION, tokens):
        problems.append(f"{payload.name}: header {head.tolist()}, expected [{SHARD_MAGIC}, {SHARD_VERSION}, {tokens}]")
    if size != SHARD_HEADER_BYTES + 4 * tokens or m.get("payload_bytes") != size:
        problems.append(f"{payload.name}: {size:,} bytes, expected {SHARD_HEADER_BYTES + 4 * tokens:,} "
                        f"(manifest payload_bytes {m.get('payload_bytes')})")
    try:
        idx = np.load(files["index_uri"], mmap_mode="r", allow_pickle=False)
        ok = (isinstance(idx, np.ndarray) and idx.dtype == np.dtype("<i8") and idx.ndim == 1 and len(idx) == docs + 1
              and int(idx[0]) == 0 and int(idx[-1]) == tokens and bool((np.diff(idx) > 0).all()))
        why = "" if isinstance(idx, np.ndarray) and idx.dtype == np.dtype("<i8") else f" ({getattr(idx, 'dtype', type(idx).__name__)})"
    except Exception as e:  # a cut or foreign file: EOFError, BadZipFile, ValueError, ...
        ok, why = False, f" (cannot be read: {type(e).__name__})"
    if not ok:
        problems.append(f"{files['index_uri'].name}: not {docs + 1} rising int64 offsets from 0 to {tokens}{why}")
    try:
        rows = pq.read_metadata(files["sample_metadata_uri"]).num_rows
    except Exception as e:
        rows = None
        problems.append(f"{files['sample_metadata_uri'].name}: cannot be read ({type(e).__name__})")
    if rows is not None and rows != docs:
        problems.append(f"{files['sample_metadata_uri'].name}: {rows} rows, the manifest has {docs} documents")
    for key, want in (("docs", docs), ("tokens", tokens)):
        if key in entry and entry[key] != want:
            problems.append(f"shards_summary.json: {key} {entry[key]} for {shard_id}, the manifest has {want}")
    return problems


class Run:
    def __init__(self, cfg_path):
        """Every run parameter is in the config file: run_id, the stages (each run from a settings file or adopted), and the
        optional "from", "to" and stages.clean.only (see the docstring)."""
        self.cfg_path = Path(cfg_path)
        self.cfg = load_json(self.cfg_path)
        if not isinstance(self.cfg, dict):
            raise Stop(f"{cfg_path}: expected a JSON object")
        if not self.cfg.get("run_id"):
            raise Stop(f"{cfg_path}: run_id is missing")
        unknown = sorted(k for k in self.cfg if not k.startswith("_") and k not in KEYS)
        if unknown:  # a mistyped key would otherwise be ignored: "Inventory" would run without any inventory check
            raise Stop(f"config: unknown key {unknown[0]!r}; the run parameters are {', '.join(KEYS)} (a key starting with "
                       "\"_\" is a comment)")
        self.stages = self.cfg.setdefault("stages", {})
        if not isinstance(self.stages, dict):
            raise Stop("config: stages must be an object of stage settings")
        unknown = sorted(k for k in self.stages if not k.startswith("_") and k not in STAGES)
        if unknown:  # "inventory" under "stages" would be ignored in the same way
            raise Stop(f"config: stages.{unknown[0]} is not a stage; the stages are {', '.join(STAGES)} (a key starting with "
                       "\"_\" is a comment)")
        for name, spec in self.stages.items():  # and one level deeper: no stage has a setting by these names
            for key in ("inventory", "intermediates"):
                if isinstance(spec, dict) and key in spec:
                    raise Stop(f"config: stages.{name}.{key}: \"{key}\" is a run parameter, not a stage setting; set it at the "
                               "top level of the config")
        clean = self.stages.get("clean")
        self.only = (clean.get("only") or []) if isinstance(clean, dict) else []
        if not isinstance(self.only, list) or not all(isinstance(p, str) for p in self.only):
            raise Stop("config: stages.clean.only must be a list of sample parts, e.g. [\"train/code-go/part-00000.parquet\"]")
        self.dir = path(self.cfg.get("out", "out/pipeline")) / self.cfg["run_id"]
        self.manifest_path = self.dir / "pipeline_manifest.json"
        if not isinstance(self.cfg.get("hash_cache", True), bool):
            raise Stop("config: hash_cache must be true or false")
        self.cache = HashCache(self.dir / "cache" / "sha256.json", enabled=self.cfg.get("hash_cache", True))
        self.done, self.checks, self.dropped = {}, [], None
        self.inventory = None  # the expected inventory, once validate() has read it
        self.checked = None  # the sha256 of the inventory the stage being run has passed a check point with

    def output(self, stage):
        if stage in EXTERNAL:
            spec = self.stages.get(stage) or {}
            return path(spec["output"]) if spec.get("output") else self.dir / stage  # default: inside the run folder
        if stage == "shards":
            return path(self.stages["shards"]["out"]) if self.stages.get("shards", {}).get("out") else self.dir / "shards"
        return self.dir / {"apply": "deduped", "f2": "final", "survivor_loss": "report", "ledger": "ledger",
                           "reconcile": "reconcile"}[stage]

    def last_stage(self):
        """Where a run stops without "to": reconcile when configured (with shards), else shards when configured, else the ledger."""
        if "shards" in self.stages and "reconcile" in self.stages:
            return "reconcile"
        return "shards" if "shards" in self.stages else "ledger"

    def shown(self, p):
        """A path as the manifest and the plan show it: relative to the repository when inside it, else absolute."""
        p = Path(p).resolve()
        try:
            return p.relative_to(REPO.resolve()).as_posix()
        except ValueError:
            return p.as_posix()

    def stage_command(self, stage, write):
        """None for an adopted stage; else {command, settings, settings_sha256, config, config_sha256} (stage_args.build, or the
        run config's own "command"). write=False checks and names the generated config without writing it."""
        spec = self.stages[stage]
        if spec.get("mode", "adopt") != "run":
            return None
        if spec.get("command"):
            return {"command": spec["command"], "settings": None, "settings_sha256": None, "config": None, "config_sha256": None}
        try:
            return stage_args.build(stage, spec, {s: self.output(s) for s in EXTERNAL if s != "h3" or s in self.stages}, self.dir / "cfg", REPO, write, self.only)
        except stage_args.ConfigError as e:
            raise Stop(f"config: {stage}: {e}")

    def validate(self, upto):
        """The config of every stage up to `upto`, before anything runs."""
        active = [s for s in EXTERNAL if STAGES.index(s) <= STAGES.index(upto) and (s != "h3" or s in self.stages)]
        if "h3" in active and isinstance(self.stages["h3"], dict) and self.stages["h3"].get("mode") != "run":
            raise Stop("config: stages.h3 must run on this job's cleaned parts")
        if self.only:
            clean = self.stages.get("clean") or {}
            if clean.get("mode", "adopt") != "run" or clean.get("command"):
                raise Stop("config: stages.clean.only limits the clean job to some parts, so clean must run from a settings file (not adopted, not a command)")
        for stage in active:
            spec = self.stages.get(stage)
            if not isinstance(spec, dict):
                raise Stop(f"config: stages.{stage} is missing")
            mode = spec.get("mode", "adopt")
            if mode not in ("adopt", "run"):
                raise Stop(f"config: stages.{stage}.mode is {mode!r}, expected adopt or run")
            if mode == "adopt" and not spec.get("output"):
                raise Stop(f"config: stages.{stage}.output is missing (an adopted stage needs the folder that was returned)")
            if mode == "run":
                cmd = spec.get("command")
                if "command" in spec and (not cmd or not isinstance(cmd, list)):
                    raise Stop(f"config: stages.{stage}.command (a list: script, then arguments) is missing for mode run")
                if cmd and not spec.get("output"):
                    raise Stop(f"config: stages.{stage}.output is missing: with a command, say where it writes")
                if cmd and not path(cmd[0]).is_file():
                    raise Stop(f"config: stages.{stage}.command script {cmd[0]} not found")
                script = spec.get("script", stage_args.DEFAULT_SCRIPT.get(stage))
                given = [script] if isinstance(script, str) else script if isinstance(script, list) else []
                for n, s in enumerate([] if cmd else given):  # a list: the script, then what goes before --config
                    if isinstance(s, str) and s and (n == 0 or s.endswith(".py")) and not path(s).is_file():
                        raise Stop(f"config: stages.{stage} script {s} not found")
                self.stage_command(stage, write=False)
        for stage, default in (("f2", 1), ("apply", 4)):
            workers = self.stages.get(stage, {}).get("workers", default)
            if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
                raise Stop(f"config: stages.{stage}.workers is {workers!r}, expected a whole number >= 1")
        if not isinstance(self.stages.get("f2", {}).get("pool", False), bool):
            raise Stop("config: stages.f2.pool must be true or false")
        if "reconcile" in self.stages and "shards" not in self.stages:
            raise Stop("config: stages.reconcile needs stages.shards: it reconciles the shards with the ledger")
        if upto == "reconcile" and "reconcile" not in self.stages:
            raise Stop("config: \"to\": \"reconcile\" needs stages.reconcile (it runs only when configured)")
        if STAGES.index(upto) >= STAGES.index("f2"):
            script = self.stages.get("f2", {}).get("script", DEFAULT_F2)
            if not path(script).is_file():
                raise Stop(f"config: f2 script {script} not found (run_f2.py is teams/01-data-a/spec_v1/run_f2.py; set stages.f2.script)")
        raw = self.stages.get("ledger", {}).get("raw")
        if STAGES.index(upto) >= STAGES.index("ledger") and raw is not None and not path(raw).is_dir():
            raise Stop(f"config: stages.ledger.raw {raw} is not a folder")
        if "shards" in self.stages or upto == "shards":
            self.validate_shards(upto)
        outs = {stage: self.output(stage).resolve() for stage in active}
        r = self.dir.resolve()
        for stage, o in outs.items():
            if o == r or o in r.parents:
                raise Stop(f"config: stages.{stage}.output and the run folder {self.dir} overlap")
            if self.owned(o):
                raise Stop(f"config: stages.{stage}.output {o} is a folder of the run itself ({', '.join(RESERVED)}, "
                           f"or one of them with {', '.join(BESIDE)})")
        raw_dir = self.stages.get("ledger", {}).get("raw")
        if raw_dir is not None and STAGES.index(upto) >= STAGES.index("ledger") and self.owned(path(raw_dir).resolve()):
            raise Stop(f"config: stages.ledger.raw {raw_dir} is a folder of the run itself")
        for a, b in [(a, b) for i, a in enumerate(active) for b in active[i + 1:]]:
            if outs[a] == outs[b] or outs[a] in outs[b].parents or outs[b] in outs[a].parents:
                raise Stop(f"config: stages.{a}.output and stages.{b}.output overlap")
        mode = self.cfg.get("intermediates", "keep")
        if mode not in INTERMEDIATES:
            raise Stop(f"config: intermediates is {mode!r}, expected keep or drop")
        if mode == "drop":
            self.validate_drop(upto)
        self.inventory = self.validate_inventory(upto) if self.cfg.get("inventory") is not None else None

    def validate_inventory(self, upto):
        """"inventory": the expected parts and packs of the run (inventory_check.py), read and checked here. A run with
        one is the production run: it must account for every raw document (stages.ledger.raw, so the ledger runs in
        mode B and the inventory's raw rows and raw sha256 can be checked), it must have the shard and reconcile
        stages, and it must end at reconcile, so that no such run finishes without both check points (the ledger
        side before the shard stage, each part's status after reconcile). Returns the inventory."""
        name = self.cfg["inventory"]
        if not isinstance(name, str) or not name:
            raise Stop("config: inventory must be the path of an expected-inventory JSON file")
        if self.owned(path(name).resolve()):
            raise Stop(f"config: inventory {name} is in a folder of the run itself")
        try:
            inv = inventory_check.load(path(name))
        except inventory_check.Stop as e:
            raise Stop(f"config: inventory: {e}")
        ledger, shards = self.stages.get("ledger"), self.stages.get("shards")
        if not isinstance(ledger, dict) or ledger.get("raw") is None:
            raise Stop("config: \"inventory\" needs stages.ledger.raw (the raw parts the cleaner read): a run with an expected "
                       "inventory must account for every raw document, and the inventory's raw rows and raw sha256 are "
                       "checked against the ledger in mode B")
        if "shards" not in self.stages or "reconcile" not in self.stages:
            raise Stop("config: \"inventory\" needs stages.shards and stages.reconcile: each part's expected shard status "
                       "is checked after reconcile")
        if upto != "reconcile":
            raise Stop(f"config: \"inventory\" needs a run that ends at reconcile, and \"to\" is {upto}: the ledger is checked "
                       "against the inventory before the shard stage and each part's status after reconcile, and a run "
                       "that stops earlier would end without those checks (leave \"to\" out, or run without \"inventory\")")
        packs = shards.get("packs") if isinstance(shards, dict) else None
        if packs and isinstance(packs, list) and set(map(str, packs)) != set(inv["packs"]):
            extra, absent = sorted(set(map(str, packs)) - set(inv["packs"])), sorted(set(inv["packs"]) - set(map(str, packs)))
            raise Stop(f"config: stages.shards.packs and the inventory's packs differ: {len(absent)} inventory pack(s) not in "
                       f"stages.shards.packs{inventory_check.eg(absent)}; {len(extra)} of stages.shards.packs not in the "
                       f"inventory{inventory_check.eg(extra)}")
        clean, want = self.stages.get("clean"), inv["input_manifest_sha256"]
        mode = clean.get("mode", "adopt") if isinstance(clean, dict) else None
        pinned = clean.get("manifest_sha256") if mode == "run" else None
        if pinned and pinned != want:
            raise Stop(f"config: the inventory was made from input manifest {want[:12]}…, and "
                       f"stages.clean.manifest_sha256 is {str(pinned)[:12]}…")
        if mode == "adopt" and clean.get("output") and path(clean["output"]).is_dir():
            # An adopted folder that is there already: what its clean job read is known now, so a wrong or unreadable
            # summary stops here and not after the ledger. (A folder that is not there yet is the clean stage's to refuse.)
            summary = path(clean["output"]) / "job_summary.json"
            tied = "so the inventory cannot be tied to the input manifest that job read"
            try:
                adopted = load_json(summary)
            except (OSError, ValueError) as e:
                raise Stop(f"config: {self.shown(summary)} of the adopted clean job cannot be read ({type(e).__name__}), {tied}")
            got = adopted.get("manifest_sha256") if isinstance(adopted, dict) else None
            if not isinstance(adopted, dict) or not got:
                raise Stop(f"config: {self.shown(summary)} of the adopted clean job "
                           + ("records no manifest_sha256" if isinstance(adopted, dict) else "is not a JSON object") + f", {tied}")
            if got != want:
                raise Stop(f"config: the inventory was made from input manifest {want[:12]}…, and the adopted clean job "
                           f"read {str(got)[:12]}… ({self.shown(summary)})")
        return inv

    def check_inventory(self, after):
        """The expected inventory against what the run has made (inventory_check.py). after = "ledger": on entry to the
        shard stage, in sequence or on a resume there: the ledger's parts, packs, raw rows and raw sha256, and the input
        manifest the clean job read, so a missing or unlisted part stops the run before anything is sharded, with the
        ledger stage already recorded. after = "reconcile": those again (a resumed run may have another inventory than
        the one the earlier check point saw) and each part's status and pack in shards_summary.json. Every check point
        writes <run>/inventory_check.json over the one before it, with every difference and with paths as the manifest
        shows them; one that cannot make its checks (an input it cannot read) writes a report that says so, so no
        report of an earlier check point is left as this one's. Then the first failed check stops the run. The manifest
        is not written here: stage records change only when a stage finishes, so a check point that stops a resumed run
        leaves the records of the stages after it as they were. When all pass, the stage record gets the inventory's
        sha256 (inventory_sha256)."""
        if self.inventory is None:
            return
        head = {"run_id": self.cfg["run_id"], "checked_after": after}
        try:
            report = inventory_check.check(self.inventory, ledger=self.output("ledger"), cleaned=self.output("clean"),
                                           shards=self.output("shards") if after == "reconcile" else None)
        except inventory_check.Stop as e:
            named = {**inventory_check.described(self.inventory), "file": self.shown(self.inventory["path"])}
            try:
                self.report_inventory({**head, "tool": "inventory_check.py", "inventory": named, "ok": False, "error": str(e)})
            except Stop:
                pass  # the reason the check point stopped is the one to give
            raise Stop(f"inventory: {e}")
        report["inventory"]["file"] = self.shown(self.inventory["path"])
        for side in ("ledger", "shards"):
            if side in report:
                report[side]["folder"] = self.shown(self.output(side))
        self.report_inventory({**head, **report})
        for c in report["checks"]:
            self.check(c["check"], c["ok"], c["detail"] + ("" if c["ok"] else "; see inventory_check.json in the run folder"))
        self.checked = self.inventory["sha256"]

    def report_inventory(self, report):
        """<run>/inventory_check.json. When it cannot be written, the one before it is removed (it would read as this
        check point's) and the run stops with a message."""
        file = self.dir / "inventory_check.json"
        try:
            inventory_check.write_report(report, file)
        except OSError as e:
            try:
                file.unlink(missing_ok=True)
            except OSError:
                pass
            raise Stop(f"inventory: the report {self.shown(file)} could not be written ({type(e).__name__})")

    def drop_folders(self):
        """{stage: folder} a drop deletes Parquet parts from: apply's and F2's, the two folders every run writes itself.
        Never the cleaned folder: it is an input when adopted, and when this run wrote it another run may have adopted it."""
        return {"apply": self.output("apply"), "f2": self.output("f2")}

    def validate_drop(self, upto):
        """"intermediates": "drop" deletes Parquet, so: only in a run that ends at reconcile (the kept documents of a part
        are then known to be in the shards), and nothing the run reads or keeps may lie in a folder it deletes from."""
        if upto != "reconcile":
            raise Stop("config: \"intermediates\": \"drop\" needs a run that ends at reconcile (stages.shards and "
                       "stages.reconcile, and no earlier \"to\"): a part's Parquet is deleted only once its kept documents "
                       "are accounted for in the shards")
        kept = {"stages.shards.out": self.output("shards")}  # (validate() refuses stages.ledger.raw there for every run)
        if (self.stages.get("clean") or {}).get("input") is not None:
            kept["stages.clean.input"] = path(self.stages["clean"]["input"])
        for folder in self.drop_folders().values():
            d = folder.resolve()
            for name, p in kept.items():
                if p.resolve() == d or d in p.resolve().parents:
                    raise Stop(f"config: \"intermediates\": \"drop\" deletes Parquet under {self.shown(d)}, and {name} "
                               f"({self.shown(p)}) lies in it")

    def owned(self, p):
        """Is p (resolved) in a folder the run writes, swaps or deletes: deduped/, ledger/, ... or ledger.partial,
        ledger.old, deduped.lock and the like next to them?"""
        r = self.dir.resolve()
        if r not in p.parents:
            return False
        first = p.relative_to(r).parts[0]
        return first in RESERVED or any(first == name + end for name in RESERVED for end in BESIDE)

    def validate_shards(self, upto):
        spec = self.stages.get("shards")
        if STAGES.index(upto) < STAGES.index("shards"):
            return
        if not isinstance(spec, dict):
            raise Stop("config: stages.shards is not configured (it needs at least a tokenizer); the run stops after the ledger without it")
        if not spec.get("tokenizer") or not path(spec["tokenizer"]).is_file():
            raise Stop(f"config: stages.shards.tokenizer {spec.get('tokenizer')!r} is missing or not a file")
        script = spec.get("script", DEFAULT_SHARDS)
        if not path(script).is_file():
            raise Stop(f"config: shards script {script} not found")
        tokens = spec.get("tokens")
        if tokens is not None and (not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 1):
            raise Stop(f"config: stages.shards.tokens is {tokens!r}, expected a whole number >= 1")
        packs = spec.get("packs", [])
        if not isinstance(packs, list) or not all(isinstance(p, str) for p in packs):
            raise Stop("config: stages.shards.packs must be a list of pack ids")
        if spec.get("pack_table") and not path(spec["pack_table"]).is_file():
            raise Stop(f"config: stages.shards.pack_table {spec['pack_table']} not found")
        version = spec.get("dataset_version")
        if spec.get("any_tokenizer"):
            if version not in (None, "test"):
                raise Stop(f'config: stages.shards.dataset_version is {version!r}, but any_tokenizer shards are "test" (leave it out)')
        elif not isinstance(version, str) or not version.strip() or version == "test":
            raise Stop(f'config: stages.shards.dataset_version is {version!r}: name the corpus release every shard manifest '
                       'records (e.g. "corpus-v1", "sample"); "test" is only for any_tokenizer')

    def plan(self, to=None):
        """What a run would do, as text: each stage's mode, output folder and command, with every path resolved. The config is
        checked first, as for a run; nothing is run or written."""
        to = to or self.cfg.get("to") or self.last_stage()
        if to not in STAGES:
            raise Stop(f"unknown stage {to!r}; stages are {', '.join(STAGES)}")
        if to == "h3" and "h3" not in self.stages:
            raise Stop('"to": "h3" needs stages.h3')
        self.validate(to)
        lines = [f"run folder: {self.shown(self.dir)}   manifest: {self.shown(self.manifest_path)}"]
        planned = [s for s in STAGES[: STAGES.index(to) + 1] if s != "h3" or s in self.stages]
        for n, stage in enumerate(planned, start=1):
            out = self.shown(self.output(stage))
            if stage in EXTERNAL:
                built = self.stage_command(stage, write=False)
                if built is None:
                    lines.append(f"{n:02d} {stage:13} adopt  {out}")
                    continue
                lines.append(f"{n:02d} {stage:13} run    {out}")
                lines.append("     $ python -I " + " ".join(built["command"]).replace(str(REPO) + "/", ""))
                if built["settings"]:
                    lines.append(f"     settings {built['settings']} (sha256 {built['settings_sha256'][:12]}…)")
                if built["config"]:
                    lines.append(f"     generated config {self.shown(built['config'])}: " + ", ".join(
                        f"{k} = {v}" for k, v in stage_args.generated_values(stage, {s: self.output(s) for s in EXTERNAL if s != "h3" or s in self.stages}, REPO, self.stages[stage]).items()
                        if k in stage_args.PATH_KEYS or k == "resume"))
            elif stage == "f2":
                f2 = self.stages.get("f2", {})
                how = (f"{POOL} (the set loaded once) calling {f2.get('script', DEFAULT_F2)}" if f2.get("pool")
                       else f2.get("script", DEFAULT_F2))
                lines.append(f"{n:02d} {stage:13} run    {out}   {how}, workers {f2.get('workers', 1)}")
            elif stage == "shards":
                spec = self.stages["shards"]
                lines.append(f"{n:02d} {stage:13} run    {out}   {spec.get('script', DEFAULT_SHARDS)}, tokenizer {spec['tokenizer']}, "
                             f"dataset_version {'test' if spec.get('any_tokenizer') else spec.get('dataset_version')}")
            else:
                lines.append(f"{n:02d} {stage:13} run    {out}")
        if self.cfg.get("intermediates", "keep") == "drop":
            lines.append("intermediates: drop   after reconcile passes, the Parquet of every part whose kept documents are all "
                         "in shards (or left out by the shard writer for a stated reason) is deleted from "
                         + " and ".join(self.shown(f) for f in self.drop_folders().values())
                         + "; held-out and unselected parts, the cleaned folder, reports, the ledger and the shards stay")
        else:
            lines.append("intermediates: keep   every stage's Parquet stays on disk")
        if self.inventory is not None:  # validated: the run ends at reconcile, so both check points are reached
            d = inventory_check.described(self.inventory)
            lines.append(f"inventory: {self.shown(self.inventory['path'])} (sha256 {d['sha256'][:12]}…)   {d['packs']} pack(s), "
                         f"{d['parts']} part(s), expected " + ", ".join(f"{k} {v}" for k, v in d["expected"].items())
                         + "; checked before the shard stage and after reconcile"
                         + f"; report {self.shown(self.dir / 'inventory_check.json')}")
        else:
            lines.append("inventory: none   the run's parts and packs are not checked against an input manifest, and the raw "
                         "ledger is not required: not a production run (set \"inventory\" for one)")
        return "\n".join(lines)

    def check(self, name, ok, detail):
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            raise Stop(f"check failed: {name}: {detail}")

    # --- the stages -------------------------------------------------------------------------------------------------
    def stage_external(self, stage):
        spec = self.stages[stage]
        mode = spec.get("mode", "adopt")
        built = self.stage_command(stage, write=True)
        command = built["command"] if built else None
        if command:
            log = self.dir / "logs" / f"{stage}.log"
            rc = run_script(command[0], command[1:], stage, log, append=spec.get("resume") is True)
            if rc != 0:
                raise Stop(f"{stage}: {Path(command[0]).name} failed with exit code {rc}: {tail(log)}")
        out = self.output(stage)
        for name in NEEDED.get(stage, ()):
            if not (out / name).is_file():
                raise Stop(f"{stage}: {out} has no {name}")
        counts = getattr(self, f"counts_{stage}")(out)
        rec = {"mode": mode, "command": command, "code_sha256": sha256(path(command[0])) if command else None,
               "output": self.shown(out), "counts": counts}
        tools = {a: sha256(path(a)) for a in (command or [])[1:] if a.endswith(".py") and path(a).is_file()}
        if stage == "clean" and built and built["config"]:
            # the cleaner the job was told to load (the job checked it against the pin in the same settings file) and the
            # manifest check it shares with --plan: what the job ran besides its own script
            cleaner = load_json(built["config"]).get("clean")
            if cleaner and path(cleaner).is_file():
                tools.update({cleaner: sha256(path(cleaner)), self.shown(HERE / "clean_manifest.py"): sha256(HERE / "clean_manifest.py")})
        if tools:  # the scripts a wrapper was given ("script" as a list), and the cleaner clean_job.py loads
            rec["tools_sha256"] = tools
        if stage == "clean":
            rec["job_summary_checked"] = self.clean_summary_checked  # False: an adopted folder with no clean-job summary to check
        if self.only and stage == "clean":
            rec["only"] = self.only
        if stage == "clean" and command and spec.get("resume") is True:
            rec["resume"] = True  # the job was told it may continue an interrupted folder (a fresh folder starts fresh)
        if built and built["settings"]:  # a stage run from a settings file: which file, and the config it was run with
            rec.update(settings=built["settings"], settings_sha256=built["settings_sha256"],
                       config=Path(built["config"]).relative_to(self.dir).as_posix() if built["config"] else None,
                       config_sha256=built["config_sha256"])
        return rec

    def counts_clean(self, out):
        counts = parquet_rows(out)
        self.clean_summary_checked = self.check_clean_summary(out, counts)
        return counts

    def check_clean_summary(self, out, counts):
        """The clean job's account of its work (job_summary.json, as clean_job.py and TSAI's run_tokenizer_sample.py write it)
        against the folder. True when it was checked. A stage run from settings must have one. An adopted folder without a
        summary in the job's format (an older local output) is not checked: False, and the stage record says so. A custom
        "command" is not checked either: nothing is known about what it writes."""
        spec = self.stages["clean"]
        if spec.get("command"):
            return False
        run = spec.get("mode", "adopt") == "run"
        try:
            s = load_json(out / "job_summary.json")
        except (OSError, ValueError):
            s = None
        if not (isinstance(s, dict) and all(k in s for k in CLEAN_SUMMARY) and isinstance(s["parts"], list)
                and all(isinstance(p, dict) for p in s["parts"]) and isinstance(s["actions"], dict)
                and all(type(s[k]) is int for k in ("completed_parts", "expected_parts", "input_rows", "output_rows", "errors"))):
            if run:
                raise Stop(f"clean: {self.shown(out / 'job_summary.json')} is missing or is not a clean job's summary "
                           f"({', '.join(CLEAN_SUMMARY)}): the job did not finish; see logs/clean.log")
            return False
        listed = {p.get("part"): p for p in s["parts"]}
        self.check("clean: the job reported no errors", s["errors"] == 0, f"job_summary.json: {s['errors']} error(s)")
        partial = bool(self.only) or str(s.get("scope", "")).startswith("partial")
        if run:
            want = len(self.only) if self.only else sum(spec["expected_parts"].values())
        else:
            want = len(listed) if partial else s["expected_parts"]
        self.check("clean: the job cleaned the parts the run expects, each with a report",
                   s["completed_parts"] == len(s["parts"]) == len(listed) == want and (not run or self.only or s["expected_parts"] == want),
                   f"job_summary.json: completed_parts {s['completed_parts']}, expected_parts {s['expected_parts']}, "
                   f"{len(s['parts'])} part report(s) for {len(listed)} part(s); the run expects {want}")
        if run:
            self.check("clean: the job read this run's input manifest", s.get("manifest_sha256") == spec["manifest_sha256"],
                       f"job_summary.json manifest_sha256 {str(s.get('manifest_sha256'))[:12]}…, stages.clean.manifest_sha256 "
                       f"{str(spec['manifest_sha256'])[:12]}…")
        drops, rows = s["actions"].get("drop", 0), sum(p.get("output_rows") or 0 for p in listed.values())
        self.check("clean: input rows = output rows + dropped, and the output rows are those on disk",
                   s["input_rows"] == s["output_rows"] + drops and s["output_rows"] == rows == counts["rows"],
                   f"job_summary.json input_rows {s['input_rows']}, output_rows {s['output_rows']}, dropped {drops}; "
                   f"its part reports add up to {rows}; the Parquet footers to {counts['rows']}")
        disk = counts["by_part"]
        missing, extra = sorted(set(listed) - set(disk)), sorted(set(disk) - set(listed))
        wrong = sorted(n for n in set(listed) & set(disk) if listed[n].get("output_rows") != disk[n])
        self.check("clean: the parts on disk are the parts the job reports, with their rows", not (missing or extra or wrong),
                   f"{len(missing)} reported but not on disk (e.g. {missing[:2]}), {len(extra)} on disk but not reported "
                   f"(e.g. {extra[:2]}), {len(wrong)} with other rows (e.g. {wrong[:2]})")
        names = sorted(listed)
        shas = self.cache.sha256_many([out / n for n in names])  # the stage digest reuses these: no second read
        bad = [n for n in names if shas[out / n] != listed[n].get("output_sha256")]
        self.check("clean: each part's sha256 is the one the job recorded", not bad,
                   f"{len(bad)} of {len(names)} part(s) differ from job_summary.json, e.g. {bad[:3]}")
        return True

    def counts_overlap(self, out):
        s = load_json(out / "overlap_summary.json")
        clean = self.done["clean"]["counts"]
        self.check("overlap finished", s.get("status") == "complete", f"status {s.get('status')!r}")
        self.check("overlap read every cleaned row", s.get("documents_all") == clean["rows"],
                   f"overlap documents_all {s.get('documents_all')}, cleaned rows {clean['rows']}")
        listed = {p["part"].replace("\\", "/"): p["documents"] for p in s.get("inputs", {}).get("parts", [])}
        if listed:
            diff = sorted(p for p in set(listed) | set(clean["by_part"]) if listed.get(p) != clean["by_part"].get(p))
            self.check("overlap read these cleaned parts", not diff,
                       f"{len(diff)} part(s) differ in name or row count, e.g. {diff[0] if diff else ''}")
        recorded = {p["part"].replace("\\", "/"): p.get("sha256") for p in s.get("inputs", {}).get("parts", [])}
        actual = self.cache.sha256_many([self.output("clean") / name for name in clean["by_part"]])
        bad = sorted(name for name in clean["by_part"]
                     if recorded.get(name) != actual[self.output("clean") / name])
        self.check("overlap read these cleaned bytes", not bad,
                   f"{len(bad)} part(s) differ or have no input sha256, e.g. {bad[:3]}")
        files = {}
        for name in ("overlap_matches.csv", "overlap_docs.parquet"):
            files[name] = sha256(out / name)
            want = s.get("outputs", {}).get(name, {}).get("sha256")
            if want:
                self.check(f"{name} matches overlap's summary", files[name] == want, f"{files[name][:12]}… vs {want[:12]}…")
        return {"documents_all": s.get("documents_all"), "parts": len(listed), "files_sha256": files}

    def counts_h3(self, out):
        s = load_json(out / "h3_summary.json")
        self.check("H3 finished", s.get("status") == "complete", f"status {s.get('status')!r}")
        listed = s.get("outputs", {}).get("h3_matches.csv", {}).get("sha256")
        actual = sha256(out / "h3_matches.csv")
        self.check("H3 matches match its summary", listed == actual,
                   f"summary {str(listed)[:12]}…, file {actual[:12]}…")
        rows = csv_rows(out / "h3_matches.csv")
        self.check("H3 match count matches its summary", s.get("qualifying") == rows,
                   f"summary {s.get('qualifying')}, file {rows}")
        self.check("H3 read this run's cleaned folder",
                   s.get("inputs", {}).get("root") == self.shown(self.output("clean")),
                   f"H3 inputs {s.get('inputs', {}).get('root')!r}")
        return {"matches": s.get("qualifying"), "matches_sha256": actual}

    def counts_dedup(self, out):
        s = load_json(out / "dedup_summary.json")
        ov = self.done["overlap"]["counts"]
        import pyarrow.compute as pc
        groups = pc.count_distinct(csv_column(out / "dedup_groups.csv", "group_id")).as_py()
        counts = {"remove_list_rows": csv_rows(out / "remove_list.csv"), "removed": s.get("removed"),
                  "heldout_removed": s.get("heldout_removed"), "groups": groups}
        self.check("dedup finished", s.get("status") == "complete", f"status {s.get('status')!r}")
        checked = s.get("overlap_run", {}).get("checked_sha256", {})
        self.check("dedup used this overlap run", checked == ov["files_sha256"],
                   f"dedup checked {sorted((k, v[:12]) for k, v in checked.items())}, "
                   f"the adopted overlap has {sorted((k, v[:12]) for k, v in ov['files_sha256'].items())}")
        self.check("dedup saw overlap's documents", s.get("documents_all") == ov["documents_all"],
                   f"dedup documents_all {s.get('documents_all')}, overlap {ov['documents_all']}")
        if "h3" in self.stages:
            evidence = self.done["h3"]["counts"]
            used = s.get("h3", {})
            self.check("dedup used this run's H3 matches",
                       used.get("matches", {}).get("sha256") == evidence["matches_sha256"]
                       and used.get("matches", {}).get("pairs") == evidence["matches"]
                       and used.get("remove") is False,
                       f"H3 summary {evidence}, dedup H3 {used}")
        self.check("dedup summary matches its remove list", counts["removed"] == counts["remove_list_rows"],
                   f"summary removed {counts['removed']}, remove_list.csv rows {counts['remove_list_rows']}")
        self.check("dedup removed no held-out doc", counts["heldout_removed"] == 0,
                   f"heldout_removed {counts['heldout_removed']} (rule 0)")
        return counts

    def stage_apply(self):
        import apply_dedup
        out, clean = self.output("apply"), self.done["clean"]["counts"]
        try:
            s = apply_dedup.apply(self.output("clean"), self.output("dedup") / "remove_list.csv", out,
                                  splits=tuple(sp for sp in SPLITS if sp in clean["by_split"]),
                                  link=bool(self.stages.get("apply", {}).get("link", True)),
                                  workers=self.stages.get("apply", {}).get("workers", apply_dedup.DEFAULT_WORKERS),
                                  cache=self.cache)
        except apply_dedup.Stop as e:
            raise Stop(f"apply: {e}")
        counts = dict(s["totals"])
        counts["kept_by_split"] = {}
        for p in s["parts"]:
            counts["kept_by_split"][p["split"]] = counts["kept_by_split"].get(p["split"], 0) + p["kept"]
        self.check("apply read every cleaned row", counts["rows"] == clean["rows"],
                   f"apply rows {counts['rows']}, cleaned rows {clean['rows']}")
        self.check("apply removed the remove list", counts["removed"] == self.done["dedup"]["counts"]["remove_list_rows"],
                   f"apply removed {counts['removed']}, remove list {self.done['dedup']['counts']['remove_list_rows']}")
        self.apply_parts = {(p["split"], p["part"]): p["output_sha256"] for p in s["parts"]}
        return {"mode": "run", "command": ["teams/01-data-a/pipeline/apply_dedup.py"],
                "code_sha256": s["code_sha256"], "output": "deduped", "counts": counts}

    def f2_units(self, src, split, workers, pool=False):
        """The F2 work units of one split: the whole split with one worker or with the pool (f2_pool.py shares the parts
        out itself), else one unit per pack folder (plus one for Parquet files sitting directly in the split folder).
        Each unit: (name, inputs, out)."""
        out = self.output("f2") / split
        if workers <= 1 or pool:
            return [(split, [src / split], out)]
        units = [(f"{split}/{d.name}", [d], out / d.name) for d in sorted((src / split).iterdir())
                 if d.is_dir() and any(d.rglob("*.parquet"))]
        loose = sorted(f for f in (src / split).glob("*.parquet") if f.is_file())
        if loose:
            units.append((f"{split}/(files)", loose, out))
        return units

    def stage_f2(self):
        from concurrent.futures import ThreadPoolExecutor
        spec = self.stages.get("f2", {})
        script, workers, pool = spec.get("script", DEFAULT_F2), int(spec.get("workers", 1)), bool(spec.get("pool", False))
        src, out = self.output("apply"), self.output("f2")
        parts = getattr(self, "apply_parts", None)
        if parts is None:  # apply was recorded by an earlier run
            s = load_json(src / "apply_dedup_summary.json")
            parts = {(p["split"], p["part"]): p["output_sha256"] for p in s["parts"]}
        kept_by_split = self.done["apply"]["counts"]["kept_by_split"]
        splits = [sp for sp in SPLITS if (src / sp).is_dir()]
        for split in splits:  # before any F2 runs
            mine = {p for (sp, p) in parts if sp == split}
            if (out / split).is_dir():
                stale = sorted(f.relative_to(out / split).as_posix() for f in (out / split).rglob("*.parquet")
                               if f.relative_to(out / split).as_posix() not in mine)
                self.check(f"no stale F2 output in final/{split}", not stale,
                           f"{len(stale)} Parquet file(s) from an earlier run, e.g. {stale[0] if stale else ''}")
        units = [u for sp in splits for u in self.f2_units(src, sp, workers, pool)]

        def one(unit):
            name, inputs, dst = unit
            log = self.dir / "logs" / ("f2_" + name.replace("/", "_").replace("(", "").replace(")", "") + ".log")
            if pool:  # one f2_pool.py per split: the set loaded once, the split's parts shared out among the workers
                rc = run_script(POOL, ["--inputs", *inputs, "--out", dst, "--workers", workers, "--script", path(script)], "f2", log)
            else:
                rc = run_script(script, ["--inputs", *inputs, "--out", dst], "f2", log)
            return name, dst, rc, log

        t0 = time.time()
        with ThreadPoolExecutor(max_workers=1 if pool else max(1, workers)) as threads:  # each thread waits on its own process
            results = list(threads.map(one, units))
        failed = [(n, rc, log) for n, dst, rc, log in results if rc != 0 and not (dst / "f2_summary.json").is_file()]
        if failed:
            n, rc, log = failed[0]
            raise Stop(f"f2: {len(failed)} of {len(units)} unit(s) failed without a summary, e.g. {n} "
                       f"(exit code {rc}): {tail(log)}. Rerun with from = f2: finished files are skipped")

        totals = {"rows": 0, "kept": 0, "dropped_by_f2": 0, "errors": 0}
        by_split, sets = {sp: dict.fromkeys(totals, 0) for sp in splits}, set()
        for name, dst, rc, log in results:
            s = load_json(dst / "f2_summary.json")
            sets.add(s.get("set_sha256"))
            errors = s.get("errors", 0)
            errors = len(errors) if isinstance(errors, list) else errors
            split = name.split("/")[0]
            for k, v in (("rows", s.get("rows", 0)), ("kept", s.get("kept", 0)),
                         ("dropped_by_f2", s.get("dropped_by_f2", 0)), ("errors", errors)):
                by_split[split][k] += v
                totals[k] += v
            self.check(f"F2 reported no errors on {name}", errors == 0 and rc == 0,
                       f"{errors} docs raised during the check, exit code {rc}; see {log.name}")
        for split in splits:
            self.check(f"F2 read every deduplicated row of {split}", by_split[split]["rows"] == kept_by_split.get(split),
                       f"F2 rows {by_split[split]['rows']}, apply kept {kept_by_split.get(split)}")
            wrong = []
            for part in sorted(p for (sp, p) in parts if sp == split):
                rep = out / split / (part + ".f2.json")
                got = load_json(rep).get("input_sha256") if rep.is_file() else None
                if got != parts[(split, part)]:
                    wrong.append(part)
            self.check(f"F2 read what apply wrote in {split}", not wrong,
                       f"{len(wrong)} part(s) without a matching F2 report, e.g. {wrong[0] if wrong else ''}")
        self.check("F2 used one fingerprint set", len(sets) == 1 and None not in sets, f"set_sha256 values {sorted(map(str, sets))}")
        self.check("F2 counts add up", totals["kept"] + totals["dropped_by_f2"] + totals["errors"] == totals["rows"], f"{totals}")
        return {"mode": "run", "command": [script, "--inputs", "<run>/deduped/<split>[/<pack>]", "--out", "<run>/final/<split>[/<pack>]"],
                "code_sha256": sha256(path(script)), "output": "final", "set_sha256": sets.pop(),
                "pool": pool, "pool_code_sha256": sha256(path(POOL)) if pool else None,
                "workers": workers, "units": len(units), "wall_seconds": round(time.time() - t0, 1),
                "counts": {**totals, "by_split": by_split}}

    def stage_survivor_loss(self):
        import survivor_loss
        out = self.output("survivor_loss")
        try:
            s = survivor_loss.report(self.output("dedup") / "dedup_groups.csv", self.output("f2"), out)
        except survivor_loss.Stop as e:
            raise Stop(f"survivor_loss: {e}")
        # the groups in dedup_groups.csv against what dedup.py decided (its summary), not against the same file again
        g, d = s["groups"], load_json(self.output("dedup") / "dedup_summary.json")
        want = {k: d.get(k) for k in ("clusters", "groups_without_survivor", "groups_with_several_survivors")}
        self.check("dedup's summary counts its groups", all(type(v) is int and v >= 0 for v in want.values()),
                   f"dedup_summary.json gives {want}")
        self.check("survivor loss saw every dedup group", g["total"] == want["clusters"],
                   f"dedup_groups.csv {g['total']} group(s), dedup_summary.json clusters {want['clusters']}")
        # dedup.py counts the groups without a survivor before H3 turns survivors into removed copies: with H3, up to
        # h3.groups_survivor_removed more groups have none, and none has more survivors than before
        h3 = (d.get("h3") or {}).get("groups_survivor_removed") or 0
        self.check("survivor loss's groups without a survivor = dedup's",
                   want["groups_without_survivor"] <= g["without_survivor"] <= want["groups_without_survivor"] + h3,
                   f"dedup_groups.csv {g['without_survivor']}, dedup_summary.json {want['groups_without_survivor']}"
                   + (f" (+ up to {h3} whose survivors H3 removed)" if h3 else ""))
        several = want["groups_with_several_survivors"]
        self.check("survivor loss's groups with several survivors = dedup's",
                   g["with_several_survivors"] <= several if h3 else g["with_several_survivors"] == several,
                   f"dedup_groups.csv {g['with_several_survivors']}, dedup_summary.json {several}")
        return {"mode": "run", "command": ["teams/01-data-a/pipeline/survivor_loss.py"], "code_sha256": s["code_sha256"],
                "output": "report", "counts": {**s["groups"], "survivors_dropped_by_f2": s["survivors_dropped_by_f2"]}}

    def stage_ledger(self):
        import ledger
        raw = self.stages.get("ledger", {}).get("raw")
        dedup = self.output("dedup")
        log = dedup / "dedup_log.jsonl"
        try:
            s = ledger.build(self.output("clean"), dedup / "remove_list.csv", dedup / "dedup_groups.csv",
                             self.output("f2"), self.output("ledger"), log=log if log.is_file() else None,
                             raw=path(raw) if raw is not None else None)
        except ledger.Stop as e:
            raise Stop(f"ledger: {e}")
        t, c = s["totals"], {st: self.done[st]["counts"] for st in ("clean", "apply", "f2")}
        self.check("ledger holds every cleaned row", t["rows_cleaned"] == c["clean"]["rows"],
                   f"ledger {t['rows_cleaned']}, cleaned rows {c['clean']['rows']}")
        self.check("ledger removed_by_dedup = apply's removed", t["removed_by_dedup"] == c["apply"]["removed"],
                   f"ledger {t['removed_by_dedup']}, apply {c['apply']['removed']}")
        self.check("ledger dropped_by_f2 = F2's", t["dropped_by_f2"] == c["f2"]["dropped_by_f2"],
                   f"ledger {t['dropped_by_f2']}, F2 {c['f2']['dropped_by_f2']}")
        self.check("ledger f2_error = F2's errors", t["f2_error"] == c["f2"]["errors"],
                   f"ledger {t['f2_error']}, F2 {c['f2']['errors']}")
        self.check("ledger kept = F2's kept", t["kept"] == c["f2"]["kept"], f"ledger {t['kept']}, F2 {c['f2']['kept']}")
        self.check("ledger used F2's fingerprint set", s["inputs"]["set_sha256"] == self.done["f2"]["set_sha256"],
                   f"{str(s['inputs']['set_sha256'])[:12]}… vs {str(self.done['f2']['set_sha256'])[:12]}…")
        by_pack = {pack: {split: pack_chain(c_, s["clean_mode"]) for split, c_ in splits.items()}
                   for pack, splits in s["by_pack"].items()}
        applied = load_json(self.output("apply") / "apply_dedup_summary.json").get("by_pack", {})
        mine = {(pk, sp): (r["cleaned"], r["removed_by_dedup"]) for pk, sps in by_pack.items() for sp, r in sps.items()}
        theirs = {(pk, sp): (r["rows"], r["removed"]) for pk, sps in applied.items() for sp, r in sps.items()}
        # a pack/split the cleaner emptied (mode B) is in the ledger with 0 rows and absent from apply: both mean (0, 0)
        diff = sorted(k for k in set(mine) | set(theirs) if mine.get(k, (0, 0)) != theirs.get(k, (0, 0)))
        self.check("ledger per pack = apply per pack", not diff,
                   f"{len(diff)} pack/split(s) differ in cleaned rows or removed, e.g. "
                   f"{diff[0][0] + '/' + diff[0][1] + ': ledger ' + str(mine.get(diff[0])) + ', apply ' + str(theirs.get(diff[0])) if diff else ''}")
        bad = sorted(f"{pk}/{sp}" for pk, sps in s["by_pack"].items() for sp, r in sps.items()
                     if r["rows_cleaned"] - r["removed_by_dedup"] - r["dropped_by_f2"] - r["f2_error"] != r["kept"]
                     or r["rows"] - r["dropped_by_clean"] != r["rows_cleaned"])
        self.check("every per-pack row adds up", not bad,
                   f"{len(bad)} pack/split(s) where raw - clean != cleaned or cleaned - dedup - f2 - errors != final, "
                   f"e.g. {bad[0] if bad else ''}")
        sums = {k: sum(r[k] for sps in by_pack.values() for r in sps.values())
                for k in ("cleaned", "removed_by_dedup", "dropped_by_f2", "final")}
        stage = {"cleaned": c["clean"]["rows"], "removed_by_dedup": c["apply"]["removed"],
                 "dropped_by_f2": c["f2"]["dropped_by_f2"], "final": c["f2"]["kept"]}
        self.check("per-pack table adds up to the stages' counts", sums == stage, f"table {sums}, stages {stage}")
        # each dedup survivor F2 dropped, counted twice and independently: by the ledger, from every document's row, and
        # by survivor_loss.py, from the groups and F2's reports
        mine, loss = s["survivors_dropped_by_f2"], load_json(self.output("survivor_loss") / "survivor_loss_summary.json")
        self.check("ledger's survivors dropped by F2 = survivor loss's", mine["total"] == loss.get("survivors_dropped_by_f2"),
                   f"ledger {mine['total']}, survivor_loss_summary.json {loss.get('survivors_dropped_by_f2')}")
        theirs = {p: sum(v.values()) for p, v in (loss.get("survivor_rows_by_pack") or {}).items()}
        diff = sorted(p for p in set(mine["by_pack"]) | set(theirs) if mine["by_pack"].get(p, 0) != theirs.get(p, 0))
        self.check("ledger's survivors dropped by F2 per pack = survivor loss's", not diff,
                   f"{len(diff)} pack(s) differ, e.g. "
                   f"{diff[0] + ': ledger ' + str(mine['by_pack'].get(diff[0], 0)) + ', survivor loss ' + str(theirs.get(diff[0], 0)) if diff else ''}")
        return {"mode": "run", "command": ["teams/01-data-a/pipeline/ledger.py"], "code_sha256": s["code_sha256"],
                "output": "ledger", "clean_mode": s["clean_mode"],
                "counts": {k: v for k, v in t.items() if v is not None}, "by_pack": by_pack}

    def stage_shards(self):
        """The cleaning_pipeline.json of the run, then run_shards.py on final/. The manifest on disk (written after the earlier
        stages) is what the shard writer reads; this stage's own record is added to the manifest afterwards."""
        spec = self.stages["shards"]
        script, out = spec.get("script", DEFAULT_SHARDS), self.output("shards")
        sys.path.insert(0, str(HERE.parent / "shards"))
        import provenance, verify_shards
        try:
            record_path, record = provenance.write_record(self.manifest_path, REPO)
        except provenance.Stop as e:
            raise Stop(f"shards: {e}")
        args = ["--input", self.output("f2"), "--manifest", self.manifest_path, "--tokenizer", path(spec["tokenizer"]), "--out", out]
        if spec.get("tokens"):
            args += ["--tokens", spec["tokens"]]
        for pack in spec.get("packs", []):
            args += ["--pack", pack]
        if spec.get("pack_table"):
            args += ["--pack-table", path(spec["pack_table"])]
        if spec.get("any_tokenizer"):
            args.append("--any-tokenizer")
        else:
            args += ["--dataset-version", spec["dataset_version"]]
        # The verification below is the run's one (it hashes every shard once and hands the hashes to the cache), so the default
        # run_shards.py is told not to repeat it. Another script gets no flag it may not know, and is verified here all the same.
        skip_own = script == DEFAULT_SHARDS
        if skip_own:
            args.append("--no-verify")
        log = self.dir / "logs" / "shards.log"
        rc = run_script(script, args, "shards", log)
        summary_path = out / "shards_summary.json"
        if not summary_path.is_file():
            raise Stop(f"shards: {Path(script).name} failed with exit code {rc} and wrote no shards_summary.json: {tail(log)}")
        s = load_json(summary_path)
        counts, record_sha = s["counts"], sha256(record_path)
        first = next((f"{n}: {e.get('reason')}" for n, e in s["parts"].items() if e["status"] in ("failed", "skipped")), "")
        self.check("shards: no part failed or was skipped", counts["failed"] == 0 and counts["skipped"] == 0,
                   f"{counts}; first: {first}; see logs/shards.log")
        self.check("shards: run_shards.py exited 0", rc == 0, f"exit code {rc}: {tail(log)}")
        self.check("shards: at least one shard written", counts["written"] > 0, f"{counts}")
        cut = sorted(name for name, e in s["parts"].items() if e.get("truncated"))
        self.check("shards: no part was cut short (every row of a written part was read into its shards)",
                   counts.get("truncated", 0) == 0 and not cut,
                   f"{len(cut) or counts.get('truncated')} part(s) cut short, e.g. {cut[:3]}: the writer rolls over into "
                   "more shards, so rows it never read point to a writer fault; reconcile reports them as not_reached")
        self.check("shards: the summary is this run's, made with this run's cleaning_pipeline.json",
                   s.get("run_id") == self.cfg["run_id"] and s.get("cleaning_pipeline_sha256") == record_sha,
                   f"summary run_id {s.get('run_id')}, cleaning_pipeline_sha256 {str(s.get('cleaning_pipeline_sha256'))[:12]}…")
        # Not the summary's word: the shards as they are on disk (files, sha256, format, counts, pack table, first and last document)
        table = path(spec["pack_table"]) if spec.get("pack_table") else verify_shards.pack_table.TABLE
        try:
            problems, known = verify_shards.verify(out, self.manifest_path, path(spec["tokenizer"]), table, s)
        except Exception as e:  # an unreadable tokenizer, manifest or pack table: not a traceback
            raise Stop(f"shards: the shards could not be verified: {type(e).__name__}: {e}")
        for name, h in known.items():  # the stage digest then reuses them: each shard file is read once
            self.cache.remember(out / name, h)
        self.check("shards: the shard files on disk verify (files, sha256, format, counts, pack table, first and last document)",
                   not problems, f"{len(problems)} problem(s), the first {min(3, len(problems))}: {'; '.join(problems[:3])}")
        return {"mode": "run", "command": [script, "--input", "<run>/final", "--manifest", "<run>/pipeline_manifest.json", "--out", "<out>",
                                           *(["--no-verify"] if skip_own else [])],
                "code_sha256": sha256(path(script)), "output": spec.get("out") or "shards", "cleaning_pipeline_sha256": record_sha,
                "counts": {**counts, "parts": len(s["parts"])}}

    def stage_reconcile(self):
        """reconcile_shards.py: every kept document of the ledger is in exactly one shard, or left out for a stated reason."""
        import reconcile_shards
        out, packs = self.output("reconcile"), self.stages.get("shards", {}).get("packs") or None
        try:  # on a failed check, reconcile_shards.py has written its summary and per-document statuses before stopping
            r = reconcile_shards.reconcile(self.output("ledger"), self.output("shards"), out, packs)
        except reconcile_shards.Stop as e:
            raise Stop(f"reconcile: {e}. See {self.shown(out)}/reconcile_summary.json and reconcile_docs.parquet (shard_status)")
        for c in r["checks"]:
            self.check(f"reconcile: {c['check']}", c["ok"], c["detail"])
        self.check_inventory("reconcile")
        return {"mode": "run", "command": ["teams/01-data-a/pipeline/reconcile_shards.py"], "code_sha256": r["code_sha256"],
                "output": "reconcile", "counts": {"kept": r["kept"], "in_shards": r["in_shards"], **r["totals"]}}

    # --- the run ----------------------------------------------------------------------------------------------------
    def execute(self, start=None, to=None):
        start = start or self.cfg.get("from") or STAGES[0]
        to = to or self.cfg.get("to") or self.last_stage()
        for s in (start, to):
            if s not in STAGES:
                raise Stop(f"unknown stage {s!r}; stages are {', '.join(STAGES)}")
        if "h3" not in self.stages and (start == "h3" or to == "h3"):
            raise Stop('"from" or "to": "h3" needs stages.h3')
        if STAGES.index(start) > STAGES.index(to):
            raise Stop(f"\"from\": {start} comes after \"to\": {to}")
        self.validate(to)
        prior = load_json(self.manifest_path) if self.manifest_path.is_file() else {}
        state = (prior.get("intermediates") or {}).get("state")
        if state:  # a drop began in this run folder: parts of deduped/ and final/ may be gone
            raise Stop(f"{self.manifest_path} records that this run dropped its intermediate Parquet (\"intermediates\": "
                       f"\"drop\", {state}): it cannot be resumed or rerun in place; start a new run with a new run_id")
        old = {s["stage"]: s for s in prior.get("stages", [])}
        try:  # an inventory report of an earlier invocation is not this one's: its check points write their own
            (self.dir / "inventory_check.json").unlink(missing_ok=True)
        except OSError as e:
            raise Stop(f"inventory: the earlier report {self.shown(self.dir / 'inventory_check.json')} could not be removed "
                       f"({type(e).__name__})")
        sys.path.insert(0, str(HERE))
        for stage in STAGES[: STAGES.index(to) + 1]:
            if stage == "h3" and stage not in self.stages:
                continue
            out = self.output(stage)
            if STAGES.index(stage) < STAGES.index(start):
                if stage not in old:
                    raise Stop(f"\"from\": {start}: stage {stage} has no record in {self.manifest_path}; run it first")
                if not out.exists() or digest(out, self.cache)[0] != old[stage]["digest"]:
                    raise Stop(f"{stage}: {out} changed after the manifest recorded it; rerun from {stage}")
                self.done[stage] = old[stage]
                continue
            t0, self.checks, self.checked = time.time(), [], None
            if stage == "shards":  # the ledger is recorded by now, whether it ran in this invocation or an earlier one
                self.check_inventory("ledger")  # before anything is sharded: a part the input manifest lists and the ledger lacks stops here
            rec = self.stage_external(stage) if stage in EXTERNAL else getattr(self, f"stage_{stage}")()
            rec["digest"], rec["files"] = digest(out, self.cache)
            if self.checked:  # which inventory this stage's "inventory: ..." checks passed with
                rec["inventory_sha256"] = self.checked
            self.done[stage] = {"stage": stage, **rec, "checks": self.checks, "seconds": round(time.time() - t0, 1)}
            self.write()
            self.cache.save()  # a resumed run reuses every hash so far
            print(f"{stage}: {json.dumps({k: v for k, v in self.done[stage]['counts'].items() if k != 'by_part'})}",
                  file=sys.stderr, flush=True)
        m = self.write()
        if self.cfg.get("intermediates", "keep") == "drop":  # validated: the run ended at reconcile, and every check passed
            m = self.drop()
        table = pack_table(m.get("by_pack") or {})
        if table:
            print(table, file=sys.stderr, flush=True)
        return m

    def droppable_parts(self):
        """(the parts <split>/<pack>/<file> whose Parquet a drop deletes, how many parts with kept documents it leaves).
        A part goes only when reconcile_docs.parquet shows every kept document of it in a shard, or left out by the shard
        writer for a stated reason, and the shard stage reports the part as written. So a held-out part (not_sharded), a
        part of a pack the shard stage was not asked for (not_selected) and a part without kept documents all stay.
        Read a batch at a time: two columns of one row per kept document."""
        import pyarrow as pa, pyarrow.parquet as pq
        from collections import Counter
        written = {name for name, e in load_json(self.output("shards") / "shards_summary.json").get("parts", {}).items()
                   if e.get("status") == "written"}
        ok, other = Counter(), Counter()
        with pq.ParquetFile(self.output("reconcile") / "reconcile_docs.parquet") as docs:
            for batch in docs.iter_batches(columns=["input_part", "shard_status"]):
                groups = pa.Table.from_batches([batch]).group_by(["input_part", "shard_status"]).aggregate([([], "count_all")])
                for g in groups.to_pylist():
                    status = g["shard_status"] or ""
                    (ok if status == "in_shard" or status.startswith("left_out:") else other)[g["input_part"]] += g["count_all"]
        parts = sorted(p for p in ok if p not in other and p in written)
        return parts, len(set(ok) | set(other)) - len(parts)

    def check_shards_for_drop(self, parts):
        """Stop, with nothing deleted, unless every shard the parts to drop went into is on disk as its manifest says
        (shard_problems: files, sha256, header, size, index, document rows, summary counts). The summary and reconcile
        only say what the shard writer reported; this looks at the shards themselves, since after a drop they are the
        only copy of those documents. Returns how many shards were checked."""
        out = self.output("shards")
        entries = load_json(out / "shards_summary.json").get("parts", {})
        problems, checked = [], 0
        for name in parts:
            e = entries.get(name) or {}
            # run_shards.py lists a part's shards (one or more, after rollover) with each one's docs and tokens
            shards = e.get("shards") if isinstance(e.get("shards"), list) else [e] if e.get("shard_id") else []
            sids = [s.get("shard_id") if isinstance(s, dict) else None for s in shards]
            if not sids or not all(isinstance(sid, str) and sid for sid in sids):
                problems.append(f"{name}: shards_summary.json names no shard for it")
                continue
            for sid, s in zip(sids, shards):
                checked += 1
                problems += [f"{name} → {sid}: {p}" for p in shard_problems(out, sid, s, self.cache)]
        self.cache.save()  # what was hashed is kept, whether the check passes or not
        if problems:
            more = f" (and {len(problems) - 3} more)" if len(problems) > 3 else ""
            raise Stop(f"intermediates: a shard is not on disk as its manifest says, so its Parquet stays: "
                       f"{'; '.join(problems[:3])}{more}. Nothing was deleted")
        return checked

    def drop_files(self, parts):
        """[(folder name, file)]: the Parquet of these parts under deduped/ and final/. Every check is made here, before
        the first file goes: the name is <split>/<pack>/<file>.parquet and nothing else; the folder and the part's own
        folder are where they should be in the run folder once links are resolved (a folder that is a link to somewhere
        else stops the drop); and the file can be deleted (on Windows a read-only file cannot, and its attribute is not
        changed here, since a hard-linked part shares it with the adopted file)."""
        root, files = self.dir.resolve(), []
        for folder in self.drop_folders().values():
            real = folder.resolve()
            if real != root / folder.name:
                raise Stop(f"intermediates: {folder} is a link to somewhere else; nothing was deleted")
            for name in parts:
                bits = name.split("/")
                if (len(bits) != 3 or bits[0] not in SPLITS or not bits[2].endswith(".parquet")
                        or any(b in ("", ".", "..") or Path(b).name != b for b in bits)):
                    raise Stop(f"intermediates: {name!r} is not a part name (<split>/<pack>/<file>.parquet); nothing was deleted")
                f = folder.joinpath(*bits)
                if not f.is_file():
                    continue
                if f.parent.resolve() != real.joinpath(*bits[:2]):
                    raise Stop(f"intermediates: {f.parent} is a link to somewhere else; nothing was deleted")
                if not os.access(f.parent, os.W_OK) or (os.name == "nt" and not os.access(f, os.W_OK)):
                    raise Stop(f"intermediates: {f} cannot be deleted (read-only); nothing was deleted")
                files.append((folder.name, f))
        return files

    def drop(self):
        """Delete, from deduped/ and final/, the Parquet of every part whose kept documents are all in shards or left out by
        the shard writer for a stated reason (see droppable_parts and drop_files; nothing else is deleted). The manifest
        says "started" before the first file goes and "done" with the counts afterwards: "parts" counts parts, "folders"
        the files deleted. If the very first deletion fails the mark is taken back, since the run folder is then whole;
        with nothing to delete there is no mark at all, and the run stays resumable. A hard-linked part loses only this
        name. Returns the manifest."""
        parts, left = self.droppable_parts()
        files = self.drop_files(parts)
        verified = self.check_shards_for_drop(parts) if files else 0  # before the first file goes
        folders = {f.name: {"stage": stage, "parquet_files": 0, "bytes": 0, "hard_links": 0}
                   for stage, f in self.drop_folders().items()}
        if not files:  # no part is wholly in shards (or its Parquet is not there): nothing changes on disk
            self.dropped = {"mode": "drop", "parts": {"dropped": 0, "left": left + len(parts)}, "folders": folders}
            print("intermediates: nothing to drop (no part has all its kept documents in shards)", file=sys.stderr, flush=True)
            return self.write()
        self.dropped = {"mode": "drop", "state": "started"}
        self.write()  # on disk before the first file goes: a run stopped halfway through the drop says so
        gone = 0
        for name, f in files:
            try:
                st = f.stat()
                f.unlink()
            except OSError as e:
                if gone:
                    raise Stop(f"intermediates: could not delete {f} ({e}) after {gone} file(s) were deleted; the manifest "
                               "records the drop as started")
                self.dropped = None
                self.write()
                raise Stop(f"intermediates: could not delete {f} ({e}); nothing was deleted")
            gone += 1
            c = folders[name]
            c["parquet_files"], c["bytes"], c["hard_links"] = c["parquet_files"] + 1, c["bytes"] + st.st_size, c["hard_links"] + (st.st_nlink > 1)
        self.dropped = {"mode": "drop", "state": "done", "parts": {"dropped": len(parts), "left": left},
                        "shards_verified": verified, "folders": folders}
        m = self.write()
        print(f"intermediates: dropped {len(parts)} part(s), left {left}: " + ", ".join(
            f"{name} {c['parquet_files']} Parquet file(s), {c['bytes']:,} bytes" for name, c in folders.items()),
            file=sys.stderr, flush=True)
        return m

    def write(self):
        c = {s: self.done[s]["counts"] for s in self.done}
        totals = {}
        if "clean" in c:
            totals["cleaned"] = c["clean"]["rows"]
        if "apply" in c:
            totals["removed_by_dedup"] = c["apply"]["removed"]
        if "f2" in c:
            totals["dropped_by_f2"] = c["f2"]["dropped_by_f2"]
            totals["final"] = c["f2"]["kept"]
        if "shards" in c:
            totals["shards_written"] = c["shards"]["written"]
        if "ledger" in c and self.done["ledger"].get("clean_mode") == "B":
            totals = {"raw": c["ledger"]["rows"], "dropped_by_clean": c["ledger"]["dropped_by_clean"], **totals}
        stages = [self.done[s] for s in STAGES if s in self.done]
        by_pack = self.done.get("ledger", {}).get("by_pack")
        manifest = {"tool": "run_pipeline.py", "run_id": self.cfg["run_id"], "config": self.cfg,
                    "code_sha256": code_sha256(Path(__file__), _CACHE, ("stage_args.py", "clean_manifest.py", "inventory_check.py"))[0], "git_commit": git_commit(),
                    "python": platform.python_version(), "pyarrow": pyarrow_version(), "stages": stages,
                    "checks": [dict(ch, stage=s["stage"]) for s in stages for ch in s.get("checks", [])], "totals": totals,
                    "intermediates": self.dropped or {"mode": self.cfg.get("intermediates", "keep")}}
        if by_pack:
            manifest["by_pack"] = by_pack
        manifest["inventory"] = None  # a run without an expected inventory says so
        if self.inventory is not None:
            # The inventory this invocation was given, and under "checked" the sha256 of the inventory each check point
            # passed with. It is read from the records of the shard and reconcile stages, so it is null until that stage
            # is recorded, and after a resume it shows a check point that passed with another file. "report" is where
            # the check points write, from the shard stage on.
            manifest["inventory"] = {
                **inventory_check.described(self.inventory), "file": self.shown(self.inventory["path"]),
                "checked": {"ledger": self.done.get("shards", {}).get("inventory_sha256"),
                            "reconcile": self.done.get("reconcile", {}).get("inventory_sha256")},
                "report": "inventory_check.json"}
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.manifest_path.with_name(self.manifest_path.name + ".tmp")
        tmp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(self.manifest_path)
        return manifest


def pack_chain(c, clean_mode):
    """One pack and split of the ledger summary as the manifest's chain: (raw, dropped_by_clean,) cleaned, removed by
    dedup, dropped by F2, final. F2 errors have no column: the runner stops when F2 reports any ("F2 reported no errors"),
    so a finished run has none; stage_ledger's "every per-pack row adds up" check still counts them."""
    chain = {"raw": c["rows"], "dropped_by_clean": c["dropped_by_clean"]} if clean_mode == "B" else {}
    chain.update(cleaned=c["rows_cleaned"], removed_by_dedup=c["removed_by_dedup"], dropped_by_f2=c["dropped_by_f2"],
                 final=c["kept"])
    return chain


def pack_table(by_pack):
    """The per-pack chain as a plain-text table, with a total row ("" when there is nothing to show)."""
    first = next((r for sps in by_pack.values() for r in sps.values()), None)
    if first is None:
        return ""
    cols = list(first)
    head = {"raw": "raw", "dropped_by_clean": "-clean", "cleaned": "cleaned", "removed_by_dedup": "-dedup",
            "dropped_by_f2": "-f2", "final": "final"}
    rows = [(pack, split, [r[c] for c in cols]) for pack in sorted(by_pack)
            for split, r in sorted(by_pack[pack].items(), key=lambda kv: SPLITS.index(kv[0]) if kv[0] in SPLITS else 9)]
    rows.append(("total", "", [sum(r[2][i] for r in rows) for i in range(len(cols))]))
    w = max(len("pack"), *(len(r[0]) for r in rows))
    nums = [max(len(head[c]), *(len(f"{r[2][i]:,}") for r in rows)) for i, c in enumerate(cols)]
    line = lambda a, b, vals: f"{a:<{w}}  {b:<7}  " + "  ".join(f"{v:>{n}}" for v, n in zip(vals, nums))
    out = [line("pack", "split", [head[c] for c in cols])]
    out += [line(a, b, [f"{v:,}" for v in vals]) for a, b, vals in rows]
    return "\n".join(out)


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip() or None
    except OSError:
        return None


def pyarrow_version():
    try:
        import pyarrow
        return pyarrow.__version__
    except ImportError:
        return None


def run(config, start=None, to=None):
    """start and to default to the config's "from" and "to"; the arguments are for tests and scripts, not the command line."""
    return Run(config).execute(start, to)


def plan(config, to=None):
    return Run(config).plan(to)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, required=True, help="the run config (JSON): every run parameter is in this file")
    ap.add_argument("--plan", action="store_true", help="check the config and print every stage's folder and command; run nothing")
    args = ap.parse_args()
    try:
        if args.plan:
            print(plan(args.config))
            return
        m = run(args.config)
    except Stop as e:
        sys.exit(f"run_pipeline: {e}")
    print(json.dumps(m["totals"]))


if __name__ == "__main__":
    main()
