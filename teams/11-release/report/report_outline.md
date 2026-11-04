# ERA V5 Lab: run report outline

**Date:** 3 Nov 2026
**Owner of this outline:** Release

The run report is the long public document that explains how the lab built and trained the model.
The V4 run report (https://lightninglm.theschoolofai.in/) is the model for its shape.
This file lists the sections of the run report.
Each section has an owner team and a status.

## How to use this outline

- The owner team writes the text of its section.
- Release edits the text for style and runs `check_style.py` on it.
- TSAI approves the text before it goes into the run report.
- A section can have more than one owner team. The first team named leads the section.

**Status** is one of these:

- **empty:** nobody has written the text yet.
- **in progress:** the owner team is writing the text.
- **approved:** TSAI approved the text.

## Sections

| Section | Owner team | Status |
|---|---|---|
| Abstract | Release | empty |
| Introduction | Release, Data B, Evaluation | empty |
| Background and Related Work | Release, Data A, Tokenizer, KE2, Architecture, Post-training | empty |
| Training Data | Data A, Data B, Evaluation | empty |
| Tokenizer | Tokenizer | empty |
| KE2 | KE2 | empty |
| Model Design | Architecture | empty |
| Training Speed and Correctness | Performance, KE2 | empty |
| Training Infrastructure | Infrastructure | empty |
| Monitoring the Training Run | Monitoring | empty |
| The Training Run | Infrastructure, Data A, Architecture, Monitoring | empty |
| What Went Wrong and How We Fixed It | Monitoring, Infrastructure | empty |
| Post-training | Post-training | empty |
| Quantization and Serving | Quantization | empty |
| Results | Evaluation, Quantization | empty |
| Limitations | Evaluation, Release | empty |
| Reproducibility | Release, Architecture, Infrastructure | empty |
| Licence and Attribution | Post-training, Data A, Data B | empty |
| Conclusion | Release | empty |
| Contributors and Acknowledgments | Release | empty |
| Resources and Citation | Release | empty |

## Rules for every section

- Write only about work that is done. Do not promise dates, sizes or results.
- Write `[number: waiting for TSAI]` in place of any number that TSAI has not approved.
- Name a person only if they signed the consent form.
- Follow `teams/11-release/style/style_guide.md`.
