# KE2 output shape (for G5)

**Status:** revalidated 2 Nov on v0, v0.1, v1-c1 and the committed C1, C2 and C3. Not yet measured on
Team 3's week-2 replacements C1-s0, C2-s0 and C3-s0, nor on the v2 file. Both P = 32 and P = 64 are
supported; P = 32 is recommended.

## Shape

KE2 replaces the token-embedding table. Each token ID becomes a fixed vector (no learned
weights), followed by one learned linear layer.

| Step | Shape | dtype |
|---|---|---|
| Input: token IDs | `(B, T)` | int64 |
| KE2 code | `(B, T, D)`, with `D = 256 · P` | float32 |
| Projection `Linear(D, d_model, bias=False)` | `(B, T, d_model)` | float32 |

`B` = batch size, `T` = sequence length, `d_model` = model width (open; set by G5 / TSAI).
The final shape is the same as a standard `nn.Embedding`. KE2 does not change tokenization,
so `T` for a given text is the same as with a standard embedding.

| P | D |
|---|---|
| **32 (recommended)** | **8,192** |
| 64 | 16,384 |

## Settings

| Setting | Value | Source |
|---|---|---|
| `pos_dim` (P) | 32; 64 supported | The longest token in every measured candidate is 32 bytes, so P = 32 cuts nothing off and gives 0 raw-table collisions (`results/tokenizer_candidates/summary.json`) |
| `char_dim` | 256 | One slot per possible byte value (fixed) |
| `D` | `256 · P` | Codec definition |

`pos_dim` is the byte position **inside a token** (slot 0 = first byte). It is unrelated to the
token's position in the sequence; sequence positions (e.g. RoPE) are handled as usual.

### P = 32 vs P = 64

| | P = 32 | P = 64 |
|---|---|---|
| `D` (numbers per token) | 8,192 | 16,384 |
| Projection parameters at `d_model = 768` | 6.29 M | 12.58 M |
| Code memory per token (float32) | 32 KB | 64 KB |
| Code memory for 8,192 tokens (e.g. `B = 8`, `T = 1,024`) | 256 MB | 512 MB |
| Tokens longer than P (cut off) | 0 | 0 |
| Collisions | 0 | 0 |
| Slots used on average (candidate means = 6.5854–7.1404 bytes) | 20.58–22.31 % | 10.29–11.16 % |

On every measured candidate both give identical codes for every token's bytes; P = 64 costs twice the size
with no gain. The longest token is exactly 32 bytes, so P = 32 has no spare room: any longer
token in a future tokenizer would be cut off.

## Properties of the code

- Index layout: byte value `b` at position `p` maps to index `b · P + p`.
- Normalised per token: mean ≈ 0, std ≈ 0.9999 (library epsilon 1e-6).
- Before normalisation, a token of `L` bytes has exactly `L` non-zero entries (`L ≤ 32`).
- Deterministic: the same token ID always gives the same vector.
- Special tokens (BOS, EOS, PAD, UNK, …) are encoded from their literal text, so each has
  its own non-zero vector, including PAD.

## Parameter count (input side)

| | Formula | Example at `d_model = 768` |
|---|---|---|
| Standard embedding | `V · d_model` (V = 131,072) | 100.66 M |
| KE2, P = 32 | `8,192 · d_model` | 6.29 M |
| KE2, P = 64 | `16,384 · d_model` | 12.58 M |

KE2's size does not depend on V, so adding special-token slots does not change it.

## Not covered

The output side (the model's next-token layer) is not decided. KE2 decision: 14 Nov.

## Tokenizer-candidate revalidation

The two former pending checks are closed. The compact reproducible outputs are
[`results/tokenizer_candidates/summary.json`](results/tokenizer_candidates/summary.json) and
[`collisions_by_script.csv`](results/tokenizer_candidates/collisions_by_script.csv). Exact affected
token IDs are recorded by collision equivalence group in
[`collision_groups.csv`](results/tokenizer_candidates/collision_groups.csv): every pair of IDs in
one group collides, and `n_pairs = n_tokens · (n_tokens - 1) / 2`. This lossless group form avoids
expanding large groups into hundreds of thousands of redundant pair rows. The tokenizer files and
generated NPZ tables are not committed.

The complete Team 3 verification set was also rerun on v0 and v0.1. For both candidates:

- `verify_no_cross_script_merges.py`: PASS, 301,398 merges and zero cross-script entries.
- `verify_max_byte_length.py`: PASS, 130,716 normal tokens and zero above 32 bytes.
- `verify_kronecker_constraints_unified.py`: PASS at P=32.
- `verify_sarvam_m_structural_identity.py` against itself: PASS.
- Structural comparison with BrahmicTokenizer-131K: identical BPE merges in identical rank order;
  differences are confined to the expected renamed special slots.

One Team 3 verifier reporting bug was observed: `verify_kronecker_constraints_unified.py` prints
`131,072 normal tokens` and `0 special tokens` for v0/v0.1, whereas the tokenizer contains
130,716 normal and 356 special tokens. Its maximum-length and cross-script checks still cover the
vocabulary and pass, but those two displayed category counts should not be used as provenance.

| Candidate | tokenizer.json SHA-256 | V | Maximum raw bytes | Truncated at P=32 | Raw collisions, P=32 / P=64 | Decode collisions, P=32 / P=64 |
|---|---|---:|---:|---:|---:|---:|
| Team 3 v0 | `2de039f2…f2af8e5` | 131,072 | 32 | 0 | 0 / 0 | 1,141 / 1,141 excess tokens |
| Team 3 v0.1 | `a33c9907…6e578` | 131,072 | 32 | 0 | 0 / 0 | 1,141 / 1,141 excess tokens |
| Team 3 v1-c1 | `7d2cff92…6af44` | 131,072 | 32 | 0 | 0 / 0 | 1,098 / 1,098 excess tokens |
| Team 3 C1 | `5d386e2e…e46db9` | 131,072 | 32 | 0 | 0 / 0 | 1,095 / 1,095 excess tokens |
| Team 3 C2 | `84204d78…e35ad3` | 131,072 | 32 | 0 | 0 / 0 | 1,096 / 1,096 excess tokens |
| Team 3 C3 | `54f20825…055306` | 131,072 | 32 | 0 | 0 / 0 | 1,096 / 1,096 excess tokens |

For v0 and v0.1 at each P, the decode table has 10 groups containing 1,151 tokens (1,141
excess tokens), all with the known `decode_collapse` cause. Partial UTF-8 tokens become U+FFFD
under `decode([id])`. The exact raw-byte table has 131,072 unique rows and no collisions. There
are no unexplained (`other`) collision groups in either candidate.

For v1-c1, the same known decode bug forms 17 groups containing 1,115 tokens (1,098 excess
tokens) at either P. Its raw table is also fully injective. Thus the candidate changes the grouping
of lossy decode rows but does not create a raw-code collision or an unexplained collision cause.

C1 has 14 known decode-collapse groups containing 1,109 tokens (1,095 excess). C2 and C3 each
have 15 groups containing 1,111 tokens (1,096 excess). All three have zero raw collisions, zero
truncations and zero unexplained groups at P=32 and P=64.

v0.1 differs from v0 only at token IDs 130822–130826, the five G10 slot renames. Therefore five
raw rows and five decode rows change, while vocabulary size, output shape, maximum byte length,
truncation counts and collision counts stay unchanged. P = 32 is final for v0.1.

The measured row changes along the candidate chain are: v0.1 → v1-c1, 130,720 raw and 130,708
decode rows; v1-c1 → C1, 25,393 rows; C1 → C2, 8,704 rows; and C2 → C3, 2,844 rows. The compact
report stores exact lists for small differences and a count, stable SHA-256 of the ID list, and
first/last examples for large differences.

### Recurring Team 3 candidate gate

Run the same validator within one day of every delivered candidate. The registry already pins the
published hashes for v1-c1 (PR #137), C1, C2 and C3, plus their sample-v0 retrains. A candidate is
reported as measured only after its exact `tokenizer.json` has been supplied or rebuilt and its
SHA-256 has passed the loader gate. At this revision, v0, v0.1, v1-c1 and the committed C1–C3
are measured. v1-c1 was
rebuilt with the exact PR #137 scripts after all 11 corpus byte counts and hashes matched its
manifest; the rebuilt tokenizer matched `7d2cff92…6af44`. C1–C3 were rebuilt from those same
verified corpus files and each matched its published hash. The later sample-v0 retrains C1-s0,
C2-s0 and C3-s0 remain unmeasured because neither their tokenizer files nor their training sample
are present locally. The v2 file in Team 3's `train/v2_manifest.json` (sha `0862f6…bc47`) is likewise unmeasured and is not in the script's hash registry. Manifest claims alone are not copied into the KE collision results.

Reproduce from locally built, hash-verified tokenizer files:

```bash
python teams/04-ke2/src/revalidate_tokenizer_candidates.py \
  --candidate v0=/path/to/v0/tokenizer.json \
  --candidate v0.1=/path/to/v0.1/tokenizer.json \
  --candidate v1-c1=/path/to/v1-c1/tokenizer.json \
  --candidate C1=/path/to/C1/tokenizer.json \
  --candidate C2=/path/to/C2/tokenizer.json \
  --candidate C3=/path/to/C3/tokenizer.json
```

For a newly announced candidate not yet in the registry, pin it on the command line as
`--candidate NAME@FULL_SHA256=/path/to/tokenizer.json`.

Based on: Team 3 tokenizer v0, v0.1, v1-c1 and C1–C3, all accepted only at the full hashes
recorded above and in the generated report; BrahmicTokenizer-131K baseline
`01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff`; and
kronecker-embeddings 0.1.1 (commit d07cb54, as pinned in `src/ke2/config.py`).
