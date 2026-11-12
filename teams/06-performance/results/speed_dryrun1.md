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

## 1. MoE dispatch (compute)

Method: level-3 sum of `fwd:block*.moe.dispatch` medians; default **`model.moe.dispatch=sorted`**.

| metric | ms | source SHA |
| :--- | ---: | :--- |
| moe.dispatch (sum) | _awaiting_ | |
| clean step_ms | | |

## 2. MoE all-to-all (`comm`)

Command shape: `torchrun --nproc_per_node ≥2 -m perfkit.bench --modes comm model.ffn=moe --tag dryrun1_a2a`.  
Isolated a2a (no compute overlap). One GPU = not measured.

| metric | value | source SHA |
| :--- | :--- | :--- |
| per_call_ms (slowest rank) | _awaiting_ | |
| calls_per_step | | |
| per_step_ms | | |
| payload_mb_per_call | | |

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
