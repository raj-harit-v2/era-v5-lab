# G6 Week-3 checkpoint timing — `dryrun1_ckpt`

**Status: EXACT-SCRIPT CPU SMOKE COMPLETE — AWAITING G6 LEAD QA BEFORE TSAI EXECUTION.**

```text
Team:            06-performance
Owner:           Siva Ajjapu (AJJAPUSIVA)
Lead approval:   raj-harit-v2
Question:        What are save_ms, to_cpu_ms, write_ms and size_mb for the signed G5 small-width MoE checkpoint on one lab GPU?
Script:          teams/06-performance/jobs/dryrun1_ckpt.py
Command:         python3 jobs/dryrun1_ckpt.py --device cuda --repeats 10 --run-id dryrun1_ckpt
Config:          teams/05-architecture/configs/config_v1.yaml + explicit G6 small-width mapping in script
Inputs:          synthetic (no network or tokenizer download)
Hardware:        1 GPU (Linux lab)
Max time:        60
Precision:       fp32 (G5 production precision remains open)
Measures:        checkpoint.save_ms; checkpoint.to_cpu_ms; checkpoint.write_ms; checkpoint.size_mb; GPU; source SHA
Expected result: exit 0 only with complete per-parameter Muon/AdamW state; JSON under out/dryrun1_ckpt.json; small-width only
Outputs:         ./out/dryrun1_ckpt.json (checkpoint temporary file deleted after timing)
Test log:        teams/06-performance/jobs/2026-11-15-dryrun1-ckpt-cpu-smoke.txt (exact-script CPU smoke complete; Kaggle rehearsal documented separately)
```

## Pins and limitations

- Instructor-main baseline used for the Kaggle rehearsal: `6728a7a02f13fd7e0d2d230241407d9059ffff36`.
- G5 signed config v1: `teams/05-architecture/configs/config_v1.yaml` from G5 PR #447 (`aec75af`).
- G5 signed model choices: Muon, eager attention, 16 routed experts + 1 shared, top-2.
- Dry Run 1 Muon LR is `0.01` per separate instructor instruction. G5 `optim.lr=0.001` remains provisional.
- **Full-width parameters and production precision are not assigned in config v1.** This is a valid small-width timing request, **not** a full-width measurement. Do not enter its values into the official full-width row.
- Run from `teams/06-performance/`. The program uses the existing `perfkit.bench.run_checkpoint()` and writes only under `./out/`.
- MoE dispatch is pinned to `sorted`; real synthetic training steps (up to 16 by default) must fully initialize every expected optimizer state tensor before a save is timed. Failure aborts measurement rather than reporting an underestimated checkpoint.
- JSON records `optimizer.coverage`, `optimizer.warmup_steps`, `resolved_config`, `git.sha`, `git.dirty`, `git.dirty_paths`, and `wall_s`.
- **Documentation pending:** include a direct link to the instructor instruction for `optim.muon_lr=0.01` before TSAI submission; this setting is NOT specified by G5 `config_v1.yaml`.
- The benchmark times GPU-to-CPU transfer plus local `torch.save`, flush and `fsync`; it is *not* the G7 remote commit/restore protocol.
- For official full-width evidence, a separate approved request will be needed once dimensions and layout are fixed.

## Smoke and reviewer checklist

```bash
cd teams/06-performance
/usr/bin/time -p python3 jobs/dryrun1_ckpt.py --device cpu --repeats 2 --run-id dryrun1_ckpt_smoke 2>&1 | tee out/dryrun1_ckpt_smoke.log
cat out/dryrun1_ckpt_smoke.json
```

- [x] Run and attach the exact-script CPU smoke command, last log lines, elapsed `real` seconds, and `out/dryrun1_ckpt_smoke.json`. Do not check until it actually succeeds.
- [x] Check `optimizer.coverage` complete for all parameters, with warm-up step count recorded.
- [x] Confirm G5 signed `settings` keys (optim.name, attention.impl, moe.n_expert, moe.n_shared, moe.top_k) match live config. Verified on instructor main, 15 Nov 2026.
- [ ] Add the exact source URL for TSAI `muon_lr=0.01` instruction.
- [x] Confirm the Git SHA and output JSON are recorded.
- [ ] Lead QA approves the small-width scope and one-GPU resources.
- [x] Submit class JOB_REQUEST PR to `theschoolofai/era-v5-lab` with base `main` (not Vaibhav tip `main`).
- [ ] TSAI schedules the approved job and returns measured logs.
