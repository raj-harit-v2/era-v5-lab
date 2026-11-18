# harness_lab: score a lab checkpoint, write eval-mini v1

`run_lab_ckpt.py` takes the folder of a run in the checkpoint store and writes one eval-mini v1 file
(`../results/eval_mini_v1_schema.md`, section 6).

Steps it does: read `latest.json` (or the `commits.jsonl` line of `--step`) -> read `MANIFEST.json` ->
`export_safetensors()` (Team 7; checks sha256 of every file and the probe-loss bits) -> score -> build the v1 records ->
`check(doc, 0)` from `results/convert_v0_to_v1.py` -> write the file (byte-identical on a rerun).

```bash
python teams/07-infrastructure/jobs/restore_test/restore_test.py          # makes the CPU test store
python teams/09-evaluation/harness_lab/run_lab_ckpt.py \
    --run-dir teams/07-infrastructure/jobs/restore_test/out/ckpt_store/restore-b
```

CPU log: `logs/cpu_test.log`. Needs torch >= 2.14.1, safetensors, and the pinned `kronecker-embeddings`
(`teams/04-ke2/src/requirements.txt`).

## Scorers

`--scorer smoke` scores Team 5's tiny MoE (a pipeline test, not an eval-mini task). `--scorer <module>:<function>`
loads a real scorer; the arguments `run_lab_ckpt.py` does not know go to it. The contract is in the docstring of
`run_lab_ckpt.py`: the scorer builds the model, gives the probe for the export check, and returns the record fields.

`lm_eval_lab:team5` (`lm_eval_lab.py`) is eval-mini on a Team 5 `LanguageModel` (`week2/model.py`), the model class
dry run 1 trains. The task list, items and seeds are `eval_lab_v1.yaml`:

| Tier | `--tier` | Tasks | Items | Requests | Use |
|---|---|---|---|---|---|
| A | `A` | `mmlu` 0-shot, first 10 per subject; `milu_Hindi`, `milu_Telugu`, `milu_Tamil`, `milu_Bengali` 5-shot, eval-mini spec items | 970 | 3,880 | the freeze set, every checkpoint (`results/config_freeze_proposal.md` section 6.2) |
| B | `B` | `arc_challenge` 0-shot first 500; `hellaswag` 0-shot first 400; `leaderboard_mmlu_pro` 5-shot, 300 spec items; `belebele_hin_Deva`, `belebele_tel_Telu`, `belebele_tam_Taml` 5-shot, 100 spec items each | 1,500 | 7,617 | diagnostics, every 10th checkpoint (TSAI on #357); each number labelled "diagnostic, not cleared for contamination" |

```bash
python teams/09-evaluation/harness_lab/run_lab_ckpt.py --run-dir <remote_root>/<run_id> --step <N> --device cuda \
    --scorer lm_eval_lab:team5 --model-config <arm.yaml | run manifest.json | model.json> \
    --tokenizer <tokenizer.json> --tokenizer-sha256 <sha256> --byte-table <raw table .npz> \
    --tier A --hf-home <HF cache> --offline
```

- **Model:** built by Team 5's own code from `--model-config`; Team 7's export checks every file's sha256 and the
  strict key list against it, so a wrong config stops at the export. The probe is `probe_loss` (next-token loss on a
  fixed seeded batch); the export compares it only with bits saved on the same device class (a GPU-trained checkpoint
  exported on CPU is checked by file sha256 and keys).
- **Tokenizer:** `--tokenizer-sha256` must match the file (Team 5's `Artifacts` checks it) and the tokenizer the
  checkpoint was trained with: `env.tokenizer_sha` in a Team 7 `MANIFEST.json`, `artifacts.tokenizer_sha256` in a Team 5
  `manifest.json`. New work uses the frozen **p1536** (`e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`,
  TSAI Gate 3 notice of 15 Nov; dry run 1 was trained with it) and Team 4's p1536 raw table on main,
  `teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz` (file sha256 `21072027…168a`). C3 work stays valid as a
  record. Other tables: `teams/04-ke2/src/build_tables.py`. C3's normalizer changes some Indic text, so a few prompts do not rebuild their
  exact bytes; the scorer counts them ("encode fallbacks") and uses the tokenizer's ids, as #387 did.
- **Speed** (course rule of 13 Nov): every distinct text is tokenized once in one batched call;
  requests with the same input tokens (the answer letters of one item) share one forward row; rows are length-sorted
  and batched under `--max-batch-tokens`; the output head runs only on the continuation positions, in chunks; one
  device-to-host copy per batch. lm-eval indexes only the task folders in `eval_lab_v1.yaml` (`lm_eval_task_dirs`),
  not its 14,000 default task files, and its per-call environment report (pip list, OS queries, git: 5 to 16 s a
  call) is skipped. The numbers equal #387's code (`tests/test_lm_eval_lab.py` keeps #387's loop as the reference);
  the timings are in `logs/watcher_cpu_test.log` and `logs/watcher_gpu_test.log`. At the dry run 1 shape (T2, 237M
  parameters) on a Tesla T4 in fp32: through a Team 7 store, Tier A 95.6 s and Tier B 133.5 s per checkpoint (export
  plus scoring); through `--team5-run` (dry run 1's path), Tier A 53.6 s and Tier B 81.4 s (the checkpoint.pt load
  is 4.7 s). The default `--max-batch-tokens 16384` was the fastest of 16384, 32768 and 65536, with identical scores.
  Measured on an RTX 3070 (bf16, one 8 x 2048 batch): Team 5's MoE layers (`week2/model.py`, a Python loop over the 16
  experts with one `nonzero()` sync each, 128 per forward) take 48% of the forward time. That is Team 5's model, as dry
  run 1 trained it, and `week2/config.py` allows only that dispatch; the scorer uses it unchanged. The scorer's own
  per-batch uploads (4 small arrays, about 0.24 ms) are 0.04% of that forward.
- **lm-eval version:** pinned to 0.4.13 in `eval_lab_v1.yaml` (`lm_eval_version`), the version of the lm-eval records
  in `../results/eval_mini_v1.json`; the scorer stops on another one, because prompts and default seeds can change.
- **Firewall** (`../firewall/eval_firewall.md` section 3): with `--offline` no network; no `log_samples`; no item text
  in the output or the log. The spec file's sha256 is taken with LF line endings, so a Windows checkout with
  `core.autocrlf=true` gives the same `item_set` as Linux.

## eval_watcher.py: score every new checkpoint, load it into ClickHouse

`eval_watcher.py` follows one run in the checkpoint store. For each new line in the run's `commits.jsonl` it runs
`run_lab_ckpt.py --step <N>` in its own process and loads the eval-mini v1 file into Team 8's `eval_mini` table
with `teams/08-monitoring/clickhouse/load_jsonl.py`. The watcher itself needs only the Python standard library.

```bash
# CPU test on Team 7's tiny store; --no-load parses the rows exactly as the load would, without ClickHouse
python teams/07-infrastructure/jobs/restore_test/restore_test.py
python teams/09-evaluation/harness_lab/eval_watcher.py \
    --run-dir teams/07-infrastructure/jobs/restore_test/out/ckpt_store/restore-b --once --no-load

# dry run 1, on the eval slot: Tier A on every commit, Tier B on every 10th; both share one GPU slot lock and end
# by themselves after the run's final checkpoint (--until-final)
python teams/09-evaluation/harness_lab/eval_watcher.py --run-dir <remote_root>/<run_id> --label tier-a --until-final \
    --scorer lm_eval_lab:team5 --clickhouse-url http://<host>:8123 -- --device cuda --tier A <scorer inputs>
python teams/09-evaluation/harness_lab/eval_watcher.py --run-dir <remote_root>/<run_id> --label tier-b --every 10 \
    --until-final --scorer lm_eval_lab:team5 --clickhouse-url http://<host>:8123 -- --device cuda --tier B <scorer inputs>

# a Team 5 LanguageModel store in Team 7's layout, for a test before dry run 1 checkpoints exist
python teams/09-evaluation/harness_lab/tests/make_lab_store.py --arm teams/05-architecture/configs/arms/t2.yaml \
    --tokenizer <tokenizer.json> --tokenizer-sha256 <sha256> --byte-table <raw table .npz> --out <dir>

# tests (no GPU, no ClickHouse server, no network)
python -m pytest teams/09-evaluation/harness_lab/tests -q
```

| Point | How |
|---|---|
| Which checkpoints | Lines of `commits.jsonl` (written after MANIFEST.json and latest.json), never a directory listing. A line without its newline is an append in flight and waits for the next poll. A complete line that is not a commit stops the watcher (exit 78). |
| Tier B | `--every N` scores commit N, 2N, ...: the count Team 7's retention uses for `--protect-every`. Dry run 1 retention is `--keep 9 --protect-every 15` at a 600 s interval (`teams/07-infrastructure/docs/checkpoint_interval.md`), so an unprotected checkpoint stays about 90 minutes; one deleted before it is scored is recorded as `gone`. |
| Labels | `--label` names the out folder (`out/watcher/<run>.<label>.every<N>/`), the state and the ClickHouse run_ids. The default is the scorer plus a hash of the arguments after `--`, so Tier A and Tier B never share a state. |
| ClickHouse `run_id` | `<run>:<commit path>:<label>:<model_revision[:12]>`. `load_jsonl.py` deletes all rows of a run_id before it inserts, so the run_id is unique per checkpoint, tier and run (two runs with one name differ in `model_revision`, the sha256 of MANIFEST.json). |
| One GPU slot | Every watcher takes `--slot-lock` (default `out/watcher/gpu_slot.lock`) around a scorer run, so two tiers never load two models at once. |
| Isolation | One process per checkpoint. On Linux it gets its own process group, and `--timeout` (default 1,800 s, for a hung scorer) or a stop ends the whole group. Logs go to `<out folder>/logs/`. |
| Time per checkpoint | Each scored checkpoint prints and keeps the scorer's wall time, the wait for the slot and the lag from its commit; the last lines give the mean and the max. A checkpoint must score within the save interval (600 s in dry run 1) for the watcher to keep up. |
| End of the run | `--until-final`: the watcher exits by itself once the run's final checkpoint (Team 7's trainer commits it with reason `final`) is committed and every owned commit is done. Without it, or if the run never commits a final checkpoint, SIGTERM saves the state and exits 75. |
| Restarts | State in `state.json` (written atomically), one watcher per state file (OS lock). A scoring failure is retried once more (`--max-attempts 2`, JOB_REQUEST.md rule 5), and the checkpoint's log keeps both attempts; a ClickHouse failure keeps the scored file and retries only the load. A commit superseded by a later commit of the same step, or deleted by retention, is recorded and skipped. If `commits.jsonl` cannot be read (a store or mount that dropped out), nothing is marked and the exit is 75. |
| Events | `eval.scored`, `eval.loaded`, `eval.failed`, `eval.load_failed`, `eval.skipped`, `eval.store_unavailable` through Team 7's `common/events.py` when `V5_EVENTS_DIR` is set. |
| Exit codes | 0 done, 1 a checkpoint failed `--max-attempts` times, 75 stopped, store unreadable or work left for a rerun, 78 fatal. |

## Dry run 1: a Team 5 run folder (`--team5-run`)

TSAI on #475 (16 Nov): dry run 1 is finished, trained with p1536, and saved **one** checkpoint at the end
(`train_week2.py`: `checkpoint.pt`, `manifest.json`, `summary.json`; about 2.2 GB, kept by TSAI). There is no Team 7
store for it, so `--team5-run <folder>` scores that folder in place of `--run-dir`:

- It is scored only when `summary.json` says `COMPLETED` (Team 5: anything else is not a result).
- `checkpoint.pt` is opened with `mmap=True` and only `state["model"]` is loaded (strict). The optimizer state in the
  same file is never read into memory.
- The weights hash (Team 5's own `train_week2.model_hash`) must equal `summary.json` `final_model_sha256`, which becomes
  `model_revision`: the check that the weights scored are the ones the run reported, as the probe-loss check is for a
  Team 7 export. `checkpoint`: `run` = the folder name (or `--run-name`), `branch` "main", `step` = the completed steps,
  `epoch` and `tokens_seen` null, `path` = `<folder>/checkpoint.pt`.
- The watcher treats the folder as one commit with reason "final": it waits for `summary.json`, scores once per label
  (same slot lock, state, retries and exit codes), loads under run_id `<run>:checkpoint.pt:<label>:<rev[:12]>`, and
  exits (`--team5-run` implies `--until-final`; `--every` must be 1).
- Speed: the model's MoE uses Team 5's `dispatch: loop` (the only dispatch `week2/config.py` allows); the scorer uses
  Team 5's model unchanged. Measured: Tier A 53.6 s and Tier B 81.4 s per checkpoint on a Tesla T4 in fp32
  (`logs/watcher_gpu_test.log`, section 6).

## What is and is not done

| | State |
|---|---|
| Pointer, manifest, `model_revision`, `checkpoint` block, export, `check(doc, 0)` | Done, tested on the tiny MoE and on a Team 5 `LanguageModel` on CPU |
| `--scorer smoke` (next-token accuracy on Team 5's seeded stream) | Done. It tests the pipeline. It is not an eval-mini task and says nothing about quality. Output byte-identical to before the scorer contract |
| lm-eval tasks on a Team 5 `LanguageModel` in Team 7's layout (`lm_eval_lab:team5`) | Done, CPU end to end in `logs/watcher_cpu_test.log` |
| `eval_watcher.py`: each new commit scored and loaded, restarts, retries, tiers, slot lock | Done; tests without GPU or ClickHouse. The store must be a local or mounted path, as for `run_lab_ckpt.py` |
| Team 5 `checkpoint.pt` + `manifest.json` layout (section 6, last paragraph): dry run 1 | Done: `--team5-run <folder>` in `run_lab_ckpt.py` and `eval_watcher.py` (below). Tested on a stub model; the real run is the job request `../jobs/2026-11-15-eval-watcher-dry-run-1.md` |
| `--run-name` for queue jobs (`<job_run_id>/<arm>`) | Done, not tested on a real queue job |

## Schema point to confirm

Section 6 says `checkpoint.epoch` is the `<E>` in the folder name, and also that it comes from `latest.json`. After a restore,
`latest.json` holds epoch + 1 (the restore claims it) while the folder is still `-e1`. The script takes the folder name.
