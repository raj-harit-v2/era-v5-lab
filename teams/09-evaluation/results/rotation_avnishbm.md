# G9 week 3 rotation: Avnish's two shards

Checked on 17 November 2026 against TSAI main
`8de78eced899111ddea295d6822d024e3c6faecc`. These are the two shards
assigned to `@AvnishMidha` in the G9 rotation post. Raghav's
`results/decontam_shards.md` remains the main report for all shards.

## R1: full fingerprint set and canaries

| shard_id | payload_sha256 | docs scanned | docs flagged | fingerprints v2 set_sha256 | canary hits |
| --- | --- | ---: | ---: | --- | ---: |
| `code-python-train-000001` | `537723be5641f3aedab93695cb85f98c4b2259bb71300c9fb55bcc41ed2019d6` | 19,116 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` | 0 |
| `ind-bn-fw2-train-000000` | `ecf0822aca757724ac6b72d06af70c58350caffd848de126798b761a62f845ba` | 10,704 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` | 0 |

`decode_shard.py` accepted both manifests, payload hashes, indexes, document
metadata and EOS checks. It decoded 21,509,045 tokens in the Python shard
and 7,127,920 in the Bengali shard using frozen p1536 tokenizer SHA-256
`e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`.
`decontam_check.py` used the **full v2 set** without benchmark, tag or
exclude filters. `canary_scan.py` checked four canaries (lab, GPQA Diamond,
HLE and Terminal-Bench 2); both shard scans found zero hits.

## R2: flagged hits

None. There is no benchmark item ID, document ID or character offset to
report for either shard.

## Reproduce

Place each assigned shard's `.bin`, `.idx.npy`, `.docs.parquet` and `.json`
beside each other locally. From the repository root:

```sh
python -m pytest teams/09-evaluation/decontam/tests -q
python teams/09-evaluation/decontam/decode_shard.py <local-shards> \
  --tokenizer <local-p1536>/tokenizer.json --out <local-decoded>
python teams/09-evaluation/decontam/decontam_check.py \
  <local-decoded>/code-python-train-000001.text.parquet \
  --fingerprints teams/09-evaluation/fingerprints/v2
python teams/09-evaluation/decontam/decontam_check.py \
  <local-decoded>/ind-bn-fw2-train-000000.text.parquet \
  --fingerprints teams/09-evaluation/fingerprints/v2
python teams/09-evaluation/decontam/canary_scan.py \
  <local-decoded>/code-python-train-000001.text.parquet \
  --fingerprints teams/09-evaluation/fingerprints/v2
python teams/09-evaluation/decontam/canary_scan.py \
  <local-decoded>/ind-bn-fw2-train-000000.text.parquet \
  --fingerprints teams/09-evaluation/fingerprints/v2
```

The decode and all four scan commands exited 0. The tests gave **145 passed, 2 skipped**;
the skips require `ERA_SHARD`/`ERA_TOKENIZER` and `ERA_CLEAN_DOCS` respectively.
I also ran the optional real-shard decoder test on the Python shard with the
p1536 tokenizer: **1 passed**. Environment:
Python 3.14.9, tokenizers 0.23.3, pyarrow 26.0.0, numpy 2.5.3. The decoded
`.text.parquet` files, signed download links and scan logs remain local.
This report contains no benchmark item text or document text.
