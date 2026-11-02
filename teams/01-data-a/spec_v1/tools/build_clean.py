"""Write ../clean.py from ../sheets/specv1.md: one function per disease code, each rule's code unchanged, and one
scope table at the top that says which packs each rule applies to.

  python -I build_clean.py [--sheet ../sheets/specv1.md] [--out ../clean.py]

specv1.md has one "## Medicine N — <family> / <code> / `<ID>`" section per rule, each with one python block. A block names
its packs in SPEC_PACKS, and a math block checks its ORIGIN packs too (PACKS); the scope is what both allow. The build
moves those pack IDs into SCOPE and points SPEC_PACKS and PACKS at it, so pack IDs are written once. A document goes to the
family of its pack_id and runs that family's rules in sheet order; a missing or unknown pack_id passes unchanged.

Each rule block goes into its own closure, so helpers with the same name in two blocks do not clash. Prints any string
that indenting a block changed: only a multi-line string can change, and a docstring or a verbose regex does not care.
"""
import argparse, ast, re, textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE.parent
SECTION = re.compile(r"^## Medicine (\d+) — (\w+) / (\w+) / `(DA-[A-H]\d-\d{3})`\n(.*?)(?=^## Medicine \d+ — |\Z)", re.S | re.M)
BLOCK = re.compile(r"^```python\n(.*?)^```", re.S | re.M)  # at line start: a rule can hold ``` inside a regex
CODE_ORDER = ["A1", "A2", "A6", "A4", "A5", "A3", "B1", "B2", "B5", "B3", "E1", "E2", "C3", "C4", "C5", "D4", "E4", "C1", "C2", "D1", "D3", "B4", "E3", "F1"]  # RULES order; each family runs in its own sheet order
SHARED_F1 = "f1_rule.py"  # the shared F1 (TSAI ruling of 31 Oct), in SCOPE under this name: it runs last on the packs of these families
SHARED_F1_FAMILIES = ("code", "math", "sci")  # code with tree-sitter, math and sci with the prose path (TSAI, 1 Nov). English keeps DA-F1-005
MUST_KEEP = {"DA-F1-005": "english"}  # the instructor's F1 rule: on every pack of its family, never left out


def literal(b, name, rid):
    """The value of the one-line assignment name = <literal> in a block."""
    lines = re.findall(rf"^{name} = (.*?)(?:\s+#.*)?$", b, re.M)
    assert len(lines) == 1, f"{rid}: {len(lines)} lines set {name}"
    return ast.literal_eval(lines[0])


def rules(sheet):
    out = []
    for n, family, code, rid, body in SECTION.findall(sheet.read_text(encoding="utf-8")):
        blocks = BLOCK.findall(body)
        assert len(blocks) == 1, f"medicine {n} ({rid}): {len(blocks)} python blocks"
        b = textwrap.dedent(blocks[0])
        assert re.search(rf'^RULE_ID = "{rid}"$', b, re.M) and re.search(rf'^CODE = "{code}"$', b, re.M), f"medicine {n}: block does not match its heading {code} {rid}"
        packs = set(literal(b, "SPEC_PACKS", rid))
        b = re.sub(r"^SPEC_PACKS = .*$", f'SPEC_PACKS = SCOPE["{rid}"]', b, flags=re.M)
        if re.search(r"^PACKS = ", b, re.M):  # a math block: its own ORIGIN packs, inside the SPEC_PACKS guard
            assert re.search(r'^PACKS = set\(ORIGIN\.split\(", "\)\)', b, re.M), f"{rid}: PACKS is not set(ORIGIN.split(...))"
            packs &= set(literal(b, "ORIGIN", rid).split(", "))
            b = re.sub(r"^PACKS = .*$", f'PACKS = SCOPE["{rid}"]  # the math packs share the "en" tag, so the pack is checked too', b, flags=re.M)
        assert packs, f"{rid}: applies to no pack"
        for line in b.split("\n"):  # pack IDs come only from SCOPE
            assert "pack_id" not in line or re.search(r'doc\.get\("pack_id"\) not in (SPEC_PACKS|PACKS)\b', line), f"{rid}: reads pack_id outside the guard: {line.strip()}"
        if family == "code" and rid == "DA-B4-009":  # <EMAIL> is the tag TSAI asks for, so B4 must not rewrite it. Move this to the sheet when the team agrees.
            assert b.count('"<EMAIL>": "user@example.com", ') == 1
            b = b.replace('"<EMAIL>": "user@example.com", ', "")
        b = re.sub(r"^AUTHOR = .*\n", "", b, flags=re.M)  # the sheet keeps it for medicine_conflicts.py; the cleaner has no use for it
        out.append(dict(n=int(n), id=rid, code=code, family=family, packs=packs, name=f"_{family}_{rid[3:].lower().replace('-', '_')}", src=b.rstrip()))
    assert [r["n"] for r in out] == list(range(1, len(out) + 1)), "medicine sections are not numbered 1, 2, 3, ..."
    ids = [r["id"] for r in out]
    assert len(ids) == len(set(ids)), "two medicines share an ID"
    return out


def strings(node): return [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def factory(r, sheet):
    body = textwrap.indent(r["src"], "    ")
    text = f'@cache\ndef {r["name"]}():\n    # {r["id"]}, {sheet}, medicine {r["n"]} ({r["family"]})\n{body}\n    return medicine\n'
    a, b = strings(ast.parse(r["src"])), strings(ast.parse(text))
    changed = [x for x, y in zip(a, b) if x != y]
    if len(a) != len(b) or changed:
        print(r["id"], r["family"], "strings changed:", len(changed), [x[:40] for x in changed])
    return text


def scope_line(key, packs, note):
    return f'    "{key}": frozenset({{{", ".join(f"{chr(34)}{p}{chr(34)}" for p in sorted(packs))}}}),  # {note}\n'


SHARED = """
_shared_f1 = f1


@cache
def _shared_f1_rule():
    # the shared F1, spec_v1/tools/f1_rule.py: the TSAI F1 ruling of 31 Oct. It has no pack guard of its own, so _run applies SCOPE
    return _shared_f1
"""
RUN = """

def _run(doc, *factories):
    \"\"\"Run the rules in order: a drop ends the document, a fix passes its text on. A rule runs only on the packs SCOPE gives it.\"\"\"
    d = dict(doc)
    for make in factories:
        if doc.get("pack_id") not in SCOPE[_ID[make]]:
            continue
        action, text = make()(d)
        if action == "drop":
            return ("drop", doc["text"])
        d["text"] = text
    return ("fix" if d["text"] != doc["text"] else "keep", d["text"])
"""
CLEAN = """

def clean(doc):
    \"\"\"The whole pipeline for one document: its pack's family in sheet order, then the shared F1 (code, math and sci packs).
    A missing or unknown pack_id passes unchanged; such a document is not eligible for release.\"\"\"
    return _run(doc, *_PIPELINES.get(_FAMILY.get(doc.get("pack_id")), ()), _shared_f1_rule)
"""


def build(sheet, dest):
    rs = rules(sheet)
    families = {}
    for r in rs:
        families.setdefault(r["family"], []).append(r)
    family_packs = {f: set().union(*(r["packs"] for r in x)) for f, x in families.items()}
    for f, packs in family_packs.items():
        others = set().union(*(p for g, p in family_packs.items() if g != f))
        assert not packs & others, f"{sorted(packs & others)} in two families"
    for rid, fam in MUST_KEEP.items():
        r = next((r for r in rs if r["id"] == rid), None)
        assert r and r["code"] == "F1" and r["packs"] == family_packs[fam], f"{rid} must be in the sheet, under F1, on every {fam} pack"
    assert not set(SHARED_F1_FAMILIES) & set(MUST_KEEP.values()), "a family with its own required F1 must not get the shared F1"
    f1_packs = set().union(*(family_packs[f] for f in SHARED_F1_FAMILIES))
    codes = [c for c in CODE_ORDER if any(r["code"] == c for r in rs)] + sorted({r["code"] for r in rs} - set(CODE_ORDER))
    assert codes[-1] == "F1", "F1 must be the last disease code"
    out = ['"""Spec v1 cleaning: one function per disease code, and clean(doc) to run them in order. GENERATED by spec_v1/tools/build_clean.py from\n'
           f"spec_v1/sheets/{sheet.name}: change the sheet, not this file.\n\n"
           "doc is {doc_id, text, url, lang_label, pack_id}. Each function returns (action, text), action being keep, fix or drop.\n"
           "SCOPE says which packs each rule applies to; on any other pack, or without a pack_id, a rule does nothing.\n"
           f"Families: {', '.join(f'{f} ({len(p)} packs, {len(families[f])} rules)' for f, p in family_packs.items())}.\n"
           '"""\n'
           "import re\nfrom functools import cache\n\n"
           "# The packs each rule applies to: SPEC_PACKS in the sheet (and a math rule's own ORIGIN packs). Each rule reads its entry.\n"
           "SCOPE = {\n"]
    out += [scope_line(r["id"], r["packs"], f'{r["family"]} {r["code"]}, medicine {r["n"]}') for r in rs]
    out.append(scope_line(SHARED_F1, f1_packs, f"the shared F1, spec_v1/tools/f1_rule.py: {', '.join(SHARED_F1_FAMILIES)} packs, last"))
    out.append("}\n\n\n")
    out += [factory(r, sheet.name) + "\n" for r in rs]
    out.append((HERE / "f1_rule.py").read_text(encoding="utf-8").rstrip() + "\n\n")
    out.append(SHARED)
    out.append('\n\n_RULE = {  # rule ID -> its factory, in sheet order\n' + "".join(f'    "{r["id"]}": {r["name"]},\n' for r in rs)
               + f'    "{SHARED_F1}": _shared_f1_rule,\n}}\n_ID = {{make: rid for rid, make in _RULE.items()}}\n')
    out.append(RUN)
    for code in codes:
        names = [r["name"] for r in rs if r["code"] == code] + (["_shared_f1_rule"] if code == "F1" else [])
        out.append(f'\n\ndef {code.lower()}(doc):\n    return _run(doc, {", ".join(names)})\n')
    out.append("\n\nRULES = {" + ", ".join(f'"{c}": {c.lower()}' for c in codes) + "}  # disease code -> function, the form harm_test.py reads\n")
    out.append("# each family's rules in sheet order; clean() runs the shared F1 after them\n_PIPELINES = {\n")
    out += [f'    "{f}": ({", ".join(r["name"] for r in x)},),\n' for f, x in families.items()]
    out.append("}\n_FAMILY = {pack: family for family, rules in _PIPELINES.items() for make in rules for pack in SCOPE[_ID[make]]}  # pack_id -> family\n")
    out.append(CLEAN)
    dest.write_text("".join(out), encoding="utf-8", newline="\n")
    print(f"{dest.name}: rules {len(rs)} + shared F1 |", ", ".join(f"{f} {len(x)} rules on {len(family_packs[f])} packs" for f, x in families.items()),
          "| functions:", len(codes))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", type=Path, default=SPEC / "sheets" / "specv1.md")
    ap.add_argument("--out", type=Path, default=SPEC / "clean.py")
    args = ap.parse_args()
    build(args.sheet, args.out)
