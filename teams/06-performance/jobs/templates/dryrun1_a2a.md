# G6 dry-run-1 MoE all-to-all — dryrun1_a2a

```
Team:            06-performance
Owner:           Vaibhav Lohar
Lead approval:   raj-harit-v2
Question:        Time MoE all-to-all (comm) on dry-run-1 / config_v1; slowest-rank ms and payload; cite GPU + SHA.
Script:          torchrun + perfkit.bench
Command:         torchrun --nproc_per_node 2 -m perfkit.bench --config teams/05-architecture/configs/config_v1.yaml --modes comm model.ffn=moe --tag dryrun1_a2a --out out
Config:          teams/05-architecture/configs/config_v1.yaml
Inputs:          G7 layout may raise nproc; until then nproc=2
Hardware:        2+ GPU (never 1)
Max time:        90
Precision:       bf16 (or harness default)
Measures:        per_call_ms_slowest_rank; calls_per_step; per_step_ms; payload_mb; GPU; SHA; mfu_method=g6-v1 if MFU packed
Expected result: exit 0; tip speed_dryrun1.md a2a table from logs
Outputs:         out/*.json out/*.md
Test log:        teams/06-performance/jobs/2026-11-14-dryrun1-a2a.log (smoke note; multi-GPU for TSAI)
```

## Pins

| Item | Value |
| :--- | :--- |
| Class `main` pin (G5 signed) | `aec75af` (#447 / config_v1) |
| Config | `teams/05-architecture/configs/config_v1.yaml` |
| Tag | `dryrun1_a2a` |
| Prefer | `model.moe.dispatch=sorted` if overriding |
| Branch | `g6/job-w3-dryrun1-a2a` ← class `main` |

## Notes

- Wide MoE: pin `model.moe.ffn_hidden` if needed (e.g. 768).
- After PASS: Vaibhav tables → Adinath analysis.
