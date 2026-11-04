# Health baseline job (`jobs/health_baseline/`)

Job request: [../2026-11-01-health-baseline.md](../2026-11-01-health-baseline.md) (format: [JOB_REQUEST.md](../../../JOB_REQUEST.md)).
Decision record: [ADR 0003](../../adr/0003-node-health-checks.md), "baseline method". Health checks:
[../../health/README.md](../../health/README.md).

> **In one paragraph.** The health check needs real numbers before it can judge a node: how fast is a healthy
> node's all-reduce, and what do its ECC counters, temperature and Xid log look like? ADR 0003 says to run
> `--mode full` at least five times on a known-good node and take the median. This job does that with **one
> command**, checks the result against what a healthy node must show, and asks Team 08's validator whether every
> report follows `v5-health/1`.

## Start command

From the repository root (the job writes only to `./out/`):

```bash
bash teams/07-infrastructure/jobs/health_baseline/run.sh
```

Options: `--runs N` (default 5), `--gpus N` (default: what `nvidia-smi -L` lists), `--out DIR` (default `./out`).
Exit code 0 means every expectation was met and the validator passed.

Needs `python3` with `pyyaml`, and `torch` (a CUDA build when the node has 2 or more GPUs). No network, no keys.

## What it does

| Step | What | Output in `out/` |
|---|---|---|
| 1 | `health/gpu_health.sh --mode full` five times (the `v5-health/1` producer; includes the four collectives) | `health_run1.json` … `health_run5.json` |
| 2 | `health/xid_scan.py` on its own | `xid_scan.json` |
| 3 | `health/allreduce_test.py` on its own, one rank per GPU (all-reduce, reduce-scatter, all-gather, all-to-all) | `allreduce.json` |
| 4 | `summarize_baseline.py`: join the reports, check `expected_results.json`, compute the baseline | `node_health.jsonl`, `baseline_summary.json`, `results_check.txt` |
| 5 | Team 08's validator (`teams/08-monitoring/health-check/health_check.py`) on every report and the Xid output; the ClickHouse row mapping | `validation.txt`, `clickhouse_rows.jsonl` |
| | machine description, log, exit codes | `env.txt`, `run.log`, `exit_codes.txt` |

`state/` and `events/` hold the scratch files of the health scripts. They normally write to `/var/lib` and
`/var/log`; the job moves them under `out/` because jobs may only write there.

**The GPU count picks the mode:**

| GPUs | Mode | What you get |
|---|---|---|
| 2 or more | `full`, NCCL | the real baseline: busbw per collective and size |
| 1 | `prolog`, no collectives | GPU count, ECC, temperature, Xid, host checks. **No bandwidth baseline**: a collective needs 2 or more ranks |
| 0 | `full`, gloo on CPU | a smoke test that proves the pipeline works. The numbers are not a GPU baseline |

## Expected results

Rules, in machine-readable form: [expected_results.json](expected_results.json). On a known-good node:

| Item | Expected |
|---|---|
| verdict of each run | `pass`, `admit_training` true |
| `gpu_inventory` | `pass`, count equals the GPU count |
| `ecc_uncorrectable` | `pass`, 0 on every GPU |
| `gpu_temperature`, `pcie_link`, `gpu_throttle` | `pass` (idle GPU). A narrow PCIe link or hardware slowdown is a `warn` and fails the expectation |
| collectives (2+ GPUs) | all four `pass`, backend `nccl`, world size = GPU count, `max_error` 0, `busbw` > 0 |
| `xid` | `pass` (no Xid), or `skipped` if the kernel log is unreadable (see below) |
| `nvlink`, `remapped_rows`, `dcgm_diag`, `clock_offset`, `nvme_free` | `pass` or `skipped` (a PCIe-only card has no NVLink; `dcgmi`, `chronyc` and `/nvme` may be absent) |
| `host_mem` | `pass` |
| run to run | busbw spread (max − min) / median ≤ 10 % for messages ≥ 64 MB. Larger is a **warning**: 0.9 × median is then not a safe floor |
| Team 08 validator | `PASS` for every report |

There is deliberately **no expected bandwidth number**: it is what the job measures.

A sample of what `results_check.txt` looks like on a pass (CPU smoke run, gloo; bandwidth is not meaningful there):

```text
baseline summary: host=… profile=cpu (expected_gpus=0) runs=5
verdicts: pass, pass, pass, pass, pass
  nccl_all_reduce        largest size 16 MiB: busbw median … GB/s (min …, max …, spread …%, floor …)
NOTE: backend is gloo on a CPU host: the bandwidth numbers prove the pipeline works but are NOT a baseline for GPU nodes
RESULT: all expectations met
```

## From the result to `thresholds.yaml`

`baseline_summary.json` lists, per collective and message size, the min, median and max busbw and
`floor_0p9` = 0.9 × median (ADR 0003). Two things to know before copying numbers:

- `thresholds.yaml` has `baseline_busbw_gbps: {size_bytes: median}`, one number per size, but the four collectives
  differ in busbw. Decide the mapping (for example one entry per collective) when you fill it in.
- **No code reads that key yet.** `allreduce_test.py` has a `--floor-gbps` option, but `health_check.py` does not
  pass it. Filling in the baseline does not enforce a floor until that is wired.

## Xid on a runner

`xid_scan.py` reads the kernel log with `journalctl -k`, or `dmesg -T` if that fails. A job runner often cannot:
no permission (`dmesg` is root-only on many systems; `journalctl -k` needs root or the `adm` / `systemd-journal`
group), or a container with no access to the host's kernel log. Then the Xid check reports **`skipped`**, with
`source: null`. That is deliberate: **skipped means "could not look", not "no errors"** (a missing tool is never a
pass). The job accepts it, writes a NOTE in `results_check.txt`, and `baseline_summary.json` has
`"xid_visible": false`. If Xid matters for the run, rerun as root.

The job starts with a fresh state folder, so run 1 reports every Xid line in the kernel log since boot as new and
runs 2–5 report only new ones. A node with an old, harmless Xid 13 therefore shows a `warn` in run 1 only, and the
expectation "verdict `pass`" fails: look at `health_run1.json` to decide whether the node is really known-good.

## Files

| File | What |
|---|---|
| `run.sh` | the one start command |
| `expected_results.json` | what a healthy node must show, per profile (`cpu`, `gpu1`, `gpu`) |
| `summarize_baseline.py` | joins the reports, checks the expectations, computes the baseline (standard library only; also usable on an `out/` folder copied back from the node: `python summarize_baseline.py --out out`) |
| `README.md` | this file |

Reused unchanged from `../../health/`: `gpu_health.sh`, `health_check.py`, `xid_scan.py`, `allreduce_test.py`,
`thresholds.yaml`. The job needs the whole `teams/07-infrastructure/` folder (`health_check.py` imports `common/`
and `queue/`) and `teams/08-monitoring/health-check/` beside it.

## Test log

Run on CPU (gloo, 5 runs): 5 of 5 reports `PASS` in Team 08's validator, "all expectations met", about 2 minutes.
Run on 2 GPUs (NCCL): add your log here.
