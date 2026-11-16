# KE2 decision input for Gate 2 (Team 04-ke2, consolidated 10 Nov and updated 14 Nov 2026; TSAI decides Sat 14 Nov)

Decisions requested:
1. Byte table: the raw byte table, not `decode([id])` text (section 1).
2. P = 32, D = 8,192, supported by the frozen C3-s0 tokenizer; recheck any newly accepted candidate (section 2).
3. Decoder contract for Teams 5 and 6: cosine over the raw table, fp32 scores, margin and ties reported; tau = 0.3,
   provisional until re-checked on Team 5's predicted vectors (section 3).
4. Whether to add one scalar per token for a frequency prior (risk 4) is a lab call, not Team 4's.

The measured candidate numbers below are read from results files in this tree. Upstream PR #349 consolidated the
week-2 package; the 12 Nov follow-up adds C1-s0, C2-s0, and frozen C3-s0 reports. Other sources are named where used:
TSAI's week-1 experiment files and decision notes (risks 3 and 4), Team 3's 13 Nov reply and PR #407 (responses
A to C), and the local before/after verifier run described in response C. Paths are relative to `teams/04-ke2/`
unless stated otherwise.

| Source | What it adds | Files cited below |
|---|---|---|
| theschoolofai/era-v5-lab #268 | GPU decode determinism, every id, batch 1 / 7 / 4,096 | `determinism_gpu.md`, `results/decode_gpu/` |
| swatibansal/era-v5-lab #2 | Team 3 candidate tables: v0, v0.1, v1-c1, C1, C2, C3 | `output_shape.md`, `results/tokenizer_candidates/` |
| swatibansal/era-v5-lab #3 | Theorem 2 (structural decode) and Theorem 3 (nearest-code cosine) | `proof.md` sections 5 and 6, `results/decode_checks.json` |
| swatibansal/era-v5-lab #4 | exact minimum decode margin per script class, fp64 / fp32 / bf16 | `min_margin.md`, `results/min_margin/` |
| swatibansal/era-v5-lab #5 | tau sweep (synthetic vectors); CPU counterpart of the GPU determinism run | `min_margin.md` "Acceptance threshold", `results/min_margin/tau_*`; `determinism_gpu.md` section 7, `results/decode_cpu/` |
| `theschoolofai/era-v5-lab` #372 (follow-up to merged #349) | Team 3 C1-s0, C2-s0, and frozen C3-s0 candidate tables | `output_shape.md`, `results/tokenizer_candidates/sample_v0/` |

The proof, margin and CPU/GPU determinism runs use the HF baseline tokenizer BrahmicTokenizer-131K (sha256
`01d968a7…739fff`). Team 3 candidates are measured separately by the revalidation script behind sections 1 and 2.

## 1. Byte table type: raw bytes

Use the raw byte table (exact token bytes from the inverted ByteLevel alphabet), not `decode([id])` text.
On all nine measured candidates the raw table has 131,072 unique rows and 0 collisions. The decode table has 1,141
(v0, v0.1), 1,098 (v1-c1), 1,095 (C1), 1,096 (C2, C3), 1,094 (C1-s0) and 1,095 (C2-s0, C3-s0) excess tokens, every one of
them caused by partial-UTF-8 fragments that `decode([id])` collapses (`results/tokenizer_candidates/summary.json`,
`collision_groups.csv`, and the corresponding files under `results/tokenizer_candidates/sample_v0/`). No
whole-token and no special-token collision exists. Theorem 1 says the codec adds none (`proof.md` section 3).

## 2. P = 32

Longest token is 32 bytes on v0, v0.1, v1-c1, C1, C2, C3, C1-s0, C2-s0 and C3-s0; nothing is cut at P = 32 and there are 0
raw collisions (`results/tokenizer_candidates/summary.json` and `sample_v0/summary.json`). P = 64 doubles D without
improving the 32-byte fit or raw collision count (`output_shape.md`). D = 8,192. Team 3 confirmed that the older v2
corpus60 build (`0862f6…`) was replaced by frozen C3-s0 and needs no check because nothing trains on it. A token
over 32 bytes in a newly accepted candidate would reopen P. Re-check with `python src/revalidate_tokenizer_candidates.py`
when Team 3 announces a new candidate and sends its SHA-256. The
loader verifies the file against the registry hash or an explicit `NAME@SHA256=PATH` identity supplied on the command
line.

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
| 1 | TSAI | closed with caveats | CUDA determinism: PR #268, section 4. CPU repeats now match the CUDA token-ID hash; CUDA evidence still covers one GPU class and batches up to 4,096. |
| 2 | Team 5 -> Team 4 | open | No Team 5 predicted-vector artifact is present in this checkout. tau = 0.3 is proposed from synthetic error models only (section 3) and must be re-checked on Team 5's vectors with `tau_sweep.py --vectors`; the margin, not tau, is what detects a near-code wrong answer. |
| 3 | TSAI | open | E4 to E8 remain single-seed evidence. The four 11 Nov GPU re-runs use seed 0 and check reproducibility against TSAI's reported values; they do not measure seed-to-seed variation. Multi-seed results are still needed. |
| 4 | Lab decision | open | Unit-norm codes cannot express a per-token frequency prior; the fix is one scalar per token, V extra parameters. |
| 5 | Team 4 with Team 3 | closed for frozen C3-s0 | v0, v0.1, v1-c1, C1 to C3, and sample-v0 C1-s0 to frozen C3-s0 are measured: longest token 32 bytes, 0 raw collisions. Team 3 replaced the older v2 corpus60 build with C3-s0; check any newly accepted candidate after its SHA-256 is announced (response A). |
| 6 | Team 4 with Team 3 | role mapping closed; proof integration pending | Merged PR #407 supplies the HF configuration files. With the frozen C3-s0 tokenizer, `AutoTokenizer` resolves eos to `<|endoftext|>` (id 130822); id 36 is still a special token but has no model role. The separate proof-check run against this configuration remains pending (response B). |
| 7 | Team 5 | partially closed | Margin floor and precision rules are proven and measured (section 3). The cosine-decoder and margin-reporting requirements remain open; this checkout has no evidence that the downstream predicted-vector decode path implements them. |
| 8 | Team 3 verifier | fix proposed upstream | `verify_kronecker_constraints_unified.py` still displays incorrect normal/special counts in its released version. [BrahmicTokenizer-131K PR #1](https://github.com/theschoolofai/BrahmicTokenizer-131K/pull/1) proposes a fix; use `added_tokens.special` counts until it is merged and rechecked (response C). |

Team 3 responses received 13 Nov (risks 5, 6 and 8):

A. **Closed: older v2 build.** Team 3 confirmed that v2 (`0862f6…`) was its 31 Oct corpus60 build of C3, superseded
by C3-s0 from PR #195. Nothing trains on v2, so it needs no separate table check. No model trained on v1-c1; Team 3
also withdrew the earlier ID-reuse and bits-per-byte requests in `train/v2_spec.md`. If a new pruned-o200k candidate
is accepted, Team 3 will send its SHA-256 before validation.

B. **Frozen C3-s0 roles aligned with merged PR #407.** Team 3 confirmed that `added_tokens` entries with
`special: true` in `tokenizer.json` are the source of truth. The frozen C3-s0 tokenizer has SHA-256
`15468e66…2ddc3`. The merged `release/special_tokens_map.json` and `release/tokenizer_config.json` from PR #407
were placed beside the local C3-s0 file. Their role strings resolve to bos 130725, eos `<|endoftext|>` 130822,
pad 130726 and unk 130727, all with `special: true`. `AutoTokenizer.from_pretrained` on that folder reports eos
130822. ID 36 `<|end_of_text|>` remains a distinct special token with no bos/eos/pad/unk role. The older synthesized
baseline map named id 36 as eos; it must not be used as Team 3's role mapping. The committed
`results/inspect_BrahmicTokenizer-131K.json` records that historical baseline map and has not been regenerated
for frozen C3-s0. A separate proof-check run against the new configuration is still pending.

C. **Verifier display fix proposed upstream.** Team 3 confirmed that `verify_kronecker_constraints_unified.py` is in
`theschoolofai/BrahmicTokenizer-131K` and PR #195 did not change it. Its earlier display of `131,072 normal tokens`
and `0 special tokens` for v0/v0.1 remains unfixed upstream. [BrahmicTokenizer-131K PR #1](https://github.com/theschoolofai/BrahmicTokenizer-131K/pull/1)
reads the special IDs from `tokenizer.json` in both local-JSON paths. Local before/after runs on v0, v0.1 and frozen
C3-s0 changed only the displayed split from 131,072 / 0 to 130,716 normal / 356 special; maximum byte length 32,
zero over-limit tokens, zero cross-script tokens and the PASS verdict remained the same. The PR is open as of 13 Nov.
Use `added_tokens.special` as provenance until the fix is merged and the released verifier is rerun.
