# Full-size GPU feasibility check — 10 November 2026

Five sequential runs, three steps each, using unchanged source c9cac5a.
Context 2048, global batch 8, microbatch 1, bf16, seed 1234.
The generated synthetic documents each exceed 2048 tokens; the trainer
recorded 16384 input positions on every training step.

All five completed with finite losses/gradient norms. Median trainer step
time per design was 1.20–1.35 seconds. Maximum sampled total GPU memory
was 11225–12233 MiB (10.96–11.95 GiB), sampled by nvidia-smi every 0.5 s.
Sampling can miss instantaneous peaks and includes runtime/other device use.

This uses a tiny synthetic holdout and disables checkpoint writes in smoke
mode. These checks establish fit and initial progress, not official quality
or a guarantee that 1221 steps plus real evaluation/checkpointing finish
within 90 minutes. No official quality run has been performed here.

Reproduction helper: ../../../../notebooks/full_shape_probe.py (see notebook README).
The generated synthetic training fixture is reproducible from that helper;
fixture.json records its hash and token count. Original manifests, summaries,
metrics, command records, logs and plotted losses are retained here.
