Team:            07-infrastructure
Owner:           Max (uz9ai)
Lead approval:   sureshmantha
Question:        What do ECC, temperature, PCIe link, NVLink state and Xid look like on a healthy single-GPU node over 5 health runs (prolog mode), so that the real thresholds in health/thresholds.yaml can replace the vendor limits (ADR 0003, baseline method)? Bus bandwidth is not part of this run: one GPU cannot run a collective
Script:          teams/07-infrastructure/jobs/health_baseline/run.sh 
Command:         bash teams/07-infrastructure/jobs/health_baseline/run.sh
Config:          teams/07-infrastructure/jobs/health_baseline/expected_results.json
Inputs:          synthetic
Hardware:        1 GPU
Max time:        30      (a few minutes on 1 GPU: no collectives run; the rest is for DCGM diag level 2 x 5 if dcgmi is installed)
Precision:       fp32
Measures:        ECC uncorrectable per GPU; temperature; PCIe width; NVLink state; Xid events; verdict and runtime of each run (prolog mode). No busbw and no collective error: with 1 GPU the collectives are skipped
Expected result: all 5 runs verdict "pass" and admit_training true (mode prolog, profile gpu1); gpu_inventory sees 1 GPU; ECC 0; no Xid; no collective checks and no allreduce.json (skipped by design); Team 08's validator prints PASS for every report. Exact rules: expected_results.json (profile gpu1)
Outputs:         out/*.json, out/*.jsonl, out/*.txt, out/*.log
Test log:        teams/07-infrastructure/jobs/2026-11-12-health-baseline.log

Note for the reviewer: `out/baseline_summary.json` holds the numbers (no busbw table with 1 GPU), `out/results_check.txt` says whether every expectation was met, and `out/validation.txt` is Team 08's validator output. If `out/results_check.txt` says the Xid check was not visible, the kernel log was not readable on that node; the Xid result is then "could not look", not "no errors".

A collective needs 2 or more ranks. With 1 GPU the job runs in prolog mode, skips the collectives and gives no bandwidth baseline; the bus bandwidth part of ADR 0003 still needs a run on a node with 2 or more GPUs

Python packages: `pyyaml==6.0.2` (`torch==2.5.1` is not needed with 1 GPU; the preflight skips it). The test log used Python 3.13.7.