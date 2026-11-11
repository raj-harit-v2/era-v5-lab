# Team 07 merged submission plan: pradeep-kumar-gs, millermuttu, uz9ai

One page to decide what goes into the single Team 07 submission. Sources:

| Who | Repo | State reviewed | Built for |
|---|---|---|---|
| **P** pradeep-kumar-gs | `pradeep-kumar-gs/era-v5-lab`, branch `infrastructure` | `7b722f2` (30 Oct) | Docker Slurm sim of an cloud fleet; checkpoint + queue + health + monitoring |
| **M** millermuttu | `millermuttu/era-v5-lab`, branch `07-infrastructure` | `c6e38a3` (28 Oct) | Docker Slurm + the shared GPU node; checkpoint, health, queue |
| **X** uz9ai | `uz9ai/queue`, branch `main` | 28 Oct | real cloud (controller + train + eval nodes); queue, installer, trainer |

**Target agreed: the TSAI shared GPU node(s)** from 1 Nov (every Slurm daemon on the node, S3 keys held by
TSAI). The detailed reviews behind this page: [merge_plan.md](merge_plan.md)
(P vs M, all areas) and [queue_review_max.md](queue_review_max.md) (X, queue in depth). Where they differ,
**this page wins**.

> **In simple words.** Each of us is strongest in a different place. pradeep-kumar-gs: the checkpoint, what happens
> after a failure, and monitoring, all proven in a Docker cluster. millermuttu: a small, clear setup for the one
> shared node we will actually get, and the best network test. uz9ai: the most careful real-machine install, with
> one checked config file, tight limits and test evidence, and the only one run on real GPUs. The merged
> submission takes the best part of each and leaves cloud-fleet extras for later.

## Evidence behind each source

| | Ran where | Proof |
|---|---|---|
| P | laptop + Docker Slurm (CPU) | 56 unit tests pass (2 GPU-only skipped); **33/33** Docker drills (run 14); Kaggle GPU package ready, not run |
| M | Docker Slurm (CPU), one GPU by hand | his `test.sh` (13 checks, ~90 s) and `ckpt.py` self-test; **not re-run here** (running downloaded code is blocked on this machine) |
| X | **real cloud nodes, 1 GPU per node** | screenshot: T12/T12b self-requeue PASS on `train-01` (3 requeues each); training/eval on a 1-GPU node; T01–T11 result not in repo; **not re-run here** |

## What to keep, area by area

**Keep** names the source for each piece. "+" means add the other's piece to it.

### 1. Checkpoint

| Piece | Keep | Why |
|---|---|---|
| Save format and commit | **P**: DCP shards (+ DeepSpeed ZeRO 1/2/3), sums per rank, re-check every object, MANIFEST last, conditional `latest.json` | M's rename-on-commit and X's `COMPLETE` marker work on one disk only; P's works on S3 |
| Two live copies of a run | **P**: epoch fencing (T24–T26, drill `split_brain`) | neither M nor X handles it |
| Damaged newest checkpoint | **P** (sha256 per object, fall back to previous commit); X does the same in `train.py` | M has no checksums: a damaged newest checkpoint stops the run |
| Restore proofs | **P** (state digest, probe-loss bits, next-batch hash, frozen fingerprints) **+ M's frozen check at save** (refuse to save if a frozen part changed since the previous checkpoint) | catches the error when it happens, not at the next restore |
| What the environment check covers | **P + M's `embedding_policy_id`** | Team 04's KE2 policy must match |
| RNG, data position | **P** (all RNGs per rank, one global ledger offset) **+ M's shard `manifest` sha** in the data position | M gives every new rank rank 0's RNG after a resize; X is single-GPU |
| Async save | **P** (with its own copy of CPU tensors, T27) | only P has it |
| Durability on disk | **P + X's `fsync`** of the per-rank files before the manifest | X and M both noted the power-cut case |
| Retention | **P** (own job/role, never deletes protected) | M and X delete from inside the training job |
| Export for Teams 09/12 | **P** (`safetensors`, DeepSpeed `zero_to_fp32`, checked) | |
| ADR text | **P's ADR 0001 + M's** "when is the loss bit-equal" list, Young/Daly with our lab's 12.9 h MTBF, 30B sizing (provisional) | |

### 2. Queue and Slurm

| Piece | Keep | Why |
|---|---|---|
| Single source of truth | **X**: `cluster.toml` + `team7config` validation, installed on every host, readable by training code | one checked file instead of P's spread of conf/env/scripts |
| Installing a host | **X**: `install.sh validate/render/--dry-run/controller/node/apply/verify`, safe to rerun, `apply` never deletes | P and M have no installer; **needs a single-host mode** for the shared node |
| Single-node layout | **M**: `node/` files (every daemon on one host, cgroups on, `AutoDetect=nvml`), rendered from `cluster.toml` | X assumes separate controller/train/eval hosts |
| Config distribution | **X**: configless Slurm (`enable_configless`) | a node never runs a stale `slurm.conf` |
| Accounts and users | **X**'s reconcile code + **M**'s 12 team accounts with GPU shares (`GrpTRES=gres/gpu=N`) + real users with fixed UIDs | P's node cap (`node=2`) means nothing on one node |
| QOS limits | **X**: `MaxWall`, `MaxTRESPerJob`, `MaxJobsPA=1`, `MaxSubmitJobsPU`, `debug` QOS | P has none of these |
| Budgets, fair share, accounting | **P** (`GrpTRESMins` GPU-hour budgets, fair share, GPU-hours per team) + X's priority weights | |
| Main-run protection | **P**'s `mainrun` QoS with requeue preemption, **if the main run shares the node with team jobs** | X's no-preemption fits only separate nodes |
| Exit-code contract | **P**: 0 done, 75 requeue, 78 hold, 3 crashes in 30 min → hold, job comment in plain words | X: any crash = `FAILED`, no hold path; M: requeue on node loss only |
| Time limits | **X**: `--signal=B:USR1@<lead>` before `MaxWall`, self-requeue, `lead ≥ 2 × save + 60 s` | P runs the main run with no time limit |
| Launch shape | **P**: `srun` one task per GPU, trainer called directly (X's ADR-10 "alternative b"; P's DeepSpeed trainer runs this way) **+ X's ADR-10 text** as the reason **+ M's rendezvous id per restart** if torchrun is ever used | no launcher that dies on SIGUSR1, no PID files |
| Prolog / epilog / periodic health hooks | **P** (`PrologFlags=Alloc`, `nohold_on_prolog_fail`, scripts drain via `scontrol`) | X designed the same rules but left health off (`health/launch.sh --quick` does not exist) |
| Accounting DB backup | **P** (dump + **test restore**) + X's daily block-volume/state snapshot note | |
| Hot spare, spot watcher, controller failover, cloud cost | **park in `support/cloud/`** | no spare, spot or second host on one shared node |
| Secrets | **X**: munge key by hand or the cloud parameter store (encrypted), DB password generated on host, nothing secret in git | |
| Pinned training environment | **X**: `pyenv/pyproject.toml` + `uv.lock`, built before `slurmd` starts | P pins only the Docker image |
| Starting the stack | **P**: `launch.sh` (12 checked steps, store probe, submit), calling X's installer steps | X has `verify`; P adds order, health, store probe and main-run start |

### 3. Node health and network

| Piece | Keep | Why |
|---|---|---|
| Engine | **P**: `health_check.py` (modes prolog/periodic/full, JSON for Team 08, thresholds file, auto-drain, jobs save first) | M's and X's are shell/BAD-line only |
| GPU checks | **P + M's NVLink inactive-link check** | P sees NVLink only through DCGM |
| Collectives | **M**: all-reduce, reduce-scatter, all-gather, all-to-all, result check + busbw floor, inside P's JSON frame | P tests all-reduce only |
| DCGM | **P's rule** (`health -c` periodic, `diag` only in full / maintenance) + M's `DCGM_LEVEL` knob | diag loads the GPUs |
| Xid table | **P + M's 61, 62, 92, 140**; move **94** (contained ECC) to "restart the job, drain if it repeats" | both P and M wrongly treat 94 as fatal |
| Hang diagnosis | P's flight-recorder env **+ M's trace-file path and reading guide** | |
| Faking faults in Docker | **M**: fake `nvidia-smi` and `dmesg` with faults in `/run/fake/*` | the real scripts run unchanged |
| Operator checklist | **M's `TESTING.md`** (levels 1–3) | clearest week-2 checklist |

### 4. Monitoring and cost

**P only** (ADR 0004, 74 metrics, live alert watcher, `explain.py`, GPU-hours per team). Trim for one node:
cloud prices and the unmanaged-instance finder move to `support/cloud/`.

### 5. Tests and evidence

| Piece | Keep | Why |
|---|---|---|
| Acceptance list | **X**'s T01–T18 (accounts, refusals, every limit with its exact reason, cross-user cancel, self-requeue through the launcher, node failure, prolog/timer health, controller and DB restarts) | the most complete queue test plan |
| Evidence format | **X**: `evidence/<test>/` with commands, user, outputs, `sacct`/`scontrol`, `summary.md` | what the G7 review asks for |
| Failure drills | **P**: 33 Docker drills (kills, signals, kill during save/restore, split brain, NaN, spike, rollback, reshard, failover, DB restore, budget, retention, export, alerts) | |
| Fast smoke test | **M**: `test.sh`, ~90 s, incl. chained 2-node FSDP2 restart with bit-equal losses and weights | P's suites take 17–30 min |
| FSDP2 without GPUs | **M's finding**: torch 2.9+ runs FSDP2 on CPU; move the Docker image to the torch in X's `uv.lock` | P's T16 then runs in every drill, not only on Kaggle |
| Unit tests | **P** (T1–T27 and the store/health/cost/queue suites) | |
| GPU evidence | P's Kaggle package now; X's 1-GPU cloud runs; then the shared node | |

### 6. Design documents

ADR 0001 (checkpoint) **P + M's sections**; ADR 0002 (queue) **X's `queue_design.md` structure** (10 ADRs with
alternatives, test plan, admin sign-off) **with P's failure contract and M's single-node layout**; ADR 0003
(health) **P + M's collectives/NVLink/Xid changes**; ADR 0004 (cost and alerts) **P**, one-node version.

## Merged layout

> **Done differently (30 Oct):** for the PR to the lab repo, `submission/` was flattened: its folders are now topic
> folders directly under `teams/07-infrastructure/` (`launch.sh` in `launch/`). See the team [README](../../README.md).

```text
teams/07-infrastructure/
├── README.md                     one page: what is here, who wrote which part (provenance)
├── submission/                   what the instructor reviews; all of it runs on the shared node
│   ├── adr/                      0001 P+M · 0002 X layout with P+M content · 0003 P+M · 0004 P
│   ├── cluster/                  X: cluster.toml(.example), install.sh, installer/, team7config/, pyenv/ (uv.lock)
│   │                             + single-host mode; renders slurm.conf, node files (M), accounts, job templates
│   ├── launch.sh                 P: start order and checks, calls the installer's verify
│   ├── ckpt/                     P: ckpt.py, ds_ckpt.py, store.py, loader_contract.py (+ M's 3 additions, X's fsync)
│   ├── queue/                    P: job_queue.py (0/75/78, crash loop, drain, status) used by X's job templates
│   ├── slurm/                    P: prolog/epilog/healthcheck, mainrun/team job scripts (+ X's --signal), backup_db.sh
│   ├── health/                   P: health_check.py + M: 4 collectives, NVLink, Xid merge, TESTING.md
│   └── metrics/                  P: catalogue, watch.py, explain.py (one-node version)
└── support/
    ├── slurm-docker/             one Docker cluster: P's drills + M's test.sh + M's fake nvidia-smi/dmesg
    ├── tests/                    P's unit tests + X's T01–T18 runners (on real hosts and in Docker)
    ├── kaggle/                   GPU checks
    ├── cloud/                      parked: cloud site/nodes/gres files, keep-spare, spot-watch, failover, cloud cost
    └── docs/                     this plan, the two detailed reviews, sim results, G7 review response
```

## Work list (one order for all three)

| # | Task | Takes | Owner (suggested) | Size |
|---|---|---|---|---|
| W1 | Bring X's `cluster/` in; add a **single-host mode** (controller + node on the shared node) | X + M | uz9ai | M |
| W2 | Render M's `node/` files and M's team accounts with GPU shares from `cluster.toml`; configless | M → X | millermuttu + uz9ai | M |
| W3 | X's QOS limits and `--signal=B:USR1@<lead>` in P's job scripts; job templates call `job_queue.py` (0/75/78) | X ↔ P | uz9ai + pradeep-kumar-gs | S |
| W4 | `[health]` points at `health_check.py --mode prolog/periodic`; M's 4 collectives, NVLink check, Xid merge (94 → restart) | M → P | millermuttu | M |
| W5 | Checkpoint additions: M's frozen check at save, `embedding_policy_id`, shard `manifest`; X's `fsync` | M, X → P | pradeep-kumar-gs | S |
| W6 | Docker cluster: M's fake `nvidia-smi`/`dmesg`, M's `test.sh` as smoke test, image on X's `uv.lock` torch (FSDP2 on CPU) | M, X → P | pradeep-kumar-gs + millermuttu | M |
| W7 | Evidence folders for drills and smoke tests; port X's T01–T11 to the Docker cluster | X → P | uz9ai + pradeep-kumar-gs | M |
| W8 | Move cloud-only parts to `support/cloud/`; `launch.sh` defaults for one host | P | pradeep-kumar-gs | S |
| W9 | ADRs merged as in §6; one README with provenance; one PR under `teams/07-infrastructure/` | all | all | S |
| W10 | On the node (1 Nov): `install.sh` single-host, `launch.sh`, M's TESTING.md level 3, X's T01–T18 with evidence; Kaggle run for GPU checkpoint numbers | all | all | — |

Order: W1–W2 first (the shared node needs them on 1 Nov), then W3–W5 in parallel, then W6–W9, W10 on the node.

## Decisions the team must make

1. **OS on the shared node** (24.04 → Slurm 23.11, or 26.04 → 25.11). X pins 23.11 and refuses others; M
   tests 25.11 and says 23.11 cannot launch steps in Docker; P runs 23.11 in Docker with a cgroup workaround.
2. **Does the main run share the node with team jobs?** Yes → keep P's preemption QoS. No (node reserved in the
   main run's window) → X's no-preemption is enough.
3. **GPU share per team** (`GrpTRES=gres/gpu=N`) and `MaxWall` per QOS: TSAI sets them; placeholders until then.
4. **Crash policy:** P's "retry, hold after 3 in 30 min" or X's "every crash fails". Recommendation: P's.
5. **Launcher:** `srun` per rank (P) or the `deepspeed` launcher with PID-file forwarding (X). Recommendation:
   `srun` per rank; X's template stays documented as the alternative.
6. **Owners** for W1–W9 (suggested above).
