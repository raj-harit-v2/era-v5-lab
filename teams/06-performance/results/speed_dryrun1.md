# Speed — dry run 1

**Status:** §1–6 filled; §2 WO1 / #496 modeled α-β (21 Nov); §4d #690 clean step (22 Nov); §5 MoE / #486 + sorted/grouped verdict (24 Nov); §4b + `profile_dryrun1.md` loop step shares from [#776](https://github.com/theschoolofai/era-v5-lab/pull/776#issuecomment-7131723877) (24 Nov); §1 loop dispatch only (sorted / grouped A/B in `kernels_dryrun2.md`).  
**Sources:** G6 Modal A100s (20 Nov); lab #620; WO1 Modal nccl+perfkit (21 Nov, gist below); [Admin #690](https://github.com/theschoolofai/era-v5-lab/pull/690) clean; [Admin #776](https://github.com/theschoolofai/era-v5-lab/pull/776#issuecomment-7131723877) layer shares; §5 cites #485/#486.  
**Rule:** GPU + SHA per table. Member-GPU runs give shares, counts and sizes only; step time comes from the lab run. `mfu_method=g6-v1` until CAP flips.  
**TSAI lab column:** #690 → §4d median ~12.0 s/step @ B=8 (clean SoT). #776 → loop step shares in `profile_dryrun1.md` + §4b (fwd 24.2 / bwd 66.7 / opt 6.9) — Admin: **directionally fine** (spill run), not clean; no absolute ms/tok/s. Fine §1 MoE/Nsight rows stay `_pending_` when not posted. §5 checkpoint TSAI cites #485 (8% / 92%, `checkpoint_dryrun1.md`), not #690. Keep loop / `g5_t2_base` / #690+#776 distinct from #620 and from #486 sorted.

| Field | Value |
| :--- | :--- |
| GPU | NVIDIA A100-SXM4-80GB (Modal): one GPU for §1 and §3, two in one container for §2 |
| Commit | `7b2ee0e3` + the `configs/g5_t2_base.yaml` change in this PR (`muon_impl: loop`, `data.source: synthetic`, `bench.modes: [clean, layer, trace]`) |
| Config | `configs/g5_t2_base.yaml` (dry run 1 model, class #475), B=8, T=2048, bf16, synthetic data |
| Software | torch 2.11.0+cu130, CUDA 13.0, cuDNN 91900, Triton 3.6.0, NCCL (torch wheel). The lab run used torch 2.14.1+cu130 (#620 manifest). |
| Runner | `benchmarking/modal_dryrun1.py` (`--what bench`, `ckpt`, `comm`) |
| Run folders | `repeatbatch8` (profile, §1), `a2a` (§2), `ckpt` (§3); profile details in `profile_dryrun1.md` |
| Raw outputs | <https://gist.github.com/vaibh27/e4e60f177d4fe675ba0444054928d341>: `a2a_*` (§2), `ckpt_*` (§3), `profile_*` and `nsys_*` (§1), logs and provenance |

## 1. MoE dispatch (compute)

Method: perfkit layer pass, level 3, sum of `fwd:block*.moe.dispatch` over the 8 layers; `model.moe.dispatch=loop` (the dry run 1 setting). Two runs in separate processes (`--repeat 2`, PASS); run 2 in brackets.

| metric | G6 (Modal A100) | TSAI lab | source |
| :--- | ---: | ---: | :--- |
| `moe.dispatch`, share of the layer pass | 6.0% (6.1%) | _pending_ | `repeatbatch8` |
| of which the 16 expert calls (`moe.dispatch.expert*`) | 5.4% (5.4%) | _pending_ | `repeatbatch8` |
| `moe.router`, share of the layer pass | 0.3% | _pending_ | `repeatbatch8` |
| `moe.shared` (shared expert), share of the layer pass | 1.0% | _pending_ | `repeatbatch8` |
| `fwd:block*.moe.dispatch` rank among the slowest parts | 5th, 3.7% (3.8%) of the step | _pending_ | `repeatbatch8` |
| host syncs per step from the dispatch (Nsight `cudaStreamSynchronize`) | 256 | _pending_ | `nsys-b8` |
| host time inside `moe.dispatch` (Nsight NVTX, share of a traced step) | 19.1% | _pending_ | `nsys-b8` |

- Routing state: the perfkit rows above were measured with a collapsed router (18 of 128 expert slots with tokens, synthetic data; `profile_dryrun1.md`, Routing state), so the GPU shares understate the dispatch cost; the Nsight rows (256 syncs, 19.1%) had all 128 slots active.
- The GPU cost is small; the host cost is not. `dispatch_loop` reads two values back to the host per expert per layer (`tok.any()` and `nonzero`, `models/moe.py:79`, `:81`): 8 layers × 16 experts × 2 = 256 syncs per step with every expert active. Each one stops the CPU until the GPU queue drains, so the first expert of every block (`expert0`) holds about half of that block's dispatch range in Nsight.
- Not measured here: `dispatch=sorted` and `dispatch=grouped` (same-container A/B in `kernels_dryrun2.md`).

## 2. MoE all-to-all (`comm`)

Dry run 1 ran on one GPU, so it had no all-to-all. Below: (A) the existing Modal **measured** forecast for the dry-run-1 shape, and (B) the WO1 / class #496 **modeled** α-β estimate for the `base.yaml` shape (**8 MiB × 48**). Both are **member-GPU / Modal**, not a live TSAI multi-GPU fabric measurement.

### 2a. Measured forecast — dry-run-1 shape (64 MiB × 32)

perfkit `--modes comm` under `torchrun`, 2 ranks on 2 A100-SXM4-80GB in one container, NCCL, isolated all-to-all (no overlap with compute). Source: #89 `a2a` run.

| metric | G6 (Modal A100) | TSAI lab | source |
| :--- | :--- | :--- | :--- |
| world size / backend | 2 / NCCL | n/a: dry run 1 ran on 1 GPU | `a2a` |
| calls per step | 32 (4 per layer × 8 layers) | n/a | `a2a` |
| payload per call | 64 MiB (B × T × top-2 × d × 4 bytes: fp32 payload, an upper bound for a bf16 run) | n/a | `a2a` |
| all-to-all per step, share of the clean step (rank 0, same container) | 1.7% | n/a | `a2a` |
| per-call spread (p10..p90, 30 timed calls) | 15% | n/a | `a2a` |
| slowest rank against the median call | 0.6% above | n/a | `a2a` |

- The all-to-all is a small part of the step for this model on 2 GPUs in one node, even counted with no overlap and an fp32 payload.

### 2b. Modeled estimate — `base.yaml` shape (8 MiB × 48) — WO1 / #496

**Label: modeled estimate — not a live class-fabric a2a job.** Calibrated once on Modal (21 Nov 2026): one container, A100-SXM4-80GB ×4 (NVLink up; `nvidia-smi topo -m` still fails in the sandbox, as in #89). Tip pin for the sweep: `g6/dev` @ `eac9c46e` (clean). Evidence: [gist jssunil/3091f90](https://gist.github.com/jssunil/3091f90bc1d48d2fcfe9bc12fca26267) (`raw.log`, `nccl_W*.csv`, `torch_W*.csv`, `fit.json`).

Two series on the same host (W=2 primary for §2):

1. **nccl-tests** `alltoall_perf` (v2.21.1 `afd59ab`, NCCL 2.25.1), out-of-place time, sizes 8 B → 256 MiB.
2. **G6 perfkit** `perfkit.bench.run_comm` (`all_to_all_single`, fp32, 30 timed calls, slowest rank; torch 2.11.0+cu130, NCCL 2.28.9) — same path as §2a / #89.

Fit: \(T(m)=\alpha + m/\beta\) (β in GB/s), relative least squares on sizes ≥ 64 KiB (13 points). Max relative fit error ~15–22% (latency floor below ~8 MiB); **at 8 MiB quote the measured point**; use α-β for other sizes.

| series (W=2) | α (µs) | β (GB/s) | 8 MiB per call (measured) | ×48 per step (measured) | ×48 α-β model |
| :--- | ---: | ---: | ---: | ---: | ---: |
| nccl-tests `alltoall_perf` | 17.6 | 280 | 0.059 ms | **2.9 ms** | 2.3 ms |
| G6 perfkit `run_comm` | 57.3 | 326 | 0.068 ms | **3.3 ms** | 4.0 ms |

**Headline for WO1 / #496 close:** use the **G6 perfkit measured** step cost **~3.3 ms** (8 MiB × 48, W=2, Modal A100, isolated a2a). nccl-tests measured ~2.9 ms is the Admin-wording twin on the same host. Note: stock `base.yaml` is dense (no a2a); the 8 MiB × 48 shape is `base.yaml` **with `model.ffn=moe`**. On that MoE-on-base step (~100 ms clean median in the same gist follow-up), a2a is **~3–4%** of the step — not ~0.6% of the dry-run-1 509 ms step. Dry-run-1 shape (64 MiB × 32) stays ~1.7% (§2a).

Check vs §2a / #89: perfkit W=2 at 64 MiB = 0.272 ms/call vs #89's 0.269 ms (ratio 1.009) — same code path, same GPU type, new container.

W=4 (same gist, not the §2 headline): perfkit measured 8 MiB × 48 ≈ 4.2 ms/step; β drops ~20% vs W=2.

- Not covered: multi-node / inter-node fabric, bf16 payload (fp32 is an upper bound — halve bytes for a bf16 estimate), overlap with compute, uneven expert loads, TSAI class interconnect (no fabric sweep posted; this is **Modal**, not “our fabric”).

## 3. Checkpoint

Full-size save of the dry run 1 model: model weights, every optimizer's state and the scaler. 10 timed saves after one warm save that is not counted. Timed in two parts: GPU → CPU copy into pinned buffers, then serialise + write + fsync. Written to the container's local disk (512 GB overlay), not to a network volume.

| metric | G6 (Modal A100) | TSAI lab | source |
| :--- | :--- | :--- | :--- |
| checkpoint size | 2,081 MiB | _pending_ | `ckpt` |
| GPU → CPU copy, share of the save | 6.5% | 8% | `ckpt`; class #485 |
| serialise + write + fsync, share of the save | 93.6% | 92% | `ckpt`; class #485 |
| save time in clean steps (same container) | 2.2 steps | _pending_ | `ckpt` |
| write rate to the container disk | 1,554 MiB/s | _pending_ | `ckpt` |
| save spread (p10..p90, 10 saves) | 4.9% | _pending_ | `ckpt` |

- Size check: 2,081 MiB is the full fp32 training state: 237.06 M weights (904 MiB) + Muon momentum on 165.7 M matrix parameters (632 MiB) + AdamW's two moments on 71.3 M parameters (544 MiB).
- The disk write is the cost (94%); the GPU copy is not. At one save every 1,000 steps the save is about 0.2% of training time.
- The write rate is a property of this host's disk; the lab's disk is not known.
- **TSAI #485 provenance:** 8% GPU-to-CPU copy and 92% serialization/write are reported shares from a **smaller synthetic checkpoint; not full-size Modal**. They are not a same-workload comparison. See [class #485](https://github.com/theschoolofai/era-v5-lab/pull/485) and [checkpoint evidence #557](https://github.com/theschoolofai/era-v5-lab/pull/557). TSAI absolute size, duration, write rate and spread remain pending.

## 4. Per-rank step time + slow ranks

Dry run 1 ran on one GPU (#620 manifest: NVIDIA GeForce RTX 3090, torch 2.14.1+cu130), so per-rank = **one rank**.

### 4a. Rank 0 step time (lab, class #620)

From `metrics.jsonl` (`tokens_per_second`, 16,384 tokens per step), steps 11–1221 (1,211 steps):

| rank | median | p10 | p90 | p99 | max | source |
| ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| 0 (only rank) | 1,897.6 ms | 1,772.3 ms | 2,054.6 ms | 2,207.9 ms | 2,420.6 ms | #620 |

- Step 1: 4,430 ms (warm-up: allocator, autotune). Throughput 8,634 tokens/s; peak allocated 3.56 GB; sum of steps 2,335 s of 2,481 s wall.
- No drift: median of steps 11–110 is 1,894.4 ms, of steps 1121–1221 1,889.1 ms.
- Tail: 75 of 1,211 steps are more than 10% above the median, 7 more than 20% (steps 30, 292, 316, 321, 337, 1148, 1154), 3 more than 25%. They come in two clusters (292–337, 1148–1154) rather than at a fixed interval, so they are not a periodic eval or log step; cause not identified (the log has no per-step host timing).

### 4b. Where rank 0's step goes

**Loop / lab step shares ([#776](https://github.com/theschoolofai/era-v5-lab/pull/776#issuecomment-7131723877)):** `fwd` 24.2%, `bwd` 66.7%, `opt` 6.9% of the median step; `data` 0.0%. Layer-only, 40 steps, B=8, synthetic. **Admin caveat:** spill run — shares are **directionally fine**, not clean; do **not** use absolute step ms or tokens/s. Within-parent only (not step shares): `fwd:stack` 2.3% within fwd; `bwd:stack` 5.2% within bwd — see `profile_dryrun1.md`.

Member-GPU reference (same model, Modal A100, B=8): `fwd` 35.6%, `bwd` 45.7%, `opt` 18.4%; GPU busy 75–77%; 256 host syncs and about 30,300 kernel launches per step (Nsight).

### 4c. Slow ranks

**Not measurable on 1 GPU.** A slow rank only exists when ranks are compared; a step on N GPUs takes as long as its slowest rank, because every collective waits for it. The 2-rank all-to-all run (§2) is the only multi-rank data: its slowest rank's all-to-all is 0.6% above the median, so the collective itself adds no skew there. Per-rank step tables (median / p95 / max and ratio to the cross-rank median, mapped to node and GPU) need a multi-GPU training run with the G7 layout.

What one rank already shows: the step is host-heavy (256 host syncs from the loop dispatch, about 30,300 launches, most of them Muon's loop path). On N GPUs every rank pays this, and host jitter turns into rank-to-rank skew, so cutting syncs and launches comes before any slow-rank work.

### 4d. Clean step (lab, class #690 partial)

[Admin #690](https://github.com/theschoolofai/era-v5-lab/pull/690) (after machine crash + rerun). Job `dryrun1_tsai` / `configs/g5_t2_base.yaml`, `dispatch=loop`, B=8. Only `clean` finished; layer/trace/nsys/ckpt not returned; no `result.json`.

| metric | value | source |
| :--- | :--- | :--- |
| GPU | not reported by TSAI (~24 GB card) | Admin #690 |
| run SHA | not reported by TSAI | Admin #690 |
| batch | 8 (no OOM) | Admin #690 |
| measured steps | 100 | Admin #690 |
| median step | ~12.0 s (11.5–12.9 s) | Admin #690 |
| temp | 73–79°C | Admin #690 |
| wall | ~98 min; ran past the 90-min cap (clean only) | Admin #690 |

Label: loop / `g5_t2_base` / #690 clean step — not #620 full-run metrics, not #486 sorted. Loop step shares from [#776](https://github.com/theschoolofai/era-v5-lab/pull/776#issuecomment-7131723877) (see §4b / `profile_dryrun1.md`); fine MoE/Nsight rows still `_pending_` when not posted.

## 5. MoE analysis

| part of the MoE path | G6 GPU-side share | G6 host-side cost | TSAI lab | source |
| :--- | :--- | :--- | :--- | :--- |
| dispatch (loop over 16 experts) | 6.0% of the layer pass | 256 syncs per step, 19.1% of host time | `sorted` (#486): 2.3% fwd + 2.3% recompute of step, 19 syncs/step, GPU 31.1% busy — different width, read as direction† | §1, `profile_dryrun1.md` |
| router + shared expert | 1.3% of the layer pass | small | not in #486 top-5 | §1 |
| all-to-all (forecast, 2 GPUs; dry-run-1 64 MiB×32) | 1.7% of the step | n/a | n/a (1 GPU) | §2a |
| all-to-all (modeled, 2 GPUs; base.yaml+MoE 8 MiB×48) | ~3.3 ms/step (~3–4% of ~100 ms MoE-on-base step) | n/a | n/a (Modal, not fabric) | §2b |
| checkpoint | 2.2 steps per save | disk write 94% of the save | 8% copy / 92% write (#485) | §3 |

† #486 ran `dispatch=sorted` at small width (d=256, 6 layers, B=16, T=256), the G6 rows ran `dispatch=loop` on `g5_t2_base` (d=512, 8 layers, B=8, T=2048) — different dispatch **and** width, so read the TSAI column as sorted-vs-loop direction, not the same model measured twice (`profile_dryrun1.md`, TSAI column fill). Shares and counts only; TSAI held the absolute ms.

1. **Loop dispatch is host-bound — but neither `sorted` nor `grouped` is the fix.** The dispatch cost is on the host (256 syncs/step: 8 layers × 16 experts × 2 reads, `tok.any()` + `nonzero`, `models/moe.py:79`,`:81`), not the GPU (6.0% of the layer pass). The same-container A/B (`kernels_dryrun2.md`) cut the syncs — `sorted` 147→9, `grouped` 147→1 — yet **both are slower** (`sorted` +1.2%, `grouped` +22.8%): both pad every expert to a fixed capacity and run one batched GEMM (1.3× / 1.7× the loop's fwd+bwd under a skewed router), and both hand idle experts zero gradients, so loop-Muon's 18-matrix Newton-Schulz becomes 128 matrices. #486 (TSAI, `sorted`) agrees in direction — syncs fall to 19/step but the GPU is still only 31.1% busy (host-starved). The real candidate is a **dropless grouped GEMM** over the ragged per-expert segments (no padding, no host sync; MegaBlocks / `torch._grouped_mm`) — already on tip as `model.moe.dispatch=grouped_mm` (off by default) on `g6/w4-g5-merged`; A100 was slower; H100 pending.
2. **All-to-all is small at one node.** Measured ~3.3 ms/step at the `base.yaml`+MoE shape (8 MiB × 48, G6 perfkit W=2, isolated a2a) — ~3–4% of a MoE-on-base step (§2b), and ~1.7% of the dry-run-1 step at the 64 MiB × 32 shape (§2a). Re-measure at the main run's rank count and across nodes (the collective-sync regime a2a is built for) before ruling it out; no live class-fabric sweep exists yet, so §2 is a modeled α-β estimate, not a measurement.
3. **Checkpoint is disk-bound.** The file write is 92–94% of each save (TSAI #485: 8% copy / 92% write; G6 Modal: 94% write, 2.2 steps per save); the GPU→CPU copy is not the cost. Save less often, or copy to pinned CPU memory and write from a background thread, if the main run's disk is slower than this host's.
4. **Open `@pair` gap — cast/copy kernels.** Cast/copy kernels are 17–19% of GPU kernel time (~2,700 launches/step: fp32→bf16 casts and per-expert gathers, `profile_dryrun1.md` top ops / Nsight) and are the one hot item with **no switch and no `@pair` test** — every other candidate (CE `fused_triton`, `attn=sdpa`, `muon_impl=batched`, `dispatch=sorted`/`grouped`) already has a passing pair in `kernels_dryrun2.md`. Needs a source trace (which casts/gathers, in which pass) before a switch can be proposed — this is the gap-fill `@pair` to add if any is added at all. Non-MoE hot parts (CE, eager attention, Muon loop) and their A/B verdicts live in `kernels_dryrun2.md` Findings; §5 does not duplicate them.

## 6. G4 KE2 footnote

From the same profile (`repeatbatch8`): the KE2 embedding (`fwd:embed.ke`) is 0.7% of the layer pass, `fwd:embed` 0.7% and `bwd:embed` 0.5% of the step. KE2 is not a speed bottleneck in dry run 1.
