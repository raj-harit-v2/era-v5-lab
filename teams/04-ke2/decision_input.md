# KE2 decision input for Gate 2 (Team 04-ke2, consolidated 10 Nov 2026; input due Thu 12 Nov; TSAI decides Sat 14 Nov)

Decisions requested:
1. Byte table: the raw byte table, not `decode([id])` text (section 1).
2. P = 32, D = 8,192; provisional until Team 3's C1-s0, C2-s0, C3-s0 and v2 are measured (section 2, ask A).
3. Decoder contract for Teams 5 and 6: cosine over the raw table, fp32 scores, margin and ties reported; tau = 0.3,
   provisional until re-checked on Team 5's predicted vectors (section 3).
4. Whether to add one scalar per token for a frequency prior (risk 4) is a lab call, not Team 4's.

Every number below is read from a committed results file in this tree (`ke2-week2-stitch` plus swatibansal/era-v5-lab
#5), with three exceptions that cite documents instead: risks 3 and 4 (TSAI's week-1 experiment files and decision
notes) and the Team 3 statements in asks B and C (`teams/03-tokenizer/v0/special_slots.md`, `output_shape.md`).
Paths are relative to `teams/04-ke2/`.

| Source | What it adds | Files cited below |
|---|---|---|
| theschoolofai/era-v5-lab #268 | GPU decode determinism, every id, batch 1 / 7 / 4,096 | `determinism_gpu.md`, `results/decode_gpu/` |
| swatibansal/era-v5-lab #2 | Team 3 candidate tables: v0, v0.1, v1-c1, C1, C2, C3 | `output_shape.md`, `results/tokenizer_candidates/` |
| swatibansal/era-v5-lab #3 | Theorem 2 (structural decode) and Theorem 3 (nearest-code cosine) | `proof.md` sections 5 and 6, `results/decode_checks.json` |
| swatibansal/era-v5-lab #4 | exact minimum decode margin per script class, fp64 / fp32 / bf16 | `min_margin.md`, `results/min_margin/` |
| swatibansal/era-v5-lab #5 | tau sweep (synthetic vectors); CPU counterpart of the GPU determinism run | `min_margin.md` "Acceptance threshold", `results/min_margin/tau_*`; `determinism_gpu.md` section 7, `results/decode_cpu/` |

All committed Team 4 runs use the HF baseline tokenizer BrahmicTokenizer-131K (sha256 `01d968a7…739fff`); Team 3's
candidates enter only through the revalidation script behind sections 1 and 2.

## 1. Byte table type: raw bytes

Use the raw byte table (exact token bytes from the inverted ByteLevel alphabet), not `decode([id])` text.
On all six measured candidates the raw table has 131,072 unique rows and 0 collisions; the decode table has
1,141 (v0, v0.1), 1,098 (v1-c1), 1,095 (C1) and 1,096 (C2, C3) excess tokens, every one of them a partial-UTF-8
fragment that `decode([id])` turns into U+FFFD (`results/tokenizer_candidates/collision_groups.csv`,
`summary.json`). No whole-token and no special-token collision exists. Theorem 1 says the codec adds none
(`proof.md` section 3).

## 2. P = 32

Longest token is 32 bytes on v0, v0.1, v1-c1, C1, C2 and C3; nothing is cut at P = 32; 0 raw collisions
(`results/tokenizer_candidates/summary.json`). P = 64 doubles D for no gain (`output_shape.md`). D = 8,192.
Not measured: Team 3's sample-v0 retrains C1-s0, C2-s0, C3-s0 (`teams/03-tokenizer/COMPARE.md`, section "C1, C2, C3
retrained with the week-2 tokenizer sample v0", now lists them under the names C1 to C3) and the v2 file (sha `0862f6…`). A token over 32 bytes in any of them would reopen P. Re-check with
`python src/revalidate_tokenizer_candidates.py` once Team 3 publishes them; the script refuses a file whose sha256
is not in its registry.

## 3. Decode margins, precision, and what Team 5's decoder must do

The margin floor and precision figures are fork #4's; the tau proposal is from `src/margins/tau_sweep.py` on
synthetic vectors (`results/min_margin/tau_rates_P32.md`, `tau_summary_P32.json`; `min_margin.md`, section
"Acceptance threshold"); see risk 2.

Margin floor. The margin of a token is its best cosine minus its second-best over all 131,072 raw-table codes.
Computed exhaustively in float64 from the two-valued code structure (`results/min_margin/summary_P32.json`), the
smallest margin anywhere is 0.015809, between the 32-space token (id 50346) and the 31-space token (id 83647),
in Code/Structure. Theorem 3 proves this is the worst possible pair shape at P = 32 and that the pair is unique in
the vocabulary (`proof.md` section 6). Other class minima: Latin 0.028234, Devanagari 0.031813, the other Indic
scripts 0.037 to 0.056, Digits 0.111 (`results/min_margin/min_margin_P32.md`). For most Indic scripts the closest
rival of a word is the same word minus its last byte, a partial-UTF-8 fragment.

Sufficient condition. Nearest-code decoding returns the true token for any vector whose cosine to the true code
exceeds 0.99604 at P = 32 (0.99605 at P = 64); the bound is tight (`proof.md` section 6 (d),
`results/decode_checks.json`).

Precision (`results/min_margin/summary_P32.json`, `min_margin.md`; GPU row from `results/decode_gpu/raw_P32.json`).
Storing codes in reduced precision is harmless; scoring in reduced precision is what moves margins. The scoring rows
cover the 110 lowest-margin tokens (the 3 lowest per class), the storage rows every token.

| What is reduced | Margin shift | Tightest margin (floor 0.015809) |
|---|---|---|
| storage: codes in fp32 / bf16, exact scoring | at most 6.7e-16 / 6.2e-8 | unchanged |
| scoring in fp32 | -5.3e-5 to +2.6e-4 | 0.015795 |
| bf16 inputs, fp32 accumulation | -2.6e-4 to +9.2e-5 | 0.015795 |
| bf16-rounded scores | -5.3e-3 to +3.5e-3 | 0.012127 (-23%) |
| GPU fp32 vs float64, batch 4,096 | worst margin error 4.1e-4 | 39 times below the floor; 82% of the 5e-4 tolerance |

Tau sweep and proposal. 10,000 query tokens (seed 0) over the raw table at P = 32, tau in {0, 0.3, 0.5, 0.7, 0.9},
with three stand-ins for predicted vectors, since Team 5 has none: isotropic noise at target cosine 0.95 down to 0.3,
pure Gaussian garbage with no true token, and rival mixtures (1 - a) z_true + a z_rival with the token's own
runner-up at a = 0.3, 0.45, 0.55, 0.7. Proposed tau = 0.3 by the script's rule: the smallest grid value that accepts at
most 1% of garbage and keeps at least 99% of correct decodes under noise at target cosine 0.7 or above. The safe band
is wide: garbage never exceeds best cosine 0.065 and correct decodes at target cosine 0.5 never fall below 0.472, so
every tau between those two gives the same table; 0.3 is the grid point inside the band, not a tuned value. tau = 0.5
already drops half the queries at cosine 0.5 and tau = 0.7 half of those at 0.7. Tau is a garbage filter only: every rival mixture keeps
its best cosine above 0.77 and is accepted at every tau in the grid, and above a = 0.5 the accepted answer is wrong
(wrong-accept 100% at a = 0.55 and 0.7). The margin is what detects that case. The sweep's own margin pass
reproduces the floor and class minima above (`results/min_margin/tau_margin_pass_P32.md`). It re-runs on real vectors
with `--vectors team5.npz` (`vectors` (N, D), `true_ids` (N,), -1 where unknown).

Requirements for Team 5 (and Team 6 for a fast decoder):
1. Decode by cosine over all 131,072 raw-table codes, each divided by its own norm (the norms differ by length).
2. Keep scores and accumulators in fp32 or better; never rank bf16-rounded scores or raw bf16 dot products.
3. Report the margin (best minus second-best) and ties with every decode. Ties go to the lowest id silently in both
   reference implementations, so a tie is invisible unless reported.
4. Use the cosine decoder, not the structural decoder of Theorem 2, for predicted vectors (section 5).

## 4. Determinism

GPU (closes risk 1). fp32, TF32 off, `torch.use_deterministic_algorithms(True)`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`,
three fresh processes per batch size: the id hashes of all nine runs match each other and match the CPU float64
reference computed by `decode_ref.decode` in a separate process, elementwise for all 131,072 ids; ties 0
(`results/decode_gpu/raw_P32.json`, `raw_P32_sha256.txt`). The score hashes repeat within a batch size and differ
across batch sizes (cuBLAS picks a kernel per shape); the ids are the portable artefact. fp32 score error against
float64: 2.2e-5, 7.5e-5 and 2.35e-4 at batch 1, 7 and 4,096; `NVIDIA_TF32_OVERRIDE=0` gives identical TF32-off numbers
(`results/decode_gpu/tf32_override_0/`). Caveats: one consumer laptop GPU (compute capability 8.9, Windows, torch
2.14.1+cu130, CUDA 13.0); the decoder is a dense fp32 GEMM in `src/determinism/decode_gpu.py`, checked only against
the float64 `decode_ref.py`; the worst margin error, 4.1e-4 at batch 4,096, is 82% of the 5e-4 tolerance, and larger batches were not run.

CPU (`src/determinism/decode_batches.py`, `results/decode_cpu/raw_P32.json`; `determinism_gpu.md` section 7). The GPU
protocol repeated on CPU (macOS arm64, torch 2.15.0): the same batch sizes 1, 7 and 4,096, three fresh processes each,
fp32 with TF32 off, all 131,072 ids, scored by the structured cosine scorer `ke2.scoring`; the deterministic-algorithms
mode and the cuBLAS workspace setting are CUDA-only and not set. Hashes agree within every batch size, every run's
ids equal the float64 reference id for id, and in the GPU format the CPU id hash is `31c8d0e0…`, the value of all nine
GPU runs. Two decoders (dense fp32 GEMM on CUDA, structured cosine on CPU), two devices and three batch shapes give the
same 131,072 ids.

Target for Team 6: id hash `31c8d0e0ac50cff5c8021f88a2b608de2298fdbf216c620a40e83d2adbe26f9a` (raw table, P = 32,
format `ke2-decode-gpu-ids-v1`, the identity map); tolerance 5e-4 on scores and margins against `decode_ref.py`.

## 5. What is proven (proof.md sections 5 and 6)

Theorem 2. A vocabulary-free structural decoder with cut-off 8 recovers every token from its clean code in exact
arithmetic, fp32 and bf16 (131,072 / 131,072 at P = 32 and 64), and under any per-entry error below 7.966
(`results/decode_checks.json`). This is a sup-norm guarantee: a rival mixture of weight 0.3 already lights a short
rival's extra cell while the cosine to the true code is still 0.988, so Theorem 2 does not cover structured noise.
Predicted vectors must use the cosine decoder.

Theorem 3. Closed form for the cosine between any two codes from their lengths and shared byte positions, matching
the codec to 1.7e-15 on 10,010 real pairs; cos = 1 iff the strings are equal; the margin floor and the 0.99604
guarantee of section 3 follow.

## 6. Open risks after the package

| # | owner | status | risk |
|---|---|---|---|
| 1 | TSAI | closed with caveats | CUDA determinism: PR #268, section 4. Caveats: one GPU class, dense decoder, batch <= 4,096. |
| 2 | Team 5 -> Team 4 | open | No predicted vectors yet. tau = 0.3 is proposed from synthetic error models only (section 3) and must be re-checked on Team 5's vectors with `tau_sweep.py --vectors`; the margin, not tau, is what detects a near-code wrong answer. |
| 3 | TSAI | open | E4 to E8 are single-seed in TSAI's files. Multi-seed still needed. |
| 4 | Lab decision | open | Unit-norm codes cannot express a per-token frequency prior; the fix is one scalar per token, V extra parameters. |
| 5 | Team 4 with Team 3 | partially closed | v0, v0.1, v1-c1, C1 to C3 measured: longest token 32 bytes, 0 raw collisions. Team 3's sample-v0 retrains C1-s0, C2-s0, C3-s0 and the v2 file are unmeasured (ask A). |
| 6 | Team 4 with Team 3 | open | The special-token designation is unconfirmed, and the one file we have disagrees with Team 3 on the end-of-text id (ask B). No committed number depends on it; the upstream-compatibility check and the tokenizer test gate do. |
| 7 | Team 5 | partially closed | Margin floor and precision rules are now proven and measured (section 3). The cosine-decoder requirement and the margin-reporting requirement are stated here, not yet in Team 5's decoder. |
| 8 | Team 4 with Team 3 | new | Team 3's `verify_kronecker_constraints_unified.py` reports 131,072 normal and 0 special tokens; the correct split is 130,716 and 356 (`output_shape.md`). Its length and cross-script gates still pass (ask C). |

Asks to Team 3 (owner of risks 5, 6 and 8 on their side: @sohamniyogi, lead @rjvim):

A. **Tokenizer files for the unmeasured candidates.** Each is pinned by sha256 in its manifest under
`teams/03-tokenizer/train/`: C1-s0 `36acf126…c82a2`, C2-s0 `b0d44576…8488a`, C3-s0 `15468e66…2ddc3` (these three are
already in the registry of `src/revalidate_tokenizer_candidates.py`), and v2 `0862f683…5bc47` (not in the registry;
pin it on the command line as `--candidate v2@<sha256>=<path>`). None of the four `tokenizer.json` files is committed
or published, and rebuilding them needs the corpus60 and sample-v0 inputs. A token over 32 bytes in any of them
reopens P = 32 (section 2); a collision in the raw table reopens section 1. One day of work once the files exist.

B. **Special-token designation and the end-of-text id.** Our runs read the 356 special ids from `added_tokens`
(`special: true`) inside `tokenizer.json`; that is what every committed table, margin and determinism result uses.
The only `special_tokens_map.json` and `tokenizer_config.json` on our side were synthesised on 31 Oct from the
baseline's added tokens, because the HF repo is gated; they name three tokens, bos `<|begin_of_text|>`, eos
`<|end_of_text|>` (id 36) and pad `<|pad|>`. Team 3's `v0/special_slots.md` (lab main `9ab4f3d`) says G10's
end-of-document marker is `<|endoftext|>` at id 130822 and that id 36 is a different token that stays as it is. Nothing
in the lab repository defines which of the two the model will treat as eos, and no candidate ships either file. What it
touches on our side: the upstream-compatibility check `src/proofs/proof_checks.py` takes the literal-text path only for
ids named in the map (3 today, against 356 specials; its `fed_equals_raw` of 129,766 was computed with the synthesised
map), and `tests/conftest.py` enables the 59 tokenizer tests only when the map is present, so no Team 3 candidate can
run the full suite as shipped. Asks: (1) publish `special_tokens_map.json` and `tokenizer_config.json` with every
candidate, or state that `added_tokens` in `tokenizer.json` is the single source of truth; (2) confirm bos, eos, pad
and unk by id, in particular 36 versus 130822; (3) say whether all 356 specials are `additional_special_tokens` or only
the named ones. Until then the special-token policy sentence in `proof.md` section 4 stays open.

C. **Verifier count bug.** `verify_kronecker_constraints_unified.py` prints `131,072 normal tokens` and `0 special
tokens` for v0 and v0.1; the tokenizer has 130,716 and 356. The maximum-length and cross-script checks are unaffected;
the two printed counts should not be used as provenance until fixed.
