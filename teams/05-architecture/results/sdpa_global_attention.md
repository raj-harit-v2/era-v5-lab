# Global SDPA attention (follow-up to #536)

**Status:** code, CPU and CUDA tests done; dry run 2 A/B done on one A100-80GB (1.05x, 1.5 GB less peak).
**Decision asked of TSAI:** accept `model.attn_impl: sdpa` for dry run 2, knowing the numeric trace changes.

## What changes

- `model.attn_impl` accepts `eager` (default, unchanged) or `sdpa`.
- With `sdpa`, global layers call `F.scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=...)` on the shared K/V heads. There is no `T x T` score matrix, no fp32 scores and no K/V copy per query head.
- Local layers (window, sinks) always use the eager path. Config v1 has no local layers, so every layer uses SDPA there.
- No new parameters or state: checkpoints load in either mode.
- Arm `configs/arms/dryrun2_sdpa.yaml` is `dryrun2.yaml` plus `model.attn_impl: sdpa`, for the A/B.

## Expected numeric change

**The loss trace and final model hash will not match an eager run.** This is expected: SDPA computes the scores in bf16 inside a fused kernel, while eager computes them in fp32 and runs a separate softmax. A same-seed SDPA run repeats bitwise under the trainer's deterministic settings (`test_bf16_sdpa_backward_repeats_bitwise`, CUDA).

## Evidence

Official Gate 2 A/B by TSAI (#536 at `91e00cd`, T2 Muon arm, seed 1234, bf16, steps 6-20; `gate2_speedup_ab.md`):

| variant | median step | baseline / variant | peak GPU allocation |
| :--- | ---: | ---: | ---: |
| eager | 2,088.1 ms | 1.000x | 11.12 GiB |
| SDPA | 1,902.3 ms | 1.098x | 9.56 GiB |

Dry run 2 A/B on one A100-80GB (Modal, torch 2.14.1+cu130, 20 timed steps + 3 warm-up, synthetic dry run 2 data; `g5_speed_week4.md`):

| variant | median step | baseline / variant | peak allocation | first step |
| :--- | ---: | ---: | ---: | ---: |
| eager (`dryrun2.yaml`) | 687 ms | 1.000x | 10.19 GB | 3,096 ms |
| SDPA | 655 ms | 1.049x | 8.65 GB | 2,063 ms |

The loss trace differs from the same-container baseline by at most 8.1e-5. The 2-step smoke run's 1.20x was noise; the 20-step run gives 1.05x. `test_bf16_sdpa_backward_repeats_bitwise` confirms a same-seed SDPA run repeats bitwise.

## Tests (`tests/test_week2_sdpa.py`)

| test | checks | result |
| :--- | :--- | :--- |
| `test_eager_path_matches_the_legacy_forward_bitwise` | eager output is bit-identical to the old inline code (global and local-with-sink layers) | PASS (CPU) |
| `test_sdpa_matches_eager_forward_and_gradients` | fp32 logits and every parameter gradient match eager, for MQA, GQA and MHA | PASS (CPU) |
| `test_local_layers_stay_eager` | local layers keep the eager window and sink under `sdpa` | PASS (CPU) |
| `test_sdpa_adds_no_parameters_or_state` | same state-dict keys and shapes | PASS (CPU) |
| `test_dryrun2_sdpa_arm_is_valid_and_only_changes_attention` | the arm differs from `dryrun2.yaml` only in `attn_impl` | PASS (CPU) |
| `test_bf16_sdpa_close_to_eager` | bf16 autocast output and input gradient close to eager | PASS (CUDA) |
| `test_bf16_sdpa_backward_repeats_bitwise` | two backward passes give identical gradients under deterministic mode | PASS (CUDA) |

Full G5 suite on CPU (torch 2.14.1): 212 passed, 6 skipped. On CUDA (A100-80GB, per-branch container) the two new SDPA tests pass; the container's 8 suite failures were `ModuleNotFoundError: g5_adapter` because the archived tree omitted `teams/08-monitoring`, not code failures (`g5_speed_week4.md`).

## Other teams

- Team 7 `layout/parallel_layout_v1.py` `shape_from_arm` counts only `attn_impl: eager` and will refuse `dryrun2_sdpa.yaml`. Parameter counts are the same; the eager attention-activation estimate becomes an upper bound.
- Team 10 `rl-loop/runtime.py` reports "G5 validate requires attn_impl eager"; that note becomes out of date.
