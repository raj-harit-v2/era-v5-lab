# Response to the G7 multi-repo review: checkpoint topic

Reply to `G7_ERA_V5_DeepSpeed_ADR_and_Code_Gap_Reports` (sureshmantha/erav5, 29 Oct 2026), for the
checkpoint rows only. Written by pradeep-kumar-gs (P) for the team.

**In simple words.** The review read a copy of this repo from before the DeepSpeed work (its file list has no
`ckpt/ds_ckpt.py` and no tests after T17). Since then the checkpoint path runs on a real DeepSpeed engine, and
the one real hole the review found (an old job could still move the `latest` pointer) is closed and tested.
Below: each checkpoint row, what the review said for P, and what is in the repo now, with the test or drill
that proves it. Everything here is CPU or Docker evidence unless it says GPU.

## Row by row (01_ADR_COVERAGE_AND_GAP_ANALYSIS.md)

| # | Topic | Review said (P) | Now | Evidence |
|---:|---|---|---|---|
| 9 | DeepSpeed engine initialization | Proposed | the trainer runs `deepspeed.initialize` (`--deepspeed`, ZeRO stage, fp32/fp16/bf16) | `support/simulation/trainer/train.py`; T18 |
| 10 | ZeRO stage 1/2/3 | Design | save → new process → restore, loss bit-equal at stages 1, 2 and 3 | T18 (stages 1, 2, 3), T21 |
| 13 | Gradient accumulation boundary | Checkpoint docs | contract: save only between optimizer steps; a stop signal waits for the accumulation boundary | ADR 0001 §7 (Team 05 row) |
| 21 | Sharded checkpoint format | ADR1/DCP | two backends behind one commit protocol: DCP (plain/FSDP) and DeepSpeed `save_checkpoint`. No claim that one loads the other | `ckpt/ckpt.py`, `ckpt/ds_ckpt.py` |
| 22 | Per-rank state inventory | ADR1 broad | weights, optimizer, LR, every RNG per rank, data ledger offset + skip list, environment | ADR 0001 §1; T1, T6 |
| 23 | Atomic multi-rank commit | Proposed S3 | all-rank sums (receipts) → re-check every object → MANIFEST last → **conditional** pointer write with epoch fencing. Old attempt refused, exits 78 | T4, T24, T25, T26; drill `split_brain_fenced` |
| 24 | Integrity and corruption | Hashes | sha256 per object (S3 checksum on upload), flipped byte → fallback, crash before seal → pointer unchanged | T3, T4, T19; drills `kill_during_save`, `kill_during_restore` |
| 25 | Async staging | Design | `dcp.async_save`: stall = GPU→host copy only, one save in flight, backpressure counted (CK-10). **The race the review warns about was real on CPU**: torch 2.5.1 stages CPU tensors without a copy, so a commit could hold later weights than its digest. Found by drill `kill_during_save` (run 13), fixed by copying CPU tensors ourselves. DeepSpeed saves synchronously | ADR 0001 §2; T27; drill `kill_during_save` |
| 26 | Topology-changing restart | Design/proofs | plain/FSDP: restore 4 → 1 ranks, digest equal, branch marked resharded. DeepSpeed: refused with exit 78 `ReshardError` naming `ds_to_universal.py` | T2, T16 (GPU), T20; drill `restore_smaller_world` |
| 27 | Strict restore, no silent misload | Probe+key checks | strict keys + 4 proofs (digest, probe loss bits, next batch, frozen hashes); DeepSpeed "could not load" → fallback, never a fresh start | T5, T19 |
| 28 | Data ledger | Ledger | one global offset on every rank, checked at every save; loader contract test for Teams 01/02 | T13, T15 |
| 29 | DeepSpeed at the checkpoint boundary | **Not verified** (all four repos) | real all-rank DeepSpeed save/load with optimizer state, ZeRO-1/2/3 (optional backend, off by default) | T18–T22 |
| 33 | Export for eval/quant | Docs | DCP → safetensors and DeepSpeed `zero_to_fp32` → safetensors, digest-checked against the saved weights | T8, T22 |

From `03_VALIDATION_AND_HANDOFF.md`: "DeepSpeed ZeRO save/restart: **NOT RUN**, DeepSpeed not installed".
In this repo it runs: DeepSpeed 0.19.8 locally, 0.18.0 in the Docker image.

## The gap the review found, now closed: stale writer (row 23)

Before: rank 0 wrote `latest.json` unconditionally. An attempt that Slurm believed dead (node cut off, job
requeued, network back) could commit after the new attempt and move the pointer back, or write files into the
same step folder.

Now (ADR 0001 §2 "Fencing"):

1. On start, each attempt **claims** the run: `latest.json` gets `epoch + 1`, written only if it is still the
   version read (S3 `If-Match` / `If-None-Match: *`; the folder store uses an `O_EXCL` lock file).
2. Every commit writes `latest.json` only if it is still the version this attempt last wrote. After a newer
   claim it is not: `checkpoint.fenced`, exit 78 `FencedError` (hold, never requeue).
3. Each attempt writes into its own `step_<N>-e<epoch>` folders, so two attempts never mix files.
4. `commits.jsonl` is appended conditionally too, so no line is ever lost to a parallel writer.

Proof: T24 (in-process), T25 (two real trainer processes; the old one exits 78, none of its commits land after
the claim), T26 (store semantics on the folder store and on S3: stale version loses, 60 parallel appends keep
every line, 4 simultaneous claims never share an epoch), and the Docker drills `split_brain_fenced` and
`resume_after_fence`.

Finding on the way: **moto before 5.1.10 silently ignores `If-Match`**, so a fencing test on the old emulator
would pass without testing anything. The Docker image now pins `boto3==1.35.99` and `moto==5.1.10`.

## Production start order

`launch/launch.sh` starts the stack in order (munge → slurmdbd → DB backup with test restore → controllers →
accounts → slurmd → full health on every node → services → checkpoint-store probe → main run → status), checks
each step and stops on the first failure. The store probe refuses an S3 endpoint that ignores `If-Match`, so
fencing cannot silently be off in production. Tested against the Docker cluster, including a drained node, too
few healthy nodes and a second launch. See `README.md` "Starting production".

## Where the review is right, and what stays open

- **No GPU evidence yet** for the DeepSpeed path. T16 (FSDP2) and T23 (fp16 bit-equal resume) run only on
  Kaggle (2 GPUs); that run is pending.
- **No real S3 bucket yet.** Every S3 test runs against the moto emulator. To do on the week-2 bucket: the
  whole suite with `V5_TEST_REMOTE=s3://…`, T26 first (does the cloud answer 412 as the emulator does).
- **Simulated numbers are not GPU goodput.** Stall and commit times from the Docker cluster are CPU numbers.
- **DeepSpeed world-size change** is refused, not done: converting with `ds_to_universal.py` is an operator
  step, not automatic.
- The review's own validation file says the P tests were "not independently replayed". To replay:
  `python -m pytest -q support/tests/test_ckpt.py` from `teams/07-infrastructure` (CPU, about 17 minutes with
  DeepSpeed installed), and `python support/simulation/run_sim.py` (Docker, about 30 minutes).

## Two corrections to the review text

- `02_SOURCE_CODE_REVIEW.md` section C has lost text: rows 13/14 and 20/21 of table A are merged, and items 9–11
  of section C are cut off. Worth regenerating before it is cited.
- The proposed unified boundary keeps "S for Week 1 correctness" of the checkpoint. S is a single-process local
  checkpoint; P is multi-rank with a fenced remote commit and both backends. Suggest P's `ckpt/` as the
  checkpoint base, with S's negative tests and L's DCP experiment kept as extra evidence.
