# G6 dry-run-1 Nsight Systems profile — `dryrun1_nsys`

```
Team:            06-performance
Owner:           Shashank (shank343)
Lead approval:   raj-harit-v2
Question:        In dry run 1 (G5 config_v1.yaml), which GPU kernels, perfkit regions (NVTX) and memory copies take the step time, as seen by Nsight Systems?
Script:          teams/06-performance/jobs/run_dryrun1_nsys.py
Command:         python -B teams/06-performance/jobs/run_dryrun1_nsys.py --config teams/05-architecture/configs/config_v1.yaml --tag dryrun1_nsys --out out --synthetic
Config:          teams/05-architecture/configs/config_v1.yaml
Inputs:          synthetic
Hardware:        1 GPU; needs the Nsight Systems CLI `nsys` on PATH (or NSYS=/path/to/nsys)
Max time:        30
Precision:       bf16 (base.yaml default; config_v1 precision is open)
Measures:        top GPU kernels (ms per step, % of kernel time, calls per step); time per perfkit NVTX region; memcpy time and size; CUDA API calls; GPU name; commit SHA; nsys version
Expected result: exit 0; 5 warmup + 3 traced steps; a dryrun1_nsys.nsys-rep of a few MB; GEMM and MoE dispatch/expert kernels near the top of the kernel table
Outputs:         out/dryrun1_nsys.nsys-rep, out/dryrun1_nsys_*.csv, out/dryrun1_nsys.md, out/dryrun1_nsys_inner.json, out/result.json (under 50 MB in total)
Test log:        teams/06-performance/jobs/2026-11-16-dryrun1-nsys.log (Colab GPU with nsys, exit 0; plus --smoke-cpu exit 0)
```

## Pins

| Item | Value |
| :--- | :--- |
| Class `main` pin (G5 signed) | `aec75af` (#447 / `config_v1.yaml`) |
| Config | `teams/05-architecture/configs/config_v1.yaml` → `teams/06-performance/configs/base.yaml` |
| Tag | `dryrun1_nsys` |
| `mfu_method` | `g6-v1` (not computed by this job) |
| Branch | `g6/job-w3-dryrun1-nsys` ← class `main` (not arm) |
| Companion job | `dryrun1_prof` (#486, torch.profiler) |

## Notes

- Same model as `dryrun1_prof` (#486): `config_v1.yaml` is mapped onto `configs/base.yaml` with the same key mapping as `run_dryrun1_prof.py` (checked: identical overrides), MoE `dispatch=sorted`. Open (null) sizes keep the base.yaml small width.
- The script re-runs itself under `nsys profile --trace=cuda,nvtx --capture-range=cudaProfilerApi`. It runs 5 untraced warmup steps, then traces 3 steps between `cudaProfilerStart` and `cudaProfilerStop`. Each perfkit region is an NVTX range (perfkit trace-mode recorder), plus one `dryrun1_nsys.step<i>` range per step.
- After the capture it runs `nsys stats` (`cuda_gpu_kern_sum`, `nvtx_sum`, `cuda_gpu_mem_time_sum`, `cuda_gpu_mem_size_sum`, `cuda_api_sum`) to CSV and deletes the SQLite export.
- Times under nsys include tracing overhead: they rank kernels and regions. Step time comes from `dryrun1_prof`.
- If `nsys` is not on the node, the job stops at once with exit 3 and runs nothing.
- After TSAI PASS: Shashank fills the Nsight notes in tip `results/profile_dryrun1.md` from `out/dryrun1_nsys.md` and the CSVs only (GPU + SHA on every row, no invented ms). The `.nsys-rep` goes to a gist, not tip.
