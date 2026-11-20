# Shard check — G1 core task 6

**Task:** Decode 20 documents per shard and check each shard manifest: count, hash and source.

**Owners:** Tejaskumar + Vijay. Execution/evidence in this report: Vijay Patil (`patilvijay23`).

**Deliverable:** `teams/01-data-a/audit/shard_check.md`. **Due:** Thu 19 Nov 2026 (D5).

**Updated:** 17 Nov 2026. Shared decoder base: `23d7902a39c7cc78e1e3c19f25aeaee7a5355697`.

## Result

**41/41 downloaded sample-v0 shards have recorded 20-document checks: 820/820 documents passed decoding, normalization and exact token round-trip.** Manifest count, artifact-hash and recorded source-metadata checks pass for all 41 shards. **Exact upstream source verification remains PARTIAL**, as detailed below; this report does not declare training readiness.

Scope is the actual downloaded p1536 sample-v0 bundle: **41 shards across 31 packs**, not all possible source packs. The original two evenly spaced samples are preserved, 38 further samples use seeded random selection, and a fresh reproducible 20-document Marathi Sangraha sample was checked on 17 Nov. That last sample closes the saved-ID gap; it does not reconstruct Vijay's earlier manual selection.

Compact inventory, complete manifest hashes, recorded input hashes and evidence references: [summary.json](shard_decode_patilvijay23/summary.json). The individual `.decode.json` files contain only IDs, source references, counts, offsets and hashes, never document text.

## Per-shard results

| Shard / evidence | Source part from metadata | Docs | Tokens | Decode | Count / hash / source metadata |
|---|---|---:|---:|---|---|
| [code-cpp-train-000000](shard_decode_patilvijay23/code-cpp-train-000000.decode.json) | `code-cpp_part-00000_clean.parquet` | 40,355 | 66,915,318 | 20/20 | PASS / PASS / PASS |
| [code-cpp-train-000001](shard_decode_patilvijay23/code-cpp-train-000001.decode.json) | `code-cpp_part-00001_clean.parquet` | 14,145 | 23,634,925 | 20/20 | PASS / PASS / PASS |
| [code-go-train-000000](shard_decode_patilvijay23/code-go-train-000000.decode.json) | `code-go_part-00000_clean.parquet` | 56,588 | 56,698,571 | 20/20 | PASS / PASS / PASS |
| [code-go-train-000001](shard_decode_patilvijay23/code-go-train-000001.decode.json) | `code-go_part-00001_clean.parquet` | 20,213 | 20,255,694 | 20/20 | PASS / PASS / PASS |
| [code-java-train-000000](shard_decode_patilvijay23/code-java-train-000000.decode.json) | `code-java_part-00000_clean.parquet` | 62,421 | 56,003,499 | 20/20 | PASS / PASS / PASS |
| [code-java-train-000001](shard_decode_patilvijay23/code-java-train-000001.decode.json) | `code-java_part-00001_clean.parquet` | 22,228 | 19,878,065 | 20/20 | PASS / PASS / PASS |
| [code-js-ts-train-000000](shard_decode_patilvijay23/code-js-ts-train-000000.decode.json) | `code-js-ts_part-00000_clean.parquet` | 85,508 | 58,203,242 | 20/20 | PASS / PASS / PASS |
| [code-js-ts-train-000001](shard_decode_patilvijay23/code-js-ts-train-000001.decode.json) | `code-js-ts_part-00001_clean.parquet` | 30,441 | 20,653,602 | 20/20 | PASS / PASS / PASS |
| [code-python-train-000000](shard_decode_patilvijay23/code-python-train-000000.decode.json) | `code-python_part-00000_clean.parquet` | 53,221 | 60,537,332 | 20/20 | PASS / PASS / PASS |
| [code-python-train-000001](shard_decode_patilvijay23/code-python-train-000001.decode.json) | `code-python_part-00001_clean.parquet` | 19,116 | 21,509,045 | 20/20 | PASS / PASS / PASS |
| [code-rust-train-000000](shard_decode_patilvijay23/code-rust-train-000000.decode.json) | `code-rust_part-00000_clean.parquet` | 43,116 | 59,530,999 | 20/20 | PASS / PASS / PASS |
| [code-rust-train-000001](shard_decode_patilvijay23/code-rust-train-000001.decode.json) | `code-rust_part-00001_clean.parquet` | 15,028 | 21,040,035 | 20/20 | PASS / PASS / PASS |
| [en-dclm-train-000000](shard_decode_patilvijay23/en-dclm-train-000000.decode.json) | `en-dclm_part-00000_clean.parquet` | 45,032 | 53,960,422 | 20/20 | PASS / PASS / PASS |
| [en-dclm-train-000001](shard_decode_patilvijay23/en-dclm-train-000001.decode.json) | `en-dclm_part-00001_clean.parquet` | 14,735 | 17,781,210 | 20/20 | PASS / PASS / PASS |
| [en-fineweb-edu-train-000000](shard_decode_patilvijay23/en-fineweb-edu-train-000000.decode.json) | `en-fineweb-edu_part-00000_clean.parquet` | 53,444 | 52,995,687 | 20/20 | PASS / PASS / PASS |
| [en-fineweb-edu-train-000001](shard_decode_patilvijay23/en-fineweb-edu-train-000001.decode.json) | `en-fineweb-edu_part-00001_clean.parquet` | 17,725 | 17,662,417 | 20/20 | PASS / PASS / PASS |
| [en-nemotroncc-synth-train-000000](shard_decode_patilvijay23/en-nemotroncc-synth-train-000000.decode.json) | `en-nemotroncc-synth_part-00000_clean.parquet` | 146,778 | 50,712,366 | 20/20 | PASS / PASS / PASS |
| [en-nemotroncc-synth-train-000001](shard_decode_patilvijay23/en-nemotroncc-synth-train-000001.decode.json) | `en-nemotroncc-synth_part-00001_clean.parquet` | 49,008 | 16,961,507 | 20/20 | PASS / PASS / PASS |
| [en-nemotroncc-train-000000](shard_decode_patilvijay23/en-nemotroncc-train-000000.decode.json) | `en-nemotroncc_part-00000_clean.parquet` | 65,284 | 50,343,044 | 20/20 | PASS / PASS / PASS |
| [en-nemotroncc-train-000001](shard_decode_patilvijay23/en-nemotroncc-train-000001.decode.json) | `en-nemotroncc_part-00001_clean.parquet` | 21,912 | 16,778,602 | 20/20 | PASS / PASS / PASS |
| [ind-bn-fw2-train-000000](shard_decode_patilvijay23/ind-bn-fw2-train-000000.decode.json) | `ind-bn-fw2_part-00000_clean.parquet` | 10,704 | 7,127,920 | 20/20 | PASS / PASS / PASS |
| [ind-bn-sangraha-v-train-000000](shard_decode_patilvijay23/ind-bn-sangraha-v-train-000000.decode.json) | `ind-bn-sangraha-v_part-00000_clean.parquet` | 10,112 | 8,014,810 | 20/20 | PASS / PASS / PASS |
| [ind-gu-fw2-train-000000](shard_decode_patilvijay23/ind-gu-fw2-train-000000.decode.json) | `ind-gu-fw2_part-00000_clean.parquet` | 22,689 | 16,066,252 | 20/20 | PASS / PASS / PASS |
| [ind-hi-fw2-train-000000](shard_decode_patilvijay23/ind-hi-fw2-train-000000.decode.json) | `ind-hi-fw2_part-00000_clean.parquet` | 13,773 | 8,988,818 | 20/20 | PASS / PASS / PASS |
| [ind-hi-hplt-train-000000](shard_decode_patilvijay23/ind-hi-hplt-train-000000.decode.json) | `ind-hi-hplt_part-00000_clean.parquet` | 8,386 | 8,090,716 | 20/20 | PASS / PASS / PASS |
| [ind-hi-indiccorp-train-000000](shard_decode_patilvijay23/ind-hi-indiccorp-train-000000.decode.json) | `ind-hi-indiccorp_part-00000_clean.parquet` | 109,668 | 9,343,359 | 20/20 | PASS / PASS / PASS |
| [ind-hi-sangraha-s-train-000000](shard_decode_patilvijay23/ind-hi-sangraha-s-train-000000.decode.json) | `ind-hi-sangraha-s_part-00000_clean.parquet` | 7,467 | 5,988,971 | 20/20 | PASS / PASS / PASS |
| [ind-hi-sangraha-v-train-000000](shard_decode_patilvijay23/ind-hi-sangraha-v-train-000000.decode.json) | `ind-hi-sangraha-v_part-00000_clean.parquet` | 14,483 | 9,254,413 | 20/20 | PASS / PASS / PASS |
| [ind-kn-fw2-train-000000](shard_decode_patilvijay23/ind-kn-fw2-train-000000.decode.json) | `ind-kn-fw2_part-00000_clean.parquet` | 7,735 | 4,737,714 | 20/20 | PASS / PASS / PASS |
| [ind-kn-sangraha-s-train-000000](shard_decode_patilvijay23/ind-kn-sangraha-s-train-000000.decode.json) | `ind-kn-sangraha-s_part-00000_clean.parquet` | 5,185 | 5,217,346 | 20/20 | PASS / PASS / PASS |
| [ind-kn-sangraha-v-train-000000](shard_decode_patilvijay23/ind-kn-sangraha-v-train-000000.decode.json) | `ind-kn-sangraha-v_part-00000_clean.parquet` | 8,354 | 4,761,130 | 20/20 | PASS / PASS / PASS |
| [ind-mr-fw2-train-000000](shard_decode_patilvijay23/ind-mr-fw2-train-000000.decode.json) | `ind-mr-fw2_part-00000_clean.parquet` | 11,250 | 7,146,419 | 20/20 | PASS / PASS / PASS |
| [ind-mr-sangraha-v-train-000000](shard_decode_patilvijay23/ind-mr-sangraha-v-train-000000.decode.json) | `ind-mr-sangraha-v_part-00000_clean.parquet` | 12,164 | 7,259,040 | 20/20 | PASS / PASS / PASS |
| [ind-sa-fw2-train-000000](shard_decode_patilvijay23/ind-sa-fw2-train-000000.decode.json) | `ind-sa-fw2_part-00000_clean.parquet` | 5,667 | 13,940,676 | 20/20 | PASS / PASS / PASS |
| [ind-ta-sangraha-v-train-000000](shard_decode_patilvijay23/ind-ta-sangraha-v-train-000000.decode.json) | `ind-ta-sangraha-v_part-00000_clean.parquet` | 6,795 | 4,497,005 | 20/20 | PASS / PASS / PASS |
| [ind-te-fw2-train-000000](shard_decode_patilvijay23/ind-te-fw2-train-000000.decode.json) | `ind-te-fw2_part-00000_clean.parquet` | 5,670 | 4,758,086 | 20/20 | PASS / PASS / PASS |
| [ind-te-sangraha-s-train-000000](shard_decode_patilvijay23/ind-te-sangraha-s-train-000000.decode.json) | `ind-te-sangraha-s_part-00000_clean.parquet` | 4,419 | 4,781,160 | 20/20 | PASS / PASS / PASS |
| [ind-te-sangraha-v-train-000000](shard_decode_patilvijay23/ind-te-sangraha-v-train-000000.decode.json) | `ind-te-sangraha-v_part-00000_clean.parquet` | 8,593 | 5,326,404 | 20/20 | PASS / PASS / PASS |
| [math-finemath-train-000000](shard_decode_patilvijay23/math-finemath-train-000000.decode.json) | `math-finemath_part-00000_clean.parquet` | 28,088 | 38,582,010 | 20/20 | PASS / PASS / PASS |
| [math-megamath-train-000000](shard_decode_patilvijay23/math-megamath-train-000000.decode.json) | `math-megamath_part-00000_clean.parquet` | 17,232 | 33,979,879 | 20/20 | PASS / PASS / PASS |
| [sci-finepdfs-train-000000](shard_decode_patilvijay23/sci-finepdfs-train-000000.decode.json) | `sci-finepdfs_part-00000_clean.parquet` | 5,993 | 39,470,275 | 20/20 | PASS / PASS / PASS |

“Source metadata PASS” means the pack/part references belong to the manifest pack, source rows are ordered and in range, and document/token counts agree with the hashed metadata. It does not mean an independently authenticated raw or cleaned input has been verified for every document.

## Checks and reproduction

- Frozen p1536 tokenizer SHA-256: `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`; vocabulary 131,072; EOS 130822. No test-tokenizer bypass.
- Reused G9's existing `load_tokenizer`, `read_shard`, `special_ids`, `vocab_end` and tokenizer decode functions. Shared decoder code is unchanged. Header, size, index boundaries, manifest counts, token range, EOS and inner special-token constraints were checked for new samples; quality-report and cleaning-record hashes also match their manifests. The original two checks retain their historical evidence and reproduction method.
- Re-encoding each selected decoded text with `add_special_tokens=False` exactly matches its original IDs excluding terminal EOS. Text must be nonempty and fixed by the frozen normalizer.
- Random sample seed: `20261116`, combined with the payload hash using the method recorded in each evidence file. The original two samples remain evenly spaced and are not relabelled random.
- [COMMANDS.md](shard_decode_patilvijay23/COMMANDS.md) gives Bash/WSL, PowerShell and direct-function sampling instructions. No new submitted runner is required. Local text output remains under `out/` and must not be committed.

## Side-by-side review and disease observations

Vijay reports using the [updated side-by-side viewer](https://github.com/patilvijay23/era-v5-lab/tree/g1-web-viewer-pre-post/diagnosis/tools) to compare **20 documents per pack before sharding and after decoding**. He reported no sharding/decoding issue; his only concern was the Bengali A5-looking form in `57cf3b033b416567`. This is reported manual review, not a claim that every machine-selected ID was read manually. Only two IDs from the earlier manual selection were saved.

The Bengali example equals the frozen-tokenizer-normalized source. p1536 intentionally re-joins Bengali/Gurmukhi nukta letters after NFC: a generic NFC highlight can therefore flag expected output. See [G3's normalizer contract](../../03-tokenizer/v1/normalizer.md). Saved reference `2a103ec1a48ec07f` had no automatic A/B or scoped-cleaner flag.

A separate bounded check of the **earlier 800 samples plus those two manual examples** found 104 viewer-candidate documents among the 800; these are not 104 confirmed diseases. The scoped bundle cleaner leaves all 800 unchanged, with no rule errors. One pre-existing B3 unknown-marker candidate remains in Telugu document `1fdaae51d07345cf`, offset 38, and needs contextual review. It is present before sharding. Full-set G9 v2 F2 flagged **0/802** checked documents, set SHA-256 `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`. These disease/F2 results do not include the fresh Marathi sample and are not full-shard clearance. Compact metadata: [disease_summary.json](shard_decode_patilvijay23/disease_summary.json).

## Source verification limits and open findings

Against the available `cleaned-data-v0` copy, 775 of the earlier 800 sample IDs were found: 747 match after the frozen normalizer, 28 differ and 25 are missing. Applying the bundle cleaner makes 19 of those 28 match; **9 differences remain unresolved**, along with **25 missing IDs**. The affected IDs and source references are recorded in [source_verification_findings.json](shard_decode_patilvijay23/source_verification_findings.json). That baseline's job summary lacks a cleaner-hash pin. Obtain the exact pre-sharding inputs and reconcile these IDs before declaring complete upstream source equivalence. These baseline discrepancies are not established decoder regressions; the selected token round-trips pass.

The shared processing record contains `dedup: null`, previously tracked in [#503](https://github.com/theschoolofai/era-v5-lab/issues/503). Matching a processing-record hash does not resolve missing dedup provenance or grant training admission. Manifest JSON hashes identify the downloaded manifests but were not authenticated against an independently supplied manifest-hash inventory.

This report is ready as audit evidence with explicit limitations. It is not evidence of full-corpus disease freedom, full-shard benchmark decontamination or release approval.

## Supporting history

The original two-shard check remains in [shard_check_patilvijay23.md](shard_check_patilvijay23.md), with its original `run.json` and `reproduce.py`. The canonical task report is this file. The additional JSONs support its count/hash/source statements; they are not a separate deliverable. No payloads, decoded text, tokenizer bytes or signed URLs belong in this commit.
