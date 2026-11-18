# Capstone rehearsal execution evidence, 16 November 2026

Hardware: Apple M1 Pro, 8 cores, 16 GB unified memory; PyTorch 2.14.1. All current publication checks use CPU with OMP_NUM_THREADS=2 and MKL_NUM_THREADS=2. Historical sampler measurements include CPU and MPS. No CUDA/T2/vLLM performance is established here.

The original d128 same-script run is in `d128-probe-prior.log`: all eleven steps completed in 3169.17 s. It predates the cleanup/failure-reporting fixes. The current-code reduced d64 run is in `publication-probe.log`; this checks the orchestration and all five SFT arms, not learning. Raw inputs and IDs are private and must be staged separately. The SFT input hashes are listed in the request.

## Current-code end-to-end command

Set DATASET to the local dataset folder and REPO to this checkout. The following names identify the local private inputs, not files shipped in this PR.

```bash
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false G10_STDIO_RUNNER=docker
W="$DATASET/work/capstone-rehearsal-2026-11-16"
"$DATASET/.venv/bin/python" "$REPO/teams/10-post-training/capstone/day_one_probe.py" --g5-root "$DATASET/research/repos/lab-main-ae4c03d-ro" --run-folder "$W/private/runs/a_tiny_mps_smoke" --tokenizer "$W/artifacts/tokenizer_p1536.json" --byte-table "$W/artifacts/ke2_p1536/raw_table_P32.npz" --heldout "$W/artifacts/heldout_v1_bal60k.jsonl" --heldout-sources "$W/artifacts/heldout_v1_bal60k_sources.jsonl" --sft-eval "$W/private/sft/dolly_eval.jsonl" --sft-train "$W/private/sft/dolly_train.jsonl" --sft-steps 1 --sft-max-train-seconds 30 --rl-tasks "$DATASET/work/rl-data-v1-2026-11-11/out/v1/cc.jsonl" --rl-ids "$W/private/rl_easy_rung_ids.txt" --rl-limit 1 --rl-max-new 16 --sample-len 16 --probe-max-new 4 --device cpu --out "$W/private/publication_probe"
```

## Regression command

From this checkout, using the same private fixture inputs as the baseline:

```bash
export G10_BASELINE_TOKENIZER="$DATASET/work/g6-muon-profile-2026-11-10/staged/BrahmicTokenizer-131K/tokenizer.json"
export G10_OLMOE_SHAPE_CKPT="$DATASET/research/g10_rl/joblog/olmoe_shape_ckpt"
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
"$DATASET/.venv/bin/python" -m pytest teams/10-post-training/rl-loop teams/10-post-training/dt/tests teams/10-post-training/sft/bench/tests teams/10-post-training/chat-format -q -p no:cacheprovider -rs
```

The prior untouched-base result was 152 passed, 1 failed (the stale skipped adapter test), 4 skipped in 82.60 s. Prior rehearsal result: 166 passed, 4 skipped in 347.04 s, on a contended laptop. These are dated execution results, not matched speed comparisons. New publication results are attached separately.

## Matched sampling benchmark

`sampling_b_cpu.json` and `sampling_b_mps.json` contain full geometry, timing, warmup contract (one call per path), output parity and torch version. Model d128, 4 layers, 16+1 experts, top-2, context256; prompt128, k8, 128 new greedy tokens. Run:

```bash
python teams/10-post-training/capstone/bench_sampling_g5.py --adapter-config "$ADAPTER_B" --prompt-len 128 --k 8 --max-new 128 --device cpu
# Same command with --device mps for the MPS measurement.
```

CPU before/head/KV: 26.301/9.447/1.081 seconds, 38.9/108.4/947.6 new tokens/s; MPS: 117.353/6.253/3.959 seconds, 8.7/163.8/258.6 tokens/s. Identical greedy tokens across the three paths in each run. This covers the d128 sampler only, not total RL throughput or T2/GPU scaling.

## Operational limits

The job runner enforces the 60-minute total cap. Per-arm training caps exclude loading, calibration, evaluation and scoring. Ordinary child failures remove weights/generations; abrupt kill needs runner cleanup. Partial or failed checks must not be called a completed real-model probe. DT calibration can leave experts unseen and is diagnostic only. Packed G6 expert tensors are not supported by these per-Linear adapters.

## Current regression result
`169 passed, 4 skipped in 227.55s (0:03:47)`; full final lines in `publication-regression.log`. The four skips are missing math_verify (2) and unset G10_BENCH_SLICE (2). The final test decorator style change was separately rechecked:3passed0.47s. Guard passed28files before final evidence attachment.

Peak sampler memory was not recorded in the historical timing run; CUDA capacity and throughput remain unmeasured. The observed output-footprint check is separate from runtime peak memory.

## Final resume-compatibility correction
Review found that always adding an unset `autocast` key would reject durable states written before the new option. The identity includes it only when explicitly enabled. After this correction, `OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python -m pytest teams/10-post-training/rl-loop/test_resume_state.py teams/10-post-training/rl-loop/test_day_one_probe.py -q -p no:cacheprovider` passed10tests in12.28s, including real trainer stop/continue and kill/resume tests; see `publication-resume.log`. The earlier169-test regression predates this final small correction; it was not rerun wholesale.

## Current probe result
All11steps passed in775.91s (CPU d64,1SFTstep per arm). Each of five reports passed reload parity, frozen-weight and mask checks. No weights or generations remained. Total output:71195bytes. See `publication-probe.log` and `publication-summary.json`. This is executability evidence, not an SFT learning comparison.
