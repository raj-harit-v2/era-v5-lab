# KE2/KAS trainer adapter note

The contract between Team 4 (KE2) and Team 5 (Architecture). Status: 24 Nov 2026,
G5 #717 implementation using the public [#765 fixture contract](fixtures/kas_v2/README.md).
The dry run 1 implementation and evidence are retained below as V1 history.

## Implemented KAS V2 path

Select `model.head_mode: kas_v2`; `dryrun2.yaml` and `kas_v2_smoke.yaml` select this path.
Arms without this setting retain the V1 input codec and dense untied head. This is a new model
configuration, not an automatic conversion of a V1 checkpoint.

| Item | Implemented contract |
|---|---|
| Fixed codec | Shared deterministic `G` (256, 64) and `Phi` (32, 32) from the hash-verified #765 fixture; `d_c = 64`, `L_max = 32`, `D = 2048` |
| Raw bytes | Existing p1536 raw table and true lengths; no `decode([id])`, empty-token substitution or truncation. Missing tokenizer IDs retain `VocabHoleError` semantics in the artifact loader |
| Position code | `M_pos[:, p] = G[b_p] / sqrt(L)` for `p < L`, zero afterwards; no z-normalization |
| Input code | `K = (M_pos @ Phi).reshape(2048)`, row-major over channel and frequency |
| Input projection | Independent bias-free `Linear(2048, d_model)`, normal initialization with std `2048**-0.5`; training projects byte occupancy without materializing the full vocabulary code table |
| Output projection | Independent `head.W_out` (d_model, 2048), same initialization std; output scores use the position domain, with **no Phi applied** |
| Output terms | Length-indexed `head.beta` (33,), trainable `head.unigram` (V,), `head.tok_u` (V, 64), and `head.tok_c` (64, d_model) |
| Parameter roles | All five output parameters under `head.*`; input projection under `embedding.projection.*`. Baseline optimizer assigns both sets to AdamW |
| Tokenizer | p1536, V = 131072, SHA-256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` |
| Special IDs | EOS 130822, BOS 130725, PAD 130726, UNK 130727; ID 36 is not EOS. PAD is not a scored target |

`KASCodec`, `KASInput` and `KASHead` live in
`teams/05-architecture/harness/week2/kas_v2.py`; `LanguageModel` selects them in `model.py`.
The public #765 fixture files are a runtime dependency for the fixed codebook and must be present on the job host.

For final-normalized hidden rows `h`:

```text
S = (h @ head.W_out).reshape(..., 64, 32)
logits[..., v] = head.beta[L_v] * <M_pos[v], S> + head.unigram[v]
                + (h @ head.tok_c.T) @ dropped_tok_u[v]
```

The constructor remains `LanguageModel(m, rows, lengths)`. `head(hidden)` accepts selected hidden rows
or batched sequences and returns full-vocabulary logits; `head.out_features = 131072` for p1536.
Input/output projections are untied. `hidden_from_embeddings` remains available to the recipe owner.

### Prior and dropout

The default prior uses the verified raw #719 counts from
`teams/03-tokenizer/counts/p1536_counts.json` (LF-normalized SHA-256
`0768b5982825645a796abc76ec23c737837cfacc8f6b089335e5ce5446def3a6`).
Initialize `log((counts + 1) / (N + V))`, subtract its vocabulary mean, and store a trainable float32
parameter. All 9702 zero-count IDs receive the add-one floor. `kas_prior.add_eos_per_document`
defaults to false; adding one EOS per document is an explicit adaptation, not an implicit default.
Checkpoint identity records the fixture hash, verified prior provenance and policy.

On every training forward of the head, draw one `(V, 1)` mask with keep probability 0.95 and
use `tok_u * mask / 0.95`. Only the rank-64 token rows are dropped. Each accumulation microbatch
gets a fresh mask; evaluation consumes no dropout RNG. The current trainer does not recompute the
head during backward. Any future activation-checkpoint/reversible path must preserve the same mask
when recomputing a forward, as required by #765.

### Local validation and remaining checks

On CPU, 21 tests passed across `test_week2_kas_v2.py`, `test_week2_kas_terms.py` and
Team 4's `test_kas_v2_fixture.py`. Coverage includes float64 codes/embeddings/logits and fixed-mask
dropout at 1e-10 absolute tolerance, fused fp32 logits at the fixture's row-relative tolerance,
input/head gradients, both canonical full-p1536 fp32/bf16 code fingerprints, actual-head AdamW
membership, strict model reload, step-zero and committed checkpoint/resume, and Team 9 native
weight loading with the seeded probe contract. The fingerprint check constructs canonical codes
on CPU; it does not establish CUDA/bf16 training parity.

CUDA/bf16 training, the full Team 9 watcher/scoring job, and G5 KAS V2 folded export remain to be
validated. Historical V1 fold measurements below and G4's related export evidence are not a
validation of the G5 V2 exporter. No V1-to-V2 checkpoint conversion is implemented.

## The byte table

| Field | Value |
|---|---|
| Format | `format_version` 2, `kind` "raw", `bytes` uint8 (131072, 32), `lengths` int16 (131072,), `pos_dim` 32 |
| Content sha256 | `21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a` (over `"ke2-table-v2\|raw\|32\|"` + bytes + lengths) |
| File sha256 | `e19a6cae8a6e9e5f74c47748f459df4b156bb61b8cec2af485b439c7132a39b0` (the committed file) |
| Rows | 131,072 distinct; 0 truncated; 0 empty; lengths 1 to 32 |
| Built by | `python teams/04-ke2/src/build_tables.py --tokenizer <p1536 tokenizer.json> --pos-dims 32` |

Compare the content sha256, not the file sha256: the content hash identifies the table, the file hash only one copy of it.

## Historical V1 code (dry run 1)

For a token whose raw bytes are b_0 … b_(L−1), L ≤ 32:

- x[b_p · 32 + p] = 1/√L for p < L, and 0 in the other 8,192 − L cells;
- z = (x − mean(x)) / (std(x, unbiased) + 1e-6).

So z has two values, `high[L]` on the L lit cells and `low[L]` everywhere else. The projection is applied as
(high − low) · Σ W[:, b_p·32 + p] + low · Σ W, without building the 8,192-long code. That is mathematically the same as
W · z.

## Historical V1 numerics and training settings

| Item | Rule |
|---|---|
| Mode | Dynamic: the code is computed from the byte table at every step; no V × 8,192 table is stored |
| Embedding arithmetic | fp32 inside the KE2 class (`projection.weight.float()`); the rest of the model follows the run's precision |
| Storing codes in bf16 | Allowed: it moves decode margins by at most 6.2e-8 (`decision_input.md`, section 3) |
| Scoring codes (evaluation decoder) | fp32 or better; never rank bf16-rounded scores (`decision_input.md`, section 3) |
| Projection init | normal(0, 1/√8192) |
| Optimizer group | AdamW with `optim.lr`, with the output head and norm gains; Muon is only for the 2-D block matrices (`HARNESS_WEEK2.md`) |

## Historical V1 evidence

| Check | Result | Where |
|---|---|---|
| Table integrity (`Artifacts`: format, dtypes, shape, lengths, content hash, every row against `tokenizer.json`, BOS/PAD) | passes on the p1536 table and the released tokenizer (`verify_release.py` PASS), 16 Nov | `teams/05-architecture/harness/week2/artifacts.py` |
| Team 5 class against our float64 codec, committed table, all 131,072 ids | passes | #471, `teams/05-architecture/tests/test_week2_ke2_g4_codec.py` |
| Team 5 and Team 6 classes against our float64 codec on the p1536 table, all 131,072 ids, outputs and gradients | within 1.6e-7 | #499, `tests/test_every_id.py`, `results/every_id/` |
| Code → id round trip on the p1536 table, fp32 and bf16 | exact, 0 ties | #499 |
| Dry run 1: `exp2_muon` at T2, seed 1234, p1536, 1,221 steps | COMPLETED, no NaN or inf, val/bpb 1.5159 | #475, TSAI run, 16 Nov |

## How to check

```bash
python -m pytest teams/05-architecture/tests/test_week2_kas_v2.py \
  teams/05-architecture/tests/test_week2_kas_terms.py \
  teams/04-ke2/tests/test_kas_v2_fixture.py -q
```

The artifact checker also applies to the selected arm:

```bash
python teams/05-architecture/harness/check_week2.py <arm.yaml> --tokenizer-release frozen-p1536 \
  --tokenizer teams/03-tokenizer/release/tokenizer.json \
  --byte-table teams/04-ke2/results/tables/p1536-s0/raw_table_P32.npz
python -m pytest teams/05-architecture/tests/test_week2_tokenizer_release.py -q
```

## Open items

1. Done: the dry run 1 manifest is in the repository (#620,
   `teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/manifest.json`). It shows `tokenizer_sha256`
   `e6b93a93…a64b` and `table_content_sha256` `21072027…168a`.
2. Done: trainer support for p1536 merged with this note (#515): `--tokenizer-release frozen-p1536` in
   `train_week2.py` and `check_week2.py`, the pin in `artifacts.py`, and original-byte BPB for the normalizing releases
   (C3 and p1536). The default stays v0.
3. Implemented locally: selected untied KAS V2 codec/head under `head_mode: kas_v2`, using the
   public #765 contract. See the current contract and validation above; #717 remains a draft.
4. Remaining: CUDA/bf16 training, full watcher/scoring validation and V2 fold/export verification.
   The old predicted-vector cosine-decoder/tau investigation is historical and is not the KAS logits path.
