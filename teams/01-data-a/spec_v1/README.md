# Spec v1: structure, requirements and how to run it

Status: **DRAFT.** A proposal for how Data A's Spec v1 is laid out and what a rule must show before it is approved. It follows `spec_v1_TEMPLATE.md`. The code family is filled in as the worked example; other families can copy the form.

## Layout

```
teams/01-data-a/
  spec_v1/
    README.md               this file
    spec_v1_<family>.md     scope, order, conflicts, open items, freeze state
    medicine_<family>.md    the runnable rules: one block per rule, in run order
    decisions_<family>.md   why each rule was picked or not, for each disease
    specv1.md               the four family sheets collated: what spec_v1/tools/build_clean.py reads
    clean.py                the cleaner, generated from specv1.md, with the scope table at the top
    README_clean.md         how to build, test and run clean.py, step by step
    run_clean.py            runs the cleaner on one pack
    tests/                  unit tests on made-up values
    results/cleaner/harm_tests.md   each rule on the gold sets of its packs, each clean.py function, and clean()
    results/cleaner/specv1_<pack>_harm.json   the reports behind harm_tests.md: IDs and digests only
    results/sheets/<pack>_harm.json   harm_test.py --report on the sheet: IDs and digests only
    results/sheets/stress_<pack>_harm.json   the same, with disputed docs left in
    results/sheets/evidence.json, inputs_manifest.json   every medicine on every pack; digest of every input
    scripts/                what makes the sheet and results: see scripts/README.md
  tools/                    build, harm test run, F1 rule, checks
```

Families: `code`, `en`, `math`. Science and Indic follow when their owners are set.

**One source for each fact.** Rules live only in `medicine_<family>.md`. The registry of the template's §3 is the table at the top of that file, so it cannot drift from the code. Numbers come from `results/`, not from hand-typed tables.

`build_spec_v1.py` and `run_harm_suite.py` on `g1-harm-test` still use `spec/spec_v1.md`. This layout does not use it for now: see "Decide" below.

## What every rule must have

A block in the sheet with these fields, and a `medicine(doc) -> (action, text)`. `harm_test.py --rule all` and `medicine_conflicts.py --sheet` already read this form.

| field | meaning |
|---|---|
| `RULE_ID` | Stable `DA-<code>-<nnn>`. Never reused. |
| `CODE` | Disease code from `DISEASES.md`. |
| `ACTION` | `fix`, `drop` or `fix+drop`. |
| `STAGE` | Stage below. The run order is section order. |
| `STATUS` | `CANDIDATE`, `APPROVED`, `FAILED`, `BLOCKED` or `DEFERRED`. |
| `LANGS` | Language tags it runs on. A row outside passes unchanged. |
| `ORIGIN` | Packs it runs on, comma separated. |
| `SOURCE` | Pack whose medicine it came from. |
| `AUTHOR` | Code field for `medicine_conflicts.py`. Not used in any text. |

Around the block: disease with counts and `doc_id` examples, medicine in words, action, harm test per pack, side effects. Examples give `doc_id` and offset only. E3 and F1 give type and offset only, never the value.

## Stages

| stage | what | why here |
|---|---|---|
| 00 guard | `LANGS` and the pack scope. | A rule must not touch a language it was not tested on. The language tag is taken as correct. |
| 10 characters | A1, A2, A4, A6. | Later patterns need clean characters. |
| 20 markup | B3. | Later rules expect the file to start at its real first line. |
| 30 source | Drops first (E1, E2, C3, C4), then strips (E4, C1). | A generated file with its banner inside the licence survives if the licence goes first. |
| 40 data safety | B4, E3, and F1 if approved. | A6 can turn an obfuscated address into plain text, so this runs after it. |
| 90 post-clean | A test, not a rule: no empty docs, no doc left with no code. | Catches what the gold test cannot. |

## When a rule is APPROVED

All of these, on every pack in `ORIGIN`. Anything else stays `CANDIDATE`, or `BLOCKED` when it waits on an answer.

1. **Within the limit,** alone and in the whole sheet: changed + dropped at most `max(1, floor(1% of gold))`. An empty gold set is NOT TESTABLE, never PASS. This is the limit in `harm_test.py`; §2.5 of the template still says 1.0% and needs updating.
2. **Treats real rows:** labelled rows treated out of labelled rows, per pack. A rule that does nothing also passes the limit.
3. **Does not damage what it keeps:** comment rules leave code unchanged, which is checked with comments stripped. Gold cannot show this. `DA-E4-004` passed gold and deleted `#include`.
4. **Idempotent:** a second run changes nothing.
5. **Not resting on a dispute:** it still passes with the disputed docs left in, or the reason is written down. A reader's own dispute must not be what makes their rule pass.
6. **Reviewed** by someone other than its author, with commit and digests recorded.

## Assumptions

- **Language tags are correct.** No detector runs. D1 rows wait for a language check at scale.
- **F2 is BLOCKED on the G9 fingerprints.** The word "leetcode" alone is not a leak (instructor, 30 Oct).
- **H3 has no rule.** A vendored copy is not a disease by itself. The same file twice in a pack is H1 or H2 on the second copy (instructor, 30 Oct).
- **A 0 result is a bound, not proof.** With n gold docs and 0 hits, the harm rate is only shown to be below about 3/n. Show this next to the result. About 300 docs are needed to show 1%.

## What to report per pack, never pooled

Gold size, limit, changed, dropped, affected IDs, pack fixed / dropped / untouched, labelled rows treated, and the stress result with disputed docs left in. Each pack passes or fails on its own.

## Run the harm test on a sheet

```
python -I teams/01-data-a/tools/harm_test.py --pack <pack>.parquet --gold teams/01-data-a/gold/<pack>_gold.csv \
  --rules teams/01-data-a/spec_v1/sheets/medicine_code.md --rule all --report teams/01-data-a/spec_v1/results/sheets/<pack>_harm.json
python -I teams/01-data-a/tools/medicine_conflicts.py --packs code- --sheet teams/01-data-a/spec_v1/sheets/medicine_code.md --out <file>
```

These tools are on `g1-harm-test`, not on this base branch. Results here were made with them at `bae5163`. To remake the sheet and all results, see [scripts/README.md](scripts/README.md).

## Decide

| question | proposal |
|---|---|
| Is the sheet the source for Spec v1? | Yes. `build_spec_v1.py` lists every submission as a non-executable draft (about 3,800 lines) and stays useful for inventory. The sheet is what runs. |
| Should `run_harm_suite.py` read sheets? | Yes. It now tests registry rules one at a time and never the combined sheet, so someone has to run `harm_test.py --rule all` as well. |
| Do `STAGE` and `STATUS` apply to the other sheets? | Yes, so all families have one form. |
| Freeze date: 31 Oct or Week 2? | The template says 31 Oct, and 24 code rules still need a reviewer. |

## The cleaner

`clean.py` is the cleaner. `tools/build_clean.py` generates it from `specv1.md`, which collates the four family sheets, so **add rules to a sheet, never to `clean.py`**.

A rule names the packs it applies to (instructor, 31 Oct): `SPEC_PACKS` in its block, and for a math rule its `ORIGIN` packs too. The build puts those pack IDs in one table, `SCOPE`, at the top of `clean.py`, and each rule reads its entry there. A document goes to the family of its `pack_id` and runs that family's rules in sheet order. A document with a missing or unknown `pack_id` passes unchanged and is not eligible for release. `run_clean.py` takes `pack_id` from the file name when a pack has no such column. `make_harm_tests.py` tests each rule only on the gold sets of the packs in its `SCOPE` entry. It also runs every rule that does not apply to a pack on that whole pack, where it must change nothing.

| where | what | who changes it |
|---|---|---|
| `medicine_<family>.md` | The rules of one family: `code`, `english`, `math`, `sci` | The PR for that family |
| `specv1.md` | The four sheets collated, with the packs of each rule | The pipeline owner |
| `decisions_<family>.md` | Why each rule was picked or not | The same PR |
| `tools/f1_rule.py` | The shared F1 rule; `SCOPE` runs it on the code, math and science packs | A PR that names the family it adds |
| `clean.py`, `results/cleaner/harm_tests.md`, `results/cleaner/specv1_*` | Generated | Only the rebuild step, after a merge |

## Run it

Step by step, with every option, output and error: [README_clean.md](README_clean.md).

```
pip install pyarrow pytest tree-sitter-language-pack ftfy
python spec_v1/tools/build_clean.py
python -m pytest spec_v1/tests
python spec_v1/run_clean.py --pack <pack>.parquet --out out
python spec_v1/tools/make_harm_tests.py <g1-harm-test checkout> <folder with the packs> [<another folder with packs> ...]
```

Paths start at `teams/01-data-a/`. Run `make_harm_tests.py` where all 13 packs are: a pack it cannot find is listed as not run in `harm_tests.md`. `ftfy` is needed once the English A3 rule is in. `make_harm_tests.py` uses `harm_test.py`, which is on `g1-harm-test` until PR 140 merges. The packs are not in the repo, so get your link from the lab plan sheet.

## Add your medicines without double work

1. **Check first.** Look at the open PRs to `g1-specv1`. If a PR already covers your family and code, comment there instead of starting again.
2. **Claim it.** Open a draft PR to `g1-specv1` early, titled `medicine_<family>: <codes>`. Only one open PR per family sheet at a time, so sheets do not conflict.
3. **Put each rule in your family's sheet, in the form of `medicine_code.md`,** at the place its stage says. Add your sheet to this folder if your family has none yet:
   - **English:** the sheet is on `g1-en-medicines`. Move it to `medicine_en.md`.
   - **Math:** make `medicine_math.md`. The finemath sheet has code fragments and no functions, so each needs writing as a `medicine(doc)`.
   - **Science:** make `medicine_sci.md`: one medicine from all 500 rows, as TSAI ruled. The 5 diagnosis PRs stay as they are.
   - **Code:** add to `medicine_code.md`. Sheets that came after it still need checking against it.
4. **Resolve conflicts before you ask for review.** Run `medicine_conflicts.py --packs <family prefix> --sheet <your sheet>`, then for each code with more than one rule:

   | what you find | what to do |
   |---|---|
   | Same text on every doc | Keep one. Say so in the decisions file. |
   | They fix different rows | Keep both, as two blocks. |
   | They disagree on the same rows | Keep the one that treats the most labelled rows within the limit. On a tie, read the code. |
   | One passes only because its supporter's dispute took docs out of gold | Hold it as `BLOCKED`. |
   | It needs an answer from TSAI | Hold it as `BLOCKED`, with the question. |

5. **Do not edit someone else's rule to change what it does.** Add a new block and say why in the decisions file.
6. **In your PR, change only your sheet, your decisions file and your tests.** Leave `clean.py` and everything in `results/cleaner/` out: two PRs regenerating them will always conflict. Paste your harm results in the PR text.
7. **After a merge,** whoever merges reruns the steps in "Run it" and commits the generated files.

Each rule needs the fields in "What every rule must have" above, and has to meet the bar in "When a rule is APPROVED".

**Rule IDs:** an ID only has to be unique inside its sheet. `clean.py` adds the family, so `DA-A2-007` in two families does not clash. Registry IDs get renumbered, so a sheet's ID is a label and not a link to the registry.

## Regex: which diseases, and how

| use | diseases | how |
|---|---|---|
| Regex alone is enough | A1, A2, A4, A5, A6, B1, B3 | A fixed character or token. Replace only that. |
| Regex, with care | B2, B4, E1, E2, E4, C2 | Anchor it to the header or to a known marker. Check it does not touch valid code or markup. |
| Regex plus tree-sitter, in code | F1, and anything that should only touch comments or strings | The regex finds the value and the tree says where it sits. Leave it alone if it is in code. |
| Regex finds some, not all | C1, C3, C5, E3 | Phrase lists and shapes fit the sites seen so far. Report what is left. |
| Library | A3 | `ftfy`, as the English sheet does. |
| Regex does not work | C4, D1, D3, D4, D5, F3, H1, H2, H3 | Label it. These need a whole-pack check, a language model or a classifier. |
| Needs G9 | F2 | Blocked on the benchmark fingerprints. |

Try a pattern before you write the rule. This prints counts and doc_ids, never text:

```
python tools/regex_check.py --pack <pack>.parquet --gold <gold>.csv --labels <diagnosis/submissions/pack> --code E4 --regex "(?i)copyright"
python tools/regex_check.py --pack <pack>.parquet --gold <gold>.csv --labels <diagnosis/submissions/pack> --code E3 --regex "AKIA" --where string
```

Then:
1. **Read the misses, not only the hits.** A rule can match every labelled row and still delete real code. `DA-E4-004` passed gold and removed `#include`.
2. **Keep the match narrow.** Anchor it, set `LANGS`, and change only the bad part.
3. **Check it is idempotent.** A second run must change nothing.
4. **Add a unit test** with made-up values in `tests/`: one sick case and one look-alike that must stay.
5. **Run the harm test.** The limit is `max(1 document, 1%)` of the pack's gold, per pack, never pooled. An empty gold set is not testable.

## F1

`tools/f1_rule.py` follows the TSAI decision: `<PHONE>`, `<EMAIL>` and `<ADDRESS>` for a private person, drop a personal listing, keep organisations and public offices.

- **Where it runs:** on the code packs, with tree-sitter, and on the math and science packs, with the prose path (`_F1_PROSE`: `math-*` with `en`, `sci-*` with `eng_Latn`), as TSAI approved on 1 Nov. `SHARED_F1_FAMILIES` in `tools/build_clean.py` puts those packs in its `SCOPE` entry; on science it runs after `DA-F1-006`, so the reviewed drops stay. English keeps its own F1, `DA-F1-005`, and never gets the shared rule. The prose path is keyed by `pack_id` because English shares the `en` tag; a doc with no `pack_id` never takes it. To add a family, add it to `SHARED_F1_FAMILIES` and to `_F1_LANGS` (code) or `_F1_PROSE` (prose), run the harm test, and put the results in your PR.
- **Prose path:** a value is private when a private label sits on it (`Home:`, `Cell:`, `Daytime Phone`), when it is in a person's contact card (each field on its own line, two personal fields or more), or in a `| Name | Telephone |` table. It is kept when its block or the heading above names an organisation or public office, and for toll-free numbers, role mailboxes and example domains. A page mostly of `SURNAME, Forenames, age, address` entries is dropped. It misses a private phone in running prose with no label, non-North-American numbers outside people tables, and addresses that are not "number + name + street type".
- **Never write a private value** in a commit, a PR or chat. Use doc_ids and offsets, as `regex_check.py` does.
- **Known limits:** it misses lower-case addresses, and it reads "8 Bit Drive" as an address. An email at a company domain counts as personal unless it is a role address like `support@`. Names are not in the TSAI list, so it leaves them.
- **B4:** in `clean.py`, the code B4 rule leaves `<EMAIL>` alone, because it is now the F1 tag, and still replaces `<NAME>`, `<KEY>` and `<PASSWORD>`. Before this, a second run turned the tag into `user@example.com`. `tools/build_clean.py` makes this change, and `medicine_code.md` still has the old rule until the team agrees. 26 docs labelled B4 hold only `<EMAIL>`, so they keep the token.
