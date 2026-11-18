# clean() on the tokenizer sample v0: spec v1.1

`spec_v1_1/clean.py` (sha256 `6a57276c0e83…`) run end to end on all 86 parts of TSAI's pinned tokenizer sample v0, 17 Nov 2026. It was run on this sample only, not on the full packs.
- **The sample:** 86 parts (48 train, 38 heldout), 1,444,766 docs. Every part was checked against the manifest (`teams/01-data-a/jobs/2026-11-02-tokenizer-sample-v0-clean/tokenizer_sample_v0_manifest.json`) by sha256 before the run.
- **The runner:** `spec_v1/run_tokenizer_sample.py`, run through `use_clean.py`, with `jobs/tokenizer_sample_v0_clean.json`, which pins this `clean.py`.
- **Hardware:** Apple M4 (arm64), one process, Python 3.12.10.

From the directory the output goes under (the runner writes only beneath `./out/`):

```
python3 -I teams/01-data-a/spec_v1_1/use_clean.py teams/01-data-a/spec_v1/run_tokenizer_sample.py \
  --config teams/01-data-a/spec_v1_1/jobs/tokenizer_sample_v0_clean.json \
  --input-root <tokenizer sample v0 folder>
```

Last lines:

```
{"actions": {"drop": 166, "fix": 1062, "keep": 4783}, "errors": 0, "input_rows": 6011, "output_rows": 5845, "part": "train/sci-finepdfs/part-00000.parquet", "seconds": 47.764, "status": "cleaned"}
{"actions": {"drop": 3, "fix": 12, "keep": 48}, "errors": 0, "input_rows": 63, "output_rows": 60, "part": "heldout/sci-finepdfs/part-00000.parquet", "seconds": 0.172, "status": "cleaned"}
{"actions": {"drop": 34536, "fix": 363076, "keep": 1047154}, "completed_parts": 86, "errors": 0, "event": "complete", "input_rows": 1444766, "output_rows": 1410230, "peak_rss_mib": 549.141, "wall_seconds": 1260.25}
```

**The result:**
- **Wall time:** 1,260 s (21.0 min), 1,146 docs/s overall.
- **Memory:** peak 549 MiB.
- **Errors:** 0.
- **Output:** all 86 output parts are byte for byte those of the build before #50's speed fixes (`ea14b0899085…`, 1,674 s): the same `output_sha256` in `cleaned_manifest.json`, and the same `rule_counts.csv`.

**Each stage** (a part is one parquet file; a doc is one row):

| stage | parts | docs in | kept as is | fixed | dropped | docs out |
|---|---:|---:|---:|---:|---:|---:|
| 1. Input: the tokenizer sample v0, each part checked against the manifest | 86 (48 train, 38 heldout) | 1,444,766 | | | | 1,444,766 |
| 2a. `clean()` on the parts of the 31 packs with rules | 72 (41 train, 31 heldout) | 1,247,281 | 849,669 | 363,076 | 34,536 (2.8%) | 1,212,745 |
| 2b. Passed through unchanged: the parts of the 7 packs with no rules | 14 | 197,485 | 197,485 | 0 | 0 | 197,485 |
| **Output of the run (2a + 2b)** | **86** | **1,444,766** | **1,047,154** | **363,076** | **34,536 (2.4%)** | **1,410,230** |
| 3. Second pass: `clean()` again on the output of 2a (below) | 72 | 1,212,745 | 1,212,433 | 204 | 108 | 1,212,637 |

| pack | docs in | dropped | fixed | seconds | docs/s |
|---|---:|---:|---:|---:|---:|
| code-cpp | 56,158 | 963 (1.7%) | 38,283 | 45.9 | 1,224 |
| code-go | 84,139 | 6,374 (7.6%) | 45,576 | 104.5 | 805 |
| code-java | 86,060 | 542 (0.6%) | 60,663 | 72.5 | 1,188 |
| code-js-ts | 123,172 | 5,964 (4.8%) | 64,490 | 47.8 | 2,576 |
| code-python | 75,661 | 2,356 (3.1%) | 42,753 | 39.0 | 1,941 |
| code-rust | 60,738 | 1,943 (3.2%) | 32,466 | 33.5 | 1,811 |
| en-dclm | 61,975 | 1,173 (1.9%) | 8,474 | 101.6 | 610 |
| en-fineweb-edu | 72,665 | 565 (0.8%) | 1,395 | 98.6 | 737 |
| en-nemotroncc | 92,774 | 3,591 (3.9%) | 14,233 | 123.3 | 752 |
| en-nemotroncc-synth | 199,094 | 223 (0.1%) | 7,982 | 92.2 | 2,160 |
| math-finemath | 29,434 | 2,641 (9.0%) | 8,335 | 105.6 | 279 |
| math-megamath | 17,816 | 2,567 (14.4%) | 2,074 | 54.9 | 324 |
| sci-finepdfs | 6,074 | 169 (2.8%) | 1,074 | 47.9 | 127 |
| 18 Indic packs | 281,521 | 5,465 (1.9%) | 35,278 | 283.6 | 993 |
| cadj-commits, cadj-notebooks, cadj-stackexchange; ind-ml-fw2, ind-or-fw2, ind-ta-fw2, ind-ta-sangraha-s | 197,485 | 0 | 0 | 7.4 | — |

On sci-finepdfs, 52 of the fixes are the shared F1's (`f1_rule.py`). Since #49 (the team fork), the shared F1 picks its path by `pack_id`, not by the language label, so it also runs on the sample's science docs, whose label is `en`.

The last row's 7 packs have no rules. They pass through unchanged, with the status `unsupported_passthrough`.

**The spec v1.1 rules on the whole sample** (fixed / dropped, from `rule_counts.csv`):

| family | rules |
|---|---|
| English | `DA-A8-003` 3,966 fixed; `DA-A8-004` 5,108 fixed; `DA-D7-001` 6 dropped |
| math | `DA-C7-001` 1,559 dropped; `DA-C7-002` 1,509 dropped; `DA-C9-003` 662 dropped; `DA-C8-002` 572 dropped; `DA-A8-001` 2,443 fixed; `DA-C9-001` 70 fixed, 144 dropped; `DA-C8-001` 88 dropped; `DA-D6-001` 46 fixed, 57 dropped |
| science | `DA-C8-005` 463 fixed; `DA-A7-001` 386 fixed; `DA-C7-004` 139 fixed; `DA-C7-005` 98 dropped; `DA-B6-001` 42 dropped; `DA-C9-002` 29 dropped; `DA-C8-004` 80, `DA-C8-003` 16, `DA-A7-002` 12, `DA-A7-003` 16, `DA-A8-002` 10, `DA-C7-003` 2 fixed |
| Indic | `DB-C6-001` 4,581 fixed |

- **The highest drop rates are the math packs.** On math-megamath, `DA-C7-002` drops 1,509 of 17,816 docs (8.5%) and `DA-C7-001` 751. On math-finemath, `DA-C7-001` drops 808, `DA-C9-003` 620 and `DA-C8-002` 460.
- **The math gold can't bound those rates.** Megamath's gold set is 26 docs, so its 0/26 harm result bounds the harm only to about 3/26.

## Second pass: clean() on its own output

`spec_v1/run_clean.py`, through `use_clean.py`, with the same `clean.py` (`6a57276c0e83…`), on each of the 72 cleaned parts above (`--pack-id <pack>`), 1,212,745 docs, 17 Nov 2026:
- **Unchanged:** 1,212,433 docs.
- **Changed on the second pass:** 312 (0.026%): 204 fixed and 108 dropped. These come from rules that are not fully idempotent on their own output.
- **Errors:** 0. Wall time 1,216 s.

| pack | fixed | dropped |
|---|---:|---:|
| math-finemath | 78 | 0 |
| code-rust | 0 | 33 |
| en-dclm | 12 | 24 |
| en-nemotroncc | 20 | 19 |
| ind-mr-sangraha-v | 21 | 0 |
| the other 26 packs | 73 | 32 |
