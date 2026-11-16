# Licence table

`licence_table.md` is the one shared G10 file for the SFT and RL datasets we considered. It has three stages: foundation data (Stage 0), supervised fine-tuning (Stage 1) and preference optimization and RLVR (Stage 2). Each set has one summary row (set, source, language, licence and decision, plus the generator model in Stages 1 and 2). Most sets also have a detail entry with the licence read on a stated date, the generator model, the decision and an opinion.

Decisions used in the table:

| Decision | Meaning |
|---|---|
| `TSAI reserves` | The final decision is TSAI's. It is the default for a set that is not excluded, and many entries note which TSAI rules the set passes. |
| `allowed` | TSAI ruled it in (for example CC-BY-SA with attribution, or the SWE environments). |
| `excluded` | Out of every training mix, with the reason in the entry (non-commercial licence, text made by closed OpenAI or Anthropic models, a Llama or custom licence, unstated licence or generator, or sources we cannot trace). |
| `needs TSAI decision` | A question only TSAI can answer, written in the entry. |

A Hugging Face tag is not legal clearance. `sft/convert.py` reads this table and refuses any set that is `excluded` or missing. `tests/test_licence_table_week2_sets.py` checks five Week 2 rows and that set ids are unique.

To add a set, add a summary row in the right stage and a detail entry in the same format, and open a pull request to the lead's branch.

## Gate

Week 1 deliverable "Licence table and strategy v0" (plan sheet, 24 to 31 Oct). Rows have been added and revised since, for example the RL and SWE rows dated 4, 6 and 11 Nov.

## What has been measured

Nothing. This is a record of licences, generators and decisions, not a measurement. Other files in the folder tree cite it (`sft/sft_mix_proposal.md`, `sft/decontam_report.md`, `docs/eligibility_ledger.md`).

## What has not been done

- No row-level licence audit of any set. `docs/eligibility_ledger.md` says it does not audit CommitPackFT row or repository licences.
- No licence-table row for hendrycks MATH, which `eval/effort_manifest.json` uses (`results/effort_probe.md` records the gap).
- Many Stage 1 sets are still `TSAI reserves`. A `TSAI reserves` set is not approved for training.

## Reports

- [docs/eligibility_ledger.md](../docs/eligibility_ledger.md) reads this table together with the decontamination report.
