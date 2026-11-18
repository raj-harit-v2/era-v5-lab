"""Indic RL items from templates written by people: fill the parameters, compute the answer, check every item.

TSAI's data rule (3 Nov): RL training text is written by people, never by a model (Claude included). So the
template text in templates/indic_templates.yaml is written by a person on the team and checked by a Team 2 reader.
This file has only the mechanics: draw the parameters, compute the accepted and wrong answers from the template's
expressions, and keep an item only if indic_verifier scores its answer 1 and every wrong answer 0, and its prompt
does not give the answer away.

Template file (YAML, a list). Every field below is written by a person:

    - id: hi_mango_left                # A-Z a-z 0-9 _ . -, unique, starts with the language code
      author: <GitHub handle>          # who wrote this template
      team2_reviewer: <GitHub handle>  # the Team 2 reader who checked the wording and the answers ("" until then)
      eligibility: train               # train (needs a team2_reviewer who is not the author) or eval
      language: hi                     # ISO 639-1
      script: Deva                     # ISO 15924, one of indic_verifier.SCRIPTS
      answer_type: integer             # integer, text or choice
      difficulty: easy                 # easy, medium or hard
      prompt: |                        # {name} placeholders only; it must ask for <answer>...</answer>
        {person} के पास {a} आम थे। ...
      params:                          # drawn for every item
        a: {int: [20, 90]}             # an integer in [low, high]
        person: {pick: [सीमा, रवि]}     # one of the listed values
      lists:                           # optional named constant lists
        days: [सोमवार, मंगलवार]
      derive:                          # optional, evaluated in order; usable in the prompt and in expressions
        left: a - b
      require: [a > b]                 # optional; a draw is repeated until every condition holds
      answer: left                     # expression: the accepted answer
      also_accept: []                  # optional expressions: other accepted forms (for example spellings)
      wrong: [a + b]                   # expressions: plausible wrong answers; each must score 0
      choices: [क, ख, ग, घ]            # choice tasks only
      answer_in_prompt: false          # true only when the answer is a span of the prompt

Expressions are a small part of Python: integers, strings, the names above, + - * // %, comparisons, and, or, not,
`x if c else y`, indexing, and the functions min, max, abs, len and digits(n, script) (n written in that script's
digits). Anything else (attributes, imports, other calls, keywords, **) is rejected when the template is read, and a
placeholder must be a plain name, so a template cannot run code. * works on integers only, with the product at most
10**30, and no computed value is longer than 10,000 characters, so a template cannot use up memory either.

    python generate.py --templates templates/indic_templates.yaml --check                 # lint the templates
    python generate.py --templates templates/indic_templates.yaml --per-template 200 --seed 1234 --out out/indic_items.jsonl

The output goes to out/, which is never committed. One JSON line per item: id, prompt, accepted, wrong, answer_type,
script, language, template, author, team2_reviewer, eligibility, source, licence, generator. The trainer scores an
item with indic_verifier.score(indic_verifier.prepare(item, item["accepted"]), completion). The decontamination check
runs Team 9's decontam_check.py on the same file with --id-field id --text-field prompt.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import random
import re
import string
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("g10_indic_verifier_for_generate", HERE / "indic_verifier.py")
iv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(iv)

REQUIRED = ("id", "author", "eligibility", "language", "script", "answer_type", "difficulty", "prompt", "params",
            "answer", "wrong")
MAX_DRAWS_PER_ITEM = 50
MAX_MISSES_IN_A_ROW = 5_000
MAX_CONSTANT = 10**12
MAX_PRODUCT = 10**30
MAX_VALUE_CHARS = 10_000
_HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


def digits(n: int, script: str) -> str:
    """n written with the decimal digits of script (ASCII for Latn)."""
    shift = iv.DIGIT_ZERO[script] - 0x30
    return "".join(chr(ord(c) + shift) if c.isdigit() else c for c in str(n))


def _mul(a, b):
    if type(a) is not int or type(b) is not int:
        raise ValueError("* is only for integers")
    if abs(a * b) > MAX_PRODUCT:
        raise ValueError("product too large")
    return a * b


class _MulToCall(ast.NodeTransformer):
    def visit_BinOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Mult):
            return ast.copy_location(ast.Call(ast.Name("_mul", ast.Load()), [node.left, node.right], []), node)
        return node


FUNCS = {"min": min, "max": max, "abs": abs, "len": len, "digits": digits}
_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.Subscript, ast.Name,
          ast.Load, ast.Constant, ast.Call, ast.List, ast.Tuple, ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod,
          ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)


def compile_expr(text, names: set[str]):
    """Compiled code for a safe expression over names, or ValueError."""
    tree = ast.parse(str(text), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _NODES):
            raise ValueError(f"{type(node).__name__} is not allowed in {text!r}")
        if isinstance(node, ast.Name) and node.id not in names and node.id not in FUNCS:
            raise ValueError(f"unknown name {node.id!r} in {text!r}")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in FUNCS):
            raise ValueError(f"only min, max, abs, len and digits may be called: {text!r}")
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and abs(node.value) > MAX_CONSTANT:
            raise ValueError(f"constant too large in {text!r}")
    tree = ast.fix_missing_locations(_MulToCall().visit(tree))
    return compile(tree, "<template>", "eval")


def _run(code, ns: dict):
    try:
        value = eval(code, {"__builtins__": {}, "_mul": _mul, **FUNCS}, ns)  # noqa: S307  (AST checked by compile_expr)
    except TypeError as e:
        raise ValueError(str(e)) from None
    if isinstance(value, (str, list, tuple)) and len(value) > MAX_VALUE_CHARS:
        raise ValueError(f"a value is longer than {MAX_VALUE_CHARS}")
    return value


def _fields(prompt: str) -> list[str]:
    return [f for _, f, _, _ in string.Formatter().parse(prompt) if f is not None]


# --- templates ---------------------------------------------------------------------------------

def check_template(tpl: dict) -> list[str]:
    """Problems with one template (empty list = fine). Compiles every expression, but draws nothing."""
    if not isinstance(tpl, dict):
        return ["a template must be a mapping"]
    problems = [f"missing {k}" for k in REQUIRED if k not in tpl]
    if problems:
        return problems
    if not iv._NAME.match(str(tpl["id"])):
        problems.append("id may only have A-Z a-z 0-9 _ . -")
    if tpl["script"] not in iv.SCRIPTS:
        problems.append(f"script must be one of {sorted(iv.SCRIPTS)}")
    if tpl["answer_type"] not in iv.TYPES:
        problems.append(f"answer_type must be one of {iv.TYPES}")
    if tpl["difficulty"] not in iv.DIFFICULTIES:
        problems.append(f"difficulty must be one of {iv.DIFFICULTIES}")
    if tpl["eligibility"] not in iv.ELIGIBILITY:
        problems.append(f"eligibility must be one of {iv.ELIGIBILITY}")
    if not _HANDLE.match(str(tpl["author"])):
        problems.append("author must be a GitHub handle")
    reviewer = str(tpl.get("team2_reviewer") or "")
    if reviewer and not _HANDLE.match(reviewer):
        problems.append("team2_reviewer must be a GitHub handle")
    if tpl["eligibility"] == "train" and (not reviewer or reviewer == tpl["author"]):
        problems.append("a train template needs a team2_reviewer who is not the author")
    if "<answer>" not in str(tpl["prompt"]):
        problems.append("prompt must ask for the final answer in <answer>...</answer>")
    if tpl["answer_type"] == "choice" and not (isinstance(tpl.get("choices"), list) and len(set(tpl["choices"])) >= 2):
        problems.append("a choice template needs two or more distinct choices")
    if not isinstance(tpl["wrong"], list) or not tpl["wrong"]:
        problems.append("wrong must be a non-empty list of expressions")
    names: set[str] = set()
    params = tpl["params"] if isinstance(tpl["params"], dict) else {}
    if not params:
        problems.append("params must be a non-empty mapping")
    for name, spec in params.items():
        ok_int = (isinstance(spec, dict) and list(spec) == ["int"] and isinstance(spec["int"], list)
                  and len(spec["int"]) == 2 and all(type(x) is int for x in spec["int"]) and spec["int"][0] <= spec["int"][1])
        ok_pick = (isinstance(spec, dict) and list(spec) == ["pick"] and isinstance(spec["pick"], list) and spec["pick"])
        if not (ok_int or ok_pick):
            problems.append(f"param {name}: use {{int: [low, high]}} or {{pick: [values]}}")
        names.add(str(name))
    lists = tpl.get("lists") or {}
    if not isinstance(lists, dict) or not all(isinstance(v, list) and v for v in lists.values()):
        problems.append("lists must map names to non-empty lists")
        lists = {}
    names |= set(lists)
    try:
        derive = tpl.get("derive") or {}
        for name, expr in derive.items():
            compile_expr(expr, names)
            names.add(str(name))
        for expr in [*(tpl.get("require") or []), tpl["answer"], *(tpl.get("also_accept") or []), *tpl["wrong"]]:
            compile_expr(expr, names)
    except (SyntaxError, ValueError, AttributeError, TypeError) as e:
        problems.append(f"bad expression: {e}")
    for f in _fields(str(tpl["prompt"])):
        if not f.isidentifier():
            problems.append(f"placeholder {{{f}}} must be a plain name")
        elif f not in names:
            problems.append(f"placeholder {{{f}}} has no param, list or derived value")
    return problems


class Template:
    """A checked template with its expressions compiled once."""

    def __init__(self, tpl: dict):
        problems = check_template(tpl)
        if problems:
            raise ValueError(f"template {tpl.get('id') if isinstance(tpl, dict) else tpl!r}: {problems}")
        self.tpl = tpl
        names = set(tpl["params"]) | set(tpl.get("lists") or {})
        self.derive = []
        for name, expr in (tpl.get("derive") or {}).items():
            self.derive.append((name, compile_expr(expr, names)))
            names.add(name)
        self.require = [compile_expr(e, names) for e in tpl.get("require") or []]
        self.accepted = [compile_expr(e, names) for e in [tpl["answer"], *(tpl.get("also_accept") or [])]]
        self.wrong = [compile_expr(e, names) for e in tpl["wrong"]]
        self.meta = {"id": tpl["id"], "answer_type": tpl["answer_type"], "script": tpl["script"]}

    def draw(self, rng: random.Random) -> dict | None:
        """One item, or None when the draw breaks a condition or fails a check."""
        tpl = self.tpl
        ns = {k: (rng.randint(*v["int"]) if "int" in v else rng.choice(v["pick"])) for k, v in tpl["params"].items()}
        ns.update(tpl.get("lists") or {})
        try:
            for name, code in self.derive:
                ns[name] = _run(code, ns)
            if not all(_run(code, ns) for code in self.require):
                return None
            accepted = list(dict.fromkeys(_run(code, ns) for code in self.accepted))
            wrong = list(dict.fromkeys(_run(code, ns) for code in self.wrong))
        except ZeroDivisionError:
            return None
        kind = tpl["answer_type"]
        want = (lambda x: type(x) is int) if kind == "integer" else (lambda x: isinstance(x, str))
        if not all(want(x) for x in accepted + wrong):
            raise ValueError(f"template {tpl['id']}: an answer is not {'an int' if kind == 'integer' else 'a string'}")
        norm = (lambda x: x) if kind == "integer" else iv.normalise
        if {norm(a) for a in accepted} & {norm(w) for w in wrong}:
            return None  # this draw makes a wrong answer equal to the right one
        prompt = tpl["prompt"].format_map(ns)
        if iv.answer_in_prompt(prompt, kind, accepted, bool(tpl.get("answer_in_prompt"))):
            return None
        task = iv.prepare(self.meta, accepted)
        if any(iv.score(task, iv.wrap(a))["reward"] != 1 for a in accepted):
            return None
        if any(iv.score(task, iv.wrap(w))["reward"] != 0 for w in wrong):
            return None
        return {"prompt": prompt, "accepted": accepted, "wrong": wrong}

    def generate(self, n: int, seed: int) -> list[dict]:
        """n items with distinct prompts. Same seed, same items, whatever the other templates are."""
        tpl, rng = self.tpl, random.Random(f"{seed}:{self.tpl['id']}")
        items, seen, draws, misses = [], set(), 0, 0
        while len(items) < n:
            if draws >= n * MAX_DRAWS_PER_ITEM or misses >= MAX_MISSES_IN_A_ROW:
                raise ValueError(f"template {tpl['id']}: {len(items)} of {n} items after {draws} draws (conditions too "
                                 "strict, or too few distinct prompts)")
            draws += 1
            item = self.draw(rng)
            if item is None or item["prompt"] in seen:
                misses += 1
                continue
            misses = 0
            seen.add(item["prompt"])
            reviewer = tpl.get("team2_reviewer") or ""
            items.append({"id": f"{tpl['id']}-{len(items):05d}", **item, "answer_type": tpl["answer_type"],
                          "script": tpl["script"], "language": tpl["language"], "difficulty": tpl["difficulty"],
                          "template": tpl["id"], "author": tpl["author"], "team2_reviewer": reviewer,
                          "eligibility": tpl["eligibility"],
                          "source": f"original: template {tpl['id']} written by {tpl['author']}; Team 2 reviewer "
                                    f"{reviewer or 'none yet'}",
                          "licence": "team-written",
                          "generator": "none (person-written template; answers computed from its expressions and "
                                       "checked by indic_verifier)"})
        return items


def load_templates(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ValueError(f"{path}: the template file must be a YAML list")
    return data


def check_file(templates: list[dict], sample: int = 5, seed: int = 1234) -> dict[str, list[str]]:
    """Problems per template id, including a small trial generation and repeated ids."""
    out: dict[str, list[str]] = {}
    for i, tpl in enumerate(templates):
        key = str(tpl.get("id", f"#{i}")) if isinstance(tpl, dict) else f"#{i}"
        problems = (["id repeats an earlier template"] if key in out else []) + check_template(tpl)
        if not problems:
            try:
                Template(tpl).generate(sample, seed)
            except ValueError as e:
                problems.append(str(e))
        out[key if key not in out else f"{key}#{i}"] = problems
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--templates", type=Path, required=True)
    ap.add_argument("--per-template", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--check", action="store_true", help="lint the templates and try a few items; write nothing")
    args = ap.parse_args(argv)
    templates = load_templates(args.templates)
    if not templates:
        print("no templates yet: a person on the team writes them (see the docstring and the template file)")
        return 1
    results = check_file(templates, seed=args.seed)
    bad = {k: v for k, v in results.items() if v}
    if args.check or bad:
        for name, problems in results.items():
            print(f"{name}: {'; '.join(problems) if problems else 'OK'}")
        return 1 if bad else 0
    if not args.out:
        ap.error("give --out (or --check)")
    t0 = time.perf_counter()
    items = [it for tpl in templates for it in Template(tpl).generate(args.per_template, args.seed)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items), encoding="utf-8")
    print(json.dumps({"templates": len(templates), "items": len(items),
                      "train_items": sum(it["eligibility"] == "train" for it in items),
                      "seconds": round(time.perf_counter() - t0, 3), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
