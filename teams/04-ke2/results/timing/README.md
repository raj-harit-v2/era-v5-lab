# Public KE timing notes

## Isolated embedding microbenchmark

`src/timing/bench_public_ke.py` times only `model.tok(x)` on the frozen p1536
raw P=32 table. It runs in eval mode with gradients disabled and uses Team 6's
`StepTimer`. The JSON and stdout include the table hash, GPU name (when run on
CUDA), and checkout commit SHA. This is an isolated operation measurement; it
is not the G6 Level-3 `embed.ke` region time inside a complete training step.

CPU smoke command and output from this checkout:

```text
python -B teams/04-ke2/src/timing/bench_public_ke.py --device cpu --batch-size 2 --seq-len 16 --warmup 1 --steps 3 --out /tmp/g4_model_tok_cpu_smoke.json
gpu_name: not applicable
commit_sha: 69970092d242a34774856742631714c265c8df4f
dirty: True
p1536 table 21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a
model.tok(x)_eval_no_grad: median 0.185 ms (n=3)
wall_seconds: 0.311
```

This confirms the updated command completes locally, but it was run from a
dirty follow-up checkout and is only a smoke check, not a gate result.

The CUDA microbenchmark is approved for a three-step smoke followed by a
100-step diagnostic run from the merged main SHA. For D5 / dry-run-1 KE cost, use the G6
layer/trace harness with the same one-layer, width-64 configuration, code SHA,
GPU, and p1536 table pin. The current G6 `load_g4_table` path still selects the
earlier table, so that matched run must wait for explicit p1536 table support
in the G6 harness. Do not substitute the isolated `model.tok(x)` result for
the Level-3 region result.

## Historical exploratory outputs from merged PR #588

`public_ke_p1536_cpu.json` and `public_ke_p1536_mps.json` preserve the original
broad CPU/MPS runs, which timed the embedding, output head, argmax, full step,
and CPU reference encode/decode. Those records are retained as historical
evidence. They are not the current microbenchmark contract and their values
must not be compared directly with G6 Level-3 part timings.
