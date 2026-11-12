# G6 dry-run-1 checkpoint — dryrun1_ckpt

```
Team:            06-performance
Owner:           Siva Ajjapu
Lead approval:   raj-harit-v2
Question:        Full-size (or small-width) checkpoint save split: to_cpu_ms, write_ms, size_mb; cite GPU + SHA.
Script:          python -m perfkit.bench
Command:         python -m perfkit.bench --config teams/05-architecture/configs/config_v1.yaml --modes checkpoint --tag dryrun1_ckpt --out out --synthetic
Config:          teams/05-architecture/configs/config_v1.yaml
Inputs:          --synthetic if needed
Hardware:        1 GPU (Linux lab)
Max time:        90
Precision:       bf16 (or harness default)
Measures:        save_ms; to_cpu_ms; write_ms; size_mb; write_mb_per_s if present; GPU; SHA; mfu_method=g6-v1 if MFU packed
Expected result: exit 0; tip speed_dryrun1.md ckpt table from logs
Outputs:         out/*.json out/*.md
Test log:        teams/06-performance/jobs/2026-11-14-dryrun1-ckpt.log (own machine, smoke-cpu, PASS)
```

## Pins

| Item | Value |
| :--- | :--- |
| Class `main` pin (G5 signed) | `aec75af` (#447 / config_v1) |
| Config | `teams/05-architecture/configs/config_v1.yaml` |
| Tag | `dryrun1_ckpt` |
| Branch | `g6/job-w3-dryrun1-ckpt` ← class `main` |

## Notes

- Do not wait on G7 (single-GPU). Windows ckpt disk not Gate proof.
- After PASS: fold into tip `speed_dryrun1.md` with Vaibhav/Adinath.
