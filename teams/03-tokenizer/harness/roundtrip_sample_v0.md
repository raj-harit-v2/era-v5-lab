# Round-trip + heldout on tokenizer sample v0 (Gate 2)

Run for PR #305. Sample: week-2 tokenizer sample v0 `heldout/` (38 packs).
Candidate: C3 sample-v0 (`tokenizer.json` sha256 `15468e66457b43af79f695cbe585c0d03e3cfe7a4a5d04d189dd3c6b9f02ddc3`, #195).
Baseline: BrahmicTokenizer-131K `tokenizer.json`.

## Command

```bash
python teams/03-tokenizer/harness/run_harness.py \
  --tokenizers BrahmicTokenizer-131K \
  --brahmic-dir /path/to/BrahmicTokenizer-131K \
  --candidate c3=/path/to/c3/tokenizer.json \
  --suites heldout,roundtrip \
  --heldout-dir /path/to/sample_v0/heldout \
  --roundtrip-docs 1000
```

## Round trip

| Tokenizer | packs | docs checked | failures | docs changed by normalizer | result |
|---|---|---|---|---|---|
| BrahmicTokenizer-131K | 38 | 13154 | 0 | 0 | PASS |
| c3 | 38 | 13154 | 0 | 406 | PASS |

Docs checked = min(1000, pack size) per pack (sha256 of `doc_id`). Many packs have fewer than 1000 heldout docs.
C3 normalizer changed 406 documents; round-trip compared against the normalised string, so that is expected.

## Held-out fertility (tokens / char, lower is better)

| Pack | docs | BrahmicTokenizer-131K | c3 | Δ% |
|---|---|---|---|---|
| cadj-commits | 826 | 0.2404 | 0.2414 | +0.42% |
| cadj-notebooks | 169 | 0.2752 | 0.2702 | -1.82% |
| cadj-stackexchange | 409 | 0.2580 | 0.2592 | +0.47% |
| code-cpp | 613 | 0.2875 | 0.2890 | +0.52% |
| code-go | 872 | 0.2955 | 0.2973 | +0.61% |
| code-java | 847 | 0.2334 | 0.2324 | -0.43% |
| code-js-ts | 1234 | 0.2548 | 0.2538 | -0.39% |
| code-python | 718 | 0.2516 | 0.2512 | -0.16% |
| code-rust | 612 | 0.2554 | 0.2569 | +0.59% |
| en-dclm | 608 | 0.2192 | 0.2189 | -0.14% |
| en-fineweb-edu | 732 | 0.2112 | 0.2107 | -0.24% |
| en-nemotroncc | 954 | 0.2115 | 0.2114 | -0.05% |
| en-nemotroncc-synth | 1975 | 0.2001 | 0.1998 | -0.15% |
| ind-bn-fw2 | 112 | 0.3575 | 0.3380 | -5.45% |
| ind-bn-sangraha-v | 102 | 0.3671 | 0.3472 | -5.42% |
| ind-gu-fw2 | 239 | 0.3690 | 0.3561 | -3.50% |
| ind-hi-fw2 | 132 | 0.3096 | 0.3065 | -1.00% |
| ind-hi-hplt | 93 | 0.3164 | 0.3111 | -1.68% |
| ind-hi-indiccorp | 1094 | 0.3110 | 0.3061 | -1.58% |
| ind-hi-sangraha-s | 88 | 0.3375 | 0.3316 | -1.75% |
| ind-hi-sangraha-v | 122 | 0.3108 | 0.3058 | -1.61% |
| ind-kn-fw2 | 82 | 0.3668 | 0.3084 | -15.92% |
| ind-kn-sangraha-s | 53 | 0.3976 | 0.3391 | -14.71% |
| ind-kn-sangraha-v | 89 | 0.3731 | 0.3153 | -15.49% |
| ind-ml-fw2 | 185 | 0.3419 | 0.2915 | -14.74% |
| ind-mr-fw2 | 95 | 0.3643 | 0.2928 | -19.63% |
| ind-mr-sangraha-v | 127 | 0.3667 | 0.2923 | -20.29% |
| ind-or-fw2 | 328 | 0.5967 | 0.3519 | -41.03% |
| ind-sa-fw2 | 55 | 0.4730 | 0.4607 | -2.60% |
| ind-ta-fw2 | 58 | 0.3430 | 0.2854 | -16.79% |
| ind-ta-sangraha-s | 36 | 0.3540 | 0.2981 | -15.79% |
| ind-ta-sangraha-v | 65 | 0.3421 | 0.2877 | -15.90% |
| ind-te-fw2 | 59 | 0.3836 | 0.3259 | -15.04% |
| ind-te-sangraha-s | 47 | 0.4097 | 0.3526 | -13.94% |
| ind-te-sangraha-v | 83 | 0.3939 | 0.3385 | -14.06% |
| math-finemath | 312 | 0.2903 | 0.2904 | +0.03% |
| math-megamath | 169 | 0.2438 | 0.2446 | +0.33% |
| sci-finepdfs | 63 | 0.2377 | 0.2376 | -0.04% |
