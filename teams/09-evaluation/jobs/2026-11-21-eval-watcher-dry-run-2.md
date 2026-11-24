# eval-mini watchers on dry run 2: every commit, step 0 and the planned failure (week 4, task 1)

Week-4 work order, Team 9 task 1: "File the dry run 2 watcher job request, before Tue 24 starts." Gate 4 evidence:
"Dry run 2 watcher ran." What Gate 4 checks (`eval_schedule.md` section 1): "Step-0 scores are near random, and the
watcher survives the planned failure of dry run 2."

Dry run 2 (TSAI, 21 Nov): test scale, the same pattern as dry run 1, with Team 7's Checkpointer in Team 5's trainer
(#608, merged 21 Nov). Team 5's dry run 2 job is #720 (merged 22 Nov): run ID `dryrun2-1234`, store `/shared/ckpt`.
Its arm has the dense output head. The KE2/KAS head (Team 4's handoff #694) joins the same arm only once Team 5's
head PR is on `main` (#720, open item 4). The trainer commits step 0 (`--checkpoint-at-start`) and then every 600 s
(`--checkpoint-interval-s 600`) into Team 7's store. The planned failure is a SIGKILL, then a restore to the last
complete commit (see "The planned failure" below). So this job follows the store, not a Team 5 run folder: two
watchers, as in the "Later runs" section of `jobs/2026-11-15-eval-watcher-dry-run-1.md` (#549), and Tier C after
the run (`eval_schedule.md` section 2).

```text
Team:            09-evaluation
Owner:           Team 9 lead (rahulni). Lab rule 3 (Lab 3 briefing): no person names in the lab repo.
Lead approval:   rahulni (Team 9 lead). The GPU slot is for TSAI to approve in this PR.
Question:        Does the watcher score every dry run 2 commit into ClickHouse without a person in the loop (Tier A every commit, Tier B every 10th), with near-random scores at step 0, and does it keep going across the planned failure, scoring the restored checkpoint, with no commit missed or scored twice?
Script:          teams/09-evaluation/harness_lab/eval_watcher.py (on main, #549). For each owned commit it runs harness_lab/run_lab_ckpt.py --run-dir <run> --step N --scorer lm_eval_lab:team5 in its own process, then teams/08-monitoring/clickhouse/load_jsonl.py.
Command:         python teams/09-evaluation/harness_lab/eval_watcher.py --run-dir /shared/ckpt/dryrun2-1234 --label tier-a --out-dir ./out/watcher/dryrun2-1234.tier-a.every1 --until-final --scorer lm_eval_lab:team5 --clickhouse-url <ClickHouse URL> -- --device cuda --tier A --model-config ./out/dryrun2-1234/manifest.json --tokenizer ./inputs/tokenizer.json --tokenizer-sha256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b --byte-table teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz --hf-home ./inputs/hf --offline
                 Then the same with --label tier-b --every 10 --out-dir ./out/watcher/dryrun2-1234.tier-b.every10 and --tier B. Both out folders are under ./out/ (JOB_REQUEST.md rule 1; without --out-dir the watcher writes below teams/09-evaluation/harness_lab/out/), and the two share the slot lock ./out/watcher/gpu_slot.lock. Start both on the eval slot as soon as /shared/ckpt/dryrun2-1234/ exists (the trainer makes it when it opens the store, before the step-0 commit), and at the latest 90 minutes after the step-0 commit. Leave both running through the planned failure: only the trainer is killed. Each exits 0 by itself once the final commit is scored and loaded.
                 After both have exited: Tier C (section below), Tier B on step 0 and on each restored-from step.
Config:          teams/09-evaluation/harness_lab/eval_lab_v1.yaml; items from teams/09-evaluation/harness_code_indic/eval_mini_v0_spec.json (sha256 94de47d2…)
Inputs:          (1) /shared/ckpt/dryrun2-1234/: dry run 2's Team 7 store folder (commits.jsonl, latest.json, pins.json, the step folders), read only, as a local or mounted path on the eval slot. TSAI confirmed /shared/ckpt on the job host (#720 review), and the eval slot needs the same folder. The watcher reads commits.jsonl from disk, so it cannot follow an s3:// store directly. The run's manifest.json names both: team7_checkpoint.store and team7_checkpoint.run_id. If TSAI runs it under another ID (dry run 1 ran as dryrun1-muon-1234), use the manifest's.
                 (2) ./out/dryrun2-1234/manifest.json: dry run 2's own manifest.json (the scorer reads config.model). train_week2.py writes it in Team 5's --out folder when the run starts, before the step-0 commit; a read-only copy goes at this path on the eval slot, as for #549. The model: T2, 8 layers, width 512, 8 heads, 2 key-value heads, context 2,048, 16 routed + 1 shared experts, top-2, ke1 with P32 (dryrun2.yaml, which inherits exp2_muon.yaml), with the dense output head (#720; #717, still a draft, says the trainer still uses the dense head). If the KAS head joins the arm before the run (its own 2048-wide output projection, not tied to the input embedding, parameters under head.*: TSAI, 21 Nov), test log item 2 comes first. One manifest serves every commit, also those made after a restore (each restart has a new --out and the same model; test log). Without the manifest: --model-config teams/05-architecture/configs/arms/dryrun2.yaml --runtime teams/05-architecture/configs/runtime.yaml --resolution ./inputs/resolution.yaml (the trainer's file: a resolution can set model.rope_theta and model.norm_eps).
                 (3) ./inputs/tokenizer.json, the frozen p1536 (sha256 e6b93a93…25a64b; teams/03-tokenizer/release/README.md has the public download, #700; the same file as #720's ./inputs/tokenizer_p1536.json), and teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz (file sha256 e19a6cae…39b0, content sha256 21072027…168a), the table dry run 2 trains with (#720), the same as dry run 1. The scorer checks the tokenizer file against --tokenizer-sha256. #608 commits record env.tokenizer_sha as "unknown", so the run's manifest.json is the record: its artifacts.tokenizer_sha256 must be e6b93a93…25a64b, and its artifacts.table_file_sha256 must be e19a6cae…39b0 (the file hash; #720 quotes the content hash).
                 (4) ./inputs/hf: the Hugging Face cache of #549 (datasets and revisions below), placed in this job's folder only and deleted after the job (eval_firewall.md section 3, rule 4). Writable (lm-eval's hellaswag map cache, 93 MB).
Hardware:        1 GPU with native bf16 on the eval slot, not a training node (eval_firewall.md section 3, rule 4). Tier A and Tier B share it through one slot lock, so only one model is loaded at a time.
Packages:        as #549: torch >= 2.14.1, lm_eval 0.4.13, datasets 5.1.0, tokenizers 0.23.3, safetensors, pyyaml. run_lab_ckpt.py puts teams/07-infrastructure on sys.path itself (Team 7's export_safetensors).
Max time:        150 minutes: Team 5's 90 (#720) plus 60 for the last commits and Tier C. Each scorer process is stopped after --timeout 1800 s. Time per checkpoint: #549 on this slot (--team5-run, bf16): Tier A 168.8 s, Tier B 112.3 s. The store path adds the export: +38.5 s Tier A, +46.8 s Tier B on a Tesla T4 (logs/watcher_gpu_test.log, sections 2, 3 and 6). Estimate: Tier A about 207 s, Tier B about 159 s, so about 223 s per commit (A + B/10) and 366 s on a 10th commit (A + B), both below the 600 s save interval. The watchers print the measured times; they go into eval_schedule.md (task 5). #549 and the T4 test ran with deterministic algorithms on; since #724 (23 Nov) only the export uses them, so scoring should be no slower than these times.
Precision:       bf16
Measures:        per task: acc and acc_norm, stderr, items scored; the pooled freeze-set accuracy; per checkpoint: the scorer's wall time, the slot wait and the lag from commit to score; each owned commit's final status (loaded, gone, superseded, failed) in state.json.
Expected result: step 0: each Tier A score inside its band or its one-letter range (eval_schedule.md section 5.2; milu_Tamil can reach 34.0). Later commits near chance (test scale). Across the kill: every owned commit loaded once, none missing, none twice; each restored-from step scored; Tier A within 30 minutes of each commit (eval_schedule.md section 3). A step-0 score above both ranges means a bug, reported at once. Dry run 2 makes about 6 to 8 commits (dry run 1 took 2,481 s for 1,221 steps; one commit every 600 s, plus step 0, the final commit and the restores), so the Tier B watcher may own none and exit 0 with nothing scored. Tier C gives Tier B on step 0 and each restored-from step.
Outputs:         out/watcher/dryrun2-1234.tier-a.every1/ and out/watcher/dryrun2-1234.tier-b.every10/: one eval-mini v1 file per scored commit (6 KB Tier A, 13 KB Tier B), one log each, state.json. out/watcher/tier-c/: one file per pinned step (2: #743 expects pins.json = [0, K]). Well under 50 MB. Rows in ClickHouse eval_mini under run_id dryrun2-1234:<commit path>:<label>:<model_revision[:12]>.
Test log:        (1) teams/09-evaluation/harness_lab/logs/watcher_dry_run_2_rehearsal.log (21 Nov, laptop CPU): #608's trainer at 2424e4a2 (T1 shape, AdamW, --smoke) with --checkpoint-store --checkpoint-at-start; both watchers running with these commands (Tier B --every 3, --no-load, --limit 2); the trainer killed right after commit 4 and restored with --resume-committed from step 3; 9 commits, Tier A scored all 9 once, Tier B lines 3, 6 and 9 once, both exited 0 by themselves; a restart scored nothing again; Tier C on steps 0 and 3; canary scan and item-text probe 0. Test only: the export's probe compare was skipped by a wrapper, because a CPU-trained commit saves a cpu probe that our different probe can never match (the slot skips it for a GPU run; the log has the wrapper's source). (2) Only if the KAS head joins the arm before the run: our scorer on Team 5's head PR, which also moves the KE2 input to the 2,048 code (TSAI, 04 KE2 group, 23 Nov). #717 (draft) plans to keep head(hidden), head.* and head.out_features = 131072 for Team 9's scorer. (3) On main: logs/watcher_gpu_test.log (T4, Team 7 layout, T2 exp2_muon shape) and logs/watcher_cpu_test.log; tests/test_eval_watcher.py.
```

## Tier C: Tier B on step 0 and on each restored-from step

`--every 10` scores lines 10, 20, … of commits.jsonl, so it never scores step 0 (line 1). Team 7 pins step 0 and the
restored-from step (work order task 4; the pin job #743, which adds to the kill drill #738), so they are kept and
can be scored after the run, when the slot is free. In #738 both kills restore the same commit: (b) kills run 2's
first save, so run 3 restores the commit that run 2 did, and #743 expects pins.json = [0, K]. For each step N in
`/shared/ckpt/dryrun2-1234/pins.json`:

    python teams/09-evaluation/harness_lab/run_lab_ckpt.py --run-dir /shared/ckpt/dryrun2-1234 --step N --out ./out/watcher/tier-c/step-N.tier-b.json --device cuda --scorer lm_eval_lab:team5 --model-config ./out/dryrun2-1234/manifest.json --tokenizer ./inputs/tokenizer.json --tokenizer-sha256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b --byte-table teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz --tier B --hf-home ./inputs/hf --offline
    python teams/08-monitoring/clickhouse/load_jsonl.py ./out/watcher/tier-c/step-N.tier-b.json --run-id dryrun2-1234:step-N:tier-c --url <ClickHouse URL>

Gate 4 does not depend on Tier C: Tier A scores them all, and only the freeze set decides (eval_schedule.md 5.2).
The test log ran these two commands on its steps 0 and 3, with the parse that `--no-load` does instead of the load.

## Retention

Tier B scores every 10th commit. Team 7 agreed `--protect-every 10` in the 07 Infrastructure group (19 Nov). With 10,
every commit Tier B scores is kept until it is scored. Main's Team 7 docs (`docs/checkpoint_interval.md`,
`docs/runbook.md`) still say `--keep 9 --protect-every 15` (23 Nov); #739 (open) makes it 10, as TSAI told Team 7
(07 Infrastructure group, 22 Nov). With 15, a Tier B commit must be scored within about 90 minutes of its commit
(`--keep 9` at 600 s); one that retention deletes first is recorded as `gone`, not skipped silently. Dry run 2 makes
about 6 to 8 commits, so with `--keep 9` retention deletes none of them either way; the value matters for the main
run. Step 0 and each restored-from step are pinned.

## The planned failure

TSAI kills the trainer with SIGKILL (a) midway between two committed saves and (b) mid-save, using Team 7's
upload_delay_s switch, time permitting (07 Infrastructure group, 21 Nov). Each time the trainer restarts with
`--resume-committed` (same `--run-id` and store, a new `--out`). The watchers are not touched: they keep polling
commits.jsonl, which Team 7 only appends to. In (b) the half-written step folder never gets a commits.jsonl line, so
the watchers never see it. If a restore commits a step again, the newer commit is scored and the older one is marked
`superseded`. The test log covers (a). Team 7's drill job is #738 (open): (a) in run 1, about 5 minutes after a
commit, and (b) during run 2's first save, so both restores start from the same commit.

## Datasets

The same as #549: the ones lm-eval 0.4.13 loads for the 11 tasks (from #387, Hugging Face cache, `datasets` 5.1.0).
One online run with `HF_HOME=./inputs/hf` fills the cache; MILU needs an account that accepted its terms.

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
- The watchers only read the store. They never write to it or delete from it.

## If dry run 2 has no Team 7 store

Not expected: #608 is on main, and `train_week2.py` refuses a run that is not `--smoke` without `--checkpoint-store`.
If the run still saves only one checkpoint.pt at the end, this job falls back to the dry run 1 command
(`--team5-run <run folder>`, once per tier), and the Gate 4 step-0 and restore checks cannot be done.

## Not known yet

- The KAS head check (test log item 2), only if the KAS head joins the arm before the run.
- TSAI: whether the eval slot sees `/shared/ckpt` as a local or mounted folder, the copy of the run's manifest.json
  at `./out/dryrun2-1234/`, and the ClickHouse URL.
- Team 7: `--protect-every 10` in its docs (#739), the kill drill (#738) and the pins (#743), all open.
