# Bengali reader audit, day D5

Refs #568. 25 documents drawn with `random.Random(5).sample(range(n), 25)` from each shard of the p1536 sample v0: `ind-bn-fw2-train-000000` (n = 10704) and `ind-bn-sangraha-v-train-000000` (n = 10112), decoded with the frozen tokenizer p1536 (sha256 `e6b93a93…`). Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text. `OCR` is not a DISEASES code: as in #733, it marks scanned-book text with misread letters. Each finding's note starts with `source` (also in the raw text) or `cleaning` (not in the raw text), from comparing each document with its raw part `tokenizer_sample_v0_raw/train/<pack>/part-00000.parquet` (ind-bn-fw2 sha256 `fda2605f…`, ind-bn-sangraha-v `84a59d86…`). The writer's own typos that cleaning did not touch are marked `ok` with a note, as @shankarpandala asked.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `c8d51abfa5c58853` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: desk line before the article |
| `c8d51abfa5c58853` | `ind-bn-fw2-train-000000` | finding | C1 | 787 | `source`: site name and initials at the end |
| `26ddbb16e9101947` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: desk line before the article |
| `2d3b2c3e7eb833aa` | `ind-bn-fw2-train-000000` | finding | C1 | 753 | `source`: related-article headlines and a subscribe prompt at the end (also at 873) |
| `3618cd304527332e` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `fbaad0dac9ef9c64` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: byline and place before the article |
| `fbaad0dac9ef9c64` | `ind-bn-fw2-train-000000` | finding | A6 | 54 | `source`: old-font residue, ref and vowel sign out of order in a place name |
| `02449e173cbf0097` | `ind-bn-fw2-train-000000` | finding | G3 | 1293 | `source`: a sentence lacks its reporting verb |
| `02449e173cbf0097` | `ind-bn-fw2-train-000000` | finding | C1 | 2352 | `source`: initials at the end |
| `26148947ea191737` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: unrelated article teaser at the top, cut off mid-sentence |
| `26148947ea191737` | `ind-bn-fw2-train-000000` | finding | A6 | 1319 | `source`: old-font caret in place of a conjunct sign, 3 times; the caret fix seen elsewhere did not act here |
| `26148947ea191737` | `ind-bn-fw2-train-000000` | finding | C1 | 2045 | `source`: comment-policy notice at the end |
| `85cdfd698492db86` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `8fe679ebbb597a4d` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: site name and date line before the article |
| `8fe679ebbb597a4d` | `ind-bn-fw2-train-000000` | finding | A6 | 94 | `source`: old-font residue, a vowel letter plus a sign in place of one letter |
| `8dba28b4b0fee3d6` | `ind-bn-fw2-train-000000` | finding | C1 | 836 | `source`: agency credit and site sign-off at the end |
| `1aab882c64427bb0` | `ind-bn-fw2-train-000000` | finding | A6 | 9353 | `source`: old-font residue, a conjunct in place of a vowel sign |
| `d690f90a5f282228` | `ind-bn-fw2-train-000000` | finding | C1 | 524 | `source`: SEO keyword phrase repeated inside sentences |
| `d690f90a5f282228` | `ind-bn-fw2-train-000000` | finding | C1 | 965 | `source`: channel subscribe prompt |
| `d690f90a5f282228` | `ind-bn-fw2-train-000000` | finding | C1 | 3557 | `source`: download link line |
| `d690f90a5f282228` | `ind-bn-fw2-train-000000` | finding | D3 | 4378 | `source`: English lists of tutorial chapters and features (also at 4613) |
| `d690f90a5f282228` | `ind-bn-fw2-train-000000` | finding | G3 | 4547 | `cleaning`: 12 English items removed from the middle of the tutorial list by `DB-C5-007`, which reads 5 or more bullet lines of 4 or more words as a related-news ticker; the short items and all Bengali text stay |
| `991d80e21be4e22b` | `ind-bn-fw2-train-000000` | finding | C1 | 369 | `source`: service sign-off and a call to ask questions at the end |
| `9c77c62c8579e02b` | `ind-bn-fw2-train-000000` | finding | A6 | 1051 | `source`: two vowel signs on one letter, out of order |
| `2106d42688525ff8` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `7098673dc20741c9` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: desk line before the article |
| `7098673dc20741c9` | `ind-bn-fw2-train-000000` | finding | D3 | 1441 | `source`: quoted tweets in Hindi and English left untranslated (also at 2088); cleaning removed only their credit lines |
| `caa78963825d43bc` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: placeholder filler text before the post |
| `caa78963825d43bc` | `ind-bn-fw2-train-000000` | finding | C1 | 968 | `source`: technical-credit line at the end |
| `06cab795ba1ba87b` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: date stamp and byline before the article |
| `384f07e8199c8102` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: desk line before the article |
| `bb2ea0a7cb69e5db` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `d7c88f047b8042ab` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: byline and place before the article |
| `2f0cc289240cebf8` | `ind-bn-fw2-train-000000` | finding | G3 | 0 | `source`: opening sentence garbled, words missing |
| `2f0cc289240cebf8` | `ind-bn-fw2-train-000000` | finding | A6 | 211 | `source`: old-font residue, ref missing and a stray vowel sign |
| `f1473eaff51f4b19` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `edabb95ae375495a` | `ind-bn-fw2-train-000000` | finding | C1 | 3260 | `source`: initials at the end; cleaning removed the time line before them |
| `b8b3a0b29bd829dc` | `ind-bn-fw2-train-000000` | finding | G3 | 616 | `source`: a word missing in a sentence |
| `4fd139f1b3fe2f81` | `ind-bn-sangraha-v-train-000000` | finding | G3 | 0 | `source`: starts mid-sentence, opening cut |
| `4fd139f1b3fe2f81` | `ind-bn-sangraha-v-train-000000` | finding | OCR | 428 | `source`: scanned book, misread letters and joined words throughout |
| `4fd139f1b3fe2f81` | `ind-bn-sangraha-v-train-000000` | finding | G3 | 806 | `source`: words lost inside sentences (also at 868) |
| `492e89e3ee4843fd` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `c6e2e2a9d71ac09b` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `88ccecc5245db76b` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: correspondent byline before the article |
| `88ccecc5245db76b` | `ind-bn-sangraha-v-train-000000` | finding | C2 | 2579 | `source`: two sentences repeat an earlier passage |
| `00f94696503c834a` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 827 | `source`: read-more link inside the article, twice |
| `b04b0aaf5f72822e` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `1645acfb631e14de` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: related-article headlines at the top |
| `6363075579dcc4c2` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 2067 | `source`: Assamese ra in one word; DB-A6-020 needs 7 or more to act |
| `8c61a1ad723ac5c2` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `3bd68e38da22121f` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `6bd99efd3937b74d` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: desk line before the article |
| `7ff26f377079e2c3` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: byline and place before the article |
| `a6e9caae4bd7ef4b` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: whole document is a list of unrelated headlines |
| `37c62c2940bd2f55` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: byline before the article |
| `37c62c2940bd2f55` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 1461 | `source`: old-font residue, symbols in place of conjuncts (also at 2753); cleaning fixed two carets in this document |
| `996ff32be378fe34` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 581 | `source`: publication time stamp at the end |
| `18806f85f311494c` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: bylines and places before the article |
| `804dc0a0cf31ce70` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `6ff4a03899963988` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `3f3580a032e7e429` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `8d62d7700549106a` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `62c3272cd482ac4e` | `ind-bn-sangraha-v-train-000000` | finding | G3 | 0 | `source`: starts mid-sentence, opening cut |
| `62c3272cd482ac4e` | `ind-bn-sangraha-v-train-000000` | finding | OCR | 96 | `source`: scanned book, misread and dropped letters throughout |
| `62c3272cd482ac4e` | `ind-bn-sangraha-v-train-000000` | finding | G3 | 139 | `source`: text missing at page breaks (also at 3076) |
| `62c3272cd482ac4e` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 780 | `source`: Assamese ra inside a misread word |
| `62c3272cd482ac4e` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 2442 | `source`: Latin junk where an Arabic verse stood |
| `62c3272cd482ac4e` | `ind-bn-sangraha-v-train-000000` | finding | C3 | 4868 | `source`: ends mid-sentence |
| `fab3846f9bae4cc6` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `256dccbd725896c0` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `76a8dc8c3b2606d6` | `ind-bn-sangraha-v-train-000000` | finding | C2 | 0 | `source`: the opening line appears twice |
| `079cf754acb114b7` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: desk line before the article |

## Summary

- Documents read: 50 (25 per shard)
- ok: 16 (12 of them with the writer's typos only)
- with a finding: 34
- codes found: C1 (31), A6 (10), G3 (8), C2 (2), D3 (2), OCR (2), C3 (1) (OCR is not a DISEASES code)
- source: 55 findings; cleaning: 1
- G1 0, G2 0, G4 0: no word split at a vowel sign, no ZWJ or ZWNJ lost, and no Bengali digit turned Latin in cleaning.
- What cleaning changed in these 50: it removed tweet credit lines and a time trailer line, turned two old-font carets into the right conjunct sign (`37c62c2940bd2f55`), removed one of two doubled vowel signs in a word already broken in the raw text (`3bd68e38da22121f`), and removed 12 English items from the middle of an English list (`d690f90a5f282228`, the one `cleaning` row, by `DB-C5-007`).
- The old-font caret fix acted in `37c62c2940bd2f55` but not in `26148947ea191737`, where three carets stay.
- Writer's typos in the source, no code, in documents that also have a finding (count per document): `c8d51abfa5c58853` (1); `2d3b2c3e7eb833aa` (1); `fbaad0dac9ef9c64` (9); `02449e173cbf0097` (3); `26148947ea191737` (8); `8fe679ebbb597a4d` (4); `8dba28b4b0fee3d6` (1); `1aab882c64427bb0` (10); `d690f90a5f282228` (5); `991d80e21be4e22b` (5); `9c77c62c8579e02b` (4); `7098673dc20741c9` (2); `caa78963825d43bc` (2); `06cab795ba1ba87b` (9); `384f07e8199c8102` (1); `2f0cc289240cebf8` (10); `edabb95ae375495a` (4); `b8b3a0b29bd829dc` (4); `88ccecc5245db76b` (8); `1645acfb631e14de` (2); `6363075579dcc4c2` (11); `6bd99efd3937b74d` (4); `7ff26f377079e2c3` (3); `37c62c2940bd2f55` (8); `76a8dc8c3b2606d6` (1).
