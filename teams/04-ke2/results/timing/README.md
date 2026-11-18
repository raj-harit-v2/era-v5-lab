# Public code timing on the p1536 raw table

These are 100-step CPU and Apple M2 MPS checks of Team 6's `models.ke2.KE2Embedding` and Team 4's
`decode_ref.py`, using Team 6's `perfkit.timer.StepTimer`. The public
`embedding=ke2` setting computes the projected public V1 code using
`embedding_bag`. The measurements below apply to that public implementation.
Team 6's module takes G4's code values and raw bytes; it implements the
projection itself. This benchmark injects the frozen p1536 table explicitly,
because Team 6's default table loader still points to the earlier pinned table.

The verified p1536-s0 P=32 table has tokenizer SHA-256
`e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`
and content SHA-256 `21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a`.
The synthetic training batch is 2 × 16 token IDs, sampled uniformly from the
full vocabulary with NumPy seed 0, with a one-block, width-64
Team 6 GPT. The reference decoder checks 16 unprojected float64 code vectors
sampled with seed 1 against all 131,072 raw table rows. It recovered all 16 IDs. Decode is an
inference reference operation, outside the timed training step.
The training input ID digest is `e8b9827ae7e3b618f1e1883f98963b2a58ac0b11b4ffef60931c9e12bd47ed2c`;
its token lengths span 2–13 bytes. This samples vocabulary entries, not
their corpus-frequency distribution.

Exact command from the lab repository root:

```bash
/Users/ai/ERAV5/.eraenv/bin/python teams/04-ke2/src/timing/bench_public_ke.py \
  --device cpu --batch-size 2 --seq-len 16 --decode-queries 16 \
  --warmup 10 --steps 100 \
  --out teams/04-ke2/results/timing/public_ke_p1536_cpu.json
```

Last output lines:

```text
p1536 table 21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a decoded 16/16 sampled IDs
training_input_embedding_forward: median 0.129 ms (n=100)
training_output_head_forward: median 1.257 ms (n=100)
output_token_argmax: median 0.847 ms (n=100)
complete_training_step: median 19.671 ms (n=100)
reference_code_encode_cpu_float64: median 0.058 ms (n=100)
reference_code_decode_cpu_float64: median 113.508 ms (n=100)
wall_seconds: 15.317
```

The JSON records the platform, PyTorch version, thread count, workload,
timer statistics and table hash. The training step includes forward, backward
and AdamW. The separately timed output head is a dense logit projection;
`argmax` chooses an ID from its logits. Neither is the code-vector decoder.
The hot path uses batched tensor/NumPy operations, and CUDA event readings
occur after timed steps. Team 6's `correctness.framework` pairs for the public
embedding passed (`ke2.edge`, `ke2.bf16`). Its frozen p1536 input-path check
also passed against the float64 reference, including the projection gradient.
The CPU run has 100 samples, but Team 6's formal comparison gate requires a
same-GPU CUDA run; no CUDA timing or performance-gate verdict is claimed.

The same workload also ran on the Apple M2 GPU. Exact command:

```bash
/Users/ai/ERAV5/.eraenv/bin/python teams/04-ke2/src/timing/bench_public_ke.py \
  --device mps --batch-size 2 --seq-len 16 --decode-queries 16 \
  --warmup 10 --steps 100 \
  --out teams/04-ke2/results/timing/public_ke_p1536_mps.json
```

Last output lines:

```text
p1536 table 21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a decoded 16/16 sampled IDs
training_input_embedding_forward: median 0.412 ms (n=100)
training_output_head_forward: median 2.874 ms (n=100)
output_token_argmax: median 0.407 ms (n=100)
complete_training_step: median 27.231 ms (n=100)
reference_code_encode_cpu_float64: median 0.058 ms (n=100)
reference_code_decode_cpu_float64: median 113.433 ms (n=100)
wall_seconds: 17.366
```

The MPS path uses Team 6's synchronized wall-clock timer, not CUDA events.
The reference encode/decode measurements remain CPU float64 in both runs.
This is a device-specific measurement, not a CPU-versus-GPU speed ratio:
the timer mechanisms differ, and the runs were not a controlled pair.
The input-operation spread is about 20% on both devices, and the MPS output
head spread is 33.5%; these individual-operation medians are not precise
enough for a 5% comparison claim. The full-step spread is 5.7% on CPU and
5.5% on MPS. The JSON files contain p10 and p90 for each operation.

For G6: on a CUDA host, run the same workload with `--device cuda --skip-cpu-reference` and
write the output to an untracked job directory. The reference code encode and
decode measurements above remain CPU float64 and are omitted from the CUDA job.
Report the device, command, p10/median/p90, spread and full JSON. The decoder
returns token IDs and raw bytes from unprojected code vectors; it is not called
once per training step.
