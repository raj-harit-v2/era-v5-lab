# KE2 trainer adapter note (week 3, task 1)

The contract between Team 4 (KE2) and Team 5 (Architecture) for the KE2 path in the trainer. Both teams point to this
file. Status: 16 Nov 2026, after dry run 1 (#475). Open items 1 and 2 updated 21 Nov; the output head row and items 3
and 4 change with the integration PR (`gate3.md`, handoff section).

## The chosen path

| Item | Value | Source |
|---|---|---|
| Input embedding | KE2: fixed Kronecker byte code, then one learned `Linear(8192, d_model, bias=False)` | Gate 2 |
| Output head | Dense untied `nn.Linear(d_model, 131072, bias=False)`. No KE2 output head. **Superseded 21 Nov** (TSAI; corrected in #702): the capstone output head is the KE2/KAS head, untied, with its own output projection; this row changes with the integration PR (`gate3.md`, handoff section) | TSAI, 15 Nov; `HARNESS_WEEK2.md` |
| Trainer class | `KE2` in `teams/05-architecture/harness/week2/model.py` | Team 5, 16 Nov |
| Arm setting | `embedding: ke2`; `ke1` stays accepted as the older name for the same path | #472 |
| Tokenizer | p1536, `tokenizer.json` sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`, V = 131,072 | TSAI Gate 3 notice; `teams/03-tokenizer/release/` |
| Special ids | eos 130822 `<\|endoftext\|>`, bos 130725, pad 130726, unk 130727. Id 36 is not eos | `teams/03-tokenizer/release/SPECIAL_TOKENS.md` |
| Byte table | Raw table, not `decode([id])` text: `results/tables/p1536-s0/raw_table_P32.npz` | Gate 2, decision 1 |
| P | 32, so D = 256 × 32 = 8,192. Longest p1536 token is 32 bytes; nothing is truncated | `results/tables/p1536-s0/manifest.json` |

## The byte table

| Field | Value |
|---|---|
| Format | `format_version` 2, `kind` "raw", `bytes` uint8 (131072, 32), `lengths` int16 (131072,), `pos_dim` 32 |
| Content sha256 | `21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a` (over `"ke2-table-v2\|raw\|32\|"` + bytes + lengths) |
| File sha256 | `e19a6cae8a6e9e5f74c47748f459df4b156bb61b8cec2af485b439c7132a39b0` (the committed file) |
| Rows | 131,072 distinct; 0 truncated; 0 empty; lengths 1 to 32 |
| Built by | `python teams/04-ke2/src/build_tables.py --tokenizer <p1536 tokenizer.json> --pos-dims 32` |

Compare the content sha256, not the file sha256: the content hash identifies the table, the file hash only one copy of it.

## The code

For a token whose raw bytes are b_0 … b_(L−1), L ≤ 32:

- x[b_p · 32 + p] = 1/√L for p < L, and 0 in the other 8,192 − L cells;
- z = (x − mean(x)) / (std(x, unbiased) + 1e-6).

So z has two values, `high[L]` on the L lit cells and `low[L]` everywhere else. The projection is applied as
(high − low) · Σ W[:, b_p·32 + p] + low · Σ W, without building the 8,192-long code. That is mathematically the same as
W · z.

## Numerics and training settings

| Item | Rule |
|---|---|
| Mode | Dynamic: the code is computed from the byte table at every step; no V × 8,192 table is stored |
| Embedding arithmetic | fp32 inside the KE2 class (`projection.weight.float()`); the rest of the model follows the run's precision |
| Storing codes in bf16 | Allowed: it moves decode margins by at most 6.2e-8 (`decision_input.md`, section 3) |
| Scoring codes (evaluation decoder) | fp32 or better; never rank bf16-rounded scores (`decision_input.md`, section 3) |
| Projection init | normal(0, 1/√8192) |
| Optimizer group | AdamW with `optim.lr`, with the output head and norm gains; Muon is only for the 2-D block matrices (`HARNESS_WEEK2.md`) |

## Evidence

| Check | Result | Where |
|---|---|---|
| Table integrity (`Artifacts`: format, dtypes, shape, lengths, content hash, every row against `tokenizer.json`, BOS/PAD) | passes on the p1536 table and the released tokenizer (`verify_release.py` PASS), 16 Nov | `teams/05-architecture/harness/week2/artifacts.py` |
| Team 5 class against our float64 codec, committed table, all 131,072 ids | passes | #471, `teams/05-architecture/tests/test_week2_ke2_g4_codec.py` |
| Team 5 and Team 6 classes against our float64 codec on the p1536 table, all 131,072 ids, outputs and gradients | within 1.6e-7 | #499, `tests/test_every_id.py`, `results/every_id/` |
| Code → id round trip on the p1536 table, fp32 and bf16 | exact, 0 ties | #499 |
| Dry run 1: `exp2_muon` at T2, seed 1234, p1536, 1,221 steps | COMPLETED, no NaN or inf, val/bpb 1.5159 | #475, TSAI run, 16 Nov |

## How to check

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
3. Superseded 21 Nov (TSAI; corrected in #702): the capstone output head is the KE2/KAS head, untied; see `gate3.md`,
   handoff section.
   The 16 Nov text follows. A KE2 output head is not chosen. The cosine decoder (`src/decode_ref.py`) is an evaluation tool only, and tau is
   decided by TSAI at Gate 3.
4. Parked (lead, 17 Nov): the cosine decode of predicted vectors and the tau rerun on real vectors. With the head dense,
   the decoder is an inspection tool; risk 2 of `decision_input.md` stays open until a run's saved vectors exist.
