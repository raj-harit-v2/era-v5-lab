# Runbook — Adinath (G7 rotation, Week 2)

Rotation member running the Gate-2 checkpoint tests **in full** on an independent machine, to confirm the
team's save / restore / restart evidence (#257, #258) reproduces on a different CPU and OS. Results only —
no code changed; Team 05's model/config files are untouched.

| | |
|---|---|
| Member | Adinath Auti — rotation, Team 07-infrastructure |
| Repo / commit | `theschoolofai/era-v5-lab` @ `c6b0ce0` (`main`) |
| Environment | Python 3.13.18, torch 2.14.1+cu130 (CPU, `cuda=False`), numpy 2.4.6, Linux-6.6.159 x86_64 (Colab), Intel Xeon CPU @ 2.20GHz |
| Model / data | Team 05 tiny MoE (`teams/05-architecture/configs/config_v0.yaml` + `configs/small/tiny_moe.yaml`, seed 1234); checkpoints via our `ckpt/ckpt.py` |
| Deps | `pip install -r teams/04-ke2/src/requirements.txt` |
| Evidence | Colab notebook `runbook_adinath_restore_test.ipynb` (CPU run log), not committed |
| Date | 2026-11-05 |

## 1. Restore test

A run restored from a step-100 checkpoint continues exactly as a run that never stopped. Run from the repo root,
CPU only (`CUDA_VISIBLE_DEVICES=""` hides any GPU; output goes to the git-ignored `jobs/restore_test/out/`):

```
CUDA_VISIBLE_DEVICES="" python teams/07-infrastructure/jobs/restore_test/restore_test.py            # 1 process
CUDA_VISIBLE_DEVICES="" python teams/07-infrastructure/jobs/restore_test/restore_test.py --nproc 2  # 2 processes (gloo, DDP)
```

**Result: PASS on 1 and 2 processes.** Steps 101–200 have `loss_ntp` and `loss_mtp` **bit-equal** (no tolerance)
and equal batch data IDs — the restore lost no work and changed no numbers.

| processes | last line | exit | wall time |
|---|---|---|---|
| 1 | `PASS restore_test nproc=1 cpu: steps 101-200: loss_ntp and loss_mtp bit-equal, data ids equal` | 0 | 39.2 s |
| 2 | `PASS restore_test nproc=2 cpu: steps 101-200: loss_ntp and loss_mtp bit-equal, data ids equal` | 0 | 43.9 s |

## 2. Restart test (SIGKILL)

A job killed with SIGKILL restarts from the last COMPLETE checkpoint with equal loss. Run from
`teams/07-infrastructure/`:

```
python jobs/restart_test/restart_test.py --run-id g7-restart-adinath-20261105-01 --device cpu
python queue/queue_rules.py check-out ./out --run-id g7-restart-adinath-20261105-01
```

**Result: PASS** (exit 0, 26.9 s). The trainer was killed with SIGKILL after step 140; the supervisor saw the
crash (attempt 0, exit −9), restarted once from the COMPLETE checkpoint at **step 125** (attempt 1, exit 0), and
steps **1–200 are bit-equal** to the uninterrupted run with equal data IDs.

`out/g7-restart-adinath-20261105-01/result.json` (sha256[:16] `993ed4afd95b0125`):

| field | value |
|---|---|
| status / exit_code | pass / 0 |
| bit_equal_steps | 200 |
| killed_after_step | 140 |
| restarted_from_step | 125 |
| pointer_step | 125 |

`queue_rules.py check-out`: **PASS — `./out` follows queue rules v1** (exit 0).

## 3. Conclusion

Both tests reproduce the team's Gate-2 restart/restore evidence (#258) independently on a Colab CPU, on a
different OS and CPU from the original run: checkpoints are captured, a killed run resumes from the last COMPLETE
checkpoint, and every step is bit-equal with no lost work. The run-ID follows the queue-rules naming
(`g7-<name>-<YYYYMMDD>-<NN>`) and passes `check-out`.
