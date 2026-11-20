# Language labels of script-sharing packs (Week-3 task 5)

**Status: 20 Nov.** The Sanskrit reader check is done (9 rows, two readers; both flags confirmed, section 3.3).
**Pending:** the Marathi (4), Hindi (4) and Bengali (3) rows of `lang_label_review_sample.csv`, with their readers.

Task (Week-3 work order, task 5): "Check the language labels of script-sharing pairs (Hindi and Marathi, for example).
Flag each filter that drops over 20%." Owner: @keshavamurali. Scope as agreed with the lead (16 Nov): labels that are
wrong within one script, which D1 (script share) cannot see. Main check Devanagari (Hindi, Marathi, Sanskrit), plus
Assamese in the Bengali packs.

Every number and label below comes from a rule in the code (settings in `lang_label_config.json`) or from people: the
week-1 readers' `labels.csv`, the gold sets, the lead's shard audit, and the readers' check in section 3.3. So the check
re-runs unchanged on the full corpus.

## In short

- **No disagreement detected; this does not prove the labels are right.** 205,244 documents agree with their pack's
  language: 99.36% of the 206,571 judged documents, 97.77% of all 209,926. Not judged: 3,138 `short` and 217
  `other_script`. The marker words are consulted only when IndicLID disagrees with the pack, so a language that IndicLID
  absorbs into Hindi or Bengali cannot be flagged. The check catches 0 of the 6 same-script documents readers marked D1,
  and in `ind-sa-fw2` the 6 rows where IndicLID says Sanskrit but the marker words say Hindi (4) or Marathi (2) all
  come out `agree`. Of the judged documents that do not agree: 1,211 are `short_disagree` (too short to trust
  IndicLID, so unresolved), 114 uncertain, 2 flagged.
  The 2 flagged are marked as another language, both in `ind-bn-sangraha-v`, where the marker words name Sanskrit in Bengali
  script; a Sanskrit reader confirms both (section 3.3). 114 are uncertain; no pack has more than 0.3% uncertain. Of 7
  uncertain ones where IndicLID said Sanskrit, both Sanskrit readers find none Sanskrit alone (mixed pages or Hindi).
- **No filter drops over 20%.** clean.py does not record which filter dropped a document, so the lead's shard audit
  (#523, `audit_v1.csv`) gives drop rates per pack. The highest is 9.82% (`ind-hi-sangraha-s`), so no single filter in
  any pack can be over 20%. Four packs have no shard (ml, or, ta-fw2, ta-sangraha-s); they were not cleaned, so their
  "drops" are not drops.
- **The check catches none of the 6 same-script documents readers marked D1** (rule in section 3.1). The lead's summary
  of why (17 Nov): IndicLID has no Kumaoni class and reads Vedic Sanskrit as Hindi. A finding about the tool, not
  something to tune away.
- **It flags none** of the 1,590 gold documents or the 4,987 reader-labelled documents without D1.

## 1. Data

| Set | What | Used for |
|---|---|---|
| CAP-1 packs | The tokenizer-sample parts (Part_1 and Heldout) of the 10 packs: 209,926 documents. The same files as the p1536 shards' raw input: all 44 Indic parts match the hashes in `teams/01-data-a/jobs/2026-11-02-tokenizer-sample-v0-clean/tokenizer_sample_v0_manifest.json`, and #523 found every shard document in its raw part | the large run |
| Reader labels | `diagnosis/submissions/<pack>/*/labels.csv` of the 10 packs, on the 500-document diagnosis packs: 12,050 reader rows, 5,000 documents, 13 marked D1 | recall (D1 rows) and false flags (all other rows) |
| Gold | `gold/<pack>_gold.csv`: 1,590 documents, clean by definition | false flags |

Packs: `ind-hi-fw2`, `ind-hi-hplt`, `ind-hi-indiccorp`, `ind-hi-sangraha-s`, `ind-hi-sangraha-v`, `ind-mr-fw2`,
`ind-mr-sangraha-v`, `ind-sa-fw2`, `ind-bn-fw2`, `ind-bn-sangraha-v`.

## 2. Method

Each document gets two signals that do not depend on each other (`lang_id.py`):

1. **IndicLID-FTN**, AI4Bharat's fastText model for native-script text. Each paragraph is labelled on its own, with
   other scripts taken out, and the paragraphs vote, weighted by their letters. The model's own score is about 1.0 for
   almost every input, so the vote share is used as the confidence instead.
2. **Marker words**: frequent words of one language of the script and not of the others, for example आहे, आणि and मध्ये
   for Marathi against है, और and में for Hindi. The lists are in `lang_label_config.json`.

| Verdict | When |
|---|---|
| `short` | under 20 letters of the pack's script (as in D1): not judged |
| `other_script` | under half the letters in the pack's script: D1's case, not this check's |
| `agree` | IndicLID says the pack's language |
| `mislabelled` | IndicLID says another language with a vote share of 0.6 or more, **and** the marker words say the same language (both signals, as agreed with the lead) |
| `uncertain` | IndicLID disagrees, but the vote is split or the marker words do not confirm it |
| `short_disagree` | an `uncertain` document under 100 letters: too short to trust IndicLID |

Every document also gets `sign_letters`: counts of the letters that tell languages of one script apart (Assamese ৰ ৱ
against Bengali র, Marathi ळ, the avagraha ऽ ঽ, Vedic accents). They are evidence for readers, not part of the verdict.

IndicLID labels plain Hindi as Maithili (`mai_Deva`), so Maithili counts as Hindi; Hindi against its close dialects is
out of scope (lead, 16 Nov).

**v1 and v2.** v1 was fixed before any data was scored. Running it on the CAP-1 packs and debugging the code on its
flags showed four faults in the logic, fixed in v2 (17 Nov). No threshold was tuned on the labelled set; the vote share
(0.6) and the marker limits (3 hits, 2 times the next language) are v1's. The readers' check (section 3.3) confirms or
rejects these fixes.

| v1 fault | Effect on v1's results | v2 |
|---|---|---|
| Sanskrit endings (ः, म्) as markers | 3 documents in Hindi packs flagged as Sanskrit, with markers from those endings | endings removed; only Sanskrit words count |
| Repeated lines outvote the prose | repeated table lines decided the vote | a repeated paragraph counts once |
| IndicLID gives Bodo, Kashmiri or Dogri labels in Hindi packs | 1,278 uncertain in `ind-hi-indiccorp`, median 37 letters | such a label is no evidence on its own: the marker words decide; and a short disagreement is `short_disagree` |
| Sanskrit in Bengali script has no IndicLID class; its marker hits were split with Assamese, which also writes ৰ | the marker vote returned unknown | Sanskrit in Bengali script is a language of the check, and is compared together with Assamese as one marker group |

## 3. Results

### 3.1 What readers labelled (diagnosis packs)

| | Documents | Flagged `mislabelled` | `uncertain` |
|---|---|---|---|
| Gold | 1,590 | 0 | 0 |
| Reader-labelled, not D1 | 4,987 | 0 | 0 |
| Marked D1 by a reader | 13 | 0 | 0 |
| of which same-script (rule below) | 6 | 0 | 0 |

**Same-script rule:** a D1 document counts as same-script when at least 90% of its letters are in the pack's script
(`same_script_min_share`), so the readers' "wrong language" cannot be another script. The other 7 have 43% to 90% of
their letters in the pack's script, the mixed-script pages that D1 itself is for.

| Pack | Document | Readers who marked D1 | Pack's script | This check | IndicLID | Vote share | Marker words | Sign letters |
|---|---|---|---|---|---|---|---|---|
| ind-hi-hplt | ea08837da929d92e | 4 | 100% | agree | hin_Deva | 1.00 | hi | |
| ind-hi-sangraha-v | 086a0ded5e57ab37 | 1 | 100% | agree | hin_Deva | 0.62 | hi | mr ळ 1; sa ऽ 1 |
| ind-hi-sangraha-v | 4456ad657bbe6741 | 1 | 100% | agree | hin_Deva | 0.68 | hi | Vedic accents 18 |
| ind-hi-sangraha-v | e9d916f88e246a48 | 1 | 100% | agree | hin_Deva | 0.76 | hi | |
| ind-sa-fw2 | 7625ac472b005f22 | 1 | 95% | agree | san_Deva | 0.79 | unknown | |
| ind-bn-sangraha-v | 7160f28b914f8629 | 1 | 100% | agree | ben_Beng | 0.97 | unknown | as ৰ 2; bn র 53 |

The language each reader saw is in their notes, in `diagnosis/submissions/<pack>/<reader>/labels.csv`. The rule only
says the document is in the pack's script; it does not say a reader named another language for it, so some of the 6
may be marked D1 for another reason. With so few positives, recall cannot be measured. As the lead asked, the readers
check about 20 flags from the large run instead (section 3.3).

### 3.2 CAP-1 packs (the inputs of the p1536 shards)

| Pack | Docs | Judged | Agree | Mislabelled | Uncertain | Short, disagree | What IndicLID says on uncertain |
|---|---|---|---|---|---|---|---|
| ind-hi-fw2 | 14,393 | 14,313 | 99.99% | 0 | 1 | 0 | sa 1 |
| ind-hi-hplt | 8,840 | 8,821 | 100.00% | 0 | 0 | 0 | |
| ind-hi-indiccorp | 111,930 | 109,038 | 98.99% | 0 | 30 | 1,066 | ne 11, brx 11, mr 3, kas 3, sa 2 |
| ind-hi-sangraha-s | 8,368 | 8,113 | 97.93% | 0 | 23 | 145 | sa 16, ne 3, kas 3, brx 1 |
| ind-hi-sangraha-v | 14,831 | 14,808 | 99.72% | 0 | 41 | 0 | sa 39, doi 1, ne 1 |
| ind-mr-fw2 | 11,555 | 11,542 | 99.98% | 0 | 2 | 0 | hi 1, kok 1 |
| ind-mr-sangraha-v | 12,299 | 12,291 | 99.89% | 0 | 13 | 0 | hi 10, kok 2, sa 1 |
| ind-sa-fw2 | 5,963 | 5,945 | 100.00% | 0 | 0 | 0 | |
| ind-bn-fw2 | 11,317 | 11,279 | 100.00% | 0 | 0 | 0 | |
| ind-bn-sangraha-v | 10,430 | 10,421 | 99.94% | 2 (Sanskrit, Bengali script) | 4 | 0 | as 4 |
| **All** | **209,926** | **206,571** | **99.36%** | **2** | **114** | **1,211** | |

Not judged: 3,138 `short` (2,881 of them in `ind-hi-indiccorp`) and 217 `other_script`. Full tables:
`lang_label_tables.md`. Flagged IDs: `lang_label_mislabelled_ids.csv`.

The largest uncertain groups are "IndicLID: Sanskrit" in the Hindi packs (58) and "IndicLID: Hindi" in the Marathi packs
(11). In 43 of the 58, the marker words say Hindi; in the rest they are too few to decide. In the Marathi packs the marker
words mostly say Marathi. So the two signals disagree, and which one is right is for the readers (section 3.3).

### 3.3 Reader check

`lang_label_review_sample.csv` lists 20 documents, picked by the `sample` step with a fixed seed: both `mislabelled`
ones, then `uncertain` ones spread over the packs. The `reader` column says who reads each one (by rule: Sanskrit when
Sanskrit is the pack's or the found language, otherwise the pack's language): 9 Sanskrit, 4 Marathi, 4 Hindi, 3 Bengali.
Readers fill `reader_says_lang` and `reader_note`. This section is updated as they come back.

**Sanskrit rows (20 Nov), two readers.** Reader 1 is @keshavamurali, who wrote this tool, reading from a sheet that
showed only the doc ID and text (no pack, no verdicts). Reader 2 is @riteshverma, who read the documents and checked each
answer against the text. Answers are copied word for word into
`lang_label_review_sample.csv` (`reader_*` and `reader2_*` columns).

| doc_id | pack | tool verdict | tool found | markers | reader 1 | reader 1 note | reader 2 | reader 2 note |
|---|---|---|---|---|---|---|---|---|
| `142fb046694e60a8` | ind-bn-sangraha-v | mislabelled | sa_Beng | sa_Beng | not read | reader does not read Bengali script | sa | Sanskrit in Bengali script: Varaha Purana ch. 7-8 verses, OCR noise, no Bengali prose |
| `f16cdf5da3420ff9` | ind-bn-sangraha-v | mislabelled | sa_Beng | sa_Beng | not read | reader does not read Bengali script | sa | Sanskrit in Bengali script: Sanskrit dictionary entries (Shabdakalpadruma style), a few vernacular glosses, OCR noise |
| `1b10d275569b1b07` | ind-hi-fw2 | uncertain | sa | hi | mixed | Sanskrit with Hindi translation | mixed | sa+hi: news article, each paragraph in Sanskrit then its Hindi original, about half each |
| `5d72213f39cd2ebf` | ind-hi-sangraha-s | uncertain | sa | unknown | hi | mostly meaningless. Just group of words. | hi | broken machine-translated Hindi dictionary etymology, no Sanskrit, very short |
| `bacb55d31f5b0653` | ind-hi-sangraha-v | uncertain | sa | hi | mixed | Mix of Sanskrit, Prakrit and Hindi | mixed | hi+sa+Prakrit: Hindi commentary on Jain karma theory with Sanskrit and Prakrit quotations |
| `13b7aafd962fdc0d` | ind-hi-sangraha-v | uncertain | sa | hi | mixed | Hindi, Sanskrit and Prakrit | mixed | sa+hi+Prakrit: Prakrit gathas with Sanskrit chhaya and commentary, then Hindi translation |
| `9f2118ef7416b3b3` | ind-hi-sangraha-s | uncertain | sa | unknown | hi | Hindi | hi | machine-translated Hindi title of a US court case, no Sanskrit, very short |
| `012f90897ae4728a` | ind-hi-sangraha-v | uncertain | sa | hi | mixed | Hindi with Apabhramsha bhasha | mixed | hi+Apabhramsha+sa: Hindi prose on poet Pushpadanta, long Apabhramsha footnotes, a few Sanskrit lines |
| `cce99d56f83fa14d` | ind-mr-sangraha-v | uncertain | sa | mr | mixed | Mix of Sanskrit, Prakrit or Apabhamsha and Hindi | mr | Marathi notes on Sanskrit metres, many Sanskrit metre names and quoted sutras |

- **The 2 flags:** reader 2 reads both as Sanskrit in Bengali script, as the tool found (`sa_Beng`). Reader 1 does not
  read Bengali script. So both flags are confirmed by one reader.
- **The 7 uncertain documents:** both readers read all 7 and agree on 6. They differ on `cce99d56f83fa14d`
  (reader 1 `mixed`, reader 2 `mr`). Neither reader calls any of the 7 Sanskrit alone, though IndicLID's vote said
  Sanskrit for all 7; the tool flagged none of them, because the marker words did not agree.
- Reader 2's notes: the IndicLID-Sanskrit documents in the Hindi packs are mostly mixed pages or broken
  machine-translated Hindi, not Sanskrit labelled as Hindi. Two (`5d72213f39cd2ebf`, `9f2118ef7416b3b3`) are short
  garbled Hindi that IndicLID called Sanskrit with a full vote. Requiring the marker words to agree kept them out of
  the flags.
- Both readers name Prakrit or Apabhramsha in Jain texts, which IndicLID has no class for (section 5).
- **Pending:** the Marathi (4), Hindi (4) and Bengali (3) rows of `lang_label_review_sample.csv`, with their readers.

## 4. Filters that drop over 20%

From the lead's shard audit (#523, `audit_v1.csv`; `docs_raw` is the Part_1 part only):

| Pack | Raw | Dropped | Drop rate |
|---|---|---|---|
| ind-hi-sangraha-s | 8,280 | 813 | 9.82% (highest) |
| ind-te-sangraha-s | 4,782 | 363 | 7.59% |
| ind-te-fw2 | 5,997 | 327 | 5.45% |
| ind-bn-fw2 | 11,205 | 501 | 4.47% |
| ind-hi-hplt | 8,745 | 359 | 4.11% |
| ind-sa-fw2 | 5,908 | 241 | 4.08% |
| the other 12 cleaned packs | | | 3.42% or less |
| ind-ml-fw2, ind-or-fw2, ind-ta-fw2, ind-ta-sangraha-s | | | no shard: not cleaned |

**0 of 18 cleaned packs drop over 20%**, so no filter does. A filter's drops in a pack are at most the pack's drops. This
holds for every Indic pack, not only the script-sharing ones. All rows: `lang_label_filter_flags.csv`.

The step also reads a per-filter table (`pack, filter, docs_in, docs_dropped`) and, given the dropped doc IDs, counts
how many dropped documents this check found mislabelled. That stays unused until clean.py records the filter of each
drop.

## 5. Limits

- **IndicLID's label list** has no class for Kumaoni or other Pahari languages, nor for Sanskrit outside Devanagari, nor for
  Prakrit or Apabhramsha (found by both Sanskrit readers in Jain texts, section 3.3).
  Hindi against its dialects (Maithili, Bhojpuri, Awadhi, Kumaoni) cannot be checked with it.
- **Short documents:** IndicLID is unreliable under about 100 letters. These are `short_disagree`, not flags.
- **Mixed documents** get one label per document; paragraph votes make them `uncertain`, not split.
- **Packs outside the 10 are not checked.** The Telugu reader in #618 (`rotation_varshith2000.md`) found Hindi
  (Devanagari) runs in `85c371eab86e00d1`, labelled `te`, in shard `ind-te-sangraha-v-train-000000`: five D3 rows,
  which the reader puts at about 15% of the document. This is mixing across scripts, not a script-sharing pair, so
  it is outside this check and the tool has not judged it. It shows that mixed-language documents reach the shards
  with a single label; a cross-script check per paragraph would be the follow-up.
- **The marker lists are ours**, written for this check and not yet validated by readers of each language. The Sanskrit
  list has whole words only since v2, so inflected Sanskrit has few of them. Lists of frequent forms from the Marathi
  and Sanskrit readers would make the marker signal theirs.
- **The same-script rule** (90% in the pack's script) counts documents a reader may have marked D1 for another reason.
  A D1 sub-code for "same script, other language" in the readers' labels would replace it.
- **Few positives:** 6 same-script documents by the rule. Recall is unknown.
  **Pending:** the Marathi, Hindi and Bengali reader rows (section 3.3).
- The CAP-1 run includes the Heldout parts (about 1% of each pack); the shard audit's counts are Part_1 only.

## 6. How to run it

From `teams/02-data-b/audit`, with the IndicLID environment of `../romanised` (see its README, Part 2):

```bash
PY=../romanised/.venv-lid/bin/python
$PY -m unittest test_lang_label_check                       # 23 tests, made-up text, no model needed
$PY lang_label_check.py evaluate                            # reader labels and gold
$PY lang_label_check.py run --cap1-dir <Cap1-packs folder> --work-dir <scratch folder>   # about 11 minutes
$PY lang_label_check.py flag                                # audit_v1.csv, drop_threshold 0.20
$PY lang_label_check.py sample --work-dir <scratch folder>
$PY lang_label_check.py report
```

All settings, including `drop_threshold` and `same_script_min_share`, are in `lang_label_config.json`. Only counts,
labels and doc IDs are committed, never document text. The per-document results of the run stay in the work folder.

## 7. Files

| File | What |
|---|---|
| `lang_id.py` | the check for one document: both signals, the verdict and the sign letters |
| `lang_label_check.py` | the steps: evaluate, run, flag, sample, report |
| `lang_label_config.json` | languages, IndicLID labels, marker words, sign letters, thresholds, paths; the v2 changes are listed in it |
| `test_lang_label_check.py` | unit tests |
| `lang_label_labelled.csv`, `lang_label_eval_summary.csv`, `lang_label_d1_docs.csv` | section 3.1; one row per reader row (the readers' labels kept), and one per D1 document |
| `lang_label_by_pack.csv`, `lang_label_mislabelled_ids.csv` | section 3.2 |
| `lang_label_review_sample.csv` | section 3.3, for the readers |
| `lang_label_filter_flags.csv` | section 4 |
| `lang_label_tables.md` | all tables, generated |
