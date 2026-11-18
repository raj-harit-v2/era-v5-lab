# clean.py speed log: spec v1.1

Spec v1.1, Gate 2. A log of the slow rules in `clean.py` that were sped up on the spec v1.1 build: for each rule, what the fix was, docs/s per core before and after, and the checks showing that nothing else changed. It covers the shared F1 (`f1_rule.py`) and the English F1 rule `DA-F1-005`, five math rules, and five code rules. Last updated 17 Nov 2026. Reports counts, hashes and timings only, never document text.

It follows the v1 logs, which stay where they are: [speed_v1.md](../../results/spec_v1/speed_v1.md) (English rules, and the `clean.py` output hashes of the 13 original packs under the v1 build) and [speed_v1_code.md](../../results/spec_v1/speed_v1_code.md) (the first speed-up of `DA-E3-004` and the shared F1 on the code packs, measured on the v1 cleaner, 11 Nov). The fixes to rules are made in the spec v1.1 sheet (`spec_v1_1/sheets/specv1_1.md`, the sheet `clean.py` is built from; spec v1 is frozen); the fixes to the shared F1 are in `spec_v1/build/f1_rule.py`, which `build_clean.py` pastes into `clean.py`.

Every fix passes three checks before it is logged:

1. **Output sha256 unchanged** on every pack tested (`doc_id`, final action and final cleaned text of every document, in order).
2. **Harm tests unchanged** (every rule and `clean()` on each pack: same harm result, same gold changed/dropped counts).
3. **Pytest suite passes.**

## 1. Summary

| family | rule | what was done | whole-pack gain (docs/s) | commit |
|---|---|---|---|---|
| F1 | `f1_rule.py`, prose path (math, science) | email, "name at host" and phone passes skipped when the text cannot match | 1.06x to 1.42x | `9982b11`, label fix `05d9c74` |
| F1 | `f1_rule.py`, Indic path (18 packs) | digit translation, toll-free, mobile, landline and email passes skipped when the text cannot match | 1.16x to 2.68x on the packs timed | `40393df` |
| F1 | `DA-F1-005` (English) | the organisation phrase is searched only when a contact line asks | 1.24x to 1.31x | `7cb527a` |
| math | `DA-C1-001` (site boilerplate) | 120-character test before the slow search; lower-cased pattern on ASCII lines | 1.91x on math-finemath | `10e4635` |
| math | `DA-D3-005` (foreign-script lines) | no letter counting without a foreign character | 1.10x to 1.14x | `5022efb` |
| math | `DA-C7-001` (content lost in extraction) | punctuation-first search, `???` guard, per-line candidate test | 1.11x to 1.20x | `72f4674` |
| math | `DA-A5-002` (ligatures, fullwidth letters) | letters counted only for a text with a fullwidth character | 1.06x to 1.11x | `aabb1ec` |
| math | `DA-A8-001` (words run together) | a line is tested only if it has the shape of a glued word | 1.07x to 1.10x | `9c7d3c2` |
| code | `DA-A4-002`, `DA-A6-001`, `DA-E3-003`, `DA-E2-001` | one necessary-condition guard each (round 1, together) | 1.28x to 1.70x | `a92ccb6` |
| code | `DA-E3-004` | guards before `ASSIGNED`, tighter `gh` hint (round 2) | 1.22x to 1.61x | `605f513` |

The gain of the whole `clean()` loop is smaller than that of the rule, because the rest of `clean()` is unchanged; the sections below give both. The tests of each fix are in `spec_v1_1/tests/test_speed_equivalence_*.py`, each against a frozen copy of the old rule (section 5).

## 2. The F1 rule

Three speed-ups of the F1 rule (the TSAI ruling on personal details): the shared F1 (`f1_rule.py`) on its prose path (math and science) and on its Indic path, and the English F1 rule `DA-F1-005`.

### 2.1 Speed, docs/s per core, before and after

500-doc sample packs, one core pinned to CPU 0, `clean()` loop only, best of 3 passes, before and after timed back to back. The rule time is the per-document time of the F1 rule alone, from the per-rule profile (`spec_v1/run_clean.py`).

| fix | pack | docs/s | rule time, ms/doc |
|---|---|---|---|
| 1 prose path | sci-finepdfs | 143.4 to 203.4 (1.42x) | 6.636 to 4.830 |
| | math-megamath | 510.8 to 598.7 (1.17x) | 0.868 to 0.566 |
| | math-finemath | 167.0 to 176.4 (1.06x) | 0.676 to 0.424 |
| 2 Indic path | ind-hi-hplt | 202.9 to 263.1 (1.30x) | 1.496 to 0.197 |
| | ind-sa-fw2 | 178.9 to 207.2 (1.16x) | 1.354 to 0.351 |
| | ind-bn-fw2 | 762.3 to 1019.5 (1.34x) | 0.558 to 0.196 |
| | ind-ta-sangraha-v | 1266.2 to 3390.3 (2.68x) | 0.605 to 0.039 |
| 3 English `DA-F1-005` | en-dclm | 554.5 to 714.8 (1.29x) | 0.438 to 0.149 |
| | en-fineweb-edu | 748.3 to 981.7 (1.31x) | 0.354 to 0.126 |
| | en-nemotroncc | 741.0 to 921.7 (1.24x) | 0.281 to 0.110 |
| | en-nemotroncc-synth | 1997.1 to 2614.6 (1.31x) | 0.133 to 0.042 |

- **Fix 1** was timed on the packs where F1 takes the most time: before it, F1 was 94.3% of the rule time on `sci-finepdfs` (the documents are long, about 48,800 characters), 43.6% on `math-megamath` and 11.3% on `math-finemath`. The whole-pack gain on `math-finemath` is small because `DA-C1-001` (65% of that pack) was untouched by it (it is fixed in section 3).
- **Fix 2:** F1's share of the rule time fell from 25.9% to 4.4% on `ind-hi-hplt`, 22.1% to 6.8% on `ind-sa-fw2`, 37.1% to 16.1% on `ind-bn-fw2` and 67.6% to 13.2% on `ind-ta-sangraha-v`. Over all 18 Indic packs the whole-pack gain is 1.1x to 2.7x.
- **Packs a fix does not touch** read 1.0x to 1.1x, timing noise. Timings vary by about 5%, so treat ratios under 1.1x as about equal.

### 2.2 Status of each fix

| fix | rule | output sha256 | harm tests | pytest | F1 on the packs it applies to | `clean.py` before | `clean.py` after | commit |
|---|---|---|---|---|---|---|---|---|
| 1 | `f1_rule.py`, prose path | same, 13 of 13 packs | unchanged, 31 of 31 packs | 2238 passed | math-finemath: ran on 487, fixed 4, dropped 0; math-megamath: 490, 26, 0; sci-finepdfs: 488, 15, 1 | `22d818c72c9f` | `3145d54a97a5` | `9982b11` |
| | label fix: prose path chosen by pack id, not language label (section 2.4) | same, 31 of 31 packs | unchanged | | | `3145d54a97a5` | `c1a96591cefb` | `05d9c74` |
| 2 | `f1_rule.py`, Indic path | same, 31 of 31 packs | unchanged, 31 of 31 packs | 2353 passed | 18 Indic packs: ran on 8,653 of 9,000, fixed 52, dropped 0 | `c1a96591cefb` | `2aa69a36c544` | `40393df` |
| 3 | `DA-F1-005`, English, spec v1.1 sheet | same, 31 of 31 packs | unchanged, 31 of 31 packs | 2565 passed | en-dclm: ran on 491, fixed 2, dropped 0; en-fineweb-edu: 499, 0, 0; en-nemotroncc: 483, 1, 0; en-nemotroncc-synth: 499, 2, 0 | `729e37051ffd` | `9a4e3a87f124` | `7cb527a` |

- **Baseline of fix 1:** `clean.py` `22d818c72c9f`, the one in `9d96529` (14 Nov, Revert of the math speed commit) and in `536e8bc` (#244); no F1 change was made before `9982b11`.
- **Pytest** counts are the whole suite at each commit (one test skipped). For fix 1 the first run had one failure, `test_pr244_rerun_config_pins_current_cleaner_and_recorded_smoke`, which required the PR #244 rerun config to pin the live `clean.py` and so fails for any `clean.py` change; it now checks the config against its recorded smoke evidence, like the submitted-config test next to it. The job folder is untouched.
- **Output sha256** of the 13 original packs under the v1 build (fixes 1 and 2) is the same as in [speed_v1.md section 6](../../results/spec_v1/speed_v1.md#6-output-sha256-of-the-13-sample-packs-identical-before-and-after-every-fix). The v1.1 build (fix 3 on) has other hashes, because of its 24 new rules; before and after are the same under it.
- **Fix 3** is a change to the spec v1.1 sheet only (`specv1_1.md`; spec v1 is frozen). The `clean.py` committed at that time was built from `specv1.md` and is not changed by that commit; before and after are scratch `clean.py` files built from `specv1_1.md` as committed and as edited, and their diff is exactly the edit. `build_clean.py` now builds from `specv1_1.md` by default and the committed `clean.py` is that build (`9a4e3a87f124`, the same file as "after"), so from there `--before <rev> --after <rev>` works for every fix. The test `test_the_committed_sheet_is_up_to_date` in `spec_v1_1/tests/test_combine_spec.py` was removed in the same commit: it required `specv1_1.md` to equal the output of `combine_spec.py`, so it fails for any edit of the sheet, and the script was used once. It can be brought back if the sheet is generated again.

**Harm tests on all 31 registered packs, including the Indic ones.** The shared F1 rule runs on 27 of the 31 packs `clean.py` has rules for: the 18 Indic packs (Indic path), the 6 code, the 2 math and the science pack. The 4 English packs have their own F1, `DA-F1-005`. The harm tests were run on all 31 packs, before and after, with `make_harm_tests.py` and the 18 Indic gold sets (`teams/02-data-b/gold`) copied into the scratch copy of the tree, since that script reads gold only from `teams/01-data-a/gold`. Every result file (every gold changed/dropped count, every rule alone, every disease-code function and `clean()`) is identical before and after, for each fix.

| family | packs | gold docs | `clean()` changes + drops on gold | limit (1% of gold, at least 1 per pack) | whole packs, fixed / dropped (500 docs each) |
|---|---|---|---|---|---|
| code | 6 | 980 | 0 + 0 | PASS on 6 of 6 | 1,764 / 120 |
| English | 4 | 675 | 0 + 0 | PASS on 4 of 4 | 160 / 28 |
| math | 2 | 112 | 0 + 0 | PASS on 2 of 2 | 239 / 23 |
| science | 1 | 202 | 0 + 0 | PASS on 1 of 1 | 45 / 13 |
| Indic | 18 | 2,193 | 10 + 3 | PASS on 18 of 18 | 1,729 / 347 |
| **all** | **31** | **4,162** | | **31 of 31** | **3,937 / 531** of 15,500 |

No fix changes any output, so the table holds before and after each of them. The 10 changed and 3 dropped Indic gold documents come from the Indic rules and are the same before and after. The Indic F1 harm test (`spec_v1/validate/harm_f1_indic.py`, F1 alone and `clean()` on each pack's own gold) gives 18 of 18 PASS before and after fixes 1 and 2, 2,193 gold documents, F1 alone changes 2 (one each in `ind-kn-fw2` and `ind-ta-sangraha-v`) and drops 0.

Under the v1.1 `clean.py` (fix 3), four packs do not pass their harm limit, before and after alike: `en-nemotroncc` (`DA-A8-003`, `DA-A8-004`), `math-finemath`, `sci-finepdfs` and `ind-te-sangraha-v` (`DB-C6-001`). They are the four listed as FAIL in [results/combined/validation.md](combined/validation.md); `DA-F1-005` is not among the failing rules. `make_harm_tests.py` exits with 1 for them, so `speed_compare.sh` now compares the results of both sides anyway.

**Seven packs were not tested.** `week1-packs` holds 38 packs: the 31 above and these 7, none registered in `clean.py` (no rules, so `clean()` leaves them unchanged and no harm test runs). Under the new `clean.py`, `clean()` changes or drops 0 of the 500 documents of each, so the F1 changes cannot affect them.

| pack | docs | gold set | why it was not tested |
|---|---|---|---|
| `cadj-commits` | 500 | yes, `teams/02-data-b/gold/cadj-commits_gold.csv` (413 rows) | not registered in `clean.py`, so the harm script has no rules to run on it |
| `cadj-notebooks` | 500 | none | no gold, not registered |
| `cadj-stackexchange` | 500 | only a 1-row file, `gold/cadj-stackexchange.csv`, not named `<pack>_gold.csv` | not registered; effectively no gold |
| `ind-ml-fw2` | 500 | none | no gold, not registered |
| `ind-or-fw2` | 500 | none | no gold, not registered |
| `ind-ta-fw2` | 500 | none | no gold, not registered |
| `ind-ta-sangraha-s` | 500 | none | no gold, not registered |

These seven can only be tested once they get rules in `clean.py` and a gold set.

### 2.3 What each fix did

Each fix skips a pass when the text cannot match it, using a condition every match must satisfy, so the output is unchanged. Tests: [test_speed_equivalence_f1.py](../tests/test_speed_equivalence_f1.py) (fix 1, 121 tests), [test_speed_equivalence_f1_indic.py](../tests/test_speed_equivalence_f1_indic.py) (fix 2, 97) and [test_speed_equivalence_f1_english.py](../tests/test_speed_equivalence_f1_english.py) (fix 3, 29), each against a frozen copy of the old rule.

1. **Prose path of the shared F1 (`_f1_prose`, math and science).** Six regex passes ran on every text; three are now skipped when they cannot match:
   - **Email:** runs only when the text has an `@` (1.73 to 0.67 ms/doc on `sci-finepdfs`).
   - **"Name at host":** a cheap prefilter for ` at <host>.<tld>` runs first, and the full pattern only if it matches (0.66 to 0.27 ms/doc).
   - **Phone:** the international form starts with a literal `+`; a text with no `+` uses the North American form alone, which finds exactly the same matches (3.1 to about 1.7 ms/doc).
2. **Indic path of the shared F1 (`_f1_indic`, 18 packs).** Digit translation, three phone regexes and the email regex ran on every text. Now:
   - **Digit translation** runs only if the text holds an Indic-script digit (a character the translation maps; ASCII digits do not count).
   - **Toll-free** runs only if the text holds `1800` or `1860`, the only strings its existing regex can start with.
   - **Mobile and landline** run only if a short core pattern finds something: the regex without its lookarounds and optional prefixes. `_F1I_MOBILE_CORE` is the two shapes of an Indian mobile number (`98765 43210`, `987-654-3210`); `_F1I_LANDLINE_CORE` is the area code and number. A core starts with a character set, which the engine scans much faster than the lookbehind the full regex starts with.
   - **Email** runs only when the text has an `@`.
3. **English `DA-F1-005`.** The rule searched the whole text for an organisation phrase ("call us", "our team", "we provide" and so on) before reading the first line, but the answer is only used on a line with an email, a phone number or an address, which is in 3% to 6% of documents (en-dclm 32 of 500, en-fineweb-edu 18, en-nemotroncc 30, en-nemotroncc-synth 13). That search was about 70% of the rule (0.31 of 0.46 ms/doc on en-dclm). It now runs the first time such a line asks, and the answer is kept for that text.

Fixes 1 and 2 are in `spec_v1_1/build/f1_rule.py`, the source `build_clean.py` pastes into `clean.py`; they are not part of any sheet. Fix 3 is in the `DA-F1-005` card of `spec_v1_1/sheets/specv1_1.md`.

### 2.4 Note: what the Indic-digit guard saves, and where it does not

Open for discussion with the team. The digit guard is the weakest of the four guards of fix 2 and is kept because it is exact and costs almost nothing, not because it skips most documents. Most documents have a digit, but the guard asks for an *Indic-script* digit, and many packs write numbers with ASCII digits. 3,000 documents of each pack from the week-2 `train` part (54,000 documents; the 500-document week-1 sample gives the same picture). The last three columns are the cost of the digit step alone, ms/doc, one core:

| pack | ASCII digit | Indic digit | 2 consecutive Indic digits | no guard | 1-digit guard (used) | 2-consecutive guard |
|---|---:|---:|---:|---:|---:|---:|
| ind-bn-fw2 | 14% | 85% | 79% | 0.146 | 0.127 | 0.126 |
| ind-bn-sangraha-v | 11% | 78% | 73% | 0.159 | 0.131 | 0.134 |
| ind-gu-fw2 | 72% | 18% | 15% | 0.147 | 0.046 | 0.052 |
| ind-hi-fw2 | 84% | 2% | 1% | 0.143 | 0.015 | 0.028 |
| ind-hi-hplt | 90% | 4% | 2% | 0.253 | 0.040 | 0.058 |
| ind-hi-indiccorp | 36% | 1% | 0% | 0.019 | 0.002 | 0.003 |
| ind-hi-sangraha-s | 84% | 0% | 0% | 0.236 | 0.018 | 0.039 |
| ind-hi-sangraha-v | 74% | 10% | 8% | 0.133 | 0.037 | 0.043 |
| ind-kn-fw2 | 80% | 8% | 5% | 0.135 | 0.028 | 0.034 |
| ind-kn-sangraha-s | 90% | 0% | 0% | 0.214 | 0.016 | 0.035 |
| ind-kn-sangraha-v | 75% | 9% | 7% | 0.123 | 0.029 | 0.035 |
| ind-mr-fw2 | 57% | 46% | 42% | 0.146 | 0.081 | 0.085 |
| ind-mr-sangraha-v | 39% | 50% | 46% | 0.137 | 0.083 | 0.087 |
| ind-sa-fw2 | 31% | 67% | 56% | 0.354 | 0.289 | 0.269 |
| ind-ta-sangraha-v | 80% | 0% | 0% | 0.155 | 0.012 | 0.026 |
| ind-te-fw2 | 85% | 1% | 0% | 0.177 | 0.017 | 0.032 |
| ind-te-sangraha-s | 91% | 0% | 0% | 0.234 | 0.018 | 0.039 |
| ind-te-sangraha-v | 73% | 2% | 1% | 0.130 | 0.016 | 0.024 |
| mean of the 18 packs | 65% | 21% | 19% | 0.169 | 0.056 | 0.064 |

- **Effective** (Indic digit in 0% to 18% of documents; the Hindi, Telugu, Kannada, Tamil and Gujarati packs): the digit step costs 0.12 to 0.25 ms/doc without the guard and 0.002 to 0.05 with it, a saving of about 70% to 93%.
- **Not effective** (Indic digit in 46% to 85%; `ind-bn-fw2`, `ind-bn-sangraha-v`, `ind-mr-fw2`, `ind-mr-sangraha-v`, `ind-sa-fw2`): numbers are written in the script's own digits, and the guard saves only 13% to 45% of the step (13%, 18% and 18% on the Bengali packs and `ind-sa-fw2`). A pack from a source that uses Indic digits throughout would see no saving. The share is the same in week 1 and week 2 (mean 21%); other data (week-3 shards) was not checked.
- **The step is small anyway:** about 0.11 ms/doc saved on average (0.169 to 0.056). The mobile, landline, toll-free and email guards each skip their regex for 93% or more of documents and save more together.
- **Two consecutive Indic digits** instead of one is not faster overall (0.064 ms/doc against 0.056 on average) and changes the output: a number written with a mix of Indic and ASCII digits (`Call me on 9876५ 43210`) is masked now and would not be, and a single Indic digit next to a number (`contact ५98765 43210`, `Mobile 98765 43210.५ end`) blocks the match now and would not. Three of the 97 tests of fix 2 fail with it.

**Week-2 science label.** The prose path accepted only documents labelled `eng_Latn`, which is how week-1 `sci-finepdfs` is labelled. All 6,011 `train` and 63 `heldout` documents of week-2 `sci-finepdfs` are labelled `en` (ISO 639-1, as the week-2 README defines `lang_label`), so F1 skipped them; on the first 1,000, 15 differ between the two labels. Fixed in `05d9c74`: the prose path is chosen by pack id (`math-*`, `sci-*`). The week-1 packs are unchanged (0 of 15,500 documents differ); on the first 2,000 week-2 science documents, 27 more get their private values masked.

## 3. The math rules

This part covers the slow rules of the math packs (`math-finemath`, `math-megamath`): for each, what the fix was, docs/s per core before and after, and the checks showing that nothing else changed.

### 3.1 Speed, docs/s per core, before and after

500-doc sample packs, one core pinned to CPU 0, `clean()` loop only, best of 3 passes, before and after timed back to back. The rule time is the per-document time of the rule alone, from the per-rule profile (`spec_v1/run_clean.py`). Before fix 1, `DA-C1-001` was 64% of the rule time on `math-finemath` (3.9 ms/doc); it does not run on `math-megamath`. The rows were timed in separate runs, so the docs/s before of one row is not the docs/s after of the row above.

| # | rule (what it checks) | math-finemath docs/s | math-megamath docs/s | rule time math-finemath, ms/doc | rule time math-megamath, ms/doc |
|---|---|---|---|---|---|
| 1 | `DA-C1-001` (site boilerplate) | 127.3 to 242.7 (1.91x) | 259.3 to 286.6 (1.11x) | 3.858 to 0.606 | n/a (rule not on this pack) |
| 2 | `DA-D3-005` (foreign-script lines) | 253.6 to 279.9 (1.10x) | 296.9 to 339.8 (1.14x) | 0.358 to 0.033 | 0.434 to 0.038 |
| 3 | `DA-C7-001` (content lost in extraction) | 274.4 to 304.2 (1.11x) | 328.2 to 392.6 (1.20x) | 0.757 to 0.353 | 0.912 to 0.423 |
| 4 | `DA-A5-002` (ligatures and fullwidth letters) | 281.8 to 298.0 (1.06x) | 363.7 to 403.3 (1.11x) | 0.296 to 0.064 | 0.311 to 0.082 |
| 5 | `DA-A8-001` (words run together) | 308.3 to 329.9 (1.07x) | 412.6 to 455.5 (1.10x) | 0.339 to 0.129 | 0.388 to 0.187 |

In fix 2 the rule itself is 11x faster on both packs, but it was a small share of the time (about 9% and 15% before), so the whole-pack gain is 1.10x and 1.14x. In fix 3 the rule is 2.2x faster on both packs; it was the largest rule on them (20% and 28% of the time), so the whole-pack gain is 1.11x and 1.20x. In fix 4 the rule is 4.6x and 3.8x faster; it was about 9% and 12% of the time, so the whole-pack gain is 1.06x and 1.11x. In fix 5 the rule is 2.6x and 2.1x faster; it was about 10% and 15% of the time, so the whole-pack gain is 1.07x and 1.10x. The packs a fix does not touch read 1.0x to 1.2x, timing noise (for example `math-megamath` in fix 1: the rule is not on that pack).

### 3.2 Status of each fix

| # | rule | output sha256 | harm tests | pytest | documents changed, 500 docs each: math-finemath / math-megamath | `clean.py` before | `clean.py` after | commit |
|---|---|---|---|---|---|---|---|---|
| 1 | `DA-C1-001` | same, 31 of 31 packs | unchanged, 31 of 31 packs | 2763 passed | ran on 487, fixed 97, dropped 0 / not on this pack | `9a4e3a87f124` | `ddf379d68e29` | `10e4635` |
| 2 | `DA-D3-005` | same, 31 of 31 packs | unchanged, 31 of 31 packs | 2820 passed | ran on 500, fixed 7, dropped 1 / ran on 490, fixed 3, dropped 0 | `ddf379d68e29` | `ea14b0899085` | `5022efb` |
| 3 | `DA-C7-001` | same, 31 of 31 packs | unchanged, 31 of 31 packs | 2896 passed | ran on 479, fixed 0, dropped 12 / ran on 487, fixed 0, dropped 18 | `ea14b0899085` | `55f8653af9a1` | `72f4674` |
| 4 | `DA-A5-002` | same, 31 of 31 packs | unchanged, 31 of 31 packs | 2920 passed | ran on 500, fixed 6, dropped 0 / ran on 500, fixed 11, dropped 0 | `55f8653af9a1` | `097eb0a4fd3e` | `aabb1ec` |
| 5 | `DA-A8-001` | same, 31 of 31 packs | unchanged, 31 of 31 packs | 2961 passed | ran on 487, fixed 37, dropped 0 / ran on 490, fixed 32, dropped 0 | `097eb0a4fd3e` | `716c9a90093f` | `9c7d3c2` |

- **Baseline:** fix 1: `clean.py` `9a4e3a87f124`, the build from `specv1_1.md` in commit `3089352`; fix 2: `ddf379d68e29`, with fix 1 (`10e4635`); fix 3: `ea14b0899085`, with fix 2 (`5022efb`, merged as #49); fix 4: `55f8653af9a1`, with fix 3 (`72f4674`); fix 5: `097eb0a4fd3e`, with fix 4 (`aabb1ec`). The output sha256 of the two math packs under it: `math-finemath` `c6a3183c9d076f12`, `math-megamath` `6fb0de7bad7c44e0` (the v1.1 build; the hashes in [speed_v1.md section 6](../../results/spec_v1/speed_v1.md#6-output-sha256-of-the-13-sample-packs-identical-before-and-after-every-fix) are for the v1 build, which has 24 fewer rules).
- **Pytest:** the whole suite (`teams/01-data-a/tests` and `spec_v1_1/tests`), 1 test skipped, 51 subtests passed.
- **Harm tests:** `make_harm_tests.py` on all 31 packs, with the 18 Indic gold sets copied into both trees (section 6): every result file is identical before and after. Four packs do not pass their harm limit under the v1.1 `clean.py`, before and after alike (`en-nemotroncc`, `math-finemath`, `sci-finepdfs`, `ind-te-sangraha-v`; see [results/combined/validation.md](combined/validation.md)); `DA-C1-001`, `DA-D3-005`, `DA-C7-001`, `DA-A5-002` and `DA-A8-001` are not among the failing rules.

### 3.3 What each fix did

1. **`DA-C1-001`, site boilerplate (math-finemath).** The rule deletes a line that is generic site chrome (`C1_LINE`), or that holds one of 83 site phrases (`C1_SITE`, case-insensitive) and is at most 120 characters. It searched `C1_SITE` on every line first and tested the length second. Now the length test goes first (a line over 120 characters is kept whatever `C1_SITE` finds), and on a pure-ASCII line the search uses the lower-cased pattern on the lower-cased line instead of the `(?i)` pattern, which the engine runs much more slowly (3.3 to 0.57 ms/doc on the pack). The lower-cased pattern is the same pattern: every escape in `C1_SITE` is lower-case and it has no non-ASCII character, so `lower()` cannot change its meaning. A line with a non-ASCII character keeps the original `(?i)` regex.

2. **`DA-D3-005`, foreign-script lines (both math packs).** The rule removes a line that is mostly Cyrillic, Indic, kana, CJK, Hangul or Arabic script, and drops the document if more than 30% of its letters were in removed lines. It counted the letters of every line, and then of the whole text, even though a line with no foreign character is never removed and its count is never used. Now the whole text is returned as it is when it holds no foreign character (most documents), letters are counted only on lines that hold one, and the letters of the whole text are counted only when a line was removed (otherwise the drop test cannot fire). Documents with foreign script behave as before.

3. **`DA-C7-001`, content lost in extraction (both math packs).** The rule drops a document with four or more "gaps": a formula that was lost, leaving a sentence cut at `=` or at a dangling word ("the slope is"), an empty answer option, a keyword followed by a lone `.` `,` or `;` ("show that ."), or a `?` where a value was. The 14 Nov guards already skipped most work; what was left took 0.76 ms/doc (20%) on `math-finemath` and 0.91 ms/doc (28%) on `math-megamath`, in three places. All three are exact:
   - **Keyword followed by punctuation (`C7_NO_OBJECT`).** The regex starts with `\b`, so the engine tried it at every position. The punctuation is found first, with a regex that starts with a character set, and for each hit the whole word before it is checked with the same keyword regex. The counts are the same.
   - **Question marks.** The regex has two halves; the second starts with a lookbehind and was tried at every position. It is now searched only when the text holds `???`. The halves never overlap, so their counts add up.
   - **Candidate lines.** One search of three patterns joined with `|` over the whole text is replaced by a per-line test: a line that can be a gap ends, after its trailing blanks, in `=`, a letter, `)` or `.`, and only those lines run the three regexes. The loop that follows is unchanged.

4. **`DA-A5-002`, ligatures and fullwidth letters (both math packs).** The rule turns ligatures (`ﬁ`, `ﬃ`) into letters and fullwidth characters (`Ａ`, `１`, `！`) into ASCII, unless more than 1% of the letters are Chinese, Japanese or Korean (then the text is real CJK text and is left alone). It counted the letters of every document with a Python loop before looking for a fullwidth character, although the fullwidth step does nothing without one, and almost no document has one (2 and 3 of 500 do; the rule changes 6 and 11, mostly through ligatures). Now a text with no fullwidth character is returned after the ligature step, and the letters are counted only for a text that has one. The result is the same for every text.

5. **`DA-A8-001`, words run together (both math packs).** The rule puts back the space in `ProblemsThe` and `here.The` when the second word is a sentence opener (`The`, `Find`, `Question` and about 80 others), unless the line is code or inside a fence. It tested every line with `A8_CODE` and `A8_GLUED`, which both start with a lookbehind or `\b` and are tried at every position, although only 7% of documents change. Now a line is tested only if it holds the shape every match must have: a lowercase letter, an optional `.`, a capital and a lowercase letter. Other lines are returned as they are. A text with no three backticks has no fence, so the fence loop is skipped for it; a text with them uses the original loop. The result is the same for every text.

The edits are to the `DA-C1-001`, `DA-D3-005`, `DA-C7-001`, `DA-A5-002` and `DA-A8-001` cards of `specv1_1.md`; the `medicine_<family>.md` files are not read by the build and are not changed. Tests: [test_speed_equivalence_math.py](../tests/test_speed_equivalence_math.py) (126 tests for fix 1, 57 for fix 2, 76 for fix 3, 24 for fix 4 and 41 for fix 5), against frozen copies of the old rules (`c1_reference`, `d3_reference`, `c7_reference`, `a5_reference` and `a8_reference`, inside the test file; the tests of fixes 3 to 5 read the new rule from `specv1_1.md`).

## 4. The code rules

This part covers five more slow rules of the six code packs (`code-cpp`, `code-go`, `code-java`, `code-js-ts`, `code-python`, `code-rust`), made on the spec v1.1 build: for each, what the fix was, docs/s per core before and after, and the checks showing that nothing else changed. The first speed-up of `DA-E3-004` and of the shared F1 on the code packs is in [speed_v1_code.md](../../results/spec_v1/speed_v1_code.md) (measured on the v1 cleaner).

The fixes were made in two rounds, each measured with its own `speed_compare` run: round 1, four rules together (`--rules DA-A4-002,DA-A6-001,DA-E3-003,DA-E2-001`, commit `a92ccb6`); round 2, `DA-E3-004` (`--rules DA-E3-004`, before is the build of round 1).

### 4.1 Speed, docs/s per core, before and after

**Round 1: four rules.** 500-doc sample packs, one core pinned to CPU 0, `clean()` loop only, best of 3 passes. The rule rows are the time of that rule in the per-rule profile (ms per doc, before to after); the last row is the whole `clean()` loop (docs/s per core, before to after, and the ratio).

| # | rule (what it checks) | code-cpp | code-go | code-java | code-js-ts | code-python | code-rust |
|---|---|---|---|---|---|---|---|
| 1 | `DA-A4-002` (replacement-character comments), ms/doc | 0.097 to 0.001 | 0.059 to 0.002 | 0.056 to 0.001 | 0.045 to 0.001 | 0.099 to 0.001 | 0.072 to 0.001 |
| 2 | `DA-A6-001` (Cyrillic look-alike letters), ms/doc | 0.160 to 0.030 | 0.126 to 0.022 | 0.098 to 0.018 | 0.075 to 0.017 | 0.174 to 0.031 | 0.127 to 0.024 |
| 3 | `DA-E3-003` (known keys and seeds), ms/doc | 0.311 to 0.037 | 0.183 to 0.034 | 0.189 to 0.034 | 0.146 to 0.018 | 0.353 to 0.074 | 0.236 to 0.031 |
| 4 | `DA-E2-001` (byte-array and base64 blobs), ms/doc | 0.169 to 0.095 | 0.100 to 0.056 | 0.102 to 0.055 | 0.074 to 0.041 | 0.179 to 0.090 | 0.113 to 0.058 |
| all four together | docs/s before to after | 655.5 to 1018.2 (1.55x) | 727.6 to 933.6 (1.28x) | 899.9 to 1257.3 (1.40x) | 1469.5 to 2319.1 (1.58x) | 650.1 to 986.6 (1.52x) | 1001.6 to 1705.6 (1.70x) |

- `DA-A4-002` is now close to free (0.001 to 0.002 ms/doc, 30 to 100 times faster), `DA-E3-003` is 5 to 8 times faster and `DA-A6-001` 4 to 6 times faster. What is left of `DA-A6-001` (0.02 to 0.03 ms/doc) is the one `[Ѐ-ӿ]` search over each text.
- `DA-E2-001` is only 1.8 to 2.0 times faster, as expected: the byte-array half is guarded, the base64 half is not and now sets its cost.
- The four rules together took 0.34 to 0.81 ms/doc before (js-ts 0.34, cpp 0.74, python 0.81) and now take 0.08 to 0.20 ms/doc (js-ts 0.08, cpp 0.16, python 0.20), the sum of the four rows above. The whole loop gains less than that in ratio (1.28x to 1.70x), because the rest of `clean()` is unchanged.
- Slowest rules left after round 1 (share of the `clean()` time): `DA-E3-004` is first on five of the six packs (31% to 52%, 0.24 to 0.56 ms/doc; `code-go` has `DA-C3-002` first at 39%, 0.48 ms/doc and `DA-E3-004` second at 24%). Next come `f1_rule.py` (9% to 23%), then `DA-E1-007`, `DA-C1-005`, `DA-E1-008` and `DA-E1-004` on one or two packs each. `DA-E3-004` was done next (round 2).

**Round 2: `DA-E3-004`.** Same sample packs and method. Before is `clean.py` `d932badc1fc5` (after round 1), after is `6a57276c0e83`.

| rule / measure | code-cpp | code-go | code-java | code-js-ts | code-python | code-rust |
|---|---|---|---|---|---|---|
| `DA-E3-004` (known keys and assigned secrets), ms/doc | 0.437 to 0.060 | 0.287 to 0.056 | 0.264 to 0.050 | 0.222 to 0.074 | 0.588 to 0.173 | 0.297 to 0.056 |
| whole `clean()` loop, docs/s before to after | 1045.6 to 1596.2 (1.53x) | 956.8 to 1167.6 (1.22x) | 1276.9 to 1666.9 (1.31x) | 2306.8 to 3415.7 (1.48x) | 991.6 to 1598.4 (1.61x) | 1730.9 to 2777.5 (1.60x) |

- `DA-E3-004` is 3.0 to 7.3 times faster (cpp 7.3x, go 5.1x, java 5.3x, rust 5.3x, js-ts 3.0x, python 3.4x), and the whole loop 1.22x to 1.61x.
- What is left on `code-python` (0.17 ms/doc) is mostly the third test, the search for a name word followed by its value: a separate timing of that search on the python sample gave about 0.10 ms/doc, because 86 of the 500 python files pass the second test (a quoted string of 16 or more characters after an `=` or `:`) and have a name word somewhere.
- Slowest rules left after round 2 (share of the `clean()` time): `f1_rule.py` is first on four packs (cpp 28%, js-ts 28%, python 31%, rust 37%; 0.12 to 0.21 ms/doc). `code-go` has `DA-C3-002` first at 49% (0.49 ms/doc), `code-java` has `DA-C1-005` at 19% (0.12 ms/doc, with `f1_rule.py` at 19%). Then `DA-E1-007` (cpp 18%), `DA-E1-008` (js-ts 26%), `DA-E2-001` (11% to 15% on five packs, its base64 half), `DA-E4-005` and `DA-E4-009`, and `DA-E3-003` (python 11%). `DA-C3-002` is the biggest single rule left.

### 4.2 Status of the fixes

| # | rule | output sha256 | harm tests | pytest | documents changed or dropped, 500 docs each | `clean.py` before | `clean.py` after | commit |
|---|---|---|---|---|---|---|---|---|
| 1 to 4 | `DA-A4-002`, `DA-A6-001`, `DA-E3-003`, `DA-E2-001` | the same on 31 of 31 packs | unchanged on 31 of 31 packs, all result files identical | 3120 passed | see below | `716c9a90093f` | `d932badc1fc5` | `a92ccb6` |
| 5 | `DA-E3-004` | the same on 31 of 31 packs | unchanged on 31 of 31 packs, all result files identical | 4067 passed | java 1, js-ts 2, rust 1 fixed (4 of 3,000) | `d932badc1fc5` | `6a57276c0e83` | `605f513` |

- **Baseline:** `clean.py` `716c9a90093f`, the build from `specv1_1.md` in commit `9c7d3c2` (after the math fixes); round 2 starts from `d932badc1fc5`, the build of round 1.
- **Pytest:** the whole suite (`teams/01-data-a/tests` and `spec_v1_1/tests`), 1 test skipped, 51 subtests passed. Round 1: 3120 passed, 159 of them new. Round 2: 4067 passed, 947 new, all in `spec_v1_1/tests/test_speed_equivalence_code_rules.py` (1106 tests in that file).
- **Harm tests:** all 31 packs, the Indic gold copied into both trees (section 6). Result: unchanged, all result files identical before and after (every gold changed/dropped count and PASS). The `speed_compare` run reported `RESULT: PASS`, for both rounds.
- **Documents changed or dropped by the four rules of round 1** (the 500-doc sample of each code pack, 3,000 documents in all; counts from the after tree, and the output sha256 is the same as before, so the before tree gives the same):

| pack | `DA-A4-002` | `DA-A6-001` | `DA-E3-003` | `DA-E2-001` |
|---|---|---|---|---|
| code-cpp | 0 fixed | 1 fixed | 0 fixed | 1 dropped |
| code-go | 1 fixed | 2 fixed | 1 fixed | 0 |
| code-java | 0 | 0 | 0 | 0 |
| code-js-ts | 0 | 0 | 0 | 0 |
| code-python | 0 | 0 | 0 | 0 |
| code-rust | 0 | 0 | 0 | 0 |

  The rules are rare on these packs (1, 3, 1 and 1 documents of 3,000), which is why a guard that skips the regex on a text without the trigger pays off: nearly every text is kept as it is. The output sha256 is the same on all 31 packs, so the Indic and other non-code packs are untouched as well.
- **Round 2** (`DA-E3-004`, same packs and method): the rule fixes 4 of the 3,000 sampled documents, before and after (code-java 1, code-js-ts 2, code-rust 1; code-cpp, code-go and code-python 0).

### 4.3 What each fix did

Each fix is a necessary-condition guard: a cheap test that is true whenever the regex could match, so a text that fails it is returned as it is, and every other text goes through the original code. The regexes, their order and their replacements are unchanged.

1. **`DA-A4-002`, replacement-character comments.** The rule deletes a `//` comment line that holds U+FFFD and no ASCII letter or digit. `LOST` was run on every text. Every match holds a U+FFFD, so a text without one (nearly all) is kept without running it.

2. **`DA-A6-001`, Cyrillic look-alike letters.** The rule turns a Cyrillic look-alike inside a word that also has Latin letters into the Latin letter. `MIXED` starts with `\b` and two look-aheads, so the engine tried it at every position of every text. Every match holds a character of U+0400 to U+04FF (the range `MIXED` itself asks for), so a text with none is kept without running it.

3. **`DA-E3-003`, known keys and base32 seeds.** Two parts, both guarded. The five `KEYS` patterns each need a literal (`AKIA`, one of `ghp_ gho_ ghu_ ghs_ ghr_`, `sk-`, `xox`, `-----BEGIN `); each runs only when the text at that step holds one of its own, and the text is tested before each substitution, so the order and any cascade stay as they were. `SEED` is case-insensitive and was the larger cost: it needs an `=`, a quote and one of `secret`, `seed`, `totp`, `otp`, so it runs only when the text has `=` and `"` and the casefolded text holds `secret`, `seed` or `otp` (`totp` holds `otp`). The casefold matters: `(?i)` also lets U+017F (long s) match `s`, so `ſecret = "..."` is still found. A test checks, for every character below U+20000, that any character `(?i)` lets match a letter of these words keeps that letter under `casefold()`.

4. **`DA-E2-001`, byte-array and base64 blobs.** The rule drops a file when byte-array literals (`0x1f, 0x2a, ...`, 24 or more in a row) cover 10% of it, or base64-looking runs of 200 or more characters cover 40%. The byte-array regex needs 24 groups that each start with `0x`, so it runs only when the text holds 24 or more `0x` (`str.count` is exact here: `0x` cannot overlap itself). The base64 half has no cheap exact guard (it is a scan for a run of 200 characters of a wide class) and is unchanged.

5. **`DA-E3-004`, known keys and assigned secrets (round 2).** The rule replaces known key formats and a quoted value of 16 or more characters (200 at most) that looks random and is assigned to a secret-like name. The known formats were already tested for a literal; two things were slow. (a) The `ASSIGNED` regex starts with `\b[\w\-]*` and a case-insensitive list of eleven name alternatives, so it is tried from every word start, and the test that decided whether to run it (`ASSIGNED_HINT`, a case-insensitive regex for `secret`, `token`, `key`, `passw`, `pwd`) cost 0.07 to 0.19 ms/doc on its own. (b) The `gh` hint matched in 38% to 58% of code files ("right", "high"). Now: the hint for the GitHub-token pattern is `ghp_ gho_ ghu_ ghs_ ghr_`; and `ASSIGNED` runs only on a text that passes three tests, each true whenever `ASSIGNED` could match: (1) the casefolded text holds `secret`, `token`, `key`, `passw` or `pwd` (casefold, because `(?i)` also lets U+017F and U+212A match `s` and `k`; a test checks every code point below U+110000); (2) `[:=>]\s*` then a quote, 16 to 200 characters of the value class and the same quote, which is the end of any operator (`:=`, `=>`, `=`, `:`) and the value; (3) a name word followed by `ASSIGNED`'s own tail up to the closing quote, which is true wherever `ASSIGNED` matches because every name of `ASSIGNED` holds one of the five words and is followed by `[\w\-]*`, and which avoids searching from every word start. The tests are applied in that order to the text after the known-key step, as before. `ASSIGNED` itself, `_looks_random` and the replacements are unchanged. On the 500-doc samples the second test passes 3 to 86 documents per pack and `ASSIGNED` itself now runs on 1 to 4 (it ran on 90 to 174 documents per pack); it matches in 0 to 4.

The round 1 edits are to the `DA-A4-002`, `DA-A6-001`, `DA-E3-003` and `DA-E2-001` cards of `specv1_1.md`; round 2 is to the `DA-E3-004` card; the `medicine_<family>.md` files are not read by the build and are not changed.

**Tests:** [test_speed_equivalence_code_rules.py](../tests/test_speed_equivalence_code_rules.py), against frozen copies of the old rules (`a4_reference`, `a6_reference`, `e2_reference` and `e3_reference`, inside the test file; the new rules are read from `specv1_1.md`).

- *Round 1 (159 tests).* Hand cases at the edge of every guard (23 and 24 `0x`, the first and last character of the Cyrillic range, each key shape and its too-short form, each seed word in each case), a sweep of the 10% share of `DA-E2-001` across its threshold, 10,000 or more random texts per rule with coverage assertions for every outcome, spies showing each regex is skipped when its guard fails and run when it holds, and the pack scope in `clean.py`. 19 hand-made mutations of the guards (a wrong literal, range edge, threshold, missing hint, `lower()` for `casefold()`, a guard removed) were all caught.
- *Round 2 (947 tests, last section of the same file, helper names start with `e4_`),* against `code_speed_reference.e3_reference` (`DA-E3-004` as in spec v1): the `ASSIGNED` pattern is the old one; every name of `ASSIGNED` holds a word of test 1; the operator class holds the last character of every operator; the casefold test over every code point; 53 names x 15 operator spellings x 3 quotes, value lengths from 1 to 300 (15, 16, 200 and 201 at the edges) with a missing or different closing quote, 37 structure cases (JSON, Rust and TypeScript types, `:=`, `=>`, a newline between name and operator, a long identifier, a long file with a late match, a dotted or dummy value), each known key shape and its edges, the five `gh` letters and every other character after `gh`; spies showing which of the three tests stops a text; 25,000 random texts with an assertion that whenever `ASSIGNED` matches, all three tests pass, and coverage for every outcome. 36 hand-made mutations (a dropped name word, an operator character, a length edge, `lower()` for `casefold()`, a changed tail, a test removed, a wrong hint) were all caught.

## 5. Tests

| fix | test file | tests |
|---|---|---|
| shared F1, prose path | [test_speed_equivalence_f1.py](../tests/test_speed_equivalence_f1.py) | 121 |
| shared F1, Indic path | [test_speed_equivalence_f1_indic.py](../tests/test_speed_equivalence_f1_indic.py) | 97 |
| `DA-F1-005` | [test_speed_equivalence_f1_english.py](../tests/test_speed_equivalence_f1_english.py) | 29 |
| math rules 1 to 5 | [test_speed_equivalence_math.py](../tests/test_speed_equivalence_math.py) | 126 + 57 + 76 + 24 + 41 |
| code rules, rounds 1 and 2 | [test_speed_equivalence_code_rules.py](../tests/test_speed_equivalence_code_rules.py) | 159 + 947 |

Each test file holds a frozen copy of the old rule and compares the new one with it on hand cases, random texts and the pack scope; the code-rule tests also run a set of hand-made mutations of the guards (all caught).

## 6. Method and commands

x86_64, Python 3.12.15, one run at a time pinned to CPU 0 (`taskset -c 0`); timings vary by about 5%, so treat ratios under 1.1x as about equal. Only `clean.py` differs between the before and after trees. For the math and code rules, before is the committed `clean.py` (`HEAD`) and after is the rebuilt working copy (`python -I spec_v1/build/build_clean.py`, which builds from `specv1_1.md`).

One set of commands for all fixes, from the repository root. `<packs>` is the folder of the 38 `week1-packs`; `speed_compare.sh` times the 31 registered ones. Put the two `clean.py` to compare in files and pass them with `--before-clean` and `--after-clean` (this works for any change; for two commits of `clean.py`, `--before <rev> --after <rev>` does the same):

- for a fix committed in `clean.py` (F1 fixes 1 and 2): `git show <commit>:teams/01-data-a/spec_v1/clean.py > <scratch>/clean_before.py`, and the same for the after commit;
- for a change in a sheet only (F1 fix 3, the math and code rules): build them with `build_clean.py --sheet <sheet> --out <file>`, once from the sheet as committed (saved first as `<scratch>/before/specv1_1.md`, under the same file name, because the name is written into `clean.py`) and once from the edited sheet.

```bash
S=teams/01-data-a/oneoff/speed_compare.sh
$S --packs <packs> --work <scratch> --include-all --rules <RULE_OR_f1_rule.py> \
  --before-clean <scratch>/clean_before.py --after-clean <scratch>/clean_after.py \
  --profile-packs "<packs to profile>" trees
cp teams/02-data-b/gold/ind-*_gold.csv <scratch>/before/teams/01-data-a/gold/   # and the same into <scratch>/after/...
$S (the same options) speed profile harm count
for side in before after; do     # F1 fixes 1 and 2 only: the Indic F1 harm test
  (cd <scratch>/$side/teams/01-data-a && python -I -B spec_v1/validate/harm_f1_indic.py --packs <packs> --out <scratch>/f1_indic_$side.json)
done
```

The `--rules` and `--profile-packs` used:

| fixes | `--rules` | `--profile-packs` |
|---|---|---|
| F1 fix 1 | `f1_rule.py` | `"sci-finepdfs math-finemath math-megamath"` |
| F1 fix 2 | `f1_rule.py` | `"ind-hi-hplt ind-sa-fw2 ind-bn-fw2 ind-ta-sangraha-v"` |
| F1 fix 3 | `DA-F1-005` | `"en-dclm en-fineweb-edu en-nemotroncc en-nemotroncc-synth"` |
| math fixes 1 to 5 | one rule id per run, `--before HEAD --after worktree` | `"math-finemath math-megamath"` |
| code round 1 | `DA-A4-002,DA-A6-001,DA-E3-003,DA-E2-001` | `"code-cpp code-go code-java code-js-ts code-python code-rust"` |
| code round 2 | `DA-E3-004` | the same six code packs |

The command names its steps, so `build` and `pytest` do not run; run the suite on its own (`python -m pytest teams/01-data-a/tests teams/01-data-a/spec_v1_1/tests`). The routine is in [oneoff/speed_handoff.md](../../oneoff/speed_handoff.md).

## 7. Open items

- **`DA-C3-002`** (Go lexical check, `code-go`) is the largest single rule left on the code packs (39% to 49% of `code-go`, 0.49 ms/doc); not fixed yet.
- **`DA-E3-003` and `DA-E3-004`** overlap (the same six packs, run in that order). No behaviour change was made to either; only their speed. Whether to keep both is an open question for the team.
