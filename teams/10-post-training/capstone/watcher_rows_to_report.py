"""Turn Team 9's watcher output (eval_mini_v1, points 0..100) into the `eval_mini` block that sft/tests/forgetting.py reads.

Team 9's `run_lab_ckpt.py` writes `eval_mini_v1_lab.json`: one record per task with `value` and `stderr` in points
(0..100) and the `dtype` the scorer ran in. forgetting.py wants fractions (0..1) and, when the block carries a `dtype`,
checks it against the bits-per-byte report's `compute_dtype` (sft/tests/forgetting.py, `_check_benchmark_dtype`). The
eval_schedule.md section 8 proposal is that Team 9 hands rows in fractions; until it does, this is the one place the
division happens, so it is not done by hand.

    python capstone/watcher_rows_to_report.py --watcher-doc out/eval_mini_v1_lab.json --out after_mini.json
    python capstone/watcher_rows_to_report.py --watcher-doc ... --report after_forget.json --out after.json   # merged

    python sft/tests/forgetting.py --before base_forget.json base_mini.json --after after_forget.json after_mini.json \\
        --out forgetting.md

What it refuses instead of guessing: a document that is not `eval_mini_v1`, a missing task, a task that appears twice
(several formats), records that disagree on `dtype` or `model_revision`, an unknown dtype, a value or stderr outside
0..100. It reads only the watcher's own scores. Team 10 never reads benchmark items."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = "eval_mini_v1"
DEFAULT_TASKS = ("arc_challenge", "hellaswag")   # the two forgetting.py compares (its TASKS)
KEEP = ("task", "metric", "filter", "num_fewshot", "value", "stderr", "n_items")
_DTYPES = {"float32": "float32", "fp32": "float32", "bfloat16": "bfloat16", "bf16": "bfloat16"}


class WatcherRowsError(ValueError):
    pass


def _dtype(raw, task: str) -> str:
    key = str(raw).removeprefix("torch.").split(" ")[0].lower()
    if key not in _DTYPES:
        raise WatcherRowsError(f"{task}: dtype {raw!r} is not float32 or bfloat16")
    return _DTYPES[key]


def _points(rec: dict, field: str, *, allow_none: bool) -> float | None:
    v = rec.get(field)
    if v is None and allow_none:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
        raise WatcherRowsError(f"{rec.get('task')}: {field} {v!r} is not a number")
    if not 0.0 <= v <= 100.0:
        raise WatcherRowsError(f"{rec.get('task')}: {field} {v} is outside 0..100 points")
    return round(v / 100.0, 8)


def convert(doc: dict, tasks=DEFAULT_TASKS, *, source: str = "") -> dict:
    """{"eval_mini": {...}} with fractions for the given tasks. `doc` is the parsed eval_mini_v1 document."""
    if not isinstance(doc, dict) or doc.get("schema_version") != SCHEMA:
        raise WatcherRowsError(f"not an {SCHEMA} document (schema_version "
                               f"{doc.get('schema_version') if isinstance(doc, dict) else None!r}); the values are "
                               "only known to be points for that schema")
    found: dict[str, list[dict]] = {t: [] for t in tasks}
    for r in doc.get("records") or []:
        if r.get("task") in found:
            found[r["task"]].append(r)
    missing = [t for t, rs in found.items() if not rs]
    if missing:
        raise WatcherRowsError(f"the watcher document has no record for {', '.join(missing)}")
    twice = [t for t, rs in found.items() if len(rs) > 1]
    if twice:
        raise WatcherRowsError(f"{', '.join(twice)} appear more than once (formats "
                               f"{sorted({str(r.get('format')) for t in twice for r in found[t]})}); pick one")
    chosen = [rs[0] for rs in found.values()]
    dtypes = {_dtype(r.get("dtype"), r["task"]) for r in chosen}
    if len(dtypes) != 1:
        raise WatcherRowsError(f"the records were scored in different dtypes: {sorted(dtypes)}")
    revs = {r.get("model_revision") for r in chosen}
    if len(revs) != 1:
        raise WatcherRowsError(f"the records belong to different checkpoints: {sorted(map(str, revs))}")
    records = []
    for r in chosen:
        out = {k: r[k] for k in KEEP if k in r}
        out["value"] = _points(r, "value", allow_none=False)
        out["stderr"] = _points(r, "stderr", allow_none=True)
        records.append(out)
    rev = next(iter(revs))
    return {"eval_mini": {
        "returncode": 0, "dtype": next(iter(dtypes)), "records": records,
        "source": {"schema_version": SCHEMA, "file": source, "model_revision": rev,
                   "checkpoint": chosen[0].get("checkpoint"), "values": "points divided by 100"}}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--watcher-doc", required=True, type=Path, help="Team 9's eval_mini_v1 JSON (points)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--report", type=Path, help="an evaluate.py report to merge the block into (written to --out)")
    ap.add_argument("--tasks", default=",".join(DEFAULT_TASKS))
    a = ap.parse_args(argv)
    try:
        raw = a.watcher_doc.read_bytes()
        block = convert(json.loads(raw), tuple(t for t in a.tasks.split(",") if t),
                        source=f"{a.watcher_doc.name} sha256 {hashlib.sha256(raw).hexdigest()[:16]}")
        out = block
        if a.report:
            rep = json.loads(a.report.read_text(encoding="utf-8"))
            if "eval_mini" in rep and rep["eval_mini"] != block["eval_mini"]:
                raise WatcherRowsError(f"{a.report} already holds a different eval_mini block")
            out = {**rep, **block}
            comp = rep.get("compute_dtype")
            if comp is not None and _dtype(comp, "report compute_dtype") != block["eval_mini"]["dtype"]:
                raise WatcherRowsError(
                    f"the benchmark rows were scored in {block['eval_mini']['dtype']} but the report's bits per byte in "
                    f"{_dtype(comp, 'report compute_dtype')}; score both in the same dtype")
    except (WatcherRowsError, OSError, json.JSONDecodeError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    a.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    m = block["eval_mini"]
    print(f"wrote {a.out}: {len(m['records'])} tasks, dtype {m['dtype']}, model_revision {m['source']['model_revision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
