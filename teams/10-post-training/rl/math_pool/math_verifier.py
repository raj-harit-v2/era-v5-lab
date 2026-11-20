"""Binary reward for math tasks: an exact check of one boxed final answer. No candidate code is run.

    reward(task_dir, completion, pool=None) -> {"reward": 0 | 1, "reason": str, "task_id": str}

A task folder `rl/math_pool/tasks/<task_id>/task.json` holds only the id of one record of the RL data v1 math pool
(`rl-data/build_math.py`: hendrycks MATH train split, MIT, human-written, decontaminated) and two SHA-256 pins, one of the
problem and one of the answer. The problem text and the reference answer stay in the pool, which is data and stays out of
the repository. `pool` is the pool JSONL (default: the environment variable G10_MATH_POOL). A missing pool, a missing
record or a pin that does not match raises RuntimeError: it is never scored 0, because a 0 looks like a real failure.

Whether MATH may be used for RL training is TSAI's ruling, not made yet (see README.md).

What counts as the answer (stricter than rl-data/math_check.score, which also reads a bare last expression):
  * only the visible reply is read: everything up to the last `<|/think|>` is ignored, an unclosed `<|think|>` has no
    answer, and only the last MAX_SCAN_CHARS characters are read;
  * the answer must be in \\boxed{...}. A correct number written in prose scores 0, so "4 maybe 5, the answer is 5"
    cannot score;
  * every \\boxed{...} in the reply must hold the same answer (after whitespace removal). Two different boxed answers
    score 0, so a policy cannot list candidates; the same answer repeated is fine;
  * a boxed answer longer than MAX_ANSWER_CHARS scores 0;
  * the boxed content alone is compared with the reference by math-verify (Apache-2.0, pinned 0.9.0) through
    math_check.score, so \\frac12, 0.5 and \\frac{1}{2} agree. Units and "x=" are ignored by math-verify, a list
    that merely contains the right number, or an ordered pair in the other order, does not match.

CLI:
    python math_verifier.py --reward <task_dir> <completion.txt> --pool POOL.jsonl
    python math_verifier.py --check-task <task_dir> --pool POOL.jsonl   # pins match, reference scores 1, a wrong one 0
    python math_verifier.py --check-all --pool POOL.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"
RL_DATA = HERE.parent.parent / "rl-data"
MAX_SCAN_CHARS = 20_000
MAX_ANSWER_CHARS = 200
THINK_START, THINK_END = "<|think|>", "<|/think|>"
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_WS = re.compile(r"\s+")

_CHECK = None


def math_check():
    """rl-data/math_check.py, loaded by path (it imports math_verify lazily, so listing tasks needs no dependency)."""
    global _CHECK
    if _CHECK is None:
        spec = importlib.util.spec_from_file_location("g10_math_check", RL_DATA / "math_check.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CHECK = module
    return _CHECK


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- the pool ----------------------------------------------------------------------------------

def pool_path(pool=None) -> Path:
    p = pool or os.environ.get("G10_MATH_POOL")
    if not p:
        raise RuntimeError("math pool missing: pass pool=... or set G10_MATH_POOL to the RL data v1 math.jsonl")
    return Path(p)


def load_record(meta: dict, pool=None) -> dict:
    """The pool record of a task, with both pins checked."""
    path = pool_path(pool)
    if not path.is_file():
        raise RuntimeError(f"math pool not found: {path}")
    with path.open(encoding="utf-8") as f:
        for line in f:
            if f'"{meta["pool_id"]}"' not in line:
                continue
            row = json.loads(line)
            if row.get("id") != meta["pool_id"]:
                continue
            if sha256(row["problem"]) != meta["problem_sha256"] or sha256(row["answer"]) != meta["answer_sha256"]:
                raise RuntimeError(f"math pool record {meta['pool_id']} does not match the task's pins")
            return row
    raise RuntimeError(f"record {meta['pool_id']} not in math pool {path}")


# --- reading the reply -------------------------------------------------------------------------

def visible_reply(completion: str) -> str | None:
    text = completion or ""
    end = text.rfind(THINK_END)
    if end >= 0:
        text = text[end + len(THINK_END):]
    if THINK_START in text:
        return None
    return text[-MAX_SCAN_CHARS:]


def all_boxed(text: str) -> list[str]:
    """Contents of every \\boxed{...} / \\fbox{...}, in order, with nested braces handled."""
    out, pos = [], 0
    check = math_check()
    while True:
        starts = [i for i in (text.find(b, pos) for b in check.BOXED) if i >= 0]
        if not starts:
            return out
        i = min(starts)
        end = _box_end(text, i)
        content = check.last_boxed(text[i:end])  # the chunk holds exactly this one box
        if content is not None:
            out.append(content)
        pos = max(end, i + 1)


def _box_end(text: str, i: int) -> int:
    j = i + (len("\\boxed") if text.startswith("\\boxed", i) else len("\\fbox"))
    if j < len(text) and text[j] == " ":
        k = j + 1
        while k < len(text) and not text[k].isspace() and text[k] != "$":
            k += 1
        return k
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return k + 1
    return len(text)


def extract_answer(completion: str) -> tuple[str | None, str]:
    """(the one boxed answer, "ok") or (None, reason)."""
    reply = visible_reply(completion)
    if reply is None:
        return None, "think span not closed"
    boxes = all_boxed(reply)
    if not boxes:
        return None, "no boxed answer"
    answers = {_WS.sub("", b) for b in boxes}
    if "" in answers:
        return None, "empty boxed answer"
    if len(answers) > 1:
        return None, "several different boxed answers"
    if any(len(b) > MAX_ANSWER_CHARS for b in boxes):
        return None, "boxed answer too long"
    return boxes[-1], "ok"


# --- scoring -----------------------------------------------------------------------------------

def reward(task_dir: Path, completion: str, pool=None) -> dict:
    meta = json.loads((Path(task_dir) / "task.json").read_text(encoding="utf-8"))
    record = load_record(meta, pool)
    out = {"task_id": meta["id"], "reward": 0}
    answer, why = extract_answer(completion)
    if answer is None:
        return {**out, "reason": why}
    scored = math_check().score({"id": meta["id"], "answer": record["answer"]}, "$\\boxed{" + answer + "}$")
    return {**out, "reward": scored["reward"], "reason": scored["reason"]}


def known_outputs(task_dir: Path, pool=None) -> tuple[str, str]:
    """(an output that must score 1, an output that must score 0). Needs the pool for the reference answer."""
    meta = json.loads((Path(task_dir) / "task.json").read_text(encoding="utf-8"))
    ref = load_record(meta, pool)["answer"]
    wrong = "424242" if ref.strip() != "424242" else "737373"
    return f"The final answer is $\\boxed{{{ref}}}$.", f"The final answer is $\\boxed{{{wrong}}}$."


def check_task(task_dir: Path, pool=None) -> dict:
    task_dir = Path(task_dir)
    meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    if not _NAME.match(meta.get("id", "")) or meta["id"] != task_dir.name:
        problems.append("id must equal the folder name")
    record = load_record(meta, pool)  # raises on a missing or mismatching record
    if record.get("licence") != "MIT" or "none" not in str(record.get("generator", "")):
        problems.append("record must be MIT-licensed with generator none")
    good, bad = known_outputs(task_dir, pool)
    if reward(task_dir, good, pool)["reward"] != 1:
        problems.append("the reference answer does not score 1")
    if reward(task_dir, bad, pool)["reward"] != 0:
        problems.append("the wrong answer does not score 0")
    return {"task_id": meta["id"], "ok": not problems, "problems": problems}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reward", nargs=2, metavar=("TASK_DIR", "COMPLETION"))
    ap.add_argument("--check-task", metavar="TASK_DIR")
    ap.add_argument("--check-all", action="store_true")
    ap.add_argument("--pool")
    args = ap.parse_args(argv)
    if args.reward:
        print(json.dumps(reward(Path(args.reward[0]), Path(args.reward[1]).read_text(encoding="utf-8"), args.pool)))
        return 0
    if args.check_task:
        row = check_task(Path(args.check_task), args.pool)
        print(json.dumps(row))
        return 0 if row["ok"] else 1
    if args.check_all:
        rows = [check_task(p.parent, args.pool) for p in sorted(TASKS.glob("*/task.json"))]
        for r in rows:
            print(json.dumps(r))
        return 0 if rows and all(r["ok"] for r in rows) else 1
    ap.error("give --reward, --check-task or --check-all")
    return 2


if __name__ == "__main__":
    sys.exit(main())
