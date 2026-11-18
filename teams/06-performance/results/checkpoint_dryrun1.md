# G6 Week 3 — Dry Run 1 Checkpoint Timing Results

## Source

- Team: G6 — Performance and Kernels
- Owner: Siva Ajjapu (@AJJAPUSIVA)
- Job PR: https://github.com/theschoolofai/era-v5-lab/pull/485
- Execution: TSAI GPU run
- Evidence: Instructor-reported results, 17 November 2026
- Status: TSAI summary received; full timing JSON not available

## Job scope

The approved `dryrun1_ckpt` job benchmarks saving a small-width
synthetic MoE model and its fully initialized optimizer state.

This is not a full-width Dry Run 1 training checkpoint benchmark.

The job uses the existing G6 `run_checkpoint()` implementation,
including a discarded first checkpoint save.

## TSAI-reported results

| Metric | Result |
|---|---|
| Checkpoint timing repeats | 10 |
| Optimizer-state coverage | Complete |
| GPU-to-CPU copy share of save time | 8% |
| File-write share of save time | 92% |
| Absolute save time (`save_ms`) | Not provided |
| Absolute CPU-copy time (`to_cpu_ms`) | Not provided |
| Absolute file-write time (`write_ms`) | Not provided |
| Checkpoint size (`size_mb`) | Not provided |
| GPU model and device details | Not provided |
| Execution Git SHA | Not provided |

The reported 8% and 92% are relative shares of checkpoint
save time, not absolute millisecond measurements.

## Interpretation

The measured checkpoint save was dominated by the file-writing
stage, accounting for 92% of the reported save-time breakdown.

GPU-to-CPU staging accounted for the remaining 8%.

The TSAI result confirms that optimizer-state coverage was
complete before checkpoint timing, addressing the earlier
risk of understating checkpoint size because of missing
Muon or AdamW state.

## Evidence limitations

- TSAI retained the absolute checkpoint timings and GPU details.
- The full `dryrun1_ckpt.json` and execution log were not returned.
- No GPU-specific checkpoint size or absolute throughput is claimed.
- Mac CPU smoke results and Kaggle rehearsal results are separate
  preliminary evidence and are not substituted for TSAI values.
- The benchmark uses a small-width model, not the final full-width
  Dry Run 1 training configuration.
- No checkpoint restore-time measurement is claimed here.

## Follow-up

If TSAI releases the full output JSON or execution log, add
the exact save, CPU-copy, file-write, checkpoint-size, GPU,
and source-SHA values with their provenance.

Do not fill full-width performance rows using this small-width result.

## Conclusion

TSAI completed the approved checkpoint timing job with 10 repeats
and complete optimizer-state coverage.

The checkpoint save-time breakdown was:

- 8% GPU-to-CPU copy
- 92% file write

Absolute timings remain unavailable.
