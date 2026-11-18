# Speed — dry run 1

**Status:** stub — awaiting TSAI job logs.  
**Owners:** a2a/tables → Vaibhav · ckpt → Siva · MoE analysis → Adinath · per-rank → Sunil · Lead QA → Raj  
**Rule:** GPU + SHA per table. Stay `mfu_method=g6-v1` until CAP flips. Linux for checkpoint gate.

| Field | Value |
| :--- | :--- |
| GPU | _awaiting_ |
| Commit | _awaiting_ |
| Config / layout | _G5 config · G7 parallel layout_ |
| Job tags | `dryrun1_a2a`, `dryrun1_ckpt` (+ profile SHA if shared) |
| a2a job | class [#496](https://github.com/theschoolofai/era-v5-lab/pull/496), `jobs/2026-11-14-dryrun1-a2a.md`, pin `aec75af` (config_v1, #447) |
| TSAI log / gist | _awaiting_ |

## 1. MoE dispatch (compute)

Method: level-3 sum of `fwd:block*.moe.dispatch` medians; default **`model.moe.dispatch=sorted`**.  
Source: needs a `--modes layer --level 3` run. The #496 job runs `--modes comm` only, so it gives `clean step_ms` but no dispatch regions.

| metric | ms | source SHA |
| :--- | ---: | :--- |
| moe.dispatch (sum) | _awaiting_ | |
| clean step_ms | | |

## 2. MoE all-to-all (`comm`)

Job: class #496, 1 GPU: `cd teams/06-performance && python jobs/run_dryrun1_a2a.py --nproc 1 --out out`.  
Isolated a2a (no compute overlap). On 1 GPU the comm latency (`per_call_ms`, `per_step_ms`) is not measured; payload and calls/step still come from the log.  
Fill after TSAI posts the #496 logs. Multi-GPU later: same wrapper with `--nproc ≥2`.

| metric | value | source SHA |
| :--- | :--- | :--- |
| per_call_ms (slowest rank) | _awaiting_ | |
| calls_per_step | _awaiting_ | |
| per_step_ms | _awaiting_ | |
| payload_mb_per_call | _awaiting_ | |

## 3. Checkpoint — small-width TSAI job #485

**Owner:** Siva  
**Scope:** Small-width synthetic MoE; not full-width Dry Run 1.  
**Evidence:** TSAI instructor update, 17 Nov 2026; job [#485](https://github.com/theschoolofai/era-v5-lab/pull/485) and class [checkpoint_dryrun1.md](https://github.com/theschoolofai/era-v5-lab/blob/main/teams/06-performance/results/checkpoint_dryrun1.md) (merged PR #557).  


| Metric | TSAI-reported result |
| :--- | :--- |
| Timing repeats | 10 |
| Optimizer-state coverage | Complete |
| GPU-to-CPU copy share | 8% |
| File-write share | 92% |
| `save_ms` | Unavailable |
| `to_cpu_ms` | Unavailable |
| `write_ms` | Unavailable |
| `size_mb` | Unavailable |
| `write_mb_per_s` | Unavailable |

**Execution GPU / Git SHA:** Unavailable (TSAI did not report either).  
**Evidence source:** Class checkpoint results PR #557; tip PR #83.  

The 8% and 92% figures are **shares of checkpoint save time**,
not absolute timings. File writing dominated the measured save.

TSAI retained absolute timing and GPU details. No execution SHA
or checkpoint size was supplied in the instructor's update.

Earlier CPU smoke and Kaggle measurements are not substituted
for TSAI GPU results. These findings must not be interpreted
as a full-width checkpoint measurement.

Profile job #486 did not measure checkpoint or communication
time (Rule 3b); checkpoint results here come from job #485.

References:
- https://github.com/theschoolofai/era-v5-lab/pull/485
- https://github.com/theschoolofai/era-v5-lab/pull/557

## 4. Per-rank step time + slow ranks

**Owner:** Sunil · **Scope (agreed with Raj, G6 16–17 Nov):** TSAI runs 1-GPU jobs only this week, so per-rank = **one rank**; slow ranks are deferred until a multi-GPU run with the G7 layout.  
**Source:** class [#486](https://github.com/theschoolofai/era-v5-lab/pull/486) (`dryrun1_prof`, `--modes clean,layer,trace --level 3`, 1 GPU), results as posted by TSAI in the G6 group, 17 Nov 2026 12:44 IST. TSAI kept absolute times and device details, so this section has **shares and counts only** (no invented ms).  
**Width:** small-width. The job maps G5's signed `config_v1.yaml` settings (pin `aec75af`, #447) onto `configs/base.yaml` because `config_v1` leaves model sizes open; MoE 16 routed + 1 shared, top-2, `dispatch=sorted`, Muon, `mfu_method=g6-v1`.

### 4a. Per-rank step time

| rank | step_ms | GPU busy (share of step) | kernels / step | host syncs / step | GPU starved (steps) | source |
| ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| 0 (only rank) | _unavailable (TSAI held absolutes)_ | 31.1% | 3,693 | 19 | 20 of 20 | #486 |

GPU / SHA: _unavailable (TSAI held device details; run SHA not reported)_. Job file: class `main` at the #486 merge, `b016b71`.

### 4b. Where rank 0's step goes (share of one training step, #486)

| part | share of step |
| :--- | ---: |
| backward of the block gradients | 17.7% |
| Muon Newton-Schulz update | 5.3% |
| backward of the head and loss | 5.2% |
| MoE dispatch (`sorted` path; profiler region named `dispatch.grouped`), recompute pass | 2.3% |
| MoE dispatch (`sorted` path; profiler region named `dispatch.grouped`), forward pass | 2.3% |

Caveats from TSAI's report:

- The GPU ran out of queued work in all 20 recorded steps, so these part times **include host time** (time the GPU spent waiting for Python to launch work), not only kernel time.
- 22 gated parts had a repeat spread above 10% (the 5% repeat gate does not hold for them); read small differences between parts as noise.
- Rule 3b: checkpoint and comm were **not** measured in this run (checkpoint is §3 / #485; a2a is §2 / #496).

### 4c. Slow ranks

**Not measurable on 1 GPU.** A slow rank only exists when ranks are compared, and a step on N GPUs takes as long as its slowest rank (every collective waits for it). Deferred until TSAI runs a multi-GPU job with the G7 layout; then this table gets one row per rank (median / p95 / max step_ms and ratio to the cross-rank median), mapped to node and GPU.

**What one rank already shows:** rank 0 is bound by the host, not by the GPU. With the GPU busy 31.1% of the step and starved in every recorded step, about two-thirds of the step is the GPU waiting for the CPU (3,693 kernel launches and 19 host syncs per step). On more GPUs every rank pays this, and host jitter becomes rank-to-rank skew, so cutting launches and syncs comes before any slow-rank work. Analysis and kernel proposals: §5 and `kernels_dryrun2.md`.

## 5. MoE analysis (Adinath)

_Bottlenecks, imbalance, dispatch vs a2a vs ckpt story. Cite tables above. Hot kernels (2–4) for Tharun / kernels_dryrun2:_

1. _awaiting_  
2.  
3.  

## 6. G4 KE2 footnote

_Awaiting Team 4 KE2 timing row._
