# Repeat check v1 (Task 1, week 2)

**The rule.** The gated parts are those at `report.gate_level` (2) or coarser — **28 parts** for
`configs/base.yaml` (the clean step, the level-1 phases `data` / `fwd` / `fwd:stack` / `bwd` / `bwd:stack` / `opt`,
the level-2 regions `embed` / `block0..5` / `head+loss` in forward and backward, the optimizer level-2 regions
`opt:opt.clip` / `opt:opt.polar_muon_adamw` / `opt:opt.muon` / `opt:opt.adamw`, and `checkpoint save`). A part
**passes** when the two runs are within `report.tol_pct` (**5%**, computed as `slower / faster - 1`) **or** less than
`report.abs_tol_ms` (**0.05 ms**) apart — the absolute rule exists because a sub-millisecond part can move >10% on
timer noise alone (TSAI, 30 Oct). Each run of a pair executes in its own Python process (`bench --repeat`,
`perfkit/bench.py`), measuring **100 steps** after 10 warmup steps (`bench.steps >= report.min_compare_steps = 100`;
at 50 steps small parts drifted).

**Status:**
- **Colab A100-SXM4-40GB (two sessions):** PASS, 28 of 28 gated parts (Section 2).
- **RTX 5070 Ti, Linux (6 normal + 6 MTP pairs):** PASS, 28 of 28 gated parts in all 12 pairs (Section 3).
- **RTX 5070 Ti, Windows WDDM:** All 27 code parts PASS; the 7.7–9.5% checkpoint save gap is Windows disk/fsync variance, and **Windows WDDM is recorded as out of scope** since all training and benchmarking run on Linux (Section 4).
- **Modal A100-80GB (normal pair + 100-step MTP pair on current commit):** PASS, 28 of 28 gated parts in both pairs (Section 5).
- **TSAI job runs:** Baseline pair + one repeat pair per A/B arm tracked in Section 6.

---

## 1. The #135 failure on record, confirmed from its run files

- **GPU:** NVIDIA H200 (140 GB HBM3e, Modal)
- **Commit:** `19221759f9d820ce0563d5d2f44e22eac0de53d2` (clean tree, `dirty: false`; 9 layers (`block0..8`), `model.ffn=moe`, `B=32`, `T=512`, `bf16`, 150 steps, **33 gated parts**)
- **Run IDs / tags:** `h200_v1` / `h200_v1-run2` (PR [#135](https://github.com/theschoolofai/era-v5-lab/pull/135))
- **Command:** `python -m perfkit.bench --config configs/lab_small.yaml --level 3 --repeat 2 --tag h200_v1`
- **Run files:**
  - Comparison & slowest-5: <https://gist.github.com/varshith2000/5eeebb4cb0ec3e7810782a4cf905d01d>
  - Run 1 & Run 2 reports: <https://gist.github.com/varshith2000/e394873e87f79d224815b6996a7e3fe1>
  - Full console log: <https://gist.github.com/varshith2000/63ac8f7d5dae8049597432c94c203a0a>

**Confirming the cause from #135's run files.** In both runs, `trace.host_syncs_per_step` = **433**:
- **432 syncs** at `models/moe.py:76` and `models/moe.py:78` (216 each — `tok.any()` and `nonzero()` copy a boolean/integer scalar from GPU to CPU once per expert per call: 9 layers $\times$ 3 forward passes of the reversible midpoint stack $\times$ 8 experts $\times$ 2 sync sites = 432).
- **1 sync** at `torch/__init__.py:1270`.
- On top of that, the optimizer ran `optim.muon_impl=loop` (the default then), pacing hundreds of small Newton-Schulz kernel launches from Python.

The failure signature in the 33-part table below is **CPU pacing, not GPU noise**: the GPU-bound parts were rock-solid (`fwd:head+loss` 0.22%, `bwd:head+loss` 0.02%, `fwd:embed` 0.96%, `checkpoint save` 1.37%), whereas every host-paced part moved wildly (`fwd:block0..7` 5.37–39.56%, `bwd:block0..7` 7.81–20.37%, `opt:opt.muon` 13.51%, `opt:opt.adamw` 8.22%). When the host CPU decides when small kernels launch, the wall time between two CUDA events depends on host OS scheduling, which is not repeatable across runs.

**The fix (merged prior to #167).** Stacking same-shaped parameter matrices in `optim.muon_impl: batched` (cutting Muon from 72.1 ms to 7.4 ms on the same H200 in [#135's A/B gist](https://gist.github.com/varshith2000/3a491b0af2c21978a35399c0e2dd0717)), multi-tensor `optim.adamw_impl: foreach`, and host batch prefetch after backward (`data.prefetch: true`) reduced host launches from ~3,540 to ~1,392 kernels per step and brought `configs/base.yaml` (`ffn: mlp`) down to **1 host sync per step** (step time 71 ms $\to$ 43 ms on A100).

**Full 33-part comparison table (recomputed with today's 5% or 0.05 ms gate — FAIL, 24 of 33 gated parts outside):**

| part | run 1 (ms) | run 2 (ms) | gap % | gap ms | verdict | rule |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| step (clean) | 401.984 | 430.363 | 7.06 | 28.379 | **outside** | - |
| data | 0.658 | 0.723 | 9.88 | 0.065 | **outside** | - |
| fwd | 63.244 | 67.783 | 7.18 | 4.539 | **outside** | - |
| fwd:embed | 1.988 | 2.007 | 0.96 | 0.019 | ok | 5% |
| fwd:stack | 44.932 | 49.313 | 9.75 | 4.381 | **outside** | - |
| fwd:block0 | 4.059 | 5.635 | 38.83 | 1.576 | **outside** | - |
| fwd:block1 | 3.999 | 5.581 | 39.56 | 1.582 | **outside** | - |
| fwd:block2 | 5.100 | 5.374 | 5.37 | 0.274 | **outside** | - |
| fwd:block3 | 4.410 | 5.294 | 20.05 | 0.884 | **outside** | - |
| fwd:block4 | 5.068 | 5.811 | 14.66 | 0.743 | **outside** | - |
| fwd:block5 | 4.346 | 5.631 | 29.57 | 1.285 | **outside** | - |
| fwd:block6 | 5.177 | 4.616 | 12.15 | 0.561 | **outside** | - |
| fwd:block7 | 4.021 | 4.519 | 12.38 | 0.498 | **outside** | - |
| fwd:block8 | 5.432 | 5.357 | 1.40 | 0.075 | ok | 5% |
| fwd:head+loss | 16.270 | 16.305 | 0.22 | 0.035 | ok | 5% |
| bwd | 145.424 | 155.510 | 6.94 | 10.086 | **outside** | - |
| bwd:head+loss | 16.340 | 16.337 | 0.02 | 0.003 | ok | 5% |
| bwd:stack | 128.831 | 138.887 | 7.81 | 10.056 | **outside** | - |
| bwd:block8 | 14.519 | 15.160 | 4.41 | 0.641 | ok | 5% |
| bwd:block7 | 12.973 | 14.228 | 9.67 | 1.255 | **outside** | - |
| bwd:block6 | 14.498 | 14.426 | 0.50 | 0.072 | ok | 5% |
| bwd:block5 | 13.373 | 15.353 | 14.81 | 1.980 | **outside** | - |
| bwd:block4 | 14.306 | 15.783 | 10.32 | 1.477 | **outside** | - |
| bwd:block3 | 13.778 | 15.095 | 9.56 | 1.317 | **outside** | - |
| bwd:block2 | 14.260 | 14.774 | 3.60 | 0.514 | ok | 5% |
| bwd:block1 | 12.629 | 15.201 | 20.37 | 2.572 | **outside** | - |
| bwd:block0 | 13.194 | 15.393 | 16.67 | 2.199 | **outside** | - |
| bwd:embed | 0.243 | 0.251 | 3.29 | 0.008 | ok | 5% |
| opt | 76.925 | 87.256 | 13.43 | 10.331 | **outside** | - |
| opt:opt.clip | 2.854 | 3.049 | 6.83 | 0.195 | **outside** | - |
| opt:opt.muon | 72.080 | 81.815 | 13.51 | 9.735 | **outside** | - |
| opt:opt.adamw | 0.986 | 1.067 | 8.22 | 0.081 | **outside** | - |
| checkpoint save | 3315.026 | 3360.569 | 1.37 | 45.543 | ok | 5% |

---

## 2. Colab A100-SXM4-40GB — PASS (two sessions, #167)

### 2.1 Session 1 (Vaibhav): Normal baseline pair (`baseline_v0`)

- **GPU:** NVIDIA A100-SXM4-40GB (Colab, driver `580.82.07`, torch `2.11.0+cu130`, CUDA `13.0`)
- **Commit:** `f1ed7f2daf525242d84e4daf45c9d0247583ed71` (`g6/dev`, clean tree `dirty: false`, `B=16`, `T=256`, `bf16`, 100 steps, 1 host sync/step)
- **Run IDs:** `157b8f124fa24a8e818dfcfa08efde32` (run 1) / `2a9ac20d7fef4e68ac3c654780678d68` (run 2)
- **Command:** `python -m perfkit.bench --config configs/base.yaml --level 3 --repeat 2 --tag baseline_v0`
- **Run files:** <https://gist.github.com/vaibh27/574990425455e4a9cb64822f14e3d85b>

**Result: PASS, 28 of 28 gated parts (all 28 by the 5% rule).**

| part | run 1 (ms) | run 2 (ms) | gap % | gap ms | verdict | rule |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| step (clean) | 42.909 | 42.946 | 0.09 | 0.037 | ok | 5% |
| data | 0.027 | 0.028 | 3.85 | 0.001 | ok | 5% |
| fwd | 14.013 | 14.021 | 0.06 | 0.008 | ok | 5% |
| fwd:embed | 0.395 | 0.396 | 0.26 | 0.001 | ok | 5% |
| fwd:stack | 2.931 | 2.935 | 0.14 | 0.004 | ok | 5% |
| fwd:block0 | 0.482 | 0.482 | 0.00 | 0.000 | ok | 5% |
| fwd:block1 | 0.484 | 0.485 | 0.21 | 0.001 | ok | 5% |
| fwd:block2 | 0.484 | 0.486 | 0.42 | 0.002 | ok | 5% |
| fwd:block3 | 0.485 | 0.486 | 0.21 | 0.001 | ok | 5% |
| fwd:block4 | 0.485 | 0.486 | 0.11 | 0.001 | ok | 5% |
| fwd:block5 | 0.485 | 0.485 | 0.00 | 0.000 | ok | 5% |
| fwd:head+loss | 10.674 | 10.678 | 0.04 | 0.004 | ok | 5% |
| bwd | 23.746 | 23.765 | 0.08 | 0.019 | ok | 5% |
| bwd:head+loss | 12.339 | 12.342 | 0.02 | 0.003 | ok | 5% |
| bwd:stack | 10.983 | 10.999 | 0.14 | 0.015 | ok | 5% |
| bwd:block5 | 1.825 | 1.827 | 0.11 | 0.002 | ok | 5% |
| bwd:block4 | 1.825 | 1.828 | 0.17 | 0.003 | ok | 5% |
| bwd:block3 | 1.826 | 1.829 | 0.17 | 0.003 | ok | 5% |
| bwd:block2 | 1.824 | 1.826 | 0.14 | 0.003 | ok | 5% |
| bwd:block1 | 1.825 | 1.828 | 0.20 | 0.004 | ok | 5% |
| bwd:block0 | 1.823 | 1.827 | 0.22 | 0.004 | ok | 5% |
| bwd:embed | 0.415 | 0.415 | 0.00 | 0.000 | ok | 5% |
| opt | 5.314 | 5.319 | 0.09 | 0.005 | ok | 5% |
| opt:opt.clip | 0.443 | 0.443 | 0.00 | 0.000 | ok | 5% |
| opt:opt.polar_muon_adamw | 4.861 | 4.866 | 0.11 | 0.005 | ok | 5% |
| opt:opt.muon | 2.322 | 2.328 | 0.22 | 0.005 | ok | 5% |
| opt:opt.adamw | 2.525 | 2.524 | 0.04 | 0.001 | ok | 5% |
| checkpoint save | 1914.178 | 1893.130 | 1.11 | 21.048 | ok | 5% |

### 2.2 Session 1 (Vaibhav): MTP pair at 100 steps (`mtp_v0`)

- **GPU:** NVIDIA A100-SXM4-40GB (Colab)
- **Commit:** `f1ed7f2daf525242d84e4daf45c9d0247583ed71` (`g6/dev`, clean tree `dirty: false`, `model.mtp=true`, `B=16`, `T=256`, `bf16`, 100 steps, 1 host sync/step)
- **Run IDs:** `4d52a594526846fba7a645edf375c1cf` (run 1) / `2c275390d51d46f6b868a0b172ba409e` (run 2)
- **Command:** `python -m perfkit.bench --config configs/base.yaml --level 3 --repeat 2 --tag mtp_v0 model.mtp=true`
- **Run files:** <https://gist.github.com/vaibh27/574990425455e4a9cb64822f14e3d85b>

**Result: PASS, 28 of 28 gated parts (all 28 by the 5% rule).**

| part | run 1 (ms) | run 2 (ms) | gap % | gap ms | verdict | rule |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| step (clean) | 68.620 | 68.614 | 0.01 | 0.006 | ok | 5% |
| data | 0.022 | 0.022 | 0.00 | 0.000 | ok | 5% |
| fwd | 24.701 | 24.698 | 0.01 | 0.003 | ok | 5% |
| fwd:embed | 0.397 | 0.397 | 0.00 | 0.000 | ok | 5% |
| fwd:stack | 2.955 | 2.954 | 0.03 | 0.001 | ok | 5% |
| fwd:block0 | 0.486 | 0.486 | 0.00 | 0.000 | ok | 5% |
| fwd:block1 | 0.489 | 0.488 | 0.21 | 0.001 | ok | 5% |
| fwd:block2 | 0.488 | 0.488 | 0.00 | 0.000 | ok | 5% |
| fwd:block3 | 0.490 | 0.489 | 0.21 | 0.001 | ok | 5% |
| fwd:block4 | 0.489 | 0.489 | 0.00 | 0.000 | ok | 5% |
| fwd:block5 | 0.489 | 0.489 | 0.00 | 0.000 | ok | 5% |
| fwd:head+loss | 21.336 | 21.334 | 0.01 | 0.002 | ok | 5% |
| bwd | 36.105 | 36.104 | 0.00 | 0.001 | ok | 5% |
| bwd:head+loss | 24.607 | 24.608 | 0.00 | 0.001 | ok | 5% |
| bwd:stack | 11.067 | 11.066 | 0.01 | 0.001 | ok | 5% |
| bwd:block5 | 1.839 | 1.839 | 0.00 | 0.000 | ok | 5% |
| bwd:block4 | 1.837 | 1.836 | 0.06 | 0.001 | ok | 5% |
| bwd:block3 | 1.841 | 1.841 | 0.00 | 0.000 | ok | 5% |
| bwd:block2 | 1.840 | 1.839 | 0.06 | 0.001 | ok | 5% |
| bwd:block1 | 1.839 | 1.838 | 0.06 | 0.001 | ok | 5% |
| bwd:block0 | 1.838 | 1.839 | 0.03 | 0.001 | ok | 5% |
| bwd:embed | 0.421 | 0.422 | 0.24 | 0.001 | ok | 5% |
| opt | 7.974 | 7.976 | 0.02 | 0.002 | ok | 5% |
| opt:opt.clip | 0.734 | 0.734 | 0.00 | 0.000 | ok | 5% |
| opt:opt.polar_muon_adamw | 7.228 | 7.231 | 0.04 | 0.003 | ok | 5% |
| opt:opt.muon | 2.349 | 2.350 | 0.04 | 0.001 | ok | 5% |
| opt:opt.adamw | 4.867 | 4.868 | 0.02 | 0.001 | ok | 5% |
| checkpoint save | 3575.717 | 3563.679 | 0.34 | 12.038 | ok | 5% |

### 2.3 Session 2 (Raj): Second Colab A100 session (#167)

- **GPU:** NVIDIA A100-SXM4-40GB (Colab, driver `580.82.07`, torch `2.11.0+cu130`, CUDA `13.0`)
- **Commit:** `f1ed7f2daf525242d84e4daf45c9d0247583ed71`
- **Command:** `python -m perfkit.bench --config configs/base.yaml --level 3 --repeat 2 --tag raj_a100`
- **Run files:** <https://drive.google.com/file/d/1RYqAON9qQ2XWPArQNp-iwq-qAKm1efCA/view>
- **Result:** Normal pair at 100 steps **PASS, 28 of 28 gated parts** (`data` passed via the `0.05 ms` rule: `0.027` vs `0.023` ms, `17.39%` / `0.004 ms`; all other 27 parts passed via the `5%` rule). Raj's MTP pair in that archive ran with `bench.steps=50` (below `report.min_compare_steps=100`); the 100-step MTP rerun is closed in Section 5.2 below (as well as Section 2.2 above and Section 3.2 below).

---

## 3. RTX 5070 Ti, Linux — PASS (6 + 6 pairs, 28 of 28 each, #167)

- **GPU:** NVIDIA GeForce RTX 5070 Ti (16 GB, Linux, driver `595.99.02`, torch `2.13.0+cu130`, CUDA `13.0`)
- **Commit:** `190693a8ab1026c19f8c52115940b3b3f68b41df` (`g6/dev`, identical code to `f1ed7f2`, docstring changes only; clean tree `dirty: false` in all 8 runs)
- **Run IDs:**
  - Normal (4 runs $\to$ 6 pairs): `f639324f65494635a69a20c271f8a862` (`run1`), `1394bd1bb7cb4a9ebb4c86289cd91375` (`run2`), `7d0ca28c…` (`run3`), `28627376…` (`run4`)
  - MTP (4 runs $\to$ 6 pairs): `80d55d357cff4be1a13f28cbcddcdb53` (`run1`), `2e584fd4b6d44c378835c9bc34b9bac8` (`run2`), `531463cc…` (`run3`), `f1231e18…` (`run4`)
- **Commands:**
  - `python -m perfkit.bench --config configs/base.yaml --level 3 --repeat 4 --steps 100 --tag rtx5070ti_normal run.device=cuda`
  - `python -m perfkit.bench --config configs/base.yaml --level 3 --repeat 4 --steps 100 --tag rtx5070ti_mtp run.device=cuda model.mtp=true`
- **Run files:** <https://gist.github.com/jssunil/0f0e289c5dca5630214d1de1da109ba9>

All $\binom{4}{2} = 6$ normal pairs and all $\binom{4}{2} = 6$ MTP pairs **PASS 28 of 28 gated parts** (12 of 12 pairs PASS; largest checkpoint save gap across all 12 pairs is 2.8%; GPU busy 99%).

### 3.1 RTX 5070 Ti Linux — Normal pair (`rtx5070ti_normal` vs `rtx5070ti_normal-run2`, 28 of 28 PASS)

| part | run 1 (ms) | run 2 (ms) | gap % | gap ms | verdict | rule |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| step (clean) | 59.616 | 59.627 | 0.02 | 0.011 | ok | 5% |
| data | 0.010 | 0.010 | 1.90 | 0.000 | ok | 5% |
| fwd | 20.040 | 20.036 | 0.02 | 0.004 | ok | 5% |
| fwd:embed | 0.287 | 0.287 | 0.05 | 0.000 | ok | 5% |
| fwd:stack | 2.434 | 2.435 | 0.06 | 0.001 | ok | 5% |
| fwd:block0 | 0.399 | 0.399 | 0.02 | 0.000 | ok | 5% |
| fwd:block1 | 0.405 | 0.405 | 0.00 | 0.000 | ok | 5% |
| fwd:block2 | 0.405 | 0.405 | 0.01 | 0.000 | ok | 5% |
| fwd:block3 | 0.407 | 0.407 | 0.01 | 0.000 | ok | 5% |
| fwd:block4 | 0.405 | 0.406 | 0.13 | 0.001 | ok | 5% |
| fwd:block5 | 0.405 | 0.405 | 0.00 | 0.000 | ok | 5% |
| fwd:head+loss | 17.309 | 17.311 | 0.01 | 0.002 | ok | 5% |
| bwd | 33.151 | 33.170 | 0.06 | 0.019 | ok | 5% |
| bwd:head+loss | 23.414 | 23.432 | 0.07 | 0.017 | ok | 5% |
| bwd:stack | 9.516 | 9.520 | 0.04 | 0.004 | ok | 5% |
| bwd:block5 | 1.574 | 1.575 | 0.01 | 0.000 | ok | 5% |
| bwd:block4 | 1.583 | 1.584 | 0.05 | 0.001 | ok | 5% |
| bwd:block3 | 1.587 | 1.589 | 0.15 | 0.002 | ok | 5% |
| bwd:block2 | 1.580 | 1.581 | 0.07 | 0.001 | ok | 5% |
| bwd:block1 | 1.590 | 1.590 | 0.01 | 0.000 | ok | 5% |
| bwd:block0 | 1.573 | 1.573 | 0.04 | 0.001 | ok | 5% |
| bwd:embed | 0.217 | 0.217 | 0.05 | 0.000 | ok | 5% |
| opt | 6.483 | 6.480 | 0.03 | 0.002 | ok | 5% |
| opt:opt.clip | 0.597 | 0.597 | 0.01 | 0.000 | ok | 5% |
| opt:opt.polar_muon_adamw | 5.883 | 5.881 | 0.03 | 0.002 | ok | 5% |
| opt:opt.muon | 1.777 | 1.777 | 0.03 | 0.000 | ok | 5% |
| opt:opt.adamw | 4.103 | 4.101 | 0.04 | 0.002 | ok | 5% |
| checkpoint save | 237.658 | 238.338 | 0.29 | 0.679 | ok | 5% |

### 3.2 RTX 5070 Ti Linux — MTP pair at 100 steps (`rtx5070ti_mtp` vs `rtx5070ti_mtp-run2`, 28 of 28 PASS)

| part | run 1 (ms) | run 2 (ms) | gap % | gap ms | verdict | rule |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| step (clean) | 104.694 | 104.357 | 0.32 | 0.337 | ok | 5% |
| data | 0.014 | 0.016 | 18.51 | 0.003 | ok | **0.05 ms** |
| fwd | 37.291 | 37.258 | 0.09 | 0.033 | ok | 5% |
| fwd:embed | 0.288 | 0.288 | 0.03 | 0.000 | ok | 5% |
| fwd:stack | 2.417 | 2.418 | 0.06 | 0.001 | ok | 5% |
| fwd:block0 | 0.397 | 0.398 | 0.32 | 0.001 | ok | 5% |
| fwd:block1 | 0.403 | 0.403 | 0.05 | 0.000 | ok | 5% |
| fwd:block2 | 0.403 | 0.403 | 0.03 | 0.000 | ok | 5% |
| fwd:block3 | 0.404 | 0.404 | 0.13 | 0.001 | ok | 5% |
| fwd:block4 | 0.402 | 0.403 | 0.04 | 0.000 | ok | 5% |
| fwd:block5 | 0.403 | 0.403 | 0.05 | 0.000 | ok | 5% |
| fwd:head+loss | 34.581 | 34.544 | 0.11 | 0.037 | ok | 5% |
| bwd | 56.567 | 56.401 | 0.29 | 0.166 | ok | 5% |
| bwd:head+loss | 46.818 | 46.732 | 0.18 | 0.086 | ok | 5% |
| bwd:stack | 9.521 | 9.440 | 0.85 | 0.080 | ok | 5% |
| bwd:block5 | 1.578 | 1.574 | 0.20 | 0.003 | ok | 5% |
| bwd:block4 | 1.592 | 1.570 | 1.41 | 0.022 | ok | 5% |
| bwd:block3 | 1.596 | 1.567 | 1.83 | 0.029 | ok | 5% |
| bwd:block2 | 1.581 | 1.569 | 0.76 | 0.012 | ok | 5% |
| bwd:block1 | 1.580 | 1.568 | 0.73 | 0.011 | ok | 5% |
| bwd:block0 | 1.570 | 1.573 | 0.14 | 0.002 | ok | 5% |
| bwd:embed | 0.219 | 0.217 | 0.80 | 0.002 | ok | 5% |
| opt | 10.838 | 10.818 | 0.18 | 0.019 | ok | 5% |
| opt:opt.clip | 1.120 | 1.120 | 0.05 | 0.001 | ok | 5% |
| opt:opt.polar_muon_adamw | 9.707 | 9.696 | 0.11 | 0.011 | ok | 5% |
| opt:opt.muon | 1.778 | 1.781 | 0.17 | 0.003 | ok | 5% |
| opt:opt.adamw | 7.926 | 7.912 | 0.17 | 0.014 | ok | 5% |
| checkpoint save | 448.607 | 440.749 | 1.78 | 7.859 | ok | 5% |

---

## 4. RTX 5070 Ti, Windows WDDM — Out of Scope (27/27 code parts PASS; Windows disk gap recorded)

- **GPU:** NVIDIA GeForce RTX 5070 Ti (16 GB, Windows WDDM driver `610.88`, display attached to the same GPU)
- **Commit:** `f1ed7f2daf525242d84e4daf45c9d0247583ed71` (`g6/dev`, clean tree `dirty: false` in all 4 runs)
- **Run IDs:** `86baa9a5452b4a81bd7d4217062dc2a7` (`run1`), `5069707b7d3e4cd6ba86a46f46b4a7f1` (`run2`), `56732aeb…` (`run3`), `850c6caf…` (`run4`)
- **Command:** `python -u -m perfkit.bench --config configs/base.yaml --level 3 --repeat 4 --tag local_5070ti_20261031_set2`
- **Run files:** <https://gist.github.com/jssunil/a8180d70598e5a62d7534d252b5cdc08>

Across all $\binom{4}{2} = 6$ pairs on Windows, **every one of the 27 code/compute/data parts passes within 5%** ($\le 2.18\%$). Only `checkpoint save` failed in the 3 pairs involving `run2` (7.65%, 8.76%, and 9.52% gaps: `write_ms` moved from 405.97 ms to 440.70 ms due to Windows NTFS/Defender/fsync jitter on the local volume, while the same physical GPU on Linux passes checkpoint save at 0.29–2.8% in Section 3).

**Decision (closed):** **Windows WDDM is recorded as out of scope** for benchmark gating. We do not run training or performance benchmarks on Windows/WDDM; the Linux run on the same RTX 5070 Ti hardware (Section 3) is the passing evidence.

**Full 28-part table for `run1` vs `run2` on Windows WDDM (27/27 code parts PASS; `checkpoint save` disk write outside):**

| part | run 1 (ms) | run 2 (ms) | gap % | gap ms | verdict | rule |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| step (clean) | 64.680 | 64.718 | 0.06 | 0.038 | ok | 5% |
| data | 0.111 | 0.112 | 1.27 | 0.001 | ok | 5% |
| fwd | 20.649 | 20.705 | 0.27 | 0.056 | ok | 5% |
| fwd:embed | 0.326 | 0.327 | 0.31 | 0.001 | ok | 5% |
| fwd:stack | 3.161 | 3.168 | 0.23 | 0.007 | ok | 5% |
| fwd:block0 | 0.550 | 0.548 | 0.41 | 0.002 | ok | 5% |
| fwd:block1 | 0.516 | 0.515 | 0.18 | 0.001 | ok | 5% |
| fwd:block2 | 0.513 | 0.514 | 0.14 | 0.001 | ok | 5% |
| fwd:block3 | 0.518 | 0.518 | 0.08 | 0.000 | ok | 5% |
| fwd:block4 | 0.515 | 0.516 | 0.20 | 0.001 | ok | 5% |
| fwd:block5 | 0.514 | 0.516 | 0.39 | 0.002 | ok | 5% |
| fwd:head+loss | 17.147 | 17.201 | 0.32 | 0.054 | ok | 5% |
| bwd | 35.854 | 35.913 | 0.16 | 0.059 | ok | 5% |
| bwd:head+loss | 23.691 | 23.736 | 0.19 | 0.046 | ok | 5% |
| bwd:stack | 11.729 | 11.734 | 0.04 | 0.005 | ok | 5% |
| bwd:block5 | 1.960 | 1.941 | 0.98 | 0.019 | ok | 5% |
| bwd:block4 | 1.947 | 1.965 | 0.93 | 0.018 | ok | 5% |
| bwd:block3 | 1.939 | 1.944 | 0.28 | 0.005 | ok | 5% |
| bwd:block2 | 1.927 | 1.934 | 0.38 | 0.007 | ok | 5% |
| bwd:block1 | 1.927 | 1.938 | 0.54 | 0.010 | ok | 5% |
| bwd:block0 | 1.909 | 1.927 | 0.89 | 0.017 | ok | 5% |
| bwd:embed | 0.425 | 0.434 | 2.18 | 0.009 | ok | 5% |
| opt | 8.173 | 8.214 | 0.50 | 0.041 | ok | 5% |
| opt:opt.clip | 0.646 | 0.646 | 0.02 | 0.000 | ok | 5% |
| opt:opt.polar_muon_adamw | 7.522 | 7.566 | 0.59 | 0.045 | ok | 5% |
| opt:opt.muon | 3.280 | 3.315 | 1.06 | 0.035 | ok | 5% |
| opt:opt.adamw | 4.245 | 4.245 | 0.01 | 0.000 | ok | 5% |
| checkpoint save | 419.305 | 456.043 | 8.76 | 36.738 | **outside** | - |

---

## 5. Modal A100-80GB — PASS (Normal & 100-step MTP reruns, 1 Nov)

On pre-fix commits (PR #31), CPU-paced parts (`opt.muon`, `fwd:embed`, `fwd:block0`) moved >5% between runs on Modal A100-80GB. Rerunning `--repeat 2` on the current `g6/dev` codebase (with batched Muon, foreach AdamW, and batch prefetch $\to$ `trace.host_syncs_per_step = 1`) closes both the Modal A100-80GB case and the 100-step MTP case.

### 5.1 Modal A100-80GB: Normal pair (`modal_a100_v1`, 100 steps) — PASS, 28 of 28

- **GPU:** NVIDIA A100 80GB PCIe (`bf16`, `B=16`, `T=256`, 100 steps after 10 warmup, `trace.host_syncs_per_step = 1` in both runs, GPU busy 51–54%)
- **Commit:** `7bc8beecefd0ab6584bfa233fca38d02710af412` (`g6/dev`, clean tree `dirty: false` in both runs)
- **Run IDs:** `43e5077125e146868fdb87669099afad` (run 1) / `24a2483666ce4beba4525cfed5a247fc` (run 2)
- **Command:** `python -m perfkit.bench --config configs/base.yaml --level 3 --repeat 2 --tag modal_a100_v1`
- **Run files:** <https://gist.github.com/varshith2000/55800d512eae8878af294e274e15ff8b>

**Result: PASS, 28 of 28 gated parts — every part passed by the 5% rule (0 needed the 0.05 ms rule).** The three formerly-missed parts (`opt:opt.muon` 1.04%, `fwd:embed` 0.26%, `fwd:block0` 0.22%) are all well within 5%.

| part | run 1 (ms) | run 2 (ms) | gap % | gap ms | verdict | rule |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| step (clean) | 39.308 | 39.401 | 0.24 | 0.093 | ok | 5% |
| data | 0.019 | 0.019 | 0.00 | 0.000 | ok | 5% |
| fwd | 12.883 | 12.896 | 0.10 | 0.013 | ok | 5% |
| fwd:embed | 0.394 | 0.395 | 0.26 | 0.001 | ok | 5% |
| fwd:stack | 2.803 | 2.815 | 0.44 | 0.012 | ok | 5% |
| fwd:block0 | 0.464 | 0.465 | 0.22 | 0.001 | ok | 5% |
| fwd:block1 | 0.465 | 0.467 | 0.44 | 0.002 | ok | 5% |
| fwd:block2 | 0.464 | 0.467 | 0.66 | 0.003 | ok | 5% |
| fwd:block3 | 0.465 | 0.466 | 0.22 | 0.001 | ok | 5% |
| fwd:block4 | 0.465 | 0.466 | 0.22 | 0.001 | ok | 5% |
| fwd:block5 | 0.465 | 0.466 | 0.33 | 0.002 | ok | 5% |
| fwd:head+loss | 9.676 | 9.677 | 0.01 | 0.001 | ok | 5% |
| bwd | 21.694 | 21.740 | 0.21 | 0.045 | ok | 5% |
| bwd:head+loss | 10.841 | 10.843 | 0.02 | 0.002 | ok | 5% |
| bwd:stack | 10.430 | 10.470 | 0.39 | 0.040 | ok | 5% |
| bwd:block5 | 1.733 | 1.739 | 0.35 | 0.006 | ok | 5% |
| bwd:block4 | 1.733 | 1.739 | 0.32 | 0.006 | ok | 5% |
| bwd:block3 | 1.734 | 1.742 | 0.47 | 0.008 | ok | 5% |
| bwd:block2 | 1.734 | 1.740 | 0.35 | 0.006 | ok | 5% |
| bwd:block1 | 1.735 | 1.742 | 0.44 | 0.008 | ok | 5% |
| bwd:block0 | 1.734 | 1.741 | 0.41 | 0.007 | ok | 5% |
| bwd:embed | 0.419 | 0.422 | 0.73 | 0.003 | ok | 5% |
| opt | 4.854 | 4.881 | 0.57 | 0.028 | ok | 5% |
| opt:opt.clip | 0.376 | 0.376 | 0.00 | 0.000 | ok | 5% |
| opt:opt.polar_muon_adamw | 4.472 | 4.499 | 0.61 | 0.027 | ok | 5% |
| opt:opt.muon | 2.310 | 2.334 | 1.04 | 0.024 | ok | 5% |
| opt:opt.adamw | 2.151 | 2.154 | 0.12 | 0.003 | ok | 5% |
| checkpoint save | 797.917 | 824.692 | 3.36 | 26.775 | ok | 5% |

### 5.2 Modal A100-80GB: MTP pair at 100 steps (`modal_a100_mtp_v1`) — PASS, 28 of 28

- **GPU:** NVIDIA A100-SXM4-80GB (`bf16`, `B=16`, `T=256`, `model.mtp=true`, **100 measured steps** after 10 warmup, `trace.host_syncs_per_step = 1` in both runs, GPU busy 85.9–89.3%)
- **Commit:** `67ba1efe867aa4044d18b1355867457c8a8b2141` (`g6/dev`, clean tree `dirty: false` in both runs)
- **Run IDs:** `f9a3710b8436459189cb19d8bfb187ba` (run 1) / `b929ba25a33240eea73e4cda5508b31f` (run 2)
- **Command:** `python -m perfkit.bench --config configs/base.yaml --level 3 --repeat 2 --tag modal_a100_mtp_v1 model.mtp=true`
- **Run files:** <https://gist.github.com/varshith2000/55800d512eae8878af294e274e15ff8b>

**Result: PASS, 28 of 28 gated parts at 100 steps — every part passed by the 5% rule (0 needed the 0.05 ms rule).** This closes the 100-step MTP repeat check.

| part | run 1 (ms) | run 2 (ms) | gap % | gap ms | verdict | rule |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| step (clean) | 59.867 | 59.714 | 0.26 | 0.153 | ok | 5% |
| data | 0.023 | 0.023 | 0.00 | 0.000 | ok | 5% |
| fwd | 21.785 | 21.760 | 0.11 | 0.025 | ok | 5% |
| fwd:embed | 0.398 | 0.395 | 0.78 | 0.003 | ok | 5% |
| fwd:stack | 2.811 | 2.791 | 0.70 | 0.019 | ok | 5% |
| fwd:block0 | 0.463 | 0.459 | 0.89 | 0.004 | ok | 5% |
| fwd:block1 | 0.464 | 0.461 | 0.67 | 0.003 | ok | 5% |
| fwd:block2 | 0.465 | 0.461 | 0.89 | 0.004 | ok | 5% |
| fwd:block3 | 0.465 | 0.461 | 0.89 | 0.004 | ok | 5% |
| fwd:block4 | 0.465 | 0.462 | 0.67 | 0.003 | ok | 5% |
| fwd:block5 | 0.464 | 0.462 | 0.55 | 0.003 | ok | 5% |
| fwd:head+loss | 18.561 | 18.559 | 0.01 | 0.002 | ok | 5% |
| bwd | 31.292 | 31.219 | 0.23 | 0.073 | ok | 5% |
| bwd:head+loss | 20.484 | 20.483 | 0.01 | 0.001 | ok | 5% |
| bwd:stack | 10.385 | 10.314 | 0.69 | 0.072 | ok | 5% |
| bwd:block5 | 1.722 | 1.713 | 0.54 | 0.009 | ok | 5% |
| bwd:block4 | 1.724 | 1.709 | 0.90 | 0.015 | ok | 5% |
| bwd:block3 | 1.724 | 1.713 | 0.66 | 0.011 | ok | 5% |
| bwd:block2 | 1.723 | 1.713 | 0.63 | 0.011 | ok | 5% |
| bwd:block1 | 1.727 | 1.717 | 0.60 | 0.010 | ok | 5% |
| bwd:block0 | 1.724 | 1.712 | 0.72 | 0.012 | ok | 5% |
| bwd:embed | 0.417 | 0.414 | 0.74 | 0.003 | ok | 5% |
| opt | 6.935 | 6.893 | 0.60 | 0.041 | ok | 5% |
| opt:opt.clip | 0.592 | 0.591 | 0.17 | 0.001 | ok | 5% |
| opt:opt.polar_muon_adamw | 6.333 | 6.292 | 0.66 | 0.041 | ok | 5% |
| opt:opt.muon | 2.352 | 2.316 | 1.55 | 0.036 | ok | 5% |
| opt:opt.adamw | 3.967 | 3.964 | 0.08 | 0.003 | ok | 5% |
| checkpoint save | 1673.459 | 1723.982 | 3.02 | 50.523 | ok | 5% |

---

## 6. Case summary & TSAI job runs

| # | Case | Owner | Status |
| :--- | :--- | :--- | :--- |
| 1 | Modal A100-80GB (`--repeat 2` on current commit) | Varshith | **Closed (1 Nov): PASS 28 of 28** (`opt:opt.muon` 1.04%, `fwd:embed` 0.26%, `fwd:block0` 0.22%, Section 5.1). |
| 2 | MTP pair rerun at 100 steps | Varshith / Raj | **Closed (1 Nov): PASS 28 of 28** at `bench.steps=100` on Modal A100-SXM4-80GB (Section 5.2), matching Vaibhav's Colab A100 pair (Section 2.2) and Sunil's Linux RTX 5070 Ti pairs (Section 3.2). |
| 3 | Windows checkpoint save | Sunil / Varshith | **Closed: Windows WDDM recorded as out of scope** (Section 4). All 27 code parts pass; the 7.7–9.5% gap is Windows disk/fsync variance, and all project benchmarks target Linux. |
| 4 | TSAI job runs (baseline pair + pair per arm) | Varshith / Sunil | Submit via `JOB_REQUEST.md` (`teams/06-performance/jobs/<YYYY-MM-DD>-<short-name>.md`) with the baseline pair (`configs/base.yaml --repeat 2`) and the `--repeat 2` pair for each A/B arm (`optim.muon_impl`, `optim.adamw_impl`, `data.prefetch`, `model.moe.dispatch`, and G5 architecture arms), attaching the Colab / Modal test logs above. |

**CUDA-graph fallback rule (if any future host or MoE arm still fails on host-paced parts):**
 because Modal A100-80GB passed 28 of 28 on the current commit, the CUDA-graph fallback was not needed for the baseline model. If a host or MoE arm later fails due to host pacing, capture the optimizer step (`opt.polar_muon_adamw`) as a CUDA graph (`PARTS.md`), keep the uncaptured step as the reference implementation, and add a `@pair` correctness test (captured vs uncaptured on identical inputs and gradients) before trusting the captured timings.

---

## 7. Reproduce

```bash
cd teams/06-performance
python -m perfkit.bench --config configs/base.yaml --level 3 --repeat 2 --tag <name>                  # normal pair (100 steps)
python -m perfkit.bench --config configs/base.yaml --level 3 --repeat 2 --tag <name>_mtp model.mtp=true  # MTP pair (100 steps)
python -m perfkit.report results/runs/<a>.json --compare results/runs/<b>.json                          # official 5% / 0.05 ms check
```

Every table above was generated by `perfkit.report.compare` on the linked run JSONs (`tol_pct=5.0`, `gate_level=2`, `abs_tol_ms=0.05` — the defaults in `configs/base.yaml`).
