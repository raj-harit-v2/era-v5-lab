# Checkpoint (`ckpt/`): how we save training so we never pay for the same work twice

Decision record: [ADR 0001](../adr/0001-checkpoint-format-and-commit.md). Longer design notes:
[checkpoint_design.md](../support/docs/checkpoint_design.md). Queue side: [../queue/README.md](../queue/README.md).
Health side: [../health/README.md](../health/README.md).

> **In one paragraph.** Training costs money every hour. A checkpoint is a saved copy of the training, so if
> a machine breaks we continue from the copy instead of starting again. This folder decides **how** we save
> (fast, without stopping training for long), **how we know a copy is complete and correct** before we trust
> it, and **how we prove** that a restore gives exactly the same training as before.

---

## How it works, step by step

Plain-words overview and the reasons behind each choice: [team briefing §3.1](../TEAM_BRIEFING.md#31-checkpoints-save-commit-prove-adr-0001).
Every step names the function that does it (`ckpt/ckpt.py` unless noted), so you can follow it in the code.
DeepSpeed runs the same steps through `ckpt/ds_ckpt.py` (`DSCheckpointer`), with DeepSpeed writing the tensors.

**A. Start of every attempt: claim and restore** (`Checkpointer.restore`)

```text
1. claim()            write latest.json with epoch+1, only if nobody changed it since we read it
                      → from now on an older copy of this run cannot commit (fencing)
2. candidates()       latest.json first, then commits.jsonl newest → oldest (never "list folders")
3. for each candidate (_restore_one):
   a. checksums       every file in MANIFEST.json against its sha256            ✗ → try the previous commit
   b. environment     image, torch/CUDA/NCCL, config, tokenizer, embedding policy, threads (+ DeepSpeed config)
                                                                                 ✗ → stop, exit 78 (EnvMismatchError)
   c. download        to node-local NVMe, each copy re-checked                   ✗ → try the previous commit
   d. strict keys     every name, shape and dtype matches the model             ✗ → stop, exit 78 (StrictLoadError)
   e. load            tensors (resharded if the number of GPUs changed), data position, random generators
                      other data list → exit 78 (DataManifestError); other GPU count with per-rank data → 78 (ReshardError)
   f. 4 proofs        state digest · probe-loss bits · next-batch hash · frozen fingerprints
                                                                                 ✗ → try the previous commit
4. nothing committed yet → fresh start at step 0;   every candidate failed → exit 78 (CheckpointError)
```

**B. Every save** (`Checkpointer.save`, then a background thread `_upload_and_commit`)

```text
in the training loop (training waits only for this part, "the stall"):
1. NaN/Inf anywhere in the state?                      yes → nothing saved, exit 78 (NonFiniteError)
2. enough free local disk?                             no  → save skipped, alert CK-03, training continues
3. fingerprints of the state and of frozen tensors; a frozen tensor changed?  yes → exit 78 (FrozenChangedError)
4. probe loss on the fixed batch; data position (must be the same on every rank)
5. copy the state to host memory (own copy of CPU tensors), start the write; training continues
in the background:
6. every rank: wait for its write, upload its files to the shared store (sha256 each), write sums_rank<r>.json
7. rank 0: wait for every rank's sums → re-check every stored file → write MANIFEST.json LAST
8. rank 0: move latest.json, only if this attempt still owns the run   another attempt owns it → FencedError,
                                                                       the job stops with 78, nothing moved
9. append the commit to commits.jsonl; event checkpoint.committed; keep the newest 2 local copies
```

**C. On a stop signal** (preemption, spot notice, health drain, time limit): the trainer finishes its step, saves
(B), waits for the commit, exits **75**; Slurm restarts it and it continues at A.

**D. Around the run**

| When | What | Command / function |
|---|---|---|
| before the run | the store refuses a stale write (else fencing cannot work) | `ckpt.py probe-store --run <run>` (run by `ops/launch.sh`) |
| after a NaN or loss spike | restore an older step, skip some batches, continue on a new branch | `TRAIN_EXTRA="--from-step K --skip 5 --branch b1"` |
| daily, as its own job | delete old checkpoints, never protected / pinned / latest ones | `ckpt.py retention`, `run_retention()` |
| for Teams 09/11/12 | export one checked `safetensors` file | `export_safetensors()`, DeepSpeed: `ds_ckpt.export_ds()` |
| any time | list commits, verify files, pin a step | `ckpt.py list / verify / pin` |

---


## 1. Why this matters (the money view)

- A run with 8 GPU nodes uses 8 node-hours every hour; every minute lost is paid on all of them (ADR 0004).
- Interruptions are normal at this scale. The Session 15 reference run had one every ~13 hours; Llama 3 had 466
  in 54 days.
- On each interruption we lose **the work since the last checkpoint** plus **the restart time**.
- V4 (last year's run) showed three ways checkpoints go wrong:
  1. a checkpoint was **damaged during save** (step 3009) and had to be rolled back;
  2. a **silent misload**: weights were loaded under the wrong names, stayed random, and five quick checks
     still passed;
  3. **library drift** on a new machine changed the results.

Every rule below exists to stop one of these from costing money.

---

## 2. The big picture

```text
           training loop (every GPU = one "rank")
                         │
        every 30 min, or on a stop signal (preemption, spot notice, sick node)
                         │
   ┌─────────────────────▼──────────────────────┐
   │ 1. safety checks: no NaN? enough disk?      │  if NaN → do NOT save, exit 78 (wait for a person)
   │    ALL ranks: fingerprint, probe loss       │  (under FSDP these are collectives: never rank 0 alone)
   │ 2. STALL: copy state GPU → host RAM         │  ← the only part training waits for (dcp.async_save)
   └─────────────────────┬──────────────────────┘
                         │ training continues
   ┌─────────────────────▼──────────────────────┐   background threads
   │ 3. write shards to local NVMe (DCP, gloo)   │
   │    upload every file to S3 + SHA256         │
   │ 4. each rank writes sums_rank<r>.json       │
   │ 5. rank 0 re-checks every object in S3      │
   │ 6. rank 0 writes MANIFEST.json  (LAST file) │
   │ 7. move latest.json → this step, only if    │  ← only now does the checkpoint "count"
   │    no newer attempt claimed the run         │    (fencing, below)
   │ 8. append a line to commits.jsonl           │
   └────────────────────────────────────────────┘
```

**The key idea: the receipt is written last.** If anything dies halfway (power, kill, network), there is no
`MANIFEST.json` and `latest.json` still points at the previous good checkpoint. A half-written checkpoint can
never be picked.

**Only the newest attempt may commit (fencing).** Slurm can think a job is dead while it still runs (a node
loses its network, Slurm starts a new job, the network comes back). Then two copies of the run train and save.
So every attempt takes a ticket number, the *epoch*, before it restores: it writes `latest.json` with
`epoch + 1`, and S3 accepts that write only if `latest.json` has not changed since it was read (`If-Match`).
Every later commit is conditional the same way. After a newer claim, the old copy's next commit is refused, it
logs `checkpoint.fenced` and exits 78 (`FencedError`). It can never move the pointer back, and since each attempt
writes into its own `step_<N>-e<epoch>` folders, the two never mix files (tests T24–T26, drill `split_brain`).

---

## 3. What is in a checkpoint

Everything that changes the next training step, and nothing else:

| Part | Why |
|---|---|
| Model weights (and buffers) | obviously |
| Optimizer state (AdamW moments, step count) | without it the next steps differ |
| LR scheduler, grad-scaler | same |
| **Every random-number generator**: Python, NumPy, torch CPU, CUDA for every local GPU | dropout and sampling must repeat exactly (V4 saved only the current GPU's RNG) |
| Data position: ledger offset + skip list | resume on the exact next batch, not "about here" |
| Identity: run id, branch, step, tokens seen | which training this is |
| Environment: git sha, image digest, torch/CUDA/NCCL versions, tokenizer hash, **config sha256**, `OMP_NUM_THREADS` | a different software stack refuses to resume (V4's drift problem) |
| Hashes of frozen tensors (e.g. KE2 tables) | prove they did not change |

Not saved: gradients, activations, NCCL state. They are rebuilt on the next step.

> **Found in the simulation:** on CPU, `OMP_NUM_THREADS` changes the last bits of the loss. So the thread
> count is part of the environment: job scripts set it to 1 and the manifest records it.

### Where it lives

```text
<remote_root>/<run_id>/latest.json             pointer to the newest committed checkpoint, + the owning epoch
<remote_root>/<run_id>/commits.jsonl           every commit in order (restore never "lists folders")
<remote_root>/<run_id>/<branch>/step_<N>-e<E>/ DCP shard files, extra_rank<r>.json, sums_rank<r>.json, MANIFEST.json
```

`remote_root` is either a folder on a **shared file system** every node mounts (the default, `/shared/ckpt`:
NFS, Lustre, GPFS or CephFS, so it works on bare metal) or `s3://bucket/prefix` on any **S3-compatible object
store** (self-hosted or a cloud's; the Docker test also runs it through an S3 emulator). Nothing else in the
code depends on which one. The node's local NVMe holds a **cache** copy only: it can be wiped when a node stops
or is replaced. **The copy in the shared store is the only one that counts.**

---

## 4. Restore: how we prove we got back exactly what we saved

```text
latest.json ─► read MANIFEST ─► every file's sha256 matches? ─► environment matches? ─► strict key check
                                     │ no                          │ no (exit 78)          │ no (exit 78, lists keys)
                                     ▼                             ▼                       ▼
                         fall back to previous commit       person decides          person fixes the code
                                                         (--allow-env-change)
   ─► load (reshards to the current number of GPUs) ─► RNG + data position ─► 4 PROOFS (below)
```

The four proofs. **Any one failing stops us**, prints both values, and the next attempt uses the previous commit:

| Proof | Rule | Catches |
|---|---|---|
| **State digest** | a fingerprint of every **logical** tensor (each rank adds its shard, weighted by position in the full tensor; one all-reduce), must equal the saved one, at the same or another world size | a damaged, partial or wrongly resharded load |
| **Probe loss** | loss on one fixed held-out batch must be **bit-equal** (raw float bits, not rounded) to the saved value for this device class (`cpu`, `cuda:<model>`) | V4's silent misload |
| **Next batch** | hash of the next batch must equal the saved one | data loader resumed at the wrong place |
| **Frozen hashes** | each frozen tensor must match the manifest | a frozen table changed |

**Resharding:** a checkpoint saved on 4 ranks loads on 2 or 1 (tested). This is what lets the main run
continue after losing a node. A smaller world is not bit-equal going forward (the sum order changes), so the
run is marked `<branch>-resharded-w<N>`.

---

## 5. Exit codes: one number tells Slurm what to do

| Code | Meaning | What Slurm does |
|---|---|---|
| `0` | finished | job complete |
| `75` | "retry": state is safe (just saved, or nothing to save) | requeue, maybe on another node (`RequeueExit=75`) |
| `78` | "fatal": NaN, loss spike, failed checks, environment mismatch. Retrying will not help | **hold** and page a person (`RequeueExitHold=78`) |
| anything else | unexplained crash (1, 137, 139…) | the job wrapper turns it into 75; **3 crashes in 30 min → 78** |

Without Slurm (a single machine, the TSAI runner, the CPU tests), `ckpt/supervisor.py` applies the same rules
itself: it runs the trainer as a child process and starts the same command again after a `75` or a crash, so
the trainer restores the newest COMPLETE checkpoint (MANIFEST written, `latest.json` moved). It stops on `0`
and `78`, after **3 crashes in 30 minutes** (same `CRASHLOOP_N` / `CRASHLOOP_WINDOW_S` as the job wrapper),
after `--max-restarts` crashes (default 10) and after `--max-stops` exits 75 (default 100; 75 is the normal
time-limit path, so it has its own larger limit). A stop signal (SIGTERM, or Ctrl-C passed on as SIGTERM) is
passed to the trainer and no new trainer starts after it. It logs one JSON line per attempt (`--log`, and
`supervisor.*` events).
Proof: `jobs/restart_test/` (SIGKILL on CPU, equal loss), result in `results/restart_cpu.txt`.

```bash
RUN_ID=r1 V5_REMOTE_ROOT=/shared/ckpt python ckpt/supervisor.py --log out/supervisor.jsonl -- python my_train.py
```

### The two "do not save" guards

- **NaN guard:** checked before every save. A NaN/Inf state is never saved; exit 78.
- **Loss-spike guard:** loss > **1.5 × the median of the last 100 steps** for **3 steps in a row** → no save,
  exit 78. This catches divergence with finite numbers, which the NaN check cannot see. Flags:
  `--spike-ratio`, `--spike-steps`, `--spike-window` (tuned on dry runs). Test T12 shows 300 normal steps never
  trip it.

After a 78, an operator **rolls back** (§7). The held job's Slurm comment names the cause and the next step;
`python metrics/explain.py <cause>` explains any of them ([monitoring guide](../metrics/README.md)).

---

## 6. How often to save (the cost trade-off)

```text
interval = min( Young's formula, eval cadence, RPO cap )
Young    = √(2 × stall × MTBF)
```

- Saving often costs a small stall every time. Saving rarely costs a lot on every failure. Young's formula
  finds the balance.
- With today's numbers the cap on "how much work we accept losing" wins, so the **start value is 30 min**.
- Work lost per failure without warning: on average **interval/2 + stall (~15 min)**; worst case
  interval + commit time (~40 min).
- With a warning (preemption, spot notice, health drain) we do an **emergency save** and lose **~0**.
- `support/cost/cost_model.py` computes this for each model and cluster size.

---

## 7. Rollback (after a NaN or loss spike)

```bash
sbatch --export=ALL,TRAIN_EXTRA="--from-step 1200 --skip 5 --branch b1" slurm/mainrun.sbatch
```

It restores step 1200, skips the next 5 batches (the bad data), and continues on a **new branch** `b1`. The
old branch stays, so the run can be replayed exactly later. You can also restart on fewer nodes
(`sbatch --nodes=1 …`); the simulation tests both.

---

## 8. Retention: storage costs money every month

| Tier | Keeps |
|---|---|
| Node NVMe | last 2 committed (fast restore on the same node) |
| S3 Standard | last 3 committed + **protected** ones: every N-th (Team 09 sets N), the final one, any pinned |
| Archive tier | protected checkpoints older than X days (~6× cheaper) |

- Only the **retention job** may delete (its own cloud role). A bug in training can never wipe checkpoints.
- It never deletes a protected checkpoint or the one `latest.json` points to.
- Orphans (uploads with no manifest, from a crash) are deleted after 1 hour.
- Protected checkpoints are replicated to a second region; deletes are not replicated.
- S3 versioning is on.

---

## 9. Files in this folder

| File | What it does |
|---|---|
| `ckpt.py` | the `Checkpointer` (save, background upload and commit, restore with all checks), `run_retention`, `export_safetensors`, and a small CLI |
| `store.py` | one interface, two stores: `LocalStore` (a folder) and `S3Store` (boto3: multipart above 64 MB, retries, SHA256 checksums). `open_store("s3://…")` picks S3 |
| `supervisor.py` | restarts a killed or saved-and-stopped trainer from its last COMPLETE checkpoint, with crash, 75 and crash-loop limits; logs every attempt. Tests: `test_supervisor.py` |
| `loader_contract.py` | the test Teams 01/02's real data loader must pass: `state_dict` (**one global ledger offset, the same on every rank**), `load_state_dict`, `next_batch_id`, `add_skip`, and a resume at another world size |
In `support/` (optional): `tests/test_ckpt.py` (tests T1–T13, below), `tools/bench_save.py` (measures the real
stall on a GPU: GPU-to-host copy speed, sync and async save), and `simulation/trainer/train.py`, a tiny trainer
that follows every rule here (signals, watchdog, guards).

### Using the CLI

From `teams/07-infrastructure/`:

```bash
python ckpt/ckpt.py list      --run s3://v5-ckpt/ckpt/v5main          # committed checkpoints
python ckpt/ckpt.py verify    --run s3://v5-ckpt/ckpt/v5main --step 1200   # re-check every file
python ckpt/ckpt.py pin       --run s3://v5-ckpt/ckpt/v5main --step 1200   # protect from retention
python ckpt/ckpt.py retention --run s3://v5-ckpt/ckpt/v5main --keep 3 --dry-run
```

`V5_VERIFY_MODE=full` re-reads and hashes every object (tests, small checkpoints); `head` compares the
checksum S3 stored at upload and downloads nothing (TB-size checkpoints).

---

## 10. Tests (what each one proves)

| Test | What we do | What must happen |
|---|---|---|
| T1 | train, save, restore, continue (1 and 2 ranks) | loss **bit-equal** to a run that never stopped |
| T2 | save on 4 ranks, restore on 1 | digest equal, probe bit-equal, marked resharded |
| T3 | flip one byte in the newest checkpoint | verify fails, previous checkpoint used |
| T4 | die after upload, before the manifest | `latest.json` unchanged; retention removes the orphan |
| T5 | rename a key (V4's converter bug) | strict load aborts and names the keys |
| T6 | SIGUSR1 to one of 2 ranks | all ranks save, exit 75; continuation bit-equal |
| T7 | NaN | no save, exit 78 |
| T8 | export to safetensors | strict keys pass, probe bit-equal |
| T9 | changed config | refuses resume (78); `--allow-env-change` resumes and logs it |
| T10 | rollback `--from-step K --skip 3 --branch b1` | restores K, skips 3 batches, new branch |
| T11 | loss × 10 for 5 steps (no NaN) | no save during the spike, exit 78, `latest` from before |
| T12 | 300 normal steps | spike guard never trips |
| T13 | data-loader contract | our synthetic loader passes |
| T14–T17 | fingerprints of sharded tensors, FSDP2 (GPU), real DTensors | equal to the full-tensor fingerprint |
| T18–T23 | the DeepSpeed backend (`ds_ckpt.py`) | see `support/docs/deepspeed_impact.md` §1.12 |
| T24 | a second attempt claims the run while the first still trains | the first one's next commit is refused; pointer stays the second's |
| T25 | the same with two real trainer processes | the old one exits 78 `FencedError`; none of its commits land after the claim |
| T26 | conditional writes, folder store and S3 emulator | old version loses; 60 parallel appends lose no line; 4 claims at once never share an epoch |
| T27 | async save on CPU, slow writer, weights change right after `save()` | the checkpoint still restores exactly what was saved (we copy CPU tensors ourselves) |
| T28 | a frozen table changed by training | the next save is refused; `latest.json` keeps the last good step |
| T29 | another embedding policy | resume refused (78), naming `embedding_policy_id` |
| T30 | a loader reading another shard list | restore refused (`DataManifestError`) instead of training on other data |

Run them from `teams/07-infrastructure`:

```bash
# local folder store
docker run --rm -v "$PWD":/opt/v5:ro --entrypoint bash v5-slurm-sim:1 \
  -c 'cd /opt/v5 && python -m pytest -q -p no:cacheprovider -W ignore support/tests/test_ckpt.py'
# the same tests against S3 (moto emulator): see ../../support/README.md
# on a GPU (Kaggle): V5_DEVICE=cuda, see ../../support/kaggle/README.md
```

Result today: all pass on the folder store and against the S3 emulator.

### In the Docker Slurm simulation (run 9)

| Drill | Result |
|---|---|
| kill a process | restored from the last commit; lost 24–45 steps (the work since the last save) |
| preemption / spot notice / health drain | emergency save; **0 steps lost** |
| kill **during** a save | half-uploaded checkpoint never used; previous commit restored |
| kill **during** a restore | next attempt restores the same checkpoint cleanly |
| NaN, loss spike | nothing bad saved; job held; rollback on a new branch and on half the GPUs |
| retention, export | no protected checkpoint deleted; export probe bit-equal |

---

## 11. Metrics to watch

Full list with LOW / MEDIUM / HIGH thresholds: CK-01 … CK-20 in
[metrics_catalog.md](../support/docs/metrics_catalog.md). These page someone immediately (HIGH):

| ID | Metric | HIGH when | What to do |
|---|---|---|---|
| CK-01/02 | time / node-hours since last commit | ≥ 2 × interval | saves are not committing: check S3 and CK-03 |
| CK-03 | failed saves in a row | ≥ 2 | look at `checkpoint.failed` cause (`nvme_full`, upload error) |
| CK-04 | checksum mismatch | any | storage corruption: keep the checkpoint, investigate |
| CK-05 | restore check failure | any | read both printed values; the job already fell back |
| CK-06 | strict-load failure | any | the model code changed names: fix before restart |
| CK-07 | NaN guard | any | roll back (§7) |
| CK-08 | save stall | ≥ 5% of interval | Team 06: GPU-to-host copy too slow |
| CK-13 | restore time | ≥ 30 min | S3 throughput or checkpoint size |
| CK-15 | protected checkpoint missing | any | check retention and replication |

---

## 12. Contracts with other teams

| Team | Must give us |
|---|---|
| 01/02 Data | a loader that passes `loader_contract.py` (state save/load, next-batch hash, skip) |
| 05 Architecture | stable tensor names; the parallel layout; experts stored by global id |
| 04 KE2 | frozen tensors declared as buffers, so we hash them |
| 05/06 Kernels | a deterministic mode for every kernel (needed for bit-equal tests) |
| 06 Performance | owns the save stall time (≤ 2% of interval); we own correctness |
| 09/11/12 | read checkpoints read-only from the `checkpoint.committed` path; we provide the safetensors export |

---

## 13. Not tested yet (honest list)

- **Truly sharded state** (FSDP/ZeRO-3, expert parallel). The test trainer uses DDP, where every rank holds a
  full copy, so "4 ranks → 1" is the easy case. Needs Team 05's model (week 2).
- **Real S3 speed** on a multi-GB checkpoint (the emulator is in memory).
- **Real GPU stall**: `support/tools/bench_save.py` on Kaggle's GPUs now, the GPU node in week 2.
- Protected cadence N (Team 09), the RPO cap (instructor), model size (config due 31 Oct).

---

## 14. Words used here

| Word | Meaning |
|---|---|
| rank | one training process, usually one GPU |
| DCP | `torch.distributed.checkpoint`: every rank writes its own part in parallel, and it can load onto a different number of GPUs |
| manifest | the "receipt": list of every file with its sha256, written last |
| commit | the moment a checkpoint counts: manifest written, `latest.json` moved |
| stall | the time training waits during a save |
| bit-equal | exactly the same number, down to the last bit |
| resharding | loading a checkpoint onto a different number of GPUs |
| RPO | the most work we accept losing (here 30 min) |
| emergency save | a save triggered by a warning signal instead of the timer |
