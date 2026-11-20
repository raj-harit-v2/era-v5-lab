"""A finished synthetic pipeline run for the shard tests, made by run_pipeline.py itself.

clean, overlap and dedup are adopted (made-up folders in dedup's real formats, from pipeline/tests); apply and
survivor_loss run for real, and F2 is the pipeline tests' stand-in (fake_run_f2.py), which drops the doc_ids in
FAKE_F2_DROP. No real data: every document is made up by the test.
"""
import hashlib
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SHARDS = Path(__file__).resolve().parents[1]  # teams/01-data-a/shards
sys.path.insert(0, str(SHARDS.parent / "pipeline" / "tests"))
sys.path.insert(0, str(SHARDS.parent / "pipeline"))
sys.path.insert(0, str(SHARDS))
from conftest import HEADER  # noqa: E402  (pipeline/tests/conftest.py)
from test_run_pipeline import GROUP_HEADER, overlap_folder, write_config, write_csv  # noqa: E402
import provenance  # noqa: E402
import run_pipeline as rp  # noqa: E402

CLEAN_SHA = "c" * 64


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def raw_sha(split, part):
    """The made-up sha256 of the raw sample part a cleaned part came from."""
    return hashlib.sha256(f"raw {split}/{part}".encode()).hexdigest()


def write_cleaned(root, parts):
    """Cleaned parts <root>/<split>/<part> and the clean job's job_summary.json. parts: {(split, part): [row dicts]}."""
    root, entries = Path(root), []
    for (split, part), rows in parts.items():
        path = root / split / part
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows), path)
        entries.append({"part": f"{split}/{part}", "split": split, "pack_id": part.split("/")[0], "status": "cleaned",
                        "input_sha256": raw_sha(split, part), "output_sha256": sha(path)})
    (root / "job_summary.json").write_text(json.dumps({"clean_sha256": CLEAN_SHA, "parts": entries}), encoding="utf-8")


def make_run(folder, monkeypatch, parts, removed=(), f2_drop=(), shards=None):
    """Run the pipeline in `folder` over `parts` and return the run's folder (<folder>/runs/test-run).

    removed: [(split, part, row_in_part)] that dedup removes, each as a group of two (the other member is the survivor).
    f2_drop: doc_ids the stand-in F2 drops.
    shards: a stages.shards config; the run then goes through the real shard stage (which writes cleaning_pipeline.json),
    otherwise this writes it as the stage does."""
    for k in ("FAKE_F2_ERROR", "FAKE_F2_BAD_SHA", "FAKE_F2_CRASH"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("FAKE_F2_DROP", ",".join(f2_drop))
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    cleaned = folder / "cleaned"
    write_cleaned(cleaned, parts)
    total = sum(len(rows) for rows in parts.values())
    overlap = overlap_folder(folder / "overlap", parts, docs_all=total)
    dedup = folder / "dedup"
    removals, groups = [], []
    for n, (split, part, row) in enumerate(removed, start=1):
        rows = parts[(split, part)]
        pack, kept, gid = rows[row]["pack_id"], (0 if row else 1), f"G{n:06d}"
        removals.append([pack, split, part, row, rows[row]["doc_id"]])
        groups += [[gid, 2, 4, "survivor", pack, split, part, kept, rows[kept]["doc_id"]],
                   [gid, 2, 4, "removed", pack, split, part, row, rows[row]["doc_id"]]]
    write_csv(dedup / "remove_list.csv", HEADER, removals)
    write_csv(dedup / "dedup_groups.csv", GROUP_HEADER, groups)
    checked = {n: sha(overlap / n) for n in ("overlap_matches.csv", "overlap_docs.parquet")}
    (dedup / "dedup_summary.json").write_text(json.dumps({
        "status": "complete", "overlap_run": {"documents_all": total, "checked_sha256": checked}, "documents_all": total,
        "removed": len(removals), "heldout_removed": 0,
        "clusters": len(groups) // 2, "groups_without_survivor": 0, "groups_with_several_survivors": 0,
        "config": {"cross_pack": True, "pack_order": ["code-go", "en-dclm"], "licence_usable": {}, "default_licence_usable": True,
                   "gold_dirs": []}}), encoding="utf-8")
    config = write_config(folder / "pipeline.json", {"cleaned": cleaned, "overlap": overlap, "dedup": dedup},
                          **({"shards": shards} if shards else {}))
    rp.run(config)
    run = folder / "runs" / "test-run"
    if not shards:
        provenance.write_record(run / "pipeline_manifest.json")  # what run_pipeline.py's shard stage does first
    return run
