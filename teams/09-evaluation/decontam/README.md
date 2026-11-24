# Decontamination check (G9, fingerprints v2)

Benchmark test questions are public, so copies of them are on the web, and the web is our
training data. If the model trains on a test question, its score on that test is not true.
This folder finds benchmark text in training documents, so that the data teams can remove it.

## How it works

1. `build_fingerprints.py` reads the benchmarks in `benchmarks.toml`. It cuts each item into
   runs of words, hashes each run and writes the hashes to `../fingerprints/v2/`.
2. `decontam_check.py` cuts each document in the same way and looks up each hash.
   A document is flagged when it shares one run with a benchmark item, or when it contains
   a benchmark canary string. The report gives the item and the character offset of the match.

Run lengths:

| Text | Run | Why |
|---|---|---|
| Prose (questions, answers, solutions) | 13 words | Used by GPT-3 and lm-evaluation-harness. Long enough that a match is not by chance. |
| Code (patches, pasted code in issues) | 20 tokens | One code line is 4 to 6 tokens (`import numpy as np`). At 13, shared imports and tracebacks gave false hits. |
| Short prose (8 to 12 words) | the whole text | A short question has no 13-word run. The whole text is stored, unless another item of the benchmark has the same text (then it is a template). |

## For the data teams (G1, G2, G10)

```
pip install pyarrow pytest
python teams/09-evaluation/decontam/decontam_check.py /path/to/shard.parquet > flagged.jsonl   # columns doc_id, text
python teams/09-evaluation/decontam/decontam_check.py docs.jsonl --id-field id --text-field text
python teams/09-evaluation/decontam/decontam_check.py shard.parquet --tags code      # quick run: code benchmarks only
```

The default set is v2 (`../fingerprints/v2/`). Use `--fingerprints teams/09-evaluation/fingerprints/v1` only to repeat an old v1 result.

One output line per flagged document (the script never prints document text):

```
{"doc_id": "35eb8b91a98d3a41", "flagged": true, "n_items": 3,
 "hits": [{"item": "mmlu:test:5817", "grams": 32, "item_grams": 210, "coverage": 0.152, "offset": 1111191}]}
```

- `grams`: the number of different runs of the item that the document contains.
- `coverage`: `grams / item_grams`. A value near 1.0 means a full copy of the item.
- A canary hit has `"canary": "<string>"` in place of `grams`.
- For a diagnosis label, write for example `mmlu:test:5817 at offset 1111191` (disease F2).

The first stderr line gives the `set_sha256` and the scope. Only the **full set** (no `--benchmarks`,
no `--tags`, no `--exclude`) is the formal check before a shard goes into training. Give the `set_sha256` in your report.
`--exclude` is only for a protected set itself (see "Protected sets" below).
The script checks the sha256 of every file before it starts. It needs about 1.1 GB of memory.
Build and run on Linux (cluster, Colab, Kaggle). On Windows, `../fingerprints/.gitattributes` makes Git keep the
fingerprint files byte for byte. Without it, Git with `core.autocrlf=true` checks them out as CRLF, and every sha256 check fails.

## Canary scan (lab canary)

Every file that holds eval items carries the **lab canary**, a plain-text line (not a special token,
TSAI ruling of 29 Oct: a special token never comes out of normal tokenization, so leaked text would not contain it):

```
ERA V5 LAB EVALUATION DATA. IT MUST NEVER APPEAR IN TRAINING DATA. canary GUID era-v5-lab:eval:<GUID>
```

`<GUID>` is the last part of `_ID_PARTS` in `lab_canary.py`. The full string is never written out whole in this repo
(code or docs): if the repo is crawled into training data, it must not carry the canary, and our own scans must not flag it.

The string is defined once, in `lab_canary.py` (`LAB_CANARY`, `LAB_CANARY_LINE`, `stamp()`). Do not change it:
files stamped with the old string would no longer be found. It is ASCII, so JSON written with
`ensure_ascii=True` keeps it unchanged.

Where it is written:

| File | Writer | Where |
|---|---|---|
| `harness_code_indic/runs/eval_mini_v0_items.json` (gitignored) | `make_eval_mini_items.py` | top-level `"canary"` and in every item, so one copied item is found too |
| `harness_code_indic/runs/<model>/<tag>/samples_<n>.jsonl` (gitignored, `--log-samples`) | `run_lm_eval.py` | `"canary"` in every sample line |

A new script that writes eval items should call `lab_canary.stamp()` on each record (JSON) or write
`lab_canary.MARKDOWN_LINE` (Markdown). Score files (`results/*.json`, `compare_*.md`) and `eval_mini_v0_spec.json`
hold no item text and are not stamped (a change to the spec would also change the `spec_sha256` in the results).

`canary_scan.py` looks for the lab canary and for every benchmark canary in the fingerprint set
(benchmarks with canaries in `MANIFEST.json`: GPQA, HLE). It does not load the fingerprints, so it needs little memory
and runs in seconds. A match is exact; one occurrence is a leak. A `--fingerprints` folder without `MANIFEST.json` is an
error (use `--lab-only` to look for the lab canary alone), so a wrong path cannot quietly drop the GPQA and HLE canaries.
A `.jsonl` line without the `--text-field` (for example `samples_<n>.jsonl`) is scanned whole, as raw text.

```
python teams/09-evaluation/decontam/canary_scan.py shard.parquet          # columns doc_id, text
python teams/09-evaluation/decontam/canary_scan.py docs.jsonl --id-field id --text-field text
python teams/09-evaluation/decontam/canary_scan.py some/folder             # .parquet .jsonl .json .txt .md below it
```

One output line per occurrence, with only the canary, the document ID and the character offset (never document text):

```
{"canary": "era-v5-lab:eval:<GUID>", "doc_id": "35eb8b91a98d3a41", "offset": 1204}
```

The summary goes to stderr (`docs N with_canary N hits N`). Exit code 1 means a canary was found; else 2 means a file
could not be read (it is named on stderr and skipped, the scan goes on); else 0. A pipeline can stop on any non-zero code. `decontam_check.py` also flags the lab canary (item `era-v5-lab:canary`), so the full
check covers it too.

## Training shards (`decode_shard.py`)

Data A's training shards ([shard format v1](../../01-data-a/shards/shard_format_v1.md)) hold token IDs, not text, and
`.docs.parquet` has IDs and counts only. `decode_shard.py` turns each shard back into a `doc_id, text` Parquet that
`decontam_check.py` and `canary_scan.py` read as it is. Use this one script for every shard check (task 2 and the
rotators' R1), so all shards are decoded the same way.

```bash
python teams/09-evaluation/decontam/decode_shard.py <shards folder or .bin> --tokenizer <p1536>/tokenizer.json --out <dir>
python teams/09-evaluation/decontam/decontam_check.py <dir>/<shard_id>.text.parquet    # full set
python teams/09-evaluation/decontam/canary_scan.py <dir>/<shard_id>.text.parquet
```

- **Tokenizer:** only a frozen `tokenizer.json` is accepted, and it must be the one the shard's manifest names:
  - **p1536** (sha256 `e6b93a93…25a64b`), frozen at Gate 3 (TSAI notice, 15 Nov; #414). **The first training shards use
    it.** Download it from the link in that notice.
  - **C3** (sha256 `15468e66…02ddc3`, G3 #340), the earlier freeze. Data A's sample shard (#373) and earlier work use it;
    G3 shares it on Kaggle.
  - The two have the same vocab (131,072), EOS (`<|endoftext|>` 130822) and 356 special tokens. Neither file is in the
    repo (8 MB).
- **Checks before decoding** (the rules `shard_writer.py` asserts, so a shard with a bad structure is refused even when its
  manifest hashes match):
  - header (magic 20261025, version 2); file size = the manifest's `payload_bytes`;
  - `.idx.npy` starts at 0, rises, ends at the token count;
  - `.docs.parquet`: one row per document, `doc_id` unique and not null, `n_tokens` equal to each document's length in
    the index (so doc_ids cannot attach to the wrong text);
  - manifest: `schema_version`, `token_dtype`, `shard_id` and the file names (the last part of each `*_uri`, which may
    be a full store path as in the template) match the files; payload, index and docs sha256, doc and token counts, EOS id
    and tokenizer sha256 match;
  - every token id is below the vocab size (131,072); every document ends with EOS 130822 and holds no special id,
    EOS included. Special ids are the same set the writer refuses: the tokenizer's special tokens (9 of them below
    130,725, e.g. 36 and 129994) plus 130,725 and above.
- **On failure:** the shard is reported and skipped, any old output for it is removed, and nothing new is written. Other
  shards still run; the exit code is 1 if any shard failed. A shard with a file missing (e.g. an incomplete download)
  fails. A `.bin` with none of the shard files next to it (e.g. a model file) is listed and ignored.
- **Which shard:** the printed summary and the output's columns give `payload_sha256`, `dataset_version` and `split`, so
  a result can be tied to the exact shard bytes in the run's shard list.
- **Text:** each document is its tokens minus the final EOS, decoded with the shard's tokenizer, so it is the
  tokenizer-normalized text the model trains on. `--check-text <run_clean.py *_clean.parquet>` (one shard per run)
  compares every decoded document with the normalized source text (round trip).
- **Output holds document text:** keep it local; never commit or paste it. Reports give IDs, items, coverage and offsets.
- **Tested** on Data A's sample shard, rebuilt with the two commands in
  [`../../01-data-a/shards/sample/README.md`](../../01-data-a/shards/sample/README.md). The rebuilt `.bin` and `.idx.npy`
  match the published sha256. The rebuilt `.docs.parquet` holds the same rows but is not byte-identical (Parquet output
  depends on the writer version), so the test used the manifest the rebuild wrote; against the committed manifest the
  decoder refuses it on `sample_metadata_sha256`, as it should. Result: 271 documents decoded, 271/271 round-trip;
  `decontam_check.py` 0 of 271 flagged (set `2826a3b8…`, full set); `canary_scan.py` 0 hits. Decoding took 0.4 s for
  262,032 tokens on a laptop CPU; a full-size shard (67M tokens) took about 33 s and 1.8 GB of memory. Corrupted copies
  of that shard (an EOS or an id ≥ 131,072 inside a document, rows shifted, two documents merged, a renamed shard, a
  broken or missing manifest) are all refused.
- **Tested with p1536:** a shard written by `shard_writer.py` from the same cleaned part with the p1536 tokenizer (the
  writer still pins C3, so it was run with `--any-tokenizer` and the shard is marked `dataset_version: test`): 263
  documents decoded, 263/263 round-trip; `decontam_check.py` 0 of 263 flagged; `canary_scan.py` 0 hits. Decoding the
  p1536 shard with C3, or the C3 shard with p1536, is refused on `tokenizer_sha256`.
- **Tests:** `pytest teams/09-evaluation/decontam/tests/test_decode_shard.py -q` (toy shards, no tokenizer file needed).
  Set `ERA_SHARD`, `ERA_TOKENIZER` (the shard's frozen tokenizer; the old name `ERA_C3_TOKENIZER` also works) and
  optionally `ERA_SHARD_CLEAN` to also test a real shard.

## Many shards in one command (`fetch_shards.py`, `check_shards.py`)

Two steps. Only the first one uses the network, so the second can run as a TSAI job (no network, reads only its
inputs, writes only to `./out/`: JOB_REQUEST.md rule 1).

```bash
# 1. download (network): manifest first, then each file checked against the sha256 in the manifest
python teams/09-evaluation/decontam/fetch_shards.py shard_links.tsv --out <shards>
# 2. check (no network): on a job host use --work ./out
python teams/09-evaluation/decontam/check_shards.py <shards> --tokenizer <p1536>/tokenizer.json --work <dir> \
    --compare teams/09-evaluation/results/decontam_shards.md
```

`check_shards.py` runs the chain above on every shard in the folder: `decode_shard.py` → `decontam_check.py` (full
set) and `canary_scan.py`. It calls the three scripts unchanged, so the result is the same as running them by hand.

- **Speed:** all steps share one pool of `--jobs` worker processes (default: the number of cores, at most one per
  2.5 GB of memory). The biggest shards start first. A decoded shard is cut into parts of about `--part-tokens`
  tokens (default 16M, whole documents), and `decontam_check.py` runs on each part in its own process. Each document is
  checked alone, so the parts give the same result as one run; the flagged count is the sum over the parts.
- **Resume:** each shard's result goes to `<work>/results/<shard_id>.json` only when all steps finish. A second run
  skips those shards, unless the tokenizer, the fingerprint set (set_sha256), the check code (code_sha256: the
  runner, the three scripts, the modules they import and the tokenizers version) or the manifest's payload changed
  (`--force` checks them again). A shard with a file missing fails and is named. A result with another set_sha256
  than the set of the run fails the run.
- **One run per work folder:** a lock on `<work>` stops a second run on the same folder at once, so it cannot delete
  the first run's files. The operating system releases the lock when a run ends, also after a crash. Use a local
  `--work` folder: the lock is not reliable on a network drive.
- **Decoded text:** deleted after each shard, and in `<work>/text` at the start and at the end of each run (also text
  that a step of a crashed run wrote late). `--keep-text` keeps it until the next run on the folder.
- **Compare:** `--compare <markdown>` checks payload_sha256, docs and tokens against the first table row of each shard
  (rows with or without a `#` column).
- **Output:** a table in the format of `results/decontam_shards.md`, plus the set_sha256, the canary count and the
  tokenizer sha256. Exit code 0 only when every shard passed, with 0 flagged, 0 canary hits and no mismatch. The
  decoded text is deleted after the checks (`--keep-text` keeps it). Never commit `<work>`.
- **Tested** on 7 of the 41 sample-v0 shards (`code-cpp-train-000000`, `code-go-train-000000`,
  `code-rust-train-000001`, `ind-gu-fw2-train-000000`, `ind-hi-sangraha-v-train-000000`,
  `ind-kn-sangraha-v-train-000000`, `ind-mr-sangraha-v-train-000000`; 181,994,759 tokens): all 7 match
  `results/decontam_shards.md` on payload_sha256, docs and tokens, 0 flagged, 0 canary hits. Laptop CPU (14 cores,
  24 GB), `--jobs 10`: 98 s. With 3 shards at a time, in name order and with no parts: 219 s. The biggest single
  process used about 1.8 GB.
- **Tests:** `pytest teams/09-evaluation/decontam/tests/test_check_shards.py -q` (no shard, tokenizer or network
  needed). One test runs the real `decontam_check.py` and `canary_scan.py` on a small set built in the test: a
  benchmark text and the lab canary planted in documents of different parts are flagged with their doc_id, and
  nothing else (as check 3 of `results/decontam_shards.md`).

## Normalize

Before the cut into runs, the text of an item and of a document is normalized, so that
`Janet’s DUCKS, lay 16-eggs!` and `janet's ducks lay 16 eggs` give the same words. The build and
the check must use the same normalizer, or the hashes do not match and the check finds nothing.

Each set names its normalizer in `MANIFEST.json` (`normalize_id`, also in each benchmark
`MANIFEST.json`). `decontam_check.py` reads that ID and uses the same normalizer. An unknown ID,
or a set with two normalizers, is refused. The normalizers are in `normalize.py`:

| ID | Set | What it does |
|---|---|---|
| `g9-v1` | v1 | Words are runs of Unicode letters, marks and numbers. Each word: NFKC, then lower case. |
| `spec-v1` | none | The spec v1 normalize function of Team 1 (`g1-spec-v1`). Words as in `g9-v1`, then NFC, a short list of compatibility folds and `casefold()`. No NFKC, so Indic digits and superscripts stay. ZWJ and ZWNJ stay. |
| `g9-v2` | v2 | The `spec-v1` words, then ZWJ (U+200D) and ZWNJ (U+200C) removed from each word. Only the match key changes: the training text keeps ZWJ and ZWNJ. See "Why g9-v2" below. |

`g1_spec_v1_normalize.py` is a byte-for-byte copy of `teams/01-data-a/spec_v1/tools/normalize.py` (commit `c7a3da375efdbecb14188465f4d830a8ff34bdc5`, PR #194). Do not edit it. A test checks its sha256 against `G1_SPEC_V1_SHA256` in `normalize.py`. A new Team 1 version means new words, so it needs new fingerprints.

`build_fingerprints.py` takes the normalizer of the version (`fpset.SET_NORMALIZE`): v2 is built with `g9-v2`.

```
python build_fingerprints.py --data-dir ~/bench-cache          # v2, g9-v2
```

### Why g9-v2, not spec-v1 as is

Training text goes through spec v1, so the match key starts from the spec v1 words. spec v1 keeps ZWJ and ZWNJ
inside words (TSAI, PR #194), which is right for the training text. For matching it is a problem:

- Benchmark items often have them: 1,723 FLORES-200 items and 3,700 MILU items.
- The web text that we train on almost never has them: 23 of the 19,000 documents of the 38 sample packs
  (19 in ind-hi-indiccorp, 3 in cadj-notebooks, 1 in ind-or-fw2). The Bengali, Hindi, Marathi, Malayalam and
  Sanskrit FineWeb-2 packs have none. Malayalam uses the atomic chillu letters.

So with `spec-v1` as is, an item that is copied without its joiners has other words, and it is not found.
Recall test: each FLORES-200 and MILU item with a fingerprint, put into a clean document, changed in one way
(items missed, FLORES-200 / MILU):

| Change in the copy | `spec-v1` | `g9-v2` | `g9-v1` (v1) |
|---|---|---|---|
| none | 0 / 0 | 0 / 0 | 0 / 0 |
| ZWJ and ZWNJ removed | 1,110 / 861 | 73 / 15 | 952 / 627 |
| a ZWNJ replaced by a zero-width space | 963 / 811 | 0 / 0 | 0 / 0 |
| a ZWNJ added after a Devanagari virama | 5,289 / 14,179 | 0 / 0 | 5,289 / 14,174 |
| a ZWNJ replaced by a space | 963 / 811 | 842 / 580 | 0 / 0 |

`g9-v1` splits words at ZWJ and ZWNJ, so it finds the last case. `g9-v2` keeps the spec v1 words whole, so it does
not. That case is the only one where `g9-v2` is not the best.

False hits: on the 38 sample packs, `spec-v1` and `g9-v2` flag the same 20 documents with the same top item.
Only 23 of these documents have a joiner, so this test covers few documents with joiners.

The 19 benchmarks of v2 built with `g9-v2` are byte for byte the set that these numbers were measured on.

## The fingerprint set (v2)

**set_sha256 (v2): `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`**, normalizer `g9-v2`.
149 MB in 143 files, every file below 4 MB. Two builds give the same `set_sha256`.

Changes from v1:

| | v1 | v2 |
|---|---|---|
| Normalizer | `g9-v1` | `g9-v2` (spec v1 words, see "Normalize") |
| Benchmarks | 17 | 19: + Terminal-Bench 2 (89 tasks) and BFCL v3 (4,441 items, PR #184) |
| Protected sets | none | G5 held-out set v1 (1,059 documents, PR #191) |
| Items / hashes | 127,696 / 8,406,653 | 133,285 / 8,940,301 |

The hash counts of the other benchmarks change a little with the normalizer (for example MILU 2,300,558 to
2,292,927, FLORES-200 160,356 to 158,493).

## Protected sets

A protected set is text that must never be in training data but is not a benchmark. v2 has one:
`heldout_g5_v1`, the G5 held-out set v1 (`teams/05-architecture/heldout_v1/data/heldout_v1.jsonl`, sha256
`21c6e4b2df8dae9d69e254f4a00fc934d2a3c70f0675065a03724299d94312bb`, tags `protected`, `heldout`). TSAI decided
(2 Nov) that Team 9 adds it to fingerprints v2. The full check flags a training document that copies a held-out document.

To check the held-out file itself against the benchmarks, leave its own entry out, or every document matches itself:

```
python teams/09-evaluation/decontam/decontam_check.py teams/05-architecture/heldout_v1/data/heldout_v1.jsonl --id-field id --exclude heldout_g5_v1
```

Result on v2: `docs 1059 flagged 0 (0.00%)`, scope `full set except heldout_g5_v1`.

Some held-out documents contain text that is on many other web pages. Without a fix, the held-out entry flagged
22 of the 19,000 sample-pack documents, all through such text: a GMAT Club timer (13), a CC BY licence line (4),
Home Assistant code (2), and Springer notes and a book-series text (3). `boilerplate/scoped/heldout_g5_v1.txt`
holds these 5 passages, cut from the held-out documents. It applies only to `heldout_g5_v1` (key `boilerplate`
in `benchmarks.toml`), so the other benchmarks do not change. With it:

- sample-pack documents flagged by the held-out entry: 22 to 0
- held-out documents found by their own entry: 1,059 of 1,059, each with full coverage

## The fingerprint set (v1)

v1 stays in `../fingerprints/v1/` for old results. It was built from the registry of its own commit: on the
current registry, a rebuild gives another `set_sha256`, because `not_covered.json` holds the `reason` of rows
that are now active.

`../fingerprints/v1/`: `MANIFEST.json` (rules, benchmark revisions, item counts, `set_sha256`,
the list of benchmarks not covered and why), `not_covered.json`, `SHA256SUMS`, and one folder for each benchmark
(`MANIFEST.json`, shards `n<run length>-<NNN>.tsv`, `canaries.txt`). A shard line is
`<item_ref> TAB <hash> <hash> ...`. Every file is below 4 MB (the repo limit is 5 MB).
The set is 141 MB in 126 files. **set_sha256 (v1): `11e290a44d1467875fdf8bebc55eab21f0a6367f411aab98a4a027a546fd372e`**

The top `MANIFEST.json` holds `set_sha256`, so it cannot be in `SHA256SUMS`. The check compares its parts
with files that are in `SHA256SUMS`: the benchmark list with the folders, the summary of each benchmark
(tags, counts) with the benchmark's own `MANIFEST.json`, and `not_covered` with `not_covered.json`.

Hashes are 8 bytes. With 8.4 million hashes, the chance that a clean document of 1,000 words
matches by accident is about 1 in 2 billion. With 6 bytes it would be 1 in 36,000.

| Benchmark | Tags | Items | Hashes |
|---|---|---|---|
| MMLU | english, knowledge | 14,042 | 1,237,715 |
| GSM8K | english, math | 1,319 | 161,315 |
| AIME 2024 / 2025 (problems and solutions) | english, math | 30 + 30 | 26,489 |
| GPQA (extended, includes Diamond) | english, reasoning | 546 | 123,133 |
| HLE | english, reasoning | 2,500 | 987,424 |
| SWE-bench Verified / Live / Pro | code, agentic | 500 + 1,272 + 731 | 2,435,152 |
| LiveCodeBench (release_v6, problem statements) | code | 1,055 | 273,462 |
| Codeforces (test, statements and editorials) | code | 468 | 263,466 |
| GAIA (validation + test questions) | english, agentic | 466 | 19,014 |
| MILU (11 languages) | indic, english, knowledge | 79,608 | 2,300,558 |
| FLORES-200 (dev + devtest, 10 pack languages + English) | indic, english, translation | 22,099 | 160,356 |
| IN22-Gen / IN22-Conv (English + 22 Indian languages) | indic, english, translation | 1,024 + 1,503 | 344,407 |
| LongBench v2 (question and choices only) | english, long_context | 503 | 74,162 |
| **Total: 17 benchmarks** | | **127,696** | **8,406,653** |

The benchmark list is `../benchmarks_v1.md` (licences, item counts, and the Admin decisions of 25 Oct).
GSM8K, FLORES-200 and IN22 are on that list as "Decontamination only" (team decision, 25 Oct). Their licences
(MIT, CC-BY-SA-4.0, CC-BY-4.0) are on the accepted list. AIME, LiveCodeBench and Codeforces are "Internal only"
in `benchmarks_v1.md`, like GAIA: the repo has their hashes and item IDs only, never their text. Benchmarks that are not built yet are in
`benchmarks.toml` as `planned` or `skip`, each with the reason. `python build_fingerprints.py --list` prints them.

Some item counts here are larger than in `benchmarks_v1.md`, because we fingerprint more than the harness runs.
A leak of any public item of a benchmark is a leak:

| Benchmark | benchmarks_v1.md (evaluation) | Fingerprints |
|---|---|---|
| HLE | 2,158 (text-only, Admin decision) | 2,500: the questions with images also have text that can leak |
| GPQA | 198 (Diamond) | 546 (extended, includes Diamond) |
| GAIA | 165 (validation) | 466 (validation + test questions) |
| SWE-bench Live | 300 (Lite) | 1,272 |


## Results

Tests: `pytest teams/09-evaluation/decontam/tests -q` gives 90 passed and 1 skipped (without `ERA_CLEAN_DOCS`).

**v2 false hits.** All 38 sample packs, 19,000 documents: **20 flagged (0.11%)**, the same 20 documents as v1
below. The two new benchmarks and the held-out set add none.

The rest of this section is for v1.

**False hits (limit 1% on all documents).** All 38 sample packs, 19,000 documents (English, code,
math, science and the 10 Indic languages): **20 flagged (0.11%)**. The 339 documents labelled `clean` in the en-nemotroncc-synth diagnosis: 0.
The 20 flagged documents are generated Go protobuf code that matches SWE-bench Pro (3), MILU questions that are also
in Indian exam pages (8, some can be real copies), a public Jefferson passage that MMLU quotes (1),
an MMLU option pattern (2), one HLE item in two documents (2), SWE-bench Live (2), and two common math
definitions (a perfect square, the distance between two points) that two LiveCodeBench problems also use (2).

**Known leaks (recall).** For each benchmark, 200 items put into clean documents:

| Benchmark | Full item found | 30-word part found |
|---|---|---|
| GSM8K, GPQA, SWE-bench Verified and Pro, GAIA | 100% | 99% to 100% |
| AIME 2024 and 2025 (30 items each), LiveCodeBench, Codeforces | 100% | 96% to 100% |
| HLE, SWE-bench Live | 99% to 99.5% | 99.4% to 100% |
| MMLU (question only, no options) | 89.5% | 100% |
| LongBench v2 (question only) | 89% | 100% |
| MILU (question only) | 77.5% | 100% |
| FLORES-200, IN22-Gen (one sentence) | 98% to 98.5% | 100% |
| IN22-Conv (one conversation turn) | 55.5% | no turn is longer than 30 words |

## How the false hits were removed (measured on the 19,000 documents)

| Step | Flagged |
|---|---|
| 13-word runs only | 385 (2.03%) |
| + boilerplate: runs mostly inside a licence text or lorem ipsum are not written (`boilerplate/`) | 109 |
| + code runs of 20 tokens, GitHub issues split into prose and code | 16 |
| + short texts (more items found, 2 more flagged) | 18 (0.09%) |
| + AIME, LiveCodeBench and Codeforces (27 Oct) | 20 (0.11%) |

Runs of numbers only (`1 2 3 ... 13`) and of single letters (`a b c ...`) are also not written.

## Contest-id check (Codeforces pools, `contest_id_check.py`)

The n-gram check finds copied text, not a reworded problem. Div. 1 and Div. 2 of one Codeforces round have
neighbouring contest ids, so a reworded copy of a benchmark problem sits in a contest next to a benchmark contest.
`contest_id_check.py` lists the pool rows whose contest is a benchmark contest (distance 0), the next round (1), or
within `--window` ids (default 3). It reads ids only and prints ids and counts only.

```
python teams/09-evaluation/decontam/contest_id_check.py --benchmark <open-r1/codeforces test parquet> --pool rows.jsonl \
    --out report.json --drop drop_ids.txt
```

The benchmark has 468 problems in 64 contests (ids 1993 to 2067). The contest id of a pool row is its `contest_id`
field, or the number in its `id` (`1990/A`, `cf_1990_B`, `1990A`). Rows without a readable contest id are counted in
the report. A hit is a reason to look, not proof of copying: ids next to each other are different problems unless the
round was split into Div. 1 and Div. 2.

## Add a benchmark

1. Add a table to `benchmarks.toml`: source, pinned `revision`, `files` with `sha256`, and the
   templates (`texts`, `code`, `mixed`). The comment at the top lists all keys.
2. `python build_fingerprints.py --data-dir ~/bench-cache --only <id>` rebuilds only that benchmark.
3. Run the tests, then measure false hits on the sample packs.

The build and the tests need Python 3.11 or later (`tomllib`). The check needs only `pyarrow`.
Code is needed only for a new source type, file format or text filter (`registry.py`).
Gated sets need accepted terms on Hugging Face and a token in `HF_TOKEN` or `~/.cache/huggingface/token`.

## Known limits

- **BFCL v3.** 728 of the 4,441 items (16%) have no fingerprint: 606 of them are below 8 words, 409 of these in
  `live_irrelevance`. A copy of only such a question is not found.
- **ZWNJ replaced by a space.** `g9-v2` does not find this change (see "Why g9-v2").
- **Very short items.** A text of fewer than 8 words is not found: a question without its choices,
  or a short conversation turn (282 of the 1,503 IN22-Conv turns are below 8 words in every language).
- **Paraphrase and translation.** A reworded or translated item is not found. n-gram matching finds copies only.
- **Shared public text.** Some items quote famous texts (Jefferson) or exam templates. A document with only these parts is flagged.
- **Speed.** Plain Python, about 225 documents per second on one core. Good for sample packs, slow for full shards.

## Next

- The other GitHub-based rows of `benchmarks_v1.md` (tau2, WebArena, OSWorld, IndicGenBench, Aider Polyglot).
- HELMET: a reader for each of its source datasets with fixed items.
- Source rule for SWE-bench (flag code files from the patched repositories), after a decision by G1 and TSAI.
