# Data B rotation, week 3: R1 and R2 on ind-hi-fw2 (rjvim)
 
Closes #532. Rotation member: rjvim (Rajiv Seelam). Language: Hindi (I read Hindi).
 
## What was checked
 
| Item | Value |
|---|---|
| Shard | `ind-hi-fw2-train-000000` (TSAI's list in G, 16 Nov) |
| Payload sha256 | `e64b18601f2ffc82cfeaca78c864cead9aab62b0747adf62c38a1d891613a13b` (matches the manifest) |
| Tokenizer | frozen p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`, tokenizers 0.23.3 |
| Documents in shard | 13,773 (header, index and EOS 130822 checks pass, as in `read_shard` of `indic_audit.py`) |
| Sample | DAY 4: `random.Random(4).sample(range(13773), 50)`, the sampler in #532 |
| Checks | G1, G2, A1, A4, A6 by code point (definitions in #532), plus VV (two dependent vowel signs in a row) and NFC |
| Wall time | 0.6 s for decode + all checks (one process, batched decode, regex per document) |
 
Every sampled document was also read in full for script damage. Document text is not reproduced here: only IDs, codes, offsets and code points.
 
## R1: results on 50 documents
 
| Code | Findings | Documents |
|---|---|---|
| G1 vowel sign after a space | 2 | 1 |
| G2 ZWJ/ZWNJ at word edge or doubled | 0 | 0 |
| A1 invisible characters | 0 | 0 |
| A4 U+FFFD | 0 | 0 |
| A6 Latin or other script inside a Hindi word | 0 | 0 |
| VV two vowel signs in a row (extra) | 4 | 2 |
 
- ZWJ (U+200D) and ZWNJ (U+200C): 0 of each in the 50 documents, so there is nothing to lose here. Hindi news text rarely uses them.
- NFC: all 50 documents are already NFC.
- No damage looks like it came from cleaning or tokenizing. The decode round trip is exact (ids to text), and the findings are spellings that are typical of the source (legacy font conversion or typing).
 
## R2: findings with doc ID and hex dump
 
Offsets are in code points of the decoded document. The hex dump is the finding plus three code points on each side.
 
| doc_id | code | offset | hex dump | note |
|---|---|---|---|---|
| 0bfc994afef6284a | G1 | 1911 | U+0915 U+0947 U+0020 **U+093F** U+092A U+094D U+0930 | vowel sign I after a space, detached from its consonant (legacy font conversion) |
| 0bfc994afef6284a | G1 | 1932 | U+093E U+0935 U+0020 **U+093F** U+092E U+093F U+0932 | same: stray U+093F before the next word |
| 16ce3772b144cbf5 | VV | 81 | U+0020 U+0938 U+0947 **U+093E** U+091A U+093E U+0020 | E sign + AA sign typed for O sign (U+094B); renders almost the same, different ids |
| 16ce3772b144cbf5 | VV | 501 | U+0940 U+0932 U+093E **U+0945** U+091C U+0020 U+0938 | AA + candra E typed for candra O (U+0949) in an English loanword |
| f19893e2b35b88ae | VV | 194 | U+0020 U+0932 U+093E **U+0945** U+0915 U+0921 U+093E | same AA + candra E for candra O (U+0949), same loanword |
| f19893e2b35b88ae | VV | 1028 | U+0020 U+0932 U+093E **U+0945** U+0915 U+0921 U+093E | same word, second time |
 
## Other notes from reading (not code-point findings)
 
- Two of the 50 documents are mostly English in a Hindi pack: `85f0bdbed83b462d` (exam question in English, then its Hindi translation) and `3dd47ddb3292b08b` (an English press release, about 37% of its characters are Devanagari). Language label issue (D1 territory), not script damage.
- `8cbbbf6ace045c7a` and `edf5c0290a02098a` start with web boilerplate in English (visitor counter, search-result header). Boilerplate, not damage.
 
## Summary
 
Documents checked: 50 (DAY 4). Findings: G1 2, G2 0, A1 0, A4 0, A6 0 (plus VV 4). Documents with a finding: 3 of 50. 0 ZWJ/ZWNJ changes possible (none present), 0 replacement characters, 0 invisible characters. The G1 and VV cases are spelling damage from the source, not from clean.py or p1536. Suggestion for a later rule (not applied): fold U+0947 U+093E → U+094B and U+093E U+0945 → U+0949 only after a gold-set harm test, since these change token ids.
 
## Command
 
```
python3 -I r1.py <dir with shard + tokenizer> 4
{"G1": 2, "G2": 0, "A1": 0, "A4": 0, "A6": 0, "VV": 4} nfc_bad 0 zwj 0 zwnj 0 wall 0.6
```
