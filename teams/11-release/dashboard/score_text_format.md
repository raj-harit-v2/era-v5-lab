# Public text format for benchmark scores

**Date:** 24 Nov 2026

Evaluation gives Release the benchmark names and the score format on 26 Nov. Release gives its own format first
(`teams/09-evaluation/eval_schedule.md`, section 1). This file is that format: how Release writes benchmark scores in
public text. It covers the panel "Eval-Mini Scores Alongside Training Loss" in `dashboard_text_new_panels.md`, and
the Evaluation section of the model card.

Evaluation's score format is eval-mini v1 (`teams/09-evaluation/results/eval_mini_v1_schema.md`). Release reads only
the records marked `primary`.

## Rules for public text

These rules come from `public_internal.md` and from the Release review of the Evaluation row of the model card
(`model_card/rotation_SreekanthZipsy.md`). Section 11 of the Evaluation schedule repeats them.

1. Name only the benchmarks that Evaluation gives Release. Use the name that the authors of the benchmark use.
2. Write no score until TSAI approves it. Write `[number: waiting for TSAI]` in its place.
3. Say which benchmarks have no fingerprint check. Mark each score on them as not checked for benchmark items in the
   training text.

## How each score looks (Release proposal)

4. Give each score in points out of 100, as eval-mini v1 does, and round it to one decimal place. The dashboard
   panel uses the same unit.
5. Give the training step of the checkpoint that each score comes from.
6. Say that the scores come from a small set of benchmark questions, not from the full benchmark.
7. If a benchmark has answer choices, give the score of a random guess next to the score of the model. Gate 4
   expects scores near random at the start of the run, so readers need that line.

An example with no real number:

> At training step [number: waiting for TSAI], the model scored [number: waiting for TSAI] points out of 100 on
> [benchmark: waiting for Evaluation]. A random guess scores [number: waiting for TSAI] points on it.

## What Release needs from Evaluation on 26 Nov

For each benchmark that can appear in public text:

| What | Why Release needs it |
|---|---|
| The public name, and a link to the public page of the benchmark | The name in the text, and a source for the glossary |
| One plain sentence on what it tests, such as "science questions for school students, with answer choices" | The glossary |
| Its language or subject: English, an Indian language, or code | Text that groups the scores |
| What the score counts, in plain words, such as "the share of questions answered right" | The meaning of each score |
| The score of a random guess, if the benchmark has answer choices | Rule 7 |
| Whether the fingerprint check covers it | Rule 3 |

Evaluation and Monitoring: please say in the pull request if rules 4 to 7 do not work for you.
