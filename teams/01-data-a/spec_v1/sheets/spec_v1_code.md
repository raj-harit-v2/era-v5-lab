# Spec v1: code family

> **Status:** DRAFT, not frozen. All 24 rules are `CANDIDATE`.
> **Tested on:** `g1-harm-test` at `bae5163`, gold sets at that commit.
> **Sections follow `spec_v1_TEMPLATE.md`.** §3 and §4 are in [medicine_code.md](medicine_code.md); reasons are in [decisions_code.md](decisions_code.md).

## 1. Scope and inputs

| pack | language tags | gold docs | limit | gold sha256 | pack sha256 |
|---|---|---:|---:|---|---|
| `code-go` | go | 163 | 1 | `81942db337e2e191` | `30fc352199a6b377` |
| `code-rust` | rust | 78 | 1 | `2fbb0779f2da11fb` | `c5822b7df0e76a6b` |
| `code-js-ts` | javascript, typescript | 204 | 2 | `518cf5c367f088a3` | `4aa4dea19a83b8db` |
| `code-java` | java | 116 | 1 | `223d555f68e1bd7e` | `739dc95cdb424184` |
| `code-cpp` | cpp | 120 | 1 | `0f53271f3bebb4b5` | `2aa25660b81ccaea` |
| `code-python` | python | 46 | 1 | `de8d9ade6605d9b7` | `b79698620cd7526f` |

**Inputs:** the latest `medicine.md` of the 12 code sheets and the latest labels of the 17 code label sheets in the open diagnosis PRs. Only js-ts reaches the gold target of about 200 documents.

**Assumption:** the language tag on a row is correct. No detector runs.

## 3 and 4. Registry and rule cards

The table at the top of [medicine_code.md](medicine_code.md) is the registry. Each section below it is the rule card: disease, medicine in words and code, action, harm test per pack, side effects, source.

Fields of the template's rule card that are still open for every rule: independent reviewer, and rule commit (set when the sheet is merged).

## 5. Execution plan and conflicts

| stage | rules, in order | status |
|---|---|---|
| 00 guard | `LANGS` in each rule | tested: a row outside `LANGS` passes unchanged |
| 10 characters | `DA-A1-001`, `DA-A2-007`, `DA-A6-001`, `DA-A4-002`, `DA-A4-003` (java) | in the combined test |
| 20 markup | `DA-B3-001` | in the combined test |
| 30 source, drops | `DA-E1-001` (go), `DA-E1-004` (rust, python), `DA-E1-008` (js-ts), `DA-E1-006` (java), `DA-E1-005`, `DA-E1-007` (cpp), `DA-E2-001`, `DA-C3-002` (go), `DA-C4-002` (java) | in the combined test |
| 30 source, strips | `DA-E4-005` (go), `DA-E4-010` (go, rust, java, cpp, python), `DA-E4-009` (java), `DA-E4-007` (js-ts), `DA-C1-004` (go), `DA-C1-005` (java) | in the combined test |
| 40 data safety | `DA-B4-009`, `DA-E3-003`, `DA-E3-004` | in the combined test |
| 90 post-clean | a test, not a rule | 0 empty docs on all packs. No doc lost its last code: 15 changed docs have only comments and imports, and had no other code before either (go 4, rust 1, java 2, cpp 7, python 1) |

**Conflict ledger**

| rule A | rule B | case | decision | check |
|---|---|---|---|---|
| E1, E2, C3, C4 drops | E4 strips | A generated file with its banner inside the licence block | Drops first | Reversing the order changes drop decisions on go 5, rust 1, cpp 3, python 1 docs |
| `DA-A6-001` | `DA-B4-009`, `DA-E3-*` | A6 can make an obfuscated address readable | A6 first | Stage order |
| `DA-B3-001` | B3 rules that also fill placeholders | Two rules would rewrite `<NAME>` with different words | B3 removes markers only; B4 owns placeholders | 0 placeholders left on all packs |
| `DA-E4-005` | `DA-E4-010` on go | Both remove licence blocks | 005 first: it reads Go headers and keeps build tags | 010 acts on 2 go docs after it |
| `DA-E4-010` | `DA-E4-009` on java | Blocks 010 misses | 010 first | 009 acts on 5 java docs after it |
| `DA-E1-005` | `DA-E1-007` on cpp | Overlap on generated files | 005 first; 007 adds long-line files | 007 acts on 1 cpp doc after it |
| `DA-E3-003` | `DA-E3-004` | Known formats and shape-based search | 003 first | Each replaces what the other cannot; 5 real secrets replaced |
| `DA-A4-002` | `DA-A4-003` | 003 changes an author-quoted U+FFFD on go (ruling 7) | 003 on java only | Scoped by `LANGS` |

**Combined harm test** (`harm_test.py --rule all`; files in [results/sheets/](../results/sheets/), made by [scripts/run_all.py](../scripts/run_all.py)):

| pack | gold harm | limit | result | with disputed docs left in | fixed / dropped / untouched | labelled rows treated |
|---|---|---:|---|---|---|---|
| go | 0 / 163 | 1 | PASS | 1 / 171 | 265 / 44 / 191 | 309 / 337 |
| rust | 0 / 78 | 1 | PASS | 0 / 78 | 238 / 17 / 245 | 255 / 259 |
| js-ts | 1 / 204 | 2 | PASS | 3 / 207, **over** | 264 / 22 / 214 | 286 / 296 |
| java | 0 / 116 | 1 | PASS | 2 / 138, **over** | 350 / 11 / 139 | 361 / 384 |
| cpp | 0 / 120 | 1 | PASS | 0 / 124 | 343 / 10 / 147 | 353 / 378 |
| python | 0 / 46 | 1 | PASS | 1 / 51 | 325 / 16 / 159 | 336 / 343 |

`run_harm_suite.py` on single rules: go 14 PASS, java 18 PASS, js-ts 10 PASS, python 4 PASS, cpp 4 PASS and `DA-E4-001` ERROR (needs a second argument), rust 5 ERROR (no rules file from the extractor). It does not test the combined sheet.

With 0 hits the harm rate is only shown to be below about 3/n: python 6.5%, rust 3.8%, java 2.6%, cpp 2.5%, go 1.8%, js-ts 1.5%.

## 6. Dependencies

- **F2 is BLOCKED on the G9 fingerprints.** No F2 rule is in the sheet, and none is claimed to pass.
- **G2 Indic:** not part of this family.

## 7. Coverage and open items

**Rules:** 24 `CANDIDATE`, 0 `APPROVED`. Reasons for each rule not picked are in [decisions_code.md](decisions_code.md).

| rule or disease | status | why | next |
|---|---|---|---|
| `DA-H3-001` | rejected | Instructor, 30 Oct: a vendored copy is not a disease by itself | Re-read the H3 rows |
| `DA-F2-001` | rejected | Instructor, 30 Oct: "leetcode" alone is not a benchmark leak | Re-read the F2 rows; real rule waits on G9 |
| `DA-F1-003` | BLOCKED | Over the limit with disputed docs left in: java 16 of 138 | Question 1 |
| `DA-E4-003` | BLOCKED | Over the limit with disputed docs left in: java 2 of 138 | Question 2 |
| D1 | DEFERRED | The language tag is assumed correct | Language check at scale |
| A5, B1, C2, E5, E6 | no rule | 4 or fewer labelled rows per pack | None for v1 |
| F3 | no rule | Needs a harm classifier | Week 2 |

**Questions for the instructor**

| # | question | changes |
|---|---|---|
| 1 | Are author names personal data? | `DA-F1-003` on java (93 rows), and java gold must be re-judged |
| 2 | Do short licence notes of 2 to 4 lines count as E4? | A short-note rule fails the limit on most packs; go 21, java 12, cpp 35, python 10 more rows |
| 3 | Are IDE template lines C1 in every pack? | Only one java reader labels them: 78 of java's 80 C1 rows |

From the template, still open: gold target per pack or per language, and rule interaction and single-pass acceptance.

**For review**

- `DA-E1-008` drops 3 js-ts docs on the path alone (`node_modules`, `build`, `generated`). Should `node_modules` and `vendor` stay, given the H3 ruling?
- `DA-E4-007` changes 1 js-ts gold doc: a 21-line licence header its 2 gold readers kept.
- Several picks come from the compiler's own code-go sheet. See the note in [decisions_code.md](decisions_code.md).

## 8. Freeze checklist

- [x] Gold CSVs: IDs only, coverage shortfalls disclosed above.
- [x] Medicines inventoried, conflicts resolved or tracked.
- [x] Each rule has runnable code and labelled rows it treats.
- [x] Per-pack harm results within the limit.
- [x] Changed and dropped gold IDs can be audited: `results/`.
- [x] Combined order tested.
- [x] F2 status disclosed.
- [ ] Java gold passes `gold_notes.py`: 18 problems, docs left with no note.
- [ ] Gold rebuilt after H3 and F2 rows are re-read, and all tests rerun.
- [ ] Rule IDs committed to the registry: `DA-E3-004`, `DA-E4-009`, `DA-E4-010`, `DA-C4-002` are provisional.
- [ ] Independent reviewer for all 24 rules.
- [ ] Questions 1 to 3 answered.

## 9. Handoff

Week 2 and later need the frozen sheet, its digests and `results/`. Removing a licence header removes the notice that licence asks to keep, so the licence must be recorded in metadata before cleaning at scale.
