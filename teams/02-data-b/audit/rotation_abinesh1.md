# Data B rotation, week 3: R1 and R2 on ind-ta-sangraha-v (abinesh1)

Closes #619. Rotation member: abinesh1. Language: Tamil (I read Tamil; I did the week-1 diagnosis of this pack).

## What was checked

| Item | Value |
|---|---|
| Shard | `ind-ta-sangraha-v-train-000000` (TSAI's list in G, 16 Nov) |
| Payload sha256 | `418b46986e796f806d520b883091af93be976a068554b81026f7096417b455d7` (matches the manifest) |
| Index / docs sha256 | `392a803c…1862d` / `97bccf7e…82645` (match the manifest) |
| Tokenizer | frozen p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`, tokenizers 0.23.3 |
| Documents in shard | 6,795 (header, index and EOS 130822 checks pass, `read_shard` of `indic_audit.py`) |
| Sample | DAY 4: `random.Random(4).sample(range(6795), 50)`, the sampler in #619 |
| Checks | G1, G2, A1, A4, A6 by code point (definitions in #619), plus CO (`:` inside a Tamil word, the #576 swap), VV (two vowel signs in a row) and AY (aytham ஃ not followed by a consonant) |
| Raw text | sample v0 part `ind-ta-sangraha-v_part-00000.parquet`, sha256 `3774dd4f…1724b` (matches `raw_parts_SHA256SUMS`) |
| Wall time | 1.8 s for decode + all checks (one process, batched decode, regex per document) |

All 50 documents were read in full, for damage that code points can't show (a word split in two, text cut or missing, wrong letters). Each sampled document's raw text was also passed through the p1536 normalizer and diffed against its shard text, so every change cleaning made is known (next section). Document text is not reproduced here: only IDs, codes, offsets and code points.

## What cleaning changed in the 50 documents

| Change | Edits | Documents | Verdict |
|---|---|---|---|
| none: shard text = raw text after the normalizer | | 42 | |
| literal `\n` (U+005C U+006E) turned into a newline | 24 | 2 | fix (B4) |
| space after `.` removed in a split decimal, time or URL (`1. 03` → `1.03`) | 23 | 5 | fix (G4, as labelled in week 1) |
| English newsletter line removed at the end | 1 (61 chars) | 1 | fix (C1) |

No edit touches a Tamil letter, vowel sign, pulli or aytham. So no word was split and no sentence was cut by `clean.py` or p1536 in this sample. All the damage below is in the raw text too.

## R1: results on 50 documents

| Code | Findings | Documents |
|---|---|---|
| G1 vowel sign or pulli after a space, punctuation, digit or Latin letter | 0 | 0 |
| G2 ZWJ/ZWNJ at word edge or doubled | 0 | 0 |
| A1 invisible characters | 0 | 0 |
| A4 U+FFFD | 0 | 0 |
| A6 Latin or other script inside a Tamil word, or a look-alike letter | 5 (+4 by reading) | 5 |
| CO `:` inside a Tamil word (#576 aytham swap) | 0 | 0 |
| VV two vowel signs in a row (extra) | 4 | 2 |
| AY aytham ஃ where a colon belongs (extra) | 58 (+1 by reading) | 18 |
| SP word split in two by a space (extra, by reading) | one example per document | 10 |
| G3 text missing at the start or inside the document (by reading) | 5 | 5 |
| C3 text stops mid-sentence (by reading) | 3 | 3 |

- ZWJ (U+200D) and ZWNJ (U+200C): 0 of each in the 50 documents and 0 in the whole shard, as in the raw pack (#523: 0 before, 0 after). Tamil text rarely uses them, so nothing can be lost here.
- NFC: all 50 documents are already NFC.
- Aytham: 7,369 in the shard and 7,369 in the raw pack (#576). The aytham is not turned into `:` in the shard (CO = 0).

## R2: findings with doc ID and hex dump

Offsets are in code points of the decoded document. The hex dump is the finding (in bold) plus three code points on each side. An AY row lists every offset in the document; the dump is for the first one, and at every other offset the aytham is followed by the same kind of character (space, newline or vowel letter). An SP row gives one example; the note says how common the splits are in that document.

| doc_id | code | offset | hex dump | note |
|---|---|---|---|---|
| b2270d1d6afd5af8 | A6 | 3 | U+002D U+0020 U+0023 **U+0056 U+0065 U+006C U+006C U+006F U+0072 U+0065** U+0BB5 U+0BC7 U+0BB2 | Latin hashtag glued to the next Tamil word: space or newline lost in the source |
| b2270d1d6afd5af8 | A6 | 114 | U+002D U+0020 U+0023 **U+0056 U+0065 U+006C U+006C U+006F U+0072 U+0065** U+0B9A U+0BC6 U+0BB2 | same hashtag, same lost space |
| d12b085d3fddc8fb | A6 | 101 | U+002D U+0020 U+0023 **U+0043 U+0068 U+0065 U+006E U+006E U+0061 U+0069** U+0B85 U+0BA4 U+0BC8 | same pattern, another hashtag |
| d12b085d3fddc8fb | A6 | 211 | U+002D U+0020 U+0023 **U+0043 U+0068 U+0065 U+006E U+006E U+0061 U+0069** U+0BA8 U+0BBE U+0BB3 | same |
| 7e58e72b1d38865f | A6 | 2992 | U+002E U+000A U+0B99 **U+004F** U+002E U+0020 U+0B8E | verse number read wrong by OCR: ங + Latin O, probably the Tamil numeral 30 (௩௰); the next verses are numbered ஙக and ங.உ |
| 0b98990b1828e004 | A6 | 3629 | U+0033 U+002E U+0036 **U+0BB1 U+0BC2 U+0B9A** U+0020 U+0BAA U+0BC7 | by reading: three Tamil letters where the battery unit (Wh) belongs; a font converter ran over Latin text. Same document has 8 AY |
| 7e58e72b1d38865f | A6 | 2044 | U+0BC7 U+0020 U+0BA4 **U+0BBE** U+0BAA U+0BCD U+0BAA | by reading: AA sign where ர (U+0BB0) belongs; in old Tamil type the two look alike and the OCR mixed them up. One of many in this document |
| 7e58e72b1d38865f | A6 | 7140 | U+002E U+0020 U+0028 **U+0061 U+006D U+0061 U+006E** U+0029 U+000A U+0B95 | by reading: Latin junk in brackets where a verse number belongs (OCR) |
| 38b1a7ad5013e705 | A6 | 983 | U+0BCD U+0020 U+0BAA **U+0BC6 U+0BB3** U+0BB5 U+0BAE U+0BC1 | by reading: E sign + letter LLA (ள) typed for the AU sign (U+0BCC); renders almost the same, different ids |
| 52073e78c93ab43a | VV | 275 | U+0020 U+0BB2 U+0BC1 **U+0BBE** U+0BB0 U+0BCD U+0BA4 | U sign + AA sign typed for UU sign (U+0BC2); legacy-font spelling (the week-1 G1 pattern of this pack). Renders close, different ids |
| 52073e78c93ab43a | VV | 616 | U+0020 U+0BA8 U+0BC1 **U+0BBE** U+0BB1 U+0BC1 U+0020 | same |
| 7e58e72b1d38865f | VV | 1999 | U+0BCD U+0BB3 U+0BC1 **U+0BBE** U+0BB5 U+0BA9 U+0BBE | OCR: a stray AA sign inside a name that the verse above spells without it |
| 7e58e72b1d38865f | VV | 2008 | U+0020 U+0B9A U+0BC1 **U+0BBE** U+0BA8 U+0BCD U+0BA4 | OCR: ர read as AA sign (as at 2044); the verse above spells this word with ர |
| 0b98990b1828e004 | AY | 2126, 2343, 2515, 2865, 3046, 3250, 3455, 3589 | U+0BCD U+0B9F U+0BBE **U+0B83** U+000A U+0BAA U+0BBF | aytham at the end of a heading, before a newline: a colon lost in the source (week-1 A6 of this pack) |
| 0d741151121a0b2f | AY | 1154, 1543, 1905, 2151, 2493, 3237, 3732, 4218, 4891, 5351 | U+0BBF U+0BB2 U+0BC8 **U+0B83** U+000A U+0BA4 U+0BBE | same, a repeated heading |
| 4b563fbbbd8c572e | AY | 355, 596, 805, 1070, 1226, 1433, 1657, 1872, 2203, 2617, 2752, 3010, 3257, 3614, 4025, 4127, 4330, 4481 | U+0BBF U+0B9F U+0BC8 **U+0B83** U+0020 U+0BA4 U+0BC2 | aytham before a space after a label word |
| d12b085d3fddc8fb | AY | 433, 1613, 1927, 2136, 2832, 3251 | U+0BCD U+0BA9 U+0BC8 **U+0B83** U+0020 U+0B85 U+0BAE | same, after times of day. The same document writes 4 other times with a real colon |
| a39d95d5e12c8f5c | AY | 507, 1919, 2262 | U+0BC1 U+0BA4 U+0BBF **U+0B83** U+000A U+0B95 U+0BBF | heading before a newline |
| 4d1e37b425720145 | AY | 6, 399 | U+0BCD U+0BA9 U+0BC8 **U+0B83** U+0020 U+0027 U+0BAA | label before a quote |
| 38a18628cbe54ff7 | AY | 1817 | U+0BAA U+0BB2 U+0BBF **U+0B83** U+0020 U+0033 U+0020 | headline, before a number |
| 53328137ecdcfcb8 | AY | 2775 | U+0BB0 U+0BAE U+0BCD **U+0B83** U+0020 U+0BAE U+0BC1 | headline |
| 5e1e7b92305917b1 | AY | 10 | U+0BCD U+0BB2 U+0BBF **U+0B83** U+0020 U+0B95 U+0BCA | place label at the start |
| 6d19ed6fbf0c1f4c | AY | 29 | U+0BBE U+0B9F U+0BC1 **U+0B83** U+0020 U+0041 U+004B | label before Latin text |
| 6f88ea9e3d7af29f | AY | 8 | U+0BBF U+0B99 U+0BCD **U+0B83** U+0020 U+0B95 U+0B9F | place label at the start |
| a4c40a0287d1e17a | AY | 8 | U+0B95 U+0BB0 U+0BCD **U+0B83** U+0020 U+0B9C U+0BAE | place label at the start |
| b2270d1d6afd5af8 | AY | 229 | U+0BCD U+0BA9 U+0BC8 **U+0B83** U+0020 U+0B95 U+0BC1 | place label |
| c36588c4520094b0 | AY | 12 | U+0BC1 U+0B9F U+0BBF **U+0B83** U+0020 U+0BA4 U+0BC2 | place label at the start |
| ce898dcaac3e1df3 | AY | 15 | U+0BC6 U+0BAF U+0BBE **U+0B83** U+0020 U+0B9A U+0BBF | place label at the start |
| e7a05aa2ea1e588d | AY | 106 | U+0BAE U+0BB0 U+0BBF **U+0B83** U+000A U+0BA8 U+0BBE | place label before a newline |
| f2d8aad58bc40638 | AY | 44 | U+0BC1 U+0BAA U+0B9F **U+0B83** U+0B8E U+0BA8 U+0BCD | aytham before a vowel letter, no space: colon and space both lost |
| 52073e78c93ab43a | AY | 337 | U+0BB5 U+0BA4 U+0BC1 **U+0B83** U+0BAA U+0BC1 U+0BA4 | by reading: aytham for a colon, then no space before the next word. Code points can't catch it: ஃ before ப is also the valid loanword spelling (ஃபுட் in `0d741151121a0b2f`) |
| 0d0cb0705c2e18d0 | SP | 82 | U+0020 U+0B87 U+0BB2 **U+0020** U+0B99 U+0BCD U+0B95 | a place name split in two; 5 such splits in this document |
| 3e37eb0e5bffc070 | SP | 282 | U+0BC1 U+0B95 U+0BCD **U+0020** U+0B95 U+0BBE U+0B95 | line-wrap split from a printed book; 6 in this document |
| 4b563fbbbd8c572e | SP | 4075 | U+0BB5 U+0BB0 U+0BCD **U+0020** U+0B95 U+0BB3 U+0BBE | a word split before its case ending |
| 7e58e72b1d38865f | SP | 657 | U+0BCD U+0BB3 U+0BC1 **U+0020** U+0BB5 U+0BB0 U+0BCD | line-wrap split from a printed book; dozens in this document |
| 9de52b6bbcb3017b | SP | 160 | U+0BC6 U+0B95 U+0BCD **U+0020** U+0BB7 U+0BA9 U+0BCD | an English loanword split before its last syllable |
| a4c40a0287d1e17a | SP | 1091 | U+0BC1 U+0B95 U+0BCD **U+0020** U+0B95 U+0BBE U+0BA9 | a word split before its case ending |
| b61c5a5de775f5a0 | SP | 224 | U+0BCD U+0B9F U+0BBE **U+0020** U+0BB5 U+0BBF U+0BA9 | line-wrap split from a printed book; more than 15 in this document |
| cc42ebc20d8ba1c2 | SP | 2389 | U+0BC6 U+0BB2 U+0BCD **U+0020** U+0BB2 U+0BBE U+0BAE | line-wrap split; 4 in this document |
| 0d741151121a0b2f | SP | 2094 | U+0BC1 U+0BA8 U+0BCD **U+0020** U+0BA4 U+0BBE U+0BB2 | line-wrap split; 2 in this document |
| e7a05aa2ea1e588d | SP | 893 | U+0BCD U+0B9F U+0BBF **U+0020** U+0BB0 U+0BC1 U+0BA8 | line-wrap split; 3 in this document |
| 7e58e72b1d38865f | G3 | 0 | **U+0BB1 U+0BC1 U+0BAE U+0BCD** U+0020 U+0B95 U+0BC2 | by reading: the document starts in the middle of a word |
| cc42ebc20d8ba1c2 | G3 | 0 | **U+0BB0 U+0BC1 U+0BAE U+0BA3** U+0BAE U+0BCD U+002C | by reading: starts in the middle of a word; its first letter is missing |
| 3e37eb0e5bffc070 | G3 | 370 | U+0BAE U+0BCD U+000A **U+0BA9 U+0BCD** U+0BAA U+0BC1 U+0BB1 | by reading: the first letter of a word lost at a line break (a page or line join in a scanned book) |
| 4b563fbbbd8c572e | G3 | 351 | U+0BCD U+002E U+000A **U+0BB5 U+0BBF U+0B9F U+0BC8 U+0B83** U+0020 U+0BA4 U+0BC2 | by reading: a quiz with 18 "answer:" lines but only 1 question line; 17 questions were dropped by an earlier filter |
| 8c558dbaf0ec04e4 | G3 | 1742 | U+0BA4 U+0BC1 **U+002E U+0020 U+002C** U+0020 U+0B95 U+0BCB | by reading: a list fragment follows a full stop, so the text before it is missing |
| 3e37eb0e5bffc070 | C3 | 1538 | U+0BB5 U+0BA8 U+0BCD U+0BA4 U+0BC1 **U+000A** | by reading: stops mid-sentence (last word is a verb participle) |
| bc181046bab89ad8 | C3 | 647 | U+0020 U+0BAA U+0BCB U+0BA4 U+0BC1 **U+000A** | by reading: stops mid-sentence ("when ...") |
| 4d1e37b425720145 | C3 | 789 | U+0BCD U+0BB8 U+0BCD U+002E U+002E **U+000A** | by reading: teaser cut with `..` in the middle of a phrase; all 4 lines of this listing page are cut the same way |

## Other notes from reading (not script damage)

- **Boilerplate that cleaning missed (C1)**, in 11 documents: `7773931c7666046c` is nothing but a page shell (link list, a comment counter, a JavaScript warning); `dfed2fcfce1be27d` repeats an English image-copyright line 3 times plus 2 "Also Read" links; `2911d6acbdecf5fd` ends with the channel's TV-listing footer; `0b98990b1828e004` starts with 11 headline links; `b2270d1d6afd5af8` and `d12b085d3fddc8fb` start with hashtag headline links; `53328137ecdcfcb8`, `cd87aae490845c38` and `f7026d74d9cce0d9` start with a site-name title line; `38a18628cbe54ff7` and `ed58e2937370a44f` end with unrelated headlines.
- **Machine translation**: `6d19ed6fbf0c1f4c` and `8c558dbaf0ec04e4` read as machine-translated Turkish news; in `6d19ed6fbf0c1f4c` the numbers have moved to the wrong nouns.
- **Two articles in one document**: `0d0cb0705c2e18d0` joins an unrelated news item and a literary-festival report.
- **OCR of an old book**: `7e58e72b1d38865f` (a verse commentary) has the most damage in the sample: ர/ா mix-ups, numerals and brackets misread, many line-wrap splits, and it starts mid-word. The rows above give examples, not every case.
- `f2d8aad58bc40638` has no space after `.` and `,`, and two words written as one at offset 485 (U+0BA4 U+0BC1 | U+0BA8 U+0BC0). The raw text is the same.
- The whole shard has 41 U+FFFD, all already in the raw pack (41). None is in this sample.

## Summary

Documents checked: 50 (DAY 4), all read in full. Code-point findings: G1 0, G2 0, A1 0, A4 0, A6 5, CO 0 (plus VV 4, AY 58). By reading: A6 4, AY 1, SP in 10 documents, G3 5, C3 3. Documents with a finding: 27 of 50. 0 ZWJ/ZWNJ in the sample or the shard, so none can be lost; 0 replacement characters, 0 invisible characters, all NFC. **Cleaning and p1536 caused none of the damage**: 42 documents are unchanged, and the 8 changed ones only got fixes (B4, G4, C1).

The main script damage in this pack is AY: the aytham ஃ written where a colon belongs, from a legacy font converter. `d12b085d3fddc8fb` shows it best: it writes some times of day with ஃ and others with a real colon. In the whole shard 4,754 of the 7,369 aytham are not followed by a consonant, in 1,922 documents. In the sample, all 58 come right after a word and before a space, a newline or a vowel letter, where a colon belongs. A real aytham is always followed by a consonant. #576 counted 4,540 words in v0-clean where the aytham became `:` and treated that as damage. Given this sample, most of those were probably repairs of AY, not damage. A Tamil reader should check some of them before the swap is called damage at Gate 3.

Suggested later rules (not applied, each after a gold-set harm test): ஃ followed by a space, a newline or a vowel letter → `:` (the week-1 A6 medicine for this pack; it must leave ஃ before a consonant alone, so it misses the `52073e78c93ab43a` case); U+0BC1 U+0BBE → U+0BC2 for VV in the legacy-font documents (not in OCR text like `7e58e72b1d38865f`, where the same pair means something else).

## Command

```
python -I r1_rotation.py ind-ta-sangraha-v-train-000000.bin p1536_tokenizer.json 4
{"G1": 0, "G2": 0, "A1": 0, "A4": 0, "A6": 5, "VV": 4, "CO": 0} nfc_bad 0 zwj 0 zwnj 0 wall 1.8
```

AY was counted with the regex `ஃ(?![க-ஹ])` over the 50 documents (58) and with pyarrow `count_substring_regex` over the whole shard (4,754). The raw-vs-shard check is `difflib.SequenceMatcher` per document, on the raw text after the p1536 normalizer.
