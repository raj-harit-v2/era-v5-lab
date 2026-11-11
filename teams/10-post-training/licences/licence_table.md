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
| sft-code-opencodereasoning-2 | [nvidia/OpenCodeReasoning-2](https://huggingface.co/datasets/nvidia/OpenCodeReasoning-2) | Code (competitive) | DeepSeek-R1 (MIT) for solutions, QwQ-32B (Apache-2.0) for critiques (both open weights) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-code-codeforces-cots | [open-r1/codeforces-cots](https://huggingface.co/datasets/open-r1/codeforces-cots) | Code (competitive) | DeepSeek-R1 (MIT, open weights) | cc-by-4.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
| sft-indic-aya-collection | [CohereLabs/aya_collection](https://huggingface.co/datasets/CohereLabs/aya_collection) (12 templated Indic subsets only) | Hindi, Bengali, Tamil, Telugu | none (human speaker-written templates applied to human-annotated Indic NLP datasets; no model generator) | apache-2.0 (Hub tag; commercial use permitted per tag) | TSAI reserves |
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

Twenty-three sets in the two stage sections are `excluded`: eleven earlier ones (six named by TSAI, and five more where a closed OpenAI or Llama model made part of the data: `sft-code-magicoder-oss`, `sft-indic-indic-align`, `sft-math-numinamath-cot`, `sft-rl-code-rstar-coder`, `rl-math-big-math`), nine added on 1 Nov for closed-model, Llama or custom-licence reasons, and three added in the 2 Nov review (`sft-math-numinamath-1.5`, `sft-agentic-nemotron-sft-agentic-v2-other`, `sft-indic-aya-collection-other`). Two CC-BY-SA sets (`sft-math-nemotron-proofs`, `sft-math-nemotron-math-v2`) are `allowed (CC-BY-SA, attribution needed)` after TSAI's update that CC-BY-SA data is allowed with attribution. `sft-science-nemotron-science` goes to G9 (Evaluation) for a decontamination test before any use. `rl-code-swe-envs-g10` and `rl-code-swe-rebench` are `allowed` after TSAI's 4 Nov answer on SWE environments (human issue, patch and tests only; every env rebuilt and gold-checked by us). `rl-code-deepcoder`, `rl-code-codeforces` and `rl-code-code-contests` are `allowed` after TSAI's 6 Nov answer (train splits only), and their decontamination results are in `rl/decontam_report.md`.

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
- **Decision:** `TSAI reserves`
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

### `sft-indic-aya-collection` — aya_collection, 12 templated Indic subsets

- **Stage:** SFT
- **Set:** `sft-indic-aya-collection`
- **Language:** Hindi, Bengali, Tamil, Telugu
- **Source:** [`CohereLabs/aya_collection`](https://huggingface.co/datasets/CohereLabs/aya_collection), only these subsets: `templated_bengali_news`, `templated_hindi_headline`, `templated_hindi_news`, `templated_indic_paraphrase`, `templated_indic_sentiment`, `templated_tamil_stories`, `templated_tamil_thirukkural`, `templated_telugu_food`, `templated_telugu_jokes`, `templated_telugu_news`, `templated_telugu_poems`, `templated_telugu_riddles`
- **Licence:** `apache-2.0` — Hugging Face tag and card read on 2 Nov 2026. The card says it aims to include only permissive datasets; it does not list the licence of each of the 44 source datasets. A tag is not legal clearance.
- **Generator model:** None for the text. In these subsets, templates written by fluent speakers are applied to existing datasets (news, headlines, sentiment, paraphrase, jokes, poems, riddles, stories, couplets); no model writes the answers. The source datasets are not named on the card.
- **Decision:** `TSAI reserves`
- **Our opinion:** use only these 12 subsets, and only after the source dataset, licence and origin of each one are written in this section (a rotation task). They are task-style data (classification, headline writing), not open instructions, and cover only four of the ten scripts: expect less usable text than the mix proposal's 5% assumes, and fill the gap from `aya_dataset`.
- **Details and 20-row sample:** [CohereLabs__aya_collection](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets/CohereLabs__aya_collection)

### `sft-indic-aya-collection-other` — aya_collection, translated datasets and other subsets

- **Stage:** SFT
- **Set:** `sft-indic-aya-collection-other`
- **Language:** 101 languages
- **Source:** [`CohereLabs/aya_collection`](https://huggingface.co/datasets/CohereLabs/aya_collection): the 19 `translated_*` datasets and every templated subset not listed above
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

## Stage 2: Preference optimization and RLVR, candidate sets

Verifiable-answer and test-based sets for RL (math, code, SWE tasks). Each entry has the standard fields, `TSAI reserves` as the decision (`excluded` where TSAI ruled a set out), and one line of opinion. Licence values are the Hugging Face tags read on 29 Oct 2026; a tag is not legal clearance. Per-dataset notes, 20-row samples and a benchmark-overlap check are in [team10-datasets](https://github.com/RaviNaik/ERA/tree/main/v5/capstone/team10-datasets).

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
   - **Apache-2.0:** `CohereLabs/aya_collection` (12 templated Indic subsets only), `CohereLabs/aya_dataset`, `open-r1/OpenR1-Math-220k`, `open-thoughts/OpenThoughts3-1.2M`, `bespokelabs/Bespoke-Stratos-17k`, `OpenAssistant/oasst2` (human turns only), `Jackrong/GLM-5.1-Reasoning-1M-Cleaned` (`PHD-Science` config).
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
