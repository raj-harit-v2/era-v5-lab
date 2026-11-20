# H3: the same content in another language

`h3.py` measures H3 (E5 of `h3_design_v1.md`): pairs of documents in two languages with the same content. It lists and
counts the pairs and removes nothing. `dedup.py` reads its `h3_matches.csv` through `h3_join.py`, where only rule 0
can remove a document: a train translation of a held-out document. The method, scope and open decisions are in
`h3_design_v1.md`.

## Run

Python 3.12 with the pinned packages in `requirements_h3.txt`, and the encoder in a local folder:

```sh
python3 -m pip install -r teams/01-data-a/dedup/requirements_h3.txt
python3 teams/01-data-a/dedup/h3.py --config teams/01-data-a/dedup/h3_local.json
```

`model_path` is LaBSE (`sentence-transformers/LaBSE`) in sentence-transformers format. The model is never downloaded:
the script sets the Hugging Face libraries offline, so the run needs no network or keys. It writes only under `out/`.
`h3_summary.json` records the sha256 of the model's weights.

## Inputs

```text
<inputs>/train/**/<part>.parquet      TSAI's cleaned output, as read by overlap.py
<inputs>/heldout/**/<part>.parquet
```

or the raw layout `<pack>/Part_N/` and `<pack>/Heldout/`, where a folder named `heldout`, in any case, is held-out.
Each row needs string `pack_id`, `doc_id` and `text`; a `url` column is used when present. `packs` maps pack ID
patterns to languages; parts without a configured pack are not read. In the cleaned layout, `part` is the path under
the split folder and `row_in_part` counts every row of the part from 0, as in `overlap_docs.parquet`, so `dedup.py`
finds each H3 document in the overlap run of the same cleaned parts.

## Which pairs count

```text
coverage = aligned sentence pairs / sentences of the shorter document >= coverage_threshold (0.6)
```

Two sentences align when each is the other's best match (mutual best, one to one) with cosine ≥ the language pair's
`sentence_threshold` (0.7 unless set for the pair, e.g. `{"sa-en": 0.55}`). Both thresholds are provisional until
E5's sweep and hand review. Candidates come from two sources:

- **Retrieval:** each document's `top_k` nearest documents in the other language by the cosine of its first
  `head_sentences` sentences, with cosine ≥ `doc_floor`, in both lists when `mutual`.
- **URL key:** pages whose URLs differ only in a language marker (`hi.example.org`, `/hi/`, `?lang=hi`).

Pairs whose lengths differ by more than `max_length_ratio` are not verified, except URL pairs. At most `max_verify`
pairs are verified: URL pairs first, then by cosine. Documents shorter than `min_chars` or with fewer than
`min_sentences` sentences of at least `sentence_min_chars` characters are counted and never encoded.

Parallel packs (H3-d: Pralekha, BPCC) are handled in `h3_join.py` (`parallel_packs`), not in `h3.py`.

## Outputs

All in `out`; IDs, scores and counts only, never text. The total must fit `max_output_mb` (at most 50 MiB).

| File | Contents |
|---|---|
| `h3_docs.parquet` | Row → document: row, id, doc_id, pack, lang, split, part, row_in_part, chars, sentences |
| `h3_candidates.csv` | Every verified pair at or above `report_floor`, and every URL pair: scores, numbers Jaccard, Latin-token share, coverage |
| `h3_matches.csv` | Pairs at or above `coverage_threshold`: `pack_id`, `split`, `part`, `row_in_part`, `doc_id` of each document, `lang_a`, `lang_b`, `coverage` (the header `h3_join.py` checks) |
| `h3_by_pack.csv` | Pack × pack: retrieved, URL, verified, listed and qualifying pairs |
| `h3_histogram.csv` | Bins of 0.01: the cosine of every retrieved pair, the coverage of every verified pair |
| `h3_summary.json` | Counts, stage times and rates, the estimate for all documents, model, versions, output sha256 |

A run stopped at `max_minutes` writes only the summary, with status `stopped_time_limit`. A run limited by
`max_docs_per_pack` also estimates the time for all documents of the selected packs and suggests a Max time
(1.5 × the estimate).

## Config

Paths are relative to the repository root; `out` and `cache` must be inside `out/`. Unknown keys fail; keys starting
with `_` are comments.

| Key | Meaning | Default |
|---|---|---|
| `inputs`, `out`, `cache` | Input root; output folder; embedding cache (`""` turns it off) | `out/tokenizer_sample_v0_clean`, `out/h3`, `out/h3_cache` |
| `packs`, `pairs` | `{pack_id pattern: language}`; the language pairs to compare | required |
| `model_path`, `device`, `precision` | Local encoder folder; `auto`, `cpu`, `mps` or `cuda`; `auto` (fp16 on CUDA, else fp32), `fp32`, `fp16` or `bf16` | required, `auto`, `auto` |
| `batch_size`, `max_seq_length` | Encoder batch and token limit | 64, 128 |
| `min_chars`, `min_sentences`, `sentence_min_chars` | Shortest document and sentence compared | 200, 3, 20 |
| `head_sentences`, `max_sentences` | Sentences in the document vector; sentences kept per document | 4, 16 |
| `top_k`, `doc_floor`, `mutual` | Neighbours per document; lowest cosine kept; both lists required | 3, 0.5, true |
| `max_length_ratio` | Longer / shorter characters allowed | 4.0 |
| `sentence_threshold`, `coverage_threshold`, `report_floor` | Aligned sentence cosine: one value, or `{"sa-en": 0.55}` per language pair in either order (a pair not named: 0.7); H3 coverage; lowest coverage listed | 0.7, 0.6, 0.3 |
| `max_verify`, `url_group_max` | Pairs verified; largest URL group paired | 10000, 20 |
| `block`, `pair_batch` | Rows per retrieval step; pairs per alignment step | 512, 1024 |
| `max_docs_per_pack`, `max_minutes`, `max_output_mb` | Documents per pack (0: all); time limit; output cap | 0, 60, 50 |
| `sync_debug` | On CUDA, torch warns at every host-device sync after the read stage | false |

`h3_local.json` is the local run: at most 2,000 documents of `ind-sa-fw2`, `ind-hi-fw2` and `en-fineweb-edu` from the raw
sample v0 in `../Cap1-packs`, pairs sa–en, sa–hi and hi–en.

## Speed and end-to-end check

`h3.py`, `h3_signals.py` and `h3_align.py` are batched. Text is processed as pyarrow record batches, vectors stay in
torch on the encoder's device, retrieval is a blocked matmul with `topk`, and sentence alignment is one `bmm` per batch
of pairs. The encoder runs the model's preprocessing and forward pass in batches of texts sorted by length, instead of
`SentenceTransformer.encode()`, which loops over every row in Python and copies each batch to the device with a
host-device sync; on CUDA, token batches and index arrays go to the device from pinned memory without blocking. No
Python loop runs over rows, documents, sentences, tokens or pairs.

- Hardware: Apple Silicon, MPS backend, fp32 (`precision` `"auto"` is fp16 on CUDA, with TF32 matmuls)
- Wall time: **305.0 s** for 6,000 documents (`h3_local.json`), from a cold start (no cache), peak RSS 845 MB
- Model: LaBSE, `model.safetensors` sha256 `deaceb20157886981bdedad1da11f39687e2343e978abc10e909939fb95d40c5`
- Versions: Python 3.12.10, numpy 2.4.3, pyarrow 23.0.1, torch 2.13.0, sentence-transformers 6.3.0

| Stage | Seconds | Rate |
|---|---|---|
| load_model | 11.5 | |
| read | 8.6 | 37,472 rows |
| encode | 158.3 | 37.9 document heads/s |
| url | 0.0 | |
| retrieve | 0.1 | 3 language pairs of 2,000 × 2,000 |
| verify_read | 0.3 | |
| verify | 126.0 | 108.0 sentences/s (13,601 sentences, 738 pairs) |

- Estimate for all documents of the three packs (72,665 en, 14,220 hi, 5,956 sa) at these rates: 50.8 min; suggested Max
  time 77 min
- Encoder: `Encoder.encode` and `SentenceTransformer.encode` on the same 587 head texts, one after the other: 18.0 s and
  20.7 s; the unit vectors differ by at most 1.5e-08
- Sync check: TODO on CUDA. MPS has no sync debug mode; run with `"sync_debug": true` on CUDA.
- No Python loops over tokens, documents, sentences or pairs: yes. Loops remain over parts, record batches, encoder chunks
  of 2,048 texts and batches of `batch_size`, retrieval row blocks, pair batches, the configured packs and language
  pairs, the distinct sizes of URL groups and the distinct non-ASCII digits in numbers.
- Host copies: one per stage result, and one per part for the embedding cache. Encoder chunks go to the tokenizer as
  Python strings.
- Result: 902 candidates, 738 verified, 0 at coverage ≥ 0.6

Command:

```sh
rm -rf out/h3_cache out/h3_local && python3 teams/01-data-a/dedup/h3.py --config teams/01-data-a/dedup/h3_local.json 2>&1 | tee out/h3_local.log
```

Last lines of output:

```text
    "documents_full": {
      "en": 72665,
      "hi": 14220,
      "sa": 5956
    },
    "seconds": {
      "load_model": 11.5,
      "read": 21.3,
      "encode": 2449.9,
      "retrieve": 17.1,
      "verify": 549.9
    },
    "minutes_total": 50.8,
    "every_stage_measured": true,
    "suggested_max_time_minutes": 77,
    "basis": "this run's rates; read scales with rows, encode with documents, retrieve with the product of the two languages' documents, verify with the smaller language's documents (at most max_verify)"
  },
  "wall_seconds": 305.0,
  "peak_rss_mb": 845.2
}

Wrote h3_docs.parquet, h3_candidates.csv, h3_matches.csv, h3_by_pack.csv, h3_histogram.csv and h3_summary.json to out/h3_local
```

The full console log is `teams/01-data-a/jobs/logs/2026-11-17-h3-local.txt` and the run's summary
`teams/01-data-a/jobs/logs/2026-11-17-h3-local/h3_summary.json`.

## Tests

```sh
python3 -B -m pytest teams/01-data-a/dedup/tests/test_h3.py teams/01-data-a/dedup/tests/test_h3_signals.py teams/01-data-a/dedup/tests/test_h3_align.py -q -rs -p no:cacheprovider
```

```text
.......................................................................  [100%]
71 passed in 2.27s
```

They check each batch function of `h3_signals.py` against its per-document reference, `align_batch` against `align`
(one threshold, and one per pair), `cross_topk` against a brute force of every pair, batch sizes of 1 against the
defaults, the 13-column `h3_matches.csv` keys against `h3_docs.parquet`, the train/heldout layout, the sentence
threshold per language pair, the time limit, the cache, the config checks, and a run without the Unix-only `resource`
module (Windows), where `peak_rss_mb` is null. A fake encoder stands in for the model, so the tests need no model or
network.
