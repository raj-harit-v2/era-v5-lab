# Checkpoint design (V5 main run)

Team 07, Infrastructure. Status: **v0**, written in week 1, moved here from `support/docs/checkpoint_design.md`
for Gate 2 (the week plan names this path). Section 13 (the save time) is filled in week 2.
Code: [`../ckpt/ckpt.py`](../ckpt/ckpt.py), tests [`../support/tests/test_ckpt.py`](../support/tests/test_ckpt.py). Related: [ADR 0001](../adr/0001-checkpoint-format-and-commit.md) (decisions, contracts, metrics; it wins where this draft differs), [ADR 0002](../adr/0002-job-queue-slurm.md) (queue) and `../health/`.

## 1. Goal

The run can stop at any moment (GPU fault, node loss, spot reclaim, walltime, NaN, operator stop) and continue
**with no lost work beyond the last checkpoint and no silent change in what is trained**.

A checkpoint is good only if all four hold:

1. **Complete.** It holds every piece of state that changes the next step (Section 3).
2. **Verified.** Every file matches its sha256 in a manifest, and "latest" never points at a partial save.
3. **Exact.** After a restore, the loss on the same batch is **bit-equal** to the loss the run would have produced.
   The week-1 pass test: a restore on CPU gives a bit-equal loss.
4. **Cheap.** Training stalls only for the GPU→host copy. Writing, hashing and uploading run in the background.

Why it matters: compute = GPUs × days × peak × MFU × **goodput**. The reference run in Session 15 lost 5.6% of its
time to 38 interruptions, at 45 min mean time to recover. Llama 3 had 466 interruptions in 54 days. One lost
day is 3.3% of a 30-day run.

## 2. What V4 did, and what we change

V4 saved every 500 steps or 30 min, whichever came first, handled SIGUSR1 (save and stop), SIGUSR2 (save and
continue) and the spot 2-minute notice, uploaded in a separate process and kept the last 3 checkpoints. We keep all
of that. We change five things, each tied to a V4 failure:

| V4 behaviour | What went wrong or could | V5 change |
|---|---|---|
| "Latest" = highest step found in the S3 listing; a local dir is reused if it exists | The step-3009 checkpoint was damaged during save; a partial upload or download can be picked | Atomic commit: a manifest with per-file sha256; the `latest` pointer is written **last**, only after verification (§5) |
| Resume checked by eye: "loss close to ~7.x, no spike" | Small state errors pass unseen | Automated **bit-equal** test (§9) |
| CUDA RNG saved for the current device only | Other devices' dropout and sampling streams are lost | RNG for every device, plus sampler state (§3) |
| Converter wrote weights under the wrong names; load did not check | **Silent misload**: step-1 loss 2.95 instead of 2.55, after five cheap checks passed | Strict name/shape/dtype load on every path, plus a step-1 loss check against the manifest (§6) |
| Two stacks (cu128 pins vs cu130 nightly + S3 tarball) | flash-attn version drift on a new machine | Image digest and library versions in the manifest; restore refuses a mismatch unless overridden (§6) |
| One node, fixed world size | — | V5 is multi-node: per-rank shards, **resharding on load** when the world size changes after a node is lost |

## 3. State inventory

"A checkpoint without a data position is incomplete" (Session 6). Everything below goes into one checkpoint:

| State | Sharded? | Why |
|---|---|---|
| Model weights (bf16) and fp32 master weights | yes (ZeRO / FSDP) | the model |
| Optimizer state: Adam m and v (fp32), step count | yes | momentum; without it the resumed run is a different run |
| LR scheduler state | no | warmup/decay position |
| Gradient scaler state (if fp16 or fp8 scaling) | no | loss-scale history |
| RNG: Python, NumPy, torch CPU, **CUDA for every local device** | per rank | dropout, sampling, any stochastic op |
| Data position: sampler epoch, shard index and offset per pool, **ledger offset** | per rank + global | exact next batch (Session 6 ledger) |
| Skip list: batches skipped after a rollback | no | a rerun must skip the same batches (Session 15) |
| Run identity: run_id, branch_id (resume / replay / fork), global step, tokens seen | no | audit |
| Code and environment: git sha, image digest, torch/CUDA/NCCL/kernel versions, config hash | no | refuse a silently different stack |
| Frozen-weight hashes (when layers are frozen) | no | frozen weights must not change (Session 15 §12) |
| Health at save: last loss, grad norm, held-out loss if computed | no | step-1 check after restore |

Not saved: gradients (they are recomputed every step), activations, NCCL state.

## 4. Size and layout

**Size.** Training state = **16 bytes per trained weight**: bf16 weight 2 + bf16 grad 2 + fp32 master 4 + Adam
m and v 8. Gradients are not saved, so a checkpoint is about **14 bytes per trained weight** plus 2 per frozen
weight.

| Model (total params) | Checkpoint ≈ 14 B/param | Per GPU at 64 GPUs |
|---|---|---|
| 30B | 420 GB | 6.6 GB |
| a frontier-size MoE | several TB | over 100 GB |

The final V5 numbers wait for the model configuration, which freezes on 3 November.

**Format.** We use `torch.distributed.checkpoint` (DCP), not a single `torch.save` and not a DeepSpeed-only
format:

- each rank writes only its own shards, in parallel, with no gather to rank 0 (V4's "one rank OOM during gather"
  failure cannot happen);
- the files are **resharded on load**, so a checkpoint saved on 64 GPUs loads on 56 GPUs or on 1 CPU;
- `async_save` stages to host memory and returns, so training continues while the writer runs.

**Directory layout** (the same on local NVMe and in S3):

```text
<run_id>/
  step_000012500/
    __0_0.distcp … __N_0.distcp      # DCP shard files, one or more per rank
    .metadata                        # DCP index (tensor → file, offset, shape)
    extra/rank_00000.json …          # per-rank RNG + sampler state
    MANIFEST.json                    # written last, see below
  step_000013000/ …
  latest                             # one line: "step_000013000", written after the manifest verifies
```

`MANIFEST.json`:

```json
{
  "format": "v5-ckpt/1",
  "run_id": "...", "branch_id": "...", "step": 13000, "tokens_seen": 0,
  "world_size": 64, "parallel": {"dp": 8, "ep": 8, "zero_stage": 3},
  "files": [{"path": "__0_0.distcp", "bytes": 0, "sha256": "..."}],
  "data": {"ledger_offset": 0, "skip_list": []},
  "env": {"git_sha": "...", "git_sha_source": "git", "code_sha256": "...", "image_digest": "...", "torch": "...", "cuda": "...", "nccl": "..."},
  "checks": {"loss_at_save": 0.0, "probe_batch_loss": 0.0, "frozen_hashes": {}},
  "created": "ISO-8601", "save_seconds": {"stall": 0.0, "write": 0.0, "upload": 0.0}
}
```

`probe_batch_loss` is the loss of one fixed, held-out probe batch, computed with the weights being saved. After a
restore we compute it again; the two must be **bit-equal**. This catches a silent misload in one forward pass.

## 5. Save protocol

```text
 training step k finishes
   │
   ├─ 1. DECIDE   rank 0 decides (timer, step, signal, spot notice) → broadcast → all ranks agree
   │              (V4's guard against one rank entering a barrier alone)
   ├─ 2. GUARD    loss/grad finite?  no → do NOT save; log, stop, print the exact resume command
   ├─ 3. STAGE    DCP async_save: copy shards GPU→pinned host RAM      ← the only training stall
   │              training resumes at step k+1
   ├─ 4. WRITE    background: host RAM → local NVMe  step_k.tmp/  → fsync files + dir
   ├─ 5. SEAL     hash every file → MANIFEST.json → fsync → rename step_k.tmp → step_k   (atomic)
   │              local `latest` ← step_k
   ├─ 6. UPLOAD   separate uploader process: files first, MANIFEST.json last, to S3
   └─ 7. COMMIT   uploader re-reads the S3 object sizes/checksums against MANIFEST
                  → writes S3 `latest` ← step_k → emits "checkpoint.committed" event (eval/quant pick it up)
```

Rules:

- **Only one save in flight.** If step 3 comes up while the previous checkpoint is still in steps 4–7, the new
  save waits for it. We never drop a save and never run two writers.
- The uploader is a **separate process**, as in V4, so S3 threads cannot starve the training process. It ignores
  SIGUSR1 and SIGUSR2.
- A checkpoint counts as **committed only after step 7**. Restore code reads `latest`, never a directory listing.
- A failed upload is retried with backoff. After N failures we page, and training continues; local NVMe still
  holds the checkpoint.
- **Emergency save** (spot notice, `--signal=USR1@120`): steps 1–5 synchronously, then exit with code 75
  (requeue). The upload resumes on the next node from the copy on the shared S3 path, or from local NVMe if
  the same node comes back.

## 6. Restore protocol

```text
 1. LOCATE   read `latest` (local NVMe if same node and it matches S3 `latest`, else S3)
 2. FETCH    parallel download of shard files (many files → many streams; V4 cut cold start to 10–15 min this way)
 3. VERIFY   sha256 of every file == MANIFEST            fail → try the previous committed checkpoint
 4. ENV      image digest / torch / CUDA / NCCL / kernel versions == MANIFEST
             mismatch → refuse, unless --allow-env-change is given and logged
 5. LOAD     DCP load into the current model + optimizer, resharding to the current world size
             STRICT: missing, unexpected, wrong-shape or wrong-dtype key → abort, listing every key
 6. STATE    restore scheduler, scaler, every RNG, sampler/ledger offset, skip list
 7. PROBE    recompute probe_batch_loss  ==  MANIFEST.checks.probe_batch_loss  (bit-equal)
             frozen-weight hashes == MANIFEST
             fail → abort with both numbers printed (this is V4's silent misload, 2.95 vs 2.55)
 8. GO       log "resumed run_id/branch_id at step k, ledger offset o, next batch id b"
```

When the world size changes (a node was lost and we continue on fewer GPUs), steps 5–7 still hold.
Continuing training is then **not** bit-equal to the original run, because the gradient reduction order changes.
The restore log says so, and the branch is marked `resume-resharded`.

## 7. When to save

**Interval.** `interval = min(Young, eval cadence, RPO cap)`, with Young = √(2 × stall × MTBF). Only the
**stall** counts, because training continues during the background write. Published failure rates scaled to our
likely size (64–256 GPUs) give an MTBF of 39–790 h, so Young's formula alone would allow 1–5 h. Failure rate is
therefore not the binding term; eval cadence and the most work we accept losing per failure are. **Start value:
30 min** (RPO ≈ 15 min; V4 used min(500 steps, 30 min), the S15 reference run 25 min). It is revisited after the
dry runs with measured stall and MTBF (ADR 0001 §4, §10). The interval must also exceed the background pipeline
time (steps 4–7), or saves queue up.

**Triggers,** all feeding one handler:

| Trigger | Source | Action | Exit code |
|---|---|---|---|
| periodic | rank-0 timer or step count | save, continue | — |
| SIGUSR2 | operator | save, continue | — |
| SIGUSR1 / SIGTERM | operator, health drain, spot watcher (`scancel --signal=USR1`); Slurm preemption (SIGTERM, then `GraceTime`) | save, wait for the commit, stop | 75 (requeue) |
| spot notice | the cloud's instance metadata service `spot/instance-action`, polled every 5 s | emergency save, stop | 75 |
| health fail | `health/` check between steps (Xid 79/94/95, ECC) | save if the GPUs still answer, stop | 75, node drained |
| NaN / Inf | loss or grad-norm guard | **no save**; log, stop | 78 (fatal, held) |
| run done | max steps | final save, protected | 0 |

The exit-code contract (0 done, 75 retry, 78 fatal) is what the queue uses to requeue or hold (`RequeueExit=75`, `RequeueExitHold=78`). See ADR 0001 §6 and ADR 0002 §5.

## 8. Retention and storage

| Tier | Keeps | Why |
|---|---|---|
| Local NVMe | last **2** committed + any in flight | fast same-node restart; NVMe must hold 3 × per-node share |
| S3 Standard | last **3** committed + **protected**: every N-th (for evals and the paper), the final one, any checkpoint pinned by an operator | a damaged checkpoint must have a good one before it (V4 step 3009 → 2909) |
| Archive tier | protected ones older than X days (lifecycle rule) | cheap long-term record; the data team already plans the archive tier for shards |

Deleting is a separate job that never touches a protected checkpoint or the one `latest` points to. Disk-full on
save was a V4 failure, so before a save starts we check free NVMe space ≥ 1.2 × checkpoint size.

## 9. Bit-equal determinism: what it needs

The pass test holds only if the step is deterministic for a fixed world size:

- `torch.use_deterministic_algorithms(True)`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`, cuDNN deterministic and
  benchmark off (on GPU; free on CPU);
- seeded, **stateful** sampler: the next batch is a function of (seed, epoch, offset), never of wall-clock or
  worker timing; data-loader workers seeded from (seed, rank, worker id);
- every RNG saved and restored (§3);
- the same world size and reduction order for continuation tests.

**Week-1 tests** (`support/tests/test_ckpt.py`, CPU only, gloo backend; T1–T10 pass, see ADR 0001 §Validation):

| # | Test | Pass |
|---|---|---|
| T1 | Run A: K+M steps straight. Run B: K steps → save → **new process** → restore → M steps. Same world size (1, then 4 ranks) | loss at every step of B's M == A's, bit for bit (`==` on the float, not "close") |
| T2 | Save on 4 ranks (sharded, ZeRO-style optimizer shards) → restore on **1 CPU process** | `probe_batch_loss` bit-equal to the value at save |
| T3 | Flip one byte in one shard file | restore refuses at VERIFY and falls back to the previous checkpoint |
| T4 | Kill the process between WRITE and SEAL | `latest` still points at the previous checkpoint; the prefix without a manifest is ignored and removed by retention |
| T5 | Rename one key in the state (the V4 converter bug) | strict LOAD aborts and names the key |
| T6 | Send SIGUSR1 mid-run | save completes, exit code 75, T1 still passes after the restart |
| T7 | Inject NaN | no checkpoint written, exit code 78 |

Week 2 (GPU node): the same tests on CUDA, plus measured stall, write and upload times for a randomly
initialised model of the final shape. You don't need a trained model to measure checkpoint speed (Session 15).

## 10. Failure modes covered

| Failure (seen in V4 or the course) | Covered by |
|---|---|
| Checkpoint damaged during save (V4 step 3009) | atomic SEAL, sha256 VERIFY, keep ≥ 3, fall back |
| Silent misload: wrong names, random weights (V4) | strict LOAD + bit-equal PROBE |
| Save code crashes after hours of training | T1–T7 run in CI before any long run; the save path runs at step 1 of every job |
| Disk full | free-space check before save; retention job |
| Hang from save + compress + upload at once (V4) | uploader in a separate process; one save in flight |
| One rank OOM / bad gather of ZeRO shards (V4) | DCP per-rank write, no gather |
| Frozen layer breaks the save, or a frozen weight changes | optimizer state only for trainable params; frozen-weight hashes |
| Library drift on a new node (V4 flash-attn) | ENV check against the manifest; pinned image |
| Wrong batch after resume or rollback | sampler + ledger offset + skip list in the checkpoint; T1 |
| Timer drift → one rank alone in a barrier (V4 fix) | rank-0 decision broadcast |
| Kill lands at step 3005 when the checkpoint is 3000 | the ledger offset is authoritative, not the step counter |
| NaN checkpoint overwrites a good one | NaN guard: never save |

## 11. Interfaces to other teams

| Team | Gets | Contract |
|---|---|---|
| 8 Monitoring | events `checkpoint.started`, `.committed`, `.failed`, with `save_seconds` | JSON line on the training log stream |
| 9 Evaluation, 12 Quantization | the S3 path of each committed checkpoint | trigger on `checkpoint.committed`; read-only; never on the training node |
| 6 Performance | stall-time budget | stall ≤ 2% of the interval |
| 1/2 Data | ledger offset + skip list format | the Session 6 ledger fields |
| 5 Architecture | list of trainable vs frozen params, parallel layout | needed for the strict-load key list |

## 12. Open questions (for the lead and the instructor)

1. Final parallel layout (ZeRO-2 on 32 GPUs or ZeRO-3 on 8, from S12; expert-parallel degree): this sets the shard
   count per node and the NVMe size.
2. S3 bucket, prefix and cloud role for the training cluster. Who can delete?
3. "Every N-th protected": N in steps or tokens? The eval team should say what cadence it needs.
4. Does the instructor's submit system restart jobs itself, or should Slurm requeue (exit 75)?
5. Spot or on-demand for the main run? Spot makes the emergency-save path the common path.

## 13. Save time (Team 6 input)

Section D of the week-2 plan. Team 6 gives the measured save time on Fri 13 Nov; it goes here with the command,
the checkpoint size and the machine, and is compared with the stall budget in section 11 (stall ≤ 2% of the
interval) and the interval in section 7.

| Input | Value | Source |
|---|---|---|
| Save time (stall, then background commit) | _pending, Fri 13 Nov_ | Team 6 |
| Checkpoint size per rank | _pending, config v1 (Sat 14 Nov)_ | Team 5 config v1, [parallel_layout_v0.md](parallel_layout_v0.md) |
