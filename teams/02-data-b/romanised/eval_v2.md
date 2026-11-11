# Romanised Indic: word list vs IndicLID (v2)

Both tools are segment classifiers inside `doc_detector.py`: the document is cut into lines and sentences, each tool says which segments are romanised Indic, and the document is romanised when those segments hold more than 50% of its words (TSAI's rule for the cap).

Test set: `testset_100.csv`, 100 documents, 52 marked D2 by a reader. Ground truth: the readers' labels; the checked labels (`checked_labels.csv`, 19 reader D2 marks changed to 0) are shown next to them.

## Contains romanised Indic (at least one romanised segment)

| tool | labels | D2 docs | flagged | true pos | false pos | missed | precision | recall |
|---|---|---|---|---|---|---|---|---|
| word list | readers | 52 | 25 | 25 | 0 | 27 | 100% | 48% |
| word list | checked | 33 | 25 | 23 | 2 | 10 | 92% | 70% |
| IndicLID | readers | 52 | 38 | 29 | 9 | 23 | 76% | 56% |
| IndicLID | checked | 33 | 38 | 22 | 16 | 11 | 58% | 67% |

## Mostly romanised (> 50% of the words)

| tool | flagged in the test set | of them reader D2 | flagged in all 22 packs (11,000 docs) | highest share in any pack document |
|---|---|---|---|---|
| word list | 0 | 0 | 0 | 35% (ind-hi-indiccorp 62707cd1ddf37b45) |
| IndicLID | 0 | 0 | 1 | 57% (ind-hi-sangraha-s 59aef801fa585bdf) |

Precision and recall are not given at this level: readers marked D2 for any romanised text, so there is no labelled set of mostly-romanised documents to measure them on.

## Gold check (false positives)

All gold documents in `teams/02-data-b/gold/` (1957 in 17 packs). Two readers marked each one clean, so none is D2 and every flag is a false positive.

| tool | flagged: contains | flagged: mostly romanised | documents flagged (contains) |
|---|---|---|---|
| word list | 0 | 0 | - |
| IndicLID | 9 | 0 | 2d9606c73b989183 (ind-hi-fw2), 82737e2262167179 (ind-hi-fw2), 8f95854f321445b1 (ind-hi-fw2), c3b2ba56f7685d9e (ind-hi-fw2), c3e69a187cd9bbce (ind-hi-fw2), ca0e066feec280a2 (ind-hi-fw2), ce6c4bba45654960 (ind-hi-fw2), 357aacb515b397a3 (ind-hi-hplt), ac416a912cfbe059 (ind-te-sangraha-s) |

## Choice

**word list**: it flags fewer gold documents.

## Test documents where the tools disagree (contains level): 19

| doc_id | pack | reader D2 | checked | word list | IndicLID | share (word list / IndicLID) |
|---|---|---|---|---|---|---|
| 7bbe5a23532255c3 | ind-bn-fw2 | 0 | 0 | 0 | 1 | 0% / 1% |
| b00ce35d528bdbcd | ind-bn-sangraha-v | 1 | 1 | 1 | 0 | 2% / 0% |
| 3776d34f591f896d | ind-hi-fw2 | 1 | 0 | 0 | 1 | 0% / 0% |
| 7232af0838e21720 | ind-hi-fw2 | 0 | 0 | 0 | 1 | 0% / 1% |
| ee19639bfb2e22a0 | ind-hi-fw2 | 1 | 0 | 0 | 1 | 0% / 0% |
| 7143c8411c407518 | ind-hi-hplt | 1 | 0 | 0 | 1 | 0% / 0% |
| a1650c45f06533a1 | ind-hi-hplt | 0 | 0 | 0 | 1 | 0% / 1% |
| ef3ed1ee60b1d6fd | ind-hi-hplt | 1 | 0 | 0 | 1 | 0% / 0% |
| 62707cd1ddf37b45 | ind-hi-indiccorp | 1 | 1 | 1 | 0 | 35% / 0% |
| 7a354dffcf84e4d4 | ind-hi-indiccorp | 1 | 1 | 1 | 0 | 3% / 0% |
| 77d13d9d62f7ba0b | ind-kn-sangraha-v | 0 | 0 | 0 | 1 | 0% / 1% |
| d9ec06a95ff824e8 | ind-kn-sangraha-v | 0 | 0 | 0 | 1 | 0% / 1% |
| 6ef515eea2d7307f | ind-ml-fw2 | 0 | 0 | 0 | 1 | 0% / 1% |
| a490e482b40744a8 | ind-or-fw2 | 0 | 0 | 0 | 1 | 0% / 1% |
| 2fae9450902b5eeb | ind-sa-fw2 | 0 | 0 | 0 | 1 | 0% / 1% |
| 6a58a10566aca6d8 | ind-sa-fw2 | 1 | 0 | 0 | 1 | 0% / 1% |
| 7bc67301a58f3aec | ind-sa-fw2 | 1 | 1 | 0 | 1 | 0% / 6% |
| b54a137e794fc027 | ind-ta-sangraha-v | 1 | 1 | 0 | 1 | 0% / 4% |
| f4decbed68c9f633 | ind-te-fw2 | 0 | 0 | 0 | 1 | 0% / 1% |
