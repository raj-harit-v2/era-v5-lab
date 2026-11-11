# Tokenizer sample scan: canary scan + full decontamination check (G9 Task 11)

Gate 2 evidence: *the canary scan finds no canary in the tokenizer sample; the decontamination report exists.*

## Summary

- **Canary scan: clean.** 0 canaries in v0-clean (1,416,238 docs scanned) and in v0 (1,444,768). 4 canaries checked: era-v5-lab, gpqa_diamond, hle, terminal_bench_2.
- **Decontamination (fingerprints v2, full set, `set_sha256` `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`):** v0-clean 1,594 of 1,416,236 documents flagged (0.113%); v0 2,128 of 1,444,766 (0.147%).
- **68 documents (0.0048%) contain real benchmark or held-out text** (65 distinct items); the rest are false hits (boilerplate, shared code, question templates) or public text that benchmarks quote.
- **No contamination** for AIME, GPQA Diamond, HLE, Codeforces, Terminal-Bench 2, GSM8K, GAIA, LongBench v2, BFCL v3, SWE-bench Verified/Live/Pro (9 SWE-bench docs hold same-repo code, listed separately).
- **Main findings:** MILU questions on Indian exam-prep pages (47 docs, mostly `math-finemath`), and **9 training documents that overlap Team 5's held-out set v1** (6 with coverage ≥ 0.5, 4 of them ≥ 0.93). Action items for Teams 1/2/5 are at the end.

## Inputs

| Sample | Source | Integrity | Parts | Documents |
|---|---|---|---|---|
| tokenizer sample **v0** | CAP plan sheet, downloaded 2 Nov | `SHA256SUMS`: 87 OK, 0 failed | 86 parquet (48 train, 38 heldout) | 1,444,766 |
| tokenizer sample **v0-clean** (Data A spec v1 cleaner, job #244) | CAP plan sheet section *Week 2: cleaned tokenizer sample v0-clean*, downloaded 6 Nov | all 86 parts match `output_sha256` in `cleaned_manifest.json`; per-part doc counts match `output_rows` | 86 parquet | 1,416,236 |

Tools: `teams/09-evaluation/decontam/canary_scan.py` and `decontam_check.py` at main `9ab4f3d` (includes #193 and #280). 18 of 86 v0-clean parts are `unsupported_passthrough` in the cleaner manifest (cadj-*, ind-hi-sangraha-s/v, ind-ml-fw2, ind-or-fw2, ind-ta-fw2, ind-ta-sangraha-s): identical to v0.

## Commands

```bash
cd teams/09-evaluation/decontam
python canary_scan.py <tok-sample>/v0-clean > canary_v0-clean.jsonl    # whole folder; exit 0
python canary_scan.py <tok-sample>/v0       > canary_v0.jsonl
# full set: no --benchmarks, no --tags, no --exclude; one call per parquet file (86 per sample)
for f in $(find <tok-sample>/v0-clean/{train,heldout} -name '*.parquet'); do
  python decontam_check.py "$f" > "<out>/$(echo $f | tr / _).jsonl" 2> "<out>/$(echo $f | tr / _).log"
done
```

Every per-file log names `fingerprints v2 set_sha256 2826a3b883210c65… (full set)`. All 172 calls exited 0.

Note: the canary folder scan also reads the sample's README/JSON files, so its doc count is the parquet count + 2 (v0-clean: manifest + job summary; v0: README + manifest).

## 1. Canary scan

| Sample | Canaries | Docs scanned | With canary | Hits |
|---|---|---|---|---|
| v0-clean | 4 (era-v5-lab, gpqa_diamond, hle, terminal_bench_2) | 1,416,238 | 0 | 0 |
| v0 | 4 | 1,444,768 | 0 | 0 |

## 2. Decontamination check (raw flags)

| Benchmark | v0 flagged | v0-clean flagged |
|---|---|---|
| heldout_g5_v1 | 563 | 529 |
| swe_bench_live | 287 | 276 |
| hle | 173 | 173 |
| milu | 167 | 164 |
| swe_bench_pro | 640 | 159 |
| mmlu | 151 | 150 |
| livecodebench | 68 | 69 |
| swe_bench_verified | 45 | 42 |
| codeforces | 27 | 27 |
| terminal_bench_2 | 14 | 14 |
| gaia | 8 | 6 |
| in22_gen | 6 | 5 |
| flores200 | 4 | 4 |
| aime_2025 | 3 | 3 |
| gpqa_diamond | 3 | 3 |
| in22_conv | 3 | 3 |
| bfcl_v3 | 3 | 2 |
| longbench_v2 | 2 | 2 |
| aime_2024 | 1 | 1 |
| **docs flagged** | **2,128** (0.147%) | **1,594** (0.113%) |

Per-benchmark numbers count a document once per benchmark it matches, so they can sum to more than the docs flagged. v0 minus v0-clean is almost all `code-go` (594 vs 98 flags): generated Go protobuf code matching SWE-bench Pro, which the spec v1 cleaner removes. The verdicts below are for **v0-clean**, the sample Team 5 now trains on.

## 3. Verdicts for every v0-clean flag

A flag means a document shares at least one 13-word (prose) or 20-token (code) run with a benchmark item. For each flagged document the exact matched text was recomputed with the checker's own normalizer and hashing, and judged against this rubric:

| Verdict | Meaning |
|---|---|
| real | specific benchmark content: a question with its numbers/names, a problem statement, or the held-out document's own content |
| real-short | a complete but short or generic question stem |
| same-repo-code | 300+ chars of non-boilerplate code from the SWE-bench task's own repository (cannot tell if the fix is included without the gold patch) |
| translation-source | a FLORES/IN22 source sentence on its original page |
| public-text | well-known text a benchmark quotes (speeches, founding documents, statutes, literature, textbook definitions) |
| false-hit | boilerplate (cookie banners, footers, licences, forum notices), common code, question-type instructions or option layouts, notation |

| Verdict | Docs | By benchmark |
|---|---|---|
| **real** | 44 | milu 29, heldout_g5_v1 9, mmlu 4, livecodebench 2 |
| **real-short** | 24 | milu 18, mmlu 6 |
| **same-repo-code** | 9 | swe_bench_pro 5, swe_bench_live 4 |
| **translation-source** | 9 | in22_gen 5, flores200 4 |
| **public-text** | 152 | mmlu 99, milu 46, gaia 5, longbench_v2 2 |
| **false-hit** | 1356 | heldout_g5_v1 518, swe_bench_live 267, hle 171, swe_bench_pro 154, milu 64, livecodebench 61, swe_bench_verified 38, mmlu 37, codeforces 22, terminal_bench_2 14, in22_conv 3, aime_2025 3, bfcl_v3 2, gpqa_diamond 2 |
| total | 1594 | |

Per-document verdicts with item, coverage and offset: [`tokenizer_sample_scan/verdicts_v0-clean.csv`](tokenizer_sample_scan/verdicts_v0-clean.csv) (no document text).

### Contaminated documents (real + real-short)

| # | Part | doc_id | Item | Coverage | Offset | Verdict |
|---|---|---|---|---|---|---|
| 1 | `train/ind-hi-hplt/part-00000` | `d07a94e8a67d8af7` | `heldout_g5_v1:heldout:fw2-hi-test-000011` | 1.000 | 0 | real |
| 2 | `train/code-go/part-00000` | `cb74514035eea595` | `heldout_g5_v1:heldout:vault-go-test-000011` | 1.000 | 713 | real |
| 3 | `train/code-rust/part-00000` | `2d6a5ca3db45c5a6` | `heldout_g5_v1:heldout:vault-rs-test-000053` | 1.000 | 440 | real |
| 4 | `train/ind-mr-sangraha-v/part-00000` | `529203eca6c34806` | `heldout_g5_v1:heldout:fw2-mr-test-000037` | 0.928 | 6769 | real |
| 5 | `train/code-rust/part-00000` | `048f9453e376a2db` | `heldout_g5_v1:heldout:vault-rs-test-000028` | 0.690 | 45422 | real |
| 6 | `train/cadj-commits/part-00000` | `f82f937d735161bc` | `heldout_g5_v1:heldout:vault-js-test-000022` | 0.563 | 674 | real |
| 7 | `train/math-finemath/part-00000` | `83585c091af2334e` | `heldout_g5_v1:heldout:owm-test-000000` | 0.199 | 4734 | real |
| 8 | `train/ind-or-fw2/part-00000` | `9fe314013d870d0d` | `heldout_g5_v1:heldout:fw2-or-test-000008` | 0.179 | 396 | real |
| 9 | `train/math-finemath/part-00000` | `e3e1c1926579bf19` | `heldout_g5_v1:heldout:owm-test-000022` | 0.041 | 11459 | real |
| 10 | `train/math-finemath/part-00000` | `9b30bdc511be06c7` | `livecodebench:release_v6:3484` | 1.000 | 72 | real |
| 11 | `train/code-go/part-00000` | `0a2e62f3f67dfe24` | `livecodebench:release_v6:2791` | 0.073 | 74 | real |
| 12 | `train/math-finemath/part-00000` | `440a2225b63497e0` | `milu:test:15804` | 0.857 | 6296 | real |
| 13 | `train/math-finemath/part-00000` | `3a4b4cf2156831fe` | `milu:test:10089` | 0.804 | 770 | real |
| 14 | `train/en-dclm/part-00000` | `2d7423e919ec3079` | `milu:test:10718` | 0.766 | 158 | real |
| 15 | `train/en-nemotroncc/part-00001` | `c8c6e6156343ea07` | `milu:test:16541` | 0.671 | 1337 | real |
| 16 | `train/sci-finepdfs/part-00000` | `38a48b123505b461` | `milu:test:6829` | 0.638 | 38703 | real |
| 17 | `train/math-finemath/part-00000` | `29f93e980eec80bf` | `milu:test:8043` | 0.633 | 11 | real |
| 18 | `train/math-finemath/part-00000` | `5a93d530d9026175` | `milu:test:18603` | 0.625 | 2139 | real |
| 19 | `train/math-finemath/part-00000` | `8f956d25e0fe3f1f` | `milu:test:16718` | 0.617 | 10468 | real |
| 20 | `train/en-nemotroncc/part-00000` | `53c0b2ba67b1fa72` | `milu:test:10712` | 0.606 | 273 | real |
| 21 | `train/math-finemath/part-00000` | `83c3f04a9be32670` | `milu:test:10089` | 0.522 | 271 | real |
| 22 | `train/math-finemath/part-00000` | `103cd5958abba4db` | `milu:test:13142` | 0.455 | 177071 | real |
| 23 | `train/math-finemath/part-00000` | `f2cae34f67d0c0e1` | `milu:test:16374` | 0.375 | 5538 | real |
| 24 | `train/math-finemath/part-00000` | `4798cdb1332550a7` | `milu:test:8060` | 0.368 | 8367 | real |
| 25 | `train/math-megamath/part-00000` | `17c87a6745a7f0f9` | `milu:test:6741` | 0.360 | 2054 | real |
| 26 | `train/math-finemath/part-00000` | `1360643339d41ec6` | `milu:test:13604` | 0.333 | 2077 | real |
| 27 | `train/math-finemath/part-00000` | `ff2fe0ad29c5867d` | `milu:test:7527` | 0.333 | 2006 | real |
| 28 | `train/ind-hi-indiccorp/part-00000` | `1db2ec0c8dab92cd` | `milu:test:37658` | 0.327 | 65 | real |
| 29 | `train/math-finemath/part-00000` | `761cb13558f5b70b` | `milu:test:8055` | 0.324 | 8182 | real |
| 30 | `train/math-finemath/part-00000` | `5a8b0f385af9cc4c` | `milu:test:14017` | 0.310 | 3351 | real |
| 31 | `train/math-finemath/part-00000` | `e7ccba73fca0573b` | `milu:test:14017` | 0.310 | 26023 | real |
| 32 | `train/en-fineweb-edu/part-00001` | `1d030ade41e37de0` | `milu:test:10088` | 0.292 | 1417 | real |
| 33 | `train/en-dclm/part-00000` | `0048d32456438d2e` | `milu:test:13908` | 0.283 | 13816 | real |
| 34 | `train/math-finemath/part-00000` | `6b484ab2cf5e72b6` | `milu:test:17914` | 0.283 | 3783 | real |
| 35 | `train/math-megamath/part-00000` | `81b3dc56cc0b5853` | `milu:test:6758` | 0.271 | 23127 | real |
| 36 | `train/math-finemath/part-00000` | `444d37e2e3e202be` | `milu:test:17787` | 0.262 | 162 | real |
| 37 | `train/math-finemath/part-00000` | `7cf3358986b63b37` | `milu:test:8198` | 0.211 | 4057 | real |
| 38 | `train/math-finemath/part-00000` | `f8f44d0005e0120a` | `milu:test:12408` | 0.203 | 1522 | real |
| 39 | `train/math-finemath/part-00000` | `e72e9f068f68bf00` | `milu:test:13415` | 0.200 | 1611 | real |
| 40 | `train/ind-hi-sangraha-v/part-00000` | `1af7818ca1f80a0f` | `milu:test:35519` | 0.098 | 6381 | real |
| 41 | `train/math-finemath/part-00000` | `e2b55a44a4e4f081` | `milu:test:18910` | 0.196 | 2364 | real-short |
| 42 | `train/math-finemath/part-00000` | `4bd750094a74c494` | `milu:test:16707` | 0.185 | 1801 | real-short |
| 43 | `train/math-finemath/part-00000` | `14fe7f10bd5448dd` | `milu:test:10618` | 0.171 | 85145 | real-short |
| 44 | `train/math-finemath/part-00000` | `1e4c6961eec00d6b` | `milu:test:12395` | 0.167 | 3953 | real-short |
| 45 | `train/en-nemotroncc/part-00001` | `dd58c719bd571569` | `milu:test:13741` | 0.167 | 2792 | real-short |
| 46 | `train/math-finemath/part-00000` | `6c473e4f9f2a6256` | `milu:test:9182` | 0.167 | 801 | real-short |
| 47 | `train/math-megamath/part-00000` | `b7c817d197c7d27e` | `milu:test:10089` | 0.152 | 7618 | real-short |
| 48 | `train/en-dclm/part-00000` | `0ab808090d15ec52` | `milu:test:10567` | 0.111 | 8634 | real-short |
| 49 | `train/en-dclm/part-00001` | `4c257ee13e92635f` | `milu:test:16371` | 0.111 | 24809 | real-short |
| 50 | `train/en-dclm/part-00000` | `6e85a768fc3fae4f` | `milu:test:18008` | 0.091 | 3219 | real-short |
| 51 | `train/ind-hi-sangraha-v/part-00000` | `16715ac27052d77c` | `milu:test:37746` | 0.091 | 7932 | real-short |
| 52 | `train/en-fineweb-edu/part-00000` | `ce02d4ac56c7b027` | `milu:test:18293` | 0.067 | 1050 | real-short |
| 53 | `train/en-dclm/part-00000` | `9e2404cc4b124600` | `milu:test:8276` | 0.067 | 538 | real-short |
| 54 | `train/math-finemath/part-00000` | `ca60fe2b86fba518` | `milu:test:16175` | 0.061 | 1174 | real-short |
| 55 | `train/en-nemotroncc-synth/part-00000` | `ccbfcc3ba037269a` | `milu:test:13495` | 0.059 | 1845 | real-short |
| 56 | `train/math-finemath/part-00000` | `dc181b12069b00fd` | `milu:test:14027` | 0.053 | 1374 | real-short |
| 57 | `train/math-finemath/part-00000` | `5048db467a38d166` | `milu:test:11467` | 0.048 | 3944 | real-short |
| 58 | `train/math-finemath/part-00000` | `021c4ecb97188bc9` | `milu:test:16634` | 0.032 | 2 | real-short |
| 59 | `train/en-fineweb-edu/part-00001` | `2b898638bc22304e` | `mmlu:test:1465` | 0.609 | 476 | real |
| 60 | `train/math-finemath/part-00000` | `4eaf1b043b89917d` | `mmlu:test:4252` | 0.310 | 35698 | real |
| 61 | `train/math-finemath/part-00000` | `c88e2d5c1c61facb` | `mmlu:test:1454` | 0.278 | 4433 | real |
| 62 | `train/math-finemath/part-00000` | `583353259ec7eda3` | `mmlu:test:1096` | 0.266 | 94 | real |
| 63 | `train/math-megamath/part-00000` | `0b649af92d9a5cfc` | `mmlu:test:2064` | 0.183 | 574 | real-short |
| 64 | `train/en-fineweb-edu/part-00001` | `886b33e7bed02d42` | `mmlu:test:12512` | 0.111 | 1343 | real-short |
| 65 | `train/math-finemath/part-00000` | `982b1d00575fc7a7` | `mmlu:test:1643` | 0.091 | 11447 | real-short |
| 66 | `train/en-nemotroncc-synth/part-00000` | `8dab660493b21976` | `mmlu:test:490` | 0.091 | 2665 | real-short |
| 67 | `train/en-nemotroncc-synth/part-00001` | `0987dfdf5f9ec1a0` | `mmlu:test:4927` | 0.067 | 683 | real-short |
| 68 | `train/en-nemotroncc/part-00001` | `f850e013d31ed753` | `mmlu:test:8335` | 0.053 | 8526 | real-short |

### Same-repo SWE-bench code (not counted as contaminated)

| Part | doc_id | Item | Coverage |
|---|---|---|---|
| `train/code-python/part-00001` | `3ef1aec4364fd9b6` | `swe_bench_pro:test:instance_ansible__ansible-d72025be751c894673ba85caa063d835a0ad3a8c-v390e508d27db7a51eece36bb6d9698b63a5b638a` | 0.105 |
| `train/code-go/part-00000` | `62f1c8bfbe06192f` | `swe_bench_pro:test:instance_gravitational__teleport-46a13210519461c7cec8d643bfbe750265775b41` | 0.057 |
| `train/code-go/part-00000` | `605498ba2242ee7c` | `swe_bench_pro:test:instance_gravitational__teleport-3587cca7840f636489449113969a5066025dd5bf` | 0.052 |
| `train/code-js-ts/part-00000` | `daf4b58fa6827b8b` | `swe_bench_pro:test:instance_element-hq__element-web-1216285ed2e82e62f8780b6702aa0f9abdda0b34-vnan` | 0.049 |
| `train/code-python/part-00000` | `886c630002e15e5b` | `swe_bench_pro:test:instance_ansible__ansible-eea46a0d1b99a6dadedbb6a3502d599235fa7ec3-v390e508d27db7a51eece36bb6d9698b63a5b638a` | 0.028 |
| `train/code-python/part-00000` | `ad975efd8103e5c8` | `swe_bench_live:test:pdm-project__pdm-3191` | 0.025 |
| `train/code-python/part-00000` | `e1f1879ef76843b8` | `swe_bench_live:test:pypsa__pypsa-896` | 0.020 |
| `train/code-python/part-00000` | `b4140476f57da914` | `swe_bench_live:test:conan-io__conan-16964` | 0.001 |
| `train/code-python/part-00001` | `df8f26f50f2ab492` | `swe_bench_live:test:freqtrade__freqtrade-10208` | 0.001 |

## 4. Known limits

- n-gram matching finds copies only: paraphrased or translated benchmark items are not found (decontam README, *Known limits*).
- Items under 8 words are not fingerprinted; BFCL v3 has 16% of items without a fingerprint.
- `same-repo-code` cannot be resolved without each task's gold patch.
- v0 flags were counted but not classified; outside `code-go` they match v0-clean closely.

## 5. Actions

- **Team 5 (held-out set v1):** 9 training documents overlap held-out documents. Six have coverage ≥ 0.5 (4 of them ≥ 0.93: `fw2-hi-test-000011` 1.00, `vault-go-test-000011` 1.00, `vault-rs-test-000053` 1.00, `fw2-mr-test-000037` 0.93, `vault-rs-test-000028` 0.69, `vault-js-test-000022` 0.56); three are partial overlaps (0.04–0.20). The same page or file was collected by two sources (e.g. FineWeb-2 test split and HPLT train). Suggest dropping these docs from training (Teams 1/2) or replacing those held-out docs (Team 5).
- **Teams 1/2 (data):** remove the contaminated documents listed above before training. The 47 MILU documents are exam-prep pages: 28 in `math-finemath`, the rest in `en-dclm`, `en-nemotroncc`, `math-megamath`, `en-fineweb-edu`, `ind-hi-sangraha-v`, `ind-hi-indiccorp`, `sci-finepdfs` and `en-nemotroncc-synth`.
- **G9 (fingerprints):** 518 held-out flags come from site boilerplate or common code inside 36 held-out documents (cookie banners, comment-policy notes, forum footers, R-bloggers/GMAT Club lines, a CC BY variant, booking-site templates, common Go/JS idioms). Adding the boilerplate passages to `decontam/boilerplate/scoped/heldout_g5_v1.txt`, as was done for the first 5, removes most of them.
- **Team 3 (tokenizer):** no canary in the sample, and nothing in this scan blocks the tokenizer freeze; 4 FLORES-200 and 5 IN22-Gen source sentences appear on their original web pages (FLORES is the fertility harness set; these are 4 training documents, not the harness files, and their effect was not measured).

