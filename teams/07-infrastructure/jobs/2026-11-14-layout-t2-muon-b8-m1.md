# Layout speed: T2 with Muon, one GPU, b = 8, m = 1


```text
Team:            07-infrastructure
Owner:           Max (uz9ai)
Lead approval:   pending, sureshmantha
Question:        What are the tokens per second and the memory of T2 with Muon on one GPU at 8 sequences per forward and 1 forward per optimizer step?
Script:          teams/05-architecture/harness/train_week2.py   (Team 5, merged; not edited)
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_muon.yaml --runtime teams/05-architecture/configs/runtime.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --device cuda --seed 1234 --smoke --smoke-steps 110 --no-checkpoint --smoke-batch-size 8 --out ./out/t2-b8-m1 && python teams/07-infrastructure/jobs/calculate_metrics.py
Config:          teams/05-architecture/configs/arms/exp2_muon.yaml + teams/05-architecture/configs/runtime.yaml
Inputs:          the TSAI-staged bundle of official job #310: tokenizer v0, its P32 raw byte table, train and held-out JSONL
Hardware:        1 GPU with native bf16 and at least 48 GiB (peak estimate 41.4 GiB)
Max time:        15 minutes
Precision:       bf16 (autocast, fp32 weights, as the harness does)
Measures:        median and p10/p90 of tokens_per_second over steps 11-110, median perf/step_ms, median gpu_alloc_gb, out of memory yes/no, GPU name
Expected result: gpu_alloc_gb about 6.9 GiB; peak about 41.4 GiB, so no out of memory on the stated GPU; tokens/s has no estimate (see below)
Outputs:         out/t2-b8-m1/metrics.jsonl, summary.json, manifest.json (under 5 MB); no checkpoint
Test log:        teams/07-infrastructure/jobs/2026-11-14-layout-t2-muon-b8-m1.log
```

## What this run is

One row of `results/layouts.md`, section 2: T2 (8 layers, width 512, 237.1M parameters) with Muon, as config v1 (PR 447) decides, at
b = 8 sequences of 2,048 tokens per forward and m = 1 forward per optimizer step, 16,384 tokens
per step. In the command, `--smoke-batch-size 8` sets the batch and the micro-batch to 8, so b = 8, m = 1. `exp2_muon.yaml` is Team 5's T2 arm with `optim.name: muon` (merged).

`--smoke` is needed: without it the harness refuses to run while the approvals in `runtime.yaml` are pending.
It keeps the shape, bf16 on CUDA and Muon, sets 110 steps and marks the output as not a quality result.

The memory estimates are from `python layout/parallel_layout_v1a.py --arm ../05-architecture/configs/arms/t2.yaml
--layout b=8,m=1` with config v1 as in PR 447. `gpu_alloc_gb` is the memory still allocated at the end of a
step: weights, gradients, Muon and AdamW state, and the bf16 logits of the last micro-batch. The harness does not
log the peak; out of memory, or none, checks it. Tokens/s is what the job measures; it has no estimate because
the speed of Team 5's model with Muon was never measured.

## Calculations for the log book

#### via calculate_metrics.py
For the job requests, I have calculated the following metrics via the calculate_metrics.py script.

A sample response (which TSAI should provide after each run):

```
out/t2-b8-m1/metrics.jsonl NO TRAINING METRICS: likely OOM or crash (no log evidence)
name, memory.total [MiB]
NVIDIA RTX PRO 4500 Blackwell Server Edition, 32623 MiB
```
#### Manually (not needed; just for reference)
**Read** `metrics.jsonl` in each folder. It has one line per step, including `tokens_per_second`, `perf/step_ms` and `gpu_alloc_gb`. Skip step 0 (an evaluation row with no speed) and the first 10 steps (warm-up), then take the medians:

```bash
uv run python - <<'EOF'
import json, statistics as st, sys, glob
for f in sorted(glob.glob("out/*/metrics.jsonl")):
    r = [json.loads(l) for l in open(f)]
    r = [x for x in r if x.get("step", 0) > 10 and x.get("perf/step_ms")]
    t = sorted(x["tokens_per_second"] for x in r)
    print(f, "tok/s median %.0f  p10 %.0f  p90 %.0f" % (st.median(t), t[len(t)//10], t[9*len(t)//10]),
            " gpu_alloc_gb %.2f" % st.median(x["gpu_alloc_gb"] for x in r))
EOF
nvidia-smi --query-gpu=name,memory.total --format=csv
```
**Fill in** each row in the logbook:
- **Tokens/s, measured:** the median.
- **`gpu_alloc_gb`, measured:** its median.
- **GPU:** the name from `nvidia-smi`.

If a run dies with CUDA out of memory, write "OOM" in that row. That is a result too: it tells us the calculated peak was right or too low.