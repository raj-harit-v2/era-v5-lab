# G3 rotation R1 + R2: encode speed of frozen p1536 vs BrahmicTokenizer-131K

R1: tokenizer speed on 1 GB of text. R2: the same run for BrahmicTokenizer-131K, side by side.
Section 4 gives two changes that make the tokenizing job 1.7x faster with the same ids.
Numbers only. No corpus text is in this file or in `rotation_Nisarg189.json`.

## 1. Result

1.001 GB of FineWeb-2 text (11 Brahmic languages, 91 MB each). `add_special_tokens=False`, 256 documents per encode call (as `teams/01-data-a/shards/shard_writer.py`). Median of 3 timed passes.

| Tokenizer | Mode | MB/s | tokens/s | Seconds for 1 GB | Tokens |
|---|---|---:|---:|---:|---:|
| **p1536 (frozen)** | single (1 core) | **7.28** | 825,897 | 137.5 | 113,574,014 |
| BrahmicTokenizer-131K | single (1 core) | 8.02 | 1,220,436 | 124.9 | 152,400,210 |
| **p1536 (frozen)** | batch (1 process, 14 cores) | **47.97** | 5,442,691 | 20.9 | 113,574,014 |
| BrahmicTokenizer-131K | batch (1 process, 14 cores) | 53.82 | 8,193,715 | 18.6 | 152,400,210 |

p1536 compared with BrahmicTokenizer-131K:

| | Single | Batch |
|---|---:|---:|
| MB/s (text read per second) | −9.2% | −10.9% |
| tokens/s | −32.3% | −33.6% |
| Tokens for the same text | −25.5% | −25.5% |

p1536 reads text about 10% slower than BrahmicTokenizer-131K and makes 25.5% fewer tokens. Read MB/s, not tokens/s: with fewer tokens for the same text, tokens/s drops more than the work rate. Section 3 shows where the 10% goes.

For reference, the earlier freeze C3 (same normalizer as p1536) measured 6.32 MB/s single and 47.81 MB/s batch in a run on the same machine that sent each language in one call. It is not in the JSON.

## 2. Per language (MB/s)

| Lang | p1536 single | p1536 batch | p1536 procs_fast | Brahmic single | Brahmic batch | Brahmic procs_fast | p1536 tokens/byte | Brahmic tokens/byte |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hi | 7.59 | 47.67 | 84.16 | 9.31 | 57.09 | 110.80 | 0.1192 | 0.1264 |
| Bn | 6.98 | 46.38 | 78.23 | 8.02 | 54.34 | 94.74 | 0.1167 | 0.1352 |
| Ta | 7.69 | 55.45 | 85.43 | 8.23 | 59.02 | 95.06 | 0.0969 | 0.1301 |
| Te | 7.40 | 52.85 | 82.08 | 7.99 | 54.65 | 88.66 | 0.1150 | 0.1498 |
| Kn | 6.92 | 47.89 | 81.03 | 7.88 | 55.61 | 92.35 | 0.1074 | 0.1407 |
| Ml | 7.58 | 55.39 | 84.19 | 8.48 | 60.87 | 99.52 | 0.0987 | 0.1278 |
| Mr | 7.44 | 47.97 | 81.99 | 8.09 | 54.67 | 94.35 | 0.1079 | 0.1409 |
| Gu | 6.92 | 44.25 | 78.27 | 7.93 | 53.60 | 93.83 | 0.1255 | 0.1457 |
| Pa | 7.27 | 44.85 | 78.75 | 7.52 | 47.53 | 90.76 | 0.1282 | 0.1962 |
| Or | 7.43 | 49.11 | 79.07 | 7.50 | 48.50 | 88.52 | 0.1128 | 0.2251 |
| As | 6.97 | 42.94 | 77.44 | 7.66 | 49.95 | 90.08 | 0.1196 | 0.1566 |

p1536 makes fewer tokens than BrahmicTokenizer-131K in every language, most in Or (−50%), Pa (−35%) and Ta (−26%). The other modes per language are in the JSON.

## 3. Where the time goes: the normalizer

Both files use the same pre-tokenizer and a BPE model. BrahmicTokenizer-131K has no normalizer. p1536 has NFC plus 15 `Replace` steps (`../v1/normalizer.md`).

Check on 20 MB per language, one core, median of 3. "No normalizer" is a test copy only, not a valid tokenizer:

| Tokenizer | Gu, full | Gu, no normalizer | Hi, full | Hi, no normalizer |
|---|---:|---:|---:|---:|
| p1536 | 7.48 | 8.77 | 7.59 | 8.99 |
| BrahmicTokenizer-131K | 8.52 | (none) | 9.25 | (none) |

Without its normalizer, p1536 is within 3% of BrahmicTokenizer-131K. The gap comes from the normalizer step and the character-offset tracking that it adds to each token. The tokenizer is frozen, so this is a note, not a request to change it. Section 4 removes most of the offset cost without changing the tokenizer.

## 4. Optimisation for the tokenizing job: 1.7x, same ids

Two changes, measured on the same 1 GB:

1. `encode_batch_fast` instead of `encode_batch`: the same ids, no character offsets. A job that keeps only the ids does not need offsets.
2. One process per core, each on its own documents (in a job: its own shard), with 1 thread each, instead of one process with 14 threads.

| Tokenizer | Mode | Layout | MB/s | vs batch | Seconds for 1 GB |
|---|---|---|---:|---:|---:|
| p1536 | batch (today) | 1 process x 14 threads | 47.97 | baseline | 20.9 |
| p1536 | procs | 14 processes x 1 thread | 65.57 | +36.7% | 15.3 |
| p1536 | batch_fast | 1 process x 14 threads | 64.96 | +35.4% | 15.4 |
| **p1536** | **procs_fast** | **14 processes x 1 thread** | **81.11** | **+69.1%** | **12.3** |
| p1536 | single_fast | 1 process x 1 thread | 8.93 | (+22.6% vs single) | 112.1 |
| BrahmicTokenizer-131K | batch | 1 process x 14 threads | 53.82 | baseline | 18.6 |
| BrahmicTokenizer-131K | procs_fast | 14 processes x 1 thread | 93.78 | +74.2% | 10.7 |

`--check-ids` encoded the whole 1 GB with both calls: **the ids are equal for every document**, for p1536 and for BrahmicTokenizer-131K. Splitting documents across processes does not change any document's ids.

With both changes, p1536 tokenizes 1 GB in 12.3 s on this machine. That is faster than BrahmicTokenizer-131K with today's call (18.6 s).

Checked on a 110 MB sample before the full run, and left as they are:
- Documents per call: 64, 256, 1,024 and 4,096 give 72 to 75 MB/s with `encode_batch_fast` on all cores. One call for a whole language is slower (66 MB/s). The shard writer's 256 is fine.
- Layout: 7 processes x 2 threads is the same as 14 x 1 (79.7 against 78.1 MB/s). 10 x 1 is slower (66.1 MB/s).

For `teams/01-data-a/shards/shard_writer.py` this means: change `tok.encode_batch` (line 105) to `tok.encode_batch_fast` (the loop reads only `enc.ids`), and run one writer process per shard with `RAYON_NUM_THREADS=1`.

In `procs` modes all processes start each language together and the time ends when the last one is done, so fast cores wait for slow ones. A job with independent shards has no such wait, so its gain can be a little higher.

## 5. Method

- Script: `../speed/speed_bench.py`. A mode is a layout (`single`, `batch`, `procs`) plus `_fast` for `encode_batch_fast`. Every mode runs in worker processes that set `RAYON_NUM_THREADS` before `tokenizers` loads.
- Each worker reads the corpus into memory and checks it against `corpus_manifest.json` before the clock starts. Worker k of P keeps documents k, k+P, ... of each language. Only the encode is timed.
- `fetch_corpus.py` writes documents as lines, so the script groups lines back to the mean document size of each language (`bytes / docs` from the manifest).
- 256 documents per encode call, `add_special_tokens=False`, as in the tokenizing job request. Tokenizers load with `tokenizers.Tokenizer.from_file`.
- One warm-up call per worker, then 3 timed passes. For each language, all workers start at a barrier. The tables give the median pass. All pass times are in the JSON. The 3 passes agree within 4%, except p1536 batch (10%).
- The Mac was kept awake (`caffeinate`) during the run.

## 6. Inputs

| Item | Value |
|---|---|
| p1536 `tokenizer.json` sha256 | `e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b` (TSAI Gate 3 notice) |
| BrahmicTokenizer-131K `tokenizer.json` sha256 | `01d968a7970b029c071b29f060abf6104b66168dedf2ff3b1a0290a545739fff` (repo commit `7dfcf398172c825c6689ad578e8b484ca5f57bc9`) |
| Corpus | `train/fetch_corpus.py --mb 91`, all 11 languages. Per-file sha256 in `rotation_Nisarg189.json` |
| Software | Python 3.12.4, tokenizers 0.23.3 (pinned in `release/README.md`) |
| Machine | Apple M4 Pro laptop, 14 cores (10 performance + 4 efficiency), arm64, macOS |

The machine is a laptop, not the Graviton c7g that the core speed task (`speed_v1.md`) uses. Absolute MB/s will differ there. The ratios between tokenizers and between modes are the result to compare.

## 7. Reproduce

```
python teams/03-tokenizer/train/fetch_corpus.py --out <corpus> --mb 91
python teams/03-tokenizer/speed/speed_bench.py --corpus <corpus> \
    --tok p1536=<p1536>/tokenizer.json \
    --tok brahmic=<BrahmicTokenizer-131K>/tokenizer.json \
    --modes single,batch,procs,single_fast,batch_fast,procs_fast --check-ids \
    --repeats 3 --out rotation_Nisarg189.json
```

Full run: about 40 minutes on the machine above.
