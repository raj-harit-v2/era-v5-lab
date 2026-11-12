# Speed v1 — Gate 2 evidence pack

One table of measured runs for baseline, CE A/B, and MoE dispatch. Fill empty arm-job rows when TSAI returns logs. MFU/HFU and lab GPU model stay scrubbed in public chat; full numbers may sit in private job artifacts.

| Section | Status |
| :--- | :--- |
| Baseline (Week-1 ref + #239 clean + Lab Cap A4) | Filled (`95bd81a` PASS 26/26; clean ~101–107 ms range) |
| B-stack (B1–B5) | Filled: B3 throughput option; B2/B5 no default win; B1 opt-in; B4 already-on |
| Fused / Triton CE A/B | Filled: 2a/2b cross-SHA (A100-40GB); 2c same-SHA on `7ef9f14` (A100-80GB, plus T4) |
| Triton CE/LN backends | Merged tip #52 @ `710f53e` — **opt-in only**; defaults stay torch |
| MoE loop / sorted / grouped | Filled (#53 / Adinath) |
| Config arms t1–t3 (job requests) | Awaiting (jobs not filed) |
| Recommendation | Polished below (Gate 2 ask) |
| Repeat check scope | Windows WDDM out of scope ([repeat_check_v1 §4](repeat_check_v1.md#4-rtx-5070-ti-windows-wddm--out-of-scope-2727-code-parts-pass-windows-disk-gap-recorded)) |

---

## Repeat check

Windows WDDM is out of scope for benchmark gating. No row in this pack comes from a Windows run. On Windows, all 27 code parts passed the repeat check (at most 2.18%); only `checkpoint save` failed, with gaps of 7.65–9.52% attributed to Windows disk variance. The same GPU passes `checkpoint save` on Linux at 0.29–2.8%. Evidence and decision: [repeat_check_v1 §4](repeat_check_v1.md#4-rtx-5070-ti-windows-wddm--out-of-scope-2727-code-parts-pass-windows-disk-gap-recorded).

---

## 1. Baseline (clean step)

| Run | GPU | Commit | Config | step_ms med | tokens/s | peak_alloc GiB | Notes |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| baseline_v0 (ref) | A100-SXM4-40GB | `f1ed7f2` | `configs/base.yaml` | 42.9 | 95,400 | 6.54 | Week-1 tip baseline |
| baseline_v1 (job) | one lab GPU | `9b43b9a` (job #239) | wrapper `--synthetic`; `clean,layer` L3; bf16; B×T 16×256 | **86.09 / 86.99** (1.0%) | **47,576 / 47,086** | — | Early Gate-2 **clean** row (history). Layer `--repeat 2` FAIL (heat). MFU/HFU scrubbed. |
| baseline_v1 Lab Cap A4 | one lab GPU (SwPowerCap) | `95bd81a` (job #239) | wrapper `--synthetic`; cool-down → discard `layerW` → `layerA` vs `layerB`; L3 | **~101.1** (cite **101–107** across last 3 runs; do not lock) | — | — | **PASS** exit 0, **26/26** within 10% or 0.5 ms (**0** by abs floor only). Recorder overhead 0.7–3.7%. Keep harness warning: 20 gated parts p10–p90 >10%. Job-only Lab Cap (not tip default). **Pre tip #60.** |

Sources: Week-1 docs; [class PR #239](https://github.com/theschoolofai/era-v5-lab/pull/239) TSAI wrapper results (4 Nov early clean; 12 Nov Lab Cap A4 @ `95bd81a`).

Lab Cap (job-only on this node): `compare_clean_step=false`, `tol_pct=10`, `abs_tol_ms=0.5`, warm layer pair after 120s cool-down. Tip `base.yaml` defaults unchanged. Tip #60 (Muon launch cut + void fill) is on `g6/dev` but **not** in the #239 class job tree.

Class #369 @ 1123e50 (post tip #60) also PASS: exit 0, 26/26 under the same Lab Cap A4. Clean step median 116.7 ms with SwPowerCap on all clean samples (12/12); 1 part passed by the 0.5 ms rule; 23 parts have p10–p90 spread above 10%. Do not compare 116.7 ms with #239 (101–107 ms) as a speed change. #239 @ 95bd81a stays the Gate-2 baseline.

---

## 1b. B-stack (compile / vocab / batch / bf16 / pinmem)

| Item | Tip PR | Result | Pack reading |
| :--- | :--- | :--- | :--- |
| B1 compile | [#58](https://github.com/vaibh27/era-v5-lab/pull/58) | Opt-in full-model compiler mode | Available behind flag; not a default flip for Gate 2 |
| B2 vocab pad ×128 | [#63](https://github.com/vaibh27/era-v5-lab/pull/63) + [gist](https://gist.github.com/smitasasindran/a85832df93d7c4c423f9a435611a937e) | Win on unaligned vocab; **no gain at current V=131072** | Keep pad/mask for future tokenizer; **no trainer default change today** |
| B3 batch 32 | [#64](https://github.com/vaibh27/era-v5-lab/pull/64) + [gist](https://gist.github.com/keshavamurali/97edd9f62db9d20388dde754fd1cf6ce) | B16→B32 **+11% tokens/s** on A100 (note B and LR) | **Config throughput option** via `configs/batch32.yaml`; not a silent `base.yaml` flip |
| B4 bf16 | closed as baseline | bf16 already the measured path | Cite as **already on**, not a speedup claim |
| B5 pinmem H2D | [#65](https://github.com/vaibh27/era-v5-lab/pull/65) | Pinmem/non-blocking already in baseline; prefetch ON/OFF no reliable step win | Results-only; **no trainer speedup** |

Tip #52 (Triton CE/LN) merged @ `710f53e`: defaults remain `ce_impl=torch` / `ln_impl=torch_ln`. Memory-bound path only; do not cite as step win (see §2).

---

## 2. CE A/B (fused family + Triton)

2a/2b: same GPU class (A100-SXM4-40GB), synthetic data, `--repeat 2`, but **different tip SHAs** — cross-branch evidence, not a single-commit A/B. 2c is the single-commit A/B (`7ef9f14`) on A100-80GB and T4.

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

### 2c. Same-SHA CE A/B (`7ef9f14`)

Every `ce_impl` on **one commit, one GPU, one config**, run back to back in one session. This is the single-commit
A/B that 2a/2b could not be. The A100 table is the result; the T4 table below it is the earlier interim run.

#### A100-SXM4-80GB

| | |
| :--- | :--- |
| GPU | NVIDIA A100-SXM4-80GB (RunPod, on-demand), bf16, torch 2.8.0+cu128, triton 3.4.0 |
| Commit | `7ef9f14` (`g6/triton-kernels`, PR #52 tip; the only commit with all seven `ce_impl`), clean tree |
| Config | `configs/base.yaml`, B×T 16×256 (the 2a/2b setting), `data.source=synthetic` |
| Command | `python -m perfkit.bench --modes clean,layer --level 3 --repeat 2 --tag ce_<impl> data.source=synthetic model.ce_impl=<impl> run.batch_size=16` |
| Steps | 100 measured after 10 warmup, `--repeat 2` (each run in its own process) |
| Evidence | Run JSON / MD / JSONL, bench and CPU-smoke logs: [gist](https://gist.github.com/keshavamurali/a417fae09ecb2886ae90ab727eb97992) |

| ce_impl | step_ms (run 1 / run 2) | tokens/s | peak GiB | vs torch step | fwd:head+loss ms | bwd:head+loss ms | repeat check (step gap) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| torch | 38.09 / 38.08 | 107,522 | 6.54 | baseline | 9.28 | 10.29 | PASS (0.0%) |
| chunked | 50.87 / 50.81 | 80,515 | 1.36 | +33.5% | 9.79 | 22.48 | PASS (0.1%) |
| fused | 51.28 / 51.14 | 79,879 | 1.31 | +34.6% | 32.48 | 0.22 | PASS (0.3%) |
| triton_ce | 94.68 / 94.86 | 43,261 | 0.88 | +148.5% | 5.59 | 70.49 | PASS (0.2%) |
| fused_cce | 95.48 / 95.48 | 42,898 | 0.88 | +150.6% | 15.58 | 61.31 | PASS (0.0%) |
| fused_liger | 214.63 / 215.31 | 19,084 | 0.88 | +463.4% | 195.58 | 0.22 | PASS (0.3%) |
| fused_cached | 215.21 / 214.59 | 19,033 | 0.88 | +464.9% | 196.13 | 0.22 | PASS (0.3%) |

All seven pass the repeat check (step gap at most 0.3%; every gated part within 5%). The two `triton_ce` runs
reported `SwPowerCap` in 6/10 and 9/10 GPU samples (no other impl did); its two runs still agree within 0.2%.
`checkpoint` and `comm` modes were not run (clean step only, per the task). CPU smoke on the same commit (pod, GPU
hidden): `pytest correctness/test_ce.py --all-configs` 104 passed.

**Reading (A100, same SHA):**
- **torch is fastest** (38.1 ms, 107.5k tok/s) and uses the most memory (6.54 GiB). Every other option is a memory
  win (4.8–7.4× less peak) at a step cost. This confirms the 2a/2b ordering on one commit.
- **`chunked` and `fused` are tied** (+33.5% / +34.6%, 1.36 / 1.31 GiB), as in 2a (+34% each). On T4 `chunked` was
  clearly cheaper (+35.5% against +67%), so the tie is A100-specific. For `chunked` the step cost is all head + loss:
  +12.8 ms step against +12.7 ms `fwd+bwd:head+loss`.
- **`triton_ce` and `fused_cce` are tied** (+148.5% / +150.6%) at the lowest peak (0.88 GiB). `triton_ce` matches
  2b on its older commit (94.25 ms). Its backward is 12.6× its forward (70.5 against 5.6 ms); the T4 run and the
  kernel code (below) explain why.
- `fused_cached` and `fused_liger` (one shared implementation) are ~5.6× torch, as in 2a (~5.7×).
- Percentages agree with 2a within a few points even though the absolute steps differ (torch 38.1 here against
  43.1 ms in 2a: 80GB SXM part, newer torch). The 2a/2b cross-SHA comparison holds.

#### Tesla T4 (interim)

| | |
| :--- | :--- |
| GPU | Tesla T4 (Colab), fp16 (no native bf16), torch 2.11.0+cu130 |
| Commit | `7ef9f14` (`g6/triton-kernels`, PR #52 tip; the only commit with all seven `ce_impl`), clean tree |
| Config | `configs/base.yaml`, `run.batch_size=8` (README setting for T4), B×T 8×256, `data.source=synthetic` |
| Command | `python -m perfkit.bench --modes clean,layer --level 3 --repeat 2 --tag ce_<impl> data.source=synthetic model.ce_impl=<impl> run.batch_size=8` |
| Steps | 100 measured after 10 warmup, `--repeat 2` (each run in its own process) |
| Evidence | Run JSON / MD / JSONL, bench and CPU-smoke logs: [gist](https://gist.github.com/keshavamurali/f4213c3d45c60e31dc560e834a5fb89e) |

| ce_impl | step_ms (run 1 / run 2) | tokens/s | peak GiB | vs torch step | fwd:head+loss ms | bwd:head+loss ms | repeat check (step gap) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| torch | 128.87 / 128.84 | 15,892 | 3.54 | baseline | 30.21 | 35.45 | PASS (0.0%) |
| chunked | 174.68 / 174.71 | 11,724 | 0.98 | +35.5% | 30.47 | 81.34 | PASS (0.0%) |
| fused | 215.44 / 216.72 | 9,506 | 1.05 | +67.2% | 149.16 | 1.19 | PASS (0.6%) |
| fused_cce | 244.76 / 244.10 | 8,367 | 0.89 | +89.9% | 42.29 | 133.33 | PASS (0.3%) |
| fused_cached | 566.93 / 566.51 | 3,612 | 0.94 | +339.9% | 501.35 | 1.19 | PASS (0.1%) |
| fused_liger | 566.74 / 566.51 | 3,614 | 0.94 | +339.8% | 501.24 | 1.19 | PASS (0.0%) |
| triton_ce | 3,069.90 / 3,069.16 | 667 | 0.89 | +2282.1% | 172.19 | 2,834.96 | PASS (0.0%) |

All seven pass the repeat check (step gap at most 0.6%). Caveat: the Colab T4 reported `SwPowerCap` (power-capped
clocks) in every run, as in #40, so absolute times are for a capped T4; the ordering and the repeat agreement hold.
`checkpoint` and `comm` modes were not run (clean step only, per the task). The `torch` row reproduces the independent T4 profile in
[`headloss_fwd_t4.md`](headloss_fwd_t4.md) (step 128.2 ms, `fwd:head+loss` 30.24 ms, `bwd:head+loss` 35.45 ms, peak
3.54 GiB). CPU smoke on the same commit: `pytest correctness/test_ce.py --all-configs` 104 passed; a tiny CPU bench
(`configs/tiny_cpu.yaml`) exits 0 for each of the six PyTorch `ce_impl` (`triton_ce` needs CUDA, so it is not in the CPU smoke).

Do not compare T4 percentages with the A100 table one to one: fp16 against bf16, B=8 against B=16.

**Reading (T4 only):**
- **torch is fastest** and uses the most memory (3.54 GiB). Every other option trades step time for 3.4–4.0× less
  peak memory. The step difference is almost all head + loss: for `chunked`, +45.8 ms step against +46.2 ms
  `fwd+bwd:head+loss`.
- **`chunked` is the cheapest low-memory option on T4:** +35.5% step for 0.98 GiB. `fused` (+67%) and `fused_cce`
  (+90%) save a little more memory for a larger step cost. On A100 (2a, other commit) `chunked` and `fused` were
  tied at +34%; the A100 same-SHA run decides that ordering.
- `fused`, `fused_cached` and `fused_liger` compute the head gradients during the forward (their `bwd:head+loss` is
  1.19 ms), so compare their total step, not the backward alone ([`docs/LINEAR_CE.md`](../docs/LINEAR_CE.md)).
  `fused_cached` and `fused_liger` share one implementation, and their numbers are identical.
- **`triton_ce` is 24× slower than torch on T4**, almost all in the backward (2,835 ms against a 172 ms forward,
  16.5×). From the kernel code (`kernels/linear_ce_fused.py` on PR #52's branch, tiles `BM, BV, BK = 16, 128, 32`), both backward
  kernels launch one program per hidden tile and each recomputes its logits over the full vocabulary, so the head
  matmul is recomputed about 2 × (256 / 32) = 16 times. That matches the 16.5× ratio; it is a reading of the code,
  not a kernel profile. It keeps the lowest peak memory (0.89 GiB). Recorded as evidence only; the kernel is
  unchanged.

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

## 4. Config arm jobs (awaiting)

| Run | Config | Status |
| :--- | :--- | :--- |
| arm t1 | `arms/t1.yaml` | Job not filed / awaiting TSAI |
| arm t2 | `arms/t2.yaml` | Job not filed / awaiting TSAI |
| arm t3 | `arms/t3.yaml` | Job not filed / awaiting TSAI |

G5 Colab MoE §3 timed t1/t2 **shapes** for dispatch A/B only — not TSAI arm job rows.

---

## 5. Trainer recommendation (Gate 2)

**Ask for Sat 14:** Keep trainer defaults on **torch CE**, **`moe.dispatch=sorted`**, and **bf16** (already the measured path). Use class **#239 Lab Cap A4** (`95bd81a`) as the lab baseline under the **job-only** warm-layer pair rule (tol 10%, abs 0.5 ms unused; clean step about **101–107 ms** across recent runs — cite the range, do not lock a single KPI; keep the harness spread warning). Prefer **torch** for step; treat fused/Triton CE (including merged tip #52) as **memory options, not step wins** (same-SHA A100 §2c). Offer **B3 `batch32.yaml`** as an explicit throughput config (+11% tokens/s on A100); do **not** change default batch. Leave **B2** (no win at V=131072), **B5** (already present / no win), and **B1** (opt-in compile) out of the default flip. Arm jobs t1–t3 remain **awaiting**. Tip #60 is on `g6/dev` but this #239 evidence is **pre-#60**; post-#60 class #369 PASS under SwPowerCap; #239 remains the baseline (see §1). Hold **#61 g6-v2 MFU** until after Gate 2 / G8 labeling.
