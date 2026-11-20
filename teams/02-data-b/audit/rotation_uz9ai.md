# Kannada shard rotation audit: uz9ai

## Scope and method

- Shard: `shards/ind-kn-sangraha-v-train-000000.bin`
- Frozen tokenizer: `p1536_tokenizer.json`
- Documents in shard: 8354
- Payload tokens: 4761130
- Mode: deterministic samples
- Deterministic seeds: 4, 5
- Sample size per seed: 50
- Sample draws: 100
- Unique documents checked: 100
- Offsets are zero-based Unicode code-point offsets in decoded shard text.
- Hex dumps contain the finding and at most three code points on each side. No document text is included.

The script imports `read_shard()` from `indic_audit.py`, validates the shard through that reader, and batch-decodes the complete shard with the frozen tokenizer. Deterministic sample selection is applied before the code-point checks. Joiners are counted with PyArrow kernels. There is no Python loop over tokens.

<details><summary>Documents checked (shard row: doc_id)</summary>

- `3867: 319a8c3f0eab0579`
- `4969: c19b266510bac049`
- `1690: 0e1d4fa2278d4532`
- `6489: 33030274ce77a8f9`
- `7845: 1d91cadee4127615`
- `2539: 87ef9addb2473fb0`
- `1476: 702d9a3bef134197`
- `1089: 4e7637264ad575d4`
- `324: c2387e27cf06cb70`
- `6579: a5275166d19f4d05`
- `4741: 1ecdab889fa23b7b`
- `964: 8ca38ec6b764b636`
- `3636: 93a79affedf3721d`
- `5902: 227bed3d888719ff`
- `4533: d43feec500cf1934`
- `2828: a2082ab9722a8c6b`
- `1739: 74aac5c212f58ea9`
- `4288: 6942cd88fd0906ac`
- `3512: 6b6d63ec997a6623`
- `420: 390aaa25b2730ee1`
- `4264: 25362cbdc390f68c`
- `4452: f11f5fe8449627e5`
- `3169: 8024e6469e4e409d`
- `2700: 3ee871915ed321b8`
- `5076: f2e76a31d95b5c8a`
- `4745: d5317b7f3b9de67d`
- `6101: d0b9b504e44217e6`
- `1420: 82b3ddb0155dc49c`
- `5528: d461a90bc7d6b79c`
- `6355: a735569a7a50a6ce`
- `8289: fdbebf9842597461`
- `4077: cc7924c6207f45fb`
- `2912: 83b71d47ab04defe`
- `4052: 13da24cd4676ded5`
- `7759: abbfb95df2528bfc`
- `4587: 0e28b2de6e6b195f`
- `1463: 6f0049059ffc5360`
- `4919: bd08f31338f4f0bd`
- `118: 8a6d63dde6d6234e`
- `4783: 7ee11b32730dfe0e`
- `5107: 187ed7edcd63462e`
- `8329: 530f88b30e965d97`
- `3196: d8ab107efcf735d6`
- `6782: 6b221f647cad3e84`
- `6942: 5e96eaad685c3294`
- `4721: db16df9163020ee5`
- `7062: 1d8385ced3a2d5dd`
- `7395: bcce64694bb74c5c`
- `2643: 2925311d5722dd30`
- `3821: 223b2abbef24a3d4`
- `4185: 7a3b8371b18dc59d`
- `5874: 4d2866e940c52ed1`
- `475: d751f381f7a6f49b`
- `7628: 18e9c467232788ff`
- `4080: e6f5a0c6e6e6f125`
- `849: 8482ede231b97ad5`
- `2569: 92f8bcadd2b6be16`
- `1854: 4bbc424a83bfb5c2`
- `6091: 53cbe23d41dbffc1`
- `7685: e19a25195805d288`
- `4039: 5226803c91fd1742`
- `6238: db7d221a2a9b4e4f`
- `1670: f66fe9b66220a20d`
- `4085: 9bc8e4bdd09953a8`
- `214: ba14f57e425e5598`
- `3550: 5915342d3d8acd19`
- `6687: e43f1cfd70645433`
- `4579: af47c6e98691b3f5`
- `2983: 7d352831fe613649`
- `6380: 9cf81d9dd13710c2`
- `2614: 31806e8a84b5c2b9`
- `1178: 9626855fb4354d74`
- `2273: 97e956d81ddc2320`
- `7288: b3a53ae36384a3b0`
- `2075: 9af18f07a6440d93`
- `2166: 149d3704f01d5ad7`
- `29: a86b514d69a2e904`
- `87: 9ef780ceb6ad0322`
- `3431: 9df33c67dc6b125b`
- `3530: 18af4e941c20f1df`
- `2717: 513cd36e759442d0`
- `2727: aaac395761dd0ded`
- `4739: 49fcdcf6346116e1`
- `5138: b4c3783579f43b0b`
- `3258: 3b96b40b4788c3e9`
- `3355: 4d29ecd4881a5b9c`
- `2976: c8cb636c9387a257`
- `3225: a722ffaff1ae1685`
- `6278: 2ab86082e9a0adfb`
- `4895: e07e3d28940245bf`
- `353: e6147baceba768fb`
- `5917: 793470eaac955c4a`
- `6797: 16a019e921a6e1a6`
- `2719: 5ff6aca9b19459bd`
- `2387: 9b7a3d25024ec1ff`
- `4322: 1e4bc782c4a3d63d`
- `1067: a998fc5b64c5186a`
- `5437: 7ae0c9c121d5a6ed`
- `4937: b42f191255857053`
- `55: 95016e206d6aad48`

</details>

## Input integrity

All hashes matched the shard manifest.

| input | SHA-256 |
|---|---|
| payload | `8d978e3e1929ceb920091cc1159c3c29d0d1e24fa11ec0ebaedf68114db8949a` |
| index | `329ff1329124e6baa6c679166c88f8ae2a1f031dd4bbe747d59d493641c1e56b` |
| document metadata | `0c58172b60a564af154c7702d81c009eda5819732d2f2c971ef10cc8f8e9824f` |
| quality report | `679637d7deacced657a008b5186f111ab2dcd48bbeec2d206c4c37fb1f626167` |
| tokenizer | `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |

## Joiner counts

| day/seed | documents drawn | ZWJ (U+200D) | ZWNJ (U+200C) |
| ---: | ---: | ---: | ---: |
| 4 | 50 | 0 | 0 |
| 5 | 50 | 0 | 0 |
| unique | 100 | 0 | 0 |

The `unique` row de-duplicates documents selected by more than one seed. Day rows represent each reproducible draw independently.

## Findings

| doc_id | code | offset | hex dump | note |
| --- | --- | ---: | --- | --- |
| c2387e27cf06cb70 | G1 | 1661 | `U+0CCD U+0CAE U+0020 U+0CBE U+0CAA U+0CCD U+0CA4` | Kannada vowel sign after U+0020 |
| abbfb95df2528bfc | A6 | 2062 | `U+0CCD U+0C9F U+0CBF U+007A U+0CB0 U+0CC6 U+002E` | non-Kannada letter run beginning U+007A inside Kannada word |
| 53cbe23d41dbffc1 | G1 | 1132 | `U+000A U+0CB0 U+0020 U+0CC1 U+0020 U+0CA8 U+0CBE` | Kannada vowel sign after U+0020 |
| 53cbe23d41dbffc1 | G1 | 2923 | `U+0020 U+0CB5 U+0020 U+0CC1 U+0C96 U+0CA6 U+0CB2` | Kannada vowel sign after U+0020 |
| 5915342d3d8acd19 | A6 | 2514 | `U+0C8F U+0CB5 U+0CBE U+0073 U+0073 U+0CB5 U+0CC3` | non-Kannada letter run beginning U+0073 inside Kannada word |
| 5915342d3d8acd19 | A6 | 7419 | `U+0CAE U+0C82 U+0CA4 U+0074 U+0020 U+0CAA U+0CCD` | non-Kannada letter run beginning U+0074 inside Kannada word |
| e43f1cfd70645433 | A6 | 19 | `U+0079 U+0061 U+0020 U+0053 U+0061 U+006D U+006D` | non-Kannada letter run beginning U+0053 inside Kannada word |
| 18af4e941c20f1df | A6 | 53 | `U+0020 U+0CB8 U+0CC1 U+007A U+0CBF U+0020 U+0C9C` | non-Kannada letter run beginning U+007A inside Kannada word |
| 18af4e941c20f1df | G1 | 54 | `U+0CB8 U+0CC1 U+007A U+0CBF U+0020 U+0C9C U+0CCA` | Kannada vowel sign after U+007A |

Summary: 9 findings in 6 documents. G1: 4, G2: 0, A1: 0, A4: 0, A6: 5.

The cleaned shard can show joiner counts and malformed joiner positions. Establishing that a joiner was lost requires raw pre-cleaning text; the before/after comparison is covered separately by `indic_audit.py`.

## Reproduction evidence

Command:

```console
uv run python rotation_uz9ai.py --shard shards/ind-kn-sangraha-v-train-000000.bin --tokenizer p1536_tokenizer.json --days 4 5 --sample-size 50 --out rotation_uz9ai.md
```

Final output lines:

```text
mode=sample sample_draws=100 unique_documents=100
checked_zwj=0 checked_zwnj=0
findings=9 documents_with_findings=6
findings_by_code=G1:4,G2:0,A1:0,A4:0,A6:5
report=rotation_uz9ai.md
audit_wall_time_seconds=2.815
```

Audit wall time reported by the script: 2.815 seconds.
