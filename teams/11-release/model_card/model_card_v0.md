# ERA V5 Lab: model card

**Date:** [date: waiting for TSAI]

## Overview

The ERA V5 lab of The School of AI (TSAI) builds and trains its own language model. Students of the lab work in
teams, and each team owns one part of the work. The work is in a public repository, so anyone can follow it.

[text: waiting for Release, what the model is]

## Intended use

[text: waiting for Post-training and Release]

## Languages

[text: waiting for Data A, Data B and Tokenizer]

## Training data

### The general text and code

[text: waiting for Data A]

### The Indian-language and code-adjacent text

Data B (the team for Indian-language and code-adjacent data) checked the Indian-language part of the training data.
It also checked the code-adjacent part: commit messages, notebooks and question-and-answer posts.

The Indian-language text comes from public collections: FineWeb-2, Sangraha, HPLT and IndicCorp. It covers Bengali,
Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Sanskrit, Tamil and Telugu. Sangraha has a verified part and a
synthetic part, which is machine-translated text.

The code-adjacent text comes from CommitPackFT, a public set of Kaggle notebooks, and Stack Exchange posts from the
StarCoder2 extra data.

Native readers read samples of each source. They labelled each document with a shared list of data problems. For each
language, the documents that both of their readers marked clean form a gold set. Data B uses the gold sets to test that
a cleaning rule does not harm good text.

The readers found these problems:

- The share of clean documents depends strongly on the source. The machine-translated part of Sangraha has the fewest
  clean documents of all the sources.
- Telugu has the least clean text of the languages that a second reader also checked.
- Native readers rated the machine-translated text. No language reached the quality bar that Data B proposed, so the
  native Indian-language share of the mix leaves translated text out.
- Romanised Indian-language text, an Indian language written in Latin letters, is rare in the samples. The mix caps it
  at 1% of the tokens of each language.
- Malayalam and Odia had no second reader, so Data B could not measure their clean share.

[text: waiting for Data B, the problems in the code-adjacent text]

Indian scripts break easily. Data B looked for invisible characters, text in the wrong script, words cut before a vowel
sign, and lost joiner characters (ZWJ and ZWNJ). In the cleaned training shards, no joiner was lost from the text that
cleaning kept.

Text in Indian languages, in their own scripts, is 8% of every training batch.

## Data cleaning

[text: waiting for Data A and Data B]

## Tokenizer

[text: waiting for Tokenizer]

## KE2

[text: waiting for KE2]

## Architecture

[text: waiting for Architecture]

## Training

[text: waiting for Performance and Architecture]

## Training infrastructure

[text: waiting for Infrastructure]

## Compute

[text: waiting for Infrastructure, after TSAI approves the numbers]

## Monitoring

[text: waiting for Monitoring]

## Post-training

[text: waiting for Post-training]

## Alignment

[text: waiting for Post-training]

## Quantized versions

[text: waiting for Quantization]

## Serving

[text: waiting for Quantization]

## Evaluation

Evaluation tests the model on public benchmarks, and keeps benchmark items out of the training text. During
training, Evaluation scores each checkpoint, a saved copy of the model, on a small set of benchmark questions. These
scores do not come from the full benchmarks.

During training, Evaluation uses the benchmarks MMLU and MILU. MMLU has questions on school and professional subjects,
such as mathematics, history and law, in English. MILU has questions from Indian exams on many subjects, including
Indian history, arts and laws. Evaluation uses its questions in Hindi, Telugu, Tamil and Bengali. Each question has
answer choices, and the answer of the model is the choice that it rates most likely.

| Benchmark | What it tests | Score | Score of a random guess | Training step |
|---|---|---|---|---|
| MMLU | School and professional subjects, in English | [number: waiting for TSAI] | [number: waiting for TSAI] | [number: waiting for TSAI] |
| MILU (Hindi) | Subjects from Indian exams, in Hindi | [number: waiting for TSAI] | [number: waiting for TSAI] | [number: waiting for TSAI] |
| MILU (Telugu) | Subjects from Indian exams, in Telugu | [number: waiting for TSAI] | [number: waiting for TSAI] | [number: waiting for TSAI] |
| MILU (Tamil) | Subjects from Indian exams, in Tamil | [number: waiting for TSAI] | [number: waiting for TSAI] | [number: waiting for TSAI] |
| MILU (Bengali) | Subjects from Indian exams, in Bengali | [number: waiting for TSAI] | [number: waiting for TSAI] | [number: waiting for TSAI] |

Each score is in points out of 100. The check of the training text covers both benchmarks. Every file of training
text is checked against their questions before training reads it.

## Limitations and risks

[text: waiting for Evaluation and Release]

## Licence and attribution

[text: waiting for Post-training, Data A and Data B]

## Contributors

These teams of the ERA V5 lab do the work. TSAI approves each decision before the lab acts on it.

- **Data A** cleans the training text, removes duplicates and packs the text into files for training.
- **Data B** reads Indian-language and code-adjacent text with native readers, and proposes how much of each kind
  goes into training.
- **Tokenizer** builds the tokenizer, which splits text into the pieces that the model reads.
- **KE2** tests its embedding method on the lab's tokenizer.
- **Architecture** sets the shape of the model and its training settings.
- **Performance** makes each training step faster, and tests that each fast part matches a high-precision
  reference.
- **Infrastructure** runs the training jobs, checks the health of the machines, and saves the work so that a run
  can restart after a crash.
- **Monitoring** watches the training run, raises alarms and builds the public dashboard.
- **Evaluation** tests the model on public benchmarks and keeps benchmark items out of the training text.
- **Post-training** tunes the model after its main training, for example to chat in the lab's chat format.
- **Quantization** makes smaller versions of the model for serving, and checks them against the full model.
- **Release** writes the public text of the lab: the weekly updates, the dashboard text, the model card and the
  run report.

## How to find more

The public lab repository holds the work of every team: https://github.com/theschoolofai/era-v5-lab

---

## Review record (remove this section before publishing)

This record is public, like the rest of the pull request. Put only public facts in it: yes or no, and links to
public pull requests. Never link to the CAP chat. Chat links are internal.

This is the first draft of the model card. The sections follow `model_card_outline.md`, which names the owner team of
each section.

How to fill it:

1. The owner team writes the text of its section, in its own folder or in a pull request comment.
2. Release pastes the text into its section and edits it only for style. Release sends the edit back to the writer.
3. The lead of each owner team gives an OK on the text in a pull request comment (`OK @handle`).
4. Write `[number: waiting for TSAI]` for any number that TSAI has not approved yet.
5. Run `python teams/11-release/style/check_style.py <this file> --numbers` and clear every error.
6. Update the status of the section in `model_card_outline.md`.
7. TSAI approves this pull request before the G11 lead merges it.

| Section | Owner team | Text in this draft | Source | Lead OK |
|---|---|---|---|---|
| Overview | Release | who made the model: yes. What the model is: no | `launch/launch_announcement_v0.md` ([#600](https://github.com/theschoolofai/era-v5-lab/pull/600), [#603](https://github.com/theschoolofai/era-v5-lab/pull/603)) | yes (the Release lead wrote this draft) |
| Training data: the Indian-language and code-adjacent text | Data B | yes, with no edit. The problems in the code-adjacent text: no, Data B adds them later | `teams/02-data-b/model_card/training_data.md` ([#525](https://github.com/theschoolofai/era-v5-lab/pull/525)). Its source table gives the TSAI approval of each number | Data B: yes ([comment on #759](https://github.com/theschoolofai/era-v5-lab/pull/759#issuecomment-7108567909)) |
| Training data: the general text and code | Data A | no | waiting for Data A | Data A: no |
| Licence and attribution | Post-training, Data A, Data B | no | waiting for the Post-training text. Facts so far: `teams/10-post-training/licences/licence_table.md`. MILU is under CC BY 4.0, so this section credits its authors ([comment on #770](https://github.com/theschoolofai/era-v5-lab/pull/770#issuecomment-7123142597)) | no |
| Evaluation | Evaluation | what Evaluation does: yes, from text that TSAI approved. The benchmarks, the table rows and the check of the training text: yes, from the Evaluation lead, with no edit. The scores: no, TSAI approves each score. Before a score from an early step goes in, check with Evaluation, because early scores can be above a random guess without any learning | the Evaluation line of `launch/launch_announcement_v0.md` ([#753](https://github.com/theschoolofai/era-v5-lab/pull/753)); the Eval-Mini panel text in `dashboard/dashboard_text_new_panels.md` and the format in `dashboard/score_text_format.md` ([#760](https://github.com/theschoolofai/era-v5-lab/pull/760)). Benchmarks and table rows: [comment on #770](https://github.com/theschoolofai/era-v5-lab/pull/770#issuecomment-7123142597). Plan: `teams/09-evaluation/eval_schedule.md` | Evaluation: yes ([comment on #770](https://github.com/theschoolofai/era-v5-lab/pull/770#issuecomment-7121407240)); the Evaluation lead sent the benchmark text |
| Contributors | Release | yes | `launch/launch_announcement_v0.md` ([#600](https://github.com/theschoolofai/era-v5-lab/pull/600), [#603](https://github.com/theschoolofai/era-v5-lab/pull/603)) | yes (the Release lead wrote this draft) |
| How to find more | Release | yes | the public lab repository | yes (the Release lead wrote this draft) |
| Every other section | the owner team in `model_card_outline.md` | no | waiting for the owner team | no |

- [ ] `check_style.py` gives 0 errors
- [ ] Every number in the text has TSAI approval
- [ ] The text names teams only, and no person
- [ ] Nothing from the internal list in `public_internal.md`
- [ ] No `waiting for` placeholder left in the text
- [ ] A team member commented on this pull request
- [ ] TSAI approved on: [DD Mon YYYY]
- [ ] Merged after TSAI approved
