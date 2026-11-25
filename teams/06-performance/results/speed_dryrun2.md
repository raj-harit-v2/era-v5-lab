# Speed for dry run 2: G6 week-4 work on the G5 trainer

**In PR #97:** only the SDPA switch. The other rows (step caches, grouped_mm, compile, micro-batch, fused, and the combined runs) come from separate branches that are not merged; their PRs follow.

**Status:** GPU smoke, full per-branch run and merged run done. All switches on (except grouped_mm) plus compile: 1.66x at micro-batch 1, 2.02x at micro-batch 2, 0 graph breaks. Open: grouped_mm on pre-SM90 GPUs.
**Raw results:** https://gist.github.com/vaibh27/87b8ba41c1abb3a092edd29e26e07bdf
**Target:** `teams/05-architecture/harness/train_week2.py` with `configs/arms/dryrun2.yaml` (dry run 2 and the main run).
**Not ours:** the KE2 input embedding and the KAS output head (Team 4 owns their kernels).

## Branches

All five branch from `g6/dev @ 369fd0d1`. Every switch defaults to the current behaviour.

| Branch | Commit | Switch | Numeric trace |
|---|---|---|---|
| `g6/w4-g5-sdpa` | `5570bd53` | `model.attn_impl: sdpa` (global layers; local layers stay eager) | changes |
| `g6/w4-g5-step-caches` | `b7abcc3f` | none: stacked expert weights and RoPE cos/sin cached per step, skipped under `torch.compile` | bit-exact |
| `g6/w4-g5-moe-grouped-mm` | `b5b7b7ab` | `model.moe.dispatch: grouped_mm` | changes |
| `g6/w4-g5-launch-overhead` | `817e5ed3` | `run.compile: true` (blocks only); `run.micro_batch_size` (resolution key, no code) | changes |
| `g6/w4-g5-fused-norm-swiglu` | `fec6d164` | `model.norm_impl: fused`, `model.swiglu_impl: triton` | changes (small) |

Per-branch write-ups: `teams/05-architecture/results/{sdpa_global_attention,step_caches,moe_grouped_mm,launch_overhead,fused_norm_swiglu}.md`. Dry run 1 counterparts: `speed_dryrun1.md`, `profile_dryrun1.md`.

## Method

- Modal, one NVIDIA A100-SXM4-80GB container per branch, torch 2.14.1+cu130, Python 3.13. Code under test is a `git archive` of each branch's committed tip.
- Per container: the branch's new test file (CUDA-only tests included), the full G5 suite (full run only), then the bench cases. Every A/B is against a baseline run in the same container.
- Bench (`g5_speed_bench.py`): the trainer's step on the resolved dry run 2 config (T2: 8 layers, d 512, 16 experts top-2, vocab 131,072, batch 8 x 2048, Muon + AdamW, WSD, bf16 autocast) with the trainer's deterministic settings. Microbatch loop with `scored_ntp_loss` / scored count, clip, lr scale, optimizer step, CUDA sync around the timed region.
- Data is synthetic (uniform token ids, about 10% right padding per row): the real trainer needs the TSAI tokenizer, byte table and shards. Loss values are not quality numbers; traces are compared only between cases on the same data.
- Reported: median step time over the timed steps (warm-up excluded), first-step time (includes compile), peak allocated memory, max loss-trace difference vs the baseline, and model hash.

## GPU smoke (2 timed steps + 1 warm-up per case)

Indicative only: two timed steps per case. Base step time differs between containers (671 to 1031 ms on the same code), so compare only within a block.

| Branch | Case | Median ms | vs base | Peak GB | First step ms | Check |
|---|---|---|---|---|---|---|
| sdpa | base | 687 | 1.000 | 10.17 | 2791 | |
| | sdpa | 571 | **1.204** | 8.64 | 1747 | trace diff 7.3e-5 |
| cache | base (`g6/dev`) | 671 | 1.000 | 10.18 | 1903 | |
| | cache | 648 | 1.035 | 10.16 | 1769 | bitwise vs base: PASS |
| grouped_mm | base | 953 | 1.000 | 10.18 | 3520 | |
| | grouped_mm | 1104 | **0.863** | 8.74 | 2008 | trace diff 6.7e-5 |
| launch | base | 963 | 1.000 | 10.18 | 3843 | |
| | micro-batch 2 | 597 | **1.613** | 16.56 | 3190 | trace diff 7.1e-5 |
| | micro-batch 4 | 528 | **1.823** | 29.44 | 3086 | trace diff 8.2e-5 |
| | compile | 572 | **1.684** | 9.09 | 19151 | trace diff 3.8e-5, 0 graph breaks |
| | compile again | 534 | 1.804 | 9.08 | 4983 | bitwise vs compile: PASS |
| fused | base | 1031 | 1.000 | 10.18 | 3837 | |
| | fused | 1003 | 1.028 | 9.72 | 3573 | trace diff 9.1e-5 |

New test files on CUDA:

| Branch | Result |
|---|---|
| sdpa | PASS (bf16 closeness, bitwise repeat under deterministic mode) |
| cache | PASS (bf16 training bit-identical to the per-call code) |
| grouped_mm | 1 FAIL: `test_no_host_synchronisation` (see below); bf16 closeness, deterministic repeat, fp32 refusal PASS |
| launch | PASS |
| fused | PASS (Triton SwiGLU on 3D expert activations, bf16 model closeness, bitwise repeat) |

## Findings

- **SDPA:** 1.05x (full run; the smoke's 1.2x was two-step noise) and 1.5 GB less peak memory. Matches the official #536 A/B direction (1.098x, 11.12 -> 9.56 GiB).
- **Step caches:** bit-exact on CUDA (loss trace and model hash equal to `g6/dev`), 1.02x. The first version broke `torch.compile` (15 graphs per block, a recompile after every optimizer step: `torch.is_inference_mode_enabled()` and `data_ptr()` in the cache key). Fixed in `b7abcc3f`: both caches step aside while compiling; CPU tests assert 1 graph, 0 breaks and no recompiles across optimizer steps.
- **Compile:** the largest gain, 1.60x with no extra memory, 0 graph breaks, run-to-run bitwise repeatable. First step 13 to 19 s cold, 3 to 5 s with a warm inductor cache; count it outside step time.
- **Microbatch size:** 1.19x at 2 (16.8 GB, fits a 24 GB card), 1.30x at 4 (29.7 GB, does not). Changes only the summation order.
- **Fused RMSNorm + Triton SwiGLU:** 1.04x and 0.5 GB less; likely redundant once blocks are compiled (inductor fuses the same ops).
- **grouped_mm:** slower, and synchronises with the host. On CUDA devices below SM90, torch 2.14's `torch._grouped_mm` runs `_grouped_mm_fallback`, a host loop over experts (inductor's Triton grouped GEMM is also gated to SM90+). A100 (SM80) and the lab's 24 GB cards (SM86) both take this path. The routing code is not the cause. Options: H100-only, or a Triton grouped GEMM for SM80/86 (the ScatterMoE / MegaBlocks approach).

## Full per-branch run (20 timed steps + 3 warm-up, full G5 suite)

grouped_mm was left out (see Findings). Same method; raw results in volume folder `20261123-202419/`.

| Branch | Case | Median ms | vs base | Peak GB | First step ms | Check |
|---|---|---|---|---|---|---|
| sdpa | base | 687 | 1.000 | 10.19 | 3096 | |
| | sdpa | 655 | **1.049** | 8.65 | 2063 | trace diff 8.1e-5 |
| cache | base (`g6/dev`) | 662 | 1.000 | 10.20 | 1863 | |
| | cache | 647 | **1.024** | 10.18 | 1758 | bitwise vs base: PASS |
| launch | base | 679 | 1.000 | 10.20 | 2347 | |
| | micro-batch 2 | 573 | **1.186** | 16.84 | 1901 | trace diff 1.4e-4 |
| | micro-batch 4 | 523 | **1.298** | 29.72 | 1845 | trace diff 1.2e-4 |
| | compile | 423 | **1.604** | 9.10 | 13249 | trace diff 1.1e-4, 0 graph breaks |
| | compile again | 424 | 1.602 | 9.11 | 2994 | bitwise vs compile: PASS |
| fused | base | 664 | 1.000 | 10.20 | 1910 | |
| | fused | 636 | **1.044** | 9.73 | 1707 | trace diff 1.5e-4 |

Base step time is now consistent across containers (662 to 687 ms); the smoke's spread (671 to 1031 ms) came from two-step medians.

Tests: every branch's new test file passes on CUDA. Full G5 suite: 209 to 214 passed, 3 skipped, 8 failed in every container. All 8 are `ModuleNotFoundError: g5_adapter` in the Team 8 logger, expert-load and Team 7 checkpoint tests: the archived tree left out `teams/08-monitoring`. Not a code failure; the script now includes it, and the merged run repeats the suite.

Micro-batch 4 logged one allocator OOM-and-retry (4 GB request with 2 GB free on 80 GB) and still finished; reserved memory is well above the 29.7 GB allocated peak.

## Merged run, first pass (before the SwiGLU compile fix)

Branch `g6/w4-g5-merged @ b578bbc2`: the five branches merged (six conflicts resolved, CPU compile check recorded in `results/merged_g5_compile_check.md`) plus the step-cache compile fix. CPU: 236 passed, 14 skipped; a block with every switch on traces as 1 graph, 0 breaks (15 graphs, 14 breaks before the fix).
"All on" = `attn_impl: sdpa`, `norm_impl: fused`, `swiglu_impl: triton` (grouped_mm left out, see Findings). One A100-80GB container, 20 timed steps + 3 warm-up; raw results in volume folder `20261123-203952/`. This container's base was slower (773 ms) than the per-branch run (662 to 687 ms); compare within the table.

| Case | Median ms | vs base | Peak GB | First step ms | Graph breaks | Check |
|---|---|---|---|---|---|---|
| base (`dryrun2.yaml`) | 773 | 1.000 | 10.18 | 2189 | 0 | |
| all on, eager | 694 | **1.113** | 8.17 | 2040 | 0 | trace diff 9.0e-5 |
| all on, compile | 697 | **1.109** | 8.09 | 20508 | 11 | trace diff 1.3e-4 |
| all on, compile again | 659 | 1.174 | 8.09 | 6724 | 11 | bitwise vs compile: PASS |
| all on, compile, micro-batch 2 | 402 | **1.923** | 12.68 | 18079 | 11 | trace diff 1.9e-4 |
| all on, compile, micro-batch 4 | 329 | **2.349** | 21.46 | 18730 | 11 | trace diff 1.3e-4 |

Full G5 suite on CUDA: 246 passed, 3 skipped, 1 failed (`test_no_host_synchronisation`, the known grouped_mm fallback; the switch is off in every case above).

Reading:

- Compile gains nothing on top of the eager switches (697 vs 694 ms), against 1.60x for compile alone in the per-branch run. The 11 graph breaks come from `swiglu_impl: triton`: the copied kernel wrapper's `once_differentiable` backward and its `torch.cuda.device(...)` context cannot be traced by Dynamo, so every MoE layer splits the compiled block.
- Micro-batch still pays on top: 1.92x at 2 (12.7 GB, fits a 24 GB card), 2.35x at 4 (21.5 GB allocated; reserved memory is higher and one allocator OOM-and-retry was logged, so too tight for a 24 GB card).
- Peak memory with all switches on is 2 GB below base at micro-batch 1.

Fix: the SwiGLU wrapper uses the torch ops while compiling (`torch.compiler.is_compiling()`), as the step caches do; inductor fuses `silu(g) * u` itself (`g6/w4-g5-fused-norm-swiglu @ fec6d164`). New tests: a CPU test that a block with the kernel enabled traces as 1 graph, 0 breaks (fails without the fix), and the same check on CUDA.

## Merged run (all switches together)

Branch `g6/w4-g5-merged @ 1467a652` (first pass plus the SwiGLU fix). CPU: 237 passed, 15 skipped. Same cases, one A100-80GB container, 20 timed steps + 3 warm-up; raw results in volume folder `20261123-220836/`.

| Case | Median ms | vs base | Peak GB | First step ms | Graph breaks | Check |
|---|---|---|---|---|---|---|
| base (`dryrun2.yaml`) | 662 | 1.000 | 10.18 | 1806 | 0 | |
| all on, eager | 550 | **1.203** | 8.17 | 1701 | 0 | trace diff 9.0e-5 |
| all on, compile | 399 | **1.659** | 8.06 | 10551 | 0 | trace diff 1.5e-4 |
| all on, compile again | 400 | 1.655 | 8.06 | 2750 | 0 | bitwise vs compile: PASS |
| all on, compile, micro-batch 2 | 328 | **2.019** | 12.62 | 10380 | 0 | trace diff 1.4e-4 |
| all on, compile, micro-batch 4 | 296 | **2.239** | 21.36 | 10153 | 0 | trace diff 1.5e-4 |

Full G5 suite on CUDA: 248 passed, 3 skipped, 1 failed (`test_no_host_synchronisation`, the known grouped_mm fallback; off in every case above). The new CUDA no-graph-break test passes.

Reading:

- With the fix, compile works with every other switch on: 0 graph breaks, 1.38x on top of the eager switches (550 -> 399 ms), run-to-run bitwise repeatable.
- Micro-batch 2 adds 1.22x on top and fits a 24 GB card (12.6 GB). Micro-batch 4 adds a little more (2.24x) but needs 21.4 GB allocated, logged an allocator OOM-and-retry, and is too tight for 24 GB.
- First step about 10 s cold (compile), about 3 s with a warm inductor cache; it is outside the step-time median.
- Every switch on lowers peak memory by about 2 GB at micro-batch 1.

## SDPA on the current dry run 2 config (24 Nov)

Class main changed `dryrun2.yaml` after the runs above: KAS V2 output head (#717), Muon lr 0.006 (#725), router default (#736, #740). SDPA rerun on class main `eef1834d` plus the SDPA commits (the same G5 code as `g6/dev`), one A100-80GB container, 20 timed steps + 3 warm-up; raw results in run `20261124-104204`.

| Case | Median ms | vs base | Peak GB | First step ms | Check |
|---|---|---|---|---|---|
| base (`dryrun2.yaml`, eager) | 1378 | 1.000 | 10.39 | 3563 | |
| sdpa | 1315 | **1.049** | 8.85 | 2744 | trace diff 4.8e-4 |

- Same SDPA ratio as on the older config (1.049x) and the same 1.5 GB saving.
- Backend: Flash. Profiled with no backend forced under the trainer's deterministic settings, the attention kernels are Flash (not the math fallback); Flash alone also serves the call, and its backward repeats bitwise.
- The dry run 2 step on the same GPU type doubled with the new config (687 -> 1378 ms base). The KAS V2 head is the likely cause; worth a profile for Team 5.
- CUDA: SDPA tests pass; full suite passes apart from one Team 9 loader test whose script was not uploaded (passes on CPU; the driver now uploads it).

## Recommendation for the main run

1. `model.attn_impl: sdpa`, `run.compile: true`, step caches (always on), `run.micro_batch_size: 2` on 24 GB cards: about 2x the dry run 2 step on A100, same model and data. Each changes the numeric trace except the caches, so it needs TSAI's agreement before the main run.
2. `model.norm_impl: fused` and `model.swiglu_impl: triton` matter only for eager runs; under compile inductor does the same fusion. Keep them for eager fallbacks or drop them.
3. grouped_mm: off. It needs SM90+ (H100) for a fused kernel in torch 2.14; on A100 and the lab's SM86 cards it is slower. A Triton grouped GEMM for SM80/86 is the follow-up if the dense path's 8x expert FLOPs become the bottleneck.

## Reproduce

```
modal run benchmarking/modal_g5_speed.py --stage parts --smoke             # this smoke
modal run benchmarking/modal_g5_speed.py --stage parts                     # full per-branch run
modal run benchmarking/modal_g5_speed.py --stage all --merged <branch>     # merged run
```

Raw results (every run's summary, per-case JSON and logs, plus the bench and Modal scripts): https://gist.github.com/vaibh27/87b8ba41c1abb3a092edd29e26e07bdf . Files are named `<run>__<branch>__...`; runs `20261123-201227` (smoke), `20261123-202419` (full per-branch run), `20261123-203952` (merged run, first pass), `20261123-220836` (merged run) and `20261124-104204` (SDPA on the current config). Same files on the Modal volume `g6-g5-speed`.
