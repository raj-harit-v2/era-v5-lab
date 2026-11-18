Team:            07-infrastructure
Owner:           Max (uz9ai)
Lead approval:   sureshmantha
Question:        What do bus bandwidth (all-reduce, reduce-scatter, all-gather, all-to-all), ECC, temperature and Xid look like on a healthy shared GPU node over 5 full health runs, so that the real thresholds in health/thresholds.yaml can replace the vendor limits (ADR 0003, baseline method)
Script:          teams/07-infrastructure/jobs/health_baseline/run.sh 
Command:         bash teams/07-infrastructure/jobs/health_baseline/run.sh
Config:          teams/07-infrastructure/jobs/health_baseline/expected_results.json
Inputs:          synthetic
Hardware:        2 GPU
Max time:        30      (about 10 minutes on 2 GPUs; the rest is for DCGM diag level 2 x 5 if dcgmi is installed)
Precision:       fp32
Measures:        busbw in GB/s per collective and message size (1 MB to 1 GB), min/median/max over 5 runs and the 0.9 x median floor; max abs error of each collective (must be 0); ECC uncorrectable per GPU; temperature; PCIe width; NVLink state; Xid events; verdict and runtime of each run
Expected result: all 5 runs verdict "pass" and admit_training true; every collective status "pass" with max_error 0 on NCCL, world size 2; ECC 0 on every GPU; no Xid; busbw spread over the 5 runs 10% or less for messages of 64 MB and larger; Team 08's validator prints PASS for every report. Exact rules: expected_results.json
Outputs:         out/*.json, out/*.jsonl, out/*.txt, out/*.log
Test log:        teams/07-infrastructure/jobs/2026-11-04-health-baseline.log

Note for the reviewer: `out/baseline_summary.json` holds the numbers, `out/results_check.txt` says whether every expectation was met, and `out/validation.txt` is Team 08's validator output. If `out/results_check.txt` says the Xid check was not visible, the kernel log was not readable on that node; the Xid result is then "could not look", not "no errors".

A collective needs 2 or more ranks. With 1 GPU the job still runs, but skips the collectives and gives no bandwidth baseline

Python packages: `torch==2.5.1`, `pyyaml==6.0.2`. The test log used Python 3.13.7.