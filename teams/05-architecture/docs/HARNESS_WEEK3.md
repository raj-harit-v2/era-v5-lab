# Week 3 harness

## G8 live metrics

Pass the job package's run ID as `--run-id "$RUN_ID"` to use the same identity in G5 and G8. IDs begin with a letter or digit and may also contain dots, dashes, and underscores. A fresh invocation without the flag generates an ID. The trainer records it in `manifest.json`, `summary.json`, and the native checkpoint. Resume uses a fresh output directory and recovers the checkpoint ID if the flag is omitted. If supplied, the ID must match the checkpoint. For a compatible legacy checkpoint without an ID, the checkpoint file's SHA-256 is its ID. The resume identity check still applies.

To enable the G8 adapter, put `teams/08-monitoring/metrics_logger` on `PYTHONPATH` and pass `--logger-factory g5_adapter:make_writer`. The trainer writes the manifest before calling the factory once with the output directory. The returned writer receives `write(row)` in step order, including the initial evaluation at step 0 and the saved history on resume. The trainer calls `flush()` before writing final artifacts and `close()` on exit. A logger error fails the invocation.

The adapter writes `g8/metrics.jsonl` with `run_id`, `step`, `time`, and the existing G8 metrics. It flushes at step 0, every 10 steps, on a nonfinite metric, and on close. Replayed rows retain their step and run ID and receive timestamps when written. Use the newest segment's G8 file for ingestion because it includes the checkpoint's history. The ClickHouse loader reads the embedded run ID. The trainer also writes its native `metrics.jsonl`.

## Validate run evidence

Run this against the output directory after the trainer has exited.

```bash
python teams/05-architecture/harness/validate_week2_run.py /path/to/run --trusted-checkpoint
python teams/05-architecture/harness/validate_week2_run.py /path/to/run --trusted-checkpoint --expected-steps 1000 --json > run-evidence.json
python teams/05-architecture/harness/validate_week2_run.py /path/to/copied-run --trusted-checkpoint --verify-inventory run-evidence.json
```

The validator uses the resolved step budget in the manifest. Supply `--expected-steps` when you have the budget from the job request. It checks the summary status and completed steps, the evaluation row at step 0, one metrics row per completed step, and one row per completed step in each loss trace. It recomputes the manifest identity and reports SHA-256 hashes for the evidence files, including the required checkpoint for non-smoke runs. Archive the JSON report with the run to check the hashes after copying.

A quality PASS requires `smoke=false`, a `COMPLETED` summary, the exact configured or expected step count, all six evidence files, and matching checkpoint identity and step. Run with `--trusted-checkpoint` only on trusted outputs because PyTorch uses its full checkpoint loader. The validator reports a failure for a quality candidate when checkpoint inspection cannot be performed.

Exit code 0 means the run completed with internally consistent evidence. This validation provides neither a BPB result nor a winning configuration. Exit code 1 covers smoke runs, incomplete runs, and evidence failures. The JSON report includes the verdict, evidence scope, row counts, checkpoint inspection status, and errors.

## Optimizer-step watchdog

Add `teams/07-infrastructure` to `PYTHONPATH`. `--watchdog-s SECONDS` overrides `WATCHDOG_S`; when neither is supplied the watchdog is off. Explicit `--watchdog-s 0` disables it for local smoke runs even if the environment supplies a value. Team 7's production guidance is the greater of 600 seconds and five times the p99 step duration.

The timer starts before the initial evaluation and resets at each optimizer step and after each completed update. It covers data loading, device synchronization, in-loop evaluation, and periodic checkpoint saves when integrated with #608. It is disarmed after the optimizer loop before final artifacts are written.

On timeout the trainer dumps all Python thread stacks, emits `train.watchdog` with the last completed step, writes the `hang_watchdog` exit note, and exits 75. Set `V5_EVENTS_DIR`, `V5_RUNS_DIR`, and `RUN_ID` for Team 7's job runner. `os._exit` drops metrics still in memory; #608 replays history retained in the last committed checkpoint. Two watchdog restarts in an hour page under H-14; three crashes in 30 minutes become a hold with exit 78 under Team 7's supervisor.

For Dry Run 2, use a job wrapper with G5's input arguments and checkpoint flags. Team 7's reference `mainrun.sbatch` supplies simulation-trainer flags such as `--remote-root` and `--step-sleep`; the G5 trainer does not accept that command unchanged.

## Team 7 periodic checkpoints

Quality runs require Team 7's committed checkpoint store and the shared job run ID. Add `teams/07-infrastructure` to `PYTHONPATH` and pass:

```bash
--run-id "$RUN_ID" --checkpoint-store /shared/ckpt --checkpoint-interval-s 600
```

The CLI interval overrides `INTERVAL_S` and defaults to 600 seconds. At a completed step after the interval, G5 flushes both metric writers and calls Team 7's asynchronous save. Team 7 handles backpressure if an earlier upload is still running. G5 waits for the Team 7 commit before reporting completion. A successful run records the committed path in its summary and publishes the compatibility `checkpoint.pt` atomically. The Team 7 commit is the recovery source for quality runs. Local smoke runs can still use the native format.

To continue a quality run, pass `--resume-committed`, the same `--run-id` and store, and a fresh `--out` directory. The restore verifies the G5 identity and can fall back to an earlier verified commit. G5 keeps metrics and loss history in the checksummed loader payload. The native smoke resume remains available with `--resume checkpoint.pt` for trusted local artifacts.

With Team 7 enabled, SIGTERM and SIGUSR1 where supported request a save at the next step boundary and exit 75. A failed final commit also exits 75. Fencing, nonfinite training state, and checkpoint restore errors exit 78. For Gate 4, `--checkpoint-at-start` commits step 0 before the first optimizer update on a fresh invocation. Native and committed resumes skip this option. The initial optimizer state travels in G5's checksummed history so a step-0 restore preserves the first real update despite DCP's lazy-state initialization. This is a normal Team 7 commit and can be pinned with `ckpt.py pin --run <run_id> --step 0`.

## Optional MoE expert load

Pass `--expert-load-every STEPS` to sample every STEPS completed optimizer steps. The default is 0. For example, `--expert-load-every 100` samples steps 100, 200, and so on. The manifest records the cadence. Resume continues using absolute training step numbers and replays the telemetry already present in the checkpoint's metrics history.

Sampled rows include `expert_load`, a list in model layer order with one integer count per routed expert in expert-index order. Each count records top-k router picks across all training microbatches in that optimizer step. Padding positions, shared experts, and evaluation forwards are excluded. For each layer the counts sum to `train/scored_tokens * top_k`. Unsampled rows omit the field.

With `--logger-factory g5_adapter:make_writer`, the G8 JSONL includes the same counts. The existing metrics writer also derives `router_max_vio`, `expert_load_imbalance`, and dead-expert statistics from them. Sampling adds work to the sampled step's performance measurement.
