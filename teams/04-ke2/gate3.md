# KE2 evidence for Gate 3 (Team 04-ke2, week 3; status 18 Nov 2026; TSAI decides Sat 21 Nov)

Gate 3 asks Team 4 for two things (week 3 work order, section 7):

1. Dry run 1 runs with the chosen path.
2. The correctness tests pass on every token ID.

This file collects the evidence of the five week-3 tasks in one place. Each task is marked **done** (merged on
main), **measured** (numbers exist, the PR is open) or **open** (no evidence yet). It is updated as the open PRs
merge. Paths are relative to `teams/04-ke2/` unless stated otherwise.

| # | Task | PR | State | Evidence |
|---|---|---|---|---|
| 1 | The chosen path in the trainer, with Team 5 | #515 (open) | measured | dry run 1 COMPLETED on p1536 with the KE2 input path (#475); `trainer_adapter.md` |
| 2 | bf16 code table for the frozen tokenizer, 0 special-token collisions | team fork #6 (open) | measured | `results/bf16/bf16_collisions_P32.md`: 0 special-token collisions, 0 duplicate rows |
| 3 | Correctness tests on every token ID, with Team 6 | #499 (merged) | **done** | `tests/test_every_id.py`, `results/every_id/every_id_P32.md`: 20 of 20 pass |
| 4 | Encode and decode time per step in Team 6's harness | #588, #624 (merged) | **open** | `results/timing/README.md`: CPU and MPS exploratory runs and a CPU smoke of the isolated `model.tok(x)` benchmark; the CUDA run and Team 6's in-step `embed.ke` region are pending |
| 5 | Export note for Team 12: the input path folded into a normal table | this PR | measured | `output_shape.md` (export section), `results/fold/fold_check_P32.md` |

Gate 3 item 1 is met by task 1 and item 2 by task 3. Tasks 2, 4 and 5 support them.

## The chosen path

| Item | Value | Source |
|---|---|---|
| Tokenizer | p1536-s0, `tokenizer.json` sha256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`, V = 131,072, 356 special IDs | TSAI Gate 3 notice, 16 Nov; Team 3 #414, #504 |
| Byte table | raw table, P = 32, D = 8,192; content sha256 `21072027b19ef6f05d57ead7a2fc9fb4c52129e491186bf38d0ba079e8d5168a`; 131,072 distinct rows, 0 truncated, 0 empty | `results/tables/p1536-s0/`; #498 |
| Input embedding | fixed Kronecker code, then the learned `Linear(8192, d_model, bias=False)`; fp32 inside the KE2 class | Gate 2; `trainer_adapter.md` |
| Output head | dense untied `Linear(d_model, 131072)`; no KE2 output head | TSAI, 15 Nov |
| Special roles | eos 130822 `<\|endoftext\|>`, bos 130725, pad 130726, unk 130727; ID 36 has no role | Team 3 #407; `teams/03-tokenizer/release/SPECIAL_TOKENS.md` |

## 1. Trainer agreement (task 1, #515)

**Done:**
- Team 5 keeps its own `KE2` class (`teams/05-architecture/harness/week2/model.py`) as the trainer's input path.
  #471 checks it against our float64 codec on the committed table.
- #472 accepts `embedding: ke2`, and `ke1` stays as the older name for the same path.
- `trainer_adapter.md` is the contract between the two teams. It fixes the path, the tokenizer, the table hashes,
  the numerics and the optimizer group.

**Measured:**
- Dry run 1 (#475, `exp2_muon` at T2, seed 1234, TSAI run): 1,221 steps, COMPLETED, no NaN or inf, val/bpb
  1.5159, on p1536 with the KE2 input path.
- Team 5's `check_week2.py` with `--tokenizer-release frozen-p1536` passes every check on our committed table,
  including every row against the released tokenizer (`verify_release.py` PASS).
- Team 5's suite: 135 passed after merging current main (the 2 Muon failures were fixed on main by #521).
- The full-run manifest of dry run 1 (#620,
  `teams/05-architecture/jobs/evidence/2026-11-15-dryrun1-full/manifest.json`) records the frozen tokenizer
  `e6b93a93…a64b` and the table content sha256 `21072027…168a`, so the run used the chosen table. It names the
  path `embedding: ke1`, the older name for the same KE2 input path (#472).

**Open:**
- p1536 support in the trainer on main lands with #515. The default stays v0, so running jobs are unchanged.
- Points 4 and 5 of the task (the cosine decode of predicted vectors and the tau rerun) are parked by the lead
  (17 Nov). See risk 2 below.

## 2. bf16 codes and special-token collisions (task 2, team fork #6)

**Measured** (`results/bf16/bf16_collisions_P32.md`, p1536, P = 32): **0 special-token collisions** and 0 duplicate
rows among the 131,072 bf16 rows of the `(131,072, 8,192)` code matrix. Each of the three ways two codes could
meet in bf16 gives 0:
- the same bytes and length: 131,072 unique raw rows;
- `high[L] == low[L]` in bf16 for some length;
- two lengths with the same bf16 `(high, low)`: 32 distinct pairs for 32 lengths.

None of the 356 special-token rows equals another row. IDs 36 and 130822 are both special and differ. The 2 GB matrix
is not committed (TSAI, 14 Nov). The PR commits the compact codes (sha256 `0bc1aa3c…565a26`), the matrix hash
`0f96a38a…dfa78` and a verifier.

**Open:** the PR is in the team fork. It needs a full test run with the p1536 tokenizer, and then a PR to the lab repo.

## 3. Correctness tests on every token ID (task 3, #499, merged)

**Done** (`results/every_id/every_id_P32.md`): `tests/test_every_id.py` passed 20 of 20, with 0 skipped, in 282 s on
one GPU. Team 5's `test_week2_ke2_g4_codec.py` passed 5 of 5 on the same table.

| Check, all 131,072 IDs of the p1536 table | Result |
|---|---|
| Code → ID, structural decode, fp32 and bf16 | 0 wrong |
| Code → ID, cosine decode, fp32 and bf16 | 0 wrong, 0 ties, smallest margin 0.0158 |
| Team 5 `KE2` vs float64 codec (outputs, gradients) | worst 7.6e-8 / 4.7e-7 (tolerance 1e-5 / 5e-5) |
| Team 6 `KE2Embedding` vs float64 codec | worst 7.8e-8 / 1.6e-7 |
| bf16 code bits vs the reference | 0 rows differ |

On the committed baseline table the same suite reproduces week 2's ID hash `31c8d0e0…`. TSAI ruled on 15 Nov that the
tests do not have to run inside dry run 1, and that a merged PR with the full run log is enough.

## 4. Timing (task 4)

**Open** (as of 18 Nov). Task 4 asks for:
- milliseconds per step for encode and decode, median with p10 and p90;
- the GPU name and the commit;
- measured in Team 6's harness.

Encode is already timed there as the `embed.ke` region. Decode is not part of a training step, because the head is
dense. It is a separate region that runs only behind a flag.

**Merged so far** (`results/timing/README.md`):
- #588: `src/timing/bench_public_ke.py` and exploratory CPU and MPS runs on the p1536 table
  (`public_ke_p1536_{cpu,mps}.json`). They time the embedding, the output head, argmax, a full step and the CPU
  reference encode and decode. They are kept as history and are not the task-4 number.
- #624: the benchmark now times only `model.tok(x)` (eval mode, no gradients) with Team 6's `StepTimer`. It checks the
  table content sha256 `21072027…168a`, records the GPU name and commit, and refuses a dirty checkout on CUDA. A CPU
  smoke of 3 steps completed.

**Still to come:**
- The approved CUDA runs from the merged main commit: a 3-step smoke, then 100 steps.
- Team 6's in-step `embed.ke` region on p1536. Team 6's table loader still selects the earlier table, so this run waits
  for p1536 support in the Team 6 harness. The isolated `model.tok(x)` time does not replace it.

Two more related measurements exist, but neither is the task-4 number:
- Team 6's dry run 1 profiling jobs (#486, #492);
- the remark in #515 that Team 5's KE2 gathers a `tokens × 32 × d_model` tensor. That is large at full width, and it
  is a performance remark, not a blocker.

## 5. Export to a normal table (task 5, this PR)

**Measured** (`results/fold/fold_check_P32.md`, d_model 512, random projection at Team 5's init):
- A lookup in the folded `V × d_model` table equals Team 5's `KE2(ids)` bit for bit on 16,384 sampled IDs: 0 rows
  differ.
- On all 131,072 IDs, the fp32 fold is within 3.8e-7 (relative) of the float64 closed form.
- On all 131,072 IDs, bf16 storage stays within bf16's unit roundoff (3.87e-3 against 2⁻⁸ = 3.91e-3).
- All 356 special rows are finite and non-zero.

The export section of `output_shape.md` gives Team 12 the checkpoint key names, the closed form, the storage advice
and the size after the fold. G12's `scripts/export_hf.py` already folds this way.

**Open:** the check on a trained checkpoint. It runs inside G12's export job (#508) with
`fold_check.py --checkpoint`, because dry-run checkpoints stay on TSAI's machines.

## 6. Open risks from `decision_input.md`, rechecked 17 Nov

| # | Gate 2 status | Now | Why |
|---|---|---|---|
| 1 | closed with caveats | unchanged | CUDA determinism. #499 adds every-ID fp32 and bf16 round trips on one more GPU run; the caveats (one GPU class, batches up to 4,096) stand |
| 2 | open | **open** | No predicted KE2 code vectors exist. Team 5's `save_hidden_vectors.py` (#473, #501) saves the `n_embd`-wide hidden states that feed the dense head, not vectors in the 8,192-wide code space, and states that it applies no projection into code space. With no KE2 output head there is nothing for `tau_sweep.py --vectors` to measure. tau = 0.3 stays a proposal from synthetic vectors, and TSAI decides tau at Gate 3. Parked by the lead, 17 Nov |
| 3 | open | unchanged | E4 to E8 are still single-seed |
| 4 | open (lab decision) | unchanged | per-token frequency prior. It matters only for a KE2 output head, and none is chosen |
| 5 | closed for C3-s0 | **closed for p1536** | longest token 32 bytes, 0 raw collisions, 0 truncated (#498, `decision_input.md` section 7) |
| 6 | role mapping closed; proof integration pending | role mapping closed; proof integration pending | p1536 keeps the C3-s0 special IDs and roles. The proof checks were not rerun on p1536; #499's every-ID tests cover the decode properties on it |
| 7 | partially closed | partially closed | the cosine-decoder requirements apply only when a decoder runs on predicted vectors. The decoder is an inspection tool while the head is dense |
| 8 | fix proposed upstream | unchanged | Team 3 verifier display counts; use `added_tokens.special` |

## What Gate 3 can quote

- Dry run 1 trained 1,221 steps on the frozen p1536 tokenizer with the KE2 input path and the dense untied head,
  with no NaN or inf (val/bpb 1.5159; #475).
- Every token ID is checked: code → ID is exact in fp32 and bf16 with 0 ties. The trainer's KE2 and Team 6's KE2
  match the float64 codec within 1.6e-7 on all 131,072 IDs (#499).
- 0 special-token collisions in the bf16 code table (task 2).
- The KE2 input folds into a normal embedding table for serving, reproducing the trainer bit for bit on 16,384 sampled
  IDs and matching float64 on all 131,072 (task 5).
- Dry run 1's manifest records the chosen table, content sha256 `21072027…168a` (#620).
- Still open: the CUDA encode and decode timing (task 4; the benchmark is merged in #588 and #624), and risk 2.
