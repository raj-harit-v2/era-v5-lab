"""Contest-id check of a Codeforces pool against the Codeforces benchmark (G9, week 3).

decontam_check.py finds copied text. A problem that was reworded between the Div. 1 and the Div. 2 version of one
round shares no 13-word run with the benchmark item, but it sits in a contest whose id is next to the id of a
benchmark contest. This script lists the pool rows whose contest is a benchmark contest or lies within --window ids of
one. It reads ids only and prints ids and counts only: never problem text.

    python contest_id_check.py --benchmark <test-00000-of-00001.parquet> --pool rows.jsonl
    python contest_id_check.py --benchmark contests.json --pool rows.jsonl --id-field id --out report.json

--benchmark  the open-r1/codeforces test parquet (column contest_id; needs pyarrow), or a JSON list of contest ids.
--pool       JSONL. The contest id is the value of --contest-field, else the number before "/", "_", "-" or ":" in
             --id-field ("1990/A", "cf_1990_A"), else the number before a trailing problem letter ("1990A").
--window     contests this close to a benchmark contest are reported (default 3).
--drop       write the ids of the rows within --window to this file, one per line, so a data team can remove them.

Output (JSON): counts, and for every pool contest within the window its distance to the nearest benchmark contest and its
number of rows. Distance 0 is a benchmark contest, 1 is the next round (Div. 1 and Div. 2 of one round have
neighbouring ids). Rows with no readable contest id are counted, never dropped silently.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ID_FORMS = (re.compile(r"\D*?(\d{3,4})[/_\-:]"), re.compile(r"\D*?(\d{3,4})[A-Z]\d?$"))


def benchmark_contests(path: Path) -> list[int]:
    """The sorted contest ids of the benchmark: from the open-r1/codeforces test parquet or a JSON list."""
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq
        values = pq.read_table(path, columns=["contest_id"]).column("contest_id").to_pylist()
    else:
        values = json.loads(path.read_text(encoding="utf-8"))
    ids = sorted({int(v) for v in values})
    if not ids:
        raise SystemExit(f"{path}: no contest ids")
    return ids


def contest_of(row: dict, id_field: str = "id", contest_field: str = "contest_id") -> int | None:
    v = row.get(contest_field)
    if v is not None and str(v).strip().isdigit():
        return int(v)
    text = str(row.get(id_field, ""))
    for form in ID_FORMS:
        m = form.match(text)
        if m:
            return int(m.group(1))
    return None


def nearest(contest: int, bench: list[int]) -> int:
    return min(abs(contest - b) for b in bench)


def check(bench: list[int], rows: list[dict], id_field: str = "id", contest_field: str = "contest_id",
          window: int = 3) -> tuple[dict, list]:
    """The report and the ids of the rows within the window."""
    per_row = [(r.get(id_field, ""), contest_of(r, id_field, contest_field)) for r in rows]
    by_contest = collections.Counter(c for _, c in per_row if c is not None)
    distance = {c: nearest(c, bench) for c in by_contest}
    near = {c: d for c, d in distance.items() if d <= window}
    report = {
        "benchmark_contests": len(bench), "benchmark_range": [bench[0], bench[-1]], "window": window,
        "pool_rows": len(rows), "rows_without_contest_id": sum(1 for _, c in per_row if c is None),
        "pool_contests": len(by_contest),
        "rows_in_benchmark_contest": sum(n for c, n in by_contest.items() if distance[c] == 0),
        "rows_within_1": sum(n for c, n in by_contest.items() if distance[c] <= 1),
        "rows_within_window": sum(by_contest[c] for c in near),
        "contests_within_window": {str(c): {"distance": d, "rows": by_contest[c]} for c, d in sorted(near.items())},
    }
    drop = [i for i, c in per_row if c is not None and c in near]
    return report, drop


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--benchmark", type=Path, required=True)
    ap.add_argument("--pool", type=Path, required=True)
    ap.add_argument("--id-field", default="id")
    ap.add_argument("--contest-field", default="contest_id")
    ap.add_argument("--window", type=int, default=3)
    ap.add_argument("--out", type=Path, help="write the report here as well as to stdout")
    ap.add_argument("--drop", type=Path, help="write the ids of the rows within the window, one per line")
    a = ap.parse_args(argv)

    bench = benchmark_contests(a.benchmark)
    with a.pool.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    report, drop = check(bench, rows, a.id_field, a.contest_field, a.window)
    text = json.dumps(report, indent=1)
    print(text)
    if a.out:
        a.out.write_text(text + "\n", encoding="utf-8")
    if a.drop:
        a.drop.write_text("".join(f"{i}\n" for i in drop), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
