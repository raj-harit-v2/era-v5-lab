# G6 baseline timing — post tip #60 (Muon launch cut + void fill)

```
Team:            06-performance
Owner:           Raj H (raj-harit-v2)
Lead approval:   raj-harit-v2
Question:        After landing tip #60 (batched Muon launch cut + layer-mode void fill), what are step_ms (median), tokens/s, MFU, HFU, peak memory, and layer gated parts under Lab Cap A4 on one GPU?
Script:          teams/06-performance/jobs/run_baseline_timing.py
Command:         python teams/06-performance/jobs/run_baseline_timing.py --out out --synthetic
Config:          teams/06-performance/configs/base.yaml (includes bench.layer_prefill=true from tip #60)
Inputs:          --synthetic forces data.source=synthetic (lab nodes without FineWeb); prefer FineWeb Brahmic-131K under data.dir when present and running without --synthetic
Hardware:        1 GPU
Max time:        45
Precision:       bf16
Measures:        clean.step_ms.median (run 1), tokens_per_s, mfu, hfu, peak_allocated_gb, layer parts via --against layerA vs layerB (Lab Cap A4: tol 10%, abs_tol 0.5 ms, no clean-step gate), GPU name, commit SHA
Expected result: comparable to pre-#60 Lab Cap A4 PASS on class #239 @ 95bd81a (clean ~101–107 ms range); exit 0 preferred; document Muon / void-fill deltas vs that row
Outputs:         out/result.json, out/baseline_v1_job.json, out/baseline_v1_job.md, out/baseline_v1_job-layerW.json, out/baseline_v1_job-layerA.json, out/baseline_v1_job-layerB.json (under 50 MB)
Test log:        teams/06-performance/jobs/2026-11-12-baseline-timing-post60.log (own machine, --smoke-cpu synthetic, PASS)
```

## Pins

| Item | Value |
| :--- | :--- |
| Tip #60 | `vaibh27/era-v5-lab` merge `41b7fb0` (commits `2e37318`, `6030b66`, `2a84b67`) |
| Pre-#60 PASS (keep) | class [#239](https://github.com/theschoolofai/era-v5-lab/pull/239) @ `95bd81a` Lab Cap A4 |
| Class PR commit | tip of this branch on `theschoolofai/era-v5-lab` after push |
| Packages | `torch>=2.3`, `numpy`, `pyyaml`, `tokenizers>=0.15` (see `teams/06-performance/perfkit/requirements.txt`) |

## Notes

- **Purpose:** post tip #60 instrumentation re-run. Class #239 @ `95bd81a` remains the pre-#60 Gate-2 Lab Cap PASS. This job is supplemental, not a Gate-2 blocker.
- Lab GPU: use `--synthetic` so nodes without FineWeb shards do not exit 4.
- Default without `--smoke-cpu` (Lab Cap Choice A4, unchanged from #239): process 1 is `--modes clean,layer --level 3 --repeat 1` (clean KPI once); after 120s cool-down, process W is a discarded `--modes layer` warm pass (never compared), process A is `--modes layer` (no against), then process B is `--modes layer --against` the A JSON with `report.compare_clean_step=false`, `report.tol_pct=10`, and `report.abs_tol_ms=0.5`.
- Tip #60 land on this branch: batched Polar Express Muon fewer launches (`models/optim.py`); layer-mode void fill via `bench.layer_prefill` / `QueueFill` (`perfkit/timer.py`, `bench.py`). Defaults remain `ce_impl=torch` (tip #52 Triton **not** in this job).
- The 0.5 ms floor is a Lab Cap rule for this GPU under SwPowerCap, not a tip default.
- The attached test log is the same script with `--smoke-cpu` (tiny synthetic CPU); TSAI GPU run uses `--synthetic` and omits `--smoke-cpu`.
- Writes only under `./out/`.
