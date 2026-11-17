# G6 dry-run-1 profile — `dryrun1_prof`

```
Team:            06-performance
Owner:           Varshith Chennuru (varshith2000)
Lead approval:   raj-harit-v2
Question:        What is the per-step wall time, MFU (mfu_method=g6-v1), per-region forward/backward layer breakdown, and top CUDA operator / MoE / attention time share on Gate-2 config_v1.yaml in dry run 1 using torch.profiler (clean,layer,trace)?
Script:          teams/06-performance/jobs/run_dryrun1_prof.py
Command:         python -B teams/06-performance/jobs/run_dryrun1_prof.py --config teams/05-architecture/configs/config_v1.yaml --modes clean,layer,trace --level 3 --tag dryrun1_prof --out out --synthetic
Config:          teams/05-architecture/configs/config_v1.yaml
Inputs:          --synthetic if FineWeb absent; prefer real data when present
Hardware:        1 GPU
Max time:        90
Precision:       bf16
Measures:        clean step_ms (median/p50, p10, p90), tokens_per_s, peak_mem_mb, mfu (mfu_method=g6-v1); layer parts (level 3); traces under out/dryrun1_prof_parts/; top torch.profiler ops; GPU name; commit SHA
Expected result: exit 0; out/result.json + out/dryrun1_prof.md + out/dryrun1_prof_parts/*.json produced so tip (g6/dev -> g6/w3-profile-dryrun1) fills teams/06-performance/results/profile_dryrun1.md from logs + gist parts (no invented ms)
Outputs:         out/result.json, out/dryrun1_prof.json, out/dryrun1_prof.md, out/dryrun1_prof.jsonl, out/dryrun1_prof_parts/ (under 50 MB total; no huge traces committed to results/)
Test log:        teams/06-performance/jobs/2026-11-14-dryrun1-prof.log (own machine, --smoke-cpu, exit 0 PASS)
```

## Pins

| Item | Value |
| :--- | :--- |
| Class `main` pin (G5 signed) | `aec75af` (#447 / `config_v1.yaml`) |
| Config | `teams/05-architecture/configs/config_v1.yaml` |
| Tag | `dryrun1_prof` |
| `mfu_method` | `g6-v1` (keep until CAP flips; no #61 for Gate 3) |
| Branch | `g6/job-w3-dryrun1-prof` ← class `main` (not arm) |

## Notes

- `teams/05-architecture/configs/config_v1.yaml` uses G5's `settings:` list format with open (`null`) model dimensions (`n_layer`, `d_model`, `n_head`, `d_ff`, `data.seq_len`, `precision`). `run_dryrun1_prof.py` maps G5's signed non-null settings (`run.seed=1234`, `run.grad_clip=1.0`, `optim.name=muon`, `optim.lr=0.001`, `model.vocab_size=131072`, `model.embedding=ke2`, `model.ke_max_pos=32`, `model.attn_impl=eager`, `model.ffn=moe`, `model.moe.num_experts=16`, `model.moe.num_shared=1`, `model.moe.top_k=2`, `model.moe.dispatch=sorted`, `model.mtp=false`) onto `teams/06-performance/configs/base.yaml` (small-width OK per work order unless full-width overrides are passed).
- `--smoke-cpu` verified exit `0` locally using `configs/tiny_cpu.yaml` with `model.ffn=moe`, `dispatch=sorted`, `optim.name=muon`, and `mfu_method=g6-v1`, producing `out/result.json`, `out/dryrun1_prof.md`, `out/dryrun1_prof.jsonl`, and 5 cut trace parts under `out/dryrun1_prof_parts/`.
- After TSAI PASS:`teams/06-performance/results/profile_dryrun1.md` on `g6/dev` (`g6/w3-profile-dryrun1`); Shashank adds Nsight notes before Fri 20 Nov 11:59 IST evidence freeze.
