"""Compile the code medicines: the picked rules in one sheet, and the decision for every disease.

Picks and reasons are written by hand in PICKS, NOT_PICKED and DISEASE_NOTES after reading the code and evidence.json;
the numbers are all computed. The annotators' code is copied unchanged (with ast); only the wrapper is added.

  python -I compile_medicine_code.py <checkout> <packs dir>   -> ../medicine_code.md, ../decisions_code.md
"""
import ast, hashlib, importlib.util, json, re, sys, textwrap
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ce", HERE / "compile_evidence.py")
ce = importlib.util.module_from_spec(spec); sys.modules["ce"] = ce; spec.loader.exec_module(ce)
TEAM = ce.TEAM
OUT = HERE.parent
PACKS = ce.PACK_IDS
SHORT = {"code-go": "go", "code-rust": "rust", "code-js-ts": "js-ts", "code-java": "java", "code-cpp": "cpp", "code-python": "python"}
LANG = {"code-go": ["go"], "code-rust": ["rust"], "code-js-ts": ["javascript", "typescript"], "code-java": ["java"],
        "code-cpp": ["cpp"], "code-python": ["python"]}
ALL = PACKS
NEW_ID = {"RaviNaik:E4": "DA-E4-009", "vaibh27:C4": "DA-C4-002", "amukka:E4fix": "DA-E4-010", "new:E3": "DA-E3-004"}  # not in the registry: the next free number
DISEASE = {"A1": "invisible junk characters", "A2": "control characters", "A3": "mojibake", "A4": "replacement characters",
           "A5": "wrong normal form", "A6": "mixed script (look-alike letters)", "B1": "HTML entities", "B2": "HTML or XML tags", "B3": "ghost markers",
           "B4": "template junk / PII placeholders", "C1": "boilerplate", "C2": "repeated lines", "C3": "truncated or broken document",
           "C4": "two documents joined", "D1": "wrong language label", "D3": "mixed language", "E1": "minified or generated code",
           "E2": "data blobs", "E3": "secrets", "E4": "repeated licence headers", "E5": "broken encoding in code", "E6": "not code", "F1": "personal data",
           "F2": "benchmark leak", "F3": "harmful content", "H3": "same content in another source"}

# run order, by stage: 10 characters, 20 markup, 30 source (drops, then strips), 40 data safety. Drops run before licence removal, or a generated file with its banner inside the licence survives.
PICKS = [
    ("DA-A1-001", ALL, "fix", "Delete U+FEFF (BOM).",
     "Only the BOM: other invisible characters of A1 (U+200B, bidi marks, soft hyphen) are not treated, and no labelled row needs it."),
    ("DA-A2-007", ALL, "fix", "CRLF and lone CR become LF; delete the other C0 control characters and DEL. Tab, newline and form feed stay.",
     "Keeps form feed, which the A2 definition lists, because source code uses it as whitespace. U+0080 to U+009F are not treated."),
    ("DA-A6-001", ALL, "fix", "Cyrillic look-alike letters inside words that also have Latin letters become Latin.",
     "Can turn an obfuscated e-mail address back into plain text, so the data-safety stage runs after it."),
    ("DA-A4-002", ALL, "fix", "Delete a `//` comment that holds U+FFFD and no ASCII letter or digit. An author-quoted U+FFFD stays (ruling 7).",
     "U+FFFD in a string, or in a comment with words, stays."),
    ("DA-A4-003", ["code-java"], "fix", "In comment lines, U+FFFD between letters becomes a space and other U+FFFD is deleted.",
     "Java only: on go it also changes the author-quoted U+FFFD that ruling 7 keeps."),
    ("DA-B3-001", ALL, "fix", "Delete the first line when it starts with `<reponame>`, `<filename>` or `<gh_stars>`.",
     "A marker in the middle of a file is not touched, and none was seen."),
    ("DA-E1-001", ["code-go"], "drop", "Generator marker before or just after the `package` clause, or a Kiota or goformation fingerprint.",
     "Generated code with no marker is missed: 1 labelled go row."),
    ("DA-E1-004", ["code-rust", "code-python"], "drop", "Generator banner in the first 15 lines, or 20 or more `#[doc = \"...\"]` lines.",
     "A hand-written file whose header says \"generated\" is dropped. On python it touches 16 docs, 10 labelled E1 and 1 labelled clean."),
    ("DA-E1-008", ["code-js-ts"], "drop", "A build folder in the path (`node_modules/`, `dist/`, `build/`, `bundles/`, `vendor/`, `generated/`) or `.min.js`, except `.d.ts`; a `sourceMappingURL` line; compiled-module output; a generator word in the header comment; a minified line; a line over 1,000 characters; three or more `.html#` links; or `var searchData =`.",
     "A hand-written file in such a folder, or with one line over 1,000 characters, is dropped. **3 js-ts docs go on the path alone** (`node_modules`, `build`, `generated`). The 30 Oct ruling says a vendored copy is not a disease by itself, so the reviewer should decide whether `node_modules` and `vendor` stay in the path check. Touches 6 js-ts docs that a reader labelled clean."),
    ("DA-E1-006", ["code-java"], "drop", "Decompiler or generator marker in the text (Jad, Procyon, \"AUTO-GENERATED FILE\", \"This class was generated by\", swagger).",
     "Stub files and jadx output with no marker are missed: 4 labelled java rows. Touches 1 doc labelled clean."),
    ("DA-E1-005", ["code-cpp"], "drop", "Generator note in a comment line of the first 1500 characters, or a Kiota or goformation fingerprint.",
     "A comment such as \"the ID generated by the server\" near the top would match."),
    ("DA-E1-007", ["code-cpp"], "drop", "Generator marker in a comment line, or any line longer than 1000 characters.",
     "A hand-written file with one very long line, such as a data table, is dropped."),
    ("DA-E2-001", ALL, "drop", "Byte-array literals cover 10% or more of the file, or base64 runs 40% or more.",
     "Smaller blobs stay: the labelled E2 rows of rust (2), js-ts (1), java (1) and python (1) are not caught."),
    ("DA-C3-002", ["code-go"], "drop", "Go lexical check fails: unclosed string, rune or block comment, or unbalanced brackets.",
     "Go only: it reads Rust lifetimes (`'a`) as unclosed runes. It is not a full parser."),
    ("vaibh27:C4", ["code-java"], "drop", "A separator line (20 or more `_` or `=`) or a \"sample 12 ms submission\" caption outside a comment.",
     "Java only: in python such a line can be a docstring heading."),
    ("DA-E4-005", ["code-go"], "fix+drop", "Drop on a restrictive licence phrase in the first 60 lines. Else delete a licence comment block of 4 or more lines in the Go header, a boxed header, or a block at the end. Build tags and package docs stay.",
     "A licence block touching the package doc comment takes the doc with it. Removes the notice the licence asks to keep: record the licence in metadata first."),
    ("amukka:E4fix", ["code-go", "code-rust", "code-java", "code-cpp", "code-python"], "fix", "Delete a leading comment block of 5 or more lines that is at least 40% licence text. `#` lines count as comments on python only. Shebang, encoding and Go build lines stay. Repeats until nothing changes, for stacked headers.",
     "Short 2 to 4 line notes stay. Removes the notice the licence asks to keep: record the licence in metadata first. **Changed from `DA-E4-004`:** see the decisions file."),
    ("RaviNaik:E4", ["code-java"], "fix+drop", "Drop on a restrictive licence phrase. Else delete the first licence comment block of 7 or more lines in the first 60 lines, or one at the end.",
     "Short headers stay."),
    ("DA-E4-007", ["code-js-ts"], "fix", "Delete the first comment at the top when it is 10 or more lines and names Apache, MIT, GPL or \"Permission is hereby granted\".",
     "Short notices stay. **Changes 1 js-ts gold doc** (`67c9226601f26da9`, a 21-line licence header the gold readers kept). That is within the limit of 2 and it is what the rule is for; the readers disagree on whether a real header is E4. Removes the notice the licence asks to keep: record the licence in metadata first."),
    ("DA-C1-004", ["code-go"], "fix", "Delete kubebuilder and operator-sdk scaffold notes (\"EDIT THIS FILE!\", \"NOTE: json tags are required\").",
     "Other generators' scaffold notes are not covered."),
    ("DA-C1-005", ["code-java"], "fix", "Delete IDE template lines and the template part of a header comment (\"To change this template\", \"Created by ... on\").",
     "Only one java reader labels these; the other two mark 23 of the touched docs clean. It only touches comments."),
    ("DA-B4-009", ALL, "fix", "`<NAME>` -> `AUTHOR`, `<EMAIL>` -> `user@example.com`, `<KEY>` -> `EXAMPLE_KEY`, `<PASSWORD>` -> `EXAMPLE_PASSWORD`.",
     "Cannot repair code that the redaction cut (C3 drops that file). A neutral word is still not the true author."),
    ("DA-E3-003", ALL, "fix", "Known key formats (AWS, GitHub, `sk-`, Slack, PEM) and base32 seeds assigned to secret, seed or otp names become `EXAMPLE_SECRET`.",
     "Secrets with no known format and no telling name are missed. A public test vector is replaced too."),
    ("new:E3", ALL, "fix", "Replace a secret with `EXAMPLE_SECRET` and keep the file. Two kinds: known formats (Google, AWS, GitHub, Stripe, SendGrid, Slack, JWT, PEM), and a quoted value of 16 or more characters assigned to a secret-like name or passed to `new Pusher(`. The value must look random: mixed letters and digits, at least 15% digits, no dots, no dummy words such as `test` or `example`.",
     "A key with no digits, or under 16 characters, or under a neutral variable name is missed. A random-looking ID stored under a name like `key` is replaced too; it only changes a string, so the code still parses. Not a full scanner: gitleaks or trufflehog would catch more."),
]
STAGE = {"A1": "10", "A2": "10", "A4": "10", "A6": "10", "B3": "20", "E1": "30", "E2": "30", "C3": "30", "C4": "30", "E4": "30", "C1": "30", "B4": "40", "E3": "40"}
BLOCKED = {
    "DA-H3-001": "**Rejected by the instructor.** A vendored copy is not a disease by itself. Only the same file twice in a pack counts, as H1 or H2 on the second copy.",
    "DA-F2-001": "**Rejected by the instructor.** The word \"leetcode\" alone is not a benchmark leak. F2 needs a problem or solution from a known benchmark test set, named in the evidence. A real rule is BLOCKED on the G9 fingerprints.",
    "DA-F1-003": "**BLOCKED.** Fails with disputed docs left in: java 16 of 138, limit 1. Only one reader calls those sick, and those docs left the java gold set with no note, so `gold_notes.py` fails. Needs: are author names personal data?",
    "DA-E4-003": "**BLOCKED.** Fails with disputed docs left in: java 2 of 138, limit 1. Only one reader disputes those 2. Would add 13 java rows, 8 of them labelled clean by another reader. Needs: do short licence notes count as E4?",
}
NOT_PICKED = {
    "AjaySnl:B3": "Also rewrites `<EMAIL>` and `<NAME>`, which is B4's job, so it clashes with the B4 pick. The markers it removes are the same. Its extra 13 js-ts and 12 python rows all hold placeholders, and the B4 pick treats them. Its chat-token removal fires on 0 docs.",
    "DA-B3-002": "Same text as the pick on all 3000 docs.", "DA-B3-003": "Same text as the pick on all 3000 docs.",
    "DA-B3-004": "Same text as the pick on all 3000 docs.", "DA-B3-007": "Same text as the pick on all 3000 docs.",
    "DA-B3-008": "Same text as the pick on all 3000 docs.", "udisinghania:B3": "Same text as the pick on all 3000 docs.",
    "DA-B3-005": "Same, plus it strips a BOM, which is A1's job (15 docs differ).",
    "DA-B3-006": "Leaves a blank first line on every file it changes (880 docs differ from the pick).",
    "DA-B3-009": "Also fills placeholders, which is B4's job, so it clashes with the B4 pick. The markers it removes are the same.",
    "DA-B2-001": "Same text as the B3 pick on all 3000 docs. One reader labels the StarCoder markers B2; ruling 1 says B3.",
    "DA-A2-001": "Only fixes line endings; leaves `\\x00`, `\\x1b`, DEL.", "DA-A2-002": "Only fixes line endings.", "DA-A2-003": "Only fixes line endings.",
    "DA-A2-004": "Only fixes line endings.", "DA-A2-008": "Only fixes line endings.",
    "DA-A2-006": "Same text on all 3000 docs, but it deletes a lone CR instead of turning it into LF. That joins lines and can pull code into a `//` comment. No doc here has a lone CR; the full corpus may.",
    "DA-A2-009": "Same text as the pick on all 3000 docs. Also deletes form feed and U+0080 to U+009F. Form feed is whitespace in old source, so the pick keeps it; the A2 definition lists it, so a reviewer may prefer this one.",
    "DA-B4-001": "Deletes the word. `IGNORECASE` also hits real `<email>` and `<year>` tags. Leaves `<KEY>`: 12 docs keep placeholders.",
    "DA-B4-002": "Leaves `<KEY>`: 12 docs keep placeholders.", "DA-B4-003": "Same idea as the pick, but only replaces a quoted `\"<KEY>\"`: 7 docs keep placeholders.",
    "DA-B4-004": "Detector only: it would drop 377 docs that the ruling says to fix.", "DA-B4-005": "Treats the same docs but deletes the word, which breaks a placeholder in a code position.",
    "DA-B4-010": "Treats the same docs but deletes the word, which breaks a placeholder in a code position.",
    "RaviNaik:B4": "Drops 145 docs that can be fixed (any `<KEY>`, `<PASSWORD>`, or a placeholder in code).",
    "DA-F1-001": "Same regex as `DA-B4-010`. One python reader labels the placeholders F1; the B4 pick treats the same 377 docs.",
    "DA-C1-001": "Its 1 java row is treated by `DA-C1-005`. It touches 1 js-ts gold doc.",
    "DA-E1-002": "On js-ts it treats 16 of 23 labelled rows; `DA-E1-008` treats 22 at the same 0 gold docs.",
    "DA-E1-003": "Adds no row: every row it hits on python is hit by `DA-E1-004`. It crashes on 8 docs because it returns None, which the team tool rejects.",
    "DA-E3-001": "Drops the file, and takes any 8+ character value: it touches 1 js-ts gold doc over a dummy `AuthToken` and 1 go gold doc over `Password: \"password\"`. Replaced by `DA-E3-004`, which keeps the file and touches no gold doc.",
    "DA-E2-003": "Its rows are a subset of `DA-E2-001` (go 5 of 7).",
    "DA-E4-001": "Cannot run: needs a second `header` argument, and it has no detection logic.",
    "DA-E4-004": "**Bug: deletes real code.** It treats `#` lines as comments, so on 20 cpp and 2 rust docs it removes `#include`, `#ifndef`, `#pragma once`, `#[derive]`. It also removes shebang, encoding and Go build lines, and needs 2 runs on stacked headers. The gold sets cannot see this. Replaced by `DA-E4-010`.",
    "DA-E4-006": "On js-ts it gives the same text as `DA-E4-007` on all 6 docs. Elsewhere its rows are treated by `DA-E4-010`: it never acts inside the sheet.",
    "DA-E4-002": "Touches gold on go (1) and js-ts (5). Adds no java row beyond the picks.",
    "DA-E4-008": "Changes 0 documents on all 6 packs.",
    "DA-D3-001": "A check that changes nothing. `DISEASES.md`: label it, do not judge it.",
}
DISEASE_NOTES = {
    "A1": "One candidate. It treats every labelled row and touches no gold doc.",
    "A2": "All 8 give the same text on all 3000 docs, because the packs only have CRLF. So the decision is on the code, with a test string holding a lone CR, `\\x00` and form feed. Five only fix line endings and leave `\\x00`. `DA-A2-006` joins lines on a lone CR. `DA-A2-009` also deletes form feed. `DA-A2-007` treats the rest safely and keeps form feed. It was chosen on that test.",
    "A4": "A conflict. `DA-A4-003` treats java's 2 rows, but on go it also changes `1dbf03039c9ea15c`, where the author quotes U+FFFD on purpose (ruling 7). So `DA-A4-002` runs everywhere and `DA-A4-003` on java only.",
    "A6": "One candidate.",
    "B2": "No rule picked. The only candidate gives the same text as the B3 pick, so the 244 js-ts rows are treated under B3.",
    "B3": "A conflict. 7 rules give identical text, so any of them works; the lowest registry ID was taken. The real choice was two rules that also rewrite placeholders. The js-ts one scores highest on row count (1504 vs 1484 rows) only because it also treats B4 rows. Choosing it would hide the B4 decision, and it would replace `<NAME>` with a different word from the B4 pick.",
    "B4": "A conflict in the action: delete, replace, or drop. Replace was chosen. All 3 rules that leave no placeholder treat the same docs, so the count cannot decide. Deleting `<NAME>` in a code position breaks the syntax, while a neutral word stays valid in code and in strings. `DA-B4-009` comes from the compiler's own code-go sheet, so this pick deserves a second look; the java sheets also replace rather than delete, and the rulings do not settle it.",
    "C1": "A different rule for each kind of boilerplate: `DA-C1-004` for Go scaffolds (go), `DA-C1-005` for IDE templates (java). `DA-C1-005` touches 1 gold doc each on js-ts and cpp. That is inside the new limit, but cpp's 2 labelled rows do not justify changing a gold doc, so they stay untreated.",
    "C3": "One candidate, Go only. It drops 16 rust, 20 python and 2 js-ts gold docs because it does not understand those languages.",
    "C4": "One candidate, java only.",
    "D3": "No rule picked: `DISEASES.md` says to label it, not judge it.",
    "E1": "A conflict: 8 rules overlap, each tuned to its own language. For each pack the sheet takes the smallest set that fixes the most labelled rows. Running all of them everywhere only adds drops nobody labelled. Rows still untreated: go 1, rust 6, js-ts 1, java 4, cpp 13, python 1. Those have no marker a rule can see.",
    "E2": "`DA-E2-001` covers every row of `DA-E2-003`.",
    "E3": "A placeholder, never a drop. `DA-E3-003` handles known formats and base32 seeds. `DA-E3-004` is new, written for this sheet, because no submitted rule could do this: it separates real keys from dummy values by the shape of the value, and touches 0 gold docs. Of the 12 labelled rows: 5 are real secrets and all 5 are replaced (go 1, rust 1, js-ts 2, java 1). 6 js-ts rows already hold `<PASSWORD>` or `<KEY>`, which the B4 pick replaces. 1 js-ts row has neither a value nor a placeholder that a rule can see. The code-go `medicine.md` now holds both in one E3 section; that section gives the same text as these two rules on all 3000 docs.",
    "E4": "The biggest conflict, and the one rule that was changed. `DA-E4-004` had the widest reach and the best numbers, and it was deleting real code (see its row). So `DA-E4-010` is that rule with 3 bugs fixed: gold still 0, 2 more labelled rows, 0 docs with code changed, idempotent. It is the base on 5 packs. `DA-E4-005` runs first on go because it reads Go headers and keeps build tags. `DA-E4-009` adds java rows it misses. **js-ts:** the readers mark real licence headers clean, so every rule touches its gold. `DA-E4-007` treats 6 of 9 rows for 1 gold doc, a 21-line header, inside the limit of 2. Rows still untreated are short notes of 2 to 4 lines and blocks that are mostly not licence text: go 18, js-ts 3, java 16, cpp 82, python 21.",
    "F1": "Nothing active. `DA-F1-001` is the same regex as a B4 rule, so its 83 python, 2 cpp and 1 go rows are treated by the B4 pick. `DA-F1-003` is the only rule for names, and it is blocked: see its row. So java's 93 author-name rows stay until the team decides. The `DISEASES.md` definition lists emails, phones, addresses and IDs, not names.",
    "F2": "Nothing active: BLOCKED on the G9 fingerprints. The instructor ruled that \"leetcode\" alone is not a benchmark leak, so the only candidate, which reads the path, is rejected. A real F2 rule has to match known benchmark problems (HumanEval, MBPP, LiveCodeBench, SWE-bench), and none exists yet. The labelled rows in go, rust, js-ts and python need re-reading by their annotators.",
    "H3": "Nothing active. The instructor ruled that a vendored copy is not a disease by itself and needs no proof of which copy is the original. If the same file is in the pack twice, the second copy is H1 or H2; otherwise it is clean. So vendored files stay.",
}
NO_RULE = {
    "A5": "1 labelled row (js-ts). No medicine exists, and one row is below the 5 the template asks for.",
    "B1": "2 labelled rows (go 1, cpp 1). The only rule was withdrawn. Unescaping entities in code would harm valid HTML templates.",
    "C2": "4 labelled rows (js-ts 3, cpp 1). The only rule was withdrawn.",
    "D1": "8 labelled rows (js-ts 1, cpp 7). **Assumption: the language tag on a row is taken as correct, and no detector runs.** A rule on one document cannot tell that a label is wrong, so these rows wait for a language check at scale.",
    "E5": "2 labelled rows (go 1, cpp 1). No medicine exists. go's row sits in the same comment that `DA-A4-002` removes.",
    "E6": "1 labelled row (python). No medicine exists.",
    "F3": "4 labelled rows (go 1, js-ts 1, cpp 2). No medicine exists; it needs a harm classifier.",
}
ORIGIN_PR = {"TharunSivamani": "PR 9", "RaviNaik": "PR 36", "TEJASKUMAR-REDDY-J": "an updated `medicine.md`, not in PR 73 yet", "curioustushar": "PR 93",
             "riyaagrahari": "PR 123", "vaibh27": "PR 48", "varshith2000": "PR 32", "amukka": "PR 52", "Sagar063": "PR 115"}
NOT_RUNNABLE = [
    ("code-go B4, E1, E2, E4 of one sheet", "Need reviewed patches or human confirmation as arguments, so they are hand edits, not rules. Its B3 runs and is listed above."),
    ("code-js-ts E4 of one sheet", "The section has only a regex and no function, so nothing can run."),
    ("`DA-E4-001`", "Needs a second `header` argument."),
    ("code-python A1, A2, A3, A4, B1, C2, E2, E3 of one sheet", "Withdrawn: no longer in that `medicine.md`."),
    ("`cure` and `drop_if_nothing_left` of one code-java sheet", "`cure` is that sheet's own pipeline of its rules. `drop_if_nothing_left` has no disease code, so nothing labels it."),
]


NO_ID = {"AjaySnl:B3": "B3 of a code-js-ts sheet (no ID)", "udisinghania:B3": "B3 of a code-go sheet (no ID)", "RaviNaik:B4": "B4 of a code-go sheet (no ID)"}  # the extractor finds no rule in these sections


def rid_of(name): return NEW_ID.get(name) or NO_ID.get(name, name)


def limit(n): return max(1, n // 100)  # the official limit, harm_test.py


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def source_of(c):
    """(python source, function name) for a candidate, from the file it was loaded from."""
    fn = c["fn"]; name = fn.__name__
    if c["id"] == "new:E3":
        return (HERE / "e3_rule.py").read_text(encoding="utf-8"), name
    if c["id"] == "amukka:E4fix":
        return ce.e4_fixed_source(), name
    if c["handle"] == "amukka":
        return ce.amukka_source(), name
    return (TEAM / "rules" / c["pack"] / f"{c['handle']}.py").read_text(encoding="utf-8"), name


def closure(src, name):
    """Source of `name` plus every top-level def, assignment and import it needs, in file order."""
    tree = ast.parse(src); defs, imports = {}, {}
    def visit(node):
        for n in ([node] if not isinstance(node, ast.Try) else node.body):
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)): defs[n.name] = n
            elif isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id not in ("RULES", "RULES_BY_ID", "_student_rules", "PIPELINE"): defs[t.id] = n
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names: imports[(a.asname or a.name).split(".")[0]] = ast.get_source_segment(src, n)
    for node in tree.body: visit(node)
    need, todo, imps = set(), [name], {"import re"}
    while todo:
        x = todo.pop()
        if x in imports: imps.add(imports[x])
        if x in need or x not in defs: continue
        need.add(x); todo += [w.id for w in ast.walk(defs[x]) if isinstance(w, ast.Name)]
    keep = sorted({id(defs[n]): defs[n] for n in need}.values(), key=lambda n: n.lineno)
    return "\n".join(sorted(imps)) + "\n\n" + "\n\n".join(ast.get_source_segment(src, n) for n in keep)


STD = '''def _std(out, text):
    # the author's result in the shared form: str -> fix/keep, None or True -> drop, False -> keep
    if out is None or out is True: return ("drop", text)
    if out is False: return ("keep", text)
    if isinstance(out, str): return ("fix" if out != text else "keep", out)
    action, new = out
    if action == "drop": return ("drop", text)
    return ("fix" if new != text else "keep", new)'''


def snippet(name, packs, action, c):
    src, fn = source_of(c)
    langs = sorted(l for p in packs for l in LANG[p])
    arg = "doc" if ce.takes_doc(c["fn"]) else 'doc["text"]'
    return (f'RULE_ID = "{rid_of(name)}"\nCODE = "{c["code"]}"\nACTION = "{action}"\nSTAGE = "{STAGE[c["code"]]}"\nSTATUS = "CANDIDATE"\nLANGS = {{{", ".join(map(repr, langs))}}}\n'
            f'ORIGIN = "{", ".join(packs)}"  # packs it runs on\nSOURCE = "{"new rule, written for this sheet" if c["id"] == "new:E3" else c["pack"]}"  # pack whose medicine this came from\nAUTHOR = "{c["handle"]}"\n'
            + closure(src, fn).strip() + "\n\n\n" + STD + "\n\n\ndef medicine(doc):\n"
            '    if doc.get("lang_label") not in LANGS:\n        return ("keep", doc["text"])\n'
            f'    return _std({fn}({arg}), doc["text"])\n')


def run_sheet(rules, doc):
    d, acted = dict(doc), []
    for rid, med in rules:
        a, t = med(d)
        if a == "drop": return "drop", doc["text"], acted + [rid]
        if t != d["text"]: acted.append(rid)
        d["text"] = t
    return ("fix" if d["text"] != doc["text"] else "keep"), d["text"], acted


def main():
    cands = {c["id"]: c for c in ce.load_candidates()}; data = ce.load_data()
    ev = json.loads((HERE.parent / "results" / "sheets" / "evidence.json").read_text(encoding="utf-8"))
    assert {n for n, *_ in PICKS} <= set(cands)
    def touched(name, p): return set(ev["rules"][name]["per"][p]["fix"]) | set(ev["rules"][name]["per"][p]["drop"])
    def cell(name, p, packs=None):
        if packs is not None and p not in packs: return "off"
        g = set(ev["packs"][p]["gold_ids"]); t = touched(name, p); sick = set(ev["packs"][p]["sick"].get(ev["rules"][name]["code"], []))
        n = len(g); h = len(t & g); pct = 100 * h / n
        return f"{pct:.2f}% ({h}/{n}) {'PASS' if h <= limit(n) else 'FAIL'} · {len(t & sick)}/{len(sick)}"
    # the sheet
    head = ["# medicine_code: compiled code medicines", "",
            "Packs: " + ", ".join(f"{SHORT[p]} {len(data[p]['gold'])}" for p in PACKS) + " gold docs (Data A gold, `teams/01-data-a/gold/`). Each pack is tested on its own gold set.",
            "Rule form: `RULE_ID`, `CODE`, `ACTION`, `STAGE`, `STATUS`, `LANGS`, `ORIGIN`, `SOURCE`, `AUTHOR`; `medicine(doc) -> (action, text)`, `doc = {doc_id, text, url, lang_label}`. A row outside `LANGS` passes unchanged. Same form as `medicine_en.md`, with `STAGE` and `STATUS` added. `AUTHOR` is a code field the team's `medicine_conflicts.py` reads; it is not used in the text.",
            "Run order is section order, by stage: 10 characters, 20 markup, 30 source (drops, then strips), 40 data safety. An annotator's code is copied unchanged; only the imports it uses, `_std` and the `LANGS` guard are added. Two exceptions: `DA-E4-010` is `DA-E4-004` with 3 bugs fixed, and `DA-E3-004` is new.",
            "IDs: Data A registry after running the extractor on the latest sheets. `DA-E3-004`, `DA-E4-009`, `DA-E4-010` and `DA-C4-002` are the next free numbers. All IDs are provisional until the team commits the registry.",
            "Assumption: the language tag on a row is correct. No language detector runs (`D1`).",
            "Tested on `g1-harm-test` at `bae5163`. Limit: changed + dropped at most `max(1, floor(1% of gold))`. Why each rule was picked, for each disease: `decisions_code.md`.", "",
            "| pack | gold sha256 | pack sha256 |", "|---|---|---|"] + [f"| {SHORT[p]} | `{sha(TEAM / 'gold' / f'{p}_gold.csv')}` | `{sha(ce.PACKS / f'{p}.parquet')}` |" for p in PACKS] + ["",
            "Each cell: gold harm % (gold docs changed or dropped / gold docs), the result at the limit, and the labelled rows the rule treats / the labelled rows with its code. `off` = not in `LANGS`.", "",
            "| # | ID | disease | action | stage | source | " + " | ".join(SHORT[p] for p in PACKS) + " |", "|---|---|---|---|---|---|" + "---|" * len(PACKS)]
    body = []
    for i, (name, packs, action, what, side) in enumerate(PICKS, 1):
        c = cands[name]; code = c["code"]
        head.append(f"| {i} | `{rid_of(name)}` | {code} {DISEASE[code]} | {action} | {STAGE[code]} | {c['pack']} | " + " | ".join(cell(name, p, packs) for p in PACKS) + " |")
        counts = ", ".join(f"{SHORT[p]} {len(ev['packs'][p]['sick'].get(code, []))}" for p in PACKS)
        ex = [d for p in packs for d in sorted(touched(name, p) & set(ev["packs"][p]["sick"].get(code, [])))][:3]
        fires = ", ".join(f"{SHORT[p]} {len(touched(name, p))}" for p in packs)
        body += ["", f"## {i}. `{rid_of(name)}` · {code} {DISEASE[code]} · {action} · stage {STAGE[code]}", "",
                 f"1. **Disease:** {code} {DISEASE[code]}. Labelled rows: {counts}." + (f" Examples: {', '.join(f'`{d}`' for d in ex)}." if ex else ""),
                 f"2. **Medicine:** {what}", "", "```python", snippet(name, packs, action, c).rstrip(), "```", "",
                 f"3. **Action:** {action}. **Runs on:** {', '.join(SHORT[p] for p in packs)}. **Docs it touches:** {fires}.",
                 "4. **Harm test:** " + "; ".join(f"{SHORT[p]} {cell(name, p).split(' ·')[0]}" for p in packs) + ".",
                 f"5. **Side effects:** {side}",
                 f"6. **Spec v1:** status CANDIDATE, reviewer pending. Source: {c['pack']} sheet, {ORIGIN_PR[c['handle']]}. Idempotent on every doc of its packs. A rule that raises gives ERROR in `harm_test.py`, never PASS."]
    sheet_path = OUT / "sheets" / "medicine_code.md"
    sheet_path.write_text("\n".join(head + body) + "\n", encoding="utf-8", newline="\n")
    # load it back the way harm_test.py does, and test the whole sheet
    rules = []
    for b in re.findall(r"```python\n(.*?)```", sheet_path.read_text(encoding="utf-8"), re.S):
        ns = {"__name__": "rules"}; exec(textwrap.dedent(b), ns); rules.append((ns["RULE_ID"], ns["medicine"]))
    assert len({r for r, _ in rules}) == len(rules)
    res, rows_out, bad = {}, [], 0
    loaded = dict(rules)
    for name, packs, *_ in PICKS:  # the copy behaves as the source on every doc of its packs
        fn = cands[name]["fn"]
        for p in packs:
            for r in data[p]["rows"]:
                a = ce.classify(r["text"], fn(dict(r) if ce.takes_doc(fn) else r["text"]))
                act, t = loaded[rid_of(name)](dict(r))
                bad += a != (act if act == "drop" else "fix" if t != r["text"] else "keep")
    for p in PACKS:
        d = data[p]; g = {"fix": 0, "drop": 0}; pk = {"fix": 0, "drop": 0, "keep": 0}; again = []; sick_any = set().union(*d["sick"].values()); treated = 0; clean_hit = 0; gold_hit = []
        for r in d["rows"]:
            v, t, acted = run_sheet(rules, r); pk[v] += 1
            if r["doc_id"] in d["gold"] and v != "keep": g[v] += 1; gold_hit.append((r["doc_id"], acted[-1]))
            if r["doc_id"] in sick_any and v != "keep": treated += 1
            if r["doc_id"] in d["clean"] - d["gold"] and v != "keep": clean_hit += 1
            if v == "fix":
                v2, _, a2 = run_sheet(rules, dict(r, text=t))
                if v2 != "keep": again.append((r["doc_id"], v2, a2))
        n = len(d["gold"]); pct = 100 * (g["fix"] + g["drop"]) / n
        res[p] = dict(gold=n, g=g, pct=pct, pk=pk, treated=treated, sick=len(sick_any), clean_hit=clean_hit, again=again, gold_hit=gold_hit)
        rows_out.append(f"| {SHORT[p]} | {n} | {g['fix']} | {g['drop']} | {pct:.2f}% | {'PASS' if g['fix'] + g['drop'] <= limit(n) else 'FAIL'} | {pk['fix']} / {pk['drop']} / {pk['keep']} | {treated} / {len(sick_any)} | {clean_hit} |")
    table = ["", "## Harm test of the whole sheet, in run order", "",
             "| pack | gold | gold changed | gold dropped | harm | result | pack fixed / dropped / untouched | labelled rows treated | labelled-clean docs changed outside gold |",
             "|---|---|---|---|---|---|---|---|---|"] + rows_out
    with open(sheet_path, "a", encoding="utf-8", newline="\n") as f: f.write("\n".join(table) + "\n")
    # the decisions file
    ids = {c["id"]: c for c in cands.values()}
    picked = {n: packs for n, packs, *_ in PICKS}
    PACK_OF = {c["handle"]: c["pack"] for c in cands.values()}
    verdict = (HERE / "verdict_block.md").read_text(encoding="utf-8") if (HERE / "verdict_block.md").exists() else ""
    out = ["# Code medicines: final decision", "", verdict,
           "## How rules were picked", "",
           "On each pack, run the smallest set of rules that treats the most labelled rows and stays inside the limit of that pack. A rule that touches a gold doc needs a reason in its side effects; only `DA-E4-007` does (js-ts, 1 doc). Where rules tie, read the code and take the one closest to the disease definition. A rule that passes only because its own supporters' disputes removed docs from gold is held back as BLOCKED.", "",
           "**Inputs:** the latest `medicine.md` of all 12 code sheets in the open PRs (for code-go, one updated file that is not in PR 73 yet, in place of its older 6-rule one), the latest labels of all 17 label sheets, and the official gold sets of `g1-harm-test` at `bae5163`.", "",
           "## The decision for each disease", "",
           "Each cell: gold docs touched · labelled rows treated / labelled rows · labelled-clean docs touched outside gold.", ""]
    codes = sorted({r["code"] for r in ev["rules"].values()} | set(NO_RULE))
    for code in codes:
        names = sorted([n for n, r in ev["rules"].items() if r["code"] == code], key=lambda n: (n not in picked, rid_of(n)))
        chosen = [n for n in names if n in picked]
        out += [f"### {code} {DISEASE[code]}", "",
                "**Picked:** " + ("; ".join(f"`{rid_of(n)}` ({cands[n]['pack']}) on {'all 6 packs' if len(picked[n]) == 6 else ', '.join(SHORT[p] for p in picked[n])}" for n in chosen) if chosen else "nothing") + ".", "",
                "**Why:** " + DISEASE_NOTES.get(code, NO_RULE.get(code, "")), ""]
        if names:
            out += ["| rule | source | decision | " + " | ".join(SHORT[p] for p in PACKS) + " |", "|---|---|---|" + "---|" * len(PACKS)]
            for n in names:
                r = ev["rules"][n]; cells = []
                for p in PACKS:
                    t = touched(n, p); g = set(ev["packs"][p]["gold_ids"]); s = set(ev["packs"][p]["sick"].get(code, [])); cl = set(ev["packs"][p]["clean"]) - g
                    err = len(r["per"][p]["err"])
                    cells.append(("crash " + str(err)) if err == ev["packs"][p]["n"] else f"{len(t & g)} · {len(t & s)}/{len(s)} · {len(t & cl)}" + (f" (crash {err})" if err else ""))
                dec = "**PICKED**" if n in picked else BLOCKED.get(n) or NOT_PICKED.get(n, "?")
                out.append(f"| `{rid_of(n)}` | {PACK_OF[r['handle']]} | {dec} | " + " | ".join(cells) + " |")
            out.append("")
    out += ["## Medicines that could not run", "", "| medicine | why |", "|---|---|"] + [f"| {a} | {b} |" for a, b in NOT_RUNNABLE]
    (OUT / "sheets" / "decisions_code.md").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    missing = [n for n in ev["rules"] if n not in picked and n not in NOT_PICKED and n not in BLOCKED]
    print("rules in sheet:", len(rules), "| copy vs source differences:", bad, "| not explained:", missing)
    for p in PACKS: print(SHORT[p], {k: v for k, v in res[p].items()})


if __name__ == "__main__":
    main()
