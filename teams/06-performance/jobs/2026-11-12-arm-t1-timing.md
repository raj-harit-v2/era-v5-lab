# G6 arm timing — t1 (Team 5 Architecture shape)

```
Team:            06-performance
Owner:           Raj H (raj-harit-v2)
Lead approval:   raj-harit-v2
Question:        On one lab GPU, what are clean step_ms (median), tokens/s, MFU, HFU, peak memory, GPU name, and commit SHA for Architecture arm t1?
Script:          teams/06-performance/jobs/run_arm_timing.py
Command:         python teams/06-performance/jobs/run_arm_timing.py --out out --synthetic --config teams/05-architecture/configs/arms/t1.yaml
Config:          teams/05-architecture/configs/arms/t1.yaml
Inputs:          --synthetic forces data.source=synthetic (lab nodes without FineWeb); prefer FineWeb Brahmic-131K under data.dir when present and running without --synthetic
Hardware:        1 GPU
Max time:        45
Precision:       bf16
Measures:        clean.step_ms.median (--repeat 2), tokens_per_s, mfu, hfu, peak_allocated_gb, GPU name, commit SHA; cite mfu_method from run JSON if present
Expected result: exit 0; pack fills tip speed_v1.md §4 arm t1 from out/; Sat-14 Gate-2 ask remains non-blocking
Outputs:         out/result.json, out/arm_v1_job.json, out/arm_v1_job.md (and -run2 if free_path suffixes; under 50 MB)
Test log:        teams/06-performance/jobs/2026-11-12-arm-t1-timing.log (own machine, --smoke-cpu, PASS)
```

## Pins

| Item | Value |
| :--- | :--- |
| Base job tree | class [#369](https://github.com/theschoolofai/era-v5-lab/pull/369) @ `1123e50` |
| Arm config | `teams/05-architecture/configs/arms/t1.yaml` |
| Mode | clean only, level 3, `--repeat 2` (no Lab Cap A4) |
| Gate-2 baseline (unchanged) | class [#239](https://github.com/theschoolofai/era-v5-lab/pull/239) @ `95bd81a` Lab Cap A4 |
| Packages | `torch>=2.3`, `numpy`, `pyyaml`, `tokenizers>=0.15` (see `teams/06-performance/perfkit/requirements.txt`) |

## Notes

- First filing for Week-2 arm rows. Not a Lab Cap layer pair.
- Tip #61 / `g6-v2` MFU flip is parallel; do not wait on it. Label `mfu_method` if MFU is packed.
