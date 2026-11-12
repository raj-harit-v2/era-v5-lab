# Eval-mini scores for the config freeze, and eval schedule v0 (Gate 2 proposal, Team 09)

**Status:** proposal, 11 Nov 2026. TSAI decides at Gate 2 (Sat 14 Nov). Lead: `rahulni`.

Asked for in the week-2 G9 brief ("Your proposal of the eval-mini scores for the config freeze is in by Thu 12 Nov.
TSAI decides at Gate 2.") and on the CAP plan sheet (week 2: "TSAI picks the eval-mini scores for the config freeze").
The first eval schedule for the run (v0) is section 6, as TSAI asked in G9 on 11 Nov. `eval_schedule.md` becomes its
own file in week 3.

## Decisions requested

1. **Freeze set.** MMLU (0-shot, the first 10 items of each of the 57 subjects: 570 items) and MILU Hindi, Telugu,
   Tamil and Bengali (5-shot, the 100 eval-mini items of each: 400 items). 970 items in all, every one with four
   options, so chance is 25. These are the only eval-mini tasks that are both cleared for scoring our model
   (`benchmarks_v1.md`, Use "Evaluation") and covered by fingerprints v2.
2. **Role.** Bits per byte decides config v1, by Team 5's rule (`teams/05-architecture/experiments/plan_v1.md`).
   Eval-mini is a guard: it can block a candidate, never pick one.
3. **Block rule.** A candidate is blocked if (a) a freeze-set task returns no score, or fewer items than listed; or
   (b) its pooled freeze-set accuracy is below **22.2** (chance 25 minus 2 standard errors at 970 items) **and** more
   than **3.9** points below the baseline of the same experiment (2 standard errors of a difference at 970 items).
   Part (b) needs both, because a model that prefers one answer letter scores that letter's share of the items,
   which can sit below 25 for every candidate. A block goes to TSAI with the task, item count and score. TSAI
   decides, for example that the config v0 default stays (`plan_v1.md`, "Defaults if Thu 12 Nov has no result").
4. **Diagnostics.** ARC-Challenge, MMLU-Pro, Belebele (hi, te, ta) and HellaSwag may be run on lab checkpoints as
   internal diagnostics, labelled, and never as part of the rule. **TSAI to confirm:** `benchmarks_v1.md` Decision 7
   says ARC, MMLU-Pro and Belebele are "not a score for our model", while `firewall/eval_firewall.md` section 5
   expects labelled lab-checkpoint scores on them. If TSAI says no, only the freeze set is run.

## 1. Why bits per byte decides and eval-mini only guards

- The config v1 arms (attention type, expert count, optimizer) run at test size T2: 233M parameters, 1,221 steps of
  16,384 tokens (about 20M tokens), 3 seeds (`plan_v1.md`).
- Their differences are small. The one-seed T2 attention screen in PR #345 gives overall bits per byte from 1.9214
  to 1.9379, at most 0.85% from the reference. PR #345 marks these runs as not yet eligible for comparison.
- Eval-mini cannot see differences that small. On a 100-item task the sampling standard error at 25% is 4.3 points,
  and the difference between two candidates has a standard error of 6.1 points. Even on all 970 freeze-set items,
  a difference has a standard error of 2.0 points. Switching only the attention kernel moved 100-item tasks by up to
  2 items (`results/eval_mini_v1.json`, file note).
- The public models we ran (1.5B to 3B parameters) score 26 to 41 on these 100-item MILU sets (section 2). We expect
  a 233M model trained on about 20M tokens to score near chance. The first lab-checkpoint scores
  (`results/eval_mini_lab_ckpts.md`, due Fri 13 Nov) will show whether it does.
- What eval-mini can catch at this size is a broken candidate: a wrong tokenizer or export, a load error, a failed
  task, or scores clearly below chance and below the baseline. That is the guard.

## 2. The freeze set

| Task | Shots | Items | Item set (v1 schema) | Metric | Chance | Fingerprints v2 | `benchmarks_v1.md` |
|---|---|---|---|---|---|---|---|
| `mmlu` | 0 | 570 | `limit:10`, the first 10 per subject (`harness/run_eval_mini.py`, profile `mini`) | acc | 25 | yes | Evaluation |
| `milu_Hindi` | 5 | 100 | `spec:94de47d2…` (`harness_code_indic/eval_mini_v0_spec.json`) | acc | 25 | yes | Evaluation |
| `milu_Telugu` | 5 | 100 | same | acc | 25 | yes | Evaluation |
| `milu_Tamil` | 5 | 100 | same | acc | 25 | yes | Evaluation |
| `milu_Bengali` | 5 | 100 | same | acc | 25 | yes | Evaluation |

Scores of public models on the same items (`results/eval_mini_v1.json`, lm-eval 0.4.13):

| Task | SmolLM2-1.7B | Qwen2.5-0.5B | Qwen2.5-1.5B | gemma-2-2b | Llama-3.2-3B |
|---|---|---|---|---|---|
| mmlu (570) | 53.68 | 49.47 | 63.86 | not run | not run |
| milu_Hindi (100) | not run | not run | 37.0 | 31.0 | 36.0 |
| milu_Telugu (100) | not run | not run | 33.0 | 28.0 | 32.0 |
| milu_Tamil (100) | not run | not run | 31.0 | 30.0 | 29.0 |
| milu_Bengali (100) | not run | not run | 26.0 | 34.0 | 41.0 |

Left out of the freeze set, and why:

- **GSM8K:** decontamination only for our model's scores (`benchmarks_v1.md`, Decisions 6 and 7).
- **ARC, TruthfulQA, MMLU-Pro, BBH, HumanEval(+), MBPP(+), Belebele:** harness checks, "not a score for our model"
  (Decision 7), and not in fingerprints v2 (`firewall/eval_firewall.md` section 5).
- **HellaSwag:** internal only (Decision 8), and not in fingerprints v2.

The freeze set uses only items eval-mini already has, so the public-model scores above stay comparable. It needs
log-likelihood scoring only, no generation.

## 3. How the rule is computed

- Pooled accuracy = (570 × mmlu + 100 × each of the four milu scores) / 970.
- Standard error at chance: √(0.25 × 0.75 / 970) × 100 = 1.39 points. Part (b) of the block rule uses
  25 − 2 × 1.39 = 22.2, and 2 × √2 × 1.39 = 3.9 for the gap to the baseline.
- Per-task bands, for reading only (chance ± 2 standard errors): mmlu 21.4 to 28.6; each milu 16.3 to 33.7.
- The baseline of each experiment is the one `plan_v1.md` names: `attn-0` for attention, `exp3-base` for experts,
  and `exp2-adamw` (the config v0 optimizer) for EXP-2.
- Every record uses the eval-mini v1 schema (`results/eval_mini_v1_schema.md`; section 6 for lab checkpoints), so
  `model_revision` is the sha256 of the checkpoint's `MANIFEST.json`, or of the checkpoint file for a Team 5
  `checkpoint.pt`.

## 4. What is scored, and when

The final checkpoint (step 1,221) of each Team 5 arm and seed that Team 5 counts as a result is scored: at least the
candidate TSAI intends to freeze and the baseline of its experiment. Team 9 scores them with
`harness_lab/run_lab_ckpt.py` in its job request for the Team 4 and Team 5 checkpoints, and writes the results to
`results/eval_mini_lab_ckpts.md` (due Fri 13 Nov).

If these scores are not in before Gate 2, TSAI freezes on bits per byte as planned, and the guard runs on the first
dry-run-1 checkpoint of the frozen config (section 6). A block there goes to TSAI as an incident.

Team 4's KE2 decision input (`teams/04-ke2/decision_input.md`) asks for no eval-mini score, so this proposal covers
config v1 only.

## 5. Open points

- `harness_lab/run_lab_ckpt.py` is not on `main` yet (Member D, due Thu 12 Nov).
- Decision 4 waits for TSAI.
- The open items of the eval schedule are in section 6.5.

## 6. Eval schedule v0

The plan sheet makes the eval schedule a week-3 task ("Write eval_schedule.md: the benchmarks for each step of the
run"), and TSAI approves it in week 3 ("TSAI approves the eval schedule for the training run"). This v0 fixes the
structure. Week 3 moves it to its own file, `eval_schedule.md`, and closes the open items in section 6.5.

### 6.1 Dates (CAP plan sheet)

| Date | Event | What evaluation must show |
|---|---|---|
| Sat 14 Nov | Gate 2: tokenizer and config frozen | this proposal |
| Sun 15 to Sat 21 Nov | Dry run 1 | Gate 3: "The watcher scores each dry run 1 checkpoint, and the first shards have zero fingerprint hits." |
| 24 to 26 Nov | Dry run 2 | Gate 4: "Step-0 scores are near random, and the watcher survives the planned failure of dry run 2." |
| Sat 28 Nov | Training starts | nothing in this section |

### 6.2 What runs at each step

| Tier | When | Tasks | Items | Use |
|---|---|---|---|---|
| A | Every checkpoint the watcher sees: dry run 1, dry run 2 and the run | The freeze set (section 2): `mmlu` (0-shot, the first 10 per subject) and `milu_Hindi`, `milu_Telugu`, `milu_Tamil`, `milu_Bengali` (5-shot, eval-mini spec items) | 970 | Trend panel, and the guard (decision 3). Log-likelihood only |
| B | Every N-th checkpoint (N is open item 4) | `arc_challenge` (0-shot, first 500), `leaderboard_mmlu_pro` (5-shot, 300 spec items), `belebele_hin_Deva`, `belebele_tel_Telu`, `belebele_tam_Taml` (5-shot, 100 spec items each), `hellaswag` (0-shot, first 400) | 1,500 | Internal diagnostics, labelled "not decontaminated" and "not a score for our model". Only if TSAI allows them (decision 4) |
| C | Step 0 of dry run 2; the restored checkpoint after the planned failure of dry run 2 | Tier A, plus Tier B if allowed | 970 or 2,470 | The two Gate 4 checks |
| Later | When Tier A scores leave chance | Benchmarks marked "Evaluation" in `benchmarks_v1.md` | not set | Not in v0. A later version adds them, with TSAI approval |

All items are the ones eval-mini already has (`harness/run_eval_mini.py`, profile `mini`;
`harness_code_indic/eval_mini_v0_spec.json`), so every score can be read next to the public-model scores in section 2
and `results/eval_mini_v1.json`.

### 6.3 Near random at step 0 (Gate 4)

Chance is 25 on all Tier A items (four options each). Bands of chance ± 2 standard errors:

| Scope | Items | Band |
|---|---|---|
| Pooled Tier A | 970 | 22.2 to 27.8 |
| `mmlu` | 570 | 21.4 to 28.6 |
| each `milu_*` | 100 | 16.3 to 33.7 |

These bands assume no answer bias. A step-0 model often prefers one answer letter and then scores that letter's share
of the items, so the bands are checked against the answer-letter shares in week 3 (open item 5). A score above the band
at step 0 means the checkpoint is not step 0, or the evaluation has a bug.

### 6.4 How scoring works

- **Finding checkpoints:** only the folder that `latest.json` or a `commits.jsonl` line names, never one found by
  listing; weights through `export_safetensors()` (Team 7, PR #245; `results/eval_mini_v1_schema.md` section 6).
- **Scoring:** `harness_lab/run_lab_ckpt.py` writes eval-mini v1 records with the `checkpoint` fields.
  `eval_watcher.py` (week 3) runs it on each new checkpoint.
- **Storage:** Team 8's ClickHouse table `eval_mini` (`teams/08-monitoring/clickhouse/schema_v1.sql`). Team 8's eval
  tables are due 18 Nov (plan sheet). Team 8 plots scores by `checkpoint.step`.
- **Compute:** TSAI gives a GPU slot for the watcher (plan sheet, week 3).
- **Eval files** stay in the eval folder (`firewall/eval_firewall.md`). Results carry task names, IDs and scores only.
- **Public scores:** TSAI approves each one (plan sheet, week 4). Nothing in this schedule is public by default.

### 6.5 Open items for week 3

1. Checkpoint interval of the V5 run: Team 7. `teams/07-infrastructure/docs/checkpoint_design_v0.md` says the final
   V5 numbers wait for the model configuration; V4 saved every 500 steps or 30 minutes.
2. Size of the watcher's GPU slot: TSAI.
3. Time for one Tier A and one Tier B run on a lab checkpoint: measured in the job for the Team 4 and Team 5
   checkpoints (`results/eval_mini_lab_ckpts.md`, due Fri 13 Nov).
4. N for Tier B, from items 1 to 3.
5. The step-0 bands against the answer-letter shares of the Tier A items (section 6.3).
6. Whether Tier B runs at all (decision 4).
7. Benchmark names and score format for Team 11 (plan sheet, week 4).

## Sources

- Week-2 G9 brief (31 Oct 2026); CAP plan sheet, Team 9 tab, weeks 2 to 4; TSAI in G9, 11 Nov (eval schedule v0 as
  the last section of this file).
- `teams/05-architecture/experiments/plan_v1.md`; PR #345 (one-seed T2 attention screen).
- `teams/09-evaluation/benchmarks_v1.md` (Use legend; Decisions 6 to 8); `firewall/eval_firewall.md` section 5;
  `fingerprints/v2/MANIFEST.json` (`set_sha256` `2826a3b8…`, PR #280).
- `results/eval_mini_v1.json` and `results/eval_mini_v1_schema.md` (PR #186); `harness/run_eval_mini.py`;
  `harness_code_indic/eval_mini_v0_spec.json`.
- `teams/04-ke2/decision_input.md`; `teams/07-infrastructure/docs/checkpoint_design_v0.md`;
  `teams/08-monitoring/clickhouse/schema_v1.sql`.
