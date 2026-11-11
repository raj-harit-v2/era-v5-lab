# Queue design v0

Team 07, Infrastructure. Status: **v0** for Gate 2. This file is the short form of the queue design. The full
decision, with the options and the evidence, is [ADR 0002](../adr/0002-job-queue-slurm.md); the job rules TSAI
checks are [queue rules v1](queue_rules_v1.md); the code is [`queue/`](../queue/README.md) and
[`ckpt/supervisor.py`](../ckpt/supervisor.py). Where this file and those disagree, they win and this file is fixed.

> **In simple words.** The queue decides which job runs, and restarts a job that stopped. A job that saved and
> stopped (exit 75) starts again by itself and restores its last checkpoint. A job that must not continue
> (exit 78) waits for a person, with a note that says why. A job that keeps crashing is held, so it stops
> wasting GPU hours.

## 1. Two ways a job runs

| | Now (week 2 on) | The main run (later) |
|---|---|---|
| Who starts jobs | TSAI, from an approved [`JOB_REQUEST.md`](../../../JOB_REQUEST.md) | Slurm |
| Who restarts after a stop or a crash | [`ckpt/supervisor.py`](../ckpt/supervisor.py) around the trainer | Slurm requeue (`RequeueExit=75`), through [`queue/job_queue.py`](../queue/job_queue.py) |
| Limits | queue rules R1 (max time) and R2 (devices) | Slurm QOS limits (ADR 0002 §4) |
| Where output goes | `./out/<run_id>/` only (R3, R4) | `<remote_root>/<run_id>/`, logs to the job log and `V5_EVENTS_DIR` |

Both use the **same exit codes** and the **same crash-loop rule**, so a trainer behaves the same under either.

## 2. The restart contract (both ways)

| Trainer exit | Meaning | The queue does |
|---|---|---|
| `0` | done | stops |
| `75` | saved, run me again (time limit, stop signal, preemption, health drain) | starts the same command again; the trainer restores `latest.json` |
| `78` | stopped on purpose (NaN, environment or key mismatch, every checkpoint failed) | holds; a person reads the cause |
| anything else | a crash | restarts, unless it is the 3rd crash in 30 minutes: then holds (78) |

- A checkpoint is used only when it is COMPLETE: `MANIFEST.json` is written and `latest.json` or `commits.jsonl`
  names its folder ([queue rules R4](queue_rules_v1.md), [checkpoint design](checkpoint_design_v0.md) §5–6).
- SIGTERM and SIGUSR1 mean "save, wait for the commit, exit 75". The queue passes them on to the trainer.
- Every restart decision is logged: `supervisor.jsonl` and `supervisor.*` events now, `job.*` events and the
  Slurm job comment later. A held job says what happened and what to do (`common/reasons.py`).

## 3. Who gets the devices (the main run)

- The main run comes first: its QOS preempts team jobs, which save and go back to the queue (exit 75).
- Teams share the rest by fair share, each with a device share, per-job limits (time, devices, queued jobs) and a
  device-hour budget that stops new jobs when it is used up. A job over a per-job limit is refused at submit,
  with the reason.
- One quick debug job per user can run ahead of the queue.

Details and numbers: ADR 0002 §4.

## 4. Evidence

| What | Result | Where |
|---|---|---|
| Restart after SIGKILL under the supervisor, CPU | PASS, steps 1–200 bit-equal, one restart from the COMPLETE checkpoint | [`results/restart_cpu.txt`](../results/restart_cpu.txt) |
| Supervisor unit tests | pass | [`ckpt/test_supervisor.py`](../ckpt/test_supervisor.py) |
| Queue rules checker | pass | [`queue/test_queue_rules.py`](../queue/test_queue_rules.py) |
| Requeue, hold, crash loop, preemption in a Docker copy of the Slurm cluster | drills pass | [`support/docs/sim_results.md`](../support/docs/sim_results.md) |
| Restart on the lab node, as a TSAI job | _pending_: job request Thu 12 Nov | `results/restart_node.txt` |

## 5. Open items

| Item | Owner | Due |
|---|---|---|
| Restart job request on the lab node; `results/restart_node.txt` | Lead | Thu 12 Nov / Sat 14 Nov |
| TSAI confirms the proposed limits in queue rules R1 and R2 | TSAI | Gate 2 |
| Slurm limits for the main run, sized from config v1 | Team 07 | after Sat 14 Nov |
