# Gate 3: the Indic shards (Data B summary)

Week 3, task 6 of the Data B work order, finished as week 4, task 4. Updated Tue 24 Nov 2026 with Bengali (#766).
One reader file is still to come (section 3): the Tamil second reader, due Tue 24.

Gate 3 asks: "Indic shards keep ZWJ and ZWNJ, pass the reader audit and stay inside approved drop rates."

**Inputs.** TSAI's 18 Indic token shards of 16 Nov (sample v0 train parts, after `clean.py` and F2, frozen tokenizer
p1536, sha256 `e6b93a93...`). The 22 raw sample v0 Indic train parts they were made from (from Data A; sha256 in
`audit/raw_parts_SHA256SUMS`). Every shard document is in its raw part.

## 1. ZWJ and ZWNJ

Measured with `audit/indic_audit.py` (#523): the counts of every kept document, in the raw text and in the shard text
decoded with the frozen tokenizer. The tokenizer's own chillu fold (Malayalam) is the one allowed change.

| | Raw | Shard | Documents changed | Changed in kept text |
|---|---:|---:|---:|---:|
| ZWNJ (U+200C) | 619 | 619 | 0 | 0 |
| ZWJ (U+200D) | 11,179 | 11,139 | 26 | **0** |

- **ZWNJ: no change in any pack.**
- **ZWJ: no joiner was lost from text that cleaning kept.** The 40 missing ZWJ are in 26 `ind-hi-indiccorp` documents.
  In each of them, cleaning cut a trailing "Also Read" link line, and the ZWJ were in that line (38 of the 40 in half
  forms, virama + ZWJ + consonant). The shard text of each of these documents is one unbroken piece of the raw text.
- **A second count, made independently, agrees exactly** (task 4, `audit/zwj_counts.py` and `audit/zwj_counts.csv`,
  #653): over the same 273,114 kept documents, ZWJ 11,179 raw and 11,139 shard, ZWNJ 619 and 619, and 26 documents
  changed, all in `ind-hi-indiccorp`.

### Visarga

Data A's #566 found the visarga turned into an ASCII colon in the v0-clean sample (ః U+0C03 to `:` in
`ind-te-sangraha-s`, and in the Hindi packs). `indic_audit.py` checks the shards for it (#576): it counts the
visarga of each script in every kept document, and the words in kept text whose visarga cleaning turned into `:` or
deleted. Tamil uses the aytham ஃ (U+0B83).

| Language | Visarga raw | Visarga shard | Documents with fewer | Words edited in kept text |
|---|---:|---:|---:|---:|
| hi | 26,535 | 26,352 | 109 | 0 |
| bn | 23,681 | 23,400 | 172 | 0 |
| te | 28,352 | 28,308 | 7 | 0 |
| kn | 21,520 | 20,620 | 650 | 0 |
| ta | 7,369 | 7,369 | 0 | 0 |
| mr | 14,444 | 14,342 | 89 | 0 |
| gu | 6,441 | 6,238 | 105 | 0 |
| sa | 404,275 | 402,911 | 422 | 0 |
| **all** | 532,617 | 529,540 | 1,554 | **0** |

- **No visarga in text that cleaning kept was turned into a colon or deleted.** In the 1,554 documents with fewer
  visargas, they went out with text that cleaning removed: whole lines, short phrases such as a Marathi "हे ही वाचाः"
  ("Also read:") tail, and Sanskrit wiki markup.
- The damage #566 found is in the v0-clean sample only. The same check on raw vs v0-clean finds 3,490 edited words in
  `ind-te-sangraha-s`, 4,540 in `ind-ta-sangraha-v` (ஃ to `:`, not in #566) and 73 in the Hindi packs. The shards come
  from a later cleaning run without the visarga-to-colon step (TSAI, #240 review, 5 Nov). Indic audits should read the
  shards, not v0-clean.

## 2. Drop rate per language

Documents in the raw part with no row in the shard. The work order flags a filter that drops over 20%: no pack drops
over 20% in total, so no single filter does.

| Language | Packs with a shard | Raw | Kept | Dropped | Drop rate | Highest pack | ZWJ raw / shard | ZWNJ raw / shard |
|---|---|---:|---:|---:|---:|---|---:|---:|
| hi | fw2, hplt, indiccorp, sangraha-s, sangraha-v | 156,831 | 153,777 | 3,054 | 1.95% | ind-hi-sangraha-s 9.82% | 11,178 / 11,138 | 564 / 564 |
| bn | fw2, sangraha-v | 21,533 | 20,816 | 717 | 3.33% | ind-bn-fw2 4.47% | 0 / 0 | 0 / 0 |
| te | fw2, sangraha-s, sangraha-v | 19,388 | 18,682 | 706 | 3.64% | ind-te-sangraha-s 7.59% | 0 / 0 | 42 / 42 |
| kn | fw2, sangraha-s, sangraha-v | 21,576 | 21,274 | 302 | 1.40% | ind-kn-sangraha-v 2.30% | 0 / 0 | 13 / 13 |
| ta | sangraha-v | 6,796 | 6,795 | 1 | 0.01% | ind-ta-sangraha-v 0.01% | 0 / 0 | 0 / 0 |
| mr | fw2, sangraha-v | 23,632 | 23,414 | 218 | 0.92% | ind-mr-fw2 1.83% | 1 / 1 | 0 / 0 |
| gu | fw2 | 23,118 | 22,689 | 429 | 1.86% | ind-gu-fw2 1.86% | 0 / 0 | 0 / 0 |
| sa | fw2 | 5,908 | 5,667 | 241 | 4.08% | ind-sa-fw2 4.08% | 0 / 0 | 0 / 0 |
| **all** | 18 packs | **278,782** | **273,114** | **5,668** | **2.03%** | | 11,179 / 11,139 | 619 / 619 |

No shard yet (no cleaner rules; task 1): `ind-ml-fw2`, `ind-or-fw2`, `ind-ta-fw2`, `ind-ta-sangraha-s`. Malayalam and
Odia therefore have no shard at all, and Tamil has only `sangraha-v`.

The `sangraha-s` shards (hi, kn, te) are machine-translated text. They are counted here, but they are not part of the
native Indic share of the mix (`mix/indic_share_v1.md`, #522).

## 3. Reader audit

Task 3: each reader reads 50 cleaned documents of their language each day, Wed 18 to Fri 20
(`audit/day_D4_<lang>.md` to `audit/day_D6_<lang>.md`). A second reader on the same documents, reading on their own,
gives a reader agreement. Week 4, task 2 added Sanskrit (#711, 25 documents). R1 and R2: rotation members check one
shard each for script damage and lost joiners (`audit/rotation_<handle>.md`).

| Language | Reader files | Documents read | With a finding | Second reader | Rotation check (R1, R2) |
|---|---|---:|---:|---|---|
| te | D4 (#527) | 50: 25 `fw2`, 25 `sangraha-v` | 27 | none | `ind-te-sangraha-v` (#533, final in #672): 50 documents, G1 3 rows in 1, A6 1, D3 12 in 2, 0 ZWJ/ZWNJ damage |
| kn | D4 to D6 (#528) | 150: 75 `fw2`, 75 `sangraha-v` | 38 | #569, same 150: 34 with a finding. Same verdict on 130 of 150 (86.7%), κ 0.63 | `ind-kn-sangraha-v` (#550): 100 documents, G1 4 in 3, A6 5 in 4, 0 ZWJ/ZWNJ |
| ta | D4 to D6 (#529) | 150 `sangraha-v` | 84 | D4: due Tue 24 | `ind-ta-sangraha-v` (#619): 50 documents, A6 5, 0 ZWJ/ZWNJ in the sample or the shard |
| sa | D4 (#711) | 25 `fw2` | 11 | Same 25: 8 with a finding. Same verdict on 22 of 25, κ 0.75 (21 of 24, κ 0.73, without `4f7a6a85a601d7bf`, see below) | |
| bn | D4 to D6 (#568, #766) | 150: 75 `fw2`, 75 `sangraha-v` | 100 | none | |
| hi | none in the core team | | | | `ind-hi-fw2` (#560): 50 documents, G1 2 in 1, A5 4 in 2 (source spelling), 0 ZWJ/ZWNJ |
| gu | none in Data B | | | | `ind-gu-fw2` (#570), by code point only: 50 documents, G1 1, A6 14 runs in 7, 0 ZWJ/ZWNJ in the sample |
| mr | none in Data B | | | | |

"Same verdict" counts documents both readers marked `ok`, or both marked with a finding; κ is Cohen's kappa on that
verdict. In Sanskrit, all 3 disagreements are documents the first reader flagged and the second marked `ok`: two
scanned commentary pages and one document with a repeated line and lost word spaces.

**Damage from cleaning.** Every damage row (G1 to G4) in the reader files on main and the rotation files was
compared with the raw part after p1536's own normalizer (`audit/source_check.py`): a row is `source` when the
document is unchanged by cleaning, or when the 12 characters on each side of its offset are also in the raw text (for
a cut start or end: the raw text starts or ends the same way).

| Files | Damage rows | Also in the raw text (`source`) | From cleaning |
|---|---|---:|---:|
| te D4 | G1 4 | 4 | 0 |
| kn D4 to D6, both readers | G1 5, G3 5 | 10 | 0 |
| ta D4 to D6 | G3 23, G4 47 | 70 | 0 |
| sa D4, both readers | G3 7, G4 2 | 7 | 2 |
| bn D4 to D6 | G2 2, G3 20, G4 2 | 23 | 1 |
| rotations: kn, gu, hi, ta | G1 7, G3 5 | 12 | 0 |
| **all** | **129** | **126** | **3** |

- **The 3 rows from cleaning are two findings.** `DB-B4-004` in `4f7a6a85a601d7bf`, read by both Sanskrit readers
  (below). And `DB-C5-007` in `d690f90a5f282228` (`ind-bn-fw2`): it removed 12 English list items from the middle of
  a Bengali tutorial page, because it reads 5 or more bullet lines of 4 or more words as a related-news ticker
  (#766). Not fixed.
- **No joiner was lost in cleaning.** The only G2 rows are 2 Bengali ones: a word written without its ZWJ in the raw
  text (`source`).
- The 47 Tamil G4 rows are the aytham ஃ written for a colon, from a legacy font converter (#619). The aytham count is
  the same in the raw text and the shard (7,369, section 1), so cleaning did not add them. #619 suggests a source
  medicine for later, after a harm test.
- The Telugu rotation's 3 G1 rows (#672, not yet on main) were checked against the raw part in its review (`source`).
- Other changes by cleaning that readers noted are intended: F1 put `<PHONE>` in place of an author's phone number
  (`476ebc3ae4e21d16`, `ind-te-fw2`); cleaning removed site headers, link lists and a Hindi line from Sanskrit pages.

**`DB-B4-004` (#734).** In `4f7a6a85a601d7bf`, cleaning removed the verse numbers १०० to
१२० after `॥` (1 to 99 are kept). The rule is Data B's Sanskrit medicine `DB-B4-004` in
`teams/01-data-a/spec_v1_1/clean.py`: Python's `\d{3,}` also matches Devanagari digits, so it deletes verse numbers
from 100 up and numbers written next to a word, such as years. In the `ind-sa-fw2` shard that is 491 Devanagari
numbers in 97 of 5,667 documents (#734). **Fixed on main by #767**: the rule keeps verse numbers and years and still
removes the wiki markup, with a regression test. The corpus-v1 job and `pipeline/clean.json` pin `clean.py`
`d275556e…`, the file on main. The second reader's file was committed after this finding was posted on #733, so the
Sanskrit agreement is also given without this document (table above).

How (`audit/source_check.py`, with the raw parts of `audit/raw_parts_SHA256SUMS`, all hashes checked):

```
python -I source_check.py --shards shards-p1536 --raw raw --tokenizer p1536_tokenizer.json \
    day_D4_te.md day_D4_kn.md day_D5_kn.md day_D6_kn.md day_D4_kn_r2.md day_D5_kn_r2.md day_D6_kn_r2.md \
    day_D4_ta.md day_D5_ta.md day_D6_ta.md day_D4_sa.md day_D4_sa_r2.md day_D4_bn.md day_D5_bn.md day_D6_bn.md \
    rotation_uz9ai.md:ind-kn-sangraha-v-train-000000 rotation_AjaySnl.md:ind-gu-fw2-train-000000 \
    rotation_rjvim.md:ind-hi-fw2-train-000000 rotation_abinesh1.md:ind-ta-sangraha-v-train-000000
all {'G1 source': 16, 'G2 source': 2, 'G3 CHECK': 3, 'G3 source': 57, 'G4 source': 51}
rows to check by hand: 3
  day_D4_sa.md 4f7a6a85a601d7bf G3 8753
  day_D4_sa_r2.md 4f7a6a85a601d7bf G3 8753
  day_D5_bn.md d690f90a5f282228 G3 4547
wall 10.0 s
```

All 3 were read by hand: they are the two findings above.

Languages with no reader are reported as not read, not as passed. 10 of the 18 shards have a reader or rotation
file (`te-fw2`, `te-sangraha-v`, `kn-fw2`, `kn-sangraha-v`, `ta-sangraha-v`, `sa-fw2`, `bn-fw2`, `bn-sangraha-v`,
`hi-fw2`, `gu-fw2`). Not read: `hi-hplt`, `hi-indiccorp`, `hi-sangraha-v`, `mr-fw2`, `mr-sangraha-v`, and the three
`sangraha-s` (machine-translated) shards.

## 4. Language labels of script-sharing pairs

Task 5 (`audit/lang_label_check.md`; #622, corrected in #673; #531): Hindi, Marathi and Sanskrit in Devanagari, and
Assamese in the Bengali packs. Each document gets two signals, IndicLID-FTN (a paragraph vote) and marker words, and is
flagged only when both name the same other language. The check runs on the 10 CAP-1 packs that are the raw input of the
hi, mr, sa and bn shards (the same files, by sha256).

| Documents in the 10 packs | Count |
|---|---:|
| All | 209,926 |
| Judged | 206,571 |
| Agree with the pack's language | 205,244 (99.36% of judged, 97.77% of all) |
| Flagged as another language | 2 |
| Uncertain | 114 |
| Disagree but too short to trust IndicLID (`short_disagree`) | 1,211 |
| Not judged: too short (3,138) or another script (217) | 3,355 |

- **No disagreement detected; this does not prove the labels are right.** The marker words are consulted only when
  IndicLID disagrees with the pack, so a language that IndicLID reads as Hindi or Bengali cannot be flagged. The check
  catches 0 of the 6 same-script documents readers marked D1 (IndicLID has no Kumaoni class and reads Vedic Sanskrit as
  Hindi).
- **The 2 flags are right.** Both are Sanskrit in Bengali script in `ind-bn-sangraha-v`; a Sanskrit reader confirms both.
- **Reader check of the uncertain ones (Sanskrit, 9 documents, two readers):** none of the 7 uncertain documents where
  IndicLID said Sanskrit is Sanskrit alone. They are mixed pages (Sanskrit or Prakrit with Hindi) or Hindi, so
  `uncertain` is the right verdict.
- **No false flags** on 1,590 gold documents or 4,987 reader-labelled documents without D1.
- **Pending:** the Marathi (4), Hindi (4) and Bengali (3) reader rows of `audit/lang_label_review_sample.csv`.
- **Not covered:** same-script languages IndicLID has no class for (Kumaoni and other Pahari languages, Prakrit,
  Apabhramsha); packs outside hi, mr, sa and bn; and mixing across scripts, such as Hindi runs in a Telugu document
  (`85c371eab86e00d1`, found by the Telugu reader in #618).

## 5. Result

| Gate 3 condition | Result |
|---|---|
| Indic shards keep ZWJ and ZWNJ | **Yes** for the 18 shards: 0 documents with a joiner changed in kept text (section 1) |
| (and the visarga, #566) | **Yes** for the 18 shards: 0 words with a visarga turned into `:` or deleted in kept text (section 1) |
| Pass the reader audit | **Yes, with one fix**, for the 10 shards read: of 129 damage rows, 126 are in the raw text, and no joiner was lost in cleaning. The other 3 are two findings from cleaning (section 3): `DB-B4-004` (#734), fixed on main by #767, and `DB-C5-007`, 12 English list items removed from one Bengali document, not fixed |
| Inside approved drop rates | No pack drops over 20%; highest 9.82% (`ind-hi-sangraha-s`); all packs 2.03% (section 2) |

Not covered: Malayalam, Odia and two Tamil packs have no shard. 8 of the 18 shards have no reader file (section 3);
Marathi has no reader at all, and Gujarati was checked by code point only.
