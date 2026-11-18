# G4 public embedding timing (p1536)

```
Team:            04-ke2
Owner:           Avnish Midha (avnishbm)
Lead approval:   pending G6 lead review
Question:        On one lab CUDA GPU, what are the input-embedding, output-head, argmax and complete-step times for Team 6's public embedding path using the frozen p1536 table? Record device, SHA, median, p10, p90 and spread.
Script:          teams/04-ke2/src/timing/bench_public_ke.py
Smoke command:   python -B teams/04-ke2/src/timing/bench_public_ke.py --device cuda --batch-size 2 --seq-len 16 --decode-queries 16 --warmup 1 --steps 3 --skip-cpu-reference --out out/g4_public_p1536_cuda_smoke.json
Full command:    python -B teams/04-ke2/src/timing/bench_public_ke.py --device cuda --batch-size 2 --seq-len 16 --decode-queries 16 --warmup 10 --steps 100 --skip-cpu-reference --out out/g4_public_p1536_cuda.json
Inputs:          p1536 raw P=32 table; tokenizer SHA-256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b; table content SHA-256 21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a
Dependency:      Check out this G4 timing branch in the lab repository. The table is present in the branch; the script rejects a table whose content hash differs.
Hardware:        1 CUDA GPU
Max time:        10 minutes
Precision:       fp32 training path; CPU float64 reference omitted in the CUDA job (measured separately)
Measures:        input embedding, dense output head, argmax and complete training step; p10/median/p90/spread
Local check:     CPU and Apple M2 MPS both completed end to end; Team 6 timer tests: 24 passed, 2 CUDA-only skipped. The same CUDA-job mode also completed 10 CPU steps in 0.502 s. See teams/04-ke2/results/timing/README.md and the checked-in CPU/MPS JSON files.
Last output:     p1536 table 21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a CPU reference skipped; complete_training_step: median 19.969 ms (n=10); wall_seconds: 0.502 (CPU job-mode smoke; CUDA result pending)
Expected result: Run the smoke command first. Continue to the full command only if smoke exits 0 and prints the verified table hash. Retain both JSON files and stdout with GPU model, exact commands, p10/median/p90/spread. Report CUDA results only after the full run. The reference decoder is separately CPU-tested and intentionally omitted from this job.
Outputs:         out/g4_public_p1536_cuda_smoke.json, out/g4_public_p1536_cuda.json and captured stdout (small JSON/log only)
```

Scope: synthetic 2 x 16 batch, one block, width 64. This is a small diagnostic timing request, not a production throughput or architecture comparison. Training IDs are drawn from the full vocabulary with a fixed seed. No text corpus or tokenizer download is needed.
