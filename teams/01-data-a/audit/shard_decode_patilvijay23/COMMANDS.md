# Decode using the existing G9 functions

Run from the repository root with NumPy, PyArrow and `tokenizers==0.23.3` installed. No additional runner is required.

## Existing CLI: decode a complete shard

In WSL/Bash, use backslashes for line continuation. Press **Ctrl+C** first if the shell is waiting at a `>` prompt. Each backslash must be the final character on its line.

```bash
python teams/09-evaluation/decontam/decode_shard.py \
  "/mnt/c/Users/heman/Downloads/tokenizer_samplev0_shards/ind-mr-sangraha-v-train-000000.bin" \
  --tokenizer "/mnt/c/Users/heman/Documents/vijay/erav5-lab-other-files/p1536/tokenizer.json" \
  --out out/shard_decode_2026-11-16/manual_full
```

In Windows PowerShell, use backticks and Windows paths:

```powershell
python teams/09-evaluation/decontam/decode_shard.py `
  "C:\Users\heman\Downloads\tokenizer_samplev0_shards\ind-mr-sangraha-v-train-000000.bin" `
  --tokenizer "C:\Users\heman\Documents\vijay\erav5-lab-other-files\p1536\tokenizer.json" `
  --out out/shard_decode_2026-11-16/manual_full
```

This uses the existing CLI and decodes every document in that shard. Its output holds text and must remain local.

## Decode only 20 documents: direct function calls

The existing CLI has no sampling option. Use its existing `load_tokenizer`, `read_shard`, `special_ids` and `vocab_end` functions, then call the tokenizer's `decode_batch` on the selected document spans. Paste this in a Python console/notebook from the repository root. These calls have no CLI wrapper or resume layer.

```python
import hashlib, json, random, sys
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path("teams/09-evaluation/decontam").resolve()))
import decode_shard as ds

shards = Path(r"C:\Users\heman\Downloads\tokenizer_samplev0_shards")
tokenizer = Path(r"C:\Users\heman\Documents\vijay\erav5-lab-other-files\p1536\tokenizer.json")
shard_id = "ind-mr-sangraha-v-train-000000"
out = Path("out/shard_decode_2026-11-16/manual")

tok, tok_sha = ds.load_tokenizer(tokenizer)
assert tok_sha == ds.P1536_SHA256
sid, tokens, starts, doc_ids, manifest = ds.read_shard(
    shards / (shard_id + ".bin"), tok_sha, ds.special_ids(tok), ds.vocab_end(tok))
seed = int.from_bytes(hashlib.sha256(f"20261116:{manifest['payload_sha256']}".encode("ascii")).digest(), "big")
rows = sorted(random.Random(seed).sample(range(len(doc_ids)), min(20, len(doc_ids))))
sequences = [tokens[starts[i]:starts[i + 1] - 1].tolist() for i in rows]
texts = tok.decode_batch(sequences, skip_special_tokens=False)
encoded = tok.encode_batch_fast(texts, add_special_tokens=False)
assert all(text and (tok.normalizer is None or tok.normalizer.normalize_str(text) == text)
           and enc.ids == ids for text, enc, ids in zip(texts, encoded, sequences))
out.mkdir(parents=True, exist_ok=True)
pq.write_table(pa.table({"doc_id": [doc_ids[i] for i in rows], "text": texts,
                        "shard_id": [sid] * len(rows), "shard_document_index": rows}),
               out / (sid + ".sample.text.parquet"))
summary = {"shard_id": sid, "decoded": len(rows), "passed": len(rows), "seed": 20261116,
           "payload_sha256": manifest["payload_sha256"], "tokenizer_sha256": tok_sha,
           "documents": [{"shard_document_index": i, "doc_id": doc_ids[i],
                          "decoded_utf8_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
                         for i, text in zip(rows, texts)]}
(out / (sid + ".summary.json")).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(f"{sid}: {len(rows)}/{len(rows)} PASS")
```

`read_shard` performs full-shard integrity checks before returning the arrays, including manifest hashes, header, index, metadata, vocabulary, EOS and inner-special-token checks. Only the selected 20 documents are decoded. The seed incorporates the payload hash and reproduces this audit's random selection.

For WSL/Linux, change the first two paths to:

```python
shards = Path("/mnt/c/Users/heman/Downloads/tokenizer_samplev0_shards")
tokenizer = Path("/mnt/c/Users/heman/Documents/vijay/erav5-lab-other-files/p1536/tokenizer.json")
```

The manual sample text and metadata-only summary stay under `out/shard_decode_2026-11-16/manual/`. Review the texts locally and record the result in the report. Do not commit text Parquet files. This command checks decoding/token round-trip; it does not scan benchmark contamination or assess semantic quality. Vijay has since reported his side-by-side manual review and supplied two saved IDs; running this new random sample does not reconstruct the other 18 IDs from that earlier review.

For another shard, change `shard_id`. For a batch, get paths from `ds.find_shards(shards)` and repeat the same function calls, excluding the Marathi pack if reproducing the original automated extension. Load the tokenizer once. The original two assigned checks, 38 further random samples and the fresh 20-document Marathi check are already recorded, so no rerun is needed. The Marathi check recorded on 17 Nov is a new reproducible selection, not a reconstruction of the earlier manual review. The subsequent viewer-candidate, scoped-cleaner and sample-level F2 results are in [the report](../shard_check.md#side-by-side-review-and-disease-observations) and `disease_summary.json` (the larger local `sample_disease_check.json` is not needed for this commit).

## Execution history

The completed batch used an audit-only wrapper around these same G9 functions. That wrapper and its two tests are preserved locally under `out/shard_decode_2026-11-16/execution_archive/`, outside the proposed branch changes. Generated evidence remains under this audit directory; the shared decoder is unchanged. The original `reproduce.py` is retained as the reproducer for the historical two-shard evenly spaced check.
