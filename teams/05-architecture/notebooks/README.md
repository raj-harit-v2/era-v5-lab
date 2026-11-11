# Attention notebooks

| Notebook | Purpose |
|---|---|
| `attention_smoke.py` | Short synthetic CPU/GPU launch checks |
| `attention_gpu_screen.py` | Five full-step real-data designs, one common seed; preliminary evidence |

Both use explicit controls and start no training when opened or exported.

## Short smoke lab

A readable marimo notebook that checks the existing G5 attention implementations
with the actual Week-2 training program. It changes no model or trainer source.

## Open the notebook

From a configured marimo/PyTorch environment, run from this directory:

```bash
marimo edit attention_smoke.py
```

The notebook opens without starting training. Use **Run verification and smoke
tests** to queue the existing verification suite and the selected smoke checks.
Jobs run one at a time to avoid loading five large models into RAM together.
Use **Refresh completed results** to update the view. Matching completed results
are validated and reused; incomplete output is preserved for inspection.

The default workspace is `attention-smoke-lab/` beneath the process working
directory. To keep it elsewhere, set `ATTENTION_SMOKE_DIR` before launching.
The nested workspace is ignored by this folder's `.gitignore`.

## What it checks

The reference plus four alternatives are loaded from the existing configuration
files: more key/value sharing, windowed attention with a learned sink, half-RoPE,
and an attention output gate. The notebook explains those labels and draws the
eight-layer attention patterns.

The model width, depth, experts, vocabulary, and attention choices remain those
of the reviewed T2 configurations. Supported smoke flags reduce only context,
batch, steps, and CPU precision:

| Check | Steps | Context | Batch | Format | Seed |
|---|---:|---:|---:|---|---:|
| CPU launch check | 6 | 160 | 1 | fp32 | 1234 |
| Optional GPU launch check | 8 | 160 | 1 | bf16 | 1234 |

A context of 160 is deliberate: it exceeds the unchanged local window of 128.
At least one synthetic document is verified to contain more than 128 tokens.
The real artifact loader validates the tokenizer and every byte-table row.
Nothing patches the identity checks or grants quality-run approval.

## Inputs and reproducibility

- Source is pinned to `c9cac5a0d5811e712212a37a01d6c540346ff1a1`.
- The published course tokenizer v0 is rebuilt from its pinned public baseline.
  Its expected SHA-256 is checked before use.
- The existing G4 builder generates the matching format-v2 raw P32 byte table.
- Only synthetic English, code, and Hindi documents are used for smoke data.
- Input hashes, commands, resolved model settings, versions, and original trainer
  manifests/metrics/summaries are retained in the workspace.
- Initial evaluation at step zero is excluded from training-loss plots.

The evidence download contains launch evidence, not official evaluation results.
The trainer's `smoke` and `eligible_for_quality_comparison` fields are checked.
Cached evidence must match the current source, artifacts, data, configuration,
and PyTorch runtime. Choose a fresh workspace when changing those inputs.

## Observed validation: 10 November 2026

The user-provided Linux notebook completed all 102 existing Week-2 tests and all
five CPU plus five GPU smoke checks. All runs had finite losses and gradients;
the final training loss was lower than the first in each observed run.
The notebook passed `marimo check`.

Observed runtime: Python 3.13.11, PyTorch 2.11.0, CUDA 13.0,
NumPy 2.4.6, tokenizers 0.22.2, PyYAML 6.0.3, marimo 0.25.2.
GPU: RTX PRO 6000 Blackwell Server Edition, approximately 95 GiB visible memory.
These are the tested installed versions; the harness's older requirements file
is unchanged. Wall times are diagnostic, not comparative speed benchmarks.

## Full-quality runs

The course permits an owner's machine when it meets the run budget. A full
comparison is a separate operation: approved real training/evaluation inputs,
source sidecars/checksums/decontamination report, approved runtime resolution,
context 2048, global batch 8, 1221 steps within 90 minutes, and all three seeds.
The short checks here do not establish full-budget memory or runtime, and no
quality run is automatically launched.

Keep tokenizer/table downloads, run outputs, model checkpoints, archives, HTML,
and PDF exports outside Git. The notebook contains no kernel URL or credential.
Notebook setup/orchestration is AI-assisted; model code is the upstream code.

## Optional full-size GPU fit check

After the notebook prepares the workspace, run this separate, bounded helper:

```bash
python full_shape_probe.py --workspace /path/to/attention-smoke-lab
```

It runs each design for three steps at context 2048, global batch 8 and
microbatch 1, using longer synthetic documents. It preserves the trainer and
records actual per-step timing and sampled total device memory. It does not
measure official evaluation/checkpoint overhead or establish a 90-minute finish.
Choose a fresh workspace if a prior probe exists; evidence is never overwritten.

The [compute request](https://github.com/revantg/era-v5-lab/blob/codex/g5-attention-job/teams/05-architecture/jobs/2026-11-10-attention-t2.md) includes the full
five-design, three-seed matrix and links the saved evidence.

## Single-seed GPU screen

`attention_gpu_screen.py` is a separate, annotated notebook for the owner's
requested preliminary comparison: all five attention designs, one common seed
**1235**, full context/batch shape and **1,221 updates per design**. Seed 1235 had
the lowest reported score in the earlier learning-rate screen; that observation
does not establish a generally best seed. The submitted three-seed request is
unchanged.

This notebook discovers the published cleaned sample through the course's public
plan widget, downloads all **48 TRAIN parts across 38 packs**, verifies their
official checksums, and applies the existing full G9 v2 protection checks.
Flagged documents and exact held-out copies are removed; other IDs/text are
preserved in deterministic part/row order. It uses the permanent, published
**1,059-document G5 held-out set**, which supplies all 15 slices. The cleaned
sample's own held-out split lacks Punjabi and Assamese. This reconstructed bundle
is explicitly different from the unpublished JSONL staging of job #310.

Runs use the supported development flag with the full step budget, without shape
reductions, and keep checkpointing enabled. They retain pending approval,
`smoke=true` and `eligible_for_quality_comparison=false`; one seed cannot satisfy
the final mean/range comparison. The notebook records actual scored-token counts
and does not infer them from padded input positions.

A documented data-loader repair restores the CPU sampler's RNG state on CPU
after a checkpoint is mapped to CUDA. Original and repaired file hashes are
recorded; the model and optimizer mathematics are unchanged. The restart check
compares six continuous steps against three steps plus a resumed three steps.

Execution is pinned to `c1849c1b9dd11eec9ed1958c07deee173ca73265`.
The optional `build_window_cache.py` companion in that pinned execution checkout
prepares checksum-verified numeric
windows, then the trainer reads those files through a read-only memory map.
Ordered workers retain the existing strict tokenizer/UTF-8 validation. Input,
artifact, source and window-setting identities are checked before reuse; no
pickle or raw-document cache is used. The default uncached loader is unchanged.

On the GPU runtime, **113 harness tests passed**. Six-step uncached, cached and
cached/resumed checks produced byte-identical losses and identical final model
hashes. The cache avoids repeating tokenization and large Python-list allocation;
it preserves the documents, sample order and numerical training behavior.

All execution controls are explicit, background tasks survive display refreshes,
and completed results are read from evidence files. Opening or exporting the
notebook does not start training. The default workspace is `attention-gpu-lab/`;
set `ATTENTION_GPU_DIR` to choose another location. Signed download URLs and
credentials are never included in notebook output or evidence downloads.

After measuring spare capacity, optional controls overlap the half-RoPE and
output-gate designs with the original queue, capped at **three independent
trainers**. Each process keeps the same run settings. The observed GPU activity
rose from 37–52% with one trainer to 94–100% with two; the three-trainer trial
used about 37 GiB of 95 GiB. Short-window aggregate training throughput improved
by approximately 50% over one trainer. These operational samples and contended
wall times are not comparative model-speed benchmarks.

Training plots show raw batch losses and an explicitly labeled 25-update moving
average. Evaluation plots retain the actual logged held-out scores, including
the initial evaluation. Plot labels name the designs in plain language.

## Completed real-data screen: 10 November 2026

| Design | Three-group BPB | Code BPB | Indic BPB | Difference from reference |
|---|---:|---:|---:|---:|
| Reference | 1.9379 | 2.0936 | 1.6325 | +0.0000 |
| More key/value sharing | 1.9360 | 2.0892 | 1.6243 | -0.0020 |
| Recent text + learned sink | 1.9250 | 2.0694 | 1.6231 | -0.0129 |
| Partial position rotation | 1.9313 | 2.0886 | 1.6177 | -0.0066 |
| Learned output gate | 1.9214 | 2.0844 | 1.5996 | -0.0165 |

All five runs completed 1,221 updates at the same seed 1235 and full model/batch shape.
These are single-seed preliminary scores; approval and the formal three-seed comparison
remain pending. The learned output gate is lowest overall/Indic; windowed attention
is lowest on code. [Raw evidence and limitations](https://github.com/revantg/era-v5-lab/blob/codex/g5-attention-job/teams/05-architecture/jobs/evidence/2026-11-10-attention-screen/README.md).

## Review boundaries

The compute request and completed real-data records, the cache/resume repair, and
these notebook sources are separate submissions following the scope review on
[#337](https://github.com/theschoolofai/era-v5-lab/pull/337#pullrequestreview-5845815690).
This PR preserves the notebook Python sources byte-for-byte. The synthetic launch
and full-size fit evidence lives in
[`../jobs/evidence/2026-11-10-attention-smoke/`](../jobs/evidence/2026-11-10-attention-smoke/README.md).
The GPU notebook deliberately retains its historical execution pin; it does not
claim that the proposed cache/resume repair is merged or approved.

- [Compute request and completed real-data records: #345](https://github.com/theschoolofai/era-v5-lab/pull/345).
- [Cache/resume implementation and tests: #343](https://github.com/theschoolofai/era-v5-lab/pull/343), for Sonu/Udit coordination and review.
- [This notebook companion: #344](https://github.com/theschoolofai/era-v5-lab/pull/344).

The original [#337](https://github.com/theschoolofai/era-v5-lab/pull/337) is superseded;
its execution history remains available. These links separate review ownership
without changing the historical notebook execution pins.
