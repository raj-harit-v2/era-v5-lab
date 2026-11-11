# Merge execution plan: bringing the best of millermuttu and uz9ai into this repo

How we carry out [team07_merge_plan.md](team07_merge_plan.md) in this repo, step by step, and how each step is
proven. Written 30 Oct 2026, on `2adaf11`.

> **Layout note (30 Oct):** `submission/` was flattened into topic folders (`adr/`, `ckpt/`, `queue/`, `slurm/`,
> `health/`, `metrics/`, `common/`, `launch/`) for the PR to the lab repo; file names below follow the old layout.

> **In simple words.** We port the good ideas from millermuttu's and uz9ai's repos into our code one piece at a time.
> After each piece, a test must show it works, and at the end the whole Docker cluster simulation must pass
> again with the new drills added. Pieces that need a real machine (uz9ai's installer) or a team decision are
> listed separately, so nothing is claimed that was not run.

## Rules for every step

1. **Port, do not paste.** We re-write each idea in our code's shape (JSON health reports, events, exit
   codes), and credit the source in the file and in the provenance table below. Teammates' files are copied
   verbatim only with their agreement (Phase B).
2. **Each step lands with a test** (unit test or Docker drill) that fails without it.
3. **Nothing old breaks:** the full unit suite and the full drill set run at the end (Phase A gate).
4. Only `teams/07-infrastructure/` changes; pr-guard rules hold (no secrets, no data files, nothing > 5 MB).

## Phase A: in this repo now, proven in Docker

| Step | What | Source | Files | Proof |
|---|---|---|---|---|
| **A0** | `launch.sh` health step **drains** a node whose full check fails (today it only reports it; found while planning) | P bug | `launch/launch.sh` | `launch.sh --only health` with a planted fault: node `drain` in `sinfo` with reason `health:<check>` |
| **A1** | Collective test runs **all-reduce, reduce-scatter, all-gather, all-to-all**, each with an exact-value check and busbw; one JSON result per op | M `allreduce.py` | `health/allreduce_test.py`, `health/health_check.py` (`nccl_allreduce` → `nccl_<op>` checks), `thresholds.yaml` (`nccl.ops`) | unit: gloo on 2 and 3 ranks, all 4 ops pass; a forced wrong value fails |
| **A2** | **NVLink inactive-link** check (`nvidia-smi nvlink -s`) | M `gpu_health.sh` | `health/health_check.py` | unit with fixture: 1 inactive link → fail; none → pass; no NVLink → skipped |
| **A3** | **Xid table merge**: add 61, 62, 92, 140 as fatal; 94 (contained ECC) becomes `restart` (job restarts, node drains only if it repeats within 24 h) | M + NVIDIA catalog | `health/thresholds.yaml`, `health/xid_scan.py` | unit: 94 once → warn, 94 twice in 24 h → fail; 61 → fail |
| **A4** | **Fake `nvidia-smi` and `dmesg`** in the Docker image, faults planted as files in `/run/fake/` (gpus, nvlink, dmesg); Docker nodes expect 2 GPUs, so GPU checks really run | M `docker/fake-*` | `support/simulation/slurm-docker/{fake-nvidia-smi,fake-dmesg,Dockerfile,entrypoint.sh}` | drills: hot GPU → drain; NVLink down → drain; Xid 79 in dmesg → drain; healthy → pass |
| **A5** | Checkpoint: **refuse to save if a frozen part changed** since the previous commit | M `ckpt.py` | `ckpt/ckpt.py`, `ckpt/ds_ckpt.py` | unit T28: change a frozen tensor, save → `FrozenChangedError`, exit 78, `latest.json` unchanged |
| **A6** | Checkpoint: **`embedding_policy_id`** in the environment check | M DESIGN.md | `ckpt/ckpt.py` (`env_manifest`, `ENV_MUST_MATCH`), trainer | unit T29: other policy id → `EnvMismatchError` names it |
| **A7** | Data position carries the **shard manifest sha**; a different shard list refuses to resume | M DESIGN.md | `ckpt/loader_contract.py`, `trainer/tiny.py` | unit T30: loader with another manifest → refused; contract test checks the field |
| **A8** | **QOS limits**: `MaxWall`, `MaxTRESPerJob`, `MaxSubmitJobsPU` on team QOS; **`debug` QOS** (30 min, 1 GPU, 1 job/user, priority 100); team **GPU shares** (`GrpTRES=gres/gpu=N`) next to the node cap | X `queue_design.md` §6, M `accounts.cfg` | `slurm/setup_accounts.sh`, `slurm/slurm.conf` | drills (A10) |
| **A9** | **Time limit with self-requeue**: team jobs get `--time` + `--signal=B:USR1@<lead>`; the wrapper forwards SIGUSR1 to the ranks (`srun --signal`/`scancel -s USR1` on the step), they save and exit 75; Slurm requeues with the same job id | X ADR-05 | `slurm/team_job.sbatch`, `queue/job_queue.py` | drill `time_limit_self_requeue`: `Restarts ≥ 1`, resumed at the saved step, 0 lost steps, run completes |
| **A10** | **Limit drills** ported from X's T05–T11, with real users (alice → arch, bob → perf, carol → none): wrong account refused, QOS not allowed on partition, GPU share `AssocGrpGRES`, `QOSMaxGRESPerJob`, `MaxWall` refused or pending (recorded), `MaxSubmit`, cross-user `scancel` refused | X `test_limits.py`, M users | `support/simulation/run_sim.py`, `Dockerfile` (users) | each drill records the exact Slurm reason string |
| **A11** | **Evidence per drill**: every command, user, exit code and output (trimmed) to `results/evidence/<drill>.log`, plus `summary.md` | X evidence folders | `support/simulation/run_sim.py` | files exist for every drill; size budget < 2 MB total |
| **A12** | **Smoke mode** `run_sim.py --smoke`: accounts, limits, health fakes, one kill + bit-equal restore, < 5 min | M `test.sh` | `support/simulation/run_sim.py` | runs in < 5 min, all pass |

**Phase A gate:** unit suite (local store and S3 emulator) all pass; `run_sim.py` full run: all old drills +
new drills pass; `run_sim.py --smoke` passes; results and evidence committed.

## Phase B: needs a teammate, a decision or a real machine

| Step | What | Why not now |
|---|---|---|
| B1 | uz9ai's `cluster/` (installer, `team7config`, `cluster.toml`, `uv.lock`) into a topic folder `cluster/`, plus a **single-host mode** | uz9ai's code, copied with his agreement; the installer uses apt and systemd on real hosts, so it needs a VM or the shared node to test |
| B2 | Render `slurm.conf`, millermuttu's `node/` files and the accounts from `cluster.toml`; configless Slurm | depends on B1 |
| B3 | Docker image on the torch in X's `uv.lock` (2.14) so FSDP2 runs on CPU in the drills (millermuttu's finding); recheck DeepSpeed | large image change; DeepSpeed/torch pairing to verify |
| B4 | Preemption kept or parked; GPU shares and MaxWall values | team decisions 2–3 |
| B5 | Move cloud-only parts to `support/cloud/` and rewrite the ADRs as in the merge plan §6 | after B1–B4, so docs describe what is final |
| B6 | Shared node (1 Nov): installer single-host, `launch.sh`, millermuttu's TESTING.md level 3, X's T01–T18 with evidence; Kaggle for GPU checkpoint numbers | hardware |

## Provenance (filled as steps land)

| Step | Idea from | Our file |
|---|---|---|
| A1, A2, A4, A5, A6, A7 | millermuttu (`millermuttu/era-v5-lab`, `07-infrastructure`, `c6e38a3`) | see step |
| A8 (GPU shares) | millermuttu `queue/slurm-docker/docker/accounts.cfg` | `slurm/setup_accounts.sh` |
| A8, A9, A10, A11 | uz9ai (`uz9ai/queue`, `main`) `queue_design.md`, `cluster/tests/` | see step |
| A3 | millermuttu's Xid list + NVIDIA Xid catalog | `health/thresholds.yaml` |
