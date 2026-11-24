# Decontamination check of the first training shards (week 3, task 2)

Team 9 (Evaluation), week-3 task 2. Gate 3 evidence: "the first shards have zero fingerprint hits".

**Result: 0 flagged documents and 0 canary hits in all 41 shards (1,200,725 documents, 1,009,387,985 tokens).**

- **Owner:** `raghavTayal`. Assigned by the Team 9 lead in G9 (14 Nov; confirmed 18 Nov).
- **Shards:** the 41 p1536 sample-v0 train shards from TSAI's 16 Nov notice, which TSAI confirmed are the first shards for
  Gate 3 (G9, 17 Nov). One shard per sample-v0 train part, after `clean.py` and F2. Seven parts have no shard yet (no
  cleaner rules) and held-out parts are not sharded, as the notice says.
- **Chain:** [`decode_shard.py`](../decontam/decode_shard.py) (p1536) → [`decontam_check.py`](../decontam/decontam_check.py)
  (fingerprints v2, full set: no `--benchmarks`, `--tags` or `--exclude`) → [`canary_scan.py`](../decontam/canary_scan.py).
- **Repo commit:** `8732384` (main, 17 Nov). The decontam scripts are unchanged on main up to `431f9b3` (18 Nov).
- **Tokenizer:** frozen p1536, sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`; every shard's
  manifest names it.
- **Fingerprint set:** v2, `set_sha256 2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`, scope `full set`
  (the same line on all 41 runs).
- **Canaries:** 4 checked on every shard (`era-v5-lab`, `gpqa_diamond`, `hle`, `terminal_bench_2`).
- **Run:** 17 Nov 2026, 16:33–18:14 UTC, laptop CPU (Apple Silicon), 3 shards at a time.

## Per shard

| # | shard_id | payload_sha256 | docs | tokens | flagged | canary hits |
|---:|---|---|---:|---:|---:|---:|
| 1 | `code-cpp-train-000000` | `511b3e97a96627c2ac71c6772b0a91fa05522dff1467d3248d295269bcfb1761` | 40,355 | 66,915,318 | 0 | 0 |
| 2 | `code-cpp-train-000001` | `161b269499bf813885d0b68fac55c8b31afa546ddee698a76d28f3bbb356d5cb` | 14,145 | 23,634,925 | 0 | 0 |
| 3 | `code-go-train-000000` | `b68bf390d5800853f476ede764289f045993384fd6c771db0739b74adcc5b500` | 56,588 | 56,698,571 | 0 | 0 |
| 4 | `code-go-train-000001` | `36430989fd7f5caf0f4e22ab1a88b730ca3b901eec537a5ab286d4b3c766fadd` | 20,213 | 20,255,694 | 0 | 0 |
| 5 | `code-java-train-000000` | `d885478b8a77ebfec35d9525d35a2f479e38f2b475f1167215c64b2ec5bec2dd` | 62,421 | 56,003,499 | 0 | 0 |
| 6 | `code-java-train-000001` | `c8e3aca96a7f6c16047b187caec4d09b0fdfab2eb4ec13ca2120e0c680f18c14` | 22,228 | 19,878,065 | 0 | 0 |
| 7 | `code-js-ts-train-000000` | `61d72a9aa9c8078e9e5a621fe497244fb7699dbe855bf8793a2b0631a23e605a` | 85,508 | 58,203,242 | 0 | 0 |
| 8 | `code-js-ts-train-000001` | `62e7aa3793863ace476e851aa89e0e4ffbd007eff5b7c2ebdb05fd1c1a355418` | 30,441 | 20,653,602 | 0 | 0 |
| 9 | `code-python-train-000000` | `bf6c275f296566cb88eb5e732238c1744c3294cbc8a47502a1ebfb06685b7900` | 53,221 | 60,537,332 | 0 | 0 |
| 10 | `code-python-train-000001` | `537723be5641f3aedab93695cb85f98c4b2259bb71300c9fb55bcc41ed2019d6` | 19,116 | 21,509,045 | 0 | 0 |
| 11 | `code-rust-train-000000` | `9468c56cccae9055e00dc2a530be2e1732b4798d1025611bc1ec438c1727278b` | 43,116 | 59,530,999 | 0 | 0 |
| 12 | `code-rust-train-000001` | `b747ac07155d28fb9cb70871bfaddbbbe446c1806e375ff52ba20ee7444b93e1` | 15,028 | 21,040,035 | 0 | 0 |
| 13 | `en-dclm-train-000000` | `1fccdcc4c15bb22ea564c8d3f1850582abd8b60e6c504386ee84308f6ee074de` | 45,032 | 53,960,422 | 0 | 0 |
| 14 | `en-dclm-train-000001` | `2b6e1f71836f08242e4d9f5c3ef9cf217617a125eb516849886360347b321f7b` | 14,735 | 17,781,210 | 0 | 0 |
| 15 | `en-fineweb-edu-train-000000` | `6625fc47c89e34bf2242a2c747c7e1f9b3583234e45e13e3a653b265007aca07` | 53,444 | 52,995,687 | 0 | 0 |
| 16 | `en-fineweb-edu-train-000001` | `f1b97344614f7f54b407e60602204fd8313b83565de817cdf75b2cd6990a55ef` | 17,725 | 17,662,417 | 0 | 0 |
| 17 | `en-nemotroncc-synth-train-000000` | `2be6f68c01d036a9e27ee3cc16d1ce02e8bf9adcd33f4f949baf48986144e278` | 146,778 | 50,712,366 | 0 | 0 |
| 18 | `en-nemotroncc-synth-train-000001` | `2d041dc03bfbaabb3b6be8c43abe8122d012a0006ef1325f6fea57513f3eda34` | 49,008 | 16,961,507 | 0 | 0 |
| 19 | `en-nemotroncc-train-000000` | `3b64c48e320d38c58ae3e8114cdb26fabb71f387131ddebd5453184128ae2ce0` | 65,284 | 50,343,044 | 0 | 0 |
| 20 | `en-nemotroncc-train-000001` | `a7b14cbbbfc45f81aa1f881c1da97d97d3ce656018073c869435423b61095a42` | 21,912 | 16,778,602 | 0 | 0 |
| 21 | `ind-bn-fw2-train-000000` | `ecf0822aca757724ac6b72d06af70c58350caffd848de126798b761a62f845ba` | 10,704 | 7,127,920 | 0 | 0 |
| 22 | `ind-bn-sangraha-v-train-000000` | `dec1b695aca02613d958a232c760f09e77127ba4d680920c1284d8feba8f834d` | 10,112 | 8,014,810 | 0 | 0 |
| 23 | `ind-gu-fw2-train-000000` | `d10b573a08bcecf70cc8a8e193fefbcd502a50b9fa3c17c37fb006dbd8d41f5f` | 22,689 | 16,066,252 | 0 | 0 |
| 24 | `ind-hi-fw2-train-000000` | `e64b18601f2ffc82cfeaca78c864cead9aab62b0747adf62c38a1d891613a13b` | 13,773 | 8,988,818 | 0 | 0 |
| 25 | `ind-hi-hplt-train-000000` | `e7e357d21beceacab190959591e68e9b00e24729fd098b87be0a28c4cdf95d46` | 8,386 | 8,090,716 | 0 | 0 |
| 26 | `ind-hi-indiccorp-train-000000` | `6be0f58e567a0f8a45eb2891aeadacbeb43d570e988355c5f15efa576f0764db` | 109,668 | 9,343,359 | 0 | 0 |
| 27 | `ind-hi-sangraha-s-train-000000` | `4b92b39b427566809d1653f1b81b35b274c2a6c7de99c3b4f8a9d5b017bb5561` | 7,467 | 5,988,971 | 0 | 0 |
| 28 | `ind-hi-sangraha-v-train-000000` | `78aca29173b76840de617be0b1335b9417a340adce7b0b0564b23e195b919ab1` | 14,483 | 9,254,413 | 0 | 0 |
| 29 | `ind-kn-fw2-train-000000` | `7224b101435879f73f07b17e5156919aa225376d1636bb622cb4ec80540a8126` | 7,735 | 4,737,714 | 0 | 0 |
| 30 | `ind-kn-sangraha-s-train-000000` | `41fe68ef433fe8612de02c9b30d846b58597f4e46ee456b806a03355421dce7e` | 5,185 | 5,217,346 | 0 | 0 |
| 31 | `ind-kn-sangraha-v-train-000000` | `8d978e3e1929ceb920091cc1159c3c29d0d1e24fa11ec0ebaedf68114db8949a` | 8,354 | 4,761,130 | 0 | 0 |
| 32 | `ind-mr-fw2-train-000000` | `c6aa0cf3adb8e3f01741ad41cab255d033ac47a802040bd6ce60fe5a61681be4` | 11,250 | 7,146,419 | 0 | 0 |
| 33 | `ind-mr-sangraha-v-train-000000` | `043e1ff61f9f7db24600f13e63c62605671925dbdebcbfa59984908e6e0b3742` | 12,164 | 7,259,040 | 0 | 0 |
| 34 | `ind-sa-fw2-train-000000` | `a6d8546c5f48e7e1388edc441b48b409e29be870b79fd61ee6624f930ba7dab5` | 5,667 | 13,940,676 | 0 | 0 |
| 35 | `ind-ta-sangraha-v-train-000000` | `418b46986e796f806d520b883091af93be976a068554b81026f7096417b455d7` | 6,795 | 4,497,005 | 0 | 0 |
| 36 | `ind-te-fw2-train-000000` | `5a70a65df7d07063e942df6c9079217fc370cd7042230bfeeba7ed494f2721ed` | 5,670 | 4,758,086 | 0 | 0 |
| 37 | `ind-te-sangraha-s-train-000000` | `fbc93236d63888dd04421090847c98831ae033234908474e97713b87bb33bea9` | 4,419 | 4,781,160 | 0 | 0 |
| 38 | `ind-te-sangraha-v-train-000000` | `1036ff48ca9f714311ae676f8b9170cfa30ae8f94e826fb2cee03193bf811045` | 8,593 | 5,326,404 | 0 | 0 |
| 39 | `math-finemath-train-000000` | `6e84f270a53bcdd225bb2a6cd6cd053b5e8e74c3cdf93d3aa80a2606cc9597da` | 28,088 | 38,582,010 | 0 | 0 |
| 40 | `math-megamath-train-000000` | `ff5a213f47981243e42a31e3ffe6733e276181ef0e8cfb7c581f77bea6e22e57` | 17,232 | 33,979,879 | 0 | 0 |
| 41 | `sci-finepdfs-train-000000` | `e95a44b141ec04314968a54bc44e48183861fd4591197c862553a9f6d2968585` | 5,993 | 39,470,275 | 0 | 0 |
| | **total (41 shards)** | | **1,200,725** | **1,009,387,985** | **0** | **0** |

Every shard decoded as `split: train`, `dataset_version: sample`. `decontam_check.py` printed
`flagged 0 (0.00%) by benchmark {}` and `canary_scan.py` printed `with_canary 0 hits 0` for all 41.

## Hits

**None.** No benchmark item ID, document ID or offset to report, so no shard documents go to `flagged_check.md`.

## Checks on the result

A zero result is only useful if the chain would have found a leak. Four checks:

1. **Shard files match the manifests.** Before decoding, `decode_shard.py` checks each shard against its manifest and the
   writer's rules. Separately, the sha256 of every `.bin`, `.idx.npy` and `.docs.parquet` was recomputed: all 123 match,
   as do the payload sizes and the tokenizer sha256. The decoded, scanned and manifest document counts agree for every
   shard, and no decoded document is empty.
2. **The decode is exact.** 150 random documents per shard (6,150 in all) were encoded again with p1536: all 6,150 give
   exactly the token IDs in the `.bin` (final EOS excluded), and the `doc_id` order matches each `.docs.parquet`.
3. **Planted leaks are caught.** In a copy of a decoded shard (`ind-hi-indiccorp-train-000000`, 109,668 documents), text
   from 5 benchmark items (MILU, FLORES-200 ×2, LiveCodeBench, held-out G5) was inserted into 5 documents and the lab
   canary into a sixth. `decontam_check.py` flagged exactly those 6 documents, each with the planted item (the sixth as
   `era-v5-lab:canary`), and nothing else;
   `canary_scan.py` found the canary in the planted document only. The copy was then deleted.
4. **Same numbers as the second checks.** All 41 shards now have a second check: 36 in the rotation files on main
   (`results/rotation_*.md`) and the last 5 in the week-4 section below. All 41 give the same document count as this table,
   and 0 flagged, 0 canary hits. Every second check that gives a `payload_sha256` gives the same one as this table. The two
   rotation rows without one, `code-go-train-000000` and `ind-hi-sangraha-v-train-000000` (`rotation_ranjani-cse.md`), get
   their `payload_sha256` and token count in the same section; both match this table.

## Second check of the last 5 shards (week 4, task 3)

The 5 shards that no rotator had checked, from the Team 9 lead's week-4 post (G9, 21 Nov). Run by Team 9 on
23 Nov 2026, 19:52–20:10 IST, at main `e5544324`, with the same chain as above: `decode_shard.py` (frozen p1536,
sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`) → `decontam_check.py` (fingerprints v2,
`set_sha256 2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`, full set) → `canary_scan.py`
(4 canaries). Shard files from TSAI's `shard_links.tsv` of 23 Nov; `decode_shard.py` accepted every shard against its
manifest (payload, index and docs sha256, document and token counts, EOS id, tokenizer sha256), and each decoded as
`split: train`, `dataset_version: sample`.

| shard_id | payload_sha256 | docs | tokens | flagged | canary hits |
|---|---|---:|---:|---:|---:|
| `code-cpp-train-000000` | `511b3e97a96627c2ac71c6772b0a91fa05522dff1467d3248d295269bcfb1761` | 40,355 | 66,915,318 | 0 | 0 |
| `code-rust-train-000001` | `b747ac07155d28fb9cb70871bfaddbbbe446c1806e375ff52ba20ee7444b93e1` | 15,028 | 21,040,035 | 0 | 0 |
| `ind-gu-fw2-train-000000` | `d10b573a08bcecf70cc8a8e193fefbcd502a50b9fa3c17c37fb006dbd8d41f5f` | 22,689 | 16,066,252 | 0 | 0 |
| `ind-kn-sangraha-v-train-000000` | `8d978e3e1929ceb920091cc1159c3c29d0d1e24fa11ec0ebaedf68114db8949a` | 8,354 | 4,761,130 | 0 | 0 |
| `ind-mr-sangraha-v-train-000000` | `043e1ff61f9f7db24600f13e63c62605671925dbdebcbfa59984908e6e0b3742` | 12,164 | 7,259,040 | 0 | 0 |

All 5 have the same `payload_sha256`, documents and tokens as the per-shard table above. `decontam_check.py` printed
`flagged 0 (0.00%) by benchmark {}` and `canary_scan.py` printed `with_canary 0 hits 0` for each, so there are no hits
to report.

**Payload hash and token count for two rotation rows.** `rotation_ranjani-cse.md` has the documents scanned, 0 flagged,
the `set_sha256` and 0 canary hits for these two; it lacks only the `payload_sha256` and the token count. Same run
and chain:

| shard_id | payload_sha256 | docs | tokens | flagged | canary hits |
|---|---|---:|---:|---:|---:|
| `code-go-train-000000` | `b68bf390d5800853f476ede764289f045993384fd6c771db0739b74adcc5b500` | 56,588 | 56,698,571 | 0 | 0 |
| `ind-hi-sangraha-v-train-000000` | `78aca29173b76840de617be0b1335b9417a340adce7b0b0564b23e195b919ab1` | 14,483 | 9,254,413 | 0 | 0 |

Both match the per-shard table above and the document counts in `rotation_ranjani-cse.md`.

`pytest teams/09-evaluation/decontam/tests` at `e5544324`: 152 passed, 2 skipped. All exit codes were 0.
Environment: Windows, Python 3.14.4, tokenizers 0.23.3, pyarrow 26.0.0, numpy 2.5.4. Decoded `.text.parquet` files stay local.

## Notes

- Decoded `.text.parquet` files hold document text: kept local, not committed, and deleted once this PR merges. The shard download links are not repeated here.
- A zero is the expected result: TSAI ran the F2 (benchmark leak) cleaning step before sharding. This check is the
  independent test of that step.
- Reproduce one shard:

```bash
python teams/09-evaluation/decontam/decode_shard.py <shard>.bin --tokenizer <p1536>/tokenizer.json --out <dir>
python teams/09-evaluation/decontam/decontam_check.py <dir>/<shard_id>.text.parquet
python teams/09-evaluation/decontam/canary_scan.py <dir>/<shard_id>.text.parquet
```
