"""Execution tasks (stdin/stdout tests) for the bench's dev or test problems, from the pinned human-written sources.

    python exec_tasks.py --split-file <slice>/test.tok.jsonl --sources-root <root with sources/> --out test.exec.jsonl

Evaluation-side only: train.py never reads its output. One task per problem cluster (the cluster's first row by id).
The source row is located by the pack sidecar fields carried in the slice (`source_row_key`, `source_file`,
`source_local_ordinal`) and accepted only if the statement's family hash recomputed from that row equals the row's
`problem_family_key` (so a mis-located row can never lend its tests). Tests come from the source's own fields:
TACO / APPS `input_output` (call-based `fn_name` problems are skipped: the stdio checker cannot run them);
code_contests `public_tests` + `private_tests` + `generated_tests` (file-I/O problems skipped). The record holds the
tests and keys only, never the statement; the prompt comes from the slice row. Output stays out of Git.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SFT = HERE.parent


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


si = _load("g10_source_index_for_bench", SFT / "source_index.py")
MAX_TESTS = 20  # = rl-data/stdio_check.MAX_TESTS
SOURCES = {  # dataset -> (folder under sources/, file suffix, question assembly, licence, generator)
    "taco": ("BAAI__TACO@d593ed0a2bec", "", "question", "Apache-2.0", "human (source tests)"),
    "apps": ("codeparrot__apps@21e74ddf8de1", "", "question", "MIT", "human (source tests)"),
    "code_contests": ("deepmind__code_contests@802411c3/data", ".parquet", "description", "CC-BY-4.0",
                      "human problems; generated_tests are programmatic mutations of human inputs"),
}


def _as_text(v) -> str | None:
    if isinstance(v, str):
        return v
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        return "\n".join(v)
    return None


def tests_from_row(dataset: str, row: dict) -> tuple[list[dict] | None, str]:
    if dataset in ("taco", "apps"):
        raw = row.get("input_output")
        try:
            io = json.loads(raw) if isinstance(raw, str) and raw else None
        except json.JSONDecodeError:
            return None, "input_output_not_json"
        if not isinstance(io, dict):
            return None, "no_input_output"
        if io.get("fn_name"):
            return None, "call_based_fn_name"
        tests = []
        for i, o in zip(io.get("inputs") or [], io.get("outputs") or []):
            ti, to = _as_text(i), _as_text(o)
            if ti is None or to is None:
                return None, "non_text_test"
            tests.append({"input": ti, "output": to})
    else:
        if row.get("input_file") or row.get("output_file"):
            return None, "file_io"
        tests = []
        for key in ("public_tests", "private_tests", "generated_tests"):
            t = row.get(key) or {}
            tests += [{"input": i, "output": o} for i, o in zip(t.get("input", []), t.get("output", []))]
    if not tests:
        return None, "no_tests"
    return tests[:MAX_TESTS], "ok"


def build(split_file: Path, sources_root: Path) -> tuple[list[dict], dict]:
    reps: dict[str, dict] = {}
    with open(split_file, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("split") == "train":
                raise SystemExit("exec_tasks.py builds evaluation tasks only; got a train row")
            keep = {k: r[k] for k in ("id", "split", "cluster", "problem_family_key", "source_row_key", "source_file",
                                      "source_local_ordinal")}
            if r["cluster"] not in reps or keep["id"] < reps[r["cluster"]]["id"]:
                reps[r["cluster"]] = keep
    # group by source file so each file is streamed once
    wanted: dict[Path, dict[int, list[dict]]] = {}
    for rep in reps.values():
        dataset = rep["source_row_key"][2]
        folder, suffix, *_ = SOURCES[dataset]
        path = sources_root / "sources" / folder / (rep["source_file"] + suffix)
        wanted.setdefault(path, {}).setdefault(int(rep["source_local_ordinal"]), []).append(rep)
    tasks, outcomes = [], Counter()
    for path, by_ord in sorted(wanted.items()):
        dataset = next(iter(by_ord.values()))[0]["source_row_key"][2]
        _, _, assembly, licence, generator = SOURCES[dataset]
        cols = ["question", "input_output"] if dataset != "code_contests" else [
            "description", "public_tests", "private_tests", "generated_tests", "input_file", "output_file"]
        last = max(by_ord)
        for i, row in enumerate(si._file_rows(path, cols)):
            if i in by_ord:
                q = si._usable(si.assemble_question(assembly, row))
                fam = "sha256:" + si.family_sha256(q) if q is not None else None
                for rep in by_ord[i]:
                    if fam != rep["problem_family_key"]:
                        outcomes["skipped_family_mismatch"] += 1
                        continue
                    tests, why = tests_from_row(dataset, row)
                    if tests is None:
                        outcomes[f"skipped_{why}"] += 1
                        continue
                    outcomes["task"] += 1
                    tasks.append({"id": rep["cluster"], "row_id": rep["id"], "split": rep["split"],
                                  "problem_family_key": rep["problem_family_key"], "kind": "stdio", "tests": tests,
                                  "time_limit_s": 4, "source": f"{dataset} ({rep['source_row_key'][0]}@{rep['source_row_key'][1][:12]})",
                                  "licence": licence, "generator": generator})
            if i >= last:
                break
    tasks.sort(key=lambda t: t["id"])
    return tasks, {"clusters": len(reps), "outcomes": dict(outcomes),
                   "by_source": dict(Counter(t["source"].split(" ")[0] for t in tasks))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split-file", required=True, type=Path)
    ap.add_argument("--sources-root", required=True, type=Path, help="folder holding sources/<pinned snapshots>")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    tasks, summary = build(args.split_file, args.sources_root)
    blob = "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks).encode("utf-8")
    args.out.write_bytes(blob)
    print(json.dumps({**summary, "tasks": len(tasks), "sha256": hashlib.sha256(blob).hexdigest()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
