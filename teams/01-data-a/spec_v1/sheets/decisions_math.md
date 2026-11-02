# decisions_math: why each math rule was picked or not

Packs: `math-finemath` (gold 86), `math-megamath` (gold 26). Limit `max(1, floor(1% of gold))` = 1 document on both.
Inputs: every math diagnosis PR. finemath: SomaKorada07 #61 (labels and medicine), uz9ai #41 (labels). megamath: asraj
#146 (labels; its `medicine.md` is a copy of its `labels.csv`), mukund-23 #102 (labels), kunal2016 #151 (labels and medicine).
Gold built with `build_gold.py`; refreshed on `g1-harm-test` on 31 Oct (86 / 26; it was 30 / 18). Labelled-row counts below are from the 30 Oct labels. Numbers in `medicine_math.md` are per pack, never pooled.

**v1.1: the finemath rules are SomaKorada07's own functions.** In v1 her sheet (#61) described the medicines in words and
fragments, so kunal2016 wrote them as code. On 31 Oct she reviewed those rewrites on #19 and put every medicine in #61 as a
complete `medicine_<code>(text)` function (commit `cc74c7e`), each matching her `medicines.py` on the 500-doc pack. v1.1
copies her functions unchanged (rule fields, the `pack_id` guard and `\u` escapes for non-ASCII characters added) and
adds her A6 and D3. Her F1 is not used: F1 is the one shared rule. kunal2016's megamath C5 drop is unchanged.

## Per disease

| code | rule(s) | packs | decision | why |
|---|---|---|---|---|
| A3 | `DA-A3-001` | both | keep | finemath 10/11 (v1: 9; her cp866 repair and the extra lead characters), megamath 8/21, 0 gold. Runs first: a repaired run can hold an invisible character, which A1 then removes. |
| A1 | `DA-A1-001` | finemath | keep | 14 of 15 labelled rows, 0 gold. megamath has no A1 rows. |
| A6 | `DA-A6-001` | finemath | keep (new) | finemath 5/9, 0 gold: the Symbol-font map for 46 codes. Changes nothing on megamath, so it is off there. |
| A5 | `DA-A5-001` | both | keep | finemath 6/6, megamath 9/12, 0 gold. Ligatures and fullwidth punctuation only; never full NFKC (x² must stay). |
| B2 | `DA-B2-001` | both | keep | finemath 3/8, megamath 6/112, 0 gold. Skips documents that hold code; most megamath B2 rows do. |
| B4 | `DA-B4-001` | both | keep | finemath 9/18, megamath 1/10, 0 gold. Leaves `<EMAIL>`, the F1 tag. |
| B5 | `DA-B5-001` | both | keep | finemath 5/28 (7 docs changed: case-insensitive BBCode), megamath 1/192, 0 gold. Formulas stripped by the scraper cannot be repaired; those documents are `drop` by verdict. |
| C5 | `DA-C5-001` (drop), `DA-C5-002` (fix) | drop: megamath; fix: both | keep both | They fix different rows: the drop takes answers.com "related questions" pages (megamath 10); the fix removes "See more:" and title-case keyword lines (finemath 5/51, megamath 2/168). |
| D3 | `DA-D3-001` | both | keep (new) | finemath 5/10, megamath 2/9, 0 gold. Removes lines that are mostly Cyrillic, Indic, CJK, kana, Hangul or Arabic; drops a page where those hold over 30% of the letters. Greek is left alone: it is maths. |
| C3 | `DA-C3-001` (drop), `DA-C3-002` (fix) | finemath | keep, as two blocks of one medicine | The preview drop runs before C1, which would otherwise delete the banner it reads; the teaser trim runs after the strips. Off on megamath: there the trim is not idempotent on one doc. |
| C1 | `DA-C1-001` | finemath | keep | finemath 109/328 (v1: 47; her full `C1_LINE`, `C1_SITE` and phpBB block), 0 gold. Off on megamath because, as she says, the site list was fitted on finemath; on megamath it would change 72 docs, all labelled C1, with 0 of 26 gold docs changed. She agreed (#61) to try it in v1.2 after a spot-check of the deleted lines on 10-15 of the 72 docs, mainly whole-line phrases such as Share, Views, Recommended, Tags:. |
| C2 | `DA-C2-001` | finemath | keep on finemath, off on megamath | finemath 40/187 (v1: 39; keeps repeated answer options and code-like passages, ruling 13), 0 gold. On megamath it changes 1 of 26 gold docs: inside the limit, but it would use all of it. |
| F1 | shared `../tools/f1_rule.py` | both | shared | One F1 for all families, per the TSAI ruling. On math it runs the prose path, last (TSAI, 1 Nov): 0 of 86 and 0 of 26 gold docs; it treats 4 finemath and 26 megamath docs. |
| C4, D4 | none | | no rule | Her sheet: a tested C4 rule caught 0 labelled cases and changed 2 clean docs; D4 (spun text) needs a language model. |
| G3 | none | | open | megamath loses hyphens and minus signs pack-wide (`2^n1` for `2^n-1`). No rule can restore them; documents whose maths became wrong are `drop` by verdict. |

## Combined

`make_harm_tests.py` (team `harm_test.py`): finemath 0/86, megamath 0/26 for every rule, every function and `clean()`
(`results/cleaner/harm_tests_f1_math_sci.md`). `clean()` on the whole pack, with the shared F1: finemath 177 fixed, 13 dropped,
310 kept; megamath 62 fixed, 10 dropped, 428 kept. Before F1 (30 Oct gold run, also 0 harm): 176 / 13 and 37 / 10. A second `clean()` changes nothing on any doc of either pack.

## Open

- Routing: `clean.py` sends a doc to its family by `pack_id` (`SCOPE`, built from `specv1.md`); each math rule also checks its `ORIGIN` packs.
- Gold is small (86 and 26): with 0 hits the harm rate is only shown to be below about 3.5% and 11.5%, so C1 on megamath waits for a spot-check (above).
- Reviewer for all 14 rules: SomaKorada07 checked them on #61 (1 Nov): same output as her functions on all 500 finemath docs, and every scope as she intended.
