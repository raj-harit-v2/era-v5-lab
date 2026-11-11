# Restore test

## What it proves

A training run restored from one of our checkpoints continues exactly as if it had never stopped:
the save, the restore and the restart lose no work and change no numbers. This is the core evidence for
the week-2 goal (save, restore, restart with no lost work) and for Gate 2.

- **Model and data:** Team 05's tiny MoE harness (`teams/05-architecture/harness/train.py`,
  `configs/config_v0.yaml` + `configs/small/tiny_moe.yaml`, seed 1234). The script imports `TinyMoE` and
  `stream_for()` and uses Team 05's loss and optimizer step unchanged. Team 05's files are not edited.
- **Checkpointing:** our `ckpt/ckpt.py` (`Checkpointer.save` / `Checkpointer.restore`), not a plain `torch.save`,
  so the test proves our code: checksums, strict key check, state digest, probe loss and data position are all
  checked on restore.

## What it does

| Run | What happens |
|---|---|
| A | train step 1 to 200 with no stop; save a checkpoint after step 100 |
| B, first launch | train step 1 to 150, save after step 100, then the processes exit |
| B, second launch | new processes restore B's step-100 checkpoint and train step 101 to 200 |

Then, for every step 101 to 200, it compares run A with run B:

- `loss_ntp` and `loss_mtp` (the next-token and the t+2 loss): **bit-equal**, no tolerance;
- the batch data ID: `{"position": <global batch number>, "sha256": <hash of the batch tokens>}` (the
  loader contract's `next_batch_id()`), so the data stream resumed at the right position.

A step is one optimizer step: "step 100" means 100 steps are done, which is how the Checkpointer numbers a save.
With more than one device each step's loss is the mean over the ranks.

## How to run

Needs torch 2.14.1 or newer (the script stops with a clear message on older torch: it uses DDP's
`init_sync` and `forward_sync_buffers`), numpy, pyyaml and Team 04's `kronecker_embeddings` package
(Team 05's model imports it). Team 04's requirements file pins all of them:

```
pip install -r teams/04-ke2/src/requirements.txt
```

One command, no GPU, no network:

```
python teams/07-infrastructure/jobs/restore_test/restore_test.py              # 1 CPU process
python teams/07-infrastructure/jobs/restore_test/restore_test.py --nproc 2    # 2 CPU processes (gloo, DDP)
python teams/07-infrastructure/jobs/restore_test/restore_test.py --nproc 2 --device cuda   # 2 GPUs (NCCL)
```

The script starts its own processes (no `torchrun`). Run A and run B always use the same `--nproc`.

| Flag | Default | Meaning |
|---|---|---|
| `--nproc` | 1 | number of devices: CPU processes, or GPUs with `--device cuda` |
| `--device` | cpu | `cpu` or `cuda` |
| `--steps` | 200 | last step |
| `--save-at` | 100 | checkpoint step; the comparison starts at the step after it |
| `--stop-at` | 150 | where run B's first launch stops |
| `--out` | `out/` next to this script (git-ignored) | the only folder the script writes to |
| `--config`, `--tiny` | Team 05's files | model and data settings |

## Expected output

The last line is one of:

```
PASS restore_test nproc=1 cpu: steps 101-200: loss_ntp and loss_mtp bit-equal, data ids equal
FAIL restore_test nproc=1 cpu: steps 101-200: first difference at step 137 in loss_ntp_bits: a=<bits> b=<bits>
FAIL restore_test: a run crashed: <error>
```

Exit code: `0` PASS, `1` a difference, `78` a run crashed (for example a checkpoint failed its restore checks).
With `--nproc 2` on CPU, gloo prints a few `[Gloo] Rank ...` lines first. A 1-process CPU run takes about 15 s.

Files in `out/`:

| File | What |
|---|---|
| `result.json` | `pass`, `first_diff`, the settings, and every step of run A and run B (losses, loss bits, data ID) |
| `run_a.jsonl`, `run_b_before_stop.jsonl`, `run_b_after_restore.jsonl` | the raw per-step rows of each launch |
| `ckpt_store/`, `ckpt_local/` | the checkpoints (the store is a plain folder) |
| `events/` | the Checkpointer's events (`checkpoint.committed`, `restore.done`, ...) |

`out/` is cleared of old checkpoints at the start of each run, so a restore never picks up an old run.

## Test results (1 Nov 2026)

Own machine, torch 2.14.1, Python 3.13, the real `kronecker_embeddings` (Team 04's pinned commit), default
settings (200 steps, save at 100, stop at 150), run with every Python warning shown (`-W default`): no warnings.

| Command | Result | Exit | Time |
|---|---|---|---|
| `--nproc 1` (CPU) | PASS, steps 101-200 bit-equal, data IDs equal | 0 | about 14 s |
| `--nproc 2` (CPU, gloo) | PASS, steps 101-200 bit-equal, data IDs equal | 0 | about 17 s |
| `--nproc 1 --device cuda` (1 GPU) | PASS, steps 101-200 bit-equal, data IDs equal | 0 | about 16 s |
| `pytest support/tests/test_ckpt.py -k restore_job` | 2 passed (1 and 2 processes) | 0 | about 25 s |

`loss_ntp` of run A:

| Run | Step 1 | Step 100 | Step 200 |
|---|---|---|---|
| CPU, 1 process | 4.31079626 | 0.03366756 | 0.01066788 |
| CPU, 2 processes | 4.31079578 | 0.03366755 | 0.01066788 |
| 1 GPU | 4.31079626 | 0.03366745 | 0.01066785 |

Step 1 on one CPU process equals the first-step loss in Team 05's own evidence
(`teams/05-architecture/experiments/evidence/result.txt`, 4.31079626), so the script trains Team 05's model and
data as Team 05 does. The last bits differ between CPU, 2 processes and GPU; that is expected, and the test only
compares run A with run B on the same device and process count.

A second CPU run on Windows 11 (native PowerShell, not WSL) also passes on 1 and 2 processes, with
`pytest ... -k restore_job` giving 2 passed: see `results/restore_test_cpu_windows.txt`. The Linux CPU run is in
`results/restore_test_cpu.txt`.

The test can fail: with the optimizer state dropped on purpose after the restore (a local change, not in this
folder), it prints `FAIL ... first difference at step 12 in loss_ntp_bits` and exits 1, on 1 and 2 processes.

## What a FAIL means

- A difference at step 101: the data position, the weights or the random state did not come back.
- A difference at step 102 or later with step 101 equal: something the next step uses, for example the
  optimizer state, did not come back (the loss of step 101 is computed before its optimizer step).
- A different `batch_id`: the data stream resumed at the wrong position.

## Test

`support/tests/test_ckpt.py::test_restore_job` runs the same script with 20 steps (save at 10, stop at 15) on
1 and 2 processes, and checks that the stream loader passes `ckpt/loader_contract.py`. It is skipped when
`kronecker_embeddings` is not installed.
