# Sanskrit reader audit, day D4 (first reader)

Refs #711. Documents drawn with `random.Random(4).sample(range(n), 25)` from `ind-sa-fw2-train-000000` (n = 5667), decoded with the frozen tokenizer p1536 (sha256 `e6b93a93…`). Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text. `OCR` is not a DISEASES code: it marks scanned-book text with misread letters, written down as #527 says for codes outside the list. Each finding's note starts with `source` (also in the raw text) or `cleaning` (not in the raw text). The tags come from @shankarpandala's comparison of each document with the raw part `ind-sa-fw2_part-00000.parquet` (sha256 `1238fde5…`) on this PR; the new `cleaning` row I checked against the shard.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `75423f9e4d47b94e` | `ind-sa-fw2-train-000000` | finding | G3 | 466 | `source`: blank lines, quoted verse kept only its first line |
| `75423f9e4d47b94e` | `ind-sa-fw2-train-000000` | finding | C3 | 872 | `source`: ends mid-sentence |
| `4a0d46c68a0ec578` | `ind-sa-fw2-train-000000` | ok |  |  | stotra, complete |
| `bd181980f5d209a9` | `ind-sa-fw2-train-000000` | ok |  |  |  |
| `b7c7d966b6019d97` | `ind-sa-fw2-train-000000` | finding | G3 | 912 | `source`: blank lines, quoted verse kept only its first half |
| `b7c7d966b6019d97` | `ind-sa-fw2-train-000000` | finding | C3 | 1136 | `source`: ends mid-word |
| `738dca7eb9deb0bb` | `ind-sa-fw2-train-000000` | ok |  |  | news |
| `d6049ed74b2695f9` | `ind-sa-fw2-train-000000` | ok |  |  | colon at 95 is a dateline, not a visarga |
| `bd4759d1fb5e05ad` | `ind-sa-fw2-train-000000` | ok |  |  | Rigveda sukta, complete |
| `0fe8486c2bb9e0c4` | `ind-sa-fw2-train-000000` | ok |  |  | news |
| `68c788acd9ae8594` | `ind-sa-fw2-train-000000` | finding | D3 | 1444 | `source`: one Hindi sentence inside Sanskrit news |
| `37d6294642ac041a` | `ind-sa-fw2-train-000000` | ok |  |  | Samhita text; avagraha after a space is normal |
| `9f60e07096013f17` | `ind-sa-fw2-train-000000` | ok |  |  | Purana chapter, complete |
| `e4e5b4944e701553` | `ind-sa-fw2-train-000000` | ok |  |  | essay; spelling slips are the author's |
| `1e92b88cfec3f31a` | `ind-sa-fw2-train-000000` | ok |  |  | news |
| `ec09cf84f27662b9` | `ind-sa-fw2-train-000000` | ok |  |  | kavya canto, complete; title line twice at top |
| `4d8f70ef5085c008` | `ind-sa-fw2-train-000000` | finding | G3 | 0 | `source`: starts mid-word, opening cut |
| `4d8f70ef5085c008` | `ind-sa-fw2-train-000000` | finding | OCR | 53 | `source`: scanned commentary, misread letters and split words throughout |
| `cd67620279a32c81` | `ind-sa-fw2-train-000000` | finding | A6 | 71 | `source`: Latin capital I used as danda |
| `cd67620279a32c81` | `ind-sa-fw2-train-000000` | finding | A6 | 445 | `source`: Latin capital I used as danda |
| `185387955f0849d5` | `ind-sa-fw2-train-000000` | ok |  |  | news |
| `832cf7bbd1a72622` | `ind-sa-fw2-train-000000` | finding | C2 | 87 | `source`: first verse repeated; in the raw text one Hindi line sat between the copies, cleaning removed it |
| `832cf7bbd1a72622` | `ind-sa-fw2-train-000000` | finding | G4 | 2401 | `source`: ASCII colon for visarga, 7 times from here to 3164 |
| `4f7a6a85a601d7bf` | `ind-sa-fw2-train-000000` | finding | A6 | 4366 | `source`: OM sign in place of a vowel sign, also at 5172; `---` gaps are the edition's |
| `4f7a6a85a601d7bf` | `ind-sa-fw2-train-000000` | finding | G3 | 8753 | `cleaning`: verse numbers १००–१२० after ॥ removed (21 verses; 1–99 kept), by `DB-B4-004` in `teams/01-data-a/spec_v1_1/clean.py`, whose `\d{3,}` also matches Devanagari digits |
| `7bd8a8fa5e6288c7` | `ind-sa-fw2-train-000000` | finding | A1 | 104314 | `source`: VARIATION SELECTOR-15 U+FE0E, 211 times, ends of apparatus lines |
| `7bd8a8fa5e6288c7` | `ind-sa-fw2-train-000000` | finding | C1 | 104174 | `source`: 8.6k chars of manuscript variant notes after the text |
| `51e19714fc999a42` | `ind-sa-fw2-train-000000` | finding | C2 | 68 | `source`: first line repeated; in the raw text one Hindi line sat between the copies, cleaning removed it |
| `51e19714fc999a42` | `ind-sa-fw2-train-000000` | finding | G3 | 7034 | `source`: spaces between words lost in many verses |
| `c1a3da3a70d87d45` | `ind-sa-fw2-train-000000` | ok |  |  | Rigveda with svara marks and padapatha |
| `46f9b9113237390c` | `ind-sa-fw2-train-000000` | finding | C1 | 0 | `source`: wiki user-page header with Latin user name |
| `46f9b9113237390c` | `ind-sa-fw2-train-000000` | finding | B2 | 194 | `source`: `<poem>` tag left in |
| `07aafc1c903649cd` | `ind-sa-fw2-train-000000` | ok |  |  | Rigveda with bhashya; hyphen line breaks at 744 are the scan's |
| `7d742912c34be333` | `ind-sa-fw2-train-000000` | finding | G3 | 0 | `source`: starts mid-word, opening cut |
| `7d742912c34be333` | `ind-sa-fw2-train-000000` | finding | OCR | 52 | `source`: scanned commentary, misread letters and split words throughout |

## Summary

- Documents read: 25
- ok: 14
- with a finding: 11
- codes found: G3 (6), A6 (3), C1 (2), C2 (2), C3 (2), A1 (1), B2 (1), D3 (1), G4 (1), OCR (2, not a DISEASES code)
- source: 20 findings; cleaning: 1 (`4f7a6a85a601d7bf`, G3, `DB-B4-004`, raised separately by @shankarpandala)
- G1 0, G2 0. The one G4 row (ASCII colon for visarga, `832cf7bbd1a72622`) is the case #576 asked to hear about: it is `source`. The raw text has the same 7 colons and the same 34 visargas, so cleaning edited no visarga.
