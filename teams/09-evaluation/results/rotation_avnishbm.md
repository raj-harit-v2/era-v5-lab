# G9 week 3 rotation: Avnish's two shards

Checked on 17 November 2026 against TSAI main
`8de78eced899111ddea295d6822d024e3c6faecc`. These are the two shards
assigned to `@avnishbm` in the G9 rotation post. Raghav's
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

## Task 2 shards

Checked on 18 November 2026 against class main
`431f9b33feb674acbc370fbea6d64159bf9551ac`. These four shards were
assigned to `@avnishbm` in the Task 2 split. The same frozen p1536
tokenizer and unfiltered fingerprints v2 set were used for every row.

| shard_id | payload_sha256 | docs scanned | docs flagged | canary hits | fingerprints v2 set_sha256 |
| --- | --- | ---: | ---: | ---: | --- |
| `code-js-ts-train-000001` | `62e7aa3793863ace476e851aa89e0e4ffbd007eff5b7c2ebdb05fd1c1a355418` | 30,441 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `en-nemotroncc-synth-train-000000` | `2be6f68c01d036a9e27ee3cc16d1ce02e8bf9adcd33f4f949baf48986144e278` | 146,778 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `ind-hi-indiccorp-train-000000` | `6be0f58e567a0f8a45eb2891aeadacbeb43d570e988355c5f15efa576f0764db` | 109,668 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |
| `ind-te-sangraha-v-train-000000` | `1036ff48ca9f714311ae676f8b9170cfa30ae8f94e826fb2cee03193bf811045` | 8,593 | 0 | 0 | `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a` |

`decode_shard.py` verified each manifest, payload, index, document metadata
and EOS boundaries before writing local text Parquet. It decoded 20,653,602,
50,712,366, 9,343,359 and 5,326,404 tokens respectively. The full v2
`decontam_check.py` scan flagged no documents, and `canary_scan.py` found no
canary hits. There are no benchmark item IDs, document IDs or offsets to
report for Task 2.

To reproduce each row, replace `<shard_id>` with the ID in the table and use
the same local p1536 tokenizer (SHA-256
`e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`):

```sh
python teams/09-evaluation/decontam/decode_shard.py \
  <local-shards>/<shard_id>.bin --tokenizer <local-p1536>/tokenizer.json \
  --out <local-decoded>
python teams/09-evaluation/decontam/decontam_check.py \
  <local-decoded>/<shard_id>.text.parquet \
  --fingerprints teams/09-evaluation/fingerprints/v2
python teams/09-evaluation/decontam/canary_scan.py \
  <local-decoded>/<shard_id>.text.parquet \
  --fingerprints teams/09-evaluation/fingerprints/v2
```

All twelve Task 2 commands exited 0. Decoded text, scan logs and signed
download links remain local; this report contains no document or benchmark
item text.

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
