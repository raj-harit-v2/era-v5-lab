# Kannada reader audit, day D6 (Fri 20 Nov)

Issue #528. Documents drawn with `random.Random(6).sample(range(n), 25)` from each of `ind-kn-fw2-train-000000` and `ind-kn-sangraha-v-train-000000`, decoded with the frozen tokenizer p1536. Codes from `diagnosis/DISEASES.md`; `offset` is the character offset in the decoded text.

| doc_id | shard | verdict | code | offset | note |
|---|---|---|---|---|---|
| `ab81f5685dcba16c` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `504e6b2c16bacdb2` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `c192ff407f81a979` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `0eae2271578db989` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `d17c1328b4eacc26` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `ada376863f7d378b` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `a4f23033716bcec4` | `ind-kn-fw2-train-000000` | finding | C1 | 0 | related-links menu at top, not removed by clean |
| `8a936cc99b3be8a4` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `41bbfb7bc6f80dac` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `df9fa8312cf929a2` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `9eecba027137f9a4` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `b30ad084fe4b359a` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `e98f6d5815e41dce` | `ind-kn-fw2-train-000000` | finding | C1 | 0 | relative timestamp line at top |
| `1548d15e601b486b` | `ind-kn-fw2-train-000000` | finding | C1 | 0 | latest-news label and date line at top |
| `3faa9600dab5dbe7` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `4e0499e6fe04d5ef` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `a4810e2ce45188d6` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `ef2cbb24f9bcd4b3` | `ind-kn-fw2-train-000000` | finding | C1 | 1712 | read-also link at end |
| `2bcc8f1dfbfa6308` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `cf9a0a1aca5c8266` | `ind-kn-fw2-train-000000` | finding | A6 | 411 | Latin-1 symbols inside a Kannada word (broken encoding) |
| `cf9a0a1aca5c8266` | `ind-kn-fw2-train-000000` | finding | C1 | 1095 | ad block, then top-news and more-news lists |
| `5871c61d5f76e8a3` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `9581eb7ce8af876c` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `bcc4d2c47010f521` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `08fd07944e9482e5` | `ind-kn-fw2-train-000000` | ok |  |  |  |
| `c1abd8dde50e7702` | `ind-kn-fw2-train-000000` | finding | C1 | 515 | top-news and more-news lists at end |
| `c1abd8dde50e7702` | `ind-kn-fw2-train-000000` | finding | C1 | 22 | Source name and date |
| `00a66b88258331e1` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `f18429fe501ab198` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `e50ca973b3a44406` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 1962 | related headline with English slug at end |
| `ca5d6381bb99717c` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `08eec45c5112a4e1` | `ind-kn-sangraha-v-train-000000` | ok |  |  | clean fixed Kannada zero used as anusvara, correct |
| `e32b234e11ef163a` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 0 | site URL prefix before each short story |
| `a64817f18003cb4b` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `29a10f74b8ba2e5c` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `7bec847c5083a812` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `3421de80008bd39f` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `8037e3835a2a7607` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `cb2f6d72afd45693` | `ind-kn-sangraha-v-train-000000` | ok |  |  | clean fixed Kannada zero used as anusvara, correct |
| `91f6d163e332e79d` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `136aef2b5c250731` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `24d63eabb7875a39` | `ind-kn-sangraha-v-train-000000` | ok |  |  | clean fixed Kannada zero used as anusvara, correct |
| `27144f3a00f4aa21` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `6f5a20f7c8ad3be9` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `a8a3eac50edc0d27` | `ind-kn-sangraha-v-train-000000` | finding | G3 | 0 | starts mid-article, opening cut |
| `31273b4045e78e8d` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `4e43f29da42baa17` | `ind-kn-sangraha-v-train-000000` | finding | A6 | 0 | Telugu-script title line in Kannada text |
| `979976d993252fad` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 737 | read-also stub left after clean removed the tail |
| `57242f7c17621305` | `ind-kn-sangraha-v-train-000000` | ok |  |  | clean fixed Kannada zero used as anusvara, correct |
| `d30e463a387e4988` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |
| `aca7bce465a4704d` | `ind-kn-sangraha-v-train-000000` | finding | C1 | 394 | English system-generated disclaimer at end |
| `7fb225efa83a0137` | `ind-kn-sangraha-v-train-000000` | ok |  |  |  |

## Summary

- Documents read: 50
- ok: 38
- With a finding: 12
- Codes found: A6 (2), C1 (11), G3 (1)
