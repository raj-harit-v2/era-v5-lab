# Kannada reader audit, day D5 (Thu 19 Nov)

Issue #528. Documents drawn with `random.Random(5).sample(range(n), 25)` from each of `ind-kn-fw2-train-000000` and `ind-kn-sangraha-v-train-000000`, decoded with the frozen tokenizer p1536. Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `f6cca908158eabe1` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `fdb866ae9a8f65a0` | `ind-kn-fw2-train-000000` | finding | C1 | 0 | site name prefix at top |
| `14cd6184e5a7c002` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `4e537ea40f7108ed` | `ind-kn-fw2-train-000000` | finding | C1 | 1972 | site about-us footer, Kannada then English |
| `42f8f2eca7010b37` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `631fda82a5ee70fc` | `ind-kn-fw2-train-000000` | ok |  |  | phone masked by clean |
| `1cb776b17dd3077d` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `f007b1e1ff131f59` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `93f6406a6abb5a3d` | `ind-kn-fw2-train-000000` | finding | C1 | 1338 | page timestamp line at end |
| `7734f0de1ce05623` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `69167eb49ba38c15` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `213ae824d6bf1f20` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `0c2721e31ecca8d8` | `ind-kn-fw2-train-000000` | finding | C1 | 0 | search-results listing page, not one article |
| `0c2721e31ecca8d8` | `ind-kn-fw2-train-000000` | finding | C1 | 1974 | English headlines. |
| `b8459c46b827b91e` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `01d991c094ee398d` | `ind-kn-fw2-train-000000` | ok |  |  | two unrelated stories joined |
| `af6942924c91b084` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `d4fc8c482723c71d` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `4d067af590a6832e` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `56b7965a9fcc13cd` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `3a1efec8d9561f73` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `a2b2e065314ba1a8` | `ind-kn-fw2-train-000000` | finding | G3 | 0 | starts mid-sentence, opening cut |
| `045d4ac57a8262c1` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `b2f4162ff509d53e` | `ind-kn-fw2-train-000000` | finding | A6 | 692 | Latin A for anusvara inside a word (font conversion) |
| `c0470ff127645c8a` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `4a59a8daf84d9a04` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `7a3b8371b18dc59d` | `ind-kn-sangraha-v-train-000000` | ok |  |  | clean removed related-links header (265 chars), correct |
| `4d2866e940c52ed1` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `d751f381f7a6f49b` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `18e9c467232788ff` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `e6f5a0c6e6e6f125` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 0 | English category label line at top |
| `8482ede231b97ad5` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `92f8bcadd2b6be16` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `4bbc424a83bfb5c2` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `53cbe23d41dbffc1` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 0 | OCR running page header, spaced letters |
| `53cbe23d41dbffc1` | `ind-kn-sangraha-v-train-000000` | finding | G1 | 1132 | OCR: vowel sign after a space, letter lost |
| `53cbe23d41dbffc1` | `ind-kn-sangraha-v-train-000000` | finding | G1 | 2923 | OCR: vowel sign after a space, letter lost |
| `53cbe23d41dbffc1` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 2465 | Looks to be OCR header |
| `e19a25195805d288` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 0 | headline list only, no article |
| `5226803c91fd1742` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `db7d221a2a9b4e4f` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `f66fe9b66220a20d` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 0 | list of unrelated news teasers, no article |
| `9bc8e4bdd09953a8` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `ba14f57e425e5598` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `5915342d3d8acd19` | `ind-kn-sangraha-v-train-000000` | finding | A6 | 7419 | Latin t inside a Kannada word |
| `5915342d3d8acd19` | `ind-kn-sangraha-v-train-000000` | finding | D1 | 4741 | long English translation blocks, ~30% of letters |
| `5915342d3d8acd19` | `ind-kn-sangraha-v-train-000000` | finding | G3 | 0 | Abrupt start from middle |
| `5915342d3d8acd19` | `ind-kn-sangraha-v-train-000000` | finding | A6 | 2514 | Latin ss for avagraha, missed by clean |
| `e43f1cfd70645433` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 0 | hashtag tag glued to the headline |
| `af47c6e98691b3f5` | `ind-kn-sangraha-v-train-000000` | ok |  |  | clean removed follow-us line at end, correct |
| `7d352831fe613649` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `9cf81d9dd13710c2` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `31806e8a84b5c2b9` | `ind-kn-sangraha-v-train-000000` | ok |  |  | clean removed related-links header (310 chars), correct |
| `9626855fb4354d74` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 1815 | read-also link and English tag line at end |
| `97e956d81ddc2320` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `b3a53ae36384a3b0` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 1045 | related headlines left; clean removed only the last |
| `9af18f07a6440d93` | `ind-kn-sangraha-v-train-000000` | ok |  |  | email masked; reader comments after the article |

## Summary

- Documents read: 50
- ok: 36
- With a finding: 14
- Codes found: A6 (3), C1 (13), D1 (1), G1 (2), G3 (2)
