# filters: Indic-aware filters for Data B (issue #214, G2)

Filters that understand Indic scripts and do not harm clean text. Each filter is a small function with a unit test and
a harm result for each pack, judged on that pack's own gold set (never pooled).

| File | What it holds |
|---|---|
| `medicine.md` | The filters, in the form `tools/harm_test_indic.py` reads (`**Disease:** <code>` and `medicine_<code>(text)`) |
| `test_filters.py` | 45 unit tests on made-up text, including ZWJ/ZWNJ counts before and after, NFC-only, nukta and chillu |
| `run_harm.py` | Runs the harm tool one pack at a time, with the pack's script set; writes `harm_<pack>.md` with the joiner counts |
| `harm_<pack>.md` | The harm result of each pack (part 4 of the medicine) |

## Filters
| Code | Filter | Whose code | Status |
|---|---|---|---|
| D1 | Script share: drop a document where another script dominates | Data B (no author had a D1 rule) | code, tests; harm run on 6 packs, all PASS (0 changed). On all documents of the 10 packs on hand: 0 dropped, 8 flagged |
| A1 | Invisible junk characters; ZWJ and ZWNJ are kept | the author's: adinathauti, PR #114 | code, tests; harm run on 6 packs, all PASS, but 0 changed: no pack on hand holds an A1 character |
| G1 | Broken vowel sign for Kannada, Devanagari, Malayalam, Tamil, Odia | the authors' code per script (see below) | code, tests; harm run on 6 packs, all PASS (0 changed; the Hindi pack ind-hi-sangraha-s is the first Devanagari run on real text) |

D2 (romanised text) is @keshavamurali's (#213); G2/visarga/F1/F2 and the per-pack fixes are out, as listed in the issue.

## Whose code: the rule
**#211 (TSAI's Data B rules task):** "Keep each author's code as they wrote it, and mark anything you add to make it
fit." `indic_rules/README.md` (PR #240) repeats it: "The author's code, unchanged", and what Data B changes is marked in
the code and listed. #240 also accepts a **same-language borrowed rule** for a pack that has none of its own
(Pritish52718, 3 Nov). The only other changes allowed so far are TSAI's rulings on #240: a visarga used as a colon
is clean, also with a space before it, so a visarga stays as written. This is not stated in #214 or #217; it is in #211 and #240.

What that means here:
- **A1**: PR #114's rule (adinathauti). PR #109's (SreekanthZipsy) removes the same 12 characters; a test compares both, on the author's own text and on random strings. #114 is one regex call, about 20 times faster. Two marked changes: the 12 characters are written as escapes (the author typed invisible characters), and medicine_a1 is added (the harm tool's name). Characters outside the `DISEASES.md` list (U+200E, U+200F, U+2060 and others) are not touched.
- **G1**: each script's function is the author's, renamed (they were all called `medicine_g1`) and with only the marked
  changes. One added function, `_g1_script`, picks the script of the document, because a text-only function is not told the pack.

| Script | For pack | Author's code | Marked change |
|---|---|---|---|
| Kannada | `ind-kn-sangraha-s` | keshavamurali #47 (`DB-G1-005`, a same-language borrow) | visarga out of the set it joins (TSAI, #240) |
| Devanagari | `ind-mr-sangraha-v` | thinktinkergreen #50 (`DB-G1-006`, a same-language borrow) | visarga-to-colon step removed (TSAI, #240) |
| Malayalam | `ind-ml-fw2` | umeshnmenon #116 | visarga out of the set it joins; `drop_stacked_sign` left out (it drops a whole document) |
| Tamil | `ind-ta-fw2` | Dharshanthaigu #169 | none |
| Odia | `ind-or-fw2` | Pritish52718 #86 | none |

Bengali, Gujarati, Telugu and Gurmukhi have no owner's code in this file. For them `medicine_g1` uses **Data B's own fallback**
(`_g1_generic`, marked as ours in `medicine.md`): it removes a space or line break between a consonant and a following vowel sign or
virama, and nothing else (the visarga and anusvara are not touched). It is the Devanagari rule (#50) on each script's code points. It is
harm-tested on real gold sets only for Bengali (`ind-bn-fw2`, `ind-bn-sangraha-v`) and Telugu (`ind-te-sangraha-s`): 0 documents changed in each.
Gujarati and Gurmukhi are covered by the unit tests only. A text with no Indic letters is left as it is.
The G1 functions of #116, #169 and #86 are from their open PRs (not on `main`), copied by script, not retyped. Each reproduces its
author's own count on the full pack: Tamil 22 of 500 (#169 says 22), Malayalam 19 of 500 (#116: 19), Odia 4 of 500 (#86: 4).

## What every filter here must have (#214 step 2; #217 "How we work")
| Requirement | How it is met and checked |
|---|---|
| A small function | `medicine_<code>(text)` in `medicine.md` |
| A unit test | `test_filters.py`, on made-up text only; mutation-checked (a filter that strips ZWJ, or eats a visarga, fails it) |
| A before-and-after ZWJ and ZWNJ count | in the tests, each document keeps its joiners (`EveryFilterTest`, which fails a filter that has no joiner samples in `JOINER_SAMPLES`); on real text, `run_harm.py` writes the counts before and after into each `harm_<pack>.md` under "ZWJ and ZWNJ before and after" |
| NFC only, never NFKC | `test_only_nfc_in_the_code` fails if the code calls any form but NFC; the harm tool's `form` column checks the result |
| Never remove ZWJ or ZWNJ | the harm tool's `joiners` column and the counts above |
| Nukta and Malayalam chillu unchanged (#211, Team 3's normalizer #134) | `test_nukta_and_malayalam_chillu_are_not_changed` |
| Only counts and IDs committed, never document text | `harm_<pack>.md` holds counts; the tests use made-up text |

Joiner counts on real text: the packs on hand hold almost none (ZWJ 0 and ZWNJ 0 in every pack except ind-or-fw2, which has 2 ZWNJ in
1 document and no gold set). So the real-data count is 0 to 0, and the made-up tests (all nine scripts for G1) carry the joiner check.

## D1 in short
Count the letters of a document by script (NFC, letters and combining signs only). Share of the pack's script:
0.50 or more keep; under 0.30 with another script the largest: drop; in between: flag and keep; under 20 letters: keep.
A document with a few English words is kept. D1 only returns `True` or `False`, never new text. The pack's script is read from `D1_SCRIPT`, which
`run_harm.py` sets (a text-only function cannot be told the pack). Without `D1_SCRIPT` it asks only that the text is mostly in some Indic script.
Limit: Hindi, Marathi and Sanskrit share Devanagari, so Hindi in a Marathi pack is not caught.

## Run
```
python test_filters.py                                        # 45 tests, no data needed
python run_harm.py --packs-dir PATH_TO_PARQUETS               # all packs, one at a time
python run_harm.py --packs-dir PATH_TO_PARQUETS --packs ind-kn-fw2
```
`run_harm.py` needs `pyarrow` (`pip install pyarrow`) to read `<pack_id>.parquet`. By hand, one pack:
```
D1_SCRIPT=Kannada python ../tools/harm_test_indic.py --medicine medicine.md --pack ind-kn-fw2.parquet --gold-dir ../gold --md-out harm_ind-kn-fw2.md
```
(PowerShell: `$env:D1_SCRIPT="Kannada"` first.) A filter passes when it changes or drops at most max(1 document, 1%) of the
pack's gold set and the tool's `joiners` and `form` columns are both ok.

## Harm results (run 12 Nov 2026, `medicine.md` sha256 in each `harm_<pack>.md`), each pack on its own gold set
Changed / dropped, for D1, A1, G1 and "all in order"; `joiners` and `form` are ok in every row.

| Pack | Gold docs | D1 | A1 | G1 | All in order | Result |
|---|---:|---|---|---|---|---|
| ind-bn-fw2 | 227 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | PASS |
| ind-bn-sangraha-v | 137 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | PASS |
| ind-kn-fw2 | 115 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | PASS |
| ind-kn-sangraha-s | 22 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | PASS |
| ind-te-sangraha-s | 24 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | PASS |
| ind-hi-sangraha-s | 24 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | PASS |
| ind-ta-fw2, ind-ta-sangraha-s, ind-ml-fw2, ind-or-fw2 | 0 | | | | | gold set empty, not testable |
| ind-te-fw2, ind-te-sangraha-v, ind-kn-sangraha-v, ind-ta-sangraha-v, ind-hi-fw2, ind-hi-hplt, ind-hi-indiccorp, ind-hi-sangraha-v, ind-mr-fw2, ind-mr-sangraha-v, ind-gu-fw2, ind-sa-fw2 | per `../gold/gold_coverage.csv` | | | | | not run yet: pack file missing |

**Information only, not a harm result** (packs with no gold set, all 500 documents; ZWJ/ZWNJ and NFC differences: 0 everywhere):

| Pack | D1 changed/dropped | A1 | G1 changed |
|---|---|---|---|
| ind-ta-fw2 | 0 / 0 | 0 | 22 of 500 |
| ind-ml-fw2 | 0 / 0 | 0 | 19 of 500 |
| ind-or-fw2 | 0 / 0 | 0 | 4 of 500 |
| ind-ta-sangraha-s | 0 / 0 | 0 | 1 of 500 (no reader has looked at it) |

On the packs run, the lowest script share among gold documents is 0.81 (ind-bn-fw2) and 0.93 or higher elsewhere,
far above the 0.30 drop line. Over all documents of the 10 packs on hand, D1 drops none. It flags and keeps 8 (share 0.31 to 0.44, all with Latin letters
as the largest other script; in ind-bn-fw2, ind-kn-fw2 (2), ind-ml-fw2, ind-or-fw2, ind-ta-fw2 (2) and ind-hi-sangraha-s). **A pass on gold shows no harm. It does not show that a filter catches the defect:** the packs with most of the
D1 marks (ind-te-sangraha-v, ind-sa-fw2, ind-hi-hplt) and most A1 marks are among the missing pack files.

## For Friday (#217: Gate 2 asks for script-aware filters that pass the harm test)
- [x] D1, A1 and G1: functions, unit tests, before-and-after ZWJ/ZWNJ counts, NFC only.
- [x] Harm result for each pack whose pack file is here: 6 tested (PASS), 4 "gold set empty, not testable".
- [ ] Harm results for the 12 packs with gold documents whose pack file is missing (list above).
- [ ] Open the PR with `Closes #214` as the first line of its description; it must pass pr-guard.
- [x] Draft of "our proposal for the native Indic share" (#217, due Thu 12 Nov): `../native_indic_share_v1.md`.

Open questions for TSAI (invisible characters, author-code rule, D1 and Devanagari, missing packs): [questions_for_tsai.md](questions_for_tsai.md).
D1 proposal (what we propose to run, the evidence, what is not known): [../d1_proposal_v1.md](../d1_proposal_v1.md). Numbers: `python d1_share_stats.py`.
