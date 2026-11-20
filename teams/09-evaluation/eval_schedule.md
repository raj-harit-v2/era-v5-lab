# Eval schedule v1 (Team 09)

**Status:** v1.1, Thu 19 Nov 2026 (v1 plus the review points on #662), week-3 task 4. Lead: `rahulni`. This is Team
9's proposal. TSAI decides the eval schedule at Gate 3 (Sat 21 Nov): "The eval schedule for the run [decide]: TSAI
decides at Gate 3" (Team 9 week-3 work order, section 5).

Week-3 work order, task 4: "Write `eval_schedule.md`: the benchmarks for each step of the run. Add the post-training
benchmarks and the accuracy per effort level (Session 18)." This file replaces the v0 schedule in section 6 of
[`results/config_freeze_proposal.md`](results/config_freeze_proposal.md) (#357, Gate 2). That section stays as the Gate 2
record. TSAI in G9, 11 Nov: "eval_schedule.md becomes its own file in week 3."

How to read it: **Fact** lines give a source. **Proposal** lines are Team 9's choice, for TSAI to accept or change.
**Open** lines wait for another team or TSAI; section 14 lists them with owners.

## 1. Dates and gates

| Date | Event | What evaluation must show |
|---|---|---|
| Sat 21 Nov | Gate 3 | "The watcher scores each dry run 1 checkpoint, and the first shards have zero fingerprint hits." Plan sheet milestone: "Automatic checkpoint evaluation live" |
| 24 to 26 Nov | Dry run 2 | Gate 4: "Step-0 scores are near random, and the watcher survives the planned failure of dry run 2." Milestone: "Step-0 eval of dry run 2", 24 Nov |
| Sat 28 Nov | Training starts | TSAI gives go or no-go for evaluation (plan sheet, week 4) |

Other teams wait for these from Team 9 (CAP plan sheet, "depends" rows):

| Team | What they need from Team 9 | Date |
|---|---|---|
| Monitoring (8) | checkpoint scores | 21 Nov |
| Architecture (5) | step-0 evaluation of dry run 2 | 24 Nov |
| Release (11) | the public score format; Team 9's week-4 task: "Give Team 11 the benchmark names and the score format" (Team 11 gives its dashboard text format on 25 Nov) | 26 Nov |
| Post-training (10) | RL model scores | 27 Nov |
| Data B (2) | the Indic benchmark list | week 4 |
| Quantization (12) | the eval watcher score format; week 4: "match the watcher scores" on a dry run 2 checkpoint | week 3 and 4 |

## 2. Pre-training checkpoints: what runs at each commit

The tiers count **commits** (lines of Team 7's `commits.jsonl`), not minutes. The checkpoint interval of the main run is
not fixed yet (section 3), so a rule in commits stays right when the interval changes.

| Tier | When | Tasks | Items | Use |
|---|---|---|---|---|
| A | Every commit (`--every 1`) of dry run 2 and the main run | The freeze set: `mmlu` 0-shot, the first 10 per subject (570); `milu_Hindi`, `milu_Telugu`, `milu_Tamil`, `milu_Bengali` 5-shot, the eval-mini spec items (100 each) | 970 | The trend (panel 28) and the in-run signals of section 6. Log-likelihood only |
| B | Every 10th commit (`--every 10`) | `arc_challenge` 0-shot first 500; `hellaswag` 0-shot first 400; `leaderboard_mmlu_pro` 5-shot, 300 spec items; `belebele_hin_Deva`, `belebele_tel_Telu`, `belebele_tam_Taml` 5-shot, 100 spec items each | 1,500 | Diagnostics only. Every number carries the label "diagnostic, not cleared for contamination" |
| C | The step-0 commit of dry run 2, and the restored checkpoint after its planned failure | Tier A and Tier B | 2,470 | The two Gate 4 checks (sections 4 and 5) |
| Later | Section 7 | Benchmarks marked "Evaluation" in [`benchmarks_v1.md`](benchmarks_v1.md) | not set | With TSAI approval |

- **Fact:** tasks, shots, item sets, seeds, primary metrics and labels are the ones in
  [`harness_lab/eval_lab_v1.yaml`](harness_lab/eval_lab_v1.yaml) (spec sha256 `94de47d2…`, lm-eval 0.4.13).
- **Fact:** Tier B "every N-th checkpoint": TSAI's comment on #357 (12 Nov): "use every 10th until TSAI says otherwise".
  TSAI's Decision 4 on #357 allows these diagnostics on lab checkpoints: each number is labelled, they never pick or
  block a candidate, and no score is shown as a model score outside the lab.
- **Fact:** dry run 1 saved one final checkpoint (TSAI on #475). It is scored once per tier by the job in
  [`jobs/2026-11-15-eval-watcher-dry-run-1.md`](jobs/2026-11-15-eval-watcher-dry-run-1.md).

## 3. Interval, time per checkpoint and the GPU slot

**Facts:**
- Checkpoint interval: dry run 1 `INTERVAL_S=600` (10 min), "Status: provisional". Main run: "the same rule, re-run
  when the model size and the GPU count are fixed", which "gives 10 min at 64 to 256 GPUs and up to 30 min on a single
  8-GPU node" ([`../07-infrastructure/docs/checkpoint_interval.md`](../07-infrastructure/docs/checkpoint_interval.md),
  the summary at the top and section 4). It names no interval for dry run 2.
- Measured time per checkpoint at the dry run 1 shape (T2, 237M parameters) on a Tesla T4 in fp32, which has no
  native bf16, so these are upper bounds for the bf16 eval slot (job file above, "Max time"):

  | Path | Tier A | Tier B | Per checkpoint (A + B/10) |
  |---|---:|---:|---:|
  | Team 7 store (export + scoring) | 95.6 s | 133.5 s | 108.9 s |
  | Team 5 run folder (`--team5-run`) | 53.6 s | 81.4 s | 61.7 s |

- At a 600 s interval that is 144 commits a day, so about 15,700 s or **4.4 GPU-hours a day** on the store path.
- Session 18 (14 Nov, auto-transcript): at a checkpoint "main training is continuing"; "if evaluation is let's say
  half an hour you know we are good"; if it is bad, "we stop … and we start from there"; so "your validation should be
  very fast". It also warns that a badly run evaluation means "interfering with the main cluster", and asks for the
  script to run "very infrequently", "taking the checkpoints where the checkpoints are there and immediately running it".

**Proposal (time budget):**
- The watcher runs only on the eval slot, never on a training node ([`firewall/eval_firewall.md`](firewall/eval_firewall.md),
  section 3, rule 4). So it takes no GPU time from training. That is how the work order's "every checkpoint gets a
  score" and Session 18's warning about slowing the main cluster both hold.
- Every Tier A score lands in ClickHouse within **30 minutes of its commit**. The watcher records the lag from commit to
  score in its state file, and stops a scorer after `--timeout 1800` s.
- If the slot cannot keep up, Tier A drops to every k-th commit (with `--protect-every` changed to match, section 4),
  and this file says so.
- **Open:** measure the time per checkpoint again at the main-run size on the eval slot before 28 Nov. The 4.4
  GPU-hours a day is for the T2 shape only. TSAI approves the slot size.

## 4. Retention: protected checkpoints

**Facts:**
- Team 7: "Team 9 sets the protected cadence; this keeps their 2.5 h spacing until they name a step count"
  (`checkpoint_interval.md`, section 5, which shows `--keep 9 --protect-every 15` at 10 min).
- [`harness_lab/eval_watcher.py`](harness_lab/eval_watcher.py): "`--every N` scores commit number N, 2N, 3N ... of
  commits.jsonl, the count Team 7's retention uses for `protect_every` ((i + 1) % N == 0). With N equal to
  protect_every, retention never deletes a checkpoint before it is scored."

**Proposal (D1):** `--protect-every 10`, the same commits Tier B scores. At 10 min that is one protected checkpoint
every 100 min, and 1.5 times the protected storage of 15. Team 7 agreed in the 07 Infrastructure group (19 Nov):
"protect-every 10: fine, since storage is small at T2". **Open:** Team 7 to put the value in section 5 of
`checkpoint_interval.md`, so `main` has one number.

- Team 7 also pins the step-0 commit and the commit the planned failure restores from (same message, 19 Nov).
- A checkpoint that retention deletes before it is scored is recorded as `gone` (watcher), never silently skipped.

## 5. Gate 4: step 0 and the planned failure

### 5.1 Where step 0 comes from

**Facts:**
- Nothing on `main` commits step 0 today: `train_week2.py` refuses `--stop-after 0`. Team 9 asked for an opt-in step-0
  commit on #608 (18 Nov). The author asked whether Gate 4 needs "an evaluation-only snapshot of the initial weights or
  a checkpoint that must also resume training from step 0", and Team 9 asked for the resumable one (D8 below).
- #608 (open, ready for review) adds `--checkpoint-at-start`: "Commit resumable step-0 state on a fresh run before
  training"; resumes skip it. The author on #608 (19 Nov): its tests check that a restore from step 0 gives identical
  loss traces and final model hashes, and that a pin keeps step 0 through retention. The author asked Team 9 to check
  that it meets the watcher's Gate 4 needs.
- TSAI (G9, 17 Nov): "Dry run 2 (24 to 26 Nov) is planned under the Team 7 supervisor and Checkpointer. Keep the
  watcher able to read both formats."

**Proposal (D8):** a normal, resumable Checkpointer commit at step 0 on a fresh run (skipped on resume), pinned by
Team 7. Evaluation needs only the weights, but a normal commit means the watcher, `run_lab_ckpt.py`, the pin and
retention all work unchanged, with no second path to build or test. **Open:** #608 to merge, and the dry run 2 job
to pass `--checkpoint-at-start` (Team 5 and Team 7). Without both, dry run 2 has no step 0 to score.

### 5.2 Near random at step 0

**Fact:** bands of chance plus or minus 2 standard errors (#357, section 6.3): pooled Tier A 22.2 to 27.8 (970 items);
`mmlu` 21.4 to 28.6 (570); each `milu_*` 16.3 to 33.7 (100). These bands assume no answer bias. A step-0 model often
prefers one answer letter and then scores that letter's share of the items.

**Fact (counted 19 Nov, closes v0 open item 5):** the gold answers of the 970 Tier A items, and the score of a model
with uniform next-token probabilities. Counted by `rahulni` (standing access,
[`firewall/access_list.md`](firewall/access_list.md) section 1) under firewall section 4: a separate `HF_HOME`, deleted
afterwards; counts only, no item text. Items: `cais/mmlu` @ `c30699e8…` (57 subjects, first 10 test rows each) and
`ai4bharat/MILU` @ `846d7016…` (the spec items; each task's `items_sha256` matched `eval_mini_v0_spec.json`).
Tokenizer: p1536 (`e6b93a93…`).

| Task | Items | Gold A / B / C / D (%) | One-letter range | Band | Uniform model |
|---|---:|---|---|---|---:|
| `mmlu` | 570 | 26.1 / 25.3 / 24.4 / 24.2 | 24.2 to 26.1 | 21.4 to 28.6 | 26.1 |
| `milu_Hindi` | 100 | 29 / 20 / 27 / 24 | 20 to 29 | 16.3 to 33.7 | 27.0 |
| `milu_Telugu` | 100 | 27 / 20 / 30 / 23 | 20 to 30 | 16.3 to 33.7 | 24.0 |
| `milu_Tamil` | 100 | 34 / 28 / 18 / 20 | 18 to **34** | 16.3 to 33.7 | 25.0 |
| `milu_Bengali` | 100 | 18 / 31 / 31 / 20 | 18 to 31 | 16.3 to 33.7 | 26.0 |
| Pooled | 970 | 26.5 / 25.1 / 25.3 / 23.2 | 23.2 to 26.5 | 22.2 to 27.8 | 25.9 |

How to read it:
- `mmlu` scores the letters " A" to " D", one token each, so a step-0 model scores the share of the letter it happens
  to prefer: 24.2 to 26.1, inside the band.
- `milu_*` scores the option texts (`utils_milu.py`), so a near-uniform model picks the option with the fewest tokens,
  the first one on a tie (lm-eval's `argmax`). That gives 24.0 to 27.0, inside the band.
- `milu_Tamil`: option A is gold for 34 of 100 items. A step-0 model that always picks the first option would score
  34.0, above the band's 33.7, without being trained.

**Proposal (D2):** step 0 passes when each Tier A score is inside its band, **or** inside that task's one-letter range in
the table. With these counts the second part matters only for `milu_Tamil` (up to 34.0). Only the freeze set decides.
Tier B is reported, with its label. A score above both means the checkpoint is not step 0, or the evaluation has a bug:
Team 9 reports it to TSAI at once.

### 5.3 The planned failure

**Fact (Team 7, 19 Nov):** the planned failure is "SIGKILL between two commits, so the restore goes back to the last
COMPLETE one". Team 7 owns the drill plan, and adds: "Dry run 2's planned failure only tests G7's path if #608 lands
first." Plan sheet, week 4: "Check that the watcher scores the restored checkpoint
after the planned failure."

**Proposal (evidence for Gate 4):**
1. The Tier A and Tier B watchers' state files show every owned commit scored once across the kill: none missing, none
   scored twice.
2. The restored checkpoint is scored. If the restore commits a step again, the newer commit is scored and the older one
   is marked `superseded` (watcher rule).
3. The commit-to-score lag table covers the time of the kill.

**Fact:** panel 28 shows one score per step and series, the newest:
`argMax(value, (ifNull(checkpoint_epoch, 0), loaded_at))`
([`../08-monitoring/grafana/private_v1.json`](../08-monitoring/grafana/private_v1.json)). So step 0's Tier A and Tier C
rows, and a step that the restore commits again, need no panel change.

Team 7's restore drill (#491, #573) passed bit-equal in both of its jobs (07 Infrastructure group, 19 Nov). That
supports point 2 but is not evidence for the watcher.

## 6. Signals during a run

**Fact:** the guard of #357 (Decision 3) blocks a candidate when (a) a freeze-set task returns no score, or fewer items
than listed; or (b) pooled accuracy is below 22.2 **and** more than 3.9 points below the experiment's baseline.
Part (b) needs a baseline run, and a single training run has none.

**Proposal (D9)** for one training run, on Tier A:

| Level | When | What Team 9 does |
|---|---|---|
| Incident | A freeze-set task has no score or fewer items than `expected_items` (`eval_lab_v1.yaml`); a scorer fails `--max-attempts` times; a Tier B checkpoint is `gone` | Post in G9 and fix the watcher. Not a signal about the model |
| Check | Pooled Tier A drops more than 3.9 points below the previous scored commit. Applies only after the section 7 trigger, because before it scores sit at chance | Look at the loss panels and the per-task scores; post in G9 |
| Recommend stop | The same check fires on 2 commits in a row | Tell TSAI at once in G9, with task, step, item count and score. TSAI decides; Session 18: "we stop … and we start from there" |

**Open:** an eval alarm. Team 8 has none on `eval_mini` today, so a stopped watcher would go unseen. Team 9 asked Team 8
(18 Nov) for a page when a run's newest `eval_mini` step lags its newest training step by more than 2 checkpoint
intervals. That needs one run ID in both tables (#606, merged 19 Nov). Until the alarm exists, Team 9 checks panel 28
once a day. The on-call note for eval failures is a week-4 task.

## 7. Later benchmarks on pre-training checkpoints

**Proposal (D3):** add the bigger "Evaluation" benchmarks to pre-training checkpoints once pooled Tier A is above 27.8
(the top of the chance band) at 2 commits in a row. TSAI approves each addition. Until then they add cost and show
only chance.

## 8. Post-training benchmarks (SFT and RL checkpoints)

**Facts:**
- [`benchmarks_v1.md`](benchmarks_v1.md) marks these "Evaluation" and fingerprints v2 covers them
  ([`fingerprints/v2/MANIFEST.json`](fingerprints/v2/MANIFEST.json), `set_sha256` `2826a3b8…d22a`):

  | Area | Benchmark | Items (`benchmarks_v1.md`) |
  |---|---|---|
  | Coding and agentic | SWE-bench Verified | 500 |
  | | SWE-bench Live | 300 (Lite) |
  | | SWE-bench Pro | 731 |
  | | Terminal-Bench 2.0 | 89 |
  | | BFCL v3 | 4,441 |
  | Indic | MILU | 79,608 (no Sanskrit; 9 of the 10 pack languages) |
  | Reasoning | GPQA Diamond | 198 |
  | | HLE (text-only) | 2,158 |
  | General | MMLU | 14,042 |
  | Long context | LongBench v2 | 503 |

- Six "Evaluation" benchmarks are **not** in fingerprints v2 (status "planned" in `MANIFEST.json`): tau2-bench,
  WebArena, WorkArena, BrowseComp, OSWorld, IndicGenBench.
- RULER and ONERULER are "Evaluation" but synthetic: items are generated at eval time, so there is nothing to
  fingerprint (status "skip"). They need a set context length.
- "Harness check" benchmarks are never a score for our model (`benchmarks_v1.md`, Decision 7). "Internal only"
  benchmarks run internally only, and their items are never published or copied into the repo (Decisions 3, 5, 8).
- No runner for these benchmarks exists in the lab repo yet. Team 10's SFT and RL jobs keep no weights yet; the next
  one will save through Team 7's Checkpointer and `export_safetensors()`, which the watcher reads (Team 10 lead, 18 Nov;
  #634, drafts not runnable). Team 10 has since built a default-off `--keep-weights-dir` on the SFT and RL job scripts,
  saved through Team 7's Checkpointer and readable by `run_lab_ckpt.py`; its PR goes to Team 10's week-3 branch (10
  Post-training group, 19 Nov 20:17).

**Proposal (D4):** post-training benchmark set v1 = the 10 benchmarks above, built in waves. Wave 1, one per priority
area: SWE-bench Verified, MILU, GPQA Diamond, MMLU. Each wave needs its own job request and a test log.

**Proposal (D6):** fingerprint the six missing benchmarks before the main-run data is checked. Every shard passes
`decontam_check.py` before training reads it (firewall section 5), so a set added later protects the main run only if
the checked shards are scanned again. Rule: when a new fingerprint set version lands, every shard already checked is
scanned again with it before training reads it. A rescan is cheap: #641 checked all 41 first shards (1,200,725
documents) in 1 h 41 min on a laptop CPU, 3 shards at a time (`results/decontam_shards.md`). Until the six are in a
set, any number on them is labelled "not decontaminated". TSAI decides.

**Forgetting check (Team 10, [`../10-post-training/sft/eval_v1.md`](../10-post-training/sft/eval_v1.md)):** ARC-Challenge
(first 500) and HellaSwag (first 400) before and after SFT, with bits per byte. Its `forgetting.py` refuses reports
that differ in device, dtype, metric, item count or few-shot count. **Proposal:** the watcher scores the base and the
after-SFT checkpoint with the same command, slot, dtype and items (the Tier B rows have exactly these two tasks and
item counts).

**Fact (Team 10 lead, lab G, 19 Nov 19:41):** `forgetting.py` reads the eval-mini rows. It needs one record per task
for `arc_challenge` and `hellaswag` with task, metric, filter, value, stderr, n_items and num_fewshot, and returncode 0
with no error_tail. Value and stderr must be fractions (0 to 1) in both reports: its 0.01 floor and at-limit margin
assume fractions. Eval-mini v1 rows hold points, 0 to 100
([`results/eval_mini_v1_schema.md`](results/eval_mini_v1_schema.md), section 3).

**Proposal:** Team 9 hands both reports to `forgetting.py` in fractions, with value and stderr divided by 100, the same
step for base and after-SFT. The rows in ClickHouse stay in points, so panel 28 does not change.

**Proposal:** the generation backend for these benchmarks is vLLM (Session 18, which teaches "serving with vLLM": Lab 3
briefing, section 4). It is not built yet.

**Open:** which SFT and RL checkpoints come to Team 9, and when (TSAI, Team 10). Team 10 needs the RL model scores by
27 Nov.

## 9. Accuracy per effort level

**Facts (Team 10, [`../10-post-training/rl/effort_v1.md`](../10-post-training/rl/effort_v1.md) and
[`../10-post-training/eval/README.md`](../10-post-training/eval/README.md)):**
- The levels are `1k`, `4k`, `16k` and `64k`: budgets of 1,024, 4,096, 16,384 and 65,536 reasoning-trace tokens. The
  label is text in the first system turn, `Reasoning effort: {level}`. The final reply is not counted.
- With one 1,024-token cap for every label, the label did nothing visible, and "generation caps must be decoupled from
  the effort budget". A run with the cap set to the label's budget plus a reply allowance (Stage C) has not been done.
- Team 10's 100-slot effort suite is development evidence for the labels: "G9's own final score is separate."
- Session 18: the serving stack's reasoning parser lets users select the level. The transcript gives no format for the
  per-level readout.
- Team 10 lead (18 Nov): at 2,048 tokens the 4k, 16k and 64k budgets cannot fit; plan 1k on dry run 1 and placeholders
  for the rest until TSAI sets the context length. TSAI decides the context length for each phase at Gate 3.

**Proposal (D5):**
- Benchmarks: GPQA Diamond (198), the Tier A MILU spec items (Hindi, Telugu, Tamil, Bengali, 400), and one code set
  from the section 8 list (proposal: SWE-bench Verified, once its runner exists).
- Each item runs at each level that fits: prompt + the level's budget + a reply allowance must fit the context length
  TSAI sets. The cap follows the level, never one fixed cap.
- Dry runs: `1k` only. `4k`, `16k`, `64k`: placeholders until the context length is set.
- Readout per benchmark and level: accuracy, median trace tokens, and the share of items over budget. Scores and counts
  only: no generated text and no output token ids in the repo, since the public tokenizer turns ids back into text.
- Team 10's effort suite stays theirs. This readout uses Team 9 benchmarks only.

## 10. How scoring works

- **Pipeline:** [`harness_lab/eval_watcher.py`](harness_lab/eval_watcher.py) follows a run's `commits.jsonl` (never a
  directory listing) and runs `harness_lab/run_lab_ckpt.py --scorer lm_eval_lab:team5` in its own process for each
  owned commit, then Team 8's `load_jsonl.py`. It also reads a Team 5 run folder (`--team5-run`), so both formats TSAI
  asked for are covered.
- **Inputs:** the frozen tokenizer p1536 (sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`)
  and Team 4's p1536 raw table `teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz`. The scorer refuses a tokenizer
  other than the run manifest's.
- **Dataset revisions** (pinned in the job file): `cais/mmlu` `c30699e8…`, `ai4bharat/MILU` `846d7016…`,
  `allenai/ai2_arc` `210d026f…`, `Rowan/hellaswag` `218ec52e…`, `TIGER-Lab/MMLU-Pro` `b189ec76…`,
  `facebook/belebele` `7899cdfa…`.
- **Output head:** the scorer calls the model's dense output head (`model.head`). Config v1 leaves the output head to
  TSAI (`embedding.ke2_output_dim` is empty), and dry run 1 used the dense untied head. **Open:** if TSAI picks a KE2
  output head for a later run, the scorer changes first (Team 9 with Team 4).
- **Storage:** Team 8's `eval_mini` table in ClickHouse database `default`
  ([`../08-monitoring/clickhouse/schema_v1.sql`](../08-monitoring/clickhouse/schema_v1.sql)), one `run_id` per checkpoint
  and tier: `<run>:<commit path>:<label>:<model_revision[:12]>`. Panel 28 of the private dashboard plots it. Records
  follow the eval-mini v1 schema ([`results/eval_mini_v1_schema.md`](results/eval_mini_v1_schema.md), section 6).
- **Open:** the ClickHouse address of the eval slot (TSAI). Without it the watcher runs with `--no-load`, and the rows
  are loaded later with `load_jsonl.py`.
- **Firewall:** eval files are placed only in an approved Team 9 job's folder and deleted when it ends. Scores only: no
  `--log-samples`, no item text in `out/` or logs, and `canary_scan.py … --lab-only` exits 0 before results return
  (`eval_firewall.md`, section 3).

## 11. Results and who reads them

- **Proposal (D10):** lab checkpoint scores go in one file, `results/eval_mini_lab_ckpts.md` (the file
  `eval_lab_v1.yaml` already names), with one section per run.
- **Score format** for Teams 11 and 12: eval-mini v1 (`results/eval_mini_v1_schema.md`). Team 12 matches the watcher's
  bf16 scores. Quantized evaluation runs only through Team 12's flow and limits, so Tier A and Tier B stay bf16.
- **Public text** (Team 11 review, `../11-release/model_card/rotation_SreekanthZipsy.md`): name only benchmarks marked
  "Evaluation"; write `[number: waiting for TSAI]` until TSAI approves a score; say which benchmarks have no fingerprint
  coverage. TSAI approves each public score (plan sheet, week 4). No eval panel is public until TSAI decides the public
  dashboard panels (Gate 3).
- **Proposal (D11):** a public contamination number counts a flag with only one matching 13-word run only if the
  document also holds the item's options or answer. #656: of the 351 one-run flags in `verdicts_v0-clean.csv`, the
  first pass labels 321 false-hit and 0 real, and all 44 `real` flags have two or more runs. This is for reports only:
  the training filter still drops every flagged document (#656). TSAI decides.

## 12. Job requests this schedule needs

Compute rule: "You get no keys and no machine access. Send a job request." Each scoring run below is one request.

| # | Job | State |
|---|---|---|
| 1 | Dry run 1 checkpoint, Tier A and Tier B | [`jobs/2026-11-15-eval-watcher-dry-run-1.md`](jobs/2026-11-15-eval-watcher-dry-run-1.md), on `main` (#549). Not run yet: TSAI restarted its job runner and queued it on 19 Nov (07 Infrastructure group, 15:13). Gate 3 evidence |
| 2 | Dry run 2 watcher: Tier A every commit, Tier B every 10th, step 0 and the restored checkpoint | to file before 24 Nov |
| 3 | Main-run watcher | to file before 28 Nov, with the time per checkpoint at the main-run size |
| 4 | Post-training evaluation (section 8 wave 1, the forgetting check, section 9) | after an SFT or RL job keeps weights |

## 13. Before each gate

- Run the job-file check of `eval_firewall.md` section 3 (`git grep` over `teams/*/jobs/*.md`) and send any hit to TSAI.
- Every shard passes `decontam_check.py` and `canary_scan.py` before a training job reads it (section 5). Gate 3's
  41 first shards: `results/decontam_shards.md` (task 2).
- The RL pool (task 5): `results/decontam_rl_pool.md` (#661, merged 19 Nov).
- The check on the checker: #656 (`results/flagged_check.md`) hand-checks 50 flagged documents against their items.

## 14. Open items

| # | Item | Owner | When |
|---|---|---|---|
| 1 | Run the #549 dry run 1 job; the ClickHouse address of the eval slot | TSAI | Gate 3 evidence, Fri 20 Nov |
| 2 | Step-0 commit in dry run 2: merge #608 (`--checkpoint-at-start`) and use it in the dry run 2 job | Team 5, Team 7 | before 24 Nov |
| 3 | `--protect-every 10` in `checkpoint_interval.md` section 5 (asked 19 Nov; not on `main` yet) | Team 7 | before 24 Nov |
| 4 | Eval-lag alarm on `eval_mini` | Team 8 | dry run 2 |
| 5 | Main-run size, sequence length, context length per phase, precision, output head | TSAI (Gate 3), Team 4 for the head | Sat 21 Nov |
| 6 | Time per checkpoint at the main-run size on the eval slot; slot size | Team 9, TSAI | before 28 Nov |
| 7 | Which SFT and RL checkpoints come to Team 9, and when | TSAI, Team 10 | before 27 Nov |
| 8 | Fingerprint the six missing benchmarks (D6) | TSAI decides | before the main-run data check |
| 9 | Closed 19 Nov: `forgetting.py` reads the watcher's rows, with value and stderr in fractions (section 8) | Team 10 | done |
| 10 | Team 6's full-size save time (moves the interval). #485 gave shares only (a save is 8% copy to CPU, 92% file write); TSAI keeps the absolute times, so the 600 s interval stays provisional | Team 6, Team 7 | due Thu 19 Nov; still open |

## 15. Changes

Each change to this schedule is a pull request that TSAI approves. **Proposal:** once TSAI accepts it at Gate 3, the
schedule is frozen with the launch config, and changes after 26 Nov need TSAI's approval.

## Sources

- Team 9 week-3 work order (G9, 14 Nov); Capstone Lab 3 briefing (14 Nov), sections 3, 4 and 7; CAP plan sheet, Team 9
  tab, weeks 3 and 4, and the "depends" rows of Teams 5, 10, 11 and 12; Session 18 transcript (14 Nov).
- TSAI on #357 (12 Nov), #475 (16 Nov), in G9 (11 Nov; 17 Nov 15:17) and in G6 (17 Nov, #485).
- [`results/config_freeze_proposal.md`](results/config_freeze_proposal.md) sections 1 and 6;
  [`harness_lab/eval_lab_v1.yaml`](harness_lab/eval_lab_v1.yaml); [`harness_lab/eval_watcher.py`](harness_lab/eval_watcher.py);
  `harness_lab/lm_eval_lab.py`; [`jobs/2026-11-15-eval-watcher-dry-run-1.md`](jobs/2026-11-15-eval-watcher-dry-run-1.md);
  [`benchmarks_v1.md`](benchmarks_v1.md); [`fingerprints/v2/MANIFEST.json`](fingerprints/v2/MANIFEST.json);
  [`firewall/eval_firewall.md`](firewall/eval_firewall.md); [`firewall/access_list.md`](firewall/access_list.md).
- [`../07-infrastructure/docs/checkpoint_interval.md`](../07-infrastructure/docs/checkpoint_interval.md); 07 Infrastructure
  group, 19 Nov (answers to Team 9's three asks); #573.
- [`../05-architecture/configs/config_v1.yaml`](../05-architecture/configs/config_v1.yaml); #608.
- [`../08-monitoring/clickhouse/schema_v1.sql`](../08-monitoring/clickhouse/schema_v1.sql); #517 (panel 28); #606;
  #641; #656; #661.
- [`../10-post-training/rl/effort_v1.md`](../10-post-training/rl/effort_v1.md);
  [`../10-post-training/eval/README.md`](../10-post-training/eval/README.md);
  [`../10-post-training/sft/eval_v1.md`](../10-post-training/sft/eval_v1.md); #634; Team 10 lead in the CAP G group,
  18 and 19 Nov.
- [`../11-release/model_card/rotation_SreekanthZipsy.md`](../11-release/model_card/rotation_SreekanthZipsy.md); #460.
