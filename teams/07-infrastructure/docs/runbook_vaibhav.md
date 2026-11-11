# Team 07 runbook: restore a training run from a checkpoint

What to do when a training run stops and must continue from its last checkpoint, and how long the restore takes.
First version (week 2): the restore steps and the restore time. Later versions add the supervisor restart
(`ckpt/supervisor.py`) and the restart job result (`results/restart_node.txt`).

The design behind each step: [ckpt/README.md](../ckpt/README.md) and
[ADR 0001](../adr/0001-checkpoint-format-and-commit.md). The full on-call guide:
[USER_GUIDE.md section 5](../USER_GUIDE.md#5-on-call-what-to-do-when).

Paths below are relative to `teams/07-infrastructure/`. On a cluster node the same files are under `/opt/v5/`.
`<run>` is the run folder in the shared store: `$V5_REMOTE_ROOT/$RUN_ID` (the main run's `RUN_ID` is `v5main`).

---

## 1. When a restore happens

| How the job stopped | Exit code | What happens | You do |
|---|---|---|---|
| Crash, kill, OOM, NCCL error, node lost | 75 (the wrapper turns a crash into 75) | Slurm requeues the job; it restores from the last committed checkpoint by itself | nothing; check it came back (section 3) |
| Preemption, time limit, health drain, `scancel --signal=USR1` | 75 | the trainer saves first, then exits; the restore loses no steps | nothing; check it came back (section 3) |
| 3 crashes in 30 min | 78 (held) | the job waits for a person | read the cause, fix, release (section 4) |
| Restore refused (environment, keys, data list, world size) | 78 (held) | the job waits for a person | section 4 |
| NaN or loss spike | 78 (held) | no save; the job waits for a person | roll back to an older step (section 5) |

A restore always starts from the step in `latest.json`. A save that died halfway has no `MANIFEST.json` and is
never picked, so a restore never loads a half-written checkpoint.

## 2. What a restore does (automatic)

`Checkpointer.restore` in `ckpt/ckpt.py` runs these steps at the start of every job attempt:

1. **Claim.** Write `latest.json` with `epoch + 1`, only if nobody changed it since it was read. An older copy of
   the run can no longer commit (fencing).
2. **Pick.** Take `latest.json` first, then `commits.jsonl` from newest to oldest.
3. **Check files.** Every file in `MANIFEST.json` against its sha256. A bad file: try the previous commit.
4. **Check environment.** Image, torch, CUDA, NCCL, config, tokenizer, embedding policy, thread count. A mismatch:
   stop with 78 (`EnvMismatchError`).
5. **Copy to the node.** Copy to the node-local disk, each copy checked again.
6. **Strict keys.** Every tensor name, shape and dtype must match the model. A mismatch: stop with 78
   (`StrictLoadError`).
7. **Load.** Weights, optimizer, data position, random generators.
8. **Prove.** State digest, probe-loss bits, next-batch hash, frozen-tensor fingerprints. A failed proof: try the
   previous commit.
9. **Report.** Write the event `restore.done` with the step and the time of each part (section 6).

If nothing was ever committed, the run starts at step 0. If every candidate fails, the job stops with 78
(`CheckpointError`).

## 3. Restore steps (operator)

Use these steps after any stop, to check the automatic restore, or before you release a held job.

**Step 1. Find the job and why it stopped.**

```bash
python queue/job_queue.py status
scontrol show job <id> | grep -E 'JobState|Reason|Comment'
```

`JobState=PENDING` with `Reason=BeginTime` or a requeue: the job restarts by itself, go to step 5.
`JobState=SPECIAL_EXIT` (held, exit 78): the `Comment` names the cause, go to section 4 first.

**Step 2. Look at the committed checkpoints.**

```bash
python ckpt/ckpt.py list --run <run> | tail -3
```

Each line is one commit. The last line is the step the restore will use. Example from the restore test:

```
{"step": 100, "branch": "main", "path": "main/step_00000100-e1", "time": 1793675187.3785548, "reason": "restore_test", "epoch": 1}
```

**Step 3. Check the checkpoint files.**

```bash
python ckpt/ckpt.py verify --run <run>              # the latest commit
python ckpt/ckpt.py verify --run <run> --step <N>   # one step
```

`"bad": []` means every file matches its sha256. Example:

```
{"step": 100, "path": "main/step_00000100-e1", "files": 3, "bad": []}
```

A non-empty `bad` list: the restore will skip this commit and use the one before it. Pin a good older step so
retention never deletes it: `python ckpt/ckpt.py pin --run <run> --step <N>`.

**Step 4. Start the job again.**

| Case | Command |
|---|---|
| Held job, cause fixed | `scontrol release <id>` |
| Job cancelled or gone | `sbatch slurm/mainrun.sbatch` (it restores from `latest.json`) |
| Approved environment change | `sbatch --export=ALL,TRAIN_EXTRA=--allow-env-change slurm/mainrun.sbatch` (logged) |
| Older step needed | section 5 |

**Step 5. Check that the restore worked.** In the run's events (`$V5_EVENTS_DIR/*.jsonl`), look for
`restore.done` for this `run_id`:

```bash
grep -h '"restore.done"' $V5_EVENTS_DIR/*.jsonl | grep "\"run_id\": \"$RUN_ID\"" | tail -1
```

Check that:

- `step` is the step from step 2;
- `resharded` is `false`, unless the number of GPUs changed on purpose;
- `env_override` is `[]`, unless you allowed an environment change;
- `restore_s` is below 600 s (alert CK-13, section 6);
- the loss of the first steps after the restore continues the curve from before the stop.

A `restore.failed` event means one candidate failed and the next one was tried. `restore.fatal` (written by the
trainer when `restore()` raises) means the job stopped with 78: go to section 4.

## 4. A held job (exit 78) after a restore

The job comment names the cause. Do not release the job before the cause is fixed: it would fail the same way.

| Cause | Do |
|---|---|
| `crash_loop` | read the job log, fix the crash, `scontrol release <id>` |
| `EnvMismatchError` | software or config changed. If the change is intended and approved, resubmit with `TRAIN_EXTRA=--allow-env-change`; otherwise go back to the old image |
| `StrictLoadError` | the model code renamed or reshaped tensors. Fix the code or the key mapping. Never resume by ignoring keys |
| `DataManifestError` | point the loader back at the run's shard list, or start a new branch on purpose |
| `ReshardError` | resubmit with the saved number of GPUs, or convert the checkpoint (DeepSpeed: `ds_to_universal.py`) |
| `CheckpointError` | no usable checkpoint: `ckpt.py verify --run <run>`, check the store (alerts CK-04, CK-05) |
| `FencedError` | nothing to do for the run, a newer copy owns it. Find why the old copy was still alive |
| `nonfinite`, `loss_spike` | roll back (section 5) |

`python metrics/explain.py <cause>` prints the full answer for any cause or alert id.

## 5. Restore an older step (rollback)

Use this after a NaN or a loss spike, or when the newest checkpoints are bad.

```bash
python ckpt/ckpt.py list --run <run>      # pick the last good step K
python ckpt/ckpt.py verify --run <run> --step K
scancel <held job id>
sbatch --export=ALL,TRAIN_EXTRA="--from-step K --skip 5 --branch b1" slurm/mainrun.sbatch
```

The run continues on branch `b1` from step K and skips the 5 batches after it. The old branch stays readable.

## 6. Restore time

The restore time is `restore_s` in the `restore.done` event: from the start of `Checkpointer.restore` to the end
of the four proofs. The event also splits it into `verify_s` (file checksums), `download_s` (copy to the node),
`load_s` (tensors and state) and `checks_s` (the four proofs).

### 6.1 Measured (restore test, Team 05 tiny MoE, 3 Nov 2026)

`jobs/restore_test/restore_test.py`, default settings (save at step 100, run B stops at 150, restores from 100,
continues to 200). Checkpoint size 3 MB, plain folder store. All runs PASS: loss bit-equal and data IDs equal at
steps 101 to 200.

| Run | verify_s | download_s | load_s | checks_s | restore_s | whole script |
|---|---|---|---|---|---|---|
| CPU, 1 process (own machine) | 0.0009 | 0.0026 | 0.0263 | 0.0115 | **0.057** | 8.2 s |
| CPU, 2 processes, gloo (own machine) | 0.0013 | 0.0130 | 0.0364 | 0.0133 | **0.067** | 9.3 s |
| 1 GPU, CUDA 13.0 (own run, hosted notebook) | 0.006 | 0.007 | 0.2486 | 0.354 | **0.71** | 31.5 s |

All runs: torch 2.14.1, Python 3.13.16, numpy 2.2.6. The 1-GPU run's `result.json` has sha256
`aa804d3fe5c7d7f665c5611ade2864609179d1ae32018f7996dba72d045f9967`; its loss at steps 1, 100 and 200 (4.31079626,
0.03366745, 0.01066785) equals the TSAI 1-GPU job in [results/restore_test_gpu.txt](../results/restore_test_gpu.txt).

On the GPU most of the time is `load_s` and `checks_s` (state moved to the GPU and the probe forward pass), not
reading files. With a 3 MB checkpoint the file steps are close to zero; on a full-size run `download_s` and
`verify_s` grow with the checkpoint size and the store throughput.

How to measure it again:

```bash
python jobs/restore_test/restore_test.py --nproc 1 --out /tmp/rt     # add --device cuda for a GPU
grep -h '"restore.done"' /tmp/rt/events/*.jsonl
```

### 6.2 Job start to first training step (simulation)

The Docker Slurm simulation measures the whole restart: job start, restore, first productive step (metric CK-13,
the largest over all drills). GPUs are placeholders there, so this is the time of the mechanism, not of a real
model.

| Store | CK-13 | Source |
|---|---|---|
| S3-compatible emulator | 92.19 s | [sim_results.md](../support/docs/sim_results.md) |
| plain folder | 91.27 s | [sim_results_folder.md](../support/docs/sim_results_folder.md) |

### 6.3 Alert levels

CK-13, restore time from job start to the first productive step ([metrics_catalog.md](../support/docs/metrics_catalog.md)):

| Level | Above |
|---|---|
| low | 600 s |
| medium | 900 s |
| high | 1800 s |

Every restore minute is paid on every node of the run with no training. Above the low level: use the node-local
copy when it is valid, copy from the store in parallel, check the store throughput.

### 6.4 Still open

- Restore time on a real node with a full-size checkpoint: from the restart job request
  (`results/restart_node.txt`, due Sat 14 Nov).
- Restore on 2 GPUs: moved to after Gate 2. Until then the 2-process CPU run above is the 2-device evidence.

## 7. Check the restore code itself

Run the restore test before any change to `ckpt/` is merged, and before a job request that restores:

```bash
python jobs/restore_test/restore_test.py              # 1 CPU process
python jobs/restore_test/restore_test.py --nproc 2    # 2 CPU processes
```

The last line must be `PASS restore_test ...` and the exit code 0. Exit 1 is a difference (the line names the
first step), exit 78 is a crashed run. What a difference means:
[jobs/restore_test/README.md](../jobs/restore_test/README.md#what-a-fail-means).
