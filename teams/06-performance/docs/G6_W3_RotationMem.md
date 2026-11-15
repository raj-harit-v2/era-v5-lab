# G6 Week-3 — Rotation members

**Week 3 = second rotation week.** One correctness test each: fast kernel vs reference.  
**Path:** `teams/06-performance/correctness/rotation_<github_handle>.py`  
**Tip base:** `g6/dev` · branch `g6/w3-rotation-<handle>` · PR → `g6/dev`  
**Due:** **R1** file exists **D4 Wed 18** · **R2** ref-vs-fast asserts **D5 Thu 19**  
**Framework:** `@pair` / check — fp64 reference; see `correctness/framework.py`. bf16 defaults `TOLERANCES[bf16]=(1e-2, 3e-2)`.

---

## Assignments + buddies

| Rotator | Buddy (first review) | Branch example |
| :--- | :--- | :--- |
| Anirudh Narla | Tharun | `g6/w3-rotation-<handle>` |
| Hariprasad Reddy | Vaibhav | same |
| Revant Gupta | Shashank | same |
| Sandeep Kunkunuru | Varshith | `g6/w3-rotation-sandeepkunkunuru` |
| Soma Korada | Siva | same |
| Utkarsh Mittal | Sunil | same |

Buddy reviews before Lead merge. Lead: Raj H.

---

## How to start

```text
git fetch origin
git checkout g6/dev && git pull
git checkout -b g6/w3-rotation-<your_handle>
# add correctness/rotation_<your_handle>.py
python -m pytest teams/06-performance/correctness/rotation_<your_handle>.py -q -rs
# PR → g6/dev; ask buddy then @RajH
```

**R1:** file exists with a fast-kernel case.  
**R2:** reference vs fast asserts green; do not report CUDA-skipped as GPU PASS.

---

## Not your job

Dry-run-1 JOB_REQUESTs (Varshith / Vaibhav / Siva) · filling profile/speed tables · `kernels_dryrun2.md` (Lead).

Core guide: [`G6_W3_Members.md`](G6_W3_Members.md).
