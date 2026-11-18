# Week 3 G1 rotation shard audit — udisinghania

Verified both assigned **tokenizer sample-v0** shards from the 16 Nov TSAI artifact return. These are two actual sample-v0 payloads. First-training-shard verification is a separate milestone.

Frozen tokenizer p1536 SHA-256: `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b`. I independently hashed and loaded the tokenizer, which reports 131,072 entries and EOS 130822. Applied the [shard-v1 format](../shards/shard_format_v1.md) and manifest template with the p1536 identity supplied for this release. Both manifests identify writer commit `0064f81d57ef47e22d8fa5f42d96c99089a98ce4`.

## Java — `code-java-train-000000`

Manifest SHA-256: `be5e714f712d236fe16eced0cc1125fcc5b7a572c6692404303d0cf0c3751f72`.

| Check | Observed evidence | Result |
| --- | --- | --- |
| Manifest schema and identity | All 28 template fields present. Schema, sample/train identity, pack, language, script, domain, capability lane, EOS, tokenizer hash, URI filenames and hash syntax matched the expected values. | Pass |
| Payload | 224,015,020 bytes. SHA-256 `d885478b8a77ebfec35d9525d35a2f479e38f2b475f1167215c64b2ec5bec2dd` matched the manifest. | Pass |
| Payload header and tokens | Magic 20261025, version 2, zero reserved fields. Header count, uint32 payload length, index end and manifest agree at **56,003,499 tokens**. IDs range from 0 to 130,822. | Pass |
| Document index | 499,504 bytes. SHA-256 `8b8f6ecc12a338017efe4cbdabc39776cf29ba7cfd4e80ecbb65258bcdf6e501` matched. int64, first offset zero, strictly increasing, 62,422 entries. | Pass |
| EOS | **62,421** document ends had EOS 130822. Total EOS occurrences equal the document count. | Pass |
| Parquet | 1,813,885 bytes. SHA-256 `d0a00c9cf8debef20ebcdb5e94f90fb39851433b0a004dbc6ba99fda0f35af7f` matched. **62,421 rows**, expected metadata columns, and every row's `n_tokens` matches its index span including EOS. | Pass |
| Quality report | 1,122 bytes. SHA-256 `bd9f2b12270005f21fda9b17c029c9e8758354854f6136c6ec55763dbd7a6d35` matched. 62,430 rows read. Omissions reconcile with the kept count and the per-reason ID list lengths. | Pass |
| Reported omissions | Secret-like 8, empty 1, special 0, round-trip 0. These are the producer's recorded drops. | Pass |
| Shared pipeline | SHA-256 `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` matched. F2 hash matched the manifest. Dedup version was expected and the file contains `dedup: null`. | Fail, [#503](https://github.com/theschoolofai/era-v5-lab/issues/503) |

## Telugu — `ind-te-sangraha-v-train-000000`

Manifest SHA-256: `cb5341b9e879c028b0638db98c0174df527a52749d3983a1f5340d4cf28a0549`.

| Check | Observed evidence | Result |
| --- | --- | --- |
| Manifest schema and identity | All 28 template fields present. Schema, sample/train identity, pack, language, script, domain, capability lane, EOS, tokenizer hash, URI filenames and hash syntax matched the expected values. | Pass |
| Payload | 21,306,640 bytes. SHA-256 `1036ff48ca9f714311ae676f8b9170cfa30ae8f94e826fb2cee03193bf811045` matched the manifest. | Pass |
| Payload header and tokens | Magic 20261025, version 2, zero reserved fields. Header count, uint32 payload length, index end and manifest agree at **5,326,404 tokens**. IDs range from 0 to 130,822. | Pass |
| Document index | 68,880 bytes. SHA-256 `77fbd21dae6f0a55face1e020e4975797fc9e735130e0a205dbc5d72be638352` matched. int64, first offset zero, strictly increasing, 8,594 entries. | Pass |
| EOS | **8,593** document ends had EOS 130822. Total EOS occurrences equal the document count. | Pass |
| Parquet | 257,649 bytes. SHA-256 `047ec298980994c1f94eb4287bc2114f31474fa80bff9fc67bb0e4fe2b692b4b` matched. **8,593 rows**, expected metadata columns, and every row's `n_tokens` matches its index span including EOS. | Pass |
| Quality report | 920 bytes. SHA-256 `74ca486f7edb13b3359559e118c381ed6c9321b1fd89f775afbb66ae693e1e7c` matched. 8,594 rows read. Omissions reconcile with the kept count and the per-reason ID list lengths. | Pass |
| Reported omissions | Secret-like 1, empty 0, special 0, round-trip 0. These are the producer's recorded drops. | Pass |
| Shared pipeline | SHA-256 `35611a83cfa6d6b510a43b07c5d356c4f6d5d908bbb7d4f3c8b9f05856046589` matched. F2 hash matched the manifest. Dedup version was expected and the file contains `dedup: null`. | Fail, [#503](https://github.com/theschoolofai/era-v5-lab/issues/503) |

## Reproduction and disposition

Set `SHARDS` to the directory containing the returned artifacts. From a shell with NumPy and PyArrow, run the following per assigned shard. Compare each printed hash and the derived counts with that shard's JSON manifest. Use the [G3 release](../../03-tokenizer/release/) to verify the tokenizer hash and EOS ID.

```bash
cd "$SHARDS"
sha256sum code-java-train-000000.* ind-te-sangraha-v-train-000000.* cleaning_pipeline.json
python - <<'PY'
import json
import numpy as np
import pyarrow.parquet as pq
for shard in ("code-java-train-000000", "ind-te-sangraha-v-train-000000"):
    with open(shard + ".json", encoding="utf-8") as file:
        manifest = json.load(file)
    header = np.fromfile(shard + ".bin", dtype="<i4", count=256)
    ids = np.memmap(shard + ".bin", mode="r", dtype="<u4", offset=1024)
    offsets = np.load(shard + ".idx.npy", allow_pickle=False)
    metadata = pq.ParquetFile(shard + ".docs.parquet")
    print(shard, header[:3].tolist(), len(ids), int(ids.min()), int(ids.max()),
          len(offsets) - 1, int(offsets[-1]), bool((np.diff(offsets) > 0).all()),
          int((ids[offsets[1:] - 1] == manifest["eos_token_id"]).sum()),
          metadata.metadata.num_rows)
PY
```

One shared provenance finding, tracked in #503. No new issue was identified. Manual text decoding was outside this rotation assignment. Review requested from Vijay.
