# ADR 0002: Job queue and cluster operations on self-managed Slurm on cloud GPU nodes, validated in Docker Slurm

- Status: Proposed
- Date: 2026-10-27 (revised from 2026-10-25; second revision after the week-1 review, see [review_week1.md](../support/docs/review_week1.md))
- Area: Queue (`slurm/`, `support/simulation/slurm-docker/`, `support/simulation/run_sim.py`), cluster image, storage, access, events, goodput
- Related: ADR 0001 (checkpoint, exit codes), ADR 0003 (health, drain), ADR 0004 (cost, metrics)

> **In simple words.** A scheduler is the "front desk" of the cluster: teams hand in jobs, it decides who
> runs where and when, and it restarts the main run by itself when something breaks. We use Slurm, the
> standard for training clusters. The instructor asked us to prove it works in a Docker copy of the
> cluster first, so we do not pay for GPUs while we debug the queue.

## Context

V4 had **no scheduler**: jobs were started by hand.
One cluster sat idle for 3 days; the only guard was a CPU-idle alarm. Restarts were typed by hand.

For V5 the instructor gives **no keys to students**, wants scheduling on **Slurm, validated in Docker Slurm**,
and we will run on **cloud GPU nodes**. The cluster must:

- run the **main run** without letting anything else take its GPUs;
- share the remaining capacity fairly: Team 05's scaling ladder (5–8 runs), Team 06 benchmarks, Team 09 evals,
  Team 12 quantization, Team 10 RL tests, Teams 01–03 CPU data jobs;
- **restart the main run on its own** from the last committed checkpoint (ADR 0001);
- keep sick nodes out of service (ADR 0003);
- account for every GPU-hour and node-hour (ADR 0004).

Team 07 also runs the **two dry runs** (S15 team charter). The S15 reference run lost 9 of its 38 interruptions
to slow storage reads.

## Decision drivers

1. Automatic requeue and restart, with no person typing a command.
2. Hard priority for the main run, fair share for everyone else, and **no idle paid GPUs**.
3. One pinned software stack on every node.
4. Storage that never stalls training.
5. Every lost minute is measured and priced (goodput accounting).
6. Testable on a laptop in week 1, **in Docker Slurm, with the same configuration as production**.

## Options considered

| Option | For | Against |
|---|---|---|
| A. No scheduler, as in V4 (SSH + scripts) | nothing to run | no queue, no fairness, no automatic restart |
| B. managed Kubernetes + Kueue or Volcano | strong for services | gang scheduling and topology for multi-node NCCL jobs are add-ons; extra layers (CNI, device and fast-network plugins) |
| C. the provider's managed Slurm service (managed Slurm) | provider-built autoscaling, managed Lustre and fast-network wiring | its config layer and update cycle sit between us and Slurm; harder to mirror in Docker |
| D. A managed cloud batch service | managed | weak multi-node gang jobs; no fair-share like Slurm's |
| E. **Self-managed Slurm on cloud nodes** | full control of `slurm.conf`, versions and node image; the norm for LLM training; `slurmdbd` gives accounting and fair-share; **the Docker test runs the same file** | we operate the control plane ourselves |

Runtime options: (i) bare node image + venv; (ii) **container image run by Slurm through Pyxis/Enroot**; (iii) Apptainer.

> **In simple words.** We run Slurm ourselves on cloud nodes (E), because then the Docker copy and the real cluster
> use the same configuration file, and what we test is what we run. The provider's managed Slurm (C) would be a sensible
> fallback if operating Slurm ourselves becomes too much work.

## Decision

**E. Self-managed Slurm on cloud nodes, with containers through Pyxis/Enroot. One `slurm/slurm.conf` for Docker and
the cloud; only the node lines differ (`support/simulation/slurm-docker/nodes.conf` vs `slurm/nodes.cloud.conf`).**

### 1. Cluster shape

- **Head instance** (small, CPU): `slurmctld`, `slurmdbd` and MariaDB on a block volume with daily snapshots.
  A **backup `slurmctld`** on a second small instance (`SlurmctldHost=slurmctld2`), sharing
  `StateSaveLocation` on a shared file system. Tested in Docker: the backup takes over, running jobs keep training, new jobs are
  accepted, and the primary takes back control when it returns.
- **Accounting database backup:** `slurm/backup_db.sh` dumps `slurm_acct_db` daily to S3; a backup only counts
  after `--verify-latest` has restored it into a scratch database with the same tables (tested in Docker).
- **GPU nodes:** a generic 8-GPU node with a fast node-to-node network. All nodes in **one placement group** in
  one zone, so the network between them is the fast one.
- **Main run on on-demand or a reserved capacity booking**, never spot (ADR 0004 §3), plus **one hot spare**.
- **The hot spare is not idle:** it runs preemptible team jobs, which the main run preempts when it needs the node.
- **Idle nodes are stopped:** `State=CLOUD` nodes with `SuspendProgram` / `ResumeProgram` and `SuspendTime=600`;
  the spare is kept up by **name**: `job_queue.py keep-spare` (systemd timer on the controller, every minute,
  `slurm/v5-keep-spare.*`) sets `SuspendExcNodes=<spare node>` and powers a node up if none is free. The count
  form `gpu-[1-9]:1` was dropped: the man page says it keeps N "powered up" nodes and does not say whether busy
  main-run nodes count, and if they do, no spare is kept (review finding, week 1). This replaces V4's idle alarm.

- **GPUs are a Slurm resource (gres).** `GresTypes=gpu`; on cloud nodes `gres.conf` uses `AutoDetect=nvml` and
  `cgroup.conf` sets `ConstrainDevices=yes`, so a job sees only its own GPUs (`CUDA_VISIBLE_DEVICES`). Job
  scripts ask `--gpus-per-node=8 --ntasks-per-node=8` (one rank per GPU). `AccountingStorageTRES=gres/gpu`
  records GPU-hours per account, so budgets and reports are in GPU-hours. Docker uses 2 placeholder GPUs per
  node (no computation) to test allocation and accounting.
- **The only Docker/the cloud differences** are four small files: `site.conf` (process tracking and cgroups),
  `nodes.conf`, `gres.conf`, `cgroup.conf` (`support/simulation/slurm-docker/` vs `slurm/*.cloud.conf`). `slurm.conf` is shared.
- **When nodes run out:** if more nodes fail than there are spares, the main run **waits** (pending) and
  Q-01 pages at 10 min. It does **not** shrink by itself: a smaller world changes speed, is not bit-equal, and
  needs a person to agree. The operator may restart it on fewer nodes (`sbatch --nodes=1`), which the
  rollback drill tests.

| Partition | For |
|---|---|
| `gpu` | training, whole nodes (`OverSubscribe=EXCLUSIVE`) |
| `eval` | separate, cheaper GPU nodes; the training node is never used for evaluation (S6, S15) |
| `debug` | 30-min limit |
| `cpu` | data, tokenizer, retention and export jobs |

### 2. Runtime image

- One image per release, **built in CI** from a lock file, pinned by **digest**. Base: the NVIDIA CUDA image
  matching the node image's driver major version, plus `the cloud's NCCL network plugin` and the fast-network libraries; exact torch, triton and
  NCCL versions and our kernels. At build time the image runs an import and version check (kept from V4).
- Jobs run with `srun --container-image=<digest>`; the node image holds only the driver, the fast network, Enroot/Pyxis and Slurm.
- The digest goes into every checkpoint manifest (ADR 0001); a different digest refuses to resume unless overridden.
- **One stack only.** A second, hand-built software stack is not allowed. The Docker test image
  (`support/simulation/slurm-docker/Dockerfile`) pins torch 2.5.1 CPU the same way.

### 3. Storage

> **In simple words.** Nothing here assumes a cloud. "The shared store" is whatever the site has that every node
> can reach: a shared file system on bare metal (NFS, Lustre, GPFS, CephFS), or an S3-compatible object store
> (self-hosted, or a cloud's). The code picks it from one setting, `V5_REMOTE_ROOT`, and the drills run on both.

| Data | Where | Rule |
|---|---|---|
| Training shards | the shared store → **local NVMe**, prefetched ahead of use | the next shard is copied while the current one trains (S6). No training read goes to the shared store |
| Checkpoints | local NVMe → the shared store | ADR 0001 |
| Code, configs, small shared files | the image (or the shared file system) | never on the training read path |
| Job logs, events, exit notes | node-local `/var/log/v5/{logs,events,runs}` → shipped by Team 08's agent to the shared store | in Docker `/var/log/v5` is a link to the shared volume, which plays the shipped copy |
| Crash-loop count | one file `crashes.json` in the run's folder of the shared store, read and rewritten whole | not a file on a node |

**The shared store** (`V5_REMOTE_ROOT`):
- **a folder on a shared file system** (`/shared/ckpt`, the default): the bare-metal case. Writes go to a
  temporary name and are renamed; fencing uses an exclusive-create lock file (ADR 0001 §2).
- **an S3-compatible object store** (`s3://bucket/prefix`): optional, for sites without a shared file system.

Nothing a job needs on its next node may live on a node: state that must survive a move goes to the shared store
through `ckpt/store.py` (checkpoints, `latest.json`, `commits.jsonl`, `crashes.json`), everything else is a
node-local file the log agent ships. Week 1 review found the first draft broke this rule: the crash counter was an
appended file on a node-local disk, which restarts from zero on every new node (so the cap never fires), and an
object store cannot append at all. The job log used `--open-mode=append` for the same reason. Both moved.
slurmctld's `StateSaveLocation` (§1) also needs a folder both controllers see; no job touches it. Keep the shared
store close to the nodes (same site or zone), so copies do not cross a paid or slow network link.

### 4. Accounts, QOS and budgets (`slurmdbd`, `slurm/setup_accounts.sh`)

> **In simple words.** Every job is charged to an account. The main run's account outranks everyone and may
> take nodes from team jobs. Teams share the rest fairly, none can grab more than its GPU share, each job has a
> time limit (longer work requeues itself), and each team has a GPU-hour budget that Slurm enforces.

```text
root
├── mainrun            QOS=mainrun   (Priority 1000, Preempt=normal, no walltime cap)
└── teams              QOS=normal    (Priority 10, GraceTime=60 s, PreemptMode=REQUEUE, MaxWall 24 h,
    │                                  MaxTRESPerJob=gres/gpu=<share>, MaxSubmitJobsPerAccount 50, DenyOnLimit)
    │                  QOS=debug     (Priority 100, 30 min, 1 GPU, 1 running + 2 queued per user, DenyOnLimit)
    ├── data ├── tokenizer ├── ke2 ├── arch ├── perf ├── infra ├── monitoring ├── eval ├── posttrain ├── release ├── quant
```

- `PriorityType=priority/multifactor`, fair-share across the children of `teams`.
- `PreemptType=preempt/qos`, `PreemptMode=REQUEUE`: a preempted team job gets SIGTERM, has `GraceTime` to
  save, and goes back to the queue.
- `AccountingStorageEnforce=associations,limits,qos`: a job with no valid account is rejected.
- `GrpTRES=node=<cap>,gres/gpu=<share>` per team account (`V5_NODE_CAP`, `V5_TEAM_GPUS`): on cloud nodes 2 nodes and
  16 GPUs; on the shared node, TSAI's GPU share per team (millermuttu's GPU shares, team 07). A job over the share
  waits with `AssocGrpGRES`.
- **Per-job limits** on the team QOS (uz9ai's queue design, team 07): `MaxWall`, `MaxTRESPerJob`, a cap on queued
  jobs per team. `Flags=DenyOnLimit`: a job that breaks a per-job limit is **refused at submit** with the reason
  (`QOSMaxGRESPerJob`, `QOSMaxWallDurationPerJobLimit`, `QOSMaxSubmitJobPerUserLimit`), instead of pending forever.
- **`debug` QOS** instead of a debug partition (uz9ai's ADR-09): one quick 1-GPU job per user ahead of the queue,
  on the team's own nodes; the main run may preempt it.
- **Time limit with self-requeue** for team jobs (uz9ai's ADR-05): `--time` + `--signal=B:USR1@<lead>`, lead ≥
  2 × the save time + 60 s. The warning reaches only the batch shell (`B:`); the wrapper passes it to the
  trainers through `srun`; they save and exit 75; Slurm requeues the job with the same id. Long work runs in
  segments and loses nothing. The main run keeps no time limit.
- **Launch shape:** `srun` starts one trainer per GPU directly, with no launcher in between (uz9ai's ADR-10
  "alternative b"). uz9ai checked in DeepSpeed's source that the `deepspeed` launcher dies on SIGUSR1 and kills all
  ranks when one exits non-zero, which would break both the save-on-signal and the exit-75 contract. Our
  DeepSpeed test trainer (`train.py --deepspeed`, tests T18–T22) runs `deepspeed.initialize` from Slurm's
  variables, no launcher.
- **`GrpTRESMins` budget** per account, alerts at 50 / 75 / 90% (Q-15), hard stop at 100%.
  `AccountingStorageEnforce=associations,limits,qos,safe`: with **`safe`** a job starts only if it can finish
  inside what is left of the budget (its CPUs/GPUs × `--time`). Without it Slurm only stops a team once the
  budget is already used, so the last job overspends (found by the budget drill in run 16; `safe` is in uz9ai's
  design). A job that could never fit is refused at submit (`DenyOnLimit`, `AssocGrpCPUMinutesLimit`).
- **Default time per partition:** `eval` 1 h, `debug` 10 min, `cpu` 1 h. A job without `--time` otherwise gets the
  QOS `MaxWall` (24 h), above those partitions' `MaxTime`, and pends forever (`PartitionTimeLimit`, run 15).
  `gpu` has none: team jobs there get the QOS `MaxWall`, the main run no limit.
- **Order matters in `setup_accounts.sh`:** the QOS that `mainrun` preempts (`normal`, `debug`) are created
  before `mainrun`'s `Preempt` list is set. sacctmgr rejects the whole list if one name is unknown, and the main
  run then waits for free nodes instead of preempting (run 15). The script checks the list and stops if it is
  wrong; the `accounts` drill checks it too.
- **Capacity calendar:** each week's GPU-hours per team, including Team 05's ladder and the dry runs, agreed
  with the lead.

### 5. Restart contract

> **In simple words.** If the main run stops for any reason, Slurm puts it back in the queue and it starts
> again from the last checkpoint, by itself. Only two cases wait for a person: a NaN, and a job that keeps
> crashing (3 times in 30 minutes), because restarting those just burns money.

- `slurm/mainrun.sbatch`: `--requeue --open-mode=append --exclusive`. The same script for every restart; it
  always resumes from `latest.json`. Rollback passes `TRAIN_EXTRA="--from-step K --skip N --branch B"`.
- `slurm.conf`: `JobRequeue=1`, **`RequeueExit=75`**, **`RequeueExitHold=78`**, `MaxBatchRequeue=1000`.
- `queue/job_queue.py` (the wrapper) maps every trainer outcome to 0, 75 or 78 (ADR 0001 §6), applies the
  **crash-loop cap** (3 crashes in 30 min → 78), and emits `job.started / ended / requeued / held`. The crash
  times live in `crashes.json` next to the checkpoints in S3, so the count survives a move to any node. If S3
  cannot be reached the crash is retried as usual and `job.crash_ledger_unavailable` says the cap is not counting.
  (`SLURM_RESTART_COUNT` alone cannot do this: preemptions and spot moves also raise it, and they are not crashes.)
- **Plain-words status** (added for monitoring): the trainer leaves an exit note with its cause; the wrapper
  writes "what happened / already done / what you do" (from `common/reasons.py`) into the Slurm job comment,
  the job log and the job events. A held job therefore says why and what to do in `squeue` itself, instead of
  only `SPECIAL_EXIT / JobHeldUser`. Tested in the simulation (drill `held_job_explains_itself`).
- **Signals.** The trainer treats SIGUSR1 and SIGTERM the same: save, wait for the commit, exit 75.
  - Preemption: Slurm sends SIGTERM, then SIGKILL after `GraceTime` (60 s) / `KillWait` (30 s).
  - Spot notice or health drain: `scancel --signal=USR1 <job>` from the node itself (ADR 0003).
  - Time limit (team jobs): `--signal=B:USR1@300` to the batch shell, passed on by the wrapper (above). The
    first draft put `--signal=USR1@120` on the main run; it has no time limit, so it stays without one.
- A node that stops answering for `SlurmdTimeout=30` s is marked DOWN and its job is requeued by Slurm.
- **Requeue delay.** Slurm holds every requeued job until the old job's launch credential has expired
  (`cred_expire` + 1 s, default ≈ 121 s). We set **`AuthInfo=cred_expire=60`**. The man page says the credential
  must also live "long enough to … run prolog", and our prolog budget is 30 s, so 60 s is twice the budget. Week 1
  used 30 s (≈ 52 s exit to running); the review pointed out that left no margin for a slow prolog. 60 s costs
  about 30 s more per restart: run 11 measured reschedule 90 s and MTTR 85 s (run 10: 57 s and 55 s). A first attempt forced an immediate restart with a controller epilog (≈ 4 s); run 7 of
  the simulation showed it sometimes starts the job while the old credential is still valid, and Slurm then kills
  it as "Job credential revoked" and marks it **FAILED**, losing the main run. That hack was removed.

### 6. Health and idle integration

- `HealthCheckProgram=slurm/healthcheck.sh` every `HealthCheckInterval` (30 s in Docker; the main-run value is
  set from its measured cost, ADR 0003). Slurm ignores this program's exit code, so the check drains the node
  itself on `fail` (`scontrol update state=drain`) and sends its jobs SIGUSR1.
- `Prolog=slurm/prolog.sh` runs the quick checks at allocation (`PrologFlags=Alloc`). It exits non-zero only on
  `fail`; Slurm then drains the node and requeues the job (`SchedulerParameters=nohold_on_prolog_fail`).
- `queue/job_queue.py spot-watch` on every node polls the instance metadata service for a spot notice (a file in Docker).

### 7. Access and secrets

- **No static cloud keys anywhere**, and none in git (gitleaks before every push; pr-guard also checks).
- Nodes use **instance roles**:

| Role | Can |
|---|---|
| training | read data; write (not delete) checkpoints |
| eval | read checkpoints only |
| retention job | delete non-protected checkpoints (the only delete permission) |

- Students never get SSH or cloud keys. The instructor's submit system calls `sbatch` with a team account through
  one service user (`svc` in Docker).
- Admin access uses the cloud session manager, not an open port 22. The database password lives in the cloud secrets store
  (the Docker file's `simonly` value is for the local container only).

### 8. Event schema and time (shared by all ADRs)

- Every event is one JSON line `{schema, time, host, run_id, job_id, event, ...}`, `time` in UTC ISO-8601
  (`common/events.py`). Each process writes its own file, so writers never interleave.
- Events: `checkpoint.started / committed / failed / backpressure / retention`, `restore.done / failed / fatal`,
  `export.done / failed`, `train.started / step / stop_requested / watchdog / nonfinite / exit`,
  `job.started / ended / requeued / held / signal / signalled / rejected`, `node.drained / resumed / spot_notice`,
  `health.report`, and in the test `drill.injected`.
- chrony runs on every node (the cloud's time service); the health check reports the offset (Q-17).

### 9. Goodput accounting

> **In simple words.** We split every second of the main run into "trained the model" and named kinds of
> waste, and count each in node-hours. Then we know where the GPU time went.

| Bucket | Source |
|---|---|
| productive training (kept steps) | the rest of the wall clock |
| checkpoint stall | `checkpoint.committed.stall_s` (+ backpressure) |
| lost work (steps redone) | step at fault − restored step, × step time |
| detection (fault → job ends) | fault time → `job.ended` |
| reschedule (job end → job running) | `job.ended` → `job.started` |
| restore (job start → first productive step) | `job.started` → first `train.step` |

```text
goodput = productive / wall-clock
planning model:  waste ≈ stall/interval + (interval/2 + MTTR) / MTBF
```

`metrics/evaluate.py` rebuilds one **incident record** per interruption from the events:
`{kind, cause_class, t_fault, detect_s, reschedule_s, restore_s, mttr_s, step_at_fault, restored_step,
lost_steps, lost_s, human_action}`. `cause_class` uses the Llama 3 / S15 taxonomy. MTBF, MTTR and the paper's
failure table come from these records only. Team 08 stores and displays them.

### 10. Dry runs and drills (Team 07 runs both)

Each dry run, and the Docker simulation, runs these drills, timed and recorded as incidents:

| Drill | How | Expected |
|---|---|---|
| preemption | team jobs on all GPU nodes, then submit the main run | team jobs save on SIGTERM and requeue; main run starts |
| kill | `kill -9` one training process | job requeued; resumes from the last commit |
| SIGUSR1 | `scancel --signal=USR1` | emergency save; 0 steps lost |
| spot notice | notice on one node | node drained; save; job moves to the spare |
| health fail | forced `fail` on one node | node drained by the health check; save; job moves to the spare |
| hang | `SIGSTOP` one rank | step watchdog exits 75; job restarts |
| node loss | stop a node's container (instance) | Slurm marks it DOWN; job requeued on the remaining nodes + spare |
| NaN | NaN at a set step | no save; exit 78; held |
| rollback + smaller world | `--from-step --skip 5 --branch b1` on 1 node instead of 2 | restored, resharded, branch b1; run completes |
| crash loop | a job that crashes at step 3 | requeued twice, then held |
| budget | 2 CPU-minute budget: a job asking 240 CPU-minutes; then one that fits; then another | the big one refused at submit (`AssocGrpCPUMinutesLimit`); the next waits with `AssocGrpCPUMinutesLimit` |
| limits (uz9ai's T05–T11) | users alice (arch), bob (perf), carol (none) | wrong account and no account refused; third job of a full GPU share waits `AssocGrpGRES`; another user's `scancel` refused; 6 GPUs per job and `--time=25:00:00` refused at submit (`QOSMaxGRESPerJob`, `QOSMaxWallDurationPerJobLimit`); debug QOS: second job `QOSMaxJobsPerUserLimit`, third refused, 2 GPUs refused |
| time limit | team job `--time=00:02:00 --signal=B:USR1@60` | warning → save → exit 75 → requeued with the same id (`Restarts=1`) → resumed at the saved step, 0 lost |
| health fakes (ADR 0003) | fake `nvidia-smi`/`dmesg`; planted hot GPU, ECC, row-remap failure, NVLink down, Xid 79, Xid 94 | GPU checks run and pass when healthy; each fault fails the right check; 94 only warns; NVLink down drained by the periodic check |
| split brain (ADR 0001) | a second attempt claims the run while the main run trains | the old attempt's commit is refused, it is held (`FencedError`), the pointer does not move; resubmit resumes |
| fair share | heavy vs unused account | heavy account's fair-share factor is lower |
| retention, export | retention job; safetensors export on the eval partition | no protected checkpoint deleted; probe bit-equal |
| GPU allocation | main run on 2 nodes × 2 GPUs; a job asking 3 GPUs per node | `gres/gpu=4` allocated; the over-ask refused at submit |
| kill during save | slow the upload, kill all ranks while a save is in flight | the half-uploaded checkpoint is never used |
| kill during restore | slow the restore, kill while restoring | next attempt restores the same checkpoint cleanly |
| two nodes down | force `fail` on both main-run nodes (one spare) | main run waits (pending), no crash loop; recovers when nodes return |
| controller failover | stop the primary `slurmctld` | backup in control, training continues, new jobs accepted, primary returns |
| DB backup | dump and test-restore `slurm_acct_db` | same table count in the restored copy |
| loss spike | loss × 10 for 5 steps (no NaN) | no save during the spike; exit 78; held; rollback completes |
| repeats | kill and SIGUSR1 three times each | MTTR p50 / p95 per fault type |
| live alerts | `metrics/watch.py` runs during the whole simulation | HIGH alerts fire for the spot notice, the held run and the NaN |

### 11. Operations (added after the week-1 review)

> **In simple words.** How we change things without breaking the run, where logs live, how someone gets woken
> up, and what is still only on paper.

- **Upgrades** (image, driver, Slurm) never happen in the middle of a run segment. Order: build and test the new
  image in CI → run the checkpoint tests on one drained node → wait for a checkpoint commit → `scancel
  --signal=USR1` the main run (emergency save, exit 75) → roll the nodes → requeue with
  `TRAIN_EXTRA=--allow-env-change`, which is logged in the restore event. Slurm itself: `slurmdbd` first, then
  `slurmctld`, then `slurmd`, as Slurm's upgrade guide requires.
- **Logs:** job stdout/stderr (`/var/log/v5/logs`) and events (`/var/log/v5/events`) are node-local files,
  shipped by Team 08's agent to S3 (`s3://…/logs/`, 90 days Standard, then the archive tier). A requeue on another node
  starts a new file there; the agent's S3 copy holds them all. In Docker `/var/log/v5` links to the shared volume.
- **Paging path:** `metrics/watch.py` runs on the head node, recomputes the catalog every 30 s, and on a new
  severity writes `alert.fired` and posts to `V5_ALERT_WEBHOOK` (Team 08's pager or a chat webhook). HIGH pages
  the on-call person. Tested in the simulation (alerts fired live for the drills).
- **Starting the stack:** `launch/launch.sh` starts munge, slurmdbd, the DB backup with a test restore, the
  controllers, the accounts, slurmd, a full health check on every node (a failing node is drained), the services,
  the checkpoint-store probe and the main run, in that order, checking each step and stopping on the first
  failure (`--from <step>` continues). Tested against the Docker cluster; the `services` step and the SSH
  transport need real hosts.
- **Evidence:** every drill writes `support/simulation/results/evidence/<drill>.log` (each command, its exit code
  and output, and the recorded result), so a reviewer can check a claim without rerunning it (uz9ai's evidence
  folders). `run_sim.py --smoke` runs accounts, limits, health fakes, preemption and one kill + restore in about
  3 minutes (millermuttu's quick test idea).
- **Security, designed but not yet tested in the cloud:** munge key from the cloud secrets store at boot; cloud roles per job type
  (§7); the submit service; session-manager-only admin access. These need the cloud account (week 2).

### 12. Metrics

All queue metrics with LOW / MEDIUM / HIGH thresholds are Q-01 … Q-21 in `metrics/catalog.yaml`
([metrics_catalog.md](../support/docs/metrics_catalog.md)). The ones that page immediately (HIGH):

| ID | Metric | HIGH when |
|---|---|---|
| Q-01 | Main run not running | pending ≥ 10 min |
| Q-02 | Main run held | any |
| Q-03 | Reschedule latency | ≥ 10 min |
| Q-05 | Interruptions | ≥ 10 per day |
| Q-06 | Idle GPU node-hours | ≥ 4 per day |
| Q-07 | Allocated but not stepping | ≥ 15 min |
| Q-09 | Drained nodes | ≥ 3 |
| Q-10 | Node replacement time | ≥ 15 min |
| Q-11 | slurmctld down | ≥ 60 s |
| Q-15 | Account budget used | ≥ 90% |
| Q-17 | Clock offset | ≥ 500 ms |
| Q-19 | Goodput | ≤ 80% |
| Q-20 | MTTR | ≥ 60 min |

Targets: goodput ≥ 90%, MTTR ≤ 15 min, reschedule ≤ 2 min with the spare (measured ≈ 90 s, run 11), node replacement ≤ 5 min,
human interventions ≈ 0 (Llama 3: 3 of 466).

## Consequences

Good:

- The main run cannot be starved, the rest is shared fairly and within budget, and idle nodes are stopped.
- Restarts are automatic, use one script, and lose ≈ 0 work when there is a warning signal.
- One pinned stack; training never reads from S3 directly.
- Goodput, MTTR and node-hours come from records, so the paper's failure table is factual.

Bad and accepted:

- **Ops load:** we operate slurmctld, slurmdbd and MariaDB, plus image CI.
- **Container cost:** Pyxis/Enroot adds a component, and the first image pull on a node costs time (cache on NVMe, Q-18).
- **Preemption cost:** preempted team jobs lose the work since their last save (Q-14).
- **Spare node cost:** a hot spare costs one node of GPU-hours; it runs preemptible work to recover some of that.
- **Local disk only:** with no shared FS, a node's local checkpoint copy is lost with the node; S3 is the copy that counts.
- **Docker is not the cloud nodes:** no GPUs, no fast network, no Pyxis, power saving or cgroup enforcement in the test (§Validation).

## Validation

`support/simulation/run_sim.py` starts `support/simulation/slurm-docker/` (MariaDB, slurmdbd, slurmctld, 4 compute containers) with the
production `slurm.conf`, runs every drill in §10, then `metrics/evaluate.py`. Results are in
`support/simulation/results/` (`drills.json`, `report.md`, `metrics.json`, `alerts.json`); see [sim_results.md](../support/docs/sim_results.md).

**Result (run 9, 2026-10-28): 31 of 31 drills pass in 22 minutes** (run 8: 30 of 30). MTTR per fault type (2 nodes × 2 ranks,
tiny model, checkpoints on the S3 emulator):

| Drill | MTTR p50 (n) | Steps lost |
|---|---|---|
| kill -9 | 50 s (3) | 24–45 (since last commit) |
| SIGUSR1 | 58 s (3) | 0 (emergency save) |
| kill during save / during restore | 50 s / 112 s | since previous commit / 0 extra |
| spot notice | 57 s | 0 |
| health fail | 60 s | 0 |
| two nodes down (after repair) | 58 s | — |
| hang (SIGSTOP) | 56 s (watchdog 20 s) | 44 |
| node loss | 88 s (`SlurmdTimeout` 30 s) | 24 |
| controller failover | backup in control after 82 s; training never stopped | 0 |

Most of each MTTR is Slurm's requeue wait (`cred_expire=60`, §5; run 11: MTTR 85 s, 31 of 31 drills; run 14: 33 of 33, adding the split-brain drills).

**Latest (2026-10-30, after the cloud-agnostic changes): 44 of 44 drills pass with checkpoints on a shared folder
(the bare-metal case, [sim_results_folder.md](../support/docs/sim_results_folder.md)) and 44 of 44 on an
S3-compatible store ([sim_results.md](../support/docs/sim_results.md)), about 34 minutes each** (runs 17 and 19: the same before), adding the limit, health-fake and time-limit
drills of the merge with millermuttu's and uz9ai's work; smoke run 13 of 13 in 193 s. Runs 15 and 16 found three
problems the merge itself had introduced, all fixed above: `mainrun` no longer preempting (QOS order), jobs without
`--time` pending forever (default times), and budgets that overspend by one job (`safe`).
The table above is run 9 (`cred_expire=30`); with 60 s each restart is about 30 s longer. Run 3 measured 3–57 s with an
immediate-restart hack, but run 7 showed that hack can lose the main run, so it was removed. Goodput in the
simulation is low only because a fault is injected about every minute; ADR 0004 projects the measured
durations onto real failure rates.

Differences from the cloud, by design: CPU instead of GPU (gloo instead of NCCL), `proctrack/linuxproc` and
`task/none` instead of cgroup enforcement (`cgroup.conf` uses `IgnoreSystemd=yes` because there is no
systemd), no Pyxis (the image already holds the code), no `State=CLOUD` power saving, one controller.

## Open points

- GPU type and count; reserved capacity booking or on-demand.
- The cloud account, cloud roles and S3 bucket names.
- The submit system's contract: does it call `sbatch` with an account?
- The on-call rota (who acts on a HIGH alert at 4 a.m.).
- The capacity calendar for weeks 2–4.
- Automatic shrink to fewer nodes (decided against for now, §1); revisit if spares prove too expensive.
- Security items in §11, which need the cloud account.
