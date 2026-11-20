"""Where one final part came from: check its chain through the pipeline and return what the shard has to record.

  python -I teams/01-data-a/shards/provenance.py --input <run>/final/train/code-go/part-00000.parquet \
      --manifest <run>/pipeline_manifest.json

--input is a part F2 wrote (<run>/final/<split>/<pack>/<part>.parquet); --manifest is run_pipeline.py's
pipeline_manifest.json, which sits in <run>, next to final/ and deduped/. The chain, each link a sha256 that must match:

  final part  --(<part>.f2.json: output_sha256)------------>  the part as it is now
  F2 report   --(input_sha256)------------------------------>  apply's output_sha256 (deduped/apply_dedup_summary.json)
  apply       --(remove_list.sha256)------------------------>  dedup's remove_list.csv as it is now
  apply       --(input_sha256)------------------------------>  the cleaned part = output_sha256 in clean's job_summary.json
  clean job   --(input_sha256)------------------------------>  the raw sample part

Stops (Stop, with the failed link named) when a link breaks, when the F2 report has errors or another fingerprint set than
the manifest's, when the manifest lacks a stage or holds a failed check, when a doc_id removed by dedup has no group in
dedup_groups.csv, when the part's pack_id column is not the pack it sits in, or when the clean output folder has no
job_summary.json (the raw part's sha256, shard field inputs_sha256, comes from it).

It trusts the recorded hashes of the cleaned part and of dedup_groups.csv; it rehashes only the final part and
remove_list.csv. It reads no document text: the part's pack_id column and its row count only.

Returns a dict of IDs, counts and hashes (never text):
  part        {split, part, pack_id, path}            split is train or heldout, as the pipeline names them
  final       {sha256, rows}
  raw_input   {sha256, part}                          the sample part clean read (shard field inputs_sha256)
  clean       {clean_py_sha256, status}               status: clean's own word for the part ("cleaned", a pass-through, ...)
  dedup       {remove_list_sha256, remove_list_rows, removed: [{doc_id, row_in_part, group_id, priority_rule}]}
                                                      removed: this part's docs, rows in the cleaned part
  f2          {set_sha256, run_f2_py_sha256, dropped: [{doc_id, items, offset}]}   items are benchmark item IDs
  counts      {cleaned, removed_by_dedup, dropped_by_f2, final}
  pipeline    {manifest_sha256, run_id, git_commit}
  record      {clean_py_sha256, f2_set_sha256, dedup: {...}}   = processing_record(): see there

processing_record(manifest) is what <run>/cleaning_pipeline.json says: the processing behind every shard of the run (no
link to the manifest, which is rewritten after every stage). run_pipeline.py's shard stage writes that file with
write_record(manifest) (or: provenance.py --manifest <m> --write-record); shard_writer.py finds it next to the manifest,
checks it against processing_record() and copies it into the shard folder.
"""
import sys
sys.dont_write_bytecode = True

import argparse, csv, hashlib, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]  # teams/01-data-a/shards/provenance.py -> the repository root
SPLITS = ("train", "heldout")
NEEDED_STAGES = ("clean", "overlap", "dedup", "apply", "f2")


class Stop(Exception):
    """A link of the chain is broken: the message says which."""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError:
        raise Stop(f"{what} not found: {path}")
    except ValueError:
        raise Stop(f"{what} is not valid JSON: {path}")


def one(entries, what):
    if len(entries) != 1:
        raise Stop(f"{what}: expected one entry, found {len(entries)}")
    return entries[0]


def where_in_run(input_part, run):
    """(split, pack_id, part) of a file under <run>/final/<split>/<pack>/..., else Stop."""
    final = (run / "final").resolve()
    try:
        rel = Path(input_part).resolve().relative_to(final)
    except ValueError:
        raise Stop(f"--input {input_part} is not under {final}, the final folder of the run the manifest belongs to")
    if len(rel.parts) < 3 or rel.parts[0] not in SPLITS:
        raise Stop(f"--input {input_part}: expected final/<train or heldout>/<pack>/<part>.parquet, found {rel.as_posix()}")
    return rel.parts[0], rel.parts[1], Path(*rel.parts[1:]).as_posix()


def pack_ids_and_rows(path):
    import pyarrow.parquet as pq
    try:
        pf = pq.ParquetFile(path)
        if "pack_id" not in pf.schema_arrow.names:
            raise Stop(f"{path}: no pack_id column")
        return set(pf.read(columns=["pack_id"]).column("pack_id").to_pylist()), pf.metadata.num_rows
    except Stop:
        raise
    except Exception as e:
        raise Stop(f"{path}: cannot be read as Parquet ({type(e).__name__})")


def csv_rows(path, split, part):
    """The rows of a dedup CSV that belong to this (split, part), as dicts."""
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["split"] == split and r["part"].replace("\\", "/") == part]


def read_manifest(manifest):
    """(the manifest, {stage: its record}); Stop when it is not run_pipeline.py's, lacks a stage the shard needs, or holds a failed check."""
    m = read_json(manifest, "the pipeline manifest")
    if m.get("tool") != "run_pipeline.py":
        raise Stop(f"{manifest} is not a run_pipeline.py manifest")
    stages = {s["stage"]: s for s in m.get("stages", [])}
    absent = [s for s in NEEDED_STAGES if s not in stages]
    if absent:
        raise Stop(f"{manifest} has no record of stage(s) {', '.join(absent)}: run the pipeline through f2 first")
    failed = [c for c in m.get("checks", []) if not c.get("ok")]
    if failed:
        raise Stop(f"{manifest} holds a failed check: {failed[0].get('stage')}: {failed[0].get('check')}")
    return m, stages


def stage_output(m, stage, repo):
    """The stage's output folder: as its manifest record shows it (the config may leave it to the default)."""
    rec = next((s for s in m.get("stages", []) if s.get("stage") == stage), {})
    out = Path(rec.get("output") or m["config"]["stages"][stage]["output"])
    return out if out.is_absolute() else Path(repo) / out


def processing_record(manifest, repo=REPO):
    """What the run's processing was, for cleaning_pipeline.json:
      {clean_py_sha256, f2_set_sha256,
       dedup: {remove_list_sha256, remove_list_rows,
               overlap: {matches_sha256, docs_sha256, k, floor, code_sha256},         the overlap run dedup used
               settings: {cross_pack, pack_order, licence_usable, default_licence_usable},
               code_sha256}}                                                         null while a stage was adopted
    Read from the manifest, the clean job's job_summary.json, apply's summary, remove_list.csv as it is now, and the config
    blocks of overlap's and dedup's summaries (paths, timings and gold_dirs are left out: they do not change what is removed)."""
    manifest = Path(manifest)
    m, stages = read_manifest(manifest)
    run = manifest.resolve().parent
    job_path = stage_output(m, "clean", repo) / "job_summary.json"
    if not job_path.is_file():
        raise Stop(f"{job_path.parent} has no job_summary.json: the clean job's summary records the clean.py sha256 and the raw parts")
    clean_sha = read_json(job_path, "the clean job's summary").get("clean_sha256")
    if not clean_sha:
        raise Stop(f"{job_path}: no clean_sha256")
    f2_set = stages["f2"].get("set_sha256")
    if not f2_set:
        raise Stop(f"{manifest}: the f2 stage records no set_sha256")
    summary = read_json(run / "deduped" / "apply_dedup_summary.json", "apply's summary")
    remove_list = stage_output(m, "dedup", repo) / "remove_list.csv"
    if not remove_list.is_file():
        raise Stop(f"{remove_list.parent} has no remove_list.csv")
    rl_sha = sha256(remove_list)
    if rl_sha != summary.get("remove_list", {}).get("sha256"):
        raise Stop(f"{remove_list} changed after apply used it (sha256 {rl_sha[:12]}…, apply recorded "
                   f"{str(summary.get('remove_list', {}).get('sha256'))[:12]}…)")
    overlap_sum = read_json(stage_output(m, "overlap", repo) / "overlap_summary.json", "overlap's summary")
    dedup_sum = read_json(stage_output(m, "dedup", repo) / "dedup_summary.json", "dedup's summary")
    o_cfg, d_cfg = overlap_sum.get("config"), dedup_sum.get("config")
    checked = (dedup_sum.get("overlap_run") or {}).get("checked_sha256") or {}
    for what, have, keys in (("overlap_summary.json config", o_cfg, ("k", "floor")),
                             ("dedup_summary.json config", d_cfg, ("cross_pack", "pack_order", "licence_usable", "default_licence_usable")),
                             ("dedup_summary.json overlap_run.checked_sha256", checked, ("overlap_matches.csv", "overlap_docs.parquet"))):
        lacking = [k for k in keys if not isinstance(have, dict) or k not in have]
        if lacking:
            raise Stop(f"{what} has no {', '.join(lacking)}: the shard records the settings dedup ran with")
    return {"clean_py_sha256": clean_sha, "f2_set_sha256": f2_set,
            "dedup": {"remove_list_sha256": rl_sha, "remove_list_rows": summary["remove_list"]["rows"],
                      "overlap": {"matches_sha256": checked["overlap_matches.csv"], "docs_sha256": checked["overlap_docs.parquet"],
                                  "k": o_cfg["k"], "floor": o_cfg["floor"], "code_sha256": stages["overlap"].get("code_sha256")},
                      "settings": {k: d_cfg[k] for k in ("cross_pack", "pack_order", "licence_usable", "default_licence_usable")},
                      "code_sha256": stages["dedup"].get("code_sha256")}}


def write_record(manifest, repo=REPO):
    """Write <run>/cleaning_pipeline.json (next to the manifest) from processing_record. Returns (path, record)."""
    record = processing_record(manifest, repo)
    path = Path(manifest).resolve().parent / "cleaning_pipeline.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path, record


def load(input_part, manifest, repo=REPO):
    input_part, manifest, repo = Path(input_part), Path(manifest), Path(repo)
    m, stages = read_manifest(manifest)
    run = manifest.resolve().parent
    split, pack_id, part = where_in_run(input_part, run)
    if not input_part.is_file():
        raise Stop(f"--input {input_part} is not a file")

    def out_of(stage):
        return stage_output(m, stage, repo)

    # the final part and its F2 report
    packs, rows = pack_ids_and_rows(input_part)
    if packs != {pack_id} and (packs or rows):  # an empty part (dedup or F2 removed every row) has no pack_id to hold
        raise Stop(f"{split}/{part}: its pack_id column holds {sorted(packs)}, the part sits in pack {pack_id}")
    final_sha = sha256(input_part)
    f2 = read_json(input_part.with_name(input_part.name + ".f2.json"), f"the F2 report of {split}/{part}")
    if f2.get("output_sha256") != final_sha:
        raise Stop(f"{split}/{part}: the part is not what F2 wrote (sha256 {final_sha[:12]}…, its F2 report says "
                   f"{str(f2.get('output_sha256'))[:12]}…): it changed after F2")
    if f2.get("errors"):
        raise Stop(f"{split}/{part}: F2 reported {len(f2['errors'])} error(s) on this part")
    if f2.get("set_sha256") != stages["f2"].get("set_sha256"):
        raise Stop(f"{split}/{part}: F2 used fingerprint set {str(f2.get('set_sha256'))[:12]}…, the manifest records "
                   f"{str(stages['f2'].get('set_sha256'))[:12]}…")
    if f2.get("kept") != rows or f2.get("rows") != rows + f2.get("dropped_by_f2", 0):
        raise Stop(f"{split}/{part}: F2 reports rows {f2.get('rows')}, kept {f2.get('kept')}, dropped "
                   f"{f2.get('dropped_by_f2')}; the part has {rows} rows")

    # apply: F2 read what apply wrote
    summary_path = run / "deduped" / "apply_dedup_summary.json"
    summary = read_json(summary_path, "apply's summary")
    entry = one([p for p in summary.get("parts", []) if p["split"] == split and p["part"] == part],
                f"{summary_path} for {split}/{part}")
    if entry["output_sha256"] != f2.get("input_sha256"):
        raise Stop(f"{split}/{part}: F2 read a part with sha256 {str(f2.get('input_sha256'))[:12]}…, apply wrote "
                   f"{entry['output_sha256'][:12]}…")
    if entry["kept"] != f2["rows"]:
        raise Stop(f"{split}/{part}: apply kept {entry['kept']} rows, F2 read {f2['rows']}")

    # dedup: the remove list apply used is the one on disk, and every removed doc has its group
    dedup_out = out_of("dedup")
    remove_list = dedup_out / "remove_list.csv"
    if not remove_list.is_file():
        raise Stop(f"{dedup_out} has no remove_list.csv")
    rl_sha = sha256(remove_list)
    if rl_sha != summary.get("remove_list", {}).get("sha256"):
        raise Stop(f"{remove_list} changed after apply used it (sha256 {rl_sha[:12]}…, apply recorded "
                   f"{str(summary.get('remove_list', {}).get('sha256'))[:12]}…)")
    listed = csv_rows(remove_list, split, part)
    if len(listed) != entry["removed"]:
        raise Stop(f"{split}/{part}: the remove list names {len(listed)} rows, apply removed {entry['removed']}")
    groups = {int(r["row_in_part"]): r for r in csv_rows(out_of("dedup") / "dedup_groups.csv", split, part)
              if r["role"] == "removed"}
    removed = []
    for r in sorted(listed, key=lambda r: int(r["row_in_part"])):
        g = groups.get(int(r["row_in_part"]))
        if g is None or g["doc_id"] != r["doc_id"]:
            raise Stop(f"{split}/{part} row {r['row_in_part']} (doc_id {r['doc_id']}): removed by the list, but "
                       "dedup_groups.csv has no removed member there")
        removed.append({"doc_id": r["doc_id"], "row_in_part": int(r["row_in_part"]), "group_id": g["group_id"],
                        "priority_rule": int(g["priority_rule"])})

    # clean: the cleaned part apply read is the one clean wrote, and clean's job_summary names the raw part
    clean_out = out_of("clean")
    job_path = clean_out / "job_summary.json"
    if not job_path.is_file():
        raise Stop(f"{clean_out} has no job_summary.json: the shard needs the sha256 of the raw sample part, "
                   "which only the clean job's summary records")
    job = read_json(job_path, "the clean job's summary")
    cleaned = one([p for p in job.get("parts", []) if p.get("part") == f"{split}/{part}"],
                  f"{job_path} for {split}/{part}")
    if cleaned.get("output_sha256") != entry["input_sha256"]:
        raise Stop(f"{split}/{part}: apply read a cleaned part with sha256 {entry['input_sha256'][:12]}…, the clean job "
                   f"wrote {str(cleaned.get('output_sha256'))[:12]}…")
    if not job.get("clean_sha256") or not cleaned.get("input_sha256"):
        raise Stop(f"{job_path}: no clean_sha256 or no input_sha256 for {split}/{part}")

    return {
        "part": {"split": split, "part": part, "pack_id": pack_id, "path": input_part.as_posix()},
        "final": {"sha256": final_sha, "rows": rows},
        "raw_input": {"sha256": cleaned["input_sha256"], "part": f"{split}/{part}"},
        "clean": {"clean_py_sha256": job["clean_sha256"], "status": cleaned.get("status")},
        "dedup": {"remove_list_sha256": rl_sha, "remove_list_rows": summary["remove_list"]["rows"], "removed": removed},
        "f2": {"set_sha256": f2["set_sha256"], "run_f2_py_sha256": f2.get("run_f2_py_sha256"),
               "dropped": f2.get("dropped", [])},
        "counts": {"cleaned": entry["rows"], "removed_by_dedup": entry["removed"],
                   "dropped_by_f2": f2["dropped_by_f2"], "final": rows},
        "pipeline": {"manifest_sha256": sha256(manifest), "run_id": m.get("run_id"), "git_commit": m.get("git_commit")},
        "record": processing_record(manifest, repo),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, help="a part F2 wrote: <run>/final/<split>/<pack>/<part>.parquet")
    ap.add_argument("--manifest", type=Path, required=True, help="the run's pipeline_manifest.json")
    ap.add_argument("--write-record", action="store_true", help="write <run>/cleaning_pipeline.json instead of checking a part")
    args = ap.parse_args()
    if not args.write_record and not args.input:
        ap.error("--input is required unless --write-record is given")
    try:
        if args.write_record:
            path, record = write_record(args.manifest)
            print(f"wrote {path}\n{json.dumps(record, indent=2)}")
            return
        info = load(args.input, args.manifest)
    except Stop as e:
        sys.exit(f"provenance: {e}")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
