r"""math/<task_id> -- exact-answer math verifier (no container).

The answer is read only from <answer>...</answer> in the last MAX_SCAN_CHARS
of the visible reply. Common LaTeX wrappers are unwrapped first:

    \boxed{5}   $5$   $$5$$   \(5\)   \[5\]

Numbers compare as exact fractions, so all of these are equal:

    1/2    \frac{1}{2}    \dfrac12    \tfrac{1}{2}    0.5

Unicode minus (U+2212) and edge punctuation are normalised. Two different
answers score 0, so a policy cannot hedge.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks"

MAX_SCAN_CHARS = 20_000
MAX_ANSWER_CHARS = 200
ELIGIBILITY = ("eval", "train")

_STRIP = {0x200B: None, 0xFEFF: None}
_GLYPHS = {"½": "1/2", "¼": "1/4", "¾": "3/4", "⅓": "1/3", "⅔": "2/3"}
_EDGE = " .,;:!?\"'()[]{}\u0964\u0965\u201c\u201d\u2018\u2019"
_ANSWER = re.compile(r"<answer>(.*?)</answer>", re.DOTALL)
_WS = re.compile(r"\s+")
_DOLLAR = re.compile(r"^\$+\s*|\s*\$+$")
_PAREN = re.compile(r"^\\\(\s*|\s*\\\)$")
_BRACK = re.compile(r"^\\\[\s*|\s*\\\]$")
_BOXED = re.compile(r"\\(?:boxed|text|mathrm)\s*\{([^{}]*)\}")
_FRAC = re.compile(r"\\(?:d|t)?frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}")
_FRAC_SHORT = re.compile(r"\\(?:d|t)?frac\s*(\d)\s*(\d)")
_NUMBER = re.compile(r"^[-\u2212]?(?:\d+(?:\.\d+)?|\d+\s*/\s*\d+)$")


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text.casefold())
    text = text.translate(_STRIP)
    for glyph, repl in _GLYPHS.items():
        text = text.replace(glyph, repl)
    text = _WS.sub(" ", text)
    return text.strip(_EDGE)


def visible_reply(completion: str) -> str | None:
    return completion[-MAX_SCAN_CHARS:] if completion else None


def _unwrap(raw: str) -> str:
    s = raw.strip()
    for _ in range(4):
        before = s
        s = _BOXED.sub(r"\1", s)
        s = _DOLLAR.sub("", s)
        s = _PAREN.sub("", s)
        s = _BRACK.sub("", s)
        s = s.strip()
        if s == before:
            break
    return s


def _fracs_to_slash(s: str) -> str:
    prev = None
    while prev != s:
        prev = s
        s = _FRAC.sub(r"(\1)/(\2)", s)
        s = _FRAC_SHORT.sub(r"\1/\2", s)
    return s


_LATEX_SCRUB = re.compile(r"\\[()\[\]]|\$|\\boxed|\\text|\\mathrm|\{|\}")
_MIXED = re.compile(r"\d\s*\(?\s*-?\d+\s*/\s*\d+\s*\)?")


class _FracParser:
    """Recursive-descent evaluator: int, '/', parentheses, leading sign."""

    def __init__(self, text: str) -> None:
        self.s = text
        self.i = 0

    def _skip(self) -> None:
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def parse(self):
        v = self._expr()
        self._skip()
        return v if self.i == len(self.s) else None

    def _expr(self):
        self._skip()
        sign = 1
        while self.i < len(self.s) and self.s[self.i] in "+-":
            if self.s[self.i] == "-":
                sign = -sign
            self.i += 1
        num = self._atom()
        if num is None:
            return None
        self._skip()
        if self.i < len(self.s) and self.s[self.i] == "/":
            self.i += 1
            den = self._expr()
            if den is None or den == 0:
                return None
            return sign * num / den
        return sign * num

    def _atom(self):
        self._skip()
        if self.i < len(self.s) and self.s[self.i] == "(":
            self.i += 1
            v = self._expr()
            self._skip()
            if self.i < len(self.s) and self.s[self.i] == ")":
                self.i += 1
                return v
            return None
        start = self.i
        if self.i < len(self.s) and self.s[self.i] in "+-":
            self.i += 1
        digits = False
        while self.i < len(self.s) and self.s[self.i].isdigit():
            digits = True
            self.i += 1
        if self.i < len(self.s) and self.s[self.i] == ".":
            self.i += 1
            while self.i < len(self.s) and self.s[self.i].isdigit():
                digits = True
                self.i += 1
        if not digits:
            return None
        try:
            return Fraction(self.s[start:self.i])
        except (ValueError, ZeroDivisionError):
            return None


def _eval_frac(s: str):
    return _FracParser(s).parse()


def parse_number(s: str) -> Fraction | None:
    s = _unwrap(s)
    if _MIXED.search(s):
        return None
    s = _fracs_to_slash(s)
    if "frac" in s:
        return None
    s = _LATEX_SCRUB.sub("", s)
    s = s.replace("\u2212", "-").replace(",", "")
    # Evaluate paren-wrapped fractions BEFORE edge-stripping, because
    # normalise()'s _EDGE strip removes leading "(" / trailing ")".
    stripped = s.strip()
    if stripped:
        frac = _eval_frac(stripped)
        if frac is not None:
            return frac
    s = normalise(s)
    if not s:
        return None
    if not _NUMBER.match(s):
        return None
    try:
        return Fraction(s)
    except (ValueError, ZeroDivisionError):
        return None


def extract_answers(completion: str) -> tuple[set[str] | None, str]:
    vis = visible_reply(completion)
    if vis is None:
        return None, "empty completion"
    found = _ANSWER.findall(vis)
    if not found:
        return None, "no <answer> tag in the reply"
    raw = {a.strip() for a in found}
    if any(len(a) > MAX_ANSWER_CHARS for a in raw):
        return None, "answer longer than MAX_ANSWER_CHARS"
    return raw, ""


def prepare(meta: dict, accepted: list, wrong: list) -> dict:
    kind = meta.get("answer_type", "number")
    if kind == "number":
        acc = {f for f in (parse_number(str(a)) for a in accepted) if f is not None}
        bad = {f for f in (parse_number(str(a)) for a in wrong) if f is not None}
    else:
        acc = {normalise(str(a)) for a in accepted}
        bad = {normalise(str(a)) for a in wrong}
    return {"meta": meta, "kind": kind, "accepted": acc, "wrong": bad}


def load_task(task_dir: Path | str) -> dict:
    d = Path(task_dir)
    meta = json.loads((d / "task.json").read_text(encoding="utf-8"))
    ans = json.loads((d / "answer.json").read_text(encoding="utf-8"))
    return prepare(meta, ans.get("accepted", []), ans.get("wrong", []))


def score(task: dict, completion: str) -> dict:
    raw, reason = extract_answers(completion)
    if raw is None:
        return {"reward": 0, "reason": reason}
    kind = task["kind"]
    if kind == "number":
        vals = {f for f in (parse_number(a) for a in raw) if f is not None}
        if not vals:
            return {"reward": 0, "reason": "no parseable number in the answer"}
    else:
        vals = {normalise(a) for a in raw}
    if len(vals) != 1:
        return {"reward": 0, "reason": "more than one distinct answer"}
    v = next(iter(vals))
    if v in task["accepted"]:
        return {"reward": 1, "reason": "exact match"}
    if v in task["wrong"]:
        return {"reward": 0, "reason": "known wrong answer"}
    return {"reward": 0, "reason": "not an accepted answer"}


def reward(task_dir: Path | str, completion: str) -> dict:
    return score(load_task(task_dir), completion)


def wrap(answer) -> str:
    return f"<answer>{answer}</answer>"


def known_outputs(task_dir: Path | str) -> tuple[str, str]:
    t = load_task(task_dir)
    good = sorted(t["accepted"], key=str)[0]
    bad = sorted(t["wrong"], key=str)[0]
    return wrap(good), wrap(bad)


def check_task(task_dir: Path | str) -> list[str]:
    d = Path(task_dir)
    problems: list[str] = []
    for name in ("task.json", "answer.json", "prompt.md"):
        if not (d / name).is_file():
            problems.append(f"missing {name}")
    if problems:
        return problems
    meta = json.loads((d / "task.json").read_text(encoding="utf-8"))
    ans = json.loads((d / "answer.json").read_text(encoding="utf-8"))
    for key in ("id", "title", "answer_type", "source", "author", "eligibility"):
        if not meta.get(key):
            problems.append(f"task.json missing {key}")
    if meta.get("eligibility") not in ELIGIBILITY:
        problems.append(f"eligibility must be one of {ELIGIBILITY}")
    if meta.get("answer_type") not in ("number", "text"):
        problems.append("answer_type must be number or text")
    if not ans.get("accepted"):
        problems.append("answer.json has no accepted answers")
    if not ans.get("wrong"):
        problems.append("answer.json has no wrong answers")
    task = prepare(meta, ans.get("accepted", []), ans.get("wrong", []))
    if not task["accepted"]:
        problems.append("no accepted answer parses")
    if not task["wrong"]:
        problems.append("no wrong answer parses")
    for v in ans.get("accepted", []):
        r = score(task, wrap(v))
        if r["reward"] != 1:
            problems.append(
                f"accepted variant {v!r} scores {r['reward']}, "
                f"expected 1 ({r['reason']})"
            )
    good, bad = known_outputs(d)
    if score(task, good)["reward"] != 1:
        problems.append("accepted answer does not score 1")
    if score(task, bad)["reward"] != 0:
        problems.append("wrong answer does not score 0")
    prompt = (d / "prompt.md").read_text(encoding="utf-8")
    for a in ans.get("accepted", []):
        if str(a) in prompt:
            problems.append(f"accepted answer {a!r} appears in the prompt")
    return problems


def check_all(tasks_dir: Path = TASKS) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in sorted(Path(tasks_dir).glob("*/task.json")):
        out[p.parent.name] = check_task(p.parent)
    return out


def bench(n: int = 200_000, tasks_dir: Path = TASKS) -> dict:
    import time
    tasks = [load_task(p.parent) for p in sorted(Path(tasks_dir).glob("*/task.json"))]
    if not tasks:
        return {"rewards": 0, "per_second": 0}
    good = [known_outputs(p.parent)[0] for p in sorted(Path(tasks_dir).glob("*/task.json"))]
    t0 = time.perf_counter()
    rewards = 0
    for i in range(n):
        t = tasks[i % len(tasks)]
        c = good[i % len(good)]
        rewards += score(t, c)["reward"]
    dt = time.perf_counter() - t0
    return {"rewards": rewards, "per_second": round(n / dt) if dt else 0}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="math verifier")
    ap.add_argument("--reward", nargs=2, metavar=("TASK_DIR", "COMPLETION"))
    ap.add_argument("--check-task", metavar="TASK_DIR")
    ap.add_argument("--check-all", action="store_true")
    ap.add_argument("--bench", action="store_true")
    ap.add_argument("--n", type=int, default=200_000)
    args = ap.parse_args(argv)

    if args.reward:
        task_dir, comp = args.reward
        if not (Path(task_dir) / "task.json").is_file():
            print(f"task folder not found: {task_dir}", file=sys.stderr)
            return 2
        if not Path(comp).is_file():
            print(f"completion not found: {comp}", file=sys.stderr)
            return 2
        print(json.dumps(reward(task_dir, Path(comp).read_text(encoding="utf-8")), ensure_ascii=False))
        return 0
    if args.check_task:
        if not (Path(args.check_task) / "task.json").is_file():
            print(f"task folder not found: {args.check_task}", file=sys.stderr)
            return 2
        problems = check_task(args.check_task)
        print("\n".join(problems) if problems else "task OK")
        return 1 if problems else 0
    if args.check_all:
        results = check_all()
        for name, problems in results.items():
            print(f"{name}: {'; '.join(problems) if problems else 'OK'}")
        return 1 if any(results.values()) else 0
    if args.bench:
        print(json.dumps(bench(args.n)))
        return 0
    ap.error("give --reward, --check-task, --check-all or --bench")
    return 2


if __name__ == "__main__":
    sys.exit(main())
