# EXP-2: AdamW vs Muon at T2

REQUEST FOR LEAD/TSAI REVIEW. No lead approval or official run completion is claimed.

```text
Team:            05-architecture
Owner:           Vardhan Walavalkar (vpw)
Lead approval:   pending review by shivman
Question:        At T2 with the same budget, does Muon give lower held-out bits per byte than AdamW by more than the larger seed spread?
Script:          teams/05-architecture/harness/train_week2.py (on main since #190). Muon backend: Deepjyoti Saha's #241, merged 5 Nov. Faster batched held-out eval: Udit Singhania's #325, merged 7 Nov.
Command:         python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_adamw.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1234 --out ./out/exp2_adamw-1234
                 python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_adamw.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1235 --out ./out/exp2_adamw-1235
                 python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_adamw.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1236 --out ./out/exp2_adamw-1236
                 python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_muon.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1234 --out ./out/exp2_muon-1234
                 python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_muon.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1235 --out ./out/exp2_muon-1235
                 python teams/05-architecture/harness/train_week2.py --config teams/05-architecture/configs/arms/exp2_muon.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml --tokenizer ./inputs/tokenizer_v0.json --byte-table ./inputs/raw_table_P32.npz --train-data ./inputs/train.jsonl --heldout-data ./inputs/heldout.jsonl --heldout-sources ./inputs/heldout_sources.jsonl --heldout-sha256 ./inputs/heldout.sha256 --heldout-report ./inputs/heldout_report.json --device cuda --seed 1236 --out ./out/exp2_muon-1236
Config:          exp2_adamw.yaml (teams/05-architecture/configs/arms/): optim.lr = 0.001, the current best candidate from EXP-1 (TSAI, #310, 7 Nov) -- mean val/bpb 1.9686 across seeds 1234/1235/1236, lowest on all three seeds, smallest spread (SD 0.0070). intended.comparison_final: false until three-group/code/Indic bpb are posted alongside the aggregate (same bar Shivanshu set on #341 and on the attention job).
                 exp2_muon.yaml: optim.muon_lr = 0.01, PROVISIONAL from the T1 Muon screen (TSAI, one seed, 245 steps, reported on #241: final CE 7.287 at 1e-1, 6.626 at 1e-2, 7.086 at 1e-3). One seed does not name a winner (Shivanshu, 6 Nov); optim.lr = 0.001 for the non-matrix parameters, matching the AdamW arm; momentum 0.95 Nesterov, weight decay 0, router on Muon (as set in #241). intended.comparison_final: false.
Inputs:          training data reuses the TSAI-staged bundle from official job #310: train split of tokenizer sample v0-clean (all 38 packs), tokenizer teams/03-tokenizer/v0. Held-out is heldout_v1 (#191, 1,059 docs, all 15 slices including Punjabi and Assamese) -- #310's own held-out split is missing those two slices, so this follows the same substitution Shivanshu set for the attention T2 job. Byte table teams/04-ke2/results/tables/raw_table_P32.npz, sha256 0b2b499e58ae644362c6ef7f6413aef833cf4707d41433931f47bc4990ad72b0 (Udit Singhania, #310 comment, 6 Nov).
Hardware:        1 GPU, native bf16 (compute capability 8 or higher)
Max time:        540 minutes total: 2 arms x seeds 1234/1235/1236, 90 minutes cap per run.
                 Muon is projected at about 96 minutes (measured on my own backend, not #241) plus evaluation, so it is likely to hit the cap. A run that stops before 1,221 steps is INCOMPLETE_NOT_A_RESULT.
Precision:       bf16
Measures:        val/bpb (aggregate), per-slice bpb, three-group bpb, loss_ntp, gradient_norm, tokens_per_second, perf/step_ms, final_model_sha256, per seed and per arm
Expected result: no winning arm is assumed. Step time on an L4 (not TSAI's GPU): AdamW about 3.9 s/step, Muon about 4.7 s/step at T2 batch 8 x 2048, projecting to about 79 and 96 minutes for 1,221 steps before the held-out evals. Void if any NaN or inf.
Outputs:         each run's metrics.jsonl, manifest.json, summary.json, losses.txt, total_losses.txt only; 50 MB or less total. The trainer also writes a checkpoint because a quality run requires one (same as #310) -- retained internally, not returned. final_model_sha256 in summary.json stays as the weights fingerprint.
Test log:        102 Week 2 tests passing on main after #325 (Udit Singhania, 7 Nov). exp2_adamw.yaml and exp2_muon.yaml validated today to load and inherit cleanly from t2.yaml/base.yaml. No fresh GPU/CPU training smoke was run for this request -- no local GPU/torch in this environment -- consistent with #310 citing existing suite evidence rather than adding a new per-job log.
```

## Six runs

| Arm | Config | Seed | Output directory |
|---|---|---:|---|
| exp2-adamw | exp2_adamw.yaml | 1234 | ./out/exp2_adamw-1234/ |
| exp2-adamw | exp2_adamw.yaml | 1235 | ./out/exp2_adamw-1235/ |
| exp2-adamw | exp2_adamw.yaml | 1236 | ./out/exp2_adamw-1236/ |
| exp2-muon | exp2_muon.yaml | 1234 | ./out/exp2_muon-1234/ |
| exp2-muon | exp2_muon.yaml | 1235 | ./out/exp2_muon-1235/ |
| exp2-muon | exp2_muon.yaml | 1236 | ./out/exp2_muon-1236/ |

## Why now

Gate 2 proposals are due Thu 12 Nov 23:59 IST (Instructor, 11 Nov); `config_v1.yaml` and `decisions.md` need every arm's bits-per-byte result on main or in a linked PR by then, or it is treated as missing. EXP-1 landed 7 Nov (the Instructor's own condition for filing this job), so filing now rather than waiting for the AdamW rate to be formally "final" follows the same pattern already used for the attention T2 job and the Muon T1 screen's own arm note: file with `comparison_final: false`, fill in the per-slice bpb once TSAI can run it.

## Open items

1. **AdamW rate** is the current best candidate (0.001), not yet final org-wide. If the lead's eventual call differs, `exp2_adamw.yaml` needs updating before this is a quality result.
2. **`muon_lr`** is provisional (one-seed screen). If the official multi-seed screen moves it, `exp2_muon.yaml` needs updating.
3. **Inputs** above name TSAI-staged paths (`./inputs/...`); TSAI republishes `train.jsonl`, the resolution, and their sha256 for this job the same way as for #310. heldout_v1's files are already on main from #191.
4. **Muon step time on #241** is not measured on real hardware; the 96-minute projection is from my own backend, not #241.
