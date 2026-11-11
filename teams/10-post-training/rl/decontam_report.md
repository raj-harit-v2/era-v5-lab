# RL decontamination report

Run for G10 on 2026-11-06. Every set was checked against Team 9's benchmark fingerprints **v2** with the **full set** (no `--benchmarks`, `--tags` or `--exclude`), and scanned for canaries.

- **set_sha256:** `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`
- **Tools:** `teams/09-evaluation/decontam/decontam_check.py` and `canary_scan.py`, lab main `4332666816088984c00edc45f734657934b11a10`. sha256 of the files used:
  - `canary_scan.py`: `322066d675e13af8bee0d05602f755f49e33da5a148bf664306ce6d6a9f908c2`
  - `decontam_check.py`: `62a269a25123543b5470c4956ba1be530ea257c597bc2be2eab19201cb62df8f`
  - `fpset.py`: `7f5f48d08506d619ebfadd2742e86d29ec3ea28e5fcfd729f13cd8d959689c59`
  - `lab_canary.py`: `373536a777c9f16367cf6affcc2cc6243755ac23e75850a2624eadf65918ea09`
  - `normalize.py`: `570dcb820ac2ae6c667b1abc5ea1d781a6795aa42a7735aa94377e756d7d70e9`
- **Runner and reconciliation:** `sft/decontam_run.py`; this file is written by `sft/decontam_report.py`.
- **Sets run:** 4. **Rows in:** 47,192. **Removed (flagged or canary):** 9,843 (20.86%). **Kept:** 37,349.
- No benchmark item text is in this file or in the run records: only set names, counts, document ids, benchmark item ids, offsets and sha256 values.

## 1. Result per set

| Set | Rows in | Flagged | Canary | Removed | Rows kept | Clean file sha256 |
|---|---:|---:|---:|---:|---:|---|
| `rl-code-code-contests` | 13,328 | 2,454 | 0 | 2,454 (18.41%) | 10,874 | `f8a15cb66d69…` |
| `rl-code-codeforces` | 9,556 | 624 | 0 | 624 (6.53%) | 8,932 | `6bebfb332fef…` |
| `rl-code-deepcoder` | 24,287 | 6,765 | 0 | 6,765 (27.85%) | 17,522 | `0ea67ce470df…` |
| `rl-code-swe-envs-g10` | 21 | 0 | 0 | 0 (0.00%) | 21 | `46e7f7da3161…` |
| **Total** | **47,192** | **9,843** | **0** | **9,843** (20.86%) | **37,349** | |

A row that is both flagged and carries a canary counts once in Removed.

## 2. Flagged documents by benchmark

| Set | `codeforces` | `gaia` | `heldout_g5_v1` | `hle` | `livecodebench` | `milu` |
|---|---:|---:|---:|---:|---:|---:|
| `rl-code-code-contests` | 1199 | 1 | 1 | 23 | 1662 | 1 |
| `rl-code-codeforces` | 498 | 0 | 0 | 15 | 168 | 0 |
| `rl-code-deepcoder` | 3609 | 4 | 0 | 57 | 4609 | 1 |
| `rl-code-swe-envs-g10` | 0 | 0 | 0 | 0 | 0 | 0 |

A document is flagged when it shares at least one 13-word run (20 tokens for code) with a benchmark item. The whole document is removed. The count is documents per benchmark, so a document that matches two benchmarks counts in both columns.

## 3. Flagged documents by coverage

Coverage is the share of one benchmark item's runs that the document contains (the highest over its hits). The bands are for reading the result; every flagged document is removed whatever its band.

| Set | Flagged | Coverage 0.5 or more | 0.1 to 0.5 | Below 0.1 |
|---|---:|---:|---:|---:|
| `rl-code-code-contests` | 2454 | 0 | 8 | 2446 |
| `rl-code-codeforces` | 624 | 2 | 20 | 602 |
| `rl-code-deepcoder` | 6765 | 599 | 81 | 6085 |
| `rl-code-swe-envs-g10` | 0 | 0 | 0 | 0 |

## 4. Benchmark items with the largest overlap

**`rl-code-code-contests`**: at least 819 different benchmark items found in 2454 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `hle:test:66ed458ed841eb51a985ca8d` | 1 | 0.471 | 192 / 408 | `rl-code-code-contests/train-00036-of-00039-146e1a11c054aeab/19` | 0 |
| `hle:test:672f6cfd609b665328565e5c` | 1 | 0.421 | 134 / 318 | `rl-code-code-contests/train-00038-of-00039-96a59dd6a98cd075/144` | 0 |
| `hle:test:672f72e3609b665328565e6b` | 1 | 0.238 | 125 / 526 | `rl-code-code-contests/train-00000-of-00039-e991a271dbfa9925/142` | 0 |
| `hle:test:673627bc10ec0a5f859365ce` | 1 | 0.188 | 69 / 368 | `rl-code-code-contests/train-00003-of-00039-e3822fccad6e083a/71` | 861 |
| `hle:test:67373220a4d09488d430f640` | 1 | 0.185 | 69 / 373 | `rl-code-code-contests/train-00003-of-00039-e3822fccad6e083a/71` | 861 |
| `hle:test:672e24f117ed86a6ef9def55` | 1 | 0.183 | 72 / 393 | `rl-code-code-contests/train-00008-of-00039-7246e6b7423b404f/133` | 0 |
| `hle:test:66eeea0187ec4a6a04092e78` | 11 | 0.163 | 67 / 412 | `rl-code-code-contests/train-00021-of-00039-b257bf03d6876780/39` | 127 |
| `hle:test:66f28a89f1256af80477e15d` | 1 | 0.136 | 100 / 733 | `rl-code-code-contests/train-00011-of-00039-5de236be5188959d/231` | 0 |
| `gaia:2023:2b3ef98c-cc05-450b-a719-711aee40ac65` | 1 | 0.110 | 13 / 118 | `rl-code-code-contests/train-00009-of-00039-b8c920f6629b57b2/104` | 1828 |
| `codeforces:test:2023/A` | 17 | 0.099 | 56 / 565 | `rl-code-code-contests/train-00018-of-00039-8c793837880f5507/118` | 0 |
| `livecodebench:release_v6:abc348_e` | 39 | 0.093 | 24 / 259 | `rl-code-code-contests/train-00014-of-00039-dc3ebb07a3cba8e4/187` | 8 |
| `livecodebench:release_v6:abc355_d` | 11 | 0.093 | 15 / 161 | `rl-code-code-contests/train-00029-of-00039-2b6615897d038115/263` | 828 |
| `livecodebench:release_v6:abc350_d` | 30 | 0.091 | 26 / 286 | `rl-code-code-contests/train-00012-of-00039-da9476a39a1bdbb7/142` | 496 |
| `codeforces:test:2056/D` | 82 | 0.088 | 24 / 273 | `rl-code-code-contests/train-00038-of-00039-96a59dd6a98cd075/47` | 866 |
| `livecodebench:release_v6:abc394_f` | 33 | 0.088 | 23 / 261 | `rl-code-code-contests/train-00014-of-00039-dc3ebb07a3cba8e4/187` | 627 |

**`rl-code-codeforces`**: at least 288 different benchmark items found in 624 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `livecodebench:release_v6:1899_D` | 1 | 0.692 | 278 / 402 | `rl-code-codeforces/1899/D` | 0 |
| `livecodebench:release_v6:1899_B` | 1 | 0.517 | 212 / 410 | `rl-code-codeforces/1899/B` | 0 |
| `livecodebench:release_v6:1899_A` | 1 | 0.482 | 67 / 139 | `rl-code-codeforces/1899/A` | 0 |
| `livecodebench:release_v6:1899_C` | 1 | 0.368 | 78 / 212 | `rl-code-codeforces/1899/C` | 0 |
| `hle:test:66ed458ed841eb51a985ca8d` | 1 | 0.338 | 138 / 408 | `rl-code-codeforces/282/A` | 0 |
| `livecodebench:release_v6:1873_B` | 1 | 0.311 | 50 / 161 | `rl-code-codeforces/1873/B` | 0 |
| `livecodebench:release_v6:1883_C` | 15 | 0.197 | 64 / 325 | `rl-code-codeforces/1883/C` | 0 |
| `livecodebench:release_v6:1883_B` | 6 | 0.185 | 79 / 426 | `rl-code-codeforces/1883/B` | 0 |
| `hle:test:672e24f117ed86a6ef9def55` | 1 | 0.183 | 72 / 393 | `rl-code-codeforces/71/A` | 0 |
| `hle:test:672f72e3609b665328565e6b` | 1 | 0.165 | 87 / 526 | `rl-code-codeforces/339/A` | 0 |
| `hle:test:672f6cfd609b665328565e5c` | 1 | 0.148 | 47 / 318 | `rl-code-codeforces/112/A` | 0 |
| `livecodebench:release_v6:1873_D` | 1 | 0.130 | 35 / 270 | `rl-code-codeforces/1873/D` | 0 |
| `codeforces:test:2029/H` | 19 | 0.122 | 48 / 395 | `rl-code-codeforces/1864/E` | 1347 |
| `codeforces:test:2018/A` | 1 | 0.118 | 47 / 398 | `rl-code-codeforces/1967/A` | 0 |
| `hle:test:66f28a89f1256af80477e15d` | 1 | 0.117 | 86 / 733 | `rl-code-codeforces/1/A` | 0 |

**`rl-code-deepcoder`**: at least 1289 different benchmark items found in 6765 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `livecodebench:release_v6:1873_A` | 52 | 1.000 | 232 / 232 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/0` | 0 |
| `livecodebench:release_v6:1873_B` | 162 | 1.000 | 161 / 161 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/1` | 0 |
| `livecodebench:release_v6:1873_D` | 138 | 1.000 | 270 / 270 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/2` | 0 |
| `livecodebench:release_v6:1883_C` | 82 | 1.000 | 325 / 325 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/3` | 0 |
| `livecodebench:release_v6:1899_A` | 4 | 1.000 | 139 / 139 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/4` | 0 |
| `livecodebench:release_v6:1899_B` | 41 | 1.000 | 410 / 410 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/5` | 0 |
| `livecodebench:release_v6:1899_C` | 82 | 1.000 | 212 / 212 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/6` | 0 |
| `livecodebench:release_v6:1899_D` | 141 | 1.000 | 402 / 402 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/7` | 0 |
| `livecodebench:release_v6:2727` | 1 | 1.000 | 168 / 168 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/8` | 0 |
| `livecodebench:release_v6:2728` | 1 | 1.000 | 170 / 170 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/9` | 0 |
| `livecodebench:release_v6:2730` | 2 | 1.000 | 151 / 151 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/10` | 0 |
| `livecodebench:release_v6:2754` | 1 | 1.000 | 153 / 153 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/11` | 0 |
| `livecodebench:release_v6:2755` | 1 | 1.000 | 182 / 182 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/12` | 0 |
| `livecodebench:release_v6:2756` | 1 | 1.000 | 167 / 167 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/13` | 0 |
| `livecodebench:release_v6:2757` | 2 | 1.000 | 152 / 152 | `rl-code-deepcoder/lcbv5/train-00000-of-00011/14` | 0 |

Coverage is the share of the item's runs found in the document. A value near 1.0 is a full copy; a low value is a short shared passage, for example a common problem statement. The ids above are enough to find the document in the set; the item text stays in Team 9's restricted folder.

## 5. Checks

| Check | Sets passed |
|---|---:|
| `canary_ids_in_input` | 4 of 4 |
| `canary_scan_complete` | 4 of 4 |
| `clean_file_flags_0` | 4 of 4 |
| `docs_match_checker` | 4 of 4 |
| `flagged_count_matches` | 4 of 4 |
| `flagged_ids_in_input` | 4 of 4 |
| `ids_unique` | 4 of 4 |
| `rows_in_eq_kept_plus_removed` | 4 of 4 |

`rows_in_eq_kept_plus_removed`: rows in = rows kept + rows removed. `clean_file_flags_0`: the checker, run again on the clean file, flags 0 of the kept rows. `canary_scan_complete`: `canary_scan.py` read every file (exit 0 or 1). A set with a failed check or a canary is not in this report (the script stops).

## 6. Inputs (to reproduce a run)

| Set | Input file | Bytes | sha256 |
|---|---|---:|---|
| `rl-code-code-contests` | `rl-code-code-contests.jsonl` | 25,783,224 | `08b7a4840bd8ab7cdd18f4cbb38515a620c7c0b316e7f0bf6d4ce9be690da396` |
| `rl-code-codeforces` | `rl-code-codeforces.jsonl` | 9,859,558 | `efe89e87faeba433d8bd560617606749b7314ca06a0fbb73cc81bc5458f9174a` |
| `rl-code-deepcoder` | `rl-code-deepcoder.jsonl` | 47,651,967 | `fe30a2c55dac405bc4ee97be22e53c03dec8dec6f861683dffdb181919a41e8d` |
| `rl-code-swe-envs-g10` | `rl-code-swe-envs-g10.jsonl` | 23,134 | `46e7f7da31612e24e6bbb20231a372bfa052d0f6b2c9c60033f8eaaefa95f002` |

```
python teams/10-post-training/sft/decontam_run.py --set <set-id> --input <set>.jsonl --out-dir decontam_out
python teams/10-post-training/sft/decontam_report.py --records decontam_out --out teams/10-post-training/rl/decontam_report.md --sets <set-id> ... --title "RL decontamination report"
```

## 7. Sets not in the 4-set run (9 Nov)

An `excluded` set is out of training.

| Set | Status | Why |
|---|---|---|
| `rl-code-swe-rebench` | not built | No RL environments from SWE-rebench yet. Each one is gold-checked before use, then checked here. The SFT trajectories are in `sft/decontam_report.md`. |
| `rl-community-alignment` | excluded | Llama-based generation. |
| `rl-safety-hh-rlhf` | excluded | Anthropic closed models. |
| `rl-safety-alignment-faking` | excluded | Claude models. |
| `rl-wildguardmix` | excluded | GPT-4. |

## 8. What this check does not cover

- **Benchmarks outside the set.** This fingerprint set holds 20 benchmark entries: `aime_2024`, `aime_2025`, `bfcl_v3`, `codeforces`, `flores200`, `gaia`, `gpqa_diamond`, `gsm8k`, `heldout_g5_v1`, `hle`, `in22_conv`, `in22_gen`, `livecodebench`, `longbench_v2`, `milu`, `mmlu`, `swe_bench_live`, `swe_bench_pro`, `swe_bench_verified`, `terminal_bench_2`.
  It has no entry for HumanEval, HumanEval+, MBPP, MBPP+, ARC-Challenge, ARC-Easy, HellaSwag, TruthfulQA, MMLU-Pro, BBH, MuSR, Belebele, which Team 9's harnesses run (eval firewall, section 5, known gap), so a clean result says nothing about them.
  `sft_mix_proposal.md` section 1 was corrected on 9 Nov: HumanEval, HumanEval+, MBPP, and MBPP+ are not in this fingerprint set.
- **Paraphrase.** The check finds copied runs of words. A reworded or translated item is not found.
- **Other rows of a set.** Only the rows that were run are covered. A set that was sampled (for example the first rows of a split) is not cleared as a whole.
- **Frozen tokenizer.** The check reads the rendered `text`, so it does not depend on the tokenizer. The effort tiers of the rows do, and Team 3 freezes the tokenizer on Sat 14 Nov.
- **A rerun is needed** when Team 9 publishes a new fingerprint set (a different set_sha256), and for any set whose rows change.

