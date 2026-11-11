# Queue rules v1: what every G7 job must say before it runs

Owner: G7 Member B. Status: **v1 draft for lead review** (week 2, due Tue 3 Nov 2026).
Checker: [`queue/queue_rules.py`](../queue/queue_rules.py). Tests: [`queue/test_queue_rules.py`](../queue/test_queue_rules.py).

> **In simple words.** In week 2 there is no lab Slurm for students. We write a job package, test it on CPU,
> and send a job request (`JOB_REQUEST.md` at the repo root). TSAI runs it and sends the logs back. These rules
> make every G7 job say five things up front: **how long it may run, how many devices it uses, where its logs
> go, where its checkpoints go, and its one run ID.** A job that does not say them is not sent. The same five
> rules become Slurm settings (`--time`, `--gpus`, `--output`, `V5_REMOTE_ROOT`, `RUN_ID`) when the lab has a
> scheduler, so nothing changes for the trainer then.

---

## 0. Where these rules sit

| Layer | Who owns it | What it decides |
|---|---|---|
| `JOB_REQUEST.md` (repo root) | TSAI | the request block, the `./out/` rule, the 50 MB limit, two failures and the job goes back |
| **this file** | G7 | the five job fields below, the `./out/` layout, the run ID, the result file, the checker |
| ADR 0002 and `queue/job_queue.py` (PR #150) | G7 | the later Slurm cluster: exit codes 0 / 75 / 78, requeue, crash-loop cap |
| `ckpt/ckpt.py` (PR #150) and `ckpt/supervisor.py` (Member D) | G7 | what is inside a checkpoint, and when a restart may trust it |

Where this file and `JOB_REQUEST.md` disagree, `JOB_REQUEST.md` wins and this file is fixed.

---

## 1. The five fields (the rules TSAI checks)

Every G7 request adds these lines **inside** the `JOB_REQUEST.md` block, after `Test log:`. They are the G7
part of the request. `python queue/queue_rules.py check-request <file>` checks all of them.

```
Run ID:          g7-<short-name>-<YYYYMMDD>-<NN>
Devices:         0 | 1 | 2                              (0 = CPU; must match Hardware)
Log path:        ./out/<run_id>/logs/
Checkpoint path: ./out/<run_id>/ckpt/
```

`Max time:` is already a `JOB_REQUEST.md` line. G7 adds the limits in R1.

### R1. Max time

| Job class | Hardware | Max time (minutes) | Status |
|---|---|---|---|
| smoke (any package on CPU) | CPU | 15 | proposed, awaiting TSAI |
| health baseline (`jobs/health_baseline/`) | 1 GPU | 20 | proposed, awaiting TSAI |
| restore test (`jobs/restore_test/`) | 1 GPU, or 2 GPUs | 60 | proposed, awaiting TSAI |
| restart test (supervisor) | 1 GPU | 60 | proposed, awaiting TSAI |
| **hard cap for any G7 request** | any | **60** | proposed, awaiting TSAI |

- `Max time:` is a whole number of minutes, at least 1, at most the cap. The checker refuses more.
- **The job stops itself before TSAI stops it.** The start command computes
  `deadline = start + Max time − margin`, with `margin = max(5 min, 2 × save time + 60 s)`
  (the same lead rule as `slurm/team_job.sbatch`). At the deadline it saves, writes `result.json` with status
  `stopped_at_limit`, and exits 75. A job that TSAI has to kill writes no `result.json`, and that counts as a
  failure.
- Set `Max time` from the CPU test log: at least 2 × the measured CPU-to-device time you expect, so a surprise
  is easy to see (`Expected result:`).

### R2. Device count

- `Devices:` is `0` (CPU), `1` or `2`. One node only. `2` only when TSAI agreed to it (the restore test asks for
  1 device and 2 devices as two requests).
- `Devices:` must match `Hardware:` (`CPU` ↔ 0, `1 GPU` ↔ 1, `2 GPUs` ↔ 2).
- The script reads the device count it was given (`WORLD_SIZE` under `torchrun`, else 1) and **stops with exit
  78 if it differs from `Devices:`**. It never takes more devices than it asked for.
- A 2-device job starts with one command: `torchrun --standalone --nproc_per_node=2 <file>.py ...`.

### R3. Log path

```
./out/<run_id>/logs/job.log          everything the start command prints (rank 0)
./out/<run_id>/logs/rank<r>.log      one file per rank, when Devices is 2
./out/<run_id>/logs/events.jsonl     one JSON object per line: checkpoint.committed, job.ended, ...
```

- Logs go only here. No log goes to the home folder, `/tmp` or the console only.
- Each log line starts with the UTC time and the rank: `2026-11-04T10:15:02Z r0 step 101 loss=...`.
- The `events.jsonl` names are the ones in `common/events.py` (PR #150), so Team 8 reads them with no change.

### R4. Checkpoint path

```
./out/<run_id>/ckpt/<arm>/latest.json                       pointer to the newest committed checkpoint + epoch
./out/<run_id>/ckpt/<arm>/commits.jsonl                     every commit, in order
./out/<run_id>/ckpt/<arm>/<branch>/step_<N>-e<E>/           shards, extra_rank<r>.json, sums_rank<r>.json,
                                                            MANIFEST.json (written last)
```

- `<arm>` is one run inside the job: `main` for a job with one run; `a` and `b` for the restore test (run A
  saves at step 100; run B stops at 150, restores from 100 and runs to 200). Lowercase letters and digits.
- `<branch>`, `step_<N>-e<E>`, `MANIFEST.json`, `latest.json` and `commits.jsonl` are the layout of
  `ckpt/ckpt.py`: `Checkpointer(run_id=<arm>, remote_root=./out/<run_id>/ckpt, ...)` writes exactly this.
- **A checkpoint is COMPLETE when its step folder has `MANIFEST.json` and `latest.json` or `commits.jsonl`
  names that folder.** There is no separate `COMPLETE` file. `ckpt/ckpt.py` already writes `MANIFEST.json`
  last, and moves `latest.json` (with the fencing check) and appends to `commits.jsonl` only after it. So a
  folder that both a pointer and its `MANIFEST.json` vouch for was fully written, and only by the attempt that
  owns the run. A second "written last" file would add no safety, and would make every checkpoint saved so far
  incomplete.
- A restart (`Checkpointer.restore()`, used by `ckpt/supervisor.py`) starts from the folder `latest.json`
  names, then falls back through `commits.jsonl`, newest first. Readers outside the run follow `latest.json`.
- `MANIFEST.json` that no pointer names is a save that was cut before its commit: not a checkpoint, not an error.
  A pointer to a folder without `MANIFEST.json` is an error, and the checker reports it.
- Size: the returned `./out/` is at most 50 MB (`JOB_REQUEST.md`). At the end the job keeps the receipts
  (`latest.json`, `commits.jsonl`, `MANIFEST.json`, `sums_rank<r>.json`) and deletes shard files
  over the limit, newest step last. The proof numbers are in `result.json`, not in the shards.

### R5. One run ID per job

```
g7-<short-name>-<YYYYMMDD>-<NN>          for example g7-restore-test-20261104-01
```

- `<short-name>` is the request file name without its date: request
  `jobs/2026-11-04-restore-test.md` → `restore-test`. Lowercase letters, digits and single dashes.
- `<YYYYMMDD>` is the request date (the date in the file name). `<NN>` is `01`, `02`, ... for a resend of the
  same question after a failure.
- **One request, one run ID.** Every run inside the job is an `<arm>` under it, never a second run ID. A new
  question is a new request and a new run ID. A run ID is never reused: it names the checkpoint folder, and a
  reused ID would restore someone else's checkpoint.
- The start command takes it as `--run-id <run_id>` and exports it as `RUN_ID`, the name `queue/job_queue.py`
  and `ckpt/ckpt.py` already use.
- Make one with `python queue/queue_rules.py run-id restore-test --date 2026-11-04`.

---

## 2. The rest of the contract

### R6. One start command

- One line, run from `teams/07-infrastructure/`, with no shell pipes, `;`, `&&`, redirection or `$(...)`
  (`JOB_REQUEST.md` rule). It must include `--run-id <run_id>`.
- No network, no keys, no secrets. It reads only its inputs and writes only to `./out/`.
- The same line runs the CPU test. Only `--device` changes.

### R7. The bit-equal environment

The job sets these itself (the job scripts in `slurm/` do the same): `OMP_NUM_THREADS=1`, a fixed seed from the
config, `torch.use_deterministic_algorithms(True)`, and on a GPU `CUBLAS_WORKSPACE_CONFIG=:4096:8` (PyTorch needs
it for deterministic cuBLAS). `result.json` records the torch version and the device count, so two runs can be
compared.

### R8. `result.json`, written last

`./out/<run_id>/result.json`, one JSON object:

| Key | Type | Meaning |
|---|---|---|
| `schema` | `"g7-job-result/1"` | version of this table |
| `run_id` | string | the run ID; must match the folder |
| `status` | `pass` / `fail` / `stopped_at_limit` | the answer to the request's question |
| `exit_code` | 0 / 75 / 78 / other | 0 done; 75 stopped and saved; 78 stopped on purpose (mismatch, NaN, failed check) |
| `device_kind` | `cpu` / `gpu` | what it ran on |
| `device_count` | int | devices used; equals `Devices:` (0 on CPU) |
| `max_time_min` | int | the request's `Max time` |
| `elapsed_s` | number | wall time; at most `max_time_min × 60` |
| `started_utc`, `ended_utc` | ISO-8601 `...Z` | start and end |
| `numbers` | object | the measures the request named, for example `{"bit_equal_steps": 100}` |

`python queue/queue_rules.py check-out ./out --run-id <run_id>` checks this file, the log and checkpoint paths,
the COMPLETE rule of R4 and the 50 MB limit. Run it at the end of the CPU test, and attach its output to the request.

### R9. Failure

- Exit codes are the ones of ADR 0002: 0 done, 75 saved and stopped (may run again), 78 stopped on purpose
  (do not run again until a person looks).
- `JOB_REQUEST.md`: a job that fails two times goes back to the team. A resend is a new request with the next
  `<NN>`.
- On the later Slurm cluster the crash-loop cap applies instead: 3 crashes in 30 min turn 75 into 78.

---

## 3. From these rules to Slurm (later)

| Rule | Request line now | Slurm later (`slurm/*.sbatch`) |
|---|---|---|
| R1 max time | `Max time:` | `--time`, plus `--signal=B:USR1@<margin>` |
| R2 devices | `Hardware:`, `Devices:` | `--gpus-per-node`, `--ntasks-per-node` |
| R3 log path | `Log path:` | `--output`, `V5_EVENTS_DIR` |
| R4 checkpoint path | `Checkpoint path:` | `V5_REMOTE_ROOT` |
| R5 run ID | `Run ID:` | `RUN_ID` (`--export=ALL,RUN_ID=...`) |

---

## 4. A filled example

`teams/07-infrastructure/jobs/2026-11-04-restore-test.md` (the lead sends the real one):

```
Team:            07-infrastructure
Owner:           <name as on Axiom> (<github handle>)
Lead approval:   <lead github handle>
Question:        Does run B, restored from step 100, give bit-equal loss and equal batch IDs at steps 101 to 200?
Script:          teams/07-infrastructure/jobs/restore_test/restore_test.py
Command:         python jobs/restore_test/restore_test.py --config jobs/restore_test/config.yaml --run-id g7-restore-test-20261104-01 --device cuda
Config:          teams/07-infrastructure/jobs/restore_test/config.yaml
Inputs:          synthetic
Hardware:        1 GPU
Max time:        30
Precision:       fp32
Measures:        steps 101-200 with equal loss bits and equal batch IDs; save time in ms; restore time in ms
Expected result: 100 of 100 steps equal
Outputs:         out/*.json, out/*.csv, out/*.log (50 MB or less in total)
Test log:        <link to the CPU log>
Run ID:          g7-restore-test-20261104-01
Devices:         1
Log path:        ./out/g7-restore-test-20261104-01/logs/
Checkpoint path: ./out/g7-restore-test-20261104-01/ckpt/
```

```bash
python queue/queue_rules.py check-request jobs/2026-11-04-restore-test.md
python queue/queue_rules.py paths g7-restore-test-20261104-01 --arm a
python queue/queue_rules.py check-out ./out --run-id g7-restore-test-20261104-01
```

---

## 5. Hand-off to Teams 9 and 12 (due Wed 4 Nov)

Sections R4 and R8 are the checkpoint path layout and file list. In short, for one committed checkpoint:

| File | Who reads it |
|---|---|
| `<arm>/latest.json` | anyone: which step is the newest COMPLETE one (`step`, `branch`, `path`, `epoch`) |
| `<arm>/commits.jsonl` | anyone: every COMPLETE checkpoint, in order |
| `<arm>/<branch>/step_<N>-e<E>/MANIFEST.json` | every file of the checkpoint with its sha256, and the environment |
| shard files listed in `MANIFEST.json` | `ckpt/ckpt.py` restore, or `export_safetensors()` for one checked file |

Teams 9 and 12 open only the folder that `latest.json` (or a `commits.jsonl` line) names, never a folder found
by listing, and take weights through `export_safetensors()`, not by opening shards.

---

## 6. Open items

| Item | Owner | Blocks |
|---|---|---|
| TSAI confirms the R1 limits (or gives others) | Lead → TSAI | the numbers in R1 |
| Health and restore packages adopt R3 to R8 | Member A, Member C | their requests |
| TSAI agrees that G7 adds the four lines to the request block | Lead → TSAI | R1 to R5 as written |

## 7. Change log

| Version | Date | Change |
|---|---|---|
| v1 | 2026-11-02 | first version: five fields, `./out/` layout, `COMPLETE` marker, result file, checker |
| v1.1 | 2026-11-03 | COMPLETE = `MANIFEST.json` + named by `latest.json` / `commits.jsonl`; no separate `COMPLETE` file (team decision, matches `ckpt.py` and `supervisor.py`) |
