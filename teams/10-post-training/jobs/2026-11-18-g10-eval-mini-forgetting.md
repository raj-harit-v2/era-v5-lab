# Job request: eval-mini forgetting, base and after the first SFT on dry run 1 (SUPERSEDED / WITHDRAWN — DO NOT RUN)

**Status (21 Nov 2026): SUPERSEDED AND WITHDRAWN. TSAI must not run this file.**

## Why this draft is withdrawn (eval firewall)

Under the lab evaluation firewall (`teams/09-evaluation/firewall/eval_firewall.md`), only named Team 9 measuring jobs read benchmark items. Team 9's `eval_schedule.md` section 8 (merged in PR #662) already schedules Team 9's watcher to score both the base checkpoint and the kept after-SFT checkpoint with the same command, slot, dtype (`bfloat16` autocast on bf16 GPUs, `float32` on CPU/non-bf16 GPUs), and item subsets.

## Agreed handoff between Team 9 and Team 10 (confirmed 20–21 Nov 2026)

1. **Benchmark half (Team 9):** Team 9's watcher scores the base and after-SFT checkpoints and exports the two Tier B task records to Team 10 with `value` and `stderr` divided by 100 (fractions in `[0, 1]`, enforced by `sft/tests/forgetting.py`).
2. **Held-out bits-per-byte half (Team 10):** Team 10 runs only `sft/bench/evaluate.py --metrics forget --dtype auto` (or `--dtype bfloat16` on a bf16 GPU, which runs bf16 autocast without casting weights and writes `"compute_dtype": "bfloat16"` to match the watcher) on Team 5 held-out v1. Team 10 never reads benchmark items in this job.
3. **Verdict (`sft/tests/forgetting.py`):** Merges Team 10's held-out bits-per-byte report with Team 9's fraction-scaled benchmark records and writes the forgetting table and verdict (`0.05` bpb limit, `0.01` at-limit mark).
