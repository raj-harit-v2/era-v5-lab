# Bengali reader audit, day D6

Refs #568. 25 documents drawn with `random.Random(6).sample(range(n), 25)` from each shard of the p1536 sample v0: `ind-bn-fw2-train-000000` (n = 10704) and `ind-bn-sangraha-v-train-000000` (n = 10112), decoded with the frozen tokenizer p1536 (sha256 `e6b93a93…`). Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text. `OCR` is not a DISEASES code: as in #733, it marks scanned-book text with misread letters. Each finding's note starts with `source` (also in the raw text) or `cleaning` (not in the raw text), from comparing each document with its raw part `tokenizer_sample_v0_raw/train/<pack>/part-00000.parquet` (ind-bn-fw2 sha256 `fda2605f…`, ind-bn-sangraha-v `84a59d86…`). The writer's own typos that cleaning did not touch are marked `ok` with a note, as @shankarpandala asked.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `da8f1a3efde219d4` | `ind-bn-fw2-train-000000` | finding | C1 | 2185 | `source`: site name and initials at the end |
| `60b4dae3596eb9ed` | `ind-bn-fw2-train-000000` | ok |  |  |  |
| `74a010a74c30c729` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `e4f00f241faf89da` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `b314c4f28ba81061` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: desk line before the article |
| `57769b0dcfc9430d` | `ind-bn-fw2-train-000000` | finding | A6 | 4357 | `source`: old-font caret in place of a conjunct sign; vowel signs out of order at 4724; cleaning fixed another symbol in this document |
| `3ffb03f6bcf61e59` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: byline before the article |
| `bb7fdc42141354dc` | `ind-bn-fw2-train-000000` | ok |  |  |  |
| `cf1fffb062e00595` | `ind-bn-fw2-train-000000` | finding | C1 | 54 | `source`: byline between headline and body |
| `cf1fffb062e00595` | `ind-bn-fw2-train-000000` | finding | A6 | 72 | `source`: old-font residue, a vowel sign before its conjunct |
| `cf1fffb062e00595` | `ind-bn-fw2-train-000000` | finding | C1 | 1393 | `source`: initials and a like prompt at the end |
| `12908a7a38eff9f2` | `ind-bn-fw2-train-000000` | finding | A6 | 1998 | `source`: a currency sign used as a danda |
| `12908a7a38eff9f2` | `ind-bn-fw2-train-000000` | finding | G3 | 2008 | `source`: a negation word missing in a sentence |
| `12908a7a38eff9f2` | `ind-bn-fw2-train-000000` | finding | C1 | 2367 | `source`: reporter name at the end |
| `9e5519ace299aaaa` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `bed9eb31ab14754c` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: byline before the article |
| `73cfea54ce6a2006` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: page title with site name, then an SEO keyword line partly in romanised Bengali (at 83) |
| `73cfea54ce6a2006` | `ind-bn-fw2-train-000000` | finding | C1 | 1835 | `source`: book details box, download links and site promotion at the end |
| `556a12d55afbc9e1` | `ind-bn-fw2-train-000000` | finding | G3 | 310 | `source`: a helper verb missing in a sentence |
| `556a12d55afbc9e1` | `ind-bn-fw2-train-000000` | finding | A6 | 515 | `source`: old-font residue in one word |
| `fa8ced0e3eecbd02` | `ind-bn-fw2-train-000000` | finding | G3 | 0 | `source`: starts without its lead; the scene is never introduced |
| `f44b81f6f2250d76` | `ind-bn-fw2-train-000000` | finding | C1 | 807 | `source`: source-credit line at the end |
| `0247d2169ab33c67` | `ind-bn-fw2-train-000000` | finding | C1 | 678 | `source`: video link line at the end |
| `3487534b4f56aea0` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: byline before the article |
| `3487534b4f56aea0` | `ind-bn-fw2-train-000000` | finding | C1 | 1193 | `source`: like prompt at the end |
| `8170e6b631fd95e7` | `ind-bn-fw2-train-000000` | ok |  |  | writer's typos, source |
| `d066f39917386f27` | `ind-bn-fw2-train-000000` | finding | C1 | 46 | `source`: byline with site name and time stamp |
| `d066f39917386f27` | `ind-bn-fw2-train-000000` | finding | C1 | 975 | `source`: initials at the end |
| `f4a5f7ebe98afb8d` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: update time stamp and byline before the article |
| `50b9c0fe1c0c47f6` | `ind-bn-fw2-train-000000` | finding | C1 | 3101 | `source`: initials at the end; cleaning removed the time line before them |
| `5571fa8d80828a3d` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: date stamp and desk line before the article |
| `a3c6818bee51958c` | `ind-bn-fw2-train-000000` | finding | C1 | 547 | `source`: site name and initials at the end |
| `9cf36b452c0aa8b5` | `ind-bn-fw2-train-000000` | finding | C1 | 0 | `source`: blog front page: teasers of unrelated posts, several cut off (at 637 and 3077) |
| `9cf36b452c0aa8b5` | `ind-bn-fw2-train-000000` | finding | B2 | 2140 | `source`: forum markup tag left in |
| `9cf36b452c0aa8b5` | `ind-bn-fw2-train-000000` | finding | G3 | 2748 | `source`: a helper verb missing in a sentence |
| `2450b236b83370d8` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `be17524fcbf6445b` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: site name, date and byline joined to the first sentence; cleaning turned the Latin digits in the site name into Bengali |
| `be17524fcbf6445b` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 603 | `source`: old-font residue, a quote mark in place of a vowel sign, 3 times |
| `be17524fcbf6445b` | `ind-bn-sangraha-v-train-000000` | finding | G3 | 977 | `source`: a sentence starts with its beginning missing |
| `28f8482e4bfa16df` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `6069fad7c658c132` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 2222 | `source`: a ganda mark in place of a conjunct sign |
| `d5733d46d0012ec6` | `ind-bn-sangraha-v-train-000000` | finding | C2 | 0 | `source`: the opening line is repeated in the first paragraph |
| `d5733d46d0012ec6` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 62 | `source`: desk line before the article |
| `d5733d46d0012ec6` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 716 | `source`: app promotion at the end |
| `e99b7d325ef12dda` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `2943cc37f93bc16b` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `20d7f12840c023fd` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `37536fd723003b1e` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `ddda83cf573ec9f7` | `ind-bn-sangraha-v-train-000000` | finding | G3 | 0 | `source`: starts mid-sentence, opening cut |
| `ddda83cf573ec9f7` | `ind-bn-sangraha-v-train-000000` | finding | OCR | 281 | `source`: scanned book, misread letters throughout |
| `ddda83cf573ec9f7` | `ind-bn-sangraha-v-train-000000` | finding | A6 | 636 | `source`: Assamese ra read for ba in the scan |
| `ddda83cf573ec9f7` | `ind-bn-sangraha-v-train-000000` | finding | C3 | 3178 | `source`: ends mid-word |
| `a5272db9f388983f` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `c567c9d6feda0e7f` | `ind-bn-sangraha-v-train-000000` | finding | OCR | 16 | `source`: scanned book, misread letters throughout |
| `c567c9d6feda0e7f` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 803 | `source`: book running header inside the text |
| `5034d41bef9c023b` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |
| `1b6111365ec4a2e5` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: correspondent line, repeated at the end |
| `040b36f8f24a4fad` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `b00856cd1a77f51a` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 392 | `source`: unrelated article headline inside the text |
| `b00856cd1a77f51a` | `ind-bn-sangraha-v-train-000000` | finding | D3 | 873 | `source`: two English tweets left untranslated |
| `1c8a35c0bc2f0525` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `1f2025298d342a7e` | `ind-bn-sangraha-v-train-000000` | finding | OCR | 198 | `source`: scanned book, misread letters throughout |
| `1f2025298d342a7e` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 1966 | `source`: book running header inside the text |
| `847120f7d416b586` | `ind-bn-sangraha-v-train-000000` | finding | C2 | 0 | `source`: the opening paragraph is repeated at the end |
| `560a90d26dd9c9de` | `ind-bn-sangraha-v-train-000000` | ok |  |  | writer's typos, source |
| `cfbb685e9249d3e8` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: desk line before the article |
| `4fad556cbe2b58e2` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 0 | `source`: desk line before the article |
| `d52b22a7a1d52497` | `ind-bn-sangraha-v-train-000000` | finding | C1 | 44 | `source`: section and site name after the title, then a desk line |
| `e10a0b10f7605268` | `ind-bn-sangraha-v-train-000000` | finding | OCR | 101 | `source`: scanned book, misread letters throughout |
| `4ea56590b989290d` | `ind-bn-sangraha-v-train-000000` | ok |  |  |  |

## Summary

- Documents read: 50 (25 per shard)
- ok: 18 (10 of them with the writer's typos only)
- with a finding: 32
- codes found: C1 (30), A6 (7), G3 (6), OCR (4), C2 (2), B2 (1), C3 (1), D3 (1) (OCR is not a DISEASES code)
- source: 52 findings; cleaning: 0
- G1 0, G2 0, G4 0: no word split at a vowel sign, no ZWJ or ZWNJ lost, and no Bengali digit turned Latin in cleaning.
- What cleaning changed in these 50: it removed a publication-date line, a read-more line and a time trailer line, turned one old-font symbol into the right conjunct sign (`57769b0dcfc9430d`), wrote khanda ta as one letter in two documents, and turned the Latin digits of a site name into Bengali digits (`be17524fcbf6445b`). No `cleaning` row.
- The old-font fix acted on one symbol in `57769b0dcfc9430d` but left its caret; the currency sign used as a danda in `12908a7a38eff9f2` stays (in D4 cleaning replaced the same sign in one document).
- Writer's typos in the source, no code, in documents that also have a finding (count per document): `da8f1a3efde219d4` (3); `b314c4f28ba81061` (9); `57769b0dcfc9430d` (5); `3ffb03f6bcf61e59` (7); `cf1fffb062e00595` (8); `12908a7a38eff9f2` (2); `bed9eb31ab14754c` (5); `73cfea54ce6a2006` (5); `556a12d55afbc9e1` (4); `3487534b4f56aea0` (4); `d066f39917386f27` (2); `f4a5f7ebe98afb8d` (2); `50b9c0fe1c0c47f6` (5); `a3c6818bee51958c` (2); `9cf36b452c0aa8b5` (7); `be17524fcbf6445b` (9); `6069fad7c658c132` (1); `d5733d46d0012ec6` (1); `ddda83cf573ec9f7` (2); `1b6111365ec4a2e5` (1); `1f2025298d342a7e` (2); `847120f7d416b586` (6); `4fad556cbe2b58e2` (2); `e10a0b10f7605268` (1).
