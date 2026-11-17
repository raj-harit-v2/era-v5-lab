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

## 3. Full-size checkpoint

`--modes checkpoint` → split stall vs write.

| metric | value | source SHA |
| :--- | :--- | :--- |
| save_ms | _awaiting_ | |
| to_cpu_ms | | |
| write_ms | | |
| size_mb | | |
| write_mb_per_s | | |

## 4. Per-rank step time + slow ranks

| rank | step_ms | note |
| ---: | ---: | :--- |
| _awaiting G7 layout_ | | |

**Slow ranks:** _awaiting_

## 5. MoE analysis (Adinath)

_Bottlenecks, imbalance, dispatch vs a2a vs ckpt story. Cite tables above. Hot kernels (2–4) for Tharun / kernels_dryrun2:_

1. _awaiting_  
2.  
3.  

## 6. G4 KE2 footnote

_Awaiting Team 4 KE2 timing row._
