# SFT Mixture Proposal (`sft_mix_proposal.md`)

Shared G10 SFT mixture proposal (`teams/10-post-training/sft/sft_mix_proposal.md`).  
Prepared by **Sai Teja (G10 Lead)** and **Member B** for **Gate 2 (Thu 12 Nov proposal / Sat 14 Nov TSAI decision)**.

---

## 1. Design Goal & Binding Rules

G10 post-trains an **agentic, code-first, multilingual (Indic + English) reasoning model** using `chat_format_v0` on Team 3's frozen `BrahmicTokenizer-131K` (`vocab_size = 131,072`). Every dataset entering the SFT mixture must satisfy four hard gates before conversion by `sft/convert.py`:

1. **Licence & Generator Gate (`licences/licence_table.md` — TSAI Decision, 3 Nov):**
   - **In:** human-written data, execution-verified synthesis, and output of open-weight models whose licence is **MIT or Apache 2.0** and allows training other models on their output. Examples: `gpt-oss` (`Apache-2.0`), `DeepSeek-R1` / `DeepSeek-V3.2` (`MIT`), `Qwen` (`Apache-2.0` versions such as `Qwen3-Coder-480B-A35B-Instruct`, `Qwen3-235B`, `Qwen3-32B`), `QwQ` (`QwQ-32B`, `Apache-2.0`), `Mixtral` / `Mistral` (`Apache-2.0`), `Goedel-Prover-V2-32B` (`Apache-2.0`), `GLM-4.6` / `GLM-5.1` (`MIT`).
   - **Out (`excluded`):**
     1. Output of **closed models** (`OpenAI`, `Anthropic`, `Google`).
     2. Output of **Llama models** (`Llama-2`, `Llama-3`, `Llama-3.1`, `Llama-3.3`).
     3. Output of models with **use-restriction licences such as `OpenRAIL-M`**: **`StarCoder2` is out** (`sft-code-self-oss-instruct` / `bigcode/self-oss-instruct-sc2-exec-filter-50k` -> `excluded`), because its `BigCode OpenRAIL-M` licence makes a model trained on its output a derivative that must carry its use restrictions.
     4. **Unknown generator:** any set whose generator model is unknown / not stated on the card is **out** (`excluded`).
   - **Record:** For every set in `licences/licence_table.md`, both the generator model and its licence are recorded.
2. **Decontamination Gate (`sft/decontam_report.md`):**
   - Every set that has converted chat rows is filtered through Team 9's `decontam_check.py` against `fingerprints/v2` and recorded with its clean `set_sha256`. The v2 set (`set_sha256` `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`) has 20 benchmarks, including SWE-bench Verified/Live/Pro, Terminal-Bench 2, BFCL v3, LiveCodeBench, Codeforces, AIME 2024/2025, GPQA Diamond, MMLU, MILU, FLORES-200, IN22, and GSM8K. It does not include HumanEval, HumanEval+, MBPP, or MBPP+.
3. **ChatML `v0` & Loss Mask Gate (`chat-format/render.py`):**
   - Every sample renders deterministically with exact Team 3 token IDs (`<|im_start|>` `129994`, `<|im_end|>` `130816`, `<|endoftext|>` `130822`, `<|think|>` `130823`, `<|/think|>` `130824`, `<|tool_call|>` `130773`, `<|/tool_call|>` `130825`, `<|tool_result|>` `130774`, `<|/tool_result|>` `130826`).
   - **Loss masks** are `1` strictly on `assistant` turns (`<|think|>...<|/think|>`, `<|tool_call|>...<|/tool_call|>`, and final assistant reply) and `0` on `system`, `user`, and `tool` (`<|tool_result|>...<|/tool_result|>`) turns so the model never learns to hallucinate user prompts or untrusted tool outputs.
4. **Script Integrity Gate (No NFKC; Keep `ZWJ` & `ZWNJ`):**
   - Pre-tokenization preserves `ZWJ` (`U+200D`) and `ZWNJ` (`U+200C`) and never applies NFKC to content, protecting Indic conjuncts (`ind-hi-hplt`, `ind-mr-fw2`, `ind-kn-fw2`, `ind-ta-sangraha-v`, `chandassu`) and mathematical symbols.

---

## 2. Proposed SFT Mixture Shares by Area

Because ERA V5 is an **agentic coding and reasoning model with first-class Indic fluency**, we propose the following 6-area SFT token/trajectory share for TSAI's Gate 2 decision. Safety receives an initial proposed 3%, taken from General; Code, Agentic, Tool Use, and Indic keep their existing shares. This is a proposal, not an experimentally established optimum or clearance to train on pending datasets.

| Area | Proposed Share (%) | Target Role in Post-Training | Primary Approved Datasets (`licences/licence_table.md`) |
| :--- | :---: | :--- | :--- |
| **1. Code** *(Generation, Commits & Competitive Reasoning)* | **35%** | Core polyglot programming, surgical diffs, unit-test synthesis, and long-CoT algorithmic problem solving | `sft-code-opencodereasoning` (`nvidia/OpenCodeReasoning`, `DeepSeek-R1` MIT), `sft-code-opencodereasoning-2` (`nvidia/OpenCodeReasoning-2`, `DeepSeek-R1` MIT + `QwQ-32B` Apache-2.0), `sft-code-codeforces-cots` (`open-r1/codeforces-cots`, `DeepSeek-R1` MIT), `sft-code-commitpackft` (`bigcode/commitpackft`, human commits, MIT) |
| **2. Agentic** *(Multi-Turn SWE & Terminal Trajectories)* | **25%** | Repository navigation, multi-step bash/terminal debugging, fault localization, patch generation, and test verification | `sft-code-swe-rebench-openhands` (`nebius/SWE-rebench-openhands-trajectories`), `sft-code-nemotron-terminal` (`nvidia/Nemotron-Terminal-Corpus`), `sft-code-nemotron-cascade-swe` (`nvidia/Nemotron-Cascade-SFT-SWE`) |
| **3. Tool Use** *(Structured Function Calling & Schema Binding)* | **15%** | Deterministic JSON tool invocation inside `<\|tool_call\|>...<\|/tool_call\|>`, parallel tool `id` binding, and reasoning over `<\|tool_result\|>` | `sft-salesforce-xlam-60k` (`Salesforce/xlam-function-calling-60k`), `sft-agentic-nemotron-agentic-v1` (`nvidia/Nemotron-Agentic-v1`), `sft-agentic-nemotron-sft-agentic-v2-tool-calling` (`nvidia/Nemotron-SFT-Agentic-v2`, tool-calling part only) |
| **4. Indic** *(Native-Script Instruction, Translation & Code-Switching)* | **15%** | Native Indic instruction following across the 10 Brahmic scripts (`hi, mr, ta, te, kn, bn, gu, ml, or, pa`), preserving `ZWJ`/`ZWNJ` and avoiding translationese | `sft-indic-aya-dataset` (`CohereLabs/aya_dataset`), `sft-indic-aya-collection` (`CohereLabs/aya_collection`, 12 templated Indic subsets only) |
| **5. General** *(Math, Science & Calibrated Reasoning Effort)* | **7%** | Formal math proofs, STEM reasoning, general instruction following, and calibrating the four plain-text effort budgets (`1k, 4k, 16k, 64k`) | `sft-stem-code-openthoughts3` (`open-thoughts/OpenThoughts3-1.2M`), `sft-rl-math-openmathreasoning` (`nvidia/OpenMathReasoning`), `sft-math-openr1-math` (`open-r1/OpenR1-Math-220k`), `sft-math-nemotron-math-v2` (`nvidia/Nemotron-Math-v2`), `sft-math-nemotron-proofs` (`nvidia/Nemotron-Math-Proofs-v1`), `sft-science-nemotron-science` (`nvidia/Nemotron-Science-v1`), `sft-bespoke-stratos-17k` (`bespokelabs/Bespoke-Stratos-17k`), `sft-dolly-15k` (`databricks/databricks-dolly-15k`); additions for TSAI decision: `sft-chat-nemotron-if-v1`, `sft-chat-nemotron-if-v2`, `sft-science-nemotron-science-v2`, `sft-science-glm51-phd`, `sft-oasst2` |
| **6. Safety** *(English & Indic Safety Supervision)* | **3% proposed** | Appropriate refusals, helpful answers to benign but sensitive requests, and culturally relevant English/Indic safety supervision | `sft-safety-indicguard`, `sft-safety-nemotron-guard-v3`, `sft-safety-aegis-v1`, `sft-safety-wildjailbreak`, `sft-safety-nemotron-sft-v2`; all `TSAI reserves`, with final dataset/subset selection by TSAI |
| **Total** | **100%** | | |

---

## 3. Rationale for Each Area Share

### Area 1: Code — 35%
- **Why 35%:** The model's primary downstream benchmark suite (`SWE-bench Verified/Live/Pro`, `HumanEval+`, `MBPP+`, `LiveCodeBench`, `Codeforces`) demands strong single-file and multi-file code synthesis before RLVR (`Stage 2`) begins.
- **Composition within the 35%:**
  - **25% Long-CoT Competitive & Algorithmic Code (`OpenCodeReasoning`, `OpenCodeReasoning-2`, `codeforces-cots`):** Generated by `DeepSeek-R1` (`MIT`) and `QwQ-32B` (`Apache-2.0`) under `CC-BY-4.0`. Teaches structured problem decomposition inside `<|think|>...<|/think|>` before emitting code.
  - **10% Real Commit Diffs (`commitpackft`):** Human GitHub commit messages paired with code diffs (`MIT`, generator: `none`), grounding the model in concise patch editing without synthetic verbosity.
  - **Excluded (`self-oss-instruct-sc2-exec-filter-50k`):** Excluded per the 3 Nov TSAI decision because its generator (`StarCoder2-15B`) uses the **BigCode OpenRAIL-M** licence, which has use restrictions and makes a model trained on its output a derivative that must carry those restrictions.

### Area 2: Agentic — 25%
- **Why 25%:** Single-turn code generation does not teach an agent how to inspect a repository, run `pytest`, read a traceback from `<|tool_result|>`, and iterate when a patch fails. A dedicated 25% share of multi-turn trajectories is required so the model enters G10's 20 Docker SWE environments (`swe-envs/`) with a working action-observation loop.
- **Composition within the 25%:**
  - **15% SWE Issue Resolution (`nebius/SWE-rebench-openhands-trajectories`, `nvidia/Nemotron-Cascade-SFT-SWE`):** `SWE-rebench-openhands-trajectories` holds multi-turn OpenHands trajectories generated by `Qwen3-Coder-480B-A35B-Instruct`. `Nemotron-Cascade-SFT-SWE` holds single-turn SWE tasks (localise the bug, repair it, write a test) with responses by `DeepSeek-R1-0528`; it is not an action-observation loop. Both are `CC-BY-4.0`. The Cascade card removes repositories that appear in `SWE-bench Verified`; both sets still go through the Gate 2 decontamination check, and overlapping SWE-reBench issues are de-duplicated by instance id.
  - **10% Terminal & CLI Agent Trajectories (`nvidia/Nemotron-Terminal-Corpus`):** Generated by `DeepSeek-V3.2` (`CC-BY-4.0`), training command-line debugging, file-system manipulation, and recovery from non-zero exit codes.

### Area 3: Tool Use — 15%
- **Why 15%:** `render.py` enforces strict JSON serialization (`sort_keys=True`, optional parallel `id`, `<|tool_call|>\n{...}\n<|/tool_call|>`). Without explicit multi-tool and "when-not-to-call" training, models either emit malformed JSON or call tools unnecessarily.
- **Composition within the 15%:**
  - **8% Execution-Verified Multi-Tool Calls (`Salesforce/xlam-function-calling-60k`):** Generated by open-weight models (`DeepSeek-V2-Chat`, `Mixtral-8x22B`, `CC-BY-4.0`) and verified through Salesforce's APIGen execution checker.
  - **7% Interactive Multi-Turn Tool Agents (`nvidia/Nemotron-Agentic-v1`, `nvidia/Nemotron-SFT-Agentic-v2` tool-calling part only):** `Nemotron-Agentic-v1` is generated and judged by `Qwen3-235B-A22B`, `Qwen3-32B` and `gpt-oss-120b`; the v2 tool-calling part by `DeepSeek-V3.2` and `GLM-4.6` (`CC-BY-4.0` / `Apache-2.0` / `MIT`), covering multi-step tool chaining and user clarification turns. The search and customer-service parts of v2 are `excluded`: their generator models are not stated.

### Area 4: Indic — 15%
- **Why 15%:** `BrahmicTokenizer-131K` allocates dedicated script blocks across 9 Brahmic scripts (`Devanagari`, `Bengali`, `Tamil`, `Telugu`, `Kannada`, `Malayalam`, `Gujarati`, `Gurmukhi`, `Odia`). If SFT is 98% English/code, post-training causes catastrophic forgetting on Indic scripts and breaks `ZWJ`/`ZWNJ` conjunct generation. A 15% Indic share preserves native-script fluency on `MILU` and `IndicGenBench`.
- **Composition within the 15%:**
  - **10% Human-Written Indic Instructions (`CohereLabs/aya_dataset`):** Pure human-written prompts and responses (`Apache-2.0`) with zero translationese (`D5`) or machine-translation damage (`D4`).
  - **5% Curated Indic Task Templates (`CohereLabs/aya_collection`):** Only the 12 templated Indic subsets listed in `licence_table.md` (Hindi, Bengali, Tamil, Telugu; `Apache-2.0`), pre-processed with G10's text-prep rule (strip `U+200B`/`U+FEFF`, preserve `U+200D` ZWJ and `U+200C` ZWNJ, no NFKC). The 19 translated datasets and all other subsets are `excluded`. These subsets are task-style data and cover four of the ten scripts, so if `convert.py` finds too little usable text, the difference moves to `aya_dataset` instead of widening the `aya_collection` list.

### Area 5: General (Math, Science & Effort Calibration) — 7%
- **Why 7%:** Retain a general reasoning and instruction-following supplement while reserving 3% for explicit safety supervision. The primary coding, agentic, tool-use, and Indic shares remain unchanged.
- **Composition within the 7%:**
  - **4.9% Open-Weight Math & STEM CoT (`OpenThoughts3-1.2M`, `OpenMathReasoning`, `OpenR1-Math-220k`, `Bespoke-Stratos-17k`, `Nemotron-Science-v1`, `Nemotron-Math-v2`, `Nemotron-Math-Proofs-v1`):** Generated by `DeepSeek-R1`, `QwQ-32B`, `gpt-oss-120b`, and `Goedel-Prover-V2-32B` (`Apache-2.0`, `CC-BY-4.0`, and `CC-BY-SA-4.0` with attribution). `sft-science-nemotron-science-v2` and `sft-science-glm51-phd` (only the Apache-2.0 `PHD-Science` config of Jackrong/GLM-5.1-Reasoning-1M-Cleaned, generated by GLM-5.1) are additional assessments within this allocation, both `TSAI reserves`; they receive no extra share.
  - **2.1% Concise General Instructions (`databricks-dolly-15k`):** Anchors direct `1k`-effort responses without unnecessary CoT inflation. `NuminaMath-1.5` retains its existing team decision. Dolly has only about 15,000 rows, so if 2.1% would need more than a few epochs of it, the remainder moves to the 4.9% math and STEM line. `sft-chat-nemotron-if-v1`, `sft-chat-nemotron-if-v2` and `sft-oasst2` are additional assessments within this 2.1%, all marked `TSAI reserves`; the two Nemotron chat sets are synthetic, while OASST2 supplies conversational trees with recorded message provenance. Account for shared v1/v2 seeds when selecting the mixture.

### Area 6: Safety (English & Indic) — 3% proposed
- **Why 3%:** Reserve an explicit starting allocation for safe assistant behavior, including appropriate refusal and helpful responses to benign but sensitive requests. Taking this share from General preserves the model's code-first and Indic priorities. The final Gate 2 allocation is TSAI's decision; 3% is a proposal, not a measured optimum.
- **SFT dataset list (all `TSAI reserves`):**
  - `sft-safety-indicguard` (`l3cube-pune/IndicGuard`): Indic/English safety labels and refusal supervision; derived from the Nemotron safety dataset.
  - `sft-safety-nemotron-guard-v3` (`nvidia/Nemotron-Safety-Guard-Dataset-v3`): English/Hindi and multilingual prompt/response safety supervision; derived from AEGIS 2.0.
  - `sft-safety-aegis-v1` (`nvidia/Aegis-AI-Content-Safety-Dataset-1.0`): English dialogue-level guard/classification labels; uses HH-RLHF prompts with Mistral responses. **Text-only: no assistant turn, so it is not SFT chat training data (see note below).**
  - `sft-safety-wildjailbreak` (`allenai/wildjailbreak`): Synthetic safety-response SFT with harmful/benign and vanilla/adversarial categories; generator and access-term facts are recorded for TSAI.
  - `sft-safety-nemotron-sft-v2` (`nvidia/Nemotron-SFT-Safety-v2`): Safe-response SFT for jailbreaks, over-refusal, bias and leakage. English reuses Safety-v1; six translated languages add no Indic coverage. The English teacher is unnamed; Riva-Translate-4B-Instruct-v1.1 translates. Keep shared v1/source content accounted for when selecting data.
- **Training signal:** TSAI selects datasets and subsets after reviewing their licences, generators and intended use. Assistant-response SFT needs reviewed safe demonstrations; guard/classification records need their corresponding task format and label scope. Human safety labels and preference comparisons are different signals, and harmful assistant text is not a desired safe-response target. Balance refusal examples with helpful benign examples to avoid blanket refusal.
- **Allocation:** All five new safety SFT entries remain `TSAI reserves`; this proposal makes no dataset-level exclusion or hold decision. If TSAI selects no safety data, use **0% Safety / 10% General**, with General's prior **7% math/STEM + 3% concise instructions** split. `sft-oasst2` is included under General rather than counted again in Safety.
- **RL / preference perspective (separate from the SFT percentage):** `rl-community-alignment`, `rl-safety-hh-rlhf` and `rl-safety-alignment-faking` are all `TSAI reserves`. Community Alignment provides general cultural preferences; HH-RLHF provides safety/helpfulness preference signals. Anthropic alignment-faking-rl supplies research transcripts from experimental RL runs, with closed-Claude provenance; it is assessed for mitigation/monitoring research rather than presented as ready-made DPO pairs or desired safe-response targets. Preserve its canary/scrambling precautions. Their generator, licence, subset and training-purpose facts are in **Our opinion** in the licence table. The existing `rl-wildguardmix` entry retains its earlier team decision. TSAI decides which data and supervision forms to use; this proposal sets no RL mixture weights and does not treat classification labels as ready-made DPO pairs.

---

## 4. Reasoning Effort Budget Distribution (`1k, 4k, 16k, 64k`)

Every rendered SFT transcript starts with `Reasoning effort: {level}` in the first `system` turn (`render.py`). To ensure the model obeys all four effort budgets at inference time, `sft/convert.py` assigns each sample's effort label from the actual token length of its `<|think|>` + `<|tool_call|>`/`<|tool_result|>` trace and balances the mixture across all four tiers:

| Effort Level | Token Budget (Think + Tool Trace) | Target Share of SFT Mix | Typical Samples Assigned to This Tier |
| :--- | :---: | :---: | :--- |
| `1k` | $\le 1,024$ tokens | **30%** | Direct commits (`commitpackft`), single-turn function calls (`xlam-function-calling-60k`), concise Indic Q&A (`aya_dataset`, `dolly-15k`) |
| `4k` | $1,025 \text{ – } 4,096$ tokens | **35%** | Standard Python/polyglot code synthesis (`self-oss-instruct`), medium math/science problems, 2–4 turn tool interactions (`Nemotron-Agentic-v1`) |
| `16k` | $4,097 \text{ – } 16,384$ tokens | **25%** | Competitive programming CoT (`OpenCodeReasoning`, `codeforces-cots`), multi-step terminal debugging (`Nemotron-Terminal-Corpus`), hard STEM proofs (`OpenThoughts3-1.2M`) |
| `64k` | $16,385 \text{ – } 65,536$ tokens | **10%** | Long-horizon SWE repository trajectories (`SWE-rebench-openhands-trajectories`) and deep self-correcting math/code traces |

---

## 5. Revision note (2 Nov): licence review of five sets

| Set | Change | Reason |
| :--- | :--- | :--- |
| `Nemotron-Cascade-SFT-SWE`, `Nemotron-Agentic-v1`, `Nemotron-SFT-Agentic-v2` | Added to `licence_table.md` with licence, generator and decision | They were in the mix (Agentic and Tool Use, up to 22%) without an entry. Generators are open-weight models, so they pass the Week 2 rule |
| `Nemotron-SFT-Agentic-v2` search and customer-service parts | `excluded`; only the tool-calling part stays | The card names no generator for them |
| `NuminaMath-1.5` | `excluded`; removed from General | Model-written sources (`orca_math` is GPT-4 Turbo), no generator stated, same reason as `NuminaMath-CoT` |
| `aya_collection` | 12 templated Indic subsets stay; the 19 translated datasets and other subsets are `excluded` | The translated sets have untraced English sources, at least one distilled from InstructGPT |
| `sft-code-self-oss-instruct` (`StarCoder2`) | `excluded`; removed from Area 1 (Code) | TSAI decision (3 Nov): `StarCoder2` has the BigCode OpenRAIL-M licence, which makes a model trained on its output a derivative carrying its use restrictions |
| Open-weight generators with MIT or Apache-2.0 licences (`gpt-oss`, `DeepSeek-R1`, `Qwen` Apache-2.0 versions, `QwQ`, `Mixtral`) | Approved (`IN`) with generator model + generator licence recorded in `licence_table.md` | TSAI decision (3 Nov): open-weight models whose licence is MIT or Apache-2.0 and allows training other models on their output are in; unknown generators are out (`excluded`) |

The five-set licence review above left the shares unchanged at that revision. The safety addition below revises General and introduces a conditional Safety share. Two quantity risks remain open: Indic (`aya_collection` is narrower than assumed) and General (`dolly-15k` is small). `convert.py` row counts will show whether they hold.

## 6. Revision note (3 Nov): safety datasets for SFT and RL

- Propose **3% Safety**, funded by reducing General from **10% to 7%**. Shares are **Code 35%, Agentic 25%, Tool Use 15%, Indic 15%, General 7%, Safety 3%**, totaling **100%**. The four effort-tier shares remain unchanged and apply across the area mix, not in addition to it.
- All **13 new dataset assessments** are marked **`TSAI reserves`**. Earlier team decisions on existing datasets remain unchanged. Generator, licence and intended-use facts are recorded for TSAI rather than assigned new exclusion or hold recommendations.
- Record the RL safety/preference assessments separately from the SFT allocation. The supporting Nemotron chat, Science-v2, GLM-5.1 `PHD-Science` and OASST2 assessments fit within General's 7% budget.
- Remove BeaverTails and PKU-SafeRLHF from these additions because both carry CC-BY-NC-4.0. Named Kolibri use was not confirmed, so no PKU exception is added.
- The separate safety evaluation list remains removed. The specifically requested alignment-faking-rl research artifact is documented in Stage 2 with its actual purpose and generator provenance.
- **Commercial permission and lab eligibility are separate:** Anthropic/hh-rlhf is MIT-licensed, and Anthropic/alignment-faking-rl is CC-BY-4.0; those published licences permit commercial reuse subject to their terms. WildJailbreak's ODC-By licence covers database rights, not every right in its individual contents, and its Ai2 access conditions also apply. Closed-model provenance does not itself make a dataset non-commercial, but the week 2 rule still excludes closed-model-generated text. Keep these assessments as `TSAI reserves`; any exception to that rule requires an explicit TSAI decision before training. [HH-RLHF licence](https://github.com/anthropics/hh-rlhf/blob/master/LICENSE), [alignment-faking-rl card](https://huggingface.co/datasets/Anthropic/alignment-faking-rl), [CC-BY-4.0 terms](https://creativecommons.org/licenses/by/4.0/), [WildJailbreak card](https://huggingface.co/datasets/allenai/wildjailbreak), [ODC-By scope](https://opendatacommons.org/licenses/by/1-0/).
- **Alignment-faking-rl training purpose:** Commercial reuse permission does not make its experimental evaluation transcripts desired safe-response demonstrations. The release contains misaligned reasoning and uses canaries/scrambling to limit accidental training contamination; preserve those precautions. TSAI decides whether it has a suitable mitigation/research role or any approved post-training use.

## 7. Revision note (6 Nov): Indic quantity check

Row counts for the Indic area, read from the Hugging Face datasets-server statistics and from `convert.py` runs on 6 Nov. Shares are not changed here.

| Set | Rows for the ten proposal languages | Notes |
| :--- | ---: | :--- |
| `sft-indic-aya-dataset` | 41,261 | Tamil 14,133, Telugu 8,439, Panjabi 6,385, Gujarati 3,989, Marathi 3,545, Malayalam 1,749, Bengali 1,534, **Hindi 1,153**, Kannada 334, **Odia 0**. Single turn |
| `sft-indic-aya-collection` (12 templated subsets) | 688,637 | 467,090 are `templated_telugu_news` and 170,848 are Hindi news or headlines (68% and 25%). Task-style, four scripts |
| `sft-indic-indic-align-oasst-t` (new) | 19,909 | Human-written oasst1 conversations translated by IndicTrans2 (MIT). One language per conversation, about 2,000 each, Odia included. 12,686 have two or more assistant turns |
| `sft-indic-indic-align-dolly-t` (new) | 10,541 of 15,011 | Human-written Dolly translated by IndicTrans2. 4,455 rows lost their context passage in translation; `convert.py` drops them (9 Nov) |

What this means for the 15%:

- **Human-written Indic chat is small and uneven.** `aya_dataset` has 1,153 Hindi rows and none in Odia, while Tamil alone is a third of it. Adding `oasst-t` gives the area its only multi-turn data and a near-even spread over the ten languages, roughly half again as many conversations as `aya_dataset`.
- **`aya_collection` must be capped per subset.** Without a cap, Telugu news is two thirds of the Indic area. A cap of a few thousand rows per subset keeps the 12 subsets as task variety, not as the bulk.
- **Proposed composition inside the 15%:** `aya_dataset` (all rows), `oasst-t` (all rows), `aya_collection` (capped per subset), `dolly-t` (10,541 rows after the context filter). All of them are short (effort `1k`), so the Indic share adds no long-reasoning data.
- **Decontamination:** `oasst-t` was run on 6 Nov with fingerprints v2, full set: 9 of 19,909 rows flagged (`in22_conv`, `hle`) and removed, 0 canary, 19,900 kept. `dolly-t` was run on 9 Nov after the context filter: 0 of 10,541 flagged, 0 canary.

## 8. Revision note (9 Nov): three more checks, and sets that are out

The area shares stay **35 / 25 / 15 / 15 / 7 / 3**. Kept-row counts are not those shares.

Added to `sft/decontam_report.md` on 9 Nov, same fingerprints, 0 canaries:

| Set | Scope | Removed | Kept |
|---|---|---:|---:|
| `sft-code-commitpackft` | python split | 15 of 56,025 (0.03%) | 56,010 |
| `sft-code-opencodereasoning-2` | all 70 python shards; questions joined from TACO, APPS, and code_contests | 115,067 of 542,219 (21.22%) | 427,152 |
| `sft-math-nemotron-proofs-v3-sft` | first of 10 parts; only rows that fit the 64k budget | 42 of 1,757 (2.39%) | 1,715 |

All 70 OpenCodeReasoning-2 python shards are converted. Of the 1,398,166 raw rows, 268,752 are upstream test splits, 3,629 are protected family, 513,809 fail the quality proposal and 69,690 are held because the `open-r1/codeforces` revision is not established; 542,286 join, 67 are rejected by the converter and 542,219 reach the scan, with 0 canaries. The joined rows are 19,825 distinct problems by position (19,340 by content at Jaccard 0.8). The 427,152 kept rows are 15,670 problems by position and 15,402 by content at Jaccard 0.8, about 2.54B trained tokens (2,539,177,884). In the proofs part, 18,266 of 20,023 source rows were over 64k and were not converted, so they were not checked.

`sft-safety-aegis-v1` has no assistant turn. Its stored `text` column was still checked on 9 Nov (11,997 rows, 2 removed, 0 canary). That does not make it chat training data. `sft-safety-indicguard`, `sft-safety-nemotron-guard-v3`, `sft-safety-wildjailbreak`, `sft-safety-nemotron-sft-v2`, and `sft-code-self-oss-instruct` are `excluded`. So are `rl-community-alignment`, `rl-safety-hh-rlhf`, `rl-safety-alignment-faking`, and `rl-wildguardmix`. Until TSAI names an allowed safety set with chat rows, use the section 6 fallback: **0% Safety / 10% General**.
