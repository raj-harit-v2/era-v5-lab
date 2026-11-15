# G6 dry-run-1 profile — dryrun1_prof

```
Team:            06-performance
Owner:           Varshith Chennuru
Lead approval:   raj-harit-v2
Question:        Full-width (or small-width) dry run 1 step profile with torch.profiler (clean,layer,trace); cite GPU + SHA.
Script:          python -m perfkit.bench (from teams/06-performance or repo root per TSAI cwd)
Command:         python -m perfkit.bench --config teams/05-architecture/configs/config_v1.yaml --modes clean,layer,trace --level 3 --tag dryrun1_prof --out out --synthetic
Config:          teams/05-architecture/configs/config_v1.yaml
Inputs:          --synthetic if FineWeb absent; prefer real data when present
Hardware:        1 GPU
Max time:        90
Precision:       bf16 (or as config_v1 / harness default)
Measures:        clean step_ms; layer parts; traces under runs/dryrun1_prof_parts/; GPU name; commit SHA; mfu_method=g6-v1 if MFU packed
Expected result: exit 0; tip fills results/profile_dryrun1.md from out/ + gist parts (no invented ms)
Outputs:         out/*.json out/*.md out/*_parts/ (under 50 MB); no huge traces in results/
Test log:        teams/06-performance/jobs/2026-11-14-dryrun1-prof.log (own machine, smoke-cpu, PASS)
```

## Pins

| Item | Value |
| :--- | :--- |
| Class `main` pin (G5 signed) | `aec75af` (#447 / config_v1) |
| Config | `teams/05-architecture/configs/config_v1.yaml` |
| Tag | `dryrun1_prof` |
| Branch | `g6/job-w3-dryrun1-prof` ← class `main` (not arm) |

## Notes

- Model sizes in config_v1 may be null — small-width OK per work order.
- After TSAI PASS: Varshith fills tip `profile_dryrun1.md`; Shashank adds Nsight.
