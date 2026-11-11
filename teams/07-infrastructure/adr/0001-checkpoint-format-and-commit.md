# ADR 0001: Checkpoint format, commit protocol and restore checks

- Status: Proposed
- Date: 2026-10-27 (revised from 2026-10-25; second revision after the week-1 review, see [review_week1.md](../support/docs/review_week1.md))
- Area: Checkpoint (`ckpt/ckpt.py`, `support/tests/test_ckpt.py`, `support/simulation/trainer/train.py`, `docs/checkpoint_design_v0.md`)
- Related: ADR 0002 (queue, exit codes, events), ADR 0003 (health, hang policy), ADR 0004 (cost, metrics)

> **In simple words.** Training costs money every hour. A checkpoint is a saved copy of the training, so
> if a machine breaks we continue from the copy instead of starting again. This ADR decides how to save
> (quickly, without stopping training for long), how to make sure a copy is complete and correct before
> we trust it, and how to prove a restore gives exactly the same training as before.

## Context

The lab's goal for Team 07: the cluster saves, restores and restarts the main run with no lost work.
Interruptions are routine at scale. The Session 15 reference run had one every 12.9 h and lost 5.6% of its
time; Llama 3 had 466 in 54 days. Every hour lost to a bad restart is paid for and trains nothing (ADR 0004).

V4 used DeepSpeed checkpoints. Its code picks "latest" as the
highest step in an S3 listing, has no checksums, saves the CUDA RNG of the current device only, and checks
resume by eye. During the run V4 hit:

- a checkpoint damaged during save (step 3009, rolled back to 2909);
- a silent misload: a converter wrote wrong names, the load left weights random, and five cheap checks still
  passed (step-1 loss 2.95 against 2.55);
- library drift on a new machine.

V5 is larger and multi-node, so the world size changes when a node is lost. Several teams read checkpoints
(Teams 09, 11, 12), and several write state we save (Teams 01/02 data loader, 04 KE2, 05 architecture,
06 kernels). The architecture team's `config_v0.yaml` fixes `run.seed=1234` ("two runs with this seed must
match"), `attention.impl=eager` (fast attention backward does not repeat), `run.grad_clip=1.0` and AdamW.
Model sizes and precision are still open (TSAI fills them on 31 Oct).

## Decision drivers

1. A restore must be provably exact. The week-1 pass condition is **bit-equal loss on CPU**.
2. A partial or damaged checkpoint must never be picked.
3. The stall per save is small, and the work (money) lost per failure is bounded.
4. A checkpoint must load on a different number of GPUs, and on one CPU process.

## Options considered

| Option | For | Against |
|---|---|---|
| A. `torch.save` of a gathered state dict on rank 0 | simple; one file | gathers several TB on one rank (V4's OOM-during-gather); no parallel write; slow |
| B. DeepSpeed `save_checkpoint` (V4) | proven in V4; sharded | tied to DeepSpeed's engine and ZeRO stage; resharding needs `zero_to_fp32`; no integrity layer |
| C. **`torch.distributed.checkpoint` (DCP) plus our own manifest and commit layer** | every rank writes in parallel; **reshards on load** to any world size, including 1 CPU; works with FSDP2 and DDP; no engine lock-in | newer API; the manifest/verify layer is our code |
| D. Megatron distributed checkpoint | reshards; used at scale | brings in Megatron-Core, which we may not use |

> **In simple words.** We pick C: PyTorch's own sharded format, where every GPU writes its own part at
> the same time, and the checkpoint can later be loaded on a different number of GPUs. On top we add a
> small "receipt" (the manifest) that lists every file and its checksum.

## Decision

**C. DCP for the tensor data, wrapped in a commit protocol we own.**

### 1. State saved

- Model weights (fp32 master weights), including frozen tensors and buffers.
- Optimizer state (AdamW moments and step), scheduler and gradient scaler.
- **Every** RNG: Python, NumPy, torch CPU, and CUDA for each local device.
- Data position: the loader's ledger offset and the rollback skip list (the offset is the authority, not the step).
- Identity: run id, branch id, step, tokens seen.
- Environment: git sha, image digest, torch, CUDA, NCCL, tokenizer hash, **config sha256**, **`OMP_NUM_THREADS`**.
- Hashes of frozen tensors (KE2 tables).

Not saved: gradients, activations, NCCL state.

> **Found in the simulation.** On CPU, `OMP_NUM_THREADS` changes the last bits of the loss even with
> `torch.set_num_threads(1)`: torchrun sets it to 1, a plain launch does not, and the two runs differed from
> step 16. The thread count is therefore part of the environment; job scripts set it, and a mismatch refuses
> to resume.

### 2. Save protocol

> **In simple words.** Training pauses only for the quick copy to local disk. The upload to S3 runs in the
> background. The checkpoint "counts" only when every file is in S3 *and* re-checked; the receipt is written
> last, and only then does the `latest` pointer move. If anything dies halfway, the pointer still shows the
> previous good checkpoint.

1. Rank 0 decides when to save, and all ranks agree in one all-reduce (a stop signal on any rank counts).
2. A NaN/Inf guard runs first: a bad state is never saved (exit 78).
3. A free-space check: free NVMe must be ≥ 1.2 × this node's share of the last checkpoint, or the save is
   skipped with `checkpoint.failed cause=nvme_full` (alert CK-03).
4. **Stall:** on **every rank together**: the NaN check, the state fingerprint (§8), the probe-batch loss and
   the loader position. Under FSDP the probe forward and the fingerprint are collectives, so none of them may run
   on rank 0 alone (it would wait forever for the others; review finding, week 1). Then `dcp.async_save` copies
   each rank's shard to host RAM and returns: that copy is the end of the stall. DCP writes the files to
   node-local NVMe from a background thread, on a separate **gloo** process group so it never shares NCCL with
   training. The fingerprint is integer sums on the GPU (milliseconds); there is no sha256 of the state on the
   stall path. `V5_ASYNC_SAVE=0` falls back to the blocking `dcp.save` (used to compare stall times).
   **We hand `async_save` our own copy of every CPU tensor.** DCP's staging moves tensors to host memory, but a
   tensor already on the CPU is passed through without a copy (torch 2.5.1), so the background writer would
   read weights the optimizer keeps changing, and the files would hold a later state than the recorded digest.
   Found by the `kill_during_save` drill in run 13: the newest commit failed its own restore proofs (CK-05) and
   the job fell back one checkpoint. Fixed with `own_cpu_copies()`; T27 reproduces the race. GPU tensors are
   copied by DCP itself (to be confirmed on Kaggle).
5. **Background:** each rank waits for its DCP write to finish, then uploads its own files to `s3://…/<run>/<branch>/step_<N>-e<epoch>/` through `ckpt/store.py`
   (boto3: multipart above 64 MB, 16 parallel parts, standard retry mode for `503 SlowDown`). Each object
   carries its sha256 in metadata and S3 verifies a SHA256 checksum on upload. Then the rank writes
   `sums_rank<r>.json`.
6. Rank 0 waits for every rank's sums, re-checks every object in S3, writes `MANIFEST.json` **last**, then moves
   `latest.json` **with a conditional write** (fencing, below) and appends to `commits.jsonl`, and emits
   `checkpoint.committed` (ADR 0002 §8).
   Re-check mode `V5_VERIFY_MODE`: `full` re-reads and hashes every object (tests, small checkpoints);
   `head` compares the checksum S3 stored at upload, which costs no download (TB-size checkpoints).

**One interface, two stores; nothing assumes a cloud** (`ckpt/store.py`). The store is chosen by the path:
- **a shared file system (the default):** a plain path such as `/shared/ckpt` on a file system every node mounts
  (NFS, Lustre, GPFS, CephFS). This is the bare-metal case and needs nothing beyond POSIX. Files are written to a
  temporary name, `fsync`ed and renamed; fencing (below) uses an exclusive-create lock file, which these file
  systems make atomic.
- **an S3-compatible object store (optional):** `s3://bucket/prefix`, any store that speaks the S3 API (a
  self-hosted one such as MinIO, or a cloud's). It adds checksums verified by the store and conditional writes.

`launch/launch.sh` runs `ckpt.py probe-store` on whichever store is configured: a store that cannot refuse a stale
write stops the launch. Every unit test runs on the folder store, the checkpoint tests also on an S3 emulator, and
the whole Docker drill set runs on either (`run_sim.py --store folder` / `--store s3`). On S3 there is no append: `commits.jsonl` is read, extended and written back **only if nobody wrote it in
between** (`If-Match`), else read again, so two writers never lose each other's line.

**Fencing: only one attempt may commit.**

> **In simple words.** Slurm can believe a job is dead while it still runs: a node loses its network, Slurm
> requeues the job, then the network comes back. Now two copies of the run train and save. Without a guard,
> the old copy could commit after the new one and move `latest.json` back, or the two could write files into the
> same folder. So each attempt takes a ticket number (the *epoch*) when it starts, and the pointer only accepts
> writes from the newest ticket.

- On start, before it reads anything, the attempt **claims** the run: it writes `latest.json` with `epoch + 1`,
  only if `latest.json` is still the version it read (`If-Match` on the S3 ETag; `If-None-Match: *` for a new
  run). If two attempts claim at the same moment, exactly one wins; the other stops (`FencedError`).
- Every commit writes `latest.json` only if it is still the version **this attempt** last wrote. After a newer
  claim it is not, so the old attempt's commit is refused: `checkpoint.fenced`, then it exits **78**
  (`FencedError`: hold, never requeue; a newer attempt already owns the run). Its sealed folder is never pointed
  to and retention removes it.
- Each attempt writes into its own folders, `step_<N>-e<epoch>`, so two attempts never overwrite each other's
  files, even at the same step.
- One object is the lock and the pointer at once, so there is no gap between "check the lease" and "move the
  pointer". The folder store does the same with an `O_EXCL` lock file and a sha256 as the version.
- S3 conditional writes (`If-Match` on PutObject) exist since Nov 2024; boto3 ≥ 1.35.69 sends them. The emulator
  enforces them from moto 5.1.10 (older moto silently ignores `If-Match`, so a test on it would pass falsely).

> **Node-local disk is a cache, never a copy that counts.** A node's local NVMe can be wiped when the node stops
> (on a cloud: including Slurm power-saving) or is replaced, and on bare metal a dead node takes its disk with it.
> A restore always works from the shared store; the local copy only saves a download when the job comes back on
> the same, still-running node.

S3 has no rename, so there is no `.tmp` directory: a prefix without a manifest is simply not a checkpoint.
The retention job (§5) deletes such orphans after one hour, because they are billed like any other object.
Only one save is in flight at a time; a save that has to wait for the previous one is counted (CK-10).

### 3. Restore protocol

> **In simple words.** We never guess which checkpoint is newest by listing folders. We follow the pointer,
> check the receipt, and then prove that what we loaded is exactly what we saved. If the newest checkpoint
> fails a check, we fall back to the one before it automatically.

1. Claim the run (fencing, §2). Then read `latest.json`; never list directories. Fallback order comes from
   `commits.jsonl`.
2. Check every file against the manifest checksums (rank 0), then copy it to local NVMe once per node.
3. Check the environment; a mismatch refuses (exit 78) unless `--allow-env-change` is given, which is logged.
4. **Strict key check:** every missing, extra, wrong-shape or wrong-dtype key aborts, and all of them are listed.
5. DCP load (reshards to the current world size), then RNG, data position and skip list.
6. Run the **checks in §8**. A damaged file or a failed check falls back to the previous commit; a strict-key or
   environment error does not (every checkpoint would fail the same way) and exits 78.

### 4. Interval

```text
interval = min( Young(stall, MTBF), eval cadence, RPO cap )
Young    = √(2 × stall × MTBF)
```

> **In simple words.** Saving often costs a little on every save; saving rarely costs a lot on every failure.
> Young's formula finds the balance. With today's failure rates the balance point is far (hours) for small
> clusters, so in practice the cap on how much work we accept losing decides.

`support/cost/cost_model.py` computes this per model size and cluster size (ADR 0004). With the S15 failure rate and
8 nodes, Young gives 3–17 min (1B–30B parameters). With 2 nodes the **30-min RPO cap** binds for 7B and up.
**Start value: 30 min**, or Young when Young is shorter. Revisit after the dry runs with measured stall and MTBF.

Work lost per failure: on average **interval/2 + stall** (≈ 15 min). The worst case is
**interval + commit latency** (≈ 40 min), when the failure hits just before a commit finishes. Signals that
give warning (preemption, spot notice, health drain) trigger an **emergency save**, so they lose ≈ 0 (§6).

### 5. Retention and storage

> **In simple words.** Storage costs money every month, so we keep only a few recent checkpoints, plus
> the ones we can never re-buy. Only a separate job may delete, so a bug in training can never wipe them.

| Tier | Keeps |
|---|---|
| Local NVMe | last 2 committed (fast restore on the same node) |
| S3 Standard | last 3 committed + **protected**: every N-th (Team 09 sets N), the final one, any pinned (`ckpt.py pin`) |
| Archive tier | protected checkpoints older than X days (≈ 6× cheaper per GB-month) |

- S3 **versioning** on, plus a lifecycle rule that aborts incomplete multipart uploads after 1 day.
- **Second copy of protected checkpoints:** S3 Replication to a bucket in a second region, filtered on the tag
  `v5:protected=true` (set by `ckpt.py pin` and by retention when it marks a checkpoint protected). Deletes are
  not replicated, so a wrong delete in the main bucket cannot remove the copy.
- Delete permission belongs **only** to the retention job's cloud role (`ckpt.py retention`, ADR 0002 §7).
- Retention never deletes a protected checkpoint or the one `latest.json` points to (CK-15 is HIGH).

### 6. Exit codes (shared with ADR 0002 and 0003)

> **In simple words.** One number tells Slurm what to do next: done, run again, or wait for a person.

| Code | Meaning | Slurm |
|---|---|---|
| 0 | done | complete |
| **75** | retry: the state is safe (just saved, or nothing to save); requeue, possibly on another node | `RequeueExit=75` |
| **78** | fatal: NaN, **loss spike**, failed checks, strict-load or environment error; retrying will not help | `RequeueExitHold=78`: hold and page |
| anything else | unexplained crash (exit 1, SIGKILL 137, segfault 139) | the job wrapper turns it into 75, or 78 after 3 crashes in 30 min |

**Loss-spike guard** (added after the week-1 review). A NaN check does not see a model that diverges with finite
numbers. If the loss is above **1.5 × the median of the last 100 steps** for **3 steps in a row**, the trainer
stops with 78, and **no checkpoint is written while a spike is in progress**, so `latest` stays before the spike.
The operator then rolls back (§9). Thresholds are flags (`--spike-ratio`, `--spike-steps`) and get tuned on the
dry runs; T12 checks that 300 normal steps never trip it. Metric H-24 (HIGH).

Changed from the first draft, which used 1 for fatal: an uncaught Python error (for example from
`TORCH_NCCL_ASYNC_ERROR_HANDLING`, ADR 0003 §2) also exits 1, and most of those are one-off faults worth one retry.

### 7. Contracts with other teams

| Team | Contract |
|---|---|
| 01/02 Data | the loader exposes `state_dict()` / `load_state_dict()` returning JSON-serialisable state, and `next_batch_id()` with a content hash of the next batch. The state is **one global ledger offset + the skip list + `manifest` (sha256 of the shard list), identical on every rank**; `load_state_dict` raises `ValueError` for a state saved on another manifest, and the restore then holds the job (`DataManifestError`, exit 78) instead of continuing on other data (millermuttu's field, team 07) (each rank derives its slice from it); no per-rank positions. Reason: after a resharded restore every new rank loads old rank 0's state. The checkpointer checks this at every save (`loader_global` in the manifest) and refuses to reshard a checkpoint that fails it (`ReshardError`, exit 78); `ckpt/loader_contract.py` tests it, including a resume at another world size |
| 05 Architecture | every tensor is trainable, frozen or a buffer, with a stable name. The parallel layout is given: ZeRO/FSDP stage, expert-parallel size. **Experts are stored by global expert id** (DTensor or an explicit index), so the checkpoint reshards when the EP size changes. Reversible models keep dropout at 0 |
| 05 Training loop | the trainer calls `save()` only **between optimizer steps**, never between micro-batches of one step. With gradient accumulation (DeepSpeed `gradient_accumulation_steps` > 1) a stop signal is acted on at the next boundary (`engine.is_gradient_accumulation_boundary()`), so half-accumulated gradients never need saving. The stall budget (≤ 2 %) covers the extra wait of up to one step |
| 04 KE2 | Kronecker tables and other non-trained tensors are declared frozen buffers and hashed in the manifest. **A save is refused** (`FrozenChangedError`, exit 78) if one changed since the last restore or save, so the bug that trained it shows at once, not at the next restore. The embedding policy is part of the environment check (`V5_EMBEDDING_POLICY_ID`): another policy refuses to resume, even with the same shapes (both from millermuttu's design, team 07) |
| 05 + 06 Kernels | **every kernel has a deterministic mode**: no unordered atomics, a fixed reduction order, deterministic reversible recompute. Resume tests and the CI restore probe run in deterministic mode; production may run fast mode. A kernel without a deterministic mode is flagged in its docstring and in the manifest |
| 06 Performance | owns the **GPU-to-host stall time** against our budget (≤ 2% of the interval); Team 07 owns correctness |
| 09 Eval, 12 Quant, 11 Release | each reads the S3 path from `checkpoint.committed`, read-only, never on a training node. **Team 07 owns the `dcp → safetensors` export**, with the same strict-key and probe-loss checks: **bit-equal** when the dtype is unchanged; a dtype change (quantization) belongs to Team 12, which states its own tolerance |
| 08 Monitoring | ships `checkpoint.*`, `restore.*` and `export.*` events and pages on the HIGH alerts in ADR 0004 |

### 8. Restore checks

> **In simple words.** Four independent proofs that the restored training is the saved training. Any one
> failing stops us from continuing on a wrong model, which is how V4 wasted a run.

| Check | Rule |
|---|---|
| **State digest** | a fingerprint of every **logical** tensor (weights, optimizer, buffers): two sums mod 2³¹−1 over the raw bits, each word weighted by its position in the full tensor. Each rank adds its own shard (DTensor offset from its placement; a replicated or DDP copy is added once), then one all-reduce. The sum does not depend on how the tensor is split, so it **must be equal** at the same and at another world size. Then one sha256 over name, dtype, shape and fingerprint of every key. A moved, swapped or flipped value changes it (T14, T17) |
| **Probe loss** | loss of one fixed held-out probe batch, in deterministic mode, stored **per device class** (`cpu`, `cuda:<model>`) because CPU and GPU arithmetic differ; compared as raw float bits, not rounded |
| **Next batch** | `next_batch_id()` and its content hash equal the saved ones |
| **Frozen hashes** | the same logical fingerprint of each frozen tensor equals the manifest |

Any failure prints both values, emits `restore.failed`, and the next attempt uses the previous commit.

### 9. Rollback (operator action, not crash resume)

One job script supports `--from-step K --skip N --branch <id>`: it restores step K, adds the next N batch
ids to the skip list, and continues on a new branch. The run can therefore be replayed exactly later
(Session 6: resume / replay / fork). The simulation does this after the NaN drill.

### 10. Metrics

All checkpoint metrics, with LOW / MEDIUM / HIGH thresholds, are in `metrics/catalog.yaml` (CK-01 … CK-20)
and in [metrics_catalog.md](../support/docs/metrics_catalog.md). The ones that page immediately (HIGH):

| ID | Metric | HIGH when |
|---|---|---|
| CK-01/02 | Time / node-hours at risk since the last commit | ≥ 2 × interval |
| CK-03 | Consecutive failed saves | ≥ 2 |
| CK-04 | Checksum mismatch | any |
| CK-05 | Restore check failure | any |
| CK-06 | Strict-load or environment refusal | any |
| CK-07 | NaN guard trip | any |
| CK-08 | Save stall | ≥ 5% of the interval |
| CK-13 | Restore time | ≥ 30 min |
| CK-15 | Protected checkpoint missing | any |

Targets: mean work lost ≤ interval/2 + stall; RTO ≤ 15 min; commit latency ≤ 10 min; stall ≤ 2% of interval;
0 restores from an uncommitted checkpoint; export probe bit-equal.

## Consequences

Good:

- A half-written or damaged checkpoint cannot be chosen, and a bad newest checkpoint falls back by itself.
- A silent misload fails within one forward pass, with both numbers printed.
- A checkpoint saved on 4 ranks restores on 2 or 1 (tested), so losing a node does not stop the run.
- A warned interruption (preemption, spot, health drain) loses ≈ 0 work thanks to the emergency save.
- Other teams get one checked export format.
- Two live copies of one run (split brain) cannot both commit: the older one is refused and stops (T24–T25).

Bad and accepted:

- **Host RAM:** async staging needs pinned host memory for one per-node shard.
- **Kernel cost:** every custom kernel needs a deterministic mode (extra work for Teams 05/06, and slower).
- **Resharded continuation is not bit-equal:** after a world-size change the reduction order changes. The
  restored state is still digest-checked, and the branch is marked `<branch>-resharded-w<N>`.
- **Probe per device class:** the first save on new hardware records its own value (CK-20).
- **Extra code:** we own the manifest, verify, commit, retention and export code, and their tests.

## Validation

`python -m pytest support/tests/test_ckpt.py` runs on CPU, with gloo for more than one rank, inside the
`v5-slurm-sim` image. **On 2026-10-30 (T1–T30 and the other suites): 63 pass with the local store and the 34
checkpoint tests pass with `V5_TEST_REMOTE=s3://…` against the S3 emulator (moto 5.1.10); only the GPU tests T16
and T23 skip, they run on Kaggle.**

| Test | What it does | Result |
|---|---|---|
| T1 | straight run vs save → new process → restore, on 1 and 2 ranks: loss bit-equal at every step; digest and next batch checked | pass |
| T2 | save on 4 ranks, restore on 1: digest equal, CPU probe bit-equal, marked resharded | pass |
| T3 | one flipped byte in the newest checkpoint: verify fails, previous checkpoint used | pass |
| T4 | process dies after the upload, before the manifest: `latest.json` unchanged; retention removes the orphan | pass |
| T5 | renamed key (the V4 converter bug): strict load aborts and names both keys | pass |
| T6 | SIGUSR1 to one of 2 ranks: all ranks save, exit 75; continuation bit-equal to a run never stopped | pass |
| T7 | NaN: no save, exit 78 | pass |
| T8 | export to safetensors: strict keys pass, probe loss bit-equal | pass |
| T9 | a changed config refuses to resume (78); `--allow-env-change` resumes and logs it | pass |
| T10 | rollback `--from-step K --skip 3 --branch b1` | pass |
| T11 | loss × 10 for 5 steps (no NaN): no save during the spike, exit 78, `latest` before the spike | pass |
| T12 | 300 normal steps never trip the spike guard | pass |
| T13 | the data-loader contract (`ckpt/loader_contract.py`) that Teams 01/02's real loader must pass | pass |
| T14 | fingerprint of a tensor split into uneven row shards (FSDP) or column shards (tensor parallel), for fp32/bf16/fp64/bool/int64 = fingerprint of the full tensor; a swapped row or one flipped bit changes it | pass |
| T15 | a loader whose state differs per rank fails the contract ("must be one global ledger offset") | pass |
| T16 | **FSDP2** (`fully_shard`) on 2 GPUs: save does not hang; restore at 2 ranks and resharded at 1 rank pass every check | GPU only: runs on Kaggle (2 GPUs) |
| T17 | real DTensors on 2 and 3 gloo ranks (uneven `Shard(0)`, `Shard(1)`, `Replicate`): digest = single-process digest | pass |
| T18–T23 | the DeepSpeed backend (ZeRO-1/2/3 resume, fallback, world change, export, fp16): see `support/docs/deepspeed_impact.md` §1.12 | pass (T23 GPU only) |
| T24 | split brain in one process: attempt B claims the run; A's next commit is refused, the pointer stays B's, A's step is not in the history, B commits its own step in its own folder | pass |
| T25 | the same end to end: trainer A commits every step, trainer B starts on the same run; A exits 78 (`FencedError`), no A commit lands after B's claim | pass |
| T26 | the store operations, on the folder store and on S3 (moto): a write against an old version loses; 6 writers × 10 appends lose no line; 4 attempts claiming at once never share an epoch | pass |
| T28 | a frozen table changed by training: the next save is refused (`FrozenChangedError`), `latest.json` keeps the good step; the same after a restore in a fresh process | pass |
| T29 | another `V5_EMBEDDING_POLICY_ID`: resume refused (78) naming `embedding_policy_id`; the original policy resumes | pass |
| T30 | a loader on another shard list: restore refused (`DataManifestError`); the loader contract requires the `manifest` field | pass |
| T27 | async save on CPU with a slow writer, weights changed right after `save()` returns: the checkpoint still restores exactly what was saved (fails without `own_cpu_copies`) | pass |

Simulation drills that exercise the checkpoint in Slurm (ADR 0002 §10): kill **during** a save (the half-uploaded
checkpoint is never used), kill **during** a restore (the next attempt restores the same checkpoint cleanly),
restore onto a smaller world, retention and export, all against the S3 emulator.

The same code runs inside the Docker Slurm cluster in `support/simulation/run_sim.py` (ADR 0002 §Validation).
GPU: `V5_DEVICE=cuda` runs T1–T10 with the trainer on CUDA in deterministic mode (`CUBLAS_WORKSPACE_CONFIG` set),
and `support/tools/bench_save.py` measures the GPU-to-host stall and `dcp.async_save` times. Both run on Kaggle (2 GPUs) via
`support/kaggle/run_gpu_checks.py` (see `support/kaggle/README.md`). Week 2: the same on the GPU node for a randomly initialised
model of the final shape.

## Open points

- **Sharded state, partly tested:** the digest is checked on real DTensor shards (T17, CPU) and the whole save →
  reshard → restore path under FSDP2 runs as T16 on Kaggle (2 GPUs). Expert parallel and Team 05's real model wait
  for week 2. FSDP2 needs CUDA in torch 2.5, so the Docker cluster (CPU) still trains with DDP.
- Real S3 throughput and `head` verification on a multi-GB checkpoint (week-2 node; the emulator is in-memory).
  Run T26 once against the real bucket too (`V5_TEST_REMOTE=s3://…`), to confirm the cloud answers 412 the way the
  emulator does; `launch.sh` runs `ckpt.py probe-store` on it before every launch.
- Parallel layout: ZeRO-2 on 32 GPUs or ZeRO-3 on 8, and the EP degree. This sets the per-node share and the NVMe size.
- Protected cadence N (Team 09).
- The RPO cap the instructor accepts (start: 30 min).
- Model size and precision (config_v0.yaml, 31 Oct), which set the checkpoint size and stall.
