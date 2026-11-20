# G6 dry-run-1 lab profile — `dryrun1_tsai`

```
Team:            06-performance
Owner:           Raj H (raj-harit-v2)
Lead approval:   raj-harit-v2
Question:        Lab-GPU dry run 1 profile (torch.profiler clean,layer,trace + repeat 2), full-size checkpoint save, and Nsight Systems on the dry run 1 model (g5_t2_base: 16+1 MoE, top-2, dispatch=loop, Muon loop, torch kernels) so tip can fill the TSAI lab column in profile_dryrun1.md and speed_dryrun1.md (no invented ms).
Script:          teams/06-performance/jobs/run_dryrun1_tsai.py
Command:         python -B teams/06-performance/jobs/run_dryrun1_tsai.py --out out
Config:          teams/06-performance/configs/g5_t2_base.yaml
Inputs:          data.source=synthetic (script sets this)
Hardware:        1 GPU (A100-class or lab GPU with enough memory; script retries B=8,4,2,1 on OOM)
Max time:        90
Precision:       bf16 (g5_t2_base)
Measures:        step shares/counts from prof (GPU busy, kernels/syncs, top parts); ckpt save wall; nsys report if nsys present; GPU name (nvidia-smi.txt); commit SHA in out/result.json; batch_size that fitted
Expected result: exit 0; out/result.json with prof+ckpt (+ nsys or skip note); tip fills TSAI lab cells in results/profile_dryrun1.md and results/speed_dryrun1.md from shares/counts only (no invented ms)
Outputs:         out/result.json, out/prof/, out/ckpt/, out/nsys/ (optional), out/logs/, out/nvidia-smi.txt; script deletes large traces/ckpts/sqlite so out/ stays under ~50 MB
Test log:        teams/06-performance/jobs/2026-11-20-dryrun1-tsai.log (own machine, --smoke-cpu, PASS)
```

## Pins

| Item | Value |
| :--- | :--- |
| Tip pin (code + config) | tip `vaibh27/era-v5-lab` @ `7e255df2` (`g6/job-w3-dryrun1-tsai`; includes `configs/g5_t2_base.yaml` from tip #89 / class #688 and this job script) |
| Class shape SoT | `#447` / `aec75af` — MoE 16+1, top-2, eager, muon (dispatch **not** in config_v1) |
| Config | `teams/06-performance/configs/g5_t2_base.yaml` |
| `moe.dispatch` | **`loop`** (explicit in g5_t2_base; matches G5 dry run 1 `#620`, not tip `#486` sorted mapper) |
| Tag | `dryrun1_tsai` |
| `mfu_method` | `g6-v1` |
| Related evidence | class [#688](https://github.com/theschoolofai/era-v5-lab/pull/688); tip Gate pack / Modal columns already filled |

## Notes

- This job is for the **lab / TSAI column**, not a redo of member Modal A100 numbers.
- Do **not** use `jobs/g5_config.py` sorted inject — that path is `#486` / tip `#90` (Earlier TSAI runs).
- If `nsys` is missing, script skips Nsight and still exits 0 when prof+ckpt succeed.
- After PASS: fill tip `profile_dryrun1.md` / `speed_dryrun1.md` **TSAI lab** cells from returned shares/counts; keep Modal columns unchanged.
- Smoke: `python -B teams/06-performance/jobs/run_dryrun1_tsai.py --smoke-cpu`
