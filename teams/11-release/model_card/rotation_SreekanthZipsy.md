# Model card rotation review: Evaluation

Rotation into the Release team. This file reviews the Evaluation row of [model_card_outline.md](model_card_outline.md) and marks each claim that has no evidence.

Checked on the current branch, which includes the rotation reviews merged so far.

The row says: "The benchmarks, and the scores that TSAI approves." The owner team is Evaluation. The status is empty. The Lead OK cell records an OK from the Evaluation lead.

The Evaluation section has no text yet, so this review checks the outline row and its evidence.

## R1: Claims in the row

| Claim | Evidence | Verdict |
|---|---|---|
| The section is empty, with no text yet | [model_card_outline.md](model_card_outline.md) shows the status as empty. The [model card folder](.) holds no Evaluation text. | Supported |
| The lab has a list of benchmarks cleared for evaluation | [benchmarks_v1.md](../../09-evaluation/benchmarks_v1.md), rows with Use "Evaluation" | Supported |
| The public weekly update names the cleared benchmarks | [first weekly update](../updates/2026-10-31_week1.md), Benchmarks section. The names match the Evaluation rows of benchmarks_v1.md. | Supported |
| Benchmarks with unclear or restricted licences stay internal | [benchmarks_v1.md](../../09-evaluation/benchmarks_v1.md), rows with Use "Internal only", and the licence decisions in its Decisions section | Supported |
| Benchmark items stay out of the public repository | [eval firewall](../../09-evaluation/firewall/eval_firewall.md), its first section, which states the rule. benchmarks_v1.md says internal-only items are never copied into the repository. | Supported as a rule. Compliance was not checked file by file. |
| Benchmark items are fingerprinted, so training data can be checked against them | [fingerprints v1](../../09-evaluation/fingerprints/v1/), [fingerprints v2](../../09-evaluation/fingerprints/v2/), and [decontamination check, #31](https://github.com/theschoolofai/era-v5-lab/pull/31) | Partly supported. The [eval firewall](../../09-evaluation/firewall/eval_firewall.md) names harness benchmarks that have no fingerprint rows. |
| The harness runs the cleared benchmarks on public models | [harness](../../09-evaluation/harness/), [code and Indic harness](../../09-evaluation/harness_code_indic/), [general comparison](../../09-evaluation/results/compare_v0.md) | Supported, for public models only |
| The harness matches published scores within the agreed limit | [rotation checks](../../09-evaluation/results/rotation_checks.md), [known failures](../../09-evaluation/results/known_failures.md) | Partly supported. Some code checks fail the agreed limit, and the known failures file records them as standing. |
| TSAI approved the freeze set and the block rule | [comment by TSAI on #357](https://github.com/theschoolofai/era-v5-lab/pull/357#issuecomment-6811765729): the freeze set and block rule are accepted as written. | Supported. This approves the rule, not any score. |
| TSAI allowed labelled diagnostic runs on lab checkpoints, with conditions | The same [comment by TSAI on #357](https://github.com/theschoolofai/era-v5-lab/pull/357#issuecomment-6811765729): the diagnostics decision is "yes", with conditions. | Supported. The known failures file still says this is pending, so it needs an update. |
| The Evaluation lead confirmed the row | [comment from the Evaluation lead](https://github.com/theschoolofai/era-v5-lab/pull/384#issuecomment-6829303755) on the outline review, #384 | Supported |
| TSAI approved the scores for the configuration freeze | The [Gate 2 update](../updates/gate2.md) has no Evaluation decision. The Evaluation proposal, [#357](https://github.com/theschoolofai/era-v5-lab/pull/357), is closed and holds rules, not approved scores. | No evidence |
| TSAI approved any score of our model for public text | No such decision is on main. | No evidence |
| Our model has scores that could be published | The [eval watcher job request](../../09-evaluation/jobs/2026-11-15-eval-watcher-dry-run-1.md) is on main. It waits for TSAI to approve a GPU slot. No result file is on main. | No evidence |

## R2: Claims with no public evidence

- **TSAI approved the scores for the configuration freeze.** The Gate 2 update has no Evaluation decision. Until TSAI approves a score, the text must read `[number: waiting for TSAI]`.
- **TSAI approved any score of our model.** No such score is approved on main.
- **Our model has scored results.** The eval watcher job waits for TSAI's GPU approval. No result file is on main.
- **Every harness benchmark has fingerprint coverage.** The eval firewall names harness benchmarks without fingerprint rows. Any score on those tasks must say that the task was not decontaminated. This claim is only partly supported.

## Notes

- **Conflicting records on diagnostics.** The [known failures](../../09-evaluation/results/known_failures.md) file says TSAI's confirmation is pending. TSAI's comment on #357 says yes, with conditions. The known failures file should be updated to match TSAI's comment.
- **Scope of the lead OK.** The outline OK covers the row. The [week 2 review record](../updates/week2.md) marks the Evaluation text of that update as not yet OK. So the outline OK does not cover that update text.
- **Gate 2 gap.** The Gate 2 draft has an Evaluation decision row for the configuration freeze scores. The published [Gate 2 update](../updates/gate2.md) does not. The Release lead should confirm whether TSAI decided that item.
- **Benchmark list.** The first weekly update lists only the cleared benchmarks. It does not list the internal-only ones. Keep it that way in the model card.

## Suggestions for the owner team

1. Name only the benchmarks with Use "Evaluation" in the section text.
2. Write no score until TSAI approves it. Use `[number: waiting for TSAI]` in its place.
3. Say which benchmarks have no fingerprint coverage, and mark any score on them as not decontaminated.
4. Record TSAI's decision on the Gate 2 scores in the public Gate 2 update.
