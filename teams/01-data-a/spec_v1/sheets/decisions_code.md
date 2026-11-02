# Code medicines: final decision

## Verdict

**Ready for team review. Not approved or frozen.** All 24 rules are `CANDIDATE` in Spec v1 terms. They need an independent reviewer, and 3 questions below still need an answer. No criterion fails on the sheet itself.

### Result per pack

Each pack is tested with the team's `harm_test.py --rule all` on its own gold set. Limit: changed + dropped at most `max(1, floor(1% of gold))`. "Stress" leaves in the docs that the gold builder excludes as disputed; it is not the official test.

| pack | gold harm | limit | result | stress | fixed / dropped / untouched | labelled rows treated |
|---|---|---|---|---|---|---|
| go | 0 / 163 | 1 | PASS | 1 / 171 PASS | 265 / 44 / 191 | 309 / 337 |
| rust | 0 / 78 | 1 | PASS | 0 / 78 PASS | 238 / 17 / 245 | 255 / 259 |
| js-ts | 1 / 204 | 2 | PASS | 3 / 207 **over** | 264 / 22 / 214 | 286 / 296 |
| java | 0 / 116 | 1 | PASS | 2 / 138 **over** | 350 / 11 / 139 | 361 / 384 |
| cpp | 0 / 120 | 1 | PASS | 0 / 124 PASS | 343 / 10 / 147 | 353 / 378 |
| python | 0 / 46 | 1 | PASS | 1 / 51 PASS | 325 / 16 / 159 | 336 / 343 |

- **js-ts's 1 gold doc** is `67c9226601f26da9`, a 21-line licence header that its 2 gold readers kept. `DA-E4-007` removes it on purpose: see E4.
- **Stress hits:** 6 docs that a third reader labelled with that disease, so the rule agrees with that reader. They show how much the numbers rest on reader disagreement. The two packs over the limit are the ones where this matters most.
- **0 hits is not 0 harm.** A gold set of n docs with 0 hits only bounds the harm rate below about 3/n: python 6.5%, rust 3.8%, java 2.6%, cpp 2.5%, go 1.8%, js-ts 1.5%. About 300 docs are needed to show 1%.
- "Labelled rows" still counts the H3 and F2 rows that the 30 Oct ruling sends back for re-reading.

### Against the criteria

| criterion | source | result |
|---|---|---|
| Disease, medicine in words and code, action, harm test, side effects | `DISEASES.md` §4 | **Met.** Every section has all 5. Examples give `doc_id` only. |
| Within the limit, alone and combined, per pack | `DISEASES.md` §4, official limit | **Met.** |
| Pick the rule that passes and fixes the most; two rules only if they fix different cases | TSAI answer, 27 Oct | **Met.** |
| Vendored copy and "leetcode" rulings | Instructor answer, 30 Oct | **Partly.** No H3 or F2 rule is in the sheet. `DA-E1-008` still drops 3 js-ts docs on the path alone, 1 of them in `node_modules`: reviewer to decide. |
| Never remove a gold doc to make a rule pass | TSAI answer; guideline 3 | **Met by this sheet.** The branch's java gold has a separate problem: see below. |
| A medicine for each disease seen more than 5 times | `DISEASES.md` §4 | **Partly.** Gaps: cpp D1 (7), java F1 (94, waiting on an answer). By ruling, no medicine: go H3, the F2 rows, js-ts D3. |
| Exact text differences count; each doc counted once | Spec v1 §2 | **Met.** Counted by the team's tool. |
| Tested on every pack a rule applies to; failures not hidden | Spec v1 §2.6 | **Met.** `LANGS` is explicit; other packs are N/A. |
| Treats real cases without new damage | Spec v1 §2.3 | **Met after fixes.** Python: 0 files stop parsing. All packs: 0 docs with code changed by a comment rule. No markers, placeholders or CR left. |
| Idempotent; order and conflicts recorded; combined test | Spec v1 §2.8 and §4 | **Met.** 0 docs change on a second run. |
| No secrets or personal data | `DISEASES.md` §2a, pr-guard | **Met.** Scanned: no keys, and the only email is `user@example.com`. |
| Digests, owner, reviewer, commit | Spec v1 §1 and §2.9 | **Partly.** Gold and pack digests are in the sheet. Reviewer and the sheet's own commit come at review. |

### What changed in this round

1. **New js-ts rules.** `DA-E1-008` replaces `DA-E1-002` (22 of 23 labelled rows, was 16). `DA-E4-007` gives js-ts its first licence rule (6 of 9 rows, for 1 gold doc inside the limit).
2. **Run order follows the Spec v1 stages:** 10 characters, 20 markup, 30 source (drops, then strips), 40 data safety. Outcomes on go, rust, java, cpp and python are the same as before the reorder.
3. **New official limit applied**, and IDs refreshed after the latest sheets: the changed licence rule is `DA-E4-010`, and the java licence rule is `DA-E4-009`.
4. **Language tags are assumed correct.** No detector runs; D1 rows wait for a language check at scale.
5. Personal names are out of the text. `AUTHOR` stays as a code field because the team's `medicine_conflicts.py` reads it.

### What the earlier review changed

1. **A real bug in `DA-E4-004`.** It deleted `#include`, `#ifndef`, `#pragma once` and `#[derive]` on 20 cpp and 2 rust docs, because it treats `#` lines as comments. It also deleted shebang, encoding and Go build lines. The harm test cannot see this, because those docs are not in gold. `DA-E4-010` fixes it: `#` counts as a comment on python only, those lines stay, and it repeats until nothing changes. Gold still 0, 2 more labelled rows, 0 docs with code changed.
2. **New rule `DA-E3-004` for secrets.** It replaces the value with `EXAMPLE_SECRET` and never drops a file. It decides by the shape of the value, so dummy values stay.
3. **The A2 pick changed.** `DA-A2-006` deletes a lone CR, which joins lines and can pull code into a comment. No doc here has one, so the numbers could not show it.
4. **2 rules held back.** `DA-F1-003` and `DA-E4-003` passed only because a reader's own disputes kept docs out of gold.

Every other rule is its author's code, copied unchanged: 0 differences from the source. Only the imports, `_std` and the `LANGS` guard are added. Several picks come from the compiler's own code-go sheet (`DA-A2-007`, `DA-B4-009`, `DA-E3-003`, `DA-E3-004`, `DA-E4-005` and others), so a reviewer should look at those independently.

### Questions for the team

| question | what the answer changes |
|---|---|
| Are author names personal data? | `DA-F1-003` on: treats java's 93 rows, and java gold must be re-judged. |
| Do short licence notes (2 to 4 lines) count as E4, in every pack? | `DA-E4-003` on, and a rule elsewhere. It adds rows on every pack but fails the limit on most. |
| Are IDE template lines C1 in every pack? | Only one java reader labels them. They are 78 of java's 80 C1 rows. |

### Problems to report to the team

- **The branch's java gold fails the team's own check.** `gold_notes.py` reports 18 problems: docs left the gold set with no note. Its docstring says such a file must not be used.
- **`run_harm_suite.py` refuses a spec that lists an `UNSTRUCTURED` sheet.** The builder writes that state, but the runner's inventory pattern accepts only `TEMPLATE` and `MEDICINES`, so the counts disagree. One code-go sheet triggers it. Tested here with that sheet moved aside.
- **`run_harm_suite.py` per pack:** go 14 rules PASS, java 18 PASS, js-ts 10 PASS, python 4 PASS. cpp 4 PASS and `DA-E4-001` ERROR, because it needs a second argument. rust 5 ERROR, because the extractor writes no rules file for that sheet. It tests rules one at a time, never the combined sheet, and overall it reports INCOMPLETE, as it should for a draft.
- **`DA-E4-004` deletes code**, in its own rust pack too (2 docs).
- **F2 and H3 rows need re-reading** under the ruling: F2 in go 7, rust 4, js-ts 1, python 5; H3 in go 38. That will change the go gold set, so this test must be rerun on the rebuilt gold.
- **The extractor gets nothing from 3 sheets** (a `RULES` dict in one, no `**Disease:**` lines in two), and it skips 4 more sections.
- **Rules that return None to drop:** `harm_test.py` reports an error on those docs. The sheet's wrapper handles it.
- **Rule IDs in this sheet are provisional.** `DA-E3-004`, `DA-E4-009`, `DA-E4-010` and `DA-C4-002` are new, and others come from a local extractor run.

### Limits

- The numbers come from 500-doc samples, and 5 of 6 gold sets are under the 200 target.
- `DA-E3-004` is not a full scanner. A key with no digits, under 16 characters, or under a neutral name is missed. Its thresholds were written after seeing these packs, so new data is its real test.
- Only python has a real parser check. Other languages have the comments-stripped comparison and bracket counts, not a compile.
- A licence rule can take a file description in the same comment block: `doc comment` hits in the audit are `DA-E4-010` 32, `DA-E4-007` 4, `DA-E4-005` 3, `DA-E4-009` 3. It also removed one `# pylint:` line on python. No code is lost.
- `DA-C1-005` removes 57 doc comment parts on java. It only touches comments.
- Run on Windows with the merged watchdog, not on Linux. No rule hung.


## How rules were picked

On each pack, run the smallest set of rules that treats the most labelled rows and stays inside the limit of that pack. A rule that touches a gold doc needs a reason in its side effects; only `DA-E4-007` does (js-ts, 1 doc). Where rules tie, read the code and take the one closest to the disease definition. A rule that passes only because its own supporters' disputes removed docs from gold is held back as BLOCKED.

**Inputs:** the latest `medicine.md` of all 12 code sheets in the open PRs (for code-go, one updated file that is not in PR 73 yet, in place of its older 6-rule one), the latest labels of all 17 label sheets, and the official gold sets of `g1-harm-test` at `bae5163`.

## The decision for each disease

Each cell: gold docs touched · labelled rows treated / labelled rows · labelled-clean docs touched outside gold.

### A1 invisible junk characters

**Picked:** `DA-A1-001` (code-cpp) on all 6 packs.

**Why:** One candidate. It treats every labelled row and touches no gold doc.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-A1-001` | code-cpp | **PICKED** | 0 · 0/0 · 0 | 0 · 1/1 · 0 | 0 · 1/1 · 0 | 0 · 1/1 · 0 | 0 · 12/12 · 0 | 0 · 0/0 · 0 |

### A2 control characters

**Picked:** `DA-A2-007` (code-go) on all 6 packs.

**Why:** All 8 give the same text on all 3000 docs, because the packs only have CRLF. So the decision is on the code, with a test string holding a lone CR, `\x00` and form feed. Five only fix line endings and leave `\x00`. `DA-A2-006` joins lines on a lone CR. `DA-A2-009` also deletes form feed. `DA-A2-007` treats the rest safely and keeps form feed. It was chosen on that test.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-A2-007` | code-go | **PICKED** | 0 · 1/1 · 1 | 0 · 6/6 · 0 | 0 · 17/17 · 8 | 0 · 44/44 · 0 | 0 · 47/47 · 0 | 0 · 2/2 · 2 |
| `DA-A2-001` | code-cpp | Only fixes line endings; leaves `\x00`, `\x1b`, DEL. | 0 · 1/1 · 1 | 0 · 6/6 · 0 | 0 · 17/17 · 8 | 0 · 44/44 · 0 | 0 · 47/47 · 0 | 0 · 2/2 · 2 |
| `DA-A2-002` | code-java | Only fixes line endings. | 0 · 1/1 · 1 | 0 · 6/6 · 0 | 0 · 17/17 · 8 | 0 · 44/44 · 0 | 0 · 47/47 · 0 | 0 · 2/2 · 2 |
| `DA-A2-003` | code-java | Only fixes line endings. | 0 · 1/1 · 1 | 0 · 6/6 · 0 | 0 · 17/17 · 8 | 0 · 44/44 · 0 | 0 · 47/47 · 0 | 0 · 2/2 · 2 |
| `DA-A2-004` | code-js-ts | Only fixes line endings. | 0 · 1/1 · 1 | 0 · 6/6 · 0 | 0 · 17/17 · 8 | 0 · 44/44 · 0 | 0 · 47/47 · 0 | 0 · 2/2 · 2 |
| `DA-A2-006` | code-rust | Same text on all 3000 docs, but it deletes a lone CR instead of turning it into LF. That joins lines and can pull code into a `//` comment. No doc here has a lone CR; the full corpus may. | 0 · 1/1 · 1 | 0 · 6/6 · 0 | 0 · 17/17 · 8 | 0 · 44/44 · 0 | 0 · 47/47 · 0 | 0 · 2/2 · 2 |
| `DA-A2-008` | code-java | Only fixes line endings. | 0 · 1/1 · 1 | 0 · 6/6 · 0 | 0 · 17/17 · 8 | 0 · 44/44 · 0 | 0 · 47/47 · 0 | 0 · 2/2 · 2 |
| `DA-A2-009` | code-js-ts | Same text as the pick on all 3000 docs. Also deletes form feed and U+0080 to U+009F. Form feed is whitespace in old source, so the pick keeps it; the A2 definition lists it, so a reviewer may prefer this one. | 0 · 1/1 · 1 | 0 · 6/6 · 0 | 0 · 17/17 · 8 | 0 · 44/44 · 0 | 0 · 47/47 · 0 | 0 · 2/2 · 2 |

### A4 replacement characters

**Picked:** `DA-A4-002` (code-go) on all 6 packs; `DA-A4-003` (code-java) on java.

**Why:** A conflict. `DA-A4-003` treats java's 2 rows, but on go it also changes `1dbf03039c9ea15c`, where the author quotes U+FFFD on purpose (ruling 7). So `DA-A4-002` runs everywhere and `DA-A4-003` on java only.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-A4-002` | code-go | **PICKED** | 0 · 1/1 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/2 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |
| `DA-A4-003` | code-java | **PICKED** | 0 · 1/1 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 2/2 · 1 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |

### A5 wrong normal form

**Picked:** nothing.

**Why:** 1 labelled row (js-ts). No medicine exists, and one row is below the 5 the template asks for.

### A6 mixed script (look-alike letters)

**Picked:** `DA-A6-001` (code-go) on all 6 packs.

**Why:** One candidate.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-A6-001` | code-go | **PICKED** | 0 · 2/2 · 1 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |

### B1 HTML entities

**Picked:** nothing.

**Why:** 2 labelled rows (go 1, cpp 1). The only rule was withdrawn. Unescaping entities in code would harm valid HTML templates.

### B2 HTML or XML tags

**Picked:** nothing.

**Why:** No rule picked. The only candidate gives the same text as the B3 pick, so the 244 js-ts rows are treated under B3.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-B2-001` | code-js-ts | Same text as the B3 pick on all 3000 docs. One reader labels the StarCoder markers B2; ruling 1 says B3. | 0 · 0/0 · 0 | 0 · 0/1 · 0 | 0 · 244/244 · 1 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |

### B3 ghost markers

**Picked:** `DA-B3-001` (code-cpp) on all 6 packs.

**Why:** A conflict. 7 rules give identical text, so any of them works; the lowest registry ID was taken. The real choice was two rules that also rewrite placeholders. The js-ts one scores highest on row count (1504 vs 1484 rows) only because it also treats B4 rows. Choosing it would hide the B4 decision, and it would replace `<NAME>` with a different word from the B4 pick.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-B3-001` | code-cpp | **PICKED** | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 245/262 · 1 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 272/284 · 0 |
| `B3 of a code-go sheet (no ID)` | code-go | Same text as the pick on all 3000 docs. | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 245/262 · 1 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 272/284 · 0 |
| `B3 of a code-js-ts sheet (no ID)` | code-js-ts | Also rewrites `<EMAIL>` and `<NAME>`, which is B4's job, so it clashes with the B4 pick. The markers it removes are the same. Its extra 13 js-ts and 12 python rows all hold placeholders, and the B4 pick treats them. Its chat-token removal fires on 0 docs. | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 258/262 · 4 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 279/284 · 0 |
| `DA-B3-002` | code-go | Same text as the pick on all 3000 docs. | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 245/262 · 1 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 272/284 · 0 |
| `DA-B3-003` | code-go | Same text as the pick on all 3000 docs. | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 245/262 · 1 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 272/284 · 0 |
| `DA-B3-004` | code-java | Same text as the pick on all 3000 docs. | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 245/262 · 1 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 272/284 · 0 |
| `DA-B3-005` | code-java | Same, plus it strips a BOM, which is A1's job (15 docs differ). | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 245/262 · 1 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 272/284 · 0 |
| `DA-B3-006` | code-python | Leaves a blank first line on every file it changes (880 docs differ from the pick). | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 245/262 · 1 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 272/284 · 0 |
| `DA-B3-007` | code-rust | Same text as the pick on all 3000 docs. | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 245/262 · 1 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 272/284 · 0 |
| `DA-B3-008` | code-java | Same text as the pick on all 3000 docs. | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 245/262 · 1 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 272/284 · 0 |
| `DA-B3-009` | code-js-ts | Also fills placeholders, which is B4's job, so it clashes with the B4 pick. The markers it removes are the same. | 0 · 247/247 · 0 | 0 · 225/225 · 0 | 0 · 262/262 · 8 | 0 · 250/250 · 0 | 0 · 245/245 · 0 | 0 · 284/284 · 1 |

### B4 template junk / PII placeholders

**Picked:** `DA-B4-009` (code-go) on all 6 packs.

**Why:** A conflict in the action: delete, replace, or drop. Replace was chosen. All 3 rules that leave no placeholder treat the same docs, so the count cannot decide. Deleting `<NAME>` in a code position breaks the syntax, while a neutral word stays valid in code and in strings. `DA-B4-009` comes from the compiler's own code-go sheet, so this pick deserves a second look; the java sheets also replace rather than delete, and the rulings do not settle it.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-B4-009` | code-go | **PICKED** | 0 · 43/45 · 0 | 0 · 18/18 · 0 | 0 · 25/25 · 7 | 0 · 82/83 · 0 | 0 · 121/122 · 0 | 0 · 27/27 · 1 |
| `B4 of a code-go sheet (no ID)` | code-go | Drops 145 docs that can be fixed (any `<KEY>`, `<PASSWORD>`, or a placeholder in code). | 0 · 43/45 · 0 | 0 · 18/18 · 0 | 0 · 25/25 · 7 | 0 · 82/83 · 0 | 0 · 121/122 · 0 | 0 · 27/27 · 1 |
| `DA-B4-001` | code-cpp | Deletes the word. `IGNORECASE` also hits real `<email>` and `<year>` tags. Leaves `<KEY>`: 12 docs keep placeholders. | 0 · 39/45 · 0 | 0 · 17/18 · 1 | 0 · 22/25 · 5 | 0 · 81/83 · 0 | 0 · 121/122 · 0 | 0 · 27/27 · 1 |
| `DA-B4-002` | code-java | Leaves `<KEY>`: 12 docs keep placeholders. | 0 · 39/45 · 0 | 0 · 17/18 · 0 | 0 · 22/25 · 5 | 0 · 81/83 · 0 | 0 · 121/122 · 0 | 0 · 27/27 · 1 |
| `DA-B4-003` | code-java | Same idea as the pick, but only replaces a quoted `"<KEY>"`: 7 docs keep placeholders. | 0 · 41/45 · 0 | 0 · 18/18 · 0 | 0 · 24/25 · 7 | 0 · 82/83 · 0 | 0 · 121/122 · 0 | 0 · 27/27 · 1 |
| `DA-B4-004` | code-js-ts | Detector only: it would drop 377 docs that the ruling says to fix. | 0 · 43/45 · 0 | 0 · 18/18 · 0 | 0 · 25/25 · 7 | 0 · 82/83 · 0 | 0 · 121/122 · 0 | 0 · 27/27 · 1 |
| `DA-B4-005` | code-rust | Treats the same docs but deletes the word, which breaks a placeholder in a code position. | 0 · 43/45 · 0 | 0 · 18/18 · 0 | 0 · 25/25 · 7 | 0 · 82/83 · 0 | 0 · 121/122 · 0 | 0 · 27/27 · 1 |
| `DA-B4-010` | code-java | Treats the same docs but deletes the word, which breaks a placeholder in a code position. | 0 · 43/45 · 0 | 0 · 18/18 · 0 | 0 · 25/25 · 7 | 0 · 82/83 · 0 | 0 · 121/122 · 0 | 0 · 27/27 · 1 |

### C1 boilerplate

**Picked:** `DA-C1-004` (code-go) on go; `DA-C1-005` (code-java) on java.

**Why:** A different rule for each kind of boilerplate: `DA-C1-004` for Go scaffolds (go), `DA-C1-005` for IDE templates (java). `DA-C1-005` touches 1 gold doc each on js-ts and cpp. That is inside the new limit, but cpp's 2 labelled rows do not justify changing a gold doc, so they stay untreated.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-C1-004` | code-go | **PICKED** | 0 · 1/1 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/80 · 0 | 0 · 0/2 · 0 | 0 · 0/0 · 0 |
| `DA-C1-005` | code-java | **PICKED** | 0 · 0/1 · 0 | 0 · 0/0 · 0 | 1 · 0/0 · 0 | 0 · 78/80 · 23 | 1 · 0/2 · 0 | 0 · 0/0 · 0 |
| `DA-C1-001` | code-java | Its 1 java row is treated by `DA-C1-005`. It touches 1 js-ts gold doc. | 0 · 0/1 · 0 | 0 · 0/0 · 0 | 1 · 0/0 · 0 | 0 · 1/80 · 1 | 0 · 0/2 · 0 | 0 · 0/0 · 0 |

### C2 repeated lines

**Picked:** nothing.

**Why:** 4 labelled rows (js-ts 3, cpp 1). The only rule was withdrawn.

### C3 truncated or broken document

**Picked:** `DA-C3-002` (code-go) on go.

**Why:** One candidate, Go only. It drops 16 rust, 20 python and 2 js-ts gold docs because it does not understand those languages.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-C3-002` | code-go | **PICKED** | 0 · 1/1 · 0 | 16 · 0/0 · 36 | 2 · 0/0 · 1 | 0 · 0/0 · 0 | 0 · 0/0 · 1 | 20 · 0/0 · 62 |

### C4 two documents joined

**Picked:** `DA-C4-002` (code-java) on java.

**Why:** One candidate, java only.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-C4-002` | code-java | **PICKED** | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 1/1 · 0 | 0 · 0/1 · 0 | 0 · 0/0 · 1 |

### D1 wrong language label

**Picked:** nothing.

**Why:** 8 labelled rows (js-ts 1, cpp 7). **Assumption: the language tag on a row is taken as correct, and no detector runs.** A rule on one document cannot tell that a label is wrong, so these rows wait for a language check at scale.

### D3 mixed language

**Picked:** nothing.

**Why:** No rule picked: `DISEASES.md` says to label it, not judge it.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-D3-001` | code-js-ts | A check that changes nothing. `DISEASES.md`: label it, do not judge it. | 0 · 0/1 · 0 | 0 · 0/0 · 0 | 0 · 0/27 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |

### E1 minified or generated code

**Picked:** `DA-E1-001` (code-go) on go; `DA-E1-004` (code-rust) on rust, python; `DA-E1-005` (code-go) on cpp; `DA-E1-006` (code-java) on java; `DA-E1-007` (code-java) on cpp; `DA-E1-008` (code-js-ts) on js-ts.

**Why:** A conflict: 8 rules overlap, each tuned to its own language. For each pack the sheet takes the smallest set that fixes the most labelled rows. Running all of them everywhere only adds drops nobody labelled. Rows still untreated: go 1, rust 6, js-ts 1, java 4, cpp 13, python 1. Those have no marker a rule can see.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-E1-001` | code-go | **PICKED** | 0 · 42/43 · 0 | 0 · 8/23 · 0 | 0 · 4/23 · 0 | 0 · 3/14 · 0 | 0 · 5/20 · 0 | 0 · 0/11 · 0 |
| `DA-E1-004` | code-rust | **PICKED** | 0 · 34/43 · 0 | 0 · 17/23 · 0 | 0 · 4/23 · 0 | 0 · 4/14 · 1 | 0 · 6/20 · 0 | 0 · 10/11 · 1 |
| `DA-E1-005` | code-go | **PICKED** | 0 · 41/43 · 0 | 0 · 14/23 · 0 | 0 · 3/23 · 0 | 0 · 6/14 · 1 | 0 · 6/20 · 0 | 0 · 0/11 · 0 |
| `DA-E1-006` | code-java | **PICKED** | 0 · 2/43 · 0 | 0 · 0/23 · 0 | 0 · 1/23 · 0 | 0 · 10/14 · 1 | 0 · 0/20 · 0 | 0 · 1/11 · 0 |
| `DA-E1-007` | code-java | **PICKED** | 0 · 34/43 · 0 | 0 · 9/23 · 0 | 0 · 4/23 · 0 | 0 · 8/14 · 1 | 0 · 4/20 · 0 | 0 · 0/11 · 0 |
| `DA-E1-008` | code-js-ts | **PICKED** | 3 · 37/43 · 17 | 0 · 14/23 · 0 | 0 · 22/23 · 6 | 0 · 3/14 · 0 | 1 · 6/20 · 1 | 1 · 0/11 · 2 |
| `DA-E1-002` | code-js-ts | On js-ts it treats 16 of 23 labelled rows; `DA-E1-008` treats 22 at the same 0 gold docs. | 0 · 32/43 · 0 | 0 · 8/23 · 0 | 0 · 16/23 · 4 | 0 · 3/14 · 1 | 0 · 2/20 · 0 | 0 · 3/11 · 1 |
| `DA-E1-003` | code-python | Adds no row: every row it hits on python is hit by `DA-E1-004`. It crashes on 8 docs because it returns None, which the team tool rejects. | 0 · 1/43 · 0 | 0 · 0/23 · 0 | 0 · 1/23 · 0 | 0 · 1/14 · 0 | 0 · 0/20 · 0 | 0 · 8/11 · 0 |

### E2 data blobs

**Picked:** `DA-E2-001` (code-go) on all 6 packs.

**Why:** `DA-E2-001` covers every row of `DA-E2-003`.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-E2-001` | code-go | **PICKED** | 0 · 7/7 · 0 | 0 · 0/2 · 0 | 0 · 0/1 · 0 | 0 · 0/1 · 0 | 0 · 1/1 · 0 | 0 · 0/1 · 0 |
| `DA-E2-003` | code-go | Its rows are a subset of `DA-E2-001` (go 5 of 7). | 0 · 5/7 · 0 | 0 · 0/2 · 0 | 0 · 0/1 · 0 | 0 · 0/1 · 0 | 0 · 1/1 · 0 | 0 · 0/1 · 0 |

### E3 secrets

**Picked:** `DA-E3-003` (code-go) on all 6 packs; `DA-E3-004` (code-go) on all 6 packs.

**Why:** A placeholder, never a drop. `DA-E3-003` handles known formats and base32 seeds. `DA-E3-004` is new, written for this sheet, because no submitted rule could do this: it separates real keys from dummy values by the shape of the value, and touches 0 gold docs. Of the 12 labelled rows: 5 are real secrets and all 5 are replaced (go 1, rust 1, js-ts 2, java 1). 6 js-ts rows already hold `<PASSWORD>` or `<KEY>`, which the B4 pick replaces. 1 js-ts row has neither a value nor a placeholder that a rule can see. The code-go `medicine.md` now holds both in one E3 section; that section gives the same text as these two rules on all 3000 docs.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-E3-003` | code-go | **PICKED** | 0 · 1/1 · 0 | 0 · 0/1 · 0 | 0 · 0/9 · 0 | 0 · 0/1 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |
| `DA-E3-004` | code-go | **PICKED** | 0 · 0/1 · 0 | 0 · 1/1 · 0 | 0 · 2/9 · 0 | 0 · 1/1 · 1 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |
| `DA-E3-001` | code-js-ts | Drops the file, and takes any 8+ character value: it touches 1 js-ts gold doc over a dummy `AuthToken` and 1 go gold doc over `Password: "password"`. Replaced by `DA-E3-004`, which keeps the file and touches no gold doc. | 1 · 0/1 · 0 | 0 · 0/1 · 0 | 1 · 4/9 · 1 | 0 · 0/1 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |

### E4 repeated licence headers

**Picked:** `DA-E4-005` (code-go) on go; `DA-E4-007` (code-js-ts) on js-ts; `DA-E4-009` (code-go) on java; `DA-E4-010` (code-rust) on go, rust, java, cpp, python.

**Why:** The biggest conflict, and the one rule that was changed. `DA-E4-004` had the widest reach and the best numbers, and it was deleting real code (see its row). So `DA-E4-010` is that rule with 3 bugs fixed: gold still 0, 2 more labelled rows, 0 docs with code changed, idempotent. It is the base on 5 packs. `DA-E4-005` runs first on go because it reads Go headers and keeps build tags. `DA-E4-009` adds java rows it misses. **js-ts:** the readers mark real licence headers clean, so every rule touches its gold. `DA-E4-007` treats 6 of 9 rows for 1 gold doc, a 21-line header, inside the limit of 2. Rows still untreated are short notes of 2 to 4 lines and blocks that are mostly not licence text: go 18, js-ts 3, java 16, cpp 82, python 21.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-E4-005` | code-go | **PICKED** | 0 · 56/76 · 3 | 1 · 19/22 · 0 | 4 · 9/9 · 4 | 0 · 81/103 · 3 | 1 · 91/176 · 1 | 0 · 0/70 · 0 |
| `DA-E4-007` | code-js-ts | **PICKED** | 0 · 42/76 · 1 | 0 · 12/22 · 0 | 1 · 6/9 · 1 | 0 · 61/103 · 0 | 0 · 57/176 · 0 | 0 · 0/70 · 0 |
| `DA-E4-009` | code-go | **PICKED** | 0 · 53/76 · 2 | 0 · 12/22 · 0 | 1 · 7/9 · 3 | 0 · 82/103 · 2 | 1 · 85/176 · 1 | 0 · 0/70 · 0 |
| `DA-E4-010` | code-rust | **PICKED** | 0 · 50/76 · 2 | 0 · 22/22 · 0 | 4 · 7/9 · 3 | 0 · 81/103 · 2 | 0 · 94/176 · 1 | 0 · 49/70 · 4 |
| `DA-E4-001` | code-cpp | Cannot run: needs a second `header` argument, and it has no detection logic. | crash 500 | crash 500 | crash 500 | crash 500 | crash 500 | crash 500 |
| `DA-E4-002` | code-java | Touches gold on go (1) and js-ts (5). Adds no java row beyond the picks. | 1 · 9/76 · 0 | 0 · 0/22 · 0 | 5 · 1/9 · 2 | 0 · 37/103 · 6 | 0 · 0/176 · 0 | 0 · 0/70 · 0 |
| `DA-E4-003` | code-java | **BLOCKED.** Fails with disputed docs left in: java 2 of 138, limit 1. Only one reader disputes those 2. Would add 13 java rows, 8 of them labelled clean by another reader. Needs: do short licence notes count as E4? | 5 · 45/76 · 15 | 2 · 10/22 · 2 | 8 · 6/9 · 4 | 0 · 48/103 · 10 | 5 · 79/176 · 14 | 0 · 0/70 · 0 |
| `DA-E4-004` | code-rust | **Bug: deletes real code.** It treats `#` lines as comments, so on 20 cpp and 2 rust docs it removes `#include`, `#ifndef`, `#pragma once`, `#[derive]`. It also removes shebang, encoding and Go build lines, and needs 2 runs on stacked headers. The gold sets cannot see this. Replaced by `DA-E4-010`. | 0 · 50/76 · 2 | 0 · 21/22 · 0 | 4 · 7/9 · 3 | 0 · 81/103 · 2 | 0 · 93/176 · 5 | 0 · 49/70 · 4 |
| `DA-E4-006` | code-java | On js-ts it gives the same text as `DA-E4-007` on all 6 docs. Elsewhere its rows are treated by `DA-E4-010`: it never acts inside the sheet. | 0 · 23/76 · 0 | 0 · 3/22 · 0 | 1 · 6/9 · 1 | 0 · 72/103 · 0 | 0 · 47/176 · 0 | 0 · 0/70 · 0 |
| `DA-E4-008` | code-python | Changes 0 documents on all 6 packs. | 0 · 0/76 · 0 | 0 · 0/22 · 0 | 0 · 0/9 · 0 | 0 · 0/103 · 0 | 0 · 0/176 · 0 | 0 · 0/70 · 0 |

### E5 broken encoding in code

**Picked:** nothing.

**Why:** 2 labelled rows (go 1, cpp 1). No medicine exists. go's row sits in the same comment that `DA-A4-002` removes.

### E6 not code

**Picked:** nothing.

**Why:** 1 labelled row (python). No medicine exists.

### F1 personal data

**Picked:** nothing.

**Why:** Nothing active. `DA-F1-001` is the same regex as a B4 rule, so its 83 python, 2 cpp and 1 go rows are treated by the B4 pick. `DA-F1-003` is the only rule for names, and it is blocked: see its row. So java's 93 author-name rows stay until the team decides. The `DISEASES.md` definition lists emails, phones, addresses and IDs, not names.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-F1-001` | code-python | Same regex as `DA-B4-010`. One python reader labels the placeholders F1; the B4 pick treats the same 377 docs. | 0 · 1/2 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 7 | 0 · 10/94 · 0 | 0 · 2/2 · 0 | 0 · 83/83 · 1 |
| `DA-F1-003` | code-java | **BLOCKED.** Fails with disputed docs left in: java 16 of 138, limit 1. Only one reader calls those sick, and those docs left the java gold set with no note, so `gold_notes.py` fails. Needs: are author names personal data? | 1 · 1/2 · 0 | 1 · 0/0 · 0 | 2 · 0/0 · 1 | 0 · 93/94 · 37 | 5 · 0/2 · 0 | 1 · 5/83 · 1 |

### F2 benchmark leak

**Picked:** nothing.

**Why:** Nothing active: BLOCKED on the G9 fingerprints. The instructor ruled that "leetcode" alone is not a benchmark leak, so the only candidate, which reads the path, is rejected. A real F2 rule has to match known benchmark problems (HumanEval, MBPP, LiveCodeBench, SWE-bench), and none exists yet. The labelled rows in go, rust, js-ts and python need re-reading by their annotators.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-F2-001` | code-go | **Rejected by the instructor.** The word "leetcode" alone is not a benchmark leak. F2 needs a problem or solution from a known benchmark test set, named in the evidence. A real rule is BLOCKED on the G9 fingerprints. | 0 · 6/7 · 1 | 0 · 4/4 · 1 | 0 · 1/1 · 1 | 4 · 0/0 · 0 | 11 · 0/0 · 0 | 0 · 3/5 · 2 |

### F3 harmful content

**Picked:** nothing.

**Why:** 4 labelled rows (go 1, js-ts 1, cpp 2). No medicine exists; it needs a harm classifier.

### H3 same content in another source

**Picked:** nothing.

**Why:** Nothing active. The instructor ruled that a vendored copy is not a disease by itself and needs no proof of which copy is the original. If the same file is in the pack twice, the second copy is H1 or H2; otherwise it is clean. So vendored files stay.

| rule | source | decision | go | rust | js-ts | java | cpp | python |
|---|---|---|---|---|---|---|---|---|
| `DA-H3-001` | code-go | **Rejected by the instructor.** A vendored copy is not a disease by itself. Only the same file twice in a pack counts, as H1 or H2 on the second copy. | 0 · 38/38 · 17 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 | 0 · 0/0 · 0 |

## Medicines that could not run

| medicine | why |
|---|---|
| code-go B4, E1, E2, E4 of one sheet | Need reviewed patches or human confirmation as arguments, so they are hand edits, not rules. Its B3 runs and is listed above. |
| code-js-ts E4 of one sheet | The section has only a regex and no function, so nothing can run. |
| `DA-E4-001` | Needs a second `header` argument. |
| code-python A1, A2, A3, A4, B1, C2, E2, E3 of one sheet | Withdrawn: no longer in that `medicine.md`. |
| `cure` and `drop_if_nothing_left` of one code-java sheet | `cure` is that sheet's own pipeline of its rules. `drop_if_nothing_left` has no disease code, so nothing labels it. |
