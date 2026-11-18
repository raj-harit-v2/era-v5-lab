# Rotation check: model card, Training row

**Date:** 17 Nov 2026

Week 3 rotation in the Release team. This file reviews the Training row of `model_card_outline.md` (R1) and marks each claim that has no evidence (R2).

Checked against main at commit `8de78ec`.

The Training section has no text yet, so this review covers the current outline row and its evidence.

## R1: review of the Training row

The row says: "How the lab trained the model."
The owner teams are Performance and Architecture. The status is empty. The Lead OK cell records an OK from each owner team.

### What the evidence supports

- Both owner teams work on training. The Architecture team owns the model settings in `config_v1.yaml`, approved at Gate 2 in #443. The Performance team times and profiles the training step.
- Both teams have filed dry run 1 jobs: the Architecture job `teams/05-architecture/jobs/2026-11-15-dryrun1.md`, and the Performance jobs in #485, #486, #492 and #496.
- The Performance lead approves the Performance dry run 1 jobs, as their "Lead approval" lines show. This matches the Release lead's note on #281 that this lead now leads Performance.
- The status "empty" is correct. No Training section text is on main.

### What the evidence does not support yet

- **How the lab trained the model.** The lab has not trained the model yet. Dry run 1 has finished ([TSAI comment on #475](https://github.com/theschoolofai/era-v5-lab/pull/475#issuecomment-6909031441)), but it is a short test, not the main training run. The outline rule says to write only about work that is done.
- **Training settings.** The learning rate in `config_v1.yaml` is provisional and holds for short test runs at the smallest test size only (`teams/05-architecture/decisions.md`). It is not the setting of the main training run.
- **Numbers.** Most facts about training are numbers, such as steps, tokens, learning rate and time. TSAI has approved none of them for public text.

### Suggestions for the owner teams

1. Keep the status "empty" until the main run has results.
2. Write the section only from finished runs, with a link to each result.
3. Write `[number: waiting for TSAI]` for every number that TSAI has not approved.
4. Do not write the provisional test learning rate as the training setting.
5. Agree with Infrastructure where Training ends and "Training infrastructure" and "Compute" begin, so that no fact appears in two sections.

## R2: claims and evidence

| # | Claim | Evidence | Result |
|---|---|---|---|
| 1 | The owner teams are Performance and Architecture | `model_card_outline.md` on main. Both teams have filed dry run 1 jobs | has evidence |
| 2 | The status is empty | No Training section text is on main | has evidence |
| 3 | The Performance lead confirmed the row | A comment from the Performance lead on #355, recorded in the outline by #384. The Release lead's review on #281 names this lead as the Performance lead | has evidence |
| 4 | The Architecture lead confirmed the row | The Release lead's review on #281 says the Architecture lead confirmed in the lab chat. The repository does not link that chat (`public_internal.md`). No public comment from that lead names this row | no public evidence |
| 5 | The lab trained the model | Dry run 1 has finished ([TSAI comment on #475](https://github.com/theschoolofai/era-v5-lab/pull/475#issuecomment-6909031441)). It is a short test, not the main training run | no evidence |
| 6 | The training settings are known | `config_v1.yaml` sets a provisional learning rate for short test runs only. The model size is empty in config v1 | no evidence for the main run |
| 7 | Any number about training | TSAI has approved none for public text | no evidence. Write `[number: waiting for TSAI]` |

## No evidence

- Claim 4: the Architecture lead's OK has no public source. The Release lead recorded it from the lab chat.
- Claim 5: dry run 1 has finished, but it is a short test, not the main training run. Evidence comes when the main run has results.
- Claim 6: no setting for the main run is final. Evidence comes when TSAI approves the setting.
- Claim 7: no number is approved. Evidence comes when TSAI approves each number.
