# Team 07 infrastructure: user guide and how the system works

For everyone who runs, feeds or watches the V5 main run: teams submitting jobs, Team 05's training code, the
teams that read checkpoints, on-call, and Team 07 itself. Every command here exists in this repo and was run in
the Docker test cluster unless the text says otherwise.

> **In simple words.** Training a large model costs money every hour, and machines break every few hours.
> This system makes sure that (1) **work already paid for is never lost**: training is saved often and every
> saved copy is proven exact; (2) **a failure fixes itself**: Slurm restarts the job from the last save without
> anyone waking up; (3) **broken GPUs are taken out** before they waste paid hours; (4) when a person *is*
> needed, **the system says what happened and what to do**, in plain words.

## Which part to read

| You are | Read |
|---|---|
| Anyone, first time | [§1 How the system works](#1-how-the-system-works) |
| A team running jobs (ladder runs, benchmarks, evals) | [§2 Running jobs](#2-running-jobs-every-team) |
| Team 05 (the training script) | [§3 Plugging in the training code](#3-plugging-in-the-training-code-team-05) |
| Teams 01/02 (data loader) | [§3.6 The data-loader contract](#36-the-data-loader-contract-teams-0102) |
| Teams 09, 11, 12 (eval, release, quantization) | [§4 Reading checkpoints](#4-reading-checkpoints-teams-09-11-12) |
| On-call (Team 07 rota, Team 08 pager) | [§5 On-call](#5-on-call-what-to-do-when) |
| Team 07, bringing the cluster up | [§6 Starting and running the cluster](#6-starting-and-running-the-cluster-team-07) |
| Team 07, changing the code | [§7 Testing and the simulation](#7-testing-and-the-simulation-team-07) |
| Looking something up | [§8 Reference](#8-reference) |

---

## 1. How the system works

### 1.1 The parts

```text
                     ┌───────────────────────── control (one host on the shared node) ──────────────────────────┐
  you ── ssh ──► sbatch ──► slurmctld (scheduler) ◄──► slurmdbd ◄──► MariaDB (accounts, limits, GPU-hours)       │
                     │        │   decides who runs where: accounts, QOS limits, GPU shares, priority, preemption  │
                     └────────┼──────────────────────────────────────────────────────────────────────────────────┘
                              │ starts jobs on
          ┌───────────────────▼──────────────────────── GPU node(s) ─────────────────────────────────────┐
          │ prolog.sh ─► health_check.py --mode prolog      (before every job: bad node? job goes back)  │
          │ healthcheck.sh ─► health_check.py --mode periodic (every 30 s: bad GPU? save, drain, move)    │
          │                                                                                               │
          │ job script (mainrun.sbatch / team_job.sbatch)                                                 │
          │   └─ job_queue.py run   ← the wrapper: turns any outcome into 0 / 75 / 78, crash-loop cap,    │
          │        └─ srun ─► trainer × 1 per GPU          writes the plain-words job comment            │
          │              └─ ckpt.Checkpointer  ← save / commit / restore / prove                          │
          │                     │ local NVMe (fast copy, the "stall")                                     │
          └─────────────────────┼─────────────────────────────────────────────────────────────────────────┘
                                ▼ background upload, checked
                     checkpoint store (shared file system, or any S3-compatible store):
                     <run>/latest.json, commits.jsonl, <branch>/step_<N>-e<epoch>/ (+ MANIFEST.json)
                                │
     events (JSON lines) ──────►│ metrics/watch.py (alerts, plain words) ─► Team 08 pager / webhook
                                ▼
                     Teams 09/11/12 read committed checkpoints (export to safetensors)
```

| Part | Folder | Decision record |
|---|---|---|
| Checkpoint: save, commit, restore, prove, export, retention | `ckpt/` | ADR 0001 |
| Queue: Slurm config, accounts and limits, job scripts, the wrapper | `slurm/`, `queue/` | ADR 0002 |
| Node health: GPU checks, Xid scan, NVLink, collectives, drain | `health/` | ADR 0003 |
| Monitoring and cost: events, 74 metrics, alerts, explanations | `metrics/`, `common/` | ADR 0004 |
| Start-up of the whole stack, in order | `launch/launch.sh` | ADR 0002 §11 |

### 1.2 The life of the main run

1. **Submit.** `sbatch slurm/mainrun.sbatch` (account `mainrun`, QOS `mainrun`: top priority, may preempt team
   jobs, no time limit, `--requeue`).
2. **Prolog.** Before the job starts on a node, a quick health check runs. A failing node is drained and the job
   goes back to the queue (not held), to start on a healthy node.
3. **Claim.** The trainer's first act is to *claim* the run: it writes `latest.json` with a new **epoch** number,
   only if nobody changed it since it read it. From then on, an older copy of the run that is somehow still alive
   cannot commit anything (§1.4).
4. **Restore.** It follows `latest.json` to the newest committed checkpoint, checks every file's sha256, checks
   the software environment, loads, and **proves** the load is exact (§1.3). A fresh run starts at step 0.
5. **Train.** Every `INTERVAL_S` (production: 30 min) it saves. Training pauses only for the copy to host memory
   (the *stall*); writing to NVMe and copying to the shared store run in the background.
6. **Commit.** The checkpoint counts only when every rank's files are in the shared store, re-checked, the `MANIFEST.json` is
   written **last**, and `latest.json` is moved (conditionally). A save that dies halfway is simply not a
   checkpoint; the pointer still shows the previous good one.
7. **Something goes wrong** → §1.5. **Done** → exit 0, the final checkpoint is committed.

### 1.3 Why a restore can be trusted: the four proofs

| Proof | What it catches |
|---|---|
| **State digest**: a fingerprint of every tensor (weights, optimizer, buffers), equal at any number of GPUs | a damaged, partial or wrongly resharded load |
| **Probe loss**: the loss on one fixed held-out batch, compared **bit for bit** | a model that loads "fine" but computes something else (last year's silent misload) |
| **Next batch**: the hash of the next data batch | resuming at the wrong place in the data |
| **Frozen tensors**: fingerprints of tensors that must never change (KE2 tables) | training that touched a frozen part |

Before the proofs: checksums of every file, the environment check (image, torch/CUDA/NCCL, config sha, tokenizer,
embedding policy, thread count), strict key names and shapes. A damaged checkpoint falls back to the previous
commit by itself. A wrong environment or renamed keys stop with exit 78, because every older checkpoint would
fail the same way.

### 1.4 Only one copy of a run may write (fencing)

Slurm can believe a job is dead while it still runs (a node loses its network, Slurm starts a new copy, the
network comes back). Two copies would then both save. Each attempt therefore takes an **epoch** ticket when it
starts, and `latest.json` accepts commits only from the newest ticket (a conditional write: a lock file on a file system, `If-Match` on an S3 store). The old copy's next commit
is refused, it logs `checkpoint.fenced` and exits 78 (`FencedError`). Each attempt also writes into its own
folders, `step_<N>-e<epoch>`, so two attempts never mix files.

### 1.5 What happens when something fails

| What happens | What the system does by itself | Work lost | A person? |
|---|---|---|---|
| Process killed, crash, OOM, NCCL error | wrapper turns it into 75; Slurm requeues; restore from last commit | since last commit | no (3 crashes in 30 min → held, yes) |
| Preemption by the main run, spot warning, health drain, operator `scancel --signal=USR1` | trainers save now, exit 75, requeued (on another node if needed) | ≈ 0 | no |
| Team job reaches its time limit | 300 s before: warning → save → exit 75 → requeued with the same job id | 0 | no |
| Kill during a save | half-written save is never committed; restore from the previous commit | since previous commit | no |
| A bad GPU (Xid, ECC, temperature, row remap, NVLink down, wrong collective) | periodic check drains the node; jobs save and move to a healthy node | ≈ 0 | replace hardware later |
| Node disappears | Slurm marks it DOWN after 30 s; job requeued elsewhere | since last commit | repair the node |
| Rank hangs without an error | step watchdog: stack dump, exit 75, restart | since last commit | no |
| Controller dies | backup controller takes over (the cloud layout); training keeps running | 0 | restart it |
| NaN, or a loss spike (×1.5 the median for 3 steps) | **no save**; exit 78; job **held** | since last commit | **yes**: roll back (§5.4) |
| Checkpoint fails its proofs | falls back to the previous commit | since that commit | look at it (alert CK-05) |
| Environment changed, keys renamed, other data manifest, other world size (DeepSpeed) | restore refused, exit 78, held | 0 | **yes**: fix, or allow on purpose |
| A frozen tensor changed | save refused, exit 78, held | since last commit | **yes**: fix the training code |
| A second copy of the run is alive | the old copy's commit is refused, it exits 78 | 0 | find why the old one lived |

### 1.6 The three exit codes

| Exit | Means | Slurm does | You do |
|---|---|---|---|
| **0** | finished, final checkpoint committed | marks COMPLETED | nothing |
| **75** | stopped in a safe state (saved, or nothing to save), or one crash | requeues (`RequeueExit=75`), restarts from `latest.json` | nothing |
| **78** | stopped on purpose: retrying would burn GPU hours for nothing | **holds** (`RequeueExitHold=78`, `squeue` shows `SPECIAL_EXIT`) | read the job comment; it says what to do |

---

## 2. Running jobs (every team)

> **In simple words.** Submit with your team's account. Your team has a fair share and a GPU share; the main run
> outranks you and may pause your job (it saves first and comes back by itself). Long jobs run in segments of
> up to 24 h and continue automatically.

### 2.1 Accounts, queues and limits

| Item | Value (the cloud layout / shared node) |
|---|---|
| Team accounts | `data tokenizer ke2 arch perf infra monitoring eval posttrain release quant` (under `teams`) |
| Partitions | `gpu` (training nodes, whole nodes), `eval` (≤ 4 h, default 1 h), `debug` (≤ 30 min, default 10 min), `cpu` (≤ 1 day, default 1 h). Without `--time` a job gets the partition default (`gpu`: the QOS `MaxWall`) |
| QOS `normal` (default for teams) | `MaxWall` 24 h; GPUs per job ≤ your share; ≤ 50 queued jobs per team; refused at submit if over a per-job limit |
| QOS `debug` | 30 min, 1 GPU, 1 running + 2 queued per user, higher priority |
| GPU share per team | `GrpTRES=gres/gpu=<share>` (Cloud nodes: 16; shared node: set by TSAI) |
| Budget | `GrpTRESMins` GPU-hours per team; alerts at 50 / 75 / 90 %, hard stop at 100 % |
| Main run | QOS `mainrun` preempts `normal` and `debug`; your job gets SIGTERM, 60 s to save, then requeues |

### 2.2 Submitting

```bash
# a training-style job with automatic save/restart (the template every team should copy)
sbatch --account=arch --export=ALL,RUN_ID=ladder-350m,STEPS=20000,INTERVAL_S=600 \
       /opt/v5/slurm/team_job.sbatch

# your own script with the same save/restart behaviour
sbatch --account=arch --export=ALL,RUN_ID=my-run,V5_TRAIN_SCRIPT=/path/to/train.py \
       /opt/v5/slurm/team_job.sbatch

# a quick check on one GPU, ahead of the queue
sbatch --account=arch --qos=debug -p debug --time=00:10:00 --gpus-per-node=1 --wrap 'nvidia-smi; python -c "import torch"'

# an evaluation job
sbatch --account=eval -p eval --time=02:00:00 --gpus-per-node=1 my_eval.sbatch
```

`team_job.sbatch` sets `--requeue`, `--time=04:00:00` and `--signal=B:USR1@300`: five minutes before the time
limit the job saves, exits 75 and Slurm requeues it with the **same job id**, so a long run continues in segments.
Override with `sbatch --time=12:00:00 ...` (at most the QOS `MaxWall`). Set the lead to at least 2 × your save
time + 60 s.

Options your job reads (`--export=ALL,KEY=value`):

| Key | Default | Meaning |
|---|---|---|
| `RUN_ID` | `team-<jobid>` | names the checkpoint folder: **reuse it to continue a run** |
| `STEPS` | 1000 | total steps |
| `INTERVAL_S` | 600 | seconds between saves |
| `TRAIN_EXTRA` | empty | extra trainer arguments, e.g. `--from-step 1200 --skip 5 --branch b1` |
| `V5_TRAIN_SCRIPT` | the test trainer | your training script (it must follow §3) |
| `V5_REMOTE_ROOT` | from `/etc/v5/node.env` | where checkpoints go: a shared folder (`/shared/ckpt`) or `s3://...` |

### 2.3 When your job does not start

`squeue -u $USER -o '%A %j %T %r'` shows the reason. A refused `sbatch` prints it at once.

| Reason | Means | Do |
|---|---|---|
| `Invalid account or account/partition combination` | you are not in that account | use your team's account; ask Team 07 to add you |
| `AssocGrpGRES` | your team already uses its GPU share | wait for your own jobs to finish |
| `QOSMaxGRESPerJob` (refused) | more GPUs per job than the QOS allows | ask for fewer |
| `QOSMaxWallDurationPerJobLimit` (refused) | `--time` above `MaxWall` | ask for less; long runs requeue themselves |
| `QOSMaxSubmitJobPerUserLimit` / `QOSMaxJobsPerUserLimit` | too many jobs queued / running | wait or cancel some |
| `AssocGrpCPUMinutesLimit`, `AssocGrpGRESMinutes` | budget used up | talk to the lead (alert Q-15) |
| `Priority` | others are ahead | normal |
| `BeginTime` | requeued; waiting for the old launch credential to expire (≈ 60 s) | normal after a restart |
| `Resources` | no free node | normal; the main run pages after 10 min (Q-01) |

### 2.4 Watching your job

```bash
squeue -u $USER                          # state and pending reason
scontrol show job <id> | grep -E 'JobState|Restarts|Comment'   # Comment = plain-words status from the wrapper
sacct -X -j <id> -o jobid,state,exitcode,restarts,elapsed,alloctres
python /opt/v5/queue/job_queue.py status               # every job and drained node, in plain words
python /opt/v5/metrics/explain.py 78                  # or 75, AssocGrpGRES, FencedError, CK-05, nvlink ...
python /opt/v5/ckpt/ckpt.py list --run /shared/ckpt/<RUN_ID>         # committed checkpoints (or s3://<bucket>/<prefix>/<RUN_ID>)
```

---

## 3. Plugging in the training code (Team 05)

> **In simple words.** The training script must do five things: restore at the start, save on a timer, save and
> exit 75 when asked to stop, exit 78 when retrying cannot help, and give us a probe function and a loader that
> can say where it is. Everything else (upload, commit, proofs, fencing, retention) is done for you.

### 3.1 How it is launched

`srun` starts **one trainer process per GPU** directly (no `torchrun`, no `deepspeed` launcher). Slurm sets
`SLURM_PROCID`, `SLURM_LOCALID`, `SLURM_NTASKS`; the job script sets `MASTER_ADDR` and `MASTER_PORT`. Initialise
the process group from those (the test trainer does: `support/simulation/trainer/train.py`). Why not a launcher:
the `deepspeed` launcher dies on SIGUSR1 and kills all ranks when one exits non-zero, which breaks both the
save-on-signal and the exit-75 contract (uz9ai's analysis, ADR 0002 §4). DeepSpeed itself works this way: our
The DeepSpeed test trainer calls `deepspeed.initialize` with no launcher.

### 3.2 The skeleton

```python
import signal, sys
from ckpt.ckpt import Checkpointer, EXIT_DONE, EXIT_RETRY, EXIT_FATAL, NonFiniteError, FrozenChangedError, \
    CheckpointError
from ckpt.ds_ckpt import DSCheckpointer           # only with DeepSpeed: same API, pass the engine as `model`
from common.reasons import write_exit_note

ck = Checkpointer(run_id, local_root="/nvme/ckpt", remote_root=remote_root,
                  config_path=config_path,          # its sha256 goes into the environment check
                  seed=seed, frozen_keys=("ke2_table",))   # tensors that must never change
try:
    info = ck.restore(model, optim, loader, probe_fn,      # claims the run (epoch), restores, proves
                      from_step=None, skip=0, new_branch=None, allow_env_change=False)
except CheckpointError as e:                       # renamed keys, other environment, other data, ...
    write_exit_note(EXIT_FATAL, type(e).__name__, None, str(e)); sys.exit(EXIT_FATAL)
step = info["step"] if info else 0

stop = {"sig": None}
for s in (signal.SIGUSR1, signal.SIGTERM):        # preemption, spot, drain, time limit: save now
    signal.signal(s, lambda n, f: stop.update(sig=signal.Signals(n).name))   # only set a flag here

while step < total_steps:
    train_one_step(); step += 1
    flags = all_reduce_max([due_for_save(), stop["sig"] is not None, ck.fenced])  # every rank agrees
    if flags.fenced:                               # a newer copy of this run owns it
        sys.exit(EXIT_FATAL)
    if flags.stop:
        ck.save(step, model, optim, loader, probe_fn, tokens, reason="signal")
        ok = ck.wait()                             # wait for the commit before exiting
        sys.exit(EXIT_FATAL if ck.any_fenced() else EXIT_RETRY)
    if flags.due:
        ck.save(step, model, optim, loader, probe_fn, tokens, reason="interval")   # returns after the stall

ck.save(step, model, optim, loader, probe_fn, tokens, reason="final")
sys.exit(EXIT_DONE if ck.wait() else EXIT_RETRY)
```

The working version, with the loss-spike guard, the watchdog and the drill hooks, is
`support/simulation/trainer/train.py`. Copy its structure.

### 3.3 Rules

| Rule | Why |
|---|---|
| Call `save()` / `restore()` on **every rank** | fingerprints, the probe forward and DCP are collectives; a rank-0-only call hangs |
| Save only **between optimizer steps**, never between micro-batches of one step | half-accumulated gradients are not saved; act on a stop signal at the next accumulation boundary |
| In the signal handler **only set a flag** | saving inside a handler can deadlock |
| All ranks agree on save/stop in **one all-reduce** | a signal may reach one rank only |
| `NonFiniteError` from `save()` (NaN/Inf) and `FrozenChangedError` → exit **78** with `write_exit_note` | nothing bad is ever saved; a person rolls back |
| Write `write_exit_note(code, cause, step, detail)` before exiting with 75/78 | the wrapper turns it into the plain-words job comment |
| Never catch and ignore `CheckpointError` from `restore()` | starting at step 0 with random weights is the failure we exist to prevent |
| Keep kernels deterministic in resume tests and the CI probe | the probe loss is compared bit for bit |
| Set `OMP_NUM_THREADS` the same on every restart (job scripts set 1) | it changes the last bits of the loss on CPU |

### 3.4 The probe function

`probe_fn(model) -> float`: the loss of one fixed held-out batch, in `eval()` mode under `torch.no_grad()`,
restoring the previous mode. It must call the model on every rank (FSDP/ZeRO-3 forward is collective). See
`make_probe_fn` in `support/simulation/trainer/tiny.py`.

### 3.5 Environment variables the trainer and checkpoint read

| Variable | Meaning |
|---|---|
| `V5_EMBEDDING_POLICY_ID` | Team 04's embedding policy (e.g. `ke2-v1`); part of the environment check |
| `IMAGE_DIGEST`, `TOKENIZER_SHA` | recorded in every manifest and must match on resume |
| `GIT_SHA` | source commit, recorded but not compared (issue #298). Unset: `git rev-parse HEAD` of the checkout; no git either: `none` and a `checkpoint.provenance_unknown` event |
| `V5_CODE_PATHS` | extra files that change the numbers (trainer, model, loader), `:`-separated; with `ckpt.py` and `Checkpointer(code_paths=...)` they make `code_sha256`, which must match on resume |
| `V5_ASYNC_SAVE` | `1` (default) async save; `0` blocking save |
| `V5_VERIFY_MODE` | `full` (re-hash every object; tests) or `head` (compare the checksum an S3 store kept at upload; TB-size runs) |
| `V5_DEEPSPEED`, `V5_ZERO_STAGE`, `V5_DS_PRECISION` | test trainer: DeepSpeed backend, ZeRO 0–3, fp32/fp16/bf16 |
| `V5_FSDP` | test trainer: FSDP2 (`fully_shard`) |

With DeepSpeed: use `DSCheckpointer`, pass the engine as `model`. A change of world size is refused
(`ReshardError`, 78) until an operator converts the checkpoint with `ds_to_universal.py`; the ZeRO stage and the
DeepSpeed config are part of the environment check.

### 3.6 The data-loader contract (Teams 01/02)

The loader must offer:

| Method | Returns / does |
|---|---|
| `state_dict()` | JSON dict: **one global ledger offset**, the skip list and `manifest` (sha256 of the shard list), **the same on every rank** |
| `load_state_dict(d)` | continue from it; **raise `ValueError`** if `d["manifest"]` is not this loader's data |
| `next_batch_id()` | `{"position": ..., "sha256": <hash of the next batch>}`, without consuming it |
| `next()` | the next batch |
| `add_skip(n)` | skip the next n batches (rollback) |

Prove it before the main run:

```bash
python /opt/v5/ckpt/loader_contract.py --factory mypkg.loader:make_loader   # make_loader(rank, world)
```

Why one global offset: after a node is lost the run may continue on fewer GPUs, and every new rank then gets the
saved state of old rank 0. That only works if it means "global batch N".

---

## 4. Reading checkpoints (Teams 09, 11, 12)

- Read only **committed** checkpoints: the path in `latest.json`, in `commits.jsonl`, or in the
  `checkpoint.committed` event. Never list folders: a folder without `MANIFEST.json` is not a checkpoint.
- Read-only, never on a training node. Retention never deletes the checkpoint `latest.json` points to, pinned
  steps, or every N-th protected step.
- Export to one plain file, checked (strict keys, digest, probe loss bit-equal when the dtype is unchanged):

```python
from ckpt.ckpt import export_safetensors
export_safetensors("/shared/ckpt/<run>",          # or "s3://<bucket>/<prefix>/<run>"
                   model_factory, probe_fn, "/tmp/model.safetensors", step=None)
```

  DeepSpeed checkpoints export through `zero_to_fp32` the same way (`ckpt/ds_ckpt.py:export_ds`). A dtype change
  (quantization) is Team 12's step, with its own tolerance.
- Protect a step you need: `python ckpt/ckpt.py pin --run <run> --step 1200`.

---

## 5. On-call: what to do when

> **In simple words.** Most failures fix themselves; you only act on **78 (held)**, a **drained node**, or a
> **HIGH alert**. Each of them already tells you what to do; `explain.py` prints the full answer.

### 5.1 Daily look

```bash
python /opt/v5/queue/job_queue.py status    # jobs and drained nodes, plain words
sinfo -R                                               # drained nodes and why (v5:<check> or health: <check>)
python /opt/v5/ckpt/ckpt.py list --run <run> | tail -3
python /opt/v5/metrics/explain.py <anything you do not recognise>
```

Alerts arrive through Team 08's pager or the webhook in `V5_ALERT_WEBHOOK`; each carries the metric id
(e.g. `CK-05`), what happened and the first action. The full list: `support/docs/metrics_catalog.md` and
`support/docs/codes_and_actions.md`.

### 5.2 A job is held (exit 78)

`scontrol show job <id> | grep Comment` names the cause:

| Cause | Do |
|---|---|
| `nonfinite` (NaN) / `loss_spike` | roll back (§5.4), tell Team 05 |
| `crash_loop` | read the job log; fix; `scontrol release <id>` |
| `StrictLoadError` | the model code renamed keys: fix the code or the mapping; never resume by ignoring keys |
| `EnvMismatchError` | software/config changed. If intended and approved: resubmit with `TRAIN_EXTRA=--allow-env-change` (logged); else go back to the old image |
| `FrozenChangedError` | find the code that trains the named tensor, fix it, roll back |
| `DataManifestError` | point the loader back at the run's shard list, or start a new branch on purpose |
| `ReshardError` | resubmit at the saved size, or convert (DeepSpeed: `ds_to_universal.py`) |
| `FencedError` | nothing for the run (a newer copy owns it); find why the old copy was still alive, drain that node if it repeats |
| `CheckpointError` (no usable checkpoint) | `ckpt.py verify --run <run>`; check the store (CK-04/CK-05) |

### 5.3 A node is drained

`sinfo -R` shows `v5:<check>` (periodic health) or `health: <check>` (launch). Its jobs already saved and moved.

| Check | Do |
|---|---|
| `xid`, `ecc_uncorrectable`, `remapped_rows`, `dcgm_diag`, `gpu_inventory` | replace the instance / open a hardware ticket; reboot first for `gpu_inventory` |
| `nvlink` | reset GPUs or reboot; replace if the link stays down |
| `nccl_<op>` or `nccl_collectives` | `health_check.py --mode full` on it; replace if it fails again; read the flight-recorder dump |
| `gpu_temperature` | check cooling |
| `nvme_free` | clean `/nvme` |
| `clock_offset` | fix chrony |
| `drill_force_fail` | test only: remove `/var/lib/v5-health/force_fail` |

Then: `sudo scontrol update nodename=<node> state=resume`.

Xid 94 (contained ECC) alone is only a warning: the job restarts, the GPU stays. A second 94 on the same GPU within
24 h drains the node.

### 5.4 Rolling back after a NaN or a loss spike

```bash
python /opt/v5/ckpt/ckpt.py list --run <run>          # pick the last good step K
scancel <held job id>
sbatch --export=ALL,TRAIN_EXTRA="--from-step K --skip 5 --branch b1" /opt/v5/slurm/mainrun.sbatch
```

The run continues on branch `b1` from step K, skipping the 5 batches after it. The old branch stays readable.

### 5.5 Other operations

| Task | Command |
|---|---|
| Move jobs off a node and keep new ones away | `python queue/job_queue.py drain "<reason>" --node <node>` |
| Check every file of a checkpoint | `python ckpt/ckpt.py verify --run <run> [--step N]` |
| Free storage | `python ckpt/ckpt.py retention --run <run> --keep 3 --protect-every 5 --dry-run` (then without `--dry-run`; own role in the cloud) |
| Back up the accounting DB (and prove it restores) | `slurm/backup_db.sh <dir>` then `slurm/backup_db.sh --verify-latest <dir>` |
| Check the checkpoint store still refuses stale writes | `python ckpt/ckpt.py probe-store --run <run>` |
| Upgrade software mid-run | only at a checkpoint: emergency save → upgrade (`slurmdbd` → `slurmctld` → `slurmd`) → resubmit with `--allow-env-change` |

---

## 6. Starting and running the cluster (Team 07)

### 6.1 Start everything in order

```bash
cp /opt/v5/launch/cluster.env.example /etc/v5/cluster.env      # hosts, store, run id; no secrets
$EDITOR /etc/v5/cluster.env
/opt/v5/launch/launch.sh --list        # the 12 steps
/opt/v5/launch/launch.sh --dry-run     # what would run where
/opt/v5/launch/launch.sh               # start; stops at the first failed step
/opt/v5/launch/launch.sh --from health # continue after a fix
```

| Step | Proves before going on |
|---|---|
| preflight | settings complete, every host reachable, **the same code on every host** |
| munge | `munged` everywhere; every host accepts the controller's credential |
| slurmdbd | accounting daemon answering |
| dbbackup | today's DB dump **and a test restore** |
| slurmctld | controllers UP (`scontrol ping`) |
| accounts | `setup_accounts.sh` (safe twice); `mainrun` association exists |
| slurmd | every node registered (a node drained on purpose stays drained) |
| health | full check on every node at once (GPUs, ECC, row remap, NVLink, Xid, NVMe, 4 collectives); a failing node is drained; fewer healthy than `V5_MIN_NODES` stops |
| services | hot-spare timer and alert watcher (controller), spot watcher (nodes) |
| store | `probe-store`: write, read, **stale write refused** (fencing depends on it) |
| submit | main run submitted unless queued; it claimed its epoch, restored and started |
| status | `job_queue.py status` |

Secrets never live in the repo: the DB password is in `/etc/v5/db.env` (written at boot from the cloud secrets
store), access to an S3 store is the node's own role, the munge key is copied by hand or from the cloud session manager.

### 6.2 Settings to adapt to the shared node

| Setting | Where | Shared-node value |
|---|---|---|
| Team GPU share, node cap, `MaxWall`, queued-job cap | env of `setup_accounts.sh`: `V5_TEAM_GPUS`, `V5_NODE_CAP`, `V5_TEAM_MAXWALL`, `V5_TEAM_MAXSUBMIT` | TSAI's share per team; node cap ≥ 1 |
| GPUs per node | `thresholds.yaml: expect_gpus` or `V5_EXPECT_GPUS` in `/etc/v5/node.env` | the node's count |
| Collective size in the full check | `V5_COLL_MAX_MB` (default 1024 on GPU) | default |
| Checkpoint store | `V5_REMOTE_ROOT` | the bucket TSAI gives |
| Thresholds (temperature, ECC, busbw floor, Xid classes) | `health/thresholds.yaml` | vendor limits until the week-2 baseline (5 × `--mode full`) |

### 6.3 Health checks by hand

```bash
python health/health_check.py --mode prolog   --report-only    # quick, ≤ 30 s
python health/health_check.py --mode periodic --report-only    # what the 30 s timer runs (drains on fail without --report-only)
python health/health_check.py --mode full     --report-only    # adds DCGM diag 2 and the 4 collectives, ≤ 15 min
torchrun --nproc_per_node=8 health/allreduce_test.py --max-mb 1024 --ops all_reduce,all_to_all
python health/xid_scan.py                                       # Xids in the kernel log, classified
```

Exit codes of the health check: 0 pass, 3 warn, 4 fail (in prolog mode a warn exits 0, so Slurm does not drain a
healthy node). A missing tool is `skipped`, never `pass`.

---

## 7. Testing and the simulation (Team 07)

```text
teams/07-infrastructure/
├── USER_GUIDE.md          this file
├── adr/ ckpt/ queue/ slurm/ health/ metrics/ common/ launch/   what runs on the cluster
└── support/
    ├── tests/             unit tests (pytest)
    ├── simulation/        Docker Slurm cluster + drills (run_sim.py), test trainer, results*/
    ├── kaggle/            GPU checks on Kaggle (2 GPUs)
    ├── tools/             bench_save.py (stall and async timings)
    └── docs/              reviews, sim results, merge plans, codes_and_actions, metrics_catalog
```

### 7.1 Unit tests

```bash
cd teams/07-infrastructure/support
python -m pytest -q tests/                              # ~17 min on a laptop (2 GPU-only tests skip)
# the checkpoint tests against S3 (an emulator, or a real bucket)
V5_S3_ENDPOINT=http://127.0.0.1:9000 V5_TEST_REMOTE=s3://v5-ckpt python -m pytest -q tests/test_ckpt.py
```

Checkpoint tests T1–T30 are listed in `ckpt/README.md` §10; DeepSpeed tests (T18–T23) need
`pip install deepspeed`.

### 7.2 The Docker Slurm simulation

```bash
python3 support/simulation/run_sim.py --smoke        # ~5 min after start: accounts, limits, health fakes, kill + restore
python3 support/simulation/run_sim.py                # every drill (~35 min); writes results/ and docs/sim_results.md
python3 support/simulation/run_sim.py --deepspeed    # optional: every drill with the DeepSpeed trainer (not part of the submitted results)
python3 support/simulation/run_sim.py --store folder # every drill with checkpoints on a shared file system (bare metal)
python3 support/simulation/run_sim.py --only limits time_limit --keep-up    # some drills, leave the cluster up
docker compose -f support/simulation/slurm-docker/docker-compose.yml exec slurmctld bash   # look around
```

The cluster: `slurmctld` + `slurmctld2` (backup), `slurmdbd` + MariaDB, GPU nodes `c1`–`c3` (2 placeholder GPUs
each, fake `nvidia-smi`), `c4` (eval/cpu), and an S3 emulator. Users `svc` (submit service), `alice` (arch),
`bob` (perf), `carol` (no account).

Plant a hardware fault by hand (the real health scripts read the fakes):

```bash
docker compose ... exec c3 sh -c 'echo "1 temperature.gpu=92" > /run/fake/gpus'           # hot GPU 1
docker compose ... exec c3 sh -c 'printf "GPU 0: x\n\t Link 0: <inactive>\n" > /run/fake/nvlink'
docker compose ... exec c3 sh -c 'echo "NVRM: Xid (PCI:0000:3b:00): 79, pid=1, off the bus" > /run/fake/dmesg'
docker compose ... exec c3 rm -f /run/fake/*          # heal; then scontrol update nodename=c3 state=resume
```

Every drill writes its evidence to `results/evidence/<drill>.log`: each command, its exit code and output, and the
recorded result, so a reviewer can check a claim without rerunning it. To add a drill: write `d_<name>()` in
`run_sim.py` that breaks one thing, waits for the system's reaction through the events, and calls
`record(<name>, ok, **details)`; add it to `plan` in `main()`.

### 7.3 GPU checks on Kaggle

`support/kaggle/README.md`: build the zip, upload, turn Internet on, run all; it runs the checkpoint tests on
CUDA (incl. FSDP2 and DeepSpeed fp16), the stall benchmark and the NCCL checks, and writes `summary.md`.

---

## 8. Reference

### 8.1 Files on a node

| Path | What |
|---|---|
| `/opt/v5/` | this team folder (read-only) |
| `/etc/v5/node.env` | per-node settings (events dir, expected GPUs, checkpoint store) |
| `/etc/v5/cluster.env` | what `launch.sh` needs (hosts, store, run id) |
| `/var/log/v5/events/*.jsonl` | every event, one JSON per line (shipped to the shared store) |
| `/var/log/v5/logs/<job>-<id>.out` | job logs (appended across restarts) |
| `/var/lib/v5-health/` | health state (Xid lines seen, last report) |
| `/nvme/ckpt/<run>/` | local checkpoint cache (the shared store holds the copy that counts) |

### 8.2 Checkpoint store layout

```text
<remote_root>/<run_id>/latest.json          newest committed checkpoint + the owning epoch
<remote_root>/<run_id>/commits.jsonl        every commit in order (the fallback list)
<remote_root>/<run_id>/pins.json            steps a person pinned
<remote_root>/<run_id>/crashes.json         crash times for the crash-loop cap
<remote_root>/<run_id>/<branch>/step_<N>-e<epoch>/   shards, extra_rank<r>.json, sums_rank<r>.json, MANIFEST.json
```

### 8.3 Settings (environment)

| Variable | Used by | Default |
|---|---|---|
| `RUN_ID` | job scripts, trainer | `v5main` (main run) |
| `STEPS`, `INTERVAL_S`, `WATCHDOG_S`, `STEP_SLEEP`, `TRAIN_EXTRA` | job scripts | see the scripts |
| `V5_REMOTE_ROOT`, `V5_S3_ENDPOINT`, `V5_S3_CONCURRENCY` | checkpoint store | `/shared/ckpt`, the library default, 16 |
| `V5_TRAIN_SCRIPT` | wrapper | test trainer |
| `CRASHLOOP_N`, `CRASHLOOP_WINDOW_S` | wrapper | 3, 1800 |
| `V5_EVENTS_DIR` | everything | `/var/log/v5/events` |
| `V5_EXPECT_GPUS`, `V5_NVME`, `V5_NVME_MIN_FREE_GB`, `V5_MEM_MIN_GB`, `V5_HEALTH_STATE`, `V5_COLL_MAX_MB` | health check | thresholds.yaml |
| `V5_SPOT_NOTICE_FILE`, `V5_IMDS_URL`, `V5_SPOT_POLL_S` | spot watcher | file, none, 5 |
| `V5_ALERT_WEBHOOK` | alert watcher | none |
| `V5_TEAM_GPUS`, `V5_NODE_CAP`, `V5_TEAM_MAXWALL`, `V5_TEAM_MAXSUBMIT` | `setup_accounts.sh` | 16, 2, 24:00:00, 50 |
| `V5_EMBEDDING_POLICY_ID`, `V5_ASYNC_SAVE`, `V5_VERIFY_MODE` | checkpoint | none, 1, full |

### 8.4 Words used here

| Word | Meaning |
|---|---|
| checkpoint | a saved copy of everything training needs to continue |
| commit | the moment a checkpoint counts: manifest written last, `latest.json` moved |
| stall | the time training waits during a save (only the copy to host memory) |
| epoch (fencing) | the ticket number of one attempt of a run; only the newest may commit |
| drain | no new jobs on a node; its jobs save and move first |
| requeue | Slurm puts the job back in the queue with the same id; it restarts from `latest.json` |
| hold | Slurm keeps the job until a person releases it (after exit 78) |
| QOS | a set of limits and a priority a job runs under (`mainrun`, `normal`, `debug`) |
| GPU share | the most GPUs one team may hold at once (`GrpTRES=gres/gpu`) |
| Xid | the NVIDIA driver's error number in the kernel log |
| collective | a multi-GPU exchange (all-reduce, reduce-scatter, all-gather, all-to-all) |
| probe loss | the loss on one fixed batch, compared bit for bit after a restore |

### 8.5 What is not proven yet

- Nothing has run on the shared GPU node yet (from 1 Nov); GPU numbers come from the pending Kaggle run.
- The store is tested as a shared folder and as an S3-compatible emulator (moto 5.1.10), not on the real store;
  `probe-store` checks it at every launch.
- The DeepSpeed path runs on CPU (gloo) in Docker; fp16 and FSDP2 on GPUs wait for Kaggle.
- `launch.sh`'s `services` step and SSH transport were not run (the Docker cluster has no systemd).
- uz9ai's installer (`cluster.toml`) is not merged yet: Phase B of `support/docs/merge_execution_plan.md`.
