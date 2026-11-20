# KE2 output shape (for G5 and G12)

**Status:** Gate 3 p1536-s0 is the current frozen tokenizer (16 Nov); its exact file hash passed
the loader gate and both P = 32 and P = 64 were measured. C3-s0 remains a historical result.
Both P values are supported; P = 32 is recommended and is the path dry run 1 trains (#475).
For export and serving (Team 12), see [Export: fold into a normal embedding table](#export-fold-into-a-normal-embedding-table-for-g12).

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
| Slots used on average (current p1536 mean = 7.8887 bytes) | 24.65 % | 12.33 % |

On every measured candidate both retain every token's bytes; P = 64 costs twice the size
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

## Output side

No KE2 output head is chosen. Dry run 1 and the Team 5 trainer use a dense untied head,
`nn.Linear(d_model, 131072, bias=False)` (TSAI, 15 Nov; `trainer_adapter.md`). KE2 is on the input only.

## Export: fold into a normal embedding table (for G12)

KE2 needs no runtime code at inference. The code of a token depends only on its ID, and the projection is
linear, so every ID has one fixed embedding row. Computing all rows once gives an ordinary `V × d_model`
table, which llama.cpp loads as `token_embd.weight` and Hugging Face / vLLM load as
`model.embed_tokens.weight`. The fold is exact: a lookup in the folded table returns the same vector the
trainer computes.

### What is in the checkpoint

A `train_week2.py` `checkpoint.pt` holds the state dict under `"model"`. The KE2 part is:

| Key | Shape, dtype | What |
|---|---|---|
| `embedding.projection.weight` | `(d_model, 8192)`, float32 | the only learned KE2 weight, `W` |
| `embedding.rows` | `(131072, 32)`, uint8 | buffer: the raw byte table, one row per ID |
| `embedding.lengths` | `(131072,)`, int64 | buffer: the byte length L of each ID |
| `head.weight` | `(131072, d_model)` | the dense untied output head; export as is (`output.weight`) |
| `mtp_head.weight` | `(131072, d_model)` | only if the run uses MTP; G12 drops it at export |

Before folding, check that `embedding.rows` and `embedding.lengths` are the frozen p1536 table: content
sha256 `21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a` over
`"ke2-table-v2|raw|32|"` + bytes + lengths (int16), as in `trainer_adapter.md`.

### The fold

For an ID with raw bytes b_0 … b_(L−1):

```
E[id] = (high[L] − low[L]) · Σ_{p<L} W[:, b_p · 32 + p]  +  low[L] · Σ_j W[:, j]
```

`high[L]` and `low[L]` are the two values of the z-normalised code (Lemma 1): with D = 8,192, v = 1/√L,
mean = L·v/D, var = (L·(v − mean)² + (D − L)·mean²)/(D − 1) and s = √var + 1e-6,
high = (v − mean)/s and low = −mean/s (`src/ke2/codec.py`, `code_values`). The 1e-6 is added to the
standard deviation, not to the variance. This is the same arithmetic as Team 5's `KE2.projected`.

The simplest correct fold runs Team 5's `KE2` module over `torch.arange(131072)` in fp32, which is what
G12's `scripts/export_hf.py` (`fold_ke2`) does. Each row is computed independently of the others, so the
chunk size does not matter.

### Measured (`src/export/fold_check.py`, `results/fold/fold_check_P32.md`)

Frozen p1536 table, d_model 512 (T2 width), with a random projection at Team 5's initialisation (no trained
checkpoint is in the repository yet). CPU. The bit-for-bit check uses 16,384 sampled IDs; the fp32, bf16 and
special-token checks use all 131,072 IDs.

| Check | Result |
|---|---|
| Folded-table lookup vs Team 5 `KE2(ids)`, 16,384 sampled IDs (eight random `(8, 256)` batches) | 0 of 16,384 rows differ, bit for bit |
| fp32 fold vs the float64 closed form, all 131,072 IDs | max abs error 1.4e-6; 3.8e-7 of the row's largest entry |
| Folded table stored in bf16 vs float64, all 131,072 IDs | max 3.87e-3 of the row's largest entry (median 2.33e-3); the bf16 unit roundoff is 2⁻⁸ = 3.91e-3 |
| Special tokens (356 IDs, Team 3 p1536 manifest) | every row finite and non-zero |
| Fold time | 5 s on a laptop CPU |

How to read this for export:

- **fp32 storage reproduces training exactly.** bf16 storage adds only the usual bf16 rounding of each
  entry; nothing KE2-specific is lost. Quantizing `token_embd` further (Q8_0, Q4_K) is measured like any
  other tensor.
- **Special tokens need no special case.** Each of the 356 special IDs is encoded from its literal bytes,
  so it has its own non-zero row, including pad (130726). eos is ID 130822 `<|endoftext|>`; ID 36 has no
  role. No two IDs share a code (0 raw collisions, `results/tables/p1536-s0/`), so no two rows of `E` are
  forced to be equal.
- **Unchanged by the fold:** the tokenizer, the token IDs, the output head, and the shape
  `(B, T, d_model)`. The served model needs neither the byte table nor the KE2 codec.

### Size after the fold

The fold gives up KE2's parameter saving at inference: the table grows with V, while training stored only
the projection.

| d_model | Trained KE2 projection (8,192 × d_model) | Folded table (131,072 × d_model) | Folded table in bf16 |
|---:|---:|---:|---:|
| 256 (T1) | 2.10 M | 33.55 M | 64 MiB |
| 512 (T2, dry run 1) | 4.19 M | 67.11 M | 128 MiB |
| 640 (T3) | 5.24 M | 83.89 M | 160 MiB |
| 4,096 | 33.55 M | 536.87 M | 1 GiB |

When a model card or a size table counts parameters, say which one it uses: the training count has the
projection, and the served count has the folded table.

### On a trained checkpoint

`fold_check.py --checkpoint <run>/checkpoint.pt` repeats the checks with the trained projection. It first
checks that the checkpoint's byte table is the p1536 table. Dry-run checkpoints stay on TSAI's machines, so
this runs inside G12's export job (#508), next to G12's logit test (export vs Team 5's model on 64 prompts).
The fold itself does not depend on the trained values: a lookup in the folded table equals `KE2(ids)` for
any `W`.

Notes for `teams/12-quantization/docs/unsupported_parts.md` §1:
- The projection is `embedding.projection.weight`, not `ke2.proj.weight`.
- `ke2.codec.encode_ids` wraps the upstream library's fp32 codec. The reference for the trained model is
  Team 5's `KE2` module, which `export_hf.py` already uses.

## Tokenizer-candidate revalidation

The two former pending checks are closed. The compact reproducible outputs are
[`results/tokenizer_candidates/summary.json`](results/tokenizer_candidates/summary.json) and
[`collisions_by_script.csv`](results/tokenizer_candidates/collisions_by_script.csv). Exact affected
token IDs are recorded by collision equivalence group in
[`collision_groups.csv`](results/tokenizer_candidates/collision_groups.csv): every pair of IDs in
one group collides, and `n_pairs = n_tokens · (n_tokens - 1) / 2`. This lossless group form avoids
expanding large groups into hundreds of thousands of redundant pair rows. Tokenizer files are
not committed; the Gate 3 p1536 tables are committed under `results/tables/p1536-s0/`.

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
| Team 3 C1 sample-v0 | `36acf126…01c82a2` | 131,072 | 32 | 0 | 0 / 0 | 1,094 / 1,094 excess tokens |
| Team 3 C2 sample-v0 | `b0d44576…f8488a` | 131,072 | 32 | 0 | 0 / 0 | 1,095 / 1,095 excess tokens |
| Team 3 C3 sample-v0 (previous freeze, #340) | `15468e66…2ddc3` | 131,072 | 32 | 0 | 0 / 0 | 1,095 / 1,095 excess tokens |
| Team 3 p1536 sample-v0 (current freeze, #414) | `e6b93a93…25a64b` | 131,072 | 32 | 0 | 0 / 0 | 857 / 857 excess tokens |

For C3-s0 and p1536-s0, merged Team 3 PR #407 names `<|endoftext|>` (id 130822) as eos in both
`release/special_tokens_map.json` and `release/tokenizer_config.json`. ID 36 `<|end_of_text|>`
remains a distinct special token with no named model role. This role assignment does not change
the byte-table collision counts above.

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

C1 sample-v0 has 13 known decode-collapse groups containing 1,107 tokens (1,094 excess), C2
sample-v0 has 14 groups containing 1,109 tokens (1,095 excess), and frozen C3-s0 has 14 groups
containing 1,109 tokens (1,095 excess), at both P values. All three have zero raw collisions,
zero truncations, zero empty rows and zero unexplained groups. Their separate
compact reports are under
[`results/tokenizer_candidates/sample_v0/`](results/tokenizer_candidates/sample_v0/) so the
earlier C1–C3 candidate chain remains intact. C2 sample-v0 changes exactly 8,704 raw rows and
8,704 decode rows relative to C1 sample-v0. C3-s0 changes 5,406 raw rows and 5,406 decode rows
relative to C2-s0; its SHA-256 matches Team 3's frozen #340 artifact.

Gate 3 p1536-s0 has 10 known `decode_collapse` groups containing 867 tokens (857 excess)
at both P values, with zero raw collisions, truncations, empty rows or unexplained groups.
Its maximum raw token length is 32 bytes. Relative to C3-s0, exactly 13,824 raw rows and
13,824 decode rows changed. The independently built raw and decode NPZ tables and manifest
are under [`results/tables/p1536-s0/`](results/tables/p1536-s0/); the compact collision
report is under [`results/tokenizer_candidates/gate3_p1536/`](results/tokenizer_candidates/gate3_p1536/).
The tokenizer itself is kept outside the repository.

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
SHA-256 has passed the loader gate. At this revision, v0, v0.1, v1-c1, the committed C1–C3, C1-s0,
C2-s0, C3-s0 and p1536-s0 are measured. v1-c1 was
rebuilt with the exact PR #137 scripts after all 11 corpus byte counts and hashes matched its
manifest; the rebuilt tokenizer matched `7d2cff92…6af44`. C1–C3 were rebuilt from those same
verified corpus files and each matched its published hash. C1-s0 and C2-s0 were measured from
locally supplied tokenizer files after their full SHA-256 values matched the published identities.
C3-s0 was rebuilt from the #195 job with checksum-verified sample-v0 and corpus60 inputs; its SHA-256
matched Team 3's frozen #340 artifact (`15468e66…2ddc3`). The v2 file in Team 3's `train/v2_manifest.json` (sha
`0862f6…bc47`) is likewise unmeasured and is not in the script's hash registry. Manifest claims
alone are not copied into the KE collision results.
The current p1536-s0 file matched the Gate 3 announced SHA-256 (`e6b93a93…25a64b`) before its
tables and collision report were generated. New tokenizer-dependent work must use this hash and
the p1536-s0 tables; earlier C3 and baseline results are preserved as historical measurements.

Reproduce from locally built, hash-verified tokenizer files:

```bash
python teams/04-ke2/src/revalidate_tokenizer_candidates.py \
  --candidate v0=/path/to/v0/tokenizer.json \
  --candidate v0.1=/path/to/v0.1/tokenizer.json \
  --candidate v1-c1=/path/to/v1-c1/tokenizer.json \
  --candidate C1=/path/to/C1/tokenizer.json \
  --candidate C2=/path/to/C2/tokenizer.json \
  --candidate C3=/path/to/C3/tokenizer.json

python teams/04-ke2/src/revalidate_tokenizer_candidates.py \
  --candidate C1-s0=/path/to/c1-sample-v0/tokenizer.json \
  --candidate C2-s0=/path/to/c2-sample-v0/tokenizer.json \
  --candidate C3-s0=/path/to/c3-sample-v0/tokenizer.json \
  --out teams/04-ke2/results/tokenizer_candidates/sample_v0

python teams/04-ke2/src/revalidate_tokenizer_candidates.py \
  --candidate C3-s0=/path/to/c3-sample-v0/tokenizer.json \
  --candidate p1536-s0=/path/to/p1536-sample-v0/tokenizer.json \
  --out teams/04-ke2/results/tokenizer_candidates/gate3_p1536

python teams/04-ke2/src/build_tables.py \
  --tokenizer /path/to/p1536-sample-v0/tokenizer.json \
  --out teams/04-ke2/results/tables/p1536-s0 --pos-dims 32 64
```

For a newly announced candidate not yet in the registry, pin it on the command line as
`--candidate NAME@FULL_SHA256=/path/to/tokenizer.json`.

Based on: Team 3 tokenizer v0, v0.1, v1-c1, C1–C3, C1-s0, C2-s0, C3-s0 and p1536-s0, all accepted only at the full
hashes recorded above and in the generated reports; BrahmicTokenizer-131K baseline
`01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff`; and
kronecker-embeddings 0.1.1 (commit d07cb54, as pinned in `src/ke2/config.py`).
