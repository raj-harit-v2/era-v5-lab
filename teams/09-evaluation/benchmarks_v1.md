# Benchmarks v1 — Team 09 (Evaluation)

Licence and item count for each benchmark in the V5 evaluation suite.
Priority order: Coding & Agentic → Indic → everything else.

Status: ✅ checked against an official source · ⚠️ to be rechecked or licence unclear · ❓ information still to collect.
Use: **Evaluation** = cleared for evaluation · **Internal only** = run internally; never publish its items and never copy its items into this repo · **Decontamination only** = fingerprinted so training data can be checked against it; not evaluated · **Not available** = cannot be run (private) · **Harness check** = run on public models only, to check the harness or a quantization against published scores; not a score for our model.

## 1. Coding & Agentic

| Benchmark | Source | Items | Licence | Status | Use |
|---|---|---|---|---|---|
| SWE-bench Verified | `princeton-nlp/SWE-bench_Verified` | 500 | MIT (SWE-bench code repo; dataset card states none) | ✅ | Evaluation |
| SWE-bench Live | `SWE-bench-Live/SWE-bench-Live` | 300 (Lite) | MIT | ✅ | Evaluation |
| SWE-bench Pro | `ScaleAI/SWE-bench_Pro` | 731 (public set) | MIT (repo); tasks come from copyleft (GPL) projects | ✅ | Evaluation |
| Terminal-Bench 2.0 | `harbor-framework/terminal-bench-2` | 89 | Apache-2.0 | ✅ | Evaluation |
| tau2-bench | `sierra-research/tau2-bench` | 278 (airline 50, retail 114, telecom 114) | MIT | ✅ | Evaluation |
| BFCL v3 | `gorilla-llm/Berkeley-Function-Calling-Leaderboard` | 4,441 | Apache-2.0 | ✅ | Evaluation |
| WebArena | `web-arena-x/webarena` | 812 | Apache-2.0 | ✅ | Evaluation |
| WorkArena | `ServiceNow/WorkArena` | 33 (L1) | Apache-2.0 | ✅ | Evaluation |
| GAIA | `gaia-benchmark/GAIA` | 165 (validation; test 301 has private answers) | Gated terms (not on the accepted list) | ✅ | Internal only |
| BrowseComp | `openai/simple-evals` | 1,266 | MIT | ✅ | Evaluation |
| OSWorld | `xlang-ai/OSWorld` | 369 | Apache-2.0 | ✅ | Evaluation |
| LiveCodeBench | `livecodebench/code_generation_lite` | 1,055 (release_v6) | CONFLICT: code MIT, dataset card "cc" | ⚠️ | Internal only |
| Aider Polyglot | `Aider-AI/polyglot-benchmark` | 225 (cpp 26, go 39, java 47, js 49, python 34, rust 30) | No LICENSE file in repo (exercises adapted from Exercism) | ⚠️ | Internal only |
| Codeforces | `open-r1/codeforces` | 468 (test split) | Card: CC-BY-4.0 (metadata) and ODC-By-4.0 (text), both cover the open-r1 packaging; the problems come from Codeforces | ⚠️ | Internal only |

## 2. Indic

| Benchmark | Source | Items | Licence | Status | Use |
|---|---|---|---|---|---|
| MILU | `ai4bharat/MILU` | 79,608 (test) | CC-BY-4.0 (gated) | ✅ | Evaluation |
| FLORES-200 (FLORES+) | `openlanguagedata/flores_plus` | dev 997 + devtest 1,012 sentences per language | CC-BY-SA-4.0 (gated) | ✅ | Decontamination only |
| IN22-Gen | `ai4bharat/IN22-Gen` | 1,024 sentences × 23 languages | CC-BY-4.0 (gated) | ✅ | Decontamination only |
| IN22-Conv | `ai4bharat/IN22-Conv` | 1,503 turns × 23 languages | CC-BY-4.0 (gated) | ✅ | Decontamination only |
| IndicGenBench | `google-research-datasets/indic-gen-bench` | 29,589 (test, our 10 languages) | Flores-IN, XQuAD-IN: CC-BY-SA-4.0 · XorQA-IN: MIT · CrossSum-IN: CC-BY-NC-SA-4.0 | ✅ | Evaluation |

### Indic coverage — the 10 pack languages (test items per language)

| Benchmark | bn | gu | hi | kn | ml | mr | or | sa | ta | te |
|---|---|---|---|---|---|---|---|---|---|---|
| MILU | 6,637 | 4,826 | 14,831 | 6,234 | 4,321 | 6,924 | 4,525 | — | 6,372 | 7,304 |
| IndicGenBench CrossSum-IN | 155 | 104 | 481 | 500 | 500 | 118 | 500 | 499 | 315 | 212 |
| IndicGenBench Flores-IN (xx→en) | 1,012 | 1,012 | 1,012 | 1,012 | 1,012 | 1,012 | 1,012 | 1,012 | 1,012 | 1,012 |
| IndicGenBench XQuAD-IN | 1,190 | 1,190 | 1,190 | 1,190 | 1,190 | 1,190 | 1,190 | — | 1,190 | 1,190 |
| IndicGenBench XorQA-IN | 539 | 535 | 539 | 536 | 537 | 538 | 537 | 537 | 538 | 539 |
| FLORES+ (dev + devtest) | 2,009 | 2,009 | 2,009 | 2,009 | 2,009 | 2,009 | 2,009 | 2,009 | 2,009 | 2,009 |
| IN22-Gen | 1,024 | 1,024 | 1,024 | 1,024 | 1,024 | 1,024 | 1,024 | 1,024 | 1,024 | 1,024 |
| IN22-Conv | 1,503 | 1,503 | 1,503 | 1,503 | 1,503 | 1,503 | 1,503 | 1,503 | 1,503 | 1,503 |
| ONERULER (long context) | — | — | generated | — | — | — | — | — | generated | — |

bn Bengali · gu Gujarati · hi Hindi · kn Kannada · ml Malayalam · mr Marathi · or Odia · sa Sanskrit · ta Tamil · te Telugu.
— = not covered · generated = synthetic, items are generated at run time · FLORES+ 2,009 = dev 997 + devtest 1,012. FLORES+, IN22-Gen and IN22-Conv are decontamination only.

## 3. Reasoning & Math

| Benchmark | Source | Items | Licence | Status | Use |
|---|---|---|---|---|---|
| AIME 2024 / 2025 | `HuggingFaceH4/aime_2024` + `opencompass/AIME2025` | 30 + 30 | `opencompass/AIME2025` card: MIT; `HuggingFaceH4/aime_2024` card: none stated; the problems are © MAA | ⚠️ | Internal only |
| FrontierMath | `Epoch AI` | 338 (12 public) | Private | ✅ | Not available |
| GSM8K | `openai/gsm8k` | 1,319 (test) | MIT | ✅ | Decontamination only |
| GPQA Diamond | `Idavidrein/gpqa` | 198 | CC-BY-4.0 (gated) | ✅ | Evaluation |
| HLE (text-only) | `cais/hle` | 2,158 (text-only; 342 of the 2,500 have images) | MIT (gated) | ✅ | Evaluation |

## 4. General Knowledge

| Benchmark | Source | Items | Licence | Status | Use |
|---|---|---|---|---|---|
| MMLU | `cais/mmlu` | 14,042 | MIT | ✅ | Evaluation |

## 5. Long context

Approved by the lead: RULER, HELMET, LongBench v2 and ONERULER. ONERULER is kept for its Indic coverage.

| Benchmark | Source | Items | Licence | Status | Use |
|---|---|---|---|---|---|
| RULER | `NVIDIA/RULER` | 13 task configurations (generated per length) | Apache-2.0 | ✅ | Evaluation |
| HELMET | `princeton-nlp/HELMET` | 4,100 at 128K (7 categories, 21 datasets) | MIT (code); data keeps each source dataset's licence | ⚠️ | Internal only |
| LongBench v2 | `zai-org/LongBench-v2` | 503 | Apache-2.0 (dataset card); code MIT | ✅ | Evaluation |
| ONERULER | `mungg/OneRuler` | 7 tasks × 26 languages (kept for Indic coverage: hi, ta) | MIT | ✅ | Evaluation |

## 6. Harness checks

Benchmarks the harness runs on public models (`results/compare_v0.md`, `results/compare_v0_code_indic.md`, eval-mini).

| Benchmark | Source | Items | Licence | Status | Use |
|---|---|---|---|---|---|
| ARC (Challenge, Easy) | `allenai/ai2_arc` | 1,172 + 2,376 (test) | CC-BY-SA-4.0 | ✅ | Harness check |
| HellaSwag | `Rowan/hellaswag` | 10,042 (validation) | Dataset card states none; GitHub blocks the source repo `rowanz/hellaswag` (wikiHow DMCA notice, 14 Sep 2026) | ⚠️ | Internal only |
| TruthfulQA (mc2) | `truthfulqa/truthful_qa` | 817 (validation, multiple_choice) | Apache-2.0 | ✅ | Harness check |
| MMLU-Pro | `TIGER-Lab/MMLU-Pro` | 12,032 (test) | MIT | ✅ | Harness check |
| BBH (Open LLM Leaderboard subset) | `SaylorTwift/bbh` | 5,761 (test, 24 tasks) | MIT (source repo `suzgunmirac/BIG-Bench-Hard`; dataset card states none) | ✅ | Harness check |
| HumanEval / HumanEval+ | `openai/openai_humaneval`; EvalPlus 0.3.1 | 164 | HumanEval MIT; EvalPlus Apache-2.0 | ✅ | Harness check |
| MBPP / MBPP+ | `google-research-datasets/mbpp`; EvalPlus 0.3.1 | 378 (MBPP+ set) | MBPP CC-BY-4.0; EvalPlus Apache-2.0 | ✅ | Harness check |
| Belebele (hi, te, ta) | `facebook/belebele` | 900 per language (test) | CC-BY-SA-4.0 | ✅ | Harness check |

## Decisions (lead, 25 Oct 2026)

1. **Long context:** use RULER, HELMET, LongBench v2 and ONERULER. Keep ONERULER for the Indic coverage.
2. **HLE:** use the text-only part.
3. **Unclear licences** (Aider Polyglot, Codeforces, LiveCodeBench, HELMET, AIME): internal evaluation only. Never publish their items, and never copy their items into the repo. The licence status stays recorded in this doc.
   Why each one: Aider Polyglot has no licence file; LiveCodeBench's code and dataset card disagree; HELMET's data keeps each source's licence. Codeforces and AIME show accepted licences (CC-BY-4.0 / ODC-By-4.0, MIT), but those cover the dataset packaging; the problems themselves come from Codeforces and the MAA.
4. **Accepted licences for evaluation:** MIT, Apache-2.0, CC-BY-4.0, CC-BY-SA-4.0, CC-BY-NC-SA-4.0 and ODC-By-4.0.
5. **GAIA** is internal only (its gated terms are not on the accepted list).
6. **FLORES-200, IN22 and GSM8K** are decontamination only.
7. **Harness checks** (lead, 31 Oct 2026): ARC, TruthfulQA, MMLU-Pro, BBH, HumanEval(+), MBPP(+) and Belebele check the harness and quantizations against published scores on public models. GSM8K stays decontamination only for our model's scores; eval-mini also uses it as a harness check.
8. **HellaSwag** (lead, 31 Oct 2026): internal only. The dataset card states no licence, and GitHub blocks the source repo under a wikiHow DMCA notice (14 Sep 2026). Never copy its items into the repo.

## Verification

Where and when each ✅ row was checked. Hugging Face revisions in sections 1–5 are the ones PR #31 builds its fingerprints from. Section 6 revisions are the ones current on 31 Oct 2026; the harness does not pin dataset revisions.

| Benchmark | Checked at | Split | How | Date |
|---|---|---|---|---|
| SWE-bench Verified | HF `princeton-nlp/SWE-bench_Verified` @ `c104f84`; licence: GitHub `SWE-bench/SWE-bench` @ `02e7a74` | test | count: PR #31 build (500); licence: LICENSE file; dataset card on the HF page has no licence field | 27 Oct 2026 |
| SWE-bench Live | HF `SWE-bench-Live/SWE-bench-Live` @ `b51a864`; licence: GitHub `microsoft/SWE-bench-Live` @ `62d0293` | lite | count: PR #31 registry (lite = 300; it builds lite + verified + test = 1,272 unique); licence: LICENSE file | 27 Oct 2026 |
| SWE-bench Pro | HF `ScaleAI/SWE-bench_Pro` @ `2d52cb3`; licence: GitHub `scaleapi/SWE-bench_Pro-os` @ `66f9276` | test (public v1) | count: PR #31 build (731); licence: LICENSE file | 27 Oct 2026 |
| Terminal-Bench 2.0 | GitHub `harbor-framework/terminal-bench-2` @ `2fd12b8` | all tasks | counted `task.toml` folders (89); LICENSE file | 27 Oct 2026 |
| tau2-bench | GitHub `sierra-research/tau2-bench` @ `9970d4b` | base split | counted `split_tasks.json` (50 + 114 + 114); LICENSE file | 27 Oct 2026 |
| BFCL v3 | GitHub `ShishirPatil/gorilla` @ `cd9429c` (last commit with v3 data); licence @ `6ea5797` | scored v3 categories | counted entries: non-live 1,390 + live 2,251 + multi-turn 800; LICENSE file | 27 Oct 2026 |
| WebArena | GitHub `web-arena-x/webarena` @ `dce0468` | `test.raw.json` | counted tasks (812); LICENSE file | 27 Oct 2026 |
| WorkArena | GitHub `ServiceNow/WorkArena` @ `e885130` | L1 | counted atomic task IDs in `TASK_CATEGORY_MAP` (33); LICENSE file | 27 Oct 2026 |
| GAIA | HF `gaia-benchmark/GAIA` @ `682dd72` | 2023 validation | count: PR #31 build (466 total); released split 165 validation + 301 test; terms: gated dataset page | 27 Oct 2026 |
| BrowseComp | GitHub `openai/simple-evals` @ `652c89d` | all | count: BrowseComp paper, arXiv 2504.12516 (1,266); licence: LICENSE file | 27 Oct 2026 |
| OSWorld | GitHub `xlang-ai/OSWorld` @ `044bc33` | `test_all.json` | counted tasks (369); LICENSE file | 27 Oct 2026 |
| MILU | HF `ai4bharat/MILU` @ `846d701` | test | count: counted per language by us (25 Oct) and PR #31 build (79,608); licence: AI4Bharat MILU README (CC BY 4.0) | 27 Oct 2026 |
| FLORES-200 (FLORES+) | HF `openlanguagedata/flores_plus` @ `e707e62` | dev, devtest | count: PR #31 build (22,099 = 2,009 × 11 languages); licence: OLDI / WMT24 shared-task page (CC BY-SA 4.0) | 27 Oct 2026 |
| IN22-Gen | HF `ai4bharat/IN22-Gen` @ `e042ab3` | test (HF split "train") | count: PR #31 build (1,024); licence: AI4Bharat IndicTrans2 page (CC-BY-4.0) | 27 Oct 2026 |
| IN22-Conv | HF `ai4bharat/IN22-Conv` @ `18cd458` | test (HF split "train") | count: PR #31 build (1,503); licence: AI4Bharat IndicTrans2 page (CC-BY-4.0) | 27 Oct 2026 |
| IndicGenBench | GitHub `google-research-datasets/indic-gen-bench` @ `c96a10d` | test | counted per task and language by us; per-task LICENSE files | 25 Oct 2026 |
| FrontierMath | Epoch AI FrontierMath pages (v2) | — | 338 = 295 (Tiers 1-3) + 43 (Tier 4); 12 public | 27 Oct 2026 |
| GSM8K | HF `openai/gsm8k` @ `740312a`; licence: GitHub `openai/grade-school-math` @ `3101c7d` | test | count: PR #31 build (1,319); licence: LICENSE file | 27 Oct 2026 |
| GPQA Diamond | HF `Idavidrein/gpqa` @ `83022ce` | diamond (inside the extended set PR #31 builds) | count: PR #31 registry (diamond = 198); licence: dataset listing (CC BY 4.0) | 27 Oct (count), 25 Oct 2026 (licence) |
| HLE (text-only) | HF `cais/hle` (PR #31 builds @ `5a81a4c`) | test | counted rows without an image by us (2,158 + 342 = 2,500); licence: dataset card metadata | 25 Oct 2026 |
| MMLU | HF `cais/mmlu` @ `c30699e` | test | count: PR #31 build (14,042); licence: dataset card | 27 Oct (count), 25 Oct 2026 (licence) |
| RULER | GitHub `NVIDIA/RULER` @ `c3f5e3b` | synthetic | 13 tasks in `scripts/synthetic.yaml`; LICENSE file | 27 Oct 2026 |
| LongBench v2 | HF `zai-org/LongBench-v2` @ `2b48e49` | test | count: PR #31 build (503); licence: dataset card (apache-2.0) | 27 Oct 2026 |
| ONERULER | GitHub `mungg/OneRuler` @ `a3fe6af` | synthetic | 26 language folders in the repo; 7 tasks from the ONERULER paper (arXiv 2503.01996); LICENSE file | 27 Oct 2026 |
| ARC | HF `allenai/ai2_arc` @ `210d026` | test (ARC-Challenge, ARC-Easy) | count: HF split sizes; licence: dataset card | 31 Oct 2026 |
| TruthfulQA (mc2) | HF `truthfulqa/truthful_qa` @ `741b827` | validation (multiple_choice) | count: HF split sizes; licence: dataset card | 31 Oct 2026 |
| MMLU-Pro | HF `TIGER-Lab/MMLU-Pro` @ `b189ec7` | test | count: our full gate runs (12,032) and HF split sizes; licence: dataset card | 31 Oct 2026 |
| BBH | HF `SaylorTwift/bbh` @ `b5306be`; licence: GitHub `suzgunmirac/BIG-Bench-Hard` @ `9ee07bd` | test, the 24 tasks of lm-eval `leaderboard_bbh` | count: HF split sizes of the 24 configs in lm-eval 0.4.13 `tasks/leaderboard/bbh_mc/`; licence: LICENSE file | 31 Oct 2026 |
| HumanEval / HumanEval+ | HF `openai/openai_humaneval` @ `7dce605`; GitHub `evalplus/evalplus` (package 0.3.1) | all | count: our EvalPlus runs (164); licence: dataset card (MIT), EvalPlus LICENSE file (Apache-2.0) | 31 Oct 2026 |
| MBPP / MBPP+ | HF `google-research-datasets/mbpp` @ `4bb6404`; GitHub `evalplus/evalplus` (package 0.3.1) | MBPP+ set | count: our EvalPlus runs (378); licence: dataset card (CC-BY-4.0), EvalPlus LICENSE file (Apache-2.0) | 31 Oct 2026 |
| Belebele | HF `facebook/belebele` @ `7899cdf` | test (hin_Deva, tel_Telu, tam_Taml) | count: our eval-mini runs (900 each) and HF split sizes; licence: dataset card | 31 Oct 2026 |