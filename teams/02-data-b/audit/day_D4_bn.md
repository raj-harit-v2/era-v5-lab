# Bengali reader audit, day D4

Refs #568. 25 documents drawn with `random.Random(4).sample(range(n), 25)` from each shard of the p1536 sample v0: `ind-bn-fw2-train-000000` (n = 10704) and `ind-bn-sangraha-v-train-000000` (n = 10112), decoded with the frozen tokenizer p1536 (sha256 `e6b93a93…`). Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text. `OCR` is not a DISEASES code: as in #733, it marks scanned-book text with misread letters. Each finding's note starts with `source` (also in the raw text) or `cleaning` (not in the raw text), from comparing each document with its raw part `tokenizer_sample_v0_raw/train/<pack>/part-00000.parquet` (ind-bn-fw2 sha256 `fda2605f…`, ind-bn-sangraha-v `84a59d86…`). The writer's own typos that cleaning did not touch are marked `ok` with a note, as @shankarpandala asked.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `dce0f53a3c0625ba` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: date and clock line before the article |
| `dce0f53a3c0625ba` | `ind-bn-fw2-train-000000` | finding | A6 | 572 | `source`: old-font residue in one word, a macron and a split vowel sign |
| `63d8b9a9d73ba5c3` | `ind-bn-fw2-train-000000` | finding | C1 | 1028 | `source`: tweet text and hashtag repeat the quote above; cleaning removed only the tweet's credit line |
| `4e027bc47c08fe94` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `588018acae54edd3` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: listing page of titles and teasers, no article |
| `c79b75fcbe68f548` | `ind-bn-fw2-train-000000` | finding | C1 | 42 | `source`: site name line between headline and body; cleaning removed the date line after it |
| `c79b75fcbe68f548` | `ind-bn-fw2-train-000000` | finding | C1 | 1662 | `source`: three article links left at the end; cleaning removed the longer link lists |
| `9a9793870bed6439` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `3ad013de2753df02` | `ind-bn-fw2-train-000000` | finding | A6 | 117 | `source`: Latin y in place of a vowel sign inside a word |
| `3ad013de2753df02` | `ind-bn-fw2-train-000000` | finding | C1 | 884 | `source`: editor credit line at the end; cleaning removed the time line after it |
| `62c3c6c96167d9ad` | `ind-bn-fw2-train-000000` | finding | C1 | 54 | `source`: section name, site name and time stamp between headline and body |
| `97920c500b2e217a` | `ind-bn-fw2-train-000000` | ok |  |  |  |
| `c9008b54b5e55930` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: correspondent label, time stamp and print-edition link before the article |
| `4db6c8eddf74ccb1` | `ind-bn-fw2-train-000000` | ok |  |  |  |
| `ffd41845f68e2d5c` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: menu word and date stamp before the article |
| `ffd41845f68e2d5c` | `ind-bn-fw2-train-000000` | finding | D3 | 715 | `source`: a full English quote paragraph left untranslated; its Bengali version follows |
| `13220cb822d3d2d8` | `ind-bn-fw2-train-000000` | finding | C1 | 1683 | `source`: source-credit line at the end |
| `c07e6557df7589e7` | `ind-bn-fw2-train-000000` | ok |  |  |  |
| `9157d11b82307cd1` | `ind-bn-fw2-train-000000` | finding | C1 | 1573 | `source`: agency sign-off with date and initials |
| `7d1e9855a877ab2e` | `ind-bn-fw2-train-000000` | finding | C1 | 3104 | `source`: reporter and editor initials at the end; cleaning removed the time line before them |
| `5bebd0658a2f7ca4` | `ind-bn-fw2-train-000000` | ok |  |  |  |
| `5a1e585cd3b2ec9a` | `ind-bn-fw2-train-000000` | finding | D3 | 1733 | `source`: about 10 Arabic tweets left untranslated; an Arabic hashtag at 449 too |
| `5a1e585cd3b2ec9a` | `ind-bn-fw2-train-000000` | finding | G3 | 3106 | `source`: two lines introduce a tweet that is not in the text |
| `68456223b0bed76d` | `ind-bn-fw2-train-000000` | finding | C1 | 78 | `source`: photo credit without its photo |
| `68456223b0bed76d` | `ind-bn-fw2-train-000000` | finding | C1 | 2273 | `source`: site name and initials at the end |
| `4caaaec30c853c0c` | `ind-bn-fw2-train-000000` | finding | G3 | 4112 | `source`: a sentence stops after two words, the closing note follows |
| `427e8f00c15c5ceb` | `ind-bn-fw2-train-000000` | finding | C1 | 84 | `source`: read-time label and update time joined to the headline; cleaning changed its Latin 1 to a Bengali digit |
| `f1c1a8403bbb071d` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: desk byline and place before the first sentence |
| `f1c1a8403bbb071d` | `ind-bn-fw2-train-000000` | finding | A6 | 199 | `source`: old-font residue, a low quote mark in place of a vowel sign |
| `f1c1a8403bbb071d` | `ind-bn-fw2-train-000000` | finding | C1 | 3713 | `source`: site name, date and initials at the end |
| `ed5c7783fe384cd9` | `ind-bn-fw2-train-000000` | ok |  |  |  |
| `b93f5ab46158e0ae` | `ind-bn-fw2-train-000000` | ok |  |  |  |
| `a3582a88294f7784` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: desk byline, repeated at the end |
| `a3582a88294f7784` | `ind-bn-fw2-train-000000` | finding | G2 | 1816 | `source`: RAB written without ZWJ, in the raw text too |
| `9a577da14279284a` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 1836 | `source`: site promotion line after the article |
| `41b152246fc99def` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 70 | `source`: old-font residue in 4 words, symbols or wrong letters in place of signs (also at 482, 2134, 3227) |
| `cf03e11e788caa34` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `db7dcf1e456211d4` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `1e9fdbe8d03744c7` | `ind-bn-sangraha-v-train-000000` | finding | G3 | 153 | `source`: words missing in a sentence, its verb is gone |
| `09192e190be3acf6` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `8fa858308323ff85` | `ind-bn-sangraha-v-train-000000` | finding | G4 | 68 | `source`: space after the decimal point in a number, in the raw text too |
| `d05f88d7e0e69dca` | `ind-bn-sangraha-v-train-000000` | finding | OCR | 1369 | `source`: scanned book, a vowel sign read as a danda |
| `00b09cfe2c89c434` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: book title as a running header |
| `00b09cfe2c89c434` | `ind-bn-sangraha-v-train-000000` | finding | OCR | 259 | `source`: triangle sign read as Latin A |
| `12794bb8fec8d0f8` | `ind-bn-sangraha-v-train-000000` | finding | OCR | 499 | `source`: scanned dictionary, misread letters throughout (danda for a vowel sign, garbled sutra numbers, ? inside words) |
| `12794bb8fec8d0f8` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 687 | `source`: Latin f inside a Sanskrit derivation |
| `12794bb8fec8d0f8` | `ind-bn-sangraha-v-train-000000` | finding | G3 | 2766 | `source`: text lost mid-word, an unrelated derivation follows |
| `12794bb8fec8d0f8` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 7161 | `source`: Assamese wa inside a Sanskrit word; DB-A6-020 covers only the Assamese ra |
| `12794bb8fec8d0f8` | `ind-bn-sangraha-v-train-000000` | finding | C3 | 7416 | `source`: ends inside an unclosed verse quote |
| `737c9c028d1ccfff` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: desk byline joined to the first sentence |
| `737c9c028d1ccfff` | `ind-bn-sangraha-v-train-000000` | finding | G2 | 99 | `source`: RAB written without ZWJ, twice, in the raw text too |
| `7ce047c033c46620` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `71bcc221f0fce456` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: book running header joined to the first line |
| `71bcc221f0fce456` | `ind-bn-sangraha-v-train-000000` | finding | OCR | 1927 | `source`: scanned book, misread vowel signs (also at 2752) |
| `71bcc221f0fce456` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 2072 | `source`: Assamese ra in one word; DB-A6-020 needs 7 or more to act |
| `71bcc221f0fce456` | `ind-bn-sangraha-v-train-000000` | finding | C3 | 3378 | `source`: ends mid-sentence |
| `eecd59d16eb2e4a6` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `d126a37532a9a7cf` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 1473 | `source`: portal sign-off with date and initials |
| `2fdace7bbf6e32f3` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `adf572971bf3d6d9` | `ind-bn-sangraha-v-train-000000` | finding | G3 | 0 | `source`: starts mid-passage, opening cut |
| `adf572971bf3d6d9` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 210 | `source`: Assamese ra in place of Bengali ra (also at 2869); DB-A6-020 needs 7 or more to act |
| `adf572971bf3d6d9` | `ind-bn-sangraha-v-train-000000` | finding | G3 | 1545 | `source`: sentences cut and words missing in several paragraphs (also at 1686) |
| `adf572971bf3d6d9` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 4850 | `source`: Latin fragment joined to a word where a quoted verse should be |
| `adf572971bf3d6d9` | `ind-bn-sangraha-v-train-000000` | finding | C3 | 7343 | `source`: ends mid-sentence |
| `ded12bb595c237b5` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `e7bb7d870eddd3ec` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 2621 | `source`: closing line asking readers to follow the site |
| `17c6c3846e50407f` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 381 | `source`: old-font residue, vowel signs out of order in one word; cleaning removed one of two doubled signs, the word stays broken |
| `6ea2e576b58bc0b7` | `ind-bn-sangraha-v-train-000000` | finding | C3 | 1031 | `source`: ends mid-sentence |
| `b3d9814e4abc8537` | `ind-bn-sangraha-v-train-000000` | finding | C2 | 162 | `source`: the first paragraph appears twice |
| `f5e8c01fb2e4b0bb` | `ind-bn-sangraha-v-train-000000` | finding | C2 | 0 | `source`: a quote paragraph repeated as the third paragraph |
| `a531ad5e1b4ec988` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: site name banner before the article |
| `a531ad5e1b4ec988` | `ind-bn-sangraha-v-train-000000` | finding | G4 | 907 | `source`: space after the decimal point in the ratings list, in the raw text too |
| `e9708d968c9d2885` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |

## Summary

- Documents read: 50 (25 per shard)
- ok: 16
- with a finding: 34
- codes found: C1 (25), A6 (10), G3 (6), C3 (4), OCR (4), G2 (2), G4 (2), C2 (2), D3 (2) (OCR is not a DISEASES code)
- source: 57 findings; cleaning: 0
- G1 0. The two G2 rows are `source`: RAB is written without ZWJ in the raw text, and no document lost a ZWJ or ZWNJ in cleaning. No G4 from cleaning: no Bengali digit became Latin; the two G4 rows are spaces after a decimal point that the raw text already has.
- What cleaning changed in these 50: it removed date and time trailer lines and related-link lists (sign-off initials and short link lists before or after them stay, rows above), replaced one wrong danda sign with `।`, turned a Latin 1 into a Bengali digit in one read-time label, and removed one of two doubled vowel signs in an already broken word.
- `DB-A6-020` replaced the Assamese ra with the Bengali ra in `12794bb8fec8d0f8` (28 letters). It acts only when a document has 7 or more, so `71bcc221f0fce456` and `adf572971bf3d6d9` keep 1 and 2; the Assamese wa (`12794bb8fec8d0f8`) is not covered.
- Old-font conversion residue (symbols or wrong letters in place of vowel signs) is in 4 documents of both shards: `dce0f53a3c0625ba`, `f1c1a8403bbb071d`, `41b152246fc99def`, `17c6c3846e50407f`. All are in the raw text.
- Writer's typos in the source, no code, in documents that also have a finding: `dce0f53a3c0625ba` at 135; `c79b75fcbe68f548` at 419, 1712; `c9008b54b5e55930` at 477; `13220cb822d3d2d8` at 1217; `9157d11b82307cd1` at 620; `d126a37532a9a7cf` at 374; `adf572971bf3d6d9` at 1356.
