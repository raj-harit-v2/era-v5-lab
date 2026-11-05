# Speed v1 — Gate 2 evidence pack

One table of measured runs for baseline, CE A/B, and MoE dispatch. Fill empty arm-job rows when TSAI returns logs. MFU/HFU and lab GPU model stay scrubbed in public chat; full numbers may sit in private job artifacts.

| Section | Status |
| :--- | :--- |
| Baseline (Week-1 ref + #239 clean) | Filled |
| Fused / Triton CE A/B | Filled (cross-SHA; see notes) |
| MoE loop / sorted / grouped | Filled (#53 / Adinath) |
| Config arms t1–t3 (job requests) | TBD |
| Recommendation | Draft below |
| Repeat check scope | Windows WDDM out of scope ([repeat_check_v1 §4](repeat_check_v1.md#4-rtx-5070-ti-windows-wddm--out-of-scope-2727-code-parts-pass-windows-disk-gap-recorded)) |

**Windows WDDM is out of scope for benchmark gating.** No row in this pack comes from a Windows run. On Windows, all 27 code parts passed the repeat check (at most 2.18%); only `checkpoint save` failed, with gaps of 7.65–9.52% attributed to Windows disk variance. The same GPU passes `checkpoint save` on Linux at 0.29–2.8%. Evidence and decision: [repeat_check_v1 §4](repeat_check_v1.md#4-rtx-5070-ti-windows-wddm--out-of-scope-2727-code-parts-pass-windows-disk-gap-recorded).

---

## 1. Baseline (clean step)

| Run | GPU | Commit | Config | step_ms med | tokens/s | peak_alloc GiB | Notes |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| baseline_v0 (ref) | A100-SXM4-40GB | `f1ed7f2` | `configs/base.yaml` | 42.9 | 95,400 | 6.54 | Week-1 tip baseline |
| baseline_v1 (job) | one lab GPU | `9b43b9a` (job #239) | wrapper `--synthetic`; `clean,layer` L3; bf16; B×T 16×256 | **86.09 / 86.99** (1.0%) | **47,576 / 47,086** | — | Gate-2 **clean** baseline. Layer `--repeat 2` FAIL (heat pause in run 2). MFU/HFU scrubbed. |

Sources: Week-1 docs; [class PR #239](https://github.com/theschoolofai/era-v5-lab/pull/239) TSAI wrapper result (4 Nov).

---

## 2. CE A/B (fused family + Triton)

Same GPU class (A100-SXM4-40GB), synthetic data, `--repeat 2`. **Different tip SHAs** — cross-branch evidence, not a single-commit A/B.

### 2a. Fused linear CE (`g6/fused-linear-ce` @ `f84ac3d`)

| ce_impl | step_ms | peak_GB | vs torch step |
| :--- | ---: | ---: | :--- |
| torch | 43.09 | 6.54 | baseline |
| chunked | 57.93 | 1.36 | +34% slower |
| fused | 57.88 | 1.31 | +34% slower |
| fused_cce | 100.90 | 0.89 | +134% slower |
| fused_cached | 245.55 | 0.89 | ~5.7× slower |
| fused_liger | 245.62 | 0.89 | ~5.7× slower |

Evidence: Colab from Tharun / PR #35 path (`Colab_35_Tharun`).

### 2b. Triton CE (`g6/triton-kernels` @ `d18d20a`)

| ce_impl | step_ms | peak_GB | --repeat 2 |
| :--- | ---: | ---: | :--- |
| triton_ce | 94.25 | 0.89 | PASS |

Cmd: `python -m perfkit.bench --level 3 --modes clean,layer --repeat 2 --tag ce_triton data.source=synthetic model.ce_impl=triton_ce`

**Reading:** On A100-40GB, **torch remains fastest** on step_ms. Triton (~94 ms) sits near `fused_cce`, with peak mem ~0.89 GiB (~7× below torch). Prefer torch (or fused if mem OK) when step binds; Triton/fused_cce when memory binds — confirm later on one SHA if claiming a hard %.

---

## 3. MoE dispatch A/B — loop vs sorted vs grouped (T1 and the exp3 arms)

**Result: `sorted` is the default.** On every arm, `sorted` gives the fastest (or tied-fastest) step and a
faster MoE dispatch than `loop` (1.33×–5.43×). `grouped` is **slower than `loop` on all four T2 arms** and only
beats `loop` on T1 — in this single forward-pass, `reversible=false` regime its fixed `E·N·k` buffer dominates
because there are few host syncs to remove. This is the deferred Task-4 timing item from PR #41 (grouped MoE
dispatch).

| | |
|---|---|
| GPU | NVIDIA A100-SXM4-80GB, Colab |
| Commit | `46cc52624e` (`g6/dev`), clean tree |
| Software | torch 2.11.0+cu130, CUDA 13.0, Python 3.13 |
| Arms | `teams/05-architecture/configs/arms/{t1,t2,exp3_experts_8,exp3_experts_32,exp3_shared_0}.yaml` |
| Config | bf16, B=8. T1: T=1024, `mlp_ratio=2` (no `ffn_hidden`). T2 family: T=2048, `model.moe.ffn_hidden=768`, `model.ce_impl=chunked`. All arms `model.reversible=false`, `optim.lr=0.001`, `data.source=synthetic`. |
| Modes | `clean,layer`, level 3, `--repeat 2`, 100 measured steps after 10 warmup, each dispatch in its own process |
| Dispatches | `model.moe.dispatch` ∈ {`loop`, `sorted`, `grouped`} per arm |
| Evidence | Colab notebook `task4_exp3_timing_chunked.ipynb` (A100, full run log): https://colab.research.google.com/drive/11xd7DV07nf1HGyNjVpJ3bQHfGijLDKpV — not committed to the repo |
| Method | `moe.dispatch(ms)` = sum of the per-layer `fwd:block*.moe.dispatch` medians (level-3 layer mode). `step` = clean-mode median. `vs loop` = loop's dispatch ÷ this dispatch. Each arm's `--repeat 2` passed the 5% check except T1 `loop` (lab-GPU variance on one bwd block; the dispatch signal is unaffected). |

**Why `ce_impl=chunked` on the T2 family.** At T=2048 the fp32 `[B·T, V]` head logits are ~8 GB (16 GB with the
gradient) and OOM a 24 GB card before the dispatch runs. `chunked` avoids materialising the full logits; it
changes head/loss timing only, not the MoE dispatch being measured. Within each arm all three dispatches use the
same CE, so the A/B is clean. Across arms, compare the **dispatch** column, not raw step (T1 is not chunked).

### Results

| arm | dispatch | moe.dispatch (ms) | step (ms) | vs loop | peak mem (GB) |
|---|---|---:|---:|---:|---:|
| **t1** (T=1024, E=8) | loop | 34.53 | 123.15 | 1.00× | 14.72 |
| | sorted | 6.36 | 76.23 | **5.43×** | 15.34 |
| | grouped | 9.95 | 84.07 | 3.47× | 16.40 |
| **t2** (T=2048, E=16) | loop | 60.85 | 401.20 | 1.00× | 21.61 |
| | sorted | 40.40 | 384.16 | **1.51×** | 28.52 |
| | grouped | 81.27 | 482.12 | 0.75× | 36.83 |
| **exp3_experts_8** (E=8) | loop | 39.37 | 361.27 | 1.00× | 20.93 |
| | sorted | 25.63 | 356.90 | **1.54×** | 24.12 |
| | grouped | 43.92 | 400.35 | 0.90× | 28.17 |
| **exp3_experts_32** (E=32) | loop | 95.17 | 456.23 | 1.00× | 22.97 |
| | sorted | 71.79 | 440.45 | **1.33×** | 37.46 |
| | grouped | 156.99 | 645.87 | **0.61×** | **54.17** |
| **exp3_shared_0** (E=16, 0 shared) | loop | 67.47 | 401.63 | 1.00× | 21.03 |
| | sorted | 43.22 | 379.65 | **1.56×** | 28.18 |
| | grouped | 81.27 | 474.97 | 0.83× | 36.25 |

### Reading

1. **`sorted` wins on every arm.** It removes the per-expert host syncs of `loop` without a large fixed buffer:
   1.33×–1.56× faster dispatch on the T2 arms and 5.43× on T1, and the lowest step time everywhere. Its extra
   memory over `loop` (the sort/gather buffers) is modest (≤ +15 GB, worst on `exp3_experts_32`).

2. **`grouped` loses to `loop` on all four T2 arms** (0.61×–0.90× dispatch) and, while 3.47× on T1, still trails
   `sorted` there. `grouped` pre-pads a fixed `E·N·k` buffer; with a single forward pass and `reversible=false`
   there are almost no host syncs for it to amortise, so the buffer's compute and memory traffic dominate. The
   step times also show it: `grouped` is the slowest dispatch and slowest step of the three on every T2 arm.

3. **`grouped` memory scales with E and is the gating risk.** `exp3_experts_32` (E=32) `grouped` peaks at
   **54.17 GB** — vs 22.97 GB for `loop` and 37.46 GB for `sorted` — so it OOMs anything smaller than an 80 GB
   card even with `ce_impl=chunked`. Its dispatch (157 ms) is also the single worst number in the table. For
   high-E arms, `grouped` is not viable here; keep `loop`/`sorted`.

4. **Expected shape.** This matches PR #41's rationale: `grouped` is built to pay off in the **sync-heavy** regime
   (reversible / multi-pass), where removing repeated host syncs outweighs the buffer. A single forward pass is
   the opposite regime, so `grouped` loses. Capturing where the tradeoff flips needs a `reversible=true` A/B
   (follow-up); until then, `sorted` is the robust production default across T1 and the exp3 arms.

### Follow-up (MoE)

- `reversible=true` A/B on the same arms to find the sync-heavy crossover where `grouped` should win.
- `exp3_experts_32` `grouped` needs the `N·k` cap (or a per-expert cap) before it is usable below 80 GB.

---

## 4. Config arm jobs (TBD)

| Run | Config | Status |
| :--- | :--- | :--- |
| arm t1 | `arms/t1.yaml` | Job not filed / awaiting TSAI |
| arm t2 | `arms/t2.yaml` | Job not filed / awaiting TSAI |
| arm t3 | `arms/t3.yaml` | Job not filed / awaiting TSAI |

---

## 5. Draft trainer recommendation (Gate 2)

Until arm jobs and a cooled layer re-run land: use **#239 clean** (~87 ms / ~47k tok/s on `9b43b9a`, synthetic) as the lab baseline; keep **`moe.dispatch=sorted`** as the MoE default for the measured single-pass regime; treat fused/Triton CE as **memory wins, not step wins** vs torch on A100-40GB cross-SHA evidence. Revisit after layer re-run and same-SHA CE confirm.
