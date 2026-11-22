"""Unused source tests for the strict check: for the given RL data v1 code tasks, fetch the pinned code_contests parquet
shard of each task, verify the shard sha256 and that the kept tests are the prefix of the source tests, and write the
next tests (the ones the reward never used) to a private jsonl. Same rule as rl-loop/pilots/fable_e1_20261115/
modal_audit.py::fetch_hidden, for a local machine.

    python fetch_unused_tests.py --tasks cc.jsonl --ids passed_task_ids.txt --max-unused 80 --out hidden.jsonl

Only the shards that hold the listed tasks are downloaded (Hugging Face cache). Output stays private (test data).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DATASET = "deepmind/code_contests"


def unused_tests(row: dict, kept: list[dict], max_unused: int) -> list[dict] | None:
    """Source tests in the builder's order (public, private, generated); None if the kept tests are not the prefix."""
    tests = []
    for key in ("public_tests", "private_tests", "generated_tests"):
        t = row.get(key) or {}
        tests += [{"input": i, "output": o} for i, o in zip(t.get("input", []), t.get("output", []))]
    if tests[: len(kept)] != kept:
        return None
    return tests[len(kept): len(kept) + max_unused]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--ids", type=Path, required=True)
    ap.add_argument("--max-unused", type=int, default=80)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    import pyarrow.parquet as pq  # noqa: PLC0415
    from huggingface_hub import hf_hub_download  # noqa: PLC0415
    want = set(a.ids.read_text().split())
    tasks = {}
    for line in a.tasks.read_text(encoding="utf-8").splitlines():
        if line.strip():
            t = json.loads(line)
            if t["id"] in want:
                tasks[t["id"]] = t
    by_file: dict[tuple[str, str], list[str]] = {}
    for tid, t in tasks.items():
        p = t["provenance"]
        by_file.setdefault((p["file"], p["revision"]), []).append(tid)
    stats = {"tasks": len(tasks), "files": len(by_file), "sha_mismatch": 0, "prefix_mismatch": 0, "no_unused": 0, "written": 0,
             "unused_tests": 0}
    with open(a.out, "w", encoding="utf-8") as f:
        for (fname, rev), tids in sorted(by_file.items()):
            try:
                path = hf_hub_download(DATASET, f"data/{fname}", repo_type="dataset", revision=rev)
            except Exception:  # noqa: BLE001  (layout without data/)
                path = hf_hub_download(DATASET, fname, repo_type="dataset", revision=rev)
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != tasks[tids[0]]["provenance"]["file_sha256"]:
                stats["sha_mismatch"] += len(tids)
                continue
            table = pq.read_table(path, columns=["public_tests", "private_tests", "generated_tests"])
            for tid in tids:
                row = table.slice(tasks[tid]["provenance"]["source_ordinal"], 1).to_pylist()[0]
                hidden = unused_tests(row, tasks[tid]["tests"], a.max_unused)
                if hidden is None:
                    stats["prefix_mismatch"] += 1
                    continue
                if not hidden:
                    stats["no_unused"] += 1
                    continue
                f.write(json.dumps({"id": tid, "tests": hidden}) + "\n")
                stats["written"] += 1
                stats["unused_tests"] += len(hidden)
    a.out.chmod(0o600)
    print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
