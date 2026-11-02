"""Write clean_english.py from ../medicine_english.md: the English cleaner on its own, one function per disease code.

  python -I build_clean_english.py

The same form as ../clean_english.py, which ../../tools/build_clean.py makes from the code and English sheets: each rule block goes into its own closure, so
helpers with the same name in two blocks do not clash; one function per disease code runs that code's rules in sheet
order; clean(doc) runs every rule in the sheet's order. Two differences, both on purpose:

  - F1 is the sheet's own DA-F1-005, the rule written to the instructor's F1 ruling of 31 Oct. The build stops if it is
    missing, not under F1 or not the last rule, and writes nothing. ../clean_english.py runs the same rule on English text.
  - An invisible character in a string literal (a format or control character, such as U+FEFF or U+200B) is written
    as a \\u escape, so a reviewer can see it. The value of every string is checked to be the same before and after.
"""
import ast
import hashlib
import io
import re
import sys
import textwrap
import tokenize
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHEET = HERE.parent / "sheets" / "medicine_english.md"
DEST = HERE / "clean_english.py"
FAMILY = "english"
MUST_KEEP = {"DA-F1-005"}  # written to the instructor's F1 ruling of 31 Oct: never left out
BLOCK = re.compile(r"^```python\n(.*?)^```[ \t]*$", re.S | re.M)  # a fence on its own line: a rule can hold ``` inside
HEADING = re.compile(r"^## \d+\. `(DA-[A-H]\d-\d{3})` · [A-H]\d (.+?) · ", re.M)


def invisible(c):
    return c not in "\n\t" and (unicodedata.category(c) in ("Cf", "Cc", "Zl", "Zp") or (unicodedata.category(c) == "Zs" and c != " "))


def escape_invisible(src, rid):
    """Write invisible characters in (non-raw) string literals as \\u escapes. Only those tokens change."""
    starts = [0]
    for line in src.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    edits, raw_left = [], []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        s = tok.string
        if tok.type != tokenize.STRING or not any(invisible(c) for c in s):
            continue
        prefix = s[:len(s) - len(s.lstrip("rRbBuU"))].lower()
        if "r" in prefix or "b" in prefix:
            raw_left.append(s[:40])
            continue
        new = "".join((f"\\u{ord(c):04x}" if ord(c) <= 0xFFFF else f"\\U{ord(c):08x}") if invisible(c) else c for c in s)
        edits.append((starts[tok.start[0] - 1] + tok.start[1], starts[tok.end[0] - 1] + tok.end[1], new))
    if raw_left:
        print(f"{rid}: invisible characters left as they are in raw strings: {raw_left}")
    for a, b, new in reversed(edits):
        src = src[:a] + new + src[b:]
    return src


def strings(src):
    return [n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def rules():
    text = SHEET.read_text(encoding="utf-8")
    names = dict(HEADING.findall(text))
    out = []
    for b in BLOCK.findall(text):
        b = textwrap.dedent(b)
        if 'RULE_ID = "' not in b:
            continue
        field = lambda k: re.search(rf'^{k} = "([^"]*)"', b, re.M).group(1)
        rid, code, status, stage = field("RULE_ID"), field("CODE"), field("STATUS"), field("STAGE")
        if status != "CANDIDATE":
            sys.exit(f"STOP: {rid} is {status} in {SHEET.name}; the sheet holds CANDIDATE rules only. Nothing was written.")
        src = b.rstrip()
        if any(invisible(c) for c in src):
            src = escape_invisible(src + "\n", rid).rstrip()
        if strings(src) != strings(b):
            sys.exit(f"STOP: escaping changed a string value of {rid}. Nothing was written.")
        out.append(dict(id=rid, code=code, stage=stage, disease=names.get(rid, ""), src=src,
                        author=field("AUTHOR"), name=f"_{FAMILY}_{rid[3:].lower().replace('-', '_')}"))
    return out


def factory(r):
    body = textwrap.indent(r["src"], "    ")
    text = (f'@cache\ndef {r["name"]}():\n    # {r["id"]} · {r["code"]} {r["disease"]} · stage {r["stage"]} · '
            f'{r["author"]} · {SHEET.name}\n{body}\n    return medicine\n')
    a, b = strings(r["src"]), strings(text)
    changed = [x for x, y in zip(a, b) if x != y]
    if len(a) != len(b) or changed:  # only a multi-line string can change when indented; a docstring does not matter
        docs = {ast.get_docstring(n, clean=False) for n in ast.walk(ast.parse(r["src"]))
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        if len(a) != len(b) or any(x not in docs for x in changed):
            sys.exit(f"STOP: indenting {r['id']} changed a string that is not a docstring: {[x[:40] for x in changed]}. "
                     "Nothing was written.")
        print(f"{r['id']}: indenting changed {len(changed)} docstring(s) only")
    return text


def main():
    rs = rules()
    ids = [r["id"] for r in rs]
    if len(ids) != len(set(ids)):
        sys.exit(f"STOP: a RULE_ID appears twice in {SHEET.name}. Nothing was written.")
    for rid in sorted(MUST_KEEP):
        r = next((r for r in rs if r["id"] == rid), None)
        if r is None or r["code"] != "F1":
            sys.exit(f"STOP: {rid} is written to an instructor's ruling and must never be left out, but {SHEET.name} "
                     f"{'has no such rule' if r is None else 'has it under ' + r['code']}. Nothing was written.")
    f1 = [r for r in rs if r["code"] == "F1"]
    if [r["id"] for r in f1] != sorted(MUST_KEEP) or rs[-1]["code"] != "F1":
        sys.exit(f"STOP: F1 must be {sorted(MUST_KEEP)} alone, run last; the sheet has {[r['id'] for r in f1]}. "
                 "Nothing was written.")
    codes = list(dict.fromkeys(r["code"] for r in rs))  # in the order each code first runs in the sheet
    disease = {r["code"]: r["disease"] for r in rs}
    out = ['"""Spec v1 cleaning, English family: one function per disease code, and clean(doc) to run every rule in the\n'
           "sheet's order. GENERATED by scripts/build_clean_english.py from ../medicine_english.md: change the sheet, not this file.\n"
           "The same rules run in ../clean_english.py, made by ../../tools/build_clean.py from the code and English sheets.\n\n"
           "doc is {doc_id, text, url, lang_label}. Each function returns (action, text), action being keep, fix or drop.\n"
           'Each rule keeps its own LANGS guard ({"en", "eng"}), so a doc of another language passes unchanged.\n'
           "F1 is DA-F1-005, written to the instructor's F1 ruling of 31 Oct (<PHONE>, <EMAIL>, <ADDRESS> for a private person).\n"
           "Each rule's code is the sheet's, unchanged; an invisible character in a string is written as a \\\\u escape.\n"
           '"""\n'
           "import re\nfrom functools import cache\n\n"
           f'SHEET_SHA256 = "{hashlib.sha256(SHEET.read_bytes()).hexdigest()}"  # medicine_english.md this file was built from\n\n\n']
    out += [factory(r) + "\n\n" for r in rs]
    out.append('''def _run(doc, *factories):
    """Run rules in order: a drop ends it, a fix passes the new text on."""
    d = dict(doc)
    for make in factories:
        action, text = make()(d)
        if action == "drop":
            return ("drop", doc["text"])
        d["text"] = text
    return ("fix" if d["text"] != doc["text"] else "keep", d["text"])
''')
    for code in codes:
        mine = [r for r in rs if r["code"] == code]
        out.append(f'\n\ndef {code.lower()}(doc):\n    """{code} {disease[code]}: {", ".join(r["id"] for r in mine)}."""\n'
                   f'    return _run(doc, {", ".join(r["name"] for r in mine)})\n')
    out.append("\n\nRULES = {" + ", ".join(f'"{c}": {c.lower()}' for c in codes) +
               "}  # disease code -> function, the form harm_test.py reads\n")
    out.append("# rule by rule, in the sheet's run order, which keeps the sheet exactly as it was tested\n_PIPELINES = {\n")
    out.append(f'    "{FAMILY}": (\n' + "".join(f"        {r['name']},  # {r['id']}\n" for r in rs) + "    ),\n}\n")
    out.append('_FAMILY = {"en": "english", "eng": "english"}\n')
    out.append('''

def clean(doc):
    """The whole English pipeline for one document, rule by rule in the sheet's order. F1 (DA-F1-005) runs last."""
    return _run(doc, *_PIPELINES.get(_FAMILY.get(doc.get("lang_label")), ()))
''')
    src = "".join(out)
    compile(src, str(DEST), "exec")
    DEST.write_text(src, encoding="utf-8", newline="\n")
    print(f"wrote {DEST.name}: {len(rs)} rules, {len(codes)} functions ({', '.join(codes)})")


if __name__ == "__main__":
    main()
