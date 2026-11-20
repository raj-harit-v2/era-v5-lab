# Core shard decode check — Tejaskumar Reddy J

G1 core task 6, checked on **17 November 2026** by Tejaskumar Reddy J (`TEJASKUMAR-REDDY-J`). Coverage: all **41 sample-v0** shards of TSAI’s 41-shard bundle, with documents chosen at random so they differ from the evenly spaced ones in [#541](https://github.com/theschoolofai/era-v5-lab/pull/541). Repository base `55460a23e263e48e098988dfd8176a78800fc842`.

## Result

| Shard | Source pack | Documents in shard | Tokens in shard | Decoded and exact token round-trip |
|---|---|---:|---:|---|
| `code-cpp-train-000000` | `code-cpp` | 40,355 | 66,915,318 | 20/20 PASS |
| `code-cpp-train-000001` | `code-cpp` | 14,145 | 23,634,925 | 20/20 PASS |
| `code-go-train-000000` | `code-go` | 56,588 | 56,698,571 | 20/20 PASS |
| `code-go-train-000001` | `code-go` | 20,213 | 20,255,694 | 20/20 PASS |
| `code-java-train-000000` | `code-java` | 62,421 | 56,003,499 | 20/20 PASS |
| `code-java-train-000001` | `code-java` | 22,228 | 19,878,065 | 20/20 PASS |
| `code-js-ts-train-000000` | `code-js-ts` | 85,508 | 58,203,242 | 20/20 PASS |
| `code-js-ts-train-000001` | `code-js-ts` | 30,441 | 20,653,602 | 20/20 PASS |
| `code-python-train-000000` | `code-python` | 53,221 | 60,537,332 | 20/20 PASS |
| `code-python-train-000001` | `code-python` | 19,116 | 21,509,045 | 20/20 PASS |
| `code-rust-train-000000` | `code-rust` | 43,116 | 59,530,999 | 20/20 PASS |
| `code-rust-train-000001` | `code-rust` | 15,028 | 21,040,035 | 20/20 PASS |
| `en-dclm-train-000000` | `en-dclm` | 45,032 | 53,960,422 | 20/20 PASS |
| `en-dclm-train-000001` | `en-dclm` | 14,735 | 17,781,210 | 20/20 PASS |
| `en-fineweb-edu-train-000000` | `en-fineweb-edu` | 53,444 | 52,995,687 | 20/20 PASS |
| `en-fineweb-edu-train-000001` | `en-fineweb-edu` | 17,725 | 17,662,417 | 20/20 PASS |
| `en-nemotroncc-synth-train-000000` | `en-nemotroncc-synth` | 146,778 | 50,712,366 | 20/20 PASS |
| `en-nemotroncc-synth-train-000001` | `en-nemotroncc-synth` | 49,008 | 16,961,507 | 20/20 PASS |
| `en-nemotroncc-train-000000` | `en-nemotroncc` | 65,284 | 50,343,044 | 20/20 PASS |
| `en-nemotroncc-train-000001` | `en-nemotroncc` | 21,912 | 16,778,602 | 20/20 PASS |
| `ind-bn-fw2-train-000000` | `ind-bn-fw2` | 10,704 | 7,127,920 | 20/20 PASS |
| `ind-bn-sangraha-v-train-000000` | `ind-bn-sangraha-v` | 10,112 | 8,014,810 | 20/20 PASS |
| `ind-gu-fw2-train-000000` | `ind-gu-fw2` | 22,689 | 16,066,252 | 20/20 PASS |
| `ind-hi-fw2-train-000000` | `ind-hi-fw2` | 13,773 | 8,988,818 | 20/20 PASS |
| `ind-hi-hplt-train-000000` | `ind-hi-hplt` | 8,386 | 8,090,716 | 20/20 PASS |
| `ind-hi-indiccorp-train-000000` | `ind-hi-indiccorp` | 109,668 | 9,343,359 | 20/20 PASS |
| `ind-hi-sangraha-s-train-000000` | `ind-hi-sangraha-s` | 7,467 | 5,988,971 | 20/20 PASS |
| `ind-hi-sangraha-v-train-000000` | `ind-hi-sangraha-v` | 14,483 | 9,254,413 | 20/20 PASS |
| `ind-kn-fw2-train-000000` | `ind-kn-fw2` | 7,735 | 4,737,714 | 20/20 PASS |
| `ind-kn-sangraha-s-train-000000` | `ind-kn-sangraha-s` | 5,185 | 5,217,346 | 20/20 PASS |
| `ind-kn-sangraha-v-train-000000` | `ind-kn-sangraha-v` | 8,354 | 4,761,130 | 20/20 PASS |
| `ind-mr-fw2-train-000000` | `ind-mr-fw2` | 11,250 | 7,146,419 | 20/20 PASS |
| `ind-mr-sangraha-v-train-000000` | `ind-mr-sangraha-v` | 12,164 | 7,259,040 | 20/20 PASS |
| `ind-sa-fw2-train-000000` | `ind-sa-fw2` | 5,667 | 13,940,676 | 20/20 PASS |
| `ind-ta-sangraha-v-train-000000` | `ind-ta-sangraha-v` | 6,795 | 4,497,005 | 20/20 PASS |
| `ind-te-fw2-train-000000` | `ind-te-fw2` | 5,670 | 4,758,086 | 20/20 PASS |
| `ind-te-sangraha-s-train-000000` | `ind-te-sangraha-s` | 4,419 | 4,781,160 | 20/20 PASS |
| `ind-te-sangraha-v-train-000000` | `ind-te-sangraha-v` | 8,593 | 5,326,404 | 20/20 PASS |
| `math-finemath-train-000000` | `math-finemath` | 28,088 | 38,582,010 | 20/20 PASS |
| `math-megamath-train-000000` | `math-megamath` | 17,232 | 33,979,879 | 20/20 PASS |
| `sci-finepdfs-train-000000` | `sci-finepdfs` | 5,993 | 39,470,275 | 20/20 PASS |

**820/820 selected documents decoded successfully**, were nonempty, already tokenizer-normalized, ended with EOS 130822 and re-encoded to exactly the original document token IDs (excluding the terminal EOS). Artifact hashes, payload headers, index boundaries and metadata token counts were verified before decoding.

## Method

Same checks and reproducer as #541; the shard list and document selection differ. Actual local tokenizer bytes match frozen p1536 SHA-256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`; vocabulary 131,072; EOS `<|endoftext|>` 130822. Uses the Rust-backed `tokenizers.Tokenizer` implementation, with no substitute/test tokenizer.

Seeded random selection: 20 document indices drawn without replacement with `numpy.random.default_rng(20261117 + int(sha256(shard_id)[:8], 16))`, excluding #541's evenly spaced indices `i * (doc_count - 1) // 19`, so no selected document is one #541 decodes and the draw is reproducible. Document boundaries come from the index; source part and row come from the corresponding `.docs.parquet` row. The final EOS is removed for decoding and re-encoding uses `add_special_tokens=False`.

Each JSON evidence row records the document ID, source part/row, token offsets, decoded character count, SHA-256 of decoded UTF-8 and the four verification outcomes. Decoded text stays in memory and is not written to disk or Git.

Environment: Python 3.12.7, NumPy 1.26.4, PyArrow 21.0.0, tokenizers 0.20.3.

## Reproduce

```bash
python teams/01-data-a/audit/shard_decode_tejaskumar-reddy-j/reproduce.py \
  --input <downloaded-shard-folder> \
  --tokenizer <p1536-folder>/tokenizer.json \
  --out teams/01-data-a/audit/shard_decode_tejaskumar-reddy-j
```

Exit code **0**. All 41 shards report `20/20 decoded, normalized and exact token round-trip`.

## code-cpp-train-000000

Evidence: [code-cpp-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/code-cpp-train-000000.decode.json).

Selected zero-based document indices: `3533, 5994, 7052, 7309, 15761, 17329, 18298, 19640, 20153, 20604, 27415, 28902, 30379, 32068, 34069, 36167, 37082, 37642, 37736, 38136`.

Source part: `code-cpp_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-cpp-train-000000.json` | `ac5d75eb0c7fc44289df6639bcb4c7245e2bcbb23beebbf4f317e9d89116ad02` |
| `code-cpp-train-000000.bin` | `511b3e97a96627c2ac71c6772b0a91fa05522dff1467d3248d295269bcfb1761` |
| `code-cpp-train-000000.idx.npy` | `f5da1e46d38d1d2290334e7ace7963ddf8a2591463d1879cb78932e83560b72e` |
| `code-cpp-train-000000.docs.parquet` | `1dbcb682bded9965218b37bc8dd98419dad8ff3396fdf258cdbd6979fb59afaa` |
| `code-cpp-train-000000.quality_report.json` | `36a64772408631e05430b5d3dc93cc58268496135d5bb9b52e6e42878812e19e` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-cpp-train-000001

Evidence: [code-cpp-train-000001.decode.json](shard_decode_tejaskumar-reddy-j/code-cpp-train-000001.decode.json).

Selected zero-based document indices: `478, 1080, 1417, 2346, 2681, 2821, 3082, 3920, 4669, 5140, 5860, 6631, 8447, 8667, 9747, 10046, 10228, 11627, 11830, 12565`.

Source part: `code-cpp_part-00001_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-cpp-train-000001.json` | `bf87f4c79f48168a8149a6e43695f6a785a21b49d10895f8b55ae1e1c0a334d1` |
| `code-cpp-train-000001.bin` | `161b269499bf813885d0b68fac55c8b31afa546ddee698a76d28f3bbb356d5cb` |
| `code-cpp-train-000001.idx.npy` | `6bc153ec9bdf8fe0203e371c013c38a0f80676a4cbbb58c695947b945d712762` |
| `code-cpp-train-000001.docs.parquet` | `f9f7125c579c7646e0ea7ff8268b5f69f25ff48468ea84fe00283b31b21d6290` |
| `code-cpp-train-000001.quality_report.json` | `69503588b184946731ff9f0e3ec207f1cbe688256de9aa0a19244205f87ce218` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-go-train-000000

Evidence: [code-go-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/code-go-train-000000.decode.json).

Selected zero-based document indices: `238, 1590, 3277, 8710, 11466, 15083, 16593, 17607, 19280, 19455, 19598, 22542, 31443, 33519, 42936, 46892, 49632, 51525, 51540, 56212`.

Source part: `code-go_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-go-train-000000.json` | `b8d8807552c5d5a86aad6bfb8c43f1153b2524cdd3255a34d47a71b71e8b0f5d` |
| `code-go-train-000000.bin` | `b68bf390d5800853f476ede764289f045993384fd6c771db0739b74adcc5b500` |
| `code-go-train-000000.idx.npy` | `4be8739535179c8c79b4c937e44f5583da60e025287597fd6261cc197a81b0aa` |
| `code-go-train-000000.docs.parquet` | `35d6f20fb997fe3b13b11e1b1e2e8af8aba68a97ef81ae743254e9d8e3b1a171` |
| `code-go-train-000000.quality_report.json` | `ae4fa9782f6541f5544394283437486df9774e0bb65394d14755b7c567016547` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-go-train-000001

Evidence: [code-go-train-000001.decode.json](shard_decode_tejaskumar-reddy-j/code-go-train-000001.decode.json).

Selected zero-based document indices: `1565, 1982, 2880, 4085, 7100, 7233, 7548, 8065, 8384, 8635, 8779, 9061, 9072, 10360, 13570, 14103, 16137, 17943, 18130, 18429`.

Source part: `code-go_part-00001_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-go-train-000001.json` | `32905229e516b346b9ea84ebec696d6e8ce26085cc24f718c1b13949d19b0626` |
| `code-go-train-000001.bin` | `36430989fd7f5caf0f4e22ab1a88b730ca3b901eec537a5ab286d4b3c766fadd` |
| `code-go-train-000001.idx.npy` | `f0c1311278c2032422e6cc601c74d6b3f7f8ad729cc2ea15daa7e2ca3378503f` |
| `code-go-train-000001.docs.parquet` | `c86f78f0ed6dfb253f3f8ebba16dd98768bf5efa0d37060d3ed7b58148be7078` |
| `code-go-train-000001.quality_report.json` | `d370e1a29fa5710a7f2590c27c03f2d133e95a3ecd95fa5d552747878e48c2c9` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-java-train-000000

Evidence: [code-java-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/code-java-train-000000.decode.json).

Selected zero-based document indices: `1435, 4550, 5520, 6815, 15504, 18127, 18748, 19017, 25368, 32472, 34802, 39580, 42254, 45047, 49907, 53116, 54962, 55451, 57213, 62106`.

Source part: `code-java_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-java-train-000000.json` | `be5e714f712d236fe16eced0cc1125fcc5b7a572c6692404303d0cf0c3751f72` |
| `code-java-train-000000.bin` | `d885478b8a77ebfec35d9525d35a2f479e38f2b475f1167215c64b2ec5bec2dd` |
| `code-java-train-000000.idx.npy` | `8b8f6ecc12a338017efe4cbdabc39776cf29ba7cfd4e80ecbb65258bcdf6e501` |
| `code-java-train-000000.docs.parquet` | `d0a00c9cf8debef20ebcdb5e94f90fb39851433b0a004dbc6ba99fda0f35af7f` |
| `code-java-train-000000.quality_report.json` | `bd9f2b12270005f21fda9b17c029c9e8758354854f6136c6ec55763dbd7a6d35` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-java-train-000001

Evidence: [code-java-train-000001.decode.json](shard_decode_tejaskumar-reddy-j/code-java-train-000001.decode.json).

Selected zero-based document indices: `469, 2436, 2950, 4796, 5451, 5599, 5616, 6649, 8693, 8726, 8730, 13475, 15047, 16684, 18406, 18487, 19068, 20067, 21223, 21993`.

Source part: `code-java_part-00001_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-java-train-000001.json` | `1b9963b6aba1bacac505417d332155253ec21480db1a009ce338d5be203db931` |
| `code-java-train-000001.bin` | `c8e3aca96a7f6c16047b187caec4d09b0fdfab2eb4ec13ca2120e0c680f18c14` |
| `code-java-train-000001.idx.npy` | `12be8310bb76cc2641040bc8302a9dfe1ae1b5058ec7d4af9892636fc7c7cf0e` |
| `code-java-train-000001.docs.parquet` | `f610a4fb22892f04ec0c0d6a3aca67ec55172e090670250d02347ee9e475714a` |
| `code-java-train-000001.quality_report.json` | `1638affbd5a69a6b71fee6c14a5a19609870f6b3c486edbe18bc7caafaa0091d` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-js-ts-train-000000

Evidence: [code-js-ts-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/code-js-ts-train-000000.decode.json).

Selected zero-based document indices: `2560, 2623, 17444, 23030, 30305, 33500, 35977, 36394, 40728, 44261, 49067, 49123, 51015, 51865, 59307, 63585, 66141, 70622, 78256, 84740`.

Source part: `code-js-ts_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-js-ts-train-000000.json` | `274f108533057d769e67e09f91a29127bcb75bb52e2afca9760e3e90cf2caefc` |
| `code-js-ts-train-000000.bin` | `61d72a9aa9c8078e9e5a621fe497244fb7699dbe855bf8793a2b0631a23e605a` |
| `code-js-ts-train-000000.idx.npy` | `606defa67376ace792075d68ba05dcf8cd6630f99176e914ae65fdca5ddf27f0` |
| `code-js-ts-train-000000.docs.parquet` | `f142b0e0fa3dcd678d9e98e4b80a1f1d77d1a1816494936d4ceb48dbdb18da82` |
| `code-js-ts-train-000000.quality_report.json` | `03b353cf20c073ec2b5866f27ef37fdd13f6f378dce9b51759a2725ba65d35c6` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-js-ts-train-000001

Evidence: [code-js-ts-train-000001.decode.json](shard_decode_tejaskumar-reddy-j/code-js-ts-train-000001.decode.json).

Selected zero-based document indices: `1319, 2934, 3004, 5686, 6025, 6469, 6759, 8634, 10329, 14879, 15519, 15618, 16223, 16654, 16768, 19069, 20638, 23002, 27436, 29909`.

Source part: `code-js-ts_part-00001_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-js-ts-train-000001.json` | `3a568d5858bc3cf63bda5ba608fd44fe52e31c019588f668da969f8e78ca7782` |
| `code-js-ts-train-000001.bin` | `62e7aa3793863ace476e851aa89e0e4ffbd007eff5b7c2ebdb05fd1c1a355418` |
| `code-js-ts-train-000001.idx.npy` | `ec04a84fd2e77141f62cd52fd158e24346a4dc36c069280eb8a84b24b0d31d61` |
| `code-js-ts-train-000001.docs.parquet` | `8f91bb0392ddb4562df8258f111f866d85d46c59ba52cf414deaafa38813bca6` |
| `code-js-ts-train-000001.quality_report.json` | `8356096d544c29e168d61300270622da4fcac19eabcea7be31d7d2f3871e9941` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-python-train-000000

Evidence: [code-python-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/code-python-train-000000.decode.json).

Selected zero-based document indices: `833, 1758, 3571, 4069, 4862, 7202, 9721, 11848, 12662, 14057, 18953, 20260, 20426, 22655, 23249, 25785, 32271, 39673, 47459, 49261`.

Source part: `code-python_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-python-train-000000.json` | `00cb92e4224b2ffc50da4a115fe0502bc1f17f9751b4678b3e18dd2aadf995fc` |
| `code-python-train-000000.bin` | `bf6c275f296566cb88eb5e732238c1744c3294cbc8a47502a1ebfb06685b7900` |
| `code-python-train-000000.idx.npy` | `55bbde3a87e44c50b4566933f12583633101c165cc91a082cc8c444802e5b27d` |
| `code-python-train-000000.docs.parquet` | `18ea16dadefc38f0256179f029980c58d2f499c96962d3bc4d9e3096fb9293a3` |
| `code-python-train-000000.quality_report.json` | `410256c92da98eb3d204812dff5035c16c9115172e12113dc84e58e79846f9f4` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-python-train-000001

Evidence: [code-python-train-000001.decode.json](shard_decode_tejaskumar-reddy-j/code-python-train-000001.decode.json).

Selected zero-based document indices: `440, 929, 1119, 1851, 3531, 6540, 8524, 8967, 9008, 9368, 9878, 9962, 11734, 13241, 13993, 14490, 16044, 16477, 17022, 18221`.

Source part: `code-python_part-00001_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-python-train-000001.json` | `1f4ade8496d60fdffcac7bd7260a7b62d0347d7227fc90162e484e672da54c71` |
| `code-python-train-000001.bin` | `537723be5641f3aedab93695cb85f98c4b2259bb71300c9fb55bcc41ed2019d6` |
| `code-python-train-000001.idx.npy` | `016396b816822dc6478fc9bd6adaa496b5e05c6ede838774478c490f1ec5b05e` |
| `code-python-train-000001.docs.parquet` | `4565b1d04a85ddd4b04c6cb3468efa4852ebb35935eeddd26a494ff83bd5f99e` |
| `code-python-train-000001.quality_report.json` | `29fb0a7554f6cb502b8baf8e727ba4b4e33b68830c33c3a53c949fa824722ec5` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-rust-train-000000

Evidence: [code-rust-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/code-rust-train-000000.decode.json).

Selected zero-based document indices: `2465, 4425, 5887, 5975, 6108, 7831, 7990, 8301, 9237, 11183, 16471, 18937, 19467, 21003, 21377, 24846, 26279, 30072, 34668, 34812`.

Source part: `code-rust_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-rust-train-000000.json` | `e8c9cbb7bf03a6d56ec82d721a44798acb8882b8d98aa42d14728be936aefc73` |
| `code-rust-train-000000.bin` | `9468c56cccae9055e00dc2a530be2e1732b4798d1025611bc1ec438c1727278b` |
| `code-rust-train-000000.idx.npy` | `978a875772b39a37189f58f7d693a67b6c4863e05cd974a122aac0d66f3a5640` |
| `code-rust-train-000000.docs.parquet` | `b47840d725272e10112b9482ee5bd184cdaff5bff25f0ee484f5462840025457` |
| `code-rust-train-000000.quality_report.json` | `ea22d8909d72239bc6a3a6dad1eedf3267517de639f60fef99aecc499ff4ec70` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## code-rust-train-000001

Evidence: [code-rust-train-000001.decode.json](shard_decode_tejaskumar-reddy-j/code-rust-train-000001.decode.json).

Selected zero-based document indices: `909, 1114, 1181, 2402, 2428, 3862, 4012, 5436, 7211, 7782, 8194, 8358, 8538, 8663, 9847, 12208, 12264, 12804, 13176, 13948`.

Source part: `code-rust_part-00001_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `code-rust-train-000001.json` | `d23a19f51cfb5ffcf7f826a69affa5a8f5099e4969c5dd0a44c2e1b919918294` |
| `code-rust-train-000001.bin` | `b747ac07155d28fb9cb70871bfaddbbbe446c1806e375ff52ba20ee7444b93e1` |
| `code-rust-train-000001.idx.npy` | `8f020bcbfd86cb14b5be94b610ca6fbf8498ab1eee8a5890179c4cdb257bded9` |
| `code-rust-train-000001.docs.parquet` | `10c5ce7051384228b2df6fe836ed7ec733f0fe5aa649d13ff5a27a83aaf4de30` |
| `code-rust-train-000001.quality_report.json` | `c49898d1f75759a0b4f92d6f9b81c866effdd534b6299f0c8e17cf0ea44e904d` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## en-dclm-train-000000

Evidence: [en-dclm-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/en-dclm-train-000000.decode.json).

Selected zero-based document indices: `1357, 2473, 2652, 7199, 11022, 14078, 15385, 16272, 19357, 20977, 21833, 25506, 26270, 26981, 27633, 28905, 29915, 30571, 31915, 44567`.

Source part: `en-dclm_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `en-dclm-train-000000.json` | `aea60298ee0c7eed31b498c49f709d7f2fb96d01896388d8af2ec28a9240331a` |
| `en-dclm-train-000000.bin` | `1fccdcc4c15bb22ea564c8d3f1850582abd8b60e6c504386ee84308f6ee074de` |
| `en-dclm-train-000000.idx.npy` | `2cb4f8478781d20a73c43db1dbf5426ec85a7784f1fd3e4cbb60d443bfd6891d` |
| `en-dclm-train-000000.docs.parquet` | `3193a184ca4f89a3ef8d13ababaaa576d034fe767fed85269bd0322f5bb15bf7` |
| `en-dclm-train-000000.quality_report.json` | `ce3729e776105cd4ab4c82496d8913fa4aef794eb8e52342e5c6d3807faa9dea` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## en-dclm-train-000001

Evidence: [en-dclm-train-000001.decode.json](shard_decode_tejaskumar-reddy-j/en-dclm-train-000001.decode.json).

Selected zero-based document indices: `148, 1609, 2250, 2684, 3735, 4944, 5382, 6309, 6591, 7951, 8243, 9353, 9964, 10409, 11915, 13326, 13829, 14196, 14237, 14480`.

Source part: `en-dclm_part-00001_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `en-dclm-train-000001.json` | `7b66b835062e555738da2201546d42202030af538d8e529294c84efe41f8732e` |
| `en-dclm-train-000001.bin` | `2b6e1f71836f08242e4d9f5c3ef9cf217617a125eb516849886360347b321f7b` |
| `en-dclm-train-000001.idx.npy` | `8de73a1607e59f0362e8730441146836b25608a599d495d08fc2c8a265650a33` |
| `en-dclm-train-000001.docs.parquet` | `1f8d042845da40174271ed593e5ce08eb9bc398024dcc5405291d106e8fb78ee` |
| `en-dclm-train-000001.quality_report.json` | `c75db383abecf3d5c5274b15767a6444be093379a033fdaa07e926e951efa3de` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## en-fineweb-edu-train-000000

Evidence: [en-fineweb-edu-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/en-fineweb-edu-train-000000.decode.json).

Selected zero-based document indices: `4038, 4818, 12715, 13349, 14121, 14174, 17197, 22574, 23591, 28237, 30537, 34377, 37664, 41586, 45337, 46893, 49009, 49530, 49927, 52756`.

Source part: `en-fineweb-edu_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `en-fineweb-edu-train-000000.json` | `dede0aae38e08c48588955bb560acb9fc5901261262d93a4c1ffb317bb2f2be0` |
| `en-fineweb-edu-train-000000.bin` | `6625fc47c89e34bf2242a2c747c7e1f9b3583234e45e13e3a653b265007aca07` |
| `en-fineweb-edu-train-000000.idx.npy` | `8302b6298e67f07be6e1a0ea5218c33da2bcba7b510e9bdd7b2bbc41d0f72c18` |
| `en-fineweb-edu-train-000000.docs.parquet` | `13845ffb8fa6e8bc0fe91d58dde62c4d812fba1ed63d6673a8bee351594cfefe` |
| `en-fineweb-edu-train-000000.quality_report.json` | `03775cec876ddec067b4e8921f77587fa3c49585e727c61c15cf14a686fd9bfd` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## en-fineweb-edu-train-000001

Evidence: [en-fineweb-edu-train-000001.decode.json](shard_decode_tejaskumar-reddy-j/en-fineweb-edu-train-000001.decode.json).

Selected zero-based document indices: `1058, 1075, 1494, 1823, 2764, 2812, 5257, 5867, 6102, 8556, 9184, 9848, 10111, 10834, 10905, 13140, 13868, 14527, 15030, 17476`.

Source part: `en-fineweb-edu_part-00001_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `en-fineweb-edu-train-000001.json` | `b63116c6810d7873b7d604101b44ae1c879c7af7c9f2dde06aff26dabdd6552f` |
| `en-fineweb-edu-train-000001.bin` | `f1b97344614f7f54b407e60602204fd8313b83565de817cdf75b2cd6990a55ef` |
| `en-fineweb-edu-train-000001.idx.npy` | `e134f21e354a5e81ed3319bb5d27d1cb4ee869e9ce25f1001b4e9e8f48e260e8` |
| `en-fineweb-edu-train-000001.docs.parquet` | `05d02bb3a6f87af6ca223864871fac427f4c9df8108e6170854b9a0384d8d37b` |
| `en-fineweb-edu-train-000001.quality_report.json` | `c12c07aa37d18751ce53461d106a05541573546982cba35c1fe616169c2787e0` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## en-nemotroncc-synth-train-000000

Evidence: [en-nemotroncc-synth-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/en-nemotroncc-synth-train-000000.decode.json).

Selected zero-based document indices: `25535, 42123, 55473, 70249, 70396, 80994, 85528, 94850, 98807, 102406, 105551, 107222, 119436, 120331, 124519, 129326, 129575, 130822, 139132, 142192`.

Source part: `en-nemotroncc-synth_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `en-nemotroncc-synth-train-000000.json` | `3b356a648e0ac5a4752f373f773d4e92838a8b67b2d2bfec6d7256aafee40468` |
| `en-nemotroncc-synth-train-000000.bin` | `2be6f68c01d036a9e27ee3cc16d1ce02e8bf9adcd33f4f949baf48986144e278` |
| `en-nemotroncc-synth-train-000000.idx.npy` | `cb323ee4ade3a4196bfa195d6e223f7cf72a7d7d88995018a93c7a0e5cf7390a` |
| `en-nemotroncc-synth-train-000000.docs.parquet` | `eeb29f59c8361ba87ea457561e324309e372298becb0e5e1ae36466c314f4fe4` |
| `en-nemotroncc-synth-train-000000.quality_report.json` | `bd956706da5fe52eaeaf5dfb2ffc6a7a83d41f9593a4da3a820308bc31cb6b15` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## en-nemotroncc-synth-train-000001

Evidence: [en-nemotroncc-synth-train-000001.decode.json](shard_decode_tejaskumar-reddy-j/en-nemotroncc-synth-train-000001.decode.json).

Selected zero-based document indices: `173, 3077, 4102, 4972, 6857, 7631, 8230, 9997, 15013, 17863, 23144, 27188, 27288, 28725, 32528, 36095, 37880, 38565, 45288, 46399`.

Source part: `en-nemotroncc-synth_part-00001_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `en-nemotroncc-synth-train-000001.json` | `9ac291ce5ec22efbcc40c14aa2500907d56cd8239ebd732c9386aaa7ea1d70d7` |
| `en-nemotroncc-synth-train-000001.bin` | `2d041dc03bfbaabb3b6be8c43abe8122d012a0006ef1325f6fea57513f3eda34` |
| `en-nemotroncc-synth-train-000001.idx.npy` | `1c651f4195f45b3c8e07df9db8fb86d319bec4e96cd251e0da8325a968f2eccd` |
| `en-nemotroncc-synth-train-000001.docs.parquet` | `55952dbb7fbed57cd6ce0b24baa31e368c73764277a6ee7cf060209a80b59f21` |
| `en-nemotroncc-synth-train-000001.quality_report.json` | `e8292469eee32e9be089a0cbb2bed4517ff87007cfd5a9ab77b4b94cd6333fa8` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## en-nemotroncc-train-000000

Evidence: [en-nemotroncc-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/en-nemotroncc-train-000000.decode.json).

Selected zero-based document indices: `33, 51, 631, 6403, 11916, 16007, 16251, 21603, 25394, 25646, 33528, 37116, 37671, 47533, 48217, 56208, 59725, 63161, 64707, 65073`.

Source part: `en-nemotroncc_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `en-nemotroncc-train-000000.json` | `9b8ac78faa958bb36e117489d17615a5e6a58e532654ba8cbf965b9d6146dffb` |
| `en-nemotroncc-train-000000.bin` | `3b64c48e320d38c58ae3e8114cdb26fabb71f387131ddebd5453184128ae2ce0` |
| `en-nemotroncc-train-000000.idx.npy` | `64bfbe0d61a72c6c9f91afb7c80a08145cb58b2e64c168c8a32d94da24cc664e` |
| `en-nemotroncc-train-000000.docs.parquet` | `e73818ab8dad470e7a87ce570e2dc23efd79aa095aee25131c59359e4f0e4d75` |
| `en-nemotroncc-train-000000.quality_report.json` | `48dc21a62f5fe77fb82d272b7b076809b0df540a3f2aef17caafb32f8ade72db` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## en-nemotroncc-train-000001

Evidence: [en-nemotroncc-train-000001.decode.json](shard_decode_tejaskumar-reddy-j/en-nemotroncc-train-000001.decode.json).

Selected zero-based document indices: `2036, 3847, 6849, 7548, 9238, 9790, 10625, 10661, 10983, 11300, 11391, 14324, 14569, 14741, 15275, 15707, 17978, 20062, 20648, 21323`.

Source part: `en-nemotroncc_part-00001_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `en-nemotroncc-train-000001.json` | `2c61e1348f462310c4b0a858d686c0ed1f830947acf75867ca87de7ccf0a247f` |
| `en-nemotroncc-train-000001.bin` | `a7b14cbbbfc45f81aa1f881c1da97d97d3ce656018073c869435423b61095a42` |
| `en-nemotroncc-train-000001.idx.npy` | `aff94ee8b83fbd153e6f3e525455b4e7780d5f02c55a47fc7be582f692cec0b4` |
| `en-nemotroncc-train-000001.docs.parquet` | `e374d89f1b7a9ee2d7c423d968bc9ce8a9f405fbf0bfd4931f8e772cb13d70ae` |
| `en-nemotroncc-train-000001.quality_report.json` | `045cd4e2f4d8d6e621394eded2873bd602ea06a2f46f4779c7d0bb5ace0920ac` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-bn-fw2-train-000000

Evidence: [ind-bn-fw2-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-bn-fw2-train-000000.decode.json).

Selected zero-based document indices: `757, 2046, 2305, 2932, 3665, 4450, 5171, 5488, 5609, 5704, 5870, 6502, 6536, 6789, 7660, 8127, 8521, 10111, 10270, 10679`.

Source part: `ind-bn-fw2_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-bn-fw2-train-000000.json` | `9837209aaf98ce78bfcbe3126590781a871718e21cdd710775443e5ee31d6caa` |
| `ind-bn-fw2-train-000000.bin` | `ecf0822aca757724ac6b72d06af70c58350caffd848de126798b761a62f845ba` |
| `ind-bn-fw2-train-000000.idx.npy` | `98d658070ffe5c20c6eb98dbac47fff6a2cf5d19cca6ea3a98ae8031ab7d5c6f` |
| `ind-bn-fw2-train-000000.docs.parquet` | `d4c1d84577065bc28404e2b9a90b745e103271d2f9d0765b4c50ee68f174ec12` |
| `ind-bn-fw2-train-000000.quality_report.json` | `a34007586a03a9d628a72ff406641b0013a01fc19e6c299246cc1aed37d179b0` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-bn-sangraha-v-train-000000

Evidence: [ind-bn-sangraha-v-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-bn-sangraha-v-train-000000.decode.json).

Selected zero-based document indices: `1366, 2757, 3110, 3488, 3783, 4334, 4436, 4571, 4594, 4643, 6458, 6509, 7949, 8104, 8713, 9259, 9287, 9297, 9851, 9961`.

Source part: `ind-bn-sangraha-v_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-bn-sangraha-v-train-000000.json` | `f8f1d8ebd45ec05ad95e93a5f8add41fa8a52ff79b94caa6071805d6e18fb545` |
| `ind-bn-sangraha-v-train-000000.bin` | `dec1b695aca02613d958a232c760f09e77127ba4d680920c1284d8feba8f834d` |
| `ind-bn-sangraha-v-train-000000.idx.npy` | `d2884cb85e1c339b0c434e5f0442ad5304aa2178a672c8dd715f7a9a7afa0f44` |
| `ind-bn-sangraha-v-train-000000.docs.parquet` | `9cbaf41318c85735a7ef9442a5f29345c8e1f0d8ca514d052228db7c7dc763ec` |
| `ind-bn-sangraha-v-train-000000.quality_report.json` | `df05ef966bab76fe3539d28d81eacfc5adc7c3a842efa6851f276e4bbca3bce7` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-gu-fw2-train-000000

Evidence: [ind-gu-fw2-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-gu-fw2-train-000000.decode.json).

Selected zero-based document indices: `2483, 3329, 3797, 5095, 5584, 6066, 7628, 7756, 8382, 9621, 10283, 12146, 14477, 15397, 16787, 17154, 19427, 21229, 21289, 22198`.

Source part: `ind-gu-fw2_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-gu-fw2-train-000000.json` | `0b6953b4a9712c4340d2f4794ac4d40382bf977177a50befa14ccb076783bc5d` |
| `ind-gu-fw2-train-000000.bin` | `d10b573a08bcecf70cc8a8e193fefbcd502a50b9fa3c17c37fb006dbd8d41f5f` |
| `ind-gu-fw2-train-000000.idx.npy` | `ae3d08b49d746c1533ff0a946253f0e203f734d355dd73e54ce590109087a9c5` |
| `ind-gu-fw2-train-000000.docs.parquet` | `e88876f5a98c98df80cb8d9eede350a48c5fad246dcc02cbc71e031cdc67301a` |
| `ind-gu-fw2-train-000000.quality_report.json` | `53b20086085fdb98faf98f52c56fe9a6dabc420a559dcdff400df2063d6ed4c7` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-hi-fw2-train-000000

Evidence: [ind-hi-fw2-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-hi-fw2-train-000000.decode.json).

Selected zero-based document indices: `27, 979, 1672, 1789, 3723, 4629, 6635, 6745, 6862, 7672, 8014, 8274, 8766, 8996, 9054, 9315, 10956, 12091, 12601, 13314`.

Source part: `ind-hi-fw2_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-hi-fw2-train-000000.json` | `44b6e81ee0e3cb2a3ce09e33acc2f67c66e9f2525a3763b123f0fdb1c3af541f` |
| `ind-hi-fw2-train-000000.bin` | `e64b18601f2ffc82cfeaca78c864cead9aab62b0747adf62c38a1d891613a13b` |
| `ind-hi-fw2-train-000000.idx.npy` | `a25df3d8c92f2369156aa37eb82886df9f481890f5e6d75642a1a6f06fd2b6f6` |
| `ind-hi-fw2-train-000000.docs.parquet` | `5c4dc9c258e7d7b9b9711bfe5eaebe9d93a1f7a8394416490eb281fb29e3c028` |
| `ind-hi-fw2-train-000000.quality_report.json` | `69a0b16d5d57fb97ba6b765d034d78baf5822a0df08ccab8bda6cd4b6fc8fc0f` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-hi-hplt-train-000000

Evidence: [ind-hi-hplt-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-hi-hplt-train-000000.decode.json).

Selected zero-based document indices: `896, 976, 1241, 2019, 2093, 2350, 2520, 3202, 3478, 3499, 3630, 4128, 4594, 4695, 5620, 6582, 6963, 7488, 7671, 7804`.

Source part: `ind-hi-hplt_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-hi-hplt-train-000000.json` | `55be2ff53e9352d46da5670f62601ebab500431c8096e485d8f3df6e58ec38b8` |
| `ind-hi-hplt-train-000000.bin` | `e7e357d21beceacab190959591e68e9b00e24729fd098b87be0a28c4cdf95d46` |
| `ind-hi-hplt-train-000000.idx.npy` | `a2150ef0f8af461b574330d291d96b736e5280b377906a2721f885ef0208ed10` |
| `ind-hi-hplt-train-000000.docs.parquet` | `33aa6f89ce985b51fea502f7783ca0cbec48352e45301ca0edd9a3ca3c95ee37` |
| `ind-hi-hplt-train-000000.quality_report.json` | `939a3f8914d0415c441af827bdbefb2a426384760f474d9fb40d35397a235d7d` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-hi-indiccorp-train-000000

Evidence: [ind-hi-indiccorp-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-hi-indiccorp-train-000000.decode.json).

Selected zero-based document indices: `1746, 5417, 5977, 8035, 9136, 9229, 11257, 11405, 17638, 30038, 39388, 51346, 52999, 55960, 56510, 76609, 79829, 85111, 90333, 101800`.

Source part: `ind-hi-indiccorp_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-hi-indiccorp-train-000000.json` | `a607399e7860ea5e4e72ddae069e4889c96c3195f8adc0c3b43cc95db847f00e` |
| `ind-hi-indiccorp-train-000000.bin` | `6be0f58e567a0f8a45eb2891aeadacbeb43d570e988355c5f15efa576f0764db` |
| `ind-hi-indiccorp-train-000000.idx.npy` | `b72b261067244371edd5cb1daf28d541857c2d8117edef0957888369b2acef1f` |
| `ind-hi-indiccorp-train-000000.docs.parquet` | `0b4c2e1960a7734b19893baa953e5df6c3b9e557c396abf3667cb68310b0788f` |
| `ind-hi-indiccorp-train-000000.quality_report.json` | `7e23df4f5d07c2bfccef3ea4cbf866978f8cc37c5f61e1a79e620ca68e1d1171` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-hi-sangraha-s-train-000000

Evidence: [ind-hi-sangraha-s-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-hi-sangraha-s-train-000000.decode.json).

Selected zero-based document indices: `138, 357, 476, 1073, 1266, 1800, 1894, 2532, 2538, 2578, 3438, 3782, 4707, 5423, 5816, 6144, 6618, 6702, 6729, 6972`.

Source part: `ind-hi-sangraha-s_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-hi-sangraha-s-train-000000.json` | `0c87141000efd28fa86ea53ca42f59af9bb7c93f859d57f67448df32d1d25125` |
| `ind-hi-sangraha-s-train-000000.bin` | `4b92b39b427566809d1653f1b81b35b274c2a6c7de99c3b4f8a9d5b017bb5561` |
| `ind-hi-sangraha-s-train-000000.idx.npy` | `eb18bf82886e8ca1ec25b508ed03d53eb201e095de285ef6d876c2616bfb3b46` |
| `ind-hi-sangraha-s-train-000000.docs.parquet` | `62def28380f53b515ca5d470ae297f9bcb3bd863538836093a1076b7d1c65a03` |
| `ind-hi-sangraha-s-train-000000.quality_report.json` | `63b01203bd687f387f0b25511da7d93eabae5768a7792bf83ff6c85f8fd4d53a` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-hi-sangraha-v-train-000000

Evidence: [ind-hi-sangraha-v-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-hi-sangraha-v-train-000000.decode.json).

Selected zero-based document indices: `504, 2853, 3814, 3844, 4858, 4925, 5369, 5630, 5991, 9338, 9558, 9630, 9756, 9932, 11462, 11585, 12065, 13327, 14058, 14277`.

Source part: `ind-hi-sangraha-v_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-hi-sangraha-v-train-000000.json` | `f9d5256ef7a0765f13b7dd891eb435851f45abaeb5247994e459b00997d74513` |
| `ind-hi-sangraha-v-train-000000.bin` | `78aca29173b76840de617be0b1335b9417a340adce7b0b0564b23e195b919ab1` |
| `ind-hi-sangraha-v-train-000000.idx.npy` | `f726a8321ba63e0024fcfa0e39781aa310c6a4ae93f933594682f7548ee95543` |
| `ind-hi-sangraha-v-train-000000.docs.parquet` | `13c7992518db42ec847b5af8de3aa26918986692dcf18b4f03720c99ec7096fb` |
| `ind-hi-sangraha-v-train-000000.quality_report.json` | `b2858cefc2de35888443960078131cd9f1ffc00d9c4db8b792113363b2ba53f4` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-kn-fw2-train-000000

Evidence: [ind-kn-fw2-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-kn-fw2-train-000000.decode.json).

Selected zero-based document indices: `689, 1150, 1461, 1646, 2155, 2518, 2902, 3313, 3648, 4003, 4180, 4185, 4307, 4976, 5845, 6030, 6208, 6618, 6809, 7504`.

Source part: `ind-kn-fw2_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-kn-fw2-train-000000.json` | `c683d5be3aaf7223ca56ebdf609277abfe840ae81e064130af09588cac19a890` |
| `ind-kn-fw2-train-000000.bin` | `7224b101435879f73f07b17e5156919aa225376d1636bb622cb4ec80540a8126` |
| `ind-kn-fw2-train-000000.idx.npy` | `830c5bd4630098f51105d72c78fa4905064e0073d35f0f220b183b35d64a06c3` |
| `ind-kn-fw2-train-000000.docs.parquet` | `102a8f05625b9b5e050224f1cb3cb5c0ed165ce3ccb9fb0b9047c858772fb15f` |
| `ind-kn-fw2-train-000000.quality_report.json` | `19b8327257d3e642c492b5eb0bd2a1b089e03f3d4a36bd10b5ca56cf880a5508` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-kn-sangraha-s-train-000000

Evidence: [ind-kn-sangraha-s-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-kn-sangraha-s-train-000000.decode.json).

Selected zero-based document indices: `366, 577, 895, 930, 1400, 2408, 2454, 2602, 2791, 3035, 3150, 3310, 3311, 4157, 4198, 4344, 4424, 4553, 5052, 5171`.

Source part: `ind-kn-sangraha-s_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-kn-sangraha-s-train-000000.json` | `86690a17b8ad4134c038652ed89a86f9e6665c85da256fc7d8f7bfe14d061520` |
| `ind-kn-sangraha-s-train-000000.bin` | `41fe68ef433fe8612de02c9b30d846b58597f4e46ee456b806a03355421dce7e` |
| `ind-kn-sangraha-s-train-000000.idx.npy` | `80fb768e1d5919af21ab8ffd8002a5e63b4c5b70370924539f7867f0e4bfa33d` |
| `ind-kn-sangraha-s-train-000000.docs.parquet` | `4162b186d5476aa301263d3ed46dc9991b5060c54aedfa808e53e1261d0fa6dd` |
| `ind-kn-sangraha-s-train-000000.quality_report.json` | `a866a561d2b626fa67561309c11a767c75b64ef7e325c9d1dbf6961de0ebf2b9` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-kn-sangraha-v-train-000000

Evidence: [ind-kn-sangraha-v-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-kn-sangraha-v-train-000000.decode.json).

Selected zero-based document indices: `206, 573, 1298, 1775, 1879, 2534, 3072, 3412, 3954, 3986, 4041, 4401, 4528, 4664, 4717, 6396, 6873, 7085, 7786, 8280`.

Source part: `ind-kn-sangraha-v_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-kn-sangraha-v-train-000000.json` | `1b80a32aafec5cb7607e8fc3d4c04270c802ce8370d7fdcb7341474b4286c33b` |
| `ind-kn-sangraha-v-train-000000.bin` | `8d978e3e1929ceb920091cc1159c3c29d0d1e24fa11ec0ebaedf68114db8949a` |
| `ind-kn-sangraha-v-train-000000.idx.npy` | `329ff1329124e6baa6c679166c88f8ae2a1f031dd4bbe747d59d493641c1e56b` |
| `ind-kn-sangraha-v-train-000000.docs.parquet` | `0c58172b60a564af154c7702d81c009eda5819732d2f2c971ef10cc8f8e9824f` |
| `ind-kn-sangraha-v-train-000000.quality_report.json` | `679637d7deacced657a008b5186f111ab2dcd48bbeec2d206c4c37fb1f626167` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-mr-fw2-train-000000

Evidence: [ind-mr-fw2-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-mr-fw2-train-000000.decode.json).

Selected zero-based document indices: `2261, 2460, 3443, 3831, 3840, 4858, 5236, 6021, 6163, 6613, 6957, 7315, 8064, 8246, 8251, 8641, 9509, 10315, 10972, 11140`.

Source part: `ind-mr-fw2_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-mr-fw2-train-000000.json` | `d6f0701b8fd7d4fe3851eb9f6a8fc975498bad25977a79d676d705fbcf2d4551` |
| `ind-mr-fw2-train-000000.bin` | `c6aa0cf3adb8e3f01741ad41cab255d033ac47a802040bd6ce60fe5a61681be4` |
| `ind-mr-fw2-train-000000.idx.npy` | `3ac9e6f9865c14a076960034f04ba1ba669e450f643fe913738a8d97adce1bf5` |
| `ind-mr-fw2-train-000000.docs.parquet` | `31918741dc7ca33959489003eb7b5209cd95e9ffd7fffd8f44085ebd3c472b46` |
| `ind-mr-fw2-train-000000.quality_report.json` | `98f99a882f47758f456d4e1f28ca7cbd0db98c607ec6c8a2c3f5452406860513` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-mr-sangraha-v-train-000000

Evidence: [ind-mr-sangraha-v-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-mr-sangraha-v-train-000000.decode.json).

Selected zero-based document indices: `331, 1246, 1450, 2053, 3364, 3772, 3907, 4657, 4846, 4904, 5032, 6320, 6927, 8310, 9331, 10601, 10884, 10974, 11139, 11146`.

Source part: `ind-mr-sangraha-v_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-mr-sangraha-v-train-000000.json` | `87263aebcdb167d54bd84d223ed37553ab34a31e09532546829f5b64e6e82548` |
| `ind-mr-sangraha-v-train-000000.bin` | `043e1ff61f9f7db24600f13e63c62605671925dbdebcbfa59984908e6e0b3742` |
| `ind-mr-sangraha-v-train-000000.idx.npy` | `629caea639dd4429efc736da0ed2eff2222a947f8b850f1d2c5e9d3cdc933275` |
| `ind-mr-sangraha-v-train-000000.docs.parquet` | `650281215a7bc93d9003ee12e43e85ac3d4e4849b9d6c84ec6c0b0fd68a82fa3` |
| `ind-mr-sangraha-v-train-000000.quality_report.json` | `ffc1f032b3b36a05519b3be4170c33d87c7d163f18cbc3f8f8fd1d80c10cc132` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-sa-fw2-train-000000

Evidence: [ind-sa-fw2-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-sa-fw2-train-000000.decode.json).

Selected zero-based document indices: `14, 194, 862, 980, 2118, 2262, 2752, 2832, 3199, 3510, 3662, 3722, 3809, 3920, 5066, 5318, 5508, 5546, 5580, 5661`.

Source part: `ind-sa-fw2_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-sa-fw2-train-000000.json` | `813d8070a9a8dac7e297520956317d7cc5c3b9ce7cf288f6ccf62e8d27c7466f` |
| `ind-sa-fw2-train-000000.bin` | `a6d8546c5f48e7e1388edc441b48b409e29be870b79fd61ee6624f930ba7dab5` |
| `ind-sa-fw2-train-000000.idx.npy` | `b8b52e366ec1b765d65a15efdd2275946f5a8bad38379253a0684c92439a9ad5` |
| `ind-sa-fw2-train-000000.docs.parquet` | `1dd519173a5a5111a77845eb1f3230ca9912bddedf1898610281a4283f24b6d7` |
| `ind-sa-fw2-train-000000.quality_report.json` | `65982831379798c28bb1f1e0d4fe861017c40bc4456fa2607bc6b3914733d3bd` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-ta-sangraha-v-train-000000

Evidence: [ind-ta-sangraha-v-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-ta-sangraha-v-train-000000.decode.json).

Selected zero-based document indices: `127, 580, 777, 1167, 1208, 1536, 1862, 2507, 2827, 2857, 3254, 3362, 3648, 4194, 4211, 4445, 5646, 5813, 6190, 6218`.

Source part: `ind-ta-sangraha-v_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-ta-sangraha-v-train-000000.json` | `102e55601de11d559b854ba6bb74e72d8827df285ac5a264f52ec4bc9a4a7a4e` |
| `ind-ta-sangraha-v-train-000000.bin` | `418b46986e796f806d520b883091af93be976a068554b81026f7096417b455d7` |
| `ind-ta-sangraha-v-train-000000.idx.npy` | `392a803c9e2854ac733ff28d89da66e6cfce8f081ffe1d252cba5bdb6421862d` |
| `ind-ta-sangraha-v-train-000000.docs.parquet` | `97bccf7e5e31c9af5482ef9474cb352b3a37c60da902c1ef6a80ed96a9582645` |
| `ind-ta-sangraha-v-train-000000.quality_report.json` | `111af26f12f3a101c7f21b3c97107484d0ff06c15b603867bb59697ce66485b8` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-te-fw2-train-000000

Evidence: [ind-te-fw2-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-te-fw2-train-000000.decode.json).

Selected zero-based document indices: `31, 210, 420, 524, 572, 580, 1106, 1283, 1289, 1629, 1899, 1969, 2125, 2157, 3257, 3395, 3514, 4415, 5491, 5571`.

Source part: `ind-te-fw2_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-te-fw2-train-000000.json` | `148a1b336f3d5e670b9d30fc38253ed819d3624a3d480593cd7c2dcec9d931bb` |
| `ind-te-fw2-train-000000.bin` | `5a70a65df7d07063e942df6c9079217fc370cd7042230bfeeba7ed494f2721ed` |
| `ind-te-fw2-train-000000.idx.npy` | `a36a7bc63afb8bf60280b37961ae3e0f3851e513e448eea4921304ddb1fa083b` |
| `ind-te-fw2-train-000000.docs.parquet` | `b6d0121d4bd1c88b365c27a5e6732dcbd81f17ceeacd850d2081d16d9a5c247e` |
| `ind-te-fw2-train-000000.quality_report.json` | `f68327b1c589342c69a70797a9d61931f14ef1d33562b416d6c0a76448ba34a3` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-te-sangraha-s-train-000000

Evidence: [ind-te-sangraha-s-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-te-sangraha-s-train-000000.decode.json).

Selected zero-based document indices: `391, 753, 910, 1254, 1436, 1616, 1837, 2003, 2588, 2682, 2807, 2808, 2914, 3035, 3353, 3451, 3510, 3621, 3704, 4024`.

Source part: `ind-te-sangraha-s_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-te-sangraha-s-train-000000.json` | `eb3376088c992207e72f71dc6fa0b2bc154949316a6bb53151692703f87f803f` |
| `ind-te-sangraha-s-train-000000.bin` | `fbc93236d63888dd04421090847c98831ae033234908474e97713b87bb33bea9` |
| `ind-te-sangraha-s-train-000000.idx.npy` | `1268303984e44e9a4a75ff096b1cc8e35cb112a901628a4b446a163081d4fae0` |
| `ind-te-sangraha-s-train-000000.docs.parquet` | `9398ed9dca44f6ce3ed52ad010cc90e0f3bf1ab3838a5bd58c6b49e84ac4d47f` |
| `ind-te-sangraha-s-train-000000.quality_report.json` | `e690ff06459bd27e1e4c128f5f873aaf153a500caee5266afccfd3df5a8f5f8d` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## ind-te-sangraha-v-train-000000

Evidence: [ind-te-sangraha-v-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/ind-te-sangraha-v-train-000000.decode.json).

Selected zero-based document indices: `123, 146, 308, 617, 794, 1288, 1475, 2381, 2476, 3847, 3888, 5191, 5474, 5804, 6298, 6308, 6851, 7967, 8043, 8116`.

Source part: `ind-te-sangraha-v_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `ind-te-sangraha-v-train-000000.json` | `cb5341b9e879c028b0638db98c0174df527a52749d3983a1f5340d4cf28a0549` |
| `ind-te-sangraha-v-train-000000.bin` | `1036ff48ca9f714311ae676f8b9170cfa30ae8f94e826fb2cee03193bf811045` |
| `ind-te-sangraha-v-train-000000.idx.npy` | `77fbd21dae6f0a55face1e020e4975797fc9e735130e0a205dbc5d72be638352` |
| `ind-te-sangraha-v-train-000000.docs.parquet` | `047ec298980994c1f94eb4287bc2114f31474fa80bff9fc67bb0e4fe2b692b4b` |
| `ind-te-sangraha-v-train-000000.quality_report.json` | `74ca486f7edb13b3359559e118c381ed6c9321b1fd89f775afbb66ae693e1e7c` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## math-finemath-train-000000

Evidence: [math-finemath-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/math-finemath-train-000000.decode.json).

Selected zero-based document indices: `394, 1392, 4451, 7323, 7567, 8676, 9010, 9689, 13173, 14024, 14057, 15332, 22495, 23556, 23628, 24285, 24809, 25447, 25986, 27382`.

Source part: `math-finemath_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `math-finemath-train-000000.json` | `2e18384cbeb96254f99ac302f8f53c1a6dddd6bdd68d75fdd754808f7ac5e206` |
| `math-finemath-train-000000.bin` | `6e84f270a53bcdd225bb2a6cd6cd053b5e8e74c3cdf93d3aa80a2606cc9597da` |
| `math-finemath-train-000000.idx.npy` | `71e7583ba412e00d3aecc776333777df3a69428e5a9c0acfc4f0e572c9428e77` |
| `math-finemath-train-000000.docs.parquet` | `49bca3b3a8eb9955b1bd821f7d2590d020da2ee8705c42f853fdf5ed3aa8e891` |
| `math-finemath-train-000000.quality_report.json` | `7608571c0930abc22fa3232e22cefcc6abfe536840b0ce488bb846296134ce08` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## math-megamath-train-000000

Evidence: [math-megamath-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/math-megamath-train-000000.decode.json).

Selected zero-based document indices: `65, 241, 351, 1141, 2466, 3840, 5302, 6054, 8586, 8908, 10673, 10902, 11657, 11767, 14705, 14789, 14952, 15904, 16106, 16254`.

Source part: `math-megamath_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `math-megamath-train-000000.json` | `ccdae49682b19c7f724620406911d02c157eb94b14463b9eb2463e27b0318214` |
| `math-megamath-train-000000.bin` | `ff5a213f47981243e42a31e3ffe6733e276181ef0e8cfb7c581f77bea6e22e57` |
| `math-megamath-train-000000.idx.npy` | `1fbbfcfc8a8e19f160f5bbfc8b4902a017455421572232b3b55c0e6ed98fca8f` |
| `math-megamath-train-000000.docs.parquet` | `7f11583f97a20c2904cb583a24981d04c4d4b002b3809e79447bd09bbff8e770` |
| `math-megamath-train-000000.quality_report.json` | `538f893f47a2eb805fb27e7b11ba8d5890acd16d3359a254d00ec57b1eb6b33c` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## sci-finepdfs-train-000000

Evidence: [sci-finepdfs-train-000000.decode.json](shard_decode_tejaskumar-reddy-j/sci-finepdfs-train-000000.decode.json).

Selected zero-based document indices: `129, 273, 501, 583, 1585, 1961, 1970, 2575, 2645, 2650, 2822, 2839, 3621, 4028, 4765, 5506, 5665, 5790, 5831, 5981`.

Source part: `sci-finepdfs_part-00000_clean.parquet`.

| Verified input | Recomputed SHA-256 |
|---|---|
| `sci-finepdfs-train-000000.json` | `659ff75ecb86c4625e445d3211c316a1322083336158deb0de4163b447dda21f` |
| `sci-finepdfs-train-000000.bin` | `e95a44b141ec04314968a54bc44e48183861fd4591197c862553a9f6d2968585` |
| `sci-finepdfs-train-000000.idx.npy` | `7a290cbf1835fda071697c040d341a7db4fe06ac7597970bc5b0a36c90c29e3d` |
| `sci-finepdfs-train-000000.docs.parquet` | `5cab0da0405d6e903caabfaa0d9b04d6bc32cc7d79a8d363ec1c7cb1a2af891b` |
| `sci-finepdfs-train-000000.quality_report.json` | `f655095bf5872eecf092595b8941df82b7ffb8b4a77c0696ce05c52d452df5cc` |
| `cleaning_pipeline.json` | `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` |

## Limits and related evidence

Token round-trip establishes consistency of the decoded text with the selected token sequences. Comparing that text with the original cleaned documents requires upstream Parquet files. This report does not claim human semantic review, all-document decoding, a whole-bundle audit or benchmark decontamination.

Decoded character count vs `.docs.parquet` `n_chars`: equal for every selected document except in `ind-bn-fw2-train-000000` (20/20), `ind-bn-sangraha-v-train-000000` (20/20), `ind-hi-indiccorp-train-000000` (2/20). `shard_writer.py` records `n_chars` as the length of the cleaned text before tokenizer normalization, and p1536 normalization changes the length of some Bengali and Hindi text (composed or decomposed nukta letters). These documents still pass all four checks, including exact token round-trip; it is a definition point for `n_chars` in shard format v1, not a decoding fault.

The shared `cleaning_pipeline.json` has `dedup: null`, tracked by [#503](https://github.com/theschoolofai/era-v5-lab/issues/503). This bundle was written before the dedup v1 job ([#547](https://github.com/theschoolofai/era-v5-lab/pull/547)); 227 of the documents that job removes are in these 41 shards. Successful decoding does not resolve that provenance finding or establish training admission. The separate Data A rotation reports contain the full-shard integrity results.
