# API-Bank / Nemotron-SFT-Agentic-v2 Overlap Audit (Effort Suite v2)

**Date:** 23 Nov 2026  
**Schema:** `g10-api-bank-overlap/1`  
**Target Evaluation Suite:** `eval/effort_manifest_v2_proposed.json` (20 `tool_agentic` slots)  
**Training Set Evaluated:** `nvidia/Nemotron-SFT-Agentic-v2 (tool-calling part)`  
**Policy (G10 Lead & User Directive):** **Strict Hard-Decontamination** (purge colliding seed instances from training mix; keep evaluation slots pristine).  

---

## 1. Executive Summary & Provenance Audit

In `licences/licence_table.md` (§370), `Nemotron-SFT-Agentic-v2` (tool-calling part) explicitly names **API-Bank** as one of its seed toolsets alongside UltraTool, ToolEyes, AutoTools, Glaive v2, and Toucan-1.5M. Because synthetic dialogue teachers (DeepSeek-V3.2 and GLM-4.6) simulated tool-use trajectories over these seed schemas, any evaluation on API-Bank faces direct schema and prompt collision risks.

| Audit Dimension | Metric / Status | Implication |
| :--- | :--- | :--- |
| **Proposed Eval Slots** | 20 slots (`tool_agentic-00` to `tool_agentic-19`) | Selected across 20 distinct APIs from API-Bank Level 1. |
| **Seed Ingestion Status** | Confirmed (Declared in NVIDIA dataset card) | High risk of training on simulated variants of these APIs. |
| **Decontamination Gate** | **Strict Hard-Decontamination** | Zero-tolerance for training on evaluation APIs or dialogues. |
| **Remediation Action** | Purge matching training rows from SFT mix | Reserves all 20 API-Bank evaluation scenarios as clean held-out tests. |

---

## 2. Slot-by-Slot Audit Breakdown

| Slot | Task ID | API Name | Seed Category | Schema Risk | Decontamination Action |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `tool_agentic-00` | `apibank/QueryReminder-level-1-1.jsonl#5` | `QueryReminder` | reminder | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing QueryReminder or its schema; Retain slot tool_agentic-00 as clean held-out test instance in effort v2. |
| `tool_agentic-01` | `apibank/AddAlarm-level-1-1.jsonl#8` | `AddAlarm` | alarm | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing AddAlarm or its schema; Retain slot tool_agentic-01 as clean held-out test instance in effort v2. |
| `tool_agentic-02` | `apibank/RegisterUser-level-1-2.jsonl#7` | `RegisterUser` | account | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing RegisterUser or its schema; Retain slot tool_agentic-02 as clean held-out test instance in effort v2. |
| `tool_agentic-03` | `apibank/Dictionary-level-1-3.jsonl#2` | `Dictionary` | reference | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing Dictionary or its schema; Retain slot tool_agentic-03 as clean held-out test instance in effort v2. |
| `tool_agentic-04` | `apibank/ModifyMeeting-level-1-1.jsonl#9` | `ModifyMeeting` | calendar | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing ModifyMeeting or its schema; Retain slot tool_agentic-04 as clean held-out test instance in effort v2. |
| `tool_agentic-05` | `apibank/TimedSwitch-level-1-2.jsonl#5` | `TimedSwitch` | iot | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing TimedSwitch or its schema; Retain slot tool_agentic-05 as clean held-out test instance in effort v2. |
| `tool_agentic-06` | `apibank/Translate-level-1-1.jsonl#2` | `Translate` | language | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing Translate or its schema; Retain slot tool_agentic-06 as clean held-out test instance in effort v2. |
| `tool_agentic-07` | `apibank/GetMeeting-level-1-1.jsonl#5` | `GetMeeting` | calendar | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing GetMeeting or its schema; Retain slot tool_agentic-07 as clean held-out test instance in effort v2. |
| `tool_agentic-08` | `apibank/BookHotel-level-1-4.jsonl#11` | `BookHotel` | hospitality | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing BookHotel or its schema; Retain slot tool_agentic-08 as clean held-out test instance in effort v2. |
| `tool_agentic-09` | `apibank/OpenBankAccount-level-1-3.jsonl#8` | `OpenBankAccount` | banking | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing OpenBankAccount or its schema; Retain slot tool_agentic-09 as clean held-out test instance in effort v2. |
| `tool_agentic-10` | `apibank/CancelRegistration-level-1-3.jsonl#2` | `CancelRegistration` | account | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing CancelRegistration or its schema; Retain slot tool_agentic-10 as clean held-out test instance in effort v2. |
| `tool_agentic-11` | `apibank/DocumentQA-level-1-1.jsonl#3` | `DocumentQA` | search | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing DocumentQA or its schema; Retain slot tool_agentic-11 as clean held-out test instance in effort v2. |
| `tool_agentic-12` | `apibank/ModifyAgenda-level-1-2.jsonl#9` | `ModifyAgenda` | calendar | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing ModifyAgenda or its schema; Retain slot tool_agentic-12 as clean held-out test instance in effort v2. |
| `tool_agentic-13` | `apibank/DeleteScene-level-1-3.jsonl#2` | `DeleteScene` | iot | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing DeleteScene or its schema; Retain slot tool_agentic-13 as clean held-out test instance in effort v2. |
| `tool_agentic-14` | `apibank/CancelTimedSwitch-level-1-2.jsonl#6` | `CancelTimedSwitch` | iot | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing CancelTimedSwitch or its schema; Retain slot tool_agentic-14 as clean held-out test instance in effort v2. |
| `tool_agentic-15` | `apibank/SymptomSearch-level-1-2.jsonl#4` | `SymptomSearch` | medical | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing SymptomSearch or its schema; Retain slot tool_agentic-15 as clean held-out test instance in effort v2. |
| `tool_agentic-16` | `apibank/QueryScene-level-1-1.jsonl#2` | `QueryScene` | iot | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing QueryScene or its schema; Retain slot tool_agentic-16 as clean held-out test instance in effort v2. |
| `tool_agentic-17` | `apibank/GetReminder-level-1-1.jsonl#6` | `GetReminder` | reminder | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing GetReminder or its schema; Retain slot tool_agentic-17 as clean held-out test instance in effort v2. |
| `tool_agentic-18` | `apibank/RecordHealthData-level-1-1.jsonl#3` | `RecordHealthData` | health | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing RecordHealthData or its schema; Retain slot tool_agentic-18 as clean held-out test instance in effort v2. |
| `tool_agentic-19` | `apibank/DeleteMeeting-level-1-1.jsonl#8` | `DeleteMeeting` | calendar | **high_seed_origin** | Exclude any Nemotron-SFT-Agentic-v2 training rows referencing DeleteMeeting or its schema; Retain slot tool_agentic-19 as clean held-out test instance in effort v2. |

---

## 3. Training Mix Hard-Decontamination Directive

To ensure zero benchmark contamination for Gate 4 and Effort v2:
1. **Training Mask:** When assembling `sft-agentic-nemotron-sft-agentic-v2-tool-calling`, apply an exclusion mask removing any dialogue whose tools match the 20 audited API-Bank endpoints:
   - `QueryReminder`, `AddAlarm`, `RegisterUser`, `Dictionary`, `ModifyMeeting`, `TimedSwitch`, `Translate`, `GetMeeting`, `BookHotel`, `OpenBankAccount`, `CancelRegistration`, `DocumentQA`, `ModifyAgenda`, `DeleteScene`, `CancelTimedSwitch`, `SymptomSearch`, `QueryScene`, `GetReminder`, `RecordHealthData`, `DeleteMeeting`.
2. **Eval Protection:** Lock all 20 slots in `effort_manifest_v2_proposed.json` as permanent held-out evaluation tasks.
3. **CI / Unit Guard:** Enforce `test_api_bank_overlap.py` in the pre-merge verification pipeline.
