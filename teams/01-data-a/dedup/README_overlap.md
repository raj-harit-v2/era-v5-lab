# Overlap across all cleaned sample-v0 packs

`overlap.py` measures H1 exact and H2 near duplicates within and across all 38 sample-v0 packs, after cleaning.
It writes the source-by-source document shares needed to inform `source_priority_v1.md`. It does not remove
or rank documents. The current rerun request is `teams/01-data-a/jobs/2026-11-12-overlap-rerun.md`, following
`JOB_REQUEST.md`; `2026-11-04-overlap.md` records the superseded run on the earlier cleaning.

## Run on TSAI

Prepare Python 3.10+ on Linux or macOS with the pinned packages in `requirements_overlap.txt` installed before the offline job:

```sh
python3 -m pip install -r teams/01-data-a/dedup/requirements_overlap.txt
python3 -I teams/01-data-a/dedup/overlap.py --config teams/01-data-a/dedup/overlap.json
```

Speed implementation, remaining Pygments constraint, reproducible input/config preparation, full console logs and
pytest output: [benchmarks/2026-11-13-speed/README.md](benchmarks/2026-11-13-speed/README.md).

The run needs no network or keys and writes only under `out/`. `resource` supplies peak RSS. The script imports
`h1_sha256.py`, `jaccard_matrix.py`, `overlap_rules.py`, `overlap_report.py`, and the frozen
`teams/01-data-a/spec_v1/tools/normalize.py`. Pygments 2.21.0 is pinned because code token boundaries affect H2.

## Inputs and inventory

```text
out/tokenizer_sample_v0_clean/
  train/**/<part>.parquet
  heldout/**/<part>.parquet
```

Every input row needs nonempty string `pack_id`, nonempty string `doc_id`, and string `text` columns.
Pack identity comes from the embedded `pack_id`; folder names provide provenance only. All selected parts form one
combined population, including train and heldout. Reports outside the split folders are ignored. Both selected split
folders must exist. An empty split folder is allowed; the summary reports actual counts by pack and split.

`expected_packs` in `overlap.json` contains the 38 sample-v0 pack IDs: six code, four English, two math,
one science, 22 Indic, and three code-adjacent packs. Missing or unexpected packs fail before pair scoring.
This checks pack presence, not that every expected part is present: the returned part inventory must also be reviewed.
For a different approved population, update this list explicitly; `[]` disables the inventory check without filtering inputs.
Input checksum verification remains deferred. Raw sample-v0 hashes do not describe cleaned Parquet bytes.

A document occurrence is identified by its run-local matrix row and `(pack, split, part, row_in_part)`.
`doc_id` is carried through unchanged. Display IDs `<pack_id>-<doc_id>` may repeat and are never used to collapse
occurrences. Multiple copies across parts remain separate documents in the denominator.

## Which pairs count

The rules come from `dedup_design_v1.md`; its thresholds remain proposed until calibration on real data.
H1 uses the existing `h1_key`: spec-v1 `normalize.match_key`, then NFKC, casefold, and whitespace collapse,
followed by SHA-256. H1 counts regardless of H2 minimum lengths, including two empty strings.

| H2 domain | Similarity and eligibility, on both documents |
|---|---|
| Prose (`en-*`, `sci-*`, `ind-*`, `cadj-*`) | Word 5-gram Jaccard ≥0.80; at least 50 words |
| Math (`math-*`) | Word 5-gram Jaccard ≥0.90; identical multisets of signed number strings |
| Code (six `code-*` packs) | Token 5-gram Jaccard ≥0.85; at least 20 nonblank lines after removing comments |

Mixed-domain pairs must pass **both domains' rules on both documents**. For example, math/prose needs ≥0.90,
matching number multisets, and at least 50 words on both sides. Code/prose additionally needs code-token similarity
≥0.85 and 20 nonblank lines on both sides. Both texts in a mixed code/text pair use the code member's language lexer.
Code/code pairs use each member's own lexer (C++, Go, Java, TypeScript for JS/TS, Python, or Rust).

Code tokenization uses built-in Pygments lexers on the original cleaned text. It removes comments, licence comment
headers, and leading licence docstrings; preserves string literals, preprocessor directives, token values and case;
and ignores whitespace tokens. Lexer token boundaries define the token sequence. Comment-only and blank lines do not
count toward the 20-line minimum. This is lexical matching, not semantic program equivalence.
Math numbers are extracted after H1 normalization as signed digit sequences with decimal/comma separators and optional
scientific exponents. Repetitions count; numeric spelling is preserved, so `2` and `2.0` do not pass the number guard.
LaTeX and numbers remain in the word-shingle text.

An independent all-pair code-token pass finds code copies even when their word similarity falls below the raw reporting
floor. Scores are exact intersections/unions of sets of 64-bit shingle digests, with the usual hash-collision limitation.
MinHash/LSH is not needed for this measurement implementation. The five-pack local timing does not establish full-data runtime.

H3's same-language cross-source overlap is measured by the cross-pack H1/H2 matches. Translations are not detected, as stated
in the v1 design pending TSAI confirmation. A zero cell does not establish absence of translated content. This job supplies
overlap evidence for E2; it does not perform E2's survivor selection, removal counts, or gold harm check, and does not
approve applying cross-pack dedup. Indic thresholds still need the design's E4 calibration before removal decisions.

## Matrix definition

For row source A and column source B:

```text
M[A,B] = number of distinct document occurrences in A with ≥1 qualifying H1/H2 match in B
         / total document occurrences in A
```

Values are fractions in [0,1], not percentages. Each A document contributes at most once to a cell, even if it has many
matches in B. The matrix can be asymmetric: if two of ten A documents match one of five B documents, both cells are 0.2;
if B instead has two documents total, B→A is 0.5 while A→B remains 0.2.
The diagonal counts documents with **another** matching document in the same source; self-matches never count.
For a cluster of three copies, all three count toward the diagonal. This measures participation in duplication,
not the share removed after retaining one survivor. A singleton source with no matches has diagonal 0.

## Outputs

All files are written to `out/overlap/`; the total, including the summary, must fit the job's 50 MiB cap.

| File | Contents |
|---|---|
| `overlap_matrix.csv` | Requested source×source document shares; sorted pack IDs, row label `source` |
| `overlap_matrix_counts.csv` | Source A/B, matched-document numerator and total-document denominator |
| `overlap_matches.csv` | Every qualifying pair once: row IDs, H1/H2 rule, stage, packs, word/code scores |
| `overlap_pairs.csv` | Raw word-Jaccard pairs ≥`floor`, sorted by score, with provenance and H1 flags |
| `overlap_by_pack.csv` | Unordered raw pair counts at the floor, E1 thresholds, 1.0, and exact |
| `overlap_histogram.csv` | Raw word-Jaccard histogram of all N(N−1)/2 pairs, including zero scores |
| `overlap_matrix.npz` | Sparse document×document raw word scores ≥`floor`; self diagonal is 1 |
| `overlap_docs.parquet` | Document row, display ID, original doc_id, pack, split, part, row_in_part, words, shingles |
| `overlap_summary.json` | Population, input part counts, domain mapping, rules, qualifying-pair counts, time, RSS, versions, output hashes |

The document-level NPZ is separate from the source-level CSV. A sparse absent NPZ entry means below the floor.
The diagnostic word-pair files are not H2 decisions. A code-only H2 row in `overlap_matches.csv` has an empty
`word_jaccard` because its decision came from the independent token pass; H1 rows may have empty `code_jaccard`.
All matches have H1/H2 in `rule`; `stage=cross_pack` identifies the cross-source H3 scope.

## Config

Paths in the JSON config are relative to the repository root. Unknown keys fail. Keys beginning with `_` are comments.

| Key | Meaning | Default |
|---|---|---|
| `inputs` | Cleaned input root | `out/tokenizer_sample_v0_clean` |
| `splits` | Nonempty, distinct selection of `train` and/or `heldout` | both |
| `expected_packs` | Exact inventory assertion; never an input filter | `[]` |
| `out` | Destination within repository `out/` | `out/overlap` |
| `floor` | Raw word-pair reporting floor; 0 < floor ≤0.80 so prose candidates cannot be lost | 0.5 |
| `k` | Words per raw shingle; fixed at 5 for this design | 5 |
| `block` | Positive document rows per sparse multiplication block | 256 |
| `top` | Number of diagnostic pairs printed | 20 |
| `max_output_mb` | Total output cap, above 0 and at most 50 MiB | 50 |

The TSAI job uses `overlap.json` for all 38 cleaned packs. `overlap_local.json` retains the five-pack local run's
input path and inventory, independently of the TSAI job config.

`overlap_en.json` is retained only as historical context for the earlier four-English-pack raw-sample experiment.
It contains the obsolete `packs` and `sha256sums_sha256` keys, so the current script rejects it. Use `overlap.json`
for the TSAI run or `overlap_local.json` for the local run; the historical English request and log describe the older implementation.

## Returned results and the Friday 13 November deliverable

TSAI returns the successful job's nine output files plus its console log to
`teams/01-data-a/jobs/results/2026-11-12-overlap-rerun/`, following `JOB_REQUEST.md`.
Review the actual pack/part/split inventory, rules, runtime, output limit and result plausibility first.
Rebuild the matrix from returned artifacts without corpus text:

```sh
python3 -I teams/01-data-a/dedup/overlap_report.py --results teams/01-data-a/jobs/results/2026-11-12-overlap-rerun
```

This checks the document table and matches file against the returned summary's SHA-256 hashes, then writes
`out/overlap_returned/overlap_matrix.csv` and `overlap_matrix_counts.csv`. Compare them with TSAI's corresponding outputs.
After review, copy the returned matrix to `teams/01-data-a/dedup/overlap_matrix.csv` for the Friday 13 November 2026
deliverable and use it to inform the agreed source priority. The local five-pack matrix is execution evidence, not the final all-pack deliverable.

## Local evidence

The primary execution log, `teams/01-data-a/jobs/logs/2026-11-04-overlap-local.txt`, is the user's verbatim terminal
transcript for five real packs, now configured by `overlap_local.json`: code-rust, en-fineweb-edu, ind-hi-hplt, ind-mr-sangraha-v and
math-finemath. The run covered 183,976 documents in 12 parts, took 570.8 s, peaked at 2,827.1 MiB RSS, and found
372 eligible H2 pairs (371 within packs and one cross-pack), with no H1 groups. Outputs totaled 5.41 MiB including
the summary. The inputs were copied unchanged from sample v0 into cleaner-compatible directories; no cleaning was applied.
These counts and timings describe the local population, not the requested all-38-pack cleaned-input run.
The original run used `overlap.json` while it held the five-pack configuration; that effective configuration is now
`overlap_local.json`. The preserved transcript and run summary were not rewritten. To repeat the local run:

```sh
python teams/01-data-a/dedup/overlap.py --config teams/01-data-a/dedup/overlap_local.json
```

The adjacent `jobs/logs/2026-11-04-overlap-local/` folder snapshots the effective config, summary, matrix/counts,
matches, raw pack counts and histogram, plus `verification.json`. All eight recorded artifact hashes/byte sizes and
the document/part/split populations were checked. Raw pair diagnostics and all 25 matrix cells agree with their
source files; rebuilding both matrix CSVs from document rows and eligible matches was byte-identical. The full
overlap job, including math number and code line eligibility checks on corpus text, was not rerun during verification.

Unit tests remain available for edge cases and duplicate-rule behavior:

```sh
python3 -B -m pytest teams/01-data-a/dedup/tests/test_overlap.py teams/01-data-a/dedup/tests/test_overlap_rules.py teams/01-data-a/dedup/tests/test_known_pairs.py -q -p no:cacheprovider
```

Tests cover raw scores against brute force, matrix directionality and distinct counts, repeated IDs, self exclusion,
length and number guards, code comments/strings, mixed-domain rules, input inventory, and rebuilding returned results.
`test_known_pairs.py` holds the rest of the design's E3 known pairs: a whitespace/case variant and a truncated copy
(caught), same-topic pages and code sharing only its imports (kept).
The real five-pack run supplies the local timing evidence; the all-38-pack cleaned population remains unbenchmarked.
The old English/raw-sample benchmark remains historical evidence only.
