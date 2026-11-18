# eval-mini on the dry run 1 checkpoint, and the watcher for later runs (week 3, task 1)

Week-3 work order, Team 9 task 1: "Write eval_watcher.py. It scores each new checkpoint and writes the result to
ClickHouse." Gate 3 evidence: "The watcher scores each dry run 1 checkpoint". TSAI in G9 (14 Nov): "move lm_eval_lab.py
into the watcher PR. State the time per checkpoint in the PR. TSAI approves the slot there."

Dry run 1 is finished (TSAI on #475, 16 Nov): exp2_muon at T2, seed 1234, tokenizer p1536, 1,221 of 1,221 steps, one
final checkpoint (about 2.2 GB) kept by TSAI, no Team 7 package. So this job scores that one checkpoint, Tier A and
Tier B, from the Team 5 run folder (`--team5-run`), and loads the rows into ClickHouse `eval_mini`. Inputs are re-pinned
to p1536, as the Gate 3 notice asks Team 9 to do for all new work. The commit-following watchers below are for later
runs that save through Team 7's Checkpointer.

```text
Team:            09-evaluation
Owner:           Team 9 lead (rahulni). Lab rule 3 (Lab 3 briefing): no person names in the lab repo.
Lead approval:   rahulni (Team 9 lead). The GPU slot is for TSAI to approve in this PR.
Question:        What are the eval-mini freeze-set and diagnostic scores of the dry run 1 checkpoint, loaded into ClickHouse without a person in the loop, and how long does one checkpoint take on the eval slot?
Script:          teams/09-evaluation/harness_lab/eval_watcher.py (this PR). It runs harness_lab/run_lab_ckpt.py --team5-run --scorer lm_eval_lab:team5 in its own process, then teams/08-monitoring/clickhouse/load_jsonl.py.
Command:         python teams/09-evaluation/harness_lab/eval_watcher.py --team5-run ./out/dryrun1-1234 --label tier-a --scorer lm_eval_lab:team5 --clickhouse-url <ClickHouse URL> -- --device cuda --tier A --model-config ./out/dryrun1-1234/manifest.json --tokenizer ./inputs/tokenizer.json --tokenizer-sha256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b --byte-table teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz --hf-home ./inputs/hf --offline
                 Then the same with --label tier-b and --tier B (the two share one slot lock; each exits 0 when its checkpoint is scored and loaded).
Config:          teams/09-evaluation/harness_lab/eval_lab_v1.yaml; items from teams/09-evaluation/harness_code_indic/eval_mini_v0_spec.json (sha256 94de47d2…)
Inputs:          (1) ./out/dryrun1-1234/: TSAI's dry run 1 output folder (manifest.json, checkpoint.pt, summary.json with status COMPLETED), read only. checkpoint.pt is opened with mmap and only state["model"] is loaded; its weights hash must equal summary.json final_model_sha256.
                 (2) The model config is that run's own manifest.json (config.model): exp2_muon at T2 (8 layers, width 512, 16 routed experts + 1 shared, top-2, ke1, P32).
                 (3) ./inputs/tokenizer.json, the frozen p1536 (sha256 e6b93a93…25a64b, the file dry run 1 trained with), and Team 4's p1536 raw P32 table on main, teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz (file sha256 21072027…168a). The scorer refuses a tokenizer other than the manifest's artifacts.tokenizer_sha256.
                 (4) ./inputs/hf: a Hugging Face cache with the datasets of the 11 tasks at the revisions below, placed by TSAI in this job's folder only and deleted after the job (eval_firewall.md section 3, rule 4). It must be writable: lm-eval's hellaswag preprocessing writes its datasets map cache there (93 MB) on the first run.
Hardware:        1 GPU with native bf16, not a training node (eval_firewall.md section 3, rule 4). Tier A and Tier B share it through one slot lock, so only one model is loaded at a time.
Packages:        torch >= 2.14.1 (run_lab_ckpt.py checks it), lm_eval 0.4.13 (the scorer stops on another version), datasets 5.1.0, tokenizers 0.23.3, safetensors, pyyaml. The env line of the test log has the versions it ran with.
Max time:        15 minutes for both tiers (each scorer process is stopped after --timeout 1800 s). This job's path (--team5-run, a train_week2.py run folder with a 2.85 GB checkpoint.pt) at the dry run 1 shape (exp2_muon, T2, 237M parameters), measured on a Tesla T4 in fp32 (no native bf16 there; logs/watcher_gpu_test.log section 6): Tier A 53.6 s (checkpoint.pt load and weights-hash check 4.7 s, scoring 43.5 s), Tier B 81.4 s (load 4.7 s, scoring 71.6 s): about 2.3 minutes for both. Through a Team 7 store (sections 2 and 3): Tier A 95.6 s (export 43.2 s, scoring 45.7 s), Tier B 133.5 s (export 51.5 s, scoring 74.2 s). The eval slot runs bf16, so these are upper bounds. For a store run, Tier A + Tier B / 10 = 108.9 s per checkpoint, below the 600 s save interval. --max-batch-tokens 16384 (the default) was the fastest of 16384, 32768 and 65536, with identical scores. CPU reference: Tier A 659 s on a laptop CPU for a T1-shape model (58M parameters, fp32; logs/watcher_cpu_test.log).
Precision:       bf16 (fp32 on a GPU without native bf16, recorded in each record's format)
Measures:        per task: acc and acc_norm, stderr, items scored; the pooled freeze-set accuracy (decision 3 of results/config_freeze_proposal.md); the scorer's wall time
Expected result: near chance on the freeze set (25 for the four-option tasks, about 10 for MMLU-Pro) or a little above: dry run 1 is a 1,221-step T2 run (val/bpb 1.5159). A score far above chance would be a bug to report.
Outputs:         out/watcher/dryrun1-1234.<label>.every1/: one eval-mini v1 file per tier (6 KB for Tier A, 13 KB for Tier B), one log each, state.json; the rows in ClickHouse eval_mini under run_id dryrun1-1234:checkpoint.pt:<label>:<rev[:12]>.
Test log:        teams/09-evaluation/harness_lab/logs/watcher_cpu_test.log (CPU, a T1-shape Team 5 model in Team 7's layout, C3, --offline) and logs/watcher_gpu_test.log (Tesla T4, fp32, p1536, --offline: the T2 exp2_muon shape in Team 7's layout, sections 1 to 5, and in a train_week2.py run folder through --team5-run, Tier A and Tier B, section 6; canary scans exit 0). The --team5-run path and the HTTP load into ClickHouse (checked against schema_v1.sql's eval_mini columns) are also tested in tests/test_run_lab_ckpt_scorer.py and tests/test_eval_watcher.py.
```

## Later runs that save through Team 7's Checkpointer

Not part of this job's run. For a run whose trainer commits through Team 7's Checkpointer, Tier A follows every commit:

    python teams/09-evaluation/harness_lab/eval_watcher.py --run-dir <run folder> --label tier-a --until-final --scorer lm_eval_lab:team5 --clickhouse-url <ClickHouse URL> -- --device cuda --tier A --model-config <arm YAML or manifest> --tokenizer ./inputs/tokenizer.json --tokenizer-sha256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b --byte-table teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz --hf-home ./inputs/hf --offline

Run both on the same eval slot. They take turns on the GPU (the slot lock), and each has its own label, results,
state and ClickHouse run_ids.

| Watcher | `--label` | `--every` | `--tier` | Tasks | Items | Requests per checkpoint |
|---|---|---|---|---|---|---|
| Tier A (the command just above) | `tier-a` | 1 | `A` | `mmlu` 0-shot, first 10 per subject; `milu_Hindi`, `milu_Telugu`, `milu_Tamil`, `milu_Bengali` 5-shot, spec items | 970 | 3,880 |
| Tier B | `tier-b` | 10 | `B` | `arc_challenge` 0-shot first 500; `hellaswag` 0-shot first 400; `leaderboard_mmlu_pro` 5-shot, 300 spec items; `belebele_hin_Deva`, `belebele_tel_Telu`, `belebele_tam_Taml` 5-shot, 100 spec items each | 1,500 | 7,617 (measured; MMLU-Pro and ARC items do not all have the same option count) |

Tier B is the same command with `--label tier-b --every 10` and `--tier B` (and `--until-final`). "Run Tier B on every 10th checkpoint"
is TSAI's comment on #357, and every Tier B number carries the label "diagnostic, not cleared for contamination".

Retention planned for dry run 1 was `--keep 9 --protect-every 15` at a 600 s interval (Team 7, `docs/checkpoint_interval.md`).
Every 10th commit is not a protected one, so a Tier B checkpoint must be scored within about 90 minutes of its commit;
one that retention deletes first is recorded as `gone`. Team 9 names the protected step count in `eval_schedule.md`
(task 4).

## Datasets

The ones lm-eval 0.4.13 loads for the 11 tasks (from #387, Hugging Face cache, `datasets` 5.1.0). One online run with
`HF_HOME=./inputs/hf` fills the cache; MILU needs an account that accepted its terms.

| Dataset | Revision | Tasks |
|---|---|---|
| `cais/mmlu` | `c30699e8356da336a370243923dbaf21066bb9fe` | `mmlu` (57 subjects) |
| `ai4bharat/MILU` | `846d7016558b2004386f30e59a2158731262492f` | `milu_Hindi`, `milu_Telugu`, `milu_Tamil`, `milu_Bengali` |
| `allenai/ai2_arc` | `210d026faf9955653af8916fad021475a3f00453` | `arc_challenge` |
| `Rowan/hellaswag` | `218ec52e09a7e7462a5400043bb9a69a41d06b76` | `hellaswag` (internal only, `benchmarks_v1.md` Decision 8) |
| `TIGER-Lab/MMLU-Pro` | `b189ec765aa7ed75c8acfea42df31fdae71f97be` | `leaderboard_mmlu_pro` |
| `facebook/belebele` | `7899cdfa4e1e0d733fd77c848e2c273cb1d32be2` | `belebele_hin_Deva`, `belebele_tel_Telu`, `belebele_tam_Taml` |

## Network and firewall (eval_firewall.md, section 3)

- With `--offline` the scorer needs no network. The watcher's only network use is the ClickHouse URL TSAI gives. With
  `--no-load` instead it needs none, and a later run without `--no-load` loads the stored results.
- Rule 4: the datasets in `./inputs/hf` are eval files, placed in this job's folder only and deleted when it ends.
- Rule 5: scores only. No `log_samples`, no item text in `out/` or in the logs. Before the results come back:
  `python teams/09-evaluation/decontam/canary_scan.py out <job logs> --lab-only` must exit 0.
- The watcher only reads the run folder. It never writes to the store or deletes from it.

## Not known yet

- The ClickHouse URL of the eval slot and whether Team 8's eval tables are up (work order: D3, Tue 17).
- The time per checkpoint on a GPU with native bf16 at the dry run 1 shape (logs/watcher_gpu_test.log, to fill).
- Whether later runs (dry run 2, the main run) save through Team 7's Checkpointer every 600 s; dry run 1 saved one
  checkpoint at the end (#475).
