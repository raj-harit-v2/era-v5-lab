# G9 week 3 rotation: decontamination and canary checks (rajiviyer)

Checked on 18 November 2026 using repository commit `69970092d242a34774856742631714c265c8df4f`. Both shards are from the p1536 sample-v0 training set.

## R1: result per shard

| shard_id | payload_sha256 | docs scanned | docs flagged | canary hits | set_sha256 (fingerprints v2, full set) |
|---|---|---:|---:|---:|---|
| `code-java-train-000001` | `c8e3aca96a7f6c16047b187caec4d09b0fdfab2eb4ec13ca2120e0c680f18c14` | 22,228 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `ind-mr-fw2-train-000000` | `c6aa0cf3adb8e3f01741ad41cab255d033ac47a802040bd6ce60fe5a61681be4` | 11,250 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |

- **Inputs:** Each payload, index, and document metadata file matched its manifest SHA-256. The frozen p1536 tokenizer matched SHA-256 `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`.
- **Decode:** `decode_shard.py` accepted both shards, including their manifest, payload, index, document metadata, tokenizer and EOS checks. Java had 19,878,065 tokens; Marathi had 7,146,419 tokens.
- **Fingerprint check:** `decontam_check.py` scanned the full v2 set without benchmark, tag, or exclusion filters.
- **Canary check:** `canary_scan.py` checked four canaries: `era-v5-lab`, `gpqa_diamond`, `hle`, and `terminal_bench_2`.

## R2: hits

None. Neither shard had a flagged document or a canary hit, so there are no hit IDs or offsets to investigate.

## Commands

```bash
for s in code-java-train-000001 ind-mr-fw2-train-000000; do
  python teams/09-evaluation/decontam/decode_shard.py <shards>/$s.bin --tokenizer <p1536>/tokenizer.json --out <local-dir>
  python teams/09-evaluation/decontam/decontam_check.py <local-dir>/$s.text.parquet
  python teams/09-evaluation/decontam/canary_scan.py <local-dir>/$s.text.parquet
done
```

All commands exited 0. Decoded text was kept in local temporary storage and is not committed. Zero hits only means no matches were found by these checks; it does not rule out contamination outside their coverage.
