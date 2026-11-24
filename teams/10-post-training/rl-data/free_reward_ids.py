"""Free-reward audit of a stdio code pool from the kept tests alone (no program is run).

For every task, with the reward's own comparison (stdio_check.same_output: the same whitespace-separated tokens) over the
tests the reward scores (the first stdio_check.MAX_TESTS = 20):

  whole   best whole-output constant: the largest share of tests that ONE fixed output passes (the commonest expected
          token list). 1.0 means a program that ignores its input earns reward 1.
  per_case best per-case constant, for the tasks where it is defined: a trivial program that reads the first input token
          as an integer T and prints one fixed token T times. Defined only if, in EVERY scored test, the first input
          token is an integer T >= 1 and the expected output has exactly T tokens; the score is then the largest share of
          tests whose expected tokens are all the same token. Otherwise "n/a" (the case count or the per-case answer
          shape cannot be read without solving the task, so it is skipped).

A task is free-reward if whole == 1 (reason `constant-output`) or per_case == 1 (reason `per-case-constant`).

    python free_reward_ids.py --tasks cc.jsonl [--existing ../capstone/rl_exclusions_v1/free_reward_ids.txt]
                              [--report report.tsv] [--append-new]

--report writes `id<TAB>n_tests<TAB>whole<TAB>per_case` for every task (no task text). --append-new appends the new
free-reward ids (sorted, `id<TAB>reason`) to --existing, leaving every existing line unchanged.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

MAX_TESTS = 20  # = stdio_check.MAX_TESTS (the reward scores the first 20 kept tests); checked in test_free_reward_ids.py


def tokens(text: str) -> tuple[str, ...]:
    return tuple(str(text).split())  # stdio_check.same_output compares actual.split() == expected.split()


def whole_constant(tests: list[dict]) -> float:
    if not tests:
        return 0.0
    c = Counter(tokens(t["output"]) for t in tests)
    return max(c.values()) / len(tests)


def per_case_constant(tests: list[dict]) -> float | None:
    if not tests:
        return None
    single = Counter()
    for t in tests:
        first = str(t["input"]).split()[:1]
        try:
            n = int(first[0]) if first else -1
        except ValueError:
            return None
        exp = tokens(t["output"])
        if n < 1 or len(exp) != n:
            return None
        if len(set(exp)) == 1:
            single[exp[0]] += 1
    return max(single.values()) / len(tests) if single else 0.0


def audit(tasks: list[dict]) -> list[dict]:
    out = []
    for t in tasks:
        tests = list(t["tests"])[:MAX_TESTS]
        w, p = whole_constant(tests), per_case_constant(tests)
        reason = "constant-output" if w == 1.0 else ("per-case-constant" if p == 1.0 else None)
        out.append({"id": t["id"], "n_tests": len(tests), "whole": w, "per_case": p, "reason": reason})
    return out


def read_ids(path: Path) -> list[str]:
    """Same rule as capstone/rl_job_v1.read_ids: one id per line, a tab starts the reason column, # and blank skipped."""
    ids = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.append(line.split("\t")[0].split()[0])
    return ids


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--existing", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--append-new", action="store_true")
    a = ap.parse_args(argv)
    tasks = [json.loads(x) for x in a.tasks.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = audit(tasks)
    existing = read_ids(a.existing) if a.existing else []
    free = [r for r in rows if r["reason"]]
    new = sorted((r for r in free if r["id"] not in set(existing)), key=lambda r: r["id"])
    if a.report:
        a.report.write_text("".join(f"{r['id']}\t{r['n_tests']}\t{r['whole']:.4f}\t"
                                    f"{'n/a' if r['per_case'] is None else format(r['per_case'], '.4f')}\n" for r in rows))
    if a.append_new:
        if not a.existing:
            raise SystemExit("--append-new needs --existing")
        text = a.existing.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        a.existing.write_text(text + "".join(f"{r['id']}\t{r['reason']}\n" for r in new), encoding="utf-8")
    print(json.dumps({"tasks": len(rows), "free_reward": len(free),
                      "by_reason": dict(Counter(r["reason"] for r in free)),
                      "already_listed": len(free) - len(new), "new": len(new),
                      "whole_ge_0.5": sum(r["whole"] >= 0.5 for r in rows),
                      "per_case_defined": sum(r["per_case"] is not None for r in rows),
                      "per_case_ge_0.5": sum((r["per_case"] or 0) >= 0.5 for r in rows),
                      "existing_not_free_by_this_rule": len(set(existing) - {r["id"] for r in free})}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
