# KAS V2 integration fixture: the contract with numbers

For Team 5's integration PR (#717). This folder answers "how should raw token bytes become the 2,048 code, and how do
hidden states, byte scores, unigram and rank-64 correction become logits" with a small exact fixture produced by the
pinned reference (`The-School-of-AI/ke2-head` 81cf1c0, arm `a10_kas_tokdrop`) at the chosen configuration, plus the
equations written out in plain numpy. No reference source is copied; the reference stays private (TSAI, 22 Nov).

| File | What |
|---|---|
| `kas_v2_fixture.npz` | 48 real p1536 tokens (5 special ids, the 32- and 31-space worst pair, 41 others): codebooks, codes, parameters, 8 hidden states and the reference logits, float64 |
| `kas_v2_fixture.json` | ids, bytes, tolerances, the sha256 of the npz, and two fingerprints of the full 131,072 x 2,048 code table (fp32 and bf16) |
| `check_kas_v2_fixture.py` | the contract as numpy functions, and a checker that compares them (or your module) with the fixture |
| `../../tests/test_kas_v2_fixture.py` | the same check in the test suite |

Generator: `theschoolofai/era-v5-ke2` `code/experiments/make_kas_fixture.py` (private; it uses the reference library). The
generator re-derives every array from `G`, `Phi`, the bytes and the parameters with plain numpy before writing:
codes bit-identical, embedding within 5e-17, logits within 6e-16, so the equations below *are* the reference.

## The contract

**Codec** (`KroneckerCodec(d_c=64, L_max=32)`, D = 2,048, deterministic, float64, no learned parameters).

- `G` (256, 64): the byte codebook, unit-norm rows. Columns 0..7 are the 8 Walsh bit columns of the 256-point
  Sylvester-Hadamard matrix (the sign of `G[b, j]` is bit `j` of byte `b`), columns 8..63 are 56 further Hadamard
  columns chosen with seed 0. `Phi` (32, 32): the real orthonormal DFT basis, `Phi @ Phi.T = I`. Both are in the npz;
  use them as constants.
- Token bytes are the tokenizer's raw bytes (Team 4's raw table, never `decode([id])`); length L is the true byte
  length, 1..32 on p1536 (no token is longer, no token is empty).
- Position matrix `M_pos[v]` (64, 32): column `p` is `G[b_p] / sqrt(L)` for `p < L`; columns `p >= L` are **zero**.
  That is the whole padding and normalisation rule: zero columns past the length, one global `1/sqrt(L)` so every code
  has unit norm. There is no z-normalisation and no per-position scaling.
- Code `K_v = (M_pos[v] @ Phi).reshape(2048)`, row-major over (channel c, frequency k). Exactly invertible.

**Input embedding.** `E_v = K_v @ W_proj`, `W_proj` (2048, d_model), init `randn * 2048**-0.5`, bias-free. The reference
never materialises `K` for the whole vocabulary; it computes the table through the byte-occupancy structure, but the
result is identical to `codes @ W_proj` and that is what the fixture checks.

**Head** (untied: its own `W_out`, nothing shared with `W_proj`). For a hidden state `h_n` (after the final norm):

```
S_n          = (h_n @ W_out).reshape(64, 32)          W_out (d_model, 2048), init randn * 2048**-0.5
byte_score   = <M_pos[v], S_n>  (Frobenius inner product; the head works in the position domain, Phi is not applied)
logits[n, v] = beta[L_v] * byte_score + unigram[v] + (h_n @ tok_c.T) @ tok_u[v]
```

| Parameter | Shape | Init | Notes |
|---|---|---|---|
| `W_out` | (d_model, 2048) | `randn * 2048**-0.5` | fp32 in training, cast with the model |
| `beta` | (33,) | ones | one scalar per token **length** 0..32, indexed by `L_v` |
| `unigram` | (V,) | zeros, then `log((c_v + 1) / (N + V))` minus its mean | counts from the training token stream (#719 for p1536); trainable float32 |
| `tok_u` | (V, 64) | `randn * 0.02 * 64**-0.5` | per-token rows; the only part vocabulary dropout touches |
| `tok_c` | (64, d_model) | `randn * d_model**-0.5` | shared context map |

The fused training path computes `byte_score` for the whole vocabulary with one `embedding_bag` over the byte
occupancy (per-sample weights `1/sqrt(L_v)`), which is exactly the sum above; `logits_f32` in the fixture comes from that
path in float32 and agrees with the float64 equations to 9e-8 relative.

**Vocabulary dropout** (training only; `model.eval()` turns it off): on **every forward call of the head** draw
`keep ~ Bernoulli(0.95)` of shape (V, 1) and use `tok_u * keep / 0.95` in the correction term. Byte scores, `beta`,
`unigram` and `W_out` are untouched. The mask is per forward, so under gradient accumulation each microbatch gets its
own mask; nothing is shared across an optimizer step, and no state is kept. If a trainer recomputes the head in the
backward pass (checkpointing, reversible stacks), derive the mask from the step so the recomputation sees the same one.
The fixture carries one fixed `keep` and `logits_dropped` so the masking arithmetic can be tested without an RNG.

## Tolerances

| Quantity | Tolerance | Fixture value |
|---|---|---|
| `M_pos`, `K`, `E`, `logits` in float64 | 1e-10 absolute | 0, 0, 5e-17, 6e-16 |
| `logits_f32` (fused fp32 path) vs float64 | 1e-5 of each row's largest `|logit|` | 9.3e-8 |
| `logits_dropped` | 1e-10 absolute | 0 |
| full p1536 code table, fp32 and bf16 bit patterns | sha256 equal to the JSON | `--p1536-table` option |

## Run

```bash
python teams/04-ke2/fixtures/kas_v2/check_kas_v2_fixture.py
python teams/04-ke2/fixtures/kas_v2/check_kas_v2_fixture.py --p1536-table teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz
python -m pytest teams/04-ke2/tests/test_kas_v2_fixture.py -q
```

To test your own code, compute `K`, `E` and `logits` from the fixture's `G`, `Phi`, `bytes`, parameters and `h` with
your module, and compare with the fixture arrays at the tolerances above. The two full-table fingerprints check your
codec on every id at once: the fp32 one must match if your codes are right, the bf16 one if your storage rounding is
round-to-nearest-even.

## Related evidence

- Every-ID round trip and bf16 collisions on this codec for p1536: `theschoolofai/era-v5-ke2` #11 (CPU, MPS, CUDA).
- Fold for export (input embedding and head become a plain `nn.Embedding` and `nn.Linear(bias=True)`): era-v5-ke2 #12.
