# Router comparison: the MoE router on Muon or on AdamW (T2, two runs)

REQUEST FOR LEAD/TSAI REVIEW. No lead approval and no run result is claimed.

```text
Team:            05-architecture
Owner:           Deepjyoti Saha (@deepjyotisaha)
Lead approval:   pending review by shivman. Shivanshu, 05 Architecture, 21 Nov: "The router comparison is a separate job request to TSAI."
Question:        With the week-4 optimizer split (#706), does putting the MoE router on AdamW (TSAI and KE2's 21 Nov recommendation) train at least as well as keeping it on Muon? TSAI: "put the router on AdamW ... but test it, don't assume it's settled."
Script:          teams/05-architecture/harness/train_week2.py on lab main after #706 merges (the router switch optim.router_on_muon is in #706). TSAI to name the exact main commit and the speed-fix state used for dry run 2, so the two runs match it.
Command A:       python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/router/router_muon.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer-release frozen-p1536 --tokenizer ./inputs/tokenizer_p1536.json --byte-table teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout_v1.jsonl --heldout-sources ./inputs/heldout_v1_sources.jsonl --heldout-sha256 ./inputs/heldout_v1.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1234 --out ./out/router-muon-1234
Command B:       the same command with --config teams/05-architecture/configs/arms/router/router_adamw.yaml --out ./out/router-adamw-1234
Config:          configs/arms/router/router_muon.yaml and router_adamw.yaml. Both inherit exp2_muon.yaml (T2: 8 layers, width 512, 16 routed experts plus 1 shared, top-2, eager attention, batch 8, context 2,048) and set muon_lr 0.003 (config v1, TSAI 21 Nov) instead of 0.01. They differ in one line only: optim.router_on_muon true (A) or false (B). AdamW lr 0.001 (config v1, provisional). Dense untied head, as in dry run 1.
Inputs:          the same TSAI-staged inputs as dry run 1 on p1536 (#475): text bundle, original heldout_v1 (1,059 documents, 15 slices), frozen p1536 tokenizer sha256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b, raw P32 table content sha256 21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a. TSAI to confirm the paths.
Hardware:        1 GPU, native bf16
Max time:        90 minutes per run (the T2 cap in runtime.yaml); two runs
Precision:       bf16
Measures:        val/bpb (aggregate), val/three_group_bpb and its three groups, per-slice bpb, loss_ntp at every step, gradient norm, perf/step_ms, tokens_per_second, completed steps, final_model_sha256; and from manifest.json the optimizer record (router_on_muon, muon_parameters, adamw_parameters).
Expected result: no outcome is assumed. A run that stops before 1,221 steps is INCOMPLETE_NOT_A_RESULT. A NaN or inf voids the run.
Outputs:         per run: metrics.jsonl, manifest.json, summary.json, losses.txt, total_losses.txt; 50 MB or less each. The checkpoint stays on the job machine.
Test log:        teams/05-architecture/jobs/evidence/2026-11-21-router-comparison/smoke.md
```

## Two runs

| Run | Config | Router on | Seed | Steps | Output directory |
|---|---|---|---:|---:|---|
| A | router/router_muon.yaml | Muon | 1234 | 1,221 | ./out/router-muon-1234/ |
| B | router/router_adamw.yaml | AdamW | 1234 | 1,221 | ./out/router-adamw-1234/ |

Same seed, data, size and every other setting, so the router's optimizer is the only difference. If budget allows, a second pair at seed 1235 would give a spread; one pair is the minimum.

## How the result will be read

- **Quality.** val/bpb of B against A. With one seed per arm the reading is "same or not", not a winner: a gap smaller than the T2 seed range (0.0254, the T2 reference at seeds 1234 to 1237) is "no measurable difference".
- **Stability.** Both runs: finite loss, the spike check of `experiments/results/dryrun1_spikes.py`, gradient norm.
- **Decision this informs.** If B is not worse, the #706 default (router on AdamW) stands for the main run. If A is clearly better, I propose moving the router back to Muon before the main run (go or no-go, Sat 28 Nov). `config_v1.yaml` is not changed by this request.

## Why now

The main-run go or no-go is Sat 28 Nov. Dry run 2 (Tue 24 to Thu 26) stays one run (Shivanshu, 21 Nov), so this comparison runs separately; two T2 runs fit beside it.

## Open items

1. **Depends on #706.** The router switch lands with #706; this request runs only after #706 is on main.
2. **Expert balance.** The trainer on main does not log per-expert load. Udit's #607 (expert-load telemetry, opt-in) would add it; if #607 is merged by then, please run with its collection on, so the comparison also shows how evenly tokens spread over experts.
3. **Source and runtime.** TSAI to say whether these runs use the same main commit, speed fixes and runtime file as dry run 2.
