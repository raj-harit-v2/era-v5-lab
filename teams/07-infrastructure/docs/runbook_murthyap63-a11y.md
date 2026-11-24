# Infrastructure Runbook: Shared GPU Box (`queue_runner.sh`)

## 1. Job Submission & Lifecycle (`queue_runner.sh`)
Jobs on the shared GPU box are managed through `~/era-v5-jobs/queue_runner.sh` (backed by `tmux`) rather than a Slurm scheduler.

- **Job Layout:** Each job lives in `jobs/<name>/` with:
  - `cmd.sh` — the command/environment to run (e.g., `WATCHDOG_S=600` for Dry Run 1).
  - `max_hours` — maximum runtime budget for the job.
  - `exit_code` — recorded exit status once the run finishes or stops.
  - `run.log` — live/appended execution output.
- **Submitting a Job:**
  1. Create or update `jobs/<name>/cmd.sh` and `jobs/<name>/max_hours`.
  2. Queue/start the job via `~/era-v5-jobs/queue_runner.sh` (or check active `tmux` sessions for running jobs).
- **Monitoring & Completion:**
  - Tail logs: `tail -f jobs/<name>/run.log`
  - Inspect `tmux` sessions: `tmux ls` and attach when needed (`tmux attach -t <session_name>`).
  - Check completion status in `jobs/<name>/exit_code` and verify the latest committed checkpoint before starting a follow-up job.

## 2. Node / Shared-Box Failures & Recovery
Because jobs run on a shared GPU box under `queue_runner.sh` without Slurm node states (`DRAIN` / requeue), recovery focuses on host/GPU health, session cleanup, and checkpoint-safe relaunch.

- **Symptom:** A job stops unexpectedly, hits `max_hours`, or the shared GPU box experiences a hardware fault, OOM kill, driver error, or power/host interruption.
- **Diagnosis:**
  1. Check `jobs/<name>/exit_code` and the tail of `jobs/<name>/run.log`.
  2. Check system and GPU health on the box:
     ```bash
     nvidia-smi
     dmesg -T | grep -iE "oom|killed|nvrm|xid|hardware" | tail -n 50
     tmux ls
     ```
- **Recovery:**
  1. Clean up any lingering `tmux` session or stuck child process belonging to the stopped job (verify PIDs carefully before terminating so other users' jobs on the shared box are unaffected).
  2. If a GPU or host issue occurred (thermal throttle, memory/ECC/Xid error, or full disk/cache), resolve or isolate the issue before relaunching.
  3. Confirm the last valid committed checkpoint, update `jobs/<name>/cmd.sh` if needed, and resubmit through `~/era-v5-jobs/queue_runner.sh`.

## 3. NCCL Hangs & Communication Deadlocks
- **Symptom:** Training stalls mid-step without progressing; GPU compute drops to 0% or collectives time out. Dry Run 1 uses a 10-minute collective timeout and `WATCHDOG_S=600` (avoiding short 60 s heartbeats that can prematurely kill healthy runs during checkpoint saves or evaluations).
- **Diagnosis:**
  - Inspect `jobs/<name>/run.log` for NCCL warnings or watchdog timeouts.
  - Run with NCCL diagnostics enabled when reproducing/debugging:
    ```bash
    export NCCL_DEBUG=INFO
    export NCCL_DEBUG_SUBSYS=INIT,COLL
    export WATCHDOG_S=600
    ```
  - Check active training processes (`ps aux | grep python`) and `nvidia-smi` to see whether ranks are wedged.
- **Recovery:**
  1. Stop the hung `tmux` session / stuck training processes cleanly (`SIGTERM` first, then `SIGKILL` only if hung).
  2. Verify `jobs/<name>/exit_code` and ensure no partial/uncommitted checkpoint was promoted.
  3. Relaunch through `~/era-v5-jobs/queue_runner.sh` from the last committed checkpoint with `WATCHDOG_S=600`.

## 4. Bad / Corrupted Checkpoints
- **Symptom:** Deserialization errors on load, checksum/manifest mismatches, or immediate loss spikes / `NaN`s after resuming.
- **Prevention (Atomic Commit):** Never overwrite the active pointer/manifest in place until all checkpoint artifacts are written and verified, committing the final marker/pointer last so an interrupted write leaves the previous good checkpoint intact.
- **Recovery:**
  1. Do not overwrite or delete the prior known-good checkpoint directory.
  2. Verify checkpoint integrity (checksums/manifest/archive readability) before launching.
  3. Point the resume configuration to the last verified good checkpoint and relaunch via `~/era-v5-jobs/queue_runner.sh`, checking `jobs/<name>/run.log` and `jobs/<name>/exit_code` after startup.