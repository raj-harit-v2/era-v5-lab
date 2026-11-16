#!/usr/bin/env python3
"""Combine spec v1 and the Spec v1.1 additions into one spec v1.1 sheet (TSAI Gate 2 decision, 14 Nov 2026).

  python3 -I combine_spec.py --v1 ../../spec_v1/sheets/specv1.md --additions ../sheets/specv1_1_additions.md \
                             --out ../sheets/specv1_1.md [--validation <combined validation .md>]

The run order is the sheet order (spec_v1/build/build_clean.py: each family runs its rules in sheet order, then the shared
F1). So each family holds its spec v1 cards first, then its v1.1 cards, because the readers found the new diseases in text
that spec v1 had cleaned. The one exception is a family that ends with its own F1 rule (English, `DA-F1-005`, the
instructor's): its v1.1 cards go before that rule, so F1 stays last.

- Spec v1's cards are copied unchanged, python blocks included. Only their relative links are rewritten, outside code,
  so they still reach the same files from `spec_v1_1/sheets/`.
- Each v1.1 block gets spec v1's wrapper, the same one specv1.md puts round its source rules: SPEC_PACKS, from the block's
  ORIGIN, guards the source medicine. That gives every block the form build_clean.py reads.
- Cards are numbered 1, 2, 3 ... in run order, and the identity table is rebuilt for the new numbers. Rule IDs don't change.
"""
import argparse
import ast
import posixpath
import re
import sys
from pathlib import Path

HEAD = re.compile(r"^## Medicine (\d+) — (\w+) / (\w+) / `(D[AB]-[A-H]\d-\d{3})`[^\n]*$", re.M)
FENCE = re.compile(r"^```python(?: deferred)?\n(.*?)^```[ \t]*$", re.S | re.M)
ANY_FENCE = re.compile(r"^```.*?^```[ \t]*$", re.S | re.M)
LINK = re.compile(r"(\]\()([^)\s]+)(\))")
ROW = re.compile(r"^\| (\d+) \| (\w+) \| (\w+) \| (.*) \|$")
F1_LAST = {"DA-F1-005"}  # a family's own F1, which must stay its last rule (build_clean.py MUST_KEEP)
V1_DIR, OUT_DIR = "spec_v1/sheets", "spec_v1_1/sheets"  # both under teams/01-data-a

WRAPPER = '''
_spec_source_medicine = medicine

SPEC_PACKS = {packs}

def medicine(doc):
    if doc.get("pack_id") not in SPEC_PACKS:
        return ("keep", doc["text"])
    out = _spec_source_medicine(doc)
    return out
'''


def split(text):
    """(preamble, [card]); a card is {n, family, code, id, head, body}, body running up to the next card."""
    marks = list(HEAD.finditer(text))
    if not marks:
        raise ValueError("no '## Medicine N — family / code / `ID`' card")
    cards = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        cards.append({"n": int(m.group(1)), "family": m.group(2), "code": m.group(3), "id": m.group(4),
                      "head": m.group(0), "body": text[m.end():end]})
    return text[:marks[0].start()], cards


def moved_link(target):
    """A relative link of specv1.md, made relative to spec_v1_1/sheets/ instead."""
    if re.match(r"^(?:[a-z][a-z0-9+.-]*:|#|/)", target, re.I):
        return target
    path, frag = (target.split("#", 1) + [""])[:2]
    new = posixpath.normpath(posixpath.join("../../" + V1_DIR, path)) if path else ""
    return new + ("#" + frag if frag else "")


def move_links(text):
    """Rewrite relative markdown links outside code fences."""
    out, last = [], 0
    for m in ANY_FENCE.finditer(text):
        out.append(LINK.sub(lambda k: k.group(1) + moved_link(k.group(2)) + k.group(3), text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(LINK.sub(lambda k: k.group(1) + moved_link(k.group(2)) + k.group(3), text[last:]))
    return "".join(out)


def literal(block, name, rid):
    vals = re.findall(rf"^{name} = (.*?)(?:\s+#.*)?$", block, re.M)
    if len(vals) != 1:
        raise ValueError(f"{rid}: {len(vals)} lines set {name}")
    return ast.literal_eval(vals[0])


def wrap(card):
    """A v1.1 card with spec v1's SPEC_PACKS wrapper added at the end of its one python block."""
    blocks = list(FENCE.finditer(card["body"]))
    if len(blocks) != 1:
        raise ValueError(f"{card['id']}: {len(blocks)} python blocks")
    b = blocks[0]
    src = b.group(1)
    if re.search(r"^SPEC_PACKS = ", src, re.M):
        raise ValueError(f"{card['id']}: already has SPEC_PACKS")
    packs = sorted(p.strip() for p in literal(src, "ORIGIN", card["id"]).split(","))
    # build_clean.py wants the RULE_ID and CODE lines bare: a comment on them moves to the line above
    src = re.sub(r'^((?:RULE_ID|CODE) = "[^"]*")[ \t]+(#[^\n]*)$', r"\2\n\1", src, flags=re.M)
    new_src = src.rstrip("\n") + "\n" + WRAPPER.format(packs="{" + ", ".join(repr(p) for p in packs) + "}")
    body = card["body"][:b.start(1)] + new_src + card["body"][b.end(1):]
    return dict(card, body=body)


def order(v1_cards, add_cards):
    """All cards in run order: each family's v1 cards, then its v1.1 cards (before a final F1 rule of the family)."""
    families = list(dict.fromkeys(c["family"] for c in v1_cards))
    unknown = sorted({c["family"] for c in add_cards} - set(families))
    if unknown:
        raise ValueError(f"v1.1 families not in spec v1: {unknown}")
    seen = set()
    for c in v1_cards:
        if c["family"] in seen and c["family"] != prev:
            raise ValueError(f"spec v1's {c['family']} cards are not together")
        seen.add(c["family"])
        prev = c["family"]
    out = []
    for f in families:
        v1 = [c for c in v1_cards if c["family"] == f]
        tail = [c for c in v1 if c["id"] in F1_LAST]
        if tail and v1[-len(tail):] != tail:
            raise ValueError(f"{f}: {tail[0]['id']} is not the family's last rule")
        head = v1[:len(v1) - len(tail)]
        out += [dict(c, spec="v1") for c in head]
        out += [dict(c, spec="v1.1") for c in add_cards if c["family"] == f]
        out += [dict(c, spec="v1") for c in tail]
    ids = [c["id"] for c in out]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError(f"rule IDs in both specs: {dup}")
    return out


def identities(preamble):
    """{consolidated ID: (source, source identity)} from a sheet's identity table."""
    out = {}
    for line in preamble.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        cells = [x.strip() for x in m.group(4).split(" | ")]
        rid = cells[-1].strip("`")
        out[rid] = (" | ".join(cells[:-2]) if len(cells) > 2 else "", cells[-2])
    return out


def replace_section(preamble, title, new):
    """Swap the '## title' section of a preamble (up to the next '## ') for new."""
    m = re.search(rf"^## {re.escape(title)}\n.*?(?=^## |\Z)", preamble, re.S | re.M)
    if not m:
        raise ValueError(f"no '## {title}' section")
    return preamble[:m.start()] + new + preamble[m.end():]


def combine(v1_text, add_text, validation=""):
    v1_pre, v1_cards = split(v1_text)
    add_pre, add_cards = split(add_text)
    v1_ids, add_ids = identities(v1_pre), identities(add_pre)
    cards = order(v1_cards, [wrap(c) for c in add_cards])
    rows = ["| Medicine | Family | Disease | Spec | Source | Source identity | Consolidated identity |",
            "|---|---|---|---|---|---|---|"]
    out_cards = []
    for n, c in enumerate(cards, 1):
        src, ident = (v1_ids if c["spec"] == "v1" else add_ids).get(c["id"], ("", f"`{c['id']}`"))
        if c["spec"] == "v1":
            src = "[specv1.md](../../spec_v1/sheets/specv1.md)"
        rows.append(f"| {n} | {c['family']} | {c['code']} | {c['spec']} | {src} | {ident} | `{c['id']}` |")
        head = f"## Medicine {n} — {c['family']} / {c['code']} / `{c['id']}`"
        body = move_links(c["body"]) if c["spec"] == "v1" else c["body"]
        out_cards.append(head + body)
    counts = {}
    for c in cards:
        counts.setdefault(c["family"], {"v1": 0, "v1.1": 0})[c["spec"]] += 1
    family_line = "; ".join(f"{f} {k['v1']} + {k['v1.1']}" for f, k in counts.items())
    identity = ("## Identity mapping\n\nMedicine numbers follow the run order of this sheet, so a spec v1 rule's number "
                "differs from its number in `specv1.md`. The rule ID is the stable key.\n\n" + "\n".join(rows) + "\n\n")
    # each preamble without its title and its own identity table, its sections one level down
    v1_body = re.sub(r"^## ", "### ", move_links(replace_section(v1_pre.split("\n", 1)[1], "Identity mapping", "")),
                     flags=re.M)
    add_body = re.sub(r"^## ", "### ", replace_section(add_pre.split("\n", 1)[1], "Identity mapping", ""), flags=re.M)
    top = (
        "# Medicine sheet: Data A — spec v1.1, combined (spec v1 + Spec v1.1, contributors retained per rule)\n\n"
        "Status: FINAL SUBMISSION for TSAI's Gate 2 decision (14 Nov 2026): spec v1 and spec v1.1 become one spec "
        "v1.1, and theschoolofai/era-v5-lab#435 is that spec. This sheet holds both, in run order: "
        f"{len(cards)} rules ({sum(k['v1'] for k in counts.values())} from spec v1 and "
        f"{sum(k['v1.1'] for k in counts.values())} from Spec v1.1). No rule is approved by this document.\n\n"
        "## How this sheet is made\n\n"
        "`spec_v1_1/scripts/combine_spec.py` writes it from `spec_v1/sheets/specv1.md` and "
        "`sheets/specv1_1_additions.md` (the Spec v1.1 medicines on their own). Change those, not this file.\n"
        "- **Run order is sheet order.** `spec_v1/build/build_clean.py` runs each family's rules in sheet order, then "
        "the shared F1. So each family has its spec v1 rules first, then its v1.1 rules, because the readers found the "
        "new diseases in text spec v1 had cleaned. English is the exception: its v1.1 rules come before `DA-F1-005`, "
        "the instructor's F1 rule, which stays the family's last.\n"
        f"- **Rules per family (spec v1 + v1.1):** {family_line}.\n"
        "- **Spec v1's cards** are copied unchanged, python blocks included. Only relative links are rewritten, so "
        "they still reach the same files from this folder.\n"
        "- **Each v1.1 block** gets spec v1's wrapper: `SPEC_PACKS`, from the block's `ORIGIN`, guards the source "
        "medicine, as in `specv1.md`. So every block has the form `build_clean.py` reads.\n\n"
        + (validation.rstrip() + "\n\n" if validation else "")
    )
    return (top + "## Spec v1\n\n" + v1_body.lstrip("\n") + "## Spec v1.1 additions (Gate 2)\n\n" + add_body.lstrip("\n")
            + identity + "\n".join(out_cards).rstrip() + "\n"), cards


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--v1", required=True, type=Path)
    ap.add_argument("--additions", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--validation", type=Path, help="a markdown section with the combined harm results, put near the top")
    a = ap.parse_args(argv)
    validation = a.validation.read_text(encoding="utf-8") if a.validation else ""
    text, cards = combine(a.v1.read_text(encoding="utf-8"), a.additions.read_text(encoding="utf-8"), validation)
    a.out.write_text(text, encoding="utf-8")
    spec = {}
    for c in cards:
        spec[c["spec"]] = spec.get(c["spec"], 0) + 1
    print(f"wrote {a.out}: {len(cards)} cards ({spec.get('v1', 0)} spec v1, {spec.get('v1.1', 0)} v1.1), "
          f"{len(text.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
