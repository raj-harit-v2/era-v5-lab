"""Build the DeepCoder PrimeIntellect Python stdin/stdout pilot from a pinned shard."""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import islice
from pathlib import Path

import stdio_check

DATASET = "agentica-org/DeepCoder-Preview-Dataset"
REVISION = "780aeec7b7716e34f0b9e02bb624fc6ad8384725"
SHARD = "train-00000-of-00005.parquet"
SHARD_SHA256 = "a1efc9d5e9eb6a9977576b08e5349758c8b139131ea5d13ef5c390f2a21db538"
SET_ID = "rl-code-deepcoder"
FINGERPRINT_SHA256 = "2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a"
WRONG = "```python\npass\n```"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def convert_row(row: dict, index: int) -> dict | None:
    """Accept Python script problems with complete, bounded stdin/stdout tests."""
    problem = row.get("problem")
    if not isinstance(problem, str) or "using the programming language python" not in problem.lower():
        return None
    try:
        tests = json.loads(row["tests"])
    except (KeyError, TypeError, ValueError):
        return None
    if not isinstance(tests, list) or not 1 <= len(tests) <= stdio_check.MAX_TESTS:
        return None
    if not all(
        isinstance(case, dict)
        and case.get("type") == "stdin_stdout"
        and isinstance(case.get("input"), str)
        and isinstance(case.get("output"), str)
        and len(case["output"]) <= stdio_check.MAX_OUTPUT_CHARS
        for case in tests
    ):
        return None
    if not any(case["output"].strip() for case in tests):
        return None

    reference = next(
        (solution for solution in (row.get("solutions") or [])
         if isinstance(solution, str) and stdio_check.extract_code(solution)[0] is not None),
        None,
    )
    if reference is None:
        return None
    return {
        "id": f"deepcoder/primeintellect/{SHARD[:-8]}/{index}",
        "kind": "stdio",
        "statement": problem,
        "tests": [{"input": case["input"], "output": case["output"]} for case in tests],
        "reference": reference,
        "time_limit_s": 4,
        "source": f"{DATASET}@{REVISION}/primeintellect/{SHARD}#{index}",
        "licence": "MIT",
        "generator": "none (human competition problems and execution tests)",
        "licence_table_set": SET_ID,
    }


def write_tasks(path: Path, tasks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")


def prepare(shard: Path, scan_rows: int, output: Path) -> None:
    import pyarrow.parquet as pq

    if shard.name != SHARD or sha256_file(shard) != SHARD_SHA256:
        raise ValueError("expected the pinned PrimeIntellect train shard")
    tasks = []
    scanned = 0
    with pq.ParquetFile(shard) as source:
        batches = source.iter_batches(batch_size=min(scan_rows, 64), columns=["problem", "tests", "solutions"])
        rows = (row for batch in batches for row in batch.to_pylist())
        for index, row in enumerate(islice(rows, scan_rows)):
            scanned += 1
            task = convert_row(row, index)
            if task is not None:
                tasks.append(task)
    if not tasks:
        raise ValueError("no supported tasks in the scanned rows")
    write_tasks(output, tasks)
    print(f"Prepared {len(tasks)} of {scanned} source rows for decontamination.")


def validate(record_path: Path, output: Path, manifest_path: Path) -> None:
    """Gold-check clean tasks, then export training records and text-free evidence."""
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if (
        record.get("set") != SET_ID
        or record.get("ok") is not True
        or record.get("scope") != "full set"
        or record.get("set_sha256") != FINGERPRINT_SHA256
        or record.get("checks", {}).get("clean_file_flags_0") is not True
        or record.get("rows_canary") != 0
        or len(record.get("clean", [])) != 1
    ):
        raise ValueError("expected a successful full Team 9 v2 decontamination record")
    clean = record["clean"][0]
    clean_path = record_path.parent / clean["name"]
    if sha256_file(clean_path) != clean["sha256"]:
        raise ValueError("clean tasks do not match the decontamination record")
    if stdio_check.RUNNER_KIND != "docker":
        raise ValueError("DeepCoder references must be scored with the Docker runner")

    tasks = []
    results = []
    skipped = []
    with clean_path.open(encoding="utf-8") as f:
        for line in f:
            task = json.loads(line)
            reference = task.pop("reference")
            gold = stdio_check.score(task, reference)
            if gold["reason"].startswith("runner exited"):
                raise RuntimeError(f"Docker runner failed for {task['id']}: {gold['reason']}")
            if gold["reward"] != 1:
                skipped.append({"id": task["id"], "reason": gold["reason"]})
                continue
            wrong = stdio_check.score(task, WRONG)
            if wrong["reward"] != 0 or wrong["reason"] != "wrong answer on a test":
                raise RuntimeError(f"negative control failed for {task['id']}: {wrong['reason']}")
            tasks.append(task)
            results.append({"id": task["id"], "correct": gold["reward"], "wrong": wrong["reward"],
                            "tests": gold["total"]})

    if not tasks:
        raise ValueError("no clean reference passed the verifier")
    write_tasks(output, tasks)
    manifest = {
        "dataset": DATASET,
        "revision": REVISION,
        "shard": f"primeintellect/{SHARD}",
        "shard_sha256": SHARD_SHA256,
        "fingerprint_set_sha256": FINGERPRINT_SHA256,
        "candidate_sha256": record["inputs"][0]["sha256"],
        "candidates_screened": record["rows_in"],
        "flagged": record["rows_flagged"],
        "canary": record["rows_canary"],
        "clean": record["rows_kept"],
        "clean_sha256": clean["sha256"],
        "skipped_after_scoring": skipped,
        "verified_tasks": results,
        "pack_sha256": sha256_file(output),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(tasks)} of {record['rows_kept']} clean tasks.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--shard", type=Path, required=True)
    prepare_parser.add_argument("--scan-rows", type=int, default=20)
    prepare_parser.add_argument("--out", type=Path, required=True)
    validate_parser = commands.add_parser("verify")
    validate_parser.add_argument("--record", type=Path, required=True)
    validate_parser.add_argument("--out", type=Path, required=True)
    validate_parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        if args.scan_rows < 1:
            parser.error("--scan-rows must be positive")
        prepare(args.shard, args.scan_rows, args.out)
    else:
        validate(args.record, args.out, args.manifest)


if __name__ == "__main__":
    main()
