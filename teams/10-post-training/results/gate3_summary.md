# Team 10 Gate 3 Evidence Summary (20 Nov 2026)

Status as of Fri 20 Nov 2026 (Gate 3 evidence due 20 Nov 23:59 IST; TSAI decisions Sat 21 Nov). All paths are under `teams/10-post-training/` unless noted. Public text names teams only.

## 1. Gate 3 Evidence Checklist

| Gate 3 Requirement | Status | Primary Evidence | Notes / Remaining Limits |
|---|---|---|---|
| **SFT data v1 & RL data v1 pass decontamination** | **Done** (RL pool verified by Team 9; SFT reports on `main`) | `sft/decontam_report.md`, `rl/decontam_report.md`, `results/rl_data_v1_close.md`, `teams/09-evaluation/results/decontam_rl_pool.md` (PR #661) | Team 9 checked **6/6** RL pool files (25,249 docs) against v2 & v1 fingerprints: **0 flagged**, plus Codeforces side check complete. TSAI rebuilt RL pool (#564); SFT pack (#565) & dry-run-1 SFT (#587) await TSAI execution. |
| **Every verifier passes its two tests (1 correct, 1 wrong)** | **Done on `main`** | `rl/reward.py`, `rl/test_reward.py`, `rl/test_verifier.py`, `rl/README.md` | All **11** env types registered under `reward(env_id, output)`: `agentic` (5), `code` (10), `go` (10), `indic` (6), `js` (5), `math` (2), `math_pool` (8), `swe` (21), `tool_call` (1), `toolresult` (10), `ts` (4). Legacy Docker builder fallback added in `swe-envs/verify.py`. |
| **SFT test sets exist & forgetting check runs on every SFT job** | **Done on `main`** | `sft/eval_v1.md`, `sft/tests/toolcall_v1.jsonl` (32), `indic_v1.jsonl` (44), `safety_v1.jsonl` (41), `sft/tests/forgetting.py`, `results/small_sft.md` | All 10 Indic scripts native-speaker reviewed (`hi, mr, te, kn, ta, bn, gu, ml, or, pa`). `forgetting.py` enforces `0.05` bpb limit, `0.01` at-limit mark, and `[0, 1]` fraction units guard. Team 9 `eval_schedule.md` (#662) aligned. |
| **Small RL shows rising reward** | **Done on `main` (surrogate)** | `results/small_rl.md`, `results/code_rl_e1_20261115.md`, `rl/objective_v1.md`, `rl/objective_v1.py`, `jobs/2026-11-19-g10-rl-dryrun1.md` | Surrogate (`Qwen2.5-Coder-7B-Instruct`, 1 seed, 60 steps): held-out pass@1 `0.151 -> 0.251` (+0.100, CI `[+0.063, +0.142]`), train cohort `0.299 -> 0.944`. Dry-run-1 RL job draft queued behind #587. |
| **After Deletion Tuning, small RL still shows rising reward** | **Done as CPU rehearsal; code canary staged** | `results/dt_then_rl.md`, `jobs/2026-11-17-dt-then-rl-code.md`, `jobs/2026-11-20-g10-dt-sft-dryrun1.md`, `capstone/sft_job_v1.py` (`--method dt_markers`) | 3-seed CPU rehearsal on stand-in Team 5 MoE: held-out reward rose in all 3 seeds (`0.4268 -> 0.6383` / `0.5013`), 348,469 deleted weights stayed 0 across 180 steps. Staged CPU test log recorded; real GPU code canary awaits #587 + #475 probe expectation. |
| **Deletion Tuning vs LoRA vs full FT table + sweeps** | **Done on `main` (surrogate)** | `results/dt_vs_fft.md`, `results/dt_sft_surrogate.md`, `results/dt_toy_sharpness_check_20261117.md`, `results/dt_lr_check_20261118.md`, `dt/mask.py` | **Candidate only (TSAI decides at Gate 3).** `SmolLM2-135M` and `1.7B` equal-step comparison + deletion-fraction & target-layer sweeps. Port check fixes landed: `band_at_init`, sharpness `100 -> 1000`, and Team 5 #521 fused-expert `einsum` fix for both DT and LoRA. |

## 2. Week 3 Core Tasks (1–11)

| # | Task | Status | Evidence / Open Item |
|---|---|---|---|
| 1 | SFT data v1 with loss masks | **On `main`** (jobs queued) | Manifest, p1536 rebuild, overlap flags on `main`. Pack (#565) & SFT (#587) jobs await TSAI run. |
| 2 | RL data v1 with verifiers | **Done on `main`** | All 11 verifier types registered & tested; RL pool rebuilt (#564) and decontaminated 6/6 by Team 9 (#661). |
| 3 | Session 18 objective | **Done on `main`** | `rl/objective_v1.md`, `rl/objective_v1.py`, integrated in `rl-loop/train.py`. |
| 4 | Effort subgroups & length penalty | **Spec + v1/v2 manifests done; Stage C pending** | `rl/effort_v1.md`, `rl/effort_reward.py`, `rl/effort_penalty.py`, `eval/effort_manifest.json` (v1, 55 resolved), `eval/effort_manifest_v2_proposed.json` (v2, 85 resolved: +20 API-Bank, +10 QASC signed off 20 Nov). 15 Indic slots and decoupled-cap Stage C await human Indic sources + Team 10 chat-format checkpoint. |
| 5 | Small SFT run | **Done on `main`** | `results/small_sft.md` (loss falls: full FT `1.444 -> 0.956`, LoRA `1.564 -> 1.129`; `forgetting.py` verdict recorded). |
| 6 | Small RL run | **Done on `main` (surrogate)** | `results/small_rl.md`; dry-run-1 RL job draft in `jobs/2026-11-19-g10-rl-dryrun1.md`. |
| 7 | Indic prompts with checkable answers | **Generator & seed verifier done; templates open** | `rl/indic_prompts_v0.md`, `rl/indic/generate.py`, 6 seed eval tasks (`indic/<id>`). `rl/indic/templates/indic_templates.yaml` still holds 0 human-written training templates and awaits human authoring + Team 2 native-reader check (per TSAI 3 Nov data rule). |
| 8 | SFT eval note & test sets | **Done on `main`** | `sft/eval_v1.md`, `sft/tests/` (all 10 languages native-reviewed, `forgetting.py` units guard). |
| 9 | Deletion Tuning study vs LoRA & full FT | **Done on `main` (surrogate)** | `results/dt_vs_fft.md`, `results/dt_sft_surrogate.md`, port check & Team 5 #521 fused-expert fix landed. |
| 10 | Task gain & forgetting table + sweeps | **Done on `main` (surrogate)** | `results/dt_vs_fft.md` (3 deletion fractions × MLP gate / all MLP / attention, sharpness `100 -> 1000`). |
| 11 | Deletion Tuning then small RL | **CPU rehearsal on `main`; code canary staged** | `results/dt_then_rl.md`, `jobs/2026-11-17-dt-then-rl-code.md`, `jobs/2026-11-20-g10-dt-sft-dryrun1.md` (lead-approved DT settings; blocked on #587 result + #475 probe expectation). |

## 3. Cross-Team Handoffs

| Partner Team | Deliverable | Status | Reference |
|---|---|---|---|
| **Team 1 (Data A)** | Licence sign-off for H3 dedup encoders (`LaBSE` Apache-2.0, `BGE-M3` MIT) | **Done on `main`** | `licences/licence_table.md` |
| **Team 3 (Tokenizer)** | Chat format & vLLM marker round-trip on frozen p1536; embedded template & eos config | **Done on `main` + PR #686** | `teams/03-tokenizer/results/chat_format_check.md` (PR #642); Team 3 PR #686 embeds byte-identical `chat_template.jinja` (`b00137fe…`) in `release/tokenizer_config.json` and adds `release/generation_config.json` (`eos_token_id: [130816, 130822]`) |
| **Team 5 (Architecture)** | Dry-run-1 `#475` probe expectation clarification | **Confirmed (21 Nov)** | Dry run 1 was not saved via Team 7 Checkpointer (`#475` weights are with TSAI); dry run 2 (`#608`) integrates Team 7 Checkpointer and writes `probe_loss` automatically |
| **Team 7 (Infrastructure)** | `Checkpointer.save` + `export_safetensors` wiring for kept SFT/RL weights | **Done on `main`** | `capstone/sft_g5.py`, `capstone/keep_weights.py`, `capstone/test_team7_ckpt_save.py` |
| **Team 9 (Evaluation)** | RL pool decontamination (6/6 files, 0 flagged), `eval_schedule.md` alignment, bf16 & firewall | **Done on `main` + PR #681** | `teams/09-evaluation/results/decontam_rl_pool.md` (#661), `eval_schedule.md` (#662). Agreed 21 Nov: Team 9 watcher scores base + after-SFT checkpoints in bf16 autocast (fractions `value/100`, `stderr/100`); `jobs/2026-11-18-g10-eval-mini-forgetting.md` withdrawn for firewall compliance; `sft/bench/evaluate.py --dtype {float32,bfloat16,auto}` matches watcher dtype (`compute_dtype: bfloat16`). Team 9 asked TSAI to add `#565`'s Codeforces decontamination read to the access list. |
| **Team 12 (Quantization & Serving)** | Chat template serving parity & G12 dry-run-1 split | **Done on `main`** | PR #646 merged; G12 dry-run-1 split in PR #669 |

## 4. Open Decisions for TSAI (Sat 21 Nov)

1. **SFT data v1 & RL data v1 admission** (including whether `rl-math-hendrycks` 7,209 reserved tasks and `python2_only` 1,545 code tasks stay in RL v1).
2. **Deletion Tuning candidate decision** (compare DT vs LoRA vs full FT findings in `results/dt_vs_fft.md`, `results/dt_sft_surrogate.md`, and `results/dt_then_rl.md`).
3. **Context length per phase** (determines when effort tiers `4k`, `16k`, `64k` move from placeholders to live runs in Team 9's eval schedule and Team 10's Stage C).
4. **Indic RL templates policy** (`rl/indic_prompts_v0.md` §7: programmatic value fills on human-written templates + Team 2 reader sign-off, and per-language share vs `native_indic_share_v1.md`).
5. **Queued TSAI jobs:** #558 (dry-run-1 probe), #565 (OCR-2 p1536 pack), #587 (first SFT on dry run 1), and #589 (E9 1.7B SFT-before-RL, approved).
