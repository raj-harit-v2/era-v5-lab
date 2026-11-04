# Node health (`health/`): find broken GPUs before they waste paid hours

Decision record: [ADR 0003](../adr/0003-node-health-checks.md). Queue side:
[../queue/README.md](../queue/README.md). Checkpoint side: [../ckpt/README.md](../ckpt/README.md).

> **In one paragraph.** Most interruptions in big training runs come from broken hardware. A broken GPU either
> **crashes** the job (we pay for the restart and the lost work) or **quietly slows everyone down** (we pay for
> every slow hour, because all GPUs wait for the slowest one). So we check every node **before it gets a job**
> and **every 30 seconds** after. A bad node is taken out ("drained"), its job saves and moves to a healthy
> node, and a frozen job is restarted instead of sitting there burning money.

---

## How it works, step by step

Plain-words overview and the reasons behind each choice: [team briefing §3.4](../TEAM_BRIEFING.md#34-node-health-adr-0003).
Everything runs through `health/health_check.py` (`main()`), in one of three modes.

```text
when                         mode       runs                                                  on "fail"
before every job (prolog)    prolog     quick checks + vendor diagnostic level 1 (GPUs idle) Slurm drains the node, job
                                                                                              goes back to the queue
every 30 s (Slurm health)    periodic   quick checks + read the vendor's background health  drain the node itself
                                        (never the diagnostic: it would load busy GPUs)       (v5:<check>), its jobs
                                                                                              save and move (exit 75)
before a dry run / repair    full       quick checks + diagnostic level 2 + 4 collectives     ops/launch.sh drains it
                             (≤ 15 min)                                                        (health: <check>)

quick checks (every mode):
  gpu_checks()      GPU count · temperature · uncorrectable memory errors · hardware slowdown · PCIe width
  remap_checks()    failed / pending GPU-memory repairs (row remap)
  nvlink_checks()   any GPU-to-GPU link inactive
  xid_check()       new GPU driver error codes in the kernel log (fatal / restart / warn / unknown; each line once)
  clock_check()     clock offset ·  disk_mem_checks(): free local disk, free memory
collectives (full): allreduce_test.py → all-reduce, reduce-scatter, all-gather, all-to-all: exact values + speed

verdict():  any fail → fail ·  else any warn, or a required check "skipped" → warn ·  else pass
exit code:  0 pass, 3 warn, 4 fail   (prolog: warn exits 0, so a healthy node is never drained)
output:     one JSON report (schema v5-health/1) + a health.report event
```

A tool that is missing gives **skipped**, never pass. Xid 94 (a contained memory error) only warns the first time;
the same GPU logging it again within 24 h fails the node. Thresholds live in `health/thresholds.yaml`.

---


## 1. Why: where interruptions come from

Llama 3's 419 unexpected interruptions:

| Cause | Share | Caught here by |
|---|---|---|
| Faulty GPU | 30.1% | Xid scan, DCGM diag, ECC, GPU count, step watchdog |
| GPU memory (HBM) | 17.2% | ECC uncorrectable, row remapping, Xid 48/63/64/94/95 |
| Software | 12.9% | step watchdog, exit codes, crash-loop cap, loss-spike guard (restarted, not prevented) |
| Network | 8.4% | all-reduce test, NCCL flight recorder, NCCL error handling |
| Host maintenance | 7.6% | spot / scheduled-event watcher → drain + emergency save |
| Other (NIC, power, NCCL timeouts) | 22.4% | partly: watchdog, NCCL timeout |
| Silent data corruption | 1.4% | **not covered** (known gap) |

Storage slowness (9 of 38 interruptions in the S15 reference run) is **not** a health check: it is watched by
the data-wait and checkpoint-throughput metrics. V4 had **no GPU health check at all**.

---

## 2. When the checks run

```text
                 job about to start on a node
                            │
               ┌────────────▼────────────┐
               │ PROLOG  (--mode prolog)  │ ≤ 30 s
               └────────────┬────────────┘
             fail │                    │ pass / warn
                  ▼                    ▼
     Slurm drains the node,       job starts
     job goes back to the queue         │
     and starts elsewhere               │  every 30 s while the node is up:
                               ┌────────▼──────────────────┐
                               │ PERIODIC (--mode periodic) │ ≤ 30 s
                               └────────┬──────────────────┘
                                   fail │
                                        ▼
                       our check drains the node itself, then sends SIGUSR1
                       to its jobs → they SAVE, exit 75 → Slurm restarts them
                       on the hot spare from the checkpoint they just wrote
                       (work lost ≈ 0)

   FULL (--mode full, ≤ 15 min): before dry runs and after a repair; adds DCGM diag level 2
   and the all-reduce bandwidth sweep.
```

Two details that are easy to get wrong (both found while designing and testing):

- **In prolog mode a `warn` exits 0.** Slurm drains any node whose prolog exits non-zero, so returning "warn"
  as non-zero would take healthy nodes out. Only `fail` exits non-zero there.
- **Slurm ignores the periodic check's exit code**, so on `fail` the check drains the node itself
  (`scontrol update state=drain reason=v5:<checks>`) and asks its jobs to save (`queue/job_queue.py`).

---

## 3. What is checked

| Check | Source | Fail (drain) | Warn |
|---|---|---|---|
| GPU count | `nvidia-smi` | fewer GPUs than expected (8 on the GPU node) | — |
| ECC uncorrectable | `nvidia-smi` | ≥ 1 | — |
| ECC correctable | `nvidia-smi` | — | trend (3 × fleet median per 24 h, after baseline) |
| Temperature | `nvidia-smi` | ≥ 90 °C (vendor slowdown) | ≥ 85 °C |
| Hardware slowdown (throttle) | `nvidia-smi` | — | active |
| PCIe link width | `nvidia-smi` | — | below max (e.g. x8 of x16) |
| Row remapping | `nvidia-smi` | remap failed (replace the GPU) | remap pending (reset needed) |
| **Xid errors** | kernel log (`journalctl -k` / `dmesg`) | fatal codes | warn and unknown codes |
| DCGM diag | `dcgmi diag -r 1` in prolog only (level 2 in full): it loads the GPUs, so never during training | any failure | — |
| DCGM health | `dcgmi health -c` in periodic mode: reads DCGM's background watches, no load | `Failure` | `Warning`, or the tool errored |
| Clock offset | `chrony` | > 100 ms | > 50 ms |
| Free NVMe | disk | < need (≥ 1.2 × this node's checkpoint share) | — |
| Host memory | `/proc/meminfo` | — | below the pinned-memory need for async saves |
| All-reduce (full mode) | `allreduce_test.py` | wrong sum, timeout, bandwidth below floor | — |

Every threshold lives in **one file**, `thresholds.yaml`, with its source. Until the week-2 baseline exists,
they are vendor limits or warn-only.

### Xid codes (the GPU driver's error numbers)

When a GPU breaks, the driver writes `NVRM: Xid (PCI:…): <number>` into the kernel log.

| Class | Codes | Action |
|---|---|---|
| **fatal** | 48, 61, 62, 64, 74, **79** (GPU fell off the bus), 92, **95** (uncontained memory error), 119, 120, 140 | drain |
| **restart** | **63** (row-remap event), **94** (contained memory error) | warn the first time; the same GPU again within 24 h → fail (drain) |
| warn | 13, 31, 43, 45 (usually an application fault) | report |
| unknown | anything else | reported as warn, **never ignored** |

Xid 63 is a *successful* row-remap event (recoverable, needs a GPU reset); Xid 64 is the row-remap **failure**
(the GPU cannot repair its memory) and stays fatal. We store a hash of every Xid line already seen on the node,
so **an old error does not drain a repaired node again**.

### The all-reduce test, explained

Every GPU fills a tensor with the whole number `rank + 1` and all GPUs add them up. The answer must be exactly
`n(n+1)/2`. Whole numbers add exactly in fp32 **in any order**, so a wrong answer means broken hardware or
network, never rounding. It also measures **bus bandwidth** (`busbw = algbw × 2(n−1)/n`, the nccl-tests
convention) from 1 MB to 1 GB. A node below **0.9 × the baseline median** fails, because one slow node slows the
whole run. Without GPUs it runs on gloo (CPU) and says so.

---

## 4. Verdict and output

`sinfo -R` shows a drained node's reason as `v5:<check names>`; `python metrics/explain.py v5:<names>` says
what each one means and what to do ([monitoring guide](../metrics/README.md) §4.3).

**Rule:** any `fail` → `fail`. Otherwise any `warn`, or a **required** check that was `skipped` (for example
`nvidia-smi` missing on a GPU node) → `warn`. Otherwise `pass`.

**A missing tool is `skipped` with the reason. It is never counted as a pass.** This is what lets the same code
run on a laptop, Kaggle, Docker and the real node without lying.

Exit codes of `health_check.py` (deliberately different from training's 75/78):

| Mode | pass | warn | fail |
|---|---|---|---|
| prolog | 0 | **0** | 4 |
| periodic / full | 0 | 3 | 4 |

Every run prints one JSON report (also sent as the `health.report` event):

```json
{
  "schema": "v5-health/1", "timestamp_utc": "2026-10-28T10:00:00.000Z", "time": "(same)", "host": "gpu-3",
  "mode": "periodic", "expected_gpus": 8,
  "checks": [{"name": "ecc_uncorrectable", "status": "fail", "required": true,
              "detail": "uncorrectable on GPU 5 (2)", "metrics": {"values": [0, 0, 0, 0, 0, 2, 0, 0]},
              "gpu": 5, "seconds": 0.4}],
  "verdict": "fail", "admit_training": false, "drain_reason": "ecc_uncorrectable", "runtime_seconds": 1.9
}
```

The format is **Team 08's `v5-health/1` contract** (`teams/08-monitoring/health-check/`, lab PR #125), so their
monitoring and ClickHouse loader read our reports as they are: `gpu_inventory` (`count`, one line per GPU),
`ecc_uncorrectable` (`values`, one per GPU), `xid` (`counts` + `events` with `pci_bdf`, `code`, `severity`
warn/fail, `reason`), collectives (`backend`, `world_size`, `status`, per size `bytes`, `seconds`, `max_error`,
`all_ranks_correct`). We add fields of our own (`gpu`, `seconds`, `runtime_seconds`, `time`, Xid `new`, busbw);
the contract allows extra fields. `support/tests/test_health.py` checks real reports against the contract;
[team08_contract_notes.md](../support/docs/team08_contract_notes.md) lists the changes and our suggestions to Team 08.
Two differences are open with Team 08: `admit_training` is true on a `warn` (our prolog starts the job on a
warn; their draft says false), and a CPU `gloo` collective passes on a node with no real GPUs (Docker, CPU test
hosts; their draft never lets gloo pass).

---

## 5. Hangs, slow GPUs and bad training (runtime rules)

Health checks find broken hardware. These rules, in the trainer and job script, handle a job that is stuck or
slow:

| Rule | Setting | In simple words |
|---|---|---|
| NCCL error handling | `TORCH_NCCL_ASYNC_ERROR_HANDLING=1` | a network error stops the process instead of hanging; the wrapper retries |
| NCCL timeout | 10 min for dry run 1, then 3 × the longest measured collective | how long a GPU waits for the others before giving up |
| Flight recorder | `TORCH_NCCL_TRACE_BUFFER_SIZE=2000`, `TORCH_NCCL_DUMP_ON_TIMEOUT=1` | on a timeout, a trace shows **which GPU stopped** |
| **Step watchdog** | no step in `WATCHDOG_S` (production: max(5 × p99 step, 10 min)) → dump stacks → exit 75 | a frozen job becomes a restart, not an endless paid wait |
| Straggler rule | one rank's step time > 1.1 × median → warn; 3 windows → drain at the next checkpoint | one slow GPU slows all; needs per-rank timing from Teams 05/06 |
| Loss-spike guard | loss > 1.5 × median for 3 steps → no save, exit 78 | see the checkpoint README |

---

## 6. Files

| File | What it does |
|---|---|
| `gpu_health.sh` | the `v5-health/1` producer named in Team 08's contract; a thin wrapper over `health_check.py` that writes one JSON report to stdout (and `--out`) |
| `health_check.py` | runs all checks, prints the JSON report, gives the verdict; in periodic mode drains and moves jobs on `fail` |
| `xid_scan.py` | reads the kernel log, classifies Xid codes, remembers lines already seen |
| `allreduce_test.py` | exact-sum and bus-bandwidth test (NCCL on GPUs, gloo on CPU) |
| `thresholds.yaml` | every limit, with its source |
| `results/health_sample_v5.json` | a committed, validated `v5-health/1` sample report (see §6.1) |

Draining the node and asking its jobs to save is done by `../queue/job_queue.py` (`drain()`,
`ask_jobs_to_save_and_stop()`), shared with the spot watcher. In `support/` (optional): `tests/test_health.py`,
`tests/fixtures/health/` (a kernel log with Xids, a bad `nvidia-smi` CSV) and `kaggle/nccl_timeout_test.py`
(one rank stops on purpose; the others must fail cleanly after the NCCL timeout, with a flight-recorder trace).

Hooked into Slurm by `../slurm/prolog.sh` (before each job) and `../slurm/healthcheck.sh` (every 30 s).

### Try it

From `teams/07-infrastructure/` (fixtures are in the optional `support/` folder):

```bash
# state and events go to /var/lib/v5-health and /var/log/v5/events by default; point them somewhere writable
export V5_HEALTH_STATE=/tmp/v5-health V5_EVENTS_DIR=/tmp/v5-events

# report only, never drains (safe anywhere). On a laptop the GPU checks are "skipped", and because 8 GPUs
# are expected the verdict is "warn", never "pass". V5_EXPECT_GPUS=0 makes it a CPU node (verdict pass).
python health/health_check.py --mode periodic --report-only

# against the test fixtures
python health/health_check.py --report-only \
  --nvidia-smi-fixture ../support/tests/fixtures/health/nvidia_smi_bad.csv --kernel-log ../support/tests/fixtures/health/kernel_xid.log
python health/xid_scan.py ../support/tests/fixtures/health/kernel_xid.log

# all-reduce on CPU with 2 ranks
torchrun --standalone --nproc_per_node=2 health/allreduce_test.py --max-mb 16

# a drill: make this node "fail" (the Docker simulation does this)
echo "drill" > /var/lib/v5-health/force_fail     # remove the file to clear
```

`V5_EXPECT_GPUS` overrides the expected GPU count (the Docker test sets 0); `V5_HEALTH_STATE` moves the state
folder.

### 6.1 Producer entrypoint (`gpu_health.sh`) and validating against Team 08

Team 08's contract (`teams/08-monitoring/health-check/README.md`) names `gpu_health.sh` as the script that
emits `v5-health/1`. It is a thin wrapper over `health_check.py`: it writes one JSON object to stdout (and, with
`--out`, to a file) and never drains a node, so it is safe to run anywhere for a sample.

```bash
# from teams/07-infrastructure/ — one v5-health/1 report to stdout (prolog mode, read-only)
health/gpu_health.sh --mode prolog

# reproducible sample from the test fixtures (planted ECC on GPU 3 + Xids 13/79/94/157): a "fail" report
V5_EXPECT_GPUS=8 health/gpu_health.sh --mode prolog \
  --kernel-log support/tests/fixtures/health/kernel_xid.log \
  --nvidia-smi-fixture support/tests/fixtures/health/nvidia_smi_bad.csv \
  --out health/results/health_sample_v5.json
```

The committed `results/health_sample_v5.json` was produced by the second command and **passes Team 08's
validator unchanged**:

```bash
# validate the sample against Team 08's validator (exit 0, "record 1: PASS")
python ../08-monitoring/health-check/health_check.py --validate health/results/health_sample_v5.json

# the same report also maps to one Week-2 ClickHouse node_health row (validator reads JSONL, so compact it first)
python -c "import json;print(json.dumps(json.load(open('health/results/health_sample_v5.json'))))" \
  | python ../08-monitoring/health-check/health_check.py --clickhouse-jsonl -
```

The sample is a `verdict="fail"` report (`drain_reason="ecc_uncorrectable,xid"`): the one fatal Xid is 79, while
94 is `restart`→`warn` under the corrected classification above.

---

## 7. Tests and results

| Where | Test | Result |
|---|---|---|
| `support/tests/test_health.py` | Xid fixture (13, 79, 94, unknown 157) gives the right classes; the same log again does not drain twice | pass |
| same | bad nvidia-smi: ECC → fail; hot + throttled → warn; x8 of x16 → warn | pass |
| same | no `nvidia-smi` on a GPU node → `skipped` → verdict `warn` (never pass); on a CPU node → pass | pass |
| same | prolog warn exits 0; periodic warn exits 3; forced fail exits 4 with a drain reason; JSON keys match | pass |
| same | all-reduce on gloo, 2 ranks: exact sums, busbw > 0 | pass |
| Docker Slurm, run 9 | forced fail on a main-run node: drained within one interval, job saved and moved to the spare | MTTR 60–88 s, **0 steps lost** |
| Docker Slurm | forced fail on **both** main-run nodes, one spare | both drained; main run waits (no crash loop); recovers on repair |
| Docker Slurm | `SIGSTOP` one rank (hang) | watchdog fires at 20 s, exit 75, restart; MTTR 56 s |
| Kaggle (2 GPUs) | real nvidia-smi parsing, NCCL all-reduce, NCCL timeout with trace | ready to run (`support/kaggle/README.md`) |
| week-2 node | 5 × `--mode full` on good nodes | gives the real baseline thresholds |

From `teams/07-infrastructure`:

```bash
docker run --rm -v "$PWD":/opt/v5:ro --entrypoint bash v5-slurm-sim:1 \
  -c 'cd /opt/v5 && python -m pytest -q -p no:cacheprovider -W ignore support/tests/test_health.py'
```

---

## 8. Metrics to watch

Full list: H-01 … H-24 in [metrics_catalog.md](../support/docs/metrics_catalog.md). These page someone now (HIGH):

| ID | Metric | HIGH when | What to do |
|---|---|---|---|
| H-01 | fatal Xid | any | node is drained automatically; open a hardware ticket / replace instance |
| H-03 | ECC uncorrectable | any | same |
| H-06 | row-remap failure | any | GPU must be replaced |
| H-07 | GPU missing | any | reboot or replace the instance |
| H-08 | at slowdown temperature | 0 °C margin | cooling / replace |
| H-11 | NVLink / fast network link down | any | replace instance |
| H-12 | all-reduce busbw | ≤ 0.7 × baseline | keep the node out of the main run |
| H-13 | all-reduce wrong sum | any | hardware fault: replace |
| H-14 | step watchdog | ≥ 2 per hour | read the stack dumps: data wait? deadlock? |
| H-15 | straggler ratio | ≥ 1.25 | drain the slow node at the next checkpoint |
| H-16 | NCCL timeouts | ≥ 2 per hour | read the flight-recorder trace for the stopped rank |
| H-21 | spot notice | any | automatic save; page only if no commit within 90 s |
| H-22 | DCGM diag failure | any | replace |
| H-23 | host memory for staging | ≤ 1.0 × need | async saves will fail: fix before the next save |
| H-24 | loss-spike guard trip | any | roll back (checkpoint README §7) |

Targets: detect Xid/ECC within one health interval and hangs within the watchdog limit; ≤ 1 false drain per
week; prolog ≤ 30 s; full ≤ 15 min.

---

## 9. Still open

- **Silent data corruption**: not covered in the first main run (it needs step replay on a second GPU).
  Revisit after dry run 2.
- Real thresholds: need 5 `--mode full` runs on known-good week-2 nodes.
- Should a `warn` node stay in the main-run pool?
- Health-check interval during the main run, and its measured cost in step time.
- On-call rota: who replaces a node at 4 a.m.?
- Kaggle results (real nvidia-smi on Kaggle's GPUs, NCCL timeout test).

---

## 10. Words used here

| Word | Meaning |
|---|---|
| drain | "no new jobs on this node"; running jobs are asked to save and move |
| prolog | a script Slurm runs on a node just before a job starts |
| Xid | the NVIDIA driver's error number for a GPU problem |
| ECC | error-correcting memory; "uncorrectable" means data was lost |
| row remapping | the GPU swaps out a bad memory row; if that fails, the GPU must be replaced |
| DCGM | NVIDIA's data-center GPU manager and its diagnostic tests |
| all-reduce | every GPU adds its numbers with every other GPU: the core step of multi-GPU training |
| busbw | bus bandwidth: how fast that all-reduce moves data |
| NCCL | NVIDIA's library that GPUs use to talk to each other |
| straggler | a GPU slower than the rest; everyone waits for it |
| watchdog | a timer that restarts the job if no training step finishes in time |
