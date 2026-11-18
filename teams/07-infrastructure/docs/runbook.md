# G7 runbook: restore and restart a run, and handle node failures, NCCL hangs and bad checkpoints

Team 07, Infrastructure. Status: **v2** (week 3, dry run 1). One runbook, consolidated from the week-2 rotation
runbooks (section 13 lists the sources); sections 10 to 12 cover node failures, NCCL hangs and bad checkpoints. Code: [`ckpt/ckpt.py`](../ckpt/ckpt.py),
[`ckpt/supervisor.py`](../ckpt/supervisor.py). Tests: [`jobs/restore_test/`](../jobs/restore_test/README.md),
[`jobs/restart_test/`](../jobs/restart_test/README.md), [`jobs/restore_time/`](../jobs/restore_time/README.md).
Rules: [queue rules v1](queue_rules_v1.md). Causes and actions:
[`codes_and_actions.md`](../support/docs/codes_and_actions.md). Design: [ADR 0001](../adr/0001-checkpoint-format-and-commit.md),
[`ckpt/README.md`](../ckpt/README.md).

> **In simple words.** A checkpoint is a saved copy of the training. To restore, a new process reads the newest
> good copy, **proves** it got back exactly what was saved, and trains on from there. Most of the time this
> happens by itself (exit 75, or a crash under the supervisor). This file says **when a person must act**,
> **what to type**, **how to tell the restore worked**, and **how long a restore takes** (measured, not guessed).

Commands run from `teams/07-infrastructure/` unless a block says otherwise. `<run>` is the run's checkpoint
folder: `<remote_root>/<run_id>` on a cluster, `./out/<run_id>/ckpt/<arm>` in a TSAI job (queue rules R4).
Where this file and the code disagree, the code wins and this file is fixed.

---

## 1. When to act

| You see | It means | Do |
|---|---|---|
| exit **75**, job back in the queue | it saved and stopped (time limit, stop signal, preemption, health drain) | nothing: the next attempt restores by itself (section 3) |
| a crash (exit -9, OOM, other non-zero) under `ckpt/supervisor.py` or Slurm | the trainer died without saving | nothing, unless it becomes a crash loop (78); check it came back (section 4) |
| exit **78**, or the job is held | stopped on purpose; retrying alone would fail the same way | read the cause (section 2), then section 7 |
| alert **CK-05** (`RestoreCheckError`) | the loaded state was not the saved state; the job fell back to an older commit | do not continue on that checkpoint; section 7 |
| alert **CK-13** | restore is slow (job start to first productive step) | section 8.5 |
| NaN or loss spike | the guards stopped the run with 78; nothing was saved after the bad step | roll back (section 6) |
| you changed `ckpt/`, the image or the store | you need proof that restore still works | rehearse (section 9) |
| a node drained (`sinfo -R` shows `v5:<checks>`) or `NODE_FAIL` | a health check failed, or the node died | fix or replace the node; check the run came back (section 10) |
| exit 1 / 134 with a NCCL timeout, or cause `hang_watchdog`; alert H-14 or H-16 | a collective or a step never finished | find the rank that stopped (section 11) |
| alert CK-04 or CK-05, or `restore.failed` in the events | a checkpoint is damaged or does not restore exactly | pin the last good step, find the bad ones (section 12) |

`python metrics/explain.py <cause>` prints the full answer for any cause, exit code or alert id.

---

## 2. Look before you act

```bash
python queue/job_queue.py status                                   # jobs and drained nodes, plain words (Slurm)
scontrol show job <id> | grep -E 'JobState|Reason|Comment'          # a held job names its cause in Comment
python ckpt/ckpt.py list   --run <run> | tail -3                    # committed checkpoints, newest last
python ckpt/ckpt.py verify --run <run> --step <N>                   # every file of step N against its sha256
python ckpt/ckpt.py pin    --run <run> --step <N>                   # keep step N safe from retention
```

`JobState=PENDING` with `Reason=BeginTime` is a requeue: it restarts by itself (section 4).
`JobState=SPECIAL_EXIT` / `JobHeldUser` is a 78: read `Comment`, then section 7.

A good checkpoint (restore test, step 100):

```text
$ python ckpt/ckpt.py list --run <run> | tail -1
{"step": 100, "branch": "main", "path": "main/step_00000100-e1", "time": 1793675187.37, "reason": "restore_test", "epoch": 1}
$ python ckpt/ckpt.py verify --run <run> --step 100
{"step": 100, "path": "main/step_00000100-e1", "files": 3, "bad": []}        exit 0
```

`"bad": []` and exit 0 is good. A damaged file is listed by name in `bad` and the exit code is 1; the restore will
skip that commit and use the one before it. `verify` without `--step` checks the latest commit only. An explicit
`--step` that does not exist fails; it does not fall back. `list` reads `commits.jsonl`; it never lists folders.

### Which checkpoint is COMPLETE

A checkpoint is **COMPLETE** when its step folder has `MANIFEST.json` **and** `latest.json` or `commits.jsonl`
names that folder ([queue rules v1.1, R4](queue_rules_v1.md)). There is **no separate `COMPLETE` file**: `ckpt.py`
writes `MANIFEST.json` last, then moves `latest.json` (with the fencing check), then appends to `commits.jsonl`.
A `MANIFEST.json` that no pointer names is a save cut before its commit: not a checkpoint, not an error. A pointer
to a folder without `MANIFEST.json` is an error.

```text
<run>/latest.json
<run>/commits.jsonl
<run>/<branch>/step_<N:08d>-e<epoch>/MANIFEST.json
<run>/<branch>/step_<N:08d>-e<epoch>/extra_rank<r>.json, sums_rank<r>.json, <shard files>
```

---

## 3. What a restore does, in order

Every trainer calls `Checkpointer.restore()` at start. Nobody picks a folder by hand.

| # | Step | If it fails |
|---|---|---|
| 1 | **Claim**: write `latest.json` with `epoch + 1`, only if nobody changed it since it was read. An older copy of the run can no longer commit (fencing) | another attempt owns the run: `FencedError`, 78 |
| 2 | **Candidates**: `latest.json` first, then `commits.jsonl` newest to oldest | none committed: fresh start at step 0 |
| 3 | **Checksums**: every file in `MANIFEST.json` against its sha256 | `IntegrityError`: try the previous commit |
| 4 | **Environment**: image, torch / CUDA / NCCL, config, tokenizer, `code_sha256`, `OMP_NUM_THREADS` | `EnvMismatchError`: 78 |
| 5 | **Copy** to node-local disk, each copy checked again | try the previous commit |
| 6 | **Strict keys**: every tensor name, shape and dtype | `StrictLoadError`: 78 |
| 7 | **Load**: weights, optimizer, random generators, data position (resharded if the device count changed) | `DataManifestError` / `ReshardError`: 78 |
| 8 | **Four proofs**: state digest, probe-loss bits, next-batch hash, frozen-tensor fingerprints | `RestoreCheckError`: try the previous commit |

If every candidate fails, restore stops with `CheckpointError` (78): nothing usable is left. The tiny-MoE test
model has no frozen tensors (`frozen={}` in its manifests), so the fourth proof compares nothing there; the
checkpoint test suite separately checks that a changed frozen tensor is refused.

### How to tell it worked

```bash
grep -h '"restore.done"' $V5_EVENTS_DIR/*.jsonl | grep "\"run_id\": \"$RUN_ID\"" | tail -1
```

- `step` is the step `ckpt.py list` showed (or an older one, see the next point);
- `resharded` is `false`, unless the device count changed on purpose;
- `env_override` is `[]`, unless an environment change was approved;
- there is **no `restore.failed`** for the same attempt. `restore.failed` followed by `restore.done` on an older
  step means it fell back: the job is fine, but `verify` the skipped step. `restore.fatal` means it stopped with 78;
- the loss of the first steps after the restore continues the curve from before the stop.

`restore.done` also carries the time of each phase: `verify_s`, `download_s`, `load_s`, `checks_s` and the total
`restore_s` (section 8).

---

## 4. Restart after a stop or a kill

**With Slurm** (the main run, later): nothing to type. `queue/job_queue.py run` (called by `slurm/mainrun.sbatch`)
turns the trainer's exit into 0, 75 or 78; Slurm requeues on 75, and the next attempt restores as in section 3.

**Without Slurm** (one machine, the TSAI runner, the CPU tests): `ckpt/supervisor.py` runs the trainer as a child
and starts the **same command** again after a 75 or a crash. The supervisor knows nothing about the model.

```bash
RUN_ID=<run_id> V5_REMOTE_ROOT=<remote_root> \
  python ckpt/supervisor.py --log ./out/<run_id>/logs/supervisor.jsonl -- <trainer command>
```

| Child exits with | Supervisor does |
|---|---|
| `0` done | stops, exit 0 |
| `75` saved and stopped | restarts, at most `--max-stops` times (default 100); then stops with 78 |
| `78` a person must look | stops, exit 78, no restart |
| anything else (exception, SIGKILL, segfault) | restarts after `--backoff` (default 5 s); stops with 78 after **3 crashes in 30 min** (`CRASHLOOP_N`, `CRASHLOOP_WINDOW_S`) or after `--max-restarts` crashes (default 10) |
| SIGTERM, SIGUSR1 or Ctrl-C to the supervisor | passes SIGTERM and SIGUSR1 on to the trainer (Ctrl-C as SIGTERM, because the trainer saves on SIGTERM), starts no new trainer, exits 75 |

- **Log**: one JSON line per attempt in `--log` (in a job: `./out/<run_id>/logs/supervisor.jsonl`, queue rules R3)
  with `attempt`, `rc`, `meaning`, `action`, `reason`, `seconds`, and `pointer_step` on a restart. `pointer_step`
  is what `latest.json` named when the restart was decided; the step really restored is in `restore.done`.
- **If the supervisor itself is killed**, the child keeps running. That is safe: the next attempt claims
  `latest.json`, and the old child's next commit is refused (`FencedError`).
- **Work lost per kill** = the steps since the last checkpoint: they are run again. Section 8.3 has measured values.

---

## 5. Restart steps for a person (held job, or a job that is gone)

| Case | Command |
|---|---|
| Held job, cause fixed | `scontrol release <id>` |
| Job cancelled or gone (Slurm) | `sbatch slurm/mainrun.sbatch` (it restores from `latest.json`) |
| Job gone (no Slurm) | run the same supervisor command again (section 4) |
| Approved environment change | add `--allow-env-change` to the trainer command (`TRAIN_EXTRA=--allow-env-change` under Slurm); it is logged |
| Older step needed | section 6 |

Then check it worked (section 3, "How to tell it worked").

---

## 6. Roll back to a chosen step (after a NaN or a loss spike)

```bash
python ckpt/ckpt.py list   --run <run>                # pick the last good step K
python ckpt/ckpt.py verify --run <run> --step K
python ckpt/ckpt.py pin    --run <run> --step K
scancel <held job id>
sbatch --export=ALL,TRAIN_EXTRA="--from-step K --skip 5 --branch b1" slurm/mainrun.sbatch
```

The run restores step K, skips the next 5 batches (the bad data) and continues on the **new branch** `b1`; the old
branch stays readable, so the run can be replayed. There is no student Slurm: in a TSAI job the same flags
(`--from-step K --skip N --branch <new>`) go on the trainer command under the supervisor. Restoring on fewer
devices reshards: the branch is marked `<branch>-resharded-w<N>` and the loss is no longer bit-equal going
forward, because the sum order changes.

---

## 7. When a restore fails: cause and action

Full list with alert ids: [`codes_and_actions.md`](../support/docs/codes_and_actions.md). Short form:

| Cause | Exit | Already done | You do | Alert |
|---|---|---|---|---|
| `IntegrityError` | falls back | a file did not match its sha256; the previous commit was tried | pin the last good step; `verify` the bad one; find which hop corrupts data | CK-04 |
| `RestoreCheckError` | falls back | digest, probe loss, next batch or frozen hashes differ | compare the two printed values; **do not continue on that checkpoint** | CK-05 |
| `CheckpointError` | 78 | every candidate failed, or the requested step does not exist | `ckpt.py list` and `verify`; check the store; tell the checkpoint owner | CK-06 |
| `EnvMismatchError` | 78 | restore refused; differences in the job log | fix the stack; `--allow-env-change` only if the lead agrees (logged) | CK-06 |
| `StrictLoadError` | 78 | restore refused; every differing key in the job log | fix the model code or the key mapping; never load around it | CK-06 |
| `DataManifestError` | 78 | refused before any step | point the loader back at the run's shard list, or start a new branch on purpose | CK-06 |
| `ReshardError` | 78 | refused before any step | restart on the saved device count (the log names it) | CK-06 |
| `FencedError` | 78 | this attempt's commit was refused; the newer attempt is untouched | nothing for the run; find why the old attempt was still alive | - |
| `nonfinite`, `loss_spike` | 78 | nothing saved after the bad step | roll back (section 6); tell Team 05 | CK-07, H-24 |
| `crash_loop` | 78 | 3 crashes in 30 min; held so it stops burning device hours | read the last trainer error (`logs/job.log` in a job, else the supervisor's terminal), fix it, then restart | Q-04 |

**Code check:** `code_sha256` (the trainer, model and loader files, plus `ckpt.py`) must match; a docs-only commit
does not change it. `git_sha` is recorded but not compared: from `GIT_SHA`, else the checkout's HEAD, else `none`
with a `checkpoint.provenance_unknown` event (issue #298). A checkpoint saved before this change has no
`code_sha256`, and the code is then not checked.

---

## 8. Restore time

**Restore time** here = `restore_s` in `restore.done`: from reading the manifest to the end of the four proofs,
for the candidate that was used. It does not include the claim (about 1 ms on a local folder), starting Python,
importing torch or building the model. It is **not CK-13**, which runs from job start to the first productive step.
Whole-test wall times (the restore test runs A, B twice and the comparison) are **not** restore times either.

### 8.1 Measured on CPU: the restore test (tiny MoE, step 100, about 1.5 MB, local folder store)

Five independent runs by the week-2 rotation (slots R1 to R5, section 13). Median seconds. All runs **PASS**:
steps 101–200 `loss_ntp` and `loss_mtp` bit-equal, data IDs equal, `"resharded": false`.

| Slot | Machine | Runs | Devices | `verify_s` | `download_s` | `load_s` | `checks_s` | **`restore_s`** | whole test |
|---|---|---|---|---|---|---|---|---|---|
| R2 | laptop, macOS arm64, 10 cores | 9 | 1 process | 0.0006 | 0.0013 | 0.0145 | 0.0064 | **0.031** (0.030–0.032) | 4.0 s |
| R2 | same | 9 | 2 processes | 0.0008 | 0.0066 | 0.0179 | 0.0071 | **0.034** (0.034–0.037) | 5.0 s |
| R3 | laptop, macOS arm64 | 3 | 1 process | 0.0007 | 0.0018 | 0.0151 | 0.0087 | **0.035** (0.034–0.036) | 5.1 s |
| R3 | same | 3 | 2 processes | 0.0009 | 0.0067 | 0.0190 | 0.0092 | **0.038** (0.0376–0.0384) | 6.0 s |
| R1 | member machine | not stated | 1 process | 0.0009 | 0.0026 | 0.0263 | 0.0115 | **0.057** | 8.2 s |
| R1 | same | not stated | 2 processes | 0.0013 | 0.0130 | 0.0364 | 0.0133 | **0.067** | 9.3 s |
| R5 | laptop, macOS arm64, 12 cores | 3 | 1 process | 0.001 | 0.015 | 0.023 | 0.008 | **0.071** (0.068–0.072) | 7.2–10.0 s |
| R5 | same | 3 | 2 processes | 0.002 | 0.036 | 0.028 | 0.009 | **0.084** (0.083–0.086) | 8.0–8.2 s |
| R4 | hosted notebook, Linux x86_64 | 1 | 1 / 2 processes | - | - | - | - | not recorded | 39.2 / 43.9 s |

Reading it: on CPU with the tiny model a restore takes **0.03 to 0.08 s**, under 2% of the test. The spread is the
machine, not the code; matching numbers across machines is not a goal, the order of size is. With 2 processes the
copy to local disk roughly doubles; the other phases barely change. Torch 2.14.1 everywhere; one thread per process
(the scripts set it).

### 8.2 Measured on 1 GPU

| Source | Devices | `verify_s` | `download_s` | `load_s` | `checks_s` | **`restore_s`** | whole test | Status |
|---|---|---|---|---|---|---|---|---|
| R1, hosted notebook, CUDA 13.0 | 1 GPU | 0.006 | 0.007 | 0.249 | 0.354 | **0.71** | 31.5 s | member run; losses at steps 1, 100, 200 equal the TSAI job; `result.json` sha256 `aa804d3f…f9967` |
| TSAI job, PR #196 ([`results/restore_test_gpu.txt`](../results/restore_test_gpu.txt)) | 1 GPU | - | - | - | - | not recorded | 45 s | PASS, committed |
| TSAI job, `restore_time.py --device cuda` | 1 GPU | | | | | _pending_ | | job request to be filed |
| 2 GPUs | | | | | | _after Gate 2_ | | needs a 2-GPU node; the 2-process CPU rows are the 2-device evidence |

On the GPU most of the time is `load_s` and `checks_s` (state moved to the device and the probe forward pass), not
reading files. For a 1.5 MB checkpoint that is fixed overhead; it does not say how a full-size restore scales.

### 8.3 Measured: restore inside the restart test (SIGKILL, CPU, 1 process)

Run B is killed with SIGKILL past the requested step; the supervisor restarts it once and the trainer restores the
last COMPLETE checkpoint (every 25 steps). All **PASS**: steps 1–200 bit-equal to the run that never stopped.

| Slot | Kill requested / actual | Restored from | Steps done twice | **`restore_s`** | Extra |
|---|---|---|---|---|---|
| R3 | 140 / 141 | 125 | 16 | **0.035** | kill points 31→33/25, 99→99/75, 164→166/150 also PASS |
| R5 | 140 / past 140 | 125 | - | **0.081** (0.078–0.121, 3 runs) | |
| R2 | 140 / 140–141 | 125 | 15–16 | not recorded | 3 runs; wall time A 1.3–1.5 s, B 2.0 s |
| R4 | 140 / 140 | 125 | 15 | not recorded | job form (`--run-id`), `queue_rules.py check-out` PASS |
| committed, [`results/restart_cpu.txt`](../results/restart_cpu.txt) | 140 / 140 | 125 | 15 | - | kill points 32, 100, 165 also PASS |
| TSAI job on #258, 1 lab GPU, [`results/restart_node.txt`](../results/restart_node.txt) | 140 / 140 | 125 | 15 | not recorded | job form (`--run-id`); `queue_rules.py check-out` not run (#245 merged later) |

### 8.4 How restore time grows with checkpoint size (synthetic, CPU)

**These sizes are synthetic**: a made-up model (8 square linear layers plus AdamW state) built only to give
restore a size axis. They are **not** real model sizes. Command: `python jobs/restore_time/restore_time.py --parts sweep`
(slot R2). Checkpoints go to a temporary folder and are deleted; only a JSON file is written. 9 repetitions,
1 process, local folder, median seconds. Total = claim + restore.

| Checkpoint | checksums | copy | load | four proofs | **total** |
|---|---|---|---|---|---|
| 25 MB | 0.009 | 0.012 | 0.008 | 0.040 | **0.070** |
| 101 MB | 0.036 | 0.050 | 0.015 | 0.153 | **0.256** |
| 403 MB | 0.144 | 0.196 | 0.045 | 0.616 | **1.010** |
| 1,611 MB | 0.594 | 1.082 | 0.321 | 2.508 | **4.514** |

About **2.5 to 2.8 s per GB** on one CPU thread, linear over this range; the four proofs are 56–61% of it. On GPUs
the proofs run faster (not measured yet: the pending row in 8.2). Local disk with a warm cache: it says nothing
about the real store's read speed. Do not extrapolate past 1.6 GB.

### 8.5 The main run, and the alarm

```text
restore_s  ~  checkpoint size per node / store read speed  +  sha256 of every file  +  load into the devices
```

| Input | Where to get it | Status |
|---|---|---|
| checkpoint size per rank (weights + AdamW state) | `ckpt.py list`, or `du` on a step folder; [parallel layout v0](parallel_layout_v0.md) | _pending_: config v1, Sat 14 Nov |
| store read speed per node | `download_s` in `restore.done` on the real store | _not measured_ |
| speed of the four proofs on a GPU | `checks_s`; `restore_time.py --parts sweep --device cuda` | _pending_ (8.2) |

Alarm **CK-13** ([`metrics/catalog.yaml`](../metrics/catalog.yaml)), job start to first productive step:
**LOW 600 s, MEDIUM 900 s, HIGH 1800 s**; HIGH pages someone. Every restore minute is paid on every node of the run
with no training. If it fires: use the node-local copy when it is valid, read from the store in parallel, check the
store read speed. `download_s` against `restore_s` shows whether the store is the slow part.

Whole recovery measured in the Docker copy of the Slurm cluster (placeholder GPUs, so this is the mechanism, not
a real model): a killed trainer back and training in about **50 s**, a preemption in **58 s** (median of 3,
[`queue/README.md`](../queue/README.md) §8); the worst CK-13 over all drills **92.19 s** on the S3-compatible
emulator and **91.27 s** on a plain folder ([sim_results.md](../support/docs/sim_results.md),
[sim_results_folder.md](../support/docs/sim_results_folder.md)). Most of it is the requeue credential wait, not
the restore.

---

## 9. Rehearse a restore and a restart (anyone, CPU, about 10 s each)

Once, from the repo root, in a fresh virtual environment (no GPU, no keys, no network after the install):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r teams/04-ke2/src/requirements.txt pyyaml        # torch 2.14.1 or newer
```

Then from `teams/07-infrastructure/`:

```bash
export OMP_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=""
python jobs/restore_test/restore_test.py                       # 1 CPU process
python jobs/restore_test/restore_test.py --nproc 2             # 2 CPU processes (gloo)
python jobs/restart_test/restart_test.py --also-kill-at 31,99,164   # SIGKILL + supervisor, 4 kill points
python jobs/restore_time/restore_time.py --parts tiny          # restore_s, 9 runs per process count
```

The last lines must start with `PASS restore_test` and `PASS restart_test`. Exit `0` PASS, `1` a difference (the
line names the first step and field: a difference at step 101 means the data position, weights or random state
did not come back; at 102 or later with 101 equal, usually the optimizer state), `78` a run crashed.

As a TSAI job (queue rules v1), with the output checked:

```bash
python jobs/restart_test/restart_test.py --run-id g7-restart-test-<YYYYMMDD>-<NN> --device cpu
python queue/queue_rules.py check-out ./out --run-id g7-restart-test-<YYYYMMDD>-<NN>
```

Read the restore time from a run: `grep -h '"restore.done"' jobs/restore_test/out/events/*.jsonl`, or
`out/<run_id>/logs/events.jsonl` in job form. Check a checkpoint by hand:
`python ckpt/ckpt.py verify --run jobs/restore_test/out/ckpt_store/restore-b --step 100`.

**Do not commit `out/`.** It holds checkpoints, and the event files and `latest.json` record the machine name.
Copy only the PASS line and the numbers.

---

## 10. Node failures

> **In simple words.** A node can break in two ways. Either our health check sees it first: the node is drained,
> the job saves and moves, and almost nothing is lost. Or the node just dies: the job loses the steps since the
> last checkpoint, and runs them again on another node. In both cases nobody picks a checkpoint by hand.

### 10.1 What you see, and what was already done

| Kind | How it shows | Already done | Steps run again |
|---|---|---|---|
| **Health check failed** (Xid, ECC, GPU missing, NCCL test, NVMe, clock, temperature) | `sinfo -R` shows `v5:<checks>`; job cause `saved_and_stopped`, exit 75 | node drained; SIGUSR1 to its jobs; emergency checkpoint committed; Slurm requeues on a healthy node or the spare | about 0 (Docker drill: 0 steps lost, back in 60–88 s, [health README](../health/README.md)) |
| **Node died** (power, kernel panic, network gone) | Slurm `NODE_FAIL` (no answer for `SlurmdTimeout` 30 s); no `job.ended` from that node | Slurm requeues; the next attempt restores the newest COMPLETE checkpoint (section 3) | the steps since the last commit: at most `INTERVAL_S` of work (600 s in dry run 1) |
| **Node cut off, process still alive** | later, a `FencedError` (78) from the old attempt | the new attempt claimed `latest.json`; the old attempt's commit is refused | none |
| **No healthy node left** | `PENDING`, `Reason=Resources` or `ReqNodeNotAvail`; alert Q-01 after 10 min | the main run waits; no crash loop | none, but time is lost |

"Steps run again" are not lost: the data position and the random state come back with the checkpoint, so the run
repeats them bit-equal. A step is **lost** only if the restore skips a COMPLETE checkpoint (section 10.4).

### 10.2 Fix the node (main run, operator)

```bash
sinfo -R                                    # drained nodes and their reason v5:<checks>
python metrics/explain.py v5:<checks>       # what each check means, and what to do
python queue/job_queue.py status            # where the job went
```

| Drain reason | Do |
|---|---|
| `xid` (fatal code), `ecc_uncorrectable`, `dcgm_diag`, `remapped_rows` (failure) | replace the instance; the Xid code is in the health report |
| `gpu_inventory`, `nvlink`, `remapped_rows` (pending) | reboot or reset the GPUs; replace if still wrong |
| `nccl_collectives`, `nccl_all_reduce`, `nccl_reduce_scatter`, `nccl_all_gather`, `nccl_all_to_all` | `health_check.py --mode full` on the node; read the flight-recorder dump (section 11.3); replace if it fails again |
| `dcgm_health`, `gpu_temperature` | `health_check.py --mode full`; check cooling; replace if it repeats |
| `nvme_free` | clean `/nvme` (old restore folders, data cache) |
| `clock_offset` | fix the time service (chrony) |

A repaired node goes back only after a full check passes:

```bash
python health/health_check.py --mode full --report-only    # on the repaired node; "verdict" must be "pass"
scontrol update nodename=<node> state=resume
```

Never resume a node with `--mode full` at `warn` or `fail` into the main run. One slow node slows every GPU.

### 10.3 Check the run came back

1. `restore.done` for the new attempt (section 3, "How to tell it worked"), on the new node (`host` field).
2. The restored step is the newest commit, or an older one with a `restore.failed` that says why (section 12).
3. The loss of the first steps after the restore continues the curve from before the stop.

### 10.4 Dry run 1: read it from the returned logs

TSAI runs dry run 1, and we only get the logs back (queue rules R3), so we cannot type `sinfo` or `scontrol`.
Read the same facts from `./out/<run_id>/logs/`:

```bash
L=./out/<run_id>/logs
# every attempt: exit code, what it means, what the supervisor did, the step latest.json named
python -c 'import sys,json
for l in open(sys.argv[1]): e=json.loads(l); print(e.get("attempt"), e.get("rc"), e.get("meaning"), e.get("action"), e.get("pointer_step"))' $L/supervisor.jsonl
# every restore: time, result, step, the folder it came from (or the cause)
grep -h '"restore\.\(done\|failed\|fatal\)"' $L/events.jsonl | python -c 'import sys,json
for l in sys.stdin: e=json.loads(l); print(e["time"], e["event"], e.get("step"), e.get("from_path") or e.get("cause"))'
python ckpt/ckpt.py list --run ./out/<run_id>/ckpt/<arm>     # the COMPLETE checkpoints
python queue/queue_rules.py check-out ./out --run-id <run_id>  # paths, COMPLETE rule (R4), size
```

Gate 3 asks for **no lost steps and only COMPLETE-checkpoint restarts**. For every restart:

| Check | Pass when |
|---|---|
| Restarted from a COMPLETE checkpoint | the `from_path` of each `restore.done` is a `path` in `ckpt.py list` |
| No lost steps | the `restore.done` step equals the `pointer_step` of the restart before it, or a `restore.failed` explains each skipped step |
| Work run again | the step where the attempt stopped (`job.log`) minus the restored step; at most one interval |
| Clean end | the last attempt has `rc` 0, and `check-out` prints `PASS` |

Example from the restart test (CPU, SIGKILL after step 140, `--run-id` job form, 15 Nov):

```text
0 -9 crash: killed by SIGKILL restart 125
1 0 done stop None
2026-11-15T17:20:43.691Z restore.done 125 main/step_00000125-e1
{"step": 125, "branch": "main", "path": "main/step_00000125-e1", ...}
PASS: ./out follows queue rules v1.
```

Restored 125 = `pointer_step` 125, the path is in the list: COMPLETE, nothing lost, 15 steps run again.

---

## 11. NCCL hangs

> **In simple words.** In every step the GPUs exchange data with NCCL, and each one waits until all have joined.
> If one GPU stops, the others wait. Without limits they wait forever on a paid node. Two timers turn the wait
> into a restart. **The NCCL timeout** stops a collective that never finishes. **The step watchdog** catches a
> hang that NCCL does not see (a data wait, a deadlock in Python, a frozen rank).

### 11.1 The settings

| Setting | Dry run 1 | Where | Effect |
|---|---|---|---|
| `TORCH_NCCL_ASYNC_ERROR_HANDLING` | `1` | `slurm/mainrun.sbatch` | a NCCL error or timeout aborts the process (exit 1 or 134) instead of hanging |
| NCCL collective timeout | **10 min** | the trainer's `init_process_group(timeout=...)` | later: 3 × the longest collective measured in the dry runs ([ADR 0003](../adr/0003-node-health-checks.md) §2) |
| `TORCH_NCCL_TRACE_BUFFER_SIZE`, `TORCH_NCCL_DUMP_ON_TIMEOUT` | `2000`, `1` | `slurm/mainrun.sbatch` | the flight recorder: on a timeout, each rank dumps its last 2000 collectives |
| `TORCH_NCCL_DEBUG_INFO_TEMP_FILE` | `./out/<run_id>/logs/nccl_trace/rank_` (`mkdir -p` the folder first) | the job's start command (**not set yet**, section 14) | where the dumps go; the default is `/tmp`, which queue rules R3 forbid and which TSAI does not send back |
| `WATCHDOG_S` | `600` | `--watchdog-s` (`slurm/mainrun.sbatch`) | no step in 600 s: dump every Python stack, exit 75 (cause `hang_watchdog`) |

Both timers are 10 min in dry run 1. Whichever fires first, the result is the same: the attempt stops, the
supervisor or Slurm restarts it, and it restores the newest COMPLETE checkpoint (section 3). A hang loses at most
one interval of steps (run again) plus the 10 min of waiting.

### 11.2 What you see

| Signal | Means |
|---|---|
| exit 1 with `Watchdog caught collective operation timeout` or `NCCL error` in `job.log` | NCCL timed out or failed; async error handling stopped the process |
| exit 134 (SIGABRT) or 139 (SIGSEGV) | NCCL or CUDA aborted, or native code crashed |
| cause `hang_watchdog`, exit 75, stack dump in `job.log` | no step for `WATCHDOG_S`, with no NCCL error |
| alert H-16 (2 or more NCCL timeouts in an hour), H-14 (2 or more watchdog restarts in an hour) | it is not a one-off: page |
| the same rank or node in every hang | a bad node: section 10 |

The supervisor counts each of these as a crash (or a 75). Three crashes in 30 min become 78 `crash_loop`: the job is
held so it stops burning node hours (section 7).

### 11.3 Find the rank that stopped

```bash
L=./out/<run_id>/logs
grep -n -E 'collective operation timeout|NCCL error|hang_watchdog' $L/job.log $L/rank*.log | head
torchfrtrace $L/nccl_trace -p rank_ --allow-incomplete-ranks     # ships with torch; reads one dump per rank
```

`torchfrtrace` lines up the collectives of all ranks. The rank that is **missing** a collective the others
entered, or that left **no dump at all**, is the one that stopped. `--allow-incomplete-ranks` is needed because a
frozen rank often writes nothing. For a `hang_watchdog`, read the Python stack of each rank in `job.log`:

| The stuck rank is in | Likely cause | Do |
|---|---|---|
| a collective (`all_reduce`, `all_gather`, `all_to_all`, ...) while the others are past it | that rank's GPU or link | drain the node (section 10.2), `health_check.py --mode full` |
| the data loader (`__next__`, reading a shard) | the store or the data, not NCCL | check the store and the shard it was reading; tell Teams 01/02 if a shard is bad |
| ranks in **different** collectives | code: ranks took different branches (a rank-dependent `if`, uneven MoE routing, a save on rank 0 only) | a bug for Team 05; a restart does not fix it, so expect 78 `crash_loop` |
| `checkpoint` or a store upload | a slow or stuck store | CK-11 (throughput), CK-10 (backpressure); save time in [checkpoint_interval.md](checkpoint_interval.md) |

Rehearse it on 2 GPUs: `torchrun --nproc_per_node=2 support/kaggle/nccl_timeout_test.py --timeout-s 20` (rank 1
sleeps on purpose; rank 0 must stop about 20 s after the timeout and leave a trace).

---

## 12. Bad checkpoints

> **In simple words.** A checkpoint can be bad in three ways. A file is damaged (its sha256 does not match). The
> files are fine, but loading them does not give back the saved state. Or the state is exact but the model in it
> was already going wrong. Restore catches the first two by itself and falls back to the commit before. The
> third one needs a person to roll back.

### 12.1 What restore does by itself

| Bad in this way | Caught by | Already done | You do | Alert |
|---|---|---|---|---|
| a file does not match its sha256 (disk, network, store) | `IntegrityError`, restore step 3 or 5 | that commit is skipped; the previous one is tried | `verify` the bad step; `pin` the good one; find the hop that corrupts | CK-04 |
| the loaded state differs from the saved state (digest, probe loss, next batch, frozen tensors) | `RestoreCheckError`, step 8 | that commit is skipped; the previous one is tried | compare the two printed values; **never continue on that checkpoint** | CK-05 |
| every commit fails | `CheckpointError` | 78, held | section 12.3 | CK-06 |
| save cut before its commit (no `MANIFEST.json`, or no pointer names it) | the COMPLETE rule (section 2) | it is not a checkpoint, never a candidate | nothing | - |
| a save that never finished (`UploadTimeout`, `nvme_full`) | the save path | not committed; training continues unprotected | fix the store or disk before the next save | CK-03 |

A fallback costs one interval more of steps run again. It does **not** lose steps from the run, as long as the
older commit is COMPLETE.

### 12.2 Find which checkpoints are bad

```bash
python ckpt/ckpt.py list --run <run> | sed -E 's/.*"step": ([0-9]+).*/\1/' |
  while read s; do python ckpt/ckpt.py verify --run <run> --step "$s" | grep -v '"bad": \[\]'; done
grep -h '"restore.failed"' $V5_EVENTS_DIR/*.jsonl | tail -5         # which commit was skipped, and why
```

`verify` prints only the steps with damaged files (exit 1). `verify` checks sha256 only. A checkpoint that
`verify` passes can still fail the four proofs (CK-05): only a restore runs those.

### 12.3 When to roll back by hand

| Case | Roll back to |
|---|---|
| `nonfinite` or `loss_spike` (78) | the last step **before the loss started to rise**, not only the last commit before the trip: the guard needs 3 high steps, and a slow rise can sit in one or two commits |
| CK-05 on the newest commit, and the previous one also fails | the newest step that passes `verify` and a test restore |
| `FrozenChangedError` | the last commit; fix the code that trains the frozen tensor first |
| `CheckpointError` (nothing usable) | check the store first (access, missing files); if every commit is truly bad, tell the lead: the run starts again from the newest protected step that passes |

Then section 6 (`--from-step K --skip N --branch <new>`), after `verify` and `pin` of step K.

**Keep a good step reachable.** Retention keeps `--keep 9 --protect-every 15` in dry run 1, about the last 90 min
([checkpoint_interval.md](checkpoint_interval.md) §5). A bad checkpoint found later than that can only roll back to
a protected or pinned step. So **pin the last known-good step** as soon as a CK-04, CK-05 or loss alarm fires,
before retention runs again. Pinned steps are never deleted (`pins.json`).

---

## 13. Sources

Each week-2 rotation member ran the tests on their own machine and wrote a runbook; this file merges them. Slots
are in PR order (names are not used in team files).

| Slot | PR | Added to this file |
|---|---|---|
| R1 | #277 | operator steps (section 5), `list` / `verify` examples, the 1-GPU `restore_s` (8.2), simulation CK-13 (8.5) |
| R2 | #291 (merged as `docs/runbook_restore_restart_cpu.md`, now replaced by this file) | the four proofs and fallback, supervisor rules, the failure table, `jobs/restore_time/` and the size sweep (8.4) |
| R3 | #294 | four kill points, frozen-proof note, phase medians with checkpoint bytes, `check-out` caveat |
| R4 | #308 | first restore and restart on Linux x86_64; restart in job form with `queue_rules.py check-out` PASS |
| R5 | #320 | "When to act" first, COMPLETE rule (queue rules v1.1), `GIT_SHA` warning, restart-test `restore_s`, rehearsal |

Other evidence: [`results/restore_test_cpu.txt`](../results/restore_test_cpu.txt) (CPU, 1 and 2 processes),
[`results/restore_test_gpu.txt`](../results/restore_test_gpu.txt) (TSAI, 1 GPU), [`results/restart_cpu.txt`](../results/restart_cpu.txt)
(restart, CPU), [`results/restart_node.txt`](../results/restart_node.txt) (restart, TSAI, 1 GPU), PR #249, open (restore test on Windows, CPU).

## 14. Open items

| Item | Owner | Due |
|---|---|---|
| 1-GPU `restore_s` and size sweep as a TSAI job (8.2, 8.4) | Lead files the request | after Gate 2 if not run by Sat 14 Nov |
| Restart on the lab node, `results/restart_node.txt` | Lead | **done**: TSAI job on #258, 1 GPU, PASS (8.3) |
| Real restore time at config v1 size on the real store (8.5) | checkpoint owner + Team 6 | after Sat 14 Nov |
| 2-GPU restore | TSAI | after Gate 2 |
| Dry run 1 start command sets `TORCH_NCCL_DEBUG_INFO_TEMP_FILE` (11.1), the 10 min NCCL timeout and `WATCHDOG_S=600` | Lead, with Team 5 (`jobs/dryrun1/`) | Tue 17 Nov |
| Confirm Team 5's trainer has the step watchdog (`--watchdog-s`); today only the test trainer in `support/simulation/` has it | Team 5 | Tue 17 Nov |
| Fill the 10.4 checks from the dry run 1 logs (restarts, restored steps, steps run again) | Member C, with the lead's restore drill | Fri 20 Nov |
| NCCL timeout test on 2 real GPUs (`support/kaggle/nccl_timeout_test.py`), trace read with `torchfrtrace` | TSAI job | after dry run 1 |

## 15. Change log

| Version | Date | Change |
|---|---|---|
| v1 | 2026-11-11 | one runbook from the five rotation runbooks (R1–R5); replaces `docs/runbook_restore_restart_cpu.md` |
| v2 | 2026-11-15 | week-3 core task 4: node failures (10), NCCL hangs (11), bad checkpoints (12); Gate 3 restart checks from the returned logs (10.4); sources, open items and change log move to 13–15 |
