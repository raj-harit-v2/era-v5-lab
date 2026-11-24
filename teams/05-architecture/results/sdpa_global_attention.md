# Global SDPA attention (follow-up to #536)

**Status:** code, CPU and CUDA tests done; dry run 2 A/B on the current `dryrun2.yaml` done on one A100-80GB (1.05x, 1.5 GB less peak).
**Default:** unchanged (eager). Switching dry run 2 is a Team 5/TSAI call; the `dryrun2_sdpa` arm is ready.
**Scope:** WO2 is the G5 trainer that dry run 2 runs. The G6 perfkit default stays eager (perfkit supports `attn_impl: sdpa` as an option).

## What changes

- `model.attn_impl` accepts `eager` (default, unchanged) or `sdpa`.
- With `sdpa`, global layers call `F.scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=...)` on the shared K/V heads. No `T x T` score matrix is materialised and K/V are not copied per query head.
- Backend: Flash. Profiled on A100 with no backend forced, under the trainer's deterministic settings: the attention kernels are Flash, not the math fallback, and Flash alone serves the call (GQA, causal, bf16, head dim 64).
- Local layers (window, sinks) always use the eager path. Config v1 has no local layers, so every layer uses SDPA there.
- No new parameters or state: checkpoints load in either mode.
- Arm `configs/arms/dryrun2_sdpa.yaml` is `dryrun2.yaml` plus `model.attn_impl: sdpa`, for the A/B.

## Expected numeric change

**The loss trace and final model hash will not match an eager run.** This is expected: eager materialises the full score matrix in fp32 and runs a separate softmax; the fused SDPA kernel never materialises it and rounds differently. A same-seed SDPA run repeats bitwise under the trainer's deterministic settings (`test_bf16_sdpa_backward_repeats_bitwise`, CUDA).

## Evidence

Official Gate 2 A/B by TSAI (#536 at `91e00cd`, T2 Muon arm, seed 1234, bf16, steps 6-20; `gate2_speedup_ab.md`):

| variant | median step | baseline / variant | peak GPU allocation |
| :--- | ---: | ---: | ---: |
| eager | 2,088.1 ms | 1.000x | 11.12 GiB |
| SDPA | 1,902.3 ms | 1.098x | 9.56 GiB |

Dry run 2 A/B on the current `dryrun2.yaml` (class main `eef1834d`: KAS V2 head, Muon lr 0.006, router default; the same G5 code as `g6/dev`). One A100-80GB on Modal, torch 2.14.1+cu130, both arms in the same container, 20 timed steps after 3 warm-up, synthetic tokens (same model and batch shape as dry run 2):

| variant | median step | baseline / variant | peak allocation | first step |
| :--- | ---: | ---: | ---: | ---: |
| eager (`dryrun2.yaml`) | 1,378 ms | 1.000x | 10.39 GB | 3,563 ms |
| SDPA (`dryrun2_sdpa.yaml`) | 1,315 ms | 1.049x | 8.85 GB | 2,744 ms |

The loss traces of the two arms differ by at most 4.8e-4. An earlier A/B on the config before the KAS V2 head gave the same ratio (687 -> 655 ms, 1.049x). Method, every run and raw results: `teams/06-performance/results/speed_dryrun2.md`.

## Tests (`tests/test_week2_sdpa.py`)

| test | checks | result |
| :--- | :--- | :--- |
| `test_eager_path_matches_the_legacy_forward_bitwise` | eager output is bit-identical to the old inline code (global and local-with-sink layers) | PASS (CPU) |
| `test_sdpa_matches_eager_forward_and_gradients` | fp32 logits and every parameter gradient match eager, for MQA, GQA and MHA | PASS (CPU) |
| `test_local_layers_stay_eager` | local layers keep the eager window and sink under `sdpa` | PASS (CPU) |
| `test_sdpa_adds_no_parameters_or_state` | same state-dict keys and shapes | PASS (CPU) |
| `test_dryrun2_sdpa_arm_is_valid_and_only_changes_attention` | the arm differs from `dryrun2.yaml` only in `attn_impl` | PASS (CPU) |
| `test_unknown_attention_impl_is_refused` | validation accepts only `eager` and `sdpa` | PASS (CPU) |
| `test_bf16_sdpa_close_to_eager` | bf16 autocast output and input gradient close to eager | PASS (CUDA) |
| `test_bf16_sdpa_backward_repeats_bitwise` | two backward passes give identical gradients under deterministic mode | PASS (CUDA) |
| `test_flash_backend_runs_under_the_trainer_settings` | Flash alone runs the call (GQA, causal, bf16, deterministic mode) | PASS (CUDA) |
| `test_default_backend_is_flash` | with no backend forced, the profiled attention kernels are Flash | PASS (CUDA) |

Full G5 suite on CPU (torch 2.14.1): 263 passed, 6 skipped. On CUDA (A100-80GB): the SDPA tests pass, and the full suite passes apart from one Team 9 loader test whose script was not uploaded to the GPU container (it passes on CPU).

## Other teams

- Team 7 `layout/parallel_layout_v1.py` `shape_from_arm` counts only `attn_impl: eager` and will refuse `dryrun2_sdpa.yaml`. Parameter counts are the same; the eager attention-activation estimate becomes an upper bound.
- Team 10 `rl-loop/runtime.py` reports "G5 validate requires attn_impl eager"; that note becomes out of date.
