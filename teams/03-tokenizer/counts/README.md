# p1536 token counts (for the KAS unigram log-prior)

Token counts of the frozen p1536 tokenizer (`e6b93a93…25a64b`, `../release/`) on the text it was trained on. G5's KAS
head (`--init logunigram`, PR #717) needs a unigram prior over the 131,072 ids. These counts are the ones that exist
now; counts from corpus-v1 (the model's training data) can replace them later without changing the format.

| File | What |
|---|---|
| `p1536_counts.json` | `total`: a list of 131,072 raw counts, index = token id. Plus `summary`, `sources` (each file's sha256, bytes, documents, tokens), `special_ids` and the software versions. 0.4 MB. |
| `p1536_counts_by_source.json` | `by_source`: each source file's counts as `{id: count}`, non-zero ids only, so another weighting can be built. 4.7 MB. |
| `count_p1536.py` | Makes both files. Checks the tokenizer and every input file against its pinned sha256 first. |
| `count_p1536.log` | The run that made them (190 s on a laptop CPU). |

## Where the text comes from

The same files p1536 was built from, pinned in `../train/p1536_s0_manifest.json` (Indic) and
`../train/heldout_manifest.json` (English and code):

| Source | Lang | MB | Docs | Tokens | Distinct ids | sha256 |
|---|---|---:|---:|---:|---:|---|
| `corpus60/Hi.txt` | Hi | 20.0 | 3,005 | 2,386,877 | 21,082 | `f9a7d43e3b7c…` |
| `corpus_s0/Hi.txt` | Hi | 416.5 | 156,831 | 49,179,029 | 51,942 | `1180b24b3a0f…` |
| `corpus60/Bn.txt` | Bn | 20.0 | 2,559 | 2,371,868 | 15,273 | `e0b4300e27dc…` |
| `corpus60/Ta.txt` | Ta | 60.0 | 6,004 | 5,844,504 | 29,006 | `7a6833efc3a5…` |
| `corpus60/Te.txt` | Te | 60.0 | 6,325 | 6,897,411 | 28,250 | `ad33037ec2ff…` |
| `corpus60/Kn.txt` | Kn | 60.0 | 8,165 | 6,476,409 | 22,803 | `8d7d649451a7…` |
| `corpus60/Ml.txt` | Ml | 60.0 | 6,561 | 5,890,997 | 23,378 | `b5f8785268ef…` |
| `corpus60/Mr.txt` | Mr | 20.0 | 2,365 | 2,183,288 | 14,596 | `a88050d1f29f…` |
| `corpus_s0/Mr.txt` | Mr | 137.5 | 23,632 | 14,605,870 | 33,824 | `ef2735f30950…` |
| `corpus_s0/Gu.txt` | Gu | 137.4 | 23,118 | 16,856,359 | 35,949 | `ac6ffb384d05…` |
| `corpus60/Pa.txt` | Pa | 20.1 | 2,390 | 2,577,454 | 15,287 | `2e3afa28202e…` |
| `corpus_s0/Or.txt` | Or | 137.5 | 33,684 | 15,298,421 | 28,065 | `f9c15bf27936…` |
| `corpus60/As.txt` | As | 20.0 | 1,957 | 2,408,382 | 15,684 | `e70f69003580…` |
| `usage/En.txt` | En | 30.0 | 9,755 | 6,499,222 | 63,839 | `32dd444500c1…` |
| `usage/Code.txt` | Code | 20.0 | 1,999 | 4,763,502 | 48,697 | `d1e20714e17d…` |
| **All** | | 1,219 | 288,350 | **144,239,593** | **121,370** | |

- **Indic:** `corpus60` is FineWeb-2 (`fetch_corpus.py`). `corpus_s0` is Data A's tokenizer sample v0 (`sample_to_corpus.py`,
  rebuilt by `../train/rebuild_cand.py`). Hi and Mr use both, Gu and Or only `corpus_s0`, the rest only `corpus60`: the
  `mix` entry of the p1536 manifest.
- **English and code:** FineWeb sample-10BT and codeparrot-clean-valid (Python), the text `prune_o200k.py` used to
  pick the o200k base tokens p1536 keeps. Train split only; no FLORES or other evaluation text.
- **Encoding:** p1536 with its normalizer, `add_special_tokens=False`. Files are split only after a newline followed
  by a non-space character, which gives the same ids as encoding each file whole (checked on Pa and Code).
- **Raw counts.** No mix factor (train_bpe.py weighted Hi and Mr corpus60 by about 21 when it learned merges), no
  smoothing, no eos. The mix is uneven: Hi is 36% of all tokens, Pa and As under 2% each. If G5 wants a flatter or
  corpus-v1-like weighting, rebuild `total` from `by_source`.

## Zero-count and special ids (for G5's policy)

| Ids | Count | Zero count | Why |
|---|---:|---:|---|
| Special tokens (bos 130725, pad 130726, unk 130727, eos 130822, chat and G10 slots, ID 36) | 356 | 356 | Text never encodes to them. |
| o200k base tokens | 103,580 | 9,344 | Kept from o200k but not used by this text: mostly other scripts (CJK, Cyrillic, Arabic, …) and rare English/code pieces. |
| Indic script blocks and extra merges | 27,136 | 2 | One Gurmukhi and one Gujarati merge. |
| **All** | 131,072 | **9,702** | |

Also: 6,010 ids have count 1 and 22,686 have counts 1–9.

The policy is G5's call. Facts that bear on it:
- **eos 130822** follows every document in Data A's shards. To count it, add one per document: 288,350 here (`summary.docs`).
- **bos / pad / unk** never appear in shards. pad should not be scored as a target.
- **Chat and G10 tokens** appear only in post-training data.
- **Zeros:** a log-prior needs a floor or smoothing (for example add-one) for the 9,702 zero ids.

## Use

```python
import json, math
c = json.load(open("teams/03-tokenizer/counts/p1536_counts.json"))
assert c["tokenizer_sha256"] == "e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b"
counts = c["total"]                                   # len 131072, index = token id
counts[c["eos_id"]] += c["summary"]["docs"]           # optional: one eos per document
alpha = 1.0                                           # example smoothing, G5's choice
z = sum(counts) + alpha * len(counts)
log_prior = [math.log((n + alpha) / z) for n in counts]
```

## Rebuild

```
python teams/03-tokenizer/counts/count_p1536.py --tokenizer teams/03-tokenizer/release/tokenizer.json \
    --corpus60 inputs/corpus60 --corpus-s0 out/corpus_s0 --usage heldout/usage --out teams/03-tokenizer/counts
```

- **Inputs:**
  - `corpus60` and `corpus_s0` are the inputs and outputs of `../train/rebuild_cand.py` (`inputs/corpus60`, `out/corpus_s0`).
  - `usage` is `fetch_heldout.py`'s `usage/` folder.
  - Any file whose sha256 differs stops the run.
- **Packages:** `tokenizers==0.23.3`.
- **Result:** the same counts. The sha256 of each output file is at the end of `count_p1536.log`.
