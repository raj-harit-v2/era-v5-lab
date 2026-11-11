# Attention smoke evidence — 10 November 2026

- Source: theschoolofai/era-v5-lab commit c9cac5a0d5811e712212a37a01d6c540346ff1a1.
- Existing verification suite: 102 tests passed, unchanged.
- Actual trainer: five CPU fp32 runs (6 steps), five GPU bf16 runs (8 steps).
- Model width/depth/experts/vocabulary/attention definitions unchanged.
- Supported smoke reductions: context 160, batch 1, seed 1234.
- Exact course tokenizer v0 and matching P32 raw table; hashes in inputs.json.
- Training/evaluation text is synthetic; no real evaluation quality is claimed.
- Every manifest says smoke=true; every summary says quality eligibility=false.
- Installed Python/PyTorch differ from older pinned requirements; exact versions recorded.
- Wall times include initialization/evaluation and GPU jobs can overlap. They are not speed benchmarks.

Each design/device folder contains the original manifest, summary, per-step metrics,
command record, and a readable smoke.log assembled from those actual files.
The official requested runs must use the prior TSAI-staged quality-data bundle,
not these synthetic smoke texts.

Work provenance: notebook orchestration and evidence packaging are AI-assisted;
the model implementation is the existing upstream implementation.
