# SFT data v1 (work-order task 1): pack manifest for the admitted sets

State on 16 Nov 2026. Machine-readable record: `sft_data_v1_manifest.json`, written by `../sft_v1_manifest.py` from the
admission summaries, the full conversion records, the OCR-2 pack manifest and the loss-mask reports in this folder.
No row text, row id or held-out id is in either file.

## Scope

No ruling on the 19 TSAI-reserves sets of the #391 mix has arrived (checked in the group export of 16 Nov, 00:19
IST), so v1 is the fallback in BLOCKED B1: the sets whose licence decision is `allowed`, plus the OCR-2 pack TSAI
admitted. A set counts toward the mix only when its decontamination covers the whole set.

| Set | Area | In the pack | Why |
|---|---|---|---|
| `sft-code-opencodereasoning-2` | Code | yes | TSAI admitted 11 Nov; pack final as built (`ocr2_pack_v1.md`) |
| `sft-dolly-15k` | General | yes | allowed; whole-set decontam; admissible |
| `sft-indic-indic-align-dolly-t` | Indic | yes | allowed; whole-set decontam; admissible |
| `sft-math-nemotron-proofs` | General | no | allowed; decontam covers 3 of 287 parts; job request `jobs/2026-11-16-sft-v1-proofs-decontam.md` (BLOCKED B6) |
| `sft-math-nemotron-math-v2` | General | no | allowed; full conversion not run (50.3 GB source); job request `jobs/2026-11-14-sft-v1-math-v2-full.md` |

Every token count is the C3 tokenizer (sha256 `15468e66…`). TSAI's Gate 3 notice of 15 Nov moved new work to p1536
(same special ids, eos 130822, same vocabulary size) and kept C3 work valid as a record. The counts were not
re-measured under p1536: the file is not on this machine. Its merges differ, so lengths and token totals would move.

## Per set

| Set | Source @ revision | Generator | Licence | Rows kept | Tokens kept | Decontam (fingerprints v2) | Over 32,768 dropped | Loss mask |
|---|---|---|---|---:|---:|---|---:|---|
| OCR-2 | `nvidia/OpenCodeReasoning-2` @ `eadf5359`; questions joined from TACO `d593ed0a`, APPS `21e74ddf`, code_contests `802411c3` (train) | DeepSeek-R1 (MIT); QwQ-32B critiques are a filter, never a target | cc-by-4.0 | 418,496 (+ 8,507 held out) | 2,661,029,931 | whole set, 70 shards: 115,040 flagged, 0 canary, zero-hit second pass | 0 (longest 29,829) | 0 violations on shards 0-3 (32,855 rows); shards 4-69 by the in-pipeline recompute |
| Dolly | `databricks/databricks-dolly-15k` @ `bdd27f4d` | none (human) | cc-by-sa-3.0 | 15,007 | 2,921,023 | whole set: 4 flagged (mmlu 2, milu 2), 0 canary | 0 (longest 5,664) | 0 violations, every converted row (15,011) |
| dolly-t | `ai4bharat/indic-align` Dolly_T @ `032b6a90` | none for the text; IndicTrans2 (MIT) translation | cc-by-4.0; source cc-by-sa-3.0 | 10,541 | 1,951,624 | whole set: 0 flagged, 0 canary | 0 (longest 7,379) | 0 violations, every converted row (10,541) |
| Proofs | `nvidia/Nemotron-Math-Proofs-v1` @ `97229c59` | gpt-oss-120b, Goedel-Prover-V2-32B (Apache-2.0) | cc-by-sa-4.0 | 902,194 (provisional) | 9,695,160,211 | 3 of 287 parts: 27 of 8,263 flagged | 18,661 | 0 violations in 10 of 287 parts (30,821 rows; 647 over 32,768, the rows the admission drops) |
| math-v2 | `nvidia/Nemotron-Math-v2` @ `8e793210` | gpt-oss-120b (Apache-2.0) | cc-by-4.0, cc-by-sa-4.0 | not built | not built | not run at this revision | 144 of the 982-row prefix | prefix record checks pass |

Hashes (full values in the manifest): conversion `content_sha256` Dolly `87790ad2…`, dolly-t `cf963f4a…`, Proofs
`d9c9d000…`; kept-id lists `9b3b49f6…`, `84351b3b…`, `d7daa10b…` (lists private); OCR-2 manifest and per-shard pack
sha256 in `ocr2_pack_v1_manifest.json`.

Loss mask rule (all sets): the assistant body and its closing `<|im_end|>` are trained; system and user text, tool
results, role headers, `<|im_start|>` and the final `<|endoftext|>` are not. The check is `check_pack_rows.py`, now
able to read converted `.jsonl.gz` parts without an OCR-2 sidecar (grouped by `set`). It walks the token ids with the
chat markers as a state machine. Reports with counts only: `sft_v1_mask_checks/`. A decoded sample of 20 rows per set
is private.

## Area budget against #391 (35 / 25 / 15 / 15 / 7 / 3)

The shares are shares of the mix, not sizes, so a budget needs an anchor. Code is the only area with a large admitted
set, so the table keeps OCR-2 at its admitted size (total 7,602,942,660 tokens) and asks what every other area needs.
A smaller total, cutting OCR-2 rows, lowers every need by the same factor and does not change the fill column.

| Area | Share | Admitted tokens | Needed at this total | Fill | Filled by (ruling) |
|---|---:|---:|---:|---:|---|
| Code | 35% | 2,661,029,931 | 2,661,029,931 | 100% | OCR-2 only. More code sets: B1 (opencodereasoning, codeforces-cots, commitpackft) |
| Agentic | 25% | 0 | 1,900,735,665 | **0%** | B1: swe-rebench-openhands, nemotron-terminal, nemotron-cascade-swe |
| Tool use | 15% | 0 | 1,140,441,399 | **0%** | B1: agentic-v1, agentic-v2 tool-calling; B2: xlam-60k |
| Indic | 15% | 1,951,624 | 1,140,441,399 | 0.17% | B1: aya-dataset, aya-collection (10 subsets), indic-align-oasst-t; B3: templated_hindi_news |
| General | 7% | 2,921,023 | 532,205,986 | 0.55% | B6: Proofs after its decontam job (9.7B tokens; would need capping or sampling to fit 7%); math-v2 job; B1/B2 sets |
| Safety | 3% | 0 | 228,088,280 | **0%** | B7: a TSAI safety set with chat rows, or the fallback |

With the fallback (0% safety, 10% general) General needs 760,294,266 and fills 0.38%; nothing else moves. As
admitted today, the mix is 99.82% Code, 0.11% General and 0.07% Indic. **Agentic, Tool use and Safety are empty;
Indic and General are below 1% of their share.** The admitted sets cannot form the #391 mix; v1 as specified needs B1
(and B6 for Proofs).

## Lead's "Decontamination Open Items" (newest list in the G10 chat)

| Item | Status | Proof |
|---|---|---|
| `sft-code-opencodereasoning-2`: `-` placeholder questions need the TACO/APPS/code_contests join | **done** (G10, this team) | join `prepare_ocr2.py` + `source_index.py`; all 70 shards built and decontaminated, `ocr2_pack_v1.md` and `ocr2_pack_v1_manifest.json` (37 of 37 checks) |
| `sft-math-nemotron-proofs-v3-sft`: TSAI reserves, unchecked | **decontam done; admission blocked** on TSAI (B1) | `decontam_report.md` line 42 and `decontam_kept_rows.md` line 31: 293,648 rows, 3,012 flagged, 290,636 kept |
| `sft-code-commitpackft`: omitted from the 30-set report | **done** | `decontam_report.md` line 26: full set, 702,062 rows, 1,001 flagged, 701,061 kept. Admission blocked on B1 |
| `sft-safety-aegis-v1`: no chat rows | **not applicable** | text checked (11,997 rows, 2 removed); no assistant turn, so not SFT text; `sft_mix_proposal.md` lines 84 and 161 |
| `rl-code-swe-rebench`: Docker envs not built | **partly done; rest on the SWE env owners** | 5 pilot envs built, gold-checked on arm64 and amd64 with a decontam record (`../../results/swe_rebench_pilot.md`, `../../swe-envs/rebench-pilot/decontam_record.json`) |
| Fingerprint coverage text (HumanEval+/MBPP+) | **done** | `sft_mix_proposal.md` line 21 now says v2 does not include HumanEval, HumanEval+, MBPP or MBPP+; `decontam_report.md` line 2656 records the 9 Nov fix |
| Mix share revision (2.05% removal baseline vs 35/25/15/15/7/3) | **answered here; shares are TSAI's (B7)** | the 2.05% figure is not in the tree at this revision. The shares apply to the kept mix, so a removal rate does not change them; the area sizes above are measured after decontam |

## p1536 transfer check (16 Nov)

TSAI's Gate 3 notice moved the frozen tokenizer to p1536. The two `tokenizer.json` files have the same 356 added tokens
(ids and text), the same normaliser, pre-tokenizer and decoder and 131,072 entries, but 13,824 vocabulary entries map
to a different id. So the C3 ids in the pack are not p1536 ids: any p1536 training needs re-encoding. Whether more than
the ids changes was measured with `../tokenizer_transfer.py` (preregistered; counts in `sft_v1_p1536_transfer.json`):

| Set (scope) | Rows | Tokens p1536 / C3 | Longest C3 → p1536 | Rows crossing 32,768 | Effort tier changes | Mask violations (p1536) |
|---|---:|---:|---|---:|---:|---:|
| Dolly (all) | 15,011 | 1.0004 | 5,664 → 5,664 | 0 | 0 | 0 |
| dolly-t (all) | 10,541 | 0.9202 | 7,379 → 6,899 | 0 | 0 | 0 |
| OCR-2 (shards 0-3, train + held-out) | 32,855 | 1.0002 | 19,366 → 19,366 | 0 | 2 (4k → 16k) | 0 |
| Proofs (10 of 287 parts) | 30,821 | 1.0009 | 55,487 → 55,496 | 3 newly over | 15 (11 4k → 16k, 3 16k → 64k, 1 1k → 4k) | 0 |

Method check: re-encoding the stored text with C3 gives the stored ids on all 89,228 rows. **What carries over:** the
rows, their text apart from the effort line, the masks (0 violations), and the length limit (no OCR-2, Dolly or dolly-t
row crosses 32,768). **What does not:** the ids, and a few effort tiers. A tier change rewrites the row's `Reasoning
effort:` line, so a p1536 version must re-run the render stage, not only re-encode. At the shard 0-3 rate that is about
25 of the 418,496 OCR-2 training rows (extrapolated, not measured). For Proofs, admission would drop 3 more rows per
30,821 at 32,768. Indic text is 8% shorter in p1536. Not measured: OCR-2 shards 4-69, Proofs beyond 10 parts, math-v2.
TSAI said C3 work stays valid as a record; whether SFT data v1 trains on C3 or is rebuilt in p1536 is TSAI's decision.

## Reproduce

```
python sft/sft_v1_manifest.py --out sft/results/sft_data_v1_manifest.json
python sft/check_pack_rows.py --pack <private>/full/<set>/<set>.part*.jsonl.gz --tokenizer <C3 tokenizer.json> \
    --report sft/results/sft_v1_mask_checks/<set>.mask_check.json
python sft/sft_v1_admit.py ...   # per set, as in sft_v1_close.md section 6
```

Measured on an Apple M1 Pro (8 cores, shared): the mask check took 2.5 s on Dolly, 1.5 s on dolly-t and 221 s on the
10 Proofs parts; the manifest script runs in under a second.
