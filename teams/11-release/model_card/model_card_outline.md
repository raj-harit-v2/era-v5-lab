# ERA V5 Lab: model card outline

**Date:** 3 Nov 2026
**Owner of this outline:** Release

The model card is the public document that describes the model and how the lab made it.
This file lists the sections of the model card.
Each section has an owner team and a status.

## How to use this outline

- The owner team writes the text of its section.
- Release edits the text for style and runs `check_style.py` on it.
- TSAI approves the text before it goes into the model card.
- A section can have more than one owner team. The first team named leads the section.

**Status** is one of these:

- **empty:** nobody has written the text yet.
- **in progress:** the owner team is writing the text.
- **approved:** TSAI approved the text.

## Sections

| Section | What it says | Owner team | Status |
|---|---|---|---|
| Overview | What the model is and who made it, in plain words | Release | empty |
| Intended use | What the model is for, and what it is not for | Post-training, Release | empty |
| Languages | The languages the model reads and writes | Data A, Data B, Tokenizer | empty |
| Training data | The public data sources, and the problems we found in them | Data A, Data B | empty |
| Data cleaning | How we cleaned the data and removed duplicates | Data A, Data B | empty |
| Tokenizer | How the model splits text into pieces | Tokenizer | empty |
| KE2 | Whether the model uses KE2, in general terms, with no design details | KE2 | empty |
| Architecture | The shape of the model, in general terms | Architecture | empty |
| Training | How the lab trained the model | Performance, Architecture | empty |
| Training infrastructure | How the run saves, restores and restarts after a crash | Infrastructure | empty |
| Compute | The hardware and the training time, once TSAI approves the numbers | Infrastructure | empty |
| Monitoring | How the lab watched the training run and kept a record of it | Monitoring | empty |
| Post-training | How the lab tuned the model after pre-training | Post-training | empty |
| Quantized versions | The smaller versions of the model, and what they lose | Quantization | empty |
| Evaluation | The benchmarks, and the scores that TSAI approves | Evaluation | empty |
| Limitations and risks | What the model gets wrong, and the known risks | Evaluation, Release | empty |
| Licence and attribution | The licence of the model, and credit for each data source | Post-training | empty |
| Contributors | The teams, and the names of people who signed the consent form | Release | empty |
| How to find more | A link to the public lab repository | Release | empty |

## Rules for every section

- Write only about work that is done. Do not promise dates, sizes or results.
- Write `[number: waiting for TSAI]` in place of any number that TSAI has not approved.
- Name a person only if they signed the consent form.
- Follow `teams/11-release/style/style_guide.md`.
