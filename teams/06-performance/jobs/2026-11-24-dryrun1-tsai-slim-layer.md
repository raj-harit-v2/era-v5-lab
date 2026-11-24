# G6 dry-run-1 lab profile — slim layer follow-up (`dryrun1_tsai_slim_layer`)

```
Team:            06-performance
Owner:           Raj H (raj-harit-v2)
Lead approval:   raj-harit-v2
Question:        Slim layer-only follow-up after class #690 partial (clean ~12.0 s/step @ B=8 landed; no layer/share/%). Fill TSAI lab share/% cells in profile_dryrun1.md / speed_dryrun1.md from measured layer shares only (no invented ms). Uses hardened run_dryrun1_tsai.py (--modes/--steps/--repeat/--skip-ckpt, per-stage result.json) from class #775.
Script:          teams/06-performance/jobs/run_dryrun1_tsai.py
Command:         python -B teams/06-performance/jobs/run_dryrun1_tsai.py --modes layer --steps 40 --repeat 1 --skip-ckpt --skip-nsys --out out
Config:          teams/06-performance/configs/g5_t2_base.yaml
Inputs:          data.source=synthetic (script sets this)
Hardware:        1 GPU (same class of ~24 GB lab card as #690; B=8 expected OK; script retries B=8,4,2,1 on OOM)
Max time:        90
Precision:       bf16 (g5_t2_base)
Measures:        layer shares/counts from prof; GPU name (nvidia-smi.txt); commit SHA in out/result.json; batch_size that fitted
Expected result: exit 0; out/result.json with layer prof step; tip fills TSAI share/% cells only (clean step already from #690; no invented ms)
Outputs:         out/result.json, out/prof/, out/logs/, out/nvidia-smi.txt; script deletes large traces so out/ stays small
Test log:        teams/06-performance/jobs/2026-11-24-dryrun1-tsai-slim-layer.log (own machine, --smoke-cpu slim flags, PASS)
```

## Pins

| Item | Value |
| :--- | :--- |
| Prior lab run | class [#690](https://github.com/theschoolofai/era-v5-lab/pull/690) **partial** — clean median ~12.0 s/step @ B=8; layer/nsys/`result.json` missing |
| Wrapper harden | class [#775](https://github.com/theschoolofai/era-v5-lab/pull/775) (included in this PR if not yet on `main`) |
| Config | `teams/06-performance/configs/g5_t2_base.yaml` |
| `moe.dispatch` | **`loop`** (same as #690; not `#486` sorted) |
| Tag | `dryrun1_tsai` (prof tag prefix) |
| Related | tip [#96](https://github.com/vaibh27/era-v5-lab/pull/96) landed clean step only |

## Notes

- **Do not** re-run full clean+layer+trace+ckpt+nsys (that is why #690 timed out on the slow card).
- Clean need not be re-run; accept #690 clean for step-time cells.
- nsys only if Rohan grants a separate 3+ h window (not this job).
- After PASS: fill tip share/% TSAI cells from returned layer JSON only.
- Smoke: `python -B teams/06-performance/jobs/run_dryrun1_tsai.py --smoke-cpu --modes layer --steps 3 --skip-ckpt --skip-nsys --out out`
