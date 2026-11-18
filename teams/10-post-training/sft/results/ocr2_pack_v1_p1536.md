> Scope: rebuild under the existing exclusion policy. The 14 source spot checks remain pending and those keys stay excluded. The full #391 mix and storage delivery are not complete.

# OCR-2 pack v1, rebuilt with p1536 (G10, 16-17 Nov 2026)

Instruction (instructor to G10, 16 Nov): "rebuild SFT data v1 with p1536. Rerun the render and pack steps and re-check
the effort tiers. Keep the C3 pack as a record." TSAI froze p1536 on 15 Nov (Gate 3 notice: sha256 `e6b93a93…a64b`,
same 356 special tokens and ids as C3, eos 130822, vocabulary 131,072). Machine-readable record:
`ocr2_pack_v1_p1536_manifest.json` (written by the aggregator, 48 of 48 checks).
The C3 pack of 14 Nov stays as a record, unchanged: `ocr2_pack_v1_c3.md`, `ocr2_pack_v1_c3_manifest.json`
(sha256 `c15a54a1109c…`). No row text and no ids here. The pack bytes are not in Git; TSAI rebuilds and
stores them through `../../jobs/2026-11-17-ocr2-pack-v1-p1536.md`.

## What changed, and what did not

The conversion changes tokenizer. Pipeline code hashes are recorded in the manifest; the orchestrator adds tokenizer approval checks and tokenizer-qualified run IDs. Same sources at the same revisions, same 2% held-out rule, same 14 unclear TACO keys left out, same 32,768 limit, same quality rule.
`ocr2_policy.json` now approves p1536 only (C3 is listed as superseded) and `run_ocr2.py` names the tokenizer in the
run id: `admission-toke6b93a93-8e4b984ba811` (C3 build: `admission-7107d5b9dc9c`).

Which stages depend on the tokenizer (from the code, then shown on shard 0 below):

| Stage | Tokenizer? | Shard 0, p1536 vs C3 |
|---|---|---|
| join (`prepare_ocr2.py`) | no | `joined.jsonl`, sidecar, exclusions byte-identical |
| render (`convert.py`) | yes: ids, loss mask, effort tier (and so the effort line), 64k trace skip | same 10,564 ids in order; trained text identical in 10,564 rows; 1 row differs only in its effort line (4k->16k: 1); skips identical |
| decontam (`decontam_run.py`, Team 9 tools) | no (text scan), but its record pins the rendered file's sha256, so it re-runs | flagged ids identical (2,314), benchmarks identical, 0 canary, kept ids identical |
| held-out split (`pack_admission.heldout_selector`) | no (salted hash of the family key) | held-out ids identical (203) |
| pack (`pack_admission.py`) | yes: re-encodes, checks ids/masks/limit, refuses an unapproved tokenizer | train ids identical (8,047); tokens 52,369,462 → 52,380,892 |

The C3 control (same tip code, the build's policy `2399c8ba…` and C3 manifest `ded9be9e…`) reproduced the 14 Nov
build's bytes for all six files compared on shard 0 (joined, sidecar, rendered, clean, pack, held-out), so the merged
code builds the same C3 pack as commit `91ee136`.

## Funnel, C3 vs p1536 (all 70 shards)

| Count | C3 (14 Nov) | p1536 | Difference |
|---|---:|---:|---|
| `joined.raw_rows` | 1,398,166 | 1,398,166 | same |
| `joined.eligible_joined` | 542,110 | 542,110 | same |
| `rendered.converter_rejected` | 67 | 67 | same |
| `rendered.rendered` | 542,043 | 542,043 | same |
| `screened.rows_flagged` | 115,040 | 115,040 | same |
| `screened.rows_canary` | 0 | 0 | same |
| `screened.rows_kept` | 427,003 | 427,003 | same |
| `pack.train_rows` | 418,496 | 418,496 | same |
| `pack.heldout_rows` | 8,507 | 8,507 | same |
| `train.tokens` | 2,661,029,931 | 2,661,573,319 | +543,388 (+0.020%) |
| `train.shifted_assistant_targets` | 2,488,857,211 | 2,489,211,865 | +354,654 (+0.014%) |
| `heldout.tokens` | 53,317,333 | 53,330,733 | +13,400 (+0.025%) |

Longest training row: 29,829 (C3) → 29,846 (p1536); no row over 32,768.
Held-out: 8,507 rows, 317 families, identical to the C3 list by id
(`c3.heldout_ids_identical`). Unclear TACO keys: 14 keys, 176 rows in
29 shards, as in C3. Codeforces: 0 rows eligible.

## Effort tiers, re-checked on every row

Rule: convert.py pick_effort: the smallest budget in 1k/4k/16k/64k (chat-format/render.py EFFORT_BUDGETS 1024/4096/16384/65536) that holds the summed tokens of the row's trace segments (convert.TRACE: think spans, tool calls, tool results with their markers); a trace over 64k skips the row.
Method: every rendered row of all 70 shards: trace segments re-extracted from the rendered text and counted with p1536 (reproduces the row's own tier in every row) and with C3 (reproduces the C3 build's render-stage tier counts in every shard).

542,043 rendered rows checked. **35 rows change tier** (35 to a higher
tier, 0 to a lower one); 31 of them are in the training pack. Matrix
(C3 tier → p1536 tier, all rendered rows):

| C3 → p1536 | Rows |
|---|---:|
| 16k->16k | 288,981 |
| 16k->64k | 7 |
| 1k->1k | 45,238 |
| 1k->4k | 4 |
| 4k->16k | 24 |
| 4k->4k | 195,207 |
| 64k->64k | 12,582 |

Per-shard flips: `ocr2_pack_v1_p1536_effort_tiers.json` (`per_shard`). What the manifest records: the p1536 tiers in
`effort_at_render_stage` (render-stage counts, before decontam and the held-out split) and these totals in
`effort_tiers_c3_vs_p1536`. A flipped row's text differs from C3 only in its `Reasoning effort:` line.

## Pack-level row comparison on the kept shards (p1536 pack vs the C3 pack of 14 Nov)

| Shard | Train rows compared | Same id, same order | Trained text identical | Effort line only | Held-out compared / same id | OK |
|---|---:|---:|---:|---:|---|---|
| 0 | 8,047 | 8,047 | 8,047 | 1 | 203 / 203 | yes |
| 1 | 8,009 | 8,009 | 8,009 | 1 | 188 / 188 | yes |
| 2 | 7,974 | 7,974 | 7,974 | 0 | 189 / 189 | yes |
| 3 | 8,052 | 8,052 | 8,052 | 0 | 193 / 193 | yes |

## Loss masks

`check_pack_rows.py` on every train and held-out row of the shards whose p1536 pack bytes were kept (0, 1, 2, 3): 32,855 rows, 212,593,659 tokens, violations none, longest 19,366. Every other shard: `pack_admission.py` recomputes ids and masks from the text with p1536 and refuses any
difference (row outcome `passed_row_checks` for every row, 0 rejected); those bytes were deleted after the build.

## Checks (48 of 48)

- `c3.heldout_ids_identical`: pass
- `c3.heldout_list_is_the_recorded_one`: pass
- `c3.manifest_unchanged`: pass
- `c3.per_shard_flagged_identical`: pass
- `c3.per_shard_join_identical`: pass
- `c3.per_shard_kept_identical`: pass
- `c3.per_shard_records_found`: pass
- `c3.per_shard_rendered_identical`: pass
- `c3.per_shard_train_heldout_identical`: pass
- `c3.train_and_heldout_totals_identical`: pass
- `c3.unclear_taco_keys_still_out`: pass
- `config.code_on_disk_matches_run`: pass
- `config.fingerprint_set_approved`: pass
- `config.local_run_json_matches_coverage`: pass
- `config.one_config_all_shards`: pass
- `config.p1536_32768_admission_not_fixture`: pass
- `config.policy_on_disk_matches_run`: pass
- `config.source_manifest_on_disk_matches_run`: pass
- `decontam.full_set_v2`: pass
- `decontam.second_pass_zero_hits`: pass
- `decontam.zero_canary`: pass
- `effort.c3_recount_reproduces_c3_build`: pass
- `effort.every_rendered_row_rechecked`: pass
- `effort.p1536_recount_reproduces_row_tier`: pass
- `heldout.families_reselect`: pass
- `heldout.ids_unique_and_counted`: pass
- `heldout.only_approved_sources_at_pinned_revision`: pass
- `heldout.policy_rule_applied`: pass
- `inputs.download_or_local_sha256`: pass
- `pack.admitted_equals_emitted`: pass
- `pack.bound_to_this_build`: pass
- `pack.max_length_within_32768`: pass
- `pack.sha256_recorded`: pass
- `pack.training_admissible_no_blocker`: pass
- `shards.all_70_present`: pass
- `shards.complete_validated_reconciled`: pass
- `shards.full_input_rows`: pass
- `shards.modal_result_complete`: pass
- `shards.unique`: pass
- `sources.no_codeforces_row_eligible`: pass
- `sources.only_approved_train_splits`: pass
- `totals.eq1_raw`: pass
- `totals.eq2_eligible`: pass
- `totals.eq3_rendered`: pass
- `totals.eq4_kept`: pass
- `totals.eq5_split`: pass
- `totals.outcomes_sum_to_raw`: pass
- `totals.raw_1398166`: pass

## Build record and run gate

Where: shards 0-3 ran on an Apple M1 Pro Mac (8 cores, 16 GB); shards 4-69 ran on a Civo CPU instance (16 vCPU, 32 GB). The Civo pass took 2 h 34 m 50 s, initially at 18 workers and then 12 after OOM recovery. All 66 Civo shards completed with recount mismatch 0. Thirty-second samples recorded peak load 19.01 and peak disk use 64.23 GiB. The Civo instance was deleted after all records were copied and hash-verified.

`run_shards.py` invokes the pinned `run_ocr2.py` pipeline once per shard. Packs for shards 4-69 were discarded after verification; hashes, counts, private row statistics and ID lists remain. This PR is build evidence and a reproducible storage request, not delivery of those training files. See `../../jobs/evidence/2026-11-16-p1536-rebuild/validation.md`.

Per shard, wall seconds: total median 2,374, max 3,549; pipeline median
1,957; decontam screen median 1,332 (68% of the pipeline).

Matched timing (shard 0, C3 control and p1536 started 27 s apart and run side by side, one worker each, same host):

| Stage (s) | C3 | p1536 |
|---|---:|---:|
| joined | 9.3 | 3.7 |
| rendered | 174.3 | 179.1 |
| screened | 1,987.1 | 1,926.3 |
| rechecked | 47.3 | 41.2 |
| pack | 215.2 | 191.7 |
| wall | 2,453.5 | 2,357.2 |

This single matched pair does not establish a tokenizer speedup or slowdown. The decontam screen
(Team 9's pinned tools, not changed here) is most of each shard; render and pack have no hot loop to fix (batched
`encode_batch` calls since the 14 Nov build). The 14 Nov laptop run did shard 0 in 1,235 s with 4 workers on a quieter
host; the difference is confounded by host load and is not an isolated tokenizer effect. Not measured: a full 70-shard run on a quiet machine.

## Evaluation firewall (16 Nov, after the pack stage)

The lead ruled that problems used to evaluate RL or effort stay out of SFT training (RL held-out set and the effort
suite's code prompts), the SFT held-out split stays out of the RL pool, and the training pools may overlap. The pack
above is the verified input; `../eval_firewall.py apply` then drops the training rows of 250 problem
families (private list, sha256 `e8183f8ff236…`) and writes `pack.firewalled.jsonl`, an ordered byte
subsequence of `pack.jsonl`. Every per-shard hash and check above stays valid; the held-out file is not touched.

All 70 shards, predicted from the per-row stats: 7,958 training rows and 37,717,518 tokens
(1.42%) removed, 410,538 rows / 2,623,855,801 tokens left. Applied on
the four shards whose verified packs are on hand (input sha256 checked against the manifest first):

| Shard | Firewalled pack sha256 | Rows kept | Rows removed | Tokens removed | Predicted = actual |
|---|---|---:|---:|---:|---|
| 0 | 227d97e37ede3b20… | 7,687 | 360 | 1,615,713 | yes |
| 1 | 8a5c19ac8c6793ee… | 7,640 | 369 | 1,607,523 | yes |
| 2 | 0143f11095ac75a1… | 7,607 | 367 | 1,683,894 | yes |
| 3 | c2b530f12a166cc2… | 7,681 | 371 | 1,650,555 | yes |

Record: `ocr2_eval_firewall_v1.json` (13 of 13 checks). TSAI's rebuild runs the same step
after `run_ocr2.py` (`../../jobs/2026-11-17-ocr2-pack-v1-p1536.md`).

