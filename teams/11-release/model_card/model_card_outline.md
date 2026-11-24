# ERA V5 Lab: model card outline

**Date:** 3 Nov 2026
**Owner of this outline:** Release

The model card is the public document that describes the model and how the lab made it.
This file lists the sections of the model card.
Each section has an owner team, a status and a lead confirmation.

## How to use this outline

- The owner team writes the text of its section.
- Release edits the text for style and runs `check_style.py` on it.
- TSAI approves the text before it goes into the model card.
- A section can have more than one owner team. The first team named leads the section.

**Status** is one of these:

- **empty:** nobody has written the text yet.
- **in progress:** the owner team is writing the text.
- **approved:** TSAI approved the text.

**Lead OK** tracks whether the lead of each owner team confirmed the section and its scope.
Write `pending` until they confirm. Then write `OK` and the GitHub handle of each lead who confirmed.
For a shared section, name each owner team, for example `Data A OK @handle; Data B pending`.
This confirms the outline only. TSAI still approves the final text.

The draft of the model card is `model_card_v0.md`. Each section there has the text received so far.

## Sections

| Section | What it says | Owner team | Status | Lead OK |
|---|---|---|---|---|
| Overview | What the model is and who made it, in plain words | Release | in progress | Release OK @pyru |
| Intended use | What the model is for, and what it is not for | Post-training, Release | empty | Post-training OK @saitej123; Release OK @pyru |
| Languages | The languages the model reads and writes | Data A, Data B, Tokenizer | empty | Data A OK @patilvijay23; Data B OK @shankarpandala; Tokenizer OK @rjvim |
| Training data | The public data sources, and the problems we found in them | Data A, Data B | in progress | Data A OK @patilvijay23; Data B OK @shankarpandala |
| Data cleaning | How we cleaned the data and removed duplicates | Data A, Data B | empty | Data A OK @patilvijay23; Data B OK @shankarpandala |
| Tokenizer | How the model splits text into pieces | Tokenizer | empty | OK @rjvim |
| KE2 | Whether the model uses KE2, in general terms, with no design details. This includes the KE2 output head, which replaced the dense untied head on 21 Nov 2026 | KE2 | empty | pending |
| Architecture | The shape of the model, in general terms | Architecture | empty | OK @shivman |
| Training | How the lab trained the model | Performance, Architecture | empty | Performance OK @raj-harit-v2; Architecture OK @shivman |
| Training infrastructure | How the run saves, restores and restarts after a crash | Infrastructure | empty | pending |
| Compute | The hardware and the training time, once TSAI approves the numbers | Infrastructure | empty | pending |
| Monitoring | How the lab watched the training run and kept a record of it | Monitoring | empty | OK @sandeepkunkunuru |
| Post-training | How the lab tuned the model after pre-training | Post-training | empty | OK @saitej123 |
| Alignment | How the lab trained the model on checked scores of its own answers, and how it scores tasks with no test | Post-training | empty | OK @saitej123 |
| Quantized versions | The smaller versions of the model, and what they lose | Quantization | empty | OK @SreekanthZipsy |
| Serving | How to run the model and chat with it in the lab's chat format, and how the smaller formats were checked against the full model | Quantization | empty | OK @SreekanthZipsy |
| Evaluation | The benchmarks, and the scores that TSAI approves | Evaluation | in progress | OK @rahulni |
| Limitations and risks | What the model gets wrong, and the known risks | Evaluation, Release | empty | Evaluation OK @rahulni; Release OK @pyru |
| Licence and attribution | The licence of the model, and credit for each data source | Post-training, Data A, Data B | empty | Post-training OK @saitej123; Data A OK @patilvijay23; Data B OK @shankarpandala |
| Contributors | The teams that did the work, with no person names | Release | in progress | Release OK @pyru |
| How to find more | A link to the public lab repository | Release | in progress | Release OK @pyru |

## Changes to this outline

- 21 Nov 2026: TSAI chose the KE2 output head in place of the dense untied head
  (`teams/04-ke2/gate3.md`, [#694](https://github.com/theschoolofai/era-v5-lab/pull/694)). The KE2 section now covers the output head too, in
  general terms. The KE2 lead confirms the new scope in the Lead OK column. The Gate 3 update records the decision.

## Rules for every section

- Write only about work that is done. Do not promise dates, sizes or results.
- Write `[number: waiting for TSAI]` in place of any number that TSAI has not approved.
- Name teams only. Do not name any person.
- Follow `teams/11-release/style/style_guide.md`.
