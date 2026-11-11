# Team 07-infrastructure: checkpoint, job queue and node health for the V5 main run

What we deliver: the infrastructure that runs the V5 main run on **GPU nodes scheduled by Slurm**, on bare metal
or any cloud: nothing in it depends on a provider (the TSAI shared GPU node, or a self-managed fleet). It is designed so that **money already spent on training is never
lost**. It comes with LOW / MEDIUM / HIGH metrics that tell people what to do. Every decision is explained in
simple words. Everything here was proven in a Docker copy of the Slurm cluster (**44 of 44 drills**, both with checkpoints on a shared folder, as on bare metal, and on an S3-compatible store); that
evidence is in the optional [`support/`](support/README.md) folder.

> **In simple words.** Training costs money every hour, and at this scale machines break every few hours.
> We **save** the training often and prove every saved copy is exact (checkpoint). We let **Slurm** restart the
> job from that copy by itself (queue). We take **broken GPUs** out before they waste paid hours (health). And
> we tell a person **what to do** only when the system stopped on purpose (monitoring).

**New here?** Read the [team briefing](TEAM_BRIEFING.md) (every decision and why, in plain words), then the
[user guide](USER_GUIDE.md) (how the system works, and what each team does with it).

## What is here

Every folder is a topic folder (`teams/07-infrastructure/<topic>/<file>`), as the lab's pr-guard requires.

```text
teams/07-infrastructure/
├── README.md        ← you are here
├── TEAM_BRIEFING.md every decision and why, in plain words (start here)
├── USER_GUIDE.md    how the system works and how each team uses it
├── adr/             the 4 decisions, each with an "In simple words" box
├── ckpt/            checkpoint      ckpt.py (save, commit, fencing, restore checks, retention, export), ds_ckpt.py (DeepSpeed), store.py (shared file system or S3-compatible store)
├── queue/           job queue       job_queue.py (job wrapper, exit codes, crash loop, spot watcher, drain, status)
├── slurm/           Slurm setup     slurm.conf, node files, job scripts, prolog/epilog/health hooks, accounts, DB backup, systemd units
├── health/          node health     health_check.py, xid_scan.py, allreduce_test.py (4 collectives), thresholds.yaml
├── metrics/         monitoring      catalog.yaml (74 metrics), watch.py (live alerts), evaluate.py, explain.py, prices.yaml (cost inputs, no prices)
├── common/          shared          events.py (event format), reasons.py (every code → plain words + what to do)
├── launch/          operations      launch.sh (start everything in order, checked), cluster.env.example
└── support/         optional: tests, the Docker Slurm simulation and its results, the test trainer, Kaggle GPU checks,
                     the cost model, reviews and merge plans
```

| Area | Decision | Read | Main file |
|---|---|---|---|
| Checkpoint | [ADR 0001](adr/0001-checkpoint-format-and-commit.md) | [ckpt/README.md](ckpt/README.md) | `ckpt/ckpt.py` |
| Job queue | [ADR 0002](adr/0002-job-queue-slurm.md) | [queue/README.md](queue/README.md) | `queue/job_queue.py`, `slurm/slurm.conf` |
| Node health | [ADR 0003](adr/0003-node-health-checks.md) | [health/README.md](health/README.md) | `health/health_check.py` |
| Cost and monitoring | [ADR 0004](adr/0004-cost-model-and-alerting.md) | [metrics/README.md](metrics/README.md) | `metrics/catalog.yaml`, `metrics/watch.py` |

Reading order: [USER_GUIDE.md](USER_GUIDE.md) → [adr/README.md](adr/README.md) → the README of the area you care
about → for the evidence, [sim_results.md](support/docs/sim_results.md) and
[review_week1.md](support/docs/review_week1.md).

The code that runs on the cluster never needs `support/`. The one link between them is a default: the job wrapper
starts the test trainer from `support/simulation/trainer/` unless `V5_TRAIN_SCRIPT` names the real one.

## The decisions in one table

| Question | Decision | Why, in simple words |
|---|---|---|
| How do we save? | PyTorch DCP shards (or DeepSpeed ZeRO) + our manifest; the manifest is written **last**, then `latest.json` with a conditional write | a half-written save can never be picked; an old copy of the run can never move the pointer back |
| How do we know a restore is right? | 4 proofs: state digest, **bit-equal** probe loss, next-batch hash, frozen hashes | catches last year's silent misload |
| How often? | every 30 min (Young's formula, capped); emergency save on any warning | warnings lose ≈ 0 work, the rest ≤ one interval |
| Who schedules? | **Slurm**; the same `slurm.conf` in Docker | we test exactly what we run |
| How does it restart? | exit **75** = Slurm requeues; **78** = hold for a person; 3 crashes in 30 min = hold | no human for normal faults, no money burnt in loops |
| Who gets the GPUs? | main run first (preempts); teams by fair share, a GPU share each, per-job limits, GPU-hour budgets as a hard stop | the main run cannot starve; no team grabs everything |
| How do we find broken GPUs? | checks before every job and every 30 s (GPUs, ECC, NVLink, Xid, 4 collectives); drain + save + move | a bad GPU costs seconds, not a crash |
| How does a person know what to do? | every job, alert and drained node says what happened, what was done, what to do | `python metrics/explain.py <anything>` |

## Starting production: `launch/launch.sh`

> **In simple words.** A cluster must start in a fixed order: logins, the accounting database, the
> controllers, the accounts, the GPU nodes. Then we prove the nodes are healthy and the checkpoint store is
> safe, and only then spend GPU hours on the main run. `launch.sh` does exactly that, one step at a time. It
> waits for each step's check and stops on the first failure, saying which step failed and why. Every step is
> safe to run twice, so after a fix you go on with `--from <step>`.

```bash
cp launch/cluster.env.example /etc/v5/cluster.env     # hosts, store, run id (no secrets)
launch/launch.sh --list                               # the steps
launch/launch.sh --dry-run                            # what would run where, nothing changed
launch/launch.sh                                      # start everything
launch/launch.sh --from health                        # continue after fixing a failed step
```

| Step | What it proves before going on |
|---|---|
| preflight | settings complete, every host reachable, **the same code on every host** (the code goes into each checkpoint, so a mix would hold the run later) |
| munge | `munged` everywhere, and every host accepts the controller's credential (one key, clocks in step) |
| slurmdbd | accounting daemon answering |
| dbbackup | today's DB dump **and a test restore** of it (a backup counts only after a restore) |
| slurmctld | primary and backup controller UP (`scontrol ping`) |
| accounts | `setup_accounts.sh`; the submit user has the `mainrun` association; `mainrun` preempts the team QOS |
| slurmd | every GPU node registered (a node drained on purpose stays drained) |
| health | `health_check.py --mode full` on every node at once (GPUs, ECC, row remap, NVLink, Xid, NVMe, the four collectives); launch drains a failing node with reason `health: <checks>`; fewer healthy nodes than `V5_MIN_NODES` stops the launch |
| services | hot-spare timer and alert watcher on the controllers, spot watcher on every node (systemd units in `slurm/`) |
| store | `ckpt.py probe-store`: write, read, and **a stale write refused**. Fencing (ADR 0001 §3) depends on it; a store that does not refuse a stale write stops the launch here |
| submit | main run submitted unless already queued; it claimed its epoch, restored and started |
| status | `job_queue.py status` |

Tested against the Docker cluster (`V5_EXEC="docker exec -i slurm-docker-%h-1"`, `V5_SKIP=services` because the
containers have no systemd): a full launch; a broken node drained while the launch goes on; too few healthy
nodes stops it; a second launch does not submit the run twice; a finished run is reported, not waited for.
`probe-store` against an emulator that ignores `If-Match` (moto 5.0.28) fails, as it must.

## For monitoring and on-call

```bash
python queue/job_queue.py status       # every job and drained node, in plain words
python metrics/explain.py 78           # or 137, loss_spike, CK-05, v5:xid, JobHeldUser, FencedError ...
```

| Exit | Means | You do |
|---|---|---|
| 0 | done | nothing |
| 75 | saved (or crashed once), restarts by itself in ~90 s | nothing |
| 78 | **held on purpose**: retrying would waste GPU hours | read the job comment; it says what to do |

Full guide: [USER_GUIDE.md §5](USER_GUIDE.md#5-on-call-what-to-do-when) and [metrics/README.md](metrics/README.md).

## Lab rules for this folder

Put your work in a **topic folder**: `teams/07-infrastructure/<topic>/<file>`, for example
`teams/07-infrastructure/harness/run.py`. Team documents named in the week plan (for example `benchmarks_v1.md`)
may sit directly in the team folder. The team lead decides the topic names. Do not make personal folders. Do not
make new folders under `teams/`. Open a pull request; the lead reviews and merges it. The pr-guard check must pass.

## Paths in this folder

Commands in these READMEs run from `teams/07-infrastructure/` (for example `python ckpt/ckpt.py list`). On the
cluster this folder is mounted at `/opt/v5`, so `slurm.conf` and the job scripts use `/opt/v5/<topic>/...`.

## Not done yet (honest list)

- Real GPUs: the Kaggle (2 GPUs) run is ready, not yet run; the shared node arrives on 1 Nov.
- The checkpoint store is a shared file system (bare metal, the default) or any S3-compatible store; both run the
  full drill set in Docker. Neither has met the real store yet: `ckpt.py probe-store` checks it at every launch.
- Sharded state: the digest is tested on real DTensor shards (CPU) and FSDP2 save/reshard/restore runs on
  Kaggle (2 GPUs) (T16); expert parallel needs Team 05's model; the real data loader must pass
  `ckpt/loader_contract.py` (Teams 01/02).
- Merging uz9ai's installer (`cluster.toml`) is phase B of [the merge plan](support/docs/merge_execution_plan.md).
- The week-1 review findings and their fixes: [review_week1.md §2b](support/docs/review_week1.md).
- Cost results are in node-hours; the price of a node-hour is a run-time input (none in the repo). The on-call rota and alert channel need people.
