# Team 10 Gate 4 Evidence Summary (live status as of Mon 23 Nov 2026)

Status as of Mon 23 Nov 2026 (Week 4 D2; Gate 4 evidence due Fri 27 Nov, 11:59 PM IST; Go/No-Go Sat 28 Nov). All paths are under `teams/10-post-training/` unless noted. Public text names teams and GitHub handles only. Nothing here claims dry run 2 numbers that have not yet run.

## 1. Gate 4 / Gate 3 Item 7 Required Evidence (SFT & RL Method Decision)

Per TSAI rulings (21 Nov 2026), closing Gate 3 item 7 requires **both** results on the **dry run 2 checkpoint** (test-scale on real `corpus-v1` shards + untied KE2/KAS head `a10_kas_tokdrop` + Team 7 Checkpointer via `#608`):

| Required Evidence | Status (23 Nov) | Code / Job Ready | Blocking External Dependency |
|---|---|---|---|
| **(1) Matched-step DT vs LoRA vs Full FT on dry run 2** | **Pre-run ready (0% GPU run)** | `capstone/dryrun2_dt_compare.py`, `jobs/2026-11-26-g10-dryrun2-dt-vs-fft.md` + CPU stand-in log (`2026-11-26-g10-dryrun2-dt-vs-fft.log`), KE2/KAS head & input adapter (`#135`, `#141`, `#144` tested against Team 5 draft `#717` at `319f2dd7`), Team 7 store loader (`capstone/run_folder_from_store.py`, `#143`). | Team 5 PR `#717` merge on `main` + dry run 2 checkpoint (Thu 26 Nov) + `#587` slice arm (`a2` vs `a4`, defaults to `a4`). |
| **(2) DT-then-RL chain on dry run 2 DT checkpoint** | **Pre-run ready (0% GPU run)** | `jobs/2026-11-17-dt-then-rl-code.md`, `capstone/rl_job_v1.py` (`--sampler g5_batch`, 12.8x faster on T4, `results/b5_sampler_2026-11-23.md`), `rl-loop/keep_zero.py` (weight-decay fix `#143`), identical-weights log-prob gate + eval update mode for dropout heads (`#141`), 66-id free-reward filter (`#139`). | Dry run 2 DT checkpoint (`keep_canary/dt/` from job 1 above) + updating `rl-loop/config/task11_code_canary.yaml` to dry run 2 KE2/KAS pins. |

## 2. Independent & Supporting Week 4 Evidence Landed on `g10-week4-post-training` (`#135`–`#147`)

| Deliverable | Evidence Level | Paths | Key Numbers / Result |
|---|---|---|---|
| **KE2/KAS head & input adapter readiness** | Unit + `#717` draft check | `rl-loop/team5_adapter.py`, `capstone/sft_g5.py`, `capstone/keep_weights.py` (`#135`, `#141`, `#144`) | Non-`Linear` head helper + `tok_u` marker rows + 8,192 / 2,048 input auto-detection + identical-weights log-prob gate + `update_mode: eval` for train-mode vocab dropout. |
| **Batched G5 RL sampler (`g5_batch`)** | Measured (Colab T4, fp16, T2/T3) | `rl-loop/g5_decode.py`, `results/b5_sampler_2026-11-23.md`, `capstone/rl_job_v1.py` (`#145`) | **12.8x speedup** on T4 (`44.3 s -> 3.45 s` per prompt at RL job settings); wired behind `--sampler g5_batch` in `rl_job_v1.py` and enabled in `jobs/2026-11-19-g10-rl-dryrun1.md` (default stays `policy`). |
| **Team 7 Checkpointer <-> Team 9 watcher bridge** | Offline verified (`#608` store + `eval_mini_v1`) | `capstone/run_folder_from_store.py` (`#143`), `capstone/watcher_rows_to_report.py` (`#147`), `sft/tests/forgetting.py` (`#138`), `sft/bench/evaluate.py` (`#136`) | Reads Team 7 `#608` stores identically to `keep_weights` folders; converts Team 9 `eval_mini_v1` points (`0..100`) to `[0, 1]` fractions; `forgetting.py` refuses cross-dtype mismatches between bpb and watcher rows. |
| **7.65B MoE Deletion Tuning study (`Phi-mini-MoE-instruct`)** | Independent public-model study (non-capstone, 1 seed, DT only) | `results/dt_phi_moe.md` (`#146`) | Official DT code (`0.6108%` deleted on 512 expert gates): GSM8K chat `+13.0` pts (`58.5% -> 71.5%`), 6-benchmark mean `-0.74`, `indic_v1` `52.27 -> 52.27`, `safety_v1` `56.10 -> 56.10`. LoRA and Full FT baselines pending. |
| **4B / 8B Qwen3-Base DT vs LoRA vs Full FT ladder job** | Lead-approved job request (23 Nov, awaits TSAI GPU run) | `jobs/2026-11-23-g10-dt-large-model.md`, `.log`, `dt/run_ladder.py`, `dt/ladder_qwen3.yaml` (`#142`) | Tests pure DT, DT+markers, LoRA, Full FT, and low-LR Full FT at 4B and 8B on H200 (141 GB) with fused AdamW + OOM micro-batch retry. |
| **RL free-reward hygiene & Data A H3 hashes** | Merged on branch | `rl-data/free_reward_ids.py`, `capstone/rl_exclusions_v1/free_reward_ids.txt` (`#139`), `licences/licence_table.md` (`#137`) | Free-reward exclusions expanded `23 -> 66` ids (dry-run-1 RL trained pool `3,233 -> 3,199`); Data A BGE-M3/LaBSE weight hashes pinned. |

## 3. Cross-Team Handoffs (Week 4)

| Partner Team | Item | Status (23 Nov) | Next Step |
|---|---|---|---|
| **Team 5 (Architecture)** | Dry run 2 checkpoint (`#720`, `corpus-v1`, KE2/KAS `#717`, Team 7 Checkpointer `#608`) | **Confirmed 23 Nov:** `#717` is still a draft; dry run 2 (`#720`) uses `#608` store/run-id/interval already on `main` with **no new manifest field**; **blocked until `corpus-v1` shards exist** | Re-test adapter + `dryrun2_dt_compare.py` once `#717` merges; launch both Gate 4 jobs once `corpus-v1` shards unblock dry run 2 and checkpoint delivers. |
| **Team 7 (Infrastructure)** | Checkpointer wiring (both ways, due Tue 24 Nov) | **Ready** (`#608` store read verified in `#136`/`#143`; write/export verified in `keep_weights.py` & `sft_g5.py`) | Final smoke check against actual dry run 2 `#608` store format when dry run 2 starts. |
| **Team 9 (Evaluation)** | `eval_schedule.md` item #7 (which SFT/RL checkpoints go to Team 9, and when) | **Aligned** (`watcher_rows_to_report.py` `#147` + dtype guard `#138`) | Hand over kept dry-run-2 Team 7 run folders (`keep_t7/g10-dr2-{full,lora,dt}/` and `g10-rl-final`) on Thu 26 / Fri 27 Nov for bf16 Tier B scoring. |
| **Team 2 (Data B)** | Native-reader review of human-written Indic RL templates | Team 2 committed to 1-day turnaround | Pending G10 human templates in `rl/indic/templates/indic_templates.yaml` (0 templates authored yet). |

## 4. Remaining Open Items Before Gate 4 (Fri 27 Nov, 11:59 PM IST)

1. **Dry run 2 GPU runs (Gate 4 required):** run `jobs/2026-11-26-g10-dryrun2-dt-vs-fft.md` and `jobs/2026-11-17-dt-then-rl-code.md` on Team 5's Thu 26 Nov dry run 2 checkpoint and populate `results/dt_vs_fft.md` and `results/dt_then_rl.md`.
2. **Queued TSAI jobs:** analyze returned logs for `#565` (OCR-2 p1536 pack), `#587` (first SFT on dry run 1), `#133` (E9 1.7B), and `#142` (`jobs/2026-11-23-g10-dt-large-model.md`, lead-approved 23 Nov).
3. **Human-written Indic RL templates:** author templates in `rl/indic/templates/indic_templates.yaml`, check decontamination, and obtain Team 2 native-reader sign-off (`team2_reviewer`).
4. **Verifier & licence hygiene PRs:** remaining Week 4 hardening across `rl/js/`, `rl/jsts/`, `rl/agentic/`, `rl/math/`, `rl/tool_call_verifier.py`, `rl/toolresult/`, effort v2 API-Bank overlap check, and paired LoRA/Full-FT baselines for `results/dt_phi_moe.md`.
