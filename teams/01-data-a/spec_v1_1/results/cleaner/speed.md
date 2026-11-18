# clean() speed: spec v1.1

Wall time of the whole `clean()`, shared F1 included, on each of TSAI's 500-doc sample packs, 17 Nov 2026. It was run on the samples only, not on the full packs; the end-to-end run on the tokenizer sample v0 is in [tokenizer_sample_run.md](tokenizer_sample_run.md).
- **The two cleaners:** spec v1 is `spec_v1/clean.py` as on TSAI main (sha256 `22d818c72c9f…`); spec v1.1 is `spec_v1_1/clean.py` (`6a57276c0e83…`).
- **The runs:** 3 per pack and cleaner; the table gives the best.
- **Hardware:** Apple M4 (arm64), one process, Python 3.12.10, CPU only.
- **Errors:** 0 in all 186 runs.

From `teams/01-data-a`, once per pack:

```
python3 -I spec_v1/run_clean.py --pack <pack>.parquet --out <out>                          # spec v1
python3 -I spec_v1_1/use_clean.py spec_v1/run_clean.py --pack <pack>.parquet --out <out>   # spec v1.1
```

| pack | spec v1 | spec v1.1 | docs changed or dropped: v1 → v1.1 |
|---|---|---|---|
| sci-finepdfs | 4.0 s (125 docs/s) | **6.1 s (82 docs/s)** | 58 → 88 |
| math-finemath | 3.0 s (167 docs/s) | 1.8 s (278 docs/s) | 190 → 220 |
| math-megamath | 1.2 s (417 docs/s) | **1.3 s (385 docs/s)** | 72 → 135 |
| en-nemotroncc | 0.7 s (714 docs/s) | 0.7 s (714 docs/s) | 79 → 119 |
| ind-te-sangraha-v | 0.8 s (625 docs/s) | 0.6 s (833 docs/s) | 25 → 255 |
| the other 26 packs (6 code, 3 English, 17 Indic) | 0.2–3.2 s | 0.2–2.7 s: the same, or up to 0.7 s faster | the same |
| **all 31 sample packs, 15,500 docs** | **36.9 s** | **30.4 s** | |

**Where the time goes** on the packs where v1.1 adds rules (seconds per 500 docs, from the per-rule timing of `run_clean.py`, v1 → v1.1):

| pack | v1.1 rules | the shared F1 (`f1_rule.py`) | spec v1's own rules |
|---|---|---|---|
| sci-finepdfs | 3.1 | 3.6 → 2.6 | 0.3 → 0.3 |
| math-finemath | 0.6 | 0.4 → 0.2 | 2.6 → 1.0, of which `DA-C1-001` 1.7 → 0.4 |
| math-megamath | 0.8 | 0.5 → 0.2 | 0.7 → 0.3 |
| en-nemotroncc | 0.2 | — | 0.7 → 0.5 |

**The rules #50 (the team fork) made faster,** before → after (`ea14b0899085…` → `6a57276c0e83…`, the same output): seconds on the sample packs they run on, the best of 3 runs, summed.

| rule | packs | seconds |
|---|---|---|
| `DA-E3-004` | 6 code | 1.17 → 0.37 |
| `DA-C7-001` | 2 math | 0.86 → 0.40 |
| `DA-E3-003` | 6 code | 0.73 → 0.20 |
| `DA-A6-001` | 6 code | 0.54 → 0.06 |
| `DA-E2-001` | 6 code | 0.52 → 0.30 |
| `DA-A8-001` | 2 math | 0.43 → 0.18 |
| `DA-A4-002` | 6 code | 0.30 → 0.00 |
| `DA-A5-002` | 2 math | 0.28 → 0.05 |

- **Spec v1.1 is as fast as spec v1 or faster on 29 of the 31 sample packs.** It has the speed fixes of #49 (the team fork) to the shared F1, `DA-F1-005`, `DA-C1-001` and `DA-D3-005`, and those of #50 to the eight rules above; spec v1 on TSAI main has neither. Their rule-by-rule logs are in [`../speed_v1_1.md`](../speed_v1_1.md). `DA-D3-005` goes from 0.22 to 0.02 s on math-finemath.
- **It is slower only on sci-finepdfs and math-megamath,** by the time of their v1.1 rules.
- **The slowest v1.1 rules,** on the sci-finepdfs sample pack: `DA-A8-002` 0.54 s, `DA-A7-001` 0.53 s, `DA-C7-003` 0.47 s, `DA-C9-002` 0.42 s, `DA-B6-001` 0.32 s. Each is a regex pass over the text, after two speed passes (`results/sheets/harm_tests.md`, "Speed").
- **No v1.1 rule loops over tokens.** Two loop over characters: `DA-A7-003`'s `str.islower` on non-ASCII lines, and `DA-C7-001` (since #50), which steps back over the one word before each hit of its punctuation regex.
- **No new file in `spec_v1_1/` loops** over tokens or characters.
