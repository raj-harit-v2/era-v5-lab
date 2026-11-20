# G4 isolated `model.tok(x)` microbenchmark (p1536)

```
Team:            04-ke2
Owner:           Avnish Midha (avnishbm)
Lead approval:   approved for CUDA diagnostic run in the later Team 6 review of #588
Question:        On one lab CUDA GPU, how long does the isolated `model.tok(x)` call take in eval/no-grad mode with the frozen p1536 table? Record GPU name, checkout SHA, median, p10, p90 and spread.
Script:          teams/04-ke2/src/timing/bench_public_ke.py
Smoke command:   python -B teams/04-ke2/src/timing/bench_public_ke.py --device cuda --batch-size 2 --seq-len 16 --warmup 1 --steps 3 --out out/g4_public_p1536_cuda_smoke.json
Full command:    python -B teams/04-ke2/src/timing/bench_public_ke.py --device cuda --batch-size 2 --seq-len 16 --warmup 10 --steps 100 --out out/g4_public_p1536_cuda.json
Inputs:          p1536 raw P=32 table; tokenizer SHA-256 e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b; table content SHA-256 21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a
Dependency:      Class main contains the isolated diagnostic from PR #624 at merge SHA 17fd544c57e207aebe6ee692444338c9e18753ea. Check out that commit or a later class-main commit containing it; record the exact checkout SHA in the CUDA JSON/stdout. The table content hash is checked.
Hardware:        1 CUDA GPU
Max time:        10 minutes
Precision:       fp32 inference embedding call; no grad
Measures:        isolated `model.tok(x)` only, via StepTimer; p10/median/p90/spread. This is not the Level-3 `embed.ke` part inside a full step.
Local check:     CPU and Apple M2 MPS runs completed end to end; previous exploratory outputs are in teams/04-ke2/results/timing/. The script records GPU name (CUDA) and checkout commit SHA in JSON and stdout.
Expected result: Run the CUDA smoke first, then the 100-step diagnostic only after smoke exits 0 and prints the verified table hash, GPU name and clean checkout SHA. For dry-run-1 / D5 KE cost, use the G6 layer/trace harness on the same one-layer d=64 config, checkout SHA, GPU and p1536 table pin.
Outputs:         out/g4_public_p1536_cuda_smoke.json, out/g4_public_p1536_cuda.json and captured stdout (small JSON/log only)
```

Scope: synthetic 2 x 16 batch, one block, width 64. This is an isolated diagnostic operation, not a full-step KE cost or a production throughput comparison. IDs are drawn uniformly from the full vocabulary with a fixed seed. No text corpus or tokenizer download is needed.
