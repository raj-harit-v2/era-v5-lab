# Tamil reader audit, day D6 (Fri 20 Nov)

Issue #529. Documents drawn with `random.Random(6).sample(range(n), 50)` from `ind-ta-sangraha-v-train-000000`, decoded with the frozen tokenizer p1536. Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `ade3dd17d14b0eaf` | `ind-ta-sangraha-v-train-000000` | ok |  |  | one U+FFFD at the end (A4, not an audit code) |
| `fbb746f1334ea66b` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `ab95521e3d2bb00f` | `ind-ta-sangraha-v-train-000000` | ok |  |  | print line-break splits leave spaces inside many words (not an audit code) |
| `ca1d9a5d85b97790` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 3042 | Tamil letter I used in place of comma (legacy font conversion, many) |
| `ca1d9a5d85b97790` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | page title with site name and breadcrumb at top |
| `2c95a50c3501f81c` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `a100aded6fa33665` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `93da64a709e27e20` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-sentence, opening cut |
| `93da64a709e27e20` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 291 | site promo and copyright footer |
| `0d9f0382cf2ad91e` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 1049 | stops mid-sentence at the end (book scan) |
| `ea5ef7d0c2c3d15e` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `b999cf12541cdf8b` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `77ef516087d202c2` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 2326 | BMI calculator widget line at end |
| `d86dc80d43b85062` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 140 | u sign + aa sign used for the long-u sign (Dinamalar style) |
| `115d8d1bc60628c5` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 395 | colon written as aytham U+0B83 |
| `72fcae6b46cc8f4d` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `f5300614b566c9a7` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 12 | colon written as aytham U+0B83 (4x) |
| `f5300614b566c9a7` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | whole doc is a list of site headlines, no article body |
| `e601a1b6094f4600` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 1377 | colon written as aytham U+0B83 |
| `e601a1b6094f4600` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 1353 | more-news promo headlines at end |
| `ab27ff66cce52de4` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 2071 | colon written as aytham U+0B83 (2x) |
| `ab27ff66cce52de4` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 2057 | other-news list and social media footer at end |
| `505657c6797c4db6` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 15 | colon written as aytham U+0B83 (6x) |
| `4c3d578412a22197` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `fce7f0b49131242c` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 822 | colon written as aytham U+0B83 |
| `fce7f0b49131242c` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 45 | aa vowel sign + virama used in place of letter RA (Dinamani style, many) |
| `bdef57135256521b` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `1f1643f65832ac48` | `ind-ta-sangraha-v-train-000000` | ok |  |  | reads like machine translation from English (D4, not an audit code) |
| `5a35746dc800bb4f` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `1297cb485af98c38` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `d57442bb6952e77c` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `425cc247188aa5c6` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `4f1fe9efd8157739` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `ffb55d46588caad1` | `ind-ta-sangraha-v-train-000000` | ok |  |  | print line-break splits leave spaces inside some words (not an audit code) |
| `e7826ac76349014d` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 11 | colon written as aytham U+0B83 (2x) |
| `e7826ac76349014d` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 79 | aa vowel sign + virama used in place of letter RA (Dinamani style, many) |
| `9b9d25f0399b3420` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `44bd87d2340093b3` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 52 | colon written as aytham U+0B83 (3x) |
| `44bd87d2340093b3` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | whole doc is three site headlines, no article body |
| `e48b6cbb07f6eb5a` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | site search-results header at top |
| `f3ecbc17b07d23c6` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 619 | colon written as aytham U+0B83 |
| `f3ecbc17b07d23c6` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | site promo headline list at top |
| `eec236b8d935d765` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `86222a89371f9dcd` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `c757a33a258e836a` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 1405 | follow-us footer with site name at end |
| `dc3a561d0c82a4f3` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `495efa7591f3dabb` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 37 | Latin O-slash used as bullet, and greater-than sign used for comma (symbol font conversion) |
| `ffb2d7803e3b2bb3` | `ind-ta-sangraha-v-train-000000` | finding | A6 | 36 | aa vowel sign + virama used in place of letter RA (Dinamani style, many) |
| `f6ba971c8801fe73` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `eecbfaa56e391d60` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 153 | colon written as aytham U+0B83 |
| `eecbfaa56e391d60` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 2073 | English comment-policy disclaimer with site name at end |
| `e23b0e89137e672a` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 4921 | line starts mid-word, text between pages missing (book scan) |
| `e23b0e89137e672a` | `ind-ta-sangraha-v-train-000000` | finding | G3 | 9076 | stops mid-sentence at the end |
| `e23b0e89137e672a` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 141 | colon written as aytham U+0B83 (39x) |
| `6eb999128097f2f2` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `365d3f0224114090` | `ind-ta-sangraha-v-train-000000` | finding | G4 | 673 | colon written as aytham U+0B83 |
| `365d3f0224114090` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | site promo headline list at top |
| `7634542215044266` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `691f87642f9b54a9` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | site latest-headlines list with timestamps at top |
| `2c83118845909c00` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |
| `74918202132b4a5f` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | SEO keyword list with site name at top |
| `74918202132b4a5f` | `ind-ta-sangraha-v-train-000000` | finding | D2 | 84 | romanised Tamil words inside the keyword list |
| `1dd163640a70e90c` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 0 | site promo headline list at top |
| `1dd163640a70e90c` | `ind-ta-sangraha-v-train-000000` | finding | C1 | 1349 | English teaser line at end |
| `b56f9a2f945427b1` | `ind-ta-sangraha-v-train-000000` | ok |  |  |  |

## Summary

- Documents read: 50
- ok: 26
- With a finding: 24
- Codes found: G3 (4), G4 (12), A6 (6), C1 (16), D2 (1)
