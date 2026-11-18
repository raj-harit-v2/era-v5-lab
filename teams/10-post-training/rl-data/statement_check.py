"""Flag stdio tasks whose statement has no problem description (only a title, or only an example).

    python statement_check.py <tasks.jsonl> [--min-chars 40] [--ids-out flagged_ids.txt]

A task record passes the builder as soon as its source `description` is non-empty. Some source rows hold nothing but
"Example / Input / Output" blocks, so the prompt does not say what to compute: every rollout fails and the group is
dropped. This check measures the text before the first Example/Input/Sample heading; fewer than `--min-chars`
characters there is flagged. It is a screen for a human to confirm, not an admission ruling, and it changes no file.
Prints counts per judge; the flagged ids go to --ids-out (keep that file out of the repository).
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

HEADING = re.compile(r"\n\s*(examples?|sample\s+input|input)\b", re.IGNORECASE)


def description_chars(statement: str) -> int:
    """Characters of the statement before its first Example / Sample Input / Input heading."""
    text = statement.strip()
    if re.match(r"\s*(examples?|sample\s+input|input)\b", text, re.IGNORECASE):
        return 0
    return len(HEADING.split(text, maxsplit=1)[0].strip())


def has_description(statement: str, min_chars: int = 40) -> bool:
    return description_chars(statement) >= min_chars


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks", type=Path)
    ap.add_argument("--min-chars", type=int, default=40)
    ap.add_argument("--ids-out", type=Path)
    a = ap.parse_args(argv)
    per = collections.defaultdict(lambda: [0, 0])
    flagged = []
    with open(a.tasks, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            t = json.loads(line)
            per[t.get("judge", "unknown")][0] += 1
            if not has_description(t["statement"], a.min_chars):
                per[t.get("judge", "unknown")][1] += 1
                flagged.append(t["id"])
    if a.ids_out:
        a.ids_out.write_text("".join(i + "\n" for i in flagged), encoding="utf-8")
    print(json.dumps({"tasks": sum(v[0] for v in per.values()), "flagged": len(flagged), "min_chars": a.min_chars,
                      "by_judge": {k: {"tasks": v[0], "flagged": v[1]} for k, v in sorted(per.items())}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
