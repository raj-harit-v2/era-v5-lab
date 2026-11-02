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

