# G6 baseline timing (Gate 2 job request)

```
Team:            06-performance
Owner:           Raj H (raj-harit-v2)
Lead approval:   raj-harit-v2
Question:        What are step_ms (median), tokens/s, MFU, HFU, and peak memory for configs/base.yaml on one GPU (clean from run 1; layer gated vs run 2 after cool-down) at level 3?
Script:          teams/06-performance/jobs/run_baseline_timing.py
Command:         python teams/06-performance/jobs/run_baseline_timing.py --out out --synthetic
Config:          teams/06-performance/configs/base.yaml
Inputs:          --synthetic forces data.source=synthetic (lab nodes without FineWeb); prefer FineWeb Brahmic-131K under data.dir when present and running without --synthetic
Hardware:        1 GPU
Max time:        45
Precision:       bf16
Measures:        clean.step_ms.median (run 1), tokens_per_s, mfu, hfu, peak_allocated_gb, layer parts via --against layerA vs layerB (Lab Cap A4: tol 10%, abs_tol 0.5 ms, no clean-step gate), GPU name, commit SHA
Expected result: step_ms near prior A100 baseline (~40–50 ms at B=16 T=256) or documented host delta; exit 0 preferred (working baseline may note Muon spread)
Outputs:         out/result.json, out/baseline_v1_job.json, out/baseline_v1_job.md, out/baseline_v1_job-layerA.json, out/baseline_v1_job-layerB.json (under 50 MB)
Test log:        teams/06-performance/jobs/2026-11-03-baseline-timing.log (own machine, --smoke-cpu synthetic, PASS)
```

## Pins

| Item | Value |
| :--- | :--- |
| Intended G6 tip (day-to-day, narrative) | `vaibh27/era-v5-lab` `g6/dev` @ `4025990` (post #47/#48/#49; not what this class PR tree times) |
| Class PR commit | tip of `g6/job-baseline-timing-2026-11-03` on `theschoolofai/era-v5-lab` after this push |
| Packages | `torch>=2.3`, `numpy`, `pyyaml`, `tokenizers>=0.15` (see `teams/06-performance/perfkit/requirements.txt`) |

## Notes

- Lab GPU: use `--synthetic` so nodes without FineWeb shards do not exit 4.
- Default without `--smoke-cpu` (Lab Cap Choice A4): process 1 is `--modes clean,layer --level 3 --repeat 1` (clean KPI once); after 120s cool-down, process W is a discarded `--modes layer` warm pass (never compared), process A is `--modes layer` (no against), then process B is `--modes layer --against` the A JSON with `report.compare_clean_step=false`, `report.tol_pct=10`, and `report.abs_tol_ms=0.5`. Against is warm layer vs warm layer so both samples share clock/cache state (A3a fixed the fwd skew; A4 removes the cold first sample that left `bwd:block0` 0.8 points over, 10.8% / 0.415 ms, in 41e9748). The 0.5 ms floor is a Lab Cap rule for this GPU under SwPowerCap, not a tip default.
- Prior TSAI working baseline on `48af4ce` (synthetic by hand): step ~104–106 ms, ~39k tok/s; `opt:opt.muon` 5.7% outside 5%; power-cap warns — working not final.
- Gate 2: report step_ms, tokens/s, and Muon part with spread; MFU/HFU / GPU model per TSAI scrub rules.
- The attached test log is the same script with `--smoke-cpu` (tiny synthetic CPU); TSAI GPU run uses `--synthetic` and omits `--smoke-cpu`.
- Writes only under `./out/`.
