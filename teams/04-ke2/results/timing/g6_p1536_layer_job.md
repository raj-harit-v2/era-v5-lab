# Team 6 Level-3 timing with a job-scoped p1536 pin

Run these public arms sequentially on one CUDA GPU. The adapter calls Team 6's
`perfkit.bench` with `clean,layer,trace`, leaving its checked-in tokenizer and
table defaults unchanged. Its p1536 SHA gates are in
`teams/04-ke2/src/timing/g6_p1536_bench.py`. The older tokenizer's dense-tied
run is a historical reference; compare the two p1536 arms when attributing
the effect of the input embedding.

Stage the frozen p1536 `tokenizer.json` at `/inputs/p1536/tokenizer.json`
(SHA-256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`)
and the original G6-pinned tokenizer at `/inputs/g6-baseline/tokenizer.json`
(SHA-256 `01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff`).
The public p1536 P=32 table is in `teams/04-ke2/results/tables/p1536-s0/`.
Run `cd teams/06-performance` first, then use the commands below from that
directory. Capture the public checkout SHA and GPU name.

## Smoke

```sh
ERA_PERF_CACHE=/outputs/g6-cache python -B ../04-ke2/src/timing/g6_p1536_bench.py --tokenizer /inputs/p1536/tokenizer.json --table ../04-ke2/results/tables/p1536-s0/raw_table_P32.npz --g6-root . --arm ke2 --device cuda --tag g4_p1536_ke2_smoke --out-dir /outputs/g6 --warmup 1 --steps 3 --trace
ERA_PERF_CACHE=/outputs/g6-cache python -B ../04-ke2/src/timing/g6_p1536_bench.py --tokenizer /inputs/p1536/tokenizer.json --table ../04-ke2/results/tables/p1536-s0/raw_table_P32.npz --g6-root . --arm dense-tied --device cuda --tag g4_p1536_dense_smoke --out-dir /outputs/g6 --warmup 1 --steps 3 --trace
ERA_PERF_CACHE=/outputs/g6-cache python -B -m perfkit.bench --config configs/base.yaml --modes clean,layer,trace --level 3 --warmup 1 --steps 3 --tag g4_old_dense_smoke run.device=cuda run.dtype=fp32 run.batch_size=2 data.source=synthetic data.tokenizer_path=/inputs/g6-baseline/tokenizer.json model.embedding=table model.tie_embeddings=true model.block_size=16 model.n_layer=1 model.n_head=4 model.n_kv_head=4 model.n_embd=64 model.reversible=false optim.name=adamw model.ffn=mlp model.ce_impl=torch bench.out_dir=/outputs/g6
```

Proceed only if all three exit 0 and their JSON metadata reports the intended
tokenizer SHA, same GPU and same model shape. For the two p1536 arms, the
adapter also verifies the table content SHA-256
`21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a`.

## Measurement

```sh
ERA_PERF_CACHE=/outputs/g6-cache python -B ../04-ke2/src/timing/g6_p1536_bench.py --tokenizer /inputs/p1536/tokenizer.json --table ../04-ke2/results/tables/p1536-s0/raw_table_P32.npz --g6-root . --arm ke2 --device cuda --tag g4_p1536_ke2_full --out-dir /outputs/g6 --warmup 10 --steps 100 --trace
ERA_PERF_CACHE=/outputs/g6-cache python -B ../04-ke2/src/timing/g6_p1536_bench.py --tokenizer /inputs/p1536/tokenizer.json --table ../04-ke2/results/tables/p1536-s0/raw_table_P32.npz --g6-root . --arm dense-tied --device cuda --tag g4_p1536_dense_full --out-dir /outputs/g6 --warmup 10 --steps 100 --trace
ERA_PERF_CACHE=/outputs/g6-cache python -B -m perfkit.bench --config configs/base.yaml --modes clean,layer,trace --level 3 --warmup 10 --steps 100 --tag g4_old_dense_full run.device=cuda run.dtype=fp32 run.batch_size=2 data.source=synthetic data.tokenizer_path=/inputs/g6-baseline/tokenizer.json model.embedding=table model.tie_embeddings=true model.block_size=16 model.n_layer=1 model.n_head=4 model.n_kv_head=4 model.n_embd=64 model.reversible=false optim.name=adamw model.ffn=mlp model.ce_impl=torch bench.out_dir=/outputs/g6
```

Report `clean.step_ms`, `metrics.tokens_per_s`,
`layer.regions["fwd:embed.ke"]` for the KE2 arm, layer recorder overhead,
trace path, GPU name and checkout SHA. Level-3 parts are informational;
the clean step and level-2 parts use Team 6's repeat gate. The byte-code
decoder is timed in a separate private codec job because it is not called by
this training step. The isolated `model.tok(x)` result from PR #624 is also
reported separately.

Local end-to-end check (Mac CPU, one measured step per arm): the p1536 KE2,
p1536 dense-tied and older-tokenizer dense-tied commands exited 0. The KE2
trace command exited 0 with
`ERA_PERF_CACHE` set to a writable temporary directory. Its JSON metadata
reported the frozen p1536 SHA and a `fwd:embed.ke` Level-3 region. These CPU
smokes do not establish CUDA timing.
