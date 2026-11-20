# Kernel proposals — dry run 2

**Status:** candidates, tests and same-container A/B done; proposal below for TSAI.  
**Sources:** `profile_dryrun1.md` and `speed_dryrun1.md` (G6 Modal A100 runs, 20 Nov 2026, and class #620), the A/B rows runs below, and the GPU test runs. Nothing else.  
**Gate 3:** each proposed change has a passing test. TSAI **decides** which land for dry run 2 (Sat 21).  
**Rule:** member-GPU results give shares, ratios and counts only; every row is compared with a torch reference measured in the same container.

| Field | Value |
| :--- | :--- |
| GPU | NVIDIA A100-SXM4-80GB (Modal), one GPU per group |
| Commit | `1f48dee8` (`g6/week_3`); the runs are tagged `-dirty` only for this file being edited (`provenance/status.txt`), no code change |
| Config | `configs/g5_t2_base.yaml` (dry run 1 model, loop dispatch, loop Muon, torch kernels), B=8, T=2048, bf16, synthetic data |
| Software | A/B: torch 2.11.0+cu130, Triton 3.6.0. Tests: torch 2.11.0 and 2.14.1+cu130 |
| Method | `perfkit.bench --modes clean,layer,trace --level 3 --repeat 2` per row; each group starts with its own `ref` row (`benchmarking/modal_dryrun1.py --what rows`), summary by `benchmarking/summarize_ab.py` |
| Run folders | `ab-ce`, `ab-attn`, `ab-moe2`, `ab-muon`, `ab-small`, `ab-all`, `ab-bal` (`ab-moe` was cut short and is replaced by `ab-moe2`) |
| Raw outputs | A/B runs: <https://gist.github.com/vaibh27/3201a544f3232f8b2e93fbcb912f7d59> (run JSONs, reports, logs with the repeat check, provenance, `summary_ab.md`). Tests: <https://gist.github.com/vaibh27/e4e60f177d4fe675ba0444054928d341> |

## Candidates (from the dry run 1 profile)

| # | profile finding (B=8) | switch | test (correctness/) | test result |
| ---: | :--- | :--- | :--- | :--- |
| 1 | full-vocab loss in fp32: `head+loss` 23% of the step | `model.ce_impl=fused_triton` (cuBLAS matmuls + Triton softmax-gradient) | `test_ce_cublas.py` (9 tests: fp32 vs full-logits CE, bf16 vs `ce.fused`, bitwise repeat, model vs torch CE) | PASS |
| 1b | same | `model.ce_impl=triton_cce` | pairs `ce.triton_cce`, `ce.triton_cce.bf16` | PASS |
| 2 | eager attention: 14.5% of the layer pass (mask + fp32 softmax) | `model.attn_impl=sdpa` | pairs `attention.causal.extended.sdpa.*`, `model.base.attn_impl_sdpa` | PASS |
| 2b | same | `model.attn_impl=triton` (`kernels/attention.py`) | `test_triton_kernels.py::test_attention_matches_eager*`, `::test_attention_backward_repeats_bitwise` | PASS |
| 3 | Muon loop path: 12.5% of the layer pass, 43% of host time (Nsight) | `optim.muon_impl=batched` | pairs `opt.muon.batched`, `opt.muon.batched.missing_grad`, `optim.muon_ns.batched` | PASS |
| 4 | loop MoE dispatch: 256 host syncs per step | `model.moe.dispatch=sorted` | pairs `moe.sorted.*` (14) | PASS |
| 4b | same | `model.moe.dispatch=grouped` (fixed capacity, no host sync) | pairs `moe.grouped.*` (14) | PASS |
| 5 | RMSNorm (small) | `model.ln_impl=triton_ln` (`kernels/rms_norm.py`) | `test_triton_kernels.py::test_rms_norm_*`, pair `ln.triton` | PASS |
| 6 | RoPE (small) | `model.rope_impl=triton` | `test_triton_kernels.py::test_rope_matches_apply_rope_on_the_qkv_view` | PASS |
| 7 | SwiGLU (small) | `model.swiglu_impl=triton` | `test_triton_kernels.py::test_swiglu_matches_torch`, `test_swiglu.py` | PASS |
| 8 | router (small) | `model.moe.router_impl=triton` | `test_triton_kernels.py::test_router_matches_torch`, `::test_moe_router_switch_and_forced_routing` | PASS |
| all | every switch together | rows `all_sdpa`, `all_triton` | `test_triton_kernels.py::test_full_model_with_every_triton_switch_matches_torch`, `::test_full_model_triton_switches_under_compile` | PASS |

Cast and copy kernels (17–19% of GPU kernel time) have no switch yet: not proposed.

### Test evidence

`pytest correctness -q --all-configs -rs` on Modal A100, `g6/week_3` with the Triton norm fix (`tl.cast` for `GROUPS` and `M` in `kernels/layer_norm.py` and `kernels/rms_norm.py`):

| torch | result | pairs |
| :--- | :--- | :--- |
| 2.11.0+cu130 (Triton 3.6.0) | 1371 passed, 0 failed, 10 skipped, 12 xfailed | 134 of 134 PASS |
| 2.14.1+cu130 (Triton 3.8.0) | 1371 passed, 0 failed, 10 skipped, 12 xfailed | 134 of 134 PASS |

Skips: 6 CPU cases of the CUDA-only CE kernels, 3 that need two GPUs, 1 opt-in stress case. Logs: gist `tests_fixed_torch2.11.0.log`, `tests_fixed_torch2.14.1.log`.

## A/B results (same-container, against `ref`)

How to read the tables:

- **step vs ref**: clean step (100 steps after 10 warmup), mean of the two runs, against the `ref` row of the same container. Negative is faster.
- **head+loss / attn / muon.ns / dispatch**: share of the layer-pass step (level 3, summed over the 8 layers).
- **active slots**: expert slots with tokens, from the `models/moe.py:81` sync count (loop dispatch only).
- **step repeat**: the clean step of run 2 against run 1 (5% check). **parts repeat**: the full perfkit check over 30 gated parts; when it fails, the failing parts are listed.
- Only rows in the same table are compared. The `ref` step differs by up to 35% between containers (GPU busy 74–86%), because the loop paths are host-bound and the host differs from container to container.

### ce

| row | step vs ref | tokens/s | peak GiB | head+loss | GPU busy | step repeat | parts repeat |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| `ref` | - | - | 44.3 | 25.1% | 85.2% | ok | PASS |
| `ce_fused_triton` | **-9.4%** | 1.10x | **22.4** | 14.6% | 83.2% | ok (0.1%) | FAIL: `opt`, `opt.muon` (8.6%, 9.1%) |
| `ce_triton_cce` | +6.5% | 0.94x | 22.4 | 31.2% | 85.1% | ok (2.9%) | FAIL: `opt`, `opt.muon`, block 6 |

- `fused_triton` halves `head+loss` and halves peak memory (no full fp32 logits). `triton_cce` saves the same memory but is slower than torch here: not proposed.

### attn

| row | step vs ref | tokens/s | peak GiB | attn | GPU busy | step repeat | parts repeat |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| `ref` | - | - | 44.3 | 16.0% | 86.3% | ok | PASS |
| `attn_sdpa` | **-25.5%** | 1.34x | 32.3 | 0.9% | 76.5% | ok (0.1%) | FAIL: `opt`, `opt.muon`, `opt.clip`, block 0, `fwd:stack` |
| `attn_triton` | -23.9% | 1.31x | 32.3 | 2.1% | 78.3% | ok | FAIL: `opt`, `opt.muon`, block 0 |

- SDPA (flash backend) takes attention from 16% of the layer pass to under 1%. Our Triton kernel is close but 1.6 points slower: propose SDPA.
- GPU busy drops because the GPU work shrank while the host-bound loop paths (Muon, dispatch) stayed.

### moe (dispatch)

| row | step vs ref | tokens/s | peak GiB | dispatch | muon.ns | GPU busy | syncs/step | step repeat | parts repeat |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| `ref` (loop) | - | - | 44.3 | 5.9% | 12.3% | 76.1% | 147 | ok | PASS |
| `disp_sorted` | +1.2% | 0.99x | 56.5 | 8.7% | 35.7% | 55.9% | 9 | ok | PASS |
| `disp_grouped` | +22.8% | 0.81x | 70.5 | 13.6% | 30.0% | 58.5% | 1 | ok | PASS |

- Both cut the host syncs (147 to 9 and 1) but neither is faster, and both use more memory. Two reasons, both visible in the parts:
  - **Padding.** Both run the experts as one batched GEMM over a padded `[E, cap, dim]` buffer (`models/moe.py:87`). `sorted` pads every expert to the busiest one; `grouped` pads every expert to `N × top_k`, so it computes 16 × the routed tokens. With a skewed router this is mostly padding: forward + backward of the layer pass is 1.3× (`sorted`) and 1.7× (`grouped`) of loop dispatch.
  - **Optimizer.** `sorted` and `grouped` give idle experts zero gradients where loop leaves `None` (`models/moe.py:19`), so loop Muon runs Newton-Schulz on all 128 expert matrices instead of the 18 active ones: `opt` is about 3× the `ref`'s in the layer pass.
- The partial `ab-moe` run (other container) agrees: `sorted` -0.7%, `grouped` +21.5%.
- Not proposed for dry run 2. The fix is a dropless grouped GEMM over the ragged per-expert segments (no padding, no host sync), as in MegaBlocks and `torch._grouped_mm`; not in the repo yet and has no test.

### muon

| row | step vs ref | tokens/s | peak GiB | muon.ns | GPU busy | step repeat | parts repeat |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| `ref` | - | - | 44.3 | 12.1% | 76.9% | ok | PASS |
| `muon_batched` | **-33.8%** | **1.51x** | 44.4 | 2.1% | 92.2% | ok (0.1%) | **PASS** |

- The largest single gain. Batching Newton-Schulz across same-shape matrices removes most of the launches and host time: GPU busy goes from 77% to 92%, `opt` from 18% to 4% of the layer pass.

### small (norm, RoPE, SwiGLU, router)

| row | step vs ref | tokens/s | peak GiB | GPU busy | step repeat | parts repeat |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| `ref` | - | - | 44.3 | 86.0% | ok (0.6%) | FAIL: `opt`, `opt.muon` |
| `ln_triton` | **-3.1%** | 1.03x | 43.8 | 84.7% | ok | PASS |
| `router_triton` | -2.0% | 1.02x | 44.3 | 84.2% | ok (2.2%) | FAIL: `opt`, `opt.muon` |
| `rope_triton` | -0.2% | 1.00x | 44.3 | 85.8% | ok (1.1%) | PASS |
| `swiglu_triton` | +1.8% | 0.98x | 43.8 | 87.1% | ok (1.6%) | FAIL: `opt`, `opt.muon` |

- `ln_triton` is a small, clean gain. `router_triton` is at the edge of the run-to-run spread (step repeats differ by up to 2.2%). RoPE and SwiGLU are within the spread: no measurable gain.

### all

| row | step vs ref | tokens/s | peak GiB | head+loss | attn | muon.ns | dispatch | GPU busy | step repeat | parts repeat |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| `ref` | - | - | 44.3 | 25.2% | 16.0% | 7.8% | 5.6% | 86.0% | ok | PASS |
| `all_sdpa` | **-57.7%** | **2.36x** | **8.2** | 33.0% | 1.6% | 5.1% | 16.4% | 84.6% | ok (1.0%) | FAIL: 10 single blocks |
| `all_triton` | -54.6% | 2.20x | 8.2 | 29.8% | 3.6% | 4.4% | 14.3% | 89.2% | ok (0.1%) | FAIL: block 0 |

- `all_*` = `ce_impl=fused_triton`, `ln_impl=triton_ln`, `rope_impl=triton`, `swiglu_impl=triton`, `router_impl=triton`, `muon_impl=batched`, plus the attention switch; dispatch stays loop.
- The single-row gains compound as expected: 0.66 (Muon) × 0.75 (SDPA) × 0.91 (CE) × 0.97 (norm) × 0.98 (router) = 0.42 of the `ref` step, against 0.42 measured.
- Peak memory falls from 44.3 to 8.2 GiB, so dry run 2 can raise the micro-batch or keep more activations.
- The parts check fails on single blocks only (3–6 ms each, 5–32% apart between runs); the step repeats within 1%. With the fast kernels in, each block is dominated by the loop dispatch's host syncs (147 per step), so block times follow host jitter.
- What is left after these switches: `head+loss` 30–33% and loop dispatch 14–16% of the layer pass.

### bal (load balancing on, `model.moe.bias_gamma=0.01`)

| row | step vs ref | tokens/s | peak GiB | muon.ns | dispatch | GPU busy | syncs/step | active slots | step repeat | parts repeat |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| `ref_bal` | - | - | 44.3 | 15.2% | 7.0% | 75.4% | 177 | 48 of 128 | OUTSIDE (5.1%) | FAIL: step |
| `muon_batched_bal` | **-24.8%** | 1.33x | 44.4 | 3.1% | 7.6% | 92.2% | 176 | 47 of 128 | ok (0.2%) | **PASS** |
| `disp_sorted_bal` | -7.1% | 1.08x | 52.0 | 28.9% | 10.1% | 69.5% | 9 | - | ok (2.8%) | PASS |
| `disp_grouped_bal` | +32.7% | 0.75x | 70.5 | 22.5% | 14.9% | 74.1% | 1 | - | ok (0.2%) | FAIL: `opt`, `opt.muon` |
| `all_sdpa_bal` | **-58.3%** | **2.40x** | 8.2 | 7.2% | 20.1% | 78.9% | 170 | 41 of 128 | OUTSIDE (6.4%) | FAIL: step and 16 parts |

- Balancing spreads the router from 18 to 41–48 of 128 slots within the run. The routing keeps changing while the bias adapts, so `ref_bal` and `all_sdpa_bal` move 5–6% between runs: read this group as direction, not as a gated number.
- The ranking holds with more experts active: `all_sdpa` 2.4×, `muon_batched` 1.3×. `sorted` turns slightly faster (less padding with a flatter router); `grouped` stays slower.

## Ranked proposals

Ranked by step change against the same-container `ref`. Kept: faster beyond the run-to-run spread, with the step repeating within 5%. RoPE and SwiGLU show no gain alone but are in the measured set, so the proposal is exactly the `all_sdpa` row; dispatch stays `loop`.

| rank | change | why (profile part, A/B) | test | test result |
| ---: | :--- | :--- | :--- | :--- |
| 1 | `optim.muon_impl=batched` | Muon loop path (43% of host time in Nsight); -33.8% step, 1.51x tokens/s, parts PASS; -24.8% with balancing | pairs `opt.muon.batched`, `opt.muon.batched.missing_grad`, `optim.muon_ns.batched` | PASS |
| 2 | `model.attn_impl=sdpa` | eager attention 16% of the layer pass, to under 1%; -25.5% step, 1.34x | pairs `attention.causal.extended.sdpa.*`, `model.base.attn_impl_sdpa` | PASS |
| 3 | `model.ce_impl=fused_triton` | full-vocab fp32 loss; -9.4% step, peak 44.3 to 22.4 GiB | `test_ce_cublas.py` | PASS |
| 4 | `model.ln_impl=triton_ln` | RMSNorm; -3.1% step, parts PASS | `test_triton_kernels.py::test_rms_norm_*`, pair `ln.triton` | PASS |
| 5 | `model.moe.router_impl=triton` | router; -2.0% step (at the edge of the spread) | `test_triton_kernels.py::test_router_matches_torch`, `::test_moe_router_switch_and_forced_routing` | PASS |
| 6 | `model.rope_impl=triton` | RoPE; neutral alone (-0.2%), part of the measured set | `test_triton_kernels.py::test_rope_matches_apply_rope_on_the_qkv_view` | PASS |
| 7 | `model.swiglu_impl=triton` | SwiGLU; neutral alone (+1.8%, inside the spread), part of the measured set | `test_triton_kernels.py::test_swiglu_matches_torch`, `test_swiglu.py` | PASS |
| set | 1–7 together, row `all_sdpa` | -57.7% step, **2.36x tokens/s**, peak 8.2 GiB; -58.3% / 2.40x with balancing | `test_full_model_with_every_triton_switch_matches_torch`, `::test_full_model_triton_switches_under_compile` | PASS |

Not proposed:

| change | why |
| :--- | :--- |
| `model.attn_impl=triton` | passes, but 1.6 points slower than SDPA (-23.9% vs -25.5%; -54.6% vs -57.7% in the full set) |
| `model.ce_impl=triton_cce` | +6.5% step, slower than torch |
| `model.moe.dispatch=sorted` | +1.2% (collapsed router), -7.1% (balanced); more memory; doubles Muon's work under loop Muon |
| `model.moe.dispatch=grouped` | +23% / +33% step, peak 70.5 GiB (pads every expert to `N × top_k`) |

## Limits

- Synthetic data and a collapsed router in all groups but `bal` (18 of 128 expert slots active; `profile_dryrun1.md`, Routing state). `bal` reaches 41–48 of 128, still not fully balanced.
- One GPU type (A100, Modal, shared cloud GPU); dry run 1 ran on an RTX 3090. The gains come mostly from fewer launches and host syncs, which should carry over, but the size of each gain will differ.
- The `ref` step varies up to 35% between containers: only same-table rows are compared.
- The perfkit parts check (30 parts) fails on several rows while their step repeats within 3%: the failing parts are the host-bound loop paths (`opt.muon` on the loop path, single blocks under loop dispatch).
- The A/B ran on torch 2.11.0; the lab ran torch 2.14.1. Tests pass on both.
- B=8 in one pass; the lab used 8 accumulated micro-steps of B=1.
- Dispatch: no dropless grouped GEMM exists in the repo; the next MoE step after dry run 2.
