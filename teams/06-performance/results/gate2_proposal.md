# Gate 2 proposal (Week 2) — G6 Performance

**Team:** 06-performance · **Owner:** `@raj-harit-v2`  
**Tip pack:** [`speed_v1.md`](speed_v1.md) on `g6/dev` (merged tip [#66](https://github.com/vaibh27/era-v5-lab/pull/66) @ `ae8ab94`)  
**TSAI decision:** Sat 14 Nov  
**This file:** canonical Sat-14 ask + pointers. Numbers and tables live in `speed_v1.md`.

---

## Ask for Sat 14

Keep trainer defaults on **torch CE**, **`moe.dispatch=sorted`**, and **bf16** (already the measured path). Use class **#239 Lab Cap A4** (`95bd81a`) as the lab baseline under the **job-only** warm-layer pair rule (tol 10%, abs 0.5 ms not needed (0 parts); clean step about **101–107 ms** across recent runs — cite the range, do not lock a single KPI; keep the harness spread warning). Prefer **torch** for step; treat fused/Triton CE (including merged tip #52) as **memory options, not step wins** (same-SHA A100 §2c). Offer **B3 `batch32.yaml`** as an explicit throughput config (+11% tokens/s on A100); do **not** change default batch. Leave **B2** (no win at V=131072), **B5** (already present / no win), and **B1** (opt-in compile) out of the default flip. Arm jobs t1–t3 remain **awaiting**. Tip #60 is on `g6/dev` but this #239 evidence is **pre-#60**. Hold **#61 g6-v2 MFU** until after Gate 2 / G8 labeling.

---

## Evidence pointers (do not invent numbers here)

| Item | Where |
| :--- | :--- |
| Lab Cap baseline PASS | Class [#239](https://github.com/theschoolofai/era-v5-lab/pull/239) @ `95bd81a` — `speed_v1` §1 |
| CE / Triton A/B | `speed_v1` §2 (torch wins step; Triton/fused = mem) |
| MoE dispatch A/B | `speed_v1` §3 — **sorted** default |
| B-stack | `speed_v1` §1b |
| Repeat check | `speed_v1` section **Repeat check** + [`repeat_check_v1.md`](repeat_check_v1.md) |
| Tip pack PR | [#66](https://github.com/vaibh27/era-v5-lab/pull/66) |

---

## Explicitly not requested this Gate

- Flip default CE to Triton or fused  
- Flip default batch to 32 without an explicit config choice  
- Lock a single clean-step KPI  
- Merge tip #61 (g6-v2 MFU) before G8 labeling  

## Open item (not blocking Sat 14 ask)

- **Checkpoint save time (rule 3b)** was not measured on class #239 (clean/layer Lab Cap only). G7 needs stall (GPU→CPU) / write+fsync / size by **Fri 13 Nov**; week-1 provisional from `baseline_v0.md` until a separate tip `--modes checkpoint` handoff lands.
