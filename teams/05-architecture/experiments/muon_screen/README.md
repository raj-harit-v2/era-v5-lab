# muon-screen

Arm owner: Deepjyoti Saha (`deepjyotisaha`). Muon screen, size T1, before the EXP-2 T2 job. Plan: `experiments/plan_v1.md`.

The plan: three T1 runs at Muon learning rates 1e-3, 1e-2 and 1e-1, seed 1234, 30 min each. The `exp2-muon` arm uses
the rate with the lowest bits per byte of the three. One seed, so this is a screen. This note does not name a winner,
and `can_win` stays false.

## What the three runs change

| Field | Value |
|---|---|
| Configs | `configs/arms/muon_screen/muon_1e-3.yaml`, `muon_1e-2.yaml`, `muon_1e-1.yaml` (each inherits `configs/arms/t1.yaml`) |
| The one change from T1 | `optim.name` = muon, with `optim.muon_lr` = 0.001, 0.01 or 0.1 |
| Optimizer | Muon for the hidden weight matrices; AdamW at `optim.lr` 0.001 (from `t1.yaml`) for the embedding projection, output head and norm gains. Code: pull request 241 |
| Budget | batch 8, context 1,024, 245 steps, 30 min cap, seed 1234 |

`optim.lr` 0.001 is the AdamW part only. It is the same in all three runs, so the screen compares `muon_lr` alone.

## Job

| Field | Value |
|---|---|
| Job | `241-g5-muon-screen`, run by TSAI after pull request 241 merged. Result posted on pull request 241 (6 Nov 2026) |
| Code | `main` at `4332666` (5 Nov), which includes pull request 241 |
| Command | `train_week2.py --config teams/05-architecture/configs/arms/muon_screen/muon_<rate>.yaml --seed 1234`, with the job's inputs and resolution |
| Training data | the confirmed EXP-1 training file: train split of the cleaned tokenizer sample v0-clean, all 38 packs (as reported by TSAI) |
| Held-out | the confirmed EXP-1 held-out file (as reported by TSAI), the job-310 held-out. It has no Punjabi or Assamese documents (lead, 11 Nov), so its Indic mean covers 9 of the 11 Indic slices. `heldout_v1/` was not used |
| Tokenizer, table | tokenizer v0; byte table P32 v0 (as reported by TSAI) |
| Settings | the published resolution, run with micro batch 8: same tokens per step and same maths, fewer accumulation steps (as reported by TSAI) |
| Precision | bf16, 1 GPU |
| Pending from TSAI | the per-run `summary.json`, `metrics.jsonl` and `manifest.json` (TSAI keeps them; asked for on pull request 241); GPU model; held-out sha256 |

## Result

Source: the TSAI comment on pull request 241 (6 Nov 2026), "TSAI job result: Muon screen". All three runs reached
245 steps and are eligible for the quality comparison. The values are training cross-entropy, not held-out bits per byte.

| muon_lr | steps | first train CE | last train CE | wall time | eligible |
|---|---|---|---|---|---|
| 1e-3 | 245 | 11.953 | 7.086 | 1538 s | yes |
| 1e-2 | 245 | 11.953 | 6.626 | 1182 s | yes |
| 1e-1 | 245 | 11.953 | 7.287 | 1064 s | yes |

On last training CE the order is 1e-2 < 1e-3 < 1e-1. The 1e-2 run was stopped once by the host and rerun from scratch;
the table shows the clean rerun.

The plan picks the rate on held-out bits per byte, and its number is the three-group mean (English, code, mean of the
Indic slices), with code and the Indic mean as guards (plan_v1, TSAI 2 Nov). Those values are not posted yet, so this
note reports no bits per byte and no pick. `exp2-muon` currently uses `muon_lr` 0.01, marked not final (lead, pull request 354).

### Pending

- Three-group, whole-file, English, code and Indic-mean bits per byte per rate.
- NaN/inf check over every logged value. COMPLETED means no run stopped, but the plan asks for the check on the logs.
- Scored training tokens per run.

When the three metric files per run are available, these come from:

```bash
python teams/05-architecture/experiments/muon_screen/summarize_screen.py <dir>/muon_1e-3 <dir>/muon_1e-2 <dir>/muon_1e-1 \
  --heldout-sha256 <sha256 of the held-out file the job used> \
  --json teams/05-architecture/experiments/muon_screen/screen_summary.json
```

The script checks each run: optimizer muon, `muon_lr` one of the three rates, AdamW `optim.lr` 0.001, seed 1234, GPU bf16,
245 of 245 steps inside 30 min, the held-out sha256 given on the command line, `val/bpb` equal to nats / ln 2 / bytes,
no NaN or inf. It checks that the three runs differ only in `muon_lr` and the arm file. It prints the per-rate bits per
byte, which Indic slices were scored, and the rate with the lowest three-group bits per byte only when all three runs
pass. `can_win` is always false.

## Earlier runs (not results)

**Provisional screen, 3 Nov.** Colab T4, fp32, smoke mode, the four #253 test values, a stand-in training file (train
splits of the held-out sources, 0 overlap with `heldout_v1/`), scored on `heldout_v1/`. All three reached 245 steps.
Held-out three-group bits per byte: 1e-3 2.1592, 1e-2 2.0773, 1e-1 2.2325. Each run had 1,009,824 scored training tokens
of 2,007,040 input positions. One seed, fp32, stand-in data: lead's label, "not the screen result".

**CPU test log for the job, 4 Nov.** `main` `4169aae` plus pull request 241 (`ecd9cfd`). 76 of 76 week-2 tests pass. All three
arms run 2 smoke steps (sequence 64, batch 2, no checkpoint) and exit 0, with the official `heldout_v1/` checks
(1,059 documents, report 0 matches, sha256). Each manifest shows its `muon_lr`, `optim.lr` 0.001, and `rope_theta` 10000,
`norm_eps` 1e-5, `mtp_weight` 0, `moe.bias` false. The 2-step scores do not rank the rates. The same three folders
test `summarize_screen.py --smoke-ok`.

## Limits

- One seed. The order of the three rates can change with another seed.
- 245 steps at T1, constant rate, no warmup. The pick is for this length; the T2 run is longer.
- Three rates a decade apart. The best rate may lie between two of them.
- The job held-out has no Punjabi or Assamese, so its Indic mean is over 9 slices and does not equal an 11-slice Indic mean on `heldout_v1/`.
- Each document takes its own 1,024-token slot with padding, so scored training tokens are below the input positions. The step count is the budget.
