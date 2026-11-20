# Tamil reader audit, day D4 (Wed 18 Nov)

Issue #529. Documents drawn with `random.Random(4).sample(range(n), 50)` from `ind-ta-sangraha-v-train-000000`, decoded with the frozen tokenizer p1536. Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `b6e8cb1bc780a5b2` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `b2270d1d6afd5af8` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 229 | colon written as aytham U+0B83 |
| `f2d8aad58bc40638` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 44 | colon written as aytham U+0B83 |
| `2098e03aca3ecdd3` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `2911d6acbdecf5fd` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 2325 | site promo and TV channel list footer |
| `4f031cb94a12e50d` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `7f589a5b1f261119` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `6249fe1b1b96741f` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `5b67805582a4056a` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `53328137ecdcfcb8` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 2775 | colon written as aytham U+0B83 |
| `53328137ecdcfcb8` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | page title, site name and byline lines at top |
| `53328137ecdcfcb8` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 2756 | related-headline list at end |
| `e7a05aa2ea1e588d` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 106 | colon written as aytham U+0B83 |
| `59fdaa7fd3a69fda` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `cc42ebc20d8ba1c2` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-word, opening cut |
| `52073e78c93ab43a` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 337 | colon written as aytham before a letter |
| `52073e78c93ab43a` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 274 | u sign + aa sign used for the long-u sign (Dinamalar style, 2x) |
| `7e58e72b1d38865f` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-word, opening cut (OCR book page) |
| `7e58e72b1d38865f` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 1998 | u sign + aa sign where one sign expected (2x) |
| `7e58e72b1d38865f` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 2992 | Latin O used as Tamil digit zero (OCR) |
| `9de52b6bbcb3017b` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `4b563fbbbd8c572e` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 351 | quiz questions removed, only answers kept |
| `4b563fbbbd8c572e` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 355 | colon written as aytham U+0B83 (18x) |
| `a4c40a0287d1e17a` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 8 | colon written as aytham U+0B83 |
| `ce898dcaac3e1df3` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 15 | colon written as aytham U+0B83 |
| `bc181046bab89ad8` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 648 | stops mid-sentence, end cut |
| `0ec4917a88faa0bc` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `0b98990b1828e004` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 3457 | list of items removed, sentence starts at 'such as' |
| `0b98990b1828e004` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 2126 | colon written as aytham U+0B83 (8x) |
| `0b98990b1828e004` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 3629 | unit Wh shown as Tamil letters (font conversion) |
| `0b98990b1828e004` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | site trending-headlines list at top |
| `b02877dde1cb95fb` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `ed58e2937370a44f` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 2129 | related-article headline at end |
| `a39d95d5e12c8f5c` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 507 | colon written as aytham U+0B83 (3x) |
| `a39d95d5e12c8f5c` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 1370 | related job-ad headline inside the article |
| `f7026d74d9cce0d9` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | page title with site name at top |
| `f7026d74d9cce0d9` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 2454 | related-headline list at end |
| `6f88ea9e3d7af29f` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 8 | colon written as aytham U+0B83 |
| `b61c5a5de775f5a0` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `9f25b25c7108076d` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `6e47faad13af6285` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `7773931c7666046c` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | link page: menus, JavaScript notice, related links, little prose |
| `dfed2fcfce1be27d` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 125 | image copyright line (3x) |
| `dfed2fcfce1be27d` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 187 | Also Read link line (2x) |
| `8c558dbaf0ec04e4` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `d12b085d3fddc8fb` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 433 | colon written as aytham U+0B83 (6x) |
| `d12b085d3fddc8fb` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | site hashtag-headline list at top |
| `78b6a273def0a7fe` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `0d741151121a0b2f` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 1154 | colon written as aytham U+0B83 (10x) |
| `3811ae9be6184acb` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `1c6befd23d61fd03` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `cd87aae490845c38` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | page title with site name at top |
| `cd87aae490845c38` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 1012 | related headline at end |
| `28b399b7b39e2adc` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `38b1a7ad5013e705` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `38a18628cbe54ff7` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 1817 | colon written as aytham U+0B83 |
| `38a18628cbe54ff7` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 1692 | related-headline list at end |
| `dc181867c5c32047` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `5e1e7b92305917b1` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 10 | colon written as aytham U+0B83 |
| `3e37eb0e5bffc070` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 370 | word cut at a line break, first letter lost |
| `3e37eb0e5bffc070` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 1539 | stops mid-sentence, end cut |
| `0d0cb0705c2e18d0` | `ind-ta-sangraha-v-train-000000` | ok |  |  | two unrelated articles joined at 629 (C4, not an audit code) |
| `6d19ed6fbf0c1f4c` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 29 | colon written as aytham U+0B83 |
| `4d1e37b425720145` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 6 | colon written as aytham U+0B83 (2x) |
| `4d1e37b425720145` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | listing page of article teasers cut with '..' |
| `c36588c4520094b0` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 12 | colon written as aytham U+0B83 |
| `b21d891f65445af1` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |

## Summary

- Documents read: 50
- ok: 22
- With a finding: 28
- Codes found: G3 (7), G4 (18), A6 (4), C1 (16)
