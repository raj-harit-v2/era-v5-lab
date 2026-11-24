# Job request: Dry run 2 matched-step SFT comparison (Full FT vs LoRA vs Deletion Tuning) — DRAFT, NOT RUNNABLE

Status: draft prepared on Week 4 D1 (21 Nov 2026) ahead of dry run 2 (Tue 24 Nov – Thu 26 Nov). **NOT RUNNABLE** until dry run 2 completes on D5 (Thu 26 Nov), Team 5 merges KE2/KAS head integration into `week2/model.py`, and a local stand-in test log on the dry-run-2 model class is attached.

Answers Gate 3 item 7 (Instructor ruling, 21 Nov 2026): compares **Deletion Tuning vs LoRA vs Full FT** at equal optimizer steps on the **dry run 2 checkpoint** (test-scale + untied KE2/KAS head `a10_kas_tokdrop` + Team 7 Checkpointer via `#608`) and saves the DT arm's three canary files (`model.safetensors`, `dt_keep_masks.bin`, `dt_keep_masks.bin.json`, `SHA256SUMS`) so the required **DT-then-RL chain** (`jobs/2026-11-17-dt-then-rl-code.md`) can run immediately after.

```
Team:            10-post-training
Owner:           10-post-training (lead saitej123)
Lead approval:   saitej123 (settings and protocol approved 21 Nov 2026; runnable once dry run 2 checkpoint + stand-in log land)
Question:        On the dry run 2 checkpoint (KE2/KAS untied head), at equal optimizer steps on the #587-selected OCR-2 slice, how do Deletion Tuning (paper-repo settings), LoRA, and Full FT compare on task NLL, chat-format validity, RL mixed groups, and held-out forgetting bpb?
Script:          teams/10-post-training/capstone/dryrun2_dt_compare.py (calls capstone/sft_g5.py, capstone/sft_slice_v1.py, capstone/day_one_probe.py, capstone/keep_weights.py)
Command:         G10_STDIO_RUNNER=docker python teams/10-post-training/capstone/dryrun2_dt_compare.py --g5-root <G5> --run-folder <DR2_RUN> --tokenizer <TOKENIZER> --byte-table <TABLE> --heldout <HELDOUT> --heldout-sources <HELDOUT_SOURCES> --packs <PACK>/shard-00000/pack.firewalled.jsonl <PACK>/shard-00001/pack.firewalled.jsonl <PACK>/shard-00002/pack.firewalled.jsonl <PACK>/shard-00003/pack.firewalled.jsonl --rl-tasks <POOL>/out/v1/cc.jsonl --rl-ids teams/10-post-training/capstone/probe_rl_easy_ids.txt --slice-arm <A2_OR_A4_FROM_587> --steps 243 --batch 16 --full-lr 1e-4 --lora-lr 1e-3 --dt-lr 5e-4 --marker-lr 1e-3 --dt-targets g5_gate --dt-alpha-start 100 --dt-alpha-end 1000 --dt-eta 0.00048828125 --dt-lambda 1e-5 --dt-prior-strength 3.0 --keep-canary-state-dir keep_canary/ --keep-weights-dir keep_t7/ --keep-weights-arms full,lora,dt --deadline-minutes 115 --device cuda --out out/
Config:          none (all settings on command line; DT settings match the 17 Nov paper-repo port check: `g5_gate`, `lr 5e-4`, `alpha 100 -> 1000`, `eta 1/2048`, `lambda 1e-5 -> 0`, `band_at_init` logged before step 1)
Inputs:          dry run 2 run folder (from Team 5 on D5, Thu 26 Nov, with KE2/KAS head & Team 7 Checkpointer `#608`); pinned OCR-2 firewalled pack shards 0–3 (`#565`); RL data v1 `cc.jsonl` (`#564`); Team 5 held-out v1; frozen p1536 tokenizer & KE2 byte table.
Hardware:        1 GPU (>= 40 GB)
Max time:        120 minutes (`--deadline-minutes 115`; Full FT sets completed step budget, LoRA and DT run exact equal steps)
Precision:       fp32 weights and AdamW state (same as `#587`; forgetting bpb compared with `forgetting.py`, Team 9 watcher scores ARC-Challenge/HellaSwag on `keep_t7/g10-dr2-{full,lora,dt}` in bf16 autocast)
Measures:        per arm (base, full, lora, dt): matched optimizer steps, eval NLL, held-out forgetting Δbpb (`0.05` limit, `0.01` at-limit mark), chat-format validity, closed turns, RL screen mixed groups / pass rate, DT `band_at_init` and `deletion_final`, reload parity, and SHA-256 of kept DT canary & Team 7 run folders.
Expected result: unknown on KE2/KAS head; surrogate baseline is `results/dt_vs_fft.md` (`SmolLM2-135M`/`1.7B`).
Outputs:         out/*.json and out/compare.md (under 5 MB) back to the repo. `keep_canary/dt/` (3 files + SHA256SUMS for Task 11 DT-then-RL) and `keep_t7/g10-dr2-{full,lora,dt}/` (Team 7 Checkpointer run folders for Team 9 watcher) to TSAI storage. No weights, training rows, or generations in Git.
Test log:        REQUIRED before sending. Offline unit tests pass (`capstone/test_dryrun2_dt_compare.py`). Attached so far: `2026-11-26-g10-dryrun2-dt-vs-fft.log` = the wrapper end to end, exit 0, all three arms + screens + both keep dirs, on the DENSE head, Mac CPU, a 20-step stand-in run folder, `--origin g10_rehearsal`. It is NOT the KE2/KAS head and NOT `g5_delivery`. Still to attach: a staged CPU stand-in log on Team 5's merged KE2/KAS `LanguageModel` once Team 5 lands dry run 2's `model.py`.
```

## Blocked by

1. **Dry run 2 checkpoint (Team 5, D5 Thu 26 Nov).**
2. **Team 5 KE2/KAS head code on `main`** (`#694`/`#702` untied `a10_kas_tokdrop` integrated in `week2/model.py`, plus `#706` optimizer split) and a local stand-in test log verifying `sft_g5.py`, `team5_adapter.py`, `keep_weights.py`, and `dryrun2_dt_compare.py` against that exact `model.py`.
3. **`#587` result** (selects `--slice-arm a2` or `a4`; defaults to `a4`).
4. **Probe file** (if dry run 2 `#608` Checkpointer `probe_loss` is present, verify compatibility; otherwise generate via `capstone/make_probe_file.py`).

## Notes

- **Eval firewall:** this job never reads ARC-Challenge, HellaSwag, or any Team 9 benchmark. Team 9's watcher scores the kept Team 7 run folders (`keep_t7/g10-dr2-{full,lora,dt}/`) and hands fraction-scaled (`value/100`, `stderr/100`) rows to `sft/tests/forgetting.py`.
- **Gate 3 item 7 chain:** once `keep_canary/dt/` is stored, run `jobs/2026-11-17-dt-then-rl-code.md` against `keep_canary/dt/` to complete both required halves of Gate 3 item 7 (DT vs LoRA vs full FT + DT-then-RL).
