# Executed G5 corpus context-extension test log

## Actual run and provenance

Self-run in the authorized personal Molab session at `2026-11-17T21:50:08.066045+00:00` UTC (18 November 2026 IST). No TSAI-returned result, lead acceptance or team-model training is claimed. The repository permits small tests on a personal machine. The original WikiText pilot is separate in `PILOT_TEST_LOG.md`.

Exact command from `/marimo/g5_context/approved_run_release`:

```bash
python context_extension_check.py --heldout /marimo/g5_context/approved_input/heldout_v1.jsonl
```

The same script is committed at `harness/context_extension_check.py`; its SHA-256 is `41a8b4b0870d465071fa6cb09e332e5e214e99d8790f46934fe40a3e8e9f3e00`. It was executed with Python 3.13.11, PyTorch 2.11.0+cu130, Transformers 5.14.1, CUDA 13.0 and NVIDIA RTX PRO 6000 Blackwell Server Edition. Outputs were written only to `./out/`.

## Model and input

- Original `HuggingFaceTB/SmolLM-135M` at revision `1d461723eec654e65efdc40cf49301c89c0c92f4`, same tokenizer revision, local cache only.
- Frozen `teams/05-architecture/heldout_v1/data/heldout_v1.jsonl`, repository revision `87323846b325997ea2c21737c7816f950b8f1a26`, SHA-256 `21c6e4b2df8dae9d69e254f4a00fc934d2a3c70f0675065a03724299d94312bb`.
- First three complete records with at least 4,096 SmolLM tokens, scanning C4/OpenWebMath/peS2o prefixes in file order before scoring. Selected `owm-test-000008`, `owm-test-000029`, `owm-test-000036`. No packing or repetition.
- Input is the first 4,096 IDs of each document; short input is its last 2,048 IDs. All four arms score the same final 512 targets per document, or 1,536 targets per arm.
- BF16, eager attention, full vocabulary projection, fixed identical weights, evaluation/inference mode, no KV cache and no training. Static YaRN factor 2, original reference 2048, theta 10000, beta_fast 32 / beta_slow 1.

## Measured result

| Run | Context | Mean NLL | Perplexity |
|---|---:|---:|---:|
| A | 2048 | 1.674093 | 5.333954 |
| B | 4096 | 7.125009 | 1242.659623 |
| C | 4096 | 1.696318 | 5.453827 |
| D | 2048 | 1.695154 | 5.447483 |

C-B=-5.428692; D-A=+0.021061; C-A=+0.022225; C-D=+0.001164 nats/token. C-D fixes YaRN and measures the added-prefix comparison. YaRN reduces the unscaled 4K loss but does not beat native 2K here. Short-window loss is higher on this subset. Three math-domain documents are not the full heldout_v1 score, retrieval evaluation or multilingual evidence.

## Actual checks and saved outputs

PASS frozen input hash; three complete eligible documents; identical target IDs; identical pretrained weights; finite losses on all four real 2K/4K input shapes. The runner computes full logits and scores correctly shifted rows `[-513:-1]`; no reduced-head or optimized-attention change is tested. The committed `approved_summary.csv`, `approved_document_results.csv` and `approved_manifest.json` contain the result and hashes. The complete download additionally preserves exact token fixtures, per-token losses, runner source and console output under `supporting_evidence/G5_approved_corpus/`.

Read the plan's reproduction section to rerun against the existing lab corpus and exact cached model. This run is a bounded surrogate, with acceptance left to the G5 lead/TSAI. The signed production context remains open.
