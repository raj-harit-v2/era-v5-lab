# OCR-2 pack v1 (C3, 32768): build record and counts

Set `sft-code-opencodereasoning-2`, nvidia/OpenCodeReasoning-2 @ `eadf535931451525f3e5621d0f960c240bc62fd9`, `train/python`,
all 70 shards. Built 14 Nov 2026 under the TSAI decisions for the OCR-2 pack (G10 group, 14 Nov). Aggregates, hashes and
commands only: no row text, no ids. The pack bytes are not in Git (TSAI rule, 14 Nov); `jobs/2026-11-16-ocr2-pack-v1.md`
asks TSAI to rebuild and store them. The machine-readable record is `ocr2_pack_v1_manifest.json` (per-shard sha256 and
counts, 37 acceptance checks).

**Status.** Built and checked by G10. Not reviewed by the lead, not merged, not stored by TSAI. Two inputs to these hashes are
G10 proposals, not rulings (table below). Changing either one changes the policy sha256, so the run id changes and the pack has to
be rebuilt. It is not a one-line edit to the pack.

## What decided each rule

| Rule | Authority | Where |
|---|---|---|
| C3 tokenizer, sha256 `15468e66…02ddc3`, eos `<|endoftext|>` 130822 | TSAI ruling, 14 Nov | `ocr2_policy.json` `pack.approved_tokenizer_sha256` |
| `max_sequence_tokens` 32768, provisional for SFT data v1 | TSAI ruling, 14 Nov | source manifest `conversion` |
| 69,690 open-r1/codeforces train rows held out of v1 | TSAI ruling, 14 Nov | policy `sources.open-r1/codeforces` |
| TACO, APPS, code_contests: repo + exact revision recorded; level `pinned_revision` (not relabelled `verified`) | TSAI ruling, 14 Nov (record repo and revision); the level name is G10's | policy `approval`, `pack.accepted_identity_levels` |
| "Any row without a clear source stays out": 14 TACO problems excluded as `policy_unclear_source` | the rule is TSAI's; which rows it covers is a G10 judgement. These are candidates where both identity signals lose to neighbouring rows, from shards 0-2. **The WP11 human spot check has not happened; no verdict exists** | policy `unclear_source_rows` |
| Quality: critique `right`, pass_rate 1.0, missing execution evidence admitted and tagged | #391 rule (SFT mix v1); the policy still calls it a proposal; TSAI has named no other threshold | policy `target_quality` |
| 2% of problem families held out as `heldout_eval_v1` | **TSAI confirmed: keep the split.** The latest G10 ruling also asks for the split seed and row IDs in the pack manifest, and completion of the 14 source spot checks before finalization. The existing salted-hash split and bytes are unchanged. | policy `pack.heldout_eval_v1`; post-build ruling in the summary manifest |

## Counts (from the manifest by `render_tables.py`; no number typed by hand)

| Stage | Rows |
|---|---|
| raw OCR-2 python rows (70 shards) | 1,398,166 |
| policy excluded | 786,366 |
| malformed or unresolved | 69,690 |
| eligible joined | 542,110 |
| converter rejected | 67 |
| rendered (C3) | 542,043 |
| decontam flagged and removed | 115,040 |
| canary hits | 0 |
| retained after second pass | 427,003 |
| pack row checks failed | 0 |
| row checks passed | 427,003 |
| held out for eval_v1 | 8,507 |
| **admitted to the training pack** | 418,496 |

| Join outcome | Rows |
|---|---|
| `eligible_joined` | 542,110 |
| `quality_critique_wrong` | 310,019 |
| `policy_protected_split` | 268,752 |
| `quality_execution_failed` | 203,790 |
| `held_source_unavailable` | 69,690 |
| `policy_protected_family` | 3,629 |
| `policy_unclear_source` | 176 |

| Training pack | Value |
|---|---|
| rows | 418,496 |
| tokens (C3) | 2,661,029,931 |
| supervised (shifted) targets | 2,488,857,211 |
| longest row, tokens | 29,829 (limit 32,768) |
| rows from apps/train | 127,271 |
| rows from code_contests/train | 51,006 |
| rows from taco/train | 240,219 |

| Held-out eval_v1 | Value |
|---|---|
| rows | 8,507 |
| problem families | 317 |
| tokens | 53,317,333 |
| rows from apps/train | 2,550 |
| rows from code_contests/train | 1,225 |
| rows from taco/train | 4,732 |
| id list sha256 | `193d589d942ec54b44c64ddf66d32af7f3a99ea842689b1275d6881f6bced7f1` |

| Effort label (rendered stage, before decontam) | Rows |
|---|---|
| 16k | 288,988 |
| 1k | 45,242 |
| 4k | 195,231 |
| 64k | 12,582 |

| Decontam flags by benchmark (a row can hit several) | Rows |
|---|---|
| codeforces | 84,154 |
| livecodebench | 68,053 |
| hle | 2,045 |
| milu | 93 |
| heldout_g5_v1 | 47 |
| swe_bench_live | 7 |
| gaia | 3 |
| mmlu | 3 |
| swe_bench_pro | 3 |
| aime_2025 | 1 |

| Count | 10 Nov diagnostic | v1 pack | Difference |
|---|---:|---:|---:|
| `policy_protected_split` | 268,752 | 268,752 | +0 |
| `policy_protected_family` | 3,629 | 3,629 | +0 |
| `quality_critique_wrong` | 310,019 | 310,019 | +0 |
| `quality_execution_failed` | 203,790 | 203,790 | +0 |
| `held_source_unavailable` | 69,690 | 69,690 | +0 |
| `policy_unclear_source` | 0 | 176 | +176 |
| `eligible_joined` | 542,286 | 542,110 | -176 |
| rendered.converter_rejected | 67 | 67 | +0 |
| rendered.rendered | 542,219 | 542,043 | -176 |
| screened.rows_removed | 115,067 | 115,040 | -27 |
| screened.rows_kept | 427,152 | 427,003 | -149 |

| Sequence length, C3 tokens (rows that passed the row checks) | Value |
|---|---|
| longest row | 29,829 |
| rows over 32,768 | 0 rejected at the pack stage |
| shards built | 70 (66 on Modal CPU (2 cores, 4 GiB), 4 on laptop (Apple M1 Pro, run_ocr2 --workers 4)) |
| training pack bytes (sum of per-shard pack.jsonl) | 32,020,460,788 |
| held-out bytes (sum) | 640,632,109 |

Acceptance checks in the manifest: 37 of 37 hold.


Reading the reconciliation: every join outcome equals the 10 Nov diagnostic (`ocr2_coverage.md`) except the 176 rows of the 14
unclear-source problems, found in 29 shards. Of those 176, 27 would have been removed by decontam and 149 kept, so the retained
total falls by 149 (−0.035%). The C3 tokenizer changes no row's admission: no row exceeds 32,768 tokens (longest 29,829; the
v0.1-tokenizer diagnostic's longest was 29,851). The diagnostic was in a different mode with a different tokenizer, so
this is reconciliation, not parity. The pack-stage comparison with the C3 shard-3 diagnostic (8,259 row checks, report mode) is
8,245 in v1: −14, which the shard-3 unclear-source exclusions account for (15 rows before decontam).

Codeforces: 227,983 OCR-2 rows name `open-r1/codeforces`. 158,293 of them fail the quality rule first (critique wrong 126,187,
pass_rate under 1 32,106). The other 69,690 are `held_source_unavailable`. **0 Codeforces rows are eligible in any shard**
(manifest check `sources.no_codeforces_row_eligible`). The decontam count by benchmark "codeforces" (84,154) is unrelated: that is
Team 9's Codeforces *benchmark* fingerprint screen.

Supervision: the loss covers each assistant body and its closing `<|im_end|>`. The final `<|endoftext|>` (130822) is in every
row but is **not a supervised token**. Team 12's stop-token setup should match.

Effort labels are counted at the render stage, before decontam and the held-out split. The compact shard results carry no
admitted-pack breakdown by effort, so effort totals for the admitted pack are **not measured**.

## Checks

- **Manifest acceptance checks, 37 of 37 hold** (`aggregate.py`; it refuses to write on any failure). They cover: all 70 shards
  exactly once; complete, `pack_validated`, reconciled, full input; one config sha256 / run id `admission-7107d5b9dc9c` for all
  70; the code, policy and source manifest on disk hash to what the run recorded; Modal download size + sha256 equal the manifest
  (66 shards). The four laptop parquet files and the four laptop pack + held-out files were re-hashed against the manifest and the
  run record. Also covered: full-set decontam with fingerprint set v2, 0 canaries, a zero-hit second pass on every shard; training
  mode, admissible, no blocker, admitted = emitted; pack and held-out sha256 present; bound to this policy, source manifest and C3;
  longest row ≤ 32768; training rows only from taco/apps/code_contests train; no Codeforces row eligible; held-out ids unique and
  counted, every held-out family re-selected under the policy salt and fraction, every held-out row from an approved split at the
  pinned revision; the five conservation equations over the set, raw = 1,398,166.
- **Held-out isolation.** `pack_admission.py` raises if a problem family lands on both sides within a shard. Across shards the
  split is a pure function of the family key (salted sha256), so a family is held everywhere or nowhere. The manifest check
  re-derives it for every held-out row. A cross-shard family-key list for the training side is not kept, so the cross-shard
  property rests on that construction and not on a set intersection.
- **Loss masks** (`check_pack_rows.py`, shards 0-3, every train and held-out row: 32,855 rows, 212,547,311 tokens): 0
  violations. It checks for every row that the first token is an untrained `<|im_start|>` and the last an untrained
  `<|endoftext|>`; that tokens are trained only inside assistant turns and the assistant `<|im_end|>` is trained; that no role
  header, system or user token is trained; that the shifted target is not empty; and length ≤ 32768. 197,555,144 trained tokens,
  all in assistant turns. 20 rows per source were decoded beside their shifted labels into a private file (not in Git).
  Shards 4-69 were checked only by `pack_admission.py`'s in-pipeline recompute (ids and mask equal a fresh tokenisation of
  the text and spans; at least one shifted target). The independent checker did not run on them, because their bytes were
  deleted in the containers.
- **Tests:** `sft/verify.sh`: 243 passed, 0 skipped, 60 s on the laptop (214 at f2f03ce).
- **Cross-machine rebuild (shard 4):** **content parity holds; one record is path-dependent.** Shard 4 was rebuilt on the laptop (macOS arm64, `--workers 1`, 1,079 s, 957 MB peak RSS) from a run root at a different absolute path, and compared with the Modal trial (Linux, 2 cores). The same run id; identical `pack.jsonl` sha256 (`d7357e5e…`, re-hashed), identical held-out sha256, identical counts, identical joined/rendered/screened/rechecked stage hashes. The pack-stage hash and the shard `deterministic_sha256` differ, because `pack_manifest.json` stores absolute paths to the policy, source manifest and tokenizer. With the run root swapped in that file, the recomputed pack-stage hash equals Modal's exactly (`e947f677…`). A rebuild should therefore compare `pack_sha256`, `heldout_sha256` and the counts, and not `deterministic_sha256` (manifest `hash_notes`). Making those paths relative would change `run_ocr2.py`, and so the run id, which is why it is left for a later version.

## Pack-stage speed (shard 3, same input, Apple M1 Pro 8 cores / 16 GB, one process, no other build running)

| Code | Mode | Seconds | CPU s (user+sys) | Peak RSS | Pack sha256 |
|---|---|---:|---:|---:|---|
| f2f03ce `pack_admission.py` (per-row `encode`) | report | 95.3, 95.9 | 94.7, 95.1 | 184-191 MB | n/a (cannot admit: identity gate) |
| branch, `encode_batch` chunks of 256 (shipped) | report | 44.6, 45.5 | 190.6, 192.1 | 625 MB | n/a |
| branch, chunks of 256 (shipped) | training | 46.3 | 193.2 | 615 MB | `2f3c16af…6c66ba2b` |
| branch, chunk 1 (per-row path) | training | 97.3 | 96.7 | 193 MB | `2f3c16af…6c66ba2b` |

The output is byte-identical: the chunk-256 pack, the chunk-1 pack and the shard-3 pack of the build all hash to
`2f3c16af550e25ae7eeb4f78e0ba4048c39fb1a8e689118da429508e6c66ba2b`, and the held-out file to `4c7ab74f…675ba584` in all three.
Wall time falls 2.1×, but CPU time doubles and peak memory triples. The gain is the tokenizer's own threads, not less work. It
helps a single process on idle cores. On a machine where `--workers` already fills every core it is **not measured** and may be
nil. The "before" row is the f2f03ce file run with the branch's `prepare_ocr2.py` / `source_index.py`: the untouched f2f03ce
`source_index.py` rejects the `pinned_revision` level in the v1 manifest, so it cannot read this input at all. In the real
build the pack stage took a median of 72 s per shard on the Modal 2-core containers (89 s for shard 4), out of a median shard total of
1,705 s. The decontam screen dominates, as it did on 10 Nov.

## Build record

| Part | Where | Shards | Time | Notes |
|---|---|---|---|---|
| local | Apple M1 Pro, `run_ocr2.py --workers 4` | 0-3 | 1,249 s wall, 4,800 s user | largest process 920 MB RSS |
| trial | Modal CPU, 2 cores, 4 GiB, app `ap-XqBIv0PIdTFURoude69Jpt` | 4 | 1,919 s | exit 0 |
| full | Modal CPU, 2 cores, 4 GiB, one container per shard, app `ap-aGu4TurDdMI4kIR1MHAbmv` | 5-69 | ≈3,630 s app wall; per shard median 1,705 s, max 2,328 s | `DONE 65 complete of 65`, exit 0 |

Modal: 66 containers, 90,352 container-seconds, 92,097 CPU-seconds, children peak RSS ≤ 1,733 MB, 132.8 GB of intermediates
deleted in the containers. **Spend is an estimate, ≈ $3.43:** the 10 Nov run's billed rate per container-second (same 2-core,
4 GiB request) × the measured seconds. It is not read from billing: the installed Modal client (1.2.6) has no `billing`
command. Earlier trial attempts that failed before any work are not counted. Check the dashboard for the exact figure.

Rebuild recipe: `../jobs/2026-11-16-ocr2-pack-v1.md` (run-root layout, command, expected per-shard hashes). The source manifest
is `../manifests/ocr2_source_manifest_v1.json` (sha256 `ded9be9e…eaf9c4`); every input file is pinned by sha256, and the runner
refuses any mismatch.

## Final state, 16 Nov 2026 (metadata only; no rebuild)

- **Final as built.** The 14 unclear-source TACO keys (176 rows in 29 shards) stay out under TSAI's "any row without a
  clear source stays out". The manifest `unclear_source` block lists the ordinals and rows per shard, says what a later
  "same" verdict would change (`if_cleared`), and records no verdict. The human spot check is pending; its side-by-side
  sheet holds dataset text and is not in Git.
- **Checks re-run.** `aggregate.py` against a `git archive` of the build commit `91ee136`: 37 of 37, output sha256
  `0dfcdb1c…` (byte-identical to the build's). Against the merged branch it refuses one check,
  `config.code_on_disk_matches_run`, for `sft/convert.py` and `chat-format/render.py`, which changed after the build.
  Shard 3 re-rendered with the merged `convert.py` is byte-identical (`30068a5f…`). Details and the rebuild revision:
  `../../jobs/2026-11-16-ocr2-pack-v1.md`, "Code revision"; manifest `rebuild_code`.
- **Held-out handoff** re-verified against the updated manifest: 8,507 rows, 317 families, 8 of 8 checks
  (`ocr2_heldout_v1_handoff.json`, new manifest sha256).
- **Tokenizer.** TSAI's Gate 3 notice (15 Nov) moved the frozen tokenizer to p1536 (same special ids, eos 130822, same
  vocabulary size) and kept C3 work valid as a record. This pack's token ids, counts and lengths are C3. Which one v1
  training uses is a TSAI question (manifest `post_build_rulings`).
