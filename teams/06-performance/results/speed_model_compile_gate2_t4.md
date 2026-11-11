# G6 Gate 2: opt-in full-model torch.compile (Kaggle T4 preliminary evidence)

This change adds **config-visible** `run.compile_mode` selection. It preserves eager execution and
keeps the existing `torch.compile(core)` invocation for the default compiler mode.
Neither batch size nor precision, loss, optimizer, learning rate, or data loading is modified.

## Preliminary Kaggle GPU results — NOT TSAI lab validation

Source: executed `g6-gate2-speed-ab-kaggle (1).ipynb` (2026-11-05). Full raw JSON and log
archive has not been supplied or independently audited. Prototype used the environment
variable `G6_MODEL_COMPILE_MODE` before this config-visible PR patch; these data
therefore require rerunning with the PR code.

* Original source: `vaibh27/era-v5-lab` commit `4a1fd315277c9fe782efe8f7e30cc57bccf602ea`.
* Tesla T4 GPU 0, SM 7.5; PyTorch 2.11.0+cu130; FP16 with GradScaler (no native BF16).
* Batch 8, sequence 256, synthetic data, `ce_impl=torch`, Polar Muon + AdamW,
  constant LR schedule and pinned/nonblocking prefetch.
* Balanced run order: eager A, default A, max-autotune A, max-autotune B, default B, eager B.
  Each independent run used 20 warmup training steps and 100 measured clean steps.

| Model execution | run A (ms) | run B (ms) | midpoint of run medians (ms) | approx speedup vs eager |
|---|---:|---:|---:|---:|
| Eager | 127.6664 | 136.4998 | 132.0831 | 1.00x |
| `torch.compile` default | 87.8112 | 94.1762 | 90.9937 | 1.45x |
| `max-autotune-no-cudagraphs` | 89.0268 | 91.2040 | 90.1154 | 1.47x |

Both compiled modes beat eager in both rounds. Their difference is below ~1% on this
sample and **does not establish that max-autotune is better than default**.
Every measured run reported `SwPowerCap`. Within-mode A/B run variation exceeded 5%
for eager and default-compiled cases. **No Gate 2 5% repeatability acceptance is claimed**.
These T4 FP16 timings must not be compared as equivalent to TSAI's BF16 lab GPU baseline.

## Correctness and reproducibility

Kaggle prototype evidence: CPU smoke exit 0, reversible reconstruction OK, finite
weights; existing `correctness/test_optimizer.py` had 10 passing tests. This was
not a GPU matched-input comparison of compiled vs eager gradients or optimizer states.

For this PR run:

```bash
cd teams/06-performance
python -m pytest correctness/test_compile_mode.py -q
python -m pytest correctness/test_optimizer.py -q
python -m perfkit.smoke --config configs/tiny_cpu.yaml data.source=synthetic
python -m perfkit.bench --config configs/base.yaml --modes clean \
  --repeat 2 --tag g6_gate2_compiled_default \
  data.source=synthetic run.compile=true run.compile_mode=default
python -m perfkit.bench --config configs/base.yaml --modes clean \
  --repeat 2 --tag g6_gate2_compiled_maxauto \
  data.source=synthetic run.compile=true run.compile_mode=max-autotune-no-cudagraphs
```

For reproducible performance comparison, explicitly keep batch, dtype, model, seed,
loss implementation and schedule fixed between eager and compiled runs. The commands
above use the GPU's config-driven dtype/batch defaults; on T4 request
`run.dtype=fp16 run.batch_size=8` for all arms.

## Gate 2 / TSAI checklist

1. Attach CPU smoke and new compile-mode selection test log **from this PR commit**.
2. Compare matched-seed/matched-input GPU losses, gradients and optimizer updates
   for eager, default-compiled and max-autotune-compiled modes.
3. Attach raw benchmark JSON, per-step distributions, GPU memory, clocks/throttle
   reasons and compilation wall-clock cost; run A/B order in both directions.
4. TSAI lab GPU performs the final clean-step timing. Do not conflate this proposal
   with separate baseline-warmup PR #239.
