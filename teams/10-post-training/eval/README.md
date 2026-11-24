# Effort evaluation (Package T2)

A fixed set of prompts crossed with the four effort labels `1k`, `4k`, `16k` and `64k`. The requested label and the enforced generation cap are separate fields in every record. The suite measures three things apart: whether the output follows the format, whether it stays inside the cap, and whether it is correct. A text instruction is not a budget mechanism.

| File | What it is |
|---|---|
| `effort_manifest.json` | The frozen manifest of 100 slots (30 code, 25 math, 20 tool/agentic, 15 Indic, 10 general). Prompt texts are not stored: each slot points at a row of a pinned upstream file and holds the sha256 of its text. |
| `effort_suite.py` | The suite, with the subcommands `verify`, `plan`, `run`, `guard` and `compare`. |
| `test_effort_suite.py` | CPU tests, no model and no network. |
| `stage_a_modal.py`, `stage_b_modal.py`, `stage_b_qwen_modal.py` | Generation only, on one H100 through Modal (OLMoE-1B-7B-0924-Instruct for Stages A and B, Qwen3.6-35B-A3B-FP8 for the Qwen Stage B). |
| `stage_a_report.py`, `stage_b_report.py`, `stage_b_qwen_report.py` | Local scoring of the generations with the checkers in `rl-data/` (math-verify for math, Docker for stdin/stdout code), then the per-tier readout. |

```bash
python -m pytest teams/10-post-training/eval/test_effort_suite.py -q -p no:cacheprovider
```

The results are in `results/`. The models in these runs are open stand-ins, not the capstone model, and every record is marked `do_not_train`.

## Gate

No gate is named in these files. The suite is development evidence for the effort labels in `sft/sft_mix_proposal.md` section 4. G9's own final score is separate.

## What has been measured (committed results only)

- **Suite and CPU checks, 11 Nov:** `results/effort_probe.md` records the 30 tests, the manifest `verify` run, a scripted-completion pipeline smoke (no model), and a `guard` run that flags the 55 resolved tasks in the local RL v1 files.
- **Qwen3.6-35B-A3B-FP8, Stage B, 12 Nov:** 55 prompts (30 code, 25 math) x 4 labels x 2 samples = 440 cells at a 1024-token cap. `results/effort_stageB_qwen_2026-11-12/report.md` records 161 of 440 cells correct, 262 cells censored by the cap, 0 parse failures, and no visible effect of the label at a fixed cap. That report calls Qwen an above-floor reference, not the capstone model.
- **OLMoE-1B-7B-0924-Instruct, Stage A and Stage B:** the Qwen report quotes these (Stage B: 5, 5, 5 and 7 correct of 110 cells at 1k, 4k, 16k, 64k). The OLMoE result files are committed in `results/effort_stageA_olmoe_2026-11-12/` and `results/effort_stageB_olmoe_2026-11-12/` (Stage B `report.md`: 22 of 440 cells correct).

## What has not been measured

- **Stage C** (label budget as the cap) has not been run.
- **The G10 chat template on the G5 model** (`--backend team5`). `results/effort_probe.md` says this waits for the G5 bundle; the Qwen and OLMoE runs use each model's own template.
- **Tool/agentic (20), Indic (15) and general (10) slots.** 45 of the 100 slots are unavailable, with the reason in the manifest.
- **Whether a label above 1k changes behaviour when the cap allows it.** Every Stage A and Stage B run uses a 1024 cap for all four labels. Only the code arm was re-run at 2048 (`results/attainability_survey_code2048.md`, Qwen stand-in); math was not.
- **Code ability of Qwen.** 195 of 240 code cells hit the cap, so the code numbers are a floor (Qwen report).
- `results/effort_probe.md` is dated 11 Nov and says no model had generated anything for the suite. The Stage B report is later. Read the two together.

## Open items stated in the results (status as of 20 Nov 2026)

- **Closed:** RL v1 drops all 55 resolved v1 effort-suite tasks before training (`results/rl_data_v1_close.md`, section 2: 55 listed, 55 excluded from both the 3,577 code pool and the 7,209 reserved MATH part; `capstone/rl_job_v1.py` asserts zero overlap).
- **Closed:** `rl-math-hendrycks` (`EleutherAI/hendrycks_math`, MIT, train split only) is recorded in `licences/licence_table.md` (`TSAI reserves`, awaiting TSAI admission).
- **Open:** Stage C (decoupled generation cap) waits for a Team 10 chat-format checkpoint and TSAI's Gate 3 context-length decision; the 15 Indic slots remain unavailable pending human-written Indic sources.

## Reports

- [results/effort_probe.md](../results/effort_probe.md)
- [results/effort_stageB_qwen_2026-11-12/report.md](../results/effort_stageB_qwen_2026-11-12/report.md)
- [results/effort_stageB_olmoe_2026-11-12/report.md](../results/effort_stageB_olmoe_2026-11-12/report.md)
- [results/attainability_survey_code2048.md](../results/attainability_survey_code2048.md)
- [results/api_bank_nemotron_overlap.md](results/api_bank_nemotron_overlap.md)

## Proposed v2 manifest (20 Nov 2026, f20201351h-maker)

`effort_manifest_v2_proposed.json` (suite `g10-effort-dev-v2-proposed`) is a proposal. `effort_manifest.json` (v1) is byte-identical to before and stays the suite. v2 keeps v1's 55 resolved code and math slots as equal objects, resolves the 30 slots that v1 marked unavailable for tool use and general (20 API-Bank calls, 10 QASC questions) and leaves the 15 Indic slots unavailable with v1's reason. It becomes the suite only when the lead signs the two new rows in `licences/licence_table.md` and accepts it. This README states no rule for amending a frozen manifest; the proposal therefore changes no v1 file and carries its own `manifest_sha256`, computed by the same rule (`manifest_digest`).

- Slot choice: v1's rule and seed (`selection_seed` g10-effort-dev-v1): lowest sha256(seed:id); one slot per distinct QASC question; at most one API-Bank call per dialogue file and per API name (the set holds several near-identical dialogues for one API with the same gold call).
- Prompt text comes from the pinned sets only. A QASC prompt is the set's `formatted_question`. An API-Bank prompt is the set's API descriptions for every API in the dialogue, then the dialogue up to the gold call, in the rendering of the set's own `evaluator.py`. Harness instructions (`DEFAULT_INSTRUCTIONS` in `effort_suite.py`) live in code and are not in any hash.
- Checkers: `answer_key` (one letter A to H; rules in the docstring of `extract_answer_key`) and `api_call` (one bracket call, API name and every parameter equal to gold, extra or missing parameters fail). The set's own evaluator executes the call and tolerates per-API differences; this one is stricter.

```bash
python teams/10-post-training/eval/effort_suite.py build-v2-manifest --pins PINS.json --qasc-dir DIR/qasc --qasc-revision a34ba204eb9a33b919c10cc08f4f1c8dae5ec070 --apibank-dir DIR/api-bank --apibank-revision f30ccf22b4e2617fab32958d4c03f5c1f2e7dfcf --out teams/10-post-training/eval/effort_manifest_v2_proposed.json
EFFORT_V2_DATA=DIR python -m pytest teams/10-post-training/eval/test_effort_suite_v2.py -q -p no:cacheprovider
```

`DIR` holds `qasc/` and `api-bank/` in the layout of their upstream repositories; `PINS.json` maps each downloaded file's relative path to its sha256. Without `EFFORT_V2_DATA` the tests that read the pinned files are skipped.

What a cheap answer scores on the 30 new slots (numbers only, 20 Nov 2026):
- QASC, 10 slots: a constant letter scores between 0 and 5 of 10 (always E: 5, always A: 2). Ten slots cannot separate a weak model from a constant answer; read this category together with the others, not alone.
- API-Bank, 20 slots, 20 different APIs: naming the first API in the descriptions with no parameters scores 0 of 20, but the API name alone is right in 16 of 20 (13 prompts describe a single API). These slots measure filling the parameters from the dialogue more than choosing the tool.
- Four gold calls have a parameter whose value is text that itself contains quotes (a list written as a string). The set's `key='value'` rendering cannot express those; a Python-quoted string or a list literal with the same text form passes the checker.

Not checked: no model has been run on the 30 slots; the exact-match API checker has not been compared with the set's own executing evaluator; no human has read the 30 prompts for ambiguity (QASC distractors can be valid); overlap with the SFT and RL training data is recorded in the pull request, not here.

**Lead sign-off (20 Nov 2026, `saitej123`):**
1. **API-Bank (20 `tool_agentic` slots):** accepted for the v2 dev suite (`eval-only`, separate from Team 9's final benchmarks). Tool-schema and seed overlap with `Nemotron-SFT-Agentic-v2` is formally measured in [results/api_bank_nemotron_overlap.md](results/api_bank_nemotron_overlap.md): strict hard-decontamination policy strips matching seed dialogues from the SFT training mix, keeping all 20 eval slots pristine.
2. **QASC (10 `general` slots):** accepted as closed-form automated dev slots to be read alongside the other categories (never standalone, given the 0–5/10 constant-letter baseline above); a blinded human rubric for free-form prompts remains optional for Week 4.
3. **Licence rows:** `eval-general-qasc` (CC-BY-4.0) and `eval-tool-api-bank` (Apache-2.0) signed off in `licences/licence_table.md` as `allowed (G10 lead sign-off, 20 Nov 2026; eval-only, not training data)`. `effort_manifest.json` (v1) remains frozen and unchanged for Gate 3 comparisons; `effort_manifest_v2_proposed.json` is ready for Week 4 runs.
