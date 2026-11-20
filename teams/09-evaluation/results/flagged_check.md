# Hand check of 50 flagged documents (week 3, task 3)

Team 9 (Evaluation), week-3 task 3. Owner: `Nisarg189`. Assigned by the Team 9 lead (`rahulni`) in G9.

**Result: the first-pass verdicts hold up.** The hand check gives the same label to 45 of 50 documents, and the same contaminated / not contaminated call to 47 of 50. The 5 changes all come from flags with a low match count: 3 flags become false hits and 2 short stems become `real`. No change makes a clean document contaminated. Contaminated documents in the sample go from 16 to 13.

The second part of task 3, the Grafana eval panel with Team 8, is panel 28 on `eval_mini` in `teams/08-monitoring/grafana/private_v1.json` (#517, merged). Team 8 checked it live in ClickHouse, and the Team 9 lead checked it against the rows from `eval_watcher.py` (#549).

## 1. Where the 50 documents come from

The lead's rule: take the hits from task 2 and from the rotators' R1 first, then top up from `results/tokenizer_sample_scan/verdicts_v0-clean.csv` (#342).

- **Task 2 and R1 hits: 0.** Task 2 (#641, `raghavTayal`) checked all 41 first training shards (1,200,725 documents) with fingerprints v2, full set, and found 0 flagged documents and 0 canary hits. The rotator files (#555, #567, #579, #580, #602, #612, #614, #627, #631, #635, #639, #647, #648) also report 0 flagged documents.
- **Top-up: all 50.** The documents come from the 1,594 v0-clean flags in `verdicts_v0-clean.csv`. That scan used fingerprints v2, full set, `set_sha256` `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`.

### Selection

The pick is fixed by a quota per first-pass verdict, so that every verdict type gets a check. This includes the rare ones. A random draw of 50 from 1,594 flags gives about 42 false hits and almost no `real-short`, `translation-source` or `same-repo-code` rows.

| First-pass verdict | Flags in the file | Picked |
|---|---:|---:|
| real | 44 | 10 |
| real-short | 24 | 6 |
| public-text | 152 | 8 |
| translation-source | 9 | 3 |
| same-repo-code | 9 | 3 |
| false-hit | 1,356 | 20 |
| **total** | **1,594** | **50** |

Inside one verdict, the rows are sorted by `sha256("<doc_id>|<item>")`. Then the pick goes round-robin over the benchmarks in name order, so one benchmark does not fill the quota. The order does not depend on the person or the machine. This code rebuilds the same 50 rows, in the same order, from the file on main:

```python
import csv, hashlib
from collections import defaultdict

QUOTA = {"real": 10, "real-short": 6, "public-text": 8,
         "translation-source": 3, "same-repo-code": 3, "false-hit": 20}
rows = list(csv.DictReader(open("results/tokenizer_sample_scan/verdicts_v0-clean.csv", encoding="utf-8")))
key = lambda r: hashlib.sha256(f"{r['doc_id']}|{r['item']}".encode()).hexdigest()
pick = []
for verdict, q in QUOTA.items():
    per_b = defaultdict(list)
    for r in sorted((r for r in rows if r["verdict"] == verdict), key=key):
        per_b[r["benchmark"]].append(r)
    order = []
    while any(per_b.values()):
        for b in sorted(per_b):
            if per_b[b]:
                order.append(per_b[b].pop(0))
    pick += order[:q]
```

The 50 rows cover 18 benchmarks and 21 source parts.

## 2. How each document was checked

Each document was read next to its benchmark item. A local viewer showed the item text from the benchmark cache and a window of the document around the match `offset` in `verdicts_v0-clean.csv`. The text came from the local copy of tokenizer sample v0-clean. The 21 part files that the 50 documents use match their `output_sha256` in `cleaned_manifest.json`. The verdict uses the same rubric as `tokenizer_sample_scan.md`, section 3 (`real`, `real-short`, `same-repo-code`, `translation-source`, `public-text`, `false-hit`). `real` and `real-short` count as contaminated.

No document text and no benchmark text is in this file or in the repo. The notes describe what matched, not the text itself.

## 3. Agreement

| | Count |
|---|---:|
| Same label as the first pass | 45 / 50 |
| Same contaminated call (`real` or `real-short` against the rest) | 47 / 50 |
| Contaminated, first pass | 16 |
| Contaminated, hand check | 13 |

Per first-pass verdict:

| First pass | Picked | Hand check |
|---|---:|---|
| real | 10 | 9 real, 1 false-hit |
| real-short | 6 | 2 real-short, 2 real, 2 false-hit |
| public-text | 8 | 8 public-text |
| translation-source | 3 | 3 translation-source |
| same-repo-code | 3 | 3 same-repo-code |
| false-hit | 20 | 20 false-hit |

The 5 changes:

- **#2, `livecodebench:release_v6:2791`, real → false-hit.** The document is a different LeetCode problem (1823, not the item's 2682). The two problems share the same circle-game introduction. The matched runs are that introduction only.
- **#12, `mmlu:test:8335`, real-short → false-hit.** One matching 13-word run in an ordinary article about CBT. The document does not contain the question.
- **#16, `mmlu:test:1643`, real-short → false-hit.** One matching 13-word run in a textbook passage about the speed of sound. The document does not contain the question.
- **#13, `milu:test:37746`, real-short → real.** The document has the exact exam question stem and its answer key.
- **#15, `milu:test:9182`, real-short → real.** The document has the complete question with the same four options.

## 4. What this means

- **The F2 decontamination filter must stay strict.** All 20 sampled false hits were correct, and no clean-labelled document was contaminated. A filter that drops every flagged document removes 1,594 of 1,416,236 v0-clean documents (0.113%). The 351 flags with only one matching run are 0.025% of the documents. Dropping them costs very little, so the filter does not need a minimum match count.
- **A flag with one matching run is weak evidence for a report.** In `verdicts_v0-clean.csv`, 351 flags have exactly one matching run: 321 false-hit, 14 public-text, 13 real-short, 3 translation-source and 0 real. All 44 `real` flags have two or more runs. In this sample, 2 of the 3 one-run `real-short` flags were false hits.
- **Recommendations (the lead decides):**
  1. For a contamination count in a report, count a one-run flag as contaminated only if the document also has the item's options or answer.
  2. For a code problem with low coverage, compare the examples and constraints, not only the statement. Sibling problems often share an introduction (#2).
  3. Keep a small hand check like this one as a control each time the fingerprint set or the normalizer changes.

## 5. Per document

`grams` is matched runs / runs in the item. `first pass` is the verdict in `verdicts_v0-clean.csv`. Changed verdicts are in bold.

| # | source | doc_id | benchmark item | grams | first pass | hand check | note |
|---:|---|---|---|---:|---|---|---|
| 1 | `train/ind-hi-hplt/part-00000` | `d07a94e8a67d8af7` | `heldout_g5_v1:heldout:fw2-hi-test-000011` | 3453/3453 | real | real | same as first pass |
| 2 | `train/code-go/part-00000` | `0a2e62f3f67dfe24` | `livecodebench:release_v6:2791` | 27/372 | real | **false-hit** | different LeetCode problem (1823 vs the item's 2682). Only the shared circle-game intro matches |
| 3 | `train/math-finemath/part-00000` | `f8f44d0005e0120a` | `milu:test:12408` | 14/69 | real | real | same as first pass |
| 4 | `train/math-finemath/part-00000` | `4eaf1b043b89917d` | `mmlu:test:4252` | 9/29 | real | real | same as first pass |
| 5 | `train/math-finemath/part-00000` | `e3e1c1926579bf19` | `heldout_g5_v1:heldout:owm-test-000022` | 29/715 | real | real | same as first pass |
| 6 | `train/math-finemath/part-00000` | `9b30bdc511be06c7` | `livecodebench:release_v6:3484` | 113/113 | real | real | same as first pass |
| 7 | `train/math-finemath/part-00000` | `1360643339d41ec6` | `milu:test:13604` | 9/27 | real | real | same as first pass |
| 8 | `train/math-finemath/part-00000` | `c88e2d5c1c61facb` | `mmlu:test:1454` | 15/54 | real | real | same as first pass |
| 9 | `train/cadj-commits/part-00000` | `f82f937d735161bc` | `heldout_g5_v1:heldout:vault-js-test-000022` | 40/71 | real | real | same as first pass |
| 10 | `train/en-dclm/part-00000` | `2d7423e919ec3079` | `milu:test:10718` | 59/77 | real | real | same as first pass |
| 11 | `train/math-finemath/part-00000` | `1e4c6961eec00d6b` | `milu:test:12395` | 1/6 | real-short | real-short | same as first pass |
| 12 | `train/en-nemotroncc/part-00001` | `f850e013d31ed753` | `mmlu:test:8335` | 1/19 | real-short | **false-hit** | ordinary article sentence about CBT, not the MMLU question. 1 matching 13-gram |
| 13 | `train/ind-hi-sangraha-v/part-00000` | `16715ac27052d77c` | `milu:test:37746` | 2/22 | real-short | **real** | exact UPSC 2014 question stem with its answer key |
| 14 | `train/math-megamath/part-00000` | `0b649af92d9a5cfc` | `mmlu:test:2064` | 13/71 | real-short | real-short | same as first pass |
| 15 | `train/math-finemath/part-00000` | `6c473e4f9f2a6256` | `milu:test:9182` | 5/30 | real-short | **real** | complete question with the same four options |
| 16 | `train/math-finemath/part-00000` | `982b1d00575fc7a7` | `mmlu:test:1643` | 1/11 | real-short | **false-hit** | textbook sentence on sound speed, not the MMLU question. 1 matching 13-gram |
| 17 | `train/code-go/part-00001` | `fed0381093e7ff4e` | `gaia:2023:2b3ef98c-cc05-450b-a719-711aee40ac65` | 9/118 | public-text | public-text | same as first pass |
| 18 | `train/en-nemotroncc/part-00000` | `73a3a2b70a4d681e` | `longbench_v2:test:66ebd0825a08c7b9b35dfe9d` | 5/190 | public-text | public-text | same as first pass |
| 19 | `train/sci-finepdfs/part-00000` | `e42e3699dad62236` | `milu:test:18206` | 9/53 | public-text | public-text | same as first pass |
| 20 | `train/en-fineweb-edu/part-00000` | `e6cc93a726d67a6f` | `mmlu:test:10707` | 1/172 | public-text | public-text | same as first pass |
| 21 | `train/en-nemotroncc-synth/part-00000` | `f20167173be6aaee` | `gaia:2023:2b3ef98c-cc05-450b-a719-711aee40ac65` | 13/118 | public-text | public-text | same as first pass |
| 22 | `train/en-fineweb-edu/part-00000` | `588792d7859965d7` | `longbench_v2:test:66ebd0825a08c7b9b35dfe9d` | 5/190 | public-text | public-text | same as first pass |
| 23 | `train/en-nemotroncc/part-00000` | `a99e6bf4cbde9ba6` | `milu:test:17933` | 1/40 | public-text | public-text | same as first pass |
| 24 | `train/en-nemotroncc/part-00000` | `c2fe659281f5d16c` | `mmlu:test:3828` | 2/40 | public-text | public-text | same as first pass |
| 25 | `train/math-megamath/part-00000` | `66e7baaf70ddab8c` | `flores200:dev+devtest:devtest:eng_Latn:613` | 12/12 | translation-source | translation-source | same as first pass |
| 26 | `train/cadj-notebooks/part-00000` | `1691d434dd306abc` | `in22_gen:test:630` | 5/192 | translation-source | translation-source | same as first pass |
| 27 | `train/en-dclm/part-00000` | `5e57e2defd59212e` | `flores200:dev+devtest:dev:eng_Latn:794` | 3/3 | translation-source | translation-source | same as first pass |
| 28 | `train/code-python/part-00000` | `ad975efd8103e5c8` | `swe_bench_live:test:pdm-project__pdm-3191` | 26/1030 | same-repo-code | same-repo-code | same as first pass |
| 29 | `train/code-go/part-00000` | `605498ba2242ee7c` | `swe_bench_pro:test:instance_gravitational__teleport-3587cca7840f636489449113969a5066025dd5bf` | 286/5462 | same-repo-code | same-repo-code | same as first pass |
| 30 | `train/code-python/part-00000` | `b4140476f57da914` | `swe_bench_live:test:conan-io__conan-16964` | 23/15601 | same-repo-code | same-repo-code | same as first pass |
| 31 | `train/math-finemath/part-00000` | `8047d6e4055e637d` | `aime_2025:test:13` | 2/65 | false-hit | false-hit | same as first pass |
| 32 | `train/en-dclm/part-00000` | `7145a6dd6832b6ff` | `bfcl_v3:test:live_irrelevance_306-76-4` | 1/1 | false-hit | false-hit | same as first pass |
| 33 | `train/math-finemath/part-00000` | `8f0f2ba59f6de2c2` | `codeforces:test:2040/A` | 5/482 | false-hit | false-hit | same as first pass |
| 34 | `train/math-finemath/part-00000` | `217ce44dfc345a39` | `gpqa_diamond:extended:recVVHkM6z2cKBZ62` | 1/323 | false-hit | false-hit | same as first pass |
| 35 | `train/en-fineweb-edu/part-00000` | `6ad102831656572a` | `heldout_g5_v1:heldout:fw2-ta-test-000028` | 3/1326 | false-hit | false-hit | same as first pass |
| 36 | `train/math-finemath/part-00000` | `9d15678843bf44cb` | `hle:test:6726c7e9d2ad475e400669c7` | 1/635 | false-hit | false-hit | same as first pass |
| 37 | `train/cadj-stackexchange/part-00000` | `e5e47f1e08c172e5` | `in22_conv:test:34-42` | 1/16 | false-hit | false-hit | same as first pass |
| 38 | `train/code-cpp/part-00000` | `78183478e3955620` | `livecodebench:release_v6:3490` | 8/135 | false-hit | false-hit | same as first pass |
| 39 | `train/math-megamath/part-00000` | `82d98563ffc9051a` | `milu:test:19384` | 4/68 | false-hit | false-hit | same as first pass |
| 40 | `train/math-megamath/part-00000` | `ab384be3a02479c4` | `mmlu:test:1408` | 1/49 | false-hit | false-hit | same as first pass |
| 41 | `train/code-go/part-00000` | `95780fc842b7a3a1` | `swe_bench_live:test:kozea__weasyprint-2326` | 3/545 | false-hit | false-hit | same as first pass |
| 42 | `train/cadj-stackexchange/part-00000` | `6a0e1580821d15b5` | `swe_bench_pro:test:instance_future-architect__vuls-999529a05b202b0fd29c6fca5039a4c47a3766bb` | 2/2169 | false-hit | false-hit | same as first pass |
| 43 | `train/code-js-ts/part-00000` | `1adf4d9d9780de22` | `swe_bench_verified:test:django__django-16502` | 1/616 | false-hit | false-hit | same as first pass |
| 44 | `train/code-rust/part-00000` | `55774bfed1a53fcc` | `terminal_bench_2:test:make-mips-interpreter` | 13/7641 | false-hit | false-hit | same as first pass |
| 45 | `train/math-finemath/part-00000` | `1dab748b3dd88e6c` | `aime_2025:test:10` | 2/111 | false-hit | false-hit | same as first pass |
| 46 | `train/cadj-stackexchange/part-00000` | `b879520ca845a280` | `bfcl_v3:test:parallel_129` | 1/47 | false-hit | false-hit | same as first pass |
| 47 | `train/math-megamath/part-00000` | `1295bba204c73365` | `codeforces:test:2009/D` | 4/181 | false-hit | false-hit | same as first pass |
| 48 | `train/math-finemath/part-00000` | `5525b76acae19175` | `gpqa_diamond:extended:recrs0kUo7Ua1xhKO` | 3/151 | false-hit | false-hit | same as first pass |
| 49 | `train/ind-ml-fw2/part-00000` | `cc9ced9db142517b` | `heldout_g5_v1:heldout:fw2-ml-test-000016` | 12/165 | false-hit | false-hit | same as first pass |
| 50 | `train/code-cpp/part-00001` | `e8aff57de88fab1e` | `hle:test:6736ddc7ab70ca0b4ee6a2e6` | 1/646 | false-hit | false-hit | same as first pass |
