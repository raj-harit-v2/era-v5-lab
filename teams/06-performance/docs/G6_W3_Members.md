# G6 Week-3 — Core members guide

**Gate 3 evidence:** Fri 20 Nov 2026 11:59 IST · **Session:** Sat 21  
**Tip:** `vaibh27/era-v5-lab` `g6/dev` · **Class jobs:** `theschoolofai/era-v5-lab` `main`  
**Config pin:** `teams/05-architecture/configs/config_v1.yaml` @ **`aec75af`** (#447)  
**MFU:** keep `mfu_method=g6-v1` until CAP flips (#61 stays draft through Gate 3)

---

## How to use this tip PR (job owners)

1. On tip, open `teams/06-performance/jobs/templates/dryrun1_*.md`.  
2. In a **class** clone: `git fetch upstream && git checkout -b g6/job-w3-dryrun1-<name> upstream/main`.  
3. Copy the template → `teams/06-performance/jobs/<date>-dryrun1-<name>.md` (edit Owner/log paths if needed).  
4. Smoke-cpu where possible → PR to class **`main`** → ping **@RajH** for QA → then `@tsai`.  
5. After PASS logs: fill tip stubs under `results/` (already on `g6/dev` from #69).

Do **not** base jobs on `g6/job-arm-*` or tip history.

---

## Core owners

| Who | Primary | Tip branch | Class job | Due |
| :--- | :--- | :--- | :--- | :--- |
| **Varshith** | `profile_dryrun1.md` (profiler) | `g6/w3-profile-dryrun1` | `dryrun1_prof` | D4 Wed 18 |
| **Shashank** | Nsight § in same profile doc | (same / follow-up) | assist smoke | D4 |
| **Vaibhav** | a2a job + MoE tables in `speed_dryrun1.md` | `g6/w3-speed-dryrun1` | `dryrun1_a2a` | D5 Thu 19 |
| **Siva** | ckpt job + ckpt columns | `g6/w3-speed-dryrun1` | `dryrun1_ckpt` | D5 |
| **Adinath** | MoE analysis + hot-kernel bullets | same speed PR | — | D5 |
| **Tharun** | Fused MoE dispatch + attention `@pair` | `g6/w3-kernel-pairs` | — | D5 |
| **Sunil** | Per-rank + slow ranks | `g6/w3-speed-per-rank` | — | D6 Fri 20 |
| **Raj (Lead)** | `kernels_dryrun2.md` + Gate pack + job QA | `g6/w3-kernels-dryrun2` | QA only | D6 |

Result stubs: `results/profile_dryrun1.md`, `speed_dryrun1.md`, `kernels_dryrun2.md` (awaiting TSAI — no invented ms).

---

## Tip vs class

| Work | Base | Target |
| :--- | :--- | :--- |
| Result docs / `@pair` / rotation | `g6/dev` | PR → `g6/dev` |
| JOB_REQUESTs | class `main` | PR → `main` |

---

## Cross-team

| Item | Status |
| :--- | :--- |
| G5 config v1 | Done — pin `aec75af` |
| G7 parallel layout | Still chased — a2a may start at nproc=2; per-rank waits layout |
| G4 KE2 all-ID test | Yasir owns; **Tharun** reviews (Wed 18) |
| Arms #408/#409 | PASS; #410 TSAI rerun — do not block dry-run-1 |

---

## Daily CAP

```text
<Name> — D<N>
Done: …
Blocked: …
Next: …
PR / SHA: …
```
