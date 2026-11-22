# Gate 2 official speedup A/B decision

TSAI ran the official five-config comparison on the lab GPU runner using #536 at `91e00cd` on the pinned Gate 2 setup, the staged T2 inputs, `exp2_muon.yaml`, seed 1234, BF16, and `--stop-after 20`. Median step times cover steps 6–20. The ratio is baseline median divided by variant median.

## Official results

| Variant | Median step | Baseline ÷ variant | Scored tokens/sec | Peak GPU allocation | Loss trace / final model hash match |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline (#521 execution path) | 2,088.1 ms | 1.000× | 2,772 | 11.12 GiB | Reference |
| Consolidated checks | 2,072.8 ms | 1.007× | 2,801 | 10.19 GiB | Yes / Yes |
| Sparse experts | 2,385.5 ms | 0.875× | 2,508 | 11.15 GiB | No / No |
| Global SDPA | 1,902.3 ms | 1.098× | 3,091 | 9.56 GiB | No / No |
| Global FlashAttention | 1,935.0 ms | 1.079× | 2,997 | 9.56 GiB | No / No |

Sources are [TSAI's official results](https://github.com/theschoolofai/era-v5-lab/pull/536#issuecomment-7033189262), [TSAI's approval](https://github.com/theschoolofai/era-v5-lab/pull/536#pullrequestreview-5992358998), and [the Architecture lead decision](https://github.com/theschoolofai/era-v5-lab/pull/536#issuecomment-7039268094). The commands, logs, manifests, and metrics are on the runner host. TSAI offered to attach them. This table transcribes the posted official evidence.

## Change proposed for #536

Consolidated checks are enabled by default. The trainer collects the total, next-token and MTP loss components for all microbatches, then reads them together with the pre-clip gradient norm. Nonfinite values raise before the optimizer update. Backward may run before an invalid loss is reported. The post-update parameter check also runs.

`--no-consolidate-step-checks` selects the #521 checks for a repeated baseline comparison. `--consolidate-step-checks` explicitly selects the default. The manifest records the selection, which is included in checkpoint identity checks.

The official median reduction is 15.3 ms per step, approximately 0.73%, with a before/after ratio of 1.007×. The loss trace and final model hash matched the baseline in TSAI's comparison.

Sparse dispatch was rejected for adoption at the measured scale. SDPA and FlashAttention require a separate proposal and explicit acceptance of their numerical trace differences. Their prototype code and the multi-variant job files have been removed from this PR. The official table preserves the measurement record for those decisions.

## Reproduce the accepted comparison

On the same submitted revision, run the agreed T2 Muon command twice with fresh output directories. Use the same GPU, input hashes, tokenizer/table, resolution, runtime, seed, precision, and batch settings. Add `--no-consolidate-step-checks` to the baseline command. Use the default for the candidate.

Compare the same post-warmup step IDs and report both medians, baseline divided by candidate, scored tokens/sec, and loss-trace/model-hash parity. Checkpoints bind the selected path to the run identity, so use each run's checkpoint only with that path.

Config v1 remains as signed. The narrowed #536 diff changes the checks in the trainer, their tests, the logger fixture compatibility field, and this results record.
