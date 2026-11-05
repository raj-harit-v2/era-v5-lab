# Restart test

Week-2 task (Gate 2): **a killed job restarts from the last COMPLETE checkpoint with equal loss.**

- **Run A** trains Team 05's tiny MoE (`teams/05-architecture/harness/train.py`, `configs/config_v0.yaml` +
  `configs/small/tiny_moe.yaml`, seed 1234) from step 1 to 200 without a stop, with a checkpoint every 25 steps.
- **Run B** is the same command under `ckpt/supervisor.py`. Once it is past step 140 and has a COMPLETE
  checkpoint, it is killed with **SIGKILL** (no warning, no save: a lost node or the OOM killer). The supervisor
  sees the crash and starts the same command again; the trainer's `Checkpointer.restore()` loads the newest
  COMPLETE checkpoint (`MANIFEST.json` written, `latest.json` moved) and trains on to step 200.
- For **every step 1 to 200**, `loss_ntp` and `loss_mtp` must be **bit-equal** to run A and the batch data ID
  (global batch position + sha256 of the batch tokens) must be the same. For the steps run B did twice
  (between the checkpoint and the kill), the value after the restart counts.
- The supervisor log must show exactly one restart (exit -9) and then exit 0, and the restarted trainer must
  start at the step after the checkpoint the supervisor named.

**What it does not cover:** the kill always lands after step 140, when the step-125 checkpoint is already
committed, so it never kills a trainer in the middle of a save. That case is covered by the checkpoint drills
(`kill_during_save` and `kill_during_restore`, `support/docs/sim_results.md`) and by tests T3/T4/T19 in
`support/tests/test_ckpt.py`.

The model, config, loss and data stream are imported from `jobs/restore_test/restore_test.py`, so both tests
train exactly the same thing.

## How to run

Same requirements as the restore test (torch 2.14.1 or newer; `pip install -r teams/04-ke2/src/requirements.txt`).
Run from `teams/07-infrastructure/`. No network, about 10 s on a laptop.

**As a TSAI job** (queue rules v1, `docs/queue_rules_v1.md`). The same line runs the CPU test; only `--device`
changes (R6):

```bash
python jobs/restart_test/restart_test.py --run-id g7-restart-test-20261104-01 --device cpu
python jobs/restart_test/restart_test.py --run-id g7-restart-test-20261104-01 --device cuda --max-time-min 30
python queue/queue_rules.py check-out ./out --run-id g7-restart-test-20261104-01
```

Everything goes to `./out/<run_id>/`:

| Path | What |
|---|---|
| `result.json` | the R8 result (`g7-job-result/1`), written last: `status` pass / fail / stopped_at_limit, `exit_code`, device, times, and `numbers` (`bit_equal_steps`, `killed_after_step`, `restarted_from_step`, `pointer_step`, ...) |
| `logs/job.log` | everything the job and its trainers print, each line `<UTC time> r0 ...` (R3) |
| `logs/events.jsonl` | `checkpoint.*`, `restore.*` and `supervisor.*` events, in time order (R3) |
| `logs/supervisor.jsonl` | one line per run B attempt |
| `ckpt/a/`, `ckpt/b/` | the `ckpt.py` layout per arm: `latest.json`, `commits.jsonl`, `main/step_<N>-e<E>/` (R4) |
| `rows/a.jsonl`, `rows/b.jsonl` | one row per step: losses, loss bits, batch data ID, attempt |
| `detail.json` | every row of both runs and the supervisor log |

- **Time limit (R1):** the job stops itself 5 minutes before `--max-time-min` (half the limit if that is
  shorter). It stops the trainer, writes `result.json` with `stopped_at_limit` and exits 75.
- **Size:** about 24 MB. Node-local copies are deleted at the end; if the folder is still over 45 MB, shard files
  of the oldest steps are deleted and the receipts (`latest.json`, `commits.jsonl`, `MANIFEST.json`,
  `sums_rank<r>.json`) are kept (R4).
- **On a GPU:** the trainer uses `cuda:0`, and the job sets `CUBLAS_WORKSPACE_CONFIG=:4096:8` for
  deterministic cuBLAS (R7). Not run on a GPU yet; that is what the job request is for.

**Locally**, with the plain-text report in `results/` (output in `jobs/restart_test/out/`, git-ignored):

```bash
CUDA_VISIBLE_DEVICES="" python jobs/restart_test/restart_test.py --also-kill-at 31,99,164 --report results/restart_cpu.txt
```

| Flag | Default | Meaning |
|---|---|---|
| `--run-id` | none | job run ID `g7-<short-name>-<YYYYMMDD>-<NN>` (R5); output goes to `./out/<run_id>/` |
| `--device` | `cpu` | `cpu`, or `cuda` (1 GPU) |
| `--max-time-min` | 30 | the request's `Max time`; the job stops itself before it |
| `--steps` | 200 | last step |
| `--save-every` | 25 | checkpoint every N steps |
| `--kill-at` | 140 | SIGKILL run B once it is past this step |
| `--out` | `out/` next to the script (git-ignored) | output folder without `--run-id` |
| `--report` | none | also write the plain-text result (the file in `results/`) |
| `--also-kill-at` | none | local runs only: comma list, e.g. `31,99,164`, also run these kill points; their result lines go into `--report` |

Exit 0 and one `PASS` line when every check holds; 1 at the first difference; 78 if a run crashed; 75 if it
stopped at the time limit.

Bit equality is between run A and run B on the same machine; the numbers are not expected to match other OSes.

Result on CPU: [`results/restart_cpu.txt`](../../results/restart_cpu.txt). One process only for now.
