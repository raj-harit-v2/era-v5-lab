# Restore time

Times `Checkpointer.restore()` (claim, checksums, download, load, the four proofs) so the numbers in
the G7 runbook in [`docs/`](../../docs/) (section 7, restore time) can be reproduced. The restore test
(`jobs/restore_test/`) proves a restore is exact; this one measures how long it takes.

## What it measures

| Part | What | Source of the numbers |
|---|---|---|
| `tiny` | Team 05's tiny MoE, via `jobs/restore_test/restore_test.py`, 1 and 2 CPU processes (1 process with `--device cuda`) | rank 0's `restore.done` event: `verify_s`, `download_s`, `load_s`, `checks_s`, `restore_s`, and the whole-script wall time |
| `sweep` | a **synthetic** model: 8 square linear layers of width 512, 1024, 2048, 4096 plus AdamW state (so the checkpoint is 3 times the weights): 25, 101, 403 and 1,611 MB | the same phases, and `Checkpointer.restore()` timed end to end (claim included), from a cold node-local folder |

Each setting runs `--reps` times (default 9); the JSON has the median, minimum and maximum.

## How to run

Same requirements as the restore test (`pip install -r teams/04-ke2/src/requirements.txt`, torch 2.14.1 or newer).
No network. About 4 minutes on a laptop CPU. From `teams/07-infrastructure/`:

```bash
python jobs/restore_time/restore_time.py --note "<machine, cores, memory>"
python jobs/restore_time/restore_time.py --parts sweep --device cuda --note "1 GPU"      # GPU: sweep only
```

| Flag | Default | Meaning |
|---|---|---|
| `--parts` | `tiny,sweep` | which parts to run |
| `--device` | `cpu` | `cpu`, or `cuda` (1 GPU) |
| `--reps` | 9 | repetitions per setting |
| `--widths` | `512,1024,2048,4096` | sweep sizes; 4096 needs about 2 GB of RAM and 3 GB of free disk |
| `--note` | empty | free text naming the machine |
| `--out` | `out/restore_time.json` next to the script (git-ignored) | **the only file written** |

The checkpoints are written to a temporary folder that is deleted before the script exits, so `out/` holds the
JSON only (a few KB), far below the 50 MB limit of a returned folder. Exit 0 when every restore passed its own
checks; any failed restore or restore test stops the script with a message.

## Output

`restore_time.json` (`schema: restore-time/1`): `device`, `reps`, `note`, Python, torch and platform versions,
the GPU name on `cuda`, and per setting `{median, min, max, n}` in seconds for each phase, `ckpt_bytes`, and for
the sweep `restore_total_s` (claim + restore, end to end).

## What it does not represent

- **Synthetic sizes.** The sweep sizes are not real model sizes; read them as a size axis only.
- **No remote store.** The store is a folder on the local disk with a warm page cache. A shared file system or
  S3 adds network time; `download_s` here is a local copy.
- **One thread per process, one process** in the sweep. The four proofs are compute-bound, so a GPU run will
  differ (the `cuda` option is for that; it has not been run on a GPU yet).
- **Not CK-13.** CK-13 is job start to the first productive step, including start-up, imports, building the
  model and the first step. `restore()` is only part of it.
