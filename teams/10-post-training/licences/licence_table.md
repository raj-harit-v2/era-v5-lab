# Licence table and strategy v0

Shared G10 licence file (`teams/10-post-training/licences/licence_table.md`).

## Team workflow (Core Team · 12 members)

- Keep this **one shared file** (`teams/10-post-training/licences/licence_table.md`).
- Give it **one section for each dataset** (for example `StarCoder`, `Stack Exchange`, `Indic web`).
- Each of the 12 G10 Core Team members adds the licence, source, and decision (`TSAI reserves`) for their own dataset in their own section by pull request to the lead's branch (`g10-week1-post-training`).
- The team lead (Sai Teja) merges the member PRs, removes duplicates in the consolidated licence table, and opens one PR to `theschoolofai/era-v5-lab` `main`.

---

## Consolidated licence table (deduplicated across datasets)

Three stages. Sets marked `excluded` stay in the table with the reason and are not used in any training mix (TSAI ruling, G10 chat, 30 Oct).

### Stage 0: Foundation data (pre-training and continual pre-training)

| Set | Source | Language | Licence | Decision |
| --- | --- | --- | --- | --- |
| code-python | bigcode/starcoderdata | Code | other (per-file permissive Stack licences; attribution required) | TSAI reserves |
| chandassu | BodduSriPavan111/chandassu | Telugu | MIT (commercial use allowed) | TSAI reserves |
| ind-mr-fw2 | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | Marathi (mr) | ODC-By v1.0 (commercial use permitted with attribution) | TSAI reserves |
| ind-ta-sangraha-v | [ai4bharat/sangraha](https://huggingface.co/datasets/ai4bharat/sangraha) | Tamil (ta) | CC-BY-4.0 (commercial use permitted with attribution) | TSAI reserves |
| ind-hi-hplt | [data.hplt-project.org/three/sorted/hin_Deva](https://data.hplt-project.org/three/sorted/hin_Deva) | Hindi (hi) | CC0-1.0 (packaging) / Web terms | TSAI reserves |
| ind-hi-indiccorp | [ai4bharat/IndicCorpV2](https://huggingface.co/datasets/ai4bharat/IndicCorpV2) | Hindi (hi) | CC-BY-4.0 (commercial use permitted with attribution) | TSAI reserves |
| ind-kn-fw2 | [HuggingFaceFW/fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | Kannada (kn) | ODC-By v1.0 (commercial use permitted with attribution) | TSAI reserves |
| code-go | bigcode/starcoderdata | Code (Go) | other (per-file permissive Stack licences; attribution required) | TSAI reserves |
| code-js-ts | bigcode/starcoderdata | Code (JavaScript / TypeScript) | other (per-file upstream licensing; attribution and training-use rights require further verification) | TSAI reserves |

### Stage 1: Supervised fine-tuning (SFT) instruction mixture

| Set | Source | Language | Generator model | Licence | Decision |
| --- | --- | --- | --- | --- | --- |
| sft-code-commitpackft | [bigcode/commitpackft](https://huggingface.co/datasets/bigcode/commitpackft) | Code (350+ languages) | none (real human GitHub commits; no model generator) | mit (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-code-self-oss-instruct | [bigcode/self-oss-instruct-sc2-exec-filter-50k](https://huggingface.co/datasets/bigcode/self-oss-instruct-sc2-exec-filter-50k) | Code (Python) | StarCoder2-15B (BigCode OpenRAIL-M licence — has use restrictions; makes a model trained on its output a derivative carrying those restrictions) via SelfCodeAlign (arXiv 2410.24198) | odc-by (Hub tag on dataset; generator model is BigCode OpenRAIL-M) | excluded |
| sft-code-magicoder-oss | [ise-uiuc/Magicoder-OSS-Instruct-75K](https://huggingface.co/datasets/ise-uiuc/Magicoder-OSS-Instruct-75K) | Code (polyglot) | GPT-3.5 (OpenAI, proprietary closed licence) | mit (Hub tag; commercial use permitted per tag) | excluded |
| sft-code-codefeedback | [m-a-p/CodeFeedback-Filtered-Instruction](https://huggingface.co/datasets/m-a-p/CodeFeedback-Filtered-Instruction) | Code (polyglot) | Mixed upstream sets (Magicoder, Evol-Instruct code, ShareGPT — GPT-3.5 / GPT-4, OpenAI proprietary closed); Qwen-72B-Chat (Tongyi Qianwen Research/Commercial Licence, not MIT/Apache-2.0) used as filter | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-rl-code-rstar-coder | [microsoft/rStar-Coder](https://huggingface.co/datasets/microsoft/rStar-Coder) | Code (competitive) | GPT-4o (OpenAI, proprietary closed) for problem synthesis and test-input generators; QwQ-32B (Apache-2.0) for the long-reasoning solutions (paper, arXiv 2505.21297) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-code-swe-rebench-openhands | [nebius/SWE-rebench-openhands-trajectories](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories) | Code (agent trajectories) | Qwen3-Coder-480B-A35B-Instruct (Apache-2.0, open weights) via OpenHands | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-code-nemotron-cp-v2 | [nvidia/Nemotron-SFT-Competitive-Programming-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Competitive-Programming-v2) | Code (competitive, SQL) | Unknown on card (Competitive subset: model not named, DeepSeek-R1-0528 MIT cited; Exercism subset: synthetic, model not named; Text-to-SQL: LLM not named) | cc-by-4.0, odc-by, mit (Hub tag; commercial use permitted per tag) | excluded |
| sft-code-nemotron-swe-v3 | [nvidia/Nemotron-SFT-SWE-v3](https://huggingface.co/datasets/nvidia/Nemotron-SFT-SWE-v3) | Code (agent trajectories) | Unknown on card (names only OpenHands, SWE-agent and mini-SWE-agent harnesses; generator model not stated on the dataset card) | cc-by-4.0, apache-2.0, mit, bsd-3-clause, bsd-2-clause (Hub tag; commercial use permitted per tag) | excluded |
| sft-code-nemotron-cascade-swe | [nvidia/Nemotron-Cascade-SFT-SWE](https://huggingface.co/datasets/nvidia/Nemotron-Cascade-SFT-SWE) | Code (SWE localisation, repair, test generation) | DeepSeek-R1-0528 (MIT, open weights) writes every response (the card's `generator` field) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-agentic-nemotron-agentic-v1 | [nvidia/Nemotron-Agentic-v1](https://huggingface.co/datasets/nvidia/Nemotron-Agentic-v1) | English / tool use and conversational agents | Qwen3-235B-A22B-Thinking-2507 (Apache-2.0), Qwen3-235B-A22B-Instruct-2507 (Apache-2.0), Qwen3-32B (Apache-2.0) and GPT-OSS-120B (Apache-2.0) simulate and judge the dialogues | cc-by-4.0 (Hub tag; the card adds apache-2.0 for the Glaive-Function-Calling-v2 part) | TSAI reserves |
| sft-agentic-nemotron-sft-agentic-v2-tool-calling | [nvidia/Nemotron-SFT-Agentic-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Agentic-v2) (tool-calling part only) | English / tool use | DeepSeek-V3.2 (MIT) and GLM-4.6 (MIT, open weights) simulate and judge | cc-by-4.0, apache-2.0, mit (Hub tags; commercial use permitted per tag) | TSAI reserves |
| sft-agentic-nemotron-sft-agentic-v2-other | [nvidia/Nemotron-SFT-Agentic-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Agentic-v2) (search and customer-service parts) | English / web search, customer service | Unknown (not stated on the card for either part) | cc-by-4.0, apache-2.0, mit (Hub tags) | excluded |
| sft-code-nemotron-terminal | [nvidia/Nemotron-Terminal-Corpus](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus) | Code (terminal agent) | DeepSeek-V3.2 (MIT, open weights) for both the synthetic tasks and the trajectories (paper, arXiv 2602.21193) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-code-opencodereasoning | [nvidia/OpenCodeReasoning](https://huggingface.co/datasets/nvidia/OpenCodeReasoning) | Code (competitive) | DeepSeek-R1 (MIT, open weights) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-code-opencodereasoning-2 | [nvidia/OpenCodeReasoning-2](https://huggingface.co/datasets/nvidia/OpenCodeReasoning-2) | Code (competitive) | DeepSeek-R1 (MIT) for solutions, QwQ-32B (Apache-2.0) for critiques (both open weights) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | allowed (TSAI admitted, 11 Nov 2026) |
| sft-code-codeforces-cots | [open-r1/codeforces-cots](https://huggingface.co/datasets/open-r1/codeforces-cots) | Code (competitive) | DeepSeek-R1 (MIT, open weights) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-indic-aya-collection | [CohereLabs/aya_collection](https://huggingface.co/datasets/CohereLabs/aya_collection) (12 reviewed: 10 with permissive source licences, 1 excluded, 1 pending TSAI) | Indic, multilingual | none (human speaker-written templates applied to human-annotated Indic NLP datasets) | apache-2.0 (Hub tag); source licences reviewed in [PR #399](https://github.com/theschoolofai/era-v5-lab/pull/399) | TSAI reserves |
| sft-indic-aya-collection-other | [CohereLabs/aya_collection](https://huggingface.co/datasets/CohereLabs/aya_collection) (all 19 translated datasets and the other templated subsets) | 101 languages | NLLB-3.3B (CC-BY-NC-4.0, non-commercial) machine translation; upstream English generator models not stated on the card | apache-2.0 (Hub tag) | excluded |
| sft-indic-aya-dataset | [CohereLabs/aya_dataset](https://huggingface.co/datasets/CohereLabs/aya_dataset) | Multilingual incl. Indic | none (human-written annotations; no model generator) | apache-2.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-indic-indic-align | [ai4bharat/indic-align](https://huggingface.co/datasets/ai4bharat/indic-align) | 14 Indic languages | Llama-2-70B-Chat (Llama 2 Community Licence, use restrictions) for many parts; Mistral-7B (Apache-2.0) in some parts | cc-by-4.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-indic-indic-align-oasst-t | [ai4bharat/indic-align](https://huggingface.co/datasets/ai4bharat/indic-align) | 14 Indic languages (`OpenAssistant_T` subset only) | none for the text (human-written OpenAssistant v1 conversations); translated with IndicTrans2 (MIT, open weights) | cc-by-4.0 (Hub tag); source oasst1 apache-2.0 | TSAI reserves |
| sft-indic-indic-align-dolly-t | [ai4bharat/indic-align](https://huggingface.co/datasets/ai4bharat/indic-align) | 14 Indic languages (`Dolly_T` subset only) | none for the text (human-written databricks-dolly-15k); translated with IndicTrans2 (MIT, open weights) | cc-by-4.0 (Hub tag); source dolly cc-by-sa-3.0 (share-alike, attribution needed) | allowed (CC-BY-SA, attribution needed) |
| sft-indic-samvaad-hi | [sarvamai/samvaad-hi-v1](https://huggingface.co/datasets/sarvamai/samvaad-hi-v1) | Hindi, English, Hinglish | Unknown (not stated on the card or in Sarvam's announcement) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-indic-code-oss-codes-coding | [oss-codes/Coding-Conversational-Dataset-Indic](https://huggingface.co/datasets/oss-codes/Coding-Conversational-Dataset-Indic) | Indic (Hindi, Tamil, ...) + code | Unknown (not stated; the card is empty) | mit (Hub tag; commercial use permitted per tag) | excluded |
| sft-indic-code-oss-codes-cs | [oss-codes/Computer-Science-Conversational-Dataset-Indic](https://huggingface.co/datasets/oss-codes/Computer-Science-Conversational-Dataset-Indic) | Indic + computer science | Unknown (not stated; the card is empty) | mit (Hub tag; commercial use permitted per tag) | excluded |
| sft-indic-math-orca-math-hi | [BhabhaAI/orca-math-word-problems-200k-hindi-filtered](https://huggingface.co/datasets/BhabhaAI/orca-math-word-problems-200k-hindi-filtered) | Hindi (math) | GPT-4 (OpenAI, proprietary closed) via Orca-Math, then translated | mit (Hub tag; commercial use permitted per tag) | excluded |
| sft-indic-math-aryabhatta-orca-hi | [GenVRadmin/Aryabhatta-Orca-Maths-Hindi](https://huggingface.co/datasets/GenVRadmin/Aryabhatta-Orca-Maths-Hindi) | Hindi (math) | GPT-4 (OpenAI, proprietary closed) via Orca-Math, then translated | mit (Hub tag; commercial use permitted per tag) | excluded |
| sft-math-nemotron-proofs | [nvidia/Nemotron-Math-Proofs-v1](https://huggingface.co/datasets/nvidia/Nemotron-Math-Proofs-v1) | English / Mathematics | gpt-oss-120b (Apache-2.0) for statement formalisation and Goedel-Prover-V2-32B (Apache-2.0) for proofs | cc-by-sa-4.0 (Hub tag; share-alike, attribution needed) | allowed (CC-BY-SA, attribution needed) |
| sft-math-nemotron-math-v2 | [nvidia/Nemotron-Math-v2](https://huggingface.co/datasets/nvidia/Nemotron-Math-v2) | English / Mathematics | gpt-oss-120b (Apache-2.0, open weights) for all solution traces | cc-by-4.0, cc-by-sa-4.0 (Hub tag; share-alike, attribution needed) | allowed (CC-BY-SA, attribution needed) |
| sft-math-openmathinstruct-2 | [nvidia/OpenMathInstruct-2](https://huggingface.co/datasets/nvidia/OpenMathInstruct-2) | English / Mathematics | Llama-3.1-405B-Instruct (Llama 3.1 Community Licence) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-rl-math-openmathreasoning | [nvidia/OpenMathReasoning](https://huggingface.co/datasets/nvidia/OpenMathReasoning) | English / Mathematics | DeepSeek-R1 (MIT) and QwQ-32B (Apache-2.0, both open weights) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-math-openr1-math | [open-r1/OpenR1-Math-220k](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k) | English / Mathematics | DeepSeek-R1 (MIT, open weights) | apache-2.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-math-numinamath-1.5 | [project-numina/NuminaMath-1.5](https://huggingface.co/datasets/project-numina/NuminaMath-1.5) | English / Mathematics | Unknown / closed (orca_math uses GPT-4 Turbo, OpenAI closed; synthetic_math and metamath generators not stated) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-math-numinamath-cot | [project-numina/NuminaMath-CoT](https://huggingface.co/datasets/project-numina/NuminaMath-CoT) | English / Mathematics | GPT-4 and GPT-4o (OpenAI, proprietary closed) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-stem-code-nemotron-post-v1 | [nvidia/Nemotron-Post-Training-Dataset-v1](https://huggingface.co/datasets/nvidia/Nemotron-Post-Training-Dataset-v1) | English / Math, STEM, Code | DeepSeek-R1-0528 (MIT) and Qwen3-235B-A22B (Apache-2.0); built for Llama-3.3-Nemotron-Super under NVIDIA/Llama terms | cc-by-4.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-stem-code-nemotron-post-v2 | [nvidia/Nemotron-Post-Training-Dataset-v2](https://huggingface.co/datasets/nvidia/Nemotron-Post-Training-Dataset-v2) | Multilingual / Math, STEM, Code | DeepSeek-R1-0528 (MIT), Qwen3-235B-A22B (Apache-2.0), Qwen3-30B-A3B (Apache-2.0), Qwen2.5-14B-Instruct (Apache-2.0) and Qwen2.5-32B-Instruct-AWQ (Apache-2.0); card does not map models to subsets | cc-by-4.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-stem-code-openthoughts3 | [open-thoughts/OpenThoughts3-1.2M](https://huggingface.co/datasets/open-thoughts/OpenThoughts3-1.2M) | English / Math, Code, Science | QwQ-32B (Apache-2.0, open weights) | apache-2.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-science-nemotron-science | [nvidia/Nemotron-Science-v1](https://huggingface.co/datasets/nvidia/Nemotron-Science-v1) | English / Science | gpt-oss-120b (Apache-2.0, open weights) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-openhermes-2.5 | [teknium/OpenHermes-2.5](https://huggingface.co/datasets/teknium/OpenHermes-2.5) | English / Multi-domain | GPT-4 (OpenAI, proprietary closed), Mixtral-8x7B (Apache-2.0), and Llama (Llama licence) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-tulu3-filtered | [allenai/tulu-3-sft-mixture](https://huggingface.co/datasets/allenai/tulu-3-sft-mixture) | English / Multi-domain | Llama-3.1-70B / Llama-3.1-405B (Llama 3.1 Community Licence) and GPT-4o (OpenAI, closed) | odc-by (Hub tag; commercial use permitted per tag) | excluded |
| sft-dolly-15k | [databricks/databricks-dolly-15k](https://huggingface.co/datasets/databricks/databricks-dolly-15k) | English | none (human-written by Databricks employees; no model generator) | cc-by-sa-3.0 (Hub tag; share-alike, attribution needed) | allowed (CC-BY-SA, attribution needed) |
| sft-lmsys-chat-1m | [lmsys/lmsys-chat-1m](https://huggingface.co/datasets/lmsys/lmsys-chat-1m) | Multilingual | Closed & Llama models in Chatbot Arena (custom non-standard LMSYS agreement) | LMSYS Agreement (custom terms, not standard permissive) | excluded |
| sft-bespoke-stratos-17k | [bespokelabs/Bespoke-Stratos-17k](https://huggingface.co/datasets/bespokelabs/Bespoke-Stratos-17k) | English / STEM Reasoning | DeepSeek-R1 (MIT, open weights) | apache-2.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-numinamath-tir | [AI-MO/NuminaMath-TIR](https://huggingface.co/datasets/AI-MO/NuminaMath-TIR) | English / Python Math Tools | GPT-4 (OpenAI, proprietary closed) generated Python tool-integrated reasoning traces | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-ultradata-cot-agent | [openbmb/UltraInteract_sft](https://huggingface.co/datasets/openbmb/UltraInteract_sft) | English / Code & Reasoning | GPT-3.5 / GPT-4 (OpenAI, proprietary closed) in OpenBMB UltraInteract tree construction | mit (Hub tag; commercial use permitted per tag) | excluded |
| sft-glaive-fc-v2 | [glaiveai/glaive-function-calling-v2](https://huggingface.co/datasets/glaiveai/glaive-function-calling-v2) | JSON / Tool Calls | Unknown (synthetic schema generator by Glaive AI; generator model and its licence are not named on the card) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-salesforce-xlam-60k | [Salesforce/xlam-function-calling-60k](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k) | Multi-tool / API | Mixtral-8x22B-Instruct (Apache-2.0, open weights) and DeepSeek-V2-Chat (DeepSeek Licence; keep only Mixtral-8x22B-Instruct Apache-2.0 rows if split by generator) via Salesforce APIGen (arXiv 2406.18518) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-code-swe-gym-trajectories | [SWE-Gym/OpenHands-SFT-Trajectories](https://huggingface.co/datasets/SWE-Gym/OpenHands-SFT-Trajectories) | Code / Python SWE | Claude 3.5 Sonnet (Anthropic, proprietary closed) and GPT-4o (OpenAI, closed) via OpenHands | mit (Hub tag; commercial use permitted per tag) | excluded |
| sft-chat-nemotron-if-v1 | [nvidia/Nemotron-Instruction-Following-Chat-v1](https://huggingface.co/datasets/nvidia/Nemotron-Instruction-Following-Chat-v1) | English / Chat, instruction following, JSON | GPT-OSS-120B (Apache-2.0), Qwen3-235B-A22B-Thinking-2507 (Apache-2.0), Qwen3-235B-A22B-Instruct-2507 (Apache-2.0) for chat split; structured-outputs split has unknown generator (exclude structured-outputs split) | ODC-By-1.0 (chat); CC-BY-4.0 (structured outputs) | TSAI reserves |
| sft-chat-nemotron-if-v2 | [nvidia/Nemotron-SFT-Instruction-Following-Chat-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Instruction-Following-Chat-v2) | English / Chat, instruction following | Kimi-K2-Thinking (Modified MIT), GLM-4.6 (MIT), Qwen3-235B-A22B-Thinking-2507 (Apache-2.0), GPT-OSS-120b (Apache-2.0), Kimi-K2-Instruct-0905 (Modified MIT), Qwen3-235B-A22B-Instruct-2507 (Apache-2.0) | ODC-By (card does not specify version) | TSAI reserves |
| sft-science-nemotron-science-v2 | [nvidia/Nemotron-SFT-Science-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2) | English / Physics, biology, chemistry | GPT-OSS (Apache-2.0), Kimi-K2-Instruct (Modified MIT), DeepSeek-V3.2 (MIT), DeepSeek-V4-Pro (MIT) | CC-BY-SA-4.0 (attribution and share-alike obligations) | allowed (CC-BY-SA, attribution needed) |
| sft-safety-indicguard | [l3cube-pune/IndicGuard](https://huggingface.co/datasets/l3cube-pune/IndicGuard) | 10 Indic languages + English reference | Google Translate API (Google, closed) + unnamed LLMs (unknown generator) | CC-BY-4.0 | excluded |
| sft-safety-nemotron-guard-v3 | [nvidia/Nemotron-Safety-Guard-Dataset-v3](https://huggingface.co/datasets/nvidia/Nemotron-Safety-Guard-Dataset-v3) | English, Hindi + 10 other languages | Mixtral-8x22B (Apache-2.0) and Mixtral-8x7B (Apache-2.0), but uses Google Translate (Google, closed) and Llama/Nemotron jury (Llama licence) | CC-BY-4.0 | excluded |
| sft-safety-aegis-v1 | [nvidia/Aegis-AI-Content-Safety-Dataset-1.0](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-1.0) | Primarily English | Mistral-7B-v0.1 (Apache-2.0) responses with NVIDIA human safety annotations (prompts from HH-RLHF, MIT) | CC-BY-4.0; card also contains research-purpose/dialogue-training restrictions | TSAI reserves |
| sft-oasst2 | [OpenAssistant/oasst2](https://huggingface.co/datasets/OpenAssistant/oasst2) | Multilingual; English, sparse Hindi/Bengali | none for human turns (`synthetic=False`, human-written crowdsourced messages; filter out any `synthetic=True` nodes) | Apache-2.0 | TSAI reserves |
| sft-safety-wildjailbreak | [allenai/wildjailbreak](https://huggingface.co/datasets/allenai/wildjailbreak) | English | GPT-4 and GPT-3.5 (OpenAI, proprietary closed) + Mixtral-8x7B (Apache-2.0) | ODC-By; gated AI2 conditions | excluded |
| sft-safety-nemotron-sft-v2 | [nvidia/Nemotron-SFT-Safety-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Safety-v2) | English, German, Spanish, French, Japanese, Italian, Chinese | Unknown English response/reasoning generator (not named on the card); Riva-Translate-4B-Instruct-v1.1 translates | CC-BY-4.0; additional Apache-2.0 / MIT terms | excluded |
| sft-science-glm51-phd | [Jackrong/GLM-5.1-Reasoning-1M-Cleaned](https://huggingface.co/datasets/Jackrong/GLM-5.1-Reasoning-1M-Cleaned) | Science; release language tags: English / Chinese | GLM-5.1 (MIT, open weights) generates reasoning and final answers (`PHD-Science` Apache-2.0 config only) | Apache-2.0 (cleaned and upstream publisher cards) | TSAI reserves |
| sft-code-nemotron-opencode | [nvidia/Nemotron-SFT-OpenCode-v1](https://huggingface.co/datasets/nvidia/Nemotron-SFT-OpenCode-v1) | English / Code (agentic CLI, tool use, agent skills) | gpt-oss-120b (Apache-2.0, open weights) writes the questions and agent skills; Qwen3-Coder-480B-A35B-Instruct (Apache-2.0, open weights) writes the solution traces | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-code-nemotron-cuda | [nvidia/Nemotron-SFT-CUDA-v1](https://huggingface.co/datasets/nvidia/Nemotron-SFT-CUDA-v1) | English / Code (CUDA kernels) | GLM-4.7 (MIT, open weights) writes the problems and the solutions; only runs that pass the hidden tests with no Compute-Sanitizer errors are kept (execution-verified) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-math-nemotron-sft-math-v4 | [nvidia/Nemotron-SFT-Math-v4](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4) | English / Mathematics | DeepSeek-V4-Pro (MIT, open weights) writes all solutions; problems are human-written (AoPS, Math StackExchange) and only solutions that match the reference answer are kept | cc-by-4.0 (AoPS-derived), cc-by-sa-4.0 (Math StackExchange-derived) (Hub tags; share-alike on part, attribution needed) | allowed (CC-BY-SA, attribution needed) |
| sft-math-nemotron-proofs-v3-sft | [nvidia/Nemotron-Math-Proofs-v3-SFT](https://huggingface.co/datasets/nvidia/Nemotron-Math-Proofs-v3-SFT) | English / Mathematics (proofs) | DeepSeek-V4-Pro (MIT, open weights) writes the proof, refinement, verification and meta-verification traces; problems are human-written AoPS proof problems | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-code-swe-fixer | [internlm/SWE-Fixer-Train-110K](https://huggingface.co/datasets/internlm/SWE-Fixer-Train-110K) | English / Code (Python SWE: issue to patch) | none (human GitHub issues, hints, PR patches and test patches; the paper's GPT-4o chain-of-thought is not in this release) | mit (Hub tag; commercial use permitted per tag; upstream repository licences not filtered) | TSAI reserves |
| sft-code-afm-codeagent | [PersonalAILab/AFM-CodeAgent-SFT-Dataset](https://huggingface.co/datasets/PersonalAILab/AFM-CodeAgent-SFT-Dataset) | English / Code and math (multi-agent tool-use trajectories) | Unknown (distilled from the OAgents multi-agent framework; the backbone LLM is not named on the card or in arXiv 2508.13167) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| sft-code-swe-hero-openhands | [nvidia/SWE-Hero-openhands-trajectories](https://huggingface.co/datasets/nvidia/SWE-Hero-openhands-trajectories) | English / Code (Python SWE agent trajectories, OpenHands) | Qwen3-Coder-480B-A35B-Instruct (Apache-2.0, open weights) writes all trajectories and the regenerated R2E-Gym-Subset issue statements | cc-by-4.0 (Hub tag; repositories limited to MIT, Apache-2.0, BSD-2, BSD-3; attribution needed) | TSAI reserves |
| sft-code-swe-zero-openhands | [nvidia/SWE-Zero-openhands-trajectories](https://huggingface.co/datasets/nvidia/SWE-Zero-openhands-trajectories) | Code (agent trajectories) | Qwen3-Coder-480B-A35B-Instruct (Apache-2.0, open weights) via OpenHands; audit of all 318,115 rows found no Claude data | cc-by-4.0 (Hub tag; attribution required; per-repo licences all permissive) | TSAI reserves |
| sft-math-openr1-math-raw | [open-r1/OpenR1-Math-Raw](https://huggingface.co/datasets/open-r1/OpenR1-Math-Raw) | English / Mathematics | DeepSeek-R1 (MIT, open weights) writes the traces; Llama-3.3-70B-Instruct (Llama 3.3 Community Licence) is used only as a verifier | apache-2.0 (Hub tag; commercial use permitted per tag; inherits NuminaMath-1.5 overlap, keep rows with a passing `correctness` flag) | TSAI reserves |
| sft-chat-puffin | [LDJnr/Puffin](https://huggingface.co/datasets/LDJnr/Puffin) | English / Chat | GPT-4 (OpenAI, proprietary closed) writes every response | apache-2.0 (Hub tag; the OpenAI terms on GPT-4 output still apply) | excluded |
| sft-code-opencodeinstruct | [nvidia/OpenCodeInstruct](https://huggingface.co/datasets/nvidia/OpenCodeInstruct) | Code (Python) | Qwen2.5-32B-Instruct (Apache-2.0) writes the instructions; Qwen2.5-Coder-32B-Instruct (Apache-2.0) writes the solutions, the unit tests and the quality scores (arXiv 2504.04030; the card itself names no model) | cc-by-4.0 (Hub tag and card text; "ready for commercial/non-commercial use") | TSAI reserves |
| sft-stem-code-acereason-1.1-sft | [nvidia/AceReason-1.1-SFT](https://huggingface.co/datasets/nvidia/AceReason-1.1-SFT), `source` in {OpenMathReasoning, OpenCodeReasoning, TACO, apps} | English / Mathematics and Code (Python) | DeepSeek-R1 (MIT) writes every response; these prompts are human competition problems or come from sets already `TSAI reserves` in this table | cc-by-4.0 (Hub tag and card text; commercial use permitted per tag) | TSAI reserves |
| sft-stem-code-acereason-1.1-sft-other | [nvidia/AceReason-1.1-SFT](https://huggingface.co/datasets/nvidia/AceReason-1.1-SFT), `source` in {NuminaMath-CoT, MagicoderEvolInstruct, opc-sft-stage2, leetcode} | English / Mathematics and Code (Python) | DeepSeek-R1 (MIT) writes the responses, but the prompts come from GPT-4 / GPT-4o text (NuminaMath-CoT, Magicoder Evol-Instruct), from a set whose card names no generator (opc-sft-stage2), or from LeetCode problem text with no stated licence | cc-by-4.0 (Hub tag) on the release; upstream prompt licences closed or unstated | excluded |
| sft-chat-dolci-think-sft | [allenai/Dolci-Think-SFT](https://huggingface.co/datasets/allenai/Dolci-Think-SFT), `source` in {OpenThoughts3, WildChat, OpenAssistant Guanaco, Aya} | English / Math, Code, Chat; some multilingual rows via Aya | DeepSeek-R1 and R1-0528 (MIT) write the traces over human WildChat, OASST1 and Aya prompts; the OpenThoughts3 rows are the existing QwQ-32B (Apache-2.0) traces | odc-by (Hub tag; card adds "intended for research and educational use" under Ai2's Responsible Use Guidelines, a statement of intent, not a licence term) | TSAI reserves |
| sft-chat-dolci-think-sft-other | [allenai/Dolci-Think-SFT](https://huggingface.co/datasets/allenai/Dolci-Think-SFT), all other `source` values | English / Instruction following, Python, Safety, Tables | Three new Ai2 subsets (Think Persona IF, Precise IF, Think Python; about 823k rows) name no generator; SYNTHETIC-2 has no licence on its own card; Nemotron-Post-Training-v1 code is `excluded` above; WildGuardMix, WildJailbreak and CoCoNot prompts were written by GPT-4 or unnamed models; TableGPT synthesis method not verified | odc-by (Hub tag) on the release; upstream licences or generators unstated | excluded |
| sft-agentic-apigen-mt-5k | [Salesforce/APIGen-MT-5k](https://huggingface.co/datasets/Salesforce/APIGen-MT-5k) | English / Tool use (retail, airline) | GPT-4o (OpenAI, proprietary closed) and DeepSeek-V3 (MIT) write the agent and simulated-user turns (arXiv 2504.03601) | cc-by-nc-4.0 (Hub tag; non-commercial; card: "for research purposes only") | excluded |
| sft-code-swe-smith | [SWE-bench/SWE-smith](https://huggingface.co/datasets/SWE-bench/SWE-smith) | English / Python SWE task instances | o3-mini (OpenAI, proprietary closed) is the main model that writes the bugs (SWE-smith paper) | mit (Hub tag) | excluded |
| sft-agentic-swe-smith-trajectories | [SWE-bench/SWE-smith-trajectories](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories) | English / SWE-agent trajectories | Claude 3.7 Sonnet (Anthropic, proprietary closed) writes most trajectories (card) | mit (Hub tag) | excluded |
| sft-reasoning-r1-distill-sft | [ServiceNow-AI/R1-Distill-SFT](https://huggingface.co/datasets/ServiceNow-AI/R1-Distill-SFT) | English / Math and instruction reasoning | DeepSeek-R1-32b distillation (card), prompts from Numina-math and Tulu | cc-by-nc-sa-4.0 (Hub tag; non-commercial) | excluded |
| sft-agentic-open-agentrl-sft-3k | [Gen-Verse/Open-AgentRL-SFT-3K](https://huggingface.co/datasets/Gen-Verse/Open-AgentRL-SFT-3K) | English / Agentic reasoning | Qwen3-Coder-30B-A3B (Apache-2.0) is the teacher for the self-curated trajectories (paper) | none stated on the card or in the paper | excluded |
| sft-agentic-toucan | [Agent-Ark/Toucan-1.5M](https://huggingface.co/datasets/Agent-Ark/Toucan-1.5M) | English / Tool use (MCP agent trajectories) | GPT-OSS-120B (Apache-2.0), Kimi-K2 (Modified MIT) and Qwen3-32B (Apache-2.0) write the trajectories, one config each; tasks by Mistral-Small, DevStral-Small, GPT-OSS, Kimi-K2 and Qwen3-32B; Kimi-K2 annotates and GPT-OSS-120B judges (arXiv 2510.01179); all open weights | apache-2.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-tool-when2call | [nvidia/When2Call](https://huggingface.co/datasets/nvidia/When2Call) | English / Tool use (when to call, ask or decline) | Mixtral-8x22B (Apache-2.0) rewrites questions and answers built on APIGen (xLAM) data, which includes DeepSeek-V2-Chat rows (DeepSeek Licence); rows carry no generator field | cc-by-4.0 (Hub tag; attribution needed); `train_sft` and `train_pref` only, the test split is built from BFCL v2 Live | needs TSAI decision |
| sft-indic-indic-instruct-hi | [ai4bharat/indic-instruct-data-v0.1](https://huggingface.co/datasets/ai4bharat/indic-instruct-data-v0.1) | Hindi (`wikihow` and `nmt-seed` subsets only) | none: `wikihow` is native Hindi wikiHow text, `nmt-seed` is human-made BPCC-Human en-hi pairs; the other subsets (Llama-2-70B in `anudesh`, closed models in `lm_sys` and `hh-rlhf`) are not part of this set | no Hub tag; per-subset licences stated in arXiv 2401.15006: `wikihow` CC-0, `nmt-seed` CC-BY-4.0 | TSAI reserves |
| sft-indic-updesh | [microsoft/Updesh_beta](https://huggingface.co/datasets/microsoft/Updesh_beta) | 13 Indic languages incl. Odia | Qwen3-235B-A22B (Updesh-G); Llama-3.1-405B-Instruct (translation) and Llama 3.3 70B (back-translation quality check) named; reasoning part translated from Microsoft Orca sets | other: Microsoft Research License (non-commercial research use only, no redistribution) | excluded |
| sft-tool-xlam-irrelevance-7.5k | [MadeAgents/xlam-irrelevance-7.5k](https://huggingface.co/datasets/MadeAgents/xlam-irrelevance-7.5k) (the data behind "MadeAgents/Hammer") | English / Tool use (irrelevance detection, 7,500 rows) | none new: 7,500 rows sampled from `Salesforce/xlam-function-calling-60k`, the correct tool removed and the answer set to `[]` (arXiv 2410.04587, §4.2); queries keep xlam-60k's Mixtral-8x22B-Instruct and DeepSeek-V2-Chat origin | cc-by-4.0 (Hub tag; attribution needed) | needs TSAI decision |
| sft-reasoning-synthetic-1 | [PrimeIntellect/SYNTHETIC-1](https://huggingface.co/datasets/PrimeIntellect/SYNTHETIC-1) | English / Reasoning (code, math, STEM) | DeepSeek-R1 (MIT) writes the traces | apache-2.0 | TSAI reserves |
| sft-reasoning-openthoughts-114k | [open-thoughts/OpenThoughts-114k](https://huggingface.co/datasets/open-thoughts/OpenThoughts-114k) | English / Math and code | DeepSeek-R1 (MIT) writes the traces | apache-2.0 | TSAI reserves |
| sft-reasoning-openthoughts2-1m | [open-thoughts/OpenThoughts2-1M](https://huggingface.co/datasets/open-thoughts/OpenThoughts2-1M) | English / Reasoning | not named per part; a mix of community datasets on top of OpenThoughts-114k | apache-2.0 | excluded |
| sft-reasoning-sky-t1 | [NovaSky-AI/Sky-T1_data_17k](https://huggingface.co/datasets/NovaSky-AI/Sky-T1_data_17k) | English / Code and math | not named; sources include NuminaMATH, which this table already excludes | apache-2.0 | excluded |
| sft-reasoning-generalthought-430k | [GeneralReasoning/GeneralThought-430K](https://huggingface.co/datasets/GeneralReasoning/GeneralThought-430K) | English / Reasoning | DeepSeek-R1 and R1-Zero (MIT), plus Llama models, and final answers from o3-mini, Gemini and Claude | mit | excluded |
| sft-tool-toolace | [Team-ACE/ToolACE](https://huggingface.co/datasets/Team-ACE/ToolACE) | English and Chinese / Tool use | not named on the card | apache-2.0 | excluded |
| sft-tool-hermes-function-calling-v1 | [NousResearch/Hermes-Function-Calling-v1](https://huggingface.co/datasets/NousResearch/Hermes-Function-Calling-v1) | English / Tool use | not named; the card names the people who led the synthetic generation, not a model | apache-2.0 | excluded |
| sft-tool-apigen-function-calling | [argilla/apigen-function-calling](https://huggingface.co/datasets/argilla/apigen-function-calling) | English / Tool use | one part is `Salesforce/xlam-function-calling-60k` (Mixtral-8x22B-Instruct and DeepSeek-V2-Chat); the distilabel part names Qwen2.5-72B-Instruct (Apache-2.0) | cc-by-4.0 | needs TSAI decision |
| sft-tool-hermes-reasoning-tool-use | [interstellarninja/hermes_reasoning_tool_use](https://huggingface.co/datasets/interstellarninja/hermes_reasoning_tool_use) | English / Tool use | DeepHermes-3-Llama-3-8B-Preview (Llama) writes the roll-outs | apache-2.0 | excluded |
| sft-agentic-afm-webagent-sft | [PersonalAILab/AFM-WebAgent-SFT-Dataset](https://huggingface.co/datasets/PersonalAILab/AFM-WebAgent-SFT-Dataset) | English / Web agent | not named; distilled from unnamed multi-agent systems, sourced from TaskCraft | apache-2.0 | excluded |
| sft-tool-toolmind | [Nanbeige/ToolMind](https://huggingface.co/datasets/Nanbeige/ToolMind) | English / Tool use | not named; a multi-agent pipeline, plus rows taken from xlam-60k and When2Call | apache-2.0 | excluded |
| sft-math-s1k-1.1 | [simplescaling/s1K-1.1](https://huggingface.co/datasets/simplescaling/s1K-1.1) | English / Mathematics | Gemini Flash Thinking Experimental (Google, proprietary closed) writes the `gemini_*` traces; DeepSeek-R1 (MIT) writes the `deepseek_*` traces; both are stored on every row | mit (Hub tag) | excluded |

### Stage 2: Preference optimization and RLVR

| Set | Source | Language | Generator model | Licence | Decision |
| --- | --- | --- | --- | --- | --- |
| rl-code-r2e-gym | [R2E-Gym/R2E-Gym-Subset](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Subset) | Code (Python SWE) | Unknown in main text (tests and issues are LLM-generated by back-translation from commits, arXiv 2504.07164; generator model not stated on the card) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-code-swe-gym | [SWE-Gym/SWE-Gym](https://huggingface.co/datasets/SWE-Gym/SWE-Gym) | Code (Python SWE) | none (real GitHub issues and unit tests; execution-verified) | mit (Hub tag; commercial use permitted per tag) | TSAI reserves |
| rl-code-swe-envs-g10 | `teams/10-post-training/swe-envs/` (21 envs, each one merged upstream GitHub PR from 2018 to 2022 that closes a human issue) | Code (Python SWE, Go) | none (issue text, fix and tests are the upstream human issue and PR; only the harness, Dockerfile and verify script, is written with a model, which TSAI confirmed on 4 Nov is fine) | each repo's own licence, recorded in every `env.json`: MIT (12 envs), BSD-3-Clause (9 envs) | allowed (TSAI, 4 Nov) |
| rl-code-swe-rebench | [nebius/SWE-rebench](https://huggingface.co/datasets/nebius/SWE-rebench) (pre-2023 rows, human parts only) | Code (Python SWE) | none for the parts we use (issue, patch and tests come from real PRs); Qwen2.5-72B-Instruct wrote the install recipes and quality labels, which we do not use (arXiv 2505.20411) | cc-by-4.0 (Hub tag; attribution needed); each repo keeps its own licence, permissive repos only | allowed (TSAI, 4 Nov: human parts only, every env rebuilt and gold-checked by us) |
| rl-code-acecode-87k | [TIGER-Lab/AceCode-87K](https://huggingface.co/datasets/TIGER-Lab/AceCode-87K) | Code (Python) | GPT-4o-mini (OpenAI, proprietary closed) rewrote the questions | mit (Hub tag; commercial use permitted per tag) | excluded |
| rl-code-deepcoder | [agentica-org/DeepCoder-Preview-Dataset](https://huggingface.co/datasets/agentica-org/DeepCoder-Preview-Dataset) | Code (competitive) | none (human competition problems and execution unit tests collected from existing sets) | mit (Hub tag; commercial use permitted per tag) | allowed (TSAI, 6 Nov: train split only; decontaminated, see rl/decontam_report.md) |
| rl-code-swe-rebench-v2 | [nebius/SWE-rebench-V2](https://huggingface.co/datasets/nebius/SWE-rebench-V2) | Code (20 languages incl. Go) | Qwen3-Coder-480B-A35B-Instruct (Apache-2.0) for installation agent; quality labels from gpt-oss-120b (Apache-2.0), GLM-4.7 (MIT) and DeepSeek-V3.2 (MIT) (arXiv 2602.23866) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| rl-code-codeforces | [open-r1/codeforces](https://huggingface.co/datasets/open-r1/codeforces) | Code (competitive) | none for problems (human Codeforces problems); DeepSeek-R1 (MIT) for generated test inputs | cc-by-4.0 (Hub tag; commercial use permitted per tag) | allowed (TSAI, 6 Nov: train split only; G9 checks the RL pool against its Codeforces benchmark) |
| rl-math-dapo-17k | [BytedTsinghua-SIA/DAPO-Math-17k](https://huggingface.co/datasets/BytedTsinghua-SIA/DAPO-Math-17k) | English / Mathematics | Unknown (an unnamed LLM rewrote competition questions so the answer is an integer, arXiv 2503.14476) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-math-big-math | [SynthLabsAI/Big-Math-RL-Verified](https://huggingface.co/datasets/SynthLabsAI/Big-Math-RL-Verified) | English / Mathematics | Llama-3.1-405B / Llama-3.1-70B / Llama-3.1-8B (Llama 3.1 Community Licence) and gpt-4o-mini (OpenAI, closed) (arXiv 2502.17387) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-math-deepmath-103k | [zwhe99/DeepMath-103K](https://huggingface.co/datasets/zwhe99/DeepMath-103K) | English / Mathematics | DeepSeek-R1 (MIT, open weights) | mit (Hub tag; commercial use permitted per tag) | TSAI reserves |
| rl-nvidia-helpsteer2 | [nvidia/HelpSteer2](https://huggingface.co/datasets/nvidia/HelpSteer2) | English / Multi-domain | Human-annotated ratings, but candidate responses include Nemotron-4-340B (NVIDIA Open Model Licence) and Mixtral-8x7B-Instruct (Apache-2.0); response generator per row is not mapped to MIT/Apache-2.0 only | cc-by-4.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-skywork-reward-80k | [Skywork/Skywork-Reward-Preference-80K-v0.2](https://huggingface.co/datasets/Skywork/Skywork-Reward-Preference-80K-v0.2) | English / Multi-domain | Upstream Magpie/OffsetBias/WildGuardMix sets generated by Llama-3-70B-Instruct (Llama 3 licence) and GPT-4 (OpenAI, closed) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-ultrafeedback-clean | [argilla/ultrafeedback-binarized-preferences-cleaned](https://huggingface.co/datasets/argilla/ultrafeedback-binarized-preferences-cleaned) | English / Multi-domain | GPT-4 (OpenAI, proprietary closed) preference annotations and Llama-2 (Llama 2 licence) responses | mit (Hub tag; commercial use permitted per tag) | excluded |
| rl-nectar-rm | [berkeley-nest/Nectar](https://huggingface.co/datasets/berkeley-nest/Nectar) | English / Multi-domain | GPT-4 (OpenAI, proprietary closed) ranking and GPT-3.5 / GPT-4 / Claude / Llama-2 responses | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-intel-orca-dpo | [Intel/orca_dpo_pairs](https://huggingface.co/datasets/Intel/orca_dpo_pairs) | English / Reasoning | GPT-4 / GPT-3.5 (OpenAI, proprietary closed) via OpenOrca | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-distilabel-math-dpo | [argilla/distilabel-math-dpo](https://huggingface.co/datasets/argilla/distilabel-math-dpo) | English / Mathematics | Unknown / Llama-3 and Qwen2 (generator models and licences not stated on card) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-code-feedback-dpo | [HuggingFaceH4/Code-Feedback](https://huggingface.co/datasets/HuggingFaceH4/Code-Feedback) | Code (Polyglot) | Derived from `m-a-p/CodeFeedback-Filtered-Instruction` (contains GPT-3.5 / GPT-4 upstream sets) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-wildguardmix | [allenai/wildguardmix](https://huggingface.co/datasets/allenai/wildguardmix) | English / Safety | GPT-4 (OpenAI, proprietary closed) generated synthetic prompts and responses (arXiv 2406.18495) | odc-by (Hub tag; commercial use permitted per tag) | excluded |
| rl-community-alignment | [facebook/community-alignment-dataset](https://huggingface.co/datasets/facebook/community-alignment-dataset) | Hindi, English, French, Italian, Portuguese | Llama-based candidate generation (Llama licence) and unnamed response generators on card | CC-BY-4.0 | excluded |
| rl-safety-hh-rlhf | [Anthropic/hh-rlhf](https://huggingface.co/datasets/Anthropic/hh-rlhf) | English | Anthropic 52B context-distilled / RLHF models (Anthropic, proprietary closed) | MIT | excluded |
| rl-safety-alignment-faking | [Anthropic/alignment-faking-rl](https://huggingface.co/datasets/Anthropic/alignment-faking-rl) | English | Anthropic Claude 3.5 Sonnet / Opus 3 / Sonnet 4 (Anthropic, proprietary closed) | CC-BY-4.0 (body link; Hub tag is cc) | excluded |
| rl-code-code-contests | [deepmind/code_contests](https://huggingface.co/datasets/deepmind/code_contests) | Code (competitive; Python, C++, Java) | none (human problems and human solutions scraped from Codeforces, AtCoder, CodeChef, Aizu and HackerEarth; extra tests are made by programmatic mutation of existing inputs and checked against known-correct solutions, no LLM) | cc-by-4.0 (Hub tag; commercial use permitted per tag; upstream site content scraped) | allowed (TSAI, 6 Nov) |
| rl-code-r2e-gym-v1 | [R2E-Gym/R2E-Gym-V1](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-V1) | Code (Python SWE) | Unknown (issues and some tests are LLM-generated by back-translation from commits, arXiv 2504.07164; generator model not stated; card body empty) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-code-afm-codeagent | [PersonalAILab/AFM-CodeAgent-RL-Dataset](https://huggingface.co/datasets/PersonalAILab/AFM-CodeAgent-RL-Dataset) | Code and math | none in this release (problems with tests or answers, repackaged from LiveCodeBench v1–v3, Skywork-OR1-RL-Data and DAPO-Math; the DAPO slice and the NuminaMath-1.5 subsets in the Skywork math slice are excluded in this table) | apache-2.0 (Hub tag; commercial use permitted per tag) | excluded |
| rl-code-leetcodedataset | [newfacade/LeetCodeDataset](https://huggingface.co/datasets/newfacade/LeetCodeDataset) | Code (Python) | Unknown for test inputs (an unnamed "LLM" wrote them, arXiv 2504.14655, Figs 4–5); outputs come from human canonical solutions; SFT responses by Qwen2.5-Coder-32B-Instruct (Apache-2.0) | apache-2.0 (Hub tag); MIT on GitHub; problem text belongs to LeetCode; pending until the test-input generator is known | needs TSAI decision |
| rl-math-processbench | [Qwen/ProcessBench](https://huggingface.co/datasets/Qwen/ProcessBench) | English / Mathematics (step verification) | Not on the card; the paper (arXiv 2412.06559, Table 4) names 12 Qwen2/Qwen2.5 and Llama-3/3.1 Instruct models; step errors labelled by human experts | apache-2.0 (Hub tag); eval only, not training data (G9 evaluation probe) | excluded |
| rl-math-deepscaler | [agentica-org/DeepScaleR-Preview-Dataset](https://huggingface.co/datasets/agentica-org/DeepScaleR-Preview-Dataset) | English / Mathematics (competition) | none for problems and solutions (human AIME 1984-2023, AMC before 2023, Omni-MATH, Still); gemini-1.5-pro-002 (Google, proprietary closed) is used in the preprocessing code as a proof-problem filter and difficulty judge; the Still rows (MATH, NuminaMath-CoT, AIME) have no stated licence and the release has no `source` column to drop them | mit (Hub tag) on the release; Still source licence unstated | excluded |
| rl-safety-aya-redteaming | [CohereLabs/aya_redteaming](https://huggingface.co/datasets/CohereLabs/aya_redteaming) | Hindi (`aya_hin`, 915 prompts); 7 other languages not used | none: harmful prompts written by paid human annotators; prompts only, no responses | apache-2.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| rl-agentic-open-agentrl-30k | [Gen-Verse/Open-AgentRL-30K](https://huggingface.co/datasets/Gen-Verse/Open-AgentRL-30K) | English / RL prompts (17K DAPO-Math, 3K MegaScience science, plus LeetCode and Skywork-OR1 data) | none for the prompts | none stated; includes 3K MegaScience rows (cc-by-nc-sa-4.0) | excluded |
| rl-agentic-nemotron-tool-use-pivot | [nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1) | English / conversational tool use (838 domains) | DeepSeek-R1-0528 (MIT), DeepSeek-V3.2 (MIT), Qwen3-235B-A22B-Thinking-2507 (Apache-2.0) and Qwen3-32B (Apache-2.0) make the data; gpt-oss-120b and Qwen3-235B-A22B-Instruct-2507 (Apache-2.0) label it | cc-by-4.0 (Hub tag; card says ready for commercial use) | TSAI reserves |
| rl-tool-hammerbench | [MadeAgents/HammerBench](https://huggingface.co/datasets/MadeAgents/HammerBench) | English and Chinese / Tool use (mobile-app function calling, multi-turn) | Unnamed "open-source models" generate queries and dialogues from app functions and anonymized user logs (arXiv 2412.16516, §4); the paper does not name them | apache-2.0 (Hub tag); eval only, not training data | excluded |
| rl-math-rlvr-gsm | [allenai/RLVR-GSM](https://huggingface.co/datasets/allenai/RLVR-GSM) | English / Mathematics (GSM8k, train split only) | none (GSM8k problems and answers, reformatted; no model writes new text) | mit | TSAI reserves |
| rl-agentic-afm-webagent | [PersonalAILab/AFM-WebAgent-RL-Dataset](https://huggingface.co/datasets/PersonalAILab/AFM-WebAgent-RL-Dataset) | English / Web agent | not named; the card does not say which model wrote the trajectories | apache-2.0 | excluded |
| rl-math-hendrycks | [EleutherAI/hendrycks_math](https://huggingface.co/datasets/EleutherAI/hendrycks_math) (train split only) | English / Mathematics | none (human AMC, AIME and other contest problems with human step-by-step solutions) | mit (Hub tag and GitHub MIT licence) | TSAI reserves |
| rl-code-apps | [codeparrot/apps](https://huggingface.co/datasets/codeparrot/apps) (train split only) | English / Code (Python) | none (human contest problems and human solutions) | mit (Hub tag and GitHub MIT licence) | TSAI reserves |
| rl-code-taco | [BAAI/TACO](https://huggingface.co/datasets/BAAI/TACO) (train split; HackerRank and LeetCode rows left out) | English / Code (Python) | none (contest problems and verified Python solutions; no model generator named) | apache-2.0 (Hub tag; card also names MIT and CC-BY-4.0 on parts; HackerRank licence unknown on the card) | TSAI reserves |
| rl-math-omni-math | [KbsdJames/Omni-MATH](https://huggingface.co/datasets/KbsdJames/Omni-MATH) | English / Mathematics (Olympiad) | none for problems and solutions (human contest and AoPS text); GPT-4o (OpenAI, closed) only writes some difficulty scores and the domain labels | apache-2.0 (Hub tag) | needs TSAI decision |

---

## Dataset sections by G10 Core Team member (12)

### 1. Sai Teja (Lead) — StarCoder (`code-python` · `bigcode/starcoderdata`)

- **Core team:** 10. Post-training and Agentic (Lead) · **Week 2:** 9. Evaluation · **Week 3:** 12. Quantization and Serving
- **Set:** `code-python`
- **Language:** `Code`
- **Source:** `bigcode/starcoderdata`
- **Licence:** `other` — StarCoder training corpus drawn from The Stack; each file retains its upstream licence and attribution notice. Commercial use must follow per-file attribution terms.
- **Decision:** `TSAI reserves`

### 1b. Sai Teja (Lead) — Chandassu (`BodduSriPavan111/chandassu`)

- **Core team:** 10. Post-training and Agentic (Lead) · **Week 2:** 9. Evaluation · **Week 3:** 12. Quantization and Serving
- **Set:** `chandassu`
- **Language:** Telugu (`te`)
- **Source:** `BodduSriPavan111/chandassu` (4,651 padyams; eight metres in vruttamu, jaathi, and vupajaathi)
- **Licence:** `MIT` — commercial use is allowed. The dataset card names the licence as MIT.
- **Decision:** `TSAI reserves`
- **Reading note:** 1,134 Vemana poems store a carriage return as the plain letters `_x000D_`. 23 poems have words replaced by `...`. ZWNJ and ZWJ stay in the text. They are not a licence issue.

### 2. Ajay Kumar — JavaScript / TypeScript (`code-js-ts` · `bigcode/starcoderdata`)

- **Core team:** 10. Post-training and Agentic
- **Set:** `code-js-ts`
- **Language:** Code (JavaScript / TypeScript)
- **Source:** `bigcode/starcoderdata`, JavaScript / TypeScript subset (500-document pack)
- **Licence:** `other` — StarCoder training corpus drawn from The Stack; individual files may retain different upstream licences and attribution notices. Repository-level licence terms and training-use rights require further verification.
- **Decision:** `TSAI reserves`

### 3. Amit T — Indic web (`ind-mr-fw2` · FineWeb-2 Marathi)

- **Core team:** 10. Post-training and Agentic (Member A) · **Week 2:** 10. Post-training
- **Set:** `ind-mr-fw2` — FineWeb-2 Marathi split (`data/mr/`)
- **Language:** Marathi (`mr`)
- **Source:** [`HuggingFaceFW/fineweb-2`](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) (Hugging Face, 2024; Common Crawl curated web pipeline)
- **Generator model:** none (real web text extracted from Common Crawl via FineWeb-2 curation pipeline; no synthetic LLM generator).
- **Licence:** `ODC-By v1.0` (Open Data Commons Attribution License v1.0). Commercial use is explicitly permitted with attribution.
- **What the pack shows:**
  - Zero ghost tokens or synthetic prompt markers found.
  - Devanagari script joiners `U+200D` (ZWJ) and `U+200C` (ZWNJ) preserved for Marathi orthography (eyelash-ra `ऱ्या`, halant conjuncts).
  - Takedown and provenance ledger: URLs and crawl dump IDs preserved to honor robots.txt opt-outs and DMCA/GDPR requests.
- **Decision:** `TSAI reserves` — commercial-use only rule satisfied. Attribution requirement to be fulfilled in the public model card and training datasheet. Raw data not committed to repository.

### 4. f20201351h-maker — StarCoder (`code-python` · `bigcode/starcoderdata`, assigned 500-document pack)

- **Core team:** 10. Post-training and Agentic · **Week 2:** 11. Release · **Week 3:** 6. Performance and Kernels
- **Set:** `code-python` (500-document pack; already in the Stage 0 table, so no new row)
- **Language:** `Code` (Python)
- **Source:** `bigcode/starcoderdata` on Hugging Face (gated; users accept its Terms of Use)
- **Generator model:** none (no LLM-generated text). The files are source code from public GitHub repositories; 12 of them are tool-generated code such as Django migrations.
- **Licence:** `other`, as on the dataset card. Users must abide by the terms of each file's original licence, including attribution.
- **What the pack shows (licence headers at the top of the 500 files):** Apache-2.0 45, MIT 16, BSD 6, GPL 6, LGPL 2, among the licence families that repeat in the pack. One-off headers were not classified, so other licences may still be present.
  **At least 8 files carry a GPL/LGPL header:**
  - GPL: `890651e4733e8944` (GPLv3+), `bcb288906f19d84d` (GPLv3+), `da1e1a24ce2d8184` (GPLv3), `1ba7834883790ea6` (GPLv2 with the Universal FOSS Exception), `b722cf3b05cb227a` (GPLv2), `e2c3db81526c288d` (GPLv2+).
  - LGPL: `6fbbb7afb4c34553` (LGPLv3+), `0f044ee517526307` (tri-licence MPL 1.1 / GPL 2.0 / LGPL 2.1).
- **Decision:** `TSAI reserves`.
  - Proposal: keep the permissive-licensed files (Apache-2.0, MIT, BSD). Keep each file's path and licence in a per-file manifest for attribution, because the `E4` cleaning medicine removes repeated licence headers from the text.
  - Flag the GPL/LGPL files for TSAI and drop them by default: the TSAI data rule lets in permissive licences and CC-BY-SA with attribution, and GPL/LGPL is neither. The licence follows the file, not the corpus (same finding as `code-go`, section 10).

### 5. Ashish Kamble — Dataset section *(placeholder for PR to `g10-week1-post-training`)*

- **Set:** *(TBD via PR)*
- **Language:** *(TBD via PR)*
- **Source:** *(TBD via PR)*
- **Licence:** *(TBD via PR)*
- **Decision:** `TSAI reserves`

### 6. Hema Varshini Palpandian — Tamil (`ind-ta-sangraha-v`)

- **Set:** `ind-ta-sangraha-v`
- **Language:** Tamil (`ta`; source split `tam`)
- **Source:** `ai4bharat/sangraha`, Verified Tamil subset.
- **Licence:** `CC-BY-4.0` — publisher-declared; permits commercial use with attribution, a licence link and notice of changes.
- **Decision:** `TSAI reserves` — source checks and SFT/RL selection pending.
- **Reading note:** 500 Tamil documents. No tested chat/tool markers found. Document URLs and the source release are missing from the sample; verify provenance before training.

### 7. Lokesh Arundathi — Kannada (`ind-kn-fw2`)

- **Set:** `ind-kn-fw2`
- **Language:** Kannada (`kn`)
- **Source:** `HuggingFaceFW/fineweb-2` (Hugging Face, 2024; Common Crawl curated web pipeline)
- **Licence:** `ODC-By v1.0` (Open Data Commons Attribution License v1.0). Commercial use is explicitly permitted with attribution.
- **Decision:** `TSAI reserves` — commercial-use only rule satisfied. Attribution requirement to be fulfilled in the public model card and training datasheet.

### 8. gmrammohan15 — Indic web (`ind-hi-hplt` · HPLT 3.0 `hin_Deva`)

- **Set:** `ind-hi-hplt`
- **Language:** `Hindi` (`hin_Deva`)
- **Source:** HPLT 3.0 monolingual, sorted release: `data.hplt-project.org/three/sorted/hin_Deva` (web crawl from Internet Archive and Common Crawl; catalogue at `hplt-project.org/datasets/v3.0`)
- **Licence:** `CC0-1.0` for the **packaging only**. HPLT's Terms of Use: "We do not own any of the text from which these text data has been extracted" and "We license the actual packaging of these text data under the Creative Commons CC0 license". The underlying web text keeps its original copyright (no per-document licence is given). HPLT 3.0 filters robots.txt opt-outs and removes sources on a takedown request in the next release.
- **Generator model:** none (web crawl). The pages are written by their publishers, not by a model chosen for this set; a single page may still be machine-translated or model-written, which the diagnosis codes (D4, D5) mark row by row.
- **Decision:** `TSAI reserves`. Commercial use of the collection is allowed (CC0). For the web text itself, treat it like every other web-crawl source: honour robots.txt opt-outs and takedown requests, keep each document's source URL so it can be removed, and do not redistribute raw text.

### 9. Ranjani Chandrasekaran — Indic web (`ind-hi-indiccorp`)

- **Set:** `ind-hi-indiccorp` — IndicCorpV2 Hindi subset (`data/hi-{1,2,3}.txt`)
- **Language:** Hindi (`hi`)
- **Source:** `ai4bharat/IndicCorpV2` (HuggingFace, AI4Bharat)
- **Licence:** CC-BY-4.0 — attribution required; commercial use permitted
- **Decision:** `TSAI reserves` (satisfies commercial-use rule via CC-BY-4.0 attribution; attribution to be carried in the model card)


### 10. Ravi Naik — Go (`code-go` · `bigcode/starcoderdata`)

- **Set:** `code-go`
- **Language:** Code (Go)
- **Source:** `bigcode/starcoderdata`, Go subset (500-document pack)
- **Licence:** `other` — Hub tag `license:other`, gated (auto-approval). StarCoder training corpus drawn from The Stack; each file keeps its upstream licence and attribution notice. Commercial use must follow per-file terms.
- **Decision:** `TSAI reserves`
- **Reading note:** 500 documents read. 53 start with a long licence header. One GPL file (`20331b3adb6eeb61`), one AGPL file (`83d8307ca8489972`) and one "free for personal use" file (`ab877ddc979bdd7d`) turned up, so licences must be filtered per file, not per corpus. Raw documents are not committed.

### 11. Syed Abdul — Dataset section *(placeholder for PR to `g10-week1-post-training`)*

- **Set:** *(TBD via PR)*
- **Language:** *(TBD via PR)*
- **Source:** *(TBD via PR)*
- **Licence:** *(TBD via PR)*
- **Decision:** `TSAI reserves`

### 12. Vikash Ranjan — Rust (`code-rust` · `bigcode/starcoderdata`)

- **Set:** `code-rust`
- **Language:** Rust
- **Source:** [bigcode/starcoderdata](https://huggingface.co/datasets/bigcode/starcoderdata) — Rust subset (500-document pack); collected GitHub source code, one upstream repository per file.
- **Licence:** `other` — Hub tag `license:other`, gated (auto-approval). Each file keeps its upstream licence and attribution notice, so the corpus is not uniformly permissive; commercial use must follow per-file terms.
- **Generator model:** Not applicable at dataset level; no generator model is declared for this collected code corpus.
- **Decision:** `TSAI reserves`
- **Reading note:** 500 documents read. Licence signals are per file: 3 copyleft files — `2309a9a7478a52e5` (LGPL-3.0-or-later, SPDX header), `11fffe33baa7bd5e` (AGPL), `c5e98659490161e2` (GPL); 6 files carry an `SPDX-License-Identifier`; 13 mention an MIT licence, 17 Apache and 1 BSD; 36 carry a copyright line and 7 say "all rights reserved"; no non-commercial or personal-use-only file turned up. All 500 documents keep their source URL, so the attribution and takedown ledger can be built per file. Licences must be filtered per file, not per corpus. Raw documents are not committed.

---

## Stage 1: SFT instruction mixture, candidate sets

Chat-formatted dialogues, reasoning traces and tool or agent trajectories for coding, Indic languages, math and science. Each entry has the standard fields, `TSAI reserves` as the decision (`excluded` where TSAI ruled a set out), and one line of opinion. Licence values are the Hugging Face tags read on 29 Oct 2026; a tag is not legal clearance. Per-dataset notes, 20-row samples and a benchmark-overlap check are in [team10-datasets](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets).

Fifty-six sets in the two stage tables are `excluded` (37 in Stage 1, 19 in Stage 2). They include eleven earlier ones (six named by TSAI, and five more where a closed OpenAI or Llama model made part of the data: `sft-code-magicoder-oss`, `sft-indic-indic-align`, `sft-math-numinamath-cot`, `sft-rl-code-rstar-coder`, `rl-math-big-math`), nine added on 1 Nov for closed-model, Llama or custom-licence reasons, and three added in the 2 Nov review (`sft-math-numinamath-1.5`, `sft-agentic-nemotron-sft-agentic-v2-other`, `sft-indic-aya-collection-other`). The others were added in later reviews, and each entry gives its reason. Six CC-BY-SA sets (`sft-math-nemotron-proofs`, `sft-math-nemotron-math-v2`, `sft-math-nemotron-sft-math-v4`, `sft-science-nemotron-science-v2`, `sft-dolly-15k`, `sft-indic-indic-align-dolly-t`) are `allowed (CC-BY-SA, attribution needed)` after TSAI's update that CC-BY-SA data is allowed with attribution. `sft-science-nemotron-science` goes to G9 (Evaluation) for a decontamination test before any use. `rl-code-swe-envs-g10` and `rl-code-swe-rebench` are `allowed` after TSAI's 4 Nov answer on SWE environments (human issue, patch and tests only; every env rebuilt and gold-checked by us). `rl-code-deepcoder`, `rl-code-codeforces` and `rl-code-code-contests` are `allowed` after TSAI's 6 Nov answer (train splits only), and their decontamination results are in `rl/decontam_report.md`.

### `sft-code-commitpackft` — commitpackft

- **Stage:** SFT
- **Set:** `sft-code-commitpackft`
- **Language:** Code (350+ languages)
- **Source:** [`bigcode/commitpackft`](https://huggingface.co/datasets/bigcode/commitpackft)
- **Licence:** `mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** none (real GitHub commits)
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. Commit data with repo licences filtered upstream; low benchmark risk but untested.
- **Details and 20-row sample:** [bigcode__commitpackft](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/bigcode__commitpackft)

### `sft-code-self-oss-instruct` — self-oss-instruct-sc2-exec-filter-50k

- **Stage:** SFT
- **Set:** `sft-code-self-oss-instruct`
- **Language:** Code (Python)
- **Source:** [`bigcode/self-oss-instruct-sc2-exec-filter-50k`](https://huggingface.co/datasets/bigcode/self-oss-instruct-sc2-exec-filter-50k)
- **Licence:** `odc-by` on the dataset card; generator model (`StarCoder2-15B`) is under the **BigCode OpenRAIL-M** licence, which has use restrictions and makes a model trained on its output a derivative that must carry its use restrictions.
- **Generator model:** `StarCoder2-15B` (BigCode OpenRAIL-M licence, use restrictions) generates instructions, responses and tests in the SelfCodeAlign method (arXiv 2410.24198).
- **Decision:** `excluded` — TSAI decision on generator models (3 Nov): output of models with use-restriction licences such as OpenRAIL-M is out. StarCoder2 is out because its licence makes a model trained on its output a derivative that must carry its use restrictions.
- **Our opinion:** excluded under the 3 Nov TSAI generator-licence ruling.
- **Details and 20-row sample:** [bigcode__self-oss-instruct-sc2-exec-filter-50k](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/bigcode__self-oss-instruct-sc2-exec-filter-50k)

### `sft-code-magicoder-oss` — Magicoder-OSS-Instruct-75K

- **Stage:** SFT
- **Set:** `sft-code-magicoder-oss`
- **Language:** Code (polyglot)
- **Source:** [`ise-uiuc/Magicoder-OSS-Instruct-75K`](https://huggingface.co/datasets/ise-uiuc/Magicoder-OSS-Instruct-75K)
- **Licence:** `mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** GPT-3.5 (OpenAI, closed)
- **Decision:** `excluded` — TSAI rule in the G10 chat (30 Oct): data made by closed OpenAI, Anthropic, Google or Llama models stays excluded. Applied by us to this set. Reason: Instructions were generated with GPT-3.5 (OpenAI, closed).
- **Our opinion:** excluded under that rule. Ask TSAI if a partial use (for example only the human-written parts) is acceptable.
- **Details and 20-row sample:** [ise-uiuc__Magicoder-OSS-Instruct-75K](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/ise-uiuc__Magicoder-OSS-Instruct-75K)

### `sft-code-codefeedback` — CodeFeedback-Filtered-Instruction

- **Stage:** SFT
- **Set:** `sft-code-codefeedback`
- **Language:** Code (polyglot)
- **Source:** [`m-a-p/CodeFeedback-Filtered-Instruction`](https://huggingface.co/datasets/m-a-p/CodeFeedback-Filtered-Instruction)
- **Licence:** `apache-2.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Mixed upstream sets (Magicoder, Evol-Instruct code); Qwen-72B-Chat used only as a filter
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. Built from several instruction sets, one of them Evol-Instruct code. Check HumanEval/MBPP overlap.
- **Details and 20-row sample:** [m-a-p__CodeFeedback-Filtered-Instruction](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/m-a-p__CodeFeedback-Filtered-Instruction)

### `sft-rl-code-rstar-coder` — rStar-Coder

- **Stage:** SFT + RL
- **Set:** `sft-rl-code-rstar-coder`
- **Language:** Code (competitive)
- **Source:** [`microsoft/rStar-Coder`](https://huggingface.co/datasets/microsoft/rStar-Coder)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** GPT-4o (OpenAI, closed) for problem synthesis and test-input generators; QwQ-32B (open weights) for the long-reasoning solutions (paper, arXiv 2505.21297)
- **Decision:** `excluded` — TSAI rule in the G10 chat (30 Oct): data made by closed OpenAI, Anthropic, Google or Llama models stays excluded. Applied by us to this set. Reason: GPT-4o (OpenAI, closed) synthesized the problems and wrote the test-input generators.
- **Our opinion:** excluded under that rule. Ask TSAI if partial use is acceptable.
- **Details and 20-row sample:** [microsoft__rStar-Coder](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/microsoft__rStar-Coder)

### `sft-code-swe-rebench-openhands` — SWE-rebench-openhands-trajectories

- **Stage:** SFT
- **Set:** `sft-code-swe-rebench-openhands`
- **Language:** Code (agent trajectories)
- **Source:** [`nebius/SWE-rebench-openhands-trajectories`](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Qwen3-Coder-480B-A35B-Instruct (open weights) via OpenHands
- **Decision:** `TSAI reserves`
- **Our opinion:** use. OpenHands trajectories. Apply the same task-ID overlap check.
- **Details and 20-row sample:** [nebius__SWE-rebench-openhands-trajectories](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nebius__SWE-rebench-openhands-trajectories)

### `sft-code-nemotron-cp-v2` — Nemotron-SFT-Competitive-Programming-v2

- **Stage:** SFT
- **Set:** `sft-code-nemotron-cp-v2`
- **Language:** Code (competitive, SQL)
- **Source:** [`nvidia/Nemotron-SFT-Competitive-Programming-v2`](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Competitive-Programming-v2)
- **Licence:** `cc-by-4.0, odc-by, mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Competitive subset: model not named on the card (NeMo-Skills pipeline; DeepSeek-R1-0528 is cited). Exercism subset: synthetic, model not named. Text-to-SQL: NVIDIA Data Designer, LLM not named
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. Per-subset licences (CC-BY-4.0, ODC-By, MIT). The Exercism subset is decontaminated against Aider.
- **Details and 20-row sample:** [nvidia__Nemotron-SFT-Competitive-Programming-v2](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__Nemotron-SFT-Competitive-Programming-v2)

### `sft-code-nemotron-cascade-swe` — Nemotron-Cascade-SFT-SWE

- **Stage:** SFT
- **Set:** `sft-code-nemotron-cascade-swe`
- **Language:** Code (SWE localisation, repair, test generation)
- **Source:** [`nvidia/Nemotron-Cascade-SFT-SWE`](https://huggingface.co/datasets/nvidia/Nemotron-Cascade-SFT-SWE)
- **Licence:** `cc-by-4.0` — Hugging Face tag and card read on 2 Nov 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1-0528 (open weights) writes every response; the card has a `generator` field per row. Prompts come from SWE-Bench-Train, SWE-reBench, SWE-Smith, R2E-Gym-Subset and SWE-Fixer-Train.
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. Open-weight generator and a permissive licence, so it passes the Week 2 rule. The prompts follow the "agentless mini" framework (localise the bug, repair it, write a test), so these are single-turn tasks, not action and observation trajectories. The card removes repositories that appear in SWE-bench Verified, nothing else, so the Team 9 decontamination test is still needed (Live, Pro, Terminal-Bench). It shares SWE-reBench issues with `sft-code-swe-rebench-openhands`: de-duplicate by instance id. The licences of the five source sets are not checked.

### `sft-agentic-nemotron-agentic-v1` — Nemotron-Agentic-v1

- **Stage:** SFT
- **Set:** `sft-agentic-nemotron-agentic-v1`
- **Language:** English / tool use and conversational agents
- **Source:** [`nvidia/Nemotron-Agentic-v1`](https://huggingface.co/datasets/nvidia/Nemotron-Agentic-v1)
- **Licence:** `cc-by-4.0` — Hugging Face tag and card read on 2 Nov 2026. The card adds `apache-2.0` for the Glaive-Function-Calling-v2 part. Attribution is needed.
- **Generator model:** Qwen3-235B-A22B-Thinking-2507, Qwen3-235B-A22B-Instruct-2507, Qwen3-32B and GPT-OSS-120B, all open weights, simulate the user, agent and tool roles and also judge the result. The user personas come from `nvidia/Nemotron-Personas-USA`.
- **Decision:** `TSAI reserves`
- **Our opinion:** use. Every named model is open weights, so it passes the Week 2 rule. 335,122 samples (19,028 interactive agent, 316,094 tool calling). The tool sets come from public datasets that the card does not name (except Glaive v2), so their licences are unchecked.

### `sft-agentic-nemotron-sft-agentic-v2-tool-calling` — Nemotron-SFT-Agentic-v2, tool-calling part

- **Stage:** SFT
- **Set:** `sft-agentic-nemotron-sft-agentic-v2-tool-calling`
- **Language:** English / tool use
- **Source:** [`nvidia/Nemotron-SFT-Agentic-v2`](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Agentic-v2), the tool-calling part only
- **Licence:** `cc-by-4.0, apache-2.0, mit` — Hugging Face tags and card read on 2 Nov 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-V3.2 and GLM-4.6 (open weights) simulate the dialogues and judge them. The seeds are tool sets from UltraTool, ToolEyes, AutoTools, API-Bank and Glaive v2, plus a sample of `Agent-Ark/Toucan-1.5M` (apache-2.0; its card names Qwen3-32B, Kimi-K2 and GPT-OSS-120B, all open weights).
- **Decision:** `TSAI reserves`
- **Our opinion:** use this part only. Only this part names its generator. The card's text says about 1.2M trajectories but its table says 707,052: count the rows before sizing the mix. The licences of the seed tool sets are unchecked.

### `sft-agentic-nemotron-sft-agentic-v2-other` — Nemotron-SFT-Agentic-v2, search and customer-service parts

- **Stage:** SFT
- **Set:** `sft-agentic-nemotron-sft-agentic-v2-other`
- **Language:** English / web search, customer service
- **Source:** [`nvidia/Nemotron-SFT-Agentic-v2`](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Agentic-v2), the search part (about 7,000 trajectories) and the customer-service part (278,880 conversations)
- **Licence:** `cc-by-4.0, apache-2.0, mit` — Hugging Face tags read on 2 Nov 2026.
- **Generator model:** Not stated. The card says the search questions were written by "an LLM" and the answers by "a model equipped with a web-search tool", and it names no model for the customer-service part.
- **Decision:** `excluded` — TSAI Week 2 rule: sources we cannot trace are out, and we cannot show that no closed model wrote them.
- **Our opinion:** excluded until NVIDIA names the generator models. Check the real split names after loading: the card's file list and its text do not match.

### `sft-code-nemotron-swe-v3` — Nemotron-SFT-SWE-v3

- **Stage:** SFT
- **Set:** `sft-code-nemotron-swe-v3`
- **Language:** Code (agent trajectories)
- **Source:** [`nvidia/Nemotron-SFT-SWE-v3`](https://huggingface.co/datasets/nvidia/Nemotron-SFT-SWE-v3)
- **Licence:** `cc-by-4.0, apache-2.0, mit, bsd-3-clause, bsd-2-clause` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Not on the card (it names only the OpenHands, SWE-agent and mini-SWE-agent harnesses). NVIDIA's Nemotron 3 Ultra paper names MiniMax-M2.5 and Qwen3-Coder-480B-A35B-Instruct (open weights) for its SWE trajectories; not tied to this set by the card, verify
- **Decision:** `TSAI reserves`
- **Our opinion:** use. Mixed permissive licences. Check overlap with the SWE-bench variants we report.
- **Details and 20-row sample:** [nvidia__Nemotron-SFT-SWE-v3](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__Nemotron-SFT-SWE-v3)

### `sft-code-nemotron-terminal` — Nemotron-Terminal-Corpus

- **Stage:** SFT
- **Set:** `sft-code-nemotron-terminal`
- **Language:** Code (terminal agent)
- **Source:** [`nvidia/Nemotron-Terminal-Corpus`](https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-V3.2 (open weights) for both the synthetic tasks and the trajectories (paper, arXiv 2602.21193)
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. The teacher model is not stated on the card. Check Terminal-Bench overlap.
- **Details and 20-row sample:** [nvidia__Nemotron-Terminal-Corpus](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__Nemotron-Terminal-Corpus)

### `sft-code-opencodereasoning` — OpenCodeReasoning

- **Stage:** SFT
- **Set:** `sft-code-opencodereasoning`
- **Language:** Code (competitive)
- **Source:** [`nvidia/OpenCodeReasoning`](https://huggingface.co/datasets/nvidia/OpenCodeReasoning)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1 (open weights)
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. DeepSeek-R1-family traces, so check the teacher's terms. The card excludes the CodeContests and open-r1/codeforces test splits.
- **Details and 20-row sample:** [nvidia__OpenCodeReasoning](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__OpenCodeReasoning)

### `sft-code-opencodereasoning-2` — OpenCodeReasoning-2

- **Stage:** SFT
- **Set:** `sft-code-opencodereasoning-2`
- **Language:** Code (competitive)
- **Source:** [`nvidia/OpenCodeReasoning-2`](https://huggingface.co/datasets/nvidia/OpenCodeReasoning-2)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1 for solutions, QwQ for critiques (both open weights)
- **Decision:** `allowed (TSAI admitted, 11 Nov 2026)`
- **Our opinion:** use, check. Same teacher-terms check as OpenCodeReasoning.
- **Details and 20-row sample:** [nvidia__OpenCodeReasoning-2](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__OpenCodeReasoning-2)

### `sft-code-codeforces-cots` — codeforces-cots

- **Stage:** SFT
- **Set:** `sft-code-codeforces-cots`
- **Language:** Code (competitive)
- **Source:** [`open-r1/codeforces-cots`](https://huggingface.co/datasets/open-r1/codeforces-cots)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1 (open weights)
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. R1 traces on Codeforces problems. Use the `_decontaminated` configs.
- **Details and 20-row sample:** [open-r1__codeforces-cots](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/open-r1__codeforces-cots)

### `sft-indic-aya-collection` — aya_collection, templated Indic subset licence review

- **Stage:** SFT
- **Set:** `sft-indic-aya-collection`
- **Language:** Multilingual Indic (see the SFT mix proposal for target-language coverage)
- **Source:** [`CohereLabs/aya_collection`](https://huggingface.co/datasets/CohereLabs/aya_collection). The 10 subsets with permissive source licences are `templated_bengali_news`, `templated_indic_paraphrase`, `templated_indic_sentiment`, `templated_tamil_stories`, `templated_tamil_thirukkural`, `templated_telugu_food`, `templated_telugu_jokes`, `templated_telugu_news`, `templated_telugu_poems`, `templated_telugu_riddles`
- **Licence:** `apache-2.0` (Hub tag for the collection). The merged [source licence review](https://github.com/theschoolofai/era-v5-lab/pull/399) found 10 subsets with Apache 2.0, CC0, or MIT source licences. It excluded `templated_hindi_headline` (CC BY-NC-SA 4.0) and held `templated_hindi_news` for a TSAI decision (CC BY-SA 4.0).
- **Generator model:** None for the text. In these subsets, templates written by fluent speakers are applied to existing datasets (news, headlines, sentiment, paraphrase, jokes, poems, riddles, stories, couplets); no model writes the answers. The source datasets are not named on the card.
- **Decision:** `TSAI reserves`
- **Our opinion:** Consider the 10 subsets with permissive source licences for task-style supervision, subject to TSAI selection. Filter to the proposal languages, cap each subset, and fill any shortfall from `aya_dataset`.
- **Details and 20-row sample:** [CohereLabs__aya_collection](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/CohereLabs__aya_collection)

### `sft-indic-aya-collection-other` — aya_collection, translated datasets and other subsets

- **Stage:** SFT
- **Set:** `sft-indic-aya-collection-other`
- **Language:** 101 languages
- **Source:** [`CohereLabs/aya_collection`](https://huggingface.co/datasets/CohereLabs/aya_collection): the 19 `translated_*` datasets and every templated subset outside the 12 reviewed above
- **Licence:** `apache-2.0` — Hugging Face tag read on 2 Nov 2026.
- **Generator model:** The 19 datasets are English sets machine-translated with NLLB 3.3B (card). The card does not list the English sources or who wrote them. At least one is model-written: `soda`, whose card says the dialogues are distilled from InstructGPT (OpenAI, closed).
- **Decision:** `excluded` — TSAI Week 2 rule: text made by closed OpenAI models is out, and sources we cannot trace are out.
- **Our opinion:** excluded. Open question for TSAI: the card of `facebook/nllb-200-3.3B` gives the model licence as `cc-by-nc-4.0`. Whether translations made with it carry that restriction is not for us to decide. The other templated subsets (not Indic) are out of scope.

### `sft-indic-aya-dataset` — aya_dataset

- **Stage:** SFT
- **Set:** `sft-indic-aya-dataset`
- **Language:** Multilingual incl. Indic
- **Source:** [`CohereLabs/aya_dataset`](https://huggingface.co/datasets/CohereLabs/aya_dataset)
- **Licence:** `apache-2.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** None (human-written)
- **Decision:** `TSAI reserves`
- **Our opinion:** use. Human-written prompt/completion pairs under Apache-2.0 per the card. The cleanest Indic set found.
- **Details and 20-row sample:** [CohereLabs__aya_dataset](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/CohereLabs__aya_dataset)

### `sft-indic-indic-align` — indic-align

- **Stage:** SFT
- **Set:** `sft-indic-indic-align`
- **Language:** 14 Indic languages
- **Source:** [`ai4bharat/indic-align`](https://huggingface.co/datasets/ai4bharat/indic-align)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Llama-2-70B-Chat for many parts (Llama), plus translated human prompts; Mistral-7B in some parts
- **Decision:** `excluded` — TSAI rule in the G10 chat (30 Oct): data made by closed OpenAI, Anthropic, Google or Llama models stays excluded. Applied by us to this set. Reason: Many responses are Llama-2-70B-Chat outputs (Llama).
- **Our opinion:** excluded under that rule. The two subsets whose text is human-written are listed separately below (`sft-indic-indic-align-oasst-t`, `sft-indic-indic-align-dolly-t`); every other subset stays excluded.
- **Details and 20-row sample:** [ai4bharat__indic-align](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/ai4bharat__indic-align)

### `sft-indic-indic-align-oasst-t` — indic-align, `OpenAssistant_T` subset

- **Stage:** SFT
- **Set:** `sft-indic-indic-align-oasst-t`
- **Language:** 14 Indic languages, native script and romanised. G10 uses the native-script columns of the ten proposal languages (`hin_Deva`, `mar_Deva`, `tam_Taml`, `tel_Telu`, `kan_Knda`, `ben_Beng`, `guj_Gujr`, `mal_Mlym`, `ory_Orya`, `pan_Guru`).
- **Source:** [`ai4bharat/indic-align`](https://huggingface.co/datasets/ai4bharat/indic-align), file `indicalign-instruct/oasst/oasst.parquet` (19,909 conversations). The card: "Translated and Romanised version of OpenAssistant v1".
- **Licence:** `cc-by-4.0` (Hub tag of indic-align) — read on 6 Nov 2026. The source [`OpenAssistant/oasst1`](https://huggingface.co/datasets/OpenAssistant/oasst1) is `apache-2.0`. A tag is not legal clearance.
- **Generator model:** None for the text: oasst1 prompts and replies are written by human volunteers. Translation: IndicTrans2 (AI4Bharat, open weights, `mit` on [`ai4bharat/indictrans2-en-indic-1B`](https://huggingface.co/ai4bharat/indictrans2-en-indic-1B)). Not a Llama, closed or use-restricted model.
- **Decision:** `TSAI reserves`
- **Our opinion:** use. It is the only multi-turn, human-written Indic chat set that passes the rule: 12,686 of 19,909 conversations have two or more assistant turns. Machine translation errors are visible (product names translated literally, for example the SID sound chip as "side sound chip"; one number changed in the Urdu column), so do not use it for translation quality. In the `_Latn` columns the turn order is not reliable; use native script only. `sft/convert.py` takes one language per conversation (by `doc_id`), so the ten translations of one conversation are not all trained.
- **Details:** converted with `sft/convert.py --set sft-indic-indic-align-oasst-t`: 19,909 of 19,909 rows written, 0 skipped, all at effort `1k`; content sha256 of the full run `d672b433316d…`. `sft/decontam_run.py` on 6 Nov, fingerprints v2 full set (`set_sha256 2826a3b8…`): 9 flagged (`in22_conv`, `hle`), 0 canary, 19,900 kept, every reconciliation check passed.

### `sft-indic-indic-align-dolly-t` — indic-align, `Dolly_T` subset

- **Stage:** SFT
- **Set:** `sft-indic-indic-align-dolly-t`
- **Language:** 14 Indic languages, native script and romanised (same columns as above)
- **Source:** [`ai4bharat/indic-align`](https://huggingface.co/datasets/ai4bharat/indic-align), file `indicalign-instruct/dolly/Dolly.parquet` (15,011 rows). The card: "Translated and Romanised version of Dolly-15K".
- **Licence:** `cc-by-4.0` (Hub tag of indic-align) — read on 6 Nov 2026. The source [`databricks/databricks-dolly-15k`](https://huggingface.co/datasets/databricks/databricks-dolly-15k) is `cc-by-sa-3.0`: share-alike, attribution needed. A tag is not legal clearance.
- **Generator model:** None for the text (human-written by Databricks employees). Translation: IndicTrans2 (`mit`, open weights).
- **Decision:** `allowed (CC-BY-SA, attribution needed)`, as for `sft-dolly-15k`
- **Our opinion:** use only the rows that never had a context. The translation drops Dolly's `context` field: of the 4,456 Dolly rows with a context passage, 4,455 appear in `Dolly_T` with the question only (1,765 `closed_qa`, 1,504 `information_extraction`, 1,186 `summarization`). Trained as they are, they teach answers about a passage the model never sees. In the `_Latn` columns the answer comes before the question. `sft/convert.py` keeps a row only if its English question matches a `databricks-dolly-15k` row with no context (read from that set's Hub file).
- **Details:** 9 Nov, full set: 10,541 of 15,011 rows kept by the filter (4,455 had a context, 15 do not match a Dolly question exactly), 0 skipped, all at effort `1k`, content sha256 `3af21a7c294c…`. `sft/decontam_run.py`, fingerprints v2 full set (`set_sha256 2826a3b8…`): 0 flagged, 0 canary, 10,541 kept.

### `sft-indic-samvaad-hi` — samvaad-hi-v1

- **Stage:** SFT
- **Set:** `sft-indic-samvaad-hi`
- **Language:** Hindi, English, Hinglish
- **Source:** [`sarvamai/samvaad-hi-v1`](https://huggingface.co/datasets/sarvamai/samvaad-hi-v1)
- **Licence:** `apache-2.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Not stated on the card or in Sarvam's announcement; unknown
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. The card does not say which model wrote the replies.
- **Details and 20-row sample:** [sarvamai__samvaad-hi-v1](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/sarvamai__samvaad-hi-v1)

### `sft-indic-code-oss-codes-coding` — Coding-Conversational-Dataset-Indic

- **Stage:** SFT
- **Set:** `sft-indic-code-oss-codes-coding`
- **Language:** Indic (Hindi, Tamil, ...) + code
- **Source:** [`oss-codes/Coding-Conversational-Dataset-Indic`](https://huggingface.co/datasets/oss-codes/Coding-Conversational-Dataset-Indic)
- **Licence:** `mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Not stated; the card is empty
- **Decision:** `TSAI reserves`
- **Our opinion:** check. Small; origin and generator not verified.
- **Details and 20-row sample:** [oss-codes__Coding-Conversational-Dataset-Indic](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/oss-codes__Coding-Conversational-Dataset-Indic)

### `sft-indic-code-oss-codes-cs` — Computer-Science-Conversational-Dataset-Indic

- **Stage:** SFT
- **Set:** `sft-indic-code-oss-codes-cs`
- **Language:** Indic + computer science
- **Source:** [`oss-codes/Computer-Science-Conversational-Dataset-Indic`](https://huggingface.co/datasets/oss-codes/Computer-Science-Conversational-Dataset-Indic)
- **Licence:** `mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Not stated; the card is empty
- **Decision:** `TSAI reserves`
- **Our opinion:** check. Small; origin and generator not verified.
- **Details and 20-row sample:** [oss-codes__Computer-Science-Conversational-Dataset-Indic](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/oss-codes__Computer-Science-Conversational-Dataset-Indic)

### `sft-indic-math-orca-math-hi` — orca-math-word-problems-200k-hindi-filtered

- **Stage:** SFT
- **Set:** `sft-indic-math-orca-math-hi`
- **Language:** Hindi (math)
- **Source:** [`BhabhaAI/orca-math-word-problems-200k-hindi-filtered`](https://huggingface.co/datasets/BhabhaAI/orca-math-word-problems-200k-hindi-filtered)
- **Licence:** `mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** GPT-4 (OpenAI, closed) via Orca-Math, then translated
- **Decision:** `excluded` — TSAI ruling in the G10 chat (30 Oct): quarantined sets stay out of the lab and out of every training mix. Reason: Hindi translation of Orca-Math, which was generated with GPT-4, so OpenAI terms apply.
- **Our opinion:** excluded, as ruled by TSAI. Hindi translation of Orca-Math, which is GPT-4 generated, so OpenAI terms apply.
- **Details and 20-row sample:** [BhabhaAI__orca-math-word-problems-200k-hindi-filtered](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/BhabhaAI__orca-math-word-problems-200k-hindi-filtered)

### `sft-indic-math-aryabhatta-orca-hi` — Aryabhatta-Orca-Maths-Hindi

- **Stage:** SFT
- **Set:** `sft-indic-math-aryabhatta-orca-hi`
- **Language:** Hindi (math)
- **Source:** [`GenVRadmin/Aryabhatta-Orca-Maths-Hindi`](https://huggingface.co/datasets/GenVRadmin/Aryabhatta-Orca-Maths-Hindi)
- **Licence:** `mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** GPT-4 (OpenAI, closed) via Orca-Math, then translated
- **Decision:** `excluded` — TSAI ruling in the G10 chat (30 Oct): quarantined sets stay out of the lab and out of every training mix. Reason: Hindi translation of Orca-Math, which was generated with GPT-4, so OpenAI terms apply.
- **Our opinion:** excluded, as ruled by TSAI. Hindi translation of Orca-Math, which is GPT-4 generated, so OpenAI terms apply.
- **Details and 20-row sample:** [GenVRadmin__Aryabhatta-Orca-Maths-Hindi](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/GenVRadmin__Aryabhatta-Orca-Maths-Hindi)

### `sft-math-nemotron-proofs` — Nemotron-Math-Proofs-v1

- **Stage:** SFT
- **Set:** `sft-math-nemotron-proofs`
- **Language:** English / Mathematics
- **Source:** [`nvidia/Nemotron-Math-Proofs-v1`](https://huggingface.co/datasets/nvidia/Nemotron-Math-Proofs-v1)
- **Licence:** `cc-by-sa-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** gpt-oss-120b (statement formalisation) and Goedel-Prover-V2-32B (proofs)
- **Decision:** `allowed (CC-BY-SA, attribution needed)` — TSAI ruling (G10 chat, 30 Oct): CC-BY-SA data is allowed with attribution when a permissive model made it, and data made by gpt-oss models is allowed because the weights are open under Apache-2.0; data made by closed OpenAI, Anthropic, Google or Llama models stays excluded. Statements were formalized by gpt-oss-120b (open-weight, Apache-2.0) and proofs attempted by Goedel-Prover-V2-32B; no OpenAI API or Llama outputs.
- **Our opinion:** use. CC-BY-SA-4.0: carry attribution and keep the share-alike terms.
- **Details and 20-row sample:** [nvidia__Nemotron-Math-Proofs-v1](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__Nemotron-Math-Proofs-v1)

### `sft-math-nemotron-math-v2` — Nemotron-Math-v2

- **Stage:** SFT
- **Set:** `sft-math-nemotron-math-v2`
- **Language:** English / Mathematics
- **Source:** [`nvidia/Nemotron-Math-v2`](https://huggingface.co/datasets/nvidia/Nemotron-Math-v2)
- **Licence:** `cc-by-4.0, cc-by-sa-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** gpt-oss-120b (all solution traces)
- **Decision:** `allowed (CC-BY-SA, attribution needed)` — TSAI ruling (G10 chat, 30 Oct): CC-BY-SA data is allowed with attribution when a permissive model made it, and data made by gpt-oss models is allowed because the weights are open under Apache-2.0; data made by closed OpenAI, Anthropic, Google or Llama models stays excluded. All solution traces came from gpt-oss-120b (open-weight, Apache-2.0); the AoPS part is CC-BY-4.0 and the StackExchange and MathGenSelect parts are CC-BY-SA-4.0.
- **Our opinion:** use, with attribution. The card says it is decontaminated.
- **Details and 20-row sample:** [nvidia__Nemotron-Math-v2](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__Nemotron-Math-v2)

### `sft-math-openmathinstruct-2` — OpenMathInstruct-2

- **Stage:** SFT
- **Set:** `sft-math-openmathinstruct-2`
- **Language:** English / Mathematics
- **Source:** [`nvidia/OpenMathInstruct-2`](https://huggingface.co/datasets/nvidia/OpenMathInstruct-2)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Llama-3.1-405B-Instruct (Llama)
- **Decision:** `excluded` — TSAI ruling in the G10 chat (30 Oct): quarantined sets stay out of the lab and out of every training mix. Reason: Solutions were generated with Llama-3.1-405B, and the Llama licence limits using its outputs to train other models.
- **Our opinion:** excluded, as ruled by TSAI. Generated with Llama-3.1-405B, so Llama licence terms apply. Built from GSM8K and MATH train problems.
- **Details and 20-row sample:** [nvidia__OpenMathInstruct-2](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__OpenMathInstruct-2)

### `sft-rl-math-openmathreasoning` — OpenMathReasoning

- **Stage:** SFT + RL prompts
- **Set:** `sft-rl-math-openmathreasoning`
- **Language:** English / Mathematics
- **Source:** [`nvidia/OpenMathReasoning`](https://huggingface.co/datasets/nvidia/OpenMathReasoning)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1 and QwQ-32B (open weights)
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. Traces from DeepSeek-R1 and QwQ, so check teacher terms. The card says benchmark decontamination was applied.
- **Details and 20-row sample:** [nvidia__OpenMathReasoning](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__OpenMathReasoning)

### `sft-math-openr1-math` — OpenR1-Math-220k

- **Stage:** SFT
- **Set:** `sft-math-openr1-math`
- **Language:** English / Mathematics
- **Source:** [`open-r1/OpenR1-Math-220k`](https://huggingface.co/datasets/open-r1/OpenR1-Math-220k)
- **Licence:** `apache-2.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1 (open weights)
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. R1 traces on NuminaMath 1.5 problems, so it inherits the NuminaMath overlap.
- **Details and 20-row sample:** [open-r1__OpenR1-Math-220k](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/open-r1__OpenR1-Math-220k)

### `sft-math-numinamath-1.5` — NuminaMath-1.5

- **Stage:** SFT
- **Set:** `sft-math-numinamath-1.5`
- **Language:** English / Mathematics
- **Source:** [`project-numina/NuminaMath-1.5`](https://huggingface.co/datasets/project-numina/NuminaMath-1.5)
- **Licence:** `apache-2.0` — Hugging Face tag and card read on 2 Nov 2026. A tag is not legal clearance.
- **Generator model:** Not stated on the card. Its source table includes `orca_math` (151,934 problems), `synthetic_math` (148,712) and `metamath` (11,014): 311,660 of 896,215 problems, all model-written sets. The card of `microsoft/orca-math-word-problems-200k` says its questions and answers were made with Azure GPT-4 Turbo (OpenAI, closed). The cards of the other two name no model (MetaMathQA says only that it is augmented from GSM8K and MATH). The card calls itself the second iteration of NuminaMath-CoT and only removes `synthetic_amc`, so the older sources probably keep the NuminaMath-CoT solutions that we record as GPT-4 rewritten.
- **Decision:** `excluded` — TSAI Week 2 rule: text made by closed OpenAI models is out (`orca_math` is GPT-4 Turbo), and sources we cannot trace are out.
- **Our opinion:** excluded for the same reason as `sft-math-numinamath-cot`. A subset that keeps only the manually parsed sources (`olympiads_ref`, `amc_aime`, `cn_contest`, `inequalities`, `number_theory`) could be reconsidered if TSAI accepts that those solutions are human-written. Not assumed here.
- **Details and 20-row sample:** [project-numina__NuminaMath-1.5](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/project-numina__NuminaMath-1.5)

### `sft-math-numinamath-cot` — NuminaMath-CoT

- **Stage:** SFT
- **Set:** `sft-math-numinamath-cot`
- **Language:** English / Mathematics
- **Source:** [`project-numina/NuminaMath-CoT`](https://huggingface.co/datasets/project-numina/NuminaMath-CoT)
- **Licence:** `apache-2.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** GPT-4 (OpenAI, closed) rewrote solutions into chain-of-thought; GPT-4o was used for the tool-integrated set (secondary sources, not on the card; verify)
- **Decision:** `excluded` — TSAI rule in the G10 chat (30 Oct): data made by closed OpenAI, Anthropic, Google or Llama models stays excluded. Applied by us to this set. Reason: Solutions were rewritten with GPT-4 / GPT-4o (OpenAI, closed).
- **Our opinion:** excluded under that rule. Ask TSAI if a partial use (for example only the human-written parts) is acceptable.
- **Details and 20-row sample:** [project-numina__NuminaMath-CoT](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/project-numina__NuminaMath-CoT)

### `sft-stem-code-nemotron-post-v1` — Nemotron-Post-Training-Dataset-v1

- **Stage:** SFT
- **Set:** `sft-stem-code-nemotron-post-v1`
- **Language:** English / Math, STEM, Code
- **Source:** [`nvidia/Nemotron-Post-Training-Dataset-v1`](https://huggingface.co/datasets/nvidia/Nemotron-Post-Training-Dataset-v1)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1-0528 and Qwen3-235B-A22B (open weights); Llama-3.3-Nemotron-Super is the model it was built to train
- **Decision:** `excluded` — TSAI ruling in the G10 chat (30 Oct): quarantined sets stay out of the lab and out of every training mix. Reason: Responses come from Qwen and DeepSeek teacher models; gated, and prompt provenance is not cleared.
- **Our opinion:** excluded, as ruled by TSAI. Responses come from Qwen and DeepSeek models, so check their terms. Some prompts must be fetched separately from their original sources under their own terms.
- **Details and 20-row sample:** [nvidia__Nemotron-Post-Training-Dataset-v1](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__Nemotron-Post-Training-Dataset-v1)

### `sft-stem-code-nemotron-post-v2` — Nemotron-Post-Training-Dataset-v2

- **Stage:** SFT
- **Set:** `sft-stem-code-nemotron-post-v2`
- **Language:** Multilingual / Math, STEM, Code
- **Source:** [`nvidia/Nemotron-Post-Training-Dataset-v2`](https://huggingface.co/datasets/nvidia/Nemotron-Post-Training-Dataset-v2)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026; gated dataset. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1-0528, Qwen3-235B-A22B, Qwen3-30B-A3B (open weights), Qwen2.5-14B-Instruct and Qwen2.5-32B-Instruct-AWQ; the card does not map models to subsets (read from the Hub page, not the gated files)
- **Decision:** `excluded` — TSAI ruling in the G10 chat (30 Oct): quarantined sets stay out of the lab and out of every training mix. Reason: Responses come from Qwen and DeepSeek teacher models; gated, and prompt provenance is not cleared.
- **Our opinion:** excluded, as ruled by TSAI. Gated so the card was not read. Earlier notes say models trained on it may fall under Qwen and DeepSeek licences.
- **Details and 20-row sample:** [nvidia__Nemotron-Post-Training-Dataset-v2](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__Nemotron-Post-Training-Dataset-v2)

### `sft-stem-code-openthoughts3` — OpenThoughts3-1.2M

- **Stage:** SFT
- **Set:** `sft-stem-code-openthoughts3`
- **Language:** English / Math, Code, Science
- **Source:** [`open-thoughts/OpenThoughts3-1.2M`](https://huggingface.co/datasets/open-thoughts/OpenThoughts3-1.2M)
- **Licence:** `apache-2.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** QwQ-32B (open weights)
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. Mixed question sources; no decontamination stated on the card.
- **Details and 20-row sample:** [open-thoughts__OpenThoughts3-1.2M](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/open-thoughts__OpenThoughts3-1.2M)

### `sft-science-nemotron-science` — Nemotron-Science-v1

- **Stage:** SFT
- **Set:** `sft-science-nemotron-science`
- **Language:** English / Science
- **Source:** [`nvidia/Nemotron-Science-v1`](https://huggingface.co/datasets/nvidia/Nemotron-Science-v1)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** gpt-oss-120b (open weights)
- **Decision:** `TSAI reserves`
- **Our opinion:** use, check. Generated with GPT-OSS-120B (open-weight). Questions mimic GPQA style, so run a near-duplicate check against GPQA. Per TSAI, the source name goes to G9 (Evaluation) for a decontamination test; no use before that.
- **Details and 20-row sample:** [nvidia__Nemotron-Science-v1](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nvidia__Nemotron-Science-v1)


### `sft-chat-nemotron-if-v1` — Nemotron-Instruction-Following-Chat-v1

- **Stage:** SFT
- **Set:** `sft-chat-nemotron-if-v1`
- **Language:** English / Chat, instruction following, JSON
- **Source:** [nvidia/Nemotron-Instruction-Following-Chat-v1](https://huggingface.co/datasets/nvidia/Nemotron-Instruction-Following-Chat-v1)
- **Licence:** ODC-By-1.0 (chat); CC-BY-4.0 (structured outputs); headline tag alone is incomplete
- **Generator model:** GPT-OSS-120B, Qwen3-235B-A22B-Thinking-2507, Qwen3-235B-A22B-Instruct-2507 for chat and simulated follow-up turns; structured-output generator not separately disclosed
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: English instruction following, multi-turn chat and structured JSON. Generator: GPT-OSS-120B and the two Qwen3-235B variants listed above; the structured-output generator is not separately named. Subset/source relationship: refreshed chat from Nemotron-Post-Training-Dataset-v2 plus new instruction data; loader splits `chat_if` and `structured_outputs`. The card reports 426,009 chat and 4,969 structured-output examples, 430,978 total, about 6.6 GB. Kolibri uses these seeds and regenerates answers with GLM-5.2/GLM-5.3, extending conversations up to 50 turns; those derived answers are not the original HF release ([Kolibri report, section 3.1.1](https://aleph-alpha.com/downloads/tech-report.pdf)). TSAI decides use and subset selection. Source check: 2026-11-01; [publisher card at revision 83dcd3aded0d289b0bbc018d3f9af4c5dd4005df](https://huggingface.co/datasets/nvidia/Nemotron-Instruction-Following-Chat-v1/blob/83dcd3aded0d289b0bbc018d3f9af4c5dd4005df/README.md).

### `sft-chat-nemotron-if-v2` — Nemotron-SFT-Instruction-Following-Chat-v2

- **Stage:** SFT
- **Set:** `sft-chat-nemotron-if-v2`
- **Language:** English / Chat, instruction following
- **Source:** [nvidia/Nemotron-SFT-Instruction-Following-Chat-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Instruction-Following-Chat-v2)
- **Licence:** ODC-By (card does not specify version)
- **Generator model:** Kimi-K2-Thinking, GLM-4.6, Qwen3-235B-A22B-Thinking-2507, GPT-OSS-120b, Kimi-K2-Instruct-0905, Qwen3-235B-A22B-Instruct-2507; no per-split model mapping
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: English instruction following and multi-turn chat with or without reasoning. Generator: the six Kimi, GLM-4.6, Qwen3 and GPT-OSS checkpoints listed above; the card gives no per-split mapping. Subset/source relationship: refreshed version of Nemotron-Instruction-Following-Chat-v1, with `reasoning_on` and `reasoning_off` splits; the card reports 1,998,568 examples, about 15 GB. Kolibri regenerates these seeds with GLM-5.2/GLM-5.3; its reasoning-off generation and long conversations describe a derived pool ([Kolibri report, section 3.1.1](https://aleph-alpha.com/downloads/tech-report.pdf)). Account for shared v1/v2 seeds when selecting the mix. TSAI decides use. Source check: 2026-11-01; [publisher card at revision 1a9454ed054b8544503ab8d8c0a519d141a44c5b](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Instruction-Following-Chat-v2/blob/1a9454ed054b8544503ab8d8c0a519d141a44c5b/README.md).

### `sft-science-nemotron-science-v2` — Nemotron-SFT-Science-v2

- **Stage:** SFT
- **Set:** `sft-science-nemotron-science-v2`
- **Language:** English / Physics, biology, chemistry
- **Source:** [nvidia/Nemotron-SFT-Science-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2)
- **Licence:** CC-BY-SA-4.0 (attribution and share-alike obligations)
- **Generator model:** GPT-OSS (size not specified), Kimi-K2-Instruct, DeepSeek-V3.2, DeepSeek-V4-Pro for solutions; no complete per-subset prompt-generator mapping
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: supplementary science reasoning with CoT, Python tools and search tools. Generator: GPT-OSS, Kimi-K2-Instruct, DeepSeek-V3.2 and DeepSeek-V4-Pro for solutions, without a complete subset-to-prompt-generator mapping. Subset/source relationship: replacement for Nemotron-Science-v1; `syn_mcq` has 96,610 examples, `vendor` 221,598, `rqa` 413,519 and Stack Exchange-derived `so` 2,105,985; publisher total 2,837,712 rows, about 49 GB. Kolibri specifically regenerates synthetic-MCQ completions with Qwen3.8-27B ([Kolibri report, section 3.1.1](https://aleph-alpha.com/downloads/tech-report.pdf)); that model is not the generator of the complete original release. Retain source attribution/share-alike notices. TSAI decides use. Source check: 2026-11-01; [publisher card at revision 6536a5021222a94126968e8c92f29ee47fc8a7df](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Science-v2/blob/6536a5021222a94126968e8c92f29ee47fc8a7df/README.md).

### `sft-science-glm51-phd` — GLM-5.1-Reasoning-1M-Cleaned — PHD-Science only

- **Stage:** SFT
- **Set:** `sft-science-glm51-phd`
- **Language:** Science; release language tags: English / Chinese
- **Source:** [Jackrong/GLM-5.1-Reasoning-1M-Cleaned](https://huggingface.co/datasets/Jackrong/GLM-5.1-Reasoning-1M-Cleaned)
- **Licence:** Apache-2.0 (cleaned and upstream publisher cards)
- **Generator model:** GLM-5.1 generates reasoning and final answers; Jackrong cleans/reformats the upstream release.
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: graduate-level physics, chemistry and biology reasoning SFT. Generator: GLM-5.1, not GLM-5.3. Subset/source relationship: select only `PHD-Science`, with 103,706 kept records from 103,759 processed; this is a cleaned derivative of Kassadin88/GLM-5.1-1000000x, whose prompts come from KIMI-K2.5-1000000x. This entry does not add the main, Math or Multilingual-STEM configs. The Apache-2.0 cards do not establish every prompt's original rights; TSAI decides source suitability and use. Kolibri use is not confirmed by the report. [Upstream card](https://huggingface.co/datasets/Kassadin88/GLM-5.1-1000000x). Source check: 2026-11-03; [publisher card at revision f6d6ccafe40359d5ec2515ee25e92aac8cae9c3d](https://huggingface.co/datasets/Jackrong/GLM-5.1-Reasoning-1M-Cleaned/blob/f6d6ccafe40359d5ec2515ee25e92aac8cae9c3d/README.md).

### `sft-safety-indicguard` — IndicGuard

- **Stage:** SFT
- **Set:** `sft-safety-indicguard`
- **Language:** 10 Indic languages + English reference
- **Source:** [l3cube-pune/IndicGuard](https://huggingface.co/datasets/l3cube-pune/IndicGuard)
- **Licence:** CC-BY-4.0
- **Generator model:** Google Translate API translates; responses are inherited from Nemotron or generated by unnamed LLMs; labels combine retained human and LLM-jury annotations.
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: culturally relevant Indic safety classification and refusal supervision, with about 334,160 examples reported. Generator: Google Translate for translation; responses are inherited from Nemotron or produced by an unnamed LLM pipeline, with human/LLM label sources. Subset/source relationship: a translated and augmented derivative of the existing `sft-safety-nemotron-guard-v3` entry, covering ten Indic languages plus English reference data, with train/validation/test/refusal splits. Preserve shared source IDs when selecting both datasets to avoid double counting. TSAI decides the suitable task format, provenance requirements and use. Kolibri use is not confirmed by the report. Source check: 2026-11-01; [publisher card at revision f60250767f0ab6ae8f1d99831516fe8a6b453f8d](https://huggingface.co/datasets/l3cube-pune/IndicGuard/blob/f60250767f0ab6ae8f1d99831516fe8a6b453f8d/README.md).

### `sft-safety-nemotron-guard-v3` — Nemotron-Safety-Guard-Dataset-v3

- **Stage:** SFT
- **Set:** `sft-safety-nemotron-guard-v3`
- **Language:** English, Hindi + 10 other languages
- **Source:** [nvidia/Nemotron-Safety-Guard-Dataset-v3](https://huggingface.co/datasets/nvidia/Nemotron-Safety-Guard-Dataset-v3)
- **Licence:** CC-BY-4.0
- **Generator model:** CultureGuard paper: Mixtral-8x22B adapts content; Google Translate translates; Mixtral-8x7B creates jailbreak prompts and Mixtral-8x22B responses; jury includes Llama/Nemotron and Qwen models.
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: multilingual prompt/response safety classification, including English and Hindi; the card reports 514,617 examples. Generator: CultureGuard documents Mixtral generation/adaptation, Google Translate and an LLM jury; the current expanded release needs its own subset mapping. Subset/source relationship: culturally adapted/translated data derived from NVIDIA AEGIS 2.0, with added jailbreak pairs; previously named Nemotron-Content-Safety-Dataset-Multilingual-v1. It is also the parent source of the IndicGuard entry above. Keep classification labels distinct from desired assistant completions. Kolibri use is not confirmed by the report. Source check: 2026-11-01; [publisher card at revision a3f7ecb3433d1933701a83f18de16c36934a7f51](https://huggingface.co/datasets/nvidia/Nemotron-Safety-Guard-Dataset-v3/blob/a3f7ecb3433d1933701a83f18de16c36934a7f51/README.md). Additional primary evidence: [CultureGuard methodology, sections 3.1–3.2](https://arxiv.org/html/2508.01710).

### `sft-safety-aegis-v1` — Aegis-AI-Content-Safety-Dataset-1.0

- **Stage:** SFT
- **Set:** `sft-safety-aegis-v1`
- **Language:** Primarily English
- **Source:** [nvidia/Aegis-AI-Content-Safety-Dataset-1.0](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-1.0)
- **Licence:** CC-BY-4.0; card also contains research-purpose/dialogue-training restrictions
- **Generator model:** Mistral-7B-v0.1 generates responses from HH-RLHF prompts; NVIDIA humans annotate safety at dialogue level.
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: English guard/classification supervision with dialogue-level safety labels; the card reports 10,798 training and 1,199 test examples. Generator: Mistral-7B-v0.1 responses with human NVIDIA safety annotations. Subset/source relationship: prompts come from the harmlessness portion of the existing `rl-safety-hh-rlhf` source, with new Mistral answers; this is a derivative, not the original HH response pairs. AEGIS 1.0 is also called Nemotron Content Safety Dataset V1. The card has differing direct-use and dialogue-training statements, which TSAI can assess alongside CC-BY-4.0. TSAI decides use. Kolibri use is not confirmed by the report. Source check: 2026-11-01; [publisher card at revision bd96d862068e47630197de64eb91f8d1481ff3e0](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-1.0/blob/bd96d862068e47630197de64eb91f8d1481ff3e0/README.md).

### `sft-oasst2` — oasst2

- **Stage:** SFT
- **Set:** `sft-oasst2`
- **Language:** Multilingual; English, sparse Hindi/Bengali
- **Source:** [OpenAssistant/oasst2](https://huggingface.co/datasets/OpenAssistant/oasst2)
- **Licence:** Apache-2.0
- **Generator model:** Crowdsourced human messages and possible synthetic nodes; schema records synthetic and model_name, so generator provenance must be checked per conversation path.
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: general assistant conversation SFT and ranked sibling-response comparisons; the card reports 135,174 ready-export messages, not conversations. Generator: crowdsourced messages; synthetic nodes, if present, are identified by `synthetic` and `model_name`. Subset/source relationship: OpenAssistant message trees with ready-export and all-tree views; select complete reviewed conversation paths and preserve parent context. It is not a dedicated Indic safety corpus; Hindi/Bengali coverage is small. TSAI decides the release/view and any synthetic-message selection. Kolibri use is not confirmed by the report. Source check: 2026-11-01; [publisher card at revision 179dd21fc55192153d94adb0e0ce8f69e222bf75](https://huggingface.co/datasets/OpenAssistant/oasst2/blob/179dd21fc55192153d94adb0e0ce8f69e222bf75/README.md).

### `sft-safety-wildjailbreak` — wildjailbreak

- **Stage:** SFT
- **Set:** `sft-safety-wildjailbreak`
- **Language:** English
- **Source:** [allenai/wildjailbreak](https://huggingface.co/datasets/allenai/wildjailbreak)
- **Licence:** ODC-By; gated AI2 conditions
- **Generator model:** GPT-4 generates prompts; GPT-3.5 generates refusals/benign responses; Mixtral-8x7B and GPT-4 create adversarial variants.
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: safety SFT with refusals for harmful requests and helpful answers for benign lookalikes, addressing jailbreaks and over-refusal. Generator: GPT-4 creates vanilla prompts, GPT-3.5 writes completions, and Mixtral-8x7B/GPT-4 form adversarial variants. Subset/source relationship: the train portion contains vanilla/adversarial harmful/benign categories; this is a separate dataset from WildGuardMix, not an already-listed subset. The earlier exclusion applied the week 2 closed-model rule; the publisher explicitly presents it as safety-training data, so this is not a universal claim that it cannot train a model. ODC-By and the access terms remain recorded for TSAI.  Kolibri use is not confirmed by the report. Source check: 2026-11-01; [HF metadata](https://huggingface.co/api/datasets/allenai/wildjailbreak/revision/5ddc12a7894f842b0619b8e1c7ee496b198af009) and [public card](https://huggingface.co/datasets/allenai/wildjailbreak); raw README at `5ddc12a7894f842b0619b8e1c7ee496b198af009` was access-gated; no gate was accepted.

### `sft-safety-nemotron-sft-v2` — Nemotron-SFT-Safety-v2

- **Stage:** SFT
- **Set:** `sft-safety-nemotron-sft-v2`
- **Language:** English, German, Spanish, French, Japanese, Italian, Chinese
- **Source:** [nvidia/Nemotron-SFT-Safety-v2](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Safety-v2)
- **Licence:** CC-BY-4.0; additional Apache-2.0 / MIT terms
- **Generator model:** English response/reasoning model not named on the card; Riva-Translate-4B-Instruct-v1.1 translates.
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: safe-response SFT, jailbreak resistance, reduced over-refusal, bias and leakage mitigation. Generator: English teacher undisclosed; Riva translates. Subset/source relationship: English matches Safety-v1, with six new translation languages and no Indic language. Prompts reuse AEGIS 2.0, Gretel Safety Alignment v1 and HarmfulTasks; original answers are replaced. The card reports 130,350 examples (43,521 English). Avoid duplicate v1/translated content across splits. Kolibri use is not confirmed by the report. TSAI decides use. Source check: 2026-11-03; [publisher card at revision 8a40a63c9a1a340874b874f980953be53bff0a07](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Safety-v2/blob/8a40a63c9a1a340874b874f980953be53bff0a07/README.md).

### `sft-code-nemotron-opencode` — Nemotron-SFT-OpenCode-v1

- **Stage:** SFT
- **Set:** `sft-code-nemotron-opencode`
- **Language:** English / Code (agentic CLI, tool use, agent skills)
- **Source:** [`nvidia/Nemotron-SFT-OpenCode-v1`](https://huggingface.co/datasets/nvidia/Nemotron-SFT-OpenCode-v1)
- **Licence:** `cc-by-4.0` — Hugging Face tag and card. The card says it is ready for commercial use. Attribution is needed.
- **Generator model:** gpt-oss-120b (Apache-2.0) writes the questions and agent skills; Qwen3-Coder-480B-A35B-Instruct (Apache-2.0) writes the agentic solution traces and also simulates the user answers in the `question_tool` subsets. Both are open weights.
- **Decision:** `TSAI reserves` — passes the 3 Nov TSAI generator rule: every generator named on the card is an open-weight model under Apache-2.0, and no closed or Llama model appears.
- **Our opinion:** use. Six subsets (`general`, `bash_only_tool`, `bash_only_tool_skills`, `agent_skills`, `question_tool`, `agent_skills_question_tool`). The data is synthetic and not execution-verified on the card, so the Team 9 decontamination test is still needed.
- **Added by:** Tanmay Sharma (Week 2 rotation, 4 Nov 2026). Hugging Face cards and generator-model pages read on 4 Nov 2026. A tag is not legal clearance.

### `sft-code-nemotron-cuda` — Nemotron-SFT-CUDA-v1

- **Stage:** SFT
- **Set:** `sft-code-nemotron-cuda`
- **Language:** English / Code (CUDA kernels)
- **Source:** [`nvidia/Nemotron-SFT-CUDA-v1`](https://huggingface.co/datasets/nvidia/Nemotron-SFT-CUDA-v1)
- **Licence:** `cc-by-4.0` — Hugging Face tag and card; the card says ready for commercial use. Attribution is needed.
- **Generator model:** GLM-4.7 (MIT, open weights) inside an OpenCode agent writes the problems and, in a second pass, the solutions. The seed code comes from `nvidia/Nemotron-Pretraining-Code-v2` CUDA files, which the card describes as permissively licensed.
- **Decision:** `TSAI reserves` — passes the 3 Nov TSAI generator rule: the only generator is an open-weight MIT model, and each kept trace passes hidden tests with no Compute-Sanitizer errors (execution-verified).
- **Our opinion:** use. Small set (about 1K to 10K rows). The seed files keep their own per-file licences and the card does not list them, so keep the source reference per row for attribution.
- **Added by:** Tanmay Sharma (Week 2 rotation, 4 Nov 2026). Hugging Face cards and generator-model pages read on 4 Nov 2026. A tag is not legal clearance.

### `sft-math-nemotron-sft-math-v4` — Nemotron-SFT-Math-v4

- **Stage:** SFT
- **Set:** `sft-math-nemotron-sft-math-v4`
- **Language:** English / Mathematics
- **Source:** [`nvidia/Nemotron-SFT-Math-v4`](https://huggingface.co/datasets/nvidia/Nemotron-SFT-Math-v4)
- **Licence:** `cc-by-4.0` for AoPS-derived samples and `cc-by-sa-4.0` for Math StackExchange-derived samples (card terms; Hub tags list both). Attribution is needed, and share-alike applies to the StackExchange part.
- **Generator model:** DeepSeek-V4-Pro (MIT, open weights) in High mode writes every solution. The problems are human-written, taken from `nvidia/Nemotron-Math-v2` (AoPS and Math StackExchange / MathOverflow). Only solutions whose final answer matches the reference answer are kept.
- **Decision:** `allowed (CC-BY-SA, attribution needed)` — TSAI ruling (G10 chat, 30 Oct): CC-BY-SA data is allowed with attribution when a permissive model made it. DeepSeek-V4-Pro is MIT, so it passes the 3 Nov generator rule.
- **Our opinion:** use, with attribution. The card calls this a direct replacement for `Nemotron-SFT-Math-v3`, so use v4 and not both.
- **Added by:** Tanmay Sharma (Week 2 rotation, 4 Nov 2026). Hugging Face cards and generator-model pages read on 4 Nov 2026. A tag is not legal clearance.

### `sft-math-nemotron-proofs-v3-sft` — Nemotron-Math-Proofs-v3-SFT

- **Stage:** SFT
- **Set:** `sft-math-nemotron-proofs-v3-sft`
- **Language:** English / Mathematics (proofs)
- **Source:** [`nvidia/Nemotron-Math-Proofs-v3-SFT`](https://huggingface.co/datasets/nvidia/Nemotron-Math-Proofs-v3-SFT)
- **Licence:** `cc-by-4.0` — Hugging Face tag and card. The card gives one licence label, `cc-by-4.0`, for every sample. Attribution is needed.
- **Generator model:** DeepSeek-V4-Pro (MIT, open weights) in Max mode writes all four trace types (proof generation, proof refinement, verification, meta-verification). The 15,879 source problems are human-written AoPS proof problems from `nvidia/Nemotron-Math-Proofs-v1`.
- **Decision:** `TSAI reserves` — passes the 3 Nov TSAI generator rule: the only generator is an open-weight MIT model and the problems are human-written.
- **Our opinion:** use. 414,890 samples over 15,818 unique problems. Proof correctness is judged by model verifier traces, not by execution, so treat the traces as unverified proofs. The same problems appear in `sft-math-nemotron-proofs`, so de-duplicate by problem.
- **Added by:** Tanmay Sharma (Week 2 rotation, 4 Nov 2026). Hugging Face cards and generator-model pages read on 4 Nov 2026. A tag is not legal clearance.

### `sft-code-swe-zero-openhands` — SWE-Zero-openhands-trajectories

- **Stage:** SFT
- **Set:** `sft-code-swe-zero-openhands`
- **Language:** Code (agent trajectories)
- **Source:** [`nvidia/SWE-Zero-openhands-trajectories`](https://huggingface.co/datasets/nvidia/SWE-Zero-openhands-trajectories)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 3 Nov 2026. A tag is not legal clearance. Attribution must go in the model card.
- **Generator model:** Qwen3-Coder-480B-A35B-Instruct (Apache-2.0, open weights) via OpenHands, per the card. R2E-Gym issue statements were also written by Qwen3-Coder.
- **Decision:** `TSAI reserves`
- **Our opinion:** use. Same generator as `sft-code-swe-rebench-openhands`. The Claude-vs-Qwen audit is clean.
- **Audit (3 Nov 2026):** the dataset has no per-row field naming the generating model, so every row was checked. All 64 parquet shards, 318,115 trajectories (SWE-Fixer-Train-110K 128,628; SWE-Gym-Raw 128,176; SWE-rebench 51,808; R2E-Gym-Subset 9,503). Every row has the same OpenHands system prompt and the same four tools (`str_replace_editor`, `execute_bash`, `think`, `finish`). No `model_patch` carries a `Co-Authored-By: Claude` or "Generated with Claude Code" line, and no assistant or system message identifies the model as Claude. Four trajectories matched the identity pattern; all are about Anthropic's own API (mlflow, haystack), which is repo subject matter, not the generator. Repo licences: Apache-2.0 129,074; MIT 94,262; BSD-3-Clause 78,484; BSD-2-Clause 15,472; MIT-0 820; BSD-3-Clause-Clear 3. The check is keyword-based and cannot detect Claude text with no identity or attribution marker. The card's "BSD-2-Claude" is a typo for BSD-2-Clause.
- **Added by:** SomaKorada07 (Week 2 rotation, 4 Nov 2026). Hugging Face cards read on 3 Nov 2026.

### `sft-math-openr1-math-raw` — OpenR1-Math-Raw

- **Stage:** SFT
- **Set:** `sft-math-openr1-math-raw`
- **Language:** English / Mathematics
- **Source:** [`open-r1/OpenR1-Math-Raw`](https://huggingface.co/datasets/open-r1/OpenR1-Math-Raw)
- **Licence:** `apache-2.0` — Hugging Face tag read on 3 Nov 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1 (MIT, open weights) writes 1 to 8 traces per problem (516,499 problems, 1,209,403 traces). Two verifiers check them: Math Verify and Llama-3.3-70B-Instruct as judge (Llama 3.3 Community Licence; it only labels, it writes no training text).
- **Decision:** `TSAI reserves`
- **Decision note:** inherits NuminaMath-1.5 overlap; keep rows with a passing `correctness` flag. Same decision as `sft-math-openr1-math` (the 220k set), which carries the same NuminaMath-1.5 note.
- **Our opinion:** use, check. The R1 traces are clean, but the questions come from NuminaMath-1.5, which is `excluded` above because of its GPT-4-Turbo and untraceable sources. TSAI should rule whether R1 traces over those questions are permitted, or whether only the filtered `sft-math-openr1-math` set is kept.
- **Added by:** SomaKorada07 (Week 2 rotation, 4 Nov 2026; updated 5 Nov after review). Hugging Face cards read on 3 Nov 2026.

### `sft-chat-puffin` — Puffin

- **Stage:** SFT
- **Set:** `sft-chat-puffin`
- **Language:** English / Chat
- **Source:** [`LDJnr/Puffin`](https://huggingface.co/datasets/LDJnr/Puffin)
- **Licence:** `apache-2.0` — Hugging Face tag read on 3 Nov 2026. A tag is not legal clearance. The card is marked deprecated in favour of Pure-Dove.
- **Generator model:** GPT-4 (OpenAI, proprietary closed) writes every response in 3,000 multi-turn conversations with real humans.
- **Decision:** `excluded` — TSAI Week 2 rule: text made by closed OpenAI models is out.
- **Our opinion:** excluded for the same reason as `sft-code-magicoder-oss`. The Apache-2.0 tag does not remove the OpenAI terms on GPT-4 output.
- **Added by:** SomaKorada07 (Week 2 rotation, 4 Nov 2026). Hugging Face cards read on 3 Nov 2026.

### `sft-code-swe-fixer` — SWE-Fixer-Train-110K

- **Stage:** SFT
- **Set:** `sft-code-swe-fixer`
- **Language:** English issue text / Code (Python SWE: issue to patch)
- **Source:** [`internlm/SWE-Fixer-Train-110K`](https://huggingface.co/datasets/internlm/SWE-Fixer-Train-110K)
- **Licence:** `mit` — Hugging Face tag; the card gives no further licence text. Issues, pull requests and code come from Python GitHub repositories with more than 100 pull requests (raw crawl: 2.3K repositories and 331K instances, arXiv 2501.05040v3, Appendix A), which keep their own licences; the paper does not filter repositories by licence.
- **Generator model:** none. Each row is a real GitHub issue with its hints, the merged PR patch and the test patch (115,406 rows). The paper trained its editor model on chain-of-thought that GPT-4o wrote for a 70K subset; that chain-of-thought is not in this release and must not be added from another source.
- **Decision:** `TSAI reserves` — passes the 3 Nov TSAI generator rule: human-written, with no model generator.
- **Our opinion:** use, check. Open point for TSAI: the upstream repository licences are mixed and not listed per row (the same question as the GPL/LGPL files flagged for code-python). Appendix A of arXiv 2501.05040v3 says repositories within SWE-Bench were excluded from the raw crawl; send it to Team 9 for the decontamination test against the other SWE benchmarks we report. Other SWE sets in this table reuse SWE-Fixer-Train prompts, so de-duplicate by `instance_id`.
- **Added by:** Sagar063 (Week 2 rotation, 4 Nov 2026). Hugging Face card and paper read on 4 Nov 2026. A tag is not legal clearance.

### `sft-code-afm-codeagent` — AFM-CodeAgent-SFT-Dataset

- **Stage:** SFT
- **Set:** `sft-code-afm-codeagent`
- **Language:** English / Code and math (multi-agent tool-use trajectories)
- **Source:** [`PersonalAILab/AFM-CodeAgent-SFT-Dataset`](https://huggingface.co/datasets/PersonalAILab/AFM-CodeAgent-SFT-Dataset)
- **Licence:** `apache-2.0` — Hugging Face tag.
- **Generator model:** Unknown. The trajectories are distilled from the OAgents multi-agent framework (arXiv 2508.13167, section 3.2.1). Neither the card nor the paper names the LLM that ran OAgents for the code-agent trajectories; the paper names no backbone for OAgents and only groups it with GPT-4.1-based systems (Section 4.1.2).
- **Decision:** `excluded` — the generator model is not stated.
- **Our opinion:** The set also contains LiveCodeBench v1–v3 problems (443 of 59,929 trajectories) next to CodeForces, ReTool-SFT and Skywork-OR1 problems. Reconsider only if OPPO names an open-weight backbone; the LiveCodeBench part would still go to Team 9 first.
- **Added by:** Sagar063 (Week 2 rotation, 4 Nov 2026). Hugging Face card and paper read on 4 Nov 2026. A tag is not legal clearance.

### `sft-code-swe-hero-openhands` — SWE-Hero OpenHands trajectories

- **Stage:** SFT
- **Set:** `sft-code-swe-hero-openhands`
- **Language:** English / Code (Python SWE agent trajectories, OpenHands scaffold)
- **Source:** [`nvidia/SWE-Hero-openhands-trajectories`](https://huggingface.co/datasets/nvidia/SWE-Hero-openhands-trajectories)
- **Licence:** `cc-by-4.0` — Hugging Face tag and card. The card limits repositories to MIT, Apache-2.0, BSD-2-Clause and BSD-3-Clause and gives each row's repository licence in a `license` column. Attribution is needed.
- **Generator model:** Qwen3-Coder-480B-A35B-Instruct (Apache-2.0, open weights) writes all trajectories. For the R2E-Gym-Subset tasks it also writes new issue statements that replace the original untraced ones. The SWE-Gym and SWE-rebench issue statements are real GitHub issues. The card names no other model.
- **Decision:** `TSAI reserves` — passes the 3 Nov TSAI generator rule: the only generator named on the card is an open-weight Apache-2.0 model, as in `sft-code-nemotron-opencode`.
- **Our opinion:** use, check. 34,269 trajectories over 11,766 issues. For SFT, the regenerated R2E-Gym-Subset issue text makes these trajectories usable. It does not make the R2E-Gym-Subset tasks usable for RL: their tests are the originals, some written by an unnamed LLM. SWE-rebench issues may repeat in other SWE trajectory sets in this table, so de-duplicate by `instance_id`. The Team 9 decontamination test is still needed.
- **Added by:** Sagar063 (Week 2 rotation, 4 Nov 2026). Hugging Face card read on 4 Nov 2026. A tag is not legal clearance.

### `sft-code-opencodeinstruct` — OpenCodeInstruct

- **Stage:** SFT
- **Set:** `sft-code-opencodeinstruct`
- **Language:** Code (Python)
- **Source:** [`nvidia/OpenCodeInstruct`](https://huggingface.co/datasets/nvidia/OpenCodeInstruct)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 10 Nov 2026. The card says "This dataset is licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0)" and "This dataset is ready for commercial/non-commercial use." Permissive with attribution: in under the data licence rule. Attribution must go in the model card. A tag is not legal clearance.
- **Generator model:** Not named on the card ("Hybrid: Automated, Synthetic"). The paper (arXiv 2504.04030) names them: Qwen2.5-32B-Instruct (Apache-2.0, open weights) writes the coding tasks, and Qwen2.5-Coder-32B-Instruct (Apache-2.0, open weights) writes the solution, ten assertion-style unit tests per question-solution pair, and a quality score. Qwen2.5-32B-Instruct and QwQ-32B-Preview appear only in an ablation. Seeds: 25,443 TACO problems (BAAI/TACO, Apache-2.0; problems scraped from Codeforces, LeetCode, AtCoder, CodeChef and other sites) for the Genetic-Instruct part, and Python functions with docstrings collected from GitHub for the OSS-Instruct part (the seed code is not in the release and its licences are not recorded; only the generated instruction is kept from that step). Each row records `generation_algorithm` and `domain`, so the two parts can be separated.
- **Decision:** `TSAI reserves` — the generators are Apache-2.0 open-weight models and the licence is permissive, so it passes the data licence rule. Open points for TSAI: the card itself names no model (the generator is known only from the paper; R2E-Gym-Subset was `excluded` on that ground), and the OSS-Instruct rows descend from GitHub seed code we cannot trace, so TSAI may want to keep only the `generation_algorithm` = Genetic-Instruct rows (TACO seeds).
- **Our opinion:** use, check. 5,000,000 rows, created January to March 2025 and released 28 April 2025. Every row carries `unit_tests`, `tests_execution_status`, `average_test_score` and `llm_judgement`, but the paper says execution was not used to drop rows, so keep only rows that pass all tests and have a top quality score (the paper's own ablation found the quality-score filter best). Problem statements derive from TACO, which overlaps APPS and CodeContests, so send it to G9 (Evaluation) for the decontamination test against HumanEval+, MBPP+ and LiveCodeBench before use. De-duplicate against `sft-code-opencodereasoning` and `sft-stem-code-acereason-1.1-sft`, which also use TACO problems.
- **Added by:** swatibansal (Week 2 rotation, 11 Nov 2026). Hugging Face cards, papers and repository code read on 10-11 Nov 2026. A tag is not legal clearance.

### `sft-stem-code-acereason-1.1-sft` — AceReason-1.1-SFT, traceable-prompt subsets

- **Stage:** SFT
- **Set:** `sft-stem-code-acereason-1.1-sft`
- **Language:** English / Mathematics and Code (Python)
- **Source:** [`nvidia/AceReason-1.1-SFT`](https://huggingface.co/datasets/nvidia/AceReason-1.1-SFT), rows whose `source` column is OpenMathReasoning (2,147,570), OpenCodeReasoning (763,495), TACO (56,694) or apps (3,736): 2,971,495 rows
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 10 Nov 2026. The card says "This dataset is licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0)". Permissive with attribution: in under the data licence rule. Attribution must go in the model card. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1 (MIT, open weights) writes every response ("all responses in the dataset generated by DeepSeek-R1", arXiv 2506.13284, released 16 June 2025). The prompts in these four subsets are human competition problems (TACO, apps) or come from `sft-rl-math-openmathreasoning` and `sft-code-opencodereasoning`, both `TSAI reserves` above. NVIDIA removed rows with a 9-gram overlap with its own math and code benchmarks.
- **Decision:** `TSAI reserves` — MIT writer, permissive licence, traceable prompts.
- **Our opinion:** use. The kept rows share prompts with `sft-rl-math-openmathreasoning` and `sft-code-opencodereasoning` (same questions, different R1 samples), so de-duplicate by prompt before mixing. NVIDIA's 9-gram check does not cover our fingerprints v2 list, so G9 runs the decontamination test. The split by `source` follows the `sft-indic-aya-collection` pattern; the other four subsets are `sft-stem-code-acereason-1.1-sft-other` below.
- **Added by:** swatibansal (Week 2 rotation, 11 Nov 2026). Hugging Face cards, papers and repository code read on 10-11 Nov 2026. A tag is not legal clearance.

### `sft-stem-code-acereason-1.1-sft-other` — AceReason-1.1-SFT, closed-model or untraceable-prompt subsets

- **Stage:** SFT
- **Set:** `sft-stem-code-acereason-1.1-sft-other`
- **Language:** English / Mathematics and Code (Python)
- **Source:** [`nvidia/AceReason-1.1-SFT`](https://huggingface.co/datasets/nvidia/AceReason-1.1-SFT), rows whose `source` column is NuminaMath-CoT (521,171), MagicoderEvolInstruct (27,625), opc-sft-stage2 (323,163) or leetcode (126,878): 998,837 rows
- **Licence:** `cc-by-4.0` on the release (Hub tag read on 10 Nov 2026), but the prompts carry their upstream terms: NuminaMath-CoT and Magicoder Evol-Instruct contain GPT-4 / GPT-4o text (both `excluded` above); the OpenCoder opc-sft-stage2 card (MIT) names no generator and its `evol_instruct` part is Magicoder Evol-Instruct again; the leetcode prompts are LeetCode problem text with no stated licence.
- **Generator model:** DeepSeek-R1 (MIT, open weights) writes the responses, but the prompts were written or rewritten by closed OpenAI models (NuminaMath-CoT, Magicoder) or by a model the card does not name (opc-sft-stage2).
- **Decision:** `excluded` — data licence rule: text made by closed OpenAI models is out; sources we cannot trace are out; unstated licences are out. The same problems would otherwise re-enter through these prompts after being excluded upstream.
- **Our opinion:** excluded. If TSAI later clears LeetCode problem text (the open question on `rl-code-leetcodedataset`), the 126,878 leetcode rows can move to the kept set; the other three subsets cannot.
- **Added by:** swatibansal (Week 2 rotation, 11 Nov 2026). Hugging Face cards, papers and repository code read on 10-11 Nov 2026. A tag is not legal clearance.

### `sft-chat-dolci-think-sft` — Dolci-Think-SFT, traceable subsets

- **Stage:** SFT
- **Set:** `sft-chat-dolci-think-sft`
- **Language:** English / Math, Code, Chat; some multilingual rows via Aya
- **Source:** [`allenai/Dolci-Think-SFT`](https://huggingface.co/datasets/allenai/Dolci-Think-SFT), rows whose `source` column is OpenThoughts3 (941,164), WildChat (76,209), OpenAssistant Guanaco (6,647) or Aya (97,156): 1,121,176 rows of 2,253,684
- **Licence:** `odc-by` — Hugging Face tag read on 10 Nov 2026. The card says "This dataset is licensed under ODC-BY." and adds "It is intended for research and educational use in accordance with Ai2's Responsible Use Guidelines." ODC-By is permissive with attribution, so it is in under the data licence rule; the second sentence is a statement of intent, not a licence term, and is recorded here for TSAI. Upstream prompt licences: OpenThoughts3 Apache-2.0, WildChat-1M ODC-By, OASST1 Apache-2.0, aya_dataset Apache-2.0. Attribution must go in the model card. A tag is not legal clearance.
- **Generator model:** New traces by "a mix of DeepSeek R1 and DeepSeek R1 0528" (MIT, open weights) over the WildChat, Guanaco and Aya prompts, which are human-written (WildChat prompts are real user messages; OASST1 and Aya are human annotations). The OpenThoughts3 rows reuse the existing QwQ-32B (Apache-2.0) traces from `sft-stem-code-openthoughts3`, extended to 32k context with code prompts downsampled.
- **Decision:** `TSAI reserves` — permissive licence, MIT or Apache-2.0 writers, human or already-accepted prompts.
- **Our opinion:** use, check. The OpenThoughts3 rows duplicate `sft-stem-code-openthoughts3`, so take them from one place only. The card describes no decontamination, so G9 runs the test. The Aya rows are a cheap Indic supplement; check script integrity with the G10 text-prep rule first. The split by `source` follows the `sft-indic-aya-collection` pattern; everything else is `sft-chat-dolci-think-sft-other` below.
- **Added by:** swatibansal (Week 2 rotation, 11 Nov 2026). Hugging Face cards, papers and repository code read on 10-11 Nov 2026. A tag is not legal clearance.

### `sft-chat-dolci-think-sft-other` — Dolci-Think-SFT, untraceable or closed-model subsets

- **Stage:** SFT
- **Set:** `sft-chat-dolci-think-sft-other`
- **Language:** English / Instruction following, Python, Safety, Tables
- **Source:** [`allenai/Dolci-Think-SFT`](https://huggingface.co/datasets/allenai/Dolci-Think-SFT), all other `source` values: Dolci Think Python (466,676), Dolci Think Persona IF (220,530), Dolci Precise IF (135,722), Nemotron-Post-Training-Dataset-v1 code (113,777), SYNTHETIC-2 SFT-verified (104,568), WildJailbreak (40,002), WildGuardMix (36,673), CoCoNot (9,549), TableGPT (4,973), Olmo identity prompts (58): about 1,132,500 rows
- **Licence:** `odc-by` on the release (Hub tag read on 10 Nov 2026), but the parts carry their own terms. SYNTHETIC-2 SFT-verified has no licence field on the PrimeIntellect card (Ai2 lists it as Apache 2.0; the primary source states none). The Dolci-Think-SFT-Python card is ODC-By but names no generator.
- **Generator model:** Not stated for the three new Ai2 subsets (Think Python, Think Persona IF, Precise IF; 822,928 rows), on either the Dolci-Think-SFT card or the Dolci-Think-SFT-Python card. SYNTHETIC-2 traces are DeepSeek-R1-0528 (MIT) but its task sources are not stated. The Nemotron-v1 code rows belong to `sft-stem-code-nemotron-post-v1`, `excluded` above. WildGuardMix and WildJailbreak prompts were written by GPT-4 (OpenAI, closed; both `excluded` above). CoCoNot prompts were expanded "by iteratively prompting different LMs" that the paper (arXiv 2407.12043) does not name, and its responses are GPT-4. TableGPT (LipengCS/Table-GPT, MIT) is partly synthesised and the card does not say how. The Dolci traces over these prompts are DeepSeek R1 / R1-0528.
- **Decision:** `excluded` — data licence rule: sources we cannot trace are out (unnamed generators, unstated task sources), unstated licences are out (SYNTHETIC-2), and text made by closed OpenAI models is out (WildGuardMix, WildJailbreak, CoCoNot prompts).
- **Our opinion:** excluded. The three new Ai2 subsets (about 823k rows) are the largest loss; if Ai2 documents their generator and it is an open MIT or Apache-2.0 model, they can move to the kept set. Nothing else here can.
- **Added by:** swatibansal (Week 2 rotation, 11 Nov 2026). Hugging Face cards, papers and repository code read on 10-11 Nov 2026. A tag is not legal clearance.

### `sft-agentic-apigen-mt-5k` — APIGen-MT-5k

- **Stage:** SFT
- **Set:** `sft-agentic-apigen-mt-5k`
- **Language:** English / Tool use (multi-turn function calling; retail and airline domains from tau-bench)
- **Source:** [`Salesforce/APIGen-MT-5k`](https://huggingface.co/datasets/Salesforce/APIGen-MT-5k)
- **Licence:** `cc-by-nc-4.0` — Hugging Face tag read on 10 Nov 2026 (gated: "Acknowledge to follow the corresponding license and cite APIGen-MT to access the repository"). Non-commercial. The card adds "This release is for research purposes only in support of an academic paper." and "A part of this dataset was generated using GPT-4 and should not be used to develop models that compete with OpenAI."
- **Generator model:** GPT-4o (OpenAI, proprietary closed) and DeepSeek-V3 (MIT, open weights) write the agent and simulated-user turns (arXiv 2504.03601; the card does not say which model played which role). 5,000 dialogues, verified by format checks, function execution with policy checks and a semantic check; a human review of 200 samples passed 99%.
- **Decision:** `excluded` — data licence rule: non-commercial licences are out, and text made by closed OpenAI models is out. The research-only clause is a third reason.
- **Our opinion:** excluded. It is the closest public match to our `<|tool_call|>` multi-turn format, so it is worth recording why it is out. Salesforce's `sft-salesforce-xlam-60k` (single-turn, CC-BY-4.0, Mixtral and DeepSeek-V2 writers) stays the tool-use source. Do not substitute the xLAM-2 models trained on this set either; they carry the same CC-BY-NC terms.
- **Added by:** swatibansal (Week 2 rotation, 11 Nov 2026). Hugging Face cards, papers and repository code read on 10-11 Nov 2026. A tag is not legal clearance.

### `sft-code-swe-smith` — SWE-smith

- **Stage:** SFT
- **Set:** `sft-code-swe-smith`
- **Source:** [`SWE-bench/SWE-smith`](https://huggingface.co/datasets/SWE-bench/SWE-smith)
- **Licence:** `mit` (Hub tag).
- **Generator model:** o3-mini (OpenAI, proprietary closed) is the main model that writes the bugs, per the SWE-smith paper (other bugs are procedural or taken from PRs).
- **Decision:** `excluded` — data rule: text made by closed OpenAI models is out. The MIT tag does not change that.
- **Our opinion:** Out. The task instances are useful as a reference for building our own SWE environments, not as training text.
- **Added by:** RaviNaik (12 Nov 2026), from the Hub cards and papers. A tag is not legal clearance.

### `sft-agentic-swe-smith-trajectories` — SWE-smith-trajectories

- **Stage:** SFT
- **Set:** `sft-agentic-swe-smith-trajectories`
- **Source:** [`SWE-bench/SWE-smith-trajectories`](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories)
- **Licence:** `mit` (Hub tag).
- **Generator model:** SWE-agent with Claude 3.7 Sonnet (Anthropic, proprietary closed) produced most trajectories, per the card.
- **Decision:** `excluded` — data rule: text made by closed Anthropic models is out.
- **Our opinion:** Out. Open-weight agent trajectories (for example `sft-code-swe-rebench-openhands`) stay the agentic source.
- **Added by:** RaviNaik (12 Nov 2026), from the Hub cards and papers. A tag is not legal clearance.

### `sft-reasoning-r1-distill-sft` — R1-Distill-SFT

- **Stage:** SFT
- **Set:** `sft-reasoning-r1-distill-sft`
- **Source:** [`ServiceNow-AI/R1-Distill-SFT`](https://huggingface.co/datasets/ServiceNow-AI/R1-Distill-SFT)
- **Licence:** `cc-by-nc-sa-4.0` (Hub tag). Non-commercial.
- **Generator model:** Distilled with DeepSeek-R1-32b (card); prompts from Numina-math and Tulu.
- **Decision:** `excluded` — data rule: non-commercial licences are out.
- **Our opinion:** Out. The generator is not the problem; the licence is.
- **Added by:** RaviNaik (12 Nov 2026), from the Hub cards and papers. A tag is not legal clearance.

### `sft-agentic-open-agentrl-sft-3k` — Open-AgentRL-SFT-3K

- **Stage:** SFT
- **Set:** `sft-agentic-open-agentrl-sft-3k`
- **Source:** [`Gen-Verse/Open-AgentRL-SFT-3K`](https://huggingface.co/datasets/Gen-Verse/Open-AgentRL-SFT-3K)
- **Licence:** None stated on the Hub card or in the paper.
- **Generator model:** The paper names Qwen3-Coder-30B-A3B (Apache-2.0) as the teacher for the self-curated trajectories. The card also lists `s1K-1.1` and `ReTool-SFT` as problem sources; their generators are not traced here.
- **Decision:** `excluded` — data rule: a set with no stated licence is out. It stays out until the authors state one.
- **Our opinion:** If the authors add a licence, ask TSAI to review it again. The set is small (about 3K rows).
- **Added by:** RaviNaik (12 Nov 2026), from the Hub cards and papers. A tag is not legal clearance.

### `sft-agentic-toucan` — Toucan-1.5M

- **Stage:** SFT
- **Set:** `sft-agentic-toucan`
- **Language:** English / Tool use (multi-turn MCP agent trajectories, Hermes tool format)
- **Source:** [`Agent-Ark/Toucan-1.5M`](https://huggingface.co/datasets/Agent-Ark/Toucan-1.5M) (card revision `0df3cf37f2`); paper [arXiv 2510.01179](https://arxiv.org/abs/2510.01179)
- **Licence:** `apache-2.0` — Hugging Face tag read on 8 Nov 2026 and unchanged on 12 Nov 2026; the card: "This dataset is released under Apache 2.0." Permissive: in under the data licence rule. A tag is not legal clearance.
- **Generator model:** Trajectories: "trajectories generated by Qwen3-32B, Kimi-K2, and GPT-OSS-120B, each stored under separate configurations" (card). Tasks: "five open-source LLMs (Mistral-Small, DevStral-Small, GPT-OSS, Kimi-K2, and Qwen3-32B) as task generators" (paper); quality annotation: "the Kimi-K2 model as the annotator" (paper); trajectory judge: GPT-OSS-120B (paper). GPT-OSS and Qwen3 are Apache-2.0 open weights. Kimi-K2 is open weights under a Modified MIT licence ([`moonshotai/Kimi-K2-Instruct` LICENSE](https://huggingface.co/moonshotai/Kimi-K2-Instruct/blob/main/LICENSE), revision `fd1984e2b7`, read on 12 Nov 2026): MIT, plus a product with more than 100 million monthly active users or more than 20 million US dollars monthly revenue must display "Kimi K2" in its user interface. The paper does not give versions for Mistral-Small and DevStral-Small, so their licences are not verified here. GPT-4o appears in the paper only as the user simulator for tau-bench evaluation, not in the data.
- **Decision:** `TSAI reserves` — permissive licence; the trajectory writers are gpt-oss (in by name under the data licence rule) and the open-weight Qwen3-32B and Kimi-K2. Open points for TSAI: whether Kimi-K2's Modified MIT attribution term is acceptable (if not, keep only the `OSS` and `Qwen3` configs), and the unstated Mistral-Small / DevStral-Small versions used for task generation.
- **Our opinion:** use, starting from the `OSS` config (457,130 rows, GPT-OSS-120B trajectories), which matches the "gpt-oss data is in" rule word for word; `Qwen3` (551,613) and `Kimi-K2` (518,516) are also open-weight. The `SFT` config (119,287 rows) is the authors' curated mix; check which generators it holds before using it. Messages are in the Hermes tool format, so `sft/convert.py` needs an adapter to the `<|tool_call|>` format. The tool definitions come from public MCP servers; tool results may contain scraped web text.
- **For Team 9:** decontaminate against tool-use benchmarks (BFCL, tau-bench) before use.
- **Added by:** jssunil (Week 2 rotation, 8 Nov 2026). Card and paper read on 8 Nov 2026; card revision re-checked and Kimi-K2 licence read on 12 Nov 2026.

### `sft-tool-when2call` — When2Call

- **Stage:** SFT (`train_sft`, 15,000 rows); `train_pref` (9,000 chosen/rejected pairs) is preference data for Stage 2
- **Set:** `sft-tool-when2call`
- **Language:** English / Tool use: when to call a tool, ask a follow-up question, or say the tools cannot answer
- **Source:** [`nvidia/When2Call`](https://huggingface.co/datasets/nvidia/When2Call) (card revision `0582f7749d`); paper [NAACL 2025](https://aclanthology.org/2025.naacl-long.174/)
- **Licence:** `cc-by-4.0` — Hugging Face tag and card text read on 8 Nov 2026 and unchanged on 12 Nov 2026. Permissive with attribution: in under the data licence rule. Attribution must go in the model card. A tag is not legal clearance.
- **Generator model:** Mixtral-8x22B (Apache-2.0, open weights): "We synthetically generate the new data for When2Call in two main steps, using Mixtral 8x22B" (paper §2.2). The training data comes from applying that pipeline "to the APIGen dataset" (§3.3.1), i.e. `Salesforce/xlam-function-calling-60k`, which this table records as Mixtral-8x22B-Instruct plus DeepSeek-V2-Chat (DeepSeek Licence). The released rows have only `tools` and `messages`, so the DeepSeek-made rows cannot be filtered out.
- **Decision:** `needs TSAI decision` — `sft-salesforce-xlam-60k` is `TSAI reserves` with the note "keep only Mixtral-8x22B-Instruct Apache-2.0 rows if split by generator". When2Call cannot be split that way, so TSAI should rule whether its unsplit rows (some built on DeepSeek-V2-Chat output) are acceptable. If yes, use; if not, excluded.
- **Our opinion:** use if TSAI accepts the unsplit rows. It is the only set found that trains the "when not to call" behaviour the mix proposal (§3, Tool Use) asks for. The tool specs use a different schema (`"type": "dict"`, Python type names), so `convert.py` needs an adapter.
- **For Team 9:** the test split (3,952 rows) is built from BFCL v2 Live, a benchmark. Use `train_sft` and `train_pref` only, and check them against BFCL.
- **Added by:** jssunil (Week 2 rotation, 8 Nov 2026). Card and paper read on 8 Nov 2026; card revision re-checked on 12 Nov 2026.

### `sft-indic-indic-instruct-hi` — indic-instruct-data-v0.1, `wikihow` and `nmt-seed` (Hindi)

- **Stage:** SFT
- **Set:** `sft-indic-indic-instruct-hi`
- **Language:** Hindi. This set is the `hi` split of two subsets: `wikihow` (6,055 rows) and `nmt-seed` (50,000 rows).
- **Source:** [`ai4bharat/indic-instruct-data-v0.1`](https://huggingface.co/datasets/ai4bharat/indic-instruct-data-v0.1) (card revision `82cd1437a0`); the Airavata report [arXiv 2401.15006](https://arxiv.org/abs/2401.15006)
- **Licence:** The Hub card has no licence tag (still none on 12 Nov 2026); it points to the report. The report gives per-subset licences: `wikihow` "released under the CC-0 license"; `nmt-seed` (BPCC-Human) "released under the CC-BY-4.0 license". Read on 8 Nov 2026. Both are permissive, but the data licence rule puts unstated licences out, and here the licence is stated only in the report, not on the dataset card.
- **Generator model:** None. `wikihow`: native Hindi wikiHow articles, "human-moderated", turned into completion tasks by the authors. `nmt-seed`: "A multi-domain human-annotated dataset containing 50K bitext English-Hindi translation pairs from BPCC-Human."
- **Decision:** `TSAI reserves` — human-written text, no generator model, permissive licences per the report. Open point for TSAI: whether a licence stated in the authors' report, with no tag on the card, counts as stated under the data licence rule.
- **Other subsets (not in this set):** `anudesh` — responses by Llama 2 70B: excluded (Llama). `lm_sys` — LMSYS-Chat-1M responses from 25 models including closed ones, LMSYS licence: excluded. `hh-rlhf` — Anthropic model responses: excluded, as `rl-safety-hh-rlhf`. `dolly` and `oasst1` — IndicTrans2 translations of the same sources as `sft-indic-indic-align-dolly-t` and `sft-indic-indic-align-oasst-t`: not added, to avoid training the same conversations twice. `flan_v2` — the report gives Apache-2.0, but FLAN mixes many source datasets with their own licences: not checked.
- **Our opinion:** use `wikihow`; it is native Hindi, not translated, and five times the Hindi rows of `sft-indic-aya-dataset` (1,153). `nmt-seed` is translation pairs, not chat: use a small, capped share if TSAI wants translation ability. Both are single-turn, effort `1k`.
- **Added by:** jssunil (Week 2 rotation, 8 Nov 2026). Card and report read on 8 Nov 2026; card revision re-checked on 12 Nov 2026.

### `sft-indic-updesh` — Updesh_beta

- **Stage:** SFT
- **Set:** `sft-indic-updesh`
- **Language:** 13 Indic languages (Assamese, Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Nepali, Odia, Punjabi, Tamil, Telugu, Urdu) and English
- **Source:** [`microsoft/Updesh_beta`](https://huggingface.co/datasets/microsoft/Updesh_beta) (card revision `73ed1f8e08`)
- **Licence:** `other` — [Microsoft Research License](https://huggingface.co/datasets/microsoft/Updesh_beta/blob/main/LICENSE.md), read on 8 Nov 2026: "use the Materials solely for non-commercial, non-revenue generating, research purposes" and "you may not distribute the data or your modifications to the data".
- **Generator model:** Updesh-G (generative part): Qwen3-235B-A22B (card). The card also names two Llama models: Llama-3.1-405B-Instruct for the translation of the reasoning data, and Llama 3.3 70B to translate outputs back to English for the translation-quality check (card, "Translation Quality Assessment"; the back-translations are compared with the source, so as far as the card says that model does not write the released text). The reasoning part (Updesh-R) is selectively translated from Microsoft's Orca-AgentInstruct and OrcaMath sets.
- **Decision:** `excluded` — data licence rule: non-commercial licences are out. Text made by Llama models is also out, which would exclude the Llama-3.1-405B stage on its own.
- **Our opinion:** excluded on the licence alone. Recorded because it is a large Indic set with Odia, and it will be proposed again.
- **Added by:** jssunil (Week 2 rotation, 8 Nov 2026). Card and LICENSE.md read on 8 Nov 2026; card revision re-checked on 12 Nov 2026.

### `sft-tool-xlam-irrelevance-7.5k` — xlam-irrelevance-7.5k (Hammer)

- **Stage:** SFT
- **Set:** `sft-tool-xlam-irrelevance-7.5k`
- **Language:** English / Tool use (irrelevance detection: the tool list does not contain the right function, and the correct answer is no call). 7,500 rows with `query`, `tools` and `answers`.
- **Source:** [`MadeAgents/xlam-irrelevance-7.5k`](https://huggingface.co/datasets/MadeAgents/xlam-irrelevance-7.5k) (card revision `34323bf09e`); paper [arXiv 2410.04587](https://arxiv.org/abs/2410.04587). The rotation list named "MadeAgents/Hammer", which is the model family, not a dataset; this is the training set the paper releases for Hammer. MadeAgents' other dataset, HammerBench, is `rl-tool-hammerbench` in Stage 2.
- **Licence:** `cc-by-4.0` — Hugging Face tag and card front matter, read on 13 Nov 2026. Attribution needed.
- **Generator model:** none new. The paper (§4.2) and card say the rows are "7,500 examples sampled from the original training set, in which the correct functions are deliberately excluded from the candidate list, and the labels are replaced with empty lists". The original set is `Salesforce/xlam-function-calling-60k` (`sft-salesforce-xlam-60k`), so each query and tool list keeps its xlam-60k origin: Mixtral-8x22B-Instruct (Apache-2.0) or DeepSeek-V2-Chat (DeepSeek Licence). The answers (`[]`) are written by a program.
- **Decision:** `needs TSAI decision` — permissive licence, and no model text is added on top of `sft-salesforce-xlam-60k`. But the queries keep xlam-60k's DeepSeek-V2-Chat rows (DeepSeek Licence), and the rows carry no generator field, so they cannot be split by generator. That is the same question as `sft-tool-when2call`. Question for TSAI: are the DeepSeek-V2-Chat-written xlam-60k queries allowed? If yes, this set follows `sft-salesforce-xlam-60k` (`TSAI reserves`); if no, it is out with them.
- **Our opinion:** if TSAI allows it, use together with `sft-salesforce-xlam-60k` if that set is used. The paper finds that about 10% irrelevance rows give the best balance between calling a tool and declining. It adds the "do not call" case that xlam-60k lacks, alongside `sft-tool-when2call`. The queries are copies of xlam-60k queries, so do not count them as new prompts in the mix.
- **For Team 9:** decontaminate against BFCL irrelevance and live-irrelevance; the paper reports BFCL v2 scores.
- **Added by:** chapanduk (Week 2 rotation, 13 Nov 2026). Card and paper read on 13 Nov 2026. A tag is not legal clearance.

### `sft-reasoning-synthetic-1` — SYNTHETIC-1

- **Stage:** SFT
- **Set:** `sft-reasoning-synthetic-1`
- **Language:** English / Reasoning across code, math and STEM
- **Source:** [`PrimeIntellect/SYNTHETIC-1`](https://huggingface.co/datasets/PrimeIntellect/SYNTHETIC-1) (card revision `f08fe8ccdb5b`)
- **Licence:** `apache-2.0` — Hugging Face tag and card, read on 13 Nov 2026.
- **Generator model:** DeepSeek-R1 (MIT). The card title is "Two Million Crowdsourced Reasoning Traces from Deepseek-R1". It also says verifiers include unnamed LLM judges. Those judges are not described as rewriting the trace.
- **Decision:** `TSAI reserves`
- **Our opinion:** use. The trace writer is DeepSeek-R1, which the 3 Nov rule names as in.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Shankar Pandala's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-reasoning-openthoughts-114k` — OpenThoughts-114k

- **Stage:** SFT
- **Set:** `sft-reasoning-openthoughts-114k`
- **Language:** English / Math and code
- **Source:** [`open-thoughts/OpenThoughts-114k`](https://huggingface.co/datasets/open-thoughts/OpenThoughts-114k) (card revision `bd093c3994fd`)
- **Licence:** `apache-2.0` — Hugging Face tag and card, read on 13 Nov 2026.
- **Generator model:** DeepSeek-R1 (MIT). The card says the traces are generated from DeepSeek-R1 and verified. Columns are `deepseek_reasoning` and `deepseek_solution`.
- **Decision:** `TSAI reserves`
- **Our opinion:** use. This is the earlier OpenThoughts release, separate from `sft-stem-code-openthoughts3`.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Srinivasan Govindaraj's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-reasoning-openthoughts2-1m` — OpenThoughts2-1M

- **Stage:** SFT
- **Set:** `sft-reasoning-openthoughts2-1m`
- **Language:** English / Reasoning
- **Source:** [`open-thoughts/OpenThoughts2-1M`](https://huggingface.co/datasets/open-thoughts/OpenThoughts2-1M) (card revision `94d0ccf8474a`)
- **Licence:** `apache-2.0` — Hugging Face tag, read on 13 Nov 2026.
- **Generator model:** not named for each part. The card says it builds on OpenThoughts-114k and adds community datasets (GeneralThought, OpenR1-Math, Nemotron, Synthetic-1, KodCode). It does not say which model wrote each added part.
- **Decision:** `excluded` — a set whose generator is not named for each part is out. `sft-reasoning-openthoughts-114k` and `sft-reasoning-synthetic-1` stay in on their own rows.
- **Our opinion:** do not train on this mix as released.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Shankar Pandala's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-reasoning-sky-t1` — Sky-T1 17k

- **Stage:** SFT
- **Set:** `sft-reasoning-sky-t1`
- **Language:** English / Code and math
- **Source:** [`NovaSky-AI/Sky-T1_data_17k`](https://huggingface.co/datasets/NovaSky-AI/Sky-T1_data_17k) (card revision `3e260822dae5`)
- **Licence:** `apache-2.0` — Hugging Face tag, read on 13 Nov 2026.
- **Generator model:** not named. The card says 5k coding rows from APPS and TACO, 10k math rows from AIME, MATH and the Olympiad subsets of NuminaMATH, and 1k science rows from STILL-2. It does not name the model that wrote the traces. NuminaMATH is already `excluded` in this table.
- **Decision:** `excluded` — the trace writer is not named, and a named source is already out.
- **Our opinion:** do not train on it.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Shankar Pandala's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-reasoning-generalthought-430k` — GeneralThought-430K

- **Stage:** SFT
- **Set:** `sft-reasoning-generalthought-430k`
- **Language:** English / Reasoning
- **Source:** [`GeneralReasoning/GeneralThought-430K`](https://huggingface.co/datasets/GeneralReasoning/GeneralThought-430K) (card revision `dcfe389f5616`)
- **Licence:** `mit` — Hugging Face tag, read on 13 Nov 2026.
- **Generator model:** the card names DeepSeek-R1, DeepSeek-R1-Zero, OpenThoughts-32B, LIMO, deepseek-r1-distill-llama-70b, DeepHermes-3-Llama-3-8B-Preview and DeepScaleR-1.5B-Preview for traces, and o3-mini, Gemini 2 Flash and Claude 3.7 Sonnet for final answers. Each row has a `model_name`.
- **Decision:** `excluded` — the release mixes Llama models and closed models (OpenAI, Google, Anthropic). A later row could keep only `DeepSeek-R1` and `DeepSeek-R1-Zero` if someone filters on `model_name` and shows the filter.
- **Our opinion:** do not train on the release as published.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Srinivasan Govindaraj's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-tool-toolace` — ToolACE

- **Stage:** SFT
- **Set:** `sft-tool-toolace`
- **Language:** English and Chinese / Tool use
- **Source:** [`Team-ACE/ToolACE`](https://huggingface.co/datasets/Team-ACE/ToolACE) (card revision `6bda777c88d2`); paper [arXiv 2409.00920](https://arxiv.org/abs/2409.00920)
- **Licence:** `apache-2.0` — Hugging Face tag, read on 13 Nov 2026.
- **Generator model:** not named on the card. The card describes a multi-agent pipeline and does not name the models.
- **Decision:** `excluded` — the generator is not named on the card.
- **Our opinion:** out until the model names are written down.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Sreekanth Janapala's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-tool-hermes-function-calling-v1` — Hermes-Function-Calling-v1

- **Stage:** SFT
- **Set:** `sft-tool-hermes-function-calling-v1`
- **Language:** English / Tool use
- **Source:** [`NousResearch/Hermes-Function-Calling-v1`](https://huggingface.co/datasets/NousResearch/Hermes-Function-Calling-v1) (card revision `dae3e1d28cfb`)
- **Licence:** `apache-2.0` — Hugging Face tag, read on 13 Nov 2026.
- **Generator model:** not named. The card says the synthetic generation was led by named people and does not name a model.
- **Decision:** `excluded` — the generator model is not named.
- **Our opinion:** out until the model is named.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Sreekanth Janapala's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-tool-apigen-function-calling` — apigen-function-calling

- **Stage:** SFT
- **Set:** `sft-tool-apigen-function-calling`
- **Language:** English / Tool use
- **Source:** [`argilla/apigen-function-calling`](https://huggingface.co/datasets/argilla/apigen-function-calling) (card revision `170a8a7e0832`)
- **Licence:** `cc-by-4.0` — Hugging Face tag, read on 13 Nov 2026. Attribution needed.
- **Generator model:** the card says it merges `Salesforce/xlam-function-calling-60k` (`origin: xLAM`) with a distilabel part whose example row names `Qwen/Qwen2.5-72B-Instruct` (Apache-2.0). xlam-60k in this table includes DeepSeek-V2-Chat rows that cannot be split out.
- **Decision:** `needs TSAI decision` — the Qwen2.5-72B-Instruct part is an allowed generator, and the xlam part is the same open question as `sft-salesforce-xlam-60k` and `sft-tool-when2call`. The Llama-3.2 link on the card is a model trained on this set, not the writer of the rows.
- **Our opinion:** do not train on the merged file until TSAI says whether the xlam part stays.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Sreekanth Janapala's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-tool-hermes-reasoning-tool-use` — hermes_reasoning_tool_use

- **Stage:** SFT
- **Set:** `sft-tool-hermes-reasoning-tool-use`
- **Language:** English / Tool use
- **Source:** [`interstellarninja/hermes_reasoning_tool_use`](https://huggingface.co/datasets/interstellarninja/hermes_reasoning_tool_use) (card revision `c27e454925db`)
- **Licence:** `apache-2.0` — Hugging Face tag, read on 13 Nov 2026.
- **Generator model:** `NousResearch/DeepHermes-3-Llama-3-8B-Preview` writes the roll-outs. Seed rows come from other tool-calling sets, including When2Call and ToolACE.
- **Decision:** `excluded` — Llama output is out.
- **Our opinion:** out.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Sreekanth Janapala's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-agentic-afm-webagent-sft` — AFM-WebAgent-SFT

- **Stage:** SFT
- **Set:** `sft-agentic-afm-webagent-sft`
- **Language:** English / Web agent
- **Source:** [`PersonalAILab/AFM-WebAgent-SFT-Dataset`](https://huggingface.co/datasets/PersonalAILab/AFM-WebAgent-SFT-Dataset) (card revision `48bd667e60cf`); paper [arXiv 2508.13167](https://arxiv.org/abs/2508.13167)
- **Licence:** `apache-2.0` — Hugging Face tag, read on 13 Nov 2026.
- **Generator model:** not named. The card says the trajectories are distilled from multi-agent systems and that the web-agent data comes from TaskCraft. It does not name the models.
- **Decision:** `excluded` — the generator is not named.
- **Our opinion:** out until the models are named.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Srinivasan Govindaraj's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-tool-toolmind` — ToolMind

- **Stage:** SFT
- **Set:** `sft-tool-toolmind`
- **Language:** English / Tool use
- **Source:** [`Nanbeige/ToolMind`](https://huggingface.co/datasets/Nanbeige/ToolMind) (card revision `8020ed1c03c3`)
- **Licence:** `apache-2.0` — Hugging Face tag, read on 13 Nov 2026.
- **Generator model:** not named. The card says a multi-agent simulation writes the trajectories and that the file also includes `Salesforce/xlam-function-calling-60k` and `nvidia/When2Call`. It does not name the agents' models. GPT-4o, Gemini, DeepSeek and Qwen appear only as evaluated models.
- **Decision:** `excluded` — the generator is not named, and the file mixes in sets that this table does not take as a whole.
- **Our opinion:** out.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Srinivasan Govindaraj's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `sft-math-s1k-1.1` — s1K-1.1

- **Stage:** SFT
- **Set:** `sft-math-s1k-1.1`
- **Language:** English / Mathematics (1,000 questions)
- **Source:** [`simplescaling/s1K-1.1`](https://huggingface.co/datasets/simplescaling/s1K-1.1) (card revision `96c411f1fe4c49d20f0e2a1565f61e1a28b0b84d`); paper [arXiv 2501.19393](https://arxiv.org/abs/2501.19393)
- **Licence:** `mit` — Hugging Face tag read on 14 Nov 2026. A tag is not legal clearance. The MIT tag does not clear the Gemini traces or the upstream question text.
- **Generator model:** Two writers, both stored on every row. `gemini_thinking_trajectory` and `gemini_attempt` are written by Gemini Flash Thinking Experimental (Google, proprietary closed). The s1 paper (§2.1) generated the original traces with the Google Gemini Flash Thinking API. `deepseek_thinking_trajectory` and `deepseek_attempt` are written by DeepSeek-R1 (MIT, open weights). The [`deepseek-ai/DeepSeek-R1` LICENSE](https://huggingface.co/deepseek-ai/DeepSeek-R1/blob/56d4cbbb4d29/LICENSE) is the MIT licence, read on 14 Nov 2026. The card says these 1,000 questions are the same as s1K and that the R1 traces are the ones to train on, but the Gemini columns are still in the file. The `metadata` field embeds the upstream messages. The card's own example has `source_type` `AI-MO/NuminaMath-CoT/aops_forum`.
- **Decision:** `excluded` — data licence rule: text made by closed Google models is out. The Gemini columns are on every row. The questions come from the s1 pool (NuminaMATH, historical AIME, Omni-MATH, AGIEval, OlympicArena and others, arXiv 2501.19393 §2.1). That pool mixes `sft-math-numinamath-cot` (excluded above for GPT-4 / GPT-4o text) with benchmark problems, and this release has no split that drops those rows.
- **Our opinion:** excluded as released. DeepSeek-R1's own traces would pass the generator rule. They cannot be taken from this file without also taking the Gemini columns or the NuminaMath text in `metadata`. A later release that ships only the R1 traces, and whose `source_type` leaves out NuminaMath-CoT and the benchmark sources, can be checked again.
- **Added by:** SreekanthZipsy (Week 10 rotation 13 Nov 2026). Hugging Face card, DeepSeek-R1 licence and the s1 paper read on 14 Nov 2026. A tag is not legal clearance.

## Stage 2: Preference optimization and RLVR, candidate sets

Verifiable-answer and test-based sets for RL (math, code, SWE tasks). Each entry has the standard fields, `TSAI reserves` as the decision (`excluded` where TSAI ruled a set out), and one line of opinion. Licence values are the Hugging Face tags read on 29 Oct 2026; a tag is not legal clearance. Per-dataset notes, 20-row samples and a benchmark-overlap check are in [team10-datasets](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets).

### `rl-agentic-open-agentrl-30k` — Open-AgentRL-30K

- **Stage:** RL
- **Set:** `rl-agentic-open-agentrl-30k`
- **Source:** [`Gen-Verse/Open-AgentRL-30K`](https://huggingface.co/datasets/Gen-Verse/Open-AgentRL-30K)
- **Licence:** None stated on the card. The card lists 17K DAPO-Math prompts, 3K MegaScience science prompts (MegaScience's own card says `cc-by-nc-sa-4.0`), self-curated LeetCode data and data from Skywork-OR1.
- **Generator model:** none for the prompts (RL data); the card does not say who made the LeetCode and Skywork-OR1 parts.
- **Decision:** `excluded` — data rule: no stated licence, and the MegaScience part is non-commercial.
- **Our opinion:** Out as a whole. A part-by-part review would be needed to use only the DAPO-Math rows; not proposed.
- **Added by:** RaviNaik (12 Nov 2026), from the Hub cards and papers. A tag is not legal clearance.

### `rl-code-r2e-gym` — R2E-Gym-Subset

- **Stage:** RL
- **Set:** `rl-code-r2e-gym`
- **Language:** Code (Python SWE)
- **Source:** [`R2E-Gym/R2E-Gym-Subset`](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Subset)
- **Licence:** `apache-2.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Not named in the paper's main text (tests and issues are LLM-generated by back-translation from commits, arXiv 2504.07164); check its appendix
- **Decision:** `excluded` — TSAI Week 2 rule: sources we cannot trace are out. The issue text and some tests are written by an LLM that the card and paper do not name; this matches the Stage 2 table.
- **Our opinion:** excluded. Same reasoning as `rl-code-r2e-gym-v1`.
- **Details and 20-row sample:** [R2E-Gym__R2E-Gym-Subset](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/R2E-Gym__R2E-Gym-Subset)

### `rl-code-swe-gym` — SWE-Gym

- **Stage:** RL
- **Set:** `rl-code-swe-gym`
- **Language:** Code (Python SWE)
- **Source:** [`SWE-Gym/SWE-Gym`](https://huggingface.co/datasets/SWE-Gym/SWE-Gym)
- **Licence:** `mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** None (real GitHub issues and tests)
- **Decision:** `TSAI reserves`
- **Our opinion:** use. The Python repos keep their own licences. Compare the 11 repos with SWE-bench.
- **Details and 20-row sample:** [SWE-Gym__SWE-Gym](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/SWE-Gym__SWE-Gym)


### `rl-code-swe-envs-g10` — G10 SWE environments

- **Stage:** RL
- **Set:** `rl-code-swe-envs-g10`
- **Language:** Code (19 Python, 2 Go)
- **Source:** `teams/10-post-training/swe-envs/`, built by `make_env.py` from merged upstream GitHub PRs (2018 to 2022). Each env keeps the upstream issue text verbatim with its link, the repo and its licence.
- **Licence:** each repo's own licence, in `env.json.licence`: MIT (12 envs), BSD-3-Clause (9 envs). No repo is in SWE-bench, SWE-bench Multimodal, Live or Pro (`swe-envs/benchmark_repos.txt`).
- **Generator model:** None. Issue, fix (`gold.patch`) and tests (`test.patch`) are human, from the upstream PR. The Dockerfile and `verify.py` are harness code written with Claude; TSAI confirmed on 4 Nov that harness code is outside the rule because the model never trains on it.
- **Decision:** `allowed (TSAI, 4 Nov)`
- **Our opinion:** use as RL environments. Down-weight or skip the 5 envs with `quality_verdict: keep-flagged`.

### `rl-code-swe-rebench` — SWE-rebench

- **Stage:** RL
- **Set:** `rl-code-swe-rebench`
- **Language:** Code (Python SWE)
- **Source:** [`nebius/SWE-rebench`](https://huggingface.co/datasets/nebius/SWE-rebench), rows created before 2023, filtered by `swe-envs/import_pool.py` (permissive repo licence, not a benchmark repo, no AI-tool marker in the issue)
- **Licence:** `cc-by-4.0`, Hugging Face tag read on 5 Nov 2026. A tag is not legal clearance. Attribution: SWE-rebench by Nebius (arXiv 2505.20411), CC-BY-4.0. Each repo keeps its own licence.
- **Generator model:** None for the parts we use: issue, patch and tests come from real merged PRs. Qwen2.5-72B-Instruct wrote the install recipes and quality labels; we do not use them, because that model's licence is outside the generator rule.
- **Decision:** `allowed (TSAI, 4 Nov: human parts only, every env rebuilt and gold-checked by us)`
- **Our opinion:** use to scale the SWE env pool for RL. Only rows that `make_env.py` rebuilds and `verify.py --check` passes become envs.
- **Pilot (11 Nov):** 5 envs in `swe-envs/rebench-pilot/`, read from Hub commit `89cdfbab4ab1bd8f5a658bb212d1b63624f4f881`, split `test` (file sha256 values in `rebench-pilot/source_manifest.json`). Issue, fix and tests come from GitHub; from the release only ids, dates, base commit and test lists are read, to compare with the rebuild. Decontamination: fingerprints v2 full set, 15 documents (issue, tests, fix), 0 flagged, 0 canaries. Results: [`results/swe_rebench_pilot.md`](../results/swe_rebench_pilot.md).

### `rl-code-acecode-87k` — AceCode-87K

- **Stage:** RL
- **Set:** `rl-code-acecode-87k`
- **Language:** Code (Python)
- **Source:** [`TIGER-Lab/AceCode-87K`](https://huggingface.co/datasets/TIGER-Lab/AceCode-87K)
- **Licence:** `mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** GPT-4o-mini (OpenAI, closed) rewrote the questions
- **Decision:** `excluded` — TSAI ruling in the G10 chat (30 Oct): quarantined sets stay out of the lab and out of every training mix. Reason: Questions were rewritten by GPT-4o-mini, so OpenAI terms apply.
- **Our opinion:** excluded, as ruled by TSAI. Tests per problem. Questions were rewritten by GPT-4o-mini, so OpenAI terms apply to that text. Check HumanEval/MBPP overlap.
- **Details and 20-row sample:** [TIGER-Lab__AceCode-87K](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/TIGER-Lab__AceCode-87K)

### `rl-code-deepcoder` — DeepCoder-Preview-Dataset

- **Stage:** RL
- **Set:** `rl-code-deepcoder`
- **Language:** Code (competitive)
- **Source:** [`agentica-org/DeepCoder-Preview-Dataset`](https://huggingface.co/datasets/agentica-org/DeepCoder-Preview-Dataset)
- **Licence:** `mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** None (problems and tests collected from existing sets)
- **Decision:** `allowed (TSAI, 6 Nov)` — "DeepCoder (MIT) [is] in, train split only. DeepCoder must pass the G9 decontamination test first."
- **Decontamination (6 Nov):** Team 9's `decontam_check.py`, fingerprints v2, full set: 6,765 of 24,287 train rows flagged and removed (27.9%; LiveCodeBench 4,609, Codeforces 3,609). The `lcbv5` subset is LiveCodeBench itself: 599 of 599 rows flagged, so leave it out entirely. `primeintellect` 24.7% and `taco` 29.0% flagged. Use only the clean rows. Details: [`rl/decontam_report.md`](../rl/decontam_report.md).
- **Our opinion:** use, `train` only, clean rows only, without the `lcbv5` subset. The `test` data is LiveCodeBench plus CodeElo and is never used.
- **Details and 20-row sample:** [agentica-org__DeepCoder-Preview-Dataset](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/agentica-org__DeepCoder-Preview-Dataset)

### `rl-code-swe-rebench-v2` — SWE-rebench-V2

- **Stage:** RL
- **Set:** `rl-code-swe-rebench-v2`
- **Language:** Code (20 languages incl. Go)
- **Source:** [`nebius/SWE-rebench-V2`](https://huggingface.co/datasets/nebius/SWE-rebench-V2)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Qwen3-Coder-480B-A35B-Instruct (installation agent, log parsing); quality labels from an ensemble of gpt-oss-120b, GLM-4.7 and DeepSeek-V3.2 (paper, arXiv 2602.23866)
- **Decision:** `TSAI reserves`
- **Our opinion:** use. The card warns that only the original SWE-bench repos were excluded. Remove task IDs that overlap with our eval set.
- **Details and 20-row sample:** [nebius__SWE-rebench-V2](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/nebius__SWE-rebench-V2)

### `rl-code-codeforces` — codeforces

- **Stage:** RL
- **Set:** `rl-code-codeforces`
- **Language:** Code (competitive)
- **Source:** [`open-r1/codeforces`](https://huggingface.co/datasets/open-r1/codeforces)
- **Licence:** `cc-by-4.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** None (Codeforces problems); the card mentions DeepSeek-R1 only for generated test inputs
- **Decision:** `allowed (TSAI, 6 Nov)` — "open-r1/codeforces (CC-BY-4.0) [is] in, train split only. Codeforces problems are also in the G9 benchmark, so G9 must check the RL pool against it."
- **Decontamination (6 Nov):** Team 9's `decontam_check.py`, fingerprints v2, full set: 624 of 9,556 train rows flagged and removed (6.5%; Codeforces 498, LiveCodeBench 168, HLE 15). Details: [`rl/decontam_report.md`](../rl/decontam_report.md). G9 to confirm the RL pool once it is chosen.
- **Our opinion:** use, `train` only, clean rows only. The Codeforces problem text may not be covered by the dataset licence (header CC-BY-4.0, body ODC-By 4.0).
- **Details and 20-row sample:** [open-r1__codeforces](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/open-r1__codeforces)

### `rl-math-dapo-17k` — DAPO-Math-17k

- **Stage:** RL
- **Set:** `rl-math-dapo-17k`
- **Language:** English / Mathematics
- **Source:** [`BytedTsinghua-SIA/DAPO-Math-17k`](https://huggingface.co/datasets/BytedTsinghua-SIA/DAPO-Math-17k)
- **Licence:** `apache-2.0` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** Problems scraped from the web and competition sites; an unnamed LLM rewrote questions so the answer is an integer (paper, arXiv 2503.14476)
- **Decision:** `excluded` — TSAI Week 2 rule: sources we cannot trace are out. An unnamed LLM rewrote the questions (arXiv 2503.14476); this matches the Stage 2 table.
- **Our opinion:** excluded. If TSAI reconsiders it, check AIME and MATH-500 overlap first.
- **Details and 20-row sample:** [BytedTsinghua-SIA__DAPO-Math-17k](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/BytedTsinghua-SIA__DAPO-Math-17k)

### `rl-math-big-math` — Big-Math-RL-Verified

- **Stage:** RL
- **Set:** `rl-math-big-math`
- **Language:** English / Mathematics
- **Source:** [`SynthLabsAI/Big-Math-RL-Verified`](https://huggingface.co/datasets/SynthLabsAI/Big-Math-RL-Verified)
- **Licence:** `apache-2.0` — Hugging Face tag read on 29 Oct 2026; gated dataset. A tag is not legal clearance.
- **Generator model:** Llama-3.1-405B (Llama) reformulated multiple-choice questions; Llama-3.1-70B filtered; Llama-3.1-8B/405B set the solve rates; gpt-4o-mini classified domains (paper, arXiv 2502.17387). Problems come from existing sets
- **Decision:** `excluded` — TSAI rule in the G10 chat (30 Oct): data made by closed OpenAI, Anthropic, Google or Llama models stays excluded. Applied by us to this set. Reason: Llama-3.1-405B (Llama) reformulated the multiple-choice questions.
- **Our opinion:** excluded under that rule. Ask TSAI if partial use is acceptable.
- **Details and 20-row sample:** [SynthLabsAI__Big-Math-RL-Verified](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/SynthLabsAI__Big-Math-RL-Verified)

### `rl-math-deepmath-103k` — DeepMath-103K

- **Stage:** RL (and SFT)
- **Set:** `rl-math-deepmath-103k`
- **Language:** English / Mathematics
- **Source:** [`zwhe99/DeepMath-103K`](https://huggingface.co/datasets/zwhe99/DeepMath-103K)
- **Licence:** `mit` — Hugging Face tag read on 29 Oct 2026. A tag is not legal clearance.
- **Generator model:** DeepSeek-R1 (open weights)
- **Decision:** `TSAI reserves`
- **Our opinion:** use. The card says it was decontaminated against common benchmarks.
- **Details and 20-row sample:** [zwhe99__DeepMath-103K](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/zwhe99__DeepMath-103K)

### `rl-code-code-contests` — code_contests

- **Stage:** RL
- **Set:** `rl-code-code-contests`
- **Language:** Code (competitive; Python, C++, Java)
- **Source:** [`deepmind/code_contests`](https://huggingface.co/datasets/deepmind/code_contests)
- **Licence:** `cc-by-4.0` — Hugging Face tag and card. The problems and solutions are scraped from Aizu, AtCoder, CodeChef, Codeforces and HackerEarth, so the upstream sites keep their own rights.
- **Generator model:** None. Problems and solutions are human-written. The `generated_tests` field comes from programmatic mutation of existing test inputs, with outputs checked against known-correct solutions; no LLM is involved.
- **Decision:** `allowed (TSAI, 6 Nov)` — "deepmind/code_contests (CC-BY-4.0) is in too." It passes the 3 Nov generator rule: human-written and execution-verified, with no model generator.
- **Decontamination (6 Nov):** Team 9's `decontam_check.py`, fingerprints v2, full set: 2,454 of 13,328 train rows flagged and removed (18.4%; LiveCodeBench 1,662, Codeforces 1,199). Details: [`rl/decontam_report.md`](../rl/decontam_report.md).
- **Our opinion:** use, check. The card does not say who holds rights in the scraped problem text, so keep the source URL per problem. Many Codeforces problems also appear in `open-r1/codeforces` and in benchmarks such as LiveCodeBench, so the Team 9 decontamination test is needed before any use.
- **Added by:** Tanmay Sharma (Week 2 rotation, 4 Nov 2026). Hugging Face cards and generator-model pages read on 4 Nov 2026. A tag is not legal clearance.

### `rl-code-r2e-gym-v1` — R2E-Gym-V1

- **Stage:** RL
- **Set:** `rl-code-r2e-gym-v1`
- **Language:** English issue text / Code (Python SWE)
- **Source:** [`R2E-Gym/R2E-Gym-V1`](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-V1)
- **Licence:** `apache-2.0` — Hugging Face tag only; the card body (README) is empty. The code inside each environment keeps its upstream repository licence, which is not filtered or listed per row.
- **Generator model:** Unknown. The `prompt` column is an instruction to an LLM to write a GitHub issue from a commit, and `problem_statement` is that LLM's output; neither the card nor the paper (arXiv 2504.07164) names the model. Some fail-to-pass tests are also LLM-generated. The commits and code come from real repositories.
- **Decision:** `excluded` — same reason as `rl-code-r2e-gym` (R2E-Gym-Subset): the issue text comes from an untraced generator. V1 also keeps the repositories that the authors removed from the Subset because they overlap the SWE-bench test set.
- **Our opinion:** V1 is the full 8.1K-task release; `rl-code-r2e-gym` covers the 4,578-task Subset. No R2E-Gym tasks, V1 or Subset, for RL until an allowed generator replaces the issue text and the LLM-written tests are removed or replaced. `sft-code-swe-hero-openhands` regenerated the issue text for its SFT trajectories only; the tasks' tests are still the originals.
- **Added by:** Sagar063 (Week 2 rotation, 4 Nov 2026). Hugging Face card and paper read on 4 Nov 2026. A tag is not legal clearance.

### `rl-code-afm-codeagent` — AFM-CodeAgent-RL-Dataset

- **Stage:** RL
- **Set:** `rl-code-afm-codeagent`
- **Language:** English / Code and math
- **Source:** [`PersonalAILab/AFM-CodeAgent-RL-Dataset`](https://huggingface.co/datasets/PersonalAILab/AFM-CodeAgent-RL-Dataset)
- **Licence:** `apache-2.0` — Hugging Face tag.
- **Generator model:** none in this release. The rows are problems with tests or reference answers, repackaged from LiveCodeBench v1–v3 (392), Skywork-OR1-RL-Data code (10,033) and math (23,766), and DAPO-Math (13,369): 47,560 in total (arXiv 2508.13167, Table 9).
- **Decision:** `excluded` until the slices are separated. 13,369 of the 47,560 rows are DAPO-Math (`rl-math-dapo-17k`, excluded: an unnamed LLM rewrote the questions); the 23,766-row Skywork-OR1 math slice includes NuminaMath-1.5 subsets per its `data_source` field (`sft-math-numinamath-1.5`, excluded); 392 rows are LiveCodeBench, a benchmark.
- **Our opinion:** Only the 10,033-row Skywork-OR1 code slice could pass, and it has not been checked on its own. If that code is wanted, check `Skywork/Skywork-OR1-RL-Data` from its own card as a separate set; this repackaging adds only a difficulty filter tuned to the AFM 7B model. The LiveCodeBench slice goes to Team 9 in any case.
- **Added by:** Sagar063 (Week 2 rotation, 4 Nov 2026). Hugging Face card and paper read on 4 Nov 2026. A tag is not legal clearance.


### `sft-openhermes-2.5` — OpenHermes-2.5

- **Stage:** SFT
- **Set:** `sft-openhermes-2.5`
- **Language:** English / Multi-domain (900+ domains)
- **Source:** [`teknium/OpenHermes-2.5`](https://huggingface.co/datasets/teknium/OpenHermes-2.5)
- **Licence:** `apache-2.0` — fully permissive open source license.
- **Generator model:** GPT-4 (OpenAI, closed), Mixtral-8x7B, and Llama instruction recipes.
- **Decision:** `excluded` — TSAI Week 2 rule: text made by closed OpenAI, Anthropic or Google models, or by Llama models, is out.
- **Our opinion:** excluded under the closed-model / Llama generator rule.

### `sft-tulu3-filtered` — Tulu 3 SFT Mixture (Filtered)

- **Stage:** SFT
- **Set:** `sft-tulu3-filtered`
- **Language:** English / Multi-domain
- **Source:** [`allenai/tulu-3-sft-mixture`](https://huggingface.co/datasets/allenai/tulu-3-sft-mixture)
- **Licence:** `odc-by` — commercial use explicitly permitted with attribution.
- **Generator model:** Llama-3.1-70B / Llama-3.1-405B (Llama) and GPT-4o in upstream subsets.
- **Decision:** `excluded` — TSAI Week 2 rule: text made by Llama or closed OpenAI models is out.
- **Our opinion:** excluded under the Llama / closed-model generator rule.

### `sft-dolly-15k` — Databricks Dolly 15k

- **Stage:** SFT
- **Set:** `sft-dolly-15k`
- **Language:** English
- **Source:** [`databricks/databricks-dolly-15k`](https://huggingface.co/datasets/databricks/databricks-dolly-15k)
- **Licence:** `cc-by-sa-4.0` — attribution and share-alike terms.
- **Generator model:** none (human-authored ground truth by Databricks employees).
- **Decision:** `allowed (CC-BY-SA, attribution needed)`
- **Our opinion:** use. 15,000 pure human demonstrations devoid of synthetic API artifacts.

### `sft-lmsys-chat-1m` — LMSYS-Chat-1M Prompts

- **Stage:** SFT
- **Set:** `sft-lmsys-chat-1m`
- **Language:** Multilingual
- **Source:** [`lmsys/lmsys-chat-1m`](https://huggingface.co/datasets/lmsys/lmsys-chat-1m)
- **Licence:** `LMSYS Dataset Agreement` — custom non-permissive terms.
- **Generator model:** none (real-world user turns from Chatbot Arena, with closed/Llama model responses).
- **Decision:** `excluded` — custom non-permissive licence agreement and closed/Llama model outputs.
- **Our opinion:** excluded under the permissive-licence and closed/Llama generator rules.

### `sft-bespoke-stratos-17k` — Bespoke Stratos 17k

- **Stage:** SFT
- **Set:** `sft-bespoke-stratos-17k`
- **Language:** English / STEM Reasoning
- **Source:** [`bespokelabs/Bespoke-Stratos-17k`](https://huggingface.co/datasets/bespokelabs/Bespoke-Stratos-17k)
- **Licence:** `apache-2.0` — commercial use permitted.
- **Generator model:** DeepSeek-R1 (open weights).
- **Decision:** `TSAI reserves`
- **Our opinion:** use. 17,000 deep `<|think|>` reasoning traces replicating R1-style self-correction.

### `sft-numinamath-tir` — NuminaMath Tool-Integrated Reasoning

- **Stage:** SFT
- **Set:** `sft-numinamath-tir`
- **Language:** English / Python Math Tools
- **Source:** [`AI-MO/NuminaMath-TIR`](https://huggingface.co/datasets/AI-MO/NuminaMath-TIR)
- **Licence:** `apache-2.0` — commercial use permitted.
- **Generator model:** GPT-4 (OpenAI, closed) generated Python tool-integrated reasoning traces.
- **Decision:** `excluded` — TSAI Week 2 rule: text made by closed OpenAI models (GPT-4) is out.
- **Our opinion:** excluded under the closed-model generator rule.

### `sft-ultradata-cot-agent` — UltraInteract SFT

- **Stage:** SFT
- **Set:** `sft-ultradata-cot-agent`
- **Language:** English / Code & Reasoning
- **Source:** [`openbmb/UltraInteract_sft`](https://huggingface.co/datasets/openbmb/UltraInteract_sft)
- **Licence:** `mit` — commercial use permitted.
- **Generator model:** GPT-3.5 / GPT-4 (OpenAI, closed) in OpenBMB UltraInteract tree construction.
- **Decision:** `excluded` — TSAI Week 2 rule: text made by closed OpenAI models is out.
- **Our opinion:** excluded under the closed-model generator rule.

### `sft-glaive-fc-v2` — Glaive Function Calling v2

- **Stage:** SFT
- **Set:** `sft-glaive-fc-v2`
- **Language:** JSON / Tool Calls
- **Source:** [`glaiveai/glaive-function-calling-v2`](https://huggingface.co/datasets/glaiveai/glaive-function-calling-v2)
- **Licence:** `apache-2.0` — commercial use permitted.
- **Generator model:** Synthetic schema generator (Glaive AI; generator model not named on card, verify).
- **Decision:** `TSAI reserves`
- **Our opinion:** verify generator provenance before training; 113k dialogues teaching exact JSON schema compliance, `<|tool_call|>`, and `<|tool_result|>`.

### `sft-salesforce-xlam-60k` — Salesforce xLAM 60k

- **Stage:** SFT
- **Set:** `sft-salesforce-xlam-60k`
- **Language:** Multi-tool / API
- **Source:** [`Salesforce/xlam-function-calling-60k`](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k)
- **Licence:** `cc-by-4.0` — commercial use permitted with attribution.
- **Generator model:** DeepSeek-V2-Chat and Mixtral-8x22B-Instruct (open weights) via Salesforce APIGen pipeline (arXiv 2406.18518).
- **Decision:** `TSAI reserves`
- **Our opinion:** use. Multi-tool agent orchestration dialogues generated by open-weight models and verified by execution.

### `sft-code-swe-gym-trajectories` — SWE-Gym OpenHands Trajectories

- **Stage:** SFT
- **Set:** `sft-code-swe-gym-trajectories`
- **Language:** Code / Python SWE
- **Source:** [`SWE-Gym/OpenHands-SFT-Trajectories`](https://huggingface.co/datasets/SWE-Gym/OpenHands-SFT-Trajectories)
- **Licence:** `mit` — commercial use permitted.
- **Generator model:** Claude 3.5 Sonnet (Anthropic, closed) and GPT-4o trajectories via OpenHands.
- **Decision:** `excluded` — TSAI Week 2 rule: text made by closed Anthropic / OpenAI models is out.
- **Our opinion:** excluded under the closed-model generator rule (use `sft-code-swe-rebench-openhands` generated by `Qwen3-Coder-480B-A35B-Instruct` instead).

### `rl-nvidia-helpsteer2` — NVIDIA HelpSteer2 & Preference

- **Stage:** RL (Reward Modeling & DPO)
- **Set:** `rl-nvidia-helpsteer2`
- **Language:** English / Multi-domain
- **Source:** [`nvidia/HelpSteer2`](https://huggingface.co/datasets/nvidia/HelpSteer2)
- **Licence:** `cc-by-4.0` — commercial use permitted with attribution.
- **Generator model:** none for ratings/justifications (human-annotated), verify response generator models before DPO use.
- **Decision:** `TSAI reserves`
- **Our opinion:** use human-annotated ratings; filter out any response turns generated by closed or Llama models.

### `rl-skywork-reward-80k` — Skywork Reward Preference 80K

- **Stage:** RL (Reward Modeling & DPO)
- **Set:** `rl-skywork-reward-80k`
- **Language:** English / Multi-domain
- **Source:** [`Skywork/Skywork-Reward-Preference-80K-v0.2`](https://huggingface.co/datasets/Skywork/Skywork-Reward-Preference-80K-v0.2)
- **Licence:** `apache-2.0` — commercial use permitted.
- **Generator model:** Skywork reward filtering pipeline over upstream preference sets (verify upstream response generators).
- **Decision:** `TSAI reserves`
- **Our opinion:** verify upstream response generators before training.

### `rl-ultrafeedback-clean` — UltraFeedback Binarized Cleaned

- **Stage:** RL (DPO / ORPO)
- **Set:** `rl-ultrafeedback-clean`
- **Language:** English / Multi-domain
- **Source:** [`argilla/ultrafeedback-binarized-preferences-cleaned`](https://huggingface.co/datasets/argilla/ultrafeedback-binarized-preferences-cleaned)
- **Licence:** `mit` — commercial use permitted.
- **Generator model:** GPT-4 (OpenAI, closed) preference annotations and Llama-2 / GPT-4 / GPT-3.5 completions.
- **Decision:** `excluded` — TSAI Week 2 rule: text made by closed OpenAI or Llama models is out.
- **Our opinion:** excluded under the closed-model / Llama generator rule.

### `rl-nectar-rm` — Berkeley Nectar

- **Stage:** RL (Reward Modeling)
- **Set:** `rl-nectar-rm`
- **Language:** English / Multi-domain
- **Source:** [`berkeley-nest/Nectar`](https://huggingface.co/datasets/berkeley-nest/Nectar)
- **Licence:** `apache-2.0` — commercial use permitted.
- **Generator model:** GPT-4 (OpenAI, closed) ranking and GPT-4 / GPT-3.5 / Claude / Llama-2 candidate responses.
- **Decision:** `excluded` — TSAI Week 2 rule: text made by closed OpenAI/Anthropic or Llama models is out.
- **Our opinion:** excluded under the closed-model / Llama generator rule.

### `rl-intel-orca-dpo` — Intel Orca DPO Pairs

- **Stage:** RL (DPO)
- **Set:** `rl-intel-orca-dpo`
- **Language:** English / Reasoning
- **Source:** [`Intel/orca_dpo_pairs`](https://huggingface.co/datasets/Intel/orca_dpo_pairs)
- **Licence:** `apache-2.0` — commercial use permitted.
- **Generator model:** GPT-4 / GPT-3.5 (OpenAI, closed) via OpenOrca.
- **Decision:** `excluded` — TSAI Week 2 rule: text made by closed OpenAI models is out.
- **Our opinion:** excluded under the closed-model generator rule.

### `rl-distilabel-math-dpo` — Distilabel Math DPO

- **Stage:** RL (DPO / Verifier)
- **Set:** `rl-distilabel-math-dpo`
- **Language:** English / Mathematics
- **Source:** [`argilla/distilabel-math-dpo`](https://huggingface.co/datasets/argilla/distilabel-math-dpo)
- **Licence:** `apache-2.0` — commercial use permitted.
- **Generator model:** NuminaMath / Argilla mathematical verifier.
- **Decision:** `TSAI reserves`
- **Our opinion:** use. Penalizes intermediate calculation bugs and step hallucinations.

### `rl-code-feedback-dpo` — Code-Feedback DPO

- **Stage:** RL (DPO)
- **Set:** `rl-code-feedback-dpo`
- **Language:** Code (Polyglot)
- **Source:** [`HuggingFaceH4/Code-Feedback`](https://huggingface.co/datasets/HuggingFaceH4/Code-Feedback)
- **Licence:** `apache-2.0` — commercial use permitted.
- **Generator model:** HF H4 / TRL execution verification pairs.
- **Decision:** `TSAI reserves`
- **Our opinion:** use. Software engineering preferences rewarding tested implementations.

### `rl-wildguardmix` — AllenAI WildGuardMix

- **Stage:** RL (Safety Alignment)
- **Set:** `rl-wildguardmix`
- **Language:** English / Safety
- **Source:** [`allenai/wildguardmix`](https://huggingface.co/datasets/allenai/wildguardmix)
- **Licence:** `odc-by` — commercial use permitted with attribution.
- **Generator model:** WildGuard adversarial filter (Ai2).
- **Decision:** `TSAI reserves`
- **Our opinion:** use. 86k safety and jailbreak interaction pairs calibrating refusal behavior without false refusals.


### `rl-community-alignment` — community-alignment-dataset

- **Stage:** RL / preference or environment assessment
- **Set:** `rl-community-alignment`
- **Language:** Hindi, English, French, Italian, Portuguese
- **Source:** [facebook/community-alignment-dataset](https://huggingface.co/datasets/facebook/community-alignment-dataset)
- **Licence:** CC-BY-4.0
- **Generator model:** LLM candidate responses with human preferences/explanations; the checked card does not name all response generators. Paper describes Llama-based candidate generation; no compliant current-release mapping is established.
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: Hindi/English and multilingual human preference learning for RM/DPO/RLHF; general cultural preferences rather than safety-only labels. Generator: LLM candidate responses with human rankings and explanations; the card does not name all response generators, and the paper describes Llama-based candidate generation. Subset/source relationship: the current v1.1 release expands v1.0; conversations can yield multiple comparisons, so the reported 200K-plus comparisons are not the same unit as HF rows. Kolibri use is not confirmed by the report. TSAI decides generator/source requirements, safety relevance and use. Source check: 2026-11-01; [publisher card at revision 97343c7f6399fcbea430ed0f37c1768281a78d56](https://huggingface.co/datasets/facebook/community-alignment-dataset/blob/97343c7f6399fcbea430ed0f37c1768281a78d56/README.md). Additional primary evidence: [Community Alignment technical paper](https://arxiv.org/html/2507.09650).

### `rl-safety-hh-rlhf` — hh-rlhf

- **Stage:** RL / preference or environment assessment
- **Set:** `rl-safety-hh-rlhf`
- **Language:** English
- **Source:** [Anthropic/hh-rlhf](https://huggingface.co/datasets/Anthropic/hh-rlhf)
- **Licence:** MIT
- **Generator model:** Anthropic context-distilled 52B base models and later sampled/online models generate responses; crowdworkers supply preference labels.
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: human chosen/rejected preferences for reward modelling and RLHF, including the harmlessness component. Generator: Anthropic models generate responses and humans rank them. Subset/source relationship: helpfulness and harmlessness preference portions plus a separate red-team artifact; AEGIS v1 above reuses prompts with replacement Mistral responses. The publisher advises against treating raw preference/red-team transcripts as ordinary desired dialogue demonstrations. MIT licensing and Anthropic output provenance are facts for TSAI to assess; this entry makes no exclusion decision. Kolibri use is not confirmed by the report. TSAI decides use. Source check: 2026-11-01; [publisher card at revision 09be8c5bbc57cb3887f3a9732ad6aa7ec602a1fa](https://huggingface.co/datasets/Anthropic/hh-rlhf/blob/09be8c5bbc57cb3887f3a9732ad6aa7ec602a1fa/README.md).

### `rl-safety-alignment-faking` — alignment-faking-rl

- **Stage:** RL / mitigation research assessment
- **Set:** `rl-safety-alignment-faking`
- **Language:** English
- **Source:** [Anthropic/alignment-faking-rl](https://huggingface.co/datasets/Anthropic/alignment-faking-rl)
- **Licence:** CC-BY-4.0 (body link; Hub tag is cc)
- **Generator model:** Anthropic Claude model organisms, including Sonnet 3.5 / Opus 3 variants; Sonnet 4 generates synthetic scratchpads for organism construction.
- **Decision:** `TSAI reserves`
- **Our opinion:** Training purpose: assess alignment-faking mitigations and monitoring in RL. Generator: Claude-based experimental models; closed-Anthropic provenance conflicts with the week 2 generator rule and is recorded for TSAI. Subset/source relationship: evaluation transcripts collected throughout experimental RL runs, not ready-made chosen/rejected pairs or desired safe-response demonstrations. Canary-marked, scrambled transcripts include misaligned reasoning; preserve the publisher's precautions when handling them. The card asks against public reproduction without similar measures. Kolibri use is not confirmed by the report. TSAI decides any training use. [Primary methodology](https://alignment.anthropic.com/2025/alignment-faking-mitigations/). Source check: 2026-11-03; [publisher card at revision 8f43dc993db186ea10f530b72b7ce9bcd8f78262](https://huggingface.co/datasets/Anthropic/alignment-faking-rl/blob/8f43dc993db186ea10f530b72b7ce9bcd8f78262/README.md).

### `rl-code-leetcodedataset` — LeetCodeDataset

- **Stage:** RL
- **Set:** `rl-code-leetcodedataset`
- **Language:** Code (Python)
- **Source:** [`newfacade/LeetCodeDataset`](https://huggingface.co/datasets/newfacade/LeetCodeDataset); code and README on [GitHub](https://github.com/newfacade/LeetCodeDataset)
- **Licence:** `apache-2.0` — Hugging Face tag read on 3 Nov 2026. The GitHub repo says MIT. The problem text belongs to LeetCode and the card is silent on that, so upstream rights need checking (same note as `rl-code-code-contests`). A tag is not legal clearance.
- **Generator model:** Unknown for the test inputs. The paper (arXiv 2504.14655, Figures 4 and 5) prompts "the LLM" for about 100+ inputs per problem and does not name the model; the GitHub README does not name it either. Test outputs come from canonical solutions taken from GitHub repos (fspv/python-leetcode, doocs/leetcode, walkccc/LeetCode) and checked on LeetCode. The paper's SFT responses were written by Qwen2.5-Coder-32B-Instruct (Apache-2.0, open weights).
- **Decision:** `needs TSAI decision` — pending until the test-input generator is known. If it was a closed OpenAI model, this matches `sft-rl-code-rstar-coder`, excluded for GPT-4o-made test-input generators. Question to be asked on the authors' GitHub repo.
- **Our opinion:** do not enter the RLVR pipeline until (1) the generator is known, (2) Team 9 runs a 13-gram decontamination audit, and (3) TSAI signs off on the LeetCode problem text. Problems before July 2024 are the training split and later ones the test split, so the decontamination check matters for both.
- **Added by:** SomaKorada07 (Week 2 rotation, 4 Nov 2026; updated 5 Nov after review). Paper and GitHub README read on 5 Nov 2026.

### `rl-math-processbench` — ProcessBench

- **Stage:** Evaluation (step verification); listed in the RL table only as a candidate verifier or PRM benchmark
- **Set:** `rl-math-processbench`
- **Language:** English / Mathematics
- **Source:** [`Qwen/ProcessBench`](https://huggingface.co/datasets/Qwen/ProcessBench)
- **Licence:** `apache-2.0` — Hugging Face tag read on 3 Nov 2026. A tag is not legal clearance.
- **Generator model:** Not on the card. The paper (arXiv 2412.06559, Table 4) names 12 solution generators: Meta-Llama-3-8B/70B-Instruct and Llama-3.1-8B/70B-Instruct (Llama Community Licences), and Qwen2-1.5B/7B/72B, Qwen2.5-1.5B/7B/72B and Qwen2.5-Math-7B/72B Instruct. Step errors are labelled by human experts with doctoral-level maths (three to five per solution). Qwen2.5-72B-Instruct only checked final answers and split solutions into steps.
- **Decision:** `excluded` from training — eval only, not training data. Assigned to Team 9 (Evaluation) as an evaluation probe, with a G9 decontamination check. Not part of the RL training mix.
- **Our opinion:** use only to evaluate a verifier or PRM. It is a benchmark built from gsm8k, MATH, OlympiadBench and Omni-MATH problems, and part of it was written by Llama models, so it must not be ingested as training data.
- **Added by:** SomaKorada07 (Week 2 rotation, 4 Nov 2026; updated 5 Nov after review). Paper read on 5 Nov 2026.

### `rl-math-deepscaler` — DeepScaleR-Preview-Dataset

- **Stage:** RL
- **Set:** `rl-math-deepscaler`
- **Language:** English / Mathematics (competition problems with a single checkable answer)
- **Source:** [`agentica-org/DeepScaleR-Preview-Dataset`](https://huggingface.co/datasets/agentica-org/DeepScaleR-Preview-Dataset)
- **Licence:** `mit` on the release — Hugging Face tag read on 10 Nov 2026 (`license: mit` in the card header; no further licence text). A tag is not legal clearance. Upstream: Omni-MATH is `apache-2.0` (human competition problems); AIME and AMC problems are competition text, as in `rl-code-code-contests`; the Still source (RUCAIBox/STILL-3-Preview-RL-Data, "30k from MATH, NuminaMathCoT, and AIME 1983-2023" per the STILL GitHub README) states no licence on its card (which returned 401 to me on 10 Nov) or in its repository README.
- **Generator model:** none for the training text. The 40,315 rows are "AIME (American Invitational Mathematics Examination) problems (1984-2023)", "AMC (American Mathematics Competition) problems (prior to 2023)", Omni-MATH and Still, each with the "Offical solution to the problem" and an answer "usually extracted from the solution". The preprocessing code (rllm-org/rllm at commit 4ff618a7ed, 12 Feb 2025) sets `GEMINI_MODEL = "gemini-1.5-pro-002"` and `OAI_RM_MODEL = "gpt-4o-mini"`; `call_gemini_llm` is used in `rllm/data/preprocess/omni_math.ipynb` to "Filter for non-proof problems" and in `difficulty_judge.py` to score difficulty; duplicates are found with `sentence-transformers/all-MiniLM-L6-v2` embeddings. So a closed Google model acted as a filter and judge, not as a writer, as far as the code shows. The team's blog post (Notion) could not be read by me; if it says Gemini also extracted the final answers, the `answer` field is closed-model output.
- **Decision:** `excluded` — data licence rule: unstated licences are out and sources we cannot trace are out. The Still rows have no stated licence and include NuminaMath-CoT problems (`excluded` above for GPT-4 / GPT-4o content), and the release has only `problem`, `answer` and `solution` columns, with no `source` field, so those rows cannot be dropped. The MIT tag on the release does not cure the upstream terms.
- **Our opinion:** excluded as released. The traceable parts are available directly: AIME and AMC problems through `rl-code-code-contests`-style competition sources, and Omni-MATH (Apache-2.0) as its own set, now `rl-math-omni-math`. If TSAI prefers to keep this set, the open questions are the Still licence, the closed-model filter, and the unverified Gemini answer extraction; G9 would also need the decontamination test, because the combined preprocessing notebook loads a `math` file not listed on the card.
- **Added by:** swatibansal (Week 2 rotation, 11 Nov 2026). Hugging Face cards, papers and repository code read on 10-11 Nov 2026. A tag is not legal clearance.

### `rl-safety-aya-redteaming` — Aya Red-teaming (Hindi)

- **Stage:** RL (safety prompts; also usable as SFT refusal prompts once responses are written)
- **Set:** `rl-safety-aya-redteaming`
- **Language:** Hindi (`aya_hin.jsonl`, 915 prompts: 608 global harm, 307 local harm). The other seven languages (Arabic, English, Filipino, French, Russian, Serbian, Spanish) are not used.
- **Source:** [`CohereLabs/aya_redteaming`](https://huggingface.co/datasets/CohereLabs/aya_redteaming) (card revision `5a16fee03c`); paper [arXiv 2406.18682](https://arxiv.org/abs/2406.18682)
- **Licence:** `apache-2.0` — Hugging Face tag and card read on 8 Nov 2026 and unchanged on 12 Nov 2026: "This dataset can be used for any purpose, whether academic or commercial, under the terms of the Apache 2.0 License." Permissive: in under the data licence rule. A tag is not legal clearance.
- **Generator model:** None. "Curated by: Professional compensated annotators" (card). Each row has the original prompt, a literal and a semantic English translation, a harm category and an explanation.
- **Decision:** `TSAI reserves` — permissive licence, human-written prompts, no generator model.
- **Our opinion:** use as Hindi safety prompts for the refusal / safety reward. Prompts only, so responses must come from the policy (RL) or an allowed generator (SFT). The prompts are harmful by design; keep them out of any general SFT mix. Small (915 rows), but human-written in Hindi with India-specific ("local") harms, which the English safety sets do not cover.
- **For Team 9:** check it is not in the safety evaluation set; Aya red-teaming prompts are used as an eval in the paper.
- **Added by:** jssunil (Week 2 rotation, 8 Nov 2026). Card read and Hindi file counted on 8 Nov 2026; card revision re-checked on 12 Nov 2026.

### `rl-agentic-nemotron-tool-use-pivot` — Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1

- **Stage:** RL
- **Set:** `rl-agentic-nemotron-tool-use-pivot`
- **Language:** English / conversational tool use (authentication, lookup, booking; 838 domains)
- **Source:** [`nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1`](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1) (card revision `bfc7a4dd55`)
- **Licence:** `cc-by-4.0`: Hub tag and card, read on 9 Nov 2026 and unchanged on 12 Nov 2026. The card says it is ready for commercial use. Attribution is needed. A tag is not legal clearance.
- **Generator model:** data from DeepSeek-R1-0528 (MIT), DeepSeek-V3.2 (MIT), Qwen3-235B-A22B-Thinking-2507 (Apache-2.0) and Qwen3-32B (Apache-2.0). Labels from gpt-oss-120b (Apache-2.0) and Qwen3-235B-A22B-Instruct-2507 (Apache-2.0). Both lists are in the card's Dataset Characterization section.
- **Decision:** `TSAI reserves`. It passes the 3 Nov generator rule: every model named is open-weight MIT or Apache-2.0.
- **Our opinion:** use, check. 170,320 train rows. Each assistant step is a reward check: did the policy pick the same tool call as the expert trajectory? The card does not name the source of those expert trajectories. The format is NeMo Gym JSON, so it needs an adapter for our RL loop.
- **Added by:** shankarpandala (Week 2 rotation, 9 Nov 2026). Hugging Face card and model pages read on 9 Nov 2026; card revision re-checked on 12 Nov 2026.

### `rl-tool-hammerbench` — HammerBench

- **Stage:** RL (eval only)
- **Set:** `rl-tool-hammerbench`
- **Language:** English and Chinese (`en/` and `zh/`) / Tool use (mobile-app function calling: imperfect instructions, intent and argument shifts, external information, irrelevant tools)
- **Source:** [`MadeAgents/HammerBench`](https://huggingface.co/datasets/MadeAgents/HammerBench) (card revision `18b4f4ea47`); paper [arXiv 2412.16516](https://arxiv.org/abs/2412.16516)
- **Licence:** `apache-2.0` — Hugging Face tag and card front matter, read on 13 Nov 2026.
- **Generator model:** not named. The paper builds the data from app-store functions and anonymized user logs and "expanded the dataset with open-source models, creating a cost-effective data generation pipeline" (§1, §4); "LLMs then generate queries" (§4.1.1). The models are not named. GPT-4o and Claude 3.5 Sonnet appear only as evaluated baselines.
- **Decision:** `excluded` — it is an evaluation benchmark, not training data, and its generator models are not stated.
- **Our opinion:** do not train on it. It is a good multi-turn function-calling probe for Team 9.
- **For Team 9:** candidate evaluation probe for multi-turn tool use. If it is used, add it to the decontamination benchmark list so tool-use SFT sets are checked against it.
- **Added by:** chapanduk (Week 2 rotation, 13 Nov 2026). Card and paper read on 13 Nov 2026. A tag is not legal clearance.

### `rl-math-rlvr-gsm` — RLVR-GSM

- **Stage:** RL
- **Set:** `rl-math-rlvr-gsm`
- **Language:** English / Mathematics. GSM8k problems with a ground-truth answer.
- **Source:** [`allenai/RLVR-GSM`](https://huggingface.co/datasets/allenai/RLVR-GSM) (card revision `b14884519de8`)
- **Licence:** `mit` — Hugging Face tag, read on 13 Nov 2026.
- **Generator model:** none. The card says this is GSM8k formatted for reinforcement learning with a verifiable answer. No model writes new text.
- **Decision:** `TSAI reserves` — human problems and answers, MIT, train split only. The test split is the GSM8k test set and is not for training.
- **Our opinion:** use the train split only, after a decontamination check against GSM8k.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Shankar Pandala's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `rl-agentic-afm-webagent` — AFM-WebAgent-RL

- **Stage:** RL
- **Set:** `rl-agentic-afm-webagent`
- **Language:** English / Web agent
- **Source:** [`PersonalAILab/AFM-WebAgent-RL-Dataset`](https://huggingface.co/datasets/PersonalAILab/AFM-WebAgent-RL-Dataset) (card revision `ab0d8541dbbe`)
- **Licence:** `apache-2.0` — Hugging Face tag, read on 13 Nov 2026.
- **Generator model:** not named. The card does not say which model wrote the trajectories.
- **Decision:** `excluded` — the generator is not named.
- **Our opinion:** out until the model is named.
- **Added by:** Sai Teja (lead), 13 Nov 2026, for Srinivasan Govindaraj's batch. Card read on 13 Nov 2026. A tag is not legal clearance.

### `rl-math-hendrycks` — MATH (train)

- **Stage:** RL (also usable as SFT on the human solutions)
- **Set:** `rl-math-hendrycks`
- **Language:** English / Mathematics
- **Source:** [`EleutherAI/hendrycks_math`](https://huggingface.co/datasets/EleutherAI/hendrycks_math) (card revision `21a5633873b6a120296cce3e2df9d5550074f4a3`, the snapshot named in `results/effort_probe.md`); GitHub [`hendrycks/math`](https://github.com/hendrycks/math); paper [arXiv 2103.03874](https://arxiv.org/abs/2103.03874)
- **Licence:** `mit` — Hugging Face tag read on 14 Nov 2026, and the GitHub LICENSE (MIT, copyright 2021 Dan Hendrycks) read the same day. Permissive: in under the data licence rule. A tag is not legal clearance.
- **Generator model:** None. The paper (§3.1) collects 12,500 competition problems (AMC 10, AMC 12, AIME and others) from AoPS, each with a human step-by-step solution. This release is that set: 7,500 train and 5,000 test, across algebra, counting and probability, geometry, intermediate algebra, number theory, prealgebra and precalculus. It does not include the AMPS pretraining corpus (Khan Academy and Mathematica).
- **Decision:** `TSAI reserves` — permissive licence, human-written problems and solutions, no generator model. Train split only.
- **Our opinion:** use the train split (7,500 problems) for RL, or for short SFT on the human solutions. The 5,000-problem test split is the MATH benchmark: do not train on it.
- **For Team 9:** decontaminate the train split against MATH, MATH-500, AIME and any other contest eval that shares these problems. The test split stays an eval hold-out.
- **Added by:** SreekanthZipsy (Week 10 rotation 13 Nov 2026). Card, GitHub licence and paper read on 14 Nov 2026. A tag is not legal clearance.

### `rl-code-apps` — APPS (train)

- **Stage:** RL (also usable as SFT on the human solutions)
- **Set:** `rl-code-apps`
- **Language:** English / Code (Python)
- **Source:** [`codeparrot/apps`](https://huggingface.co/datasets/codeparrot/apps) (card revision `21e74ddf8de1a21436da12e3e653065c5213e9d1`); GitHub [`hendrycks/apps`](https://github.com/hendrycks/apps); paper [arXiv 2105.09938](https://arxiv.org/abs/2105.09938)
- **Licence:** `mit` — Hugging Face tag read on 14 Nov 2026, and the GitHub LICENSE (MIT, copyright 2021 Dan Hendrycks) read the same day. Permissive. A tag is not legal clearance. Problem text is scraped from Codewars, AtCoder, Kattis and Codeforces (paper §3), the same kind of upstream contest text as `rl-code-code-contests`.
- **Generator model:** None. The paper (§3) says the 232,421 ground-truth solutions were written by humans. Problems were manually curated from those sites. No model generator is named.
- **Decision:** `TSAI reserves` — permissive licence, human problems and human solutions. Train split only (5,000 problems).
- **Our opinion:** use the train split for execution-checked RL. The test split (5,000) is the APPS benchmark: do not train on it. TACO reports an overlap coefficient of 0.3778 with APPS (arXiv 2312.14852), and both overlap `rl-code-code-contests`, so de-duplicate by problem URL before mixing.
- **For Team 9:** decontaminate against APPS, HumanEval, MBPP and LiveCodeBench.
- **Added by:** SreekanthZipsy (Week 10 rotation 13 Nov 2026). Card, GitHub licence and paper read on 14 Nov 2026. A tag is not legal clearance.

### `rl-code-taco` — TACO (train, HackerRank and LeetCode left out)

- **Stage:** RL
- **Set:** `rl-code-taco`
- **Language:** English / Code (Python)
- **Source:** [`BAAI/TACO`](https://huggingface.co/datasets/BAAI/TACO) (card revision `d593ed0a2becbbc952230bb89be09189bf1056dc`), train split, rows whose `source` is not HackerRank and not LeetCode; paper [arXiv 2312.14852](https://arxiv.org/abs/2312.14852)
- **Licence:** `apache-2.0` on the release — Hugging Face tag and card read on 14 Nov 2026. The card adds that some content is under MIT or was web-crawled under CC-BY-4.0, and then says: "We don't know what the legal rights or data licenses of HackerRank." Those rows are not part of this set. LeetCode problem text is the open question already recorded on `rl-code-leetcodedataset`, so those rows are not part of this set either. A tag is not legal clearance.
- **Generator model:** None named. The paper (§2 and §3.1) collects problems by scraping CodeChef, Codeforces, HackerRank and GeeksforGeeks, and by reusing APPS, CodeContests and Description2Code. It ships 1,539,152 verified Python 3 solutions collected with those problems. It names no LLM writer. The authors consolidated the sites' raw tags into skill labels.
- **Decision:** `TSAI reserves` — the kept train rows have a stated permissive licence and no model generator. HackerRank is out because its licence is unstated, in the card's own words. LeetCode is out until TSAI answers `rl-code-leetcodedataset`.
- **Our opinion:** use the filtered train split. The release has 25,443 train problems before that filter. The `source` field is what makes the filter possible. The test split (1,000) is the TACO benchmark and is not part of this set. Contest-site text is the same point TSAI already accepted for `rl-code-code-contests`. De-duplicate against `rl-code-apps` and `rl-code-code-contests`.
- **For Team 9:** decontaminate against the TACO test split, APPS, HumanEval, MBPP and LiveCodeBench.
- **Added by:** SreekanthZipsy (Week 10 rotation 13 Nov 2026). Card and paper read on 14 Nov 2026. A tag is not legal clearance.

### `rl-math-omni-math` — Omni-MATH

- **Stage:** RL, if TSAI allows a set the publisher released only as a benchmark
- **Set:** `rl-math-omni-math`
- **Language:** English / Mathematics (Olympiad)
- **Source:** [`KbsdJames/Omni-MATH`](https://huggingface.co/datasets/KbsdJames/Omni-MATH) (card revision `40ba231d8f16e29ecd40e6407e2c8640145a8f62`); paper [arXiv 2410.07985](https://arxiv.org/abs/2410.07985)
- **Licence:** `apache-2.0` — Hugging Face tag read on 14 Nov 2026. Permissive with attribution. A tag is not legal clearance. Problems and solutions are crawled from contest sites and AoPS (paper §2.1), the same kind of upstream text as `rl-code-code-contests`.
- **Generator model:** None for the problem and solution text. The paper (§2.1) crawls official contest solutions and AoPS Wiki solutions, and AoPS forum posts that agree on the answer, then has graduate annotators check them: 4,428 problems after that check. GPT-4o (OpenAI, proprietary closed) is used only to assign a difficulty score when the contest is missing from the AoPS rating page, and to assign the domain label (§2.2 and §2.3). Those two fields are closed-model output. Drop them. They are not the problem or the solution.
- **Decision:** `needs TSAI decision` — the problem and solution text passes the generator rule (human) and the licence is permissive. The publisher released all 4,428 rows as one benchmark, with no train split. The card and the paper title both call it an Olympiad benchmark. The question for TSAI: train on it, or keep it eval-only the way `rl-math-processbench` is eval-only. `rl-math-deepscaler` was excluded partly because it mixed this set with unlicensed Still rows. This entry is that set on its own.
- **Our opinion:** use for RL only if Team 9 does not report Omni-MATH. If it is an eval, do not train on any row. There is no train split to keep.
- **For Team 9:** if this set is approved for training, Omni-MATH cannot also be a reported benchmark. The difficulty and domain columns stay out either way.
- **Added by:** SreekanthZipsy (Week 10 rotation 13 Nov 2026). Card and paper read on 14 Nov 2026. A tag is not legal clearance.

## Strategy v0

- **Commercial-use data only:** Any dataset or file whose licence is missing or restricts commercial use is excluded.
- **Decision authority:** `TSAI reserves` all dataset release and retention decisions across all members.
- **Repository hygiene:** Raw Parquet, Arrow, or binary training files never enter `era-v5-lab` (enforced by `pr-guard`).
- **Token & effort rules:** 256 reserved special tokens (`0..255`) and four plain-text effort levels (`1k`, `4k`, `16k`, `64k`).
- **Benchmark decontamination protocol:** All training splits (code and text) must be programmatically decontaminated against evaluation benchmarks (SWE-bench, HumanEval, MBPP, LiveCodeBench, BigCodeBench) using 13-gram exact match and embedding-similarity filtering prior to post-training.
- **Provenance & attribution ledger:** Every permissive dataset (ODC-By, CC-BY, Apache-2.0, MIT, Stack per-file notices) has its snapshot timestamp, source repository URL, and licensing terms recorded for automatic aggregation into the release model card.
- **Right-to-be-forgotten & takedown handling:** For curated web crawls (FineWeb-2, HPLT 3.0), maintain source URL manifests to fulfill upstream robots.txt exclusions, DMCA notices, and GDPR Article 17 deletion requests across training checkpoint iterations.
- **Excluded sets:** A set that TSAI rules out is marked `excluded` in the table with the reason, stays listed, and is never used in a training mix. CC-BY-SA data made by a permissive model is `allowed (CC-BY-SA, attribution needed)`; attribution goes in the model card. Sets that need a decontamination test go to G9 (Evaluation) first.

---

## Hand-off to Team 11 (Release) — Licence & Attribution Facts (Wed 4 Nov)

For Team 11's public model card, datasheet, and release compliance ledger:

1. **Permissive & Attribution-Required Post-Training Sets (`TSAI reserves`):**
   - **MIT:** `bigcode/commitpackft`, `SWE-Gym/SWE-Gym`, `agentica-org/DeepCoder-Preview-Dataset`, `zwhe99/DeepMath-103K`, `BodduSriPavan111/chandassu`.
   - **Apache-2.0:** `CohereLabs/aya_collection` (Apache-2.0 collection tag, 10 subsets with permissive source licences under TSAI review; see [source licence review](https://github.com/theschoolofai/era-v5-lab/pull/399)), `CohereLabs/aya_dataset`, `open-r1/OpenR1-Math-220k`, `open-thoughts/OpenThoughts3-1.2M`, `bespokelabs/Bespoke-Stratos-17k`, `OpenAssistant/oasst2` (human turns only), `Jackrong/GLM-5.1-Reasoning-1M-Cleaned` (`PHD-Science` config).
   - **CC-BY-4.0 (Attribution required in release model card):** `nebius/SWE-rebench-openhands-trajectories`, `nvidia/Nemotron-Terminal-Corpus`, `nvidia/OpenCodeReasoning`, `nvidia/OpenCodeReasoning-2`, `open-r1/codeforces-cots`, `nvidia/OpenMathReasoning`, `nvidia/Nemotron-Science-v1`, `Salesforce/xlam-function-calling-60k` (Mixtral-8x22B-Instruct Apache-2.0 rows), `nvidia/Nemotron-Cascade-SFT-SWE`, `nvidia/Nemotron-Agentic-v1`, `nvidia/Nemotron-SFT-Agentic-v2` (tool-calling part only), `nvidia/Aegis-AI-Content-Safety-Dataset-1.0`, `nebius/SWE-rebench-V2`, `open-r1/codeforces`, `ai4bharat/sangraha`, `ai4bharat/IndicCorpV2`.
   - **Stack per-file permissive (MIT, Apache-2.0, BSD; attribution required):** `bigcode/starcoderdata` (`code-go`, `code-python`, `code-rust` permissive subsets; copyleft and non-commercial files filtered out).
   - **ODC-By v1.0 (Attribution required in release model card):** `HuggingFaceFW/fineweb-2` (`ind-mr-fw2`, `ind-kn-fw2`), `nvidia/Nemotron-Instruction-Following-Chat-v1` (chat split), `nvidia/Nemotron-SFT-Instruction-Following-Chat-v2`.
   - **Approved Generator Models (3 Nov TSAI decision):** Human-written data, execution-verified synthesis, and output of open-weight models whose licence is **MIT or Apache-2.0** and allows training other models on their output (`gpt-oss-120b` Apache-2.0, `DeepSeek-R1` / `DeepSeek-V3.2` MIT, `Qwen3-Coder-480B-A35B-Instruct` / `Qwen3-235B` / `Qwen3-32B` Apache-2.0, `QwQ-32B` Apache-2.0, `Mixtral-8x22B` / `Mistral-7B` Apache-2.0, `Goedel-Prover-V2-32B` Apache-2.0, `GLM-4.6` / `GLM-4.7` / `GLM-5.1` MIT).
   - **SWE environments (`allowed`, TSAI 4 Nov):** `nebius/SWE-rebench` (CC-BY-4.0; credit SWE-rebench by Nebius, arXiv 2505.20411; human issue, patch and tests only) and the G10 `swe-envs/` (each upstream repo's own licence, MIT or BSD-3-Clause, with its repo and PR link in `env.json`).
2. **Share-Alike Sets (`allowed (CC-BY-SA, attribution needed)`):**
   - `nvidia/Nemotron-Math-Proofs-v1` (`cc-by-sa-4.0`, generator: `gpt-oss-120b` Apache-2.0 + `Goedel-Prover-V2-32B` Apache-2.0), `nvidia/Nemotron-Math-v2` (`cc-by-4.0, cc-by-sa-4.0`, generator: `gpt-oss-120b` Apache-2.0), `nvidia/Nemotron-SFT-Science-v2` (`cc-by-sa-4.0`, generator: `gpt-oss` Apache-2.0 + `DeepSeek-V3.2` MIT + `Kimi-K2` Modified MIT), and `databricks/databricks-dolly-15k` (`cc-by-sa-4.0`, human-authored). Carry source URLs, licence links, and attribution notices in the release datasheet.
3. **Strict Generator & Licence Exclusions (`excluded` — zero rows enter training):**
   - Per the 3 Nov TSAI decision, three classes of generator models are strictly `excluded` above and blocked from `sft/convert.py`:
     1. **Closed models (`OpenAI`, `Anthropic`, `Google`):** `Magicoder-OSS-Instruct-75K`, `rStar-Coder`, `orca-math-word-problems-200k-hindi-filtered`, `Aryabhatta-Orca-Maths-Hindi`, `NuminaMath-1.5`, `NuminaMath-CoT`, `OpenHermes-2.5`, `NuminaMath-TIR`, `UltraInteract_sft`, `SWE-Gym/OpenHands-SFT-Trajectories`, `wildjailbreak`, `AceCode-87K`, `ultrafeedback-binarized-preferences-cleaned`, `Nectar`, `orca_dpo_pairs`, `wildguardmix`, `hh-rlhf`, `alignment-faking-rl`, `IndicGuard`.
     2. **Llama models & use-restriction licences (`OpenRAIL-M`):** `StarCoder2` (`bigcode/self-oss-instruct-sc2-exec-filter-50k` — BigCode OpenRAIL-M makes a model trained on its output a derivative carrying its use restrictions), `indic-align` (Llama-2-70B), `OpenMathInstruct-2` (Llama-3.1-405B), `tulu-3-sft-mixture` (Llama-3.1), `Nemotron-Post-Training-Dataset-v1` (Llama-3.3), `Nemotron-Safety-Guard-Dataset-v3` (Llama jury + Google Translate), `Big-Math-RL-Verified` (Llama-3.1), `Skywork-Reward-Preference-80K-v0.2` (Llama-3 Magpie), `community-alignment-dataset` (Llama candidates), `CodeFeedback-Filtered-Instruction` (GPT-3.5/4 + Qwen-72B non-Apache-2.0).
     3. **Unknown / unstated generator models on the dataset card:** `Nemotron-SFT-Competitive-Programming-v2`, `Nemotron-SFT-SWE-v3`, `Nemotron-SFT-Agentic-v2` (search & customer-service parts), `samvaad-hi-v1`, `oss-codes/*`, `glaive-function-calling-v2`, `Nemotron-SFT-Safety-v2`, `R2E-Gym-Subset`, `DAPO-Math-17k`, `distilabel-math-dpo`.


### Ranjani Chandrasekaran — RL sets (week 2)

| Set | Source | Language | Generator model | Licence | Decision |
|---|---|---|---|---|---|
| rl-synthetic2 | PrimeIntellect/SYNTHETIC-2-RL | English / Math, Code, Reasoning | DeepSeek-R1-0528 (MIT, open weights) for reasoning traces; Qwen3-32B, Qwen3-4B and DeepSeek-R1-0528-Qwen3-8B (Apache-2.0/MIT) for difficulty annotations | apache-2.0 | TSAI reserves |
| rl-skywork-or1 | PrimeIntellect/Skywork-OR1-RL-Data | English / Mathematics | DeepSeek-R1-Distill-Qwen 1.5B, 7B, 32B (open weights, derived from MIT-licensed DeepSeek-R1) for difficulty annotations | apache-2.0 | TSAI reserves |
