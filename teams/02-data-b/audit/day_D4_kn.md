# Kannada reader audit, day D4 (Wed 18 Nov)

Issue #528. Documents drawn with `random.Random(4).sample(range(n), 25)` from each of `ind-kn-fw2-train-000000` and `ind-kn-sangraha-v-train-000000`, decoded with the frozen tokenizer p1536. Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `9a458f2e6d9d43cd` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `4857246800835988` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `b54bcce8c4c72da5` | `ind-kn-fw2-train-000000` | finding | C1 | 0 | site trending-headlines list at top |
| `7e34246db19481e6` | `ind-kn-fw2-train-000000` | finding | C1 | 0 | site trending-headlines list at top |
| `5ab60e392fee772f` | `ind-kn-fw2-train-000000` | finding | C1 | 4129 | read-in-English link line |
| `5ab60e392fee772f` | `ind-kn-fw2-train-000000` | finding | C1 | 25 | English horoscope title in heading |
| `ba923d4befbe4b43` | `ind-kn-fw2-train-000000` | finding | C1 | 945 | WordPress poll shortcode at end |
| `6e970082d76cddb3` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `e051465d3c396043` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `459551715a162e74` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `54229ca98d5ac87c` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `b2c7cc8833908d9d` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `fd90bae390ec4f6d` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `7b9878d13b64e67b` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `82ccc5ed747af539` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `469acae046868c62` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `ade7e0fd86e84327` | `ind-kn-fw2-train-000000` | finding | C1 | 571 | English comment policy footer |
| `f42c7a5216544044` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `10a574c17a774790` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `5f5d4690bd5d601e` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `f9f49e8cdf04e792` | `ind-kn-fw2-train-000000` | finding | C1 | 0 | latest-news headline list at top |
| `3d5d5feeaef6de23` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `b5c875597344b331` | `ind-kn-fw2-train-000000` | finding | A6 | 803 | Latin c-cedilla inside a Kannada name (font conversion) |
| `b5c875597344b331` | `ind-kn-fw2-train-000000` | finding | A6 | 1149 | Latin o-umlaut inside a Kannada name (font conversion) |
| `13e0fc00347cbc76` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `c538752d2322a54c` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `206ff97418e30518` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `319a8c3f0eab0579` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `c19b266510bac049` | `ind-kn-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-word, opening cut |
| `0e1d4fa2278d4532` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `33030274ce77a8f9` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `1d91cadee4127615` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `87ef9addb2473fb0` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `702d9a3bef134197` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `4e7637264ad575d4` | `ind-kn-sangraha-v-train-000000` | ok |  |  | one English sentence (caption?) at 139 |
| `c2387e27cf06cb70` | `ind-kn-sangraha-v-train-000000` | finding | G1 | 1661 | vowel sign after a space, letter lost |
| `a5275166d19f4d05` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 0 | related-links list at the top |
| `1ecdab889fa23b7b` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `8ca38ec6b764b636` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `93a79affedf3721d` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `227bed3d888719ff` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `d43feec500cf1934` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `a2082ab9722a8c6b` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `74aac5c212f58ea9` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 0 | site name line at the top |
| `6942cd88fd0906ac` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `6b6d63ec997a6623` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `390aaa25b2730ee1` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `25362cbdc390f68c` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 0 | JSON-LD page metadata, not prose |
| `f11f5fe8449627e5` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `8024e6469e4e409d` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `3ee871915ed321b8` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `f2e76a31d95b5c8a` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |

## Summary

- Documents read: 50
- ok: 38
- With a finding: 12
- Codes found: A6 (2), C1 (10), G1 (1), G3 (1)
