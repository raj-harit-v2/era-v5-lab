# Shard format v1 (draft)

How the cleaned packs become token shards for training. Agreed with G3 (tokenizer, answers below); open with G7
(infrastructure). The manifest template is `shard_manifest_v1.template.json`; `shard_writer.py` writes one shard from one
cleaned part and checks it; `test_shard_writer.py` tests it.

**Sample:** `sample/` holds `code-go-train-000000` (271 docs, 262,032 tokens), written with the C3 tokenizer from the CAP-1
tokenizer sample, with every file below except the `.bin` and `.docs.parquet`, which pr-guard refuses in a PR.
`sample/README.md` gives the inputs, the commands that make them, and the sha256 of every file.

## Files of one shard

| File | What | Format |
|---|---|---|
| `<shard_id>.bin` | the token IDs | a 1,024-byte header (256 little-endian int32: magic `20261025`, version `2`, token count, then zeros), then the tokens as little-endian uint32. Byte-compatible with G6's shards |
| `<shard_id>.idx.npy` | where each document starts | `np.save` of int64, `doc_count + 1` entries: the start offset of each document, then `token_count` |
| `<shard_id>.docs.parquet` | sample metadata, one row per document in shard order | `doc_id`, `input_part`, `input_row`, `n_tokens`, `n_chars`, `lang_label`. IDs and counts only, no text |
| `<shard_id>.json` | the manifest | `shard_manifest_v1.template.json` |

- **The `.bin` layout is Data's format,** byte-compatible with G6's (`teams/06-performance/dataio/loader.py` opens it), so
  the perf loader reads our shards with no change. A header change is agreed with G6 and gets a new version.
- **uint32:** the vocab is 131,072 (max id 131,071), above the uint16 limit of 65,535.
- **Documents, not packed sequences:** each document is its tokens followed by one EOS. A shard is not cut into
  fixed-length samples, so the sequence length is a training setting (8k now, 16k later, same shards). The `.idx.npy`
  gives the document boundaries for document masking.
- **A document is never split across shards.** A shard is filled up to 2^26 tokens (256 MiB); a document longer than that
  gets a shard of its own. The header's int32 count caps a shard at 2^31 − 1 tokens.
- **One pack and one split per shard,** so mixture weights can be set per pack and language by choosing shards.
- **`payload_bytes = 1,024 + 4 × token_count`**, which the loader checks.

## Tokenizing (G3's answers)

- **Tokenizer:** C3 sample-v0, frozen (#340), `tokenizer.json` sha256 `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3`
  (`teams/03-tokenizer/release/SHA256SUMS`). The writer refuses any other file. The file (8 MB) is not in the repo: it comes
  from G3's Kaggle dataset, or is rebuilt with `teams/03-tokenizer/train/rebuild_c3_s0.py` and checked against that sha256.
  It is loaded with `tokenizers.Tokenizer.from_file`, not G6's `BrahmicTokenizer` (that pins the baseline).
- **EOS:** `<|endoftext|>`, id 130,822, after every document: G10's end-of-document marker, the same id in C3, so pretraining
  and G10's `render.py` end documents the same way. Not id 36.
- **No BOS and no language tag** for now (the `lang_slot` ids are not named).
- **Normalizer:** inside `tokenizer.json` (NFC, Malayalam chillu, Bengali/Punjabi nukta). No normalizer of our own, and no
  NFKC in cleaning (`clean.py` uses NFC; NFKC only folds the Latin ligatures U+FB00–FB06 in English packs).
- **Encoding:** `encode_batch(texts, add_special_tokens=False)`, one process per pack part.

A document is left out, counted, and listed by doc_id in the shard's quality report when:

| Reason | Why |
|---|---|
| a special id inside it | `tokenizers` turns a literal special string in the text (`<\|im_start\|>` in code) into its special id, even with `add_special_tokens=False`. Special ids: every added token marked special, and 130,725–131,071. The only special id in a shard is the EOS that ends each document |
| `decode(ids)` is not the normalized text | the tokens must give back the text, as the tokenizer's normalizer changes it |
| it encodes to no tokens | nothing to train on |
| an email-like or secret-like string | pr-guard's patterns; personal data stays out |

## Manifest fields

| Field | Meaning |
|---|---|
| `schema_version` | the manifest layout, `shard-v1` |
| `dataset_version` | the corpus release this shard belongs to |
| `shard_id` | `<pack_id>-<split>-<6 digits>`, unique within the release |
| `format`, `token_dtype` | how to read the `.bin` |
| `payload_uri`, `payload_sha256`, `payload_bytes` | the `.bin`: where, its hash, its size |
| `index_uri`, `index_sha256` | the `.idx.npy`: hashed separately, so a broken index is caught too |
| `doc_count`, `token_count` | documents and tokens in the shard, EOS included |
| `eos_token_id` | 130,822 |
| `tokenizer_sha256` | sha256 of the `tokenizer.json` bytes that made the IDs (C3: `15468e66…`) |
| `pack_id`, `language`, `script`, `domain`, `capability_lane`, `split` | what is in the shard. `split` is `train` or `validation` only: test and benchmark data are never sharded (eval firewall, G9 #269) |
| `inputs_sha256` | sha256 of the sorted lines `<input_sha256> <part>` of the input parts `run_clean.py` read (from its summaries) |
| `cleaning_pipeline_sha256` | sha256 of `cleaning_pipeline.json`: the `clean.py` sha256, the F2 fingerprint set and the dedup version |
| `decontam_set_sha256` | the G9 fingerprint set F2 checked against (v2 today). A new set means rechecking every shard with an older one |
| `sample_metadata_*`, `quality_report_*` | links to what is kept outside the manifest, with hashes |
| `created_by` | the git commit of the shard writer |

A manifest never changes after it is written.

## Dataset level

```
corpus-v1/
  SHA256SUMS                 every .json, .bin and .idx.npy of the release, sorted by path
  admission.jsonl            append-only: {"shard_id", "payload_sha256", "license_status", "admission_status", "reason", "date"}
  cleaning_pipeline.json
  <pack_id>/<split>/<shard_id>.{bin,idx.npy,docs.parquet,json}
  <pack_id>/<split>/<shard_id>.quality_report.json
```

- **License and admission live in `admission.jsonl`, not in the manifest.** They can change (a license revoked, a leak
  found); the manifest and the shard do not. The latest row for a shard wins.
- **A run pins its shard list:** the admitted shards at the start of a run, as `<payload_sha256>  <shard_id>` lines. Its
  sha256 is the `manifest` in the loader state (G7's loader contract), so a resume on another list is refused.

## Kept outside the manifest

| What | Where |
|---|---|
| Document IDs, source IDs, per-document language and provenance | `<shard_id>.docs.parquet` |
| Docs left out by the writer, dedup, contamination and held-out overlap results | quality report |
| License and admission status | `admission.jsonl` |
| Sequence length, mixture weights, curriculum | training config |
| OPUS accept/reject decisions | OPUS records |
| Samples consumed per step, resume position | training ledger and checkpoint (G7) |
| Cache location, scheduling | runtime |

## Open with G7 (infrastructure)

1. **Where shards live.** Shared file system or the S3-compatible store (the same two `ckpt/store.py` supports); the path or
   bucket and prefix, who may write, and whether training nodes read it directly or through a local cache.
2. **Shard size.** About 256 MiB (2^26 tokens) proposed: their object-size limits, upload part size, and whether
   `V5_VERIFY_MODE=head` (the store's checksum at upload) is enough for data too, or a full sha256 at load.
3. **The loader contract.** The loader state is one global offset, the skip list and `manifest` = the sha256 of the run's
   shard list. Teams 01/02 own the loader and run `ckpt/loader_contract.py` on it. Agree that the shard list format above is
   what `manifest` hashes.
4. **A shard revoked mid-run.** Removing it changes the shard list, so a resume is refused (`DataManifestError`). Is
   the answer a new branch on the new list, or the skip list?
5. **The global sampler.** How a global offset maps to (shard, document, window) at any world size, so a resharded resume gives
   the same global batch (`_reshard_check`). Who owns the sampler: Data or G7?
6. **The ledger.** Whether the training ledger logs `(shard_id, document range)` per step, or only the offset (the sampler then replays it).

## Not done yet

- Several shards per part, and the release's `SHA256SUMS` and `admission.jsonl`.
- The loader and its run of `ckpt/loader_contract.py`.
- The `capability_lane` values: from the training plan.
