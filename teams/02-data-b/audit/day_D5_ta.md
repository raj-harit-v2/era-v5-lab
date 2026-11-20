# Tamil reader audit, day D5 (Thu 19 Nov)

Issue #529. Documents drawn with `random.Random(5).sample(range(n), 50)` from `ind-ta-sangraha-v-train-000000`, decoded with the frozen tokenizer p1536. Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `995e8bbd555fead8` | `ind-ta-sangraha-v-train-000000` | ok |  |  | one U+FFFD at the end (A4, not an audit code) |
| `663df7f91d1b5919` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `a85cae03040e83d0` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 527 | colon written as aytham U+0B83 (3x) |
| `a85cae03040e83d0` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 4186 | related-post title and label at end |
| `2bb5bc3d48031950` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 730 | colon written as aytham U+0B83 |
| `2bb5bc3d48031950` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | site trending-headlines list at top |
| `703871a773fc7289` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 3603 | sentence breaks off before a heading (book scan) |
| `703871a773fc7289` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 7716 | stops mid-sentence, end cut |
| `21e32e5c0cd38139` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `742d22af79d97461` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `fd72cba15f89265b` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 442 | related-headline list inside the article |
| `fd72cba15f89265b` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 2573 | site promo and TV channel list footer |
| `05609d9b3b659189` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 21 | starts mid-sentence, opening cut (OCR book page) |
| `05609d9b3b659189` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 3525 | stops mid-sentence, end cut |
| `aff1e51a112ebe92` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 1615 | site promo and TV channel list footer |
| `1e1827915b43bbac` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 211 | colon written as aytham U+0B83 (3x) |
| `1e1827915b43bbac` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 411 | Devanagari quote run into Tamil lines (OCR book) |
| `1e1827915b43bbac` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 1886 | Latin letter inside a Tamil word (OCR) |
| `861559a33a81e14c` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | English and Tamil title lines repeated with a template join |
| `224b20c8d27868cc` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 358 | colon written as aytham U+0B83 |
| `224b20c8d27868cc` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | only a list of headlines, no article |
| `1ac6b62d9cddd92c` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `2454578a40013008` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `cd26d0f24755811e` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `9916d2bbda165345` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `234872da1a0897b3` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 656 | colon written as aytham U+0B83 |
| `234872da1a0897b3` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 386 | English name in legacy-font letters, Latin and Tamil mixed |
| `234872da1a0897b3` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 534 | related-posts list at end |
| `ffde5247caad4e05` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 247 | colon written as aytham U+0B83 |
| `035bcc7273dad9b5` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `1ad836897013a135` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-sentence, opening cut (book scan) |
| `1ad836897013a135` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 151 | colon written as aytham U+0B83 |
| `ce0a159f4bf78cc2` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 888 | colon written as aytham U+0B83 |
| `5ec65daf55276a98` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 324 | AU vowel sign used for e-sign + LLA (legacy font conversion, 2x) |
| `76d0f6d0f427edfd` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-heading, opening cut (book scan) |
| `76d0f6d0f427edfd` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 1964 | stops mid-sentence, end cut |
| `76d0f6d0f427edfd` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 1708 | colon written as aytham before a letter |
| `3954243a4ae8f920` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-sentence, opening cut (magazine scan) |
| `3954243a4ae8f920` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 823 | product ad box text inserted into the article |
| `72f302d8718fe2fb` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `0d8dfd7372e826b2` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 256 | colon written as aytham U+0B83 |
| `4c34415fef6d093f` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `54bdd967cb4da642` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | page title with site name at top |
| `54bdd967cb4da642` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 4193 | previous/next article links at end |
| `0aae662b37137b1d` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | related headlines at top, one repeated |
| `3f41352114e1cfc4` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 781 | colon written as aytham U+0B83 (6x) |
| `5408574598a2808c` | `ind-ta-sangraha-v-train-000000` | ok |  |  | one doubled vowel sign typo in the title, source spelling |
| `09b1b35d4e81ea0f` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `98cad05fc9d72f78` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `41d17fcf1c5c3499` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 58 | colon written as aytham U+0B83 (2x) |
| `9ad8e0e822d4aba5` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `52ca442d0d316596` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 173 | aa vowel sign + virama used in place of letter RA (look-alike) |
| `07cc583b22442735` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 555 | site Facebook promo footer |
| `99a9dbe04116a544` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 1170 | colon written as aytham U+0B83 (3x) |
| `684c3adc6c8205d7` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 1575 | colon written as aytham U+0B83 (2x) |
| `684c3adc6c8205d7` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | page title with English slug and posted-date lines |
| `684c3adc6c8205d7` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 1520 | related article teaser inside the text |
| `684c3adc6c8205d7` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 2338 | related-article list and tags at end |
| `5e92ef3eebbd99b4` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `f86cec93f2e0f7e6` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `ffb6a11d56a2a65f` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 11 | colon written as aytham before a letter |
| `70ce9b7a7b2c6a09` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-word, opening cut (book scan) |
| `70ce9b7a7b2c6a09` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 607 | colon written as aytham U+0B83 |
| `32ff92897989b619` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-story, opening paragraph missing |
| `32ff92897989b619` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 7 | aa vowel sign + virama used in place of letter RA (many) |
| `de257961676e553e` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-story, opening missing |
| `d268a50b6eee4358` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-sentence, opening cut (lecture transcript) |
| `ee3133a8303b974a` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 357 | related-headline list at end |
| `b85e10cd90a9ab3c` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 9 | colon written as aytham U+0B83 (3x) |
| `b85e10cd90a9ab3c` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 2065 | teaser copy of the opening at end |
| `7fc4105197ec07b4` | `ind-ta-sangraha-v-train-000000` | ok |  |  | one U+FFFD at the end (A4, not an audit code) |

## Summary

- Documents read: 50
- ok: 18
- With a finding: 32
- Codes found: G3 (12), G4 (17), A6 (6), C1 (18)
