# Attention comparison: T2, five designs, three seeds

REQUEST FOR LEAD/TSAI REVIEW. No lead approval or official run completion is claimed.

```text
Team:            05-architecture
Owner:           Revant Gupta (revantg)
Lead approval:   pending review by shivman
Question:        Which of the four approved attention alternatives passes its rule against the reference design at T2?
Script:          teams/05-architecture/harness/train_week2.py
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/t2.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1234 --out ./out/attn-0-1234
Config:          five existing attention configurations listed below
Inputs:          reuse the EXACT TSAI-staged training/held-out/source/checksum/report bundle used for official job #310; same tokenizer v0 and matching P32 raw table
Hardware:        1 GPU supporting native bf16
Max time:        1350 minutes total maximum for 15 runs; each run capped at 90 minutes
Precision:       bf16
Measures:        every held-out slice, three-group/code/Indic BPB, seeds, completed steps, finite losses, timeouts, quality eligibility, step times and allocated GPU memory
Expected result: per-design means and seed ranges; no winning design is assumed
Outputs:         each run's metrics.jsonl, manifest.json and summary.json only; total return <=50 MB; retain required checkpoints internally, do not return them
Test log:        evidence/2026-11-10-attention-screen/unit-tests.log (113 tests at the pinned execution source)
Notebook:        companion PR #344; source linked below (explicit controls, no training on open)
```

## Source and controls

Tested execution source: c1849c1b9dd11eec9ed1958c07deee173ca73265. Model/optimizer mathematics remain those of c9cac5a; the data-loader cache and CUDA sampler-resume repair are separately identified and tested. Revalidate if TSAI applies a different commit.
All five designs keep the approved T2 shape, context 2048, global batch 8,
16 routed + 1 shared expert, top-2, expert width 768, SwiGLU, dense untied head.
Use AdamW LR 0.001 as the current proposed/common fallback; comparison_final remains
false until the lead records the final LR decision. No additional LR sweep requested.

Use the approved runtime resolution and return its approval reference and actual
input hashes. Start from the current microbatch 1; TSAI may approve a different
fitting value consistently across all designs, recording that change.
Use the merged evaluation implementation. Any execution-only token-cache changes
must be identified in the returned source manifest and applied consistently.

The input names in the command define staging paths, not invented data identities.
Use the official #310 bundle; return actual checksums, source sidecar, decontamination
report, tokenizer/table identity and resolution identity. Do not substitute this
notebook's synthetic smoke input or the repository's older baseline-tokenizer table.

## Fifteen runs, in requested order

Run seed 1234 across the five designs first, then 1235, then 1236.
The reference is included so helper assignment and baseline sharing do not delay filing.
Lead/TSAI may deduplicate its three runs with the optimizer/expert comparisons only
if input/configuration/budget/source identities match.

| Design | Seed | Existing config | Separate output |
|---|---:|---|---|
| attn-0 | 1234 | t2.yaml | ./out/attn-0-1234/ |
| attn-1 | 1234 | attn1_mqa.yaml | ./out/attn-1-1234/ |
| attn-2 | 1234 | attn2_swa128_sink.yaml | ./out/attn-2-1234/ |
| attn-3 | 1234 | attn3_prope_half.yaml | ./out/attn-3-1234/ |
| attn-4 | 1234 | attn4_gate.yaml | ./out/attn-4-1234/ |
| attn-0 | 1235 | t2.yaml | ./out/attn-0-1235/ |
| attn-1 | 1235 | attn1_mqa.yaml | ./out/attn-1-1235/ |
| attn-2 | 1235 | attn2_swa128_sink.yaml | ./out/attn-2-1235/ |
| attn-3 | 1235 | attn3_prope_half.yaml | ./out/attn-3-1235/ |
| attn-4 | 1235 | attn4_gate.yaml | ./out/attn-4-1235/ |
| attn-0 | 1236 | t2.yaml | ./out/attn-0-1236/ |
| attn-1 | 1236 | attn1_mqa.yaml | ./out/attn-1-1236/ |
| attn-2 | 1236 | attn2_swa128_sink.yaml | ./out/attn-2-1236/ |
| attn-3 | 1236 | attn3_prope_half.yaml | ./out/attn-3-1236/ |
| attn-4 | 1236 | attn4_gate.yaml | ./out/attn-4-1236/ |

## Acceptance and return

For alternatives 1–3, separately on three-group, code, and Indic BPB:
candidate mean minus reference mean <= max(candidate seed range, reference seed range).
All three conditions must pass.

Alternative 4 must improve three-group BPB by more than the larger seed range,
with code and Indic regressions within their corresponding seed ranges.
Use all three complete finite runs. A timeout before 1,221 steps is not a result.
The current winner-only helper does not implement alternatives 1–3's not-worse rule;
report their arithmetic explicitly. Smoke scores cannot select a winner.

## Commands

The following are separate sequential invocations, not a shell pipeline.
No --smoke, reduced-context flag, or --no-checkpoint is present in quality commands.

```text
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/t2.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1234 --out ./out/attn-0-1234
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn1_mqa.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1234 --out ./out/attn-1-1234
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn2_swa128_sink.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1234 --out ./out/attn-2-1234
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn3_prope_half.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1234 --out ./out/attn-3-1234
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn4_gate.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1234 --out ./out/attn-4-1234
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/t2.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1235 --out ./out/attn-0-1235
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn1_mqa.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1235 --out ./out/attn-1-1235
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn2_swa128_sink.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1235 --out ./out/attn-2-1235
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn3_prope_half.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1235 --out ./out/attn-3-1235
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn4_gate.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1235 --out ./out/attn-4-1235
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/t2.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1236 --out ./out/attn-0-1236
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn1_mqa.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1236 --out ./out/attn-1-1236
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn2_swa128_sink.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1236 --out ./out/attn-2-1236
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn3_prope_half.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1236 --out ./out/attn-3-1236
python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/attn4_gate.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --lr 0.001 --seed 1236 --out ./out/attn-4-1236
```

## Execution boundary

Lead approval, approved runtime resolution, the official staged dataset and TSAI
scheduling are required before quality execution. This request grants none of them.

The owner-managed preliminary screen below is complete. Please coordinate
execution before reserving GPUs so the same approved matrix is not run twice.
The request remains useful for scheduling visibility, access to the existing
approved bundle, and a course-reviewed execution record.

The cache/resume implementation and notebook sources are submitted separately
following the [scope review on #337](https://github.com/theschoolofai/era-v5-lab/pull/337#pullrequestreview-5845815690).
The execution source above identifies what actually produced the saved evidence;
it does not grant approval to an unmerged implementation.

## Completed owner-managed preliminary screen

The separate [annotated GPU notebook](https://github.com/revantg/era-v5-lab/blob/codex/g5-attention-notebooks/teams/05-architecture/notebooks/attention_gpu_screen.py) completed
all five designs at seed 1235 for 1,221 full-shape updates each, with checkpoints.
This uses a declared reconstruction from the published cleaned TRAIN parts and
permanent G5 heldout, and keeps pending approval/development eligibility. It does
not replace the exact #310 staging request or the three-seed quality matrix above.

| Design | Three-group BPB | Code BPB | Indic BPB | Difference from reference |
|---|---:|---:|---:|---:|
| Reference | 1.9379 | 2.0936 | 1.6325 | +0.0000 |
| More key/value sharing | 1.9360 | 2.0892 | 1.6243 | -0.0020 |
| Recent text + learned sink | 1.9250 | 2.0694 | 1.6231 | -0.0129 |
| Partial position rotation | 1.9313 | 2.0886 | 1.6177 | -0.0066 |
| Learned output gate | 1.9214 | 2.0844 | 1.5996 | -0.0165 |

[Raw logs, 75 slice scores, input identities and limitations](evidence/2026-11-10-attention-screen/README.md).

![Completed real-data training losses; single-seed preliminary evidence](evidence/2026-11-10-attention-screen/screen-losses.png)

![Completed held-out score curves](evidence/2026-11-10-attention-screen/screen-heldout-bpb.png)

## Separate review scopes

- [Cache/resume implementation and regression tests: #343](https://github.com/theschoolofai/era-v5-lab/pull/343), for Sonu's coordination/integration and Udit's code review.
- [Annotated notebooks and synthetic launch evidence: #344](https://github.com/theschoolofai/era-v5-lab/pull/344).
- [This job request and one-seed records: #345](https://github.com/theschoolofai/era-v5-lab/pull/345).

The original [#337](https://github.com/theschoolofai/era-v5-lab/pull/337) is superseded
by those submissions; its branch and historical evidence remain available.
