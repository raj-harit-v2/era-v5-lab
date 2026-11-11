# indic_rules: Data B's Indic rules for spec v1

Task 1 of Data B's week 2 (#211). It hands Data B's Indic cleaning rules to Data A in their spec v1 rule form
(`teams/01-data-a/spec_v1/sheets/medicine_english.md`, PR #194), so they can go into `clean.py`.

| File | What it holds |
|---|---|
| `medicine_indic.md` | The 260 rules that are ready, in Data A's form and run order |
| `rules_status.md` | All 373 Indic medicines from the open diagnosis PRs, with the reason each one is in or not yet |
| `load_rules.py` | Reads the rules out of `medicine_indic.md`, so tests and `clean.py` use the sheet itself |
| `test_indic_rules.py` | 7 checks on every rule, with made-up text |
| `rewrites/` | Medicine sheets the harm tool could not read, rewritten in its format under TSAI's ruling 3 on #211. A rewrite's passing rules join once its author OKs it in their own PR (#46, #70 and #112 have; #58 and #83 have not, so theirs wait for the next spec) |

## Which rules are in
A rule is in when it passes the harm test on **its own pack's gold set at today's size**: the gold sets rebuilt on
3 Nov (#222, main `ea7b533`; `teams/02-data-b` is the same on `195f4ff`), unchanged on main since. TSAI (#240, 4 Nov
17:47 IST): only a result on today's gold counts.
- 194 rules: re-run on today's gold set and passed: 135 by millermuttu, 43 by the Data B rules owner (Pritish52718),
  6 by shankarpandala, and 10 by the author of #91 (the author's own run, written in words, not the tool's output).
  Each result is linked in its rule.
- 49 rules: the author's own `medicine.md` reports a pass on today's gold set.
- 17 rules: Data B's rewrites of #70 (10), #112 (5) and #46 (2), run on today's gold set and OK'd by their authors.

Every rule's harm line shows its changed and dropped counts and its result.

From the 262 published on 4 Nov: 262 − 5 out (2 that add a ZWJ, #63 F1, 2 F2) + 2 (#46) + 5 (#112) + 1 (#30 A6)
+ 1 (#256 C1) + 1 (#177 C1) = 267 (pushed at `9d32e3f`), then − 7 that convert between a visarga and a colon
(TSAI on #240, 5 Nov) = **260**. #45's other 14 rules stay in: millermuttu's run before the cut-off said "15 PASS"
(#240), and the Data B rules owner's run of 5 Nov gives the table.

**Out of spec v1, by TSAI's rulings of 4 Nov** (each is in `rules_status.md` with its reason):
- Rules that add a ZWJ by design (TSAI, G2 4 Nov 14:20 IST: for v1 the Gate 2 joiner check stays): `DB-G2-001` (#64),
  `DB-G2-002` (#138), and the G2 rules of #30 and #112. Held for v2.
- A rule that fails on today's gold: `DB-F1-005` (#63 F1, changes 2 of 114).
- Rules that need benchmark text to run, which the eval firewall keeps out of the repo: `DB-F2-001` (#45), `DB-F2-002` (#80).
  They wait for the next spec.

**Changed by TSAI's #240 review of 5 Nov:**
- A visarga used as a colon is clean, in every script, and in spec v1 no rule converts between a visarga and a colon,
  in either direction (TSAI's review and TSAI's reply on #240, 5 Nov). Seven rules are out and wait for the next spec:
  - five whose only job is to turn a visarga into `:`: `DB-G4-005` (#94), `DB-G4-001` (#25), `DB-A6-014` (#92),
    `DB-A6-018` (#106), and `DB-A6-012` (#101, Tamil `ஃ`, which Unicode names the Tamil visarga);
  - two that turn `:` into a visarga in Sanskrit: `DB-A6-010` (#45) and `DB-A6-011` (#80). Both also fix dandas and
    avagraha, but TSAI took each rule out whole. A colon-to-visarga fix in Sanskrit can come back in the next spec
    with its own harm test.

  Two rules keep their other job: Data B removed only their visarga-to-colon line, marked in the code
  (`build/patches.json` in the work folder), and re-ran them on today's gold: `DB-A6-004` (#170, its danda fix; 0 of
  62) and `DB-G1-006` (#50, its matra fix; 0 of 142). The rules were found by running every rule on made-up text in
  its own script, once with a visarga used as a colon and once with `:` in its place. On 5 Nov, none of the 260
  converts either way.
- A visarga used as a colon is clean also with a space before it (TSAI's #240 re-review, 5 Nov). `DB-G1-002` (#18,
  Gujarati) and `DB-G1-010` (#3, Telugu) deleted a lone sign after a space, the visarga included (`અમદાવાદ ઃ` became
  `અમદાવાદ`). Data B took the visarga out of each rule's set of signs to delete, marked in the code, and re-ran them on
  today's gold: 0 of 80 and 0 of 18 changed.
- TSAI's follow-up: a visarga, with or without the space before it, stays as written. `DB-G1-005` (#47, Kannada),
  `DB-G1-007` (#45, Sanskrit) and `DB-G1-014` (#109, Telugu) removed the space before a lone sign, the visarga
  included (`ಬೆಂಗಳೂರು ಃ` became `ಬೆಂಗಳೂರುಃ`). Data B took the visarga out of the set of signs each one joins to the
  word before, marked in the code, and re-ran them on today's gold: 0 of 114, 0 of 71 and 0 of 18 changed. On made-up text
  in each rule's script, with and without a space before the visarga, no rule changes it now.
- D3 is out of spec v1 as a fix, so every D3 rule is `keep`: nine rules that were labelled `fix` are now `keep`
  (`DB-D3-004`, `-005`, `-010`, `-012`, `-015`, `-016`, `-018`, `-019`, `-020`). Their authors can move a rule to
  another code if it passes again under that code.

**Waiting on one condition:** #177's C6 (repeated dots) passes on today's gold (1 of 18, inside the limit of 1). TSAI
(G2, 5 Nov): it goes into spec v1 as a new code once the code owner approves #177 after the label fixes.

Rule IDs never change once published (`DB-<code>-<nnn>`); new rules take the next free number, and a rule that leaves
the sheet keeps its ID in the registry. TSAI (G2, 1 Nov): if a rule's harm result is still missing at Wed 4 Nov,
23:59 IST, or was run on a set other than its own pack's gold, the rule stays out of spec v1; it is not rejected, it
waits for the next spec.

## What each rule block holds
- The label card: `RULE_ID`, `CODE`, `ACTION`, `STAGE`, `STATUS`, `LANGS`, `ORIGIN`, `SOURCE`, `AUTHOR` (with the PR
  number and commit).
- The author's code, unchanged: every python block of their section, in order, exactly as `harm_test_indic.py` runs it.
  Seven rules are the exception, each marked in the code: `DB-A6-004` and `DB-G1-006` have one line removed by Data B;
  `DB-G1-002` and `DB-G1-010` have the visarga taken out of their orphan-sign set; `DB-G1-005`, `DB-G1-007` and
  `DB-G1-014` have it taken out of the set of signs they join to the word before.
- Lines marked `# added by Data B`: `import re` where the author relied on the harm tool providing it, `_std` (copied
  from Data A), and `medicine(doc)`. The guard in `medicine(doc)` runs a rule only on the pack it was tested on.
- `ACTION` is checked against the code (shankarpandala's review, 4 Nov). A rule whose function can return True drops the
  document, so a rule its author called "fix" is labelled `drop` or `fix+drop`. A `keep` rule's `medicine(doc)` always
  returns `("keep", text)`. D3 is a label only and out of spec v1 as a fix (TSAI, 31 Oct and 5 Nov), so every D3 rule
  is `keep`. `DB-D4-011` also gets the page
  URL, so its host check runs; every other rule gets the text only, as the harm tool tested it.

## Use
```python
from load_rules import load
for rule in load():                      # in run order
    action, text = rule.medicine(doc)    # doc = {doc_id, text, url, lang_label, pack_id}
```
The code in the sheet is run as code: read it first.

## Tests
```
python -I test_indic_rules.py        # or: python -m pytest test_indic_rules.py
```
For each rule it makes two made-up documents in the rule's language: a clean one and one with junk (boilerplate,
HTML, mojibake, a made-up email). Joiners are written as `‍` and `‌`. It checks:

| # | Check | A rule fails when |
|---|---|---|
| 1 | Loads | its block does not run on its own |
| 2 | Other packs | it changes a document of another pack |
| 3 | Result form | it returns anything but `("keep" \| "fix" \| "drop", text)` |
| 4 | ZWJ, ZWNJ | a word it keeps loses or gains a ZWJ (U+200D) or ZWNJ (U+200C). Deleting a whole repeated sentence or junk line, joiners and all, is allowed |
| 5 | NFC | a fixed document is no longer NFC, or loses a compatibility character from the text it should keep (NFKC) |
| 6 | Nukta | a fixed document has a different number of nukta signs (counted after NFD) |
| 7 | Second run | running the rule again on its output changes it again |

**Result on 6 Nov 2026, all 260 rules: 260 pass, 0 fail, 0 skipped** (`python -m pytest test_indic_rules.py`: 2 passed,
no error). (On 4 Nov `DB-F2-001` was skipped because it needs
the Itihasa test set; it is now out of spec v1.) The test was checked on 8 made-up rules, 5 of them broken on purpose (check 2; check 4 twice,
a joiner removed and a joiner added; check 5; check 7): it caught all 5 and passed the 3 good ones, one of which deletes
a repeated sentence that holds joiners.

Check 4 changed on 4 Nov. It used to compare the joiner count of the whole document, so `DB-C2-020` (#30, which deletes a
repeated sentence) failed on the test text: the made-up clean document repeats its sentence, and deleting the copy took
its joiners with it. It now looks at the words the rule keeps.

**What this does not show:** 57 of the 260 rules acted on the test text. The other 203 found nothing to fix in it,
because each targets something of its own pack, so checks 4 to 7 had nothing to test for them. For real text, the
joiner and normal-form audit is part of each author's harm run on their pack's gold set (`harm_test_indic.py`).

## Limits
- For 49 rules, the harm result is as the author reports it, on today's gold set; 194 were re-run on today's gold on
  3 to 6 Nov, and each says who ran it. Data A's integration check re-runs every rule on the current gold.
- **Our mistake, fixed 5 Nov:** up to 4 Nov this README and the sheet said the authors' results were on "the gold of
  2 Nov", but the sizes we checked them against were those of 31 Oct (shankarpandala found it on #240). Every rule now
  has a result at today's size.
- **For Data A:** the four #19 rules `DB-C3-010`, `DB-C4-009`, `DB-D4-008` and `DB-F1-007` act only on documents of the
  author's sample, listed by hash, so on the full pack they do almost nothing (TSAI's #240 review, 5 Nov).
- A pass on a small gold set is weak: 0 changed of n shows only that the rule harms fewer than about 3 in n clean
  documents. Telugu's three packs hold 60 gold documents in all (18, 24 and 18), so a Telugu pass shows harm under 12 to 17%.
- Three rules pass right at the limit: `DB-C1-024` (#256) changes 2 of 244 (limit 2), `DB-C4-010` (#45) 1 of 71 and
  `DB-C2-006` (#63) 1 of 114 (limit 1). Four more change 1 gold document, under their limit of 2 or 4.
- The groups in `rules_status.md` are read from each author's own harm text, or from a re-run on today's gold. If you
  think your rule is in the wrong group, say so in this PR or in #211.
- 74 overlaps, where two or more authors wrote a rule for the same disease on the same pack, are listed at the top of
  `medicine_indic.md`. All are kept, in run order.
- Rule IDs (`DB-<code>-<nnn>`) never change once published; a new rule takes the next free number.

## Add or fix your rule
1. In your own diagnosis PR, give each medicine a `**Disease:** <code>` line and a python block with
   `medicine_<code>(text)`.
2. Run `teams/02-data-b/tools/harm_test_indic.py` on your pack's gold set and put its result in part 4.
3. Tell the rules owner in #211.
